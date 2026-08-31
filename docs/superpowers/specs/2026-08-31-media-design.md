# 模块设计：media

**日期** 2026-08-31
**spec** `docs/superpowers/specs/2026-08-31-media-spec.md`
**覆盖需求** R-media-01 … R-media-07

---

## 架构

`media` 是 H3 文生视频与 Music 3 文生歌曲的**作业运行器**：一次至多一个作业，
启动前必须拿到 `arbiter` 许可，产出落 outputs 根，结束（成功/失败/取消）时写历史并释放许可。

```
desk/media/
  __init__.py       # 导出 MediaService
  commands.py       # H3 / Music 命令行构造的唯一定义点（纯函数，零 IO）
  music3_cli.py     # Music 3 管线调用的唯一定义点（子进程入口脚本）
  executor.py       # 可替换的子进程执行器接口 + 真实现
  service.py        # MediaService：状态机、作业线程、取消、历史、事件
```

设计原则：

- **单点定义**（消灭 census A03/A04/A05）：H3 的全部固定参数（tokenizer / text-encoder /
  dit / ref-dit / video-vae / audio-vae / budget）只出现在 `commands.py`；
  Music 3 的 `Music3Pipeline` 调用只出现在 `music3_cli.py`。
  根目录 `run-h3.sh` / `run-music3.py` 在清理阶段删除（本模块交付其替代物）。
- **纯逻辑与副作用分层**：`commands.py` 是纯函数，逐参数可断言；
  一切 spawn/kill 走 `executor.py` 的接口，测试注入假执行器，任何单测不起真进程。
- **零路径硬编码**：模型根、outputs 根、`mlx-h3` 二进制、music 解释器全部来自
  `api:resolvePaths` / `data:pathRoots` 与 `api:listCatalog`（h3/music3 目录项的 `relpath`）。
- **互斥不自作主张**：media 自己不碰端口、不卸 LLM；让内存这件事完全委托
  `api:acquireHeavy`（其副作用是卸 LLM，见 R-arbiter-05）。acquire 失败即启动失败。

### 依赖（全部构造注入）

| 依赖 | 注册表接口 | 用途 |
|---|---|---|
| foundation | `api:resolvePaths`、`data:pathRoots` | outputs 根、models 根、`mlx-h3` 路径、music 解释器路径 |
| arbiter | `api:acquireHeavy`、`api:releaseHeavy`、`api:canStartHeavy` | 启动前取许可（自动卸 LLM）、结束后释放、预检拒绝原因 |
| resources | `api:listCatalog` | 取 h3 / music3 目录项的 `relpath`，拼出模型根 |
| library | `api:appendHistory`、`data:historyEntry` | 作业终态写历史 |
| executor | （内部接口） | 子进程 spawn / 读输出 / TERM / KILL |
| clock/stamp | （内部接口） | 时间戳文件名，测试注入固定值 |

---

## 组件

### 1. `commands.py` — 命令行构造（R-media-01 / R-media-02 唯一定义点）

```python
H3_BUDGET_GB = 70   # mlx-h3 --budget，仅此一处

def build_h3_command(mlx_h3_cmd: Sequence[str], h3_root: Path, *, prompt: str,
                     width: int, height: int, frames: int, steps: int,
                     output: Path) -> list[str]:
    # mlx_h3_cmd = foundation `data:pathRoots.mlx_h3_cmd` 的 argv 前缀
    #   （dev：mlx-h3 可执行单元素；bundle：内嵌解释器 + mlx_h3.cli 入口，packaging §1.3）
    # 返回完整 argv：
    # [*mlx_h3_cmd, prompt,
    #  --tokenizer  h3_root/tokenizer/tokenizer.json,
    #  --text-encoder h3_root/mlx-8bit/te_qwen3vl_a8g32.safetensors,
    #  --dit        h3_root/mlx-8bit/dit_fl2va_a8g32.safetensors,
    #  --ref-dit    h3_root/mlx-8bit/dit_ref2va_a8g32.safetensors,
    #  --video-vae  h3_root/bf16/vae/minimax_h3_video_vae_fp16.safetensors,
    #  --audio-vae  h3_root/bf16/vae/minimax_h3_audio_vae_fp32.safetensors,
    #  --width/--height/--frames/--steps,
    #  --budget 70, --output output]

def build_music_command(music_python: Path, music3_cli: Path, music3_root: Path, *,
                        caption: str, lyrics: str, duration: float,
                        output: Path) -> list[str]:
    # [music_python, music3_cli, --root music3_root,
    #  --caption caption, --lyrics lyrics, --duration duration, --output output]
```

