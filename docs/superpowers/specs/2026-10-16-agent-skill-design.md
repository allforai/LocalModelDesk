# 模块设计：本机 agent 能力（lmdesk 命令行 + skill + 设置页多选安装）

**日期** 2026-10-16
**来源** 用户 2026-10-16：「这个只是作为一个能力提供给 codex/claudecode/pi 等，并不是取代」；「命令行最好」；「写一下 skill，然后在设置页增加一个安装到本机的 agent 的 skill」；「按需加载」；不做服务端队列、由命令行自行等待「同意」；第一版「对话加图片」；「把本地模型的会话管理概念也给到 llm agent」；不给删除、对话不进会话「两点都按推荐来」；「deepseek harness 也需要支持」；「安装的时候要让用户可以多选，而不是全部自动安装上」；skill 更新方案「可以」。
**上游** gateway 设计 `2026-08-31-gateway-design.md`（gateway 不加载、不卸载、不排队——本设计不改它）；arbiter 设计 `2026-08-31-arbiter-design.md`；图片会话 `2026-09-24-image-sessions-design.md`；硬件软限制（内存只提醒+确认，不拦）。

每条 **[A-xx]** 可写成测试断言。

---

## 0. 范围与非目标

- 范围：
  - `lmdesk` 命令行，包含 `status`、`models`、`ask`、`image sessions|new|show|gen|rename`；
  - 一份 SKILL.md；
  - 设置页「本机 agent」区域，可多选安装到 Claude Code、Codex、pi、DeepSeek Harness；
  - 服务端三处小改：对话进行中计数、`/api/agent-skill`、`/api/state` 返回版本号；
  - 启动时检查已装链接是否失效；
  - 打包进 app。
- [A-00a] 不改 gateway（`desk/gateway/`），它仍不加载、不排队。命令行只走台面内部 `/api`。
- [A-00b] 服务端不加任务队列。排队等待全部在命令行进程内完成（§3）。
- [A-00c] 第一版不做视频、音乐，不做删除会话，`ask` 不写入台面聊天会话，不做 MCP 外壳。
- [A-00d] 不改现有界面的生成和对话交互，也不改 arbiter 的批准、拒绝规则。
- 台面未发布，不谈兼容。

## 1. 整体结构

```
agent ──执行命令──▶ lmdesk ──HTTP──▶ 台面服务 127.0.0.1:$LMD_SHELL_PORT（默认 8766）/api/...
   ▲                        │
   └── 读 SKILL.md          └─ 连不上时用 open -gj 在后台拉起 app，等它就绪
```

- [A-01] 命令行是 `desk/agent_cli/` 包，只用标准库，不 import `desk` 的其他模块。入口是 `python -m desk.agent_cli`。
- [A-02] app 包里有 `Contents/Resources/bin/lmdesk`，一个 shell 小脚本，用 `Contents/Resources/python/bin/python3.13` 运行 `-m desk.agent_cli`。它通过自身的真实路径（解析软链接后）定位所在的 app 包。
- [A-03] skill 放在 `desk/agent_skill/bundled/local-model-desk/SKILL.md`。打包后位于 `Contents/Resources/desk/agent_skill/bundled/local-model-desk/`，随 `desk/` 一起 rsync。
- [A-04] 从源码运行台面时（不是从 app 包运行），安装链接指向仓库里的 skill 目录和 `scripts/lmdesk` 开发脚本，改动立即生效。

## 2. 命令清单与输出

```
lmdesk status
lmdesk models
lmdesk ask "问题" [--model KEY] [--system "…"] [--file PATH …] [--max-tokens N]
lmdesk image sessions
lmdesk image new "名字"
lmdesk image show <会话>
lmdesk image gen <会话> "提示词" [--size WxH] [--steps N] [--seed N]
                 [--from <尝试id> --strength 0–1] [--out PATH] [--force]
lmdesk image rename <会话> "新名字"
通用参数：--json  --timeout 秒（默认 1800）
```

