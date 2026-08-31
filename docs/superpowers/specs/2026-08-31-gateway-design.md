# 模块设计：gateway

**日期** 2026-08-31
**对应 spec** `docs/superpowers/specs/2026-08-31-gateway-spec.md`
**覆盖需求** R-gateway-01 … R-gateway-10
**消费（数据形状补充声明，Phase 1.2 对齐）** spec 消费清单之外，本设计还消费 `data:llmState`
（`api:llmStatus` 载荷的 `state` 半边，503 判定依据；见 GatewayBackend 协议）。

---

## 架构

gateway 是 desk 服务进程内的**第二个 HTTP 监听器**：台面 UI 服务绑 `127.0.0.1:8766`，
gateway 按配置绑 `0.0.0.0:8770`（host/port/开关取自 `data:deskConfig` 的 `gateway` 段）。
同进程、独立 socket、独立线程池——不是独立进程，因此它对 llm / arbiter 的消费是
**进程内 Python 调用**，不是 HTTP 转发。

设计基调：

1. **gateway 是纯翻译层。** 它不持有任何模型状态、不加载、不卸载、不排队。
   每个请求走「准入判定 → 方言解析 → 调 llm → 方言封装」四步，请求间零共享可变状态
   （唯一的可变状态是监听器本身的生命周期）。
2. **方言构造是纯函数。** OpenAI / Anthropic 的请求解析、响应体构造、SSE 分块/事件序列
   全部实现为无 IO 纯函数（输入 dict / 增量序列，输出 dict / bytes 序列），
   socket 层只负责把纯函数产物写出去。协议级断言因此不需要真模型、甚至不需要 socket。
3. **对下游的依赖收敛为一个注入的 `GatewayBackend` 协议对象。** 组合根（desk 服务启动代码）
   用 llm / arbiter / foundation 的真实实现组装它；测试注入假后端。gateway 内部不 import
   任何兄弟模块的具体实现。
4. **错误只有原样与拒绝两种，没有第三种。** 下游失败按方言错误信封原样上报；
   不可服务按 503 拒绝。任何路径都不产出伪造的成功响应（R-gateway-09）。

技术选型：stdlib `http.server.ThreadingHTTPServer`，与现有代码栈一致，零第三方依赖。

```
外部客户端（OpenAI SDK / Anthropic SDK / curl）
        │  0.0.0.0:8770
        ▼
┌─ desk 进程 ────────────────────────────────────────────┐
│  GatewayHTTPServer（守护线程 + 每请求一线程）           │
│    ├ GET  /v1/models            ── openai_dialect      │
│    ├ POST /v1/chat/completions  ── guard → openai_dialect ─┐
│    └ POST /v1/messages          ── guard → anthropic_dialect ┤
│                                                        │   ▼
│  GatewayService（生命周期 + data:gatewayStatus）       │ GatewayBackend（注入）
│    ▲ api:gatewayConfig（供 8766 台面挂载）             │   ├ api:llmStatus / data:loadedModel
│                                                        │   ├ data:deskState / api:canStartHeavy
│  台面 UI 服务 127.0.0.1:8766（兄弟模块所有）            │   └ api:chatCompletion / api:chatStream
└────────────────────────────────────────────────────────┘
```

## 组件

包布局（`desk/gateway/`，均为内部文件划分，非公共边界）：

| 文件 | 职责 |
|---|---|
| `__init__.py` | 公开入口：`GatewayService`、`GatewayBackend` 协议、原因码常量 |
| `service.py` | 生命周期与配置应用；`data:gatewayStatus` 的唯一产地 |
| `http_server.py` | ThreadingHTTPServer + Handler：路由、读体、写响应、SSE 写出与断连处理 |
| `guard.py` | 准入判定：503 决策、模型标识匹配（R-gateway-08/10） |
| `openai_dialect.py` | OpenAI 方言纯函数：解析/校验、非流式响应、SSE 分块、`/v1/models`、错误信封 |
| `anthropic_dialect.py` | Anthropic 方言纯函数：解析/校验（system 两形态、块数组）、非流式响应、事件序列生成器、错误信封 |
| `errors.py` | `GatewayReject` 异常类型、原因码常量、两方言信封的公共骨架 |

