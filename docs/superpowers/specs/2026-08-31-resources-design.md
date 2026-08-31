# 模块设计：resources

**日期** 2026-08-31
**对应 spec** `2026-08-31-resources-spec.md`
**覆盖需求** R-resources-01 … R-resources-09
**消费** `api:resolvePaths`、`data:pathRoots`（foundation）、`api:canStartHeavy`（arbiter）

---

## 架构

### 定位

resources 是「模型资源」的唯一权威：目录定义、完整度校验、下载续传、删除与磁盘核算。
它取代并消灭 census A01/A02（两份目录）与 A20/A21（两处弱完整度判定）。

### 分层

```
desk/resources/
  catalog.py      # 目录单点（R-01）：8 条 ModelEntry，纯数据，零 I/O
  manifest.py     # HF 文件清单：取得 / 缓存 / 降级（R-02）
  verify.py       # 纯函数校验：清单 × 本地树 → ModelStatus（R-02/03）
  disk.py         # 占盘核算 + 卷剩余空间（R-04）
  downloader.py   # 单飞下载器：hf 子进程 + 进度采样 + 取消（R-05/06/07/09）
  events.py       # 进程内事件：downloadProgressed / downloadFinished
  service.py      # ResourcesService 门面：把上述件装配成 api:* 接口
  http.py         # JSON 路由处理器（由 desk 应用组合根挂载到 /api/resources/*）
```

设计原则：

- **catalog 零 I/O、verify 纯函数**——可深度单测，不碰网络不碰真权重。
- **所有副作用（网络、子进程、磁盘遍历）走可注入的接口**（fetcher、executor、clock），
  测试注入假件；spec 明确要求「下载器对 hf 命令的调用用可替换的执行器接口」。
- **所有路径来自 foundation**：`ResourcesService` 构造时接收 `data:pathRoots`
  （经 `api:resolvePaths` 解析出的 `models_root`、`data_root`），模块内零 `Path.home()`。
- **单飞**：模块级互斥保证同时至多一个下载（R-09 前半）；媒体重活由注入的
  `api:canStartHeavy` 回调判定（R-09 后半）。
- 错误保持为错误：结构化 `{error: {code, message, detail?}}`，绝不伪造成功或回退假数据。

### 与其他模块的接口位置

| 对手方 | 关系 |
|---|---|
| foundation | 构造注入 `pathRoots`；models_root 可因首运/收编变化，service 每次操作时向 `api:resolvePaths` 取当前值，不缓存 |
| arbiter | `startDownload` 前调用注入的 `can_start_heavy()`；仅当**媒体作业进行中**时拒绝下载（LLM 驻留不阻塞下载，下载不占统一内存） |
| llm / media | 通过 `api:listCatalog` / `data:modelEntry` 取模型路径与元数据，不再各持一份 |
| ui | 通过 `/api/resources/*` HTTP 端点消费全部能力；轮询 `data:downloadProgress` |

---

## 组件

### 1. `catalog.py` — 目录单点（R-01）

```python
@dataclass(frozen=True)
class ModelEntry:            # data:modelEntry
    key: str                 # 短稳定 id：h3 / music3 / glm / superqwen / qwen27 / gemma / qwen35 / llama70
    name: str                # 展示名（沿用 server.py 的中文名）
    group: str               # "chat" | "video" | "music"（spec canonical，不再用 llm/h3/music3）
    hf_repo: str             # HF 仓库 id
    relpath: str             # 相对 models_root 的落盘路径（llms/<org>/<repo>、minimax-h3、minimax-music3）
    gb: float                # 人类可读体积估算（UI 与 arbiter 内存预警用）
    vision: bool = False     # 仅 chat 组有意义
    quant: str | None = None
    params: str | None = None

CATALOG: tuple[ModelEntry, ...]        # 恰好 8 条：h3、music3 + 6 个 chat
def list_catalog() -> list[ModelEntry]  # api:listCatalog
def entry(key: str) -> ModelEntry       # 未知 key 抛 UnknownModelError
```