- [A-10] `<会话>` 可以填 id，也可以填名字。名字匹配到多个时，退出码 2，并列出这些候选。
- [A-11] stdout 只放最终结果，进度和等待提示都走 stderr。
  - `ask` 输出回答正文。
  - `gen` 输出图片的绝对路径；带 `--out` 时，复制过去，并输出复制后的绝对路径。
  - `--json` 时 stdout 是单个 JSON 对象：`gen` 包含 `session_id`、`attempt_id`、`path`、`seed`、`params`；`show` 列出每次尝试的 `id`、`prompt`、`params`、`path`、`status`。
- [A-12] `ask` 的 stdin 不是终端时，读入 stdin 内容，接在问题后面。`--file` 可以重复，每个文件以「文件名 + 内容」的块拼进用户消息。
- [A-13] 退出码固定为：
  - 0 成功；
  - 1 其他错误，包括接口不兼容、生成失败；
  - 2 参数错误或会话名有歧义；
  - 3 等待超时；
  - 4 内存不足，需要确认；
  - 5 模型或会话不存在，或者没有指定模型而当前也没有加载。
  - 出错时，stderr 最后一行是一句人能读懂的原因；`--json` 时，stdout 是 `{"error": {"code", "message"}}`。
- [A-14] 不提供删除命令。

## 3. 等待、换模型、提交（命令行内部）

- [A-20] 决策写成纯函数 `decide(op, want_model, state) -> wait|swap|submit|fail`，其中 state 来自 `/api/llm/status` 和 `/api/media/job`。规则如下：

| 台面状态 | `ask` | `image gen` |
|---|---|---|
| 正在加载模型 | wait | wait |
| 媒体任务在跑 | 要的就是当前模型：submit；否则 wait | wait |
| 有对话在进行（`active_chats > 0`） | 要的就是当前模型：submit；否则 wait | wait |
| 空闲 | 不是要的模型：swap；然后 submit | submit（由 arbiter 决定，必要时它自己卸掉对话模型） |

- [A-21] 选模型：
  - 有 `--model`：用它。
  - 没有 `--model` 但已加载了模型：用当前加载的那个，不换。
  - 两者都没有：退出码 5，stderr 列出可用模型的 key。
- [A-22] swap 就是调用 `POST /api/llm/load`，再轮询直到 `loaded`。加载失败时退出码 1，并附带台面给出的原因。
- [A-23] 轮询间隔从 2s 开始，每次 ×1.5，最长 5s。等待期间，stderr 每 15s 打一行，例如「等待中：图片任务进行中（已等 45s）」。
- [A-24] submit 收到 409（`media_busy`、`load_in_progress`）时，回到等待状态，不算失败。
- [A-25] 总耗时超过 `--timeout`：任务还没提交，就以退出码 3 退出；已经提交，就先 `POST /api/media/cancel`，再以退出码 3 退出。收到 SIGINT 或 SIGTERM 时同样处理。
- [A-26] 台面因为内存不足要求确认时，退出码 4，stderr 原样转述台面的内存估算文案。带 `--force` 时，把 `force: true` 透传给接口。
- [A-27] 图片的会话、尝试、`--from` 走现有的 `/api/media-sessions/image` 和 `POST /api/media/image`（字段 `session_id`、`base: {attempt_id, strength}`），参数校验由服务端负责。命令行只做格式解析，比如把 `--size` 拆成宽和高。

## 4. 服务发现与版本

- [A-30] 端口取 `LMD_SHELL_PORT`，不合法或没设置时用 8766，与 `desk/__main__.py:runtime_port` 规则一致。
- [A-31] 连不上服务时：
  - 如果命令行位于某个 app 包内，就执行 `open -gj <该 app>`，然后每 1s 探测一次 `/api/state`，最多 60s。超时以退出码 1 退出，提示「台面未能启动」。
  - 从源码运行（不在 app 包内）时，不自动启动，直接以退出码 1 提示。
- [A-32] 版本号统一取自 `packaging/VERSION`，从 app 包运行时取打包写入的 `bundle_version`。命令行比对自己的版本和 `/api/state` 返回的 `version`（见 A-42）。版本不一致时，stderr 警告一行，继续执行。

## 5. 服务端改动

