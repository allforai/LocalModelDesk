# pi 本地编程设置入口

用户确认：设置里安装 pi 接入；列出五个模型，名称体现完整版本和建议用途；方案 A 保留 key。追加：未装 pi 时通过 Homebrew 自动安装 pi agent。

## 交付范围

- 独立于「本机 agent」技能，在设置添加「pi 本地编程」。
- provider 源码 `integrations/pi/lmdesk.ts`，构建时复制进 `Resources/desk/pi_integration/bundled/lmdesk.ts`，签名前校验、verify-app 对照规范源码。
- `PiIntegrationService.status/apply/check` 隐藏文件所有权、管理摘要和连接配置；固定路径 HTTP 适配，不接受任意代码或路径。
- 安装独立副本和带 owner/format/sha256 的管理记录。未知文件、用户改动、外部链接、目录占用、损坏记录一律拒绝更新/移除；精确匹配旧发布版或当前版可显式接管。
- 状态包括未安装、手动安装、已安装、需更新、冲突、错误；变更源文件或端口须更新。
- 检查为只读：控制面 `/api/llm/status` 与网关 `/v1/models`；无模型加载/推理/后台 pi 进程。
- 安装/更新/移除都不改 pi 默认模型、账号、其他资源，不触及台面模型和会话。
- 扩展按环境变量 → 管理记录 → 默认地址解析端点。已有会话需 `/reload`。
- POST 仅接受 JSON，同源浏览器请求；外站 Origin/cross-site fetch 拒绝。不是给不可信 LAN 客户端的鉴权系统。

## 模型展示

元数据：`desk/pi_integration/models.json`。测试确保 key 集合与聊天目录一致，扩展 MODELS 的名称和此文件一致。

| key | 版本 | 用途 |
|---|---|---|
| qwen35 | Qwen3.6 35B-A3B 8bit | 最推荐编程 |
| qwen27 | Qwen3.8 27B 8bit | 擅长写作 |
| superqwen | SuperQwen3.8 27B 4bit | 擅长对话·省内存 |
| glm | GLM 4.7 Flash 30B-A3B 8bit | 快速问答 |
| gemma | Gemma 4 31B 8bit | 擅长看图 |

用途是选用建议，不声称横向评测排名；qwen35 已验工具闭环，不保证任意任务成功。GLM 未测速不宣称最快。Gemma 看图不冒充 pi 已支持图像。
Pi 自身选择器行显示 ID/provider，不修改 Pi 本体、不改 ID；用途进入 Model Name 和设置页名称。

## 验证与边界

- 临时 HOME：新装、幂等、更新、端口变更、接管、删改保护、移除、孤立回执、缺失/空包、JSON/Origin 拒绝、真实 HTTP 装配。
- Pi 真实转换器/解析器 mock：原生工具链不回退、端点优先级、配置损坏、元数据、发现不加载。
- Playwright：设置入口、五个版本和用途、复制、安装/检查/冲突/移除、窄短窗口。
- 构建包含安装源，verify-app 校验摘要一致；检查不能替代真模型编程验收。
- 首版只管理默认 `~/.pi/agent`；自定义 PI_CODING_AGENT_DIR 手动安装。不改 Pi TUI，不实现图像/Anthropic 工具。
- 显式点击安装时，缺少 pi 则后台运行固定 argv `brew install --formula pi-coding-agent`，已有 pi 不重复安装。只读状态/打开设置不启动任务，重复点击不重复执行。
- 没有 Homebrew 则提示，不执行安装脚本、不用 sudo。安装超时 900 秒，失败日志限末尾 4000 字节，退出台面终止隔离的进程组。成功后重新检测 pi，再安装扩展；失败不声称成功、不卸载 pi。
- Homebrew 分支用进程替身测试成功/失败/缺失/超时/关闭，不为验证而卸载当前机器的 pi。
- 文件修改与回执写入分别原子发布，不是跨文件事务；部分失败后状态可检查/重试（当前源码摘要可恢复）。不提供防同一用户恶意并发替换文件的沙箱保证。
