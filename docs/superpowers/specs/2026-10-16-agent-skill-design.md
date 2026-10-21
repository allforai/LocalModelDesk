# 模块设计：本机 agent 能力（lmdesk 命令行 + skill + 设置页多选安装）

**日期** 2026-10-16
**来源** 用户 2026-10-16：「这个只是作为一个能力提供给 codex/claudecode/pi 等，并不是取代」；「命令行最好」；「写一下 skill，然后在设置页增加一个安装到本机的 agent 的 skill」；「按需加载」；不做服务端队列、由命令行自行等待「同意」；第一版「对话加图片」；「把本地模型的会话管理概念也给到 llm agent」；不给删除、对话不进会话「两点都按推荐来」；「deepseek harness 也需要支持」；「安装的时候要让用户可以多选，而不是全部自动安装上」；skill 更新方案「可以」；闭环自审 14 条「全部按推荐改」。
**上游** gateway 设计 `2026-08-31-gateway-design.md`（gateway 不加载、不卸载、不排队——本设计不改它）；arbiter 设计 `2026-08-31-arbiter-design.md`；图片会话 `2026-09-24-image-sessions-design.md`；硬件软限制（内存只提醒+确认，不拦）。

每条 **[A-xx]** 可写成测试断言。

---

## 0. 范围与非目标

- 范围：
  - `lmdesk` 命令行，包含 `status`、`models`、`ask`、`image sessions|new|show|gen|wait|rename`；
  - 一份 SKILL.md；
  - 设置页「本机 agent」区域，可多选安装到 Claude Code、Codex、pi、DeepSeek Harness；
  - 服务端小改（§5）：
    - 对话进行中计数和界面最近一次对话的时间；
    - 记录模型是被谁换上的；
    - 媒体取消接口带任务 id；
    - `/api/agent-skill` 接口；
    - 只读预检接口 `/api/agent/precheck`；
    - `/api/state` 返回版本号；
  - 聊天页显示「模型已被 agent 切换」的提示；
  - 启动时检查已装链接是否失效，失效时在菜单栏显示提示点（含 Swift 侧改动）；
  - 卸载脚本清理链接；
  - 打包进 app。
- [A-00a] 不改 gateway（`desk/gateway/`），它仍不加载、不排队。命令行只走台面内部 `/api`。
- [A-00b] 服务端不加任务队列。排队等待全部在命令行进程内完成（§3）。
- [A-00c] 第一版不做以下这些：
  - 视频、音乐；
  - 删除会话；
  - `ask` 写入台面聊天会话；
  - MCP 外壳；
  - 用完后自动卸载 agent 加载的模型（见 A-28）；
  - 对话模型加载的「内存只提醒、不阻止」——现在这个软限制本来就没实现，另立题目处理。
- [A-00d] 不改 arbiter 的批准、拒绝规则。现有界面的生成和对话交互不改，只在聊天页加一条切换提示（A-66）。
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
- [A-05] 命令行发出的会改变状态的请求（对话、加载、生图、取消），一律在请求体里带上 `"origin": "agent"`。服务端靠这个字段区分是 agent 还是界面发起的（A-40、A-43）。

## 2. 命令清单与输出

```
lmdesk status
lmdesk models
lmdesk ask "问题" [--model KEY] [--system "…"] [--file PATH …] [--max-tokens N]
lmdesk image sessions
lmdesk image new "名字"
lmdesk image show <会话>
lmdesk image gen <会话> "提示词" [--size WxH] [--steps N] [--seed N]
                 [--from <尝试id> --strength 0–1] [--out PATH] [--force] [--no-wait]
lmdesk image wait <会话> <尝试id> [--out PATH]
lmdesk image rename <会话> "新名字"
通用参数：--json  --timeout 秒（默认 1800）
```

