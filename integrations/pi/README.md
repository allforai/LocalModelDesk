# pi 用台面的本地模型编程

需要支持 OpenAI 原生工具调用的新版台面网关。使用两条公开接口：

- `127.0.0.1:8766`：台面控制面，查询状态、预检预算、自动加载模型。
- `127.0.0.1:8770/v1`：OpenAI 网关，收发原生 `tools`/`tool_calls` 与真实 token 用量。

不连接 mlx 私有端口。网关只传输调用；读写文件、运行命令由 pi 在本机执行。

## 安装与使用

### 推荐：台面设置页

打开新版台面，在 **设置 → pi 本地编程** 点击「安装或更新」。
此入口安装的是 provider 扩展，不是上面的「本机 agent」技能。未检测到 pi 时，会先后台运行
`brew install --formula pi-coding-agent`，成功且检测到 pi 后再安装扩展。
仅打开设置页不会安装软件；无需 sudo。未装 Homebrew 时明确提示先安装 Homebrew，不执行网络安装脚本。
安装状态自动刷新，失败显示退出码和尾部日志，可重试；15 分钟超时终止。退出台面会停止本次安装进程组。
已有 pi 时不重复执行 brew。

- 扩展随 app 打包，不依赖源码目录；安装为独立副本，移动 app 不会使扩展链接失效。
- 管理文件：`~/.pi/agent/extensions/lmdesk.ts` 与 `~/.pi/agent/localmodeldesk.json`（摘要和两条连接地址）。
- 状态：未安装、已安装、需更新、手动安装可接管、文件冲突、不可用。
- 只更新或移除摘要匹配的台面文件。未知同名文件、目录、外部链接、用户修改过的扩展和无效管理记录均停止处理，不覆盖。
- 已知旧手动发布版或当前源码的精确副本可由「安装或更新」显式接管；未接管时不直接移除。
- 「检查连接」只读控制面和网关，不加载模型、不生成、不执行 pi；成功不等于编程任务已验收。
- 修改台面端口后，重新点击「安装或更新」并在 pi `/reload`；显式环境变量仍优先。
- 不改 pi 的 `settings.json`、`models.json`、默认模型、账号、技能或台面模型/会话；移除接入不会卸载 Homebrew 安装的 pi。
- 移除时需确认；已有 pi 会话还需 `/reload` 才会卸下扩展。

界面列出 5 个模型，key 保持 `qwen35/qwen27/superqwen/glm/gemma`。
名称带完整版本和建议用途，pi 的 `/model` 每行仍显示 key，选中后 **Model Name** 显示用途；也可搜索名称。
用途元数据在 `desk/pi_integration/models.json`，有测试确保扩展名与之同步。
“最推荐编程”基于 qwen35 已验证工具闭环，不是全模型横评排名；写作、对话与短问答是场景建议。
Gemma、Qwen27、SuperQwen 在台面与 pi 中都支持图片输入；GLM、Qwen35 保持纯文本。

默认用户目录为 `~/.pi/agent`；使用 `PI_CODING_AGENT_DIR` 自定义目录时，请手动安装到对应的 extensions 目录。

### 手动安装（源码用户）

已有同名文件时先检查并备份，不要直接覆盖自己的扩展：

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

设置页安装后，扩展从管理记录读连接地址。优先级为显式环境变量 → 管理记录 → 下列默认值。
`LMD_SHELL_PORT` 会覆盖记录中的控制面端口；`LMDESK_DESK_URL` 优先于它。
管理记录存在但格式错误时明确报错，不静默回退到错误端口。

| 环境变量 | 默认 | 含义 |
| --- | --- | --- |
| `LMDESK_GATEWAY` | `http://127.0.0.1:8770/v1` | 推理网关 |
| `LMDESK_DESK_URL` | `http://127.0.0.1:${LMD_SHELL_PORT:-8766}` | 控制面 |
| `LMDESK_AUTOLOAD` | `1` | `0` 关闭自动加载 |
| `LMDESK_LOAD_TIMEOUT_MS` | `2700000` | 包含控制面 HTTP 请求的加载等待上限 |
| `LMDESK_MAX_TOKENS` | `8192` | 每次请求的输出配额（含模型思考），不是模型最大能力 |
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


## 本地权重能力核实（2026-11-05）

- Qwen27、SuperQwen、Gemma 保留视觉权重，使用独立的 mlx-vlm 0.7.12 环境；台面对话和 pi 都能传图片。GLM、Qwen35 的本地包没有视觉权重，图片请求会明确拒绝。
- 本地配置的文本上下文：GLM 202752 tokens，其余四个 262144 tokens。这是配置声明，并非满窗实测承诺；实际内存额度看 `/api/budget`。
- 五个模型的 thinking 开/关均已用真实推理核实。pi 的 off 关闭 thinking，其余档位开启；目前没有把 low/medium/high 解释为已验证的分级思考能力。
- `LMDESK_MAX_TOKENS=8192` 是默认输出配额，可修改；没有证据表明 8192 是底模最大输出。
- 网关只接收 base64 PNG/JPEG/WebP data URL，单图最多 5 MiB、整个网关请求最多 10 MiB；台面上传每轮最多两张、单图 3 MiB。不会下载远程图片或读取图片 URL 指向的本地文件。
- 图片随会话保存并参与后续对话；含图片的会话不参与自动文本字符/token 比例校准和自动摘要，避免将 base64 体积误算为文本。
- 开发环境：`uv venv .venv-vision --python .venv-desk/bin/python`，然后 `uv pip install --python .venv-vision/bin/python --excludes packaging/excludes-vision.txt -r packaging/requirements-vision.txt`。正式 app 内嵌独立 `pylibs/vision`。

真实响应及限制见 `vision-verification.md`。

公共网关在流式响应中每 15 秒发送 SSE 注释保活，避免长时间思考或生成工具参数时触发客户端的响应体空闲超时；注释不计入模型输出。