### GatewayService（`service.py`）

```python
class GatewayService:
    def __init__(self, backend: GatewayBackend, read_config: Callable[[], dict]): ...
    def start_from_config(self) -> None   # 启动时调用；enabled 才监听；绑定失败不抛，记入 status
    def apply_config(self) -> dict        # api:gatewayConfig 的写侧：重读配置，起/停/换绑，返回 status
    def stop(self) -> None                # 关闭监听 socket，在跑的流被断开（错误即错误，不温柔收尾）
    def status(self) -> dict              # data:gatewayStatus
```

`data:gatewayStatus` 形状（settings 面板与状态条的数据来源）：

```json
{
  "enabled": true,
  "listening": true,
  "host": "0.0.0.0",
  "port": 8770,
  "openai_base_url": "http://<host>:8770/v1",
  "anthropic_base_url": "http://<host>:8770",
  "auth": "none",
  "last_error": null
}
```

- `listening` 是实测值（socket 已 bind 成功），不是 `enabled` 的回声。
- 绑定失败（端口被占等）：`listening:false`、`last_error` 记录 `errno` 级原因，
  desk 服务整体不退（对齐 foundation 的 R-foundation-05 精神）。不做自动重试；
  用户改配置后由 UI 调 `api:gatewayConfig` 重新应用。
- `auth:"none"` 是给 settings 面板「当前无鉴权」标注用的常量字段。

**`api:gatewayConfig` 的 HTTP 面**：gateway 提供一个 WSGI 风格的小处理函数
`handle_config_request(method, body) -> (code, payload)`，由 8766 台面服务的路由所有者挂到
`/api/gateway/config`（GET 返回 `{config, status}`；POST 触发 `apply_config` 并返回新 status）。
注意消费清单里**没有** `api:writeConfig`：gateway 不写配置。UI 的改动流程是
`api:writeConfig`（foundation）→ `api:gatewayConfig` 应用（gateway 重读并换绑）。

### GatewayBackend 协议（消费契约，进程内注入）

这是 gateway 对兄弟模块 暴露/消费 形状的**唯一**假设点，Phase 1.2 对齐时只需核这一处：

```python
class GatewayBackend(Protocol):
    # api:llmStatus → data:llmState + data:loadedModel（Phase 1.2 已对齐 llm 合同：
    # 组合根由 llm 的 {state: llmState, loaded_model: loadedModel} 适配——state ← llmState.status，
    # loaded.key/served_id/meta ← loadedModel（llm 设计已含 served_id 字段，= hf_repo），
    # loaded_at ← llmState.loaded_at）
    def llm_status(self) -> dict:
        # {"state": "idle|loading|loaded|error",
        #  "loaded": None | {"key": "<目录key>", "served_id": "<mlx-lm 侧模型标识>",
        #                     "loaded_at": <epoch 秒，加载完成时刻>, "meta": {...}}}
        ...
    # data:deskState（arbiter R-arbiter-06 的台面状态对象；Phase 1.2 已按 arbiter 合同对齐：
    # holder 是对象或 null，不是字符串）
    def desk_state(self) -> dict:
        # {"holder": None | {"kind": "llm|video|music", "label": ..., "phase": ...},
        #  "media_busy": bool, "can_start": {...}}；media_busy 即媒体在跑
        ...
    # api:canStartHeavy —— 取 arbiter 的机器可读拒绝原因，gateway 不自造第二套词汇
    def can_start_heavy(self, kind: str) -> dict:
        # {"ok": bool, "reason": None | {"code": "<arbiter 原因码>", "message": "..."}}（arbiter 合同）
        ...
    # api:chatCompletion（llm 模块，非流式）
    def chat_completion(self, req: ChatRequest) -> ChatResult: ...
    # api:chatStream（llm 模块，流式）
    def chat_stream(self, req: ChatRequest) -> Iterator[ChatEvent]: ...
```

