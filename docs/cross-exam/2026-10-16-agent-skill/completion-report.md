# 完成度报告 — LocalModelDesk feat/agent-skill：lmdesk 命令行（对话/图片/视频/音乐/join）、本机 agent skill 安装、服务端新接口

需求基准：spec · 共 14 面，盘问 14 面 · 实测 39 问 · 旅程 4 条，盘问 4 条 · 操作面 53 个，裁决触及 46 个
被评构建：3dd22ad98b1892f59c3ed5d40d7baecacf9eb83c-e3b0c44298fc1c14（intake 记录于 2026-10-16T13:54:05+09:00）

## 总览

实证完成：26（运行时 25 · 代码 1 · 台账 0） · 缺口：12 · 跑偏：0 · 无法自证：1
旅程裁决：实证完成：2 · 缺口：1 · 跑偏：0 · 无法自证：1

> 盘问官即交付作者（examiner_is_author）：bias-guard 生效——gap 从严，降级为 low 或 done 需额外独立证据。

> 本 run 取证类子 agent（实测官、枚举官）用 sonnet，用户于 2026-10-16T13:52:00+09:00 确认：「B 成本优先 (推荐)」。裁决与普查仍用会话模型。
> 定靶时盘问官推荐的是选项 B（靶子主要是命令行和接口，用户此前要求子 agent 用 sonnet 控成本；走浏览器的只有设置页）。

取证时间：首问 2026-10-16T15:09:00+09:00 · 末问 2026-10-19T21:27:07+09:00 · 跨 4698 分钟
相邻 runtime 问间隔不足 60 秒，请核对是否真实取证：q05（卸载脚本对 agent 链接实际做了什么（dry-run 与真实运行），真实目录…） → q06（预检对最大对话模型、362 帧视频、240 秒音乐、2048 图片返回什么？命令…）（0 秒）；q06（预检对最大对话模型、362 帧视频、240 秒音乐、2048 图片返回什么？命令…） → q07（预检在未知 op、缺参数、参数非整数、模型不存在时各返回什么？调用前后台面状态有…）（0 秒）；q07（预检在未知 op、缺参数、参数非整数、模型不存在时各返回什么？调用前后台面状态有…） → q03（安装位置已有真实目录、外来链接、真实 lmdesk 文件时，全选安装与全不选卸载…）（0 秒）；q03（安装位置已有真实目录、外来链接、真实 lmdesk 文件时，全选安装与全不选卸载…） → q08（lmdesk 在禁止网络的 macOS 沙箱里运行 status 与 statu…）（0 秒）；q08（lmdesk 在禁止网络的 macOS 沙箱里运行 status 与 statu…） → q09（命令行与台面版本不一致时有没有警告、命令是否继续？LMDESK_FAKE_VER…）（0 秒）；q09（命令行与台面版本不一致时有没有警告、命令是否继续？LMDESK_FAKE_VER…） → q04（先全选安装再只选 pi 时，共享目录 ~/.agents/skills 与 pi…）（0 秒）；q12（没加载模型时不带 --model 的 ask 输出什么？带 --model 加载…） → q17（image new 已存在的名字会怎样？同名会话有两个时 show/rename…）（0 秒）；q17（image new 已存在的名字会怎样？同名会话有两个时 show/rename…） → q23（music gen 在缺歌词、两个歌词参数都给、歌词文件不存在、非 UTF-8、…）（0 秒）；合成与续写成片文件的内容与它们声称的段是什么关系？不同会话的合成文件是否相同？ → q24（用 [instrumental] 生成的音乐有没有人声？时长与 --durati…）（0 秒）

## 规则一致性（规则 ↔ 规则；候选不计为产品缺陷）
来源 6 份 · 规则 150 条 · 比较组 16 个 · 候选 6 条
仅核对本轮材料；语义覆盖、来源完整性与用户确认真实性须核对独立审查记录。
独立审查：/private/tmp/claude-502/-Users-aa-LocalModelDesk/fa6582dc-b056-49e3-a1d5-3b44596f2ffe/tasks/afbfdac5a606dfaad.output · claude-opus-5-5 (session)
- 来源 SRC1：docs/superpowers/specs/2026-10-16-agent-skill-design.md:1-300 @ 3dd22ad（evidence/rules/sources/agent-skill-design.md）
- 来源 SRC2：docs/superpowers/specs/2026-10-16-agent-media-design.md:1-108 @ 3dd22ad（evidence/rules/sources/agent-media-design.md）
- 来源 SRC3：会话 fa6582dc 用户原话逐字摘录（evidence/rules/sources/user-confirmations.md）
- 来源 SRC4：~/.claude/projects/-Users-aa-LocalModelDesk/memory/feedback-hardware-soft-limits.md（用户 2026-09-25 原话）（evidence/rules/sources/user-hardware-soft-limits.md）
- 来源 SRC5：§1b 旅程改写读回，用户 2026-10-16 确认（evidence/rules/sources/journey-oracles.md）
- 来源 SRC6：第 1 轮规则审查（evidence/rules/rev1/review.json）后用户逐条确认（evidence/rules/sources/user-clarifications-rev1.md）
- 比较 RULE-A-scope / RULE-A00c / RULE-U7 / RULE-U14 / RULE-B-scope / RULE-B00a / RULE-RC13 / RULE-B-inherit / RULE-A-nocompat / RULE-B01 / RULE-RC12 / RULE-U13 / RULE-B-tasks：compatible — A-00c 把视频音乐排除出「第一版」，B-scope 属第二期，版本不同不构成同条件矛盾；RC13 与 U14「视频和音乐等其他」把第二期限定为视频音乐，B-00a 的排除项与 A-00c 剩余非目标继续不做，三者一致。B-01 不保留 images.py 与「台面未发布不谈兼容」一致；RC12 已确认 test_image_cli.py 不 import images，与删除 images.py 相容。U13 无可比较的具体行为，只作为来源授权。
- 比较 RULE-A00c-mem / RULE-A26-chat / RULE-A26-image / RULE-A82-exit / RULE-H1 / RULE-H2 / RULE-RC1 / RULE-A00d / RULE-B02 / RULE-BT1 / RULE-AT1：compatible — H1「不新增硬拒绝」与 A-26 对话模型立即退出 4 表面对立；RC1 已把有效规则定为「命令行跟随界面」，其条件「界面可确认后强制加载对话模型」按 A-00c-mem 在本期不成立（界面也没有该软限制），故当前 A-26-chat 与界面同规则、并非新增硬拒绝；条件句不承诺可达，不要求本期补做。生图路径 A-26-image 走确认+--force，与 H1 一致。B-02/B-T1 让 compose 不经 arbiter、不预检，与 H2「仅 ffmpeg 任务跳过内存检查」一致。A-00d 不改 arbiter 规则，与上述均不冲突。
- 比较 RULE-A50 / RULE-A50-codex / RULE-A51 / RULE-A51-result / RULE-A51-basis / RULE-RC2 / RULE-RC3 / RULE-A53 / RULE-U10 / RULE-U11 / RULE-U1 / RULE-U3 / RULE-J2-ctx / RULE-J2-done / RULE-J2-stuck / RULE-A61 / RULE-A63 / RULE-AT4：compatible — A-50 表内 codex 位置（~/.codex/skills）与第 182 行实测结论、第 183 行「默认不用 ~/.agents/skills」三者原本互相对立；RC2、RC3 已明确以 ~/.agents/skills 为准、状态判定按该路径，并接受 Codex 行对 pi、dsh 同时生效（界面注明），因此 A50-codex 与 A51-basis 被覆盖。U11「可多选」：四行仍可独立勾选，Codex 行的连带生效由用户在 RC2 中接受。J2 只装 Claude Code，要求 ~/.agents/skills 下无 local-model-desk，与 codex 行未勾选时 absent 一致；J2 的「卡死：别的 agent 也被装上」不触及 Codex 连带生效（未勾 Codex）。
- 比较 RULE-A52 / RULE-A53 / RULE-A54 / RULE-A55 / RULE-A56 / RULE-A57 / RULE-A62 / RULE-A64 / RULE-A71 / RULE-A72 / RULE-RC4 / RULE-RC5 / RULE-A41 / RULE-AT5 / RULE-AT8 / RULE-U12 / RULE-A70：findings — 命令行链接行与 agent 行共用 A-53 状态，但 A-64 的可点条件只按「勾选行」写，命令行行没有勾选框；A-71 的启动计算与菜单栏提示点、A-41 的 GET 状态、A-62 的打开页面状态都依赖同一份状态，需比较其触发条件与时间点。RC5 覆盖 A-62/A-71 的 stale 文案，A-56/A-72 与 A-52 的「自动建立」不冲突（均在用户点应用时发生）；A-57 是用户自己运行的卸载脚本，不属于「台面自己安装」。
- 比较 RULE-A00b / RULE-U5 / RULE-U6 / RULE-A20 / RULE-A20-note / RULE-A21 / RULE-A22 / RULE-A23 / RULE-A24 / RULE-RC11 / RULE-B02 / RULE-A40 / RULE-A45 / RULE-B30 / RULE-BT3 / RULE-A28 / RULE-AT3 / RULE-AT2：compatible — U5「有任务要队列化」与 A-00b「服务端不加队列」由 U6「skill 通知 agent 等待，等于自行队列」衔接，排队在命令行进程内完成。RC11 规定 A-20 自上而下首条匹配，消除多状态同时成立的歧义；A-20-note 是「界面最近 5 分钟」行内生图列的条件例外，不与首条匹配矛盾。A-21 中无 --model 且未加载时退出 5，先于 A-20「空闲→swap」生效，两者条件互斥。A-22「加载出错退出 1」与 A-24「409 load_in_progress 回到等待」作用于不同响应。B-02 的 compose 规则为新 op 单独定义，不改动 A-20 两列；B-30/B-T3 扩展预检而保持 A-45 的返回结构。A-28 不自动卸载与 A-00c 一致。
- 比较 RULE-A13 / RULE-A15 / RULE-A16 / RULE-A25 / RULE-RC8 / RULE-RC9 / RULE-A42 / RULE-B00c / RULE-B02 / RULE-B01 / RULE-B14 / RULE-B22 / RULE-A82-time / RULE-A82-exit / RULE-B15 / RULE-BT2 / RULE-J1-stuck / RULE-J3-stuck：findings — 退出码 3 在 A-13 写为「等待超时」，A-25 又用于信号中断；RC8 已确认覆盖两者并要求 SKILL.md 区分「已取消/仍在跑」，覆盖 A-82-exit 中只写「一直忙」的处理。A-16 对已取消尝试退出 1 与 A-25 的 SIGINT 退出 3 属不同命令/时点。B-15 视频一律 --no-wait 是对 A-82-time「也可以」的视频专用收紧，并不矛盾。需比较 RC9（join 的 SIGINT 取消自己的合成任务）与 A-42 的取消机制、B-02「compose 不经 arbiter」、B-00c「不改媒体服务生成规则」之间的依赖。
- 比较 RULE-A30 / RULE-A31 / RULE-A32 / RULE-A33 / RULE-A44 / RULE-RC10 / RULE-U4 / RULE-J1-ctx / RULE-J1-done / RULE-A01 / RULE-A02 / RULE-A04 / RULE-A90 / RULE-A91 / RULE-AT7 / RULE-U2 / RULE-A00a：compatible — U4「调用时不需要启动界面」、J1「全程没有弹出台面主窗口」与 A-31 用 open -gj 拉起 app 由 RC10 明确为相容（不弹窗、不抢前台，菜单栏图标可接受）。A-31 与 A-33 的触发条件不同（ECONNREFUSED 与权限类错误）。A-31「源码运行不拉起」与 J1 的 dist 环境不同。A-30 要求「与 runtime_port 规则一致」而 A-01 禁止 import desk 其他模块，可通过在命令行内复写同一规则同时满足。A-32 只警告不阻断，A-44 提供比对字段。
- 比较 RULE-A27 / RULE-B00c / RULE-RC6 / RULE-B10 / RULE-B11 / RULE-B12 / RULE-B13 / RULE-B14 / RULE-B20 / RULE-B21 / RULE-B-vcmd / RULE-B-mcmd / RULE-BT2：compatible — B-00c 与 A-27「命令行只做格式解析」和 B-11/B-12/B-13/B-14/B-20 的命令行侧拒绝表面对立；RC6 明确 B-11 至 B-20 为 B-00c 的例外、不一致时以服务端为准，覆盖面包括 B-14 的「至少两段」。B-10/B-21 的默认值取界面常量，属默认值而非校验，不触及 B-00c。B-T2 的「--frames 50 退出 2」与 B-11 一致。
- 比较 RULE-B12 / RULE-B14 / RULE-B22 / RULE-B31 / RULE-B41 / RULE-J3-ctx / RULE-J3-done / RULE-J3-stuck / RULE-B32 / RULE-B13：findings — 续写（--continue）与合成（join）都产生「完整成片」：B-31 说续写后 wait 输出的 joined_output 已是截至当前段的完整成片，B-14/B-41/J3 又要求再 join。需比较二者在同一条续写链上同时使用时的产出。B-12 的 continue/first-frame 互斥与 J3「第一段首帧引用猫图」相容（首帧只用于第一段）。
- 比较 RULE-B20 / RULE-B21 / RULE-J4-ctx / RULE-J4-done / RULE-J4-stuck / RULE-B41 / RULE-B-mcmd：findings — B-20 强制歌词与 J4「请求不带歌词」靠纯音乐标记衔接，J4 的卡死条件禁止自编歌词，与 B-20 的 [instrumental] 写法一致。J4 的「时长 ≥ 8 秒」依赖 B-21 默认时长或 agent 显式传 --duration，需比较。
- 比较 RULE-A05 / RULE-B-inherit / RULE-A40 / RULE-A43 / RULE-A66 / RULE-B13 / RULE-B14 / RULE-AT3：findings — A-05「一律」带 origin 的请求列举了对话、加载、生图、取消；B-inherit 说 origin: agent 继续适用；第二期新增的改变状态请求（POST /api/media/inputs 上传首帧、POST /api/media/compose 合成、以及第一期已有的 new/rename）是否在「一律」范围内需比较。A-40/A-43/A-66 只依赖对话与加载请求的 origin，二者相容。
- 比较 RULE-A00d / RULE-B00b / RULE-RC7 / RULE-A61 / RULE-A60 / RULE-A65 / RULE-A66 / RULE-A67 / RULE-A80 / RULE-A81 / RULE-B40 / RULE-AT6 / RULE-BT4 / RULE-A-scope：compatible — B-00b「不改界面」与 A-61 的说明文字「对话、生图、图片会话」在第二期会过时；RC7 明确补说明文字不算改界面，覆盖 B-00b 的这一面。A-00d「现有界面的生成和对话交互不改」限定在生成/对话交互，设置页新区域与菜单栏提示点在 A-scope 中显式列入范围，不构成矛盾。A-81 第一期 description 与 B-40 第二期扩展属版本递进，B-40 保留 A-80 的 1024 字符上限。
- 比较 RULE-A14 / RULE-A82-assets / RULE-U8 / RULE-U9 / RULE-A10 / RULE-A11 / RULE-A12 / RULE-A-cmds / RULE-A82-ask / RULE-A82-call / RULE-B32 / RULE-A16 / RULE-A15：compatible — U8 要求把会话管理交给 agent，U9 接受「不给删除、对话不进会话」，A-14、A-82-assets（不能删除，请用户在台面删）与 A-00c 一致。A-11 中 gen/wait --json 字段与 A-15 --no-wait 的 {session_id, attempt_id} 适用于不同参数条件。B-32 只补充 show.prompt 的取值来源，与 A-11 的 show 字段列表相容。
- 比较 RULE-A03 / RULE-A90 / RULE-A70 / RULE-A72 / RULE-A04 / RULE-A82-call / RULE-A52：compatible — A-03/A-90 把 skill 和 bin/lmdesk 放进 app 包，A-70 依赖软链接自动获得新内容，A-72 禁止自动改链接，三者在「多份 app」情形下的结果是链接停在用户上次应用的那份（再由 A-71 提示 stale），不构成矛盾。A-82-call 的后备路径 ~/.local/bin/lmdesk 与 A-52 中 occupied 时「skill 里本来就写了后备路径」互相呼应。
- 比较 RULE-AT9 / RULE-RC7 / RULE-J1-ctx / RULE-J3-ctx / RULE-J4-ctx / RULE-A82-exit / RULE-A33：compatible — A-T9 要求四个 agent 手动验收，RC7 把第二期跨 agent 验收替换为真实模型冒烟；J3、J4 是单一 Claude Code 旅程 oracle，不要求跨 agent，与 RC7 不冲突。A-T9 的沙箱放行实测结果写回 SKILL.md，与 A-82-exit 退出码 6 的写法要求一致。
- 比较 RULE-AT1 / RULE-AT2 / RULE-AT3 / RULE-AT4 / RULE-AT5 / RULE-AT6 / RULE-AT7 / RULE-AT8 / RULE-BT1 / RULE-BT2 / RULE-BT3 / RULE-BT4 / RULE-B-tasks / RULE-A45 / RULE-A41：compatible — 测试规则逐条对应其被测规则，取值一致（A-T3 的 409 与 A-42、B-T3 的 200 结构与 A-45、B-T3 的 400 为新增的参数错误分支，A-45 只规定了 404 model_not_found，没有对非整数参数作出相反规定）。A-T2 要求新增路由同时挂进 harness，与 A-41/A-45/B-30 新增路由相容。