两个函数不做存在性检查、不做 IO——只负责「参数怎么拼」这一件事，方便逐参数断言。

### 2. `music3_cli.py` — Music 3 管线入口（取代根目录 `run-music3.py`）

以**文件路径**方式被 music 解释器执行（`music_python <path>/music3_cli.py …`），
只 import `argparse` 与 `mlx_minimax_music3`，不 import `desk` 包——
因此 music venv 无需安装 desk 包。`mlx_minimax_music3` 的 import **延迟到
参数解析成功之后**（`main()` 内），模块顶层只有 `argparse`——
这使 `--help` 在未安装 mlx 管线的环境（desk 测试 venv）也能运行，
测试第 6 项（音乐 CLI 冒烟）依赖这一点。与旧脚本的差别：

- `--root` 必传（模型根由调用方解析注入，脚本内零 `Path(__file__)` 拼模型路径）；
- **不再调用 `unload-llm.sh`**（卸 LLM 是 arbiter 在 acquire 时做的，A06/A07 归它）；
- 生成结束把输出路径打到 stdout，退出码非零即失败。

### 3. `executor.py` — 可替换执行器（验收取向的落点）

```python
class ProcessHandle(Protocol):
    def iter_output(self) -> Iterator[str]: ...   # 合并 stdout/stderr，逐行
    def wait(self) -> int: ...                    # 退出码
    def terminate(self) -> None: ...              # SIGTERM
    def kill(self) -> None: ...                   # SIGKILL
    def poll(self) -> int | None: ...

class Executor(Protocol):
    def spawn(self, cmd: list[str], *, log_path: Path | None = None,
              extra_env: dict[str, str] | None = None) -> ProcessHandle: ...
        # extra_env：叠加在继承环境之上（bundle 态 H3/Music 需 PYTHONPATH=pylibs/h3|music，
        # 取自 pathRoots 的 mlx_h3_env / music_env；dev 态为空 dict）

class SubprocessExecutor:                          # 真实现：subprocess.Popen(
    ...                                           #   stdout=PIPE, stderr=STDOUT,
                                                  #   text=True, bufsize=1, start_new_session=True)
```

`start_new_session=True` 使取消时可对整个进程组发信号（mlx-h3 可能有子进程）。
测试用 `FakeExecutor`：记录被 spawn 的 argv、可编排「产出文件后退出 0」「退出 0 不产文件」
「非零退出」「阻塞直到被 terminate」四种剧本。

### 4. `service.py` — `MediaService`（状态机与作业线程）

#### `data:jobState` 形状

```json
{
  "job_id": 3,
  "status": "idle | running | done | error | cancelled",
  "kind": "video | music | null",
  "params": { "...启动时的全部参数原样..." },
  "output": "h3-20260831-101500.mp4 | null",
  "error": { "code": "…", "message": "…" } | null,
  "started_at": 1756600000.0,
  "finished_at": 1756600300.0,
  "log_len": 8192
}
```

- 服务生命周期内 `job_id` 单调递增；`idle` 时保留上一个作业的终态（前端能看到「上一单结果」）。
- 同一时刻至多一个 `running`。

#### 状态机

```
idle/done/error/cancelled ──start(video|music)──> running ──进程退出──> done | error
                                                   running ──cancel──> cancelled
start 在已 running 时 => 拒绝（media_busy），状态不变
```

#### 启动流程（`start_video_job` / `start_music_job`，R-media-01/02/05）

顺序严格如下，**任何一步失败都不 spawn 进程**：

1. 参数校验：prompt/caption 非空字符串；width/height/frames/steps 为正整数；
   duration 为正数。失败 → `invalid_params`。
2. 持锁检查自身状态：已有 `running` → 拒绝 `media_busy`。
3. 能力预检：foundation `probe_capabilities` 的 `mlx_h3`（视频）或 `music_runtime`（音乐）
   键报缺失（dev：可执行不存在；bundle：pylibs 包目录不在——判定法归 foundation §2.4）
   → 拒绝 `capability_missing`（对应 foundation R-foundation-05 的降级语义，不是崩）。
4. `api:canStartHeavy(kind)` 预检：不能开 → 以 arbiter 给的机器可读原因拒绝
   （arbiter 词汇：`media_busy` / `transition_in_progress`，取 `reason.code`，附 holder），无副作用。
