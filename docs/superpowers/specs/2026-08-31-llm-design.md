# 模块设计：llm

**日期** 2026-08-31
**spec** `docs/superpowers/specs/2026-08-31-llm-spec.md`
**覆盖需求** R-llm-01 ～ R-llm-07

## 架构

### 定位

`llm` 是聊天模型的生命周期管理者与唯一对话通路。它把现状里散落的三块东西收成一处：

1. `server.py:_load_llm / _unload_llms / _llm_alive`（生命周期，只杀自己 spawn 的子进程——漏洞归 `arbiter` 堵）；
2. `server.py:_chat / _proxy_chat_sse`（对话代理，其中流式代理现在是死代码）；
3. 浏览器直连 `127.0.0.1:8767` 的旁路（census A17——本模块之后彻底封死）。

互斥判断**完全不做**：许可一律向 `arbiter` 申请（`api:acquireHeavy` / `api:releaseHeavy`），
端口收割一律走 `api:reapLlmPort`。目录与元数据一律取自 `resources`（`api:listCatalog` / `data:modelEntry`），
路径一律取自 `foundation`（`api:resolvePaths`）。本模块内不出现第二份模型清单、不出现 `Path.home()` 拼接。

### 分层

```
                    ┌────────────────────────────────┐
  ui (HTTP/SSE) ──> │ routes.py     瘦 HTTP 适配层    │
                    ├────────────────────────────────┤
  gateway (进程内) ─> │ service.py    LlmService        │ <── 状态机 + 编排
                    ├────────────────────────────────┤
                    │ backend.py    LlmBackend 协议    │ <── 唯一可替换点（测试注入假后端）
                    │   └ MlxLmBackend  真实实现       │
                    └───────────┬────────────────────┘
                                │ subprocess + HTTP
                          mlx-lm server (127.0.0.1:8767，实现细节，不外露)
```

- **`gateway` 走进程内 Python 调用**（`api:chatStream` / `api:chatCompletion` / `api:llmStatus` /
  `data:loadedModel`），不经 HTTP，避免本机自转发。
- **`ui` 走 `routes.py` 暴露的台面 HTTP 接口**（127.0.0.1:8766 下的 `/api/llm/*`），
  前端永远拿不到 8767 这个数字（R-llm-07）。

### 文件布局

```
desk/llm/
  __init__.py     # 导出 LlmService、LlmBackend、错误码常量
  state.py        # LlmState / LoadedModel / ChatEvent 数据形状；错误码枚举
  backend.py      # LlmBackend Protocol + MlxLmBackend（subprocess + http.client）
  service.py      # LlmService：load / unload / status / chat_stream / chat_completion
  routes.py       # 台面 HTTP 路由表（由服务组装层注册进 8766 的 server）
tests/
  test_llm_service.py    # 状态机 + 加载/卸载 + 拒绝路径（假后端 + 假 arbiter）
  test_llm_chat.py       # 流式/非流式对话、reasoning 分离、拒绝路径
  test_llm_routes.py     # HTTP 层状态码与 SSE 帧格式
  fakes.py (或 conftest) # FakeBackend / FakeArbiter / FakeCatalog 共用夹具
```

## 组件

### 1. `state.py` — 数据形状（`data:llmState`、`data:loadedModel`）

```python
# data:llmState —— llmStatus 返回的对象，也是 ui 聊天面板与 gateway 503 判断的依据
{
  "status": "idle" | "loading" | "loaded" | "error",   # R-llm-01 四态
  "model_key": str | None,        # 正在加载/已加载/上次失败的目录 key
  "error": {                      # 仅 status=="error" 时非空
      "code": str,                # 机器可读，见错误码表
      "message": str,             # 人读一句话
      "log_tail": str | None      # mlx-lm.log 尾部（R-llm-04），加载类错误必带
  } | None,
  "loaded_at": float | None       # epoch 秒，仅 loaded
}

# data:loadedModel —— 仅 status=="loaded" 时非 None（R-llm-05）
# 除 served_id 外字段直接来自 resources 的 data:modelEntry，本模块零拷贝转发、不自造元数据
{
  "key": str, "name": str, "hf_repo": str,
  "served_id": str,   # mlx-lm 侧模型标识（= hf_repo）；gateway guard 与 /v1/models 消费（R-gateway-10）
  "vision": bool, "quant": str, "params": str, "gb": float
}

# ChatEvent —— api:chatStream 逐项产出的内部事件（进程内消费者：gateway、routes.py）
{ "type": "delta", "text": str | None, "reasoning": str | None }   # 二者至少一个非空，永不合并
{ "type": "done",  "usage": dict, "finish_reason": str }   # 成功终止必带二者（合同见下）
{ "type": "error", "code": str, "message": str }
```