### RC1 · needs_clarification · 已澄清
共同条件：第一期起安装区域；命令行链接 ~/.local/bin/lmdesk 为 stale 或 absent、且至少一个 agent 行为 installed 的同一时刻
第 1 轮澄清 RC4 的提问同时问了「应用是否可点」和「A-71 的『只要有一行是 stale』是否包括命令行链接」，有效规则只回答了前者（命令行链接 stale 时应用可点）。A-52 说命令行链接「状态同样按 A-53 判定」，但 A-71 的菜单栏提示点是否随命令行链接 stale 亮起仍未定；另外 RC4 只说 stale，没说 absent（agent 已装而命令行链接被手动删掉）时应用是否可点——A-52 的「至少装了一个 agent 时自动建立」暗示应用后会有变化，A-64 却只按勾选行判断。
待确认：命令行链接为 stale 时，菜单栏是否也显示提示点？命令行链接为 absent 而 agent 行已 installed 时，「应用」是否也应可点并重建链接？
- RULE-RC4 SRC6:17-17 · release=第一期与第二期 / platform=unknown / role=all / condition=命令行链接 stale
> - 有效规则：命令行链接 stale 也算「应用后有变化」，「应用」可点，点了即修复。
- RULE-A71 SRC1:225-227 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-71] 台面启动时计算一次 A-53 的状态，结果放进 `/api/agent-skill`。
>   - 只要有一行是 `stale`，菜单栏图标就显示提示点：Swift 侧 `StatusPoller` 读取这个状态，`StatusItemController` 负责显示。
>   - 设置页对应行显示「指向旧位置」或「已失效」。
- RULE-A52 SRC1:184-186 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-52] 命令行链接 `~/.local/bin/lmdesk` 不单独设勾选框。至少装了一个 agent 时自动建立；全部卸载时自动移除。
>   - 它的状态同样按 A-53 判定。
>   - 被占用（`occupied`）时，只在这一行提示，不影响 skill 的安装。skill 里本来就写了找不到命令时的后备路径。
- RULE-A64 SRC1:212-215 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-64] 「应用」按钮是否可点，按「应用后会不会有变化」判断：
>   - 有勾选的行不是 `installed`（包括 `stale`），或者有不勾选的行是 `installed` 或 `stale`：可以点。
>   - 否则不可点。
>   - 应用后，用接口返回的结果刷新各行；失败的行显示原因。
- RULE-AT8 SRC1:295-295 · release=第一期（第一版：对话+图片+安装） / platform=macOS Swift / role=all / condition=all
> - [A-T8] Swift 侧：`stale` 状态能让菜单栏显示提示点（沿用 `macos/harness` 的现有测法）。
用户于 2026-10-19T18:28:48+09:00：全部按推荐 (推荐)
有效规则：命令行链接 stale 也点亮菜单栏提示点；命令行链接 absent 而有 agent 已安装时也算有变化，「应用」可点并补建链接。

### RC2 · needs_clarification · 已澄清
共同条件：第一期；台面运行期间链接状态或「已检测到」依据在台面外被改变（用户手动删改链接、安装新 agent、另一份 app 写了链接）
A-71 写「台面启动时计算一次 A-53 的状态，结果放进 /api/agent-skill」，A-41 写 GET /api/agent-skill「返回每个安装目标的状态」，A-62 按「打开页面时」的状态决定勾选。若 GET 只返回启动时那一次的结果，运行中外部改变后页面勾选、A-64 的可点判断和菜单栏提示点都会基于过期状态；若 GET 每次重算，则「启动时计算一次」只约束菜单栏提示点。两种读法会影响 A-62/A-64 的行为。
待确认：「启动时计算一次」只针对菜单栏提示点，还是 GET /api/agent-skill 与设置页也只用启动时的结果？应用后（A-64 刷新）菜单栏提示点是否随之更新？
- RULE-A71 SRC1:225-227 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-71] 台面启动时计算一次 A-53 的状态，结果放进 `/api/agent-skill`。
>   - 只要有一行是 `stale`，菜单栏图标就显示提示点：Swift 侧 `StatusPoller` 读取这个状态，`StatusItemController` 负责显示。
>   - 设置页对应行显示「指向旧位置」或「已失效」。
- RULE-A41 SRC1:153-156 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-41] 新增 `desk/agent_skill/` 模块，路由如下：
>   - `GET /api/agent-skill`：返回每个安装目标的状态，以及命令行链接的状态。
>   - `POST /api/agent-skill`，请求体为 `{"targets": [...]}`：表示「最终要装上哪几个」，没列出的就卸载。返回应用后的状态，每一行带各自的结果或错误。
>   - `POST /api/agent-skill/check`：运行一次已安装的 `lmdesk status --json`，返回它能否连上台面，以及输出内容（A-67）。
- RULE-A62 SRC1:210-210 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-62] 打开页面时，勾选状态是：`installed` 或 `stale` 的行勾选，其余不勾选。`stale` 行的状态文字是「指向旧位置，点应用更新」。
- RULE-A64 SRC1:212-215 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-64] 「应用」按钮是否可点，按「应用后会不会有变化」判断：
>   - 有勾选的行不是 `installed`（包括 `stale`），或者有不勾选的行是 `installed` 或 `stale`：可以点。
>   - 否则不可点。
>   - 应用后，用接口返回的结果刷新各行；失败的行显示原因。
用户于 2026-10-19T18:28:48+09:00：全部按推荐 (推荐)
有效规则：设置页（GET /api/agent-skill）与「应用」判断每次读实时状态；点「应用」后菜单栏提示点随之更新。

### RC3 · scope_dependency · 已澄清
共同条件：第二期；lmdesk video/music join 已提交合成任务后收到 SIGINT
RC9 要求 join 的 SIGINT 只取消自己提交的合成任务；A-25/A-42 的取消机制是 POST /api/media/cancel 带自己的 job_id，A-42 规定 job_id 不是「当前正在跑的任务」时返回 409 且不取消。B-02 说 compose 只用 ffmpeg、不经 arbiter（区别于媒体任务槽位），B-00c 又禁止改媒体服务的生成规则。现有材料没有说明合成任务是否占用 /api/media/cancel 所认的「当前任务」，若不是，RC9 的实现就要扩展取消接口或合成任务管理，这是否落在 B-00c 允许范围内未定。
待确认：如果现有合成任务不能通过 /api/media/cancel + job_id 取消，是否允许为满足 RC9 而改动服务端取消/合成任务逻辑（视为 B-00c 的例外）？还是在不能取消时 join 的 SIGINT 退化为「只退出 3、任务继续」？
- RULE-RC9 SRC6:37-37 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - 有效规则：join 与 gen 相同：SIGINT 只取消自己提交的合成任务。
- RULE-A42 SRC1:157-159 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-42] `POST /api/media/cancel` 接受可选的 `job_id`。
>   - 带了 `job_id`，但它不是当前正在跑的任务：返回 409 `job_not_running`，不取消任何任务。
>   - 不带：保持现在的行为，界面用的就是这种。
- RULE-A25 SRC1:117-122 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-25] 中断和超时：
>   - 任务还没提交：超时以退出码 3 退出；收到 SIGINT 或 SIGTERM 时，以退出码 3 退出。
>   - 任务已经提交：
>     - **SIGTERM 或超时：不取消任务**。stderr 重复 A-15 那行续等提示，以退出码 3 退出。任务继续在台面跑，结果落在会话里，之后可以用 `wait` 取回。
>     - **SIGINT（用户在终端按 Ctrl-C）：取消任务**。调用 `POST /api/media/cancel`，带上自己的 `job_id`（A-42），然后以退出码 3 退出。
>   - SIGKILL 无法捕获，等同于 SIGTERM：任务继续跑，结果在会话里。
- RULE-B02 SRC2:28-32 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-02] `decide()` 的 `op` 取值扩展为 `chat`、`image`、`video`、`music`、`compose`。
>   - `image`、`video`、`music` 走同一套媒体规则（A-20 表格的「图片」那一列）。
>   - `compose` 只用 ffmpeg，不经过 arbiter（见现有 `start_compose_job`），所以它的规则是：
>     - 媒体任务在跑：等待；
>     - 其余情况：直接提交，不需要预检。
- RULE-B00c SRC2:21-21 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-00c] 不改媒体服务的生成规则。参数校验仍由服务端负责，命令行只做格式解析。
用户于 2026-10-19T18:28:48+09:00：全部按推荐 (推荐)
有效规则：允许为 join 的 SIGINT 取消改动服务端取消接口；B-00c 只约束生成规则，不约束取消。

