# 模块设计：arbiter

**日期** 2026-08-31
**对应 spec** `2026-08-31-arbiter-spec.md`
**覆盖需求** R-arbiter-01 … R-arbiter-07

---

## 架构

arbiter 是一个纯进程内 Python 包，位于 `/Users/aa/LocalModelDesk/desk/arbiter/`。
它不开 HTTP 端口、不 import 任何兄弟模块；对外只暴露一个 `Arbiter` 门面对象与若干数据形状。
HTTP 路由的挂载（`data:deskState` / `api:memorySnapshot` 给 UI 用）由台面服务的组装层完成——
arbiter 的方法全部是「入参基本类型、出参可 JSON 化 dict」，挂路由是一行转发。

设计原则（来自 spec 与冻结决定）：

1. **互斥独立可证明**。状态机是纯函数（无 I/O、无锁），并发与副作用集中在一个门面里，
   使 R-arbiter-01 的竞态用例可以在毫秒级单元测试里跑完。
2. **副作用可注入**。真实内存读数（子进程调 `sysctl`/`vm_stat`）与按端口收割（`lsof` + `os.kill`）
   各自封装成可替换对象；门面的单元测试注入假实现，真实实现另有针对性的真子进程测试。
3. **驱逐 LLM 不回调 llm 模块**。媒体 acquire 触发的「先卸 LLM」由 arbiter 自己按端口收割完成
   （这正是 `api:reapLlmPort` 的能力），随后广播 `event:heavyStateChanged`；
   llm 模块（它消费 `data:deskState` 与该事件）观察到持有权丢失后清掉自己的子进程句柄。
   这样互斥保证不依赖 llm 模块行为正确，堵住 A06/A07 的孤儿进程漏洞的同时保持本模块独立可证。
4. **令牌化持有权**。`api:acquireHeavy` 返回一次性 token，`api:releaseHeavy` 凭 token 释放。
   杜绝「llm 被 arbiter 驱逐后，llm 迟到的 release 误清掉 media 持有权」这一竞态。

### 包内文件

```
desk/arbiter/
  __init__.py     # 导出 Arbiter、MemoryReader、reap_port、各 dataclass/常量
  state.py        # 纯状态机：transition 计划函数，零 I/O
  memory.py       # MemoryReader：sysctl/vm_stat 读数与解析（R-arbiter-02）
  reaper.py       # reap_port：按端口收割，先 TERM 后 KILL（R-arbiter-03）
  core.py         # Arbiter 门面：锁、令牌、事件、驱逐编排（R-arbiter-01/04/05/06/07）
```

### 并发模型（两把锁）

- `_transition_lock`（`threading.Lock`）：串行化 acquire / release / reap 全过程，
  **包括驱逐期间的子进程调用**。这保证并发 acquire 只有一个成功（R-arbiter-01）。
- `_state_lock`（`threading.Lock`）：只保护状态 dict 的读写，**绝不跨子进程调用持有**。
  `api:currentHolder` / `data:deskState` 读取只取这把锁，因此驱逐进行中（可能耗时数秒）
  状态查询依然即时返回，且如实显示过渡态 `phase: "acquiring"`。

- **`transition_in_progress` 快速拒绝路径**：`acquire_heavy` / `can_start_heavy` 在竞争
  `_transition_lock` **之前**先在 `_state_lock` 下读一次状态，见 `phase == "acquiring"`
  即立即返回 `transition_in_progress`，不去排 `_transition_lock` 的队。没有这条路径，
  驱逐期间（子进程收割可长达 term_timeout+kill_timeout ≈ 8 秒）新请求会阻塞在锁上，
  与「不排队、立即拒绝」（Assumption 5）矛盾。过渡态置位前的极窄窗口内已阻塞在
  `_transition_lock` 上的请求，拿到锁后按当刻状态重新判定（得 `media_busy` 等），
  互斥不受影响。