8 条数据从现 `initModels.sh` CATALOG（repo/relpath/size）与 `server.py` MODEL_CATALOG
（name/vision/quant/params/gb）合并而来，落地后这两处删除（census A01/A02）。
这是仓库内**唯一**一处模型 repo/路径清单；前端经 HTTP 取目录，JS 里不复制。

### 2. `manifest.py` — HF 清单与缓存（R-02）

```python
@dataclass(frozen=True)
class ManifestFile:
    path: str        # 仓库内相对路径
    size: int        # 字节数

@dataclass(frozen=True)
class Manifest:
    repo: str
    files: tuple[ManifestFile, ...]
    fetched_at: str          # ISO 时间戳
    source: str              # "fresh" | "cached"

class ManifestStore:
    def __init__(self, cache_dir_provider, fetcher=default_fetcher): ...
    def get(self, entry: ModelEntry, refresh: bool = False) -> Manifest
        # refresh=True 或无缓存 → 走 fetcher；网络失败 → 回落缓存(source="cached")
        # 网络失败且无缓存 → 抛 ManifestUnavailableError（不假装校验过）
```

- `default_fetcher(repo)`：GET `https://huggingface.co/api/models/{repo}/tree/main?recursive=true`
  （分页跟随），每个 blob 取 `path` 与 `size`（LFS 文件取 `lfs.size`）。**只取路径与字节数，
  不做哈希**——spec 以「路径 + 字节数」为完整度基准，逐字节哈希 339G 属 reality-gate 范畴，不做。
- 缓存位置：`<data root>/manifests/<key>.json`，内容 = Manifest 的 JSON 序列化。
  写入用「临时文件 + `os.replace`」原子替换（与 foundation R-06 同法，但实现独立在本模块内，
  因为 foundation 只承诺 config.json 的原子性）。
- 降级语义（spec：「缓存失效时明确降级说明」）：
  - fetch 成功 → `source="fresh"`，覆写缓存；
  - fetch 失败、有缓存 → `source="cached"` + 原 `fetched_at`，状态里如实带出；
  - fetch 失败、无缓存 → `ManifestUnavailableError` → 该项校验结果 `state="unknown"`
    （见下），**绝不**报 present/missing。

### 3. `verify.py` — 完整度校验（R-02/R-03）

```python
@dataclass(frozen=True)
class FileGap:
    path: str
    expected_size: int
    local_size: int          # 0 = 完全缺失，>0 且 < expected = 短缺

@dataclass(frozen=True)
class ModelStatus:           # data:modelStatus
    key: str
    state: str               # "present" | "partial" | "missing" | "unknown"
    percent: float           # 按字节：sum(min(local,expected)) / sum(expected) * 100；unknown 时为 0
    bytes_expected: int      # 清单总字节；unknown 时为 0
    bytes_local: int         # 逐文件 min(local, expected) 之和
    disk_bytes: int          # 该目录实际占盘（含清单外杂物与 .cache 半成品）
    gaps: tuple[FileGap, ...]        # partial/missing 时的缺失与短缺清单；present 为空
    manifest_source: str     # "fresh" | "cached" | "none"
    manifest_fetched_at: str | None
    reason: str | None       # state=="unknown" 时 = "manifest_unavailable"

def verify_tree(entry, manifest: Manifest, models_root: Path) -> ModelStatus   # 纯函数
```

判定规则（取代 A20/A21 的「见到任一 safetensors 即算齐」）：

- 对清单每个文件 stat `models_root/relpath/文件路径`：不存在 → local=0；存在 → 取 st_size。
- 全部文件 local == expected → `present`；全部 local == 0 且目录无清单内文件 → `missing`；
  其余 → `partial`，百分比按**字节**（不是文件数）。
- 超出 expected 的本地字节不计入 percent（min 截断），杂物只体现在 `disk_bytes`。
- `verifyModel(key, refresh=False)`：manifest.get → verify_tree；`verifyAllModels(refresh=False)`：
  逐条执行，单条 manifest 失败不拖垮整体（该条 `state="unknown"`，其余照常）。