- [A-10] `<会话>` 可以填 id，也可以填名字。名字匹配到多个时，退出码 2，并列出这些候选。
- [A-11] stdout 只放最终结果，进度和等待提示都走 stderr。
  - `ask` 输出回答正文。
  - `gen`、`wait` 输出图片的绝对路径；带 `--out` 时，复制过去，并输出复制后的绝对路径。
  - `--json` 时 stdout 是单个 JSON 对象：`gen`、`wait` 包含 `session_id`、`attempt_id`、`path`、`seed`、`params`；`show` 列出每次尝试的 `id`、`prompt`、`params`、`path`、`status`。
- [A-12] `ask` 的 stdin 不是终端时，读入 stdin 内容，接在问题后面。`--file` 可以重复，每个文件以「文件名 + 内容」的块拼进用户消息。
- [A-13] 退出码固定为：
  - 0 成功；
  - 1 其他错误，包括接口不兼容、生成失败、台面未能启动；
  - 2 参数错误或会话名有歧义；
  - 3 等待超时；
  - 4 内存不足，见 A-26；
  - 5 模型、会话或尝试不存在，或者没有指定模型而当前也没有加载；
  - 6 被沙箱拦截，无法访问本机网络，见 A-33。
  - 出错时，stderr 最后一行是一句人能读懂的原因；`--json` 时，stdout 是 `{"error": {"code", "message"}}`。
- [A-14] 不提供删除命令。
- [A-15] `gen` 的任务一旦提交，stderr 立刻打印一行 `已提交：会话 <id> 尝试 <attempt_id>（中断后可用 lmdesk image wait <id> <attempt_id> 继续等待）`。带 `--no-wait` 时，提交后立即以 0 退出，stdout 输出这个尝试 id（`--json` 时是 `{"session_id", "attempt_id"}`）。
- [A-16] `wait` 只等结果，不提交任何东西：
  - 尝试还在进行：继续等。
  - 尝试已完成：立即输出结果。
  - 尝试失败或被取消：退出码 1，附带原因。
  - 尝试不存在：退出码 5。

## 3. 等待、换模型、提交（命令行内部）

- [A-20] 决策写成纯函数 `decide(op, want_model, state) -> wait|swap|submit|fail`，其中 state 来自 `/api/llm/status` 和 `/api/media/job`。规则如下：

| 台面状态 | `ask` | `image gen` |
|---|---|---|
| 正在加载模型 | wait | wait |
| 媒体任务在跑 | 要的就是当前模型：submit；否则 wait | wait |
| 有对话在进行（`active_chats > 0`） | 要的就是当前模型：submit；否则 wait | wait |
| 界面最近 5 分钟内有过对话（`ui_chat_recent`，A-40） | 要的就是当前模型：submit；否则 wait | submit（由 arbiter 决定，见下方说明） |
| 空闲 | 不是要的模型：swap；然后 submit | submit（由 arbiter 决定，必要时它自己卸掉对话模型） |

  - 说明：生图的 arbiter 若需要卸掉对话模型，而界面最近 5 分钟内有过对话，命令行在提交前改为 wait。理由与换模型相同：不在你聊天的间隙抢走模型。
  - 这个判断由 `decide()` 根据预检接口（A-45）返回的 `release` 里有没有 `kind: "llm"` 来做。`/api/state` 的 `can_start` 只回答「谁占着」，不带 `release`，所以不能用它判断。

- [A-21] 选模型：
  - 有 `--model`：用它。
  - 没有 `--model` 但已加载了模型：用当前加载的那个，不换。
  - 两者都没有：退出码 5，stderr 列出可用模型的 key。
- [A-22] swap 就是调用 `POST /api/llm/load`（带 `origin: "agent"`），再轮询直到 `loaded`。加载过程中出错时，退出码 1，并附带台面给出的原因。
- [A-23] 轮询间隔从 2s 开始，每次 ×1.5，最长 5s。等待期间，stderr 每 15s 打一行，例如「等待中：图片任务进行中（已等 45s）」。
- [A-24] 以下情况都回到等待重新判断，不算失败：
  - 收到 409 `media_busy` 或 `load_in_progress`；
  - 对话时收到「模型不匹配」（`model_mismatch`）、「模型已被换掉」（`evicted`）或「没有加载模型」（`no_model_loaded`）——说明换模型和对话之间被别人插了队。