事件回调**缓冲派发**：一次 acquire / release / 驱逐过程中产生的事件（如驱逐的
[acquiring, held] 序列）先记入本次调用的本地队列，待 `_transition_lock` 与
`_state_lock` 都释放后，在调用线程上按序同步派发。过渡态的实时对外可见性由
`_state_lock` 下的 deskState 读取保证，不依赖事件时点；派发时不持任何锁——
`threading.Lock` 不可重入，锁内派发会让「订阅者回调再进 arbiter」直接死锁。

---

## 组件

### 1. `state.py` — 纯状态机

spec 的状态机逐条翻译成一个纯函数：

```python
Kind = Literal["llm", "video", "music"]          # video/music 归并为 media 态
MEDIA_KINDS = ("video", "music")

@dataclass(frozen=True)
class Holder:
    kind: Kind
    label: str          # 模型 key 或作业 id，由申请方提供
    token: str          # uuid4 hex
    since: float        # epoch 秒
    phase: str          # "held" | "acquiring"（驱逐进行中的过渡态）

@dataclass(frozen=True)
class Decision:
    action: Literal["grant", "evict_then_grant", "refuse"]
    reason_code: str | None      # refuse 时必填
    reason_message: str | None

def plan_acquire(holder: Holder | None, kind: Kind) -> Decision: ...
```

转移表（`plan_acquire` 的全部输出，超出即 `refuse`）：

| 当前 | 申请 | 决定 | reason_code |
|---|---|---|---|
| idle | llm | grant | — |
| idle | video/music | grant | — |
| llm_held | video/music | **evict_then_grant** | — |
| llm_held | llm | refuse | `llm_already_held`（护栏：llm 换模型**不**再 acquire——已持许可跨越换模型，见 llm 设计 Assumption 4；此拒绝只拦异常调用） |
| media_held | 任何 | refuse | `media_busy` |
| phase=acquiring | 任何 | refuse | `transition_in_progress` |
| 非法 kind | — | refuse | `unknown_kind` |

`media_busy` 的拒绝同时覆盖 R-arbiter-04 的两个半句：媒体作业中拒加载 LLM、拒第二个媒体作业。

### 2. `memory.py` — 真实内存（R-arbiter-02）

```python
@dataclass(frozen=True)
class MemorySnapshot:        # data:memorySnapshot 的 Python 形状
    total_bytes: int
    used_bytes: int
    available_bytes: int
    pressure: str            # "normal" | "warn" | "critical" | "unknown"
    page_size: int
    captured_at: float

class MemoryReader:
    def __init__(self, run=subprocess.run): ...   # 可注入命令执行器
    def snapshot(self) -> MemorySnapshot: ...
```

取数方式（全部实测存在于目标机器，见验证记录）：

- `total_bytes` ← `sysctl -n hw.memsize`（本机返回 137438953472，与验收基准同源）。
- `vm_stat` 输出解析出 `page_size` 与各页计数；
  `available_bytes = (free + inactive + purgeable + speculative) × page_size`；
  `used_bytes = total_bytes - available_bytes`。
- `pressure` ← `sysctl -n kern.memorystatus_vm_pressure_level`，
  映射 `1→normal`、`2→warn`、`4→critical`；读不到或值不在表内 → `"unknown"`
  （压力是附加信息，不因它让整个快照失败；总量/可用读不到则**抛 `MemoryProbeError`**，错误就是错误）。

解析函数 `parse_vm_stat(text) -> (page_size, {counter: pages})` 是纯函数，独立测试。
代码中**不出现任何内存常量**；census A09 的 `"ram_gb": 128` 由此消灭。

### 3. `reaper.py` — 按端口收割（R-arbiter-03）

```python
@dataclass(frozen=True)
class ReapResult:
    ok: bool
    port: int
    killed_pids: list[int]
    error: str | None        # 失败时如 "pids [123] still listening after SIGKILL"

def reap_port(port: int, *, term_timeout=5.0, kill_timeout=3.0) -> ReapResult: ...
```

流程（吸收 `unload-llm.sh` 的按端口语义，census A06/A07 合并为此单点）：