```python
ChatRequest = {"messages": [{"role": str, "content": str}],
               "max_tokens": int, "temperature": float | None, "top_p": float | None}
ChatResult  = {"content": str, "reasoning": str,          # R-llm-03：正文与思考分离
               "finish_reason": "stop" | "length",
               "usage": {"prompt_tokens": int, "completion_tokens": int}}
ChatEvent   = ("reasoning", str) | ("content", str) \
            | ("finish", {"finish_reason": ..., "usage": {...}})   # 流的最后一个事件
```

组合根从 llm 的 ChatEvent（dict 形状，见 llm 设计 state.py）适配到上述元组流：
`{"type":"delta","text","reasoning"}` 按非空字段拆开（双字段 delta 拆成两个事件，reasoning 在前）；
`{"type":"done","usage","finish_reason"}` → `("finish", …)`；`{"type":"error",…}` → 抛异常，
进入「下游在流中途抛错」路径（§错误处理）——适配是纯搬运，不改语义、不造数据。

对 llm 模块的契约要求（Phase 1.2 已对齐，llm 设计 state.py 合同同文）：
1. `api:chatStream` **成功终止的 `done` 事件必带** `finish_reason` 与 `usage`（llm 透传
   mlx-lm 上游值，两者原生都给）。上游流终止却缺任一字段，llm 视为上游故障：产出
   `error/upstream_error` 事件而非 `done`（非流式同理 502）——适配器把它转为抛异常，
   gateway 走「流中途失败」路径。因此 gateway 拿到 `finish` 必有两值可写进
   `message_delta`；缺失场景走错误信封，绝不写残缺的成功事件——不数 token、不伪造用量。
2. `loaded_at`（epoch 秒）来自 llm 的 `data:llmState.loaded_at`（组合根适配进 `loaded`）——
   `/v1/models` 的 `created` 字段唯一来源，gateway 不自记时钟、不伪造时间。

### guard（`guard.py`）

单函数 `admit(backend, requested_model) -> Admitted`，失败抛 `GatewayReject(code, http, message)`：

| 判定顺序 | 条件 | 结果 |
|---|---|---|
| 1 | `desk_state()["media_busy"]`（即 holder 非空且 `holder["kind"] ∈ {video, music}`） | 503 `media_job_running`（原因码取 `can_start_heavy("llm")` 返回的 `reason["code"]`（arbiter 原因），保持全台面同一套词汇；取不到时用本地常量 `media_job_running` 兜底） |
| 2 | `llm_status().state != "loaded"` | 503 `no_model_loaded` |
| 3 | `requested_model` 非空 且 不等于 `loaded.key` 且 不等于 `loaded.served_id` | 503 `model_not_loaded`，message 指明当前驻留的是谁（R-gateway-10：不静默换模型） |
| 4 | 通过 | 返回 `loaded`（后续调用一律用 `loaded.served_id` 作下游 model） |

guard 里**不存在任何**触发加载/卸载/acquire 的调用路径——`GatewayBackend` 协议上根本没有
这些方法，这是「绝不自动加载」的结构性保证，测试再用调用记录二次证明。

### 方言纯函数（`openai_dialect.py` / `anthropic_dialect.py`）

全部签名形如 `dict → dict` 或 `迭代器 → 迭代器[bytes]`，无 IO、无时钟外依赖
（`id`/`created` 由调用方注入或用可注入的 now/uuid，保证测试确定性）。

## 数据流

