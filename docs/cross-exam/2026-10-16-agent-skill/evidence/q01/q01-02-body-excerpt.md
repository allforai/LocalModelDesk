/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:1 ---
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:2 name: local-model-desk
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:3 description: 本机的本地模型台面（LocalModelDesk）。需要用本地大模型做翻译、总结、改写、批量处理文本等离线或隐私敏感的任务，或者用本地模型生成、迭代图片、视频、音乐素材并按会话管理时使用。用户提到「本地模型」「台面」「本地生图」「本地生成视频」「本地生成音乐」「用本机模型」时使用。通过 lmdesk 命令调用。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:4 ---
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:5 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:6 # 本机模型台面（lmdesk）
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:7 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:8 台面是这台 Mac 上的本地模型应用。`lmdesk` 命令让你使用它的对话模型、图片模型、视频模型和音乐模型。台面会自己排队、按需加载模型。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:9 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:10 ## 调用
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:11 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:12 - 命令是 `lmdesk`。找不到时用 `~/.local/bin/lmdesk`。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:13 - 加 `--json` 时，stdout 是单个 JSON 对象；进度和提示都在 stderr。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:14 - **命令会自己排队等待**，生图或换模型可能要几分钟。把工具超时设得尽量长（至少 10 分钟），中途不要自己重试。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:15 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:16 ## 对话（一次性）
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:17 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:18 ```bash
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:19 lmdesk models                                   # 本机有哪些对话模型、哪个已加载
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:20 lmdesk ask "把下面这段翻成英文" --model KEY --file draft.md
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:21 cat notes.txt | lmdesk ask "总结成三条要点"
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:22 ```
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:23 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:24 - `ask` 不保留上下文。需要上下文时，用 `--file` 或 stdin 传入。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:25 - 不写 `--model` 时，用台面当前已加载的模型。如果当前什么都没加载，会得到退出码 5，这时先运行 `lmdesk models`，按任务挑一个模型，再加 `--model` 重试。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:26 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:27 ## 生图与素材管理
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:28 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:29 ```bash
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:30 lmdesk image sessions                            # 先看有没有合适的会话
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:31 lmdesk image new "首页 banner"                   # 没有就按用途新建，起有意义的名字
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:32 lmdesk image gen "首页 banner" "极简风格的山景插画" --size 1344x768 --out ./assets/hero.png
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:33 lmdesk image show "首页 banner"                  # 历史尝试：id、提示词、文件路径
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:34 lmdesk image gen "首页 banner" "改成黄昏色调" --from <尝试id> --strength 0.6 --out ./assets/hero.png
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:35 lmdesk image rename "首页 banner" "首页大图"
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:36 ```
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:37 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:38 - 会话可以用名字或 id 指定。同名的有多个时，改用 id。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:39 - 在满意的那张上继续改，用 `--from <尝试id>`；用 `--out` 把图放进项目。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:40 - 不能删除会话。需要删的话，请用户在台面里删。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:41 - 生图被你的工具超时打断时，stderr 里有一行 `lmdesk image wait <会话> <尝试id>`，**用它接着等，不要重新 gen**。生成会在台面继续进行。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:42 - 能后台运行命令时，也可以先用 `lmdesk image gen … --no-wait` 提交，再用 `lmdesk image wait <会话> <尝试id>` 取结果。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:43 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:44 ## 视频
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:45 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:46 ```bash
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:47 lmdesk video sessions
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:48 lmdesk video new "产品演示"
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:49 lmdesk video gen "产品演示" "湖面上的落日，微风吹起涟漪" --size 768x448 --frames 124 --no-wait
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:50 lmdesk video wait "产品演示" <尝试id> --out ./assets/sunset.mp4
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:51 lmdesk video show "产品演示"
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:52 ```
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:53 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:54 - **视频一律用 `gen --no-wait` 提交，再用 `lmdesk video wait <会话> <尝试id>` 取结果**，生成往往要几分钟到几十分钟。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:55 - `--frames` 只能取 49、73、124、192、243、362（约 2、3、5、8、10、15 秒），默认 124。`--size` 默认 768x448。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:56 - 先生图、再用图片做首帧：
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:57   1. `lmdesk image gen "封面" "雪山日出" --size 1344x768`，记下尝试 id；
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:58   2. `lmdesk video gen "产品演示" "镜头缓缓推近" --first-frame image:封面:<图片尝试id> --no-wait`。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:59   - `--first-frame` 也可以是本地文件路径（png、jpg、jpeg、webp，不超过 32 MB）。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:60 - 接着某一段往下生成：`--continue <尝试id>`（不能和 `--first-frame` 同用）。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:61 - 把几段合成成片：`lmdesk video join "产品演示" <尝试id> <尝试id> [...]`，至少两段。续写后 `wait` 输出的是到当前这段为止的完整成片。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:62 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:63 ## 音乐
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:64 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:65 ```bash
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:66 lmdesk music sessions
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:67 lmdesk music new "片头曲"
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:68 lmdesk music gen "片头曲" "温柔的民谣，木吉他伴奏，女声轻唱" --lyrics-file lyrics.txt --duration 60 --out ./assets/intro.wav
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:69 lmdesk music gen "片头曲" "电子氛围乐" --lyrics "[instrumental]" --continue <尝试id>
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:70 lmdesk music join "片头曲" <尝试id> <尝试id>
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:71 ```
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:72 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:73 - **音乐必须有歌词**：`--lyrics` 和 `--lyrics-file` 二选一，不能都不给，也不能都给，否则退出码 2。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:74 - 纯音乐：歌词只写 `[instrumental]`。段落用 `[verse]`、`[chorus]` 这样的方括号标记。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:75 - 成品时长由模型按歌词决定，常短于 `--duration`（默认 60）。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:76 - `--continue <尝试id>` 接着写下一段，`music join` 合成多段，规则与视频相同。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:77 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:78 ## 退出码
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:79 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:80 - 退出码 0：成功。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:81 - 退出码 1：其他错误，原因在 stderr 最后一行。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:82 - 退出码 2：参数错误或会话名有歧义。按提示修正。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:83 - 退出码 3：等待超时，台面一直在忙。告诉用户。如果是生图、视频或音乐，稍后可以用对应的 `wait` 命令（如 `lmdesk video wait`）取结果。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:84 - 退出码 4：内存不足。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:85   - 生图、视频、音乐：先问用户，用户同意后加 `--force` 重试。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:86   - 对话模型：不能强制加载。告诉用户，建议换一个更小的模型。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:87 - 退出码 5：模型、会话或尝试不存在。用 `lmdesk models`、`lmdesk image sessions`、`lmdesk video sessions`、`lmdesk music sessions`、`lmdesk image show` 查清楚再调用。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:88 - 退出码 6：被沙箱拦截，访问不了本机网络（127.0.0.1）。请求提升权限，或者告诉用户需要放行本机网络。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:89   - Codex：默认的 workspace-write 沙箱关闭了网络。告诉用户在 `~/.codex/config.toml` 里加上 `[sandbox_workspace_write]` 和 `network_access = true`，或者用 `codex -s workspace-write -c sandbox_workspace_write.network_access=true` 启动。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:90   - Claude Code 开启了沙箱时：请用户把 `127.0.0.1` 加进沙箱的网络白名单。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:91 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:92 ## 例子
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:93 
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:94 1. 用户说「用本地模型把 README 翻成英文」：
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:95    `lmdesk models`，选一个对话模型，然后 `lmdesk ask "翻译成英文，保留 Markdown 格式" --model KEY --file README.md`。
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:96 2. 用户说「本地生成一张 app 图标放到 ./tmp」：
/Users/aa/LocalModelDesk/dist/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk/SKILL.md:97    `lmdesk image sessions`，没有合适的会话就 `lmdesk image new "app 图标"`，然后 `lmdesk image gen "app 图标" "扁平风格的山形图标，蓝色" --size 1024x1024 --out ./tmp/icon.png`。