### RC4 · needs_clarification · 已澄清
共同条件：第二期；同一视频会话中第 2 段用 --continue 续写第 1 段，随后对这两段执行 video join
B-31 说续写后 wait 输出的 joined_output「就是到当前这一段为止的完整成片」；B-41 要求 SKILL.md 教「用 --continue 续写，再用 join 合成成片」；J3 要求最终 mp4 时长大于任一单段且会话里有合成记录。若 join 拼接各段的 joined_output，续写链会出现重复内容；若拼接各段的 output，则 join 结果与第 2 段的 joined_output 相同，续写后再 join 是否必要不明确。两条规则在同一链上的组合效果没有定义。
待确认：对一条 --continue 续写链，SKILL.md 应教 agent 直接取最后一段的 joined_output，还是一定再 join？join 的 parts 按各段 output（单段）拼接吗？J3 的「合成记录」是否要求必须走 join？
- RULE-B31 SRC2:74-74 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-31] `wait` 和 `gen` 的输出路径：有 `joined_output` 时用它（续写后，这就是到当前这一段为止的完整成片），否则用 `output`。这条规则已经存在于 `_attempt_view`，三种媒体统一沿用。
- RULE-B14 SRC2:52-52 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-14] `video join`：调用 `POST /api/media/compose`，请求体为 `{kind: "video", session_id, parts: [尝试id…]}`，至少两段，不足两段以退出码 2 拒绝。合成会在会话里产生一条 `op: "compose"` 的尝试，然后按 A-27 的规则等待这条尝试并输出成片路径。
- RULE-B41 SRC2:80-85 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-41] 正文增加视频、音乐两节，必须包含：
>   - 视频一律用 `--no-wait` 加 `wait`；
>   - 先生图、再用 `--first-frame image:<会话>:<尝试>` 生成视频的串联示例；
>   - 用 `--continue` 续写，再用 `join` 合成成片；
>   - 音乐必须有歌词，以及纯音乐的写法；
>   - 退出码 5 那条补上 `lmdesk video sessions` 和 `lmdesk music sessions`。
- RULE-J3-done SRC5:32-34 · release=第二期（视频与音乐） / platform=unknown / role=Claude Code 用户 / condition=all
> - 做成：项目里有 mp4，时长大于任一单段
> - 做成：台面视频会话里有合成记录
> - 做成：第一段首帧引用「猫」会话里的图
- RULE-B12 SRC2:48-48 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-12] `--continue <尝试id>`：接着这一段往下生成。对应接口字段 `continues`。与 `--first-frame` 同时使用时，以退出码 2 拒绝。
用户于 2026-10-19T18:28:48+09:00：全部按推荐 (推荐)
有效规则：join 用于按指定顺序合成任意几段；续写链直接用 wait 的 joined_output 即可。J3 维持用户确认的 oracle（须有合成记录）。

### RC5 · needs_clarification · 已澄清
共同条件：第二期；agent 用 lmdesk music gen 生成纯音乐且请求未说明时长
J4 要求音频时长 ≥ 8 秒，B-21 只规定 --duration 默认值取界面时长输入框的 value，材料里没有这个值；B-41 也未要求 SKILL.md 指导 agent 设置时长。如果界面默认值小于 8 秒，按 B-21 正确实现的命令仍会不满足 J4。
待确认：J4 的「≥ 8 秒」是以界面默认时长必然 ≥ 8 秒为前提，还是要求 SKILL.md 指导 agent 在纯音乐请求中显式给 --duration？
- RULE-J4-done SRC5:43-44 · release=第二期（视频与音乐） / platform=unknown / role=Claude Code 用户 / condition=all
> - 做成：得到非空音频文件，时长 ≥ 8 秒
> - 做成：台面音乐会话里有对应生成记录，歌词为纯音乐标记
- RULE-B21 SRC2:64-64 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-21] `--duration` 的默认值与界面一致，从 `desk/static/index.html` 音乐页时长输入框的 `value` 读出。
- RULE-B20 SRC2:63-63 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-20] Music 3 必须有歌词。`--lyrics` 和 `--lyrics-file` 必须给一个，两个都没给、或者两个都给了，以退出码 2 拒绝。纯音乐的写法在 SKILL.md 里说明，按 Music 3 的歌词标记约定写，例如只写 `[instrumental]`；具体写法以 `desk/static/js/panes/music.js` 和音乐会话设计里的约定为准。
用户于 2026-10-19T18:28:48+09:00：全部按推荐 (推荐)
有效规则：J4 的 ≥8 秒只是旅程验收线，不要求 SKILL.md 专门指导 --duration。

### RC6 · exception_ambiguity · 已澄清
共同条件：第一期与第二期；命令行发出的 image/video/music new、rename，POST /api/media/inputs 上传首帧，POST /api/media/compose 合成
A-05 写「会改变状态的请求……一律在请求体里带上 origin: agent」，括号只列了对话、加载、生图、取消；B-inherit 说 origin: agent 继续适用，但 B-13 的上传和 B-14 的合成请求体只列了 {name, data} 和 {kind, session_id, parts}，没有 origin。括号是穷举还是举例不明。
待确认：A-05 的「一律」是否覆盖新建/改名会话、首帧上传和 join 合成请求（请求体都要带 origin: agent）？还是只限括号里的四类？
- RULE-A05 SRC1:52-52 · release=第一期（第一版：对话+图片+安装） / platform=unknown / role=all / condition=all
> - [A-05] 命令行发出的会改变状态的请求（对话、加载、生图、取消），一律在请求体里带上 `"origin": "agent"`。服务端靠这个字段区分是 agent 还是界面发起的（A-40、A-43）。
- RULE-B-inherit SRC2:7-7 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> 每条 **[B-xx]** 可写成测试断言。第一期的 A-xx 规则全部继续适用，包括退出码、排队等待、续等、`origin: agent`。
- RULE-B13 SRC2:49-51 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-13] `--first-frame` 两种写法：
>   - 本地文件路径：先 `POST /api/media/inputs`，请求体为 `{name, data: base64}`，拿到素材 id，再以 `mode: "image", first_frame: <id>` 提交。文件不存在、扩展名不是 png、jpg、jpeg、webp，或超过 32 MB 时，以退出码 2 拒绝。
>   - `image:<图片会话>:<尝试id>`：引用图片会话里的某次尝试，`<图片会话>` 可以填名字或 id（规则同 A-10）。以 `mode: "image", refs: {"first_frame": {"kind": "image", "session_id", "attempt_id"}}` 提交。
- RULE-B14 SRC2:52-52 · release=第二期（视频与音乐） / platform=unknown / role=all / condition=all
> - [B-14] `video join`：调用 `POST /api/media/compose`，请求体为 `{kind: "video", session_id, parts: [尝试id…]}`，至少两段，不足两段以退出码 2 拒绝。合成会在会话里产生一条 `op: "compose"` 的尝试，然后按 A-27 的规则等待这条尝试并输出成片路径。
用户于 2026-10-19T18:28:48+09:00：全部按推荐 (推荐)
有效规则：A-05 覆盖命令行发出的全部会改变状态的请求（含新建/改名会话、上传首帧、join）；服务端只在需要区分来源处读 origin。