**流式/非流式的选路规则（两方言同一条）**：`parse_request` 读请求体顶层 `stream` 字段，
缺省 `false`；`true` 走 SSE 路径（§3/§5），`false` 或缺失走非流式（§2/§4）；
出现但不是布尔 → 400 `invalid_request`。选路发生在 guard 之前解析、guard 之后才发响应头，
因此 503/400 永远以普通 JSON 响应返回，不会以半截 SSE 出现。

### 1. `GET /v1/models`（R-gateway-01）

```
Handler → backend.llm_status()
  未加载 → {"object":"list","data":[]}                    # 空列表，不报错
  已加载 → {"object":"list","data":[
      {"id": loaded.key,       "object":"model","created":loaded.loaded_at,"owned_by":"localmodeldesk"},
      {"id": loaded.served_id, "object":"model","created":<同上>,           "owned_by":"localmodeldesk"}]}
```

两个可接受的标识各列一条（R-gateway-10 两者都收，列表如实反映「发什么名字都行」）。
`key == served_id` 时去重为一条。

### 2. `POST /v1/chat/completions` 非流式（R-gateway-02）

```
读体 → openai_dialect.parse_request(body)      # 校验 messages 存在且为数组，缺→400
     → guard.admit(backend, body["model"])     # 503 路径见错误处理
     → backend.chat_completion(ChatRequest)    # max_tokens 缺省 2048（沿用现行为）
     → openai_dialect.completion_response(result, model=请求里写的标识)
```

响应形状（逐字段，验收断言即此）：

```json
{"id":"chatcmpl-<uuid>","object":"chat.completion","created":<epoch>,
 "model":"<请求里的标识>",
 "choices":[{"index":0,
   "message":{"role":"assistant","content":"...","reasoning_content":"..."},
   "finish_reason":"stop|length"}],
 "usage":{"prompt_tokens":N,"completion_tokens":M,"total_tokens":N+M}}
```

`reasoning_content` 仅在 reasoning 非空时出现（与 mlx-lm/DeepSeek 系方言一致，
台面前端已按此字段消费）。

### 3. `POST /v1/chat/completions` 流式（R-gateway-03）

SSE 头：`Content-Type: text/event-stream; charset=utf-8`、`Cache-Control: no-cache`。
每块一行 `data: <json>\n\n`：

```
块0: delta={"role":"assistant"}                                  finish_reason:null
块i: delta={"content":"..."} 或 {"reasoning_content":"..."}       finish_reason:null
终块: delta={}                                                   finish_reason:"stop|length"
data: [DONE]
```

所有块共享同一 `id`/`created`/`model`，`object:"chat.completion.chunk"`。
实现为生成器：`openai_dialect.stream_chunks(events, id, created, model) -> Iterator[bytes]`，
Handler 逐块 `write+flush`，捕获 `BrokenPipeError` 后关闭下游迭代器（`close()`，
llm 侧借此终止生成）。

### 4. `POST /v1/messages` 非流式（R-gateway-04/06）

请求解析（`anthropic_dialect.parse_request`）：

- `max_tokens`：必填，缺→400 `invalid_request_error`（Anthropic 方言的硬约定）。
- `system`：字符串直接用；块数组则取全部 `type:"text"` 块拼接（R-gateway-06 两形态都收）。
  拼接结果作为 `{"role":"system"}` 消息插在 messages 之首。
- `messages[*].content`：字符串直接用；块数组取 `text` 块拼接；
  出现非 `text` 块（如 `image`）→ 400 `invalid_request_error`（不支持即明说，不静默丢弃）。
- 透传 `temperature`/`top_p`；其余字段（`metadata`/`stop_sequences`/`top_k`…）忽略，
  忽略不改变语义、符合宽进严出的兼容惯例。

响应形状：

```json
{"id":"msg_<uuid>","type":"message","role":"assistant","model":"<请求里的标识>",
 "content":[{"type":"thinking","thinking":"..."},{"type":"text","text":"..."}],
 "stop_reason":"end_turn|max_tokens","stop_sequence":null,
 "usage":{"input_tokens":N,"output_tokens":M}}
```