1. `lsof -tiTCP:<port> -sTCP:LISTEN` 找出**所有**监听该端口的 PID（含孤儿）；排除 `os.getpid()` 自保。
2. 无 PID → 立即 `ok=True, killed_pids=[]`（端口本来就空也是成功）。
3. 对每个 PID `os.kill(pid, SIGTERM)`；以 0.1s 步长轮询 lsof，至多 `term_timeout` 秒。
4. 仍监听者 `os.kill(pid, SIGKILL)`；再轮询至多 `kill_timeout` 秒。
5. **最终以 lsof 复查为准**：端口仍有监听 → `ok=False` 并列出顽固 PID。
   不以「发出了 kill」冒充成功——收割后必须确认端口确已释放才算成功。

`ESRCH`（进程已死）按成功处理；`EPERM` 记入 error 并最终按第 5 步复查判定。

### 4. `core.py` — `Arbiter` 门面

```python
class Arbiter:
    def __init__(self, llm_port: int, *,
                 memory: MemoryReader | None = None,
                 reaper: Callable[[int], ReapResult] = reap_port,
                 clock: Callable[[], float] = time.time,
                 logger: logging.Logger | None = None): ...

    # ---- 注册表接口 ----
    def memory_snapshot(self) -> dict: ...                    # api:memorySnapshot
    def acquire_heavy(self, kind: str, label: str) -> dict:   # api:acquireHeavy
    def release_heavy(self, token: str) -> dict: ...          # api:releaseHeavy
    def current_holder(self) -> dict | None: ...              # api:currentHolder
    def reap_llm_port(self, port: int) -> dict: ...           # api:reapLlmPort（按传入端口收割；
                                                              #   Phase 1.2 与 llm 对齐：带端口参数，
                                                              #   llm 是调用方并持有 8767 常量）
    def can_start_heavy(self, kind: str,
                        estimated_bytes: int | None = None) -> dict:  # api:canStartHeavy
    def desk_state(self) -> dict: ...                         # data:deskState
    def subscribe(self, cb: Callable[[dict], None]) -> Callable[[], None]:  # event:heavyStateChanged
```

`llm_port` 不在包内写死默认值：8767 的仓库唯一定义点在 `desk/llm`（`DEFAULT_LLM_PORT`，
llm 设计 Assumption 2；foundation 的 `data:deskConfig` 不含此值），组装层把同一常量传入，
供**驱逐**时收割（流 2 的 `reaper(llm_port)`）。`api:reapLlmPort` 本身按入参端口收割，
不读 `self.llm_port`——llm 的调用点与 arbiter 的驱逐用的是同一个装配常量。
测试传临时端口，**绝不**对 8767 做收割测试，避免误杀真机进程。

### 对外数据形状（与兄弟模块的合同）

**`data:deskState`**（R-arbiter-06；状态条、菜单栏、gateway 503 判定的唯一来源）：

```json
{
  "holder": {
    "kind": "llm", "label": "qwen3-30b",
    "since": 1756600000.0, "phase": "held"
  },
  "media_busy": false,
  "can_start": {
    "llm":   { "ok": false, "reason": { "code": "llm_already_held", "message": "…" } },
    "media": { "ok": true,  "reason": null }
  }
}
```

- `holder` 空闲时为 `null`；token 不出现在 deskState 里（只回给 acquire 调用方）。
- `media_busy = holder.kind ∈ {video, music}`。
- `can_start` 固定两个键：`llm` 与 `media`（video/music 在状态机里同态，合并回答）。
- deskState **不内嵌内存数字**——「内存里是谁」由 `holder` 回答；
  实时内存数字走 `api:memorySnapshot`（UI 的状态条两者都消费，避免每次状态读取都开子进程）。

**`data:memorySnapshot`**：`MemorySnapshot` 的 `asdict`，字段见上文。

**`api:acquireHeavy` 返回**：