- [A-40] `LlmService` 维护 `active_chats` 计数，在 `/api/llm/status` 中返回。
  - `chat` 和 `chat/stream` 开始时加一。
  - 正常结束、出错、客户端断开、生成器被关闭，任何一种情况下都要减一，且只减一次。
- [A-41] 新增 `desk/agent_skill/` 模块，路由如下：
  - `GET /api/agent-skill`：返回每个安装目标的状态，以及命令行链接的状态。
  - `POST /api/agent-skill`，请求体为 `{"targets": [...]}`：表示「最终要装上哪几个」，没列出的就卸载。返回应用后的状态，每一行带各自的结果或错误。
- [A-42] `/api/state` 增加 `version` 字段，取值规则同 A-32。现在 `/api/state` 只有 `holder`、`holders`、`media_busy`、`can_start` 这几个字段，没有版本信息。

## 6. 安装目标与状态

- [A-50] 安装目标（全部是软链接，指向当前 app 包或仓库里的 skill 目录）：

| key | 名称 | 链接位置 | 检测「已检测到」的依据 |
|---|---|---|---|
| `claude` | Claude Code | `~/.claude/skills/local-model-desk` | PATH 或 `~/.local/bin` 里有 `claude`，或者存在 `~/.claude/` |
| `codex` | Codex | `~/.codex/skills/local-model-desk`（见 A-51） | 有 `codex` 命令，或者存在 `~/.codex/` |
| `pi` | pi | `~/.pi/agent/skills/local-model-desk` | 有 `pi` 命令，或者存在 `~/.pi/` |
| `dsh` | DeepSeek Harness | `~/.dsh/skills/local-model-desk` | 存在 `/Applications/DeepSeek Harness.app` 或 `~/Applications/…`，或者存在 `~/.dsh/` |

- [A-51] Codex 的目录要在实现的第一步实测：把一个最小 skill 放进 `~/.codex/skills/`，看 Codex 0.160.1 能不能识别（实测完清理掉）。
  - 能识别：用 `~/.codex/skills`。
  - 不能识别：改用 `~/.agents/skills`，界面上这一行注明「同时对 pi、DeepSeek Harness 生效」。
  - 实测结论写回本节。
  - 依据：`~/.agents/skills` 会同时被 Codex、pi、DeepSeek Harness 读取（Codex 官方文档、pi 1.2.0 源码、dsh `dsh-skill-filesystem` 源码），所以默认不用它，以保证每个 agent 能单独勾选。
- [A-52] 命令行链接 `~/.local/bin/lmdesk` 不单独设勾选框。至少装了一个 agent 时自动建立；全部卸载时自动移除。
- [A-53] 每个位置的状态只有以下几种：
  - `installed`：指向当前 app 或仓库的 skill。
  - `absent`：没有安装。
  - `stale`：是一个软链接，目标是某个 LocalModelDesk 的 skill 路径（以 `agent_skill/bundled/local-model-desk` 结尾），但不是当前这个，或者目标已经不存在。
  - `occupied`：那个位置存在，但不是指向台面的链接。
  - `error`：没有写权限等，附带原因。
- [A-54] 安装：
  - `absent` 或 `stale` 的位置，创建或替换为指向当前的链接，必要时先创建上级目录。
  - `occupied` 的位置不碰，这一行报错。其余行照常进行。
- [A-55] 卸载只删除 `installed` 或 `stale` 的链接，绝不删除真实的文件或目录，也不删除指向别处的链接。
- [A-56] 台面不会自己安装任何一项。只有用户在设置页点「应用」才会写入。

## 7. 设置页「本机 agent」区域

- [A-60] 位于设置页「对外 API」之后。按钮层级、卡片列表样式沿用现有视觉基线。
- [A-61] 结构：
  - 标题，加一句说明：「让选中的 agent 通过 lmdesk 命令使用本机模型（对话、生图、图片会话）」。
  - 四行勾选项：名称、检测提示（已检测到 / 未检测到）、状态文字。
  - 一个主按钮「应用」。
  - 一行命令行链接状态。