`usage` / `finish_reason` 原样透传上游（mlx-lm 的 OpenAI 形状），**不估算、不伪造**。
与 gateway 的冻结合同（其 Assumptions #11，Phase 1.2 已对齐）：**成功终止的 `done` 事件必带
`finish_reason` 与 `usage`**（mlx-lm 原生给出；gateway 的 Anthropic `message_delta` 硬性需要）。
上游流终止却缺任一字段 → 这不是可省字段而是上游故障：产出 `error/upstream_error` 事件而非 `done`
（非流式同理：缺失即 502 `upstream_error`），绝不补造数值（冻结约定：错误就是错误）。

### 2. `backend.py` — 可替换后端（验收取向的落点）

```python
class BackendProcess(Protocol):
    def poll(self) -> int | None: ...      # None=活着；否则退出码
    def terminate(self) -> None: ...
    def kill(self) -> None: ...
    def wait(self, timeout: float) -> None: ...

class LlmBackend(Protocol):
    def spawn(self, python: Path, model_path: Path, port: int, log_path: Path) -> BackendProcess: ...
    def health(self, port: int) -> bool: ...                       # GET /v1/models，1s 超时
    def chat(self, port: int, payload: dict) -> dict: ...          # 非流式，返回上游 JSON
    def chat_stream(self, port: int, payload: dict) -> Iterator[dict]: ...
        # 逐个产出上游 SSE 解出的 chunk 对象（choices[0].delta ...），由 service 转 ChatEvent
    def log_tail(self, log_path: Path, max_lines: int = 40) -> str: ...
```

`MlxLmBackend`（真实实现）：

- `spawn`：`[python, "-s", "-m", "mlx_lm", "server", "--model", model_path, "--host", "127.0.0.1",
  "--port", port]`（`-s` 遵循 packaging §1.3 运行期契约：禁用用户 site-packages；bundle 态
  PYTHONPATH 自 desk 服务进程原样继承，已含 `pylibs/desk`），stdout/stderr 追加写入 `log_path`。**去掉现状的 `--allowed-origins *`**：
  浏览器不再直连，就不再需要放开 CORS（放开它反而重新打开 A17 旁路）。
- `python` 为内嵌 venv 的解释器，路径来自 `api:resolvePaths`（bundle 资源根），不硬编码。
- `chat` / `chat_stream`：标准库 `http.client` 直连 `127.0.0.1:<port>`，
  取代现状 shell 出去调 `curl` 的做法（少一个进程、少一处字符串拼接注入面）。
- `chat_stream` 解析 SSE：只认 `data:` 行，`[DONE]` 即停；解不出的 JSON 行跳过（上游噪声），
  但 HTTP 层错误（连接拒绝、非 200）必须抛出，由 service 转成 `error` 事件。

测试注入 `FakeBackend`，按 spec 验收取向模拟四种情形：
**启动即退出 / 一直不就绪 / 正常流式 / 返回 reasoning 增量**。

### 3. `service.py` — `LlmService`（模块核心）

构造注入（服务组装层完成，测试注入假件）：

```python
LlmService(
    backend: LlmBackend,
    arbiter,          # 提供 acquire_heavy / release_heavy / reap_llm_port / desk_state
    catalog,          # 提供 list_catalog() -> list[modelEntry]（resources）
    paths,            # 提供 resolve_paths() -> pathRoots（foundation）
    port: int = 8767, # mlx-lm 内部端口（冻结约定；见 Assumptions #2）
    load_timeout_s: float = 180.0,
    poll_interval_s: float = 0.4,   # 测试里可缩到毫秒级，保证快速确定性
)
```