```json
{ "ok": true, "token": "9f2c…", "state": { …deskState… } }
{ "ok": false, "reason": { "code": "media_busy", "message": "音乐作业进行中" } }
{ "ok": false, "reason": { "code": "evict_failed",
                           "message": "pids [4242] still listening after SIGKILL" } }
```

**`api:releaseHeavy(token)` 返回**：`{"ok": true}`；token 不匹配当前持有者 →
`{"ok": false, "reason": {"code": "not_holder", "message": "…"}}`（无副作用，幂等安全）。

**`api:canStartHeavy(kind, estimated_bytes=None)` 返回**（R-arbiter-04 + R-arbiter-07）：

```json
{ "ok": true, "reason": null,
  "memory_warning": { "code": "insufficient_memory",
                      "required_bytes": 74000000000,
                      "available_bytes": 52000000000,
                      "message": "该模型约需 74.0 GB，当前可用 52.0 GB" } }
```

- 只读预检，不改状态。`ok/reason` 来自 `plan_acquire` 同一张转移表（与 acquire 判定必然一致）。
- 传入 `estimated_bytes`（调用方从 `data:modelEntry` 的体积换算）时比对当前 `available_bytes`；
  装不下**不置 `ok=false`**，而是附 `memory_warning`——按 spec 这是加载前警告（UI R-ui-08 弹确认框），
  不是拒绝。不传体积则 `memory_warning` 恒为 `null`。

**`event:heavyStateChanged`**：进程内订阅。每次持有权变化（grant / release / 驱逐开始 / 驱逐失败回滚）
派发一次，载荷即当刻 `data:deskState`。订阅者回调异常被捕获并记日志，不影响其余订阅者与 arbiter 状态。
HTTP/SSE 推送不是本模块职责；ui/shell 若需推送由组装层桥接。

---

## 数据流

### 流 1：llm 加载（llm 模块视角）

```
llm.loadLlm(key)
  ├─ arbiter.acquire_heavy("llm", key)           # 同步段：idle→llm_held，拿 token（拒绝立即返回）
  ├─ [工作线程] arbiter.reap_llm_port(8767)      # spawn 前清孤儿（端口常量由 llm 持有）
  ├─ 启动 mlx-lm、轮询健康；每拍核对 deskState 持有权（被驱逐即中止，见 llm 设计「让位协作」）
  └─ 失败时 arbiter.release_heavy(token)；卸载顺序 terminate → reap_llm_port(8767)
     确认端口释放 → release_heavy(token)（R-llm-02）
（llm 不调 can_start_heavy——加载前内存警告由 ui 以 api:memorySnapshot 判定，acquire 为准；
  estimated_bytes 形参保留给任何想预检的调用方）
```

### 流 2：媒体作业启动，自动让出内存（R-arbiter-05）

```
media.startVideoJob()
  └─ arbiter.acquire_heavy("video", job_id)
       [持 _transition_lock 全程串行]
       1. plan_acquire(llm_held, video) → evict_then_grant
       2. _state_lock 下置过渡态 holder{kind:video, phase:"acquiring"}，
          记 acquiring 事件入缓冲
          （期间任何 acquire/canStart 走快速拒绝路径 → "transition_in_progress"，
            不排 _transition_lock 的队；deskState 读取不被阻塞，如实显示过渡态）
       3. reaper(llm_port)  ← 锁外无、_transition_lock 内执行，先 TERM 后 KILL
       4a. ReapResult.ok → holder 置 {kind:video, phase:"held", token 新发}，
           记事件入缓冲；返回 {ok:true, token} 前两锁全释放、缓冲事件按序派发
           （llm 模块从事件/deskState 看到持有权丢失，清掉自己的 Popen 句柄）
       4b. ReapResult.ok=False → 恢复原 llm holder（原 token 仍有效），记事件入缓冲
           （锁释放后派发）；返回 {ok:false, reason:{code:"evict_failed", message:<reaper.error>}}
           —— 让出失败即启动失败，绝不带着 LLM 硬上
```

### 流 3：并发竞争（R-arbiter-01）