- [A-25] 中断和超时：
  - 任务还没提交：超时以退出码 3 退出；收到 SIGINT 或 SIGTERM 时，以退出码 3 退出。
  - 任务已经提交：
    - **SIGTERM 或超时：不取消任务**。stderr 重复 A-15 那行续等提示，以退出码 3 退出。任务继续在台面跑，结果落在会话里，之后可以用 `wait` 取回。
    - **SIGINT（用户在终端按 Ctrl-C）：取消任务**。调用 `POST /api/media/cancel`，带上自己的 `job_id`（A-42），然后以退出码 3 退出。
      - 取消返回 `job_not_running`（作业在中断前已结束）时，按会话里这次尝试的状态说明：已完成则写「已中断。这次生成在中断前已经完成，没有取消」并保留续等提示；失败或已取消则写「已中断。这次生成在中断前已经结束，没有成片」。
      - 连不上台面时不说「已取消」，写「已中断，生成可能仍在台面继续」并保留续等提示。
  - SIGKILL 无法捕获，等同于 SIGTERM：任务继续跑，结果在会话里。
- [A-26] 内存不足分两种情况：
  - **生图**：台面要求确认时，退出码 4，stderr 原样转述台面的内存估算文案。带 `--force` 时，把 `force: true` 透传给接口。
  - **加载对话模型**：arbiter 返回 `insufficient_budget`，而且对话模型不能加 force。
    - 加载接口的拒绝里不带 `release`（`LlmRejected` 只有 code 和 message），所以换模型前先调用预检接口（A-45）。
    - 预检拒绝时带有可以释放的项（`release` 不为空，比如正在跑的媒体任务）：等待。
    - 没有可以释放的项（说明这个模型对这台机器太大）：立即以退出码 4 退出，原样转述台面的说明，并注明「对话模型不能强制加载，请换一个更小的模型」。
- [A-27] 图片的结果以**会话里的尝试记录**为准，不依赖媒体任务槽位：
  - 提交后，命令行记下 `session_id` 和 `attempt_id`。
  - 轮询时，`/api/media/job` 仍是这个任务：用它显示进度。
  - 槽位已经换成别的任务，或者已经空了：改为查询 `/api/media-sessions/image/{id}` 里这个尝试的状态，取得最终结果。
  - 会话、尝试、`--from` 都走现有的 `/api/media-sessions/image` 和 `POST /api/media/image`（字段 `session_id`、`base: {attempt_id, strength}`），参数校验由服务端负责。命令行只做格式解析，比如把 `--size` 拆成宽和高。
- [A-28] agent 加载的对话模型，用完后不自动卸载。这和你在界面手动加载模型的行为一致，下次调用也省掉了加载时间。这个模型会一直留着，直到被换掉，或者被媒体任务按现有规则挤掉。这是有意的决定。

## 4. 服务发现、沙箱与版本

- [A-30] 端口取 `LMD_SHELL_PORT`，不合法或没设置时用 8766，与 `desk/__main__.py:runtime_port` 规则一致。
- [A-31] 连接被拒绝（`ECONNREFUSED`，说明台面没开）时：
  - 如果命令行位于某个 app 包内，就执行 `open -gj <该 app>`，然后每 1s 探测一次 `/api/state`，最多 60s。超时以退出码 1 退出，提示「台面未能启动」。
  - 从源码运行（不在 app 包内）时，不自动启动，直接以退出码 1 提示。
- [A-32] 版本号统一取自 `packaging/VERSION`，从 app 包运行时取打包写入的 `bundle_version`。命令行比对自己的版本和 `/api/state` 返回的 `version`（见 A-44）。版本不一致时，stderr 警告一行，继续执行。
- [A-33] 连接时如果出现权限类错误（`EPERM`、`EACCES`，或者沙箱特有的拒绝），说明是被 agent 的沙箱拦了。这时不尝试拉起 app，直接以退出码 6 退出，提示「被沙箱拦截，需要允许访问本机网络（127.0.0.1）」。
  - `open -gj` 因为权限失败时，同样按退出码 6 处理。

## 5. 服务端改动