内部状态：`_lock`（threading.Lock，护所有状态转移）、`_state: LlmState`、
`_proc: BackendProcess | None`、`_load_thread`。

#### `api:loadLlm(key) -> data:llmState`（R-llm-01、R-llm-04、R-llm-06）

异步语义：校验与许可**同步**完成（失败立即返回，绝不挂起），健康轮询在工作线程；
调用方（ui）拿到 `loading` 后轮询 `api:llmStatus`。

同步段（持锁串行）：

1. `status == "loading"` → 拒绝，`load_in_progress`（不排队）。
2. key 不在 `api:listCatalog` → 拒绝，`model_not_found`。
3. 模型本地目录（`pathRoots.models_root / entry.relpath`）不存在 → 拒绝，`model_dir_missing`。
4. 重活许可，按当前状态二分：
   - 当前已 `loaded`（换模型）：**跳过 acquire**——上次 load 的重活许可仍在手上，不重复申请
     （避免依赖 arbiter 对「持有者再 acquire」的未定义语义）。对旧进程做内部收尾
     （terminate + `reap_llm_port(port)` 确认释放），**不 `release_heavy()`**，许可原样带进
     新一轮加载；收尾报告端口仍被占 → `error/port_not_released` + `release_heavy()`，
     本次 load 就此失败（500 经 status 查得）。
   - 当前非 `loaded`：`arbiter.acquire_heavy("llm", key)`（label 传目录 key，供状态条/菜单栏
     显示；成功记下返回的一次性 token，后续 `release_heavy(token)` 凭它）→ 被拒（媒体持有中）
     则原样转发 arbiter 的机器可读原因，状态**不进 error**（这是拒绝，不是故障；`_state` 保持原样，
     拒绝作为返回值/HTTP 409 表达）。
5. 置 `loading`，起工作线程。

工作线程：

6. `arbiter.reap_llm_port(port)` —— **spawn 前先收割孤儿**（堵 census A06/A07 的洞：
   上一次服务遗留的 8767 监听进程必须先死，否则新进程绑不上端口、旧模型还占着内存）。
   收割后端口**仍被占** → 不 spawn，`error/port_not_released` + `release_heavy()`，结束
   （fail-fast，不让绑不上端口的 spawn 伪装成 `backend_exited`）。
7. `backend.spawn(...)`，日志写 `<data root>/logs/mlx-lm.log`（路径来自 foundation）。
8. 轮询直到 `load_timeout_s`（每拍先核对持有权，再查进程）：
   - `arbiter.desk_state()` 显示持有者已不是 llm（媒体作业驱逐发生在本线程 reap 之后、
     spawn 前后的窗口里）→ `kill()` 自己的子进程 + `reap_llm_port(port)` 清尾，
     `error/evicted`，**不 release**（许可已易主；迟到 release 也只会得 `not_holder`），结束。
     这把「驱逐与 spawn 交错」的互斥违例窗口压缩到一个轮询拍内。
   - `proc.poll() is not None` → `error/backend_exited`，`log_tail` 必附（R-llm-04）；
     `release_heavy()`；结束。
   - `backend.health(port)` 为真 → `loaded`，`loaded_at` 打点；结束。
9. 超时 → `kill()`，`reap_llm_port(port)` 清尾，`error/load_timeout` + `log_tail`（R-llm-04：
   超时也要带日志尾部，不得只报「加载超时」），`release_heavy()`。

#### `api:unloadLlm() -> data:llmState`（R-llm-02）

1. `idle` 时幂等返回。
2. `loading` 时拒绝：`load_in_progress`（409，不改状态、不打断工作线程）。加载不提供中途取消——
   要么很快成败、要么 `load_timeout_s` 到点自清（kill + reap + release），调用方等状态落定再卸。
   若 `loading` 窗口内被 arbiter 驱逐（媒体 acquire 触发按端口收割），工作线程下一拍
   即收敛：进程被收割则按 `backend_exited` 落定；驱逐与 spawn 交错（收割发生在 spawn 之前）
   则由每拍的持有权核对落定为 `error/evicted`（见工作线程第 8 步），不 release。