多线程同时 `acquire_heavy`：全部排队在 `_transition_lock`；第一个按转移表拿到 grant，
其余进入后重读状态得到 `refuse`。任何时刻至多一个 holder；`release_heavy` 凭 token，
迟到的释放打不掉新持有者。

### 流 4：状态消费

- ui 状态条 / shell 菜单栏：轮询 `data:deskState` + `api:memorySnapshot`。
- gateway：读 `data:deskState`（`media_busy` 或无模型 → 503）。
- llm / media：acquire 前用 `api:canStartHeavy` 预检给出友好拒绝，acquire 为准。

---

## 错误处理

| 场景 | 行为 | 机器可读码 |
|---|---|---|
| 媒体作业中 acquire 任何重活 | 拒绝，状态不变 | `media_busy` |
| 已载 LLM 时再 acquire llm | 拒绝（先 release 再来） | `llm_already_held` |
| 驱逐进行中任何 acquire/canStart | 拒绝 | `transition_in_progress` |
| 非法 kind | 拒绝 | `unknown_kind` |
| 驱逐收割后端口仍被监听 | acquire 失败，回滚为 llm_held | `evict_failed`（附 reaper error） |
| release 的 token 非当前持有者 | 无副作用返回失败 | `not_holder` |
| 模型体积 > 可用内存 | `ok` 仍真，附警告（加载前，UI 弹确认） | `insufficient_memory` |
| `sysctl hw.memsize`/`vm_stat` 失败 | 抛 `MemoryProbeError`，由组装层映射为 5xx | — |
| 压力 sysctl 读不到 | `pressure:"unknown"`，快照其余字段照常 | — |
| 订阅者回调抛异常 | 捕获记日志，不传播 | — |

不存在任何回退假数据路径：收割未确认端口释放不算成功，内存读不到不编数字。

---

## 测试

全部落在 `/Users/aa/LocalModelDesk/tests/`，`pytest` 快速确定性，无 reality gate，
不触碰 8767、不触碰真实权重。

### `tests/test_arbiter_state.py`（纯状态机）
- 转移表逐格断言：上表 7 行每行一个用例，含 refuse 的 reason_code。

### `tests/test_arbiter_core.py`（门面；注入假 memory / 假 reaper / 假 clock）
- **竞态（R-arbiter-01）**：16 线程 barrier 同步同时 `acquire_heavy("llm")`，断言恰好 1 个 `ok`，
  其余 reason_code ∈ {`llm_already_held`}；再以 video/music 混合竞争重复一轮。
- 驱逐成功：llm_held 下 acquire video，假 reaper 返回 ok → holder 变 video、旧 llm token release
  得 `not_holder`、事件序列 = [acquiring, held]。
- 驱逐失败（R-arbiter-05）：假 reaper 返回 ok=False → 返回 `evict_failed`、holder 仍为原 llm
  且原 token 仍可 release。
- 假 reaper 断言：refuse 路径下 reaper **从未被调用**。
- **驱逐中的快速拒绝**：假 reaper 阻塞在 `threading.Event` 上模拟慢收割；另一线程在
  驱逐进行中 acquire / can_start → **立即**（不等收割完成）返回 `transition_in_progress`；
  放行 Event 后原驱逐正常收尾，事件序列不乱。
- `can_start_heavy`：各状态与 acquire 判定一致；`estimated_bytes` 大于假快照可用值 → 附
  `insufficient_memory` 警告且 `ok=true`；小于 → 无警告（R-arbiter-04/07）。
- deskState 形状：holder/media_busy/can_start 三键齐全、无 token 泄漏。
- 事件：订阅/退订、异常订阅者不影响后续派发（R-arbiter-06 载荷断言）。

### `tests/test_arbiter_reaper.py`（真子进程，临时端口）
- 起 `python -c` 子进程绑定 OS 分配的临时端口并 `listen`+sleep：`reap_port` 后断言
  lsof 无监听、子进程已死、`killed_pids` 含其 PID（R-arbiter-03，覆盖孤儿场景——该子进程不是被测代码 spawn 的“自家” LLM）。