5. 生成 `job_id`，然后 `api:acquireHeavy(kind, label=job_id)`（kind ∈ {video, music}）：
   这是**权威**一步，其副作用是卸掉 LLM（arbiter 按端口收割，R-arbiter-05）；成功返回一次性
   token（即下文的 permit），worker finally 的 `api:releaseHeavy(token)` 凭它释放。
   失败（含卸载失败）→ 拒绝，原因透传 arbiter 的错误码（`media_busy` / `evict_failed` /
   `transition_in_progress`；R-media-05：让出失败即启动失败）。
6. 拿到许可后才：置 `running`、拼输出路径
   `outputs_root / f"h3-{stamp}.mp4"` 或 `music3-{stamp}.wav`（stamp 来自注入的 clock，
   格式 `%Y%m%d-%H%M%S`）、`build_*_command`、`executor.spawn`、起 worker 线程。
   置 `running` 与 `executor.spawn` 后的 handle 赋值在**同一次持锁**内完成
   （`spawn` 只是 `Popen` 返回，不等待进程），因此 `cancel_job` 持锁时要么看到非
   `running`（拒绝），要么看到已就位的 handle——不存在「running 但 handle 为空」的窗口。
   若 `build_*_command` / `executor.spawn` 在此抛异常，worker 线程尚未存在，
   由 start 路径自己的 try/except 兜底：置终态 `error`（`spawn_failed`）、
   `api:releaseHeavy`、`api:appendHistory`、发 `event:jobFinished`——
   与 worker `finally` 的收尾语义一致（对应错误处理表的 `spawn_failed` 行，有专门测试）。

第 4 步只为拒绝信息的丰富度，第 5 步才是判定；两步之间的竞态由 arbiter 内部锁兜底
（acquire 失败照样正确拒绝）。

#### worker 线程（R-media-03/04/06）

```
for line in handle.iter_output(): 追加进内存日志（持锁）
code = handle.wait()
持锁判定终态：
  cancel_requested        -> cancelled
  code == 0 且 output 存在 -> done
  code == 0 且 output 不存在 -> error {code:"no_output", message:"exit 0 but output file missing"}
  code != 0               -> error {code:"exit_nonzero", message:f"exit {code}"}
finally:
  api:releaseHeavy(permit)          # 无论终态如何必然释放
  api:appendHistory(historyEntry)   # 见下
  触发 event:jobFinished(jobState)
```

`data:historyEntry`（由 library 定义形状，media 填内容）每作业一条：

```json
{ "kind": "video|music", "status": "done|failed|cancelled",
  "params": {"...全部启动参数原样，含 prompt/caption..."},
  "output": "h3-….mp4 或 null", "duration_s": 187.3, "error": "…或 null" }
```

（字段名与词汇以 library 的 `data:historyEntry` 合同为准——Phase 1.2 对齐：作业终态
`error` 写入历史时映射为 `failed`；`id`/`ts` 由 library 在 append 时补齐，media 不传。）

历史写失败（library 抛错）不改变作业终态，只追加进作业日志并写 desk 日志——
错误如实存在，但不把已成功的生成改判为失败。

#### 进度流式读取（R-media-03）

日志累积在内存（上限 1 MiB，超限丢最旧部分并记录截断标记），
`api:jobStatus` 支持增量游标：

```
job_status(log_from: int = 0) ->
  { ...jobState, "log": log[log_from:], "next_log_from": len(log) }
```

游标绑定 `job_id`：请求携带的 `job_id` 与当前不符时从 0 重发，防止旧游标读到新作业日志。
选轮询增量而非 SSE：与现有前端的轮询模式一致、可纯单测、无长连接生命周期问题（见 Assumptions）。

#### 取消（R-media-07）

```
cancel_job():
  持锁：非 running -> 拒绝 no_running_job
        置 cancel_requested = True
  handle.terminate()（对进程组）
  等 5s 仍未退出 -> handle.kill()
  终态判定由 worker 线程统一做（见上），cancel_requested 优先级最高，
  即使进程退出码为 0 也是 cancelled，不会被竞态改写成 done/error
```

释放许可、写历史、发事件都复用 worker 的 finally，不在 cancel 调用里重复做。

#### `event:jobFinished`

