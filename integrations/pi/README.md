# pi 用台面的本地模型编程

需要支持 OpenAI 原生工具调用的新版台面网关。使用两条公开接口：

- `127.0.0.1:8766`：台面控制面，查询状态、预检预算、自动加载模型。
- `127.0.0.1:8770/v1`：OpenAI 网关，收发原生 `tools`/`tool_calls` 与真实 token 用量。

不连接 mlx 私有端口。网关只传输调用；读写文件、运行命令由 pi 在本机执行。

## 安装与使用

```sh
mkdir -p ~/.pi/agent/extensions
cp integrations/pi/lmdesk.ts ~/.pi/agent/extensions/lmdesk.ts
pi --model lmdesk/qwen35
```

已有 pi 会话先 `/reload`，再 `/model` 搜索 `lmdesk`。切换后的**第一条请求**自动加载模型；仅打开选择器不会加载权重。台面应用需要已运行。

加载期间 TUI 状态栏显示进度。自动加载遵循 `lmdesk ask` 的调度口径：不抢正在对话/最近用于 UI 聊天的模型，不驱逐媒体任务，不强制超预算加载；等待可取消，默认上限 45 分钟。

推荐先只开放编码工具，减少本机模型的选择负担：

```sh
LMDESK_TOOLS=read,bash,edit,write pi --model lmdesk/qwen35
```

这限制的是提供给模型的工具声明，不是操作系统沙箱；也不会关闭其他扩展本身的网络活动。pi 的默认云端模型不被修改。

## 配置

| 环境变量 | 默认 | 含义 |
| --- | --- | --- |
| `LMDESK_GATEWAY` | `http://127.0.0.1:8770/v1` | 推理网关 |
| `LMDESK_DESK_URL` | `http://127.0.0.1:${LMD_SHELL_PORT:-8766}` | 控制面 |
| `LMDESK_AUTOLOAD` | `1` | `0` 关闭自动加载 |
| `LMDESK_LOAD_TIMEOUT_MS` | `2700000` | 包含控制面 HTTP 请求的加载等待上限 |
| `LMDESK_MAX_TOKENS` | `8192` | 最大输出 token（含模型思考） |
| `LMDESK_TOOLS` | 全部已启用工具 | 可选工具声明白名单 |
| `LMDESK_DEBUG` | 关闭 | `1` 输出加载状态，不打印提示词/凭据/工具参数 |

网关仍不自动加载、不排队；自动加载由这个 pi 扩展通过控制面完成。Anthropic `/v1/messages` 工具块、图像输入、强制 `tool_choice` 和严格 schema 约束不在本次支持范围，明确拒绝而非假装支持。模型是否正确完成编程任务仍取决于其能力，原生工具协议不保证任务成功。

## 验证

```sh
pytest tests/test_gateway_*.py tests/llm -q
# 使用已安装 pi 的真实转换器/流解析器，控制面与网关 mock，无模型推理/网络请求：
PI_PACKAGE=/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent \
  node integrations/pi/test.mjs
```

`test_gateway_tools.py` 测 Gateway → DeskGatewayBackend → LlmService → 假 mlx 的整个链路，覆盖并行分片、调用 ID、工具结果回传、真实 usage、中断不伪装成功和聊天计数。