### 4. `disk.py` — 磁盘核算（R-04）

```python
def dir_bytes(path: Path) -> int          # os.walk + lstat 求和；不存在 → 0；不跟符号链接
def volume_free(path: Path) -> DiskUsage  # os.statvfs(models_root)

@dataclass(frozen=True)
class DiskUsage:
    models_root: str
    free_bytes: int          # f_bavail * f_frsize（普通用户可用）
    total_bytes: int
    per_model: dict[str, int]   # key -> dir_bytes
```

`api:diskUsage` = `DiskUsage`。`models_root` 不存在时 statvfs 其最近存在的父目录。

### 5. `downloader.py` — 下载器（R-05/06/07/09）

```python
class Executor(Protocol):                 # spec 要求的可替换执行器
    def spawn(self, cmd: list[str], cwd: Path | None) -> Handle: ...
class Handle(Protocol):
    def poll(self) -> int | None
    def terminate(self) -> None           # TERM
    def kill(self) -> None                # KILL

@dataclass
class DownloadProgress:                   # data:downloadProgress
    key: str | None          # 当前（或最后一次）下载的目录项；从未下载过 → None
    state: str               # "idle" | "running" | "finished" | "cancelled" | "failed"
    bytes_done: int
    bytes_total: int
    percent: float
    current_file: str | None # 最佳努力：清单内最近 mtime 且未达 expected 的文件
    rate_bps: float          # 采样窗口 EWMA
    eta_seconds: float | None
    started_at: str | None
    error: dict | None       # state=="failed" 时的 {code, message}

class Downloader:
    def __init__(self, executor, manifest_store, resolve_paths, can_start_heavy,
                 events, clock=time.monotonic, sample_interval=1.0): ...
    def start(self, key: str) -> DownloadProgress          # api:startDownload
    def cancel(self) -> DownloadProgress                   # api:cancelDownload
    def progress(self) -> DownloadProgress                 # 供 GET 轮询
```

行为：

- **start**（持模块锁串行判定）：
  1. 已有下载 `running` → `DownloadBusyError("download_in_progress")`（R-09 前半：至多一个）。
  2. `can_start_heavy()` 报告**媒体作业进行中** → `MediaBusyError("media_busy")`，
     错误 message 带 arbiter 给出的原因（R-09 后半）。
  3. `manifest_store.get(entry, refresh=True)` 拿最新清单（拿不到就用缓存；两者皆无 →
     照样可以下载——hf 自己知道清单——但进度的 `bytes_total=0`、percent 不可算，如实报出）。
  4. `executor.spawn([*hf_cmd, "download", entry.hf_repo, "--local-dir", str(dest)])`——
     `hf_cmd` 取自 `data:pathRoots.hf_cmd`（Phase 1.2 与 foundation/packaging 对齐：
     dev 态为 PATH 上的 hf 可执行；bundle 态为内嵌解释器 + huggingface_hub 的 hf 入口，
     因为 GUI App 进程的 PATH 里没有 `/opt/homebrew`，裸调 `"hf"` 在 bundle 态必失败）。
     hf CLI 原生断点续传：已完整文件跳过、半成品从 `.cache/huggingface/` 续传（R-05）。
     `hf_cmd` 为空（dev 态 PATH 无 hf）或首元素不存在 → `HfCliMissingError("hf_cli_missing")`，
     启动即失败，不装死。
  5. 起采样线程：每 `sample_interval` 秒对目的树跑一次 `verify_tree` 口径的字节统计
     （min 截断求和，另加 `.cache/huggingface/download/` 下 `*.incomplete` 的字节，
     上限截到 bytes_total），算 rate（EWMA）与 eta，节流发 `event:downloadProgressed`（≤1次/秒）。
  6. 子进程退出：rc==0 → `finished` + 终验 `verify_tree`（结果进事件载荷）；
     rc!=0 且非取消 → `failed`（error 带 rc 与 stderr 尾部）。两者皆发 `event:downloadFinished`。