## 需求覆盖（基准 79 条，有裁决 60 条，无裁决 19 条）
- A-00b 服务端不加任务队列。排队等待全部在命令行进程内完成（§3）。 — 实证完成（两个、三个 lmdesk image gen 同时提交：是否都成功、按什么顺序、有没有重复生成？）
- A-00d 不改 arbiter 的批准、拒绝规则。现有界面的生成和对话交互不改，只在聊天页加一条切换提示（A-66）。 — 缺口（界面 1 分钟内刚用模型 A 对话，agent 用模型 B 问答：agent 等多久？界面对话有没有被打断？） · 缺口（从 error/evicted、界面加载但未对话、界面加载且刚对话三种起点，agent ask --model qwen27 能否得到回答？台面 holder 与 llm 状态是什么？） · 实证完成（界面正在流式对话时 agent 发起生图：界面对话能否完整收完？agent 何时提交？对话模型何时被卸载？）
- A-02 app 包里有 `Contents/Resources/bin/lmdesk`，一个 shell 小脚本，用 `Contents/Resources/python/bin/python3.13` 运行 `-m desk.agent_cli`。它通过自身的真实路径（解析软链接后）定位所在的 app 包。 — 实证完成（覆盖重建 dist 后，已装的 skill 链接与 ~/.local/bin/lmdesk 是否不需重装就指向新构建？）
- A-03 skill 放在 `desk/agent_skill/bundled/local-model-desk/SKILL.md`。打包后位于 `Contents/Resources/desk/agent_skill/bundled/local-model-desk/`，随 `desk/` 一起 rsync。 — 实证完成（覆盖重建 dist 后，已装的 skill 链接与 ~/.local/bin/lmdesk 是否不需重装就指向新构建？）
- A-10 `<会话>` 可以填 id，也可以填名字。名字匹配到多个时，退出码 2，并列出这些候选。 — 实证完成（image new 已存在的名字会怎样？同名会话有两个时 show/rename 的退出码与候选列表？用 id 时呢？）
- A-12 `ask` 的 stdin 不是终端时，读入 stdin 内容，接在问题后面。`--file` 可以重复，每个文件以「文件名 + 内容」的块拼进用户消息。 — 缺口（ask 同时读管道并带多个 --file 时模型实际收到什么？--file 非 UTF-8 或不存在时怎样？） · 缺口（从 error/evicted、界面加载但未对话、界面加载且刚对话三种起点，agent ask --model qwen27 能否得到回答？台面 holder 与 llm 状态是什么？） · 缺口（lmdesk ask 在 stdin 为未关闭的管道（agent 执行器常见）时会阻塞读 stdin、无视 --timeout 永不返回？在 Claude Code/Codex 的命令执行环境下是否发生？）
- A-13 退出码固定为： — 缺口（SKILL.md 对退出码 3 怎么说？超时、SIGINT、SIGTERM、ask 排不上队四种退出码 3 时 stderr 实际打印什么、任务是否继续？） · 实证完成（lmdesk 在禁止网络的 macOS 沙箱里运行 status 与 status --json 时退出码与输出是什么，是否拉起新进程？） · 实证完成（没加载模型时不带 --model 的 ask 输出什么？带 --model 加载后 status 的 loaded_by 是什么？） · 实证完成（image new 已存在的名字会怎样？同名会话有两个时 show/rename 的退出码与候选列表？用 id 时呢？） · 实证完成（music gen 在缺歌词、两个歌词参数都给、歌词文件不存在、非 UTF-8、空文件时各发生什么？） · 缺口（ask 同时读管道并带多个 --file 时模型实际收到什么？--file 非 UTF-8 或不存在时怎样？） · 实证完成（--from 加 --strength 时服务端收到什么参数、新图与原图关系？--out 指向已有文件、已有目录（带或不带斜杠）各发生什么？） · 实证完成（会话里有进行中、已取消、失败的尝试时，image show 与 image wait 各输出什么？） · 缺口（dist 台面没在运行时执行 status --json 与 models：有没有拉起台面、用了多久、有没有窗口或 Dock 图标？）
- A-15 `gen` 的任务一旦提交，stderr 立刻打印一行 `已提交：会话 <id> 尝试 <attempt_id>（中断后可用 lmdesk image wait <id> <attempt_id> 继续等待）`。带 `--no-wait` 时，提交后立即以 0 退出，stdout 输出这个尝试 id（`--json` 时是 `{"session_id", "attempt_id"}`）。 — 实证完成（image gen 等待中分别收到 SIGINT 和 SIGTERM：台面任务是否被取消、退出码？提示的 wait 命令能否取回结果？）
- A-16 `wait` 只等结果，不提交任何东西： — 实证完成（image gen 等待中分别收到 SIGINT 和 SIGTERM：台面任务是否被取消、退出码？提示的 wait 命令能否取回结果？） · 实证完成（会话里有进行中、已取消、失败的尝试时，image show 与 image wait 各输出什么？）
- A-20 决策写成纯函数 `decide(op, want_model, state) -> wait|swap|submit|fail`，其中 state 来自 `/api/llm/status` 和 `/api/media/job`。规则如下： — 缺口（图片生成进行中时发 lmdesk ask：等待期间 stderr 出现什么、间隔多久？生图完成后会不会自动提交？） · 缺口（界面 1 分钟内刚用模型 A 对话，agent 用模型 B 问答：agent 等多久？界面对话有没有被打断？） · 实证完成（两个、三个 lmdesk image gen 同时提交：是否都成功、按什么顺序、有没有重复生成？） · 缺口（从 error/evicted、界面加载但未对话、界面加载且刚对话三种起点，agent ask --model qwen27 能否得到回答？台面 holder 与 llm 状态是什么？） · 实证完成（界面正在流式对话时 agent 发起生图：界面对话能否完整收完？agent 何时提交？对话模型何时被卸载？）
- A-21 选模型： — 实证完成（没加载模型时不带 --model 的 ask 输出什么？带 --model 加载后 status 的 loaded_by 是什么？）
- A-22 swap 就是调用 `POST /api/llm/load`（带 `origin: "agent"`），再轮询直到 `loaded`。加载过程中出错时，退出码 1，并附带台面给出的原因。 — 实证完成（没加载模型时不带 --model 的 ask 输出什么？带 --model 加载后 status 的 loaded_by 是什么？） · 缺口（界面 1 分钟内刚用模型 A 对话，agent 用模型 B 问答：agent 等多久？界面对话有没有被打断？） · 缺口（从 error/evicted、界面加载但未对话、界面加载且刚对话三种起点，agent ask --model qwen27 能否得到回答？台面 holder 与 llm 状态是什么？）
- A-23 轮询间隔从 2s 开始，每次 ×1.5，最长 5s。等待期间，stderr 每 15s 打一行，例如「等待中：图片任务进行中（已等 45s）」。 — 缺口（图片生成进行中时发 lmdesk ask：等待期间 stderr 出现什么、间隔多久？生图完成后会不会自动提交？）
- A-24 以下情况都回到等待重新判断，不算失败： — 缺口（图片生成进行中时发 lmdesk ask：等待期间 stderr 出现什么、间隔多久？生图完成后会不会自动提交？） · 缺口（界面 1 分钟内刚用模型 A 对话，agent 用模型 B 问答：agent 等多久？界面对话有没有被打断？） · 实证完成（两个、三个 lmdesk image gen 同时提交：是否都成功、按什么顺序、有没有重复生成？）
- A-25 中断和超时： — 缺口（SKILL.md 对退出码 3 怎么说？超时、SIGINT、SIGTERM、ask 排不上队四种退出码 3 时 stderr 实际打印什么、任务是否继续？） · 实证完成（image gen 等待中分别收到 SIGINT 和 SIGTERM：台面任务是否被取消、退出码？提示的 wait 命令能否取回结果？） · 缺口（video join 等待中按 Ctrl-C，合成任务有没有被取消？） · 缺口（从 error/evicted、界面加载但未对话、界面加载且刚对话三种起点，agent ask --model qwen27 能否得到回答？台面 holder 与 llm 状态是什么？） · 缺口（lmdesk ask 在 stdin 为未关闭的管道（agent 执行器常见）时会阻塞读 stdin、无视 --timeout 永不返回？在 Claude Code/Codex 的命令执行环境下是否发生？）
- A-27 图片的结果以**会话里的尝试记录**为准，不依赖媒体任务槽位： — 实证完成（--from 加 --strength 时服务端收到什么参数、新图与原图关系？--out 指向已有文件、已有目录（带或不带斜杠）各发生什么？） · 实证完成（会话里有进行中、已取消、失败的尝试时，image show 与 image wait 各输出什么？） · 无法自证（J1 走得通吗？） · 实证完成（J1 那次 claude -p 会话执行了哪些命令？台面是被谁拉起的？台面会话记录与项目文件是否一致？）
- A-31 连接被拒绝（`ECONNREFUSED`，说明台面没开）时： — 缺口（dist 台面没在运行时执行 status --json 与 models：有没有拉起台面、用了多久、有没有窗口或 Dock 图标？） · 无法自证（J1 走得通吗？） · 实证完成（J1 那次 claude -p 会话执行了哪些命令？台面是被谁拉起的？台面会话记录与项目文件是否一致？） · 缺口（q11（实测官 Bash 下 kill 台面后运行 lmdesk：不拉起、退出 1 desk_not_running）与 J1/q43（osascript 退出后经 Claude Code 运行 lmdesk：被拉起）结果相反，触发拉起与否的条件是什么？）
- A-32 版本号统一取自 `packaging/VERSION`，从 app 包运行时取打包写入的 `bundle_version`。命令行比对自己的版本和 `/api/state` 返回的 `version`（见 A-44）。版本不一致时，stderr 警告一行，继续执行。 — 实证完成（命令行与台面版本不一致时有没有警告、命令是否继续？LMDESK_FAKE_VERSION 在 dist 是否生效？）
- A-33 连接时如果出现权限类错误（`EPERM`、`EACCES`，或者沙箱特有的拒绝），说明是被 agent 的沙箱拦了。这时不尝试拉起 app，直接以退出码 6 退出，提示「被沙箱拦截，需要允许访问本机网络（127.0.0.1）」。 — 实证完成（lmdesk 在禁止网络的 macOS 沙箱里运行 status 与 status --json 时退出码与输出是什么，是否拉起新进程？） · 缺口（Codex 默认沙箱下用户让它用本地模型翻译时，Codex 最终对用户说了什么、有没有给出放行方法、照做能否成功？）
- A-40 `LlmService` 增加两项状态，在 `/api/llm/status` 中返回： — 实证完成（没加载模型时不带 --model 的 ask 输出什么？带 --model 加载后 status 的 loaded_by 是什么？） · 实证完成（界面正在流式对话时 agent 发起生图：界面对话能否完整收完？agent 何时提交？对话模型何时被卸载？）
- A-42 `POST /api/media/cancel` 接受可选的 `job_id`。 — 实证完成（image gen 等待中分别收到 SIGINT 和 SIGTERM：台面任务是否被取消、退出码？提示的 wait 命令能否取回结果？） · 缺口（video join 等待中按 Ctrl-C，合成任务有没有被取消？）
- A-43 `LlmService` 记录当前模型的来源 `loaded_by`，取值为 `"agent"` 或 `"ui"`，依据 `/api/llm/load` 请求里的 `origin` 字段。在 `/api/llm/status` 中返回。 — 实证完成（没加载模型时不带 --model 的 ask 输出什么？带 --model 加载后 status 的 loaded_by 是什么？）
- A-45 新增只读预检接口 `GET /api/agent/precheck`，不改变任何状态： — 实证完成（预检对最大对话模型、362 帧视频、240 秒音乐、2048 图片返回什么？命令行读预检的哪些字段，memory_warning 用没用？） · 实证完成（预检在未知 op、缺参数、参数非整数、模型不存在时各返回什么？调用前后台面状态有没有变化？）
- A-44 `/api/state` 增加 `version` 字段，取值规则同 A-32。现在 `/api/state` 只有 `holder`、`holders`、`media_busy`、`can_start` 这几个字段，没有版本信息。 — 实证完成（命令行与台面版本不一致时有没有警告、命令是否继续？LMDESK_FAKE_VERSION 在 dist 是否生效？）
- A-50 安装目标（全部是软链接，指向当前 app 包或仓库里的 skill 目录）： — 实证完成（先全选安装再只选 pi 时，共享目录 ~/.agents/skills 与 pi 自己的目录各是什么？pi 能发现几份 skill、来自哪里？） · 实证完成（J2 走得通吗？）
- A-51 Codex 的目录要在实现的第一步实测：把一个最小 skill 放进 `~/.codex/skills/`，看 Codex 0.160.1 能不能识别（实测完清理掉）。 — 实证完成（先全选安装再只选 pi 时，共享目录 ~/.agents/skills 与 pi 自己的目录各是什么？pi 能发现几份 skill、来自哪里？）
- A-52 命令行链接 `~/.local/bin/lmdesk` 不单独设勾选框。至少装了一个 agent 时自动建立；全部卸载时自动移除。 — 缺口（命令行链接失效或缺失、而 agent 行都已安装时，「应用」能不能点？点了有没有修好？接口与菜单栏状态是什么？） · 实证完成（J2 走得通吗？）
- A-53 每个位置的状态只有以下几种： — 实证完成（安装位置已有真实目录、外来链接、真实 lmdesk 文件时，全选安装与全不选卸载后每个位置是什么、真实文件是否保留？） · 实证完成（skill 链接指向存在的旧位置与不存在的路径时，设置页该行显示什么、应用能否修复、agent_skill_stale 是什么？）
- A-54 安装： — 实证完成（安装位置已有真实目录、外来链接、真实 lmdesk 文件时，全选安装与全不选卸载后每个位置是什么、真实文件是否保留？） · 实证完成（先全选安装再只选 pi 时，共享目录 ~/.agents/skills 与 pi 自己的目录各是什么？pi 能发现几份 skill、来自哪里？） · 实证完成（J2 走得通吗？）
- A-55 卸载只删除 `installed` 或 `stale` 的链接，绝不删除真实的文件或目录，也不删除指向别处的链接。 — 实证完成（卸载脚本对 agent 链接实际做了什么（dry-run 与真实运行），真实目录与外来链接是否保留？） · 实证完成（安装位置已有真实目录、外来链接、真实 lmdesk 文件时，全选安装与全不选卸载后每个位置是什么、真实文件是否保留？） · 实证完成（先全选安装再只选 pi 时，共享目录 ~/.agents/skills 与 pi 自己的目录各是什么？pi 能发现几份 skill、来自哪里？）
- A-56 台面不会自己安装任何一项。只有用户在设置页点「应用」才会写入。 — 实证完成（J2 走得通吗？）
- A-57 `scripts/uninstall-app.sh` 卸载 app 时，同时清理 A-50、A-52 中 `installed` 或 `stale` 的链接，规则同 A-55，并且支持 `--dry-run`。 — 实证完成（卸载脚本对 agent 链接实际做了什么（dry-run 与真实运行），真实目录与外来链接是否保留？）
- A-61 结构： — 缺口（设置页「本机 agent」区块的说明文字写了什么？1280x800、800x600、640x480 下有没有横向滚动或溢出？）
- A-62 打开页面时，勾选状态是：`installed` 或 `stale` 的行勾选，其余不勾选。`stale` 行的状态文字是「指向旧位置，点应用更新」。 — 缺口（命令行链接失效或缺失、而 agent 行都已安装时，「应用」能不能点？点了有没有修好？接口与菜单栏状态是什么？） · 实证完成（skill 链接指向存在的旧位置与不存在的路径时，设置页该行显示什么、应用能否修复、agent_skill_stale 是什么？）
- A-63 「未检测到」的行也可以勾选。检测结果只是提示。 — 实证完成（J2 走得通吗？）
- A-64 「应用」按钮是否可点，按「应用后会不会有变化」判断： — 缺口（命令行链接失效或缺失、而 agent 行都已安装时，「应用」能不能点？点了有没有修好？接口与菜单栏状态是什么？） · 实证完成（skill 链接指向存在的旧位置与不存在的路径时，设置页该行显示什么、应用能否修复、agent_skill_stale 是什么？） · 实证完成（J2 走得通吗？）
- A-65 矮窗口和窄窗口下，没有横向滚动，内容不溢出。 — 缺口（设置页「本机 agent」区块的说明文字写了什么？1280x800、800x600、640x480 下有没有横向滚动或溢出？）
- A-66 聊天页：`/api/llm/status` 的 `loaded_by` 变成 `"agent"`，而且模型和页面上次看到的不一样时，在聊天区域上方显示一条可关闭的提示「模型已被 agent 切换为 X」。 — 实证完成（agent 换模型后聊天页有没有可关闭的切换提示？关掉后再换会不会再出现？界面自己换模型会不会误报？）
- A-70 因为装的是软链接，app 被覆盖更新后，skill 和命令行自动就是新内容，两者版本始终一致。SKILL.md 里不写版本号。 — 实证完成（覆盖重建 dist 后，已装的 skill 链接与 ~/.local/bin/lmdesk 是否不需重装就指向新构建？）
- A-71 台面启动时计算一次 A-53 的状态，结果放进 `/api/agent-skill`。 — 缺口（命令行链接失效或缺失、而 agent 行都已安装时，「应用」能不能点？点了有没有修好？接口与菜单栏状态是什么？） · 实证完成（skill 链接指向存在的旧位置与不存在的路径时，设置页该行显示什么、应用能否修复、agent_skill_stale 是什么？） · 实证完成（skill 链接正常与失效时，菜单栏图标与菜单各是什么样？重启后与应用修复后呢？）
- A-72 不自动改链接。本机可能有好几份 app，自动改会让链接来回跳。 — 实证完成（skill 链接正常与失效时，菜单栏图标与菜单各是什么样？重启后与应用修复后呢？）
- A-80 frontmatter： — 实证完成（打包进 app 的 SKILL.md 实际包含什么，与 A-80/A-81/A-82/B-40/B-41 逐条对账？）
- A-81 description 要写清楚三件事： — 实证完成（打包进 app 的 SKILL.md 实际包含什么，与 A-80/A-81/A-82/B-40/B-41 逐条对账？）
- A-82 正文必须包含： — 实证完成（打包进 app 的 SKILL.md 实际包含什么，与 A-80/A-81/A-82/B-40/B-41 逐条对账？） · 缺口（SKILL.md 对退出码 3 怎么说？超时、SIGINT、SIGTERM、ask 排不上队四种退出码 3 时 stderr 实际打印什么、任务是否继续？） · 缺口（Codex 默认沙箱下用户让它用本地模型翻译时，Codex 最终对用户说了什么、有没有给出放行方法、照做能否成功？）
- A-90 `scripts/build-app.sh` 要生成 `Contents/Resources/bin/lmdesk`（可执行），skill 随 `desk/` 进入 app 包。 — 实证完成（覆盖重建 dist 后，已装的 skill 链接与 ~/.local/bin/lmdesk 是否不需重装就指向新构建？）
- A-91 在 dist 版本的 app 中，`Contents/Resources/bin/lmdesk status --json` 能在台面运行时返回成功。 — 实证完成（覆盖重建 dist 后，已装的 skill 链接与 ~/.local/bin/lmdesk 是否不需重装就指向新构建？）
- A-T9 手动验收： — 缺口（Codex 默认沙箱下用户让它用本地模型翻译时，Codex 最终对用户说了什么、有没有给出放行方法、照做能否成功？） · 无法自证（J1 走得通吗？） · 缺口（J3 走得通吗？） · 实证完成（J4 走得通吗？）
- B-00b 不改界面、不改安装。设置页和 skill 链接都不变。 — 缺口（设置页「本机 agent」区块的说明文字写了什么？1280x800、800x600、640x480 下有没有横向滚动或溢出？）
- B-12 `--continue <尝试id>`：接着这一段往下生成。对应接口字段 `continues`。与 `--first-frame` 同时使用时，以退出码 2 拒绝。 — 实证完成（--first-frame image:猫:<id> 生成的视频首帧是不是那张图？引用无效、缺段、与 --continue 同用时各怎样？）
- B-13 `--first-frame` 两种写法： — 实证完成（--first-frame image:猫:<id> 生成的视频首帧是不是那张图？引用无效、缺段、与 --continue 同用时各怎样？） · 实证完成（用本地文件做首帧时，成功、服务端拒绝、排队中 SIGINT、等待中 SIGINT、文件不合法各情形下 .inputs 里是否留下上传文件？） · 缺口（J3 走得通吗？）
- B-14 `video join`：调用 `POST /api/media/compose`，请求体为 `{kind: "video", session_id, parts: [尝试id…]}`，至少两段，不足两段以退出码 2 拒绝。合成会在会话里产生一条 `op: "compose"` 的尝试，然后按 A-27 的规则等待这条尝试并输出成片路径。 — 缺口（video join 等待中按 Ctrl-C，合成任务有没有被取消？） · 实证完成（视频 --continue 后 wait 输出哪个文件、时长多少？video join 成片时长多少？show 怎么显示合成尝试？） · 实证完成（合成与续写成片文件的内容与它们声称的段是什么关系？不同会话的合成文件是否相同？） · 缺口（J3 走得通吗？）
- B-15 视频生成往往要几分钟到几十分钟。SKILL.md 推荐视频一律用 `gen --no-wait` 提交，再用 `video wait` 取回结果。 — 实证完成（--first-frame image:猫:<id> 生成的视频首帧是不是那张图？引用无效、缺段、与 --continue 同用时各怎样？）
- B-20 Music 3 必须有歌词。`--lyrics` 和 `--lyrics-file` 必须给一个，两个都没给、或者两个都给了，以退出码 2 拒绝。纯音乐的写法在 SKILL.md 里说明，按 Music 3 的歌词标记约定写，例如只写 `[instrumental]`；具体写法以 `desk/static/js/panes/music.js` 和音乐会话设计里的约定为准。 — 实证完成（music gen 在缺歌词、两个歌词参数都给、歌词文件不存在、非 UTF-8、空文件时各发生什么？） · 无法自证（用 [instrumental] 生成的音乐有没有人声？时长与 --duration 差多少？） · 实证完成（J4 走得通吗？）
- B-21 `--duration` 的默认值与界面一致，从 `desk/static/index.html` 音乐页时长输入框的 `value` 读出。 — 无法自证（用 [instrumental] 生成的音乐有没有人声？时长与 --duration 差多少？）
- B-22 `--continue`：对应接口字段 `continues`。`music join` 与 B-14 同理，`kind` 为 `"music"`。 — 实证完成（视频 --continue 后 wait 输出哪个文件、时长多少？video join 成片时长多少？show 怎么显示合成尝试？） · 实证完成（音乐 --continue 后输出哪个文件、时长多少？music join 时长是否等于各段之和？）
- B-30 预检接口 `/api/agent/precheck` 增加两种 op： — 实证完成（预检对最大对话模型、362 帧视频、240 秒音乐、2048 图片返回什么？命令行读预检的哪些字段，memory_warning 用没用？） · 实证完成（预检在未知 op、缺参数、参数非整数、模型不存在时各返回什么？调用前后台面状态有没有变化？）
- B-31 `wait` 和 `gen` 的输出路径：有 `joined_output` 时用它（续写后，这就是到当前这一段为止的完整成片），否则用 `output`。这条规则已经存在于 `_attempt_view`，三种媒体统一沿用。 — 实证完成（视频 --continue 后 wait 输出哪个文件、时长多少？video join 成片时长多少？show 怎么显示合成尝试？） · 实证完成（合成与续写成片文件的内容与它们声称的段是什么关系？不同会话的合成文件是否相同？） · 实证完成（音乐 --continue 后输出哪个文件、时长多少？music join 时长是否等于各段之和？）
- B-32 `show` 的 `prompt` 字段：视频取 `params.prompt`，音乐取 `params.caption`，合成尝试取 `"合成：" + 各段 id`。 — 实证完成（视频 --continue 后 wait 输出哪个文件、时长多少？video join 成片时长多少？show 怎么显示合成尝试？） · 实证完成（音乐 --continue 后输出哪个文件、时长多少？music join 时长是否等于各段之和？）
- B-40 description 加上视频、音乐，并补充触发词「本地生成视频」「本地生成音乐」。总长仍然不超过 1024 字符（A-80）。 — 实证完成（打包进 app 的 SKILL.md 实际包含什么，与 A-80/A-81/A-82/B-40/B-41 逐条对账？）
- B-41 正文增加视频、音乐两节，必须包含： — 实证完成（打包进 app 的 SKILL.md 实际包含什么，与 A-80/A-81/A-82/B-40/B-41 逐条对账？） · 缺口（J3 走得通吗？） · 实证完成（J4 走得通吗？）
- A-00a 不改 gateway（`desk/gateway/`），它仍不加载、不排队。命令行只走台面内部 `/api`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- A-00c 第一版不做以下这些： — 无裁决（面 F11 已盘问但无裁决引用它）
- A-01 命令行是 `desk/agent_cli/` 包，只用标准库，不 import `desk` 的其他模块。入口是 `python -m desk.agent_cli`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- A-04 从源码运行台面时（不是从 app 包运行），安装链接指向仓库里的 skill 目录和 `scripts/lmdesk` 开发脚本，改动立即生效。 — 无裁决（面 F12 已盘问但无裁决引用它）
- A-05 命令行发出的会改变状态的请求（对话、加载、生图、取消），一律在请求体里带上 `"origin": "agent"`。服务端靠这个字段区分是 agent 还是界面发起的（A-40、A-43）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- A-11 stdout 只放最终结果，进度和等待提示都走 stderr。 — 无裁决（面 F2 已盘问但无裁决引用它）
- A-14 不提供删除命令。 — 无裁决（面 F3 已盘问但无裁决引用它）
- A-26 内存不足分两种情况： — 无裁决（面 F1 已盘问但无裁决引用它）
- A-28 agent 加载的对话模型，用完后不自动卸载。这和你在界面手动加载模型的行为一致，下次调用也省掉了加载时间。这个模型会一直留着，直到被换掉，或者被媒体任务按现有规则挤掉。这是有意的决定。 — 无裁决（面 F1 已盘问但无裁决引用它；面 F14 已盘问但无裁决引用它）
- A-30 端口取 `LMD_SHELL_PORT`，不合法或没设置时用 8766，与 `desk/__main__.py:runtime_port` 规则一致。 — 无裁决（面 F8 已盘问但无裁决引用它）
- A-41 新增 `desk/agent_skill/` 模块，路由如下： — 无裁决（面 F9 已盘问但无裁决引用它）
- A-60 位于设置页「对外 API」之后。按钮层级、卡片列表样式沿用现有视觉基线。 — 无裁决（面 F10 已盘问但无裁决引用它）
- A-67 闭环验证： — 无裁决（面 F10 已盘问但无裁决引用它）
- B-00a 不做配乐（soundtrack）、参考视频（reference）、配乐参考（music_ref）、尾帧。这几项素材组合复杂，agent 用得少，以后再加。 — 无裁决（面 F11 已盘问但无裁决引用它）
- B-00c 不改媒体服务的生成规则。参数校验仍由服务端负责，命令行只做格式解析。 — 无裁决（面 F11 已盘问但无裁决引用它）
- B-01 把 `desk/agent_cli/images.py` 泛化为 `desk/agent_cli/media.py`：由一张按 kind 区分的配置表驱动 image、video、music 三种媒体。会话解析、`show`、`wait`、`--out`、提交时挂起信号、SIGINT 取消、SIGTERM 续等提示，三种媒体共用同一份代码。 — 无裁决（面 F4 已盘问但无裁决引用它）
- B-02 `decide()` 的 `op` 取值扩展为 `chat`、`image`、`video`、`music`、`compose`。 — 无裁决（面 F4 已盘问但无裁决引用它）
- B-10 默认值与界面一致： — 无裁决（面 F4 已盘问但无裁决引用它）
- B-11 `--frames` 只接受 `DURATIONS` 里的帧数：49、73、124、192、243、362。其他值以退出码 2 拒绝，并列出可选值和对应的秒数。 — 无裁决（面 F4 已盘问但无裁决引用它）