映射（R-gateway-06）：`finish_reason stop→end_turn`、`length→max_tokens`；
`prompt_tokens→input_tokens`、`completion_tokens→output_tokens`；
reasoning 非空时以 `thinking` 块置于 `text` 块之前（Anthropic 原生块类型，不混进正文）。

### 5. `POST /v1/messages` 流式（R-gateway-05）

`anthropic_dialect.stream_events(events, id, model) -> Iterator[bytes]`，
每个事件严格两行 `event: <name>\ndata: <json>\n\n`。事件序列：

```
message_start          data: {"type":"message_start","message":{id,type:"message",role,model,
                              content:[],stop_reason:null,usage:{"input_tokens":0,"output_tokens":0}}}
[reasoning 有增量时]
  content_block_start  index:0 {"type":"thinking","thinking":""}
  content_block_delta* index:0 delta:{"type":"thinking_delta","thinking":"..."}
  content_block_stop   index:0
content_block_start    index:k {"type":"text","text":""}        # k=0 或 1
content_block_delta*   index:k delta:{"type":"text_delta","text":"..."}
content_block_stop     index:k
message_delta          delta:{stop_reason,stop_sequence:null}, usage:{input_tokens,output_tokens}
message_stop
```

生成器内部是个两态小状态机（当前块类型 × 是否已开块）：收到与当前块类型不同的增量时
先 `content_block_stop` 再开新块。llm 保证 reasoning 先于正文（推理模型的自然顺序）；
若交错出现，按状态机如实开/关块，事件语法仍合法。`message_start` 里的 usage 以 0 占位、
真值在 `message_delta` 给出——这是 Anthropic 原生行为，不属伪造。
不发 `ping`（可选事件，YAGNI）。

### 6. 生命周期流

```
desk 启动 → GatewayService.start_from_config()
  read_config().gateway.enabled == false → 不 bind，status={enabled:false, listening:false}
  enabled → bind (host,port) → 守护线程 serve_forever
     bind 失败 → listening:false, last_error=<原因>，进程继续活
UI 改配置 → foundation api:writeConfig → gateway api:gatewayConfig(POST)
  → apply_config(): 与现监听比对 (enabled,host,port)，不同则 stop 旧 → start 新 → 返回 status
菜单栏 Quit → shell 终止服务 → GatewayService.stop()
```

## 错误处理

原则：**方言原生信封 + 机器可读原因码 + 绝不伪造成功**（R-gateway-08/09）。

信封骨架：

- OpenAI：`{"error":{"message":"...","type":"<type>","code":"<code>"}}`
- Anthropic：`{"type":"error","error":{"type":"<type>","message":"..."}}`

按路径选方言：`/v1/messages*` 用 Anthropic 信封，其余（含未知路径）用 OpenAI 信封。
所有 503 响应额外带 `Retry-After: 30` 与 `X-LocalModelDesk-Reason: <code>` 头；
后者是两方言共用的原因码通道（Anthropic 信封体内没有 code 字段的位置）。

| 情形 | HTTP | 原因码 | OpenAI type | Anthropic type |
|---|---|---|---|---|
| 媒体作业进行中 | 503 | `media_job_running`（优先取 arbiter 原因码） | `service_unavailable_error` | `overloaded_error` |
| 无模型驻留 | 503 | `no_model_loaded` | `service_unavailable_error` | `overloaded_error` |
| 请求 model 与驻留不符 | 503 | `model_not_loaded` | `service_unavailable_error` | `overloaded_error` |
| 体不是 JSON / 缺必填字段 / 非法块类型 | 400 | `invalid_request` | `invalid_request_error` | `invalid_request_error` |
| 未知路径 | 404 | `not_found` | `invalid_request_error` | `not_found_error` |
| 方法不允许 | 405 | `method_not_allowed` | `invalid_request_error` | `invalid_request_error` |
| 下游 llm 调用抛错（未开始写响应） | 500 | `upstream_error` | `api_error` | `api_error` |
| 下游在流中途抛错（200 已发出） | — | — | 见下 | 见下 |