- **cancel**：无进行中下载 → `NotDownloadingError("not_downloading")`。
  否则 `cancel()` 发 TERM、把状态置 `cancelled` 后**立即返回**（不阻塞 HTTP 线程）；
  KILL 升级由采样线程负责：继续 `poll()`，自 TERM 起 8 秒（用注入 clock 计时，可测）仍未退出则 `kill()`。
  子进程真正退出时由采样线程发 `event:downloadFinished` 并释放单飞锁——锁只在进程确认退出后释放，
  避免「cancel 返回了但旧 hf 还活着，新下载已经开跑」的并发写同一目录。
  **绝不清理**目的目录与 `.cache` 半成品（R-06 可续传）。
- **进度状态的线程安全**：进度由采样线程在 Downloader 内部锁下更新；`progress()` 在同一把锁下
  拷贝出一份不可变快照返回（HTTP 线程读到的永远是一致的一帧，不与采样写并发撕裂）。
- 进度语义（R-07）：`bytes_done`/`bytes_total` 按清单字节；`current_file`、`rate_bps`、
  `eta_seconds` 标注为最佳努力估算（来自目录采样，不解析 hf 的 stdout——那是脆弱的私有格式）。

### 6. `events.py` — 进程内事件

```python
class ResourceEvents:
    def subscribe_progress(self, fn: Callable[[DownloadProgress], None]) -> None
    def subscribe_finished(self, fn: Callable[[DownloadProgress], None]) -> None
    def emit_* (...)   # Downloader 调用；回调异常被捕获记日志，不得打断下载
```

`event:downloadProgressed` / `event:downloadFinished` 即上述两个订阅点。
运行期无兄弟订阅者是有记录的决定（Phase 1.2 裁定）：ui 明确选择短轮询（ui 设计 §1.2 原则 5），
shell 亦然（shell 设计 A-9 同理）；HTTP 消费者一律走 `GET /api/resources/download` 的
`data:downloadProgress` 快照，事件与快照载荷同源。两个订阅点由本模块单测锻炼，
作为进程内扩展点保留（注册表词汇冻结，不删不改名）。
当前唯一消费方是 HTTP 轮询（UI 用 `data:downloadProgress`），事件保留为进程内观察者，
不引入 SSE/WebSocket（YAGNI；UI spec 的消费清单里也只有轮询数据）。

### 7. `service.py` — 门面与装配

```python
class ResourcesService:
    def __init__(self, resolve_paths, can_start_heavy,
                 fetcher=default_fetcher, executor=SubprocessExecutor()): ...
    # api:listCatalog        -> list[ModelEntry]
    # api:verifyModel        (key, refresh=False) -> ModelStatus
    # api:verifyAllModels    (refresh=False) -> list[ModelStatus]
    # api:startDownload      (key) -> DownloadProgress
    # api:cancelDownload     () -> DownloadProgress
    # api:deleteModel        (key, confirm) -> {key, freed_bytes}
    # api:diskUsage          () -> DiskUsage
    # events: ResourceEvents 实例公开为属性
```

**deleteModel（R-08）**：

1. `confirm` 必须**等于该项的 key**（如 `deleteModel("glm", confirm="glm")`）；
   缺失或不匹配 → `ConfirmRequiredError("confirm_required")`，一律拒绝执行。
2. 目标 = `(models_root / entry.relpath).resolve()`；必须满足
   `target.is_relative_to(models_root.resolve())` 且 target != models_root，
   否则 `PathEscapeError("path_escape")`（符号链接逃逸在 resolve 后同样被拒）。
3. 该项正在下载 → `DownloadBusyError`（先取消再删）。
4. `shutil.rmtree(target)`，返回释放字节数（删前 `dir_bytes`）。目录不存在 → 幂等成功，freed=0。
5. 本模块**从不**收到绝对路径参数——只收 catalog key，路径永远由 relpath 推导，
   这本身就封死了「删 models 根之外」的大半攻击面；resolve 校验兜底符号链接。