3. `terminate()` 自己的子进程（宽限 8s 后 `kill()`）。
4. `arbiter.reap_llm_port(port)` —— 按端口确认，**这是成功判据**：
   收割返回端口已释放才置 `idle` 并 `release_heavy()`；
   收割报告端口仍被占 → `error/port_not_released`（错误就是错误，不假装卸干净了）。

#### `api:llmStatus() -> {state: data:llmState, loaded_model: data:loadedModel | None}`（R-llm-05）

返回前做一次**存活自检**：`status=="loaded"` 但 `proc.poll()` 非 None（mlx-lm 自己崩了）→
就地转 `error/backend_exited` + `log_tail`，并 `release_heavy()`。这让「加载着却死了」的状态
不会静默停留，也是 arbiter 强制让位（媒体作业收割了端口）后本模块状态自愈的兜底
（另有主动通道，见「与 arbiter 的让位协作」）。

#### `api:chatStream(request) -> Iterator[ChatEvent]`、`api:chatCompletion(request) -> dict`（R-llm-03、R-llm-06、R-llm-07）

`request`：`{messages, temperature?, top_p?, max_tokens?, model?}`（model 缺省取当前加载项；
`temperature`/`top_p` 透传上游——gateway 的 ChatRequest 两者都可能带）。

前置检查（两个 API 相同，同步、立即，**绝不等待**——R-llm-06）：

1. `arbiter.desk_state()` 报媒体作业运行中 → 拒绝 `media_busy`。
2. `status != "loaded"` → 拒绝 `no_model_loaded`。
3. `request.model` 非空且既不等于当前 key、也不等于 `served_id` → 拒绝 `model_mismatch`
   （gateway R-gateway-10 依赖这条：不静默换模型）。

`chatCompletion`：`backend.chat()` 一发一收，返回
`{"content": str, "reasoning": str | None, "usage": dict, "finish_reason": str, "model": key}`
（`usage`/`finish_reason` 上游缺失即 502 `upstream_error`，见 state.py 合同——不返回残缺成功体）。
`content` 与 `reasoning` 分离，**取消现状的「正文为空就拿 thinking 顶上」回填**——
正文空就是空（gateway/ui 各自决定怎么呈现空回复，llm 不造数据）。

`chatStream`：包装 `backend.chat_stream()`，逐 chunk 转 ChatEvent：

- `delta.content` → `{"type":"delta","text":...}`；
- `delta.reasoning_content` 或 `delta.reasoning` → `{"type":"delta","reasoning":...}`；
  同一 chunk 两者都有则发一个双字段 delta；两个字段**永不互相搬运**（R-llm-03）；
- 末 chunk 带 `usage` / `finish_reason` 则记入 `done` 事件；
- 上游异常（连接断、非 200）→ 产出 `error` 事件后终止迭代，不吞、不补假 done。

对话是**无状态转发**：不写聊天历史（多会话持久化归 `library`，由 ui 调 `api:updateChatSession`），
不做重活许可操作（聊天不是「加载」，模型已驻留，无需再 acquire）。

### 4. `routes.py` — 台面 HTTP 适配（ui 消费面）

由服务组装层注册进 127.0.0.1:8766 的 desk server。只做「HTTP ↔ LlmService」翻译，零业务逻辑：

| 方法 | 路径 | 成功 | 拒绝/失败 |
|---|---|---|---|
| POST | `/api/llm/load`（body `{key}`） | `202 {state}`（进入 loading） | `409 {error:{code,message}}`（media_busy / load_in_progress）、`404`（model_not_found / model_dir_missing） |
| POST | `/api/llm/unload` | `200 {state}` | `409 {error:{code:"load_in_progress",...}}`（loading 中）、`500 {error:{code:"port_not_released",...}}` |
| GET | `/api/llm/status` | `200 {state, loaded_model}` | — |
| POST | `/api/llm/chat` | `200 {content, reasoning, usage, finish_reason, model}` | `409`（media_busy / model_mismatch）、`503 {error:{code:"no_model_loaded",...}}` |
| POST | `/api/llm/chat/stream` | `200 text/event-stream` | 同上（前置拒绝发生在发头之前，用普通 JSON 状态码） |