流中途失败（响应头已发出、无法改状态码）：

- OpenAI：写一块 `data: {"error":{"message":...,"type":"api_error"}}\n\n` 后立即断开，
  **不发** `[DONE]`——`[DONE]` 是成功终止的记号，失败流不得冒充完整。
- Anthropic：发原生 `event: error\ndata: {"type":"error","error":{...}}\n\n` 后断开，
  不发 `message_stop`。
- 客户端断开（BrokenPipe）：关闭下游迭代器、记日志，无其他动作。

其余：请求体上限 10 MB（超限 400）；guard 判定与 chat 调用之间的窗口期竞态
（判定通过后模型恰被卸载）不加锁防护——下游此时会失败，按 500/流中 error 如实上报，
语义仍是「错误就是错误」，不为窄窗口引入跨模块锁。

## 测试

全部 pytest、注入 `FakeBackend`、无真模型、无 0.0.0.0（测试配置绑 `127.0.0.1` + 端口 0
取临时端口），秒级跑完。`FakeBackend` 记录每一次方法调用（名字+参数），并可编程为：
正常返回 / 返回含 reasoning 的流 / 中途抛错 / 各种状态组合。

文件：`tests/test_gateway_openai.py`、`tests/test_gateway_anthropic.py`、
`tests/test_gateway_guard.py`、`tests/test_gateway_service.py`。

| # | 用例 | 断言 | 需求 |
|---|---|---|---|
| 1 | `/v1/models` 未加载 | 200、`{"object":"list","data":[]}` | R-01 |
| 2 | `/v1/models` 已加载 | data 含 key 与 served_id 两条、各字段齐 | R-01/10 |
| 3 | OpenAI 非流式 | id/object/created/model/choices[0].message.{role,content,reasoning_content}/finish_reason/usage 三字段逐一断言 | R-02 |
| 4 | OpenAI 流式 | 首块 role、中间块 content 与 reasoning_content 分离、终块 finish_reason、最后一行 `data: [DONE]`；块序列可整体重放断言 | R-03 |
| 5 | Anthropic 非流式 | type:"message"、content 块数组（thinking 在前 text 在后）、stop_reason、usage.input/output_tokens | R-04/06 |
| 6 | Anthropic 非流式 `length` | stop_reason == "max_tokens" | R-06 |
| 7 | Anthropic system 两形态 | 字符串与块数组都被并入下游首条 system 消息（查 FakeBackend 收到的 messages） | R-06 |
| 7b | Anthropic 多轮 messages | 发 user/assistant/user 三轮（含块数组 content 一条）：FakeBackend 收到的 messages 角色顺序、条数、每条文本逐一相等（system 之后原序不增不减） | R-06 |
| 7c | `stream` 选路 | 两方言各验：`stream:true` 得 SSE、缺省得 JSON、`stream:"yes"` 得 400 `invalid_request` | R-03/05/09 |
| 8 | Anthropic 流式 | 事件名序列严格等于规定序列；每事件恰好 `event:` + `data:` 两行；delta 类型与 index 正确；message_delta 带 stop_reason+usage | R-05 |
| 9 | 503：媒体在跑（OpenAI 与 Anthropic 各一） | 503、`Retry-After`、`X-LocalModelDesk-Reason`、方言信封；**FakeBackend 调用记录里只有状态查询，无任何 chat/load 类调用** | R-08 |
| 10 | 503：无模型（两方言） | 同上，原因码 `no_model_loaded` | R-08 |
| 11 | 503：model 不符 | 原因码 `model_not_loaded`，message 含当前驻留标识；用 key 与 served_id 各发一次则 200 | R-10 |
| 12 | 错误信封：坏 JSON | OpenAI 400 `{"error":{...}}`；Anthropic 400 `{"type":"error",...}`；缺 max_tokens 400 | R-09 |
| 13 | 流中途下游抛错 | OpenAI 流出现 error 块且无 `[DONE]`；Anthropic 流出现 `event: error` 且无 message_stop | R-09 |
| 14 | 生命周期 | enabled:false 不监听（connect 被拒）；apply_config 换端口后旧端口拒、新端口通；端口被占时 listening:false + last_error 且服务线程存活 | R-07 |
| 15 | 方言纯函数单测 | stream_chunks / stream_events / parse_request 直接喂序列断言产物（不经 socket），覆盖 reasoning 交错、空正文等边角 | R-03/05 |