- [A-62] 打开页面时，勾选状态等于各行当前是否为 `installed`。`stale` 显示为勾选，状态文字是「指向旧位置，点应用更新」。
- [A-63] 「未检测到」的行也可以勾选。检测结果只是提示。
- [A-64] 勾选状态和当前已安装的一致时，「应用」按钮不可点。应用后，用接口返回的结果刷新各行；失败的行显示原因。
- [A-65] 矮窗口和窄窗口下，没有横向滚动，内容不溢出。

## 8. 更新与失效

- [A-70] 因为装的是软链接，app 被覆盖更新后，skill 和命令行自动就是新内容，两者版本始终一致。SKILL.md 里不写版本号。
- [A-71] 台面启动时计算一次 A-53 的状态。只要有一行是 `stale`，菜单栏图标就显示提示点；设置页对应行显示「指向旧位置」或「已失效」。
- [A-72] 不自动改链接。本机可能有好几份 app，自动改会让链接来回跳。

## 9. SKILL.md 内容

- [A-80] frontmatter：
  - `name: local-model-desk`，和目录名一致，用小写字母加连字符，不超过 64 字符。
  - `description` 不超过 1024 字符。
  - 文件第一行就是 `---`。
- [A-81] description 要写清楚三件事：
  - 这是本机的本地模型台面；
  - 适用场景：用本地大模型做翻译、总结、改写、批量处理文本等离线或隐私敏感的任务；用本地图片模型生成和迭代图片素材，并按会话管理；
  - 触发词：「本地模型」「台面」「本地生图」。
- [A-82] 正文必须包含：
  - **调用方式**：命令是 `lmdesk`，找不到时用 `~/.local/bin/lmdesk`。
  - **耗时**：命令会自行排队等待，可能要几分钟，工具超时至少设 10 分钟，中途不要自己重试。
  - **各退出码的处理**：3 告知用户台面一直忙；4 先问用户，同意后加 `--force`；5 先用 `models` 或 `image sessions` 查清楚。
  - **素材管理**：生图前先 `image sessions`，有合适的会话就接着用，没有就按用途新建并起有意义的名字；在满意的那张上改用 `--from`；用 `--out` 放进项目；不能删除会话，需要删就请用户在台面里删。
  - **对话**：`ask` 是一次性调用，上下文用 `--file` 或 stdin 传入。
  - 两到三个典型示例。

## 10. 打包

- [A-90] `scripts/build-app.sh` 要生成 `Contents/Resources/bin/lmdesk`（可执行），skill 随 `desk/` 进入 app 包。
- [A-91] 在 dist 版本的 app 中，`Contents/Resources/bin/lmdesk status --json` 能在台面运行时返回成功。

## 11. 测试

- [A-T1] 测 `decide()` 的单元测试，按 A-20 表格逐格覆盖。退避节奏和超时用假时钟测试。
- [A-T2] 命令行集成测试：用 `desk/testing/harness.py` 启动带假模型的台面，再在子进程里运行命令行。要覆盖：
  - `ask` 的三种情况：未加载、已加载、需要换模型；
  - `image new/gen/show/rename`，以及 `--from`、`--out`、`--json`；
  - 409 后重试成功；
  - 内存不足返回 4，加 `--force` 后成功；
  - 超时或中断时会取消已提交的任务；
  - 版本不一致只警告；
  - 会话名有歧义时返回 2。
- [A-T3] `active_chats` 的单元测试：正常结束、出错、流被中途关闭这几种情况都只减一次。
- [A-T4] 安装模块的单元测试：在临时 HOME 下覆盖 A-50 至 A-56 的全部状态和动作，确认不会删除真实文件或目录。
- [A-T5] 设置页的真实浏览器 e2e（`tests/e2e`）：勾选、应用、状态刷新、异常行提示，以及矮窗口和窄窗口布局。
- [A-T6] SKILL.md 格式检查（A-80）。
- [A-T7] 打包检查（A-90、A-91）。
- [A-T8] 手动验收：在 Claude Code、Codex、pi、DeepSeek Harness 中，各说一句「用本地模型把这段翻成英文」和「本地生成一张图放进 ./tmp」，四者都会自己调用 `lmdesk`。结果记入验收记录。