## 逐面完成度

### 对话：ask/models/status、加载与内存不足、llm 状态字段（F1）— 3 问中 1 问实证通过 · 操作面 7 个，裁决触及 6 个，未触及：S37 LlmService.precheck_load(key) (dry run of the arbiter, no acquire)
- **实证完成** [F1] 没加载模型时不带 --model 的 ask 输出什么？带 --model 加载后 status 的 loaded_by 是什么？ — 不带 --model：退出 5，stderr 列出可用模型；--model superqwen：6.0s 内加载并回答，退出 0；之后 loaded_by=agent、model=superqwen（证据：evidence/q12/）
- **缺口** [G2] [F1] ask 同时读管道并带多个 --file 时模型实际收到什么？--file 非 UTF-8 或不存在时怎样？ — 管道与两个文件按「问题、stdin、--- 文件名 --- 内容」拼进一条用户消息，模型复述一致；--file 指向 GBK 文件时退出 1 并打印 Python traceback（UnicodeDecodeError），不存在的文件退出 2 带中文提示（证据：evidence/q13/）
- **缺口** [G8] [F1] lmdesk ask 在 stdin 为未关闭的管道（agent 执行器常见）时会阻塞读 stdin、无视 --timeout 永不返回？在 Claude Code/Codex 的命令执行环境下是否发生？ — stdin 为 /dev/null 时 1–2s 返回；Claude Code（Bash 工具 stdin 为 /dev/null）与 codex exec 各 15s 正常拿到「白」；stdin 为不关闭的管道时 --timeout 60 无效，120s 外部强杀前无任何输出（证据：evidence/q42/）

### 排队等待与决策（F2）— 1 问中 0 问实证通过 · 操作面 4 个，裁决触及 3 个，未触及：D2 [dead_contract] Waiter.expired / Waiter.elapsed (no callers in desk/)
- **缺口** [G4] [F2] 图片生成进行中时发 lmdesk ask：等待期间 stderr 出现什么、间隔多久？生图完成后会不会自动提交？ — ask 在生图完成后 3.4s 得到回答，退出 0；但 ask 启动后 60.5s 内 stderr 无任何输出，第一行进度在 60s，之后约 15–17s 一行；期间 /api/llm/status 显示 error（证据：evidence/q14/）

### 中断与续等（SIGINT/SIGTERM/超时）（F6）— 2 问中 1 问实证通过 · 操作面 2 个，裁决触及 2 个
- **实证完成** [F6] image gen 等待中分别收到 SIGINT 和 SIGTERM：台面任务是否被取消、退出码？提示的 wait 命令能否取回结果？ — SIGINT：退出 3「已中断并取消这次生成」，台面任务立即 cancelled；SIGTERM：退出 3「已中断，生成仍在台面继续」并重复打印续等提示，任务继续，按提示 wait 退出 0 拿到存在的 png（证据：evidence/q15/）
- **缺口** [G5] [F6] video join 等待中按 Ctrl-C，合成任务有没有被取消？ — 合成运行中 SIGINT：任务变 cancelled、无成片，退出 3；排队中 SIGINT：不产生合成任务，「已中断」退出 3；但合成已在 0.16s 内完成后才收到 SIGINT 时，命令仍打印「已中断并取消这次生成」并退出 3，而尝试实际是 done、文件存在（证据：evidence/q16/）

### 预检接口（F7）— 2 问中 2 问实证通过 · 操作面 4 个，裁决触及 3 个，未触及：S37 LlmService.precheck_load(key) (dry run of the arbiter, no acquire)
- **实证完成** [F7] 预检对最大对话模型、362 帧视频、240 秒音乐、2048 图片返回什么？命令行读预检的哪些字段，memory_warning 用没用？ — 四个预检均 200 {ok:true, reason:null, release:[], memory_warning:null}；命令行读 ok/release/reason.message，不读 memory_warning（证据：evidence/q06/）
- **实证完成** [F7] 预检在未知 op、缺参数、参数非整数、模型不存在时各返回什么？调用前后台面状态有没有变化？ — 未知/缺 op 与 compose 返回 400 invalid_params；非整数返回 400；模型不存在 404 model_not_found；三个状态接口前后字节相同（证据：evidence/q07/）