**reality gate（不进自动验收，出 runbook）**：另一台设备经局域网访问
`http://<本机IP>:8770/v1/models` 与两 SDK 各跑一次真对话。runbook 一行 curl + 两段
官方 SDK 最小脚本，人工执行。

## Assumptions（内部决定，未越权）

1. **Anthropic 503 的 error type 用 `overloaded_error`**：Anthropic 错误词汇表里最接近
   「暂不可服务、稍后重试」的类型；精确原因码走 `X-LocalModelDesk-Reason` 头与 message 文本。
2. **`Retry-After` 固定 30 秒**：媒体作业无可靠 ETA，给一个诚实的保守常量；不假装能预测。
3. **reasoning 的对外表达**：OpenAI 方言用 `reasoning_content` 字段（与 mlx-lm 上游、
   现有前端一致）；Anthropic 方言用原生 `thinking` 块。两者都只在 reasoning 非空时出现。
4. **`/v1/messages` 拒绝非 text 内容块**（400），视觉输入不在本轮范围（Roadmap 未列，
   目录 8 项中的视觉能力走台面 UI，不走对外网关）。
5. **未识别的顶层请求字段静默忽略**（`stop_sequences`/`metadata`/`top_k`/`tools`…）——
   例外：`tools`/`tool_choice`/`functions` 出现且非空时返回 400 `invalid_request_error`，
   因为静默忽略工具定义会让客户端拿到语义错误的「成功」响应，违背「不伪造」原则。
6. **`max_tokens` 缺省**：OpenAI 方言缺省 2048（沿现行为）；Anthropic 方言必填（其方言硬约定）。
7. **流式不实现 `stream_options.include_usage`**：spec 只要求分块格式与 `[DONE]`，YAGNI。
8. **端口 0 语义**：配置 port 为 0 时绑临时端口、status 报实际端口——仅为测试路径存在，
   文档不向用户宣传。
9. **`api:gatewayConfig` 的 HTTP 挂载点**定为 `/api/gateway/config`（GET/POST），
   由 8766 路由所有者挂载；这是 8766 内部路径命名，不新增注册表接口。
10. **组合根**（把 llm/arbiter/foundation 实现装进 `GatewayBackend`）放在 desk 服务的
    启动模块里，属服务装配代码，不属 gateway 包。
11. **对 llm 的契约期望（Phase 1.2 已对齐，冲突已消）**：llm 保证成功流的 `done` 必带
    `finish_reason` 与 `usage`；上游缺失即 llm 侧 `upstream_error`（流内 error 事件 /
    非流式 502），gateway 原样走错误路径（无 `[DONE]` / 无 `message_stop`），
    不数 token 兜底、不伪造用量。
12. **`model` 字段缺失或为空串**：两方言都放行（guard 第 3 步仅在非空时比对），
    按当前驻留模型服务；此时响应体的 `model` 字段回填 `loaded.served_id`
    （「请求里的标识」不存在时的唯一诚实值）。测试 3/5 各加一发缺 `model` 的变体断言此回填。
13. 现有 `server.py` 用 curl 子进程做 HTTP 客户端的做法**不继承**——gateway 消费的是
    进程内 Python 接口，llm 内部怎么连 8767 是 llm 的事（R-llm-07 保证外界不直连 8767）。