- 端口本就无监听 → `ok=True, killed_pids=[]`。
- 子进程安装 SIGTERM 忽略处理器 → 走 KILL 路径仍成功（term_timeout 调小保持测试快）。

### `tests/test_arbiter_memory.py`
- `parse_vm_stat`：喂本机实录的 canned 文本，断言 page_size=16384 与各计数（纯函数，任何平台可跑）。
- 注入假 run 的 `MemoryReader`：used+available == total、pressure 映射 1/2/4/其他 四例。
- **防写死断言（A09）**：给假 run 的 `hw.memsize` 喂非常规值（如 `271_437_611_008`），
  断言 `total_bytes` 恰等于注入值；换第二个注入值重跑，结果随之变化——总量确实来自
  探测输出，任何写死常量（128GB 之流）都会让此用例失败。
- `@pytest.mark.skipif(sys.platform != "darwin")` 真机用例：`snapshot()` 各字段存在且为正，
  `total_bytes == int(subprocess sysctl -n hw.memsize)`（spec 验收原文）。

### 需求覆盖矩阵

| 需求 | 测试 |
|---|---|
| R-arbiter-01 | test_arbiter_core 竞态 + test_arbiter_state |
| R-arbiter-02 | test_arbiter_memory 全部 |
| R-arbiter-03 | test_arbiter_reaper 全部 |
| R-arbiter-04 | state 转移表 refuse 行 + core can_start/acquire 拒绝码 |
| R-arbiter-05 | core 驱逐成功/失败/回滚 |
| R-arbiter-06 | core deskState 形状 + 事件载荷 |
| R-arbiter-07 | core memory_warning 两例 |

---

## Assumptions（模块内部裁量，未动边界）

1. **`llm_port` 经构造注入**，包内无 8767 字面量：组装层传入 `desk.llm.DEFAULT_LLM_PORT`
   （8767 的仓库唯一定义点在 llm，Phase 1.2 对齐；`api:reapLlmPort(port)` 按入参收割，
   `llm_port` 仅供驱逐使用。arbiter 的日志落点 `logs/desk.log` 由组装层用
   foundation 路径配置 `logging` handler，arbiter 只持有一个 `logging.Logger`，自身零路径拼接）。
2. **驱逐 = arbiter 自行按端口收割**，不回调 llm 模块。依据：llm spec 已声明消费
   `data:deskState`（可观察持有权丢失），且互斥模块必须独立可证明；未新增任何注册表外接口。
3. **video/music 在 `can_start` 中合并为 `media` 键**：二者在 spec 状态机同态；
   `acquireHeavy` 仍收全三种 kind，deskState.holder.kind 保留具体值供 UI 显示「出片中/出歌中」。
4. **`available_bytes` 采用 free+inactive+purgeable+speculative 页合计**（macOS 常用近似）；
   验收锚点是总量与 `sysctl hw.memsize` 一致，可用值只要求为正且参与警告比较。
5. **驱逐期间新请求一律 `transition_in_progress` 拒绝**而非排队：spec 明言不排队的哲学
  （gateway R-gateway-08 同源），且过渡窗口以秒计，调用方重试即可。
6. **token 为 uuid4 hex**，仅在 acquire 返回值中出现；deskState 不含 token，防止旁路 release。
7. **`api:currentHolder` 无兄弟模块运行期消费者（Phase 1.2 裁定）**：持有权信息一律经
   `data:deskState.holder` 到达 ui / shell / gateway；`current_holder()` 是同一 `_state_lock`
   读路径上的进程内诊断访问器，由本模块验收测试与操作者排障使用。注册表词汇冻结，保留不删，
   不给它另开 HTTP 路由。
8. 反映当前实现的 `HEAVY_LLM_GB` 阈值建议不再保留——警告改为逐模型体积对真实可用内存比较
   （R-arbiter-07 的原意），不设「重模型」布尔标签。