SSE 帧格式（ui 聊天面板消费）：每个 ChatEvent 一帧
`data: {"type":"delta","text":"...","reasoning":null}\n\n`，
`done` / `error` 同样以 `data:` JSON 帧发出，`done` 后关流。客户端断开（BrokenPipe）→
停止读上游流并关闭上游连接，服务端状态不受影响。

现状 `/api/llm/models` 不再由本模块提供——模型列表归 `resources`（`api:listCatalog`），
ui 直接消费那边，llm 只报「当前加载的是谁」。

### 与 arbiter 的让位协作（R-arbiter-05 的本模块侧）

依赖方向是 llm → arbiter，arbiter 不 import llm。驱逐机制以 arbiter 设计为准（其设计原则 3 /
Assumption 2：**驱逐 = arbiter 自行按端口收割，不回调 llm 模块**——互斥保证不依赖 llm 行为正确，
驱逐收割失败即媒体启动失败，由 arbiter 侧保证）。本模块的职责只是**观察并收敛**：

- 组装层把 `LlmService` 的收敛回调订阅到 `event:heavyStateChanged`（载荷即当刻 `data:deskState`）。
  回调发现「本模块自认 loaded，但 `deskState.holder` 已不是 llm」→ 走与存活自检相同的收敛路径：
  清子进程句柄（进程已被 arbiter 按端口收割）、置 `error/backend_exited` + `log_tail`、
  调用 `release_heavy(token)`——自崩场景需要真释放；被驱逐场景下旧令牌已失效，
  arbiter 凭令牌化拒绝这次迟到的 release，无副作用（这正是 arbiter 令牌化要堵的竞态）。
- 本模块因此消费 `event:heavyStateChanged` 与 `data:deskState`（后者 spec 已声明；前者为
  Phase 1.2 对齐补充声明的消费，词汇取自注册表，未新增任何接口或机制）。

兜底：即使订阅缺失，`llmStatus` 的存活自检也会把状态收敛到
`error/backend_exited`，不会出现「界面显示已加载、进程早没了」。

## 数据流

### 加载（成功路径）

```
ui POST /api/llm/load {key}
  → service.load(key)
      校验 key/目录（catalog+paths） ─ 失败即 404，无副作用
      已 loaded? 收尾旧进程、许可带走，不再 acquire
      否则 arbiter.acquire_heavy("llm", key) ─ 拒绝即 409；成功记 token，无其他副作用
      state=loading，返回 202
      [工作线程]
      arbiter.reap_llm_port(8767)   ← 先清孤儿；仍被占 → error/port_not_released，不 spawn
      backend.spawn(venv_python, models_root/relpath, 8767, logs/mlx-lm.log)
      循环: poll退出? → error+log_tail+release_heavy
            health通? → state=loaded
ui 轮询 GET /api/llm/status → loaded + loadedModel 元数据
```

### 流式对话

```
ui POST /api/llm/chat/stream {messages,...}          gateway 进程内调 chatStream(request)
  → service.chat_stream(request)
      desk_state 媒体在跑? → media_busy（立即，绝不排队）
      未加载?             → no_model_loaded
      backend.chat_stream(8767, payload)
        chunk.delta.content           → {"type":"delta","text":...}
        chunk.delta.reasoning_content → {"type":"delta","reasoning":...}   ← 分离，不混流
        [DONE]/usage                  → {"type":"done","usage":...}
  routes 把每个事件编成 SSE 帧          gateway 自行转 OpenAI/Anthropic 方言
```

### 卸载

```
unload() → terminate 子进程 → arbiter.reap_llm_port(8767)
             端口已释放 → release_heavy → idle
             端口仍被占 → error/port_not_released（不谎报成功）
```

## 错误处理

原则（冻结约定）：错误就是错误。没有回退输出、没有假成功、没有「正文空拿 reasoning 顶上」。