### 8. `http.py` — HTTP 端点（挂载于台面服务 127.0.0.1:8766）

| 方法 路径 | 映射 | 说明 |
|---|---|---|
| GET `/api/resources/catalog` | listCatalog | `{"models": [modelEntry…]}` |
| GET `/api/resources/status?refresh=0\|1` | verifyAllModels + diskUsage | `{"models": [modelStatus…], "disk": diskUsage}` |
| GET `/api/resources/status/<key>?refresh=` | verifyModel | 单项 |
| GET `/api/resources/download` | progress | data:downloadProgress |
| POST `/api/resources/download` `{"key"}` | startDownload | 409 + error code 于拒绝时 |
| POST `/api/resources/download/cancel` | cancelDownload | |
| POST `/api/resources/delete` `{"key","confirm"}` | deleteModel | 400/403 于拒绝时 |
| GET `/api/resources/disk` | diskUsage | |

处理器只做 JSON 编解码与错误码→HTTP 状态映射，业务全在 service；由 desk 应用组合根注册。

---

## 数据流

### 校验（资源面板打开 / 刷新）

```
UI ── GET /api/resources/status ──> service.verifyAllModels()
  对每条 entry：
    ManifestStore.get(entry)          # 缓存命中且非 refresh → 不碰网
      ├─ fresh/cached → verify_tree(entry, manifest, models_root)  # 只 stat，不读内容
      └─ unavailable  → ModelStatus(state="unknown", reason="manifest_unavailable")
  + diskUsage()
UI 渲染：齐 / 一半 N%（缺哪些文件）/ 没下 / 无法校验（含降级说明），占盘与剩余空间
```

### 下载与续传

```
UI ── POST download {key} ──> Downloader.start
   [锁] 单飞检查 → can_start_heavy() 媒体检查 → manifest refresh → spawn hf
   采样线程 1s/次：目录字节统计 → progress 更新 → event:downloadProgressed
UI 轮询 GET /api/resources/download 画进度条（bytes/总量/当前文件/速率/ETA）
中断（cancel 或断网失败）→ 半成品原地保留
再次 POST download {key} → 同一 hf 命令重跑 → 已完整文件被 hf 跳过，半成品续传
结束 → event:downloadFinished（载荷含终验 ModelStatus）
```

### 删除

```
UI（确认对话框）── POST delete {key, confirm:key} ──> service.deleteModel
   confirm 校验 → 路径归属校验 → 非下载中校验 → rmtree → 返回 freed_bytes
UI 随后重新 GET status 看到 missing + 剩余空间回升
```

---

## 错误处理

统一异常体系 `ResourceError(code, message, detail=None)`，HTTP 层映射：

| code | 场景 | HTTP |
|---|---|---|
| `unknown_model` | key 不在 8 条目录里 | 404 |
| `manifest_unavailable` | 无网且无缓存，无法校验（只出现在 ModelStatus.reason，不是异常路径的 500） | 200（状态如实带出） |
| `download_in_progress` | 已有下载在跑 / 删除下载中的项 | 409 |
| `media_busy` | arbiter 报媒体作业进行中 | 409 |
| `not_downloading` | cancel 时无进行中下载 | 409 |
| `hf_cli_missing` | 找不到 hf 可执行 | 503 |
| `confirm_required` | deleteModel 缺确认或确认不匹配 | 400 |
| `path_escape` | 解析后路径不在 models 根之下 | 400 |
| `download_failed` | hf 退出码非 0（非取消） | 体现在 progress.error，轮询可见 |

原则：

- **不发明回退输出**：校验不了就是 `unknown` + 原因；下载失败就是 `failed` + rc/stderr 尾部；
  没有任何「假装 present」「假装下载完成」的路径。