- [A-40] `LlmService` 增加两项状态，在 `/api/llm/status` 中返回：
  - `active_chats`：正在进行的对话数。
    - `chat` 和 `chat/stream` 开始时加一。
    - 正常结束、出错、客户端断开、生成器被关闭，任何一种情况下都要减一，且只减一次。
  - `ui_chat_recent`：布尔值。表示最近 5 分钟内，有没有不是来自 agent（不带 `origin: "agent"`）的对话请求开始或结束。5 分钟先写死为常量。
- [A-41] 新增 `desk/agent_skill/` 模块，路由如下：
  - `GET /api/agent-skill`：返回每个安装目标的状态，以及命令行链接的状态。
  - `POST /api/agent-skill`，请求体为 `{"targets": [...]}`：表示「最终要装上哪几个」，没列出的就卸载。返回应用后的状态，每一行带各自的结果或错误。
  - `POST /api/agent-skill/check`：运行一次已安装的 `lmdesk status --json`，返回它能否连上台面，以及输出内容（A-67）。
- [A-42] `POST /api/media/cancel` 接受可选的 `job_id`。
  - 带了 `job_id`，但它不是当前正在跑的任务：返回 409 `job_not_running`，不取消任何任务。
  - 不带：保持现在的行为，界面用的就是这种。
- [A-43] `LlmService` 记录当前模型的来源 `loaded_by`，取值为 `"agent"` 或 `"ui"`，依据 `/api/llm/load` 请求里的 `origin` 字段。在 `/api/llm/status` 中返回。
- [A-45] 新增只读预检接口 `GET /api/agent/precheck`，不改变任何状态：
  - `?op=chat&model=KEY`：按 `/api/llm/load` 相同的参数（模型 config、权重大小）调用 `arbiter.can_start_heavy("llm", …)`；
  - `?op=image&width=W&height=H&steps=N`：按 `start_image_job` 相同的参数调用 `arbiter.can_start_heavy("image", …, key="qwen-image")`；
  - 原样返回 `{ok, reason, release, memory_warning}`。模型不存在时返回 404 `model_not_found`。
- [A-44] `/api/state` 增加 `version` 字段，取值规则同 A-32。现在 `/api/state` 只有 `holder`、`holders`、`media_busy`、`can_start` 这几个字段，没有版本信息。

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
- **实测（2026-10-16，codex-cli 0.160.1）**：不读 ~/.codex/skills（本机 Orca 把 CODEX_HOME 指向别处，探针放在 ~/.codex/skills 没被列出；放到 ~/.agents/skills 对照则被列出），codex 行用 ~/.agents/skills，并显示「同时对 pi、DeepSeek Harness 生效」。~/.codex/skills 只有 CODEX_HOME 恰好是 ~/.codex 时才会被读，不可靠。
  - 依据：`~/.agents/skills` 会同时被 Codex、pi、DeepSeek Harness 读取（Codex 官方文档、pi 1.2.0 源码、dsh `dsh-skill-filesystem` 源码），所以默认不用它，以保证每个 agent 能单独勾选。
- [A-52] 命令行链接 `~/.local/bin/lmdesk` 不单独设勾选框。至少装了一个 agent 时自动建立；全部卸载时自动移除。
  - 它的状态同样按 A-53 判定。
  - 被占用（`occupied`）时，只在这一行提示，不影响 skill 的安装。skill 里本来就写了找不到命令时的后备路径。
- [A-53] 每个位置的状态只有以下几种：
  - `installed`：指向当前 app 或仓库的 skill（命令行链接则是指向当前的 `lmdesk`）。
  - `absent`：没有安装。
  - `stale`：是一个软链接，目标是某个 LocalModelDesk 的 skill 路径（以 `agent_skill/bundled/local-model-desk` 结尾；命令行链接以 `Contents/Resources/bin/lmdesk` 或 `scripts/lmdesk` 结尾），但不是当前这个，或者目标已经不存在。
  - `occupied`：那个位置存在，但不是指向台面的链接。
  - `error`：没有写权限等，附带原因。