### 发现、拉起、沙箱、版本、gateway 不变（F8）— 5 问中 3 问实证通过 · 操作面 5 个，裁决触及 5 个
- **实证完成** [F8] lmdesk 在禁止网络的 macOS 沙箱里运行 status 与 status --json 时退出码与输出是什么，是否拉起新进程？ — 沙箱下 status 退出 6、stderr「被沙箱拦截，需要允许访问本机网络（127.0.0.1）」；--json stdout {error:{code:sandboxed}}；无新进程（证据：evidence/q08/）
- **实证完成** [F8] 命令行与台面版本不一致时有没有警告、命令是否继续？LMDESK_FAKE_VERSION 在 dist 是否生效？ — 版本不一致时 stderr「注意：版本不一致（lmdesk 9.9.9，台面 1.0.0）」，退出 0 且命令照常输出；对照组无警告；dist 下 LMDESK_FAKE_VERSION 生效；版本取自 bundle.json 1.0.0（证据：evidence/q09/）
- **缺口** [G11] [F8] dist 台面没在运行时执行 status --json 与 models：有没有拉起台面、用了多久、有没有窗口或 Dock 图标？ — 台面未运行时 ~/.local/bin/lmdesk status --json 与 models 都在 0.13s 内退出 1，提示「台面没有运行。请先打开 LocalModelDesk。」（json 码 desk_not_running）；之后约 70s 采样内没有任何 LocalModelDesk 进程被拉起（证据：evidence/q11/）
- **实证完成** [F8] J1 那次 claude -p 会话执行了哪些命令？台面是被谁拉起的？台面会话记录与项目文件是否一致？ — claude 会话只执行了 Skill、两条 lmdesk Bash 命令与 Read，没有 open 命令；台面进程在首个 lmdesk 调用（20:48:23）后 3s 启动、父进程 launchd；会话「应用图标」1 条 done 尝试，与项目 icon.png md5 相同（证据：evidence/q43/）
- **缺口** [G12] [F8] q11（实测官 Bash 下 kill 台面后运行 lmdesk：不拉起、退出 1 desk_not_running）与 J1/q43（osascript 退出后经 Claude Code 运行 lmdesk：被拉起）结果相反，触发拉起与否的条件是什么？ — 两种退出方式 × 三种调用方式共 6 组全部拉起台面（父进程 launchd，直接调用 1.18s），退出 0 并输出状态 JSON；q11 的不拉起未复现。每次拉起后都出现一个标题 LocalModelDesk、onscreen=true、1200x832 的窗口；前台应用保持 Orca（证据：evidence/q44/）

### 图片会话命令（F3）— 3 问中 3 问实证通过 · 操作面 7 个，裁决触及 7 个
- **实证完成** [F3] image new 已存在的名字会怎样？同名会话有两个时 show/rename 的退出码与候选列表？用 id 时呢？ — new 同名两次都成功、无提示，产生两个同名会话；按名 show/rename 退出 2 并列出两个候选（--json 时 stdout 为 session_ambiguous 错误）；按 id 正常（证据：evidence/q17/）
- **实证完成** [F3] --from 加 --strength 时服务端收到什么参数、新图与原图关系？--out 指向已有文件、已有目录（带或不带斜杠）各发生什么？ — --from 记录为 base={attempt_id, strength 0.6}，新图保持原构图；--out 覆盖已有文件并提示「已覆盖」；已有目录与带斜杠的新目录都把文件写进目录内；--from 不存在 id 退出 5「找不到作为底稿的那一次生成」（证据：evidence/q18/）
- **实证完成** [F3] 会话里有进行中、已取消、失败的尝试时，image show 与 image wait 各输出什么？ — wait 已取消尝试退出 1「生成已取消：已取消：…」（--json 为 attempt_cancelled）；进行中 show 显示 running、路径空；wait 进行中尝试每 15s 进度、完成后输出路径退出 0；不存在 id 退出 5；失败状态的尝试造不出来（无效参数都在提交前被拒）（证据：evidence/q19/）

### 视频命令与 join（F4）— 4 问中 4 问实证通过 · 操作面 4 个，裁决触及 4 个
- **实证完成** [F4] --first-frame image:猫:<id> 生成的视频首帧是不是那张图？引用无效、缺段、与 --continue 同用时各怎样？ — 引用猫图生成的视频第一帧与原图同一只猫同一姿态（按 768x448 裁切放大）；服务端记录 mode=image、refs.first_frame 指向猫会话该尝试；尝试 id 不存在/会话不存在退出 5，缺段与 --continue 同用退出 2，均未产生新尝试（证据：evidence/q20/）
- **实证完成** [F4] 用本地文件做首帧时，成功、服务端拒绝、排队中 SIGINT、等待中 SIGINT、文件不合法各情形下 .inputs 里是否留下上传文件？ — 提交被服务端 400 拒绝时日志为 upload→400→discard，.inputs 不变；排队中 SIGINT 未上传；文件不存在/.gif/超 32MB 退出 2 且未上传；成功、运行失败、等待中取消的尝试各留下一张被尝试引用的上传图（证据：evidence/q21/）
- **实证完成** [F4] 视频 --continue 后 wait 输出哪个文件、时长多少？video join 成片时长多少？show 怎么显示合成尝试？ — 续写后 wait 输出 h3-joined 文件 4.63s（两段各 2.33s）；join 输出 compose 文件 4.63s；show 合成尝试 prompt 为「合成：<id> <id>」；join 一段退出 2、坏 id 退出 5（证据：evidence/q22/）
- **实证完成** [F4] 合成与续写成片文件的内容与它们声称的段是什么关系？不同会话的合成文件是否相同？ — 同 md5 只出现在同一会话同一组段的重复合成（以及与同组续写成片）；不同会话的合成文件 md5、分辨率都不同；合成首帧/末帧与源段首/末帧 PSNR 42–47，帧数 111=56+56-1。q22 所说「三次同为 305579 字节」与本次清单不符（190520 为 740017 字节）（证据：evidence/q40/）

### 音乐命令与 join（F5）— 3 问中 2 问实证通过 · 操作面 3 个，裁决触及 3 个
- **实证完成** [F5] music gen 在缺歌词、两个歌词参数都给、歌词文件不存在、非 UTF-8、空文件时各发生什么？ — 缺歌词、两者都给退出 2 lyrics_required；文件不存在、非 UTF-8 退出 2 invalid_lyrics_file；--json 时 stdout 为错误 JSON；会话尝试数与 media job 前后不变；空文件未运行（客户端会放行并以空歌词提交）（证据：evidence/q23/）
- **无法自证** [F5] 用 [instrumental] 生成的音乐有没有人声？时长与 --duration 差多少？ — 生成退出 0、约 60s，wav 时长 17.5s（--duration 20）；服务端记录 lyrics=[instrumental]；本机无语音识别/人声分离工具，只有频谱参考，有无人声需人耳判断（证据：evidence/q24/）
- **实证完成** [F5] 音乐 --continue 后输出哪个文件、时长多少？music join 时长是否等于各段之和？ — 续写 gen 输出 music3-joined 36.0s（两段 17.5s+20.0s，和为 37.5s，短 1.5s）；music join 输出 compose 36.0s；show 合成行标「合成：<id> <id>」；坏 id 退出 5（证据：evidence/q25/）

### 横切：agent 与界面/多 agent 并发（F14）— 4 问中 2 问实证通过 · 操作面 6 个，裁决触及 5 个，未触及：D1 [dead_contract] The 'origin':'agent' field the CLI sends in media start, compose and cancel bodies; the media route handlers do not read origin
- **缺口** [G6] [F14] 界面 1 分钟内刚用模型 A 对话，agent 用模型 B 问答：agent 等多久？界面对话有没有被打断？ — 界面对话未被打断（等待中界面再问 200）；ask 等约 5 分 20 秒后把模型换成 qwen27（loaded_by agent），但之后 /api/llm/chat 一直返回 409 evicted「模型已被台面收回」，ask 打印「模型被换走了，重新排队」直到 600s 超时退出 3，始终没有得到回答（证据：evidence/q26/）
- **实证完成** [F14] 两个、三个 lmdesk image gen 同时提交：是否都成功、按什么顺序、有没有重复生成？ — 两路与三路并发全部退出 0，台面上依次执行无重叠；每个会话尝试数等于提交数，无重复或多余尝试（证据：evidence/q27/）
- **缺口** [G7] [F14] 从 error/evicted、界面加载但未对话、界面加载且刚对话三种起点，agent ask --model qwen27 能否得到回答？台面 holder 与 llm 状态是什么？ — agent 加载 qwen27 后，界面再加载 superqwen：/api/llm/status 显示 loaded superqwen，但 /api/state 的 holder 仍是 qwen27（since 未变），此时界面身份的对话也返回 409 evicted「模型已被台面收回」，需手动 unload 再 load 才恢复；(a)(b) 起点 agent 换模型后正常回答；(c) 起点按 5 分钟窗口等待至 240s 超时。另：ask 在 stdin 是未关闭的非终端时阻塞在读 stdin，超过 --timeout 8 分钟仍未返回（证据：evidence/q41/）
- **实证完成** [F14] 界面正在流式对话时 agent 发起生图：界面对话能否完整收完？agent 何时提交？对话模型何时被卸载？ — 界面流式对话 822 token 正常 done、无错误事件；agent 先等「有对话正在进行」，再等「生成需要卸掉对话模型，但台面里最近在用它」约 300s，ui_chat_recent 变 false 后才提交，随后对话模型被驱逐，生图退出 0（证据：evidence/q28/）

### skill 安装、链接状态与卸载脚本（F9）— 3 问中 3 问实证通过 · 操作面 8 个，裁决触及 7 个，未触及：S28 POST /api/agent-skill/check (runs <cli> status --json --timeout 10)
- **实证完成** [F9] 卸载脚本对 agent 链接实际做了什么（dry-run 与真实运行），真实目录与外来链接是否保留？ — dry-run 列出并真实删除 .claude、.codex、.local/bin 三条指向 LocalModelDesk 的链接；.agents 真实目录与 .pi 外来链接保留；真实运行不打印删了哪些链接（证据：evidence/q05/）
- **实证完成** [F9] 安装位置已有真实目录、外来链接、真实 lmdesk 文件时，全选安装与全不选卸载后每个位置是什么、真实文件是否保留？ — occupied 行（真实目录、外来链接、真实 lmdesk 文件）安装报 error 且不改动，卸载 result=ok 仍 occupied；内容 sha1 前后一致；其余行正常装上和卸掉（证据：evidence/q03/）
- **实证完成** [F9] 先全选安装再只选 pi 时，共享目录 ~/.agents/skills 与 pi 自己的目录各是什么？pi 能发现几份 skill、来自哪里？ — 只选 pi 后 ~/.agents/skills 链接被删、~/.pi/agent/skills 保留；pi 从 ~/.pi/agent/skills 发现 local-model-desk 一次；codex 行带 shared_note「同时对 pi、DeepSeek Harness 生效」（证据：evidence/q04/）

### 设置页「本机 agent」区块（F10）— 3 问中 1 问实证通过 · 操作面 3 个，裁决触及 2 个，未触及：S43 Frontend API functions agentSkillStatus / agentSkillApply / agentSkillCheck
- **缺口** [G3] [F10] 设置页「本机 agent」区块的说明文字写了什么？1280x800、800x600、640x480 下有没有横向滚动或溢出？ — 说明文字为「让选中的 agent 通过 lmdesk 命令使用本机模型（对话、生图、图片会话）。」，未提视频、音乐；三个尺寸下 scrollWidth=clientWidth，无横向滚动，区块子元素无溢出（证据：evidence/q31/）
- **缺口** [G9] [F10] 命令行链接失效或缺失、而 agent 行都已安装时，「应用」能不能点？点了有没有修好？接口与菜单栏状态是什么？ — 命令行链接失效时页面显示「已失效，点应用更新」但「应用」禁用，检查也不改变；缺失时显示「未安装」且「应用」禁用；只有改动某个 agent 勾选才能点应用。/api/agent-skill 的 cli 为 stale/absent，而 /api/state 的 agent_skill_stale 两种情形都是 false（证据：evidence/q29/）
- **实证完成** [F10] skill 链接指向存在的旧位置与不存在的路径时，设置页该行显示什么、应用能否修复、agent_skill_stale 是什么？ — 旧位置存在时显示「指向旧位置，点应用更新」、不存在时显示「已失效，点应用更新」，两种情形「应用」可点且点后变已安装、链接指向 dist；运行中链接失效时 agent_skill_stale 为 false（A-71 规定启动时计算，q33 实测重启后为 true）（证据：evidence/q30/）

### 聊天页 agent 切换提示（F13）— 1 问中 1 问实证通过 · 操作面 1 个，裁决触及 1 个
- **实证完成** [F13] agent 换模型后聊天页有没有可关闭的切换提示？关掉后再换会不会再出现？界面自己换模型会不会误报？ — agent 换到 superqwen、再换到 qwen27 时，聊天页不刷新也各出现「模型已被 agent 切换为 X」与关闭按钮，关闭后消失；界面亲手换模型后截图无提示；刷新后提示容器隐藏。第 4 步 agent 换到 qwen27 后 ask 仍循环「模型被换走了，重新排队」900s 退出 3，页面同时显示「已加载：Qwen27」与「内存里：SuperQwen」（证据：evidence/q32/）