- 下载子进程崩溃由采样线程的 `poll()` 发现，状态收敛为 `failed`，锁释放，可重新 start（即续传）。
- 采样/事件回调内的异常捕获记日志（日志走 foundation 的 logs 目录），不影响下载主体。
- 台面服务重启后：`DownloadProgress` 回到 `idle`（进程内状态不持久化），
  半成品仍在盘上，`verifyModel` 如实报 `partial`，用户可一键续传——这正是 R-05 的语义，
  不需要下载状态持久化（YAGNI）。

---

## 测试

全部 `pytest`，位于 `/Users/aa/LocalModelDesk/tests/`，用 `tmp_path`；
**不触网、不碰真权重、不真跑 hf**。

### catalog（R-01）
- 恰好 8 条；key 唯一；组分布 = 1 video + 1 music + 6 chat；chat 条目带 vision/quant/params/gb；
  relpath 均为相对路径且不含 `..`。
- census 复核（实现任务完成后，A01/A02）：`grep -rn 'CATALOG=\|MODEL_CATALOG' --include='*.sh' --include='*.py' .` 无输出；
  另外对 CATALOG 中每条 `hf_repo` 字符串做**全仓** grep（排除 `desk/resources/catalog.py` 与 `docs/`），
  必须无输出——R-01 说的是「仓库内」，不只 sh/py：这条封死 JS/HTML/Swift 里残留第二份 repo/路径清单的口子
  （「前端经 HTTP 取目录，JS 里不复制」由此获得可执行的检查点，而非口头承诺）。
- census 复核（A20/A21）：`grep -rn 'model_present' .` 无输出；旧 `initModels.sh:63`（见任一
  `.safetensors` 即算齐）与 `server.py:201`（`path.exists()` 即算有）两个判定点随文件删除一并消失，
  全仓不得再有任何「按文件存在性判 present」的路径——present 只能出自 `verify_tree` 的逐文件字节比对。

### manifest（R-02）
- 假 fetcher 返回文件清单 → 缓存文件落盘（原子写）、source=fresh。
- fetcher 抛异常 + 有缓存 → source=cached、fetched_at 保留原值。
- fetcher 抛异常 + 无缓存 → ManifestUnavailableError；verifyModel 得 state=unknown + reason。
- 缓存 JSON 损坏 → 视同无缓存（重新 fetch 或 unavailable），不崩。

### verify（R-02/03/04）
- tmp_path 造三种树（假清单 3 个文件）：
  全齐 → present、percent==100、gaps 空；
  一半（1 个缺失 + 1 个短缺）→ partial、percent 按**字节**精确断言、gaps 列出两条含 expected/local；
  空 → missing、percent==0。
- 本地多余杂物文件：不改变 state/percent，但计入 disk_bytes。
- diskUsage：per_model 与手工求和一致；free_bytes/total_bytes > 0。

### downloader（R-05/06/07/09）
- FakeExecutor（记录 cmd、可控退出）+ FakeClock：
  - start → state=running、cmd 形如 `[*hf_cmd, download, <repo>, --local-dir, <models_root/relpath>]`（hf_cmd 为注入的假前缀，逐元素断言）。
  - 运行中再 start（同 key 或异 key）→ download_in_progress。
  - 注入 can_start_heavy=「媒体在跑」 → media_busy，带 arbiter 原因；「仅 LLM 驻留」→ 允许。
  - 采样：往目的树写一半字节 → progress.bytes_done 精确、percent、rate、eta 可算；
    `.cache/huggingface/download/x.incomplete` 字节计入且截顶。
  - cancel → handle 收到 terminate；FakeClock 拨过 8 秒且 handle 仍未退出 → 收到 kill；
    半成品文件原样存在、state=cancelled。
  - cancel 后、旧 handle 尚未退出时 start → download_in_progress（锁未释放，防并发写同一目录）；
    handle 退出后 start → FakeExecutor 被第二次调用、目的目录未被清空（续传前提成立）。
  - 并发读：采样更新进行中调用 progress() → 返回自洽快照（bytes_done/percent/state 同一帧）。
  - 退出 rc=0 → finished + finished 事件载荷含终验状态；rc=1 → failed + error 含 rc。
  - executor 抛 FileNotFoundError → hf_cli_missing，锁已释放（可再 start）。