进程内观察者模式：`on_job_finished(callback)`；回调收到终态 `data:jobState` 快照。
回调异常被捕获并记日志，不影响作业终态。HTTP 层面消费者（ui）走 `api:jobStatus` 轮询即可。
运行期无进程内订阅者是有记录的决定（Phase 1.2 裁定；ui 设计 §1.2 原则 5 选择轮询）：
订阅点由本模块单测锻炼，作为进程内扩展点保留（注册表词汇冻结，不删不改名）。

### 5. HTTP 挂载（内部命名）

`MediaService` 以路由表交给台面服务器装配点挂载：

| 注册表接口 | HTTP | 说明 |
|---|---|---|
| `api:startVideoJob` | `POST /api/media/video` | body: prompt/width/height/frames/steps |
| `api:startMusicJob` | `POST /api/media/music` | body: caption/lyrics/duration |
| `api:cancelJob` | `POST /api/media/cancel` | — |
| `api:jobStatus` | `GET /api/media/job?log_from=N&job_id=K` | 返回 jobState + 增量日志 |

拒绝一律 `409`（busy 类）或 `400`（参数）或 `503`（capability_missing），
body 为 `{"error": {"code": "...", "message": "...", "detail": {...}}}`——机器可读原因在 `code`。

---

## 数据流

```
UI ── POST /api/media/video ──> MediaService.start_video_job
        │ 1 校验参数 + 持锁查自身状态（media_busy）
        │ 2 resolvePaths + listCatalog ──> mlx-h3 路径、h3_root、outputs_root
        │   （二进制缺失 => 503 capability_missing，此时尚未触碰 arbiter，不会白卸 LLM）
        │ 3 canStartHeavy(video) ──> arbiter（拒绝原因预检，无副作用）
        │ 4 acquireHeavy(video)  ──> arbiter（权威判定，副作用：按端口收割 LLM）
        │ 5 build_h3_command（commands.py，唯一定义点）
        │ 6 executor.spawn ──> mlx-h3 子进程 ──> outputs_root/h3-<stamp>.mp4
        ▼
   worker 线程：逐行收 stdout → 内存日志 ←── UI 轮询 GET /api/media/job（增量游标）
        │ 进程退出
        ├─ 判定 done/error/cancelled（含「exit 0 无文件 = error」）
        ├─ releaseHeavy ──> arbiter
        ├─ appendHistory ──> library（含全部参数）
        └─ event:jobFinished ──> 进程内订阅者
```

音乐作业同构，唯二差别：命令由 `build_music_command` 构造、产出为 `music3-<stamp>.wav`。

---

## 错误处理

原则：**错误保持是错误**；没有任何路径把失败包装成成功，也没有静默回退。

| 场景 | 结果 | 机器可读码 |
|---|---|---|
| 参数缺失/非法 | 400，不 spawn | `invalid_params` |
| 已有作业在跑 | 409，不 spawn | `media_busy` |
| arbiter 被占（媒体在跑 / 驱逐中 / 无法让出） | 409，不 spawn | 透传 arbiter 码（`media_busy` / `transition_in_progress` / `evict_failed`），附 holder |
| `mlx-h3` / music 解释器缺失 | 503，不 spawn | `capability_missing` |
| 子进程非零退出 | 作业 `error`，历史记 `error` | `exit_nonzero`（含退出码） |
| 退出码 0 但产出文件不存在 | 作业 `error`（**绝不报成功**，R-media-06） | `no_output` |
| 取消 | 作业 `cancelled`，TERM→5s→KILL | — |
| 取消时无作业 | 409 | `no_running_job` |
| spawn 本身抛异常 | 作业 `error`，**仍释放许可、仍写历史** | `spawn_failed` |
| appendHistory 抛异常 | 记日志，不改作业终态 | — |
| releaseHeavy 抛异常 | 记日志并把异常上抛给日志系统（arbiter 状态以 arbiter 为准） | — |

释放许可有两个互斥的兜底点，合起来覆盖 acquire 成功之后的全部路径：
worker 的 `finally` 覆盖 done/error/cancelled/worker 内异常；
acquire 之后、worker 线程启动之前的失败（`build_*_command` / `executor.spawn` 抛异常）
由 start 路径的 try/except 收尾（见启动流程第 6 步）。
不存在「作业死了、许可还占着」的泄漏路径（两处各有专门测试）。

---

## 测试

全部 pytest、`tmp_path`、注入 FakeExecutor / FakeArbiter / FakeHistory / 固定 clock；
不起真进程、不碰真权重、秒级跑完。测试文件 `tests/test_media_commands.py`、`tests/test_media_service.py`。