### 打包、开发入口与菜单栏（F12）— 2 问中 2 问实证通过 · 操作面 4 个，裁决触及 2 个，未触及：S46 Swift harness subcommand agent-skill-note、S48 Development entry scripts/lmdesk (LMDESK_PYTHON overrides the interpreter)
- **实证完成** [F12] skill 链接正常与失效时，菜单栏图标与菜单各是什么样？重启后与应用修复后呢？ — 运行中链接失效：菜单与图标不变、stale=false；重启后 stale=true，菜单出现「agent 链接指向旧位置，打开设置更新」；在设置页应用修复后不重启，stale 立即变 false、该菜单项消失、图标无圆点。点击该菜单项打开了一个 LocalModelDesk 窗口，但窗口内容截不到，无法确认是否为设置页（证据：evidence/q33/）
- **实证完成** [F12] 覆盖重建 dist 后，已装的 skill 链接与 ~/.local/bin/lmdesk 是否不需重装就指向新构建？ — build-app.sh 192s 退出 0；重建后 .app 与 Resources inode 都换新，链接本身不变且解析到新 inode 的 SKILL.md；重启后 lmdesk status 正常、/api/agent-skill 三行 installed、cli installed；claude -p 仍列出 local-model-desk。bin/lmdesk 实体文件指纹未采集（证据：evidence/q35/）

### SKILL.md 与 agent 发现（F11）— 3 问中 1 问实证通过 · 操作面 1 个，裁决触及 1 个
- **实证完成** [F11] 打包进 app 的 SKILL.md 实际包含什么，与 A-80/A-81/A-82/B-40/B-41 逐条对账？ — dist 与仓库 SKILL.md 字节相同；description 156 字符；A-80/81/82、B-40/41 各子项都找到对应 SKILL.md:行号 原文，无缺项（证据：evidence/q01/）
- **缺口** [G1] [F11] SKILL.md 对退出码 3 怎么说？超时、SIGINT、SIGTERM、ask 排不上队四种退出码 3 时 stderr 实际打印什么、任务是否继续？ — SKILL.md:83 对退出码 3 只写「等待超时，台面一直在忙…稍后可以用 wait 取结果」；SIGINT 路径（media.py:361）已取消任务且无续等提示，SKILL 未区分（证据：evidence/q02/）
- **缺口** [G10] [F11] Codex 默认沙箱下用户让它用本地模型翻译时，Codex 最终对用户说了什么、有没有给出放行方法、照做能否成功？ — Codex 读了 SKILL.md、lmdesk ask 退出 6 后，最终只说「需放行本机网络（127.0.0.1）」，没有转述 config.toml 或 -c 参数，并附上自己翻的「参考译文」；按 SKILL.md 的 -c sandbox_workspace_write.network_access=true 运行则成功调用本地模型（证据：evidence/q34/）

## 旅程完成度

### J1 用 Claude Code 写项目的开发者 · dist 台面进程未运行；空的临时项目目录；skill 已装在 ~/.claude/skills；一句中文请求，不提 lmdesk · 项目 ./assets 下得到本地模型生成的图片 — 无法自证
台面退出后，claude -p 用一句中文请求在 ./assets 得到 1024x1024 png；台面在 claude 运行中被拉起（q43：首个 lmdesk 调用后 3s 启动、父进程 launchd，会话记录 1 条尝试且与文件 md5 相同）；「全程没有弹出台面主窗口」未被观察（实测官未采集窗口），无法对 oracle 第 3 条下结论（证据：evidence/q36/） · 实测处境：request text: 帮我给这个项目生成一个应用图标图片，用本地模型生成，放到 ./assets 目录里。 (no command names)；project dir: empty, 0 files；run #1；timeout 900s, completed well under it；tools allowed: Bash,Read,Write；desk was running at the start and I quit it with osascript
- 1 done create empty project dir and record start → 0 files; desk pids 2877/2919 listening on 8766
- 2 done quit the desk via osascript, then check ps and lsof → no desk process and no listener
- 3 done run claude -p with the request in the project dir → exit 0; reply says icon.png saved in ./assets; the reply describes a blue-purple rounded square with a white speech-bubble symbol
- 4 done ls the project dir and check ps/lsof → assets/icon.png is 613533 bytes; the desk is running with new pids 7812/7817 and 8766 is listening
- 5 done file icon.png and curl 8766 → PNG 1024x1024; HTTP 200

### J2 第一次装 skill 的用户 · 三个 agent 都没装 skill（测前卸掉，测后恢复 claude/codex/pi 三条链接）；在 dist 台面的设置页操作 · 只给 Claude Code 装上 skill — 实证完成
在此情形下走通（三个 agent 都没装 skill（测前卸掉，测后恢复 claude/codex/pi 三条链接）；在 dist 台面的设置页操作），5 步（证据：evidence/q37/） · 实测处境：viewport 1280x800；entered at http://127.0.0.1:8766/, no waiting；ticked only the Claude Code checkbox, then clicked 应用；used Playwright MCP, no extra waits
- 1 done Open http://127.0.0.1:8766/ → Chat tab loaded; top bar has a 设置 button.
- 2 done Click 设置 → The 设置 panel opened on the right with a 本机 agent section; all four agents were 未安装 and 应用 was disabled.
- 3 done Tick the Claude Code checkbox → Checkbox ticked. I did not read the state of 应用 at this step.
- 4 done Click 应用 → Claude Code now shows 已安装. The other three show 未安装. lmdesk shows 已安装.
- 5 done Read the panel text and the ~/ links on disk → The panel text matches the screenshot. Only ~/.claude/skills/local-model-desk and ~/.local/bin/lmdesk exist.

### J3 Claude Code 用户 · 图片会话「猫」里至少有一张图；空的临时项目目录；一句中文请求 · 项目里得到以猫图为首帧、两段合成的视频 — 缺口（medium，误导）
走了 4 步，预算内未到进展（证据：evidence/q38/） · 实测处境：Request verbatim: 用本机台面图片会话「猫」里已有的那张图做首帧生成一段视频，再接着续一段，最后合成一个成片放进当前项目目录；Project dir had 0 files at the start；Run 1 of 1; one non-interactive claude -p with tools Bash,Read,Write; the wall-clock wait was 21m13s (alarm limit 2400s)
- 1 done Recorded the start state: dir empty, request text, listener on 8766 → Dir has 0 files. python3.13 pid 31246 listens on 8766 and the app is running.
- 2 done Ran claude -p with the request → Exit 0 after 21m13s. Claude Code reported two retried memory-guard aborts, then success. 猫-成片.mp4 appeared in the project dir.
- 3 done Checked the output with ffprobe → h264/aac, 768x448, 10.29s.
- 4 done Extracted Claude Code's tool-call sequence from the session jsonl → 27 tool calls: lmdesk image show, video new, video gen --first-frame image:猫:<id>, video wait, video gen --continue, video wait --out.

### J4 Claude Code 用户 · 空的临时项目目录；请求不带歌词 · ./assets 下得到一段纯音乐 — 实证完成
在此情形下走通（空的临时项目目录；请求不带歌词），5 步（证据：evidence/q39/） · 实测处境：request verbatim: 帮我用本机模型生成一段15秒左右的纯音乐背景乐，放到项目的 ./assets 目录里；project dir had 0 files at start；1st run；waited 70s (alarm limit 1200s)
- 1 done Recorded start state (empty dir, request text) and the 8766 listener → Dir had 0 files. The listener on 127.0.0.1:8766 is pid 31246, the desk python inside dist/LocalModelDesk.app.
- 2 done Ran claude -p with the request → Exit 0 after 70s. Claude Code reported bgm.wav generated, 15.0s, with lyrics set to [instrumental].
- 3 done Extracted the commands Claude Code ran from its session record → Skill local-model-desk, then lmdesk music sessions, music new, and music gen with --duration 15 and --out ./assets/bgm.wav.
- 4 done Checked the output file with afinfo and file → WAV, 44.1kHz stereo 16-bit, 15.000091s, 2.6MB, in ./assets.
- 5 done Measured peak amplitude → Peak 22609, so the audio is not silent.

## 缺口清单（按严重度）
- **high** **缺口** [G6] [F14] 界面 1 分钟内刚用模型 A 对话，agent 用模型 B 问答：agent 等多久？界面对话有没有被打断？ — 界面对话未被打断（等待中界面再问 200）；ask 等约 5 分 20 秒后把模型换成 qwen27（loaded_by agent），但之后 /api/llm/chat 一直返回 409 evicted「模型已被台面收回」，ask 打印「模型被换走了，重新排队」直到 600s 超时退出 3，始终没有得到回答（证据：evidence/q26/）
- **high** **缺口** [G7] [F14] 从 error/evicted、界面加载但未对话、界面加载且刚对话三种起点，agent ask --model qwen27 能否得到回答？台面 holder 与 llm 状态是什么？ — agent 加载 qwen27 后，界面再加载 superqwen：/api/llm/status 显示 loaded superqwen，但 /api/state 的 holder 仍是 qwen27（since 未变），此时界面身份的对话也返回 409 evicted「模型已被台面收回」，需手动 unload 再 load 才恢复；(a)(b) 起点 agent 换模型后正常回答；(c) 起点按 5 分钟窗口等待至 240s 超时。另：ask 在 stdin 是未关闭的非终端时阻塞在读 stdin，超过 --timeout 8 分钟仍未返回（证据：evidence/q41/）
- **medium** **缺口** [G1] [F11] SKILL.md 对退出码 3 怎么说？超时、SIGINT、SIGTERM、ask 排不上队四种退出码 3 时 stderr 实际打印什么、任务是否继续？ — SKILL.md:83 对退出码 3 只写「等待超时，台面一直在忙…稍后可以用 wait 取结果」；SIGINT 路径（media.py:361）已取消任务且无续等提示，SKILL 未区分（证据：evidence/q02/）
- **medium** **缺口** [G2] [F1] ask 同时读管道并带多个 --file 时模型实际收到什么？--file 非 UTF-8 或不存在时怎样？ — 管道与两个文件按「问题、stdin、--- 文件名 --- 内容」拼进一条用户消息，模型复述一致；--file 指向 GBK 文件时退出 1 并打印 Python traceback（UnicodeDecodeError），不存在的文件退出 2 带中文提示（证据：evidence/q13/）
- **medium** **缺口** [G3] [F10] 设置页「本机 agent」区块的说明文字写了什么？1280x800、800x600、640x480 下有没有横向滚动或溢出？ — 说明文字为「让选中的 agent 通过 lmdesk 命令使用本机模型（对话、生图、图片会话）。」，未提视频、音乐；三个尺寸下 scrollWidth=clientWidth，无横向滚动，区块子元素无溢出（证据：evidence/q31/）
- **medium** **缺口** [G4] [F2] 图片生成进行中时发 lmdesk ask：等待期间 stderr 出现什么、间隔多久？生图完成后会不会自动提交？ — ask 在生图完成后 3.4s 得到回答，退出 0；但 ask 启动后 60.5s 内 stderr 无任何输出，第一行进度在 60s，之后约 15–17s 一行；期间 /api/llm/status 显示 error（证据：evidence/q14/）
- **medium** **缺口** [G5] [F6] video join 等待中按 Ctrl-C，合成任务有没有被取消？ — 合成运行中 SIGINT：任务变 cancelled、无成片，退出 3；排队中 SIGINT：不产生合成任务，「已中断」退出 3；但合成已在 0.16s 内完成后才收到 SIGINT 时，命令仍打印「已中断并取消这次生成」并退出 3，而尝试实际是 done、文件存在（证据：evidence/q16/）
- **medium** **缺口** [G8] [F1] lmdesk ask 在 stdin 为未关闭的管道（agent 执行器常见）时会阻塞读 stdin、无视 --timeout 永不返回？在 Claude Code/Codex 的命令执行环境下是否发生？ — stdin 为 /dev/null 时 1–2s 返回；Claude Code（Bash 工具 stdin 为 /dev/null）与 codex exec 各 15s 正常拿到「白」；stdin 为不关闭的管道时 --timeout 60 无效，120s 外部强杀前无任何输出（证据：evidence/q42/）
- **medium** **缺口** [G9] [F10] 命令行链接失效或缺失、而 agent 行都已安装时，「应用」能不能点？点了有没有修好？接口与菜单栏状态是什么？ — 命令行链接失效时页面显示「已失效，点应用更新」但「应用」禁用，检查也不改变；缺失时显示「未安装」且「应用」禁用；只有改动某个 agent 勾选才能点应用。/api/agent-skill 的 cli 为 stale/absent，而 /api/state 的 agent_skill_stale 两种情形都是 false（证据：evidence/q29/）
- **medium** **缺口** [G10] [F11] Codex 默认沙箱下用户让它用本地模型翻译时，Codex 最终对用户说了什么、有没有给出放行方法、照做能否成功？ — Codex 读了 SKILL.md、lmdesk ask 退出 6 后，最终只说「需放行本机网络（127.0.0.1）」，没有转述 config.toml 或 -c 参数，并附上自己翻的「参考译文」；按 SKILL.md 的 -c sandbox_workspace_write.network_access=true 运行则成功调用本地模型（证据：evidence/q34/）
- **medium** **缺口** [G11] [F8] dist 台面没在运行时执行 status --json 与 models：有没有拉起台面、用了多久、有没有窗口或 Dock 图标？ — 台面未运行时 ~/.local/bin/lmdesk status --json 与 models 都在 0.13s 内退出 1，提示「台面没有运行。请先打开 LocalModelDesk。」（json 码 desk_not_running）；之后约 70s 采样内没有任何 LocalModelDesk 进程被拉起（证据：evidence/q11/）
- **medium** **缺口** [G12] [F8] q11（实测官 Bash 下 kill 台面后运行 lmdesk：不拉起、退出 1 desk_not_running）与 J1/q43（osascript 退出后经 Claude Code 运行 lmdesk：被拉起）结果相反，触发拉起与否的条件是什么？ — 两种退出方式 × 三种调用方式共 6 组全部拉起台面（父进程 launchd，直接调用 1.18s），退出 0 并输出状态 JSON；q11 的不拉起未复现。每次拉起后都出现一个标题 LocalModelDesk、onscreen=true、1200x832 的窗口；前台应用保持 Orca（证据：evidence/q44/）
- **medium** **缺口** [J3] [F4] J3 走得通吗？ — Claude Code 用 --first-frame image:猫:<id> 生成第一段、--continue 续第二段，以 wait --out 拿到 10.29s 成片放进项目（单段约 5.2s）；全程没有执行 join，台面视频会话里没有合成记录（oracle「台面视频会话里有合成记录」未命中）；两段各因视频模型的内存保护中止一次后重试成功，用时 21 分钟（证据：evidence/q38/）

