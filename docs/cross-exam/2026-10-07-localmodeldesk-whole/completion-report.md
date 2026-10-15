# 完成度报告 — LocalModelDesk 全应用（macOS 外壳 dist/LocalModelDesk.app + 本地 Python 服务 desk + 零依赖 Web UI）

需求基准：superstorm-registry · 共 20 面，盘问 9 面 · 实测 10 问 · 旅程 11 条，盘问 3 条 · 操作面 98 个，裁决触及 20 个
被评构建：0d98e9ef9e09a3f9674604308e8d63d4357bfd22-e3b0c44298fc1c14（intake 记录于 2026-10-07T18:04:03+09:00）

## 总览

实证完成：0 · 缺口：10 · 跑偏：0 · 无法自证：0
旅程裁决：实证完成：0 · 缺口：3 · 跑偏：0 · 无法自证：0

> 盘问官即交付作者（examiner_is_author）：bias-guard 生效——gap 从严，降级为 low 或 done 需额外独立证据。

> 本 run 取证类子 agent（实测官、枚举官）用 session，用户于 2026-10-07T17:55:00+09:00 确认：「A 证据优先（推荐）」。裁决与普查仍用会话模型。
> 定靶时盘问官推荐的是选项 A（靶子以 UI 旅程为主（webview、分段控件、首帧上传、续写流程），降档实测官易残缺重派）。

取证时间：首问 2026-10-07T18:16:18+09:00 · 末问 2026-10-09T04:48:11+09:00 · 跨 2071 分钟
相邻 runtime 问间隔不足 60 秒，请核对是否真实取证：调用 S44「Create chat session」（入口 POST /api/sessions (desk/library/http.py:196)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 → 调用 S45「Update chat session (messages/title/skills; keepalive)」（入口 PATCH /api/sessions/{id} (desk/library/http.py:197)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（0 秒）；调用 S45「Update chat session (messages/title/skills; keepalive)」（入口 PATCH /api/sessions/{id} (desk/library/http.py:197)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 → 调用 S35「Preview a GitHub skill install (staging)」（入口 POST /api/skills/preview (desk/skills/routes.py:22)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（0 秒）

## 规则一致性（规则 ↔ 规则；候选不计为产品缺陷）
来源 50 份 · 规则 1097 条 · 比较组 145 个 · 候选 33 条
仅核对本轮材料；语义覆盖、来源完整性与用户确认真实性须核对独立审查记录。
独立审查：/private/tmp/claude-502/-Users-aa-LocalModelDesk/ed72d520-696b-4a05-98e4-778804fec395/tasks/ad37729394796320f.output · claude-opus-5-5 (session)；本轮禁派子 agent
- 来源 SRC1：docs/superpowers/specs/2026-08-31-arbiter-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-arbiter-design.md）
- 来源 SRC2：docs/superpowers/specs/2026-08-31-arbiter-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-arbiter-spec.md）
- 来源 SRC3：docs/superpowers/specs/2026-08-31-e2e-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-e2e-design.md）
- 来源 SRC4：docs/superpowers/specs/2026-08-31-e2e-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-e2e-spec.md）
- 来源 SRC5：docs/superpowers/specs/2026-08-31-foundation-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-foundation-design.md）
- 来源 SRC6：docs/superpowers/specs/2026-08-31-foundation-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-foundation-spec.md）
- 来源 SRC7：docs/superpowers/specs/2026-08-31-gateway-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-gateway-design.md）
- 来源 SRC8：docs/superpowers/specs/2026-08-31-gateway-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-gateway-spec.md）
- 来源 SRC9：docs/superpowers/specs/2026-08-31-library-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-library-design.md）
- 来源 SRC10：docs/superpowers/specs/2026-08-31-library-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-library-spec.md）
- 来源 SRC11：docs/superpowers/specs/2026-08-31-llm-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-llm-design.md）
- 来源 SRC12：docs/superpowers/specs/2026-08-31-llm-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-llm-spec.md）
- 来源 SRC13：docs/superpowers/specs/2026-08-31-localmodeldesk-app-overview.md @ 0d98e9e（evidence/rules/sources/2026-08-31-localmodeldesk-app-overview.md）
- 来源 SRC14：docs/superpowers/specs/2026-08-31-media-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-media-design.md）
- 来源 SRC15：docs/superpowers/specs/2026-08-31-media-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-media-spec.md）
- 来源 SRC16：docs/superpowers/specs/2026-08-31-packaging-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-packaging-design.md）
- 来源 SRC17：docs/superpowers/specs/2026-08-31-packaging-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-packaging-spec.md）
- 来源 SRC18：docs/superpowers/specs/2026-08-31-resources-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-resources-design.md）
- 来源 SRC19：docs/superpowers/specs/2026-08-31-resources-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-resources-spec.md）
- 来源 SRC20：docs/superpowers/specs/2026-08-31-shell-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-shell-design.md）
- 来源 SRC21：docs/superpowers/specs/2026-08-31-shell-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-shell-spec.md）
- 来源 SRC22：docs/superpowers/specs/2026-08-31-ui-design.md @ 0d98e9e（evidence/rules/sources/2026-08-31-ui-design.md）
- 来源 SRC23：docs/superpowers/specs/2026-08-31-ui-spec.md @ 0d98e9e（evidence/rules/sources/2026-08-31-ui-spec.md）
- 来源 SRC24：docs/superpowers/specs/2026-09-17-budget-design.md @ 0d98e9e（evidence/rules/sources/2026-09-17-budget-design.md）
- 来源 SRC25：docs/superpowers/specs/2026-09-17-budget-spec.md @ 0d98e9e（evidence/rules/sources/2026-09-17-budget-spec.md）
- 来源 SRC26：docs/superpowers/specs/2026-09-23-skills-spec.md @ 0d98e9e（evidence/rules/sources/2026-09-23-skills-spec.md）
- 来源 SRC27：docs/superpowers/specs/2026-09-24-image-sessions-design.md @ 0d98e9e（evidence/rules/sources/2026-09-24-image-sessions-design.md）
- 来源 SRC28：docs/superpowers/specs/2026-09-25-media-sessions-base-design.md @ 0d98e9e（evidence/rules/sources/2026-09-25-media-sessions-base-design.md）
- 来源 SRC29：docs/superpowers/specs/2026-09-27-music-sessions-design.md @ 0d98e9e（evidence/rules/sources/2026-09-27-music-sessions-design.md）
- 来源 SRC30：docs/superpowers/specs/2026-09-27-video-sessions-design.md @ 0d98e9e（evidence/rules/sources/2026-09-27-video-sessions-design.md）
- 来源 SRC31：docs/superpowers/specs/2026-09-27-video-soundtrack-design.md @ 0d98e9e（evidence/rules/sources/2026-09-27-video-soundtrack-design.md）
- 来源 SRC32：docs/superpowers/specs/2026-09-30-library-preview-design.md @ 0d98e9e（evidence/rules/sources/2026-09-30-library-preview-design.md）
- 来源 SRC33：docs/superpowers/specs/2026-10-07-video-size-design.md @ 0d98e9e（evidence/rules/sources/2026-10-07-video-size-design.md）
- 来源 SRC34：README.md @ 0d98e9e（evidence/rules/sources/README.md）
- 来源 SRC35：~/.claude/projects/-Users-aa-LocalModelDesk/memory/feedback-hardware-soft-limits.md （用户在过往会话确认的决定，记忆文件原样）（evidence/rules/sources/user-confirmed-feedback-hardware-soft-limits.md）
- 来源 SRC36：~/.claude/projects/-Users-aa-LocalModelDesk/memory/feedback-no-legacy-framing.md （用户在过往会话确认的决定，记忆文件原样）（evidence/rules/sources/user-confirmed-feedback-no-legacy-framing.md）
- 来源 SRC37：~/.claude/projects/-Users-aa-LocalModelDesk/memory/project-deepseek-v4-not-on-mlx-lm.md （用户在过往会话确认的决定，记忆文件原样）（evidence/rules/sources/user-confirmed-project-deepseek-v4-not-on-mlx-lm.md）
- 来源 SRC38：~/.claude/projects/-Users-aa-LocalModelDesk/memory/project-img2img-next.md （用户在过往会话确认的决定，记忆文件原样）（evidence/rules/sources/user-confirmed-project-img2img-next.md）
- 来源 SRC39：~/.claude/projects/-Users-aa-LocalModelDesk/memory/project-media-sessions-plan.md （用户在过往会话确认的决定，记忆文件原样）（evidence/rules/sources/user-confirmed-project-media-sessions-plan.md）
- 来源 SRC40：~/.claude/projects/-Users-aa-LocalModelDesk/memory/project-visual-baseline-direction.md （用户在过往会话确认的决定，记忆文件原样）（evidence/rules/sources/user-confirmed-project-visual-baseline-direction.md）
- 来源 SRC41：ledger journeys[] 经用户 2026-10-08 读回确认（evidence/rules/sources/journeys-confirmed.md）
- 来源 SRC42：.allforai/bootstrap/local-requirements.json @ 0d98e9e 工作树（未跟踪目录）（evidence/rules/sources/allforai-bootstrap-local-requirements.json）
- 来源 SRC43：.allforai/visual-qa/visual-acceptance-criteria.json @ 0d98e9e 工作树（未跟踪目录）（evidence/rules/sources/allforai-visual-acceptance-criteria.json）
- 来源 SRC44：docs/qwen-image-mlx.md @ 0d98e9e（evidence/rules/sources/qwen-image-mlx.md）
- 来源 SRC45：docs/superpowers/plans/2026-09-11-cross-exam-0908-visual.md @ 0d98e9e（evidence/rules/sources/plan-2026-09-11-cross-exam-0908-visual.md）
- 来源 SRC46：docs/visual/interaction-baseline.candidate.json @ 0d98e9e（evidence/rules/sources/visual-interaction-baseline.candidate.json）
- 来源 SRC47：docs/visual/visual-baseline.candidate.json @ 0d98e9e（evidence/rules/sources/visual-visual-baseline.candidate.json）
- 来源 SRC48：盘问官检索记录 2026-10-08（仅路径存在性事实）（evidence/rules/sources/material-availability.md）
- 来源 SRC49：.allforai/product-concept/decision-journal.json @ 2026-10-09 快照（evidence/rules/sources/product-concept-decision-journal.json）
- 来源 SRC50：.allforai/visual-qa/visual-evidence-requirements.json @ 2026-10-09 快照（evidence/rules/sources/visual-qa-visual-evidence-requirements.json）
- 比较 RULE520 / RULE526 / RULE527 / RULE528 / RULE546 / RULE494 / RULE705 / RULE155 / RULE183 / RULE184 / RULE185 / RULE507 / RULE166 / RULE565：findings — version_conflict：同一台机器、聊天模型驻留时发起视频/音乐生成（J3 前置条件）；README 为 0d98e9e 当前版本，budget 修订为 2026-09-17/22，J3 为 2026-10-08 确认旅程，三者在当前构建同时有效（见 RC1）
- 比较 RULE70 / RULE283 / RULE290 / RULE436 / RULE50 / RULE42 / RULE250 / RULE260 / RULE24 / RULE140 / RULE467 / RULE166 / RULE167 / RULE168：findings — version_conflict：媒体作业进行中、聊天模型仍被台面持有时的台面聊天、网关请求与 UI 加载按钮；R-llm-06/R-gateway-08/R-e2e-08 原文未被修订，R-budget-17 为后续修订（见 RC2）
- 比较 RULE169 / RULE170 / RULE171 / RULE167 / RULE250 / RULE260：findings — needs_clarification：外部客户端经网关发请求、且媒体作业在跑时的拒绝判定与对外原因码（见 RC3）
- 比较 RULE155 / RULE158 / RULE163 / RULE175 / RULE508 / RULE547 / RULE548 / RULE549 / RULE1068 / RULE1095 / RULE944 / RULE1005 / RULE21 / RULE782：findings — needs_clarification：任意内存规格的机器上，预估内存不足以同时容纳新重活时的处置；用户软限制记忆（2026-09-24/25）晚于 budget 修订（2026-09-17~22），两者在当前构建同时被引用（见 RC4）
- 比较 RULE9 / RULE21 / RULE25 / RULE433 / RULE454 / RULE501 / RULE157 / RULE159 / RULE160 / RULE186：findings — version_conflict：加载聊天模型前与冷启动额度计算时使用的内存基准（见 RC5）
- 比较 RULE22 / RULE24 / RULE162：findings — behavior_conflict：同一份 arbiter 设计（2026-08-31）内，llm 加载前是否调用 canStartHeavy（见 RC6）
- 比较 RULE20 / RULE406 / RULE416 / RULE431 / RULE250 / RULE183 / RULE168：findings — version_conflict：多件重活同时被台面持有时，deskState、菜单栏、状态条与网关对持有者的读取（见 RC7）
- 比较 RULE92 / RULE383 / RULE386 / RULE40 / RULE486 / RULE522 / RULE537：findings — behavior_conflict：当前 README（0d98e9e）的内容（见 RC8）
- 比较 RULE82 / RULE479 / RULE490 / RULE596 / RULE534：findings — version_conflict：构建与分发签名流程（见 RC9）
- 比较 RULE36 / RULE241 / RULE114 / RULE446 / RULE536 / RULE475 / RULE569 / RULE311 / RULE302 / RULE318 / RULE90 / RULE379 / RULE550 / RULE551 / RULE148 / RULE506 / RULE193 / RULE366：findings — needs_clarification：处理用户机器上既有数据（已有模型目录、旧 outputs/history.jsonl、.m4a/.webm 旧成品、旧 LaunchAgent）的规则（见 RC10）
- 比较 RULE36 / RULE232 / RULE234 / RULE239 / RULE242：findings — exception_ambiguity：move 模式收编且源与目标在同一卷（见 RC11）
- 比较 RULE56 / RULE302 / RULE303 / RULE297 / RULE331 / RULE743 / RULE766 / RULE768 / RULE971 / RULE972 / RULE973 / RULE587 / RULE622：findings — version_conflict：图片作业产出的 PNG 在素材库/成品列表中的呈现（见 RC12）
- 比较 RULE737 / RULE582 / RULE655 / RULE1057 / RULE663 / RULE592 / RULE554 / RULE555 / RULE776 / RULE779 / RULE780 / RULE831 / RULE567：findings — version_conflict：图片会话（同一 2026-09-24 需求 revision 1）中的「在这张基础上改」「换个构图」（见 RC13）
- 比较 RULE808 / RULE1045 / RULE612 / RULE613 / RULE615 / RULE779 / RULE781：findings — behavior_conflict：图片会话中失败、已取消或文件已不在的尝试卡片展开时（见 RC14）
- 比较 RULE870 / RULE1069 / RULE822 / RULE836 / RULE741 / RULE756 / RULE786 / RULE816 / RULE623 / RULE644：findings — version_conflict：媒体会话底座合并后的图片会话存储路径与 HTTP 路由（见 RC15）
- 比较 RULE591 / RULE597 / RULE759 / RULE792 / RULE815：findings — version_conflict：图片生成未填种子时的默认值（见 RC16）
- 比较 RULE95 / RULE96 / RULE347 / RULE492 / RULE545 / RULE520 / RULE426 / RULE593 / RULE591：findings — version_conflict：模型目录与产品能力范围（见 RC17）
- 比较 RULE455 / RULE694 / RULE695 / RULE700 / RULE728 / RULE605 / RULE789：findings — version_conflict：前端标签页的地址栏 hash 与首屏标签（见 RC18）
- 比较 RULE449 / RULE978 / RULE789：findings — version_conflict：前端在浏览器存储中记忆状态（见 RC19）
- 比较 RULE671 / RULE670 / RULE560 / RULE716 / RULE793：findings — version_conflict：聊天消息列/输入区在宽窗口下的宽度（见 RC20）
- 比较 RULE710 / RULE733 / RULE560 / RULE716：findings — version_conflict：视觉验收的窗口宽度范围（见 RC21）
- 比较 RULE708 / RULE731 / RULE997：findings — version_conflict：界面动效（见 RC22）
- 比较 RULE718 / RULE437 / RULE439 / RULE890 / RULE923 / RULE924：findings — version_conflict：视频页与音乐页的布局（见 RC23）
- 比较 RULE109 / RULE406 / RULE407 / RULE688 / RULE687 / RULE667 / RULE673 / RULE431 / RULE689：findings — needs_clarification：菜单栏与窗口状态条显示同一持有状态与内存读数（见 RC24）
- 比较 RULE323 / RULE1028 / RULE1010 / RULE821 / RULE915：findings — version_conflict：H3 视频生成的内部内存预算（见 RC25）
- 比较 RULE342 / RULE460 / RULE760 / RULE840 / RULE781 / RULE912：findings — version_conflict：启动媒体作业前是否检查模型完整度（见 RC26）
- 比较 RULE244 / RULE542 / RULE594：findings — version_conflict：开发模式下各媒体运行时的解释器布局（见 RC27）
- 比较 RULE589 / RULE662 / RULE625 / RULE561 / RULE1002 / RULE709 / RULE600：findings — needs_clarification：图片页与其他界面视觉验收所用的截图证据（见 RC28）
- 比较 RULE562 / RULE561 / RULE559：findings — unreachable_condition：对 desk/static 的 UI 改动进行基线核对（见 RC29）
- 比较 RULE788 / RULE577 / RULE650 / RULE1052 / RULE605：findings — exception_ambiguity：首次进入图片页、没有任何会话时（见 RC30）
- 比较 RULE398 / RULE397 / RULE417 / RULE111：findings — exception_ambiguity：退出 App 时 8766 端口上有非台面进程监听（启动时曾判为端口冲突）（见 RC31）
- 比较 RULE739 / RULE319 / RULE325 / RULE155 / RULE184：findings — needs_clarification：两个媒体作业（如视频与音乐）同时被请求且预算判定装得下（见 RC32）
- 比较 RULE1007 / RULE1009 / RULE547 / RULE549 / RULE1005 / RULE1028：findings — needs_clarification：视频请求画幅面积超过 768×1344（见 RC33）
- 比较 RULE3 / RULE6 / RULE7 / RULE9 / RULE2 / RULE14 / RULE183 / RULE184 / RULE185 / RULE186 / RULE507 / RULE187 / RULE4 / RULE5 / RULE8 / RULE147 / RULE495 / RULE1 / RULE489：compatible — budget spec 与 budget 设计以「改：」逐条显式改写 R-arbiter-01/04/05/07、声明 02/03/06 不变，属跨版本的显式覆盖（supersedes 已记录），不是同一版本下的对立；arbiter 负责「谁占着」、budget 负责「装得下什么」的分工也互补。README 等未被覆盖的旧表述另见 findings
- 比较 RULE40 / RULE49 / RULE41 / RULE484 / RULE491 / RULE486 / RULE227 / RULE240 / RULE128 / RULE448 / RULE447 / RULE143 / RULE461 / RULE263 / RULE54 / RULE264 / RULE245 / RULE258 / RULE248 / RULE249 / RULE537 / RULE571：compatible — 网关监听 0.0.0.0、无鉴权、默认开启、端口可配置在 spec/设计/overview/README 中一致；测试绑 127.0.0.1 属测试角色范围，LAN 可达由 gateway 自测与人工 runbook 承担，作用域不同不构成矛盾
- 比较 RULE71 / RULE64 / RULE118 / RULE422 / RULE270 / RULE272 / RULE144 / RULE463 / RULE452 / RULE459 / RULE18 / RULE399：compatible — 前端不直连 8767、对话经本服务转发、测试不触碰 8767 的各条规则对象一致、效果同向
- 比较 RULE188 / RULE192 / RULE218 / RULE194 / RULE195 / RULE211 / RULE217 / RULE521 / RULE544 / RULE266 / RULE198：compatible — budget 非目标中的「不做 skill 机制」限定于 budget 模块并写明另行立项，skills spec 即该立项；skill 外部安装是用户主动下载指令文本，不是推理请求，「不上云」指推理与请求不发到云端；工具调用在 skills 与网关两处都排除，方向一致
- 比较 RULE202 / RULE203 / RULE204 / RULE206 / RULE205 / RULE160 / RULE212 / RULE213 / RULE200 / RULE178 / RULE180 / RULE182 / RULE514 / RULE215：compatible — skill 占用与压缩预算的规则在 skills spec 中显式衔接 R-budget-16 与压缩（扣除 skill 占用、skill 不进 messages 故不被摘要替换），不显示猜测分母与 budget 纪律一致
- 比较 RULE103 / RULE358 / RULE359 / RULE360 / RULE90 / RULE380 / RULE381 / RULE93 / RULE387 / RULE533 / RULE39 / RULE488 / RULE363 / RULE131：compatible — 删除模型需显式确认且限于 models 根、卸载永不删除模型权重、破坏性验收只在临时目录：各条对同一对象（模型权重）均为保护性要求，无对立
- 比较 RULE110 / RULE111 / RULE112 / RULE113 / RULE107 / RULE482 / RULE477 / RULE535 / RULE403 / RULE400 / RULE402 / RULE401 / RULE395 / RULE90 / RULE379 / RULE389：compatible — 不自启、关窗不退、Quit 才停服务在 spec/设计/overview/README 一致；R-shell-06「不写 LaunchAgent」与卸载脚本「移除旧 LaunchAgent」是写入与移除两个不同动作，不冲突（存量兼容框架问题另见 findings）
- 比较 RULE1075 / RULE872 / RULE813 / RULE909 / RULE910 / RULE916 / RULE940 / RULE736 / RULE574 / RULE818 / RULE875 / RULE869 / RULE1083 / RULE1087 / RULE1070：compatible — 「视频/音乐页不改、session_id 可省略、jobview 保留」限定于图片会话与底座两块的版本范围，并写明由第 2、3 块改为必填/改造；音乐、视频会话设计正是这些后续块，属分步上线的跨版本安排
- 比较 RULE429 / RULE456 / RULE712 / RULE732 / RULE1094 / RULE559 / RULE683 / RULE665：compatible — 只有一套深色主题在 ui 设计、候选基线、素材库完成标准、视觉记忆中一致
- 比较 RULE783 / RULE784 / RULE580 / RULE601 / RULE895 / RULE928 / RULE785：compatible — 「种子」只出现在高级参数内；D-50a 是用户明确决定的例外（仅素材库页），视觉标准同样写明豁免，例外边界清楚
- 比较 RULE124 / RULE444 / RULE969 / RULE994 / RULE995 / RULE531：compatible — 首版素材库「面板内就地播放」被素材库预览设计（2026-09-30）以预览弹层取代顶部播放区，R-ui-06 的「点击播放、回填」在新形态中仍成立，属后续版本有意调整
- 比较 RULE129 / RULE453 / RULE145 / RULE466 / RULE130 / RULE487：compatible — ui spec 把 DOM 交互列为人工 reality gate，e2e 模块（D-0001 后新增）把同类旅程改为自动验收；二者是不同模块的验收方式，e2e 并未取消人工 runbook，真生成仍按 overview 规则留 reality gate
- 比较 RULE330 / RULE339 / RULE848 / RULE80 / RULE855：compatible — media 首版在 finally 释放许可；媒体底座 B-38b 显式改为模型子进程退出即释放且只释放一次，compose 不拿许可，属后续版本的明确修订
- 比较 RULE180 / RULE693 / RULE450 / RULE702 / RULE729 / RULE692：compatible — 压缩保留全部原始消息针对已入库消息；被打断/中断的半成品不写回会话、或以「已停止」说明呈现，二者对象不同，不矛盾
- 比较 RULE89 / RULE532 / RULE370 / RULE377 / RULE378 / RULE83 / RULE474：compatible — 安装到 /Applications 在 spec、设计与 README 一致；验收只对临时目录执行属测试角色范围
- 比较 RULE924 / RULE1012 / RULE1013 / RULE1016 / RULE1096 / RULE1025 / RULE524：compatible — 视频会话的「现有三档」画幅被画幅设计（2026-10-07）显式扩展为方向×三档+自定义，默认仍为 512×288，属后续版本明确修订
- 比较 RULE899 / RULE901 / RULE921：compatible — 音乐卡片「文件已不在」由 V-10 显式统一为「音频文件已不在」，属后续块的明确修订
- 比较 RULE104 / RULE346 / RULE367 / RULE353 / RULE172：compatible — 下载只在媒体作业进行中被拒、LLM 驻留不阻塞，与 R-budget-13「无参调用只回答归属」方向一致
- 比较 RULE938 / RULE604 / RULE736：compatible — 「用这张生成视频」是视频会话块（2026-09-27）给图片页加的按钮，属于图片页元素；图片会话块的「不改视频音乐页」与视觉标准「视频/音乐元素不得出现在图片页」均为该块的版本范围，未发现同条件对立
- 比较 RULE855 / RULE868 / RULE946 / RULE549 / RULE956：compatible — ffmpeg-only 作业跳过 arbiter 与内存提醒、D1 估算沿用普通视频并标 predicted，与软限制记忆的落地方式一致
- 比较 RULE844 / RULE953 / RULE954 / RULE558 / RULE1071 / RULE918：compatible — 参考素材不能与首尾帧同用、ref-audio 2–15 秒、续写取末帧作首帧在 spike 事实与各块规则中一致
- 比较 RULE141 / RULE468 / RULE445 / RULE941 / RULE911 / RULE816 / RULE817 / RULE568：compatible — 回填从首版的「表单字段回填」演进为「回到原会话执行在这段基础上改，找不到则按字段回填」，后续块显式规定了找不到会话时的字段回填路径，旅程 J6 只要求表单出现当时参数，未发现同条件对立
- 比较 RULE758 / RULE842 / RULE909 / RULE916 / RULE945 / RULE946：compatible — session_id 必填与错误文案在图片、音乐、视频、配乐中一致沿用 IS D-18
- 比较 RULE1037 / RULE1072 / RULE1084 / RULE1088 / RULE1091 / RULE1093 / RULE1097 / RULE193 / RULE148 / RULE506 / RULE550 / RULE551：compatible — 2026-09-17 以后的各设计与用户记忆对「未发布、不谈兼容/迁移」的表述一致；它们与首版收编/兼容规则的关系另见 findings
- 比较 RULE742 / RULE755 / RULE823 / RULE824 / RULE307 / RULE306 / RULE822：compatible — 媒体会话存储的写入纪律、id 规则与锁由 B-02 显式继承 IS D-02/D-15，后者又沿用聊天 SessionStore 的写法；B-01 改的是目录划分，不改写入纪律
- 比较 RULE761 / RULE841 / RULE1009 / RULE760 / RULE840：compatible — 启动失败不写会话（IS D-21）由 B-33 继承、Z-03 的画幅校验也明确落在会话写入之前，校验顺序在 D-20/B-32 中一致扩展
- 比较 RULE768 / RULE769 / RULE864 / RULE1043 / RULE578 / RULE587 / RULE812：compatible — 删除会话只删分组、作业继续、成品留在素材库、引用为单向指针，在图片会话与媒体底座之间一致
- 比较 RULE900 / RULE931 / RULE906 / RULE907 / RULE908 / RULE874：compatible — 成片/单段切换、续写链说明与重新拼接在音乐与视频卡片中按同一机制规定，均落实 B-75 给下游的约束
- 比较 RULE834 / RULE1073 / RULE955 / RULE952 / RULE827：compatible — 参数白名单按 kind 保存，B-13 预留第 3 块扩充白名单，配乐参考设计据此新增 mode/audio_start/ref_image 记录
- 比较 RULE922 / RULE882 / RULE881 / RULE921：compatible — 控制器改名与文案参数化都以「图片页逐字不变、image_pane 测试断言不改」为约束，三处一致
- 比较 RULE938 / RULE939 / RULE1018 / RULE1019：compatible — 「用这张生成视频」跨页传递首帧引用，画幅设计把同一入口纳入首帧跟随来源并补充尺寸读取，二者互补
- 比较 RULE1007 / RULE1008 / RULE1015 / RULE1031：compatible — 合法画幅规则、违规文案顺序、自定义输入的拦截与单测边界属同一校验规则的分项，彼此一致
- 比较 RULE757 / RULE839 / RULE838：compatible — 会话列表摘要字段由 B-31 继承 IS §3.1，并只对 video/music 的 cover 补充 joined_output 优先，属显式扩展
- 比较 RULE802 / RULE893 / RULE927：compatible — 三种媒体的空会话两行提示按同一模式分别规定，文案对象不同，不冲突
- 比较 RULE809 / RULE810 / RULE879 / RULE1047：compatible — 忙碌原因与 session_not_found 自动切换由共用控制器 M-01 承接 IS 原规则，名词参数化，行为一致
- 比较 RULE814 / RULE910 / RULE940 / RULE804：compatible — main.js 对各 kind 作业的派发由图片、音乐、视频三块依次改为各自页面 applyJob，后块显式替换前块对 jobView 的使用
- 比较 RULE754 / RULE835 / RULE767：compatible — 尝试记录只由后端写（IS D-14）由 B-20 显式继承，前端只重取不落定（D-27）与之一致
- 比较 RULE825 / RULE750 / RULE751 / RULE752 / RULE753 / RULE811 / RULE879：compatible — 标题规则与重命名由 B-04、M-01 显式继承 IS D-10–D-13、D-89，仅把 music 的标题来源改为 caption，属扩展
- 比较 RULE880 / RULE797：compatible — 展开卡片大图自适应是图片页专属，M-02 规定控制器只在 image 节点存在时调用页面回调，承接 D-74 而不改变其行为
- 比较 RULE1090 / RULE942 / RULE943 / RULE913 / RULE557：compatible — 配乐范围（D1 实验性 + D2 默认）与视频会话把配乐留给 3b、用户记忆中的媒体会话计划一致
- 比较 RULE1092 / RULE965 / RULE967 / RULE968 / RULE970 / RULE457：compatible — 素材库预览为纯前端改造、不改后端接口、历史仍取最近 200 条，与 ui 首版「进入面板+操作后拉取」一致
- 比较 RULE837 / RULE1074 / RULE900 / RULE850：compatible — chain 回溯的防环与断链处理在后端（B-22、B-40）与前端链路说明（M-31 遇缺段以「…」开头）中一致
- 比较 RULE914 / RULE952 / RULE953 / RULE925：compatible — V-00b 只排除尾帧与参考视频的会话选取；配乐参考新增的是参考图（ref_image）槽，可从图片会话选，对象不同，不冲突
- 比较 RULE966 / RULE977 / RULE980 / RULE987 / RULE988：compatible — 素材库只做缩略图/列表/明细三视图，排除分栏与画廊，工具栏与三视图规则与此一致
- 比较 RULE926 / RULE957 / RULE958：compatible — 「从图片会话选首帧」选择框由配乐设计泛化为 openMediaPicker 并保留标题与空态文案，属显式替换实现、行为一致
- 比较 RULE979 / RULE975 / RULE978：compatible — 筛选为空的提示与筛选取值、筛选记忆属同一工具栏规则，彼此一致
- 比较 RULE10 / RULE11 / RULE12 / RULE13 / RULE15 / RULE16 / RULE17 / RULE19 / RULE23 / RULE26 / RULE27 / RULE28 / RULE29 / RULE30：compatible — arbiter（SRC1 设计 + SRC2 spec）：跨 SRC1、SRC2 对同一模块/主题的规则逐条对照（arbiter 测试、arbiter 验收、currentHolder、deskState 用途、假数据回退、内存压力读数 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE31 / RULE32 / RULE33 / RULE34 / RULE35 / RULE37 / RULE38 / RULE219 / RULE220 / RULE221 / RULE222 / RULE223 / RULE224 / RULE225 / RULE226 / RULE228 / RULE229 / RULE230 / RULE231 / RULE233 / RULE235 / RULE236 / RULE237 / RULE238 / RULE243：compatible — foundation（SRC5 设计 + SRC6 spec）：跨 SRC5、SRC6 对同一模块/主题的规则逐条对照（SystemExit、bundle 态 hf 调用、config.json、move 完成与失败、point 收编、resolve 副作用 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE43 / RULE44 / RULE45 / RULE46 / RULE47 / RULE48 / RULE51 / RULE52 / RULE53 / RULE246 / RULE247 / RULE251 / RULE252 / RULE253 / RULE254 / RULE255 / RULE256 / RULE257 / RULE259 / RULE261 / RULE262 / RULE265 / RULE267 / RULE268：compatible — gateway（SRC7 设计 + SRC8 spec）：跨 SRC7、SRC8 对同一模块/主题的规则逐条对照（/v1/chat/completions 流式、/v1/chat/completions 非流式、/v1/messages 流式、/v1/messages 非流式、/v1/models、/v1/models 内容 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE55 / RULE57 / RULE58 / RULE59 / RULE60 / RULE61 / RULE62 / RULE296 / RULE298 / RULE299 / RULE300 / RULE301 / RULE304 / RULE305 / RULE308 / RULE309 / RULE310 / RULE312 / RULE313 / RULE314 / RULE315 / RULE316 / RULE317：compatible — library（SRC9 设计 + SRC10 spec）：跨 SRC9、SRC10 对同一模块/主题的规则逐条对照（Range 解析、append 校验、appendHistory 端点、library 职责、不写代码目录验证、会话 CRUD 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE63 / RULE65 / RULE66 / RULE67 / RULE68 / RULE69 / RULE72 / RULE269 / RULE271 / RULE273 / RULE274 / RULE275 / RULE276 / RULE277 / RULE278 / RULE279 / RULE280 / RULE281 / RULE282 / RULE284 / RULE285 / RULE286 / RULE287 / RULE288 / RULE289 / RULE291 / RULE292 / RULE293 / RULE294 / RULE295：compatible — llm（SRC11 设计 + SRC12 spec）：跨 SRC11、SRC12 对同一模块/主题的规则逐条对照（llm HTTP 状态码、llm 互斥、llm 互斥判断、llm 测试、load 被拒、load 语义 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE73 / RULE74 / RULE75 / RULE76 / RULE77 / RULE78 / RULE79 / RULE81 / RULE320 / RULE321 / RULE322 / RULE324 / RULE326 / RULE327 / RULE328 / RULE329 / RULE332 / RULE333 / RULE334 / RULE335 / RULE336 / RULE337 / RULE338 / RULE340 / RULE341：compatible — media（SRC14 设计 + SRC15 spec）：跨 SRC14、SRC15 对同一模块/主题的规则逐条对照（H3/Music 单点定义、作业产出、作业失败判定、作业状态、作业进度、历史写失败 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE84 / RULE85 / RULE86 / RULE87 / RULE88 / RULE91 / RULE368 / RULE369 / RULE371 / RULE372 / RULE373 / RULE374 / RULE375 / RULE376 / RULE382 / RULE384 / RULE385 / RULE388 / RULE390 / RULE391 / RULE538 / RULE539 / RULE540 / RULE541：compatible — packaging（SRC16 设计 + SRC17 spec + SRC34 README 构建段）：跨 SRC16、SRC17、SRC34 对同一模块/主题的规则逐条对照（Gatekeeper 校验、Info.plist、adhoc 模式、adhoc 签名、packaging reality gate、verify 检查项 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE94 / RULE97 / RULE98 / RULE99 / RULE100 / RULE101 / RULE102 / RULE105 / RULE343 / RULE344 / RULE345 / RULE348 / RULE349 / RULE350 / RULE351 / RULE352 / RULE354 / RULE355 / RULE356 / RULE357 / RULE361 / RULE362 / RULE364 / RULE365：compatible — resources（SRC18 设计 + SRC19 spec）：跨 SRC18、SRC19 对同一模块/主题的规则逐条对照（present 判定唯一、resources 路径、resources 错误、下载续传、下载进度、下载验收 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE106 / RULE108 / RULE115 / RULE116 / RULE392 / RULE393 / RULE394 / RULE396 / RULE404 / RULE405 / RULE408 / RULE409 / RULE410 / RULE411 / RULE412 / RULE413 / RULE414 / RULE415 / RULE418 / RULE419 / RULE420：compatible — shell（SRC20 设计 + SRC21 spec）：跨 SRC20、SRC21 对同一模块/主题的规则逐条对照（DeskAPI 解析、SIGKILL 残留、Swift 路径镜像、deskState 拉取失败、shell reality gate、shell 业务逻辑 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE117 / RULE119 / RULE120 / RULE121 / RULE122 / RULE123 / RULE125 / RULE126 / RULE127 / RULE421 / RULE423 / RULE424 / RULE425 / RULE427 / RULE428 / RULE430 / RULE432 / RULE434 / RULE435 / RULE438 / RULE440 / RULE441 / RULE442 / RULE443 / RULE451 / RULE473 / RULE476 / RULE478 / RULE480 / RULE481 / RULE483 / RULE485 / RULE493：compatible — ui（SRC22 设计 + SRC23 spec + SRC13 总览）：跨 SRC13、SRC22、SRC23 对同一模块/主题的规则逐条对照（App 形态、DOM 写入、下载控件、删除确认、前端、前端 URL 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE132 / RULE133 / RULE134 / RULE135 / RULE136 / RULE137 / RULE138 / RULE139 / RULE142 / RULE146 / RULE458 / RULE462 / RULE464 / RULE465 / RULE469 / RULE470 / RULE471 / RULE472：compatible — e2e（SRC3 设计 + SRC4 spec）：跨 SRC3、SRC4 对同一模块/主题的规则逐条对照（e2e 被替换范围、harness 不递台阶、pageerror、不改 tick、依赖缺失、反同义反复 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE149 / RULE150 / RULE151 / RULE152 / RULE153 / RULE154 / RULE156 / RULE161 / RULE164 / RULE165 / RULE173 / RULE174 / RULE176 / RULE177 / RULE179 / RULE181 / RULE189 / RULE190 / RULE191 / RULE496 / RULE497 / RULE498 / RULE499 / RULE500 / RULE502 / RULE503 / RULE504 / RULE505 / RULE509 / RULE510 / RULE511 / RULE512 / RULE513 / RULE515 / RULE516 / RULE517 / RULE518 / RULE519：compatible — budget（SRC24 设计 + SRC25 spec）：跨 SRC24、SRC25 对同一模块/主题的规则逐条对照（KV dtype 推测、R-budget-12/14/15、budget 验收、fits 集合判定、mlx-lm trim、observe 传感器 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE196 / RULE197 / RULE199 / RULE201 / RULE207 / RULE208 / RULE209 / RULE210 / RULE214 / RULE216：compatible — SRC26 内的同主题细化规则（skill 来源、skill 版本说明、skill 选中、发现方式、坏 skill、多 skill 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE523 / RULE525 / RULE529 / RULE530 / RULE543：compatible — SRC34 内的同主题细化规则（台面状态可见、文生歌曲、本机对话、模型清单、能力缺失界面 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE552 / RULE553 / RULE556：compatible — 用户确认记忆（SRC35–40）：跨 SRC37、SRC38 对同一模块/主题的规则逐条对照（DeepSeek V4、ds4 集成、以图生图入口设想 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE563 / RULE564 / RULE566 / RULE570 / RULE572 / RULE573：compatible — SRC41 内的同主题细化规则（J1 聊天旅程、J10 技能旅程、J11 长对话旅程、J2 回头用户旅程、J4 写歌旅程、J8 做短片旅程 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE575 / RULE576 / RULE579 / RULE581 / RULE583 / RULE584 / RULE585 / RULE586 / RULE588 / RULE590 / RULE646 / RULE647 / RULE648 / RULE649 / RULE651 / RULE652 / RULE653 / RULE654 / RULE656 / RULE657 / RULE658 / RULE659 / RULE660 / RULE661 / RULE1049 / RULE1050 / RULE1051 / RULE1053 / RULE1054 / RULE1055 / RULE1056 / RULE1058 / RULE1059 / RULE1060 / RULE1061 / RULE1062 / RULE1063 / RULE1064：compatible — image-sessions 需求（SRC42 需求 + SRC49 决策日志 + SRC27 对照表）：跨 SRC27、SRC42、SRC49 对同一模块/主题的规则逐条对照（三轮迭代验收、会话内尝试列表、决策日志业务规则 BR-1、决策日志业务规则 BR-2、决策日志业务规则 BR-3、决策日志业务规则 BR-5 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE595 / RULE598 / RULE599：compatible — SRC44 内的同主题细化规则（图片产物验收、图片验证边界、离线 CLI 与仲裁 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE602 / RULE603 / RULE606 / RULE607 / RULE608 / RULE609 / RULE610 / RULE611 / RULE614 / RULE616 / RULE617 / RULE618 / RULE619 / RULE620 / RULE621 / RULE624：compatible — SRC43 §视觉状态 内的同主题细化规则（图片页视觉状态：三轮「生成 → 在这张基础上改 → 再生成」后的时间线、图片页视觉状态：会话内无尝试、图片页视觉状态：会话文件损坏、图片页视觉状态：删除会话确认框、图片页视觉状态：删除正在生成的会话的确认框、图片页视觉状态：别的会话在生成时查看另一会话 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE626 / RULE627 / RULE628 / RULE629 / RULE630 / RULE631 / RULE632 / RULE633 / RULE634 / RULE635 / RULE636 / RULE637 / RULE638 / RULE639 / RULE640 / RULE641 / RULE642 / RULE643 / RULE645：compatible — SRC50 §视觉状态 内的同主题细化规则（视觉证据：attempt-cancelled、视觉证据：attempt-failed、视觉证据：attempt-file-missing、视觉证据：attempt-interrupted、视觉证据：attempt-selected-actions、视觉证据：busy-other-media 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE664 / RULE666 / RULE668 / RULE669 / RULE672 / RULE674 / RULE675 / RULE676 / RULE677 / RULE678 / RULE679 / RULE680 / RULE681 / RULE682 / RULE684 / RULE685 / RULE686 / RULE690 / RULE691 / RULE696 / RULE697 / RULE698 / RULE699 / RULE701 / RULE703 / RULE704 / RULE706 / RULE707 / RULE711 / RULE713 / RULE714 / RULE715 / RULE717 / RULE719 / RULE720 / RULE721 / RULE722 / RULE723 / RULE724 / RULE725 / RULE726 / RULE727 / RULE730 / RULE734 / RULE735：compatible — 视觉/交互候选基线与修复计划（SRC45/46/47）：跨 SRC45、SRC46、SRC47 对同一模块/主题的规则逐条对照（DOM 写入、K2 思考标签、K2 消息样式、Tab 遍历、不修项、交互状态 等），设计为 spec 的细化或同一需求的重复记载，未见相同对象与条件下的相反效果；涉及其他模块的同对象规则已在其他比较组中对照
- 比较 RULE738 / RULE740：compatible — SRC27 §0. 任务与非目标 内的同主题细化规则（图片会话 D-00c、图片会话 D-00e 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE744 / RULE745：compatible — SRC27 §1.2 会话文件 内的同主题细化规则（图片会话 D-04、图片会话 D-05 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE746 / RULE747 / RULE748 / RULE749：compatible — SRC27 §1.3 尝试（Attempt） 内的同主题细化规则（图片会话 D-06、图片会话 D-07、图片会话 D-08、图片会话 D-09 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE762 / RULE763：compatible — SRC27 §3.6 `POST /api/media/image` —  内的同主题细化规则（图片会话 D-22、图片会话 D-23 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE764 / RULE765：compatible — SRC27 §3.7 落定（后端，无前端参与） 内的同主题细化规则（图片会话 D-24、图片会话 D-25 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE770 / RULE771 / RULE772 / RULE773 / RULE774 / RULE775：compatible — SRC27 §5.1 「在这张基础上改」 内的同主题细化规则（图片会话 D-40、图片会话 D-41、图片会话 D-42、图片会话 D-43、图片会话 D-44、图片会话 D-45 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE777 / RULE778：compatible — SRC27 §5.2 「换个构图」 内的同主题细化规则（图片会话 D-46、图片会话 D-47 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE787 / RULE790 / RULE791：compatible — SRC27 §6. 新会话与当前会话 内的同主题细化规则（图片会话 D-61、图片会话 D-64、图片会话 D-65 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE794 / RULE795 / RULE796 / RULE798 / RULE799 / RULE800 / RULE801：compatible — SRC27 §7.1 布局（`#pane-image`） 内的同主题细化规则（图片会话 D-71、图片会话 D-72、图片会话 D-73、图片会话 D-75、图片会话 D-76、图片会话 D-77 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE803 / RULE805：compatible — SRC27 §7.4 生成中（running 尝试卡片） 内的同主题细化规则（图片会话 D-81、图片会话 D-83 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE806 / RULE807：compatible — SRC27 §7.5 失败 / 已取消 / 图片文件已不在 内的同主题细化规则（图片会话 D-84、图片会话 D-85 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE819 / RULE820：compatible — SRC28 §0.4 非目标 内的同主题细化规则（媒体会话底座 B-00b、媒体会话底座 B-00c 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE826 / RULE828 / RULE829 / RULE830 / RULE832 / RULE833：compatible — SRC28 §1.3 尝试 内的同主题细化规则（媒体会话底座 B-05、媒体会话底座 B-07、媒体会话底座 B-08、媒体会话底座 B-09、媒体会话底座 B-11、媒体会话底座 B-12 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE843 / RULE845：compatible — SRC28 §3.3 续写（`continues`） 内的同主题细化规则（媒体会话底座 B-35、媒体会话底座 B-37 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE846 / RULE847 / RULE849 / RULE851 / RULE852 / RULE853：compatible — SRC28 §3.4 自动拼接成片 内的同主题细化规则（媒体会话底座 B-38、媒体会话底座 B-38a、媒体会话底座 B-39、媒体会话底座 B-41、媒体会话底座 B-42、媒体会话底座 B-43 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE854 / RULE856 / RULE857 / RULE858：compatible — SRC28 §3.5 手动合成 `POST /api/media/comp 内的同主题细化规则（媒体会话底座 B-44、媒体会话底座 B-46、媒体会话底座 B-47、媒体会话底座 B-48 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE859 / RULE860 / RULE861：compatible — SRC28 §4. 各 kind 的拼接规则（compose 与自动拼接共 内的同主题细化规则（媒体会话底座 B-50、媒体会话底座 B-51、媒体会话底座 B-52 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE862 / RULE863 / RULE865：compatible — SRC28 §5. 跨会话引用 `refs` 内的同主题细化规则（媒体会话底座 B-55、媒体会话底座 B-56、媒体会话底座 B-58 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE866 / RULE867：compatible — SRC28 §6. `compose.py`（ffmpeg 原语） 内的同主题细化规则（媒体会话底座 B-60、媒体会话底座 B-61 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE871 / RULE873：compatible — SRC28 §8. 前端（本文只做重构） 内的同主题细化规则（媒体会话底座 B-72、媒体会话底座 B-74 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE876 / RULE877 / RULE878：compatible — SRC29 §0. 范围与非目标 内的同主题细化规则（音乐会话 M-00b、音乐会话 M-00c、音乐会话 M-00d 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE883 / RULE884 / RULE885 / RULE886 / RULE887 / RULE888 / RULE889：compatible — SRC29 §1.3 挑选合成模式（`canCompose: true`  内的同主题细化规则（音乐会话 M-05、音乐会话 M-06、音乐会话 M-07、音乐会话 M-08、音乐会话 M-09、音乐会话 M-10 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE891 / RULE892 / RULE894：compatible — SRC29 §2.1 布局（`#pane-music`，与 `#pane- 内的同主题细化规则（音乐会话 M-21、音乐会话 M-22、音乐会话 M-24 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE896 / RULE897 / RULE898：compatible — SRC29 §2.2 提示条 内的同主题细化规则（音乐会话 M-26、音乐会话 M-27、音乐会话 M-28 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE902 / RULE903 / RULE904 / RULE905：compatible — SRC29 §2.4 三个动作 内的同主题细化规则（音乐会话 M-33、音乐会话 M-34、音乐会话 M-35、音乐会话 M-36 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE917 / RULE919 / RULE920：compatible — SRC30 §1. 后端 内的同主题细化规则（视频会话 V-02、视频会话 V-04、视频会话 V-05 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE929 / RULE930 / RULE932 / RULE933：compatible — SRC30 §3.2 卡片 内的同主题细化规则（视频会话 V-30、视频会话 V-31、视频会话 V-33、视频会话 V-34 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE934 / RULE935 / RULE936 / RULE937：compatible — SRC30 §3.3 动作 内的同主题细化规则（视频会话 V-40、视频会话 V-41、视频会话 V-42、视频会话 V-43 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE947 / RULE948 / RULE949 / RULE950 / RULE951：compatible — SRC31 §1. D2 换音轨（后端） 内的同主题细化规则（视频配乐 S-03、视频配乐 S-04、视频配乐 S-05、视频配乐 S-06、视频配乐 S-07 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE959 / RULE960 / RULE961 / RULE962 / RULE963 / RULE964：compatible — SRC31 §4. 界面 内的同主题细化规则（视频配乐 S-30、视频配乐 S-31、视频配乐 S-32、视频配乐 S-33、视频配乐 S-34、视频配乐 S-35 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE974 / RULE976：compatible — SRC32 §1. 条目模型（pure/library_view.js） 内的同主题细化规则（素材库预览 L-04、素材库预览 L-06 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE981 / RULE982 / RULE983 / RULE984 / RULE985 / RULE986：compatible — SRC32 §3. 三种视图 内的同主题细化规则（素材库预览 L-21、素材库预览 L-22、素材库预览 L-23、素材库预览 L-24、素材库预览 L-25、素材库预览 L-26 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE989 / RULE990 / RULE991 / RULE992：compatible — SRC32 §4. 选中与键盘 内的同主题细化规则（素材库预览 L-30、素材库预览 L-31、素材库预览 L-32、素材库预览 L-33 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE993 / RULE996 / RULE998：compatible — SRC32 §5. 预览弹层（widgets/library_previe 内的同主题细化规则（素材库预览 L-40、素材库预览 L-43、素材库预览 L-45 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE999 / RULE1000 / RULE1001：compatible — SRC32 §6. 文件与测试 内的同主题细化规则（素材库预览 L-50、素材库预览 L-51、素材库预览 L-52 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1003 / RULE1004 / RULE1006：compatible — SRC33 §0. 范围与非目标 内的同主题细化规则（视频画幅 Z-00a、视频画幅 Z-00b、视频画幅 Z-00d 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1011 / RULE1014：compatible — SRC33 §2. 方向与档位 内的同主题细化规则（视频画幅 Z-10、视频画幅 Z-13 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1017 / RULE1020 / RULE1021 / RULE1022 / RULE1023：compatible — SRC33 §3. 首帧自动跟随（用户选 A） 内的同主题细化规则（视频画幅 Z-20、视频画幅 Z-23、视频画幅 Z-24、视频画幅 Z-25、视频画幅 Z-26 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1024 / RULE1026：compatible — SRC33 §4. 续写、换个版本、回填 内的同主题细化规则（视频画幅 Z-30、视频画幅 Z-32 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1027 / RULE1029 / RULE1030：compatible — SRC33 §5. 提醒（只提醒，不拦） 内的同主题细化规则（视频画幅 Z-40、视频画幅 Z-42、视频画幅 Z-43 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1032 / RULE1033 / RULE1034：compatible — SRC33 §6. 文件与测试 内的同主题细化规则（视频画幅 Z-51、视频画幅 Z-52、视频画幅 Z-53 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1035 / RULE1036 / RULE1038 / RULE1039 / RULE1040 / RULE1041 / RULE1042 / RULE1044 / RULE1046 / RULE1048：compatible — SRC27 内的同主题细化规则（ImageSessionStore 接口、会话列表四种状态、图片会话错误映射、图片会话需求来源、并发边界、待决问题 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1065 / RULE1066 / RULE1067 / RULE1076 / RULE1077 / RULE1078 / RULE1079 / RULE1080：compatible — SRC28 内的同主题细化规则（compose.py 原语、底座完成标准、底座待决问题、成片、新增错误码、生成接口 seed/continues/refs 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1081 / RULE1082 / RULE1085：compatible — SRC29 内的同主题细化规则（未写到的行为、音乐会话来源、音乐完成标准 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照
- 比较 RULE1086 / RULE1089：compatible — SRC30 内的同主题细化规则（未写到的行为、视频完成标准 等）：彼此为同一机制的分项或补充，未见相同对象与条件下的相反效果；与其他来源的同对象规则已在其他比较组中对照

### RC1 · version_conflict · 待用户澄清
共同条件：同一台机器、聊天模型驻留时发起视频/音乐生成（J3 前置条件）；README 为 0d98e9e 当前版本，budget 修订为 2026-09-17/22，J3 为 2026-10-08 确认旅程，三者在当前构建同时有效
budget spec 明确改写了 R-arbiter-01/04/05（重活并存由预算判定、仅预算不足时最小让出、媒体与聊天可共存，R-budget-17 给出 80.1+27.0 GiB 共存实测），J3 也接受「与视频并存（按预算）」；但当前 README 仍写「同一时刻只有一件重活」「不能同时驻留」「出片期间不能再加载聊天模型」以及「不追求 70B 对话和视频生成同时驻留」。README 与 overview 的旧表述没有被任何来源显式废弃
待确认：README 中「同一时刻只干一件重活」「出片期间不能再加载聊天模型」「不追求同时驻留」是否仍是当前产品承诺？若预算共存是现行规则，README 这些句子是否应视为已被 budget 修订取代？
- RULE520 SRC34:3-3 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=all
> 一台 Mac 上既要本地聊天，又要出视频、出歌。这几类模型都很大，统一内存里装不下两份。这个项目要解决的是：把它们收成一张日常能用的工作台，并且保证同一时刻只有一件重活占着机器。
- RULE526 SRC34:44-44 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=all
> - 聊天模型、视频生成、音乐生成不能同时驻留
- RULE527 SRC34:45-45 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=all
> - 出视频或出歌前，自动让出内存
- RULE528 SRC34:46-46 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=出片期间
> - 出片期间不能再加载聊天模型，也不能开下一个生成任务
- RULE546 SRC34:110-110 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=all
> - 不追求 70B 对话和视频生成同时驻留
- RULE494 SRC13:121-121 · release=2026-08-31 本轮 / platform=unknown / role=all / condition=all
> - 70B 与 H3 同时驻留。
- RULE705 SRC46:33-33 · release=候选（未确认） / platform=unknown / role=all / condition=all
>         "同一时刻只有一个模型持有内存：切换模型时先驱逐再加载，界面显示谁被驱逐、为什么。",
- RULE155 SRC25:51-54 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-budget-07** 重活能否并存由预算判定，预算不足时结果即互斥。
>   判定的输入是**一组**重活而非一对：`fits(workloads)`。三件能否共存不等于
>   三个两两判断的合取，「最小让出」也只有在集合上才算得出来。
>   拒绝必须带机器可读原因与数字：需要多少、现有多少、依据来源为预测还是实测。
- RULE183 SRC25:188-188 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-arbiter-01** 改：重活能否并存由预算判定；预算不足时退化为互斥。持有者由单个变为一组。
- RULE184 SRC25:189-189 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-arbiter-04** 改：拒绝条件由「媒体在跑」变为「预算装不下」。
- RULE185 SRC25:190-190 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-arbiter-05** 改：仅在预算不足时让出，且最小让出。
- RULE507 SRC24:197-200 · release=2026-09-17 budget design / platform=unknown / role=all / condition=all
> | R-arbiter-01 三者互斥，持有者唯一 | 重活能否并存由预算判定；预算不足时结果即互斥。持有者从单个变为一组 |
> | R-arbiter-04 媒体在跑即拒绝加载 LLM | 拒绝条件改为 `fits()` 判否，理由码带数字（需要多少 / 现有多少 / 依据来源） |
> | R-arbiter-05 开媒体前自动卸 LLM | 仅在预算不足时让出，且最小让出（卸最省的那个，非全卸） |
> | R-arbiter-07 加载前比对一次体积 | 持续生效：会话中 KV 增长同样在预算内被监控 |
- RULE166 SRC25:115-115 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-budget-17** 「能不能用这个模型」问的是**台面还持不持有它**，不是「有没有媒体作业在跑」。
- RULE565 SRC41:37-47 · release=旅程声明 2026-10-08 用户确认 / platform=unknown / role=all / condition=聊天模型已加载
> - 情形：此刻有聊天模型驻留在内存；提示词约 80 字；画幅取横屏标准档
> - 进展：不手动卸载任何东西，生成一段带环境声的短视频，并在台面里直接播放
> - 前置：聊天模型已加载
> - 做成的样子：
>   - 视频作业完成
>   - 台面内可播放出画面且有声音
>   - 状态条显示聊天模型已被让出或与视频并存（按预算）
> - 卡死的样子：
>   - 提示需手动先卸载模型才能开
>   - 作业失败/卡住无进度
>   - 完成后无法在台面内播放

### RC2 · version_conflict · 待用户澄清
共同条件：媒体作业进行中、聊天模型仍被台面持有时的台面聊天、网关请求与 UI 加载按钮；R-llm-06/R-gateway-08/R-e2e-08 原文未被修订，R-budget-17 为后续修订
R-llm-06、R-gateway-08、llm/gateway 设计的准入第一步、R-e2e-08 及其设计用例都以「媒体作业进行中」为拒绝/禁用条件；R-budget-17 认定按 media_busy 拦截台面聊天、网关守卫等是错误，判据应改为 still_holds。budget spec 只列出对 R-arbiter-01/04/05/07 的改写，没有显式废弃 R-llm-06、R-gateway-08、R-e2e-08 中的媒体在跑条件
待确认：R-llm-06 / R-gateway-08 / R-e2e-08 中「媒体作业进行中即拒绝/禁用」的分句是否已被 R-budget-17 取代？若取代，这三条在共存场景下应以什么条件拒绝？
- RULE70 SRC12:20-20 · release=2026-08-31 首版 / platform=unknown / role=all / condition=媒体作业进行中或无模型
> - **R-llm-06** 媒体作业进行中、或当前没有加载模型时，聊天请求被拒绝并带明确原因，不得挂起等待。
- RULE283 SRC11:211-216 · release=2026-08-31 首版 / platform=unknown / role=all / condition=聊天请求
> 前置检查（两个 API 相同，同步、立即，**绝不等待**——R-llm-06）：
> 
> 1. `arbiter.desk_state()` 报媒体作业运行中 → 拒绝 `media_busy`。
> 2. `status != "loaded"` → 拒绝 `no_model_loaded`。
> 3. `request.model` 非空且既不等于当前 key、也不等于 `served_id` → 拒绝 `model_mismatch`
>    （gateway R-gateway-10 依赖这条：不静默换模型）。
- RULE290 SRC11:296-296 · release=2026-08-31 首版 / platform=unknown / role=all / condition=媒体作业在跑
>       desk_state 媒体在跑? → media_busy（立即，绝不排队）
- RULE436 SRC22:146-147 · release=2026-08-31 首版 / platform=unknown / role=all / condition=聊天被拒
> - 被拒（媒体在跑 / 无模型，R-llm-06 的 4xx/503）：在消息流位置内联展示服务端原因，
>   不留空转圈。
- RULE50 SRC8:28-29 · release=2026-08-31 首版 / platform=unknown / role=all / condition=无模型驻留或媒体作业进行中
> - **R-gateway-08** 无模型驻留或媒体作业进行中：返回 `503`，带 `Retry-After` 头与机器可读原因码。
>   **绝不自动加载模型，绝不排队等待。**
- RULE42 SRC8:14-14 · release=2026-08-31 首版 / platform=unknown / role=all / condition=无模型驻留或媒体作业在跑
> **不自动加载模型**：外部请求到达时若没有模型驻留、或媒体作业在跑，一律报错，不抢内存、不排队。
- RULE250 SRC7:162-167 · release=2026-08-31 首版 / platform=unknown / role=all / condition=外部请求到达
> | 判定顺序 | 条件 | 结果 |
> |---|---|---|
> | 1 | `desk_state()["media_busy"]`（即 holder 非空且 `holder["kind"] ∈ {video, music}`） | 503 `media_job_running`（原因码取 `can_start_heavy("llm")` 返回的 `reason["code"]`（arbiter 原因），保持全台面同一套词汇；取不到时用本地常量 `media_job_running` 兜底） |
> | 2 | `llm_status().state != "loaded"` | 503 `no_model_loaded` |
> | 3 | `requested_model` 非空 且 不等于 `loaded.key` 且 不等于 `loaded.served_id` | 503 `model_not_loaded`，message 指明当前驻留的是谁（R-gateway-10：不静默换模型） |
> | 4 | 通过 | 返回 `loaded`（后续调用一律用 `loaded.served_id` 作下游 model） |
- RULE260 SRC7:314-314 · release=2026-08-31 首版 / platform=unknown / role=all / condition=媒体作业进行中
> | 媒体作业进行中 | 503 | `media_job_running`（优先取 arbiter 原因码） | `service_unavailable_error` | `overloaded_error` |
- RULE24 SRC1:292-293 · release=2026-08-31 首版（arbiter design） / platform=unknown / role=all / condition=all
> - gateway：读 `data:deskState`（`media_busy` 或无模型 → 503）。
> - llm / media：acquire 前用 `api:canStartHeavy` 预检给出友好拒绝，acquire 为准。
- RULE140 SRC4:46-47 · release=2026-08-31 首版 / platform=unknown / role=测试 / condition=媒体运行中
> - **R-e2e-08** 互斥在 UI 上可见：媒体运行中，加载按钮与另一媒体按钮均被禁用，状态条给出拒绝原因；
>   媒体结束后恢复可用。
- RULE467 SRC3:307-307 · release=2026-08-31 首版 / platform=unknown / role=测试 / condition=视频作业运行中
> | test_mutex_ui.py | R-e2e-08 | 视频作业闸停在运行中 → 聊天面板「加载」按钮带 `disabled`、音乐面板「生成」带 `disabled`、状态条含拒绝原因文案（来自 `data:deskState.can_start` 的机器可读原因）；放行剧本至 done → 下一 tick 两按钮恢复可用（`not disabled`） |
- RULE166 SRC25:115-115 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-budget-17** 「能不能用这个模型」问的是**台面还持不持有它**，不是「有没有媒体作业在跑」。
- RULE167 SRC25:123-125 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
>   所以在这之后再按 `media_busy` 拦一道，拦掉的是已经付过代价的能力：共存只剩
>   「省一次加载」，兑现不了「边渲染边聊」。曾有四处这样拦着——台面聊天、网关守卫、
>   提示词助手的可用性、断流原因的归因。
- RULE168 SRC25:127-129 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
>   判据统一为 `still_holds(desk_state, kind, label)`：在**全部**持有者里找自己。
>   只看 `holder`（最后授予的那件）是同一个错误的另一种写法——视频一授予它就成了
>   video，于是「别人也拿到了」被读成「我被驱逐了」。

### RC3 · needs_clarification · 待用户澄清
共同条件：外部客户端经网关发请求、且媒体作业在跑时的拒绝判定与对外原因码
R-budget-13 把网关守卫列为无参 can_start_heavy 的归属查询调用点，并把错误码保持为 media_busy 视为正确结果；R-budget-17 又说网关守卫按 media_busy 拦截是需要去掉的四处之一；网关设计的原因码是 media_job_running（优先取 arbiter 原因）。三处对网关在媒体在跑时是否拒绝、以及拒绝码为何不一致
待确认：媒体在跑但聊天模型仍被持有时，网关应放行还是 503？若拒绝，对外原因码应是 media_busy、media_job_running 还是其他？
- RULE169 SRC25:134-134 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-budget-13** **无参的 `can_start_heavy(kind)` 只回答归属问题，绝不做预算算术。**
- RULE170 SRC25:136-137 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
>   今天有六个调用点不传 `params`/`key`（下载闸、网关守卫、台面状态的两个按钮、两处测试台面）。
>   它们问的是「现在谁占着、能不能开这一类」，不是「这个具体作业装不装得下」——后者需要参数。
- RULE171 SRC25:140-141 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
>   `insufficient_budget`**。已复现的后果：驻留模型后「换模型」按钮灰掉、下载可能被误拒、
>   网关对外返回的错误码从 `media_busy` 漂移成 `insufficient_budget`。
- RULE167 SRC25:123-125 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
>   所以在这之后再按 `media_busy` 拦一道，拦掉的是已经付过代价的能力：共存只剩
>   「省一次加载」，兑现不了「边渲染边聊」。曾有四处这样拦着——台面聊天、网关守卫、
>   提示词助手的可用性、断流原因的归因。
- RULE250 SRC7:162-167 · release=2026-08-31 首版 / platform=unknown / role=all / condition=外部请求到达
> | 判定顺序 | 条件 | 结果 |
> |---|---|---|
> | 1 | `desk_state()["media_busy"]`（即 holder 非空且 `holder["kind"] ∈ {video, music}`） | 503 `media_job_running`（原因码取 `can_start_heavy("llm")` 返回的 `reason["code"]`（arbiter 原因），保持全台面同一套词汇；取不到时用本地常量 `media_job_running` 兜底） |
> | 2 | `llm_status().state != "loaded"` | 503 `no_model_loaded` |
> | 3 | `requested_model` 非空 且 不等于 `loaded.key` 且 不等于 `loaded.served_id` | 503 `model_not_loaded`，message 指明当前驻留的是谁（R-gateway-10：不静默换模型） |
> | 4 | 通过 | 返回 `loaded`（后续调用一律用 `loaded.served_id` 作下游 model） |
- RULE260 SRC7:314-314 · release=2026-08-31 首版 / platform=unknown / role=all / condition=媒体作业进行中
> | 媒体作业进行中 | 503 | `media_job_running`（优先取 arbiter 原因码） | `service_unavailable_error` | `overloaded_error` |

### RC4 · needs_clarification · 待用户澄清
共同条件：任意内存规格的机器上，预估内存不足以同时容纳新重活时的处置；用户软限制记忆（2026-09-24/25）晚于 budget 修订（2026-09-17~22），两者在当前构建同时被引用
budget 侧规定预算不足时拒绝并给数字（R-budget-07），要腾掉正在跑的媒体时查询与授予都答「不行」（R-budget-18），并称工作集上限是硬上限、虚拟内存帮不上忙；budget 设计还要求本机无实测前媒体与聊天不并存。用户确认的软限制则要求内存检查只提醒+确认、绝不新增硬拒绝，理由恰是「有虚拟内存」，媒体底座、配乐、画幅设计都沿用了该约束。两边对同一前提（虚拟内存能否兜底）结论相反，适用边界（仅针对新作业类型的估算警告，还是也覆盖 budget 的 fits 拒绝）未写明
待确认：「绝不新增硬拒绝」是否适用于 budget 的 fits()/acquire 拒绝与「不腾掉正在跑的媒体」？还是只约束新作业类型的内存估算提醒？虚拟内存能否兜底这一前提以哪条为准？
- RULE155 SRC25:51-54 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-budget-07** 重活能否并存由预算判定，预算不足时结果即互斥。
>   判定的输入是**一组**重活而非一对：`fits(workloads)`。三件能否共存不等于
>   三个两两判断的合取，「最小让出」也只有在集合上才算得出来。
>   拒绝必须带机器可读原因与数字：需要多少、现有多少、依据来源为预测还是实测。
- RULE158 SRC25:74-77 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=Apple 芯片 / mlx / role=all / condition=all
>   取 `mlx.core.device_info()["max_recommended_working_set_size"]`——`mlx_lm/server.py`
>   启动时会 `mx.set_wired_limit()` 成这个值，而 **wired 的内存按定义不参与换页**，
>   所以它是硬上限：超过去不是慢一点，是分配失败或系统开始杀进程。虚拟内存在这里
>   帮不上忙。
- RULE163 SRC25:103-105 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
>   所以：最小让出只需卸聊天模型时，查询也答「能开」，并在 `release` 里说明会让出谁
>   （界面据此讲「会先卸掉聊天模型」）。要腾掉正在跑的媒体作业时两者都答「不行」——
>   为了开另一件重活静默杀掉用户正在跑的生成，不是台面该替他做的决定。
- RULE175 SRC25:153-154 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=内存压力升高
> - **R-budget-09** 内存压力升高时，按代价从轻到重处置：① 收紧对话额度并立即触发压缩；
>   ② 拒绝新的重活；③ 才是卸载模型或终止作业。压力传感器是兜底闸，不是决策者。
- RULE508 SRC24:203-206 · release=2026-09-17 budget design / platform=unknown / role=all / condition=本机无媒体实测峰值
> **未经本机实测不放宽**：媒体估算的标定值来自 2026-09-08 的一台机器，对别的机器只是预测。
> 预测可以用来**警告**（今天就在这么用），但不足以用来**放宽**限制——
> 在这台机器自己量出峰值之前，媒体与聊天不并存。
> 这与本仓库其它地方的证据纪律一致：没有证据的结论不算结论。
- RULE547 SRC35:11-11 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> New features must work across different hardware (36 GB → 512 GB Macs), but memory checks must stay lenient: estimate → "内存可能不足 / 仍要生成" confirm with force, never a new hard rejection, never hide features by hardware.
- RULE548 SRC35:13-13 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **Why:** user (2026-09-25) — "要考虑不同的硬件，但是不要太严格，因为有虚拟内存". Swap makes overshoot slow, not fatal.
- RULE549 SRC35:15-15 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **How to apply:** new job kinds plug into `memory_estimate.estimate_bytes` soft-warning path; ffmpeg-only jobs skip memory checks; don't cap chain lengths for memory reasons. Related: [[project-visual-baseline-direction]]
- RULE1068 SRC28:23-23 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - 硬件：不同内存的机器都要能用；内存检查只提醒可确认，不新增硬拒绝，不按硬件隐藏功能；续写段数与成片长度不设上限。
- RULE1095 SRC33:5-5 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=all
> **上游** 旧分支提交 `42f8062`（feat/video-size，基于 81 个提交前的旧视频页，不直接合并）；视频会话设计 `2026-09-27-video-sessions-design.md`（V-xx）；配乐设计 `2026-09-27-video-soundtrack-design.md`（S-xx）；内存估算 `desk/media/memory_estimate.py`；硬件软限制（只提醒+确认，不拦）。
- RULE944 SRC31:16-16 · release=2026-09-27 视频配乐 3b / platform=unknown / role=all / condition=all
> - [S-00c] 不新增内存硬拒绝；D1 估算同普通视频。
- RULE1005 SRC33:16-16 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=all
> - [Z-00c] 不改整机内存的「警告 + 确认」（后端 `estimate_bytes` + `force`）；本次的预算提醒是 H3 内部 40 GiB 预算，另一回事，只提醒。
- RULE21 SRC1:237-240 · release=2026-08-31 首版（arbiter design） / platform=unknown / role=all / condition=传入 estimated_bytes
> - 只读预检，不改状态。`ok/reason` 来自 `plan_acquire` 同一张转移表（与 acquire 判定必然一致）。
> - 传入 `estimated_bytes`（调用方从 `data:modelEntry` 的体积换算）时比对当前 `available_bytes`；
>   装不下**不置 `ok=false`**，而是附 `memory_warning`——按 spec 这是加载前警告（UI R-ui-08 弹确认框），
>   不是拒绝。不传体积则 `memory_warning` 恒为 `null`。
- RULE782 SRC27:234-234 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-49] 遇到 `insufficient_memory` 走现有确认框（「内存可能不足」/「仍要生成」），确认后带 `force: true` 重发；取消则什么都不写。

### RC5 · version_conflict · 待用户澄清
共同条件：加载聊天模型前与冷启动额度计算时使用的内存基准
R-arbiter-07、arbiter 设计与 ui 设计以「当前可用内存 available_bytes」比对模型体积并据此警告；budget 设计冷启动公式为 (available − 权重 − 安全余量)；而后续 R-budget-16 规定预算分母是机器自报的重活能力而不是此刻可用内存，且不需要再拍留量。budget spec 对 R-arbiter-07 只改写了「持续生效」，未说明警告基准是否随 R-budget-16 改变
待确认：加载前内存警告与冷启动额度应以「当前可用内存」还是「max_recommended_working_set_size 能力」为分母？budget 设计中的「安全余量」是否已被 R-budget-16 取消？
- RULE9 SRC2:36-36 · release=2026-08-31 首版（arbiter spec） / platform=unknown / role=all / condition=加载模型前
> - **R-arbiter-07** 加载某模型前比对其体积与当前可用内存，装不下要在加载前给出警告（不是加载失败后才说）。
- RULE21 SRC1:237-240 · release=2026-08-31 首版（arbiter design） / platform=unknown / role=all / condition=传入 estimated_bytes
> - 只读预检，不改状态。`ok/reason` 来自 `plan_acquire` 同一张转移表（与 acquire 判定必然一致）。
> - 传入 `estimated_bytes`（调用方从 `data:modelEntry` 的体积换算）时比对当前 `available_bytes`；
>   装不下**不置 `ok=false`**，而是附 `memory_warning`——按 spec 这是加载前警告（UI R-ui-08 弹确认框），
>   不是拒绝。不传体积则 `memory_warning` 恒为 `null`。
- RULE25 SRC1:307-307 · release=2026-08-31 首版（arbiter design） / platform=unknown / role=all / condition=模型体积 > 可用内存
> | 模型体积 > 可用内存 | `ok` 仍真，附警告（加载前，UI 弹确认） | `insufficient_memory` |
- RULE433 SRC22:120-126 · release=2026-08-31 首版 / platform=unknown / role=all / condition=加载模型
> - 「加载」流程（R-ui-08）：
>   1. 取所选 `data:modelEntry` 的体积与最新 `api:memorySnapshot`；
>   2. `mem_warn.js` 纯函数 `needsWarning(modelBytes, snapshot) -> {warn, message}`——
>      判定规则：模型字节数 ≥ 快照可用字节数即警告，message 含双方数字；
>   3. `warn` 为真 → `confirm.js` 弹层，用户确认才继续，取消即中止；
>   4. `api.loadLlm(key)`；加载中轮询 `api:llmStatus` 展示 `loading`，失败展示服务端原因
>      （含 mlx-lm 日志尾部，R-llm-04 提供）。
- RULE454 SRC22:329-331 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **A2 · 内存警告阈值**：`模型声明字节数 ≥ memorySnapshot.available_bytes` 即警告（字段名按 arbiter `data:memorySnapshot` 合同）。
>   不加安全余量系数——arbiter（R-arbiter-07）才是权威判断者，ui 侧这层只是「加载前弹窗」
>   的触发条件，宁可略敏感。
- RULE501 SRC24:143-145 · release=2026-09-17 budget design / platform=unknown / role=all / condition=本机首次装载该模型
>   → 媒体余量：档案无记录 ⇒ unavailable，本次不允许并行
>   ⇒ 额度 = (available − 权重 − 安全余量) ÷ 每 token 字节
>   ⇒ launch_args: --prompt-cache-bytes <额度 × 每 token 字节>、--prompt-cache-size <条数>
- RULE157 SRC25:72-72 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-budget-16** 预算的分母是**机器自报的重活能力**，不是此刻的可用内存。
- RULE159 SRC25:84-86 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
>   它是**静态的机器属性**，和总内存一样：量一次记进实测档案，之后直接读。
>   由此得到三个性质——同一台机器同一个模型永远同一个答案；能力随机器规格自动伸缩；
>   不需要跟踪任何人此刻占了多少。
- RULE160 SRC25:88-89 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=没装 mlx/非 Apple 芯片/字段改名
>   问不出时（没装 mlx、非 Apple 芯片、字段改名）标「算不出」、只用声明窗口，
>   **不拿 `memory_size` 顶替**——那会把 Apple 替系统留的 16% 一起吃掉。
- RULE186 SRC25:191-191 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-arbiter-07** 改：由加载时一次性检查，变为持续生效。

### RC6 · behavior_conflict · 待用户澄清
共同条件：同一份 arbiter 设计（2026-08-31）内，llm 加载前是否调用 canStartHeavy
arbiter 设计流 1 写「llm 不调 can_start_heavy」，流 4 写「llm / media：acquire 前用 api:canStartHeavy 预检给出友好拒绝」，二者对同一调用方给出相反描述；R-budget-18 后来要求查询与授予对同一请求同答案，问题仍与调用顺序相关
待确认：llm 加载路径是否应在 acquire 之前调用 canStartHeavy？以流 1 还是流 4 为准？
- RULE22 SRC1:259-260 · release=2026-08-31 首版（arbiter design） / platform=unknown / role=all / condition=llm 加载
> （llm 不调 can_start_heavy——加载前内存警告由 ui 以 api:memorySnapshot 判定，acquire 为准；
>   estimated_bytes 形参保留给任何想预检的调用方）
- RULE24 SRC1:292-293 · release=2026-08-31 首版（arbiter design） / platform=unknown / role=all / condition=all
> - gateway：读 `data:deskState`（`media_busy` 或无模型 → 503）。
> - llm / media：acquire 前用 `api:canStartHeavy` 预检给出友好拒绝，acquire 为准。
- RULE162 SRC25:95-95 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-budget-18** `can_start_heavy` 与 `acquire_heavy` 对同一个请求必须给同一个答案。

### RC7 · version_conflict · 待用户澄清
共同条件：多件重活同时被台面持有时，deskState、菜单栏、状态条与网关对持有者的读取
arbiter 设计的 deskState 只有单个 holder，media_busy 由 holder.kind 推出；shell 菜单标题与 ui 状态条都按单个 holder 映射文案；budget 规定持有者由单个变为一组，并指出只看 holder 会把「别人也拿到了」读成「我被驱逐了」。deskState 形状与各消费方映射未随之写明
待确认：持有者变为一组后，deskState 的形状、菜单栏/状态条在「聊天+视频」同时持有时应显示什么？只看 holder 的消费方是否均需改为全部持有者？
- RULE20 SRC1:207-211 · release=2026-08-31 首版（arbiter design） / platform=unknown / role=all / condition=all
> - `holder` 空闲时为 `null`；token 不出现在 deskState 里（只回给 acquire 调用方）。
> - `media_busy = holder.kind ∈ {video, music}`。
> - `can_start` 固定两个键：`llm` 与 `media`（video/music 在状态机里同态，合并回答）。
> - deskState **不内嵌内存数字**——「内存里是谁」由 `holder` 回答；
>   实时内存数字走 `api:memorySnapshot`（UI 的状态条两者都消费，避免每次状态读取都开子进程）。
- RULE406 SRC20:202-212 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - 纯映射函数 `menuTitle(for: ShellStatus) -> String`（R-shell-02 的文案唯一来源）：
> 
> | 条件 | 菜单栏标题 |
> |---|---|
> | server = starting | `启动中…` |
> | server = failed/stopped | `服务未运行` |
> | needsSetup（来自 readConfig） | `待设置` |
> | holder == null | `空闲` |
> | holder.kind == llm | `已加载 <holder.label>` |
> | holder.kind == video / music | `出片中` / `出歌中` |
> | deskState 拉取失败但进程还在 | `状态不可读` |
- RULE416 SRC20:370-374 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **A-4 deskState 消费 shape（Phase 1.2 已按 arbiter 合同修正）**：deskState 只有
>   `holder / media_busy / can_start` 三键；shell 只读 `holder`——`null` ⇒ 空闲，否则取
>   `holder.kind`（`llm|video|music`）与 `holder.label`（llm 时为模型目录 key——llm 以 key 作 acquire label）。
>   `needs_setup` 不在 deskState 里，来自 `api:readConfig`（`data:deskConfig`）。
>   多余字段忽略，缺字段降级为「状态不可读」——arbiter 侧增删字段不需要 shell 同步发版。
- RULE431 SRC22:106-110 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - `desk_state.js` 纯函数 `renderState(deskState, memSnapshot) -> {memText, holderText, mediaText, nextText, tone}`：
>   - 内存显示 `已用 X.X / 总 Y GB（可用 Z GB）`，由快照字节数格式化，**不存在任何常量 128**；
>   - `holderText`：`空闲` / `LLM：<名称>` / `视频生成中` / `音乐生成中`；
>   - `nextText`：`可开下一件重活` 或 `不可：<机器可读原因的中文文案>`；
>   - `tone`: `ok | busy | error`，决定状态条配色。
- RULE250 SRC7:162-167 · release=2026-08-31 首版 / platform=unknown / role=all / condition=外部请求到达
> | 判定顺序 | 条件 | 结果 |
> |---|---|---|
> | 1 | `desk_state()["media_busy"]`（即 holder 非空且 `holder["kind"] ∈ {video, music}`） | 503 `media_job_running`（原因码取 `can_start_heavy("llm")` 返回的 `reason["code"]`（arbiter 原因），保持全台面同一套词汇；取不到时用本地常量 `media_job_running` 兜底） |
> | 2 | `llm_status().state != "loaded"` | 503 `no_model_loaded` |
> | 3 | `requested_model` 非空 且 不等于 `loaded.key` 且 不等于 `loaded.served_id` | 503 `model_not_loaded`，message 指明当前驻留的是谁（R-gateway-10：不静默换模型） |
> | 4 | 通过 | 返回 `loaded`（后续调用一律用 `loaded.served_id` 作下游 model） |
- RULE183 SRC25:188-188 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-arbiter-01** 改：重活能否并存由预算判定；预算不足时退化为互斥。持有者由单个变为一组。
- RULE168 SRC25:127-129 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
>   判据统一为 `still_holds(desk_state, kind, label)`：在**全部**持有者里找自己。
>   只看 `holder`（最后授予的那件）是同一个错误的另一种写法——视频一授予它就成了
>   video，于是「别人也拿到了」被读成「我被驱逐了」。

### RC8 · behavior_conflict · 待用户澄清
共同条件：当前 README（0d98e9e）的内容
packaging 设计要求 README 改写为真实行为且「不得再写『推理不出门』」，并有机检测试断言 README 不含该表述；当前 README 第 20 行仍写「推理不出门，成品不出门」，同时第 88 行写默认网关监听 0.0.0.0:8770 无鉴权。同一份 README 对外部可达性给出相反陈述
待确认：README 的「推理不出门」是否应保留（例如改为限定条件），还是按 packaging 设计删除？
- RULE92 SRC17:28-29 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **R-packaging-09** README 改写为安装后的真实行为，含：不自启、菜单栏形态、模型目录位置与收编、
>   以及对外 API 监听 `0.0.0.0` 且无鉴权这一事实。
- RULE383 SRC16:228-239 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 改写为**安装后的真实行为**，必须包含：
> 
> 1. 安装：`scripts/build-app.sh` → 拷 `/Applications`；签名形态（Developer ID + hardened runtime，
>    **未公证**，首启可能需右键打开）。
> 2. **不自启**：删除「开机自启」表述；旧 LaunchAgent 由 `uninstall-app.sh`（或安装 runbook）卸除；
>    B20 改写为「打开 App 即全部可用」。
> 3. 菜单栏形态：关窗不退、菜单栏 Quit 才停服务。
> 4. 模型目录：默认 `~/Library/Application Support/LocalModelDesk/models`，首运可改；
>    既有 339G 走收编不重下；换机器 = 装 App 后在资源面板补下。
> 5. **对外 API 事实陈述**：OpenAI + Anthropic 兼容接口监听 `0.0.0.0:8770`、**无鉴权**，
>    同网段任何设备可驱动本机模型（Phase 0 人类确认的风险，README 不得再写「推理不出门」）。
> 6. 旧脚本已删除，对应操作在 App 内的位置。
- RULE386 SRC16:316-316 · release=2026-08-31 首版 / platform=unknown / role=测试 / condition=all
> | `test_readme_states_real_behavior` | README 含 `0.0.0.0:8770` 与「无鉴权」事实陈述、默认模型目录路径；不含「推理不出门」、开机自启表述、四个已删旧脚本名（R-packaging-09 机检半；菜单栏行为归 reality gate） |
- RULE40 SRC8:7-9 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 监听 `0.0.0.0`，**无令牌鉴权**。已向人类声明：同网络任何设备、以及本机浏览器里任何知道端口的页面
> 都能驱动模型并读取输出，且与 README 原有的「推理不出门」冲突。人类确认后仍如此选择。
> README 将被改写为实际行为。
- RULE486 SRC13:48-50 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> `0.0.0.0` + 无鉴权 意味着同一网络上的任何设备、以及本机浏览器里任何知道端口的页面，
> 都可以驱动本机模型并读取输出。这与 README 现有的「推理不出门」冲突。
> 按人类明示执行，README 将改写为实际行为。收紧成令牌校验是 `gateway` 单模块约 20 行的改动。
- RULE522 SRC34:20-20 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=all
> 一个人、一台大内存 Mac、模型都放本机。推理不出门，成品不出门。
- RULE537 SRC34:88-88 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=all
> - 默认网关监听 `0.0.0.0:8770`，同一局域网的设备可访问。本服务无鉴权；请只在可信网络中启用，或在设置中关闭网关。

### RC9 · version_conflict · 待用户澄清
共同条件：构建与分发签名流程
首版 packaging spec/overview 写明不做公证、公证与对外分发不在本轮；qwen-image 文档（2026-09-23）也写本次不公证。当前 README 增加了设置 LMD_NOTARY_PROFILE 后自动提交公证并 staple 的分发路径，没有来源说明公证何时纳入范围
待确认：公证/分发是否已纳入当前范围（作为可选路径）？首版「不做公证」是否被取代？
- RULE82 SRC17:7-7 · release=2026-08-31 首版 / platform=macOS / role=all / condition=all
> 人类明示：Developer ID Application 签名 + hardened runtime，**不做公证**。
- RULE479 SRC13:38-38 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> | 签名 | Developer ID Application 签名 + hardened runtime；**不做公证** | 人类 |
- RULE490 SRC13:117-117 · release=2026-08-31 本轮 / platform=unknown / role=all / condition=all
> - 公证（notarize）与对外分发：需要 App Store Connect 凭据，人类已选择跳过。
- RULE596 SRC44:66-66 · release=2026-09-23 / platform=unknown / role=all / condition=all
> 修改安全权限或覆盖现有应用。签名不等于公证；本次不公证、不发布安装。
- RULE534 SRC34:82-82 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=设置 LMD_NOTARY_PROFILE
> 之后出包时带上 `LMD_NOTARY_PROFILE=LocalModelDesk ./scripts/build-app.sh`，脚本会自动提交公证并 staple。不设该变量时只做 Developer ID 签名，本机可用、别的机器会被 Gatekeeper 拦。

### RC10 · needs_clarification · 待用户澄清
共同条件：处理用户机器上既有数据（已有模型目录、旧 outputs/history.jsonl、.m4a/.webm 旧成品、旧 LaunchAgent）的规则
首版 foundation/library/packaging 规则包含收编旧目录、一次性复制旧历史、兼容旧成品后缀、卸载旧 LaunchAgent 等兼容性动作；用户确认的记忆与 budget/skills/各会话设计则以「未发布、不存在需要兼容的存量行为、不谈兼容迁移」为前提。收编既有模型目录同时出现在 J7 确认旅程里，可能属于「新机器已有模型树」而非存量兼容，但来源没有区分
待确认：「不谈兼容/迁移」是否覆盖首版的旧历史收编、旧成品后缀兼容与旧 LaunchAgent 卸载？收编已有模型目录（J7）是否被视为正常功能而非兼容框架？
- RULE36 SRC6:37-40 · release=2026-08-31 首版 / platform=unknown / role=all / condition=用户给出 legacy 根
> - **R-foundation-04** 收编既有权重：给定一个 legacy 根（如 `~/LocalModelDesk`），
>   `api:adoptLegacyModels` 识别其中的 `llms/`、`minimax-h3/`、`minimax-music3/`，
>   以「指向」（把 models_root 设成该目录）或「移动」两种方式接管，**任何情况下都不得重新下载、不得删除源**。
>   移动模式必须先校验目标卷剩余空间，不足则拒绝并说明差多少。
- RULE241 SRC5:452-453 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **A5 收编即完成首运**：`adoptLegacyModels` 成功后置 `first_run_done=True`——它是首运
>   面板上与「选目录」并列的另一条完成路径（shell R-shell-07 / ui R-ui-09 均如此消费）。
- RULE114 SRC21:23-23 · release=2026-08-31 首版 / platform=unknown / role=all / condition=首运
> - **R-shell-07** 首运弹出 models 目录选择（`NSOpenPanel`），并可选择收编既有目录树。
- RULE446 SRC22:205-211 · release=2026-08-31 首版 / platform=unknown / role=all / condition=needs-setup
> - 全屏引导，两条路径二选一：
>   1. **选择 models 目录**：文本输入框，预填服务端默认
>      （`api:readConfig` 返回的默认 `models_root`）→ `api.completeFirstRun(models_root)`；
>   2. **收编既有目录树**：输入 legacy 根路径 → 先给「指向 / 移动」单选
>      （文案说明二者含义与移动的空间前提）→ `api.adoptLegacyModels(legacy_root, mode)`。
> - 任一调用失败（目录不可写 / 空间不足等）→ 原样展示服务端错误，停留在本页；
>   成功 → 重新走启动序列进入台面。
- RULE536 SRC34:87-87 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=all
> - 首次打开时选择模型目录；默认目录是 `~/Library/Application Support/LocalModelDesk/models`。已有模型可收编已有模型目录：可以直接指向原目录，或把已识别的模型移入新目录，无须重新下载。
- RULE475 SRC13:34-34 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> | 模型位置 | 首运可选目录；默认 `~/Library/Application Support/LocalModelDesk/models`；已有 339G 走**收编**不重下 | 人类 |
- RULE569 SRC41:95-105 · release=旅程声明 2026-10-08 用户确认 / platform=unknown / role=all / condition=首次启动无配置且已有模型树
> - 情形：首次启动（无配置），本机某目录下已有现成模型树
> - 进展：选定或收编模型目录，进入台面，看清每个模型齐/半/没有
> - 前置：config 处于首运状态（实测官须在结束后还原原配置）
> - 做成的样子：
>   - 首运界面出现并可选目录或收编
>   - 进入台面
>   - 资源页每项显示齐/一半/没下
> - 卡死的样子：
>   - 首运界面不出现或无法完成
>   - 收编后模型仍显示没下
>   - 进不去台面
- RULE311 SRC9:180-186 · release=2026-08-31 首版 / platform=unknown / role=all / condition=<data root>/history.jsonl 不存在且 <outputs root>/history.jsonl 存在
> **旧历史一次性收编（census A15，library 自己承担）**：构造时若
> `<data root>/history.jsonl` **不存在** 且 `<outputs root>/history.jsonl` **存在**
> （现状代码把历史写在 outputs 目录内；用户把 `outputs_root` 指回旧 outputs 目录即命中），
> 则把后者**逐字节复制**到数据根——只 copy，**绝不移动、绝不删除源文件**（outputs 目录
> 冻结不可动），复制经 同目录临时文件 + `os.replace` 落地。目标已存在则什么都不做
> （幂等；不合并、不覆盖用户已有新历史）。两个路径均来自 `pathRoots`，无硬编码。
> 旧格式行可被 `list` 直接读取（字段同源，缺 `id` 的旧行照常展示，宽容读）。
- RULE302 SRC9:107-108 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - 扫描 `outputs_root` 一层，后缀 ∈ `{.mp4, .wav, .m4a, .webm}`（后两者兼容既有旧成品文件）；
>   目录不存在返回 `[]` 不报错。
- RULE318 SRC9:308-312 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 9. **旧单会话聊天 `media-gui/chat-history.json` 不自动导入**（census A14）：它位于代码
>    目录，`pathRoots` 里没有任何字段能指向它，App 形态下代码目录也不可依赖；A14 的
>    动作「移到用户数据根、改多会话」由 SessionStore 的新存储设计整体承担。旧文件
>    原地保留、绝不删除（删除旧文件属 packaging A18 清理范畴），用户如需旧内容可
>    自行查看该 JSON——不做静默丢弃，也不伪造成一个「迁移完成」。
- RULE90 SRC17:24-25 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **R-packaging-07** 卸载步骤移除 App 与旧的 `com.aa.localmodeldesk` LaunchAgent；
>   用户数据仅在显式选择时删除；**模型权重在任何情况下都不得被自动删除**。
- RULE379 SRC16:197-199 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 1. **卸 LaunchAgent**（吸收 census A11）：
>    `launchctl bootout gui/$(id -u)/com.aa.localmodeldesk`（容错 `|| true`）；
>    删 `<launch-agents-dir>/com.aa.localmodeldesk.plist`。
- RULE550 SRC36:14-15 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **Why:** LocalModelDesk 从未发布，没有存量用户、没有需要兼容的既有行为。
> 套上兼容/迁移框架之后，论证听着有道理但一个前提都不成立——是空的。
- RULE551 SRC36:19-20 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **How to apply:** 改动现有子系统时，先问「这东西发布了吗、有人在用吗」。
> 没有就直接写对的设计，不谈兼容、不谈灰度、不谈行为不变。
- RULE148 SRC25:23-23 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> 本项目尚未发布，不存在需要兼容的存量行为。
- RULE506 SRC24:193-193 · release=2026-09-17 budget design / platform=unknown / role=all / condition=all
> 本项目尚未发布，不存在存量行为需要兼容，因此不做「降级迁移」，直接按预算写。
- RULE193 SRC26:29-29 · release=2026-09-23 skills / platform=unknown / role=all / condition=all
> 本项目尚未发布，不存在需要兼容的存量行为。
- RULE366 SRC18:416-417 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 1. **key 采用短 id**（h3/music3/glm/superqwen/qwen27/gemma/qwen35/llama70，来自 initModels.sh），
>    `name` 保留 server.py 的中文展示名。旧长 key 不保留别名——这是全量重构，无兼容层（冻结约定：不做兼容行为）。

### RC11 · exception_ambiguity · 待用户澄清
共同条件：move 模式收编且源与目标在同一卷
R-foundation-04 要求任何情况下不得删除源；foundation 设计同卷 move 用 os.rename，验收断言「rename 后源侧子树消失」，并在 A6 中声称这满足「不得删除源」。rename 是否属于「删除源」取决于对「源」指数据还是原路径的解释
待确认：同卷 move 让原 legacy 路径下的子树消失，是否符合「不得删除源」？
- RULE36 SRC6:37-40 · release=2026-08-31 首版 / platform=unknown / role=all / condition=用户给出 legacy 根
> - **R-foundation-04** 收编既有权重：给定一个 legacy 根（如 `~/LocalModelDesk`），
>   `api:adoptLegacyModels` 识别其中的 `llms/`、`minimax-h3/`、`minimax-music3/`，
>   以「指向」（把 models_root 设成该目录）或「移动」两种方式接管，**任何情况下都不得重新下载、不得删除源**。
>   移动模式必须先校验目标卷剩余空间，不足则拒绝并说明差多少。
- RULE232 SRC5:236-236 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> **任何模式、任何分支都不重新下载、不删除源数据。**
- RULE234 SRC5:244-246 · release=2026-08-31 首版 / platform=unknown / role=all / condition=mode=move 且同卷
>   4. **同卷** → 空间检查恒过（rename 不占新空间），对每个子树
>      `os.rename(src, target_root/<name>)`；目标已存在同名非空目录 → 该子树抛
>      `AdoptConflictError`（不合并、不覆盖）；
- RULE239 SRC5:402-403 · release=2026-08-31 首版 / platform=unknown / role=测试 / condition=mode=move 且同卷
> - move 同卷：`tmp_path` 内 src→dst，断言 rename 后源侧子树消失、目标侧内容完整、
>   config 指向目标；目标已有同名非空目录 → `AdoptConflictError`；
- RULE242 SRC5:454-456 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **A6 move 的非破坏语义**：同卷用 `os.rename`（不复制不删除）；跨卷复制后**保留源**并
>   在结果里声明，由用户自行回收。这同时满足 R-foundation-04 的「不得删除源」与本轮
>   「不得删动真实权重」的授权红线；验收一律 `tmp_path`。跨卷空间校验留 1 GiB 安全余量。

### RC12 · version_conflict · 待用户澄清
共同条件：图片作业产出的 PNG 在素材库/成品列表中的呈现
library 首版的成品列表只扫描 .mp4/.wav/.m4a/.webm，历史 kind 只有 video|music；图片会话把 qwen-image-*.png 写入 outputs_root 并要求删除会话后「素材库仍能列出并打开这些图片」，素材库预览把 kind=image 纳入条目，且 L-03 把「历史完成但 output 不在成品列表里」判为 missing。若成品扫描仍不含 .png，图片条目会被判为「文件已不在」
待确认：成品列表（GET /api/outputs）的后缀集合与历史 kind 是否已扩展到 image/.png？首版 library 设计的后缀与 kind 规则是否已被图片会话/素材库预览取代？
- RULE56 SRC10:14-15 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **R-library-01** 列出成品（视频/音频），带时间、类别、字节数。列表来源同时覆盖历史记录与磁盘上的孤儿文件
>   （历史里没有但磁盘上有的成品也要看得见）。
- RULE302 SRC9:107-108 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - 扫描 `outputs_root` 一层，后缀 ∈ `{.mp4, .wav, .m4a, .webm}`（后两者兼容既有旧成品文件）；
>   目录不存在返回 `[]` 不报错。
- RULE303 SRC9:109-111 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - 与 `HistoryStore.by_output()` 按文件名 join：有历史 → 取其 `kind/ts/id`；
>   无历史 → `orphan: true`，`kind` 按前缀推断（`h3-`→video、`music3-`→music、其余→file）。
>   历史里有、磁盘上没有的条目只出现在 `api:listHistory`（那是记录，不是成品）。
- RULE297 SRC9:63-64 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
>   "kind": "video | music",
>   "status": "done | failed | cancelled",
- RULE331 SRC14:198-198 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> { "kind": "video|music", "status": "done|failed|cancelled",
- RULE743 SRC27:32-32 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-03] 图片文件不进会话目录：仍由媒体作业写到 `outputs_root`（`qwen-image-<stamp>-<8hex>.png`），会话只存文件名。
- RULE766 SRC27:188-188 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-26] history 条目：图片作业的 history 条目增加顶层字段 `session_id` 与 `attempt_id`（未挂上会话时为 null）。素材库回填据此找回会话（§8.4）。
- RULE768 SRC27:207-207 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-30] 删除会话只删除 `image-sessions/<id>.json`。`outputs_root` 下的图片、`history.jsonl` 都不动；删除后 `GET /api/outputs` 与 `GET /api/history` 的结果与删除前相同，素材库仍能列出并打开这些图片。
- RULE971 SRC32:26-26 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=all
> - [L-01] 合并规则沿用现状：历史与成品按文件名匹配；一条历史的 `output` 与 `joined_output` 各占一条（B-43）；没匹配到历史的成品单独一条（「无历史记录」）；有历史但文件都不在的也占一条。
- RULE972 SRC32:27-27 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=all
> - [L-02] 每条条目归一为：`{ key, kind: "image"|"video"|"music"|"file", status, ts, title, prompt, spec, duration_s?, width?, height?, bytes?, gen_s?, output?: name, missing: bool, entry?: 历史记录, error? }`。`key` 跨刷新稳定（L-32 靠它保持选中）：有文件用 `o:<文件名>`，否则 `h:<ts>:<kind>:<attempt_id 或空>`，同一次渲染内重复时追加 `#2`、`#3`。
- RULE973 SRC32:28-28 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=all
> - [L-03] `missing`：有历史、状态为完成、`output` 名在成品列表里找不到。
- RULE587 SRC42:28-28 · release=image-sessions 需求 revision 1（2026-09-24 用户确认） / platform=unknown / role=验收 / condition=all
>         "删除会话后会话从列表消失，其中的图片仍能在素材库打开",
- RULE622 SRC43:735-757 · release=image-sessions 视觉验收标准（status passed） / platform=unknown / role=验收 / condition=删除一个含完成尝试的会话
>       "id": "library-after-delete",
>       "title": "删除会话后素材库仍可打开其图片",
>       "design_refs": [
>         "D-30"
>       ],
>       "requirement_refs": [
>         "AC-5"
>       ],
>       "precondition": "删除一个含完成尝试的会话",
>       "steps": [
>         "确认删除",
>         "切到素材库",
>         "预览该图片"
>       ],
>       "must_show": [
>         "图片页会话列表里已无该会话",
>         "素材库列出该图片并能预览出真实图片"
>       ],
>       "must_not_show": [
>         "素材库里该图片缺失或破图",
>         "空白图片框（全局规则）",
>         "主流程出现「种子」一词（全局规则）"
>       ],

### RC13 · version_conflict · 待用户澄清
共同条件：图片会话（同一 2026-09-24 需求 revision 1）中的「在这张基础上改」「换个构图」
已确认需求 BR-9、设计非目标 D-00b、决策日志冻结范围与 qwen 文档都写图生图不在本次范围，记忆写明图片会话跑完后再单独做、先 spike；同一设计内 D-44a/D-47a/D-47b 以「2026-09-24 修订，用户确认」加入以图生图（base + strength），媒体底座 B-10 与 J5「在这张图基础上精修出新的一张并与第一张关联」都依赖它。需求文件仍为 revision 1，决策日志里没有对应修订记录
待确认：以图生图是否已经进入图片会话的范围、BR-9/D-00b 是否被 D-44a 取代？需求 revision 与决策日志是否应有对应修订？
- RULE737 SRC27:18-18 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-00b] 局部重绘 / 图生图不做。
- RULE582 SRC42:21-21 · release=image-sessions 需求 revision 1（2026-09-24 用户确认） / platform=unknown / role=all / condition=all
>         "局部重绘/图生图不在本次范围"
- RULE655 SRC49:34-34 · release=决策日志 2026-09-24 / platform=unknown / role=all / condition=all
>               "局部重绘/图生图不在本次范围"
- RULE1057 SRC27:405-405 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> | BR-9 | 局部重绘/图生图不在本次范围 | D-00b | — |
- RULE663 SRC49:65-67 · release=决策日志 2026-09-24 / platform=unknown / role=all / condition=all
>           "question": "Freeze this product scope?",
>           "chosen": "Freeze explicit scope",
>           "rationale": "本次只做图片会话这一项已确认需求",
- RULE592 SRC44:15-17 · release=2026-09-23 / platform=unknown / role=all / condition=all
> 模型或 MLX 环境未就绪时生成按钮禁用；运行中的作业不能重复提交。
> 分辨率必须为 256–2048 范围内的 16 倍数。文件写入当前配置的成品目录，
> 不会上传到云端。本次新增的是单张文生图，不包含图生图或提示词助手。
- RULE554 SRC38:11-11 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> 用户 2026-09-24 决定：图片会话（image-sessions workflow）跑完之后，再单独做「以图生图」。
- RULE555 SRC38:15-15 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> - 尚未实测该模型的 img2img 能否跑通、质量如何——先做 spike 再立项。
- RULE776 SRC27:225-225 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-44a] 以图生图（2026-09-24 修订，用户确认）：被回填的尝试有图（`status == done`、有 `output` 且文件还在）时，提示条改为「以第 N 次为底稿」；提示条仍在时点「生成图片」，请求带 `base: {attempt_id, strength: 0.6}`，后端以那张图为底稿重绘（保留构图、重画细节），宽高取底稿的宽高。没图的尝试（失败、取消、文件不在）仍按 D-40–D-44 只回填、按文生图生成。提示条隐藏（改了种子或点 ×）后同样退回文生图。
- RULE779 SRC27:231-231 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-47a] 以图生图（2026-09-24 修订）：该尝试有图时，提交带 `base: {attempt_id, strength: 0.35}`，以这张为底稿重绘（保留主体与色调、换构图）。没图的尝试「换个构图」不可用，按钮下方原因行为「这一次没有图片，不能以它为底稿换个构图」。
- RULE780 SRC27:232-232 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-47b] 以图生图的强度只允许 0.6 与 0.35 两档（mflux 约定：强度越高越接近底稿）；后端校验底稿属于同一会话、状态为 done 且文件存在，否则分别返回 400 `invalid_params`、404 `base_not_found`、404 `base_missing`。尝试记录 `base: {attempt_id, strength}`（文生图为 `null`），卡片标题行显示「基于第 N 次」（底稿不在列表中则不显示）。
- RULE831 SRC28:91-91 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-10] `base`：仅 image，含义同 IS D-47b；其他 kind 恒为 `null`。
- RULE567 SRC41:66-75 · release=旅程声明 2026-10-08 用户确认 / platform=unknown / role=all / condition=all
> - 情形：一句约 30 字的提示词
> - 进展：文生图得到一张图，然后在这张图基础上精修出新的一张
> - 前置：无
> - 做成的样子：
>   - 得到第一张图
>   - 在其基础上得到第二张图并与第一张关联
> - 卡死的样子：
>   - 生成失败
>   - 找不到在某张图上继续的入口
>   - 精修结果与原图无关联

### RC14 · behavior_conflict · 待用户澄清
共同条件：图片会话中失败、已取消或文件已不在的尝试卡片展开时
D-86 与 §5 开头写这三种卡片「都显示两个动作按钮，参数都完整可用」，视觉标准 attempt-file-missing 要求「两个动作按钮仍可用」；同日修订 D-47a 规定没图的尝试「换个构图」不可用并显示原因
待确认：失败/取消/文件不在的尝试上，「换个构图」应可用还是禁用并显示「这一次没有图片，不能以它为底稿换个构图」？视觉标准中「两个动作按钮仍可用」是否需随 D-47a 调整？
- RULE808 SRC27:314-314 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-86] 这三种卡片都显示两个动作按钮（§5），参数都完整可用。
- RULE1045 SRC27:215-215 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> 打开（选中）任意一次尝试——包括失败、已取消、图片文件已不在的尝试——都显示这两个按钮（业务规则「打开任意一次尝试后给两个动作」）。正在生成的尝试不显示这两个按钮（它还没有结果）。
- RULE612 SRC43:346-376 · release=image-sessions 视觉验收标准（status passed） / platform=unknown / role=验收 / condition=脚本化执行器让作业非零退出（exit_nonzero，带日志尾部）
>       "id": "attempt-failed",
>       "title": "失败的尝试",
>       "design_refs": [
>         "D-08",
>         "D-09",
>         "D-84",
>         "D-85",
>         "D-86"
>       ],
>       "requirement_refs": [
>         "AC-6",
>         "BR-3",
>         "AC-7"
>       ],
>       "precondition": "脚本化执行器让作业非零退出（exit_nonzero，带日志尾部）",
>       "steps": [
>         "生成并等待作业结束"
>       ],
>       "must_show": [
>         "卡片带「失败」标记与原因标题（describeJobError 的人话，如「生成程序异常退出」）",
>         "缩略图位置是危险色图标块",
>         "展开后「详情」折叠里有 code: message 与日志尾部",
>         "两个动作按钮"
>       ],
>       "must_not_show": [
>         "空白图片框或破图",
>         "只写「失败」而没有原因",
>         "「种子」一词（高级参数折叠时）",
>         "空白图片框（全局规则）",
>         "主流程出现「种子」一词（全局规则）"
>       ],
- RULE613 SRC43:391-420 · release=image-sessions 视觉验收标准（status passed） / platform=unknown / role=验收 / condition=脚本化执行器保持运行，用户点 running 卡片上的「取消」
>       "id": "attempt-cancelled",
>       "title": "已取消的尝试",
>       "design_refs": [
>         "D-09",
>         "D-24",
>         "D-84",
>         "D-85"
>       ],
>       "requirement_refs": [
>         "AC-6",
>         "AC-7"
>       ],
>       "precondition": "脚本化执行器保持运行，用户点 running 卡片上的「取消」",
>       "steps": [
>         "生成",
>         "点「取消」",
>         "等待落定"
>       ],
>       "must_show": [
>         "卡片带「已取消」标记与说明",
>         "缩略图位置是灰色图标块",
>         "两个动作按钮"
>       ],
>       "must_not_show": [
>         "空白图片框",
>         "卡片停留在「生成中」",
>         "「种子」一词",
>         "空白图片框（全局规则）",
>         "主流程出现「种子」一词（全局规则）"
>       ],
- RULE615 SRC43:475-499 · release=image-sessions 视觉验收标准（status passed） / platform=unknown / role=验收 / condition=一次完成尝试后，从 outputs_root 删除其 PNG 文件
>       "id": "attempt-file-missing",
>       "title": "图片文件已不在",
>       "design_refs": [
>         "D-85",
>         "§2 get.output_missing"
>       ],
>       "requirement_refs": [
>         "AC-6",
>         "AC-7"
>       ],
>       "precondition": "一次完成尝试后，从 outputs_root 删除其 PNG 文件",
>       "steps": [
>         "刷新图片页"
>       ],
>       "must_show": [
>         "卡片显示「图片文件已不在」与「可能已在访达中移动或删除」",
>         "灰色图片图标块",
>         "两个动作按钮仍可用"
>       ],
>       "must_not_show": [
>         "浏览器破图标",
>         "空白图片框",
>         "空白图片框（全局规则）",
>         "主流程出现「种子」一词（全局规则）"
>       ],
- RULE779 SRC27:231-231 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-47a] 以图生图（2026-09-24 修订）：该尝试有图时，提交带 `base: {attempt_id, strength: 0.35}`，以这张为底稿重绘（保留主体与色调、换构图）。没图的尝试「换个构图」不可用，按钮下方原因行为「这一次没有图片，不能以它为底稿换个构图」。
- RULE781 SRC27:233-233 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-48] 生成中、正在提交、模型缺失、运行环境不可用、其他媒体作业占用时，该按钮 `disabled`，`title` 与按钮下方一行提示为不可用原因（与「生成图片」按钮同一原因文本，见 §7）。

### RC15 · version_conflict · 待用户澄清
共同条件：媒体会话底座合并后的图片会话存储路径与 HTTP 路由
B-71 要求图片页改用新模块后「IS 全部 D-xx 仍成立」；但 B-01 用 media_sessions_dirs 取代 image_sessions_dir，B-21 要求仓库中不再有 /api/image-sessions 等引用，而 D-01、D-16、D-60、D-94 的原文写的正是这些路径/路由；image-sessions 视觉标准与证据要求的 session-list-load-failed 前置条件仍让 GET /api/image-sessions 返回 500
待确认：D-01/D-16/D-60/D-94 中的旧路径与路由是否视为被 B-01/B-21 取代（行为保留、路径改名）？session-list-load-failed 的证据前置条件应拦截哪个路由？
- RULE870 SRC28:254-254 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-71] 图片页改用该模块后，IS 全部 D-xx 仍成立；图片页 DOM 文本、按钮、文案逐字不变。
- RULE1069 SRC28:27-27 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - 把图片会话存储泛化成按 `kind` 分的媒体会话存储；图片会话迁到新底座上，**图片页行为与文案不变**。
- RULE822 SRC28:57-57 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-01] 三个目录：`data_root/image-sessions`、`data_root/video-sessions`、`data_root/music-sessions`，由 `PathRoots.media_sessions_dirs: dict[kind, Path]` 给出（取代 `image_sessions_dir`）。互不可见。
- RULE836 SRC28:130-130 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-21] 接通要求：`runtime.py` 与 `desk/testing/harness.py` 都传 `media_sessions`；`/api/media-sessions/{kind}` 挂在生产路由与测试外壳路由上。仓库中不再有 `/api/image-sessions`、`ImageSessionStore`、`image_sessions_dir` 的引用。
- RULE741 SRC27:30-30 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-01] 图片会话目录 `PathRoots.image_sessions_dir = data_root / "image-sessions"`，与聊天会话目录 `data_root / "sessions"` 分开；两边的文件互不可见（`GET /api/sessions` 不列出图片会话，反之亦然）。
- RULE756 SRC27:109-109 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-16] 接通要求（Closure）：`runtime.py` 与 `desk/testing/harness.py` 构造 `MediaService` 时都传 `image_sessions=library.image_sessions`；`GET /api/image-sessions` 挂在生产路由和测试外壳路由上。只有文件存在、没人调用不算完成。
- RULE786 SRC27:246-246 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-60] 左上「新会话」按钮（主按钮样式、plus 图标，与聊天页同构）：`POST /api/image-sessions`，新会话成为当前会话、排在列表最上，时间线显示空会话态，焦点移到提示词输入框。每次点击都新建（与聊天页一致）。
- RULE816 SRC27:364-364 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-94] 该条目带 `session_id` 且 `GET /api/image-sessions/{session_id}` 成功、其中有 `attempt_id` 对应的尝试：切到图片页、打开那个会话、选中（展开）该尝试并滚动到它，同时执行该尝试的「在这张基础上改」（D-40–D-42）。
- RULE623 SRC43:772-793 · release=image-sessions 视觉验收标准（status passed） / platform=unknown / role=验收 / condition=Playwright page.route 让 GET /api/image-sessions 返回 500（需在证据里声明为 mock layer）
>       "id": "session-list-load-failed",
>       "title": "会话列表读取失败",
>       "design_refs": [
>         "§7.2"
>       ],
>       "requirement_refs": [
>         "AC-7"
>       ],
>       "precondition": "Playwright page.route 让 GET /api/image-sessions 返回 500（需在证据里声明为 mock layer）",
>       "steps": [
>         "打开 #tab=image"
>       ],
>       "must_show": [
>         "列表位置「会话列表读不出来：<原因>」与「重试」按钮",
>         "「生成图片」禁用，状态行「会话还没加载好」"
>       ],
>       "must_not_show": [
>         "空白的会话列表而无任何说明",
>         "「种子」一词",
>         "空白图片框（全局规则）",
>         "主流程出现「种子」一词（全局规则）"
>       ],
- RULE644 SRC50:401-418 · release=image-sessions 视觉证据要求（2026-10-09 快照） / platform=unknown / role=验收 / condition=Playwright page.route 让 GET /api/image-sessions 返回 500（需在证据里声明为 mock layer）
>       "state_id": "session-list-load-failed",
>       "viewports": [
>         "wide",
>         "narrow"
>       ],
>       "files": [
>         ".allforai/visual-qa/evidence/session-list-load-failed-wide.png",
>         ".allforai/visual-qa/evidence/session-list-load-failed-narrow.png"
>       ],
>       "data_precondition": "Playwright page.route 让 GET /api/image-sessions 返回 500（需在证据里声明为 mock layer）",
>       "steps": [
>         "打开 #tab=image"
>       ],
>       "dom_assertions": [
>         "图片页可见文本（排除展开的「高级参数」details）不含「种子」",
>         "所有可见 img.naturalWidth > 0",
>         "document.scrollingElement.scrollWidth <= clientWidth",
>         "所有可见 button 的 scrollWidth <= clientWidth"

### RC16 · version_conflict · 待用户澄清
共同条件：图片生成未填种子时的默认值
qwen-image 文档（2026-09-23）写默认 seed 42 并建议保留种子 42；图片会话设计（2026-09-24）去掉固定默认 42，省略时后端随机取值，回填缺失时为 null 不再补 42
待确认：qwen-image 文档的「默认 seed 42 / 建议保留 42」是否已被 D-19 取代？
- RULE591 SRC44:10-11 · release=2026-09-23 / platform=unknown / role=all / condition=all
> 1. 在「资源」页下载或校验 Qwen-Image 2.1 + Heretic；已有对应完整模型会复用。
> 2. 打开「图片」，填写提示词，建议保留 1024×1024、40 步、种子 42，然后点「生成图片」。
- RULE597 SRC44:68-72 · release=2026-09-23 / platform=unknown / role=all / condition=all
> HTTP 参数：非空 `prompt`；`width/height` 为 256–2048 内的 16 倍数；
> `steps` 为 1–100，`seed` 为 uint32；默认 1024×1024、40 步、seed 42。
> 无效参数、缺失/不完整模型、缺失运行环境在启动前拒绝；内存预算沿用现有预警及显式确认。
> 图片内存是保守预测值（1024² 约 52 GiB，随更大画幅上调），不是实测 RSS。
> 每个任务输出唯一 PNG 名称和同名来源/参数 JSON；历史记录保存所有输入参数。
- RULE759 SRC27:168-168 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-19] `seed` 可省略：省略时后端用 `secrets.randbelow(2**32)` 取随机值；不再有固定默认值 42（`start_image_job` 签名与 `routes.start_image` 里的 `seed=42` 默认都去掉）。给了就必须是 0–4294967295 的整数（现有校验）。
- RULE792 SRC27:252-252 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-66] 新会话第一次生成使用随机种子：种子框默认为空（`placeholder="留空则每次随机"`），前端在提交时若种子框为空则不传 `seed`，由后端 D-19 取随机值。
- RULE815 SRC27:360-360 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-93] `fillPlan` 对图片条目返回 `{pane:"image", session_id, attempt_id, fields:{prompt,width,height,steps,seed}}`，`seed` 缺失时为 `null`（不再补 42）。

### RC17 · version_conflict · 待用户澄清
共同条件：模型目录与产品能力范围
resources spec/设计规定目录恰为 8 项（h3、music3、6 个 chat）且仓库内只能有一份 repo/路径清单；README「明确不做」写只服务选定的聊天、视频、音乐能力，ui 设计只有五个 tab；qwen-image 文档新增图片模型（image-models/qwen-image-2.1-heretic），并说资源页与准备脚本共用 desk/media/image_model.py 的固定文件清单。图片能力与其清单位置没有在目录/README 规则中出现
待确认：图片模型是否属于单一目录（R-resources-01）的一项？desk/media/image_model.py 的文件清单是否构成「第二份模型清单」？README 的能力范围是否应包含图片？
- RULE95 SRC19:11-13 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 目录共 8 项（3 组）：`h3`、`music3` 各一项，`llm` 组 6 项。
> 每项含：`key`、`name`、`group`(chat|video|music)、`hf_repo`、`relpath`、以及聊天模型的
> `vision`/`quant`/`params`/`gb`。这份目录在仓库里**只能存在一处**。
- RULE96 SRC19:17-18 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **R-resources-01** 单一目录定义，供服务端、前端、以及任何 CLI 入口共同消费；
>   仓库内不得存在第二份模型 repo/路径清单（`initModels.sh` 与 `server.py` 里现有的两份都要消失）。
- RULE347 SRC18:75-77 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 8 条数据从现 `initModels.sh` CATALOG（repo/relpath/size）与 `server.py` MODEL_CATALOG
> （name/vision/quant/params/gb）合并而来，落地后这两处删除（census A01/A02）。
> 这是仓库内**唯一**一处模型 repo/路径清单；前端经 HTTP 取目录，JS 里不复制。
- RULE492 SRC13:119-119 · release=2026-08-31 本轮 / platform=unknown / role=all / condition=all
> - 任意 HF 仓库的自由添加（目录仍是选定的 8 项）。
- RULE545 SRC34:109-109 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=all
> - 不收录任意模型，只服务这张台上选定的聊天、视频、音乐能力
- RULE520 SRC34:3-3 · release=README @0d98e9e（当前） / platform=unknown / role=all / condition=all
> 一台 Mac 上既要本地聊天，又要出视频、出歌。这几类模型都很大，统一内存里装不下两份。这个项目要解决的是：把它们收成一张日常能用的工作台，并且保证同一时刻只有一件重活占着机器。
- RULE426 SRC22:88-89 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - 单页面。结构：顶部 `ui:statusBar`（常驻）→ 五个 tab（聊天 / 视频 / 音乐 / 资源 / 素材库）
>   + 右上角「设置」入口 → 主区域按 tab 显示对应 pane 的 DOM 子树（`hidden` 切换，不销毁）。
- RULE593 SRC44:43-46 · release=qwen-image-mlx 文档（2026-09-23 实测） / platform=unknown / role=all / condition=all
> 资源目录相对于应用配置的 `models_root`：`image-models/qwen-image-2.1-heretic`。
> 资源页与准备脚本使用同一固定文件清单（`desk/media/image_model.py`），逐文件记录源仓库、
> revision、目标路径和精确字节数；两源都校验通过才显示已安装。字节数校验不是内容哈希校验。
> 下载保留 `.cache/localmodeldesk/parts/*.part`，失败后续传；已有完整文件会跳过。
- RULE591 SRC44:10-11 · release=2026-09-23 / platform=unknown / role=all / condition=all
> 1. 在「资源」页下载或校验 Qwen-Image 2.1 + Heretic；已有对应完整模型会复用。
> 2. 打开「图片」，填写提示词，建议保留 1024×1024、40 步、种子 42，然后点「生成图片」。

### RC18 · version_conflict · 待用户澄清
共同条件：前端标签页的地址栏 hash 与首屏标签
ui 设计 A4 规定无前端路由/hash、刷新回到聊天；2026-09-11 修复计划、交互/视觉候选基线与 image-sessions 视觉标准（步骤「打开 #tab=image」）都以 hash 驱动标签页；D-63 只禁止为当前会话改 hash。首版「无 hash」规则未被显式废弃
待确认：标签页是否以地址栏 hash（#tab=...）路由？ui 设计 A4「无 hash、刷新回到聊天」是否已被取代？
- RULE455 SRC22:333-333 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **A4 · 无前端路由/hash**：面板切换纯内存态，刷新回到聊天面板。单窗口 WebView 内无深链诉求。
- RULE694 SRC45:1365-1369 · release=2026-09-11 视觉修复计划 / platform=unknown / role=all / condition=all
> ### Task 19: 首屏标签稳定（未拉的线 #11）
> 
> **缺口原文：** J6 起点窗口停在"音乐"标签，重启后停在"聊天"——首屏状态不确定。
> 
> **根因候选：** `pure/tab_hash.js` 从 `location.hash` 恢复标签；原生壳重新加载时 hash 可能残留上一次的值，也可能为空。
- RULE695 SRC45:1393-1393 · release=2026-09-11 视觉修复计划 / platform=unknown / role=all / condition=all
> `pure/tab_hash.js` 导出 `initialTab(hash)`，对不在白名单内的值一律返回 `"chat"`（done, delegates to existing `tabFromHash`). `main.js` 启动时改用它，并在首运结束后显式 `location.hash = "#tab=chat"` — **BLOCKED**: `main.js` is owned by lane B-core; this lane owns only `pure/tab_hash.js` and `tests/js/main_hash.test.js`. Main session must wire `main.js` line 52 (`showTab(tabFromHash(...))`) to call `initialTab` instead and set `location.hash = "#tab=chat"` after first run.
- RULE700 SRC46:13-13 · release=候选（未确认） / platform=unknown / role=all / condition=all
>         "点标签切换页面时地址栏 hash 同步改变，直接改 hash 也切换页面。",
- RULE728 SRC47:172-175 · release=候选（未确认） / platform=unknown / role=all / condition=all
>     "标签栏在状态条下方，活动标签用强调色文字 + 2px 强调色下划线，非活动为次要文字色、无下划线、无底色。",
>     "标签切换只换内容区，状态条与标签栏不动；地址栏 hash 与活动标签一致。",
>     "设置不是标签页：从右侧抽屉打开，抽屉头部固定在顶部，关闭后回到原来的标签。",
>     "首运页与致命错误页是全屏覆盖层，覆盖期间不显示标签栏。"
- RULE605 SRC43:38-66 · release=image-sessions 视觉验收标准（status passed） / platform=unknown / role=验收 / condition=空数据目录（image-sessions/ 不存在）；图片模型与运行环境可用
>       "id": "first-entry-auto-session",
>       "title": "首次进入：无任何会话时自动新建的空会话",
>       "design_refs": [
>         "D-62",
>         "D-80",
>         "D-10"
>       ],
>       "requirement_refs": [
>         "BR-4",
>         "AC-7"
>       ],
>       "precondition": "空数据目录（image-sessions/ 不存在）；图片模型与运行环境可用",
>       "steps": [
>         "打开 #tab=image"
>       ],
>       "must_show": [
>         "会话列表恰有一项「新会话」且高亮",
>         "时间线居中两行：「还没有图片」与「在下面写下想要的画面，点「生成图片」…」",
>         "「生成图片」按钮可用",
>         "「高级参数」处于折叠状态"
>       ],
>       "must_not_show": [
>         "「请先新建会话」一类提示",
>         "进度条",
>         "任何图片框或缩略图占位",
>         "「种子」一词",
>         "空白图片框（全局规则）",
>         "主流程出现「种子」一词（全局规则）"
>       ],
- RULE789 SRC27:249-249 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-63] 当前会话的恢复（刷新页面或重启 app 后进入图片页）：优先选有 running 尝试的会话；否则选 `updated` 最新的会话。不用浏览器存储、不改地址栏 hash（与聊天页一致，状态只来自服务端）。同一次页面生命周期内切换 tab 再回来，当前会话不变。

### RC19 · version_conflict · 待用户澄清
共同条件：前端在浏览器存储中记忆状态
ui 首版设计规定前端无 localStorage 依赖、不做缓存持久化；素材库预览设计把视图、筛选、缩略图大小、排序存入 localStorage 键 lmd.library；图片会话设计则规定当前会话恢复不用浏览器存储
待确认：素材库视图偏好写入 localStorage 是否为对 ui 首版「无 localStorage 依赖」的有意修订？其他页面的状态是否仍禁止使用浏览器存储？
- RULE449 SRC22:256-258 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 前端唯一的「写」出口是 api.js；面板之间不直接互调，跨面板动作（回填切 tab）经 main.js。
> store.js 只保存 tick 的最新快照与当前会话 id，供各 pane 订阅；不做任何缓存持久化
> （会话与历史的持久化全在 library 模块，前端无 localStorage 依赖）。
- RULE978 SRC32:36-36 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=all
> - [L-11] 视图、筛选、缩略图大小、明细排序记在 `localStorage` 键 `lmd.library`（JSON）；读写都包 try/catch，读不到用默认值（缩略图、全部、200px、`ts desc`）；值非法时回落默认。缩略图大小滑块是普通 `input[type=range]`，方向键只调大小，不移动选中（L-31 只在条目区内生效）。
- RULE789 SRC27:249-249 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-63] 当前会话的恢复（刷新页面或重启 app 后进入图片页）：优先选有 running 尝试的会话；否则选 `updated` 最新的会话。不用浏览器存储、不改地址栏 hash（与聊天页一致，状态只来自服务端）。同一次页面生命周期内切换 tab 再回来，当前会话不变。

### RC20 · version_conflict · 待用户澄清
共同条件：聊天消息列/输入区在宽窗口下的宽度
2026-09-11 修复计划把列宽定为 clamp(680px, 62vw, 1100px)；用户 2026-09-15 改选「消息列跟着窗口变宽」= min(对话区 − 48px, 1400px)，候选视觉基线与图片会话 D-70 也用 1400/24px
待确认：计划中的 1100px 上限是否已被 2026-09-15 的 min(区宽−48, 1400) 取代？
- RULE671 SRC45:114-119 · release=2026-09-11 计划 / platform=unknown / role=all / condition=all
>   --chat-col: clamp(680px, 62vw, 1100px);
> ```
> 
> 第 52 行 `.messages` 与第 59 行 `.composer` 里的 `max-width:820px` 都改成 `max-width:var(--chat-col)`。
> 
> 理由：1440 窗口下 62vw ≈ 893px（留白 ≈ 24%，与参考图 21.7% 同档）；1920 下取上限 1100px（主区 1608px，留白 508px = 26.5%，进入 40% 以内）；900 窗口下取下限 680px 仍不挤压。
- RULE670 SRC45:62-62 · release=2026-09-11 视觉修复计划 / platform=unknown / role=all / condition=all
> - Produces: `.messages` 与 `.composer` 共用同一个响应式宽度上限（两者必须一致，否则输入区与消息列错位）
- RULE560 SRC40:15-15 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **Update 2026-09-15:** after trying a ~1920px window the user rejected the centered narrow reading column (it left ~222px blank on each side) and chose "消息列跟着窗口变宽": message list and composer width = min(chat area − 48px, 1400px). Don't reintroduce a narrow centered chat column; the ≤40% side-whitespace cap from the 2026-09-13 baseline still applies at 2560.
- RULE716 SRC47:62-62 · release=候选（未确认） / platform=unknown / role=all / condition=all
>      "rule": "消息列表与输入区同宽同中心：宽度 = min(对话区宽 − 48px, 1400px)，未到上限时两侧各留 24px；到上限后居中，两侧留白合计不超过对话区宽的 40%（旧基线 L2 列宽子句按 2026-09-15 用户改选替换，L6 的 40% 上限原样保留）。",
- RULE793 SRC27:278-278 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-70] `#pane-image` 与 `#pane-chat` 同构：左侧 `aside.sessions`（宽 248px，复用 `.sessions` 样式与 `card session` 卡片、`session-actions` 的改名/删除图标按钮），右侧 `.image-main` 占满剩余宽度，内容最大宽 1400px，外边距 24px（视觉基线）。`#pane-image` 原来的「表单 | 作业」两栏 grid 与右侧 `.job` 区块取消，作业展示移入时间线里的 running 卡片。

### RC21 · version_conflict · 待用户澄清
共同条件：视觉验收的窗口宽度范围
视觉候选基线 proposed_width_range 为 900–2560，同文件 width_range 记 2026-09-17 用户裁定 900–1920；用户记忆写「≤40% 侧留白上限在 2560 仍适用」
待确认：视觉验收的最大宽度是 1920 还是 2560？2560 下的留白规则是否仍需验收？
- RULE710 SRC47:9-12 · release=候选（未确认） / platform=unknown / role=all / condition=all
>  "proposed_width_range": {
>   "min": 900,
>   "max": 2560,
>   "basis": "899px 媒体面单列断点之上的第一个可用宽 / 常见外接显示器；待用户确认"
- RULE733 SRC47:233-236 · release=2026-09-17 用户裁定 / platform=unknown / role=all / condition=all
>  "width_range": {
>   "min": 900,
>   "max": 1920,
>   "basis": "2026-09-17 用户裁定：contentMinSize 900×600（实测 /window?width=400 被夹到 900）；1920 = 本机逻辑分辨率"
- RULE560 SRC40:15-15 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **Update 2026-09-15:** after trying a ~1920px window the user rejected the centered narrow reading column (it left ~222px blank on each side) and chose "消息列跟着窗口变宽": message list and composer width = min(chat area − 48px, 1400px). Don't reintroduce a narrow centered chat column; the ≤40% side-whitespace cap from the 2026-09-13 baseline still applies at 2560.
- RULE716 SRC47:62-62 · release=候选（未确认） / platform=unknown / role=all / condition=all
>      "rule": "消息列表与输入区同宽同中心：宽度 = min(对话区宽 − 48px, 1400px)，未到上限时两侧各留 24px；到上限后居中，两侧留白合计不超过对话区宽的 40%（旧基线 L2 列宽子句按 2026-09-15 用户改选替换，L6 的 40% 上限原样保留）。",

### RC22 · version_conflict · 待用户澄清
共同条件：界面动效
交互与视觉候选基线都写只有设置抽屉与遮罩有 150ms 动效、没有其他动画；素材库预览设计新增预览弹层遮罩淡入、面板淡入+缩放约 180ms。候选基线尚未确认
待确认：预览弹层的 180ms 动效是否被接受为基线的例外？候选基线「没有其它动效」是否需更新？
- RULE708 SRC46:52-53 · release=候选（未确认） / platform=unknown / role=all / condition=all
>         "抽屉与遮罩 150ms；没有其它动效，也没有加载骨架屏动画。",
>         "系统开启「减弱动态效果」时上述过渡关闭，功能不受影响。"
- RULE731 SRC47:210-211 · release=候选（未确认） / platform=unknown / role=all / condition=all
>     "只有抽屉与遮罩有动效：150ms ease 的透明度过渡。列表、消息、标签切换没有动画。",
>     "系统开启「减弱动态效果」时所有过渡与动画一律关闭。"
- RULE997 SRC32:64-64 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=all
> - [L-44] 动效：遮罩淡入、面板淡入+轻微缩放（180ms 左右）；全局 `prefers-reduced-motion` 规则生效。

### RC23 · version_conflict · 待用户澄清
共同条件：视频页与音乐页的布局
视觉候选基线（2026-09-16，未确认）与 ui 首版设计写视频/音乐页为左表单右任务两栏、表单含帧数；音乐会话与视频会话设计（2026-09-27）删除「表单 | 作业」两栏与 jobview，改为会话式布局，视频以时长档位代替帧数输入
待确认：视觉候选基线中的「左表单右任务两栏」是否已失效、需在下一轮确认时替换？
- RULE718 SRC47:78-78 · release=候选（未确认） / platform=unknown / role=all / condition=all
>      "rule": "视频与音乐页是左表单右任务两栏：表单列不随窗口拉伸，任务区占据其右侧的全部剩余区域，内容左对齐于该区域的左缘；窄档退化成单列，表单在上。",
- RULE437 SRC22:151-153 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - 表单：提示词（textarea）、画幅（预设下拉 512×288 / 768×448 / 1024×576，值即 `宽x高`）、
>   帧数、步数（number，min/max 沿用现行）。
> - 「生成」→ `api.startVideoJob({prompt, width, height, frames, steps})`；
- RULE439 SRC22:163-165 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 与 videoPane 同构，仅表单不同：风格描述、歌词（textarea）、时长（秒）。
> 产出用 `<audio controls>`。二者共用一个「作业渲染」内部辅助（进度/日志/取消/播放器），
> 因为 `data:jobState` 是同一形状。
- RULE890 SRC29:100-100 · release=2026-09-27 音乐会话 / platform=unknown / role=all / condition=all
> - [M-20] 左栏、主区宽度、外边距、窄窗 900×700 规则同 IS D-70、D-78。原 `.form | .job` 两栏与 jobview 删除。
- RULE923 SRC30:46-46 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=all
> - [V-20] 左栏会话、头部「生成视频」+ 模型状态 + 「模型说明」（MiniMax H3 · MLX 本机推理；输出带声音的 MP4；「接着往下生」用上一段的最后一帧作首帧，拼接处可能有动作跳变）、时间线、底部输入区。原表单 + jobview 删除。
- RULE924 SRC30:47-47 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=all
> - [V-21] 输入区（自上而下）：提示条（V-30）；「生成方式」`<select>`（文生视频 / 图生视频 / 视频参考生成）；素材行（按方式出现，V-22）；提示词 `<textarea>`（默认 3 行，聚焦/超出时增高，最高 40vh；placeholder 随方式变化，沿用现有三条）与「生成视频」主按钮（⌘Enter）；「AI 帮写」行；「高级参数」`<details>` 默认折叠：画幅（现有三档）、视频时长（现有六档）、耗时提示（`videoCostNote`）、步数（默认 16，4–50）、种子（留空则每次随机）、「使用素材的声音」勾选（仅图生/参考方式可见，默认勾选）；上传状态行；状态行；错误行。

### RC24 · needs_clarification · 待用户澄清
共同条件：菜单栏与窗口状态条显示同一持有状态与内存读数
R-shell-02 与 shell 设计的菜单标题为「已加载 <label>」「出片中/出歌中」、内存行 x.x GiB；修复计划要求菜单与窗口同一措辞（视频生成中/音乐生成中）、用 display 人类可读名、内存统一取整，并在执行者注中说明网页状态条一侧尚未取整
待确认：菜单栏文案应遵循 R-shell-02 的「出片中」还是与窗口一致的「视频生成中」？内存读数在菜单与状态条是否统一为整数 GiB？
- RULE109 SRC21:17-17 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **R-shell-02** 菜单栏项显示实时台面状态（空闲 / 已加载 XX / 出片中），菜单含「打开窗口」与「退出」。
- RULE406 SRC20:202-212 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - 纯映射函数 `menuTitle(for: ShellStatus) -> String`（R-shell-02 的文案唯一来源）：
> 
> | 条件 | 菜单栏标题 |
> |---|---|
> | server = starting | `启动中…` |
> | server = failed/stopped | `服务未运行` |
> | needsSetup（来自 readConfig） | `待设置` |
> | holder == null | `空闲` |
> | holder.kind == llm | `已加载 <holder.label>` |
> | holder.kind == video / music | `出片中` / `出歌中` |
> | deskState 拉取失败但进程还在 | `状态不可读` |
- RULE407 SRC20:214-216 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - 菜单项：状态详情（禁用行：上表全文 + `内存 已用 x.x / 共 y GiB`，来自 `api:memorySnapshot`）、
>   分隔线、「打开窗口」（`showWindow`）、「退出」（`NSApp.terminate` ⇒ 走 `applicationWillTerminate` 收割）。
>   仅此四类，无更多菜单项（YAGNI）。
- RULE688 SRC45:1116-1116 · release=2026-09-11 视觉修复计划 / platform=unknown / role=all / condition=all
> `desk/arbiter/state.py` 的 holder 序列化处加 `"display": self._display or self._label`；`desk/llm/service.py` 取得许可时把模型 `name` 作为 display 传进去；媒体作业传 `"视频生成中"` / `"音乐生成中"`（与窗口状态条同一措辞，解决 N4）。
- RULE687 SRC45:1096-1096 · release=2026-09-11 视觉修复计划 / platform=unknown / role=all / condition=all
> - Produces: `/api/state` 的 `holder` 增加 `display` 字段（人类可读名）；`menuTitle` 优先用 `display`
- RULE667 SRC45:22-22 · release=2026-09-11 视觉修复计划 / platform=unknown / role=all / condition=all
> - 所有面向用户的字符串是简体中文；同一状态跨面措辞必须一致（基线 D3）。
- RULE673 SRC45:271-271 · release=2026-09-11 视觉修复计划 / platform=unknown / role=all / condition=all
> `MEDIA_LABEL` 定义为 `{ video: "视频生成中", music: "音乐生成中" }`——注意这两句现在只出现在持有者部件里，右侧"媒体"部件改为只说忙闲（下一步）。
- RULE431 SRC22:106-110 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - `desk_state.js` 纯函数 `renderState(deskState, memSnapshot) -> {memText, holderText, mediaText, nextText, tone}`：
>   - 内存显示 `已用 X.X / 总 Y GB（可用 Z GB）`，由快照字节数格式化，**不存在任何常量 128**；
>   - `holderText`：`空闲` / `LLM：<名称>` / `视频生成中` / `音乐生成中`；
>   - `nextText`：`可开下一件重活` 或 `不可：<机器可读原因的中文文案>`；
>   - `tone`: `ok | busy | error`，决定状态条配色。
- RULE689 SRC45:1149-1149 · release=2026-09-11 视觉修复计划 / platform=unknown / role=all / condition=all
> `memoryMenuTitle` 的数值格式从 `%.1f` 改为 `%.0f`（N3：同屏三处读数因 0.4 GiB 抖动而不同，取整后一致）。同时把 web 侧 `pure/format.js` 里状态条的内存格式也改为整数 GiB，两处必须同时改，否则仍会出现 79 vs 79.4。

### RC25 · version_conflict · 待用户澄清
共同条件：H3 视频生成的内部内存预算
media 设计把 mlx-h3 --budget 定为 70（GiB）且仅此一处；视频画幅设计提示「超过视频生成的 40 GiB 上限，可能中途失败」，并把预算 40 写进前后端镜像测试；媒体底座与视频会话均声明不改 --budget
待确认：H3 --budget 当前是 40 还是 70？若改过，改动由哪条规则授权？
- RULE323 SRC14:54-54 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> H3_BUDGET_GB = 70   # mlx-h3 --budget，仅此一处
- RULE1028 SRC33:55-55 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=all
> - [Z-41] H3 预算：`估算 = 27.0 + 1.4 × max(宽×高×帧数 ÷ (512×288×49) − 1, 0)` GiB，与 `memory_estimate.py` 同源；超过 40 时显示「按实测外推约需 N GiB，超过视频生成的 40 GiB 上限，可能中途失败。」（N 取整）。
- RULE1010 SRC33:25-25 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=all
> - [Z-04] 镜像测试：一个 Python 测试读出 JS 与 Python 两边的常量（32、256、1344、768×1344）和内存公式参数（27.0、1.4、草稿体积 512×288×49、预算 40），任何一边改了另一边不跟就失败。
- RULE821 SRC28:48-48 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-00d] 不改 H3 `--budget`（属 budget 模块）。不设续写段数、成片时长上限。
- RULE915 SRC30:24-24 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=all
> - [V-00c] 不改 H3 命令行、预算、耗时估算公式。

### RC26 · version_conflict · 待用户澄清
共同条件：启动媒体作业前是否检查模型完整度
media 首版设计 A10 规定媒体不做模型完整度预检（权重不齐由子进程失败上报），e2e 设计据此默认铺 present；图片会话与媒体底座的启动顺序都含 model_incomplete → 409，按钮在模型不完整时禁用
待确认：model_incomplete 预检是否已取代 media 设计 A10？视频/音乐作业是否同样适用？
- RULE342 SRC14:364-365 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 10. **media 不做模型完整度预检**：权重不齐由子进程失败如实上报（`exit_nonzero`）；
>     完整度是 resources 的职责，ui 在资源面板呈现。media 只对二进制/解释器缺失做快速拒绝。
- RULE460 SRC3:187-188 · release=2026-08-31 首版 / platform=unknown / role=测试 / condition=all
> h3 / music3 条目默认铺 present（媒体流程不做完整度预检，media 设计 Assumption 10，
> 但资源面板会显示它们）。清单内容纯由 `FakeFetcher` 供给，manifest 缓存照常落
- RULE760 SRC27:169-174 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-20] 校验与挂接顺序（`start_image_job` → `_start`）：
>   1. 参数校验（提示词、宽高、步数、种子、force）→ 400；
>   2. `session_id` 校验（D-18）→ 400 / 404；
>   3. 互斥 `media_busy` → 409；运行环境 `capability_missing` → 503；模型 `model_incomplete` → 409；arbiter 拒绝 → 409；内存警告 `insufficient_memory`（未 force）→ 409；
>   4. 启动子进程；`spawn_failed` → 500；
>   5. **子进程启动成功、`_state` 已为 running 之后**，在 `MediaService._lock` 内调用 `begin_attempt(session_id, attempt)`，`attempt.job_id` 为新作业号、`params` 为实际参数（含实际 seed）。
- RULE840 SRC28:163-163 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-32] 校验与挂接顺序：参数 → 会话 → `continues`（§3.3）→ `refs`（§5）→ `_start` 的既有检查（`media_busy` → `capability_missing` → `model_incomplete` → arbiter → `insufficient_memory`）→ 若需拼接则检查 ffmpeg（§6）→ 启动子进程 → 成功后 `begin_attempt`。
- RULE781 SRC27:233-233 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-48] 生成中、正在提交、模型缺失、运行环境不可用、其他媒体作业占用时，该按钮 `disabled`，`title` 与按钮下方一行提示为不可用原因（与「生成图片」按钮同一原因文本，见 §7）。
- RULE912 SRC29:144-144 · release=2026-09-27 音乐会话 / platform=unknown / role=all / condition=all
> - [M-53] 音乐模型状态与运行环境：`main.js` 以与图片页相同的方式接通（不新增后端）——资源页 `onModels` 回调里 `panes.music.setModelStatus(models?.find((m) => m.key === "music3"))`；能力探测处 `panes.music.setRuntimeStatus(capabilities?.music_runtime)`。文案：模型缺失「尚未安装音乐模型，请到「资源」页下载」，不完整「模型不完整，请到「资源」页继续下载或校验」，未知「暂时无法确认模型状态，请稍后重试」；运行环境不可用「音乐 MLX 运行环境不可用，请检查服务或应用安装」（`capability.detail` 优先）；就绪时头部显示「模型文件完整 · 可离线生成」。

### RC27 · version_conflict · 待用户澄清
共同条件：开发模式下各媒体运行时的解释器布局
foundation 设计 A8 规定不延续 .venv-desk/.venv-music3 双 venv、dev 按单环境开发；当前 README 与 qwen 文档写服务用 .venv-desk、视频/图片/音乐各用独立 venv（.venv-image、.venv-music3）
待确认：开发模式是单环境还是每个媒体运行时独立 venv？foundation A8 是否已被取代？
- RULE244 SRC5:462-464 · release=2026-08-31 首版 / platform=unknown / role=开发者 / condition=all
> - **A8 dev 态 venv**：`venv_python = sys.executable`（开发者从装齐依赖的 venv 里起服务）；
>   现有 `.venv-desk` / `.venv-music3` 双 venv 布局不被延续——bundle 是「单内嵌解释器 + 三套
>   pylibs」（packaging §1.3，无任何 venv），dev 按装齐全部依赖的单环境开发。
- RULE542 SRC34:99-103 · release=README @0d98e9e（当前） / platform=unknown / role=开发者 / condition=all
> - 服务：`.venv-desk/bin/python -m desk`（端口由 `LMD_SHELL_PORT` 指定，默认 8766；`LOCALMODELDESK_DATA_ROOT` 可换一个独立数据目录）。
> - 三个媒体运行时各用各的 venv，服务本身不装它们：
>   - 视频：`mlx-h3` 可执行文件（`uv tool install` 装在 `~/.local/bin`），或用 `LOCALMODELDESK_MLX_H3` 指定。
>   - 图片：`.venv-image`，安装见 `docs/qwen-image-mlx.md`；或用 `LOCALMODELDESK_IMAGE_PYTHON` 指定。
>   - 音乐：`uv venv --python 3.13 .venv-music3 && uv pip install --python .venv-music3/bin/python -r packaging/requirements-music.txt`；或用 `LOCALMODELDESK_MUSIC_PYTHON` 指定。
- RULE594 SRC44:48-51 · release=qwen-image-mlx 文档（2026-09-23 实测） / platform=unknown / role=all / condition=all
> 开发服务默认使用本工作树 `.venv-image/bin/python`；可用 `LOCALMODELDESK_IMAGE_PYTHON`
> 指定其他图片解释器。`GET /api/capabilities` 暴露 `image_runtime.present/detail`，
> 能力检查最多缓存 10 秒，修复运行环境后可自动恢复。构建脚本独立安装 `pylibs/image`，
> 图片工作进程不复用音乐或聊天依赖目录。

### RC28 · needs_clarification · 待用户澄清
共同条件：图片页与其他界面视觉验收所用的截图证据
AC-7 要求「在真实浏览器中截图检查」，视觉证据要求用 tests/e2e 的 Playwright（默认 Chromium）截图；用户记忆写 e2e 的 Chromium 截图不是 WKWebView 外观的证据、真机外观需 visual-capture，且新视觉验收须与用户逐类重新确认基线；素材库设计要求另用 WebKit 核对；视觉候选基线自述 confirmation 为 null 的类不能当基线用
待确认：AC-7 的「真实浏览器」是否接受 Chromium 截图，还是需要 WKWebView/WebKit 截图？image-sessions 视觉标准是否需要先完成基线重新确认？
- RULE589 SRC42:30-30 · release=image-sessions 需求 revision 1（2026-09-24 用户确认） / platform=unknown / role=验收 / condition=all
>         "在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误"
- RULE662 SRC49:43-43 · release=决策日志 2026-09-24 / platform=unknown / role=验收 / condition=all
>               "在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误"
- RULE625 SRC50:4-13 · release=image-sessions 视觉证据要求（2026-10-09 快照） / platform=unknown / role=验收 / condition=all
>   "capture": {
>     "tool": "Playwright（tests/e2e，desk.testing.launch_test_harness 启动的真实外壳 + 真实浏览器）",
>     "directory": ".allforai/visual-qa/evidence/",
>     "naming": "<state_id>-<viewport_id>.png，例如 timeline-three-rounds-wide.png",
>     "full_page": false,
>     "also_record": "每张截图旁写同名 .json：{state_id, viewport, url, session_ids, dom_checks:{seed_word_in_main_flow:false, blank_images:0, horizontal_scroll:false, clipped_buttons:[]}}",
>     "mock_layers_to_declare": [
>       "脚本化媒体执行器（desk/testing/scripts.py）代替 image_cli 子进程",
>       "测试外壳的 fake LLM / arbiter"
>     ]
- RULE561 SRC40:17-17 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **Update 2026-09-16:** the frozen baseline files are GONE. `docs/cross-exam/` was dropped from the public tree (commit "chore: drop local review dumps from the public tree"), added to `.gitignore`, and is absent from git history and from disk (searched /Users/aa). Only fragments survive, quoted inside `docs/superpowers/plans/2026-09-11-cross-exam-0908-visual.md` and the 2026-09-14 recheck plans (rule ids K2, K4, L6…). A new visual acceptance therefore has to re-freeze the baseline by re-confirming the categories with the user — don't promise a re-run that "just reuses the old baseline". Candidates for all twelve categories were drafted from the code and committed at `docs/visual/*.candidate.json` (commit 064da3d), so the confirmation session starts from those, not from zero; `.gitignore` now tracks baselines and reports and ignores only `docs/cross-exam/**/evidence/` and recordings. Capturing the real app needs `LMD_PROBE_PORT` plus `scripts/visual-capture.py` — e2e's Chromium shots are not evidence for the WKWebView's look.
- RULE1002 SRC32:73-73 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=all
> - [L-53] WebKit 核对：应用外壳是 WKWebView，而 e2e 默认跑 Chromium。视频首帧缩略图（`#t=0.1` + `preload="metadata"`）与悬停播放须另用 Playwright WebKit（本机已装 webkit-2272）跑一条用例确认能出首帧；不行则退回「视频图标 + 时长」占位并在本文件记下。
- RULE709 SRC47:3-3 · release=候选（未确认） / platform=unknown / role=all / condition=all
>  "note": "候选规则：逐条从当前代码读出，待用户在 /superstorm:cross-exam 的视觉验收里逐类确认。confirmation 为 null 的类不能当基线用。",
- RULE600 SRC43:21-25 · release=image-sessions 视觉验收标准（status passed） / platform=unknown / role=all / condition=all
>   "global_rules": {
>     "must_show": [
>       "左侧会话列表（「新会话」主按钮在最上）",
>       "右侧时间线与底部输入区（提示词输入框 + 「生成图片」主按钮 + 折叠的「高级参数」）",
>       "当前会话在列表中高亮（aria-current=true）"

### RC29 · unreachable_condition · 待用户澄清
共同条件：对 desk/static 的 UI 改动进行基线核对
同一条记忆要求任何 UI 工作都对照 2026-09-06 冻结的视觉/交互基线核对，又记录这些基线文件已不存在、不能承诺复用；按原文要求的核对对象不可得
待确认：在基线重新冻结之前，UI 改动应对照什么核对（候选基线、修复计划片段，还是暂不核对）？
- RULE562 SRC40:19-19 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **How to apply:** Any UI work on desk/static should be checked against that baseline; the cross-exam report lists the per-rule findings (F1–F29 web, N1–N14 native) to fix.
- RULE561 SRC40:17-17 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **Update 2026-09-16:** the frozen baseline files are GONE. `docs/cross-exam/` was dropped from the public tree (commit "chore: drop local review dumps from the public tree"), added to `.gitignore`, and is absent from git history and from disk (searched /Users/aa). Only fragments survive, quoted inside `docs/superpowers/plans/2026-09-11-cross-exam-0908-visual.md` and the 2026-09-14 recheck plans (rule ids K2, K4, L6…). A new visual acceptance therefore has to re-freeze the baseline by re-confirming the categories with the user — don't promise a re-run that "just reuses the old baseline". Candidates for all twelve categories were drafted from the code and committed at `docs/visual/*.candidate.json` (commit 064da3d), so the confirmation session starts from those, not from zero; `.gitignore` now tracks baselines and reports and ignores only `docs/cross-exam/**/evidence/` and recordings. Capturing the real app needs `LMD_PROBE_PORT` plus `scripts/visual-capture.py` — e2e's Chromium shots are not evidence for the WKWebView's look.
- RULE559 SRC40:11-11 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> On 2026-09-07 the user chose to "redo the visual baseline" for LocalModelDesk rather than accept the current look. Confirmed rules live in `docs/cross-exam/2026-09-06-localmodeldesk/visual/visual-baseline.json` and `interaction-baseline.json` (reference mockups in `visual/refs/`). Key direction: keep the dark tokens; ChatGPT-style chat (user question as right-aligned grey bubble, assistant answer as plain left text with dot + model name, thinking as a collapsed "已思考 N 秒" quote block); primary/secondary/danger button levels; card-style list rows; full-width main area; native-feeling affordances (e.g. an entry to open the output folder in Finder, not auto-open).

### RC30 · exception_ambiguity · 待用户澄清
共同条件：首次进入图片页、没有任何会话时
已确认业务规则 BR-4 写「会话需手动新建」；D-62 规定此时自动新建一个「新会话」并给出理由，称仍满足手动新建；视觉标准据此要求不显示「请先新建」提示。该例外是设计方解释，确认来源未记录用户是否接受
待确认：首次进入自动新建一个空会话是否被用户接受为 BR-4 的例外？
- RULE788 SRC27:248-248 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-62] 首次进入图片页且没有任何会话时，**自动新建一个「新会话」并选中**，不显示「请先新建」的提示。理由：与聊天页 `refreshSessions` 相同行为（保持两个页面一致）；用户第一次来要做的事就是写提示词生成，多一步「先新建」没有任何信息量；空会话没有代价。这仍满足「会话需手动新建」——之后的每个新分组都由用户点「新会话」产生，生成本身从不暗中另开会话。
- RULE577 SRC42:16-16 · release=image-sessions 需求 revision 1（2026-09-24 用户确认） / platform=unknown / role=all / condition=all
>         "会话需手动新建（像聊天的「新建」）；未新建时生成接在当前会话；会话标题默认取第一次生成的提示词",
- RULE650 SRC49:29-29 · release=决策日志 2026-09-24 / platform=unknown / role=all / condition=all
>               "会话需手动新建（像聊天的「新建」）；未新建时生成接在当前会话；会话标题默认取第一次生成的提示词",
- RULE1052 SRC27:400-400 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> | BR-4 | 会话需手动新建（像聊天的「新建」）；未新建时生成接在当前会话；会话标题默认取第一次生成的提示词 | D-60–D-62、D-10–D-12 | image-session-backend / image-session-pane |
- RULE605 SRC43:38-66 · release=image-sessions 视觉验收标准（status passed） / platform=unknown / role=验收 / condition=空数据目录（image-sessions/ 不存在）；图片模型与运行环境可用
>       "id": "first-entry-auto-session",
>       "title": "首次进入：无任何会话时自动新建的空会话",
>       "design_refs": [
>         "D-62",
>         "D-80",
>         "D-10"
>       ],
>       "requirement_refs": [
>         "BR-4",
>         "AC-7"
>       ],
>       "precondition": "空数据目录（image-sessions/ 不存在）；图片模型与运行环境可用",
>       "steps": [
>         "打开 #tab=image"
>       ],
>       "must_show": [
>         "会话列表恰有一项「新会话」且高亮",
>         "时间线居中两行：「还没有图片」与「在下面写下想要的画面，点「生成图片」…」",
>         "「生成图片」按钮可用",
>         "「高级参数」处于折叠状态"
>       ],
>       "must_not_show": [
>         "「请先新建会话」一类提示",
>         "进度条",
>         "任何图片框或缩略图占位",
>         "「种子」一词",
>         "空白图片框（全局规则）",
>         "主流程出现「种子」一词（全局规则）"
>       ],

### RC31 · exception_ambiguity · 待用户澄清
共同条件：退出 App 时 8766 端口上有非台面进程监听（启动时曾判为端口冲突）
shell 设计启动时对「端口被占但健康检查不过」的进程绝不杀；退出流程的 ensureFree 却对「仍在监听 8766 的任何进程（含 attached 模式下不是我们 spawn 的）」先 TERM 后 KILL。端口冲突失败状态下退出是否执行 ensureFree 未写明
待确认：退出时是否应只收割确认为台面服务的 8766 监听者？portConflict 状态下退出是否跳过 ensureFree？
- RULE398 SRC20:129-131 · release=2026-08-31 首版 / platform=unknown / role=all / condition=退出路径
> 3. `PortGuard.ensureFree(port)`：对**仍在监听 8766 的任何进程**（含 attached 模式下不是我们 spawn 的）
>    TERM → 等 2s → KILL → 复查；随后（owned 模式）复查 `llmPort`(8767) 亦无监听。
>    两个端口都确认无监听才算成功。
- RULE397 SRC20:113-115 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> 1. 健康检查 `GET :8766<healthPath>`：返回 200 且 body 是 JSON ⇒ `runningAttached`，直接完成
>    （二次启动 App、或上次 App 被 SIGKILL 留下的服务，都走这条被重新收编）。
> 2. 端口被占但健康检查不过 ⇒ `failed(.portConflict)`（不是我们的服务，绝不杀，交给错误页说明）。
- RULE417 SRC20:375-381 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **A-5 退出收割归属（Phase 1.2 裁定）**：原假设「内嵌服务收到 SIGTERM 后自行收割 :8767 与媒体子进程」
>   在对方设计中**无人认领**——foundation/llm/media 设计均未安装 desk 侧 SIGTERM 处理器；
>   llm 只在下次 spawn 前 `reap_llm_port`，media 子进程以 `start_new_session=True` 起（不随父进程死）。
>   故裁定：退出时的孤儿保证由 **shell 的按内嵌解释器路径全家收割 + 8766/8767 端口复查**规范承担
>   （terminate 流程第 2–4 步；生命周期测试场景 7 机检）。`termGrace` 窗口仍给服务体面收尾的机会，
>   服务侧将来若增加 SIGTERM 处理器，只会让 KILL 路径更少触发，契约不变。
>   attach-only 开发态无内嵌解释器路径可循，只做 8766 端口收割——残余风险与 A-6 同级，判定可接受。
- RULE111 SRC21:19-20 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> - **R-shell-04** 退出时终止内嵌服务；不得留下孤儿进程（退出后台面端口不再有监听）。
>   异常终止路径（如 SIGTERM）也要清理。

### RC32 · needs_clarification · 待用户澄清
共同条件：两个媒体作业（如视频与音乐）同时被请求且预算判定装得下
budget 把 R-arbiter-04「已有媒体作业时拒绝第二个」改写为「预算装不下才拒绝」，fits() 以一组重活为输入；media 设计与图片会话 D-00d 规定 MediaService 一次至多一个作业、media_busy 单作业互斥保持不变
待确认：预算改写后是否允许多个媒体作业并行？还是 MediaService 的单作业互斥仍独立成立（预算只管聊天与媒体共存）？
- RULE739 SRC27:20-20 · release=2026-09-24 图片会话（含同日修订） / platform=unknown / role=all / condition=all
> - [D-00d] 批量出图、排队、模型常驻不做；单作业互斥（`MediaService._start` 的 `media_busy`）保持不变。
- RULE319 SRC14:11-12 · release=2026-08-31 首版 / platform=unknown / role=all / condition=all
> `media` 是 H3 文生视频与 Music 3 文生歌曲的**作业运行器**：一次至多一个作业，
> 启动前必须拿到 `arbiter` 许可，产出落 outputs 根，结束（成功/失败/取消）时写历史并释放许可。
- RULE325 SRC14:145-145 · release=2026-08-31 首版 / platform=unknown / role=all / condition=已有作业 running
> start 在已 running 时 => 拒绝（media_busy），状态不变
- RULE155 SRC25:51-54 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-budget-07** 重活能否并存由预算判定，预算不足时结果即互斥。
>   判定的输入是**一组**重活而非一对：`fits(workloads)`。三件能否共存不等于
>   三个两两判断的合取，「最小让出」也只有在集合上才算得出来。
>   拒绝必须带机器可读原因与数字：需要多少、现有多少、依据来源为预测还是实测。
- RULE184 SRC25:189-189 · release=2026-09-17 budget 修订（含 2026-09-21/22 增补） / platform=unknown / role=all / condition=all
> - **R-arbiter-04** 改：拒绝条件由「媒体在跑」变为「预算装不下」。

### RC33 · needs_clarification · 待用户澄清
共同条件：视频请求画幅面积超过 768×1344
画幅设计以 400 硬拒绝面积 > 768×1344 的画幅，同时说预算提醒「只提醒不拦」；软限制记忆禁止因内存原因新增硬拒绝。面积上限的依据（模型约束还是内存）未写明，因此无法判断是否落入软限制约束
待确认：768×1344 的面积上限是 H3 模型约束还是内存考虑？若是内存考虑，是否应改为提醒+确认？
- RULE1007 SRC33:22-22 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=all
> - [Z-01] 合法画幅：宽、高都是整数且为 32 的倍数；每边 256–1344；`宽×高 ≤ 768×1344`。
- RULE1009 SRC33:24-24 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=all
> - [Z-03] 后端 `start_video_job` 在任何会话写入之前做同样校验，违规返回 400 `invalid_params`，文案「画幅须为 32 的倍数，每边 256–1344，面积不超过 768×1344」；拒绝时会话不留尝试记录（B-33）。
- RULE547 SRC35:11-11 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> New features must work across different hardware (36 GB → 512 GB Macs), but memory checks must stay lenient: estimate → "内存可能不足 / 仍要生成" confirm with force, never a new hard rejection, never hide features by hardware.
- RULE549 SRC35:15-15 · release=用户确认记忆（见各条日期） / platform=unknown / role=all / condition=all
> **How to apply:** new job kinds plug into `memory_estimate.estimate_bytes` soft-warning path; ffmpeg-only jobs skip memory checks; don't cap chain lengths for memory reasons. Related: [[project-visual-baseline-direction]]
- RULE1005 SRC33:16-16 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=all
> - [Z-00c] 不改整机内存的「警告 + 确认」（后端 `estimate_bytes` + `force`）；本次的预算提醒是 H3 内部 40 GiB 预算，另一回事，只提醒。
- RULE1028 SRC33:55-55 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=all
> - [Z-41] H3 预算：`估算 = 27.0 + 1.4 × max(宽×高×帧数 ÷ (512×288×49) − 1, 0)` GiB，与 `memory_estimate.py` 同源；超过 40 时显示「按实测外推约需 N GiB，超过视频生成的 40 GiB 上限，可能中途失败。」（N 取整）。
未能审查：SRC48（material-availability.md）只记录路径存在性事实，没有规范性陈述可提取，未产生规则
未能审查：冻结视觉/交互基线 docs/cross-exam/2026-09-06-localmodeldesk/visual/*baseline.json 与修复计划引用的 docs/cross-exam/2026-09-08-localmodeldesk(-widewin)/visual/visual-baseline.json、三份 reviewer 报告均不可得（SRC48、SRC40 记载已删除），计划中 K2/K4/K5/L2/L6/S1/S2/D3/C1 等基线条目原文无法核对，只能比较快照中被引用的片段
未能审查：决策记录 D-0001、D-0002 的原文不可得（SRC48），e2e 技术选型与网关局域网自动验收的决策依据只能按 SRC3/SRC4/SRC8 中的转述比较
未能审查：R-budget-12、R-budget-14、R-budget-15 的原文不在快照中（SRC25 只记录其作废），无法逐条核对被取代内容
未能审查：qwen-image 文档引用的 .allforai/bootstrap/records/image-acceptance.json、图片会话设计引用的 defensive-patterns Pattern I、素材库设计引用的 issue #12/#15 与 F3 均不在快照中，相关规则只能按快照内转述比较
未能审查：输入需求 R-library-04 的原文与 SRC10 spec 第 20 行文字不同，而与 SRC9 设计第 79–80 行一致；已同时关联两处，但无法确认哪一份是需求点名册所依据的版本

## 需求覆盖（基准 416 条，有裁决 15 条，无裁决 401 条）
- R-arbiter-01 聊天 LLM、视频生成、音乐生成三者互斥；持有者唯一，任何时刻至多一个重活。 获取与释放必须是进程内串行化的（锁），并发获取只能有一个成功。 ｜budget-spec 改写：重活能否并存由预算判定；预算不足时退化为互斥。持有者由单个变为一组。 — 缺口（J3 走得通吗？） · 缺口（在 LocalModelDesk 的视频页，对一段已完成的视频点「接着往下生」生成续写段：续写段的模型生成结束之后、该次尝试最终标为完成之前，台面会把多段拼成「成片」。在这段拼接时间窗里（以及它前后各几秒），Web 状态条的「内存里 / 媒体 / 下一件重活」三段文字、GET /api/state 的 holder/holders/media_busy/can_start、GET /api/media/job 的作业状态各是什么？在这段窗口里，若尝试再启动一件重活（例如在音乐页点生成一首短歌，或在视频页的另一个会话再生成一段），台面接受还是拒绝、给出什么文字？请按时间轴（精确到秒）记录。）
- R-arbiter-04 媒体作业进行中拒绝加载 LLM；已有媒体作业时拒绝启动第二个媒体作业。拒绝必须带机器可读原因。 ｜budget-spec 改写：拒绝条件由「媒体在跑」变为「预算装不下」。 — 缺口（在 LocalModelDesk 的视频页，对一段已完成的视频点「接着往下生」生成续写段：续写段的模型生成结束之后、该次尝试最终标为完成之前，台面会把多段拼成「成片」。在这段拼接时间窗里（以及它前后各几秒），Web 状态条的「内存里 / 媒体 / 下一件重活」三段文字、GET /api/state 的 holder/holders/media_busy/can_start、GET /api/media/job 的作业状态各是什么？在这段窗口里，若尝试再启动一件重活（例如在音乐页点生成一首短歌，或在视频页的另一个会话再生成一段），台面接受还是拒绝、给出什么文字？请按时间轴（精确到秒）记录。）
- R-gateway-04 `POST /v1/messages` 非流式：Anthropic 请求形状（`model`/`max_tokens`/`messages`/`system`） 与响应形状（`type:"message"`、`content` 块数组、`stop_reason`、`usage.input_tokens`/`output_tokens`）。 — 缺口（调用 S61「Gateway: wrong method / unknown path rejections」（入口 desk/gateway/http_server.py:110-126 (405/404)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。）
- R-gateway-09 错误按各自方言的原生错误信封返回（OpenAI 的 `{"error":{...}}`； Anthropic 的 `{"type":"error","error":{"type":...,"message":...}}`）。不得伪造成功响应。 — 缺口（调用 S61「Gateway: wrong method / unknown path rejections」（入口 desk/gateway/http_server.py:110-126 (405/404)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。）
- R-library-03 每个作业追加一条历史：类别、提示词/全部参数、耗时、状态、产出文件名、时间戳。 追加是原子的、并发安全的（多线程同时追加不得写坏行）。 — 缺口（调用 S42「Generation history (?limit)」（入口 GET /api/history (desk/library/http.py:194)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。）
- R-library-05 多会话聊天：新建、列出、切换、重命名、删除。 — 缺口（调用 S44「Create chat session」（入口 POST /api/sessions (desk/library/http.py:196)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。）
- R-library-06 每个会话持久化其消息、所用模型、更新时间；重启后仍在。删除会话即删除其持久化文件。 — 缺口（调用 S45「Update chat session (messages/title/skills; keepalive)」（入口 PATCH /api/sessions/{id} (desk/library/http.py:197)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。）
- R-shell-02 菜单栏项显示实时台面状态（空闲 / 已加载 XX / 出片中），菜单含「打开窗口」与「退出」。 — 缺口（J3 走得通吗？） · 缺口（LocalModelDesk 的 macOS 菜单栏状态项（屏幕右上角的状态图标/标题及点开后的菜单，其中有一行状态文字）在以下时刻分别显示什么：(a) 没有媒体作业时；(b) 在图片页生成一张图片的过程中；(c) 图片生成完成后。同时记录同一时刻 GET http://127.0.0.1:8766/api/state 的 holder/holders。）
- R-ui-01 前端是静态文件（`index.html`、`app.css`、ES 模块），由服务端供给； Python 源码里不再存在内联 HTML/CSS/JS 字符串。 — 缺口（调用 S2「Static assets」（入口 GET /static/* (desk/ui.py:25)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。）
- R-ui-02 聊天面板：模型选择、加载/卸载、流式回复、思考过程可展开、左侧会话列表（新建/切换/重命名/删除）。 — 缺口（J3 走得通吗？） · 缺口（J11 走得通吗？）
- R-budget-05 修正的两个生效点必须区分：软触发（压缩阈值）立即生效； 硬边界（`--prompt-cache-bytes`）下次加载生效。二者不得混淆。 — 缺口（J11 走得通吗？）
- R-context-01 会话发送给模型的内容受预算约束：超过 `Budget.for_chat()` 给出的 触发点时，较早消息由一条结构化摘要替代，尾部若干轮保持原文。 保留轮数由预算反推（尾部与摘要之和不超过触发点的一半，且至少保留最近一轮完整问答）， 不得写死为常数——各模型每 token 开销相差一个数量级。 — 缺口（LocalModelDesk 的聊天页在会话长到需要自动压缩上下文时，若这次压缩请求没能成功（例如压缩进行中聊天模型被卸载、或上游请求中断/超时），用户在界面上看到什么（有无进行中提示、有无失败提示及其文字）、这一轮用户的提问最终得到什么、会话里原来的消息与有无摘要块各是什么状态、下一次发送时又发生什么？请分别记录压缩开始前、压缩进行中、压缩失败后、再次发送后的界面与 GET /api/sessions/{id} 读回。）
- R-context-04 压缩在两轮之间进行，使用当前驻留模型，不加载第二个模型。 压缩过程对用户可见（明确的进行中提示），不得静默阻塞。 — 缺口（J11 走得通吗？） · 缺口（LocalModelDesk 的聊天页在会话长到需要自动压缩上下文时，若这次压缩请求没能成功（例如压缩进行中聊天模型被卸载、或上游请求中断/超时），用户在界面上看到什么（有无进行中提示、有无失败提示及其文字）、这一轮用户的提问最终得到什么、会话里原来的消息与有无摘要块各是什么状态、下一次发送时又发生什么？请分别记录压缩开始前、压缩进行中、压缩失败后、再次发送后的界面与 GET /api/sessions/{id} 读回。）
- R-skill-11 从外部装：先看全文，再落盘，装完不启用。 — 缺口（调用 S35「Preview a GitHub skill install (staging)」（入口 POST /api/skills/preview (desk/skills/routes.py:22)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。）
- R-skill-15 选中状态（含附件勾选）是**会话级**的，随会话存档。 — 缺口（调用 S45「Update chat session (messages/title/skills; keepalive)」（入口 PATCH /api/sessions/{id} (desk/library/http.py:197)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。）
- R-arbiter-02 真实内存快照：总量、已用、可用、内存压力，取自操作系统（macOS 上 `vm_stat` / `sysctl`）， **不得出现写死的 128 之类常量**。 — 无裁决（面 F4 未盘问）
- R-arbiter-03 按端口收割 LLM：找出监听 LLM 端口的**任何**进程并终止（先 TERM 后 KILL）， 包含本服务未曾 spawn 的孤儿。收割后必须确认端口确已释放才算成功。 — 无裁决（面 F4 未盘问）
- R-arbiter-05 启动媒体作业前自动让出内存（卸掉 LLM）；让出失败必须导致启动失败，不得带着 LLM 硬上。 ｜budget-spec 改写：仅在预算不足时让出，且最小让出。 — 无裁决（面 F4 未盘问；面 X1 已盘问但无裁决引用它）
- R-arbiter-06 暴露单一台面状态对象：内存里是谁、媒体是否在跑、现在能不能开下一件重活， 以及若不能、为什么。这是状态条与菜单栏的唯一数据来源。 — 无裁决（面 F4 未盘问）
- R-arbiter-07 加载某模型前比对其体积与当前可用内存，装不下要在加载前给出警告（不是加载失败后才说）。 ｜budget-spec 改写：由加载时一次性检查，变为持续生效。 — 无裁决（面 F4 未盘问）
- R-foundation-01 所有路径由本模块单点解析，区分「只读 bundle 资源根」与「可写用户数据根」； 其他模块只能通过 `api:resolvePaths` / `data:pathRoots` 取路径，仓库内不得出现第二处 `Path.home()` 拼接模型或输出目录。 — 无裁决（面 F1 未盘问）
- R-foundation-02 配置持久化到 `<data root>/config.json`，字段至少含： `models_root`、`outputs_root`、`first_run_done`、`gateway`（`enabled`/`host`/`port`）、`config_version`。 读取时缺字段用默认值补齐，不得因为旧配置缺键而崩。 — 无裁决（面 F1 未盘问）
- R-foundation-03 首运语义：无配置或 `first_run_done` 为假时，`api:readConfig` 必须能表达 needs-setup 状态； `api:completeFirstRun` 接受一个选定的 models 根目录（默认 `<data root>/models`），校验可写后落盘并置 `first_run_done`。 目录不可写必须返回明确错误，不得静默回退到默认目录。 — 无裁决（面 F1 未盘问）
- R-foundation-04 收编既有权重：给定一个 legacy 根（如 `~/LocalModelDesk`）， `api:adoptLegacyModels` 识别其中的 `llms/`、`minimax-h3/`、`minimax-music3/`， 以「指向」（把 models_root 设成该目录）或「移动」两种方式接管，**任何情况下都不得重新下载、不得删除源**。 移动模式必须先校验目标卷剩余空间，不足则拒绝并说明差多少。 — 无裁决（面 F1 未盘问）
- R-foundation-05 服务在 `mlx-h3`、内嵌 venv、模型目录任一缺失时仍能启动并提供状态接口； 缺失作为可查询的能力状态暴露，**不得 `SystemExit`**（现状是缺 `mlx-h3` 就整个服务起不来，聊天跟着死）。 — 无裁决（面 F1 未盘问）
- R-foundation-06 配置写入原子：先写同目录临时文件再 `os.replace`；写到一半崩掉不得留下损坏的 `config.json`。 — 无裁决（面 F1 未盘问）
- R-gateway-01 `GET /v1/models`：OpenAI 格式，列出当前可服务的模型。没有模型驻留时返回空列表而非报错。 — 无裁决（面 F11 已盘问但无裁决引用它）
- R-gateway-02 `POST /v1/chat/completions` 非流式：OpenAI 请求与响应形状，含 `usage`、`finish_reason`。 — 无裁决（面 F11 已盘问但无裁决引用它）
- R-gateway-03 同端点流式：SSE，`data:` 分块与 OpenAI 增量格式一致，以 `data: [DONE]` 结束。 — 无裁决（面 F11 已盘问但无裁决引用它）
- R-gateway-05 同端点流式：发出 `message_start`、`content_block_start`、`content_block_delta`、 `content_block_stop`、`message_delta`、`message_stop` 事件，每个事件带 `event:` 与 `data:` 两行。 — 无裁决（面 F11 已盘问但无裁决引用它）
- R-gateway-06 Anthropic 的 `system`（字符串或块数组）、多轮 `messages`、`stop_reason` （`end_turn` / `max_tokens`）与 token 用量必须正确映射到底层结果。 — 无裁决（面 F11 已盘问但无裁决引用它）
- R-gateway-07 绑定 `0.0.0.0` 于配置端口，使同网络其他设备可达；开关关闭时不监听。 — 无裁决（面 F11 已盘问但无裁决引用它；面 X4 未盘问）
- R-gateway-08 无模型驻留或媒体作业进行中：返回 `503`，带 `Retry-After` 头与机器可读原因码。 **绝不自动加载模型，绝不排队等待。** — 无裁决（面 F11 已盘问但无裁决引用它；面 X1 已盘问但无裁决引用它）
- R-gateway-10 请求里的 `model` 既接受目录 key，也接受当前加载模型的标识符； 与当前驻留模型不符时按 R-gateway-08 报错说明，不静默换模型。 — 无裁决（面 F11 已盘问但无裁决引用它）
- R-library-04 ：`list` 返回的 entry 里 `params` 原样在场，前端「再做一版」直接从 `api:listHistory` 的结果取 `params` 回填，无需第二个取回接口（registry 中也没有）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- R-library-01 列出成品（视频/音频），带时间、类别、字节数。列表来源同时覆盖历史记录与磁盘上的孤儿文件 （历史里没有但磁盘上有的成品也要看得见）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- R-library-02 提供成品字节流并支持 HTTP `Range`，返回 `206` 与正确的 `Content-Range`，使播放器可拖动。 路径必须限制在 outputs 根内，逃逸请求返回 404。 — 无裁决（面 F9 已盘问但无裁决引用它；面 X4 未盘问）
- R-library-07 历史与会话一律存于用户数据根之下，不得写进 bundle 或代码目录。 — 无裁决（面 F9 已盘问但无裁决引用它）
- R-llm-01 按目录 key 加载聊天模型：先向 `arbiter` 申请许可，再启动 mlx-lm 服务， 轮询健康直到就绪。状态可查：`idle` / `loading` / `loaded` / `error`。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-llm-02 卸载当前模型，并确认 LLM 端口确已释放（走 `api:reapLlmPort`，不只是终止自己的子进程）。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-llm-03 流式对话：逐 token 输出正文增量，并把思考/推理增量（`reasoning_content` / `reasoning`） 作为独立字段与正文分开传给上层，不混在一起。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-llm-04 加载失败必须给出原因（mlx-lm 日志尾部），不得只报一个「加载超时」。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-llm-05 报出当前加载的是哪个模型及其元数据（视觉能力、量化、参数量、体积）。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-llm-06 媒体作业进行中、或当前没有加载模型时，聊天请求被拒绝并带明确原因，不得挂起等待。 — 无裁决（面 F3 已盘问但无裁决引用它；面 X1 已盘问但无裁决引用它）
- R-llm-07 对话必须经由本服务转发；前端与外部客户端都不直连 mlx-lm 端口。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-media-01 启动文生视频作业：提示词、画幅（宽高）、帧数、步数。H3 命令行的构造只存在一处。 — 无裁决（面 F6 已盘问但无裁决引用它）
- R-media-02 启动文生歌曲作业：风格描述、歌词、时长。Music 3 调用的构造只存在一处。 — 无裁决（面 F7 未盘问）
- R-media-03 作业运行中可流式读取进度/日志输出。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-media-04 作业产出落在 outputs 根，文件名带时间戳（视频 `h3-<stamp>.mp4`，音频 `music3-<stamp>.wav`）， 并通过 `api:appendHistory` 记录一条含全部参数的历史。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-media-05 任何重活占着 `arbiter` 时拒绝启动新作业，拒绝带机器可读原因。 启动前必须成功取得许可（其副作用是卸掉 LLM），失败即失败。 — 无裁决（面 F8 已盘问但无裁决引用它；面 X1 已盘问但无裁决引用它）
- R-media-06 作业失败记录失败与原因；**产出文件不存在时绝不报成功**（退出码 0 但无文件也算失败）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-media-07 取消运行中的作业：终止子进程并释放 `arbiter` 许可，状态转为已取消。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-packaging-01 一个构建脚本从干净 checkout 产出 `LocalModelDesk.app`；步骤可重复，中途失败要报错退出而非产出半成品。 — 无裁决（面 F14 未盘问）
- R-packaging-02 包内自带 Python 运行时与全部依赖；产物不依赖 `/opt/homebrew` 或任何用户级 site-packages。 — 无裁决（面 F14 未盘问）
- R-packaging-03 `Info.plist` 含 bundle id、版本、图标、`LSMinimumSystemVersion`。 — 无裁决（面 F14 未盘问）
- R-packaging-04 用 Developer ID Application 证书签名，启用 hardened runtime 与时间戳； 内嵌的二进制与动态库一并签（由内向外）。 — 无裁决（面 F14 未盘问）
- R-packaging-05 构建自动验证：`codesign --verify --deep --strict` 通过， 并验证自包含性（包内不存在指向 `/opt/homebrew` 或 home checkout 的路径引用）。 — 无裁决（面 F14 未盘问）
- R-packaging-06 安装步骤把 App 放到 `/Applications`。 — 无裁决（面 F14 未盘问）
- R-packaging-07 卸载步骤移除 App 与旧的 `com.aa.localmodeldesk` LaunchAgent； 用户数据仅在显式选择时删除；**模型权重在任何情况下都不得被自动删除**。 — 无裁决（面 F14 未盘问）
- R-packaging-08 根目录旧脚本（`initModels.sh`、`run-h3.sh`、`run-music3.py`、`unload-llm.sh`）删除， 并验证其行为在 App 内均可达（目录/下载、H3、Music、卸模型各有对应接口）。 — 无裁决（面 F14 未盘问）
- R-packaging-09 README 改写为安装后的真实行为，含：不自启、菜单栏形态、模型目录位置与收编、 以及对外 API 监听 `0.0.0.0` 且无鉴权这一事实。 — 无裁决（面 F14 未盘问）
- R-resources-01 单一目录定义，供服务端、前端、以及任何 CLI 入口共同消费； 仓库内不得存在第二份模型 repo/路径清单（`initModels.sh` 与 `server.py` 里现有的两份都要消失）。 — 无裁决（面 F2 未盘问）
- R-resources-02 完整度以 HF 仓库文件清单为准：取得每个期望文件的路径与字节数， 逐个比对本地是否存在、大小是否一致。清单可缓存到 `<data root>` 以便离线复用，缓存失效时明确降级说明，不得假装校验过。 — 无裁决（面 F2 未盘问）
- R-resources-03 每项报出 `present` | `partial` | `missing`；`partial` 必须带完成百分比 （按字节，不是按文件数）与缺失/短缺文件列表。 — 无裁决（面 F2 未盘问）
- R-resources-04 报出每项实际占盘字节数，以及 models 所在卷的剩余空间。 — 无裁决（面 F2 未盘问）
- R-resources-05 对某一目录项发起下载；中断后再次发起必须续传，已完整的文件不得重下。 — 无裁决（面 F2 未盘问）
- R-resources-06 取消/暂停进行中的下载；已下载的部分必须保持可续传状态，不得清空。 — 无裁决（面 F2 未盘问）
- R-resources-07 下载进行时可查询实时进度：已完成字节/总字节、当前文件、速率、预估剩余。 — 无裁决（面 F2 未盘问）
- R-resources-08 删除某一目录项的权重并回收磁盘，需要显式确认参数（无确认参数一律拒绝执行）。 删除只允许发生在 models 根之下，路径逃逸必须拒绝。 — 无裁决（面 F2 未盘问；面 X4 未盘问）
- R-resources-09 同时至多一个下载在跑；`arbiter` 报告有重活（媒体生成）在跑时，下载必须拒绝启动并说明原因。 — 无裁决（面 F2 未盘问；面 X1 已盘问但无裁决引用它）
- R-shell-01 App 从 `Contents/Resources/` 内的内嵌运行时启动服务； Swift 源码中不得出现任何指向 home 下 checkout 目录的路径。 — 无裁决（面 F12 已盘问但无裁决引用它）
- R-shell-03 关闭窗口不退出应用；App 留在菜单栏，服务继续存活；再次「打开窗口」能把窗口调回来。 — 无裁决（面 F12 已盘问但无裁决引用它）
- R-shell-04 退出时终止内嵌服务；不得留下孤儿进程（退出后台面端口不再有监听）。 异常终止路径（如 SIGTERM）也要清理。 — 无裁决（面 F12 已盘问但无裁决引用它）
- R-shell-05 Dock 图标存在，App 可被正常激活与切换（不是 LSUIElement）。 — 无裁决（面 F12 已盘问但无裁决引用它）
- R-shell-06 App 不注册任何登录项、不写任何 LaunchAgent plist。 — 无裁决（面 F12 已盘问但无裁决引用它）
- R-shell-07 首运弹出 models 目录选择（`NSOpenPanel`），并可选择收编既有目录树。 — 无裁决（面 F1 未盘问）
- R-shell-08 服务意外死亡时在界面上说明，而不是显示一个空白 WebView。 — 无裁决（面 F12 已盘问但无裁决引用它）
- R-ui-03 视频面板：提示词、画幅、帧数、步数、进度、完成后就地播放。 — 无裁决（面 F6 已盘问但无裁决引用它）
- R-ui-04 音乐面板：风格描述、歌词、时长、进度、完成后就地播放。 — 无裁决（面 F7 未盘问）
- R-ui-05 资源面板：每个模型显示 `齐` / `一半 N%` / `没下`、体积、实际占盘， 以及 下载 / 续传 / 取消 / 删除 控件；`partial` 要能看到缺哪些文件；显示卷剩余空间。 — 无裁决（面 F2 未盘问）
- R-ui-06 素材库面板：成品与历史，点击播放，点击把当时的参数回填进对应表单。 — 无裁决（面 F9 已盘问但无裁决引用它）
- R-ui-07 常驻状态条：真实内存（不是写死的 128）、内存里是谁、媒体是否在跑、现在能不能开下一件重活。 — 无裁决（面 F4 未盘问）
- R-ui-08 加载装不下的模型前弹出内存警告，确认后才继续。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-ui-09 首运界面：选择 models 目录，或收编一个既有目录树。 — 无裁决（面 F1 未盘问）
- R-ui-10 设置界面：对外 API 的开关、主机、端口，并显示可复制的 base URL （OpenAI 与 Anthropic 各一条），旁边注明当前是无鉴权监听。 — 无裁决（面 F11 已盘问但无裁决引用它）
- R-budget-01 每个额度必须标注来源 `predicted` / `measured` / `unavailable`， 在台面状态对象与诊断输出中可见。预测与实测不可混为一谈。 — 无裁决（面 F4 未盘问）
- R-budget-02 模型声明窗口按序读取：`text_config.max_position_embeddings` → 顶层 `max_position_embeddings` → 记 `unavailable`。**禁止读取 `vision_config`**。 三条顺序不得调整，不得回落成默认值。 — 无裁决（面 F4 未盘问）
- R-budget-03 冷启动额度由 `config.json` 推算（每 token 字节）与内存快照合成， 并据此向 mlx-lm 传入 `--prompt-cache-bytes` 与 `--prompt-cache-size`。 不传限额等于无上限，是当前的缺陷。 — 无裁决（面 F4 未盘问）
- R-budget-04 自校准：每轮完成后，由 mlx-lm 日志的 `Prompt Cache` 字节数除以 该轮 `usage.prompt_tokens`，得出本机该模型的实测每 token 字节，写入实测档案。 档案条目须记录权重大小，与 `ModelEntry.gb` 不符即作废重测。 — 无裁决（面 F4 未盘问）
- R-budget-06 保留 `memory_estimate.estimate_bytes(kind, params)` 的按参数估算形式—— 按作业种类给一个数会让不同分辨率的作业共用同一个估值，这是它当初就修掉的缺陷。 新增的是**标定来源**：每次媒体作业运行期采样 `available_bytes`（启动前基线、 运行中最低点、结束差值）得到本机实测峰值，写入实测档案，用于修正该公式的常数项。 本机尚无实测记录时，沿用代码内写死的 2026-09-08 标定值，并标 `predicted`。 — 无裁决（面 F4 未盘问）
- R-budget-07 重活能否并存由预算判定，预算不足时结果即互斥。 判定的输入是**一组**重活而非一对：`fits(workloads)`。三件能否共存不等于 三个两两判断的合取，「最小让出」也只有在集合上才算得出来。 拒绝必须带机器可读原因与数字：需要多少、现有多少、依据来源为预测还是实测。 — 无裁决（面 F4 未盘问）
- R-budget-16 预算的分母是**机器自报的重活能力**，不是此刻的可用内存。 — 无裁决（面 F4 未盘问）
- R-budget-18 `can_start_heavy` 与 `acquire_heavy` 对同一个请求必须给同一个答案。 — 无裁决（面 F4 未盘问）
- R-budget-19 拒绝的理由是给人看的，不是给日志看的。 — 无裁决（面 F4 未盘问）
- R-budget-17 「能不能用这个模型」问的是**台面还持不持有它**，不是「有没有媒体作业在跑」。 — 无裁决（面 F4 未盘问）
- R-budget-13 **无参的 `can_start_heavy(kind)` 只回答归属问题，绝不做预算算术。** — 无裁决（面 F4 未盘问）
- R-budget-10 一组重活的依据来源取其中最弱者：只要有一件是 `unavailable`， 整组按 `unavailable` 处理并走保守路径。不得让「两件实测加一件未量过」 被当作实测依据放行。 — 无裁决（面 F4 未盘问；面 F15 未盘问）
- R-budget-08 预算判定「装得下」而实际触发内存压力时，该次失败必须落盘， 并永久收紧该组合的预算。系统必须从失败中学习，不只从成功中学习。 — 无裁决（面 F15 未盘问）
- R-budget-09 内存压力升高时，按代价从轻到重处置：① 收紧对话额度并立即触发压缩； ② 拒绝新的重活；③ 才是卸载模型或终止作业。压力传感器是兜底闸，不是决策者。 — 无裁决（面 F15 未盘问）
- R-budget-11 每 token 开销的推算只对标准 MHA/GQA 成立。config 中出现 MLA 标记（`kv_lora_rank` / `qk_nope_head_dim` / `v_head_dim`）或缺少显式 `head_dim` 时， 一律返回「算不出」走保守路径，**禁止用 `hidden_size // num_attention_heads` 推导**。 本机 glm-4.7-flash 即属此类：该推导会凑出 102（2048/20 = 102.4，连整数都不是）， 得出约 375 KB/token 而实际约 53 KB——高估 7 倍。一个看起来合理、实际错 7 倍的数， 比没有数更危险。自校准会在一轮之后填入真值。 — 无裁决（面 F4 未盘问；面 F15 未盘问）
- R-context-02 摘要按固定模板填写，模板含且至少含：用户原始意图、关键概念、 涉及文件与代码、错误与修法、**用户历次发言逐条列出**、待办与当前工作。 不得使用开放式「总结一下」指令。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-context-03 压缩只影响发送内容，不影响存储与展示。会话文件保留全部原始消息， 用户在界面上始终可以看到每一条。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-context-05 摘要作为一条 `role: "summary"` 的会话消息存在，记录其替换的消息区间， 可被用户编辑，亦可在原文基础上重新生成。 — 无裁决（面 F3 已盘问但无裁决引用它）
- R-skill-01 skill 是**指令，不是能力**。台面不执行 skill 里的任何东西：不跑脚本、 不发请求、不自动跟随它写的链接。skill 唯一的作用是把文字放进上下文。 — 无裁决（面 F10 已盘问但无裁决引用它；面 X4 未盘问）
- R-skill-02 **进模型的每个字都是原文，台面不转述。** — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-03 **选中由用户完成，不由模型判断。** — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-04 可同时开多个，按选中顺序拼接。 — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-05 skill 的文字作为 `system` 消息排在最前，**永不参与压缩**。 — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-06 **skill 的 token 占用必须可见。** — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-07 两个来源，用户的覆盖自带的。 — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-08 **坏的 skill 照样列出来，并写明坏在哪。** — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-09 发现是显式的：启动时扫一次，外加一个「重新扫描」按钮。 — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-10 附件不隐身。 — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-12 **压缩的预算必须扣掉 skill 的占用。** — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-13 **skill 必须落在 `sentChars` 的度量范围之内。** — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-14 选中集合与可用集合必须对账。 — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-16 扫描产出**唯一一份已解析列表**，注入只读它。 — 无裁决（面 F10 已盘问但无裁决引用它）
- R-skill-17 安装**全部成功才落盘**，任何中断清掉暂存。 — 无裁决（面 F10 已盘问但无裁决引用它）
- D-01 图片会话目录 `PathRoots.image_sessions_dir = data_root / "image-sessions"`，与聊天会话目录 `data_root / "sessions"` 分开；两边的文件互不可见（`GET /api/sessions` 不列出图片会话，反之亦然）。 — 无裁决（面 F5 未盘问）
- D-02 每个会话一个文件 `<id>.json`，`id` 为 32 位小写十六进制（`uuid4().hex`，与 `SessionStore._ID_RE` 相同规则）。写入沿用 `SessionStore._write` 的方式：同目录临时文件 `.tmp-XXXX.part` + `os.replace`；列目录时跳过点开头的文件。 — 无裁决（面 F5 未盘问）
- D-03 图片文件不进会话目录：仍由媒体作业写到 `outputs_root`（`qwen-image-<stamp>-<8hex>.png`），会话只存文件名。 — 无裁决（面 F5 未盘问）
- D-04 `created` / `updated` / 尝试的 `ts` / `finished` 都用 `%Y-%m-%dT%H:%M:%S` 本地时间（与聊天会话一致）。 — 无裁决（面 F5 未盘问）
- D-05 `updated` 在以下时刻刷新：新建、重命名、追加尝试、尝试落定。切换查看会话不刷新 `updated`。 — 无裁决（面 F5 未盘问）
- D-06 `id` 是尝试自己的标识（`uuid4().hex`）。`job_id` 只是进程内作业计数（`MediaService._state["job_id"]`，重启后从 0 重数），仅用于把当前轮询到的作业对上 `running` 尝试，不作为持久标识。 — 无裁决（面 F5 未盘问）
- D-07 `params` 恰好五个键：`prompt`（字符串，原样保存，不截断）、`width`、`height`、`steps`、`seed`（都是整数）。`seed` 一律是**实际使用的值**，即使用户没填（随机）也记录生成时取到的那个数。 — 无裁决（面 F5 未盘问）
- D-08 各状态下字段取值： — 无裁决（面 F5 未盘问）
- D-09 `error.code` 取值与含义（`message` 是存进文件的原话，界面显示规则见 §7.5）： — 无裁决（面 F5 未盘问）
- D-10 新建会话 `title = "新会话"`、`title_auto = true`。 — 无裁决（面 F5 未盘问）
- D-11 会话追加**第一个**尝试时（`attempts` 为空且 `title_auto == true`），标题改为该尝试的提示词：连续空白折叠为一个空格、去首尾空白，长度超过 24 个字符时取前 24 个字符加「…」（与聊天 `displayTitle` 的 24 字规则一致）。之后的尝试不再改标题。第一个尝试失败或取消也照样取它的提示词。 — 无裁决（面 F5 未盘问）
- D-12 重命名后 `title_auto = false`，此后任何生成都不再改标题。 — 无裁决（面 F5 未盘问）
- D-13 重命名的标题：去首尾空白后 1–80 个字符；空串或超长 → 400，文件不变。 — 无裁决（面 F5 未盘问）
- D-14 **尝试记录只由后端写**：追加 `running` 尝试和落定都在 `MediaService` 里、通过 `ImageSessionStore` 完成；前端从不 PATCH 尝试。前端轮询丢包、页面刷新、窗口关闭都不会丢写。 — 无裁决（面 F5 未盘问）
- D-15 `ImageSessionStore` 的每个写方法在同一把 `threading.Lock` 内「读文件 → 改 → 原子写回」，不持有内存副本；所以作业线程的落定和 HTTP 线程的重命名/删除交错时互不覆盖（重命名后落定，标题保留；落定后重命名，状态保留）。 — 无裁决（面 F5 未盘问）
- D-16 接通要求（Closure）：`runtime.py` 与 `desk/testing/harness.py` 构造 `MediaService` 时都传 `image_sessions=library.image_sessions`；`GET /api/image-sessions` 挂在生产路由和测试外壳路由上。只有文件存在、没人调用不算完成。 — 无裁决（面 F5 未盘问）
- D-17 `attempt_count` 计所有状态的尝试；`running` 为该会话是否有 `status == "running"` 的尝试；`cover` 是最后一个 `done` 尝试的 `output`，没有则 `null`。目录不存在时返回 `[]`。 — 无裁决（面 F5 未盘问）
- D-18 `session_id` 必填。缺失或不是字符串 → 400 `{"error":{"code":"session_required","message":"请先选择或新建一个会话"}}`。会话不存在 → 404 `{"error":{"code":"session_not_found","message":"这个会话已被删除，请选择或新建一个会话"}}`。 — 无裁决（面 F5 未盘问）
- D-19 `seed` 可省略：省略时后端用 `secrets.randbelow(2**32)` 取随机值；不再有固定默认值 42（`start_image_job` 签名与 `routes.start_image` 里的 `seed=42` 默认都去掉）。给了就必须是 0–4294967295 的整数（现有校验）。 — 无裁决（面 F5 未盘问）
- D-20 校验与挂接顺序（`start_image_job` → `_start`）： 1. 参数校验（提示词、宽高、步数、种子、force）→ 400； 2. `session_id` 校验（D-18）→ 400 / 404； 3. 互斥 `media_busy` → 409；运行环境 `capability_missing` → 503；模型 `model_incomplete` → 409；arbiter 拒绝 → 409；内存警告 `insufficient_memory`（未 force）→ 409； 4. 启动子进程；`spawn_failed` → 500； 5. **子进程启动成功、`_state` 已为 running 之后**，在 `MediaService._lock` 内调用 `begin_attempt(session_id, attempt)`，`attempt.job_id` 为新作业号、`params` 为实际参数（含实际 seed）。 — 无裁决（面 F5 未盘问）
- D-21 第 1–4 步任何一步失败都**不写**会话文件：没有 running 尝试，也没有失败尝试（启动失败以错误提示的方式出现在输入区，见 §7.7）。 — 无裁决（面 F5 未盘问）
- D-22 200 响应是现有 `job_status()` 快照，外加 `"session_id"` 与 `"attempt_id"` 两个字段；`job_status()` 在该作业存续期间也带这两个字段（其他 kind 为 null），前端据此把轮询到的作业对上尝试卡片。 — 无裁决（面 F5 未盘问）
- D-23 `begin_attempt` 返回 False（会话恰好在第 2 步和第 5 步之间被删）时作业照常运行，结束后图片照常进素材库，不再写任何会话。 — 无裁决（面 F5 未盘问）
- D-24 落定点是 `MediaService._finalize`：在写 history 之后、调用回调之前，对本作业调用 `settle_attempt(session_id, attempt_id, …)`： — 无裁决（面 F5 未盘问）
- D-25 启动恢复：`LibraryService` 构造时调用一次 `image_sessions.recover_running()`，把上次进程遗留的 running 尝试改为 `failed` + `interrupted`。进程内任何时刻，会话文件里的 running 尝试只可能属于当前进程正在跑的那个作业。 — 无裁决（面 F5 未盘问）
- D-26 history 条目：图片作业的 history 条目增加顶层字段 `session_id` 与 `attempt_id`（未挂上会话时为 null）。素材库回填据此找回会话（§8.4）。 — 无裁决（面 F5 未盘问）
- D-27 前端看到轮询作业已不在 running、而当前会话里对应尝试仍是 running 时，重新 `GET` 该会话；仍是 running 就在下一次 2 秒轮询时再取，直到落定。前端从不自行把尝试标成完成或失败。 — 无裁决（面 F5 未盘问）
- D-30 删除会话只删除 `image-sessions/<id>.json`。`outputs_root` 下的图片、`history.jsonl` 都不动；删除后 `GET /api/outputs` 与 `GET /api/history` 的结果与删除前相同，素材库仍能列出并打开这些图片。 — 无裁决（面 F5 未盘问）
- D-31 删除一个有 running 尝试的会话：作业不取消，完成后图片进素材库，但不出现在任何会话里；history 条目里的 `session_id` 指向已不存在的会话（回填时按「不属于任何会话」处理，§8.4）。 — 无裁决（面 F5 未盘问）
- D-40 点击后：把该尝试的 `prompt` 填进提示词输入框，`width`、`height`、`steps`、`seed` 填进「高级参数」对应输入框；焦点移到提示词输入框、光标放在末尾，输入区滚入可见区域。**不提交**。 — 无裁决（面 F5 未盘问）
- D-41 输入框上方出现一枚提示条：「沿用第 N 次的构图」，右侧 × 按钮（`aria-label="不再沿用这张的构图"`）。点 × 清空高级参数里的种子框并隐藏提示条。N 是该尝试在会话里的序号（从 1 起，按 `attempts` 顺序）。 — 无裁决（面 F5 未盘问）
- D-42 提示条只在「种子框的值 == 被引用尝试的 seed」时显示；用户在高级参数里手动改了种子框，提示条隐藏。 — 无裁决（面 F5 未盘问）
- D-43 「高级参数」保持用户当时的折叠/展开状态，不因回填而自动展开。 — 无裁决（面 F5 未盘问）
- D-44 回填后用户点「生成图片」：新尝试的 `params.seed` 等于原尝试的 `seed`（验收：种子相同）。 — 无裁决（面 F5 未盘问）
- D-45 生成中该按钮仍可用（它只改输入框，不提交）。 — 无裁决（面 F5 未盘问）
- D-46 点击后立即提交：`prompt`、`width`、`height`、`steps` 取该尝试的值，`seed` 取前端新生成的随机数（`crypto.getRandomValues` 取 32 位无符号整数，0–4294967295），若恰好等于原 seed 则重取直到不同。`session_id` 为当前会话。 — 无裁决（面 F5 未盘问）
- D-47 不改输入框和高级参数里的任何值；新尝试追加在时间线末尾。 — 无裁决（面 F5 未盘问）
- D-48 生成中、正在提交、模型缺失、运行环境不可用、其他媒体作业占用时，该按钮 `disabled`，`title` 与按钮下方一行提示为不可用原因（与「生成图片」按钮同一原因文本，见 §7）。 — 无裁决（面 F5 未盘问）
- D-49 遇到 `insufficient_memory` 走现有确认框（「内存可能不足」/「仍要生成」），确认后带 `force: true` 重发；取消则什么都不写。 — 无裁决（面 F5 未盘问）
- D-50 「种子」二字只出现在「高级参数」折叠区内（输入框标签「种子（留空则每次随机）」和尝试详情的高级参数列表）。会话列表、时间线卡片、提示条、两个动作按钮、状态文案、确认框、错误提示中都不出现「种子」。 — 无裁决（面 F5 未盘问）
- D-51 服务端校验错误原文（如「种子须为 0–4294967295 的整数」）只可能由高级参数里的输入触发；前端在提交前自行校验，错误提示为「高级参数里的数值有误：种子须为 0–4294967295 的整数」，出现在高级参数区内（该区自动展开以便看到）。 — 无裁决（面 F5 未盘问）
- D-60 左上「新会话」按钮（主按钮样式、plus 图标，与聊天页同构）：`POST /api/image-sessions`，新会话成为当前会话、排在列表最上，时间线显示空会话态，焦点移到提示词输入框。每次点击都新建（与聊天页一致）。 — 无裁决（面 F5 未盘问）
- D-61 未新建时，生成总是追加到**当前会话**末尾（D-20 的 `session_id` 就是当前会话）。新建后生成的图只进新会话。 — 无裁决（面 F5 未盘问）
- D-62 首次进入图片页且没有任何会话时，**自动新建一个「新会话」并选中**，不显示「请先新建」的提示。理由：与聊天页 `refreshSessions` 相同行为（保持两个页面一致）；用户第一次来要做的事就是写提示词生成，多一步「先新建」没有任何信息量；空会话没有代价。这仍满足「会话需手动新建」——之后的每个新分组都由用户点「新会话」产生，生成本身从不暗中另开会话。 — 无裁决（面 F5 未盘问）
- D-63 当前会话的恢复（刷新页面或重启 app 后进入图片页）：优先选有 running 尝试的会话；否则选 `updated` 最新的会话。不用浏览器存储、不改地址栏 hash（与聊天页一致，状态只来自服务端）。同一次页面生命周期内切换 tab 再回来，当前会话不变。 — 无裁决（面 F5 未盘问）
- D-64 切换会话：清空种子框、隐藏提示条（它指向的是上一个会话里的尝试）；提示词、宽、高、步数保持不动。 — 无裁决（面 F5 未盘问）
- D-65 生成成功启动后：提示词保留在输入框（方便继续微调），种子框清空、提示条隐藏（下一次直接「生成图片」就是新的随机构图；要沿用就再点一次「在这张基础上改」）。宽、高、步数保持。 — 无裁决（面 F5 未盘问）
- D-66 新会话第一次生成使用随机种子：种子框默认为空（`placeholder="留空则每次随机"`），前端在提交时若种子框为空则不传 `seed`，由后端 D-19 取随机值。 — 无裁决（面 F5 未盘问）
- D-70 `#pane-image` 与 `#pane-chat` 同构：左侧 `aside.sessions`（宽 248px，复用 `.sessions` 样式与 `card session` 卡片、`session-actions` 的改名/删除图标按钮），右侧 `.image-main` 占满剩余宽度，内容最大宽 1400px，外边距 24px（视觉基线）。`#pane-image` 原来的「表单 | 作业」两栏 grid 与右侧 `.job` 区块取消，作业展示移入时间线里的 running 卡片。 — 无裁决（面 F5 未盘问）
- D-71 时间线**旧在上、新在下**（与聊天一致，输入区在底部）。打开会话、追加新尝试、尝试落定时滚动到底部。 — 无裁决（面 F5 未盘问）
- D-72 打开会话时默认选中（展开）最后一个尝试；新尝试开始时它成为选中项。同一时刻只展开一个；点击另一张卡片（或在卡片上按 Enter/空格）切换选中。卡片是可聚焦元素（`tabindex=0`、`aria-expanded`）。 — 无裁决（面 F5 未盘问）
- D-73 折叠卡片内容：「第 N 次 · HH:MM」、缩略图（96×96 容器，`object-fit: contain`，仅 done 且文件在时出现）、提示词摘要（最多两行，超出用省略号，`title` 属性为完整提示词）、尺寸步数「1024×1024 · 40 步」、状态标记（生成中 / 失败 / 已取消 / 图片文件已不在；完成不加标记）。 — 无裁决（面 F5 未盘问）
- D-74 展开卡片额外显示：大图（宽度不超过时间线列宽、高度不超过 60vh，`object-fit: contain`，`alt` 为提示词）、完整提示词、「高级参数」折叠块（列出 宽度、高度、步数、种子 四项实际值，默认折叠）、两个动作按钮（次级按钮样式，「在这张基础上改」在左，「换个构图」在右；「生成图片」是页面唯一主按钮）。 — 无裁决（面 F5 未盘问）
- D-75 输入区：提示条（D-41，按需出现）、提示词 textarea（placeholder 沿用「例如：一只橘猫坐在窗边，午后阳光，细腻的水彩插画」，⌘Enter 等同点「生成图片」）、「生成图片」主按钮（sparkles 图标）、「高级参数」`<details>` **默认折叠**（宽度（像素）默认 1024、高度（像素）默认 1024、步数默认 40、种子（留空则每次随机）默认空；折叠区内保留现有提示「建议从 1024×1024、40 步开始；更大图片需要更多时间与内存。」）、一行状态提示 `role=status`、一行错误 `role=alert`。 — 无裁决（面 F5 未盘问）
- D-76 头部一行：「生成图片」标题、模型状态（现有 `data-image-model` 文案）、「模型说明」折叠（现有 Heretic 说明文字）。 — 无裁决（面 F5 未盘问）
- D-77 会话列表项：标题（单行省略，`title` 属性为全称）、元信息「N 次生成 · HH:MM」（N = `attempt_count`，时间取 `updated`）、有 running 尝试时标题右侧显示「生成中」小标记（`--busy` 色圆点 + 文字）。当前会话 `aria-current="true"` 与聊天页相同高亮。 — 无裁决（面 F5 未盘问）
- D-78 窄窗 900×700：左栏仍 248px，右侧约 600px；卡片、输入区、按钮不出现横向滚动和文字截断（按钮文字不换行不裁切）；两个动作按钮放不下时换到下一行而不是被裁切。 — 无裁决（面 F5 未盘问）
- D-80 时间线居中显示两行：「还没有图片」／「在下面写下想要的画面，点「生成图片」。之后可以在任意一张上「在这张基础上改」或「换个构图」。」不显示空白图片框、不显示进度条。 — 无裁决（面 F5 未盘问）
- D-81 running 卡片始终展开显示：「第 N 次 · 生成中…（已用 1 分 20 秒）」（沿用 jobview 的 `formatDuration` 文案）、`<progress>`（沿用 `parseStepProgress`：解析到步数时显示百分比，否则为不确定进度）、「取消」按钮（调用 `/api/media/cancel`）、「日志」折叠块（默认折叠）、提示词摘要与尺寸步数。**不显示图片框**，也不显示两个动作按钮。 — 无裁决（面 F5 未盘问）
- D-82 进度数据来源：`main.js` 的 2 秒轮询 `tickJob` 取到 `kind == "image"` 的作业时交给图片页，图片页按 `attempt_id`（D-22）找到对应卡片更新；当前查看的会话不是该作业的会话时只更新会话列表的「生成中」标记。 — 无裁决（面 F5 未盘问）
- D-83 生成中「生成图片」和「换个构图」禁用，原因见 §7.6；「在这张基础上改」、切换会话、新建会话、重命名、删除都可用。 — 无裁决（面 F5 未盘问）
- D-84 这三种卡片**不渲染 `<img>`、不留空白图片框**；在缩略图位置显示一个图标块（失败：`x` 图标 + `--danger` 色；已取消：`x` 图标 + `--muted` 色；文件不在：`image` 图标 + `--muted` 色），块内无图片占位。 — 无裁决（面 F5 未盘问）
- D-85 原因文案： — 无裁决（面 F5 未盘问）
- D-86 这三种卡片都显示两个动作按钮（§5），参数都完整可用。 — 无裁决（面 F5 未盘问）
- D-87 「会话标题」取 `title`；判定「别的会话在生成」用列表摘要的 `running` 字段（§3.1），列表在每次轮询看到作业开始/结束时刷新。 — 无裁决（面 F5 未盘问）
- D-88 `POST /api/media/image` 返回错误时不出现新卡片，错误显示在输入区错误行：`insufficient_memory` 走确认框（D-49）；`session_not_found` → 刷新列表、按 D-63 选中会话，错误行显示「这个会话已被删除，已切到「<标题>」，请重新点「生成图片」」；其他错误显示 `describeJobError(error).title`（如「已有作业在进行」「图片模型不完整，请到资源页检查」「无法启动生成程序」）。 — 无裁决（面 F5 未盘问）
- D-89 重命名：与聊天页相同——点铅笔图标（`aria-label="改名"`）→ 列表项变成输入框并聚焦，Enter 或失焦保存，内容为空或未变则不请求；失败时错误行显示后端原因（如「标题须为 1–80 个字」）。 — 无裁决（面 F5 未盘问）
- D-90 删除：点垃圾桶图标（`aria-label="删除会话：<标题>"`）→ 确认框（`confirmDialog`，危险样式，默认焦点在「取消」）： — 无裁决（面 F5 未盘问）
- D-91 图片页不再使用 `createJobView` 的固定 DOM（`[data-job-status]` 等）；running 卡片复用它的纯函数部分：`formatDuration`、`parseStepProgress`、`describeJobError` / `renderErrorBlock`。视频、音乐页的 jobview 用法不变。 — 无裁决（面 F5 未盘问）
- D-92 `applyHeavyAvailability` 继续调用 `panes.image.setHeavyAllowed` / 忙碌原因；`tickJob` 对 `kind == "image"` 的作业调用图片页的 `applyJob(payload)`（替代原 `jobView.apply`）；`showTab("image")` 时图片页刷新会话列表与当前会话。 — 无裁决（面 F5 未盘问）
- D-93 `fillPlan` 对图片条目返回 `{pane:"image", session_id, attempt_id, fields:{prompt,width,height,steps,seed}}`，`seed` 缺失时为 `null`（不再补 42）。 — 无裁决（面 F5 未盘问）
- D-94 该条目带 `session_id` 且 `GET /api/image-sessions/{session_id}` 成功、其中有 `attempt_id` 对应的尝试：切到图片页、打开那个会话、选中（展开）该尝试并滚动到它，同时执行该尝试的「在这张基础上改」（D-40–D-42）。 — 无裁决（面 F5 未盘问）
- D-95 否则（没有 `session_id`、会话已删、尝试找不到）：切到图片页，停在当前会话，把条目参数按 D-40 填入输入区；提示条文案为「沿用素材库里这张的构图」（此时没有序号可引用）。不新建会话。 — 无裁决（面 F5 未盘问）
- B-01 三个目录：`data_root/image-sessions`、`data_root/video-sessions`、`data_root/music-sessions`，由 `PathRoots.media_sessions_dirs: dict[kind, Path]` 给出（取代 `image_sessions_dir`）。互不可见。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-02 写入纪律、id 规则、坏文件处理、锁、「读 → 改 → 原子写回、不持内存副本」全部继承 IS D-02、D-15。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-03 `kind` 与所在目录一致；文件里写了别的 kind 视为坏文件；没写 `kind` 的按所在目录的 kind 读（下次写回时补上）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-04 标题规则继承 IS D-10–D-13。自动标题取第一个尝试的「标题来源字段」：image/video 取 `prompt`，music 取 `caption`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-05 `op`：`generate` 为模型生成；`compose` 为手动合成（§4）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-06 `params` 按 kind 的白名单保存（§1.4），白名单外的键不写入。`seed` 一律是实际使用的值。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-07 `continues`：被续写的尝试 id，非续写为 `null`。仅 video/music。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-08 `joined_output` / `joined_error`：仅 `continues != null` 的尝试有意义；`done` 时二者恰有一个非空，其他状态都为 `null`。`compose` 尝试的成品放 `output`，这两个字段为 `null`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-09 `refs`：`{名称: {"kind", "session_id", "attempt_id"}}`，名称由下游定义（例如视频的 `first_frame`、`soundtrack`）。本文只规定结构、校验与解析（§5）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-10 `base`：仅 image，含义同 IS D-47b；其他 kind 恒为 `null`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-11 状态与字段取值继承 IS D-08、D-09（含 `cancelled_on_quit`、`interrupted`）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-12 `get(id)` 对每个 `done` 尝试附加 `output_missing`；对有 `joined_output` 的尝试再附加 `joined_missing`。都只出现在响应里，不写回文件。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-13 video/music 的白名单是**现有**生成参数加 `seed`；第 3 块若新增参数（如参考图、参考音频）在其 spec 中扩充白名单。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-20 尝试记录只由后端写（继承 IS D-14）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-21 接通要求：`runtime.py` 与 `desk/testing/harness.py` 都传 `media_sessions`；`/api/media-sessions/{kind}` 挂在生产路由与测试外壳路由上。仓库中不再有 `/api/image-sessions`、`ImageSessionStore`、`image_sessions_dir` 的引用。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-22 `chain` 防御环：回溯时记录已访问 id，重复即停（正常数据不会有环，因为 `continues` 只能指向已存在的更早尝试）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-30 `kind ∈ {image, video, music}`，其他 → 404 `不认识的媒体类型：<kind>`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-31 `GET/POST /api/media-sessions/{kind}`、`GET/PATCH/DELETE /api/media-sessions/{kind}/{id}` 的请求、响应、错误与 IS §3.1–3.5 一致；列表摘要的 `cover` 对 video/music 取最后一个 `done` 尝试的 `joined_output`（没有则 `output`）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-32 校验与挂接顺序：参数 → 会话 → `continues`（§3.3）→ `refs`（§5）→ `_start` 的既有检查（`media_busy` → `capability_missing` → `model_incomplete` → arbiter → `insufficient_memory`）→ 若需拼接则检查 ffmpeg（§6）→ 启动子进程 → 成功后 `begin_attempt`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-33 B-32 任一步失败都不写会话（继承 IS D-21）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-34 200 响应与 `job_status()` 对所有 kind 都带 `session_id`、`attempt_id`（IS D-22 推广）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-35 被续写的尝试须在同一会话、`status == done`、`output` 文件存在；否则 404 `segment_not_found` / `segment_missing`。`op == compose` 的尝试也可被续写（在成片后接着生）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-36 续写时模型的输入如何取自被续写的尝试： — 无裁决（面 F8 已盘问但无裁决引用它）
- B-37 截帧失败（ffmpeg 报错）→ 启动前 500 `frame_extract_failed`「没能从上一段截出最后一帧」，不写会话。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-38 `continues != null` 的作业：模型子进程成功产出后，**同一个工作线程**继续执行拼接，再落定。拼接期间作业仍是 `running`，日志追加一行 `[join] 正在拼接成片…`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-39 拼接的片段 = `chain(本尝试)` 中每一项的「单段文件」按顺序；**不使用**上一段的 `joined_output` 再加一段。理由：片段各自独立，任何一次拼接都能只从单段文件重建。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-40 链断（某项文件不在、或 `broken`）→ 本尝试 `done`，`joined_output = null`，`joined_error = {"code": "segment_missing", "message": "第 N 段的文件已不在，无法拼成成片"}`（N 为链中序号，从 1 起）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-41 拼接命令失败 → 本尝试 `done`，`joined_error = {"code": "join_failed", "message": "拼接成片失败", "log_tail": …}`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-42 成片文件名：视频 `h3-joined-<stamp>-<8hex>.mp4`，音乐 `music3-joined-<stamp>-<8hex>.wav`，写在 `outputs_root`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-43 history：所有 kind 的条目都带 `session_id`、`attempt_id`；拼接成功时再加 `joined_output`。`HistoryStore.by_output()` 同时按 `output` 与 `joined_output` 建索引，使素材库列出成片时带上它的 history（不显示为孤儿文件）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-44 `kind` 为 image 或不认识 → 400；`parts` 须为 2 个及以上的字符串数组，可以重复同一个 id（允许同一段出现两次）；每项按 B-35 校验（`segment_not_found` / `segment_missing`）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-45 检查顺序：参数 → 会话 → parts → `media_busy` → ffmpeg 可用性 → 启动。**不经过** arbiter、模型检查、内存提醒（ffmpeg 开销小；符合「不要太严格」）。`force` 接受但无作用，保留只为前端统一重发逻辑。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-46 启动成功后 `begin_attempt`：`op = "compose"`、`params = {"parts": [...]}`、`continues = null`、`refs = {}`。标题：会话第一个尝试是 compose 不可能发生（parts 需要已有尝试），故不涉及自动标题。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-47 compose 作业与生成作业共用 `_state`、互斥、`job_status`、轮询、取消、`close()`、history（`kind` 为 `video|music`，`params.op = "compose"`）、落定。成功 → `output` 为成品；失败 → `failed` + `join_failed`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-48 片段用各自的「单段文件」：generate 尝试用 `output`（不用其 `joined_output`），compose 尝试用 `output`。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-50 video：重编码 concat（`libx264`、`yuv420p`、`aac`），**每个续写关系上的后一段丢首帧**：若 `parts[i+1].continues == parts[i].id`，则 `parts[i+1]` 丢首帧；否则不丢（手动乱序合成时不是尾帧接首帧的关系）。各段宽高不一致时按第一段宽高缩放并补边（`scale` + `pad`，保持比例）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-51 music：相邻两段 `acrossfade=d=1.5:c1=tri:c2=tri`；任何一段短于 3 秒时该接缝改为直接拼接（不交叉淡化）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-52 具体数值（丢帧数、淡化时长）写在 `compose.py` 常量里，第 2、3 块如需调整在其 spec 内改。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-55 每项 `{kind, session_id, attempt_id}`；`kind` 须为该引用名称注册的允许值；目标会话、尝试须存在、`done`、文件在；否则 404 `ref_missing`「引用的<图片/音乐/视频>已不在」（中文名按目标 kind）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-56 解析结果是一个文件路径，由 `MediaService` 交给该 kind 的命令构造；尝试记录只存引用三元组，不存路径。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-57 引用是单向指针：删除被引用会话不影响已生成的尝试；再次用该尝试「在这个基础上改」时若引用失效，按 B-55 返回 404，由下游界面提示。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-58 本文**不注册任何引用名称**；机制以测试用的假名称验证。第 3 块注册 `first_frame`（image）、`soundtrack`（music）等。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-60 ffmpeg 不可用：只有**需要拼接或截帧**的请求返回 503 `capability_missing`「需要 ffmpeg 才能拼接成片」；普通生成不检查。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-61 拼接（自动与手动合成）的子进程经 `MediaService` 现有 executor 运行，日志进作业日志，取消走同一套 `terminate/kill`。截末帧在请求内同步执行（不到 1 秒，超时 60 秒），失败按 B-37 返回。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-62 内存：这些作业不接 `estimate_bytes`、不做内存提醒（B-45）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-70 （**2026-09-25 修订：移到第 2 块**。理由：image.js 的会话逻辑与图片专属状态（提示条、种子框、底稿、大图自适应）交织很紧，只有一个使用方时抽出的接口只能靠猜；第 2 块有了音乐页这个真实的第二使用方再抽。本块前端只改接口路径与 `fillPlan`。以下为第 2 块的要求。）`panes/media_session.js` 导出一个工厂：参数为 `kind`、输入区与卡片内容的渲染回调；负责会话列表四种状态（IS §7.2）、自动新建首个会话（IS D-62）、当前会话恢复（IS D-63）、时间线骨架与选中展开（IS D-71、D-72）、running 卡片与轮询挂接（IS D-81、D-82）、改名删除（IS D-89、D-90）、忙碌原因中「别的会话在生成」（IS §7.6）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-71 图片页改用该模块后，IS 全部 D-xx 仍成立；图片页 DOM 文本、按钮、文案逐字不变。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-72 删除确认正文中的「图片」按 kind 替换为「视频 / 音乐」由工厂参数提供；本文只要求 image 的文案不变。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-73 本文不改 `panes/video.js`、`panes/music.js`。它们不传 `session_id`，按 §3.2 照旧能生成；`main.js` 的 `tickJob` 对 video/music 作业（含 compose）仍交给它们的 jobView 显示。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-74 `fillPlan`：video/music 条目带出 `session_id`、`attempt_id`（同 IS D-93）；`params.op == "compose"` 的条目返回 `null`（没有可回填的参数，素材库不显示「回填参数」）。 — 无裁决（面 F8 已盘问但无裁决引用它）
- B-75 给下游的约束（第 2、3 块界面必须实现，本文后端已备好）：卡片的 `joined_error.code ∈ {join_failed, join_cancelled, interrupted}` 时提供「重新拼接」，行为是发起 `compose`，`parts = chain(该尝试)` 各项 id，结果作为新的成片卡片追加；`segment_missing` 不提供（缺的文件补不回来），只显示原因。 — 无裁决（面 F8 已盘问但无裁决引用它）
- M-01 控制器承担 IS §6–§7 与 §3.7 中与媒体种类无关的全部行为：会话列表四种状态（IS §7.2）、自动新建首个会话（IS D-62）、当前会话恢复（IS D-63）、切换（IS D-64，经 `composer.onSessionSwitch`）、时间线骨架与选中展开（IS D-71、D-72）、running 卡片进度与日志（IS D-81、D-82）、落定后重取（IS D-27）、改名删除（IS D-89、D-90）、忙碌原因（IS §7.6，名词取 `noun`）、「回到该会话」、内存确认重发（IS D-49）、`session_not_found` 自动切换（IS D-88）、滚动意图（贴底 / 对齐选中 / 用户滚动后不拽）与 ResizeObserver。 — 无裁决（面 F7 未盘问）
- M-02 图片页专属的「展开卡片大图自适应」（IS D-74 的 `fitExpandedImage`）经 `renderCard` 返回的 `image` 节点接入：控制器只在 `image` 存在时调用页面提供的适配（由 `image.js` 以回调形式传入 `fitExpanded(node, image)`），音乐页不传。 — 无裁决（面 F7 未盘问）
- M-03 纯逻辑参数化：`availability(state, {noun})`、`deleteMessage(summary, {noun})`、`runningSessionId(job, sessions, kind)`；其余（`sessionTitle`、`sessionMeta`、`attemptLabel`、`orderSessions`、`pickCurrent`、`randomSeed`、`ParamsError`、`autoTitle`）原样迁移。图片页调用时 `noun="图片"`，产出的文案与迁移前逐字相同。 — 无裁决（面 F7 未盘问）
- M-04 **图片页零回归**：`tests/js/image_pane.test.js` 与 `tests/e2e/test_image_sessions.py`、`tests/e2e/test_image_flow.py` 的断言不改（只允许改 import 路径与挂载方式），全部通过。 — 无裁决（面 F7 未盘问）
- M-05 时间线上方工具行出现次级按钮「挑几段合成…」（`data-<prefix>-compose-start`）。会话没有 ≥2 个 `done` 且文件在的尝试时按钮 `disabled`，`title`「至少要有两段完成的才能合成」。 — 无裁决（面 F7 未盘问）
- M-06 进入模式：每张 `done` 且文件在的卡片左侧出现勾选框（`aria-label="选中第 N 次"`）；其余卡片不可选、不变灰。卡片点击在此模式下切换勾选而非展开。 — 无裁决（面 F7 未盘问）
- M-07 勾选顺序即拼接顺序，已选卡片显示序号徽标 ①②③…；取消勾选后其后序号前移。 — 无裁决（面 F7 未盘问）
- M-08 底部输入区替换为合成栏：按顺序列出已选段（「第 N 次 · 时长」），每项「上移」「下移」「移除」（图标按钮，`aria-label` 同名）；右侧主按钮「合成（K 段）」，次级按钮「取消」。K<2 时主按钮 `disabled`，原因行「至少选两段」。有作业在跑或服务不可用时 `disabled`，原因同 IS §7.6 第一条可用原因。 — 无裁决（面 F7 未盘问）
- M-09 点「合成」：`POST /api/media/compose {kind, session_id, parts}`；成功启动 → 退出挑选模式、恢复输入区、新 compose 尝试追加并选中（running 卡片）；失败 → 留在模式内，错误显示在合成栏错误行（`describeJobError` 标题，`capability_missing` 显示后端原话「需要 ffmpeg 才能拼接成片」）。 — 无裁决（面 F7 未盘问）
- M-10 「取消」、切换会话、新建会话都退出挑选模式并清空已选。 — 无裁决（面 F7 未盘问）
- M-11 界面不允许同一段选两次（勾选框语义）。B-44 后端允许重复，界面不提供。 — 无裁决（面 F7 未盘问）
- M-20 左栏、主区宽度、外边距、窄窗 900×700 规则同 IS D-70、D-78。原 `.form | .job` 两栏与 jobview 删除。 — 无裁决（面 F7 未盘问）
- M-21 输入区：提示条（M-26）；风格描述 `<input>`（`placeholder` 沿用「例如：温柔的民谣，木吉他伴奏，女声轻唱，慢速」，`aria-label="风格描述"`）；歌词 `<textarea>`（`placeholder="歌词（必填）"`，默认 4 行，聚焦或内容超出时增高，最高 `50vh`，失焦且内容不超 4 行时回落）；「AI 帮写」行（原 `data-music-assist`）；主按钮「生成歌曲」（sparkles 图标，⌘Enter 等同点击）；「高级参数」`<details>` 默认折叠，内含「时长（秒）」（10–300，默认 60，下方保留提示「成品时长由模型按歌词决定，常短于所填时长；素材库会标注实际时长。」）与「种子（留空则每次随机）」；状态行 `role=status`；错误行 `role=alert`。 — 无裁决（面 F7 未盘问）
- M-22 头部：「生成歌曲」、模型状态（沿用现有音乐模型状态文案来源）、「模型说明」折叠（MiniMax Music 3 · MLX 本机推理；需要歌词；成品为 WAV）。 — 无裁决（面 F7 未盘问）
- M-23 空会话：「还没有歌曲」／「在下面写风格描述和歌词，点「生成歌曲」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着写下一段」。」 — 无裁决（面 F7 未盘问）
- M-24 生成成功启动后：风格描述、歌词、时长保留；种子框清空；提示条若为「沿用第 N 次」则隐藏，若为「接在第 N 次后面」也隐藏（下一次生成回到普通生成，除非再点「接着写下一段」）。 — 无裁决（面 F7 未盘问）
- M-25 「种子」二字只出现在「高级参数」内（同 IS D-50）。 — 无裁决（面 F7 未盘问）
- M-26 两种，互斥： — 无裁决（面 F7 未盘问）
- M-27 提示条可见时点「生成歌曲」的请求：沿用 → 带被引用尝试的 `continues`（若它有，M-31）；续写 → `continues = 被续写尝试 id`。提示条不可见 → 不带 `continues`。 — 无裁决（面 F7 未盘问）
- M-28 若被引用 / 被续写的尝试已不再是 `done` 且文件在（`output_missing` 或会话刷新后找不到），提示条改为「第 N 次的文件已不在，不能接着写」并带 ×，「生成歌曲」`disabled`、原因同文案；点 × 回到普通生成。后端返回 `segment_missing` / `segment_not_found` 时同样处理。 — 无裁决（面 F7 未盘问）
- M-30 折叠：标题行「第 N 次 · HH:MM」＋（续写）「接第 M 次」／（合成）「合成：第 a、b、c 次」（引用的尝试不在列表中时显示「合成」）；风格描述摘要（一行省略，`title` 全文）；歌词首个非空、非 `[段落标记]` 行（一行省略）；状态标记（生成中 / 失败 / 已取消 / 文件已不在；完成不标）。 — 无裁决（面 F7 未盘问）
- M-31 展开： — 无裁决（面 F7 未盘问）
- M-32 失败 / 已取消 / 文件不在：不渲染 `<audio>`，图标块与原因同 IS D-84、D-85；动作按钮按 M-33–M-35 的可用性显示。 — 无裁决（面 F7 未盘问）
- M-33 **在这段基础上改**：回填风格描述、歌词、时长、种子；提示条「沿用第 N 次」；焦点到歌词框末尾；不提交；生成中可用（同 IS D-45）。失败 / 取消的尝试也可用（参数完整）。 — 无裁决（面 F7 未盘问）
- M-34 **换个版本**：立即提交 `{session_id, caption, lyrics, duration, seed: 新随机数≠原值, continues: 原尝试的 continues}`；不改输入区。不可用条件同 IS D-48（生成中、提交中、模型缺失、运行环境不可用、其他作业占用）。 — 无裁决（面 F7 未盘问）
- M-35 **接着写下一段**：风格描述、时长 ← 该尝试（compose 尝试：保留输入区当前值）；歌词清空；种子框清空；提示条「接在第 N 次后面」；焦点到歌词框；不提交。仅 `done` 且文件在的尝试显示为可用；否则 `disabled`，下方原因「这一段没有生成好，不能接着写」。 — 无裁决（面 F7 未盘问）
- M-36 回填不改变「高级参数」的折叠状态（同 IS D-43）。 — 无裁决（面 F7 未盘问）
- M-40 尝试 `done` 且 `joined_error` 非空时，展开卡片在播放器下显示一行：「这一段生成好了，但成片没拼成：<原因>」，原因取 `joined_error.message`。 — 无裁决（面 F7 未盘问）
- M-41 `joined_error.code ∈ {join_failed, join_cancelled, interrupted}` 时该行带次级按钮「重新拼接」：提交 `compose`，`parts` = 前端回溯出的链（M-31）各项 id，全部可找到且 `done`、文件在时才可用，否则按钮 `disabled`、原因「链上有一段已不在」。成功后新合成卡片追加并选中（B-75）。成片文件被删（`joined_missing`）同样显示问题行并按 M-41 提供重新拼接；问题行文案为「这一段生成好了，但成片文件已不在」。 — 无裁决（面 F7 未盘问）
- M-42 `segment_missing` 不提供按钮，只显示原因。 — 无裁决（面 F7 未盘问）
- M-50 `start_music_job` 的 `session_id` 改为必填：缺失 / 非字符串 → 400 `session_required`，不存在 → 404 `session_not_found`（同 IS D-18 文案）。`continues`、`refs` 规则不变。 — 无裁决（面 F7 未盘问）
- M-51 `main.js`：`tickJob` 对 `kind == "music"`（含 compose 作业，`params.op == "compose"` 且 kind 为 music）调用 `panes.music.applyJob`；`showTab("music")` 调 `panes.music.refresh()`；`applyHeavyAvailability` 调 `panes.music.setHeavyAllowed`；删除对 `panes.music.jobView` 的所有调用。`kind == "video"` 仍走视频页 jobview。 — 无裁决（面 F7 未盘问）
- M-52 素材库回填：`applyFill` 对 `plan.pane == "music"` 调 `panes.music.applyFill(plan)`：有 `session_id`、`attempt_id` 且能找到 → 切到音乐页、打开会话、选中该尝试并执行「在这段基础上改」；否则停在当前会话按 M-33 回填字段，提示条文案「沿用素材库里这首」（同 IS D-94/95）。 — 无裁决（面 F7 未盘问）
- M-53 音乐模型状态与运行环境：`main.js` 以与图片页相同的方式接通（不新增后端）——资源页 `onModels` 回调里 `panes.music.setModelStatus(models?.find((m) => m.key === "music3"))`；能力探测处 `panes.music.setRuntimeStatus(capabilities?.music_runtime)`。文案：模型缺失「尚未安装音乐模型，请到「资源」页下载」，不完整「模型不完整，请到「资源」页继续下载或校验」，未知「暂时无法确认模型状态，请稍后重试」；运行环境不可用「音乐 MLX 运行环境不可用，请检查服务或应用安装」（`capability.detail` 优先）；就绪时头部显示「模型文件完整 · 可离线生成」。 — 无裁决（面 F7 未盘问）
- V-01 `start_video_job` 的 `session_id` 必填（同 M-50 文案与状态码）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-02 `MediaService` 默认注册引用槽 `{"video": {"first_frame": "image"}}`（构造参数 `ref_slots` 未传时使用该默认；测试可覆盖）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-03 请求带 `refs.first_frame`：要求 `mode == "image"`，且请求不再带 `first_frame` 素材 id；否则 400 `invalid_params`「首帧只能从上传或图片会话二选一」。`continues` 与 `refs.first_frame` 同时出现 → 400（沿用 CONTINUE_CONFLICT 文案）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-04 解析出的图片路径直接作为 H3 `--first-frame` 参数；`params.first_frame` 记为 `null`（尝试的 `refs` 已记下引用，B-56）。引用失效 → 404 `ref_missing`「引用的图片已不在」（B-55）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-05 历史条目与素材库不变；`fillPlan` 对 video 条目带出 `refs`（`entry.params` 不含 refs，故 history 条目增加顶层 `refs` 字段，只在非空时出现）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-10 `attemptView(attempt, {broken, noun})` 移到 `pure/media_session.js`：missing 文案「<noun>文件已不在」（图片页仍得到「图片文件已不在」，逐字不变）；音乐卡片改用它（传 `noun: "音频"`，文案「音频文件已不在」——音乐卡片当前的「文件已不在」改为此）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-11 控制器 `renderCard` 返回的 `recompose` 改名 `secondary`（`{button, hint}`），`composer.updateAvailability(state, {secondary})`；卡片参数 `noImageReason` 改名 `secondaryBlockedReason`。图片页行为与文案不变（M-04 规则同样适用：`tests/js/image_pane.test.js` 断言不改）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-20 左栏会话、头部「生成视频」+ 模型状态 + 「模型说明」（MiniMax H3 · MLX 本机推理；输出带声音的 MP4；「接着往下生」用上一段的最后一帧作首帧，拼接处可能有动作跳变）、时间线、底部输入区。原表单 + jobview 删除。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-21 输入区（自上而下）：提示条（V-30）；「生成方式」`<select>`（文生视频 / 图生视频 / 视频参考生成）；素材行（按方式出现，V-22）；提示词 `<textarea>`（默认 3 行，聚焦/超出时增高，最高 40vh；placeholder 随方式变化，沿用现有三条）与「生成视频」主按钮（⌘Enter）；「AI 帮写」行；「高级参数」`<details>` 默认折叠：画幅（现有三档）、视频时长（现有六档）、耗时提示（`videoCostNote`）、步数（默认 16，4–50）、种子（留空则每次随机）、「使用素材的声音」勾选（仅图生/参考方式可见，默认勾选）；上传状态行；状态行；错误行。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-22 素材行： — 无裁决（面 F6 已盘问但无裁决引用它）
- V-23 「从图片会话选…」打开选择框（`confirmDialog` 风格的模态，`role="dialog"`，标题「从图片会话选首帧」）：左侧图片会话列表（标题 + N 次生成），右侧该会话中 `done` 且文件在的图片缩略图网格；点缩略图即选中并关闭；「取消」关闭不改变。无可选图片时显示「这个会话还没有生成好的图片」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-24 空会话：「还没有视频」／「在下面写提示词，点「生成视频」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着往下生」。」 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-25 「种子」只出现在高级参数内。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-30 提示条三种（互斥）：沿用「沿用第 N 次」（规则同 M-26 沿用型）；续写「接在第 N 次后面」（同 M-26 续写型，续写目标失效同 M-28，文案「第 N 次的文件已不在，不能接着往下生」）；素材库「沿用素材库里这段」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-31 折叠：「第 N 次 · HH:MM」＋「接第 M 次」／「合成：第 a、b 次」；方式标签（文生 / 图生 / 参考）；提示词摘要（两行省略）；规格「512×288 · 约 3 秒 · 16 步」（时长文案取 DURATIONS 最接近项）；状态标记。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-32 展开 done：`<video controls preload="metadata">`（宽不超过时间线列宽，高不超过 50vh），有可用成片时默认播成片，「成片 | 只看这一段」切换（同 M-31）；续写链说明「由：第 1 次 → 第 3 次」；成片问题行与「重新拼接」（同 M-40–M-42）；首帧来源行（图生且有 refs.first_frame：「首帧：图片会话「<标题>」第 N 次」；标题取不到时「首帧：来自图片会话」）；完整提示词；「高级参数」折叠（画幅、时长、步数、种子）；动作按钮。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-33 失败 / 取消 / 文件不在：同图片卡片规则（图标块，无 `<video>`）。`<video>` 报错 → 文件不在状态。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-34 挑选合成模式：同 M-06/M-07 与最终修订（卡片只做勾选，不显示动作与「重新拼接」）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-40 **在这段基础上改**：回填方式、提示词、画幅、时长、步数、种子；图生时回填首帧来源（上传素材 id 作为已保存素材 / 图片会话引用 / 续写关系）与尾帧；参考时回填参考视频素材 id；提示条「沿用第 N 次」；不提交。若首帧来源为图片会话引用且已失效 → 首帧区显示「引用的图片已不在」并清空首帧来源。续写段回填后生成仍接在原位置（带原 `continues`）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-41 **换个版本**：立即提交原尝试参数（含素材 id / 引用 / `continues`），种子换新随机数≠原值。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-42 **接着往下生**：方式切到图生、首帧来源为续写（V-22 第三种说明）、尾帧清空；提示词清空；画幅、时长、步数沿用该段；种子清空；提示条「接在第 N 次后面」；焦点到提示词。仅 done 且文件在可用，否则原因「这一段没有生成好，不能接着往下生」。compose 尝试：画幅、时长、步数保留输入区当前值。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-43 生成成功启动后：提示词、方式、画幅、时长、步数保留；种子清空；沿用/续写提示条隐藏；续写的首帧来源清空（回到「未选择」）；上传与图片会话来源保留。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-50 图片卡片展开时，done 且图片在的卡片在两个动作右侧增加次级按钮「用这张生成视频」。点击：切到视频页，方式设为图生，首帧来源设为该图片的引用（`{kind:"image", session_id, attempt_id}`），首帧说明「首帧：图片会话「<标题>」第 N 次」，提示词不变，焦点到提示词。图片页其余行为不变（新增按钮不影响现有按钮与文案）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-51 跨页通信经 `main.js`：图片页 `ctx.onUseAsFirstFrame(ref, label)` → `showTab("video")` → `panes.video.useFirstFrame(ref, label)`。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-60 `main.js`：`tickJob` 对 `kind == "video"` 调 `panes.video.applyJob`；`showTab("video")` 调 `panes.video.refresh()`；`applyFill` 对 video 与 image/music 同样走 `panes.video.applyFill`；模型状态 `h3` 目录项、运行环境 `mlx_h3` 能力；删除所有 `jobView` 使用；`widgets/jobview.js` 若不再被任何页面使用则删除（其纯函数部分已在 `pure/`）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- V-61 素材库回填视频条目：同 M-52（找得到会话 → 打开并执行「在这段基础上改」；否则按字段回填、提示条「沿用素材库里这段」）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-01 新接口 `POST /api/media/soundtrack`，体 `{session_id, source, refs: {soundtrack: {kind:"music", session_id, attempt_id}}, force?}`；`kind` 固定 video。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-02 校验顺序：参数（`source` 字符串、`refs.soundtrack` 结构）→ 视频会话（必填，同 V-01）→ `source` 为本会话 done 且文件在的尝试（`segment_not_found` / `segment_missing`）→ 音乐引用解析（`ref_missing`「引用的音乐已不在」）→ `media_busy` → ffmpeg（503「需要 ffmpeg 才能拼接成片」）→ 启动。不走 arbiter、模型检查、内存提醒（同 B-45）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-03 输入视频：`source` 有未缺失的 `joined_output` 用它，否则用 `output`。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-04 命令：`compose.soundtrack_command(ffmpeg, video, audio, output)`：视频流拷贝，音频 `aac`，音频 `apad` 补静音，时长以视频为准（`-shortest` 在 apad 之后生效）；输出最后一个参数（B §6 约定）。原 `replace_audio_command` 替换为此（仅此处用）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-05 尝试：`op = "soundtrack"`，`params = {"source": <attempt_id>}`，`refs = {"soundtrack": <music ref>}`，`continues = null`；成功 `output` 为 `h3-soundtrack-<stamp>-<8hex>.mp4`；失败 `failed` + `join_failed`，未完成时删除半成品（同合成）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-06 history 条目 `params.op = "soundtrack"`、顶层 `refs`；`fillPlan` 对 `op ∈ {compose, soundtrack}` 返回 null。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-07 配乐尝试可被续写（B-35 放宽到 op soundtrack）与参加合成（`find_done` 不区分 op）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-10 `start_video_job` 接受 `mode = "music_ref"`：必须有参考图（`ref_image` 上传素材 id，或 `refs.ref_image = {kind:"image", …}`，二选一，否则 400「参考图只能从上传或图片会话二选一」/ 缺失 400「请先选择参考图」）与 `refs.ref_audio = {kind:"music", …}`（缺失 400「请先选择一首歌」），以及 `audio_start`（秒，≥0 的数，默认 0）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-11 注册引用槽：`video.ref_image → image`、`video.ref_audio → music`（与 `first_frame` 并列）。`music_ref` 不能与 `continues`、`first_frame`、`last_frame`、`ref_video`、`refs.first_frame` 同用（400 invalid_params，文案「配乐参考不能和首帧、尾帧或续写同时使用」）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-12 截取：服务端在启动前用 ffmpeg 从歌中 `audio_start` 起截取 `clip = clamp(frames / 24, 2, 15)` 秒到 `.inputs/<hex>.wav`；歌短于 `audio_start + 2` 秒 → 400「这首歌从第 N 秒起不足 2 秒」；截取失败 → 500 `audio_clip_failed`「没能截取这段音乐」；之后任一步失败删除截取文件（同 B-37 做法）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-13 命令：`build_h3_command(..., ref_image=<path>, ref_audio=<path>)` 追加 `--ref-image <path> --ref-audio <path>`（H3 Ref2VA，spike 已验证可跑）。`params` 记 `mode="music_ref"`、`audio_start`、`ref_image`（上传 id 或 null），尝试 `refs` 记引用。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-14 估算同普通视频（`estimate_bytes("video", params)`），标 predicted。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-20 `widgets/media_picker.js::openMediaPicker(doc, {kind, title, emptyText, listSessions, getSession, serveOutput})`：`kind ∈ {image, music}`；图片为缩略图网格（同 V-23），音乐为列表：每项「第 N 次 · <风格描述摘要>」+ `<audio controls preload="none">` 试听 + 「选这首」按钮；只列 done 且文件在的尝试（音乐优先成片 `joined_output`，无则 `output`）。返回 `null | {ref, title, index, label}`（`label` 为风格描述摘要，图片为提示词摘要）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-21 `widgets/image_picker.js` 删除，视频页首帧改用 `openMediaPicker({kind:"image", title:"从图片会话选首帧", emptyText:"这个会话还没有生成好的图片"})`；音乐 `title` 由调用方给，`emptyText`「这个会话还没有生成好的歌」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-30 视频卡片（done 且文件在、非挑选模式）动作区增加次级按钮「配乐…」：打开音乐选择框（标题「选一首歌配到这段视频」）→ 选中即 `POST /api/media/soundtrack`（`source` = 该尝试）→ 新卡片追加并选中。不可用条件同「换个版本」（有作业在跑等），原因同一套。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-31 配乐卡片：折叠标题「第 N 次 · HH:MM · 配乐：<风格描述摘要> · 基于第 M 次」（M 取不到则省略该段；风格描述取不到显示「配乐」）；展开播放 `output`；动作只有「接着往下生」与「配乐…」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-32 「生成方式」下拉新增「配乐参考（实验性）」。选中时素材区：参考图区（「上传图片」+「从图片会话选…」+ 说明）、歌区（「从音乐会话选…」+ 所选歌说明「歌：<风格描述摘要>」+ 试听）、数字框，标签「从第几秒开始」（默认 0，≥0）、说明「实验性：画面不保证跟随音乐节奏；参考图只影响画面风格，不作为第一帧。截取与视频等长、2–15 秒的一段音乐。」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-33 提交：`mode:"music_ref"`、`audio_start`、`ref_image`（上传 id）或 `refs.ref_image`、`refs.ref_audio`。缺参考图「请先选择参考图」、缺歌「请先选择一首歌」（前端先校验）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-34 「在这段基础上改」对 music_ref 尝试回填参考图来源、歌、起始秒；引用失效时对应说明「引用的图片已不在」/「引用的歌已不在」并清空。「换个版本」原样重发（新种子）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- S-35 900×700：新增的素材在已有可滚动的素材区内（V 块 50vh 规则），不增加输入区固定行。 — 无裁决（面 F6 已盘问但无裁决引用它）
- L-01 合并规则沿用现状：历史与成品按文件名匹配；一条历史的 `output` 与 `joined_output` 各占一条（B-43）；没匹配到历史的成品单独一条（「无历史记录」）；有历史但文件都不在的也占一条。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-02 每条条目归一为：`{ key, kind: "image"|"video"|"music"|"file", status, ts, title, prompt, spec, duration_s?, width?, height?, bytes?, gen_s?, output?: name, missing: bool, entry?: 历史记录, error? }`。`key` 跨刷新稳定（L-32 靠它保持选中）：有文件用 `o:<文件名>`，否则 `h:<ts>:<kind>:<attempt_id 或空>`，同一次渲染内重复时追加 `#2`、`#3`。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-03 `missing`：有历史、状态为完成、`output` 名在成品列表里找不到。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-04 时长：音乐取 `audio_seconds`，否则 `params.duration`；视频取 `params.frames / 24`；图片无。画幅取 `params.width×height`。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-05 筛选：`all | image | video | music`；`file` 类只在 `all` 下出现。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-06 排序：键为 `ts`（生成时间）| `title`（提示词）| `kind`（类型）| `duration`（时长）| `dims`（画幅，按宽×高面积）| `bytes`（文件大小）| `gen`（耗时），方向 `asc | desc`；缩略列不可排序；缺值一律排在最后（不论方向）；`title` 用 `localeCompare(…, "zh")`；同值按 `ts` 倒序稳定。默认 `ts desc`。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-10 工具栏一行：左侧类型筛选分段控件（全部 / 图片 / 视频 / 音乐，复用 `widgets/segment_switch.js`，它按 `labels` 数组生成任意项数，只需改掉文件头「两项」的注释）；右侧视图切换三个图标按钮（缩略图 / 列表 / 明细，`aria-pressed`、`aria-label`），缩略图视图时出现大小滑块，最右「刷新」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-11 视图、筛选、缩略图大小、明细排序记在 `localStorage` 键 `lmd.library`（JSON）；读写都包 try/catch，读不到用默认值（缩略图、全部、200px、`ts desc`）；值非法时回落默认。缩略图大小滑块是普通 `input[type=range]`，方向键只调大小，不移动选中（L-31 只在条目区内生效）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-12 筛选后为空：显示「没有这类成品」并写明当前筛选（例：「当前筛选：视频」）；整体为空沿用现有引导语。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-20 缩略图：自适应网格 `repeat(auto-fill, minmax(var(--lib-thumb), 1fr))`，滑块调 `--lib-thumb` 140–320px。卡片：方形媒体区 + 提示词两行截断 + 时间一行。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-21 图片卡片：`<img loading="lazy">`，`object-fit: cover`。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-22 视频卡片：进入视口（IntersectionObserver；环境没有时直接加载）才设 `src=<url>#t=0.1`、`preload="metadata"`、`muted`、`playsinline`；角标显示时长。鼠标悬停静音播放，移开暂停并回到 0.1 秒；同一时刻最多一个卡片在悬停播放。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-23 音乐卡片：渐变底 + 音乐图标 + 时长。`file` 类（不认识的文件）：文件图标 + 文件名。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-24 音乐卡片右上角小播放按钮就地试听（右下角是时长角标）：页面只有一个隐藏的 `<audio>`；按钮 `aria-pressed` 与图标（播放/暂停）反映状态，再点暂停；开别的试听、打开预览、点「刷新」重画、离开素材库页时都停掉并复位按钮；点按钮不触发选中/打开。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-25 失败/取消（无成品）：灰卡 + 警示图标 + 状态字；`missing`：灰卡 + 「文件已不在」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-26 媒体加载失败（img/video `error`）：该卡片退回类型图标占位，不影响其他卡片。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-27 列表：每行 48px 缩略图（规则同 L-21/L-22，但视频不悬停播放）+ 提示词 + 元信息行（类型 · 状态 · 时间 · 耗时 · 规格）+ 右侧动作（预览、在访达中显示、回填参数）；失败记录照旧显示错误块（F3）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-28 明细：`<table>`，列：缩略（32px）、提示词、类型、生成时间、时长、画幅、大小、耗时。除缩略列外表头是按钮，点击按该列排序，再点反向，`aria-sort` 标当前列；缺值显示「—」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-30 每个条目的主体是一个 `<button data-lib-item>`（缩略图视图是整张卡片的媒体+文字区，列表是缩略图+文字区，明细是提示词单元格），`aria-label` 为标题；动作按钮（试听、预览、在访达中显示、回填）是它的兄弟节点，不嵌套在里面（避免交互元素嵌套）。单击主体 = 选中（`aria-current="true"` + 选中样式）；双击主体，或焦点在主体上按 Enter/空格 = 打开预览（`preventDefault`，不再额外触发选中之外的点击）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-31 roving tabindex：所有主体里只有选中项（没有选中时是第一项）`tabIndex=0`，其余 `-1`；方向键只在焦点位于某个主体上时处理，移动时同时移动选中与焦点并滚入视野（`block: "nearest"`）。缩略图视图 ←/→ 前后一个，↑/↓ 跳一行：列数 = 与第一项 `offsetTop` 相同的前导项个数，量不到（0）时 ↑/↓ 退化为 ←/→；列表/明细 ↑/↓ 前后一个。到头停住，不循环。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-32 切换筛选、排序、刷新后：原选中项仍在就保持，否则清空选中。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-33 动作按钮（预览、在访达中显示、回填、试听）点击与按键都不冒泡为选中/打开；各自行为同现状（reveal 失败把服务端文案写进错误行，issue #12）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-40 复用遮罩 + `role=dialog` + `aria-modal` + Esc/点遮罩关闭的骨架；打开时焦点进弹层，关闭后焦点与选中回到最后预览的条目。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-41 主区：图片按窗口适配；视频 `controls autoplay`（有声）；音乐大卡片 + `<audio controls autoplay>`；失败显示错误块；`missing` 显示「文件已不在」；`file` 类显示「无法预览这种文件」，信息区照常。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-42 信息区（宽屏在右，窄于 900px 在下）：完整提示词、全部参数、生成时间、耗时、文件名与大小；按钮「回填参数」（有 fillPlan 时；调用 `ctx.applyFill(plan)` 并关闭弹层）、「在访达中显示」（有文件时）、「关闭」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-43 ←/→ 在当前筛选+排序顺序里切上一件/下一件（到头不循环，按钮置灰）；Esc 关闭；空格仅在焦点不在媒体控件、按钮或输入框上时关闭（否则交给该控件，如视频暂停）。切换或关闭时停止并释放上一件媒体（`pause()` + 移除 `src`）。弹层打开期间遮罩挡住页面，素材库不会被刷新，弹层按打开时的条目快照翻页。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-44 动效：遮罩淡入、面板淡入+轻微缩放（180ms 左右）；全局 `prefers-reduced-motion` 规则生效。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-45 离开素材库页（`main.js` 的 `showTab` 切到别的页）时调用 `panes.library.onHide()`：停掉试听（L-24）与悬停播放（L-22）。现状顶部播放区切页后仍在后台出声，本条一并修掉。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-50 `node --test`：纯函数（合并含 B-43、missing、筛选、排序缺值在后）；假 DOM：视图切换与记忆（含存储抛错）、单击选中/双击打开、键盘移动、预览 ←/→ 与到头置灰、回填调用 applyFill 并关闭、reveal 失败文案、试听按钮不冒泡。现有 `library_pane.test.js` 中依赖顶部播放区的断言改为断言预览弹层。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-51 e2e（Playwright）：三视图渲染、预览打开/切换/关闭、键盘导航、回填回到对应页面（沿用 `test_library_panel.py` 的回填用例）、切页停声（L-45）；在 1280 与 900 宽截图目检，截图目录由 `$LMD_LIBRARY_SHOTS` 指定。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-52 迁移依赖 `[data-lib-player]` 的现有 e2e：`test_image_sessions.py`（约 329–355 行，含「预览与刷新按钮的间距」断言，改为断言弹层里图片的尺寸）、`test_image_flow.py`（约 466 行）；（`test_library_panel.py::test_audio_player_matches_the_dark_palette` 只查音乐会话卡片的播放器，不受影响）；`test_outputs_range.py` 只等 `[data-lib-list] li`，改为等 `[data-lib-item]`。 — 无裁决（面 F9 已盘问但无裁决引用它）
- L-53 WebKit 核对：应用外壳是 WKWebView，而 e2e 默认跑 Chromium。视频首帧缩略图（`#t=0.1` + `preload="metadata"`）与悬停播放须另用 Playwright WebKit（本机已装 webkit-2272）跑一条用例确认能出首帧；不行则退回「视频图标 + 时长」占位并在本文件记下。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-01 合法画幅：宽、高都是整数且为 32 的倍数；每边 256–1344；`宽×高 ≤ 768×1344`。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-02 违规文案（按此顺序取第一条）：「宽和高须为整数」「宽和高须为 32 的倍数」「每边须在 256–1344 之间」「面积不能超过 768×1344（约 103 万像素）」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-03 后端 `start_video_job` 在任何会话写入之前做同样校验，违规返回 400 `invalid_params`，文案「画幅须为 32 的倍数，每边 256–1344，面积不超过 768×1344」；拒绝时会话不留尝试记录（B-33）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-04 镜像测试：一个 Python 测试读出 JS 与 Python 两边的常量（32、256、1344、768×1344）和内存公式参数（27.0、1.4、草稿体积 512×288×49、预算 40），任何一边改了另一边不跟就失败。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-10 方向：`landscape` 横屏 / `portrait` 竖屏 / `square` 方形。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-11 档位（名称 草稿 / 标准 / 清晰）：横屏 512×288、768×448、1024×576；竖屏为横屏宽高对调；方形 384×384、576×576、768×768。全部满足 Z-01。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-12 方向控件在输入区主行，是分段控件（复用 `widgets/segment_switch.js`，`ariaLabel`「画幅方向」）；档位下拉在「高级参数」的「画幅」处，选项随方向变，末项「自定义…」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-13 切换方向时保持同一档（草稿→草稿……）；当前是自定义时切方向，取新方向的「标准」档。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-14 选「自定义…」出现宽、高两个数字输入，初值为切换前选中的那一档；输入框失焦时取最近的 32 的倍数（`snap32`）；提交前不合规按 Z-02 写在高级参数错误行并拦下（沿用现有 `ParamsError({advanced:true})`）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-15 默认：横屏 · 草稿（与现状 512×288 一致）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-20 形状判定：`0.9 ≤ 宽/高 ≤ 1.1` 为方形；否则宽>高为横屏、高>宽为竖屏。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-21 「图生」模式下首帧来源变化（上传选中、本页「从图片会话选…」、图片页「用这张生成视频」）且读到首帧尺寸后：若当前不是自定义且首帧方向 ≠ 当前方向，就切到首帧方向、保持档位（Z-13），在首帧说明旁提示「已按首帧切到<方向>」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-22 首帧尺寸来源：上传文件在浏览器里解码读 `naturalWidth/Height`；图片会话引用读该尝试的 `params.width/height`（`panes/video.js` 的 `lookupImage` 现只返回 `{output,title,index}`，需补上 `width,height`）；读不到（解码失败、参数缺失）就不跟随、不提示。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-23 跟随后用户手动改方向：照用户的，提示消失，同一个首帧不再自动切回。换了新的首帧重新判定。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-24 当前是自定义尺寸时不自动改，形状不一致时提示「首帧是<方向>，画幅是<方向>，画面会被拉伸变形」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-25 续写的首帧（上一段末帧）不触发跟随（见 Z-30）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-26 「在这段基础上改」「换个版本」与素材库「回填参数」恢复的是当时保存的尺寸（Z-31），带回的首帧不触发跟随，也不出提示。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-30 「接着往下生」时方向控件、档位下拉、自定义输入全部禁用，`title`「接着往下生沿用上一段的画幅」；点提示条 × 取消续写后恢复可用。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-31 续写、「换个版本」「在这张基础上改」、素材库「回填参数」带入的尺寸，用 `matchSize(width, height)` 找回方向与档位；不在任何档位里则选「自定义…」并填入宽高。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-32 卡片、素材库里显示的尺寸照旧是 `宽×高`，竖屏与自定义同样显示。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-40 耗时：`宽×高 ≥ 1024×576` 且帧数 ≥ 243（约 10 秒档）时显示「大画幅加 10 秒以上会非常慢：实测 1024×576 曾 20 分钟只走完 2/16 步，可能要一小时以上。建议先用草稿画幅试效果。」 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-41 H3 预算：`估算 = 27.0 + 1.4 × max(宽×高×帧数 ÷ (512×288×49) − 1, 0)` GiB，与 `memory_estimate.py` 同源；超过 40 时显示「按实测外推约需 N GiB，超过视频生成的 40 GiB 上限，可能中途失败。」（N 取整）。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-42 两条可同时出现，显示在现有耗时提醒位置（`[data-video-cost-note]`）；参数一变就更新。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-43 `pure/video_cost.js` 并入 `pure/video_size.js` 后删除。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-50 JS 单测：Z-01 边界（255/256、1344/1376、面积恰为上限与超 1 格）、Z-02 文案顺序、`snap32`、Z-11 全部档位合法、Z-13、Z-20 边界（0.9、1.1）、Z-21/23/24、Z-30、Z-31（档位内、竖屏、自定义）、Z-40/41 文案与阈值。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-51 Python：Z-03 各类违规 400 且会话无新尝试；合法竖屏与自定义能启动；Z-04 镜像测试。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-52 e2e：竖屏 · 标准与自定义 448×800 各生成一次，请求体与卡片尺寸正确；上传方图做首帧后方向切到方形并出提示；续写时画幅控件禁用；截图目检（1280 与 900 宽），截图目录 `$LMD_VIDEO_SIZE_SHOTS`。 — 无裁决（面 F6 已盘问但无裁决引用它）
- Z-53 实测（2026-10-07）：512×512 正圆首帧生成 512×288，第一帧圆被压成椭圆、8 条横线全在、输出 512×288——H3 **拉伸**首帧到画布，不裁切。Z-24 措辞据此为「拉伸变形」。 — 无裁决（面 F6 已盘问但无裁决引用它）
- R-e2e-01 测试态服务可启动：注入假后端、临时数据根与临时模型根，浏览器可访问， 全流程确定性可重复；断言全程未触碰真实权重目录与真实 outputs。 — 无裁决（未落任何面）
- R-e2e-02 首运流程：无配置时呈现首运界面；选定 models 目录后进入主界面；配置确已落盘。 — 无裁决（未落任何面）
- R-e2e-03 聊天流程：选模型 → 加载 → 发消息 → 看到**逐步增长**的流式正文 → 思考块可展开 → 回复入库。 必须断言「增量确实是分批到达的」，而不是一次性出现（否则流式没被证明）。 — 无裁决（未落任何面）
- R-e2e-04 多会话：新建 / 切换 / 重命名 / 删除；**刷新页面后仍在**。 — 无裁决（未落任何面）
- R-e2e-05 资源面板：齐 / 一半 N% / 没下 三态正确渲染且百分比正确； 下载 → 进度推进 → 取消 → 续传 的控件流转；删除需二次确认；剩余空间可见。 — 无裁决（未落任何面）
- R-e2e-06 视频流程：填参数 → 启动 → 进度可见 → 完成后播放器出现且 `src` 指向新成品。 — 无裁决（未落任何面）
- R-e2e-07 音乐流程：同上。 — 无裁决（未落任何面）
- R-e2e-08 互斥在 UI 上可见：媒体运行中，加载按钮与另一媒体按钮均被禁用，状态条给出拒绝原因； 媒体结束后恢复可用。 — 无裁决（未落任何面）
- R-e2e-09 素材库：点历史项把当时参数回填进对应表单（逐字段断言）；点成品可播放。 — 无裁决（未落任何面）
- R-e2e-10 状态条显示**真实内存数值**并随状态变化；断言页面上不存在写死的 `128` 内存字面量。 — 无裁决（未落任何面）
- R-e2e-11 设置面板显示对外 API 的两条 base URL（OpenAI 与 Anthropic），并明示当前无鉴权。 — 无裁决（未落任何面）
- R-e2e-12 **零直连断言**：通过浏览器网络拦截，断言整场 e2e 期间前端**没有向 `127.0.0.1:8767` 发出任何请求**。这条以行为方式证明 census A17，比 grep 更强。 — 无裁决（未落任何面）
- D-44a 以图生图（2026-09-24 修订，用户确认）：被回填的尝试有图（`status == done`、有 `output` 且文件还在）时，提示条改为「以第 N 次为底稿」；提示条仍在时点「生成图片」，请求带 `base: {attempt_id, strength: 0.6}`，后端以那张图为底稿重绘（保留构图、重画细节），宽高取底稿的宽高。没图的尝试（失败、取消、文件不在）仍按 D-40–D-44 只回填、按文生图生成。提示条隐藏（改了种子或点 ×）后同样退回文生图。 — 无裁决（未落任何面）
- D-47a 以图生图（2026-09-24 修订）：该尝试有图时，提交带 `base: {attempt_id, strength: 0.35}`，以这张为底稿重绘（保留主体与色调、换构图）。没图的尝试「换个构图」不可用，按钮下方原因行为「这一次没有图片，不能以它为底稿换个构图」。 — 无裁决（未落任何面）
- D-47b 以图生图的强度只允许 0.6 与 0.35 两档（mflux 约定：强度越高越接近底稿）；后端校验底稿属于同一会话、状态为 done 且文件存在，否则分别返回 400 `invalid_params`、404 `base_not_found`、404 `base_missing`。尝试记录 `base: {attempt_id, strength}`（文生图为 `null`），卡片标题行显示「基于第 N 次」（底稿不在列表中则不显示）。 — 无裁决（未落任何面）
- D-50a 例外（用户 2026-09-24 决定）：「素材库」页不属于图片主流程，其条目元数据可以显示「种子 N」；本需求只改图片页（BR-1），素材库文案保持不变。D-50 与视觉标准的「种子」全局规则只适用于图片页。 — 无裁决（未落任何面）
- BR-1 只改图片页；视频、音乐页不动 — 无裁决（未落任何面）
- BR-2 会话持久化在本机，重启 app 后仍在，每个会话一个 JSON 文件，沿用聊天会话的存储方式 — 无裁决（未落任何面）
- BR-3 会话内按时间顺序列出每次尝试：图片、提示词、宽高、步数、种子；失败或取消的尝试也列出并写明原因 — 无裁决（未落任何面）
- BR-4 会话需手动新建（像聊天的「新建」）；未新建时生成接在当前会话；会话标题默认取第一次生成的提示词 — 无裁决（未落任何面）
- BR-5 会话可切换、重命名、删除；删除会话只删分组，图片文件保留并仍出现在素材库 — 无裁决（未落任何面）
- BR-6 打开任意一次尝试后给两个动作：「在这张基础上改」把提示词回填到输入框并沿用该张种子，用户改完再生成；「换个构图」提示词不变、换一个新随机种子直接再生成 — 无裁决（未落任何面）
- BR-7 界面主流程不出现「种子」一词；种子与宽高、步数一起收进「高级参数」 — 无裁决（未落任何面）
- BR-8 新尝试总是追加到当前会话末尾，不覆盖旧图 — 无裁决（未落任何面）
- BR-9 局部重绘/图生图不在本次范围 — 无裁决（未落任何面）
- AC-1 连续三轮「生成 → 在这张基础上改 → 再生成」后，三张图及各自参数都在同一个会话里按顺序显示 — 无裁决（未落任何面）
- AC-2 「在这张基础上改」生成的新图与原图种子相同；「换个构图」生成的新图提示词相同而种子不同 — 无裁决（未落任何面）
- AC-3 重启 app 后会话列表、每个会话的尝试和图片都还在 — 无裁决（未落任何面）
- AC-4 切到另一个会话再切回，内容不变；新建会话后生成的图只进新会话 — 无裁决（未落任何面）
- AC-5 删除会话后会话从列表消失，其中的图片仍能在素材库打开 — 无裁决（未落任何面）
- AC-6 失败或取消的尝试在会话里可见并显示原因，不会留下一张空白图 — 无裁决（未落任何面）
- AC-7 在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误 — 无裁决（未落任何面）
- B-38a 模型产出后、开始拼接前，先调用 `store.record_output(session_id, attempt_id, output)` 把单段文件名写进仍为 running 的尝试。之后任何中断都不丢这一段： — 无裁决（未落任何面）
- B-38b 重活许可在**模型子进程退出时**释放（拼接只用 ffmpeg，不该继续占着 arbiter 的内存额度挡住聊天加载）；`_finalize` 对已释放的许可不再释放（只释放一次）。compose 作业没有许可（B-45）。 — 无裁决（未落任何面）

## 逐面完成度

### 本机对话（加载/卸载、流式、思考、会话、上下文压缩、内存警告）（F3）— 3 问中 0 问实证通过 · 操作面 11 个，裁决触及 4 个，未触及：S20 Unload chat model or cancel a load、S21 LLM status、S22 Non-streaming chat、S43 List chat sessions、S46 Delete chat session、S66 Background: LLM load thread + mlx_lm server child on port 8767、D2 [dead contract] POST /api/llm/chat (non-streaming): no caller in UI or shell, and the gateway uses DeskGatewayBackend directly (tests only)
- **缺口** [G4] [F3] 调用 S44「Create chat session」（入口 POST /api/sessions (desk/library/http.py:196)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — POST /api/sessions 200 新建会话并落盘、未知键 400、空 title 补「新会话」；但 title:123、model:["a"] 照收 200 并原样写入会话文件，无类型校验（证据：evidence/sw-S44/）
- **缺口** [G5] [F3] 调用 S45「Update chat session (messages/title/skills; keepalive)」（入口 PATCH /api/sessions/{id} (desk/library/http.py:197)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — PATCH /api/sessions/{id} 合并更新并落盘、未知键/非列表 400、keepalive 关页保存 200 生效；但 title:123、messages:[1,null,"s"]、skills:[42] 均 200 照写入会话文件，列表接口原样回吐（证据：evidence/sw-S45/）
- **缺口** [G9] [F3] LocalModelDesk 的聊天页在会话长到需要自动压缩上下文时，若这次压缩请求没能成功（例如压缩进行中聊天模型被卸载、或上游请求中断/超时），用户在界面上看到什么（有无进行中提示、有无失败提示及其文字）、这一轮用户的提问最终得到什么、会话里原来的消息与有无摘要块各是什么状态、下一次发送时又发生什么？请分别记录压缩开始前、压缩进行中、压缩失败后、再次发送后的界面与 GET /api/sessions/{id} 读回。 — 218k token 一轮后自动压缩（prompt 253571 token）开始：进行中提示「正在压缩较早的对话…」插在消息列表顶部，y=-140958 不在视口内，截图 02 看不到，仅发送键变灰；压缩中经界面卸载模型后压缩 SSE 以 evicted「内存让给了媒体作业，回答被中断」结束（当时无媒体作业）——横幅消失、发送键恢复，无任何错误/提示/控制台告警，会话无摘要块、无写入；下次发送带全量未压缩历史（372,833 字），回答后再次自动压缩，第二次约 32 分钟成功并写入 summary（replaced_through 13）（证据：evidence/p5-compact/）

### 视频会话（文/图/参考/配乐生成、画幅、首帧跟随、续写、拼接、配乐）（F6）— 0 问中 0 问实证通过 · 操作面 4 个，裁决触及 1 个，未触及：S29 Compose segments (video concat / music crossfade)、S30 Add a soundtrack to a video、S74 Media ffmpeg commands (last frame / concat / crossfade / soundtrack / audio clip)

### 媒体会话基座（上传输入、作业状态/日志/取消、会话增删改、中断恢复、提示词助手）（F8）— 1 问中 0 问实证通过 · 操作面 11 个，裁决触及 6 个，未触及：S25 Upload media input (base64; 45MB connection cap at app.py:73, 32MB in copy)、S31 Cancel media job、S49 Read media session、S50 Rename media session、S69 Startup: settle media attempts left running as interrupted
- **缺口** [G10] [F8] LocalModelDesk 的提示词助手（图片/视频/音乐页上的「看手气」「优化提示词」等，经 POST /api/llm/prompt-assist 调用已加载的聊天模型）在一次请求耗时超过界面自身的等待上限时，界面上显示什么（文字、按钮状态、原提示词框内容）？此时服务端与聊天模型是否仍在处理那次请求（看服务端/上游 mlx_lm 日志、/api/llm/status、/api/state 与模型进程 CPU）？在它被放弃之后、上游仍在忙时，立即再用一次提示词助手、以及在聊天页发一条消息，各自发生什么、各要等多久？ — 上游被 80k token 预填充占住时，「优化提示词」184.8 s 后界面显示「请求超时（180 秒无响应）」、按钮恢复、提示词框原样；同刻浏览器连接已断，但 desk→8767 的该请求仍在，服务端直到点击后 300 s 才记 502，界面无对应显示。放弃后立即重试同样 185 s 超时、服务端 300 s 才 502（被放弃的请求叠加占用上游）；同期聊天页一条「1+1」从发出到出正文约 5 分 37 秒。作用域：超时由上游被其他长请求占住造成，非 assist 自身慢（证据：evidence/p5-assist/）

### 素材库与历史（列表、预览、回填、Range 播放、访达定位）（F9）— 1 问中 0 问实证通过 · 操作面 5 个，裁决触及 1 个，未触及：S38 Reveal outputs folder in Finder、S39 Reveal one output in Finder、S40 Serve output file、S41 List outputs
- **缺口** [G2] [F9] 调用 S42「Generation history (?limit)」（入口 GET /api/history (desk/library/http.py:194)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — GET /api/history 200：67 条与 history.jsonl 逆序逐条一致，limit 0/1/3/99999 正确、负数/非数字 400；但 limit=²（上标数字）通过校验后 int() 抛错 → 500 internal（http.py:102）（证据：evidence/sw-S42/）

### 技能（列表、重扫、GitHub 预览安装、注入与占用）（F10）— 1 问中 0 问实证通过 · 操作面 9 个，裁决触及 2 个，未触及：S34 Rescan skills、S36 Confirm skill install (lands on disk, stays disabled)、S37 Discard staged skill、S70 Startup: sweep stale skill staging、S75 Bundled skills、S76 Skills store scan (bundled + user roots, broken entries)、S77 Skill GitHub fetch / stage / land / discard
- **缺口** [G6] [F10] 调用 S35「Preview a GitHub skill install (staging)」（入口 POST /api/skills/preview (desk/skills/routes.py:22)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — POST /api/skills/preview 对两个真实公开仓库（顶层有 SKILL.md）均 409「取不到仓库内容：HTTP Error 404」：服务按模板 codeload.github.com/{o}/{r}/tar/refs/heads/{branch} 取包（service.py:17），本机复现该 URL 对 main/master 都 404，而 /tar.gz/refs/heads/main 200——从 GitHub 安装技能整条路径取不到任何仓库，预览/安装无从发生（证据：evidence/sw-S35/）

### 对外网关（OpenAI/Anthropic 方言、503、配置）（F11）— 1 问中 0 问实证通过 · 操作面 7 个，裁决触及 1 个，未触及：S55 Read gateway config、S56 Apply gateway config、S58 Gateway: model list (default 0.0.0.0:8770, enabled by default)、S59 Gateway: OpenAI dialect chat、S60 Gateway: Anthropic dialect chat、S65 Background: gateway HTTP thread
- **缺口** [G3] [F11] 调用 S61「Gateway: wrong method / unknown path rejections」（入口 desk/gateway/http_server.py:110-126 (405/404)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — 405/404 按方言信封返回；但①拒绝时不读掉请求体，同一 keep-alive 连接上的下一请求被解析成 '{"a":1}GET' → 501 并断连（直连 8770 复现，curl 复用连接复现）；②任何带查询串的路径 404，含 Anthropic SDK 常用的 /v1/messages?beta=true；③PUT/DELETE/HEAD/OPTIONS 回 BaseHTTP 默认 501 HTML 而非方言错误信封（证据：evidence/sw-S61/）

### macOS 外壳（启动、菜单栏、关窗、退出清理、错误页、首运弹窗）（F12）— 1 问中 0 问实证通过 · 操作面 11 个，裁决触及 1 个，未触及：S62 Service entry (process group, port LMD_SHELL_PORT, LMD_PARENT_PID)、S63 Background: parent-process watchdog (3s)、S64 Background: SIGTERM/SIGINT graceful shutdown、S79 Shell: app launch, spawn embedded server, port guard、S81 Shell: terminate embedded server (process group reap)、S82 Shell: ⌘, settings shortcut monitor、S83 Shell: reopen / close-hides-window / no terminate on last window、S84 Shell: WKWebView file open panel、S85 Shell: error page retry message (shellRetry)、S86 Shell: VisualProbe loopback HTTP (LMD_PROBE_PORT only)
- **缺口** [G8] [F12] LocalModelDesk 的 macOS 菜单栏状态项（屏幕右上角的状态图标/标题及点开后的菜单，其中有一行状态文字）在以下时刻分别显示什么：(a) 没有媒体作业时；(b) 在图片页生成一张图片的过程中；(c) 图片生成完成后。同时记录同一时刻 GET http://127.0.0.1:8766/api/state 的 holder/holders。 — (a) 菜单栏「状态：已加载 SuperQwen…」绿色；(b) 图片作业 job-9 期间 /api/state holder=image「图片生成中」、holders=[llm, image]，菜单栏描述与首个菜单项为「状态：状态不可读」（橙色），全程未出现图片相关文字；(c) 完成后恢复「已加载 SuperQwen…」。外壳只读 holder 不读 holders；状态变化传到菜单栏滞后 1.3–3.2s（证据：evidence/p4-menubar/）

### Web 外壳与通用（静态资源、未知路由、通用确认框/错误块）（F13）— 1 问中 0 问实证通过 · 操作面 3 个，裁决触及 1 个，未触及：S1 Static UI shell (index.html)、S57 Unknown route / bad Content-Length envelope
- **缺口** [G1] [F13] 调用 S2「Static assets」（入口 GET /static/* (desk/ui.py:25)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — 正常资源 200 且与磁盘一致、../ 与编码穿越均 404；但 GET /static/js/api.js%00.png 让处理器抛 ValueError（ui.py:32），连接零字节断开（curl 52），无 4xx 响应；HEAD 501；无缓存头（证据：evidence/sw-S2/）

### [横切] 同一时刻只干一件重活：对话/图/视频/音乐/下载/网关之间的互斥与让出（X1）— 1 问中 0 问实证通过 · 操作面 12 个，裁决触及 4 个，未触及：S15 Start or resume a download、S22 Non-streaming chat、S28 Start image job (txt2img; base=img2img refine/recompose)、S29 Compose segments (video concat / music crossfade)、S30 Add a soundtrack to a video、S59 Gateway: OpenAI dialect chat、S60 Gateway: Anthropic dialect chat、S71 Arbiter: heavy-work admission / LLM eviction / port reaping
- **缺口** [G7] [X1] 在 LocalModelDesk 的视频页，对一段已完成的视频点「接着往下生」生成续写段：续写段的模型生成结束之后、该次尝试最终标为完成之前，台面会把多段拼成「成片」。在这段拼接时间窗里（以及它前后各几秒），Web 状态条的「内存里 / 媒体 / 下一件重活」三段文字、GET /api/state 的 holder/holders/media_busy/can_start、GET /api/media/job 的作业状态各是什么？在这段窗口里，若尝试再启动一件重活（例如在音乐页点生成一首短歌，或在视频页的另一个会话再生成一段），台面接受还是拒绝、给出什么文字？请按时间轴（精确到秒）记录。 — 拼接窗口实测 ≤0.33s / ≤0.42s（2–3 段各约 2 秒）：窗口内 /api/state holders 只剩 llm、media_busy=false、can_start.media ok:true，而 /api/media/job 仍 running 且日志含 [join]；此时 POST /api/media/music 与另一会话 /api/media/video 均 409 media_busy。Web 状态条 2s 刷新未落入窗口，界面全程显示生成中/不可直到完成（证据：evidence/p4-join/）

## 旅程完成度

### J3 想出短视频的人 · 此刻有聊天模型驻留在内存；提示词约 80 字；画幅取横屏标准档 · 不手动卸载任何东西，生成一段带环境声的短视频，并在台面里直接播放 — 缺口（medium，误导）
走了 10 步，预算内未到进展（证据：evidence/jr-J3/） · 实测处境：聊天模型：SuperQwen3.8 27B 越狱 4bit（15.0 GiB，下拉第 2 项），旅程前经界面加载，加载后已用 68/128 GiB；提示词 81 个字符（Python len），含「环境声：潺潺流水声、远处的鸟鸣、船桨入水的哗啦声，偶尔传来几声犬吠」；画幅方向「横屏」：表单出现时已选中，没有点击；画幅档位：从「草稿 512×288」改选「标准 768×448」；视频时长「约 2 秒（快速）」，没有改动；步数 16；种子留空；生成方式「文生视频」；视频页原有 2 个会话；本趟新建 1 个会话，结束时已删除；本趟第 1 次视频生成，生成用时约 3 分 50 秒；视口 1280×800，DPR 1
- 1 done 点顶栏「视频」 → URL 变为 #tab=video；会话栏有 2 条既有会话，主区显示第一条的 2 次生成；banner「内存里：SuperQwen3.8 27B 越狱 4bit」
- 2 done 点会话栏「新会话」 → 列表顶部出现「新会话 0 次生成 · 18:33」，主区显示「还没有视频」；画幅方向「横屏」已选中
- 3 done 在「视频提示词」框填 81 字提示词 → 文本框显示完整提示词
- 4 done 点「高级参数」展开 → 显示画幅「草稿 512×288」、视频时长「约 2 秒（快速）」、步数 16、种子空
- 5 done 画幅下拉选「标准 768×448」 → 下拉显示标准 768×448 为选中项
- 6 done 点「生成视频」 → 没有弹窗；卡片「第 1 次 · 生成中…（已用 2秒）」「文生 · 768×448 · 约 2 秒 · 16 步」，带进度条、取消、日志；banner「内存里：视频生成中」「不可：媒体作业进行中」；生成按钮变为 disabled
- 7 done 等待生成完成（分段截图） → 约 35 秒时显示已用 44 秒；2 分 24 秒时 banner「已用 87 / 总 128 GiB」；约 3 分 50 秒后卡片变为「第 1 次 · 18:33」，出现「在这段基础上改 / 换个版本 / 接着往下生 / 配乐…」；banner 回到「内存里：SuperQwen3.8 27B 越狱 4bit」「媒体：空闲」
- 8 done 在视频时间线区内滚动到视频 → 露出视频画面（水乡、石桥、小船），控制条被下方表单挡住
- 9 done 继续滚动，让视频底部对齐时间线区底边 → 控制条可见：播放键、「0:00 / 0:02」、音量、全屏、更多
- 10 done 点视频播放键 → 0.8 秒后 paused=false、currentTime=0.69、muted=false、volume=1；之后 ended=true、currentTime=2.333、webkitAudioDecodedByteCount=59087

### J10 想用技能的人 · 一个公开 GitHub 上的 SKILL.md 仓库链接 · 从 GitHub 装一个技能，先看全文再确认，然后在一个聊天里启用它并看到它起作用 — 缺口（high，系统报错）
走了 15 步，卡在第 9 步：点「预览」 → 红字「取不下来：取不到仓库内容：HTTP Error 404: Not Found」；没有 SKILL.md 正文；POST /api/skills/preview 409（证据：evidence/jr-J10/） · 实测处境：全新 Chrome 隔离上下文 jr-J10，视口 1280x860，DPR 1；会话库起点 7 条，技能库起点 3 条（均 bundled）；已加载模型 SuperQwen3.8 27B 越狱 4bit；新建会话 1 个，发 0 条消息，结束时已删除；依次输入 3 个 URL：anthropics/skills 子目录 tree URL、anthropics/skills 仓库根、aiwithremy/claude-skills-llm-council 仓库根；每次点「预览」后等 4–6 秒；第三个仓库从 GitHub 搜索前 30 中根目录 SKILL.md 返回 200 的 7 个里挑选
- 1 done 点工作区导航「资源」 → 模型清单 9 张卡（齐/能跑/删除），没有技能相关入口
- 2 done 点顶栏「设置」 → 右侧设置面板：模型目录、对外 API；没有技能相关项
- 3 done 点「关闭设置」 → 设置面板关闭（快照在第 4 步之后才拍）
- 4 done 点工作区导航「聊天」 → 回到聊天页，URL #tab=chat
- 5 done 点「新会话」 → 会话栏顶部新增「新会话 20:40」，正文写「这是一个新会话。选好模型、点「加载」，然后在下面输入第一句。」
- 6 done 点模型栏右侧「指令」 → 模态框「指令」：重新扫描 / 从 GitHub 安装 / 关闭；列出 代码审查 300 字符、写得清楚些 561 字符、译成中文 546 字符
- 7 done 点「从 GitHub 安装」 → 模态框「从 GitHub 安装 skill」，说明「填仓库地址，先看完整篇 SKILL.md 再决定装不装。」，占位符 https://github.com/owner/repo，按钮 取消/预览
- 8 done 在输入框里填 https://github.com/anthropics/skills/tree/main/skills/brand-guidelines → 输入框显示 URL 末尾部分
- 9 stuck 点「预览」 → 红字「取不下来：取不到仓库内容：HTTP Error 404: Not Found」；没有 SKILL.md 正文；POST /api/skills/preview 409
- 10 done 把输入框改成 https://github.com/anthropics/skills → 输入框值已替换
- 11 stuck 点「预览」 → 同一红字「取不下来：取不到仓库内容：HTTP Error 404: Not Found」；POST 409
- 12 done 把输入框改成 https://github.com/aiwithremy/claude-skills-llm-council → 输入框只显示末尾「aude-skills-llm-council」
- 13 stuck 点「预览」 → 同一红字「取不下来：取不到仓库内容：HTTP Error 404: Not Found」；POST 409；同一时段本机 curl 该仓库的 raw SKILL.md 返回 200
- 14 done 点「取消」 → 安装框关闭，「指令」框仍然开着，仍是 3 条技能
- 15 done 点「指令」框的「关闭」 → 回到自建空会话的聊天页，模型仍显示「已加载：SuperQwen3.8 27B 越狱 4bit」

### J11 长对话的人 · 一个会话持续多轮直到超过上下文触发点（可用大段文本快速撑满） · 在超过预算后继续聊，压缩发生时看得到进行中提示，压缩后原文仍全部可见且还能继续得到回答 — 缺口（high，无反馈）
走了 15 步，卡在第 3 步：点「发送」（Playwright 共享标签页） → 出现用户气泡和「思考中…」，按钮变成「停止」；约 185 秒后标签页 URL 变成 http://127.0.0.1:8780/「首次运行」页（证据：evidence/jr-J11/） · 实测处境：从已有状态起步：库里原有 7 个会话，模型 SuperQwen3.8 27B 越狱 4bit 已加载；新建 1 个会话（结束时已删除）；第 1 轮粘贴 100042 字，第 2 轮 100073 字，第 3 轮 80076 字，三条累计 280191 字；追问 32 字；填充方式：脚本设置 textarea 的值并派发 input 事件（等同粘贴）；第 1 次尝试被共享标签页打断后，在 Chrome DevTools 独立上下文里从头重做；视口 1280x800，DPR 1；等待时间：轮1 数秒，轮2 约 624 秒，轮3 约 584 秒，追问约 330 秒后超时
- 1 done 点「新会话」 → 会话栏顶部出现「新会话 19:58」，主区显示「这是一个新会话…」
- 2 done 在输入框粘贴 100042 字（标记A1） → 输入框显示文本末尾「…【标记A1·第一段结束】读完后只回答一句…」
- 3 stuck 点「发送」（Playwright 共享标签页） → 出现用户气泡和「思考中…」，按钮变成「停止」；约 185 秒后标签页 URL 变成 http://127.0.0.1:8780/「首次运行」页
- 4 done 在 Chrome DevTools 独立上下文新开 http://127.0.0.1:8766/ → 会话栏顶部是「新会话 19:58」，主区「这是一个新会话…」，第 3 步发出的消息不在
- 5 done 点会话栏「新会话 19:58」 → 主区仍是「这是一个新会话。选好模型、点「加载」，然后在下面输入第一句。」
- 6 done 在输入框粘贴 100042 字（标记A1） → textarea 值的长度为 100042
- 7 done 点「发送」 → 数秒后回答「资料一已收到，开头的标记名称是【标记A1·第一段开始】。」；会话改名为「【标记A1·第一段… superqwen · 20:03」；顶栏变成「对话额度 18497 字（已实测）」
- 8 done 在输入框粘贴 100073 字（标记B2） → 输入框显示「【标记B2·第二段开始】这是第二份资料…」
- 9 done 点「发送」 → 约 624 秒后回答说出 A1、B2 两个标记；顶栏回到 262144 字
- 10 done 在输入框粘贴 80076 字（标记C3） → 输入框里是第三段文本；顶栏仍是「对话额度 262144 字」
- 11 done 点「发送」 → 约 584 秒后回答依次说出 A1、B2、C3 三个标记；累计 280191 字；没有出现关于额度的提示
- 12 done 在输入框填入追问「短问题：资料一里“第1节”讲的是哪三个字的故事？只回答这三个字。」 → 输入框显示追问文字，「发送」按钮灰显
- 13 stuck 点「发送」 → 点击超时，元素没有变成可交互；按钮 disabled=true，60 秒内每 10 秒复查都还是 disabled
- 14 stuck 在输入框键入一个空格 → 「发送」仍是 disabled=true
- 15 stuck 按 ⌘Enter → 消息发出，出现「思考中…」，按钮变成「停止」；约 330 秒后显示「回答没有生成完：上游流中断: timed out」和「重试」按钮，「发送」恢复可用

## 缺口清单（按严重度）
- **high** **缺口** [G6] [F10] 调用 S35「Preview a GitHub skill install (staging)」（入口 POST /api/skills/preview (desk/skills/routes.py:22)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — POST /api/skills/preview 对两个真实公开仓库（顶层有 SKILL.md）均 409「取不到仓库内容：HTTP Error 404」：服务按模板 codeload.github.com/{o}/{r}/tar/refs/heads/{branch} 取包（service.py:17），本机复现该 URL 对 main/master 都 404，而 /tar.gz/refs/heads/main 200——从 GitHub 安装技能整条路径取不到任何仓库，预览/安装无从发生（证据：evidence/sw-S35/）
- **high** **缺口** [J11] [F3] J11 走得通吗？ — 盘问官注：第 3–5 步被盘问官并行派发的 J7 实测官（共用 Playwright 标签页导航到 8780）打断，属盘问官失误，不作裁决依据；裁决只依据第 6–15 步（Chrome DevTools 独立上下文）。三轮大段文本累计 280191 字超过顶栏额度 262144 字：第 3 轮仍得到回答，全程无压缩进行中提示、无摘要块；随后追问时「发送」灰显无原因（60s+），⌘Enter 发出后约 330s 报「上游流中断: timed out」；原消息仍全部可见（证据：evidence/jr-J11/）
- **high** **缺口** [J10] [F10] J10 走得通吗？ — 技能入口在聊天页「指令」→「从 GitHub 安装」；对 3 个真实公开仓库 URL（含根目录 SKILL.md 的仓库，同时段 curl raw SKILL.md 200）点预览均 409「取不下来：取不到仓库内容：HTTP Error 404: Not Found」，看不到全文、无确认安装按钮，15 步用尽；与扫全 sw-S35 同一缺陷（取包 URL /tar/ 模板）（证据：evidence/jr-J10/）
- **medium** **缺口** [G3] [F11] 调用 S61「Gateway: wrong method / unknown path rejections」（入口 desk/gateway/http_server.py:110-126 (405/404)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — 405/404 按方言信封返回；但①拒绝时不读掉请求体，同一 keep-alive 连接上的下一请求被解析成 '{"a":1}GET' → 501 并断连（直连 8770 复现，curl 复用连接复现）；②任何带查询串的路径 404，含 Anthropic SDK 常用的 /v1/messages?beta=true；③PUT/DELETE/HEAD/OPTIONS 回 BaseHTTP 默认 501 HTML 而非方言错误信封（证据：evidence/sw-S61/）
- **medium** **缺口** [J3] [F6] J3 走得通吗？ — 聊天模型 SuperQwen 27B 驻留下，未卸载即生成横屏标准 768×448 视频，约 3 分 50 秒完成，台面内可播（aac 双声道，mean -44.4 dB）。生成全程聊天子进程 pid 71294 存活，但状态条只显示「内存里：视频生成中」，既不显示聊天模型被让出也不显示并存（done_looks_like 第 3 条未命中）（证据：evidence/jr-J3/）
- **medium** **缺口** [G8] [F12] LocalModelDesk 的 macOS 菜单栏状态项（屏幕右上角的状态图标/标题及点开后的菜单，其中有一行状态文字）在以下时刻分别显示什么：(a) 没有媒体作业时；(b) 在图片页生成一张图片的过程中；(c) 图片生成完成后。同时记录同一时刻 GET http://127.0.0.1:8766/api/state 的 holder/holders。 — (a) 菜单栏「状态：已加载 SuperQwen…」绿色；(b) 图片作业 job-9 期间 /api/state holder=image「图片生成中」、holders=[llm, image]，菜单栏描述与首个菜单项为「状态：状态不可读」（橙色），全程未出现图片相关文字；(c) 完成后恢复「已加载 SuperQwen…」。外壳只读 holder 不读 holders；状态变化传到菜单栏滞后 1.3–3.2s（证据：evidence/p4-menubar/）
- **medium** **缺口** [G9] [F3] LocalModelDesk 的聊天页在会话长到需要自动压缩上下文时，若这次压缩请求没能成功（例如压缩进行中聊天模型被卸载、或上游请求中断/超时），用户在界面上看到什么（有无进行中提示、有无失败提示及其文字）、这一轮用户的提问最终得到什么、会话里原来的消息与有无摘要块各是什么状态、下一次发送时又发生什么？请分别记录压缩开始前、压缩进行中、压缩失败后、再次发送后的界面与 GET /api/sessions/{id} 读回。 — 218k token 一轮后自动压缩（prompt 253571 token）开始：进行中提示「正在压缩较早的对话…」插在消息列表顶部，y=-140958 不在视口内，截图 02 看不到，仅发送键变灰；压缩中经界面卸载模型后压缩 SSE 以 evicted「内存让给了媒体作业，回答被中断」结束（当时无媒体作业）——横幅消失、发送键恢复，无任何错误/提示/控制台告警，会话无摘要块、无写入；下次发送带全量未压缩历史（372,833 字），回答后再次自动压缩，第二次约 32 分钟成功并写入 summary（replaced_through 13）（证据：evidence/p5-compact/）
- **medium** **缺口** [G10] [F8] LocalModelDesk 的提示词助手（图片/视频/音乐页上的「看手气」「优化提示词」等，经 POST /api/llm/prompt-assist 调用已加载的聊天模型）在一次请求耗时超过界面自身的等待上限时，界面上显示什么（文字、按钮状态、原提示词框内容）？此时服务端与聊天模型是否仍在处理那次请求（看服务端/上游 mlx_lm 日志、/api/llm/status、/api/state 与模型进程 CPU）？在它被放弃之后、上游仍在忙时，立即再用一次提示词助手、以及在聊天页发一条消息，各自发生什么、各要等多久？ — 上游被 80k token 预填充占住时，「优化提示词」184.8 s 后界面显示「请求超时（180 秒无响应）」、按钮恢复、提示词框原样；同刻浏览器连接已断，但 desk→8767 的该请求仍在，服务端直到点击后 300 s 才记 502，界面无对应显示。放弃后立即重试同样 185 s 超时、服务端 300 s 才 502（被放弃的请求叠加占用上游）；同期聊天页一条「1+1」从发出到出正文约 5 分 37 秒。作用域：超时由上游被其他长请求占住造成，非 assist 自身慢（证据：evidence/p5-assist/）
- **low** **缺口** [G1] [F13] 调用 S2「Static assets」（入口 GET /static/* (desk/ui.py:25)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — 正常资源 200 且与磁盘一致、../ 与编码穿越均 404；但 GET /static/js/api.js%00.png 让处理器抛 ValueError（ui.py:32），连接零字节断开（curl 52），无 4xx 响应；HEAD 501；无缓存头（证据：evidence/sw-S2/）
- **low** **缺口** [G2] [F9] 调用 S42「Generation history (?limit)」（入口 GET /api/history (desk/library/http.py:194)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — GET /api/history 200：67 条与 history.jsonl 逆序逐条一致，limit 0/1/3/99999 正确、负数/非数字 400；但 limit=²（上标数字）通过校验后 int() 抛错 → 500 internal（http.py:102）（证据：evidence/sw-S42/）
- **low** **缺口** [G4] [F3] 调用 S44「Create chat session」（入口 POST /api/sessions (desk/library/http.py:196)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — POST /api/sessions 200 新建会话并落盘、未知键 400、空 title 补「新会话」；但 title:123、model:["a"] 照收 200 并原样写入会话文件，无类型校验（证据：evidence/sw-S44/）
- **low** **缺口** [G5] [F3] 调用 S45「Update chat session (messages/title/skills; keepalive)」（入口 PATCH /api/sessions/{id} (desk/library/http.py:197)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。 — PATCH /api/sessions/{id} 合并更新并落盘、未知键/非列表 400、keepalive 关页保存 200 生效；但 title:123、messages:[1,null,"s"]、skills:[42] 均 200 照写入会话文件，列表接口原样回吐（证据：evidence/sw-S45/）
- **low** **缺口** [G7] [X1] 在 LocalModelDesk 的视频页，对一段已完成的视频点「接着往下生」生成续写段：续写段的模型生成结束之后、该次尝试最终标为完成之前，台面会把多段拼成「成片」。在这段拼接时间窗里（以及它前后各几秒），Web 状态条的「内存里 / 媒体 / 下一件重活」三段文字、GET /api/state 的 holder/holders/media_busy/can_start、GET /api/media/job 的作业状态各是什么？在这段窗口里，若尝试再启动一件重活（例如在音乐页点生成一首短歌，或在视频页的另一个会话再生成一段），台面接受还是拒绝、给出什么文字？请按时间轴（精确到秒）记录。 — 拼接窗口实测 ≤0.33s / ≤0.42s（2–3 段各约 2 秒）：窗口内 /api/state holders 只剩 llm、media_busy=false、can_start.media ok:true，而 /api/media/job 仍 running 且日志含 [join]；此时 POST /api/media/music 与另一会话 /api/media/video 均 409 media_busy。Web 状态条 2s 刷新未落入窗口，界面全程显示生成中/不可直到完成（证据：evidence/p4-join/）

## 无法自证清单（待人工验证，不计为完成也不计为失败）
（无）

## 未盘问声明（按风险排序）
- 旅程 想用本机模型聊天的人 · 台面刚打开，本机已下齐至少一个聊天模型，内存里此刻没有聊天模型（若有，先由前置条件卸掉），提问是一段约 200 字、需要推理的问题 · 把模型加载起来，发出问题，边生成边看到回复正文与可展开的思考过程，最终拿到完整回答（J1）— 未盘问，不计入任何完成度 · 风险 high：README 第一项核心能力
- 旅程 回头用户 · 前一天已有至少 3 个聊天会话、其中一个有 10 轮以上消息；退出 App 后重新打开 · 找到那个长会话，看到原来的全部消息，并在它里面接着问一句得到回答（J2）— 未盘问，不计入任何完成度 · 风险 high：「关掉再开最近的对话还在」
- 旅程 写歌的人 · 给出风格描述、约 8 行歌词、时长 30 秒 · 生成一首歌并在台面里直接听（J4）— 未盘问，不计入任何完成度 · 风险 high：核心能力
- 旅程 迭代的人 · 素材库里已有至少 5 件来自不同种类（图/视频/音乐）的旧成品 · 点开其中一件视频旧成品，把当时的提示词和参数填回生成表单，再做一版（J6）— 未盘问，不计入任何完成度 · 风险 high：「能从历史里点开旧成品并把参数填回去」
- [可选] 视觉验收（visual-acceptance：29 个 UI 面 × 宽度 900–显示器宽）（V1）— 未盘问，不计入任何完成度 · 风险 medium：用户未选：29 个 UI 面在 900px 到显示器宽的视觉质量未验收；功能面裁决不覆盖视觉/排版回归
- 旅程 出图的人 · 一句约 30 字的提示词 · 文生图得到一张图，然后在这张图基础上精修出新的一张（J5）— 未盘问，不计入任何完成度 · 风险 medium：图片会话 73 条需求
- 旅程 换了新机器的人 · 首次启动（无配置），本机某目录下已有现成模型树 · 选定或收编模型目录，进入台面，看清每个模型齐/半/没有（J7）— 未盘问，不计入任何完成度 · 风险 medium：首运只走一次但走不通就整台不可用；此旅程会改写用户真实配置，风险较高
- 旅程 做短片的人 · 会话里已有一段生成完成的视频，素材里已有一首生成完成的歌 · 在这段视频后面续写下一段，把两段拼成一片，再配上那首歌，得到一个可播放的成片（J8）— 未盘问，不计入任何完成度 · 风险 medium：视频会话的组合功能
- 旅程 用外部客户端的开发者 · 台面已加载聊天模型；用 OpenAI 兼容客户端（curl 即可） · 从设置里拿到 base URL，经网关发一次对话并得到回答（J9）— 未盘问，不计入任何完成度 · 风险 medium：对外 API
- 首运与配置（模型目录、收编、扫描、重置、致命屏）（F1）— 未盘问，不计入任何完成度 · 未评估风险
- 模型资源（目录、完整度、下载续传、删除、占盘）（F2）— 未盘问，不计入任何完成度 · 未评估风险
- 仲裁、预算与状态条（台面状态、内存快照、预算、互斥/并存判定）（F4）— 未盘问，不计入任何完成度 · 未评估风险
- 图片会话（文生图、精修/重构、会话卡片）（F5）— 未盘问，不计入任何完成度 · 未评估风险
- 音乐会话（生成、续写下一段、交叉淡化拼接）（F7）— 未盘问，不计入任何完成度 · 未评估风险
- 打包、签名、安装与卸载（F14）— 未盘问，不计入任何完成度 · 未评估风险
- [需求有、census 无] 内存压力兜底：预算失败学习与按代价处置（F15）— 未盘问，不计入任何完成度 · 未评估风险
- [横切] 数据生命周期：删会话/删模型/文件被挪走后，历史、素材库、引用、回填的去向（X2）— 未盘问，不计入任何完成度 · 未评估风险
- [横切] 并发与重入：连点生成、App 与浏览器同时开台面、刷新/切会话中途（X3）— 未盘问，不计入任何完成度 · 未评估风险
- [横切] 安全边界：本机 API 无鉴权、网关 0.0.0.0、outputs 路径逃逸、外部技能安装（X4）— 未盘问，不计入任何完成度 · 未评估风险

## 未拉的线（已发现泄漏点、未实测——续盘从这里接手）
- [X2] 台面连续运行一段时间后，desk.log 与 server-stdout.log 会长到多大、有没有轮转或上限？ — 泄漏点：实测官 S3 原话：desk.log 已有 259364802 字节，server-stdout.log 已有 139455351 字节；日志里每约 3 秒出现一对 GET /api/state 和 GET /api/memory
- [F13] 对 / 发 HEAD 请求返回什么？ — 泄漏点：实测官 S3 原话：HEAD / 返回 501，日志原文 Unsupported method ('HEAD')
- [F11] served_id 与 mlx_lm /v1/models 列出的 id 形式不同（repo 名 vs 本地路径）时，网关按 model 字段匹配会不会拒掉合法请求？ — 泄漏点：实测官 S21 原话：8767/v1/models 列出本地路径形式 id 与未加载的 GLM，status 的 served_id 是 repo 形式
- [F2] manifests/ 下遗留 catalog 已无的 glm8.json——旧清单缓存会不会被某处误读或永不清理？ — 泄漏点：实测官 S13 原话：manifests/ 目录里有 glm8.json（mtime Sep 16 02:14），catalog 里没有 glm8 这个 key
- [F8] 错误信封在各接口间形状不一（媒体会话接口 {error:'字符串'}、媒体作业 {error:{code,message,detail}}）——前端每处都按对的形状读出原因了吗？ — 泄漏点：实测官 S32 原话：POST /api/media-sessions/image 带 title 返回 400，错误体是 {"error": "不认识的字段：['title']"}（error 是字符串，不是对象）
- [X2] 删除一个媒体会话后，它的成品文件与 history 行仍在——素材库里这些成品显示成什么、能不能回填？ — 泄漏点：实测官 S32 原话：DELETE 媒体会话后，outputs 下的 png 和 history.jsonl 中引用该 session_id 的那一行仍在
- [F13] 浏览器打开台面时（服务端已在 0.07s 记下 /api/config），为什么客户端 15s 才收到、界面报「服务失联 / 请求超时」？——在无其它负载与有并发请求两种情形下各开一次页面 — 泄漏点：实测官 S1 原话：第 2 次加载 /api/config 发出后约 15s 才在客户端收到响应，服务端日志在发出后约 0.07s 就记了这条；load+15s 界面显示「服务失联」「请求超时（8 秒无响应）」，同时段 curl 直连约 1ms 返回
- [X4] 会话文件里的 output 指向 outputs 根之外（如 ../video-sessions/x.json）时，读会话判 output_missing=false、列表 cover 原样带出——取文件/拼接/配乐会不会读到根外文件？ — 泄漏点：实测官 S49 原话：自建会话的 output 写成 ../video-sessions/<自身id>.json（outputs 根目录之外的一个真实文件）：响应里 output_missing false；在列表接口里这个值出现在 cover 字段
- [F11] 设置页给出的局域网 base URL 取的是哪个地址？lan_candidates 里出现多个 .0 结尾的虚拟网卡地址时，界面推荐的地址别的设备真能连上吗？ — 泄漏点：实测官 S58 原话：/api/gateway/config lan_candidates 列 7 个地址，其中多个以 .0 结尾；lan_host 为 192.168.68.53
- [F11] 网关请求完全不写日志（http_server.py log_message 为 pass）——局域网别的设备调用了网关，用户事后能查到谁、何时调过吗？ — 泄漏点：实测官 S58 原话：desk.log 和 server-stdout.log 里 v1/models 各 0 行；http_server.py 中 log_message 为 pass
- [F4] 预算快照里媒体 peak_bytes 为 null 却标 source=predicted——没有数值的额度应标 predicted 还是 unavailable？界面据此显示什么？ — 泄漏点：实测官 S54 原话：media 中 video/music/image 各 {"peak_bytes": null, "source": "predicted"}
- [F14] 卸载脚本 --app-path 指向正在运行的 App 时只打印 rm -rf，不提示/不先退出——真实执行会删掉运行中的包吗？ — 泄漏点：实测官 S91 原话：--dry-run --app-path dist/LocalModelDesk.app 打印 rm -rf …；当时这个包正在运行（pid 5408），输出里没有任何关于“正在运行”的提示
- [F3] 会话文件里 title 为数字、model 为数组时，聊天页会话列表与模型选择能正常渲染吗？ — 泄漏点：实测官 S44 原话：body 为 {"title":123,"model":["a"]} 时返回 200，文件里原样写入 "title": 123 和 "model": ["a"]
- [X2] 删除一个正有尝试在生成中的媒体会话会怎样——作业继续跑吗、产物落到哪、状态条与卡片如何显示？ — 泄漏点：实测官 S51 原话：没有覆盖有 running 状态尝试（生成进行中）的会话被删除的情况
- [X3] 台面同时被两处打开（原生窗口 + 浏览器标签）时，一处的界面会把自己持有的 model/skills 写回到另一处正在编辑的会话吗？ — 泄漏点：实测官 S45 原话：自建会话被一条非本实测官发出的 PATCH 改成 model=gemma、skills=[]，说明另有一个打开着的界面会给列表首位或当前选中的会话写回 model 和 skills
- [F10] 服务进程对 codeload.github.com 的 HTTPS 连接调用结束后长期停在 CLOSE_WAIT——每次技能预览都泄漏一个套接字吗？ — 泄漏点：实测官 S35 原话：调用后 pid 5414 仍持有多条到 20.27.177.114:443 的 CLOSE_WAIT 套接字（fd 11、12、13、14），调用结束后没有消失
- [F10] 技能 SKILL.md frontmatter 只认扁平 key: value——带嵌套 metadata 块的常见公开技能都会被拒装，这是有意范围吗？ — 泄漏点：实测官 S36 原话：一个公开 skill 仓库的 SKILL.md frontmatter 含嵌套 metadata 块，解析器报『看不懂这一行：author: OpenAI』
- [F14] 媒体生成（图/视频/音乐子进程）与外壳启动路径下，App 会不会往自身包内写文件？（DQ1 只覆盖了服务与 LLM 路径） — 泄漏点：DQ1 could_not：图片、视频、音乐生成和模型下载没有做；外壳可执行文件路径未测。P3 枚举：music3_cli.py 与 GPU 探针启动时无 -s
- [F13] 台面服务对未注册的子路径按前缀匹配到父路由（/api/resources/download/nonexistent-xyz → 200 进度，/cancel/extra → 执行取消）——任意尾巴都会触发父操作吗？ — 泄漏点：实测官 S16 原话：GET /api/resources/download/nonexistent-xyz 200；POST /api/resources/download/cancel/extra 409 与 cancel 相同；desk/app.py:208 _find 在 path.startswith(pattern + '/') 时也算匹配
- [F4] 并发对话下实测每 token 字节的标定是否取错了别的请求的 Prompt Cache 行？（S23 记录的 gemma 188679 B/token 与预测 983040 相差 5 倍） — 泄漏点：实测官 S23 原话：0.02 GB×1e9÷106 = 188679，106 是调用 1 的 total_tokens；0.02 GB 是调用 2 结束时 mlx-lm.log 最后一条 Prompt Cache 行，它后面跟的是一条非本人发起的 POST
- [F1] 每次 POST /api/models/discover 都会重写 config.json 并把 first_run_done 置真——在已完成首运、用户手动设过目录时调用会不会覆盖用户选择？ — 泄漏点：实测官 S10 原话：config.json 内容逐字节相同但 inode 每次变化；firstrun.py:142 update_config(models_root=best, first_run_done=True)
- [F3] 聊天回复里的 markdown 表格、#### 标题、--- 分隔线、$\rightarrow$ 等 LaTeX 是否被渲染？（同一回复里 **粗体** 渲染成了 strong） — 泄漏点：J1 第 13 步：表格显示为竖线文本行，####、$\rightarrow$ 原样显示
- [F3] 流式回复结束时视口停在哪里——用户需要手动滚到回答末尾吗？ — 泄漏点：J1 第 11 步：「停止」变回「发送」时视口停在对话顶部
- [F3] 思考头显示的「已思考 N 秒」与实际思考时长一致吗？ — 泄漏点：J1 第 9 步：思考头写 214 秒，按快照时间戳从发送到截图约 196 秒
- [F4] 点「加载」后、加载完成前，顶栏「内存里：XX」与状态区「加载中」同时显示——加载失败或取消时顶栏会回到「无」吗？ — 泄漏点：J1 第 2 步：点加载那一刻顶栏已显示「内存里：Gemma 4 31B…」，状态区同时「加载中：gemma」
- [F13] 聊天页 main 下方孤立出现「宽 × 高（32 的倍数）」文本——别的页面的控件文字漏到聊天页了吗？ — 泄漏点：J1 起点及所有聊天页快照里 main 下方都有一段孤立文本「宽 × 高（32 的倍数）」
- [F3] 生成结束后、模型仍驻留时，顶栏「已用」从 85 GiB 降到 69 GiB——内存读数在生成中与生成后各代表什么？ — 泄漏点：J1 第 6/11/12 步顶栏已用 85/81/69 GiB，模型仍在加载状态
- [F6] 视频页 1280×800 视口下时间线区高约 244px、视频元素 400px——用户不滚动能看到并操作完成视频的播放控制条吗？ — 泄漏点：J3 第 8–9 步：控制条被下方表单挡住，需在时间线区内滚动才露出
- [F6] 删除视频会话后主区仍显示被删会话的视频与提示词——删除后界面落到哪个会话？ — 泄漏点：J3 清理阶段：删除后主区仍显示刚才那段视频，直到列表刷新
- [F8] 媒体会话项的改名/删除只在右键后出现——不知道右键的用户如何找到删除入口？ — 泄漏点：J3 清理阶段：会话项要右键才出现「改名」「删除会话」按钮
- [X1] 状态条在视频生成中显示「不可：媒体作业进行中」——此时驻留的聊天模型还能对话吗？界面如何告知？ — 泄漏点：J3 第 6 步 banner「不可：媒体作业进行中」，聊天子进程同时存活
- [F8] 媒体生成完成时，新成品的播放器在时间线可视区之外——图/视频/音乐页完成后会自动滚到新成品吗？ — 泄漏点：J4 第 8 步：audio y=99.9 在历史区可视顶部之上，需向上滚才露出；J3 第 8 步视频同样需滚动
- [F8] 已有一个 0 次生成的空「新会话」时再点「新会话」，会不断堆积空会话吗？ — 泄漏点：J4 第 2 步：音乐页原有空会话 16:49，点新会话又新建一个
- [F8] 媒体会话列表项时间（18:45）与条目标题时间（18:43）分别取的是什么时间？ — 泄漏点：J4 第 8 步：左栏 18:45，条目标题 18:43
- [F9] 从素材库回填参数时会落进当时激活的任意既有会话（与原成品无关）——回填后生成的这一版归到哪个会话？用户能选吗？ — 泄漏点：J6 第 4 步：回填落在无关的「方案一」会话，其历史显示在表单上方
- [F9] 回填后点「新会话」会清空刚回填的提示词、种子与「沿用素材库里这段」——用户想在新会话里迭代必须回填两次吗？ — 泄漏点：J6 第 6、9 步
- [X2] 原会话已删除的成品点回填参数时，前端请求 GET /api/media-sessions/video/<已删 id> 得 404——除控制台外界面有什么表现、回填结果是否受影响？ — 泄漏点：J6 第 4、9 步控制台 404 /api/media-sessions/video/12327c5f…
- [F9] 素材库卡片单击只加蓝框、双击才打开详情——界面有提示双击吗？键盘用户如何打开？ — 泄漏点：J6 第 2–3 步
- [F9] 「沿用素材库里这段」chip 与生成方式=文生视频同时出现，成品标「文生」——这个 chip 的含义是什么、对生成有影响吗？ — 泄漏点：J6 第 9、12 步
- [F3] 聊天历史里每条助手回答显示的模型标签取自哪里？会话换模型后，旧回答的标签会被改写成新模型吗？ — 泄漏点：J2 第 10–11 步：前 12 轮回答标签从 SuperQwen 变为 GLM；后端助手消息无 model 字段
- [F3] 打开一个已有会话时，模型下拉框会恢复成该会话用过的模型吗？ — 泄漏点：J2 第 2 步：会话卡片 superqwen，下拉默认 GLM 4.7 Flash
- [F3] 未加载模型时点发送会把会话的 model 改成下拉框里的模型——一次失败的发送应该改写会话元数据吗？ — 泄漏点：J2 第 6 步：会话卡片由 superqwen·19:00 变 glm·19:02
- [F3] 会话 API 返回 title 都是「新会话」而会话栏显示首句——标题是前端派生的吗？改名后两处一致吗？ — 泄漏点：J2 第 2 步
- [F3] 聊天消息区顶部一行被模型工具栏压住一半——在 1280×800 下首条消息头能完整看到吗？ — 泄漏点：J2 第 2、3、6 步截图
- [F5] 「在这张基础上改」并在提示词里新增元素时，新元素会出现在精修图里吗？精修强度是多少、用户能调吗？ — 泄漏点：J5 第 10 步：加「猫戴着一顶红色小围巾」后第 2 张构图与第 1 张一致，截图里看不到围巾
- [F5] 精修完成后底稿标签「以第 1 次为底稿」消失——连续精修第 3 张时底稿是哪一张？ — 泄漏点：J5 incidental 步骤 10
- [F6] 配乐会把视频原有的环境声整条替换为歌曲（原音轨系数 -60.9 dB）——这是有意的吗？用户能选择混音或保留环境声吗？ — 泄漏点：q-j8-audio：配乐成片音轨与拼接成片原音轨相关 0.047
- [F6] 配乐对话框只列出音乐会话（2 个），素材库里不在会话中的歌曲（素材库共 18 首音乐）能被选来配乐吗？ — 泄漏点：J8 第 5 步：对话框左栏只有 2 个音乐会话
- [F6] 配乐对话框里所选歌曲的播放器显示 0:00 / 0:00——用户能在选之前试听吗？ — 泄漏点：J8 第 5 步
- [F6] 续写段卡片的生成方式标签写「图生」——用户能从卡片上分辨这是续写段吗？ — 泄漏点：J8 第 3、4 步
- [F6] 单段 32kHz、成片 48kHz、配乐 44.1kHz——多次拼接/配乐后音频会被反复重采样吗？ — 泄漏点：q-j8-audio incidental
- [F11] 经网关一句 13 字的非流式请求（29 completion tokens）耗时约 40 秒——时间花在哪（排队、思考、首 token）？与台面内聊天同一问题耗时相比如何？ — 泄漏点：J9 第 4 步：19:54:35 → 19:55:15
- [F11] 设置里 base URL 旁的「复制」按钮点击后无任何反馈——剪贴板里真的写入了地址吗？ — 泄漏点：J9 第 2 步
- [F11] 网关返回的 content 以 "\n\n" 开头——思考段剥离后残留的空行会传给外部客户端吗？ — 泄漏点：J9 第 4 步
- [F1] 收编完成后的页面不显示收编了哪个目录、认出了几个模型——用户如何确认收编对了？ — 泄漏点：J7 第 2 步
- [F1] 资源页「半」状态（模型文件不完整）在界面上长什么样、能续传吗？ — 泄漏点：J7：克隆树里无不完整模型，「半」未出现
- [F1] 收编的「移动」模式会移动用户的模型树吗？中途失败时文件落在哪？ — 泄漏点：J7 could_not：只走了「指向」模式
- [F12] 原生 .app 外壳有自己的首次运行流程（FirstRunFlow）——它与 Web UI 首运页是同一条路径吗？ — 泄漏点：J7 incidental：strings 外壳二进制见 FirstRunFlow
- [F11] 网关端口被占用时（隔离实例 8770 绑定失败），界面或日志有任何提示吗？ — 泄漏点：J7 incidental：desk.log 无网关记录，界面未见提示
- [F3] 超过对话额度后追问时「发送」按钮灰显且无原因——此刻后台在做什么（压缩？等待？），界面应告诉用户什么？ — 泄漏点：J11 第 12–14 步
- [F3] 顶栏「对话额度」在 262144 → 18497 → 262144 字之间跳变，后缀始终「已实测」——这个数字表示总额度还是剩余额度？ — 泄漏点：J11 第 7、9 步
- [X3] 流式回答进行中页面被导航离开时，刚发出的用户消息会丢失吗？ — 泄漏点：J11 第 3–4 步：页面被导航后重开会话，第 3 步发出的 100042 字消息不在
- [F3] 同样 100042 字首轮，一次 185 秒未答完、一次「已思考 4 秒」就答完——Prompt Cache 命中与否对首轮耗时的影响用户看得到吗？ — 泄漏点：J11 incidental 步骤 7
- [F3] 删除会话后会话栏 DOM 末尾残留 3 个「正在加载会话…」占位——会话列表加载状态会卡住吗？ — 泄漏点：J11 清理后
- [F10] 技能入口只在聊天页「指令」按钮里，资源页与设置里都没有——用户如何发现「技能」这个功能？ — 泄漏点：J10 第 1–6 步
- [F10] 从 GitHub 安装框的 URL 输入框约 175px，长 URL 只显示末尾——用户能核对自己填的地址吗？ — 泄漏点：J10 第 12 步
- [F13] 页面每 1–2 秒轮询 6 个以上接口，3 分钟累积 719 条请求——长时间开着页面（含后台标签）时轮询会降频吗？ — 泄漏点：J10 incidental
- [F10] 内置技能都标「还没量过 token」——技能的 token 占用何时被量、在哪显示？ — 泄漏点：J10 第 6 步
- [X1] 多段（如 6 段以上）或较长视频拼接时，拼接窗口有多长？窗口内状态接口宣称可开重活、实际 409 的不一致会被用户撞上吗？ — 泄漏点：p4-join：2–3 段短视频窗口 ≤0.42s
- [X1] 点「生成视频」后约 1 秒内状态条仍显示「媒体：空闲 / 可开下一件重活」——2 秒轮询下，此时在另一页点生成会怎样？ — 泄漏点：p4-join incidental：卡片已生成中，banner 仍空闲至 22:02:18.445
- [F3] mlx_lm 生成线程因 Metal OOM 死掉后，/api/llm/status 仍报 loaded、新请求被接受后无输出挂起——用户能否得知模型已不可用、如何恢复？ — 泄漏点：p5-compact incidental：pid 73750 _generate 线程 2026-10-08 20:27 OOM（321435 token prompt），03:26 发送挂起
- [F3] 未点停止时，挂起的回答在约 65 秒后以「已停止生成」(code stopped) 结束——是谁中止的、用户看到的说法是否属实？ — 泄漏点：p5-compact incidental：03:26:21 发送，03:27:26 interrupted stopped，实测官未点停止
- [F3] 经界面卸载模型打断正在进行的流式回答时，错误文字为「内存让给了媒体作业，回答被中断」（code evicted）——无媒体作业时用户是否被误导？ — 泄漏点：p5-compact：卸载触发 evicted，状态条「媒体：空闲」
- [F3] 自动压缩请求的 prompt（253571 token）比触发它的那一轮（218158 token）还大，摘要 prompt 把开头用户消息在「对话记录」与「用户原话」里各放一遍——接近 token 上限的会话压缩本身会不会超额失败？ — 泄漏点：p5-compact incidental：压缩请求体 433,144 字
- [F3] 「已思考 N 秒」把整段预填等待（1303 s）算进思考时长，而思考文本只有约 172 字——这个数字对用户意味着什么？ — 泄漏点：p5-compact incidental
- [F3] 回答失败的行内错误「回答没有生成完：当前没有加载模型」在后续成功回答与压缩后仍留在屏上——旧错误何时清除？ — 泄漏点：p5-compact incidental：04a 错误在 04c 仍显示
- [F3] GET /api/sessions/{id} 没有专门路由，返回 200 与整份会话列表——按 id 读单个会话的调用者会拿到什么？ — 泄漏点：p5-compact incidental
- [F3] 多路请求（聊天流、提示词助手、长预填充）并行压到同一个 mlx_lm 时，服务端有无准入/排队？并行导致 Metal OOM 后，用户看到什么、如何恢复？ — 泄漏点：p5-assist：4 路并行时 mlx _generate 线程 Metal OOM（顶栏「可用 11 GiB」），之后 /api/llm/status 仍 loaded、error null、顶栏「可开下一件重活」，请求 0 字节——与 p5-compact 首见的死线程同一现象第二次复现
- [F3] 客户端断开后，服务端要过约 4–5 分钟才记「sse client went away」——断开的聊天流在这期间是否继续占用上游？ — 泄漏点：p5-assist：curl 05:04:10 被 kill，desk 05:08:50 才记 went away
- [F8] 图片页没有提示词助手（看手气/优化提示词），视频与音乐页有——这是有意的范围吗？ — 泄漏点：p5-assist incidental：createPromptAssist 只在 video.js/music.js 引用
- [F11] mlx_lm 的 /v1/models 同时列出 SuperQwen 与 Huihui-GLM-4.7-Flash——单驻留模型下第二个名字从哪来，网关 /v1/models 会否把它报给外部客户端？ — 泄漏点：p5-assist incidental：OOM 后探测 /v1/models

## 缺陷模式（同类位点清点——未查位点不进任何完成度）

### P1 接收用户可控路径/名字的处理器对异常字符（NUL 等）不做校验，抛异常后连接零字节断开而非返回 4xx — 共 25 位点：实证 1，未查 24
- **缺口** GET /static/* — 调用 S2「Static assets」（入口 GET /static/* (desk/ui.py:25)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。
- **未查** GET /api/outputs/{name}（[F9] 同类嫌疑，未实证）
- **未查** POST /api/outputs/{name}/reveal（[F9] 同类嫌疑，未实证）
- **未查** PATCH /api/sessions/{id}（损坏会话文件 → 500）（[F3] 同类嫌疑，未实证）
- **未查** DELETE /api/sessions/{id}（[F3] 同类嫌疑，未实证）
- **未查** GET/POST /api/media-sessions/{kind}（[F8] 同类嫌疑，未实证）
- **未查** GET/PATCH/DELETE /api/media-sessions/{kind}/{id}（[F8] 同类嫌疑，未实证）
- **未查** POST /api/media/inputs（[F8] 同类嫌疑，未实证）
- **未查** POST /api/media/video 素材 id（[F6] 同类嫌疑，未实证）
- **未查** POST /api/media/* body.session_id（[F8] 同类嫌疑，未实证）
- **未查** POST /api/media/* continues/parts/source（损坏会话 → 500）（[F8] 同类嫌疑，未实证）
- **未查** POST /api/media/* refs（[F6] 同类嫌疑，未实证）
- **未查** POST /api/media/image base.attempt_id（损坏会话 → 500）（[F5] 同类嫌疑，未实证）
- **未查** POST /api/llm/load key（[F3] 同类嫌疑，未实证）
- **未查** POST /api/llm/chat[/stream] model（[F3] 同类嫌疑，未实证）
- **未查** GET /api/resources/status/{key}（[F2] 同类嫌疑，未实证）
- **未查** POST /api/resources/download key（[F2] 同类嫌疑，未实证）
- **未查** POST /api/resources/delete key/confirm（[F2] 同类嫌疑，未实证）
- **未查** PUT /api/config models_root/outputs_root（无规范化、未知键照写）（[F1] 同类嫌疑，未实证）
- **未查** POST /api/first-run models_root（[F1] 同类嫌疑，未实证）
- **未查** POST /api/adopt legacy_root/target_root（非字符串/NUL → 500）（[F1] 同类嫌疑，未实证）
- **未查** POST /api/skills/preview url（不校验 scheme/host）（[F10] 同类嫌疑，未实证）
- **未查** POST /api/skills/install staging_id（[F10] 同类嫌疑，未实证）
- **未查** POST /api/skills/discard staging_id（[F10] 同类嫌疑，未实证）
- **未查** :8770 /v1/* model 与 Content-Length（int 解析异常落到 socketserver 默认处理）（[F11] 同类嫌疑，未实证）

### P2 网关在读请求体之前就回拒绝响应却保持 HTTP/1.1 keep-alive，残留请求体污染同连接下一请求 — 共 9 位点：实证 1，未查 8
- **缺口** :8770 405/404 拒绝分支 — 调用 S61「Gateway: wrong method / unknown path rejections」（入口 desk/gateway/http_server.py:110-126 (405/404)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。
- **未查** GET /v1/models 带请求体（200，不读体）（[F11] 同类嫌疑，未实证）
- **未查** GET 其它路径 404（[F11] 同类嫌疑，未实证）
- **未查** POST 其它路径 404（[F11] 同类嫌疑，未实证）
- **未查** POST /v1/models 405（[F11] 同类嫌疑，未实证）
- **未查** POST chat 路由 Content-Length>10MB 400（读空提前 break 时残留）（[F11] 同类嫌疑，未实证）
- **未查** POST chat 路由 Transfer-Encoding: chunked（不处理分块体）（[F11] 同类嫌疑，未实证）
- **未查** POST chat 路由 Content-Length 非整数（无响应，异常落 socketserver）（[F11] 同类嫌疑，未实证）
- **未查** 网关 PUT/DELETE/PATCH/HEAD/OPTIONS（stdlib 默认 501）（[F11] 同类嫌疑，未实证）

### P4 写会话/记录的接口只校验键名与外层类型，不校验字段值类型与元素形状，非法值原样落盘 — 共 16 位点：实证 2，未查 14
- **缺口** POST /api/sessions — 调用 S44「Create chat session」（入口 POST /api/sessions (desk/library/http.py:196)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。
- **缺口** PATCH /api/sessions/{id} — 调用 S45「Update chat session (messages/title/skills; keepalive)」（入口 PATCH /api/sessions/{id} (desk/library/http.py:197)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。
- **未查** PUT /api/config（未知顶层键原样写入 config.json）（[F1] 同类嫌疑，未实证）
- **未查** POST /api/config/reset force bool() 强转（[F1] 同类嫌疑，未实证）
- **未查** POST /api/first-run（[F1] 同类嫌疑，未实证）
- **未查** POST /api/adopt legacy_root/target_root 无 str 检查（[F1] 同类嫌疑，未实证）
- **未查** PATCH /api/media-sessions（title 已校验）（[F8] 同类嫌疑，未实证）
- **未查** POST /api/media/video frames/steps 无上限（[F6] 同类嫌疑，未实证）
- **未查** POST /api/media/music duration 无上限与有限性检查（[F7] 同类嫌疑，未实证）
- **未查** POST /api/media/image（[F5] 同类嫌疑，未实证）
- **未查** POST /api/media/compose（[F6] 同类嫌疑，未实证）
- **未查** POST /api/media/soundtrack（[F6] 同类嫌疑，未实证）
- **未查** POST /api/resources/download key str() 强转（[F2] 同类嫌疑，未实证）
- **未查** POST /api/llm/chat/stream messages/采样参数无类型校验直传上游（[F3] 同类嫌疑，未实证）
- **未查** POST /v1/chat/completions temperature/top_p 无类型检查（[F11] 同类嫌疑，未实证）
- **未查** POST /v1/messages temperature/top_p 无类型检查（[F11] 同类嫌疑，未实证）

### P4 台面状态显示（Web 状态条持有者段 / macOS 菜单栏）只渲染单一持有者 holders[-1]，不反映多件并存与加载中、拼接中等过渡态 — 共 37 位点：实证 4，未查 33
- **缺口** Web 状态条·持有者段 | 聊天先驻留、媒体后授予（共存，显示媒体） — J3 走得通吗？
- **缺口** Web 状态条·持有者段 | 视频/音乐拼接阶段（permit 已释放、作业仍 running） — 在 LocalModelDesk 的视频页，对一段已完成的视频点「接着往下生」生成续写段：续写段的模型生成结束之后、该次尝试最终标为完成之前，台面会把多段拼成「成片」。在这段拼接时间窗里（以及它前后各几秒），Web 状态条的「内存里 / 媒体 / 下一件重活」三段文字、GET /api/state 的 holder/holders/media_busy/can_start、GET /api/media/job 的作业状态各是什么？在这段窗口里，若尝试再启动一件重活（例如在音乐页点生成一首短歌，或在视频页的另一个会话再生成一段），台面接受还是拒绝、给出什么文字？请按时间轴（精确到秒）记录。
- **缺口** Web 状态条·媒体段 | 拼接阶段（显示空闲） — 在 LocalModelDesk 的视频页，对一段已完成的视频点「接着往下生」生成续写段：续写段的模型生成结束之后、该次尝试最终标为完成之前，台面会把多段拼成「成片」。在这段拼接时间窗里（以及它前后各几秒），Web 状态条的「内存里 / 媒体 / 下一件重活」三段文字、GET /api/state 的 holder/holders/media_busy/can_start、GET /api/media/job 的作业状态各是什么？在这段窗口里，若尝试再启动一件重活（例如在音乐页点生成一首短歌，或在视频页的另一个会话再生成一段），台面接受还是拒绝、给出什么文字？请按时间轴（精确到秒）记录。
- **缺口** macOS 菜单栏 | 图片作业进行中（无 image 分支，落 default「状态不可读」） — LocalModelDesk 的 macOS 菜单栏状态项（屏幕右上角的状态图标/标题及点开后的菜单，其中有一行状态文字）在以下时刻分别显示什么：(a) 没有媒体作业时；(b) 在图片页生成一张图片的过程中；(c) 图片生成完成后。同时记录同一时刻 GET http://127.0.0.1:8766/api/state 的 holder/holders。
- **未查** Web 状态条·内存段 任意状态（整机读数，不按持有者拆分）（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·对话额度后缀 | 聊天已加载（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·对话额度后缀 | 无/加载中/失败或取消后/仅媒体（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 无（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 聊天加载中（与已加载文案相同）（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 聊天已加载（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 已加载时切换另一模型（显示旧模型名）（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 仅媒体作业进行中（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 媒体先跑、之后加载聊天（共存，显示聊天）（[X1] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 让出聊天给媒体的 acquiring 过渡态（[X1] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 下载进行中（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 加载取消后（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 加载失败后（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·持有者段 | 卸载后端口仍被占用 error 态（未 release_heavy）（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·媒体段 | 无/仅聊天（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·媒体段 | 媒体作业进行中（含共存与 acquiring）（[X1] 同类嫌疑，未实证）
- **未查** Web 状态条·媒体段 | 下载进行中（窄屏不反映）（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·下一件重活段 | 无（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·下一件重活段 | 聊天加载中/已加载（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·下一件重活段 | 媒体作业进行中（只问媒体能否开）（[X1] 同类嫌疑，未实证）
- **未查** Web 状态条·下一件重活段 | acquiring 过渡态（[X1] 同类嫌疑，未实证）
- **未查** Web 状态条·下一件重活段 | 下载进行中（[F4] 同类嫌疑，未实证）
- **未查** Web 状态条·下一件重活段 | 服务失联（[F13] 同类嫌疑，未实证）
- **未查** Web 状态条·整体 tone | 各状态（[F4] 同类嫌疑，未实证）
- **未查** GET /api/state holder=holders[-1] / holders / media_busy / can_start（[F4] 同类嫌疑，未实证）
- **未查** GET /api/budget chat 只反映已加载完成的聊天模型（[F4] 同类嫌疑，未实证）
- **未查** macOS 菜单栏 | 启动中/停止/失败/待设置/状态不可读（[F12] 同类嫌疑，未实证）
- **未查** macOS 菜单栏 | 无（[F12] 同类嫌疑，未实证）
- **未查** macOS 菜单栏 | 聊天加载中/已加载/切换中/卸载端口失败（均显示「已加载」）（[F12] 同类嫌疑，未实证）
- **未查** macOS 菜单栏 | 视频/音乐作业进行中（含聊天先驻留共存）（[F12] 同类嫌疑，未实证）
- **未查** macOS 菜单栏 | 媒体先跑、之后加载聊天（共存，显示已加载）（[F12] 同类嫌疑，未实证）
- **未查** macOS 菜单栏 | 下载进行中/拼接阶段/加载取消或失败后（显示空闲）（[F12] 同类嫌疑，未实证）
- **未查** macOS 菜单栏内存行 | 任意状态（[F12] 同类嫌疑，未实证）

### P5 服务端调用本机 LLM 上游的请求超时设定不随长上下文预填时长放宽，长上下文下以「上游流中断: timed out」中断 — 共 12 位点：实证 3，未查 9
- **缺口** POST /api/llm/chat/stream 超额度后的追问（含压缩路径） — J11 走得通吗？
- **缺口** 前端 runSummarise 自动压缩（失败被 maybeCompact 吞掉、不显示错误） — LocalModelDesk 的聊天页在会话长到需要自动压缩上下文时，若这次压缩请求没能成功（例如压缩进行中聊天模型被卸载、或上游请求中断/超时），用户在界面上看到什么（有无进行中提示、有无失败提示及其文字）、这一轮用户的提问最终得到什么、会话里原来的消息与有无摘要块各是什么状态、下一次发送时又发生什么？请分别记录压缩开始前、压缩进行中、压缩失败后、再次发送后的界面与 GET /api/sessions/{id} 读回。
- **缺口** POST /api/llm/prompt-assist（后端 300s；前端 180s 中止但后端不取消） — LocalModelDesk 的提示词助手（图片/视频/音乐页上的「看手气」「优化提示词」等，经 POST /api/llm/prompt-assist 调用已加载的聊天模型）在一次请求耗时超过界面自身的等待上限时，界面上显示什么（文字、按钮状态、原提示词框内容）？此时服务端与聊天模型是否仍在处理那次请求（看服务端/上游 mlx_lm 日志、/api/llm/status、/api/state 与模型进程 CPU）？在它被放弃之后、上游仍在忙时，立即再用一次提示词助手、以及在聊天页发一条消息，各自发生什么、各要等多久？
- **未查** backend.health GET /v1/models（timeout=1.0 字面量）（[F3] 同类嫌疑，未实证）
- **未查** 加载就绪轮询（load_timeout_s=180，超时不终止子进程）（[F3] 同类嫌疑，未实证）
- **未查** backend.chat 非流式（timeout=300.0 每次 socket 操作，无总上限）（[F3] 同类嫌疑，未实证）
- **未查** POST /api/llm/chat（502 upstream_error，前端无调用者）（[F3] 同类嫌疑，未实证）
- **未查** backend.chat_stream SSE（300s 为两行之间最长间隔）（[F3] 同类嫌疑，未实证）
- **未查** 前端 streamReply（无超时；错误保留已生成内容+重试）（[F3] 同类嫌疑，未实证）
- **未查** 网关非流式 /v1/chat/completions、/v1/messages（继承 300s，500 chat backend failed）（[F11] 同类嫌疑，未实证）
- **未查** 网关流式（继承 300s 行间隔；OpenAI 方言不发 [DONE]）（[F11] 同类嫌疑，未实证）
- **未查** 前端 llmStatus 轮询（8s 单次，无总上限）（[F3] 同类嫌疑，未实证）

## 违规裁决（无证据或非法裁决，已拒渲）
以下 58 条 entry 不计入任何统计：
- 调用 S3「Read config」（入口 GET /api/config (desk/foundation/routes.py:120)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S14「Download progress」（入口 GET /api/resources/download (desk/resources/http.py:73)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S18「Disk usage」（入口 GET /api/resources/disk (desk/resources/http.py:77)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S21「LLM status」（入口 GET /api/llm/status (desk/llm/routes.py:51)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S13「Status of one model」（入口 GET /api/resources/status/{key} (desk/resources/http.py:72)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S11「Model catalog」（入口 GET /api/resources/catalog (desk/resources/http.py:69; runtime.py:120 returns a bare array)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S12「Status of every model (?refresh)」（入口 GET /api/resources/status (desk/resources/http.py:70)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S32「Media job status + log (?log_from&job_id)」（入口 GET /api/media/job (desk/media/routes.py:95)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S1「Static UI shell (index.html)」（入口 GET / | GET /index.html (desk/ui.py:23 StaticAssets.resolve)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S6「Resolved paths」（入口 GET /api/paths (desk/foundation/routes.py:124)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S7「Capability probe (mlx_h3/image_runtime/music_runtime)」（入口 GET /api/capabilities (desk/foundation/routes.py:125)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S33「List skills」（入口 GET /api/skills (desk/skills/routes.py:20)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S41「List outputs」（入口 GET /api/outputs (desk/library/http.py:193)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S43「List chat sessions」（入口 GET /api/sessions (desk/library/http.py:195)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S40「Serve output file」（入口 GET /api/outputs/{name} (desk/library/http.py:192)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S49「Read media session」（入口 GET /api/media-sessions/{kind}/{id} (desk/library/http.py:201)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S53「Memory snapshot」（入口 GET /api/memory (desk/runtime.py:157)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S47「List media sessions (image|music|video)」（入口 GET /api/media-sessions/{kind} (desk/library/http.py:199)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S57「Unknown route / bad Content-Length envelope」（入口 desk/app.py:58-70 (404 not_found, 400 bad_request)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 让 S70「Startup: sweep stale skill staging」（入口 desk/skills/service.py:108 sweep_stale_staging）跑一次后实际发生了什么：你用什么手段让它跑起来（直接调入口函数、
改调度表达式、往队列投一条消息、发一个事件——手段本身是观察，照实记）；跑之前它作用的资源是什么状态、跑的
过程中进程输出了什么、跑完之后资源是什么状态；
跑的期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
跑完后该任务对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S58「Gateway: model list (default 0.0.0.0:8770, enabled by default)」（入口 GET /v1/models (desk/gateway/http_server.py:108; defaults foundation/config.py:59)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S92「Script: build headless shell binary」（入口 scripts/build-shell-app.sh <out-dir>）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S52「Arbiter desk state」（入口 GET /api/state (desk/runtime.py:156)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S54「Budget snapshot + chat allowance」（入口 GET /api/budget (desk/runtime.py:158 _budget_payload)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 让 S76「Skills store scan (bundled + user roots, broken entries)」（入口 desk/skills/store.py:95 scan）跑一次后实际发生了什么：你用什么手段让它跑起来（直接调入口函数、
改调度表达式、往队列投一条消息、发一个事件——手段本身是观察，照实记）；跑之前它作用的资源是什么状态、跑的
过程中进程输出了什么、跑完之后资源是什么状态；
跑的期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
跑完后该任务对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S91「Script: uninstall app (+ legacy LaunchAgent)」（入口 scripts/uninstall-app.sh [--app-path] [--data-root] [--launch-agents-dir] [--purge-data] [--dry-run]）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S55「Read gateway config」（入口 GET /api/gateway/config (desk/runtime.py:161)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S48「Create media session」（入口 POST /api/media-sessions/{kind} (desk/library/http.py:200)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S51「Delete media session」（入口 DELETE /api/media-sessions/{kind}/{id} (desk/library/http.py:203)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S50「Rename media session」（入口 PATCH /api/media-sessions/{kind}/{id} (desk/library/http.py:202)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S46「Delete chat session」（入口 DELETE /api/sessions/{id} (desk/library/http.py:198)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S89「Script: verify app bundle (V1–V8)」（入口 scripts/verify-app.sh [--source-root]）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 让 S75「Bundled skills」（入口 desk/skills/bundled/{译成中文,代码审查,写得清楚些}/SKILL.md）跑一次后实际发生了什么：你用什么手段让它跑起来（直接调入口函数、
改调度表达式、往队列投一条消息、发一个事件——手段本身是观察，照实记）；跑之前它作用的资源是什么状态、跑的
过程中进程输出了什么、跑完之后资源是什么状态；
跑的期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
跑完后该任务对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S38「Reveal outputs folder in Finder」（入口 POST /api/outputs/reveal (desk/library/http.py:190)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S39「Reveal one output in Finder」（入口 POST /api/outputs/{name}/reveal (desk/library/http.py:191)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S37「Discard staged skill」（入口 POST /api/skills/discard (desk/skills/routes.py:24)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S36「Confirm skill install (lands on disk, stays disabled)」（入口 POST /api/skills/install (desk/skills/routes.py:23)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S87「Script: build app」（入口 scripts/build-app.sh [--output] [--identity] [--adhoc] [--python-version]）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S15「Start or resume a download」（入口 POST /api/resources/download (desk/resources/http.py:74)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S16「Cancel a download」（入口 POST /api/resources/download/cancel (desk/resources/http.py:75)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 D2「[dead contract] POST /api/llm/chat (non-streaming): no caller in UI or shell, and the gateway uses DeskGatewayBackend directly (tests only)」（入口 desk/llm/routes.py:53）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S22「Non-streaming chat」（入口 POST /api/llm/chat (desk/llm/routes.py:53)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S10「Scan this Mac for model directories」（入口 POST /api/models/discover (desk/foundation/routes.py:128)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S88「Script: sign app」（入口 scripts/sign-app.sh [--identity] [--adhoc]）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S17「Delete a model (confirm=key)」（入口 POST /api/resources/delete (desk/resources/http.py:76)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S23「Streaming chat (SSE)」（入口 POST /api/llm/chat/stream (desk/llm/routes.py:54)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S24「Prompt assist (polish / feeling lucky)」（入口 POST /api/llm/prompt-assist (desk/llm/routes.py:55)）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- 调用 S90「Script: install app」（入口 scripts/install-app.sh [--app] [--dest] [--source-root]）后实际发生了什么：调用前的相关状态、调用的原始输出或响应、
调用后的相关状态各是什么；
调用期间出现了哪些下游请求或外部调用（方法、目标、请求体摘要、状态码、响应体摘要；零条就记零条，并记下
你用什么手段抓的、同一会话里它抓到过哪条别的请求）；
调用后该操作对应的服务端资源和本地存储各读回来是什么（只涉及一边的，另一边写"不适用"并说明为什么）。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- LocalModelDesk.app 在正常使用中，会不会往它自己的应用包（Contents/Resources 下）写入新文件（例如 __pycache__/*.pyc）？请用一份与正在运行的那份隔离的副本来回答：在副本被启动、并经它的界面或接口做过若干常见操作（打开页面、读状态、加载/卸载一个聊天模型、发一条聊天、查看资源页）之后，副本包内有哪些文件是启动之后新出现或被改动的、各由哪个进程在何时写入；副本的 codesign --verify --deep --strict 在启动前后各是什么结果。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- J1 走得通吗？（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- J4 走得通吗？（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- J6 走得通吗？（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- J2 走得通吗？（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- J5 走得通吗？（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- J8 走得通吗？（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- LocalModelDesk 的视频会话「海边日落，一个人沿着沙滩慢慢…」里有三次结果：第 1 次（文生）、第 2 次（接第 1 次，卡片默认播放「成片」）、第 3 次（卡片标为「配乐：温暖的城市流行，钢琴与轻鼓，男声，中速，夜晚的氛… · 基于第 2 次」，文件 /api/outputs/h3-soundtrack-20261008-191900-3a522865.mp4）。所标注的那首歌是音乐会话「温暖的城市流行…」的第 1 次，文件 /api/outputs/music3-20261008-184345-1fc8f499.wav。第 3 次文件里的音轨，与这首歌的音频、与第 2 次「成片」文件原有的音轨、与第 1 次和第 2 次单段文件的音轨之间，各是什么关系？请用信号层面的比对（例如解码成 PCM 后做互相关/逐段相似度、比较电平与频谱、对齐偏移）给出可复核的数值，而不是看文件名或标签。（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- J9 走得通吗？（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
- J7 走得通吗？（规则基线未澄清或审查未完成，不能据此判 done（见规则一致性））