- 事件：progress 回调抛异常不影响下载收尾。

### delete（R-08）
- 无 confirm / confirm 错 → confirm_required，目录原样。
- confirm==key → 目录删除、freed_bytes==删前大小；二次删除幂等 freed=0。
- 路径逃逸：把 entry.relpath 目录做成指向 tmp_path 外的符号链接 → path_escape、链接目标完好。
- 下载中删除同 key → download_in_progress。
- （防御测试用非法 relpath 构造的 ModelEntry 直接喂 service 内部函数，断言 `..` 被拒。）

### reality gate（人工 runbook，不入自动验收）
- 对真实 339G 树跑一次 `verifyAllModels`：8 项应全 present（或如实 partial），
  bytes_local 与 `du` 量级吻合，卷剩余空间与 `df -h` 一致。慢（要 stat 全树），标 `reality_gate:true`。
- 真实断点续传（**必做一次**，发布前）：R-05 的「已完整的文件不得重下」由 hf CLI 原生行为承担，
  FakeExecutor 测不到它，所以必须有一个真实验证点：选一个 <1G 的小 HF repo，把执行器的
  `--local-dir` 指向临时目录（不进 models_root，事后手工删除临时目录本身），下载中途 cancel，
  再 start，观察 hf 输出确认已完整文件被跳过、`.incomplete` 半成品被续传而非从零重下。

---

## Assumptions（模块内部决定，不改变边界）

1. **key 采用短 id**（h3/music3/glm/superqwen/qwen27/gemma/qwen35/llama70，来自 initModels.sh），
   `name` 保留 server.py 的中文展示名。旧长 key 不保留别名——这是全量重构，无兼容层（冻结约定：不做兼容行为）。
2. **group 词汇取 spec 的 chat|video|music**，不沿用 initModels 的 llm/h3/music3。
3. **清单来源**为 HF `GET /api/models/{repo}/tree/main?recursive=true`（跟随分页），
   取 main 分支即时状态；只比对路径+字节数，不做哈希。
4. **manifest 缓存目录** `<data root>/manifests/<key>.json`；目录名不在 foundation 的显式清单里，
   属 data root 下本模块私有子目录（foundation 只约定 data root 本身）。
5. **进度不解析 hf stdout**，以目录采样为准；`current_file`/`rate`/`eta` 标注最佳努力。
6. **下载状态不持久化**：服务重启后靠磁盘上的半成品 + verify 恢复语义，续传由 hf 原生完成。
7. **deleteModel 的确认参数**定义为「confirm 必须等于目标 key」，比布尔 true 更难误传。
8. **`can_start_heavy` 的判定（Phase 1.2 已与 arbiter 对齐）**：仅当媒体作业进行中/驱逐过渡期
   拒绝下载；LLM 驻留不阻塞（spec R-09 只提「媒体生成」）。装配为
   `can_start_heavy = lambda: arbiter.can_start_heavy("video")`——arbiter 转移表对媒体类 kind
   的回答恰是所需语义：media_held → `{ok: false, reason: {code: "media_busy", ...}}`、
   驱逐过渡 → `transition_in_progress`、llm_held → evict_then_grant 计 ok:true（LLM 驻留
   不误拦下载）。resources 只在 `ok == false` 时拒绝，`reason.code`（`media_busy` /
   `transition_in_progress`）原样透传进错误 message（reason 是 {code, message} 对象，
   非裸字符串）。
9. **HTTP 路径前缀 `/api/resources/`** 与「组合根统一挂载各模块路由」是本模块对应用装配的假定；
   端点形状已在本文固化，供 ui 模块对齐。
10. 事件为进程内观察者回调，无跨进程推送（当前无消费方需要）。