## 无法自证清单（待人工验证，不计为完成也不计为失败）
- **无法自证** [F5] 用 [instrumental] 生成的音乐有没有人声？时长与 --duration 差多少？ — 生成退出 0、约 60s，wav 时长 17.5s（--duration 20）；服务端记录 lyrics=[instrumental]；本机无语音识别/人声分离工具，只有频谱参考，有无人声需人耳判断（证据：evidence/q24/）
- **无法自证** [J1] [F8] J1 走得通吗？ — 台面退出后，claude -p 用一句中文请求在 ./assets 得到 1024x1024 png；台面在 claude 运行中被拉起（q43：首个 lmdesk 调用后 3s 启动、父进程 launchd，会话记录 1 条尝试且与文件 md5 相同）；「全程没有弹出台面主窗口」未被观察（实测官未采集窗口），无法对 oracle 第 3 条下结论（证据：evidence/q36/）

## 未盘问声明（按风险排序）
（所有面均已盘问或部分盘问）

## 未拉的线（已发现泄漏点、未实测——续盘从这里接手）
- [F1] 界面在对话模型内存不足时能否确认后强制加载？同情形 lmdesk ask 实际输出与退出码？ — 泄漏点：desk/agent_cli/decide.py:62 「对话模型不能强制加载」；RC1 澄清规则
- [F9] 卸载脚本真实运行时不打印删了哪些链接，用户能否知道链接被清理？ — 泄漏点：q05 实测官顺带观察：真实运行 stdout 无删除行
- [F9] 卸载（全不选应用）后 ~/.agents/skills、~/.dsh/skills 留下空的父目录，是否影响各 agent？ — 泄漏点：q03 实测官读回：卸载后父目录为空目录
- [F8] lmdesk status 文本输出在模型为空时显示「对话模型：idle 」，--json 的 media.kind 在空闲时仍是上一个任务的 kind — 泄漏点：q08/q09 实测官顺带观察
- [F8] 生产包里 LMDESK_FAKE_VERSION 环境变量可以覆盖命令行版本号，是否该只在测试里生效？ — 泄漏点：q09：dist 下该变量生效；普查 S10
- [F3] image new 同名时不提示，agent 新建同名会话后按名调用会撞退出 2；是否该在 new 时提示或拒绝？ — 泄漏点：q17：两次 new 同名均退出 0 无提示
- [F5] --lyrics-file 指向空文件时客户端放行、以空歌词提交，服务端如何处理？ — 泄漏点：q23 实测官读 _check_music：空文件通过二选一校验，未实际发送
- [F8] 台面日志 desk.log 已 451MB、server-stdout.log 240MB，是否有轮转？ — 泄漏点：q13 实测官顺带观察（不在本交付范围）
- [F10] 直接打开 #tab=settings 时设置面板宽度为 0 不显示，需点顶部「设置」才出现 — 泄漏点：q31 实测官顺带观察
- [F10] 设置页首次加载时控制台有 2 条错误，是什么？ — 泄漏点：q31 实测官顺带观察，未打开日志
- [F14] 生图挤掉对话模型期间 /api/llm/status 显示 status=error，界面与 lmdesk status 会不会把它当成加载失败？ — 泄漏点：q14 状态采样：image 运行中 llm 为 error，完成后 loading→loaded
- [F6] SIGINT 落在任务已完成后，image/video/music gen 是否同样谎报「已取消」？（共用 _run_job） — 泄漏点：q16 t1：compose 已 done 仍打印已中断并取消
- [F4] 60 段合成被取消时日志是「Error opening input file」指向存在的文件，取消是否被误记成输入错误？ — 泄漏点：q16 t2 job 9 log
- [F8] q19 探针把 --size 等选项放在位置参数后时 argparse 报 unrecognized arguments 并打印顶层 usage；什么写法会触发？SKILL 示例写法是否受影响？ — 泄漏点：q19 evidence 04-try.log
- [F3] 取消文案重复前缀「生成已取消：已取消：…」 — 泄漏点：q19 01
- [F3] failed 状态尝试的 show/wait 输出未取证（造不出失败） — 泄漏点：q19 could_not
- [F4] --steps 99999 通过客户端与服务端提交校验，任务运行后才以「steps must be in [1, 1000]」失败；视频参数上限是否应在提交时拒绝？ — 泄漏点：q21 case 2 variant
- [F4] 两个早期 h3-joined-20261008-22* 文件不被任何会话引用、首帧与候选段都不相似，来源不明（可能是旧版残留） — 泄漏点：q40 could_not
- [F12] 点击菜单栏「agent 链接指向旧位置，打开设置更新」后打开的是不是设置页？ — 泄漏点：q33 could_not：窗口内容截图为空、AX 读不到
- [F12] 用 AppleEvent quit 退出台面超时（-1712）不退出；卸载或系统登出时能否正常退出？ — 泄漏点：q33 顺带观察
- [F10] 设置页首次 resize 时控制台 193 条错误是什么？ — 泄漏点：J2 实测官顺带观察
- [F4] 视频模型的内存保护在可用内存约 88% 时因 swap 活动中止生成，agent 只能盲目重试；命令行是否该给出可行提示？ — 泄漏点：J3 实测官顺带观察

## 缺陷模式（同类位点清点——未查位点不进任何完成度）

### P1 面向用户/agent 的能力与退出情形文字停留在第一期，未随第二期与澄清规则更新 — 共 26 位点：实证 3，未查 23
- **缺口** SKILL.md 退出码 3 说明 — SKILL.md 对退出码 3 怎么说？超时、SIGINT、SIGTERM、ask 排不上队四种退出码 3 时 stderr 实际打印什么、任务是否继续？
- **缺口** 设置页「本机 agent」说明文字 — 设置页「本机 agent」区块的说明文字写了什么？1280x800、800x600、640x480 下有没有横向滚动或溢出？
- **缺口** 连接与启动文案（discovery.py、cli.py:91,103） — Codex 默认沙箱下用户让它用本地模型翻译时，Codex 最终对用户说了什么、有没有给出放行方法、照做能否成功？
- **未查** SKILL.md frontmatter description（SKILL.md:3）（[F11] 同类嫌疑，未实证）
- **未查** SKILL.md 开头与「调用」节（SKILL.md:8-14）（[F11] 同类嫌疑，未实证）
- **未查** SKILL.md「对话」节（SKILL.md:16-25）（[F11] 同类嫌疑，未实证）
- **未查** SKILL.md「生图与素材管理」节：被工具超时打断时生成在台面继续（SKILL.md:41）（[F11] 同类嫌疑，未实证）
- **未查** SKILL.md「视频」节（SKILL.md:44-61）（[F11] 同类嫌疑，未实证）
- **未查** SKILL.md「音乐」节（SKILL.md:63-76）（[F11] 同类嫌疑，未实证）
- **未查** SKILL.md「例子」节只有对话与生图（SKILL.md:92-97）（[F11] 同类嫌疑，未实证）
- **未查** 设置页 TRY_PHRASE 与面板文案（pure/agent_skill.js:2、panes/agent_skill.js）（[F10] 同类嫌疑，未实证）
- **未查** lmdesk argparse 帮助（cli.py:19-26、media.py:37-80）（[F8] 同类嫌疑，未实证）
- **未查** 提交后续等提示「中断后可用 … wait 继续等待」（media.py:140-142）（[F6] 同类嫌疑，未实证）
- **未查** 媒体中断/超时/台面退出文案（media.py:141-154）（[F6] 同类嫌疑，未实证）
- **未查** 通用中断「已中断」（cli.py:98-99）（[F6] 同类嫌疑，未实证）
- **未查** Waiter 超时与进度文案（waiter.py:35,41,43）（[F2] 同类嫌疑，未实证）
- **未查** wait 命令失败/取消文案（media.py:152-164,206）（[F3] 同类嫌疑，未实证）
- **未查** join 文案（media.py:110,168-173,384）（[F4] 同类嫌疑，未实证）
- **未查** ask 文案（chat.py）（[F1] 同类嫌疑，未实证）
- **未查** decide 等待原因文案（decide.py）（[F2] 同类嫌疑，未实证）
- **未查** media 参数校验文案（[F4] 同类嫌疑，未实证）
- **未查** 内存不足与提交失败文案（media.py:107,132,310）（[F3] 同类嫌疑，未实证）
- **未查** 菜单栏 Swift 文案（ShellStatus.swift:47、StatusItemController.swift:27）（[F12] 同类嫌疑，未实证）
- **未查** build-app.sh 输出（[F12] 同类嫌疑，未实证）
- **未查** uninstall-app.sh 输出（[F9] 同类嫌疑，未实证）
- **未查** scripts/lmdesk 注释（[F12] 同类嫌疑，未实证）

### P2 命令行把服务端可能持续返回的错误码当作可重试，重试期间只读状态、不改变条件，导致无进展地等到超时 — 共 18 位点：实证 2，未查 16
- **缺口** chat.py:run_ask POST /api/llm/chat code=evicted（服务端 _chat_precheck still_holds 为假时返回） — 界面 1 分钟内刚用模型 A 对话，agent 用模型 B 问答：agent 等多久？界面对话有没有被打断？
- **缺口** arbiter holder 在换模型（界面或 agent 加载另一模型）后未更新，导致 /api/llm/chat 的 still_holds 为假持续 409 evicted — 从 error/evicted、界面加载但未对话、界面加载且刚对话三种起点，agent ask --model qwen27 能否得到回答？台面 holder 与 llm 状态是什么？
- **未查** chat.py:_swap POST /api/llm/load code=media_busy（[F1] 同类嫌疑，未实证）
- **未查** chat.py:_swap POST /api/llm/load code=load_in_progress（[F1] 同类嫌疑，未实证）
- **未查** chat.py:_swap POST /api/llm/load code=model_mismatch（[F1] 同类嫌疑，未实证）
- **未查** chat.py:_swap POST /api/llm/load code=evicted（[F1] 同类嫌疑，未实证）
- **未查** chat.py:_swap POST /api/llm/load code=no_model_loaded（[F1] 同类嫌疑，未实证）
- **未查** chat.py:_swap POST /api/llm/load code=job_not_running（[F1] 同类嫌疑，未实证）
- **未查** chat.py:_swap POST /api/llm/load code=insufficient_budget（[F1] 同类嫌疑，未实证）
- **未查** chat.py:run_ask POST /api/llm/chat code=no_model_loaded（[F1] 同类嫌疑，未实证）
- **未查** chat.py:run_ask POST /api/llm/chat code=model_mismatch（[F1] 同类嫌疑，未实证）
- **未查** chat.py:run_ask POST /api/llm/chat code=media_busy/load_in_progress/job_not_running（[F1] 同类嫌疑，未实证）
- **未查** media.py:_submit POST 媒体/合成端点 code=media_busy（[F2] 同类嫌疑，未实证）
- **未查** media.py:_submit POST 媒体/合成端点 code=load_in_progress（[F2] 同类嫌疑，未实证）
- **未查** media.py:_submit POST 媒体/合成端点 code=model_mismatch（[F2] 同类嫌疑，未实证）
- **未查** media.py:_submit POST 媒体/合成端点 code=evicted（[F2] 同类嫌疑，未实证）
- **未查** media.py:_submit POST 媒体/合成端点 code=no_model_loaded（[F2] 同类嫌疑，未实证）
- **未查** media.py:_submit POST 媒体/合成端点 code=job_not_running（[F2] 同类嫌疑，未实证）