1. **命令构造逐参数比对**（防两处漂移复发，R-media-01/02）
   - `build_h3_command` 的完整 argv 与期望列表**全等**断言：含六个模型文件相对路径、
     `--budget 70`、宽高帧步与输出路径；
   - `build_music_command` 同理：`--root/--caption/--lyrics/--duration/--output` 全等断言；
   - 断言仓库内 `--ref-dit` 等 H3 参数字符串只在 `desk/media/` 出现（census A03/A04 的守卫，
     与 census 重跑命令一致）。
2. **四种执行剧本**（R-media-04/06/07）
   - 成功且产出文件：状态 `done`，`output` 为 `h3-<注入 stamp>.mp4`，历史一条含全部参数与 `duration_s`；
   - 退出 0 但无文件：状态 `error`/`no_output`，历史记失败；
   - 非零退出：状态 `error`/`exit_nonzero`；
   - 运行中取消：FakeHandle 阻塞剧本，`cancel_job` 后状态 `cancelled`，
     断言 terminate 被调用、且进程退出码 0 也不会改写成 done。
3. **许可纪律**（R-media-05）
   - FakeArbiter 拒绝 acquire：断言 `FakeExecutor.spawn` **从未被调用**，返回码透传；
   - 四种终态后 FakeArbiter 的 release 恰好被调用一次；
   - spawn 抛异常时 release 与 appendHistory 仍被调用。
4. **互斥与状态**
   - running 中再次 start：`media_busy`，原作业不受影响；
   - 双线程同时 start：恰一个成功（服务内锁）。
5. **日志游标**（R-media-03）
   - 分批喂日志行，`job_status(log_from)` 增量正确；`job_id` 不匹配时从头返回；截断标记用例。
6. **音乐 CLI 冒烟**
   - `music3_cli.py` 以 `--help` 子进程运行（不 import mlx 管线的路径下）断言参数面；
     真实生成不进自动验收。
7. **reality gate（人工 runbook，不入自动验收）**
   - 真出一条 5 秒视频：面板发起 512×288×73 帧×10 步，确认 `outputs/h3-*.mp4` 可播、
     历史一条、期间加载 LLM 被拒；
   - 真出一首 30 秒歌：同理确认 `music3-*.wav` 可听；
   - 生成中途点取消：进程消失（`pgrep mlx-h3` 为空）、状态 `cancelled`、arbiter 回到 idle。

---

## Assumptions（内部决定，记录备查）

1. **进度通道选轮询增量游标而非 SSE**：`api:jobStatus` 携带 `log_from`/`job_id` 返回增量日志。
   现有前端就是轮询模式，纯逻辑可单测；若 ui 设计最终要 SSE，可在 HTTP 层加一个包装端点，
   `MediaService` 接口不变。
2. **`resolvePaths` 需提供的键名（Phase 1.2 已与 foundation 对齐）**：`outputs_root`、
   `models_root`、`mlx_h3_cmd`（argv 前缀）+ `mlx_h3_env`、`music_python` + `music_env`、
   `media_cli_dir`（`music3_cli.py` 所在目录，bundle 内只读资源）。media 侧全部经构造参数
   注入，键名再演进时改动收敛在装配处。
3. **h3 / music3 模型根 = `models_root / catalog[key].relpath`**，`relpath` 取自
   `api:listCatalog` 的 h3、music3 目录项；media 不自带第二份路径清单。
4. **取消也写历史**（status=`cancelled`）：R-media-04 要求每作业一条历史，取消是作业的终态之一。
5. **TERM→KILL 宽限 5 秒**，spawn 使用进程组（`start_new_session`），信号发给组。
6. **日志上限 1 MiB** 环形截断并带截断标记；H3 数分钟的输出量远低于此，纯保险。
7. **`--budget 70` 保留为 `commands.py` 常量**：它是 mlx-h3 的显存预算参数（现行两处脚本同值），
   不是 A09 那类写死内存读数；单点定义即可，不做成配置项（YAGNI）。
8. **`idle` 状态保留上一作业终态**供前端展示；`job_id` 服务生命周期内单调递增，不持久化。
9. **HTTP 路径前缀 `/api/media/*`** 为内部命名；注册表接口名到路径的映射见「HTTP 挂载」表。
10. **media 不做模型完整度预检**：权重不齐由子进程失败如实上报（`exit_nonzero`）；
    完整度是 resources 的职责，ui 在资源面板呈现。media 只对二进制/解释器缺失做快速拒绝。