- [A-54] 安装：
  - `absent` 或 `stale` 的位置，创建或替换为指向当前的链接，必要时先创建上级目录。
  - `occupied` 的位置不碰，这一行报错。其余行照常进行。
- [A-55] 卸载只删除 `installed` 或 `stale` 的链接，绝不删除真实的文件或目录，也不删除指向别处的链接。
- [A-56] 台面不会自己安装任何一项。只有用户在设置页点「应用」才会写入。
- [A-57] `scripts/uninstall-app.sh` 卸载 app 时，同时清理 A-50、A-52 中 `installed` 或 `stale` 的链接，规则同 A-55，并且支持 `--dry-run`。
  - 直接把 app 拖进废纸篓的情况，链接会留下并失效。失效的 skill 链接会被 agent 跳过（pi 已从源码确认），不会报错。这种情况可以接受。

## 7. 设置页「本机 agent」区域

- [A-60] 位于设置页「对外 API」之后。按钮层级、卡片列表样式沿用现有视觉基线。
- [A-61] 结构：
  - 标题，加一句说明：「让选中的 agent 通过 lmdesk 命令使用本机模型（对话、生图、图片会话）」。
  - 四行勾选项：名称、检测提示（已检测到 / 未检测到）、状态文字。
  - 一个主按钮「应用」。
  - 一行命令行链接状态。
  - 一个次级按钮「检查」，以及一句可复制的试用语（A-67）。
- [A-62] 打开页面时，勾选状态是：`installed` 或 `stale` 的行勾选，其余不勾选。`stale` 行的状态文字是「指向旧位置，点应用更新」。
- [A-63] 「未检测到」的行也可以勾选。检测结果只是提示。
- [A-64] 「应用」按钮是否可点，按「应用后会不会有变化」判断：
  - 有勾选的行不是 `installed`（包括 `stale`），或者有不勾选的行是 `installed` 或 `stale`：可以点。
  - 否则不可点。
  - 应用后，用接口返回的结果刷新各行；失败的行显示原因。
- [A-65] 矮窗口和窄窗口下，没有横向滚动，内容不溢出。
- [A-66] 聊天页：`/api/llm/status` 的 `loaded_by` 变成 `"agent"`，而且模型和页面上次看到的不一样时，在聊天区域上方显示一条可关闭的提示「模型已被 agent 切换为 X」。
- [A-67] 闭环验证：
  - 「检查」按钮调用 A-41 的 check 接口，显示「lmdesk 能连上台面 ✓」或者失败原因。
  - 区域底部有一句「在 agent 里试试：用本地模型把这句话翻成英文」，附一个复制按钮。

## 8. 更新与失效

- [A-70] 因为装的是软链接，app 被覆盖更新后，skill 和命令行自动就是新内容，两者版本始终一致。SKILL.md 里不写版本号。
- [A-71] 台面启动时计算一次 A-53 的状态，结果放进 `/api/agent-skill`。
  - 只要有一行是 `stale`，菜单栏图标就显示提示点：Swift 侧 `StatusPoller` 读取这个状态，`StatusItemController` 负责显示。
  - 设置页对应行显示「指向旧位置」或「已失效」。
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
  - **耗时和中断**：
    - 命令会自行排队等待，可能要几分钟，工具超时尽量设长（至少 10 分钟），中途不要自己重试。
    - 生图如果被工具超时打断，用 stderr 里给出的 `lmdesk image wait <会话> <尝试id>` 接着等，**不要重新 gen**。
    - 能后台运行命令的 agent，也可以先 `gen --no-wait` 提交，再用 `wait` 取结果。
  - **各退出码的处理**：
    - 3：告知用户台面一直忙；如果是生图，可以稍后用 `wait` 取结果。
    - 4：生图的话，先问用户，同意后加 `--force`；对话模型的话，告知用户内存不够，建议换小一点的模型。
    - 5：先用 `models` 或 `image sessions`、`image show` 查清楚。
    - 6：被沙箱拦截了，请求提升权限，或者告诉用户需要放行本机网络。具体放行方法按 A-T9 实测结果写进 skill。
  - **素材管理**：
    - 生图前先 `image sessions`，有合适的会话就接着用，没有就按用途新建并起有意义的名字；
    - 在满意的那张上改用 `--from`；
    - 用 `--out` 放进项目；
    - 不能删除会话，需要删就请用户在台面里删。
  - **对话**：`ask` 是一次性调用，上下文用 `--file` 或 stdin 传入。
  - 两到三个典型示例。

