# 模块 spec：gateway

**单一职责** 对外提供 OpenAI 与 Anthropic 两种方言的兼容推理接口。

## 背景约束（人类明示，含已声明风险）

监听 `0.0.0.0`，**无令牌鉴权**。已向人类声明：同网络任何设备、以及本机浏览器里任何知道端口的页面
都能驱动模型并读取输出，且与 README 原有的「推理不出门」冲突。人类确认后仍如此选择。
README 将被改写为实际行为。

默认端口 `8770`（台面 UI 仍在 `127.0.0.1:8766`，mlx-lm 内部端口 `8767` 不对外）。
端口与开关可配置，存在 `data:deskConfig` 的 `gateway` 段。

**不自动加载模型**：外部请求到达时若没有模型驻留、或媒体作业在跑，一律报错，不抢内存、不排队。

## 需求

- **R-gateway-01** `GET /v1/models`：OpenAI 格式，列出当前可服务的模型。没有模型驻留时返回空列表而非报错。
- **R-gateway-02** `POST /v1/chat/completions` 非流式：OpenAI 请求与响应形状，含 `usage`、`finish_reason`。
- **R-gateway-03** 同端点流式：SSE，`data:` 分块与 OpenAI 增量格式一致，以 `data: [DONE]` 结束。
- **R-gateway-04** `POST /v1/messages` 非流式：Anthropic 请求形状（`model`/`max_tokens`/`messages`/`system`）
  与响应形状（`type:"message"`、`content` 块数组、`stop_reason`、`usage.input_tokens`/`output_tokens`）。
- **R-gateway-05** 同端点流式：发出 `message_start`、`content_block_start`、`content_block_delta`、
  `content_block_stop`、`message_delta`、`message_stop` 事件，每个事件带 `event:` 与 `data:` 两行。
- **R-gateway-06** Anthropic 的 `system`（字符串或块数组）、多轮 `messages`、`stop_reason`
  （`end_turn` / `max_tokens`）与 token 用量必须正确映射到底层结果。
- **R-gateway-07** 绑定 `0.0.0.0` 于配置端口，使同网络其他设备可达；开关关闭时不监听。
- **R-gateway-08** 无模型驻留或媒体作业进行中：返回 `503`，带 `Retry-After` 头与机器可读原因码。
  **绝不自动加载模型，绝不排队等待。**
- **R-gateway-09** 错误按各自方言的原生错误信封返回（OpenAI 的 `{"error":{...}}`；
  Anthropic 的 `{"type":"error","error":{"type":...,"message":...}}`）。不得伪造成功响应。
- **R-gateway-10** 请求里的 `model` 既接受目录 key，也接受当前加载模型的标识符；
  与当前驻留模型不符时按 R-gateway-08 报错说明，不静默换模型。

## 暴露

`api:openaiListModels`、`api:openaiChatCompletions`、`api:anthropicMessages`、
`api:gatewayConfig`、`data:gatewayStatus`

## 消费

`api:chatStream`、`api:chatCompletion`、`api:llmStatus`、`data:loadedModel`、
`data:deskState`、`api:canStartHeavy`、`api:readConfig`、`data:deskConfig`

## 验收取向

全部用注入的假 LLM 后端做协议级测试，不需要真模型：
- OpenAI 非流式/流式响应形状逐字段断言；
- Anthropic 非流式响应形状逐字段断言；
- Anthropic 流式：断言事件顺序与每个事件的 `event:`/`data:` 结构完整；
- 503 用例：无模型 与 媒体在跑 两种，断言状态码、`Retry-After`、原因码，并断言**没有触发加载**；
- 两种方言的错误信封各一例。
局域网可达性**自动验收**（决策 D-0002）：绑 `0.0.0.0:8770` 后，从本机以局域网 IP
`http://192.168.31.68:8770/v1/models` 自连——该路径不走回环，足以证明非本地监听生效。
IP 在测试中动态取自 `ipconfig getifaddr en0`，取不到则跳过并明确报告跳过原因（不得静默通过）。
**本模块无 reality gate。**