| 错误码 | 触发 | 状态机影响 | HTTP | log_tail |
|---|---|---|---|---|
| `model_not_found` | key 不在目录 | 无（拒绝非故障） | 404 | — |
| `model_dir_missing` | 目录项在、本地权重目录不在 | 无 | 404 | — |
| `media_busy` | arbiter 拒绝许可 / 聊天时媒体在跑 | 无 | 409 | — |
| `load_in_progress` | loading 中再来一次 load | 无 | 409 | — |
| `backend_exited` | mlx-lm 启动即退 / 中途崩 | → error | （经 status 查得） | 必附 |
| `load_timeout` | 超 180s 未就绪 | → error | 同上 | 必附 |
| `port_not_released` | 卸载 / 换模型收尾 / spawn 前收割后，端口仍被占 | → error | 500（unload 直接返回；load 路径经 status 查得） | — |
| `evicted` | 加载期间持有权被 arbiter 驱逐易主（媒体作业启动） | → error | （经 status 查得） | — |
| `no_model_loaded` | 未加载时来聊天 | 无 | 503 | — |
| `model_mismatch` | 请求 model 与驻留模型不符 | 无 | 409 | — |
| `upstream_error` | 对话中上游 HTTP/连接故障 | 无（模型可能仍活，交给下次自检） | 流内 error 事件 / 非流式 502 | — |

「拒绝」（前五行之外的 4xx 类）不改写 `_state`：一次被拒的加载请求不应把一个好端端的
`loaded` 状态砸成 `error`。只有**驻留进程本身的故障**才转 error 态。

`log_tail` 由 `backend.log_tail()` 读 `logs/mlx-lm.log` 末 40 行；日志文件本身缺失时
`log_tail` 为解释性占位字符串（"日志文件不存在: <path>"），不抛二次异常掩盖原始错误。

## 测试

全部 pytest、`tmp_path`、注入假件，**零真实推理、零真实权重**；轮询间隔注入毫秒级值保证秒内跑完。
共用夹具：`FakeBackend`（可编程脚本：退出码序列、health 序列、chunk 序列）、
`FakeArbiter`（记录 acquire/release/reap 调用序列，可编程拒绝）、`FakeCatalog`（tmp_path 假模型树）。

| # | 用例 | 断言 | 需求 |
|---|---|---|---|
| 1 | 正常加载 | 调用顺序 acquire→reap→spawn→health；终态 loaded；loadedModel 元数据与 catalog 条目逐字段一致 | R-llm-01、05 |
| 2 | 启动即退出 | 终态 error/backend_exited；error.log_tail 含假日志内容；release_heavy 被调 | R-llm-04 |
| 3 | 一直不就绪 | 终态 error/load_timeout；kill 与二次 reap 被调；log_tail 非空 | R-llm-01、04 |
| 4 | arbiter 拒绝（媒体持有） | load 返回 media_busy；无 spawn、无 reap；`_state` 不变 | R-llm-06 |
| 5 | 未知 key / 目录缺失 | model_not_found / model_dir_missing；无 acquire | R-llm-01 |
| 6 | loading 中并发再 load | 第二个拿到 load_in_progress；只有一次 spawn | R-llm-01 |
| 7 | 卸载成功 | terminate→reap 顺序；reap 报释放后才 idle+release_heavy | R-llm-02 |
| 8 | 卸载后端口仍被占 | error/port_not_released；不报成功 | R-llm-02 |
| 9 | 正常流式 | FakeBackend 吐 content chunk 序列 → delta.text 逐个对应；结尾 done 带 usage | R-llm-03 |
| 10 | reasoning 增量 | reasoning_content/reasoning chunk → delta.reasoning；text 恒为 None；两字段互不搬运；非流式同理 content/reasoning 分离 | R-llm-03 |
| 11 | 聊天拒绝 | 无模型→no_model_loaded；媒体在跑→media_busy；均未触碰 backend；立即返回 | R-llm-06 |
| 12 | model 不符 | model_mismatch，不换模型不转发 | R-llm-06（供 gateway R-gateway-10） |
| 13 | loaded 但进程已死 | llmStatus 自检转 error/backend_exited + log_tail + release_heavy | R-llm-01 |
| 14 | 上游流中断 | chat_stream 产出 error 事件后停止；无假 done | R-llm-03 |
| 15 | routes 层 | 各端点状态码（202/404/409/503/500）；SSE 帧逐帧可解析、`data:` 前缀、done 收尾 | R-llm-07 |
| 16 | 无直连扫描 | `grep -rn "127.0.0.1:8767" desk/static/` 无输出（census A17 复检的模块侧） | R-llm-07 |
| 17 | loading 中 unload | 拒绝 load_in_progress；工作线程不受影响，终态仍按 FakeBackend 脚本成/败 | R-llm-02 |
| 18 | 换模型（loaded → load 新 key） | 不二次 acquire；旧进程 terminate→reap 后才 spawn 新进程；全程 release_heavy 零调用；终态 loaded 且元数据为新条目 | R-llm-01、02 |
| 19 | spawn 前收割失败（reap 报端口仍被占） | 无 spawn；error/port_not_released；release_heavy 被调 | R-llm-02 |
| 20 | 加载中被驱逐 | FakeArbiter 在健康轮询期间把 desk_state 持有者改为 video → kill 与二次 reap 被调；终态 error/evicted；release_heavy **零**调用 | R-llm-06（配合 R-arbiter-05） |