## 10. 打包

- [A-90] `scripts/build-app.sh` 要生成 `Contents/Resources/bin/lmdesk`（可执行），skill 随 `desk/` 进入 app 包。
- [A-91] 在 dist 版本的 app 中，`Contents/Resources/bin/lmdesk status --json` 能在台面运行时返回成功。

## 11. 测试

- [A-T1] 测 `decide()` 的单元测试，按 A-20 表格逐格覆盖，包括 `ui_chat_recent` 和生图需要卸掉对话模型的情况，还有 A-24 的回到等待、A-26 的两种内存不足。退避节奏和超时用假时钟测试。
- [A-T2] 命令行集成测试：用 `desk/testing/harness.py` 启动带假模型的台面，再在子进程里运行命令行。要覆盖：
  - `ask` 的三种情况：未加载、已加载、需要换模型；
  - 换模型后被别人插队，回到等待；
  - `image new/gen/wait/show/rename`，以及 `--from`、`--out`、`--json`、`--no-wait`；
  - 409 后重试成功；
  - 生图内存不足返回 4，加 `--force` 后成功；
  - 对话模型内存不足、没有可以释放的项时，立即返回 4；
  - SIGTERM 时不取消任务，之后 `wait` 能拿到结果；
  - SIGINT 时只取消自己的任务；
  - 轮询期间槽位被别的任务占用，仍然能从会话里拿到结果；
  - 版本不一致只警告；
  - 会话名有歧义时返回 2；
  - 模拟权限错误时返回 6。
  - 测试环境（`launch_test_harness`）已经按正式环境装配了按内存预算调度的 arbiter，并存规则可以直接在其中测试。新增的路由要同时挂进 `desk/testing/harness.py`，`tests/test_e2e_harness_assembly.py` 会核对两边的路由表一致。
- [A-T3] 服务端单元测试：
  - `active_chats` 在正常结束、出错、流被中途关闭这几种情况下都只减一次；
  - `ui_chat_recent` 不受 agent 对话影响，5 分钟后变回 false（用假时钟）；
  - `loaded_by` 跟随 load 请求的 `origin`；
  - 带 `job_id` 的取消：id 不是当前任务时返回 409，且不影响当前任务。
- [A-T4] 安装模块的单元测试：在临时 HOME 下覆盖 A-50 至 A-57 的全部状态和动作，包括命令行链接被占用的情况、卸载脚本的 `--dry-run`，确认不会删除真实文件或目录。
- [A-T5] 设置页的真实浏览器 e2e（`tests/e2e`）：
  - 勾选、应用、状态刷新；
  - `stale` 行勾选、应用按钮能否点（A-64）；
  - 异常行提示、检查按钮、复制试用语；
  - 聊天页的切换提示（A-66）；
  - 矮窗口和窄窗口布局。
- [A-T6] SKILL.md 格式检查（A-80）。
- [A-T7] 打包检查（A-90、A-91）。
- [A-T8] Swift 侧：`stale` 状态能让菜单栏显示提示点（沿用 `macos/harness` 的现有测法）。
- [A-T9] 手动验收：
  - 在 Claude Code、Codex、pi、DeepSeek Harness 中，各说一句「用本地模型把这段翻成英文」和「本地生成一张图放进 ./tmp」，四者都会自己调用 `lmdesk`。
  - Codex 和 DeepSeek Harness 要在默认沙箱设置下实测：能否连上 127.0.0.1，被拦时是否得到退出码 6，以及具体的放行方法。放行方法写回 SKILL.md。
  - 在 Claude Code 中用一个超过工具超时的生图，验证「被打断 → `wait` 取回」这条链路。
  - 结果记入验收记录。