**reality gate（不进自动验收）**：加载一个真实模型并流式收到 token —— runbook：
打开 App → 资源面板确认某聊天模型「齐」→ 聊天面板加载 → 状态条显示驻留 → 发一句话，
观察 token 逐个出现、思考过程独立展开区、`Activity Monitor` 内存上涨；卸载后
`lsof -tiTCP:8767` 无输出。

## Assumptions（本模块内部决定，及待与兄弟设计对齐的接口形状）

1. **`api:loadLlm` 是异步语义**：同步段只做校验+许可（立即成败），健康轮询在工作线程，
   进度靠轮询 `api:llmStatus`。与现状 UI 交互模型一致，避免 3 分钟的挂起 HTTP 请求。
2. **`api:reapLlmPort(port: int)` 带端口参数（Phase 1.2 已与 arbiter 对齐）**：llm 是调用方并持有
   `8767` 常量（冻结约定「mlx-lm internal 127.0.0.1:8767」，`desk/llm` 导出 `DEFAULT_LLM_PORT`，
   `LlmService` 构造参数默认值取它，仓库唯一定义点）。组装层把同一常量传给 `Arbiter(llm_port=...)`
   供驱逐收割；arbiter 门面签名为 `reap_llm_port(port: int)`，验收对任意假端口收割。
3. **让位 = 观察而非回调**：与 arbiter 设计对齐（其 Assumption 2）——arbiter 驱逐时自行按端口
   收割，不回调本模块；本模块经组装层订阅 `event:heavyStateChanged` 观察持有权丢失并收敛状态
   （见「与 arbiter 的让位协作」）。不引入注册表外机制；即便订阅缺失，`llmStatus` 存活自检
   保证状态收敛。
4. **重活许可的粒度**：acquire 发生在 load、release 发生在 unload/加载失败；聊天本身不做许可操作
   （模型驻留即持有中，arbiter 状态机 `llm_held` 期间聊天自由）。**换模型不释放再申请**：
   已持有的许可跨越「收尾旧进程 → 加载新进程」整段带走，避免释放与再申请之间的窗口被
   媒体作业抢走（那会把一次换模型变成 media_busy 失败）；也因此不依赖 arbiter 对
   「持有者重复 acquire」的语义。
5. **一次拒绝不污染状态**：4xx 类拒绝作为返回值表达，不写入 `data:llmState.error`；
   只有驻留进程故障才进 `error` 态。
6. **去掉 `--allowed-origins *`**：浏览器不再直连 mlx-lm，CORS 放开只会重新打开旁路。
7. **不写聊天历史**：对话转发无状态，会话持久化归 `library`（由 ui 编排）。
   现状 `_chat` 里写 `chat-history.json` 的逻辑不迁移（census A14 归 library）。
8. **`model_mismatch` 用 409**：既服务 ui 也服务 gateway；gateway 对外如何映射（其 R-gateway-08/10
   的 503 + 原因码）由 gateway 自己翻译，llm 只给机器可读码。
9. **非流式走 `backend.chat()`** 而非内部拼流：mlx-lm 原生非流式响应带 `usage`/`finish_reason`，
   透传最忠实。流式与非流式一致遵守 state.py 的合同：成功结果必带二者；上游缺失属上游故障，
   走 `upstream_error`（流内 error 事件 / 非流式 502），不估算、不补造。
