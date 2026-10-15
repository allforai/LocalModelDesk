# 完成度报告 — LocalModelDesk 全应用（macOS 外壳 dist/LocalModelDesk.app + 本地 Python 服务 desk + 零依赖 Web UI）——新 run 从头完整盘，所有界面面与旅程

需求基准：superstorm-registry · 共 22 面，盘问 3 面 · 实测 32 问 · 旅程 4 条，盘问 4 条 · 操作面 96 个，裁决触及 17 个
被评构建：0d98e9ef9e09a3f9674604308e8d63d4357bfd22-e3b0c44298fc1c14（intake 记录于 2026-10-14T16:46:14+09:00）

## 总览

实证完成：7（运行时 7 · 代码 0 · 台账 0） · 缺口：15 · 跑偏：0 · 无法自证：10
旅程裁决：实证完成：4 · 缺口：0 · 跑偏：0 · 无法自证：0

> 盘问官即交付作者（examiner_is_author）：bias-guard 生效——gap 从严，降级为 low 或 done 需额外独立证据。

> 本 run 取证类子 agent（实测官、枚举官）用 sonnet（枚举官、只打 API 的实测官）；session（浏览器/界面旅程实测官），用户于 2026-10-14T16:40:00+09:00 确认：「枚举官和只打 API 的探针用 sonnet；浏览器/界面旅程的实测官用会话模型」。裁决与普查仍用会话模型。
> 定靶时盘问官推荐的是选项 A（靶子以 webview UI 旅程为主，降档实测官易残缺重派；用户记忆提过成本，B 亦合理）。

取证时间：首问 2026-10-14T16:58:18+09:00 · 末问 2026-10-15T07:48:18+09:00 · 跨 890 分钟
相邻 runtime 问间隔不足 60 秒，请核对是否真实取证：视觉验收 v05-chat A · gap → 视觉验收 v05-chat A · done（0 秒）；视觉验收 v05-chat A · done → 视觉验收 v05-chat B · gap（0 秒）；视觉验收 v05-chat B · gap → 视觉验收 v05-chat B · done（0 秒）；视觉验收 v05-chat B · done → 视觉验收 v05-chat C · gap（0 秒）；视觉验收 v05-chat C · gap → 视觉验收 v05-chat C · done（0 秒）；视觉验收 v06-video A · gap → 视觉验收 v06-video A · done（0 秒）；视觉验收 v06-video A · done → 视觉验收 v06-video B · gap（0 秒）；视觉验收 v06-video B · gap → 视觉验收 v06-video B · done（0 秒）；视觉验收 v06-video B · done → 视觉验收 v06-video C · gap（0 秒）；视觉验收 v06-video C · gap → 视觉验收 v06-video C · done（0 秒）；视觉验收 v07-image-music A · gap → 视觉验收 v07-image-music A-mid · unprovable（0 秒）；视觉验收 v07-image-music A-mid · unprovable → 视觉验收 v07-image-music B · gap（0 秒）；视觉验收 v07-image-music B · gap → 视觉验收 v07-image-music B-mid · unprovable（0 秒）；视觉验收 v07-image-music B-mid · unprovable → 视觉验收 v07-image-music C · gap（0 秒）；视觉验收 v07-image-music C · gap → 视觉验收 v07-image-music C-mid · unprovable（0 秒）；视觉验收 v08-resources-library A · gap → v08-resources-library（视觉验收 v08-resources-library A-mid · unpro…）（0 秒）；v08-resources-library（视觉验收 v08-resources-library A-mid · unpro…） → 视觉验收 v08-resources-library B · gap（0 秒）；视觉验收 v08-resources-library B · gap → 视觉验收 v08-resources-library C · gap（0 秒）；视觉验收 v09-dialogs 900x600@1 · unprovable → 视觉验收 v09-dialogs mid · unprovable（0 秒）；视觉验收 v09-dialogs mid · unprovable → 视觉验收 v09-dialogs 1400x900@1 · unprovable（0 秒）；视觉验收 v09-dialogs 1400x900@1 · unprovable → v09-dialogs（视觉验收 v09-dialogs 2560x1440@1 · unprovabl…）（0 秒）；视觉验收 v10-settings A · done → 视觉验收 v10-settings A-mid · unprovable（0 秒）；v11-firstrun-fatal-shellerror（视觉验收 v11-firstrun-fatal-shellerror A · g…） → v11-firstrun-fatal-shellerror（视觉验收 v11-firstrun-fatal-shellerror A-mid…）（0 秒）；v11-firstrun-fatal-shellerror（视觉验收 v11-firstrun-fatal-shellerror A-mid…） → v11-firstrun-fatal-shellerror（视觉验收 v11-firstrun-fatal-shellerror B · g…）（0 秒）；v11-firstrun-fatal-shellerror（视觉验收 v11-firstrun-fatal-shellerror B · g…） → v11-firstrun-fatal-shellerror（视觉验收 v11-firstrun-fatal-shellerror C · g…）（0 秒）

## 规则一致性（规则 ↔ 规则；候选不计为产品缺陷）
来源 54 份 · 规则 928 条 · 比较组 92 个 · 候选 41 条
仅核对本轮材料；语义覆盖、来源完整性与用户确认真实性须核对独立审查记录。
独立审查：/private/tmp/claude-502/-Users-aa-LocalModelDesk/6fbf13b4-174d-4f38-8ca1-21e876b7ebba/tasks/a1ba13a7b97a2bdfb.output · claude-opus-5-5 (session)
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
- 来源 SRC35：docs/adr/0001-deepseek-v4-not-yet.md @ 0d98e9e（evidence/rules/sources/adr-0001-deepseek-v4-not-yet.md）
- 来源 SRC36：docs/qwen-image-mlx.md @ 0d98e9e（evidence/rules/sources/qwen-image-mlx.md）
- 来源 SRC37：docs/visual/README.md @ 0d98e9e（evidence/rules/sources/visual-README.md）
- 来源 SRC38：docs/visual/interaction-baseline.candidate.json @ 0d98e9e（evidence/rules/sources/visual-interaction-baseline.candidate.json）
- 来源 SRC39：docs/visual/visual-baseline.candidate.json @ 0d98e9e（evidence/rules/sources/visual-visual-baseline.candidate.json）
- 来源 SRC40：docs/superpowers/plans/2026-09-11-cross-exam-0908-visual.md @ 0d98e9e（evidence/rules/sources/plan-2026-09-11-cross-exam-0908-visual.md）
- 来源 SRC41：~/.claude/projects/-Users-aa-LocalModelDesk/memory/feedback-hardware-soft-limits.md （用户在过往会话确认的决定，记忆文件原样，2026-10-14 快照）（evidence/rules/sources/user-confirmed-feedback-hardware-soft-limits.md）
- 来源 SRC42：~/.claude/projects/-Users-aa-LocalModelDesk/memory/feedback-no-legacy-framing.md （用户在过往会话确认的决定，记忆文件原样，2026-10-14 快照）（evidence/rules/sources/user-confirmed-feedback-no-legacy-framing.md）
- 来源 SRC43：~/.claude/projects/-Users-aa-LocalModelDesk/memory/project-deepseek-v4-not-on-mlx-lm.md （用户在过往会话确认的决定，记忆文件原样，2026-10-14 快照）（evidence/rules/sources/user-confirmed-project-deepseek-v4-not-on-mlx-lm.md）
- 来源 SRC44：~/.claude/projects/-Users-aa-LocalModelDesk/memory/project-img2img-next.md （用户在过往会话确认的决定，记忆文件原样，2026-10-14 快照）（evidence/rules/sources/user-confirmed-project-img2img-next.md）
- 来源 SRC45：~/.claude/projects/-Users-aa-LocalModelDesk/memory/project-media-sessions-plan.md （用户在过往会话确认的决定，记忆文件原样，2026-10-14 快照）（evidence/rules/sources/user-confirmed-project-media-sessions-plan.md）
- 来源 SRC46：~/.claude/projects/-Users-aa-LocalModelDesk/memory/project-visual-baseline-direction.md （用户在过往会话确认的决定，记忆文件原样，2026-10-14 快照）（evidence/rules/sources/user-confirmed-project-visual-baseline-direction.md）
- 来源 SRC47：.allforai/bootstrap/local-requirements.json @ 2026-10-14 工作树快照（未跟踪目录）（evidence/rules/sources/allforai-bootstrap-local-requirements.json）
- 来源 SRC48：.allforai/visual-qa/visual-acceptance-criteria.json @ 2026-10-14 工作树快照（未跟踪目录）（evidence/rules/sources/allforai-visual-acceptance-criteria.json）
- 来源 SRC49：.allforai/visual-qa/visual-evidence-requirements.json @ 2026-10-14 工作树快照（未跟踪目录）（evidence/rules/sources/allforai-visual-evidence-requirements.json）
- 来源 SRC50：.allforai/product-concept/decision-journal.json @ 2026-10-14 工作树快照（未跟踪目录）（evidence/rules/sources/allforai-product-concept-decision-journal.json）
- 来源 SRC51：ledger journeys[] 经用户 2026-10-14 读回确认（J2/J2-squeezed/J5/J5-squeezed）（evidence/rules/sources/journeys-confirmed.md）
- 来源 SRC52：用户本 run AskUserQuestion 原话，2026-10-14（evidence/rules/sources/user-confirmed-2026-10-14.md）
- 来源 SRC53：run visual/visual-baseline.json 待冻结稿（用户 2026-10-14 逐类确认）（evidence/rules/sources/visual-baseline-frozen-draft.json）
- 来源 SRC54：run visual/interaction-baseline.json 待冻结稿（用户 2026-10-14 确认）（evidence/rules/sources/interaction-baseline-frozen-draft.json）
- 比较 RULE-S34-01 / RULE-S34-06 / RULE-S34-14 / RULE-S13-12 / RULE-S38-07 / RULE-S54-03 / RULE-S24-10 / RULE-S25-09 / RULE-S25-17 / RULE-S25-29：findings — 候选冲突组：当前 README（@0d98e9e）与 2026-09-17 budget 改写同时适用于本机台面的重活并存行为；README 与 Phase 0 路线图未被 budget 文档列为改写对象（budget 只改写 R-arbiter-01/04/05/07）
- 比较 RULE-S12-07 / RULE-S11-10 / RULE-S11-14 / RULE-S8-03 / RULE-S8-08 / RULE-S7-07 / RULE-S1-11 / RULE-S13-08 / RULE-S4-09 / RULE-S3-08 / RULE-S25-17 / RULE-S25-18：findings — 候选冲突组：聊天模型已驻留且有媒体作业在跑时的台面聊天请求、网关请求与界面按钮可用性；release 维度：llm/gateway/e2e 为 2026-08-31，R-budget-17 为 2026-09-17
- 比较 RULE-S24-06 / RULE-S25-11 / RULE-S25-13 / RULE-S1-08 / RULE-S22-11 / RULE-S2-08：findings — 候选冲突组：加载模型/开启重活前的容量判定与内存警告；budget design 与 budget spec 同属 2026-09-17 预算子系统，ui/arbiter 为 2026-08-31
- 比较 RULE-S41-01 / RULE-S41-02 / RULE-S28-BSCOPE / RULE-S31-S00c / RULE-S25-09 / RULE-S25-15 / RULE-S25-22 / RULE-S24-11 / RULE-S27-D20：findings — 候选冲突组：开启重活时内存/预算不足的处置；硬件软限制记忆（2026-09-24/25）与 budget spec（2026-09-17）均适用于当前版本，平台均为 macOS 本机
- 比较 RULE-S1-07 / RULE-S2-07 / RULE-S20-10 / RULE-S40-24 / RULE-S25-29 / RULE-S25-18：findings — 候选冲突组：台面状态对象 deskState 的持有者表达；budget 改写后持有者可为一组，R-arbiter-06 声明不变
- 比较 RULE-S7-17 / RULE-S8-11：findings — 候选冲突组：gateway 模块验收方式（2026-08-31 同版本）
- 比较 RULE-S20-13 / RULE-S20-14 / RULE-S21-09 / RULE-S21-10：findings — 候选冲突组：shell 关窗不退、Quit 收割、服务死亡提示等窗口级行为的验收方式（2026-08-31）
- 比较 RULE-S34-02 / RULE-S16-11 / RULE-S17-11 / RULE-S8-01 / RULE-S13-08 / RULE-S34-11：findings — 候选冲突组：当前 README 文本（@0d98e9e）对推理与数据外流的陈述
- 比较 RULE-S13-05 / RULE-S13-12 / RULE-S17-01 / RULE-S36-09 / RULE-S34-10：findings — 候选冲突组：构建产物签名与分发流程；README 为当前版本，packaging/overview 为 Phase 0 冻结
- 比较 RULE-S5-20 / RULE-S16-02 / RULE-S34-13 / RULE-S36-05 / RULE-S36-07：findings — 候选冲突组：开发模式与打包的 Python 环境布局（macOS dev 与 bundle）
- 比较 RULE-S18-03 / RULE-S19-01 / RULE-S19-02 / RULE-S13-12 / RULE-S34-14 / RULE-S36-06 / RULE-S27-D03：findings — 候选冲突组：模型目录（catalog）的单点与条目范围；图片会话与 qwen-image 文档为后续版本
- 比较 RULE-S27-D00b / RULE-S27-TBR-9 / RULE-S47-BR-9 / RULE-S50-02 / RULE-S50-05 / RULE-S36-03 / RULE-S27-D44a / RULE-S27-D47a / RULE-S27-D47b / RULE-S28-B10：findings — 候选冲突组：图片页会话动作的生成方式；local-requirements 仍为 revision 1（confirmed），D-44a/D-47a 标注「2026-09-24 修订，用户确认」
- 比较 RULE-S36-02 / RULE-S36-10 / RULE-S27-D19 / RULE-S27-D66 / RULE-S27-D50：findings — 候选冲突组：图片生成的默认种子与界面说明；qwen-image 文档 @0d98e9e 与图片会话设计 2026-09-24
- 比较 RULE-S27-D86 / RULE-S27-DACTIONS / RULE-S48-attempt-failed / RULE-S48-attempt-cancelled / RULE-S48-attempt-file-missing / RULE-S27-D47a：findings — 候选冲突组：图片页失败/已取消/文件不在的尝试卡片（同一图片页、同一版本）
- 比较 RULE-S27-D74 / RULE-S27-D60 / RULE-S48-GSHOW / RULE-S39-13 / RULE-S53-17：findings — 候选冲突组：图片页按钮级别（同一页面、同一版本）
- 比较 RULE-S39-14 / RULE-S53-18 / RULE-S27-D70 / RULE-S29-M20：findings — 候选冲突组：会话列宽度；视觉基线（2026-10-14 用户确认稿）与图片/音乐会话设计
- 比较 RULE-S22-24 / RULE-S22-21 / RULE-S38-03 / RULE-S39-16 / RULE-S40-32 / RULE-S53-21 / RULE-S54-01：findings — 候选冲突组：主界面标签切换与地址栏 hash；ui 设计 2026-08-31，视觉候选 2026-09-16，修复计划 2026-09-11
- 比较 RULE-S22-21 / RULE-S32-L11 / RULE-S27-D63：findings — 候选冲突组：前端本机状态持久化；ui 设计 2026-08-31，素材库预览 2026-09-30
- 比较 RULE-S39-19 / RULE-S38-10 / RULE-S53-24 / RULE-S54-05 / RULE-S32-L44：findings — 候选冲突组：界面动效；视觉/交互基线（2026-10-14 用户确认稿，参考图含素材库预览弹层 vs-09）与素材库预览设计
- 比较 RULE-S14-04 / RULE-S33-Z00c / RULE-S33-Z41 / RULE-S33-Z04 / RULE-S28-B00d / RULE-S30-V00c：findings — 候选冲突组：H3 视频生成的内部预算数值
- 比较 RULE-S40-08 / RULE-S46-02 / RULE-S39-06 / RULE-S27-D70：findings — 候选冲突组：聊天消息列宽；修复计划 2026-09-11，用户更新 2026-09-15
- 比较 RULE-S40-09 / RULE-S39-23 / RULE-S53-11：findings — 候选冲突组：首运页内容列宽
- 比较 RULE-S22-09 / RULE-S20-11 / RULE-S40-26 / RULE-S40-27 / RULE-S40-10：findings — 候选冲突组：状态条与菜单栏的内存读数格式
- 比较 RULE-S15-05 / RULE-S14-01 / RULE-S28-B45 / RULE-S28-B38b / RULE-S31-S02 / RULE-S41-03：findings — 候选冲突组：只用 ffmpeg 的合成/配乐作业启动条件（2026-09-25/27 版本，R-media-05 未被改写）
- 比较 RULE-S14-17 / RULE-S3-03 / RULE-S27-D20 / RULE-S28-B32：findings — 候选冲突组：媒体作业启动前的模型完整度检查
- 比较 RULE-S9-05 / RULE-S9-02 / RULE-S10-02 / RULE-S27-D03 / RULE-S27-D30 / RULE-S32-L02：findings — 候选冲突组：素材库成品列表与历史条目的媒体种类
- 比较 RULE-S48-session-list-load-failed / RULE-S49-04 / RULE-S28-B21 / RULE-S28-B01：findings — 候选冲突组：图片会话视觉验收与取证（revision 1，status passed）与 2026-09-25 媒体会话底座
- 比较 RULE-S49-01 / RULE-S48-GSHOW / RULE-S47-AC-7 / RULE-S27-TAC-7 / RULE-S46-03 / RULE-S32-L53：findings — 候选冲突组：图片页视觉验收（AC-7）的截图证据来源
- 比较 RULE-S30-V50 / RULE-S27-D74 / RULE-S28-B71 / RULE-S29-M04 / RULE-S48-GNOT：findings — 候选冲突组：图片页展开卡片上的按钮集合；视频会话 3a（2026-09-27）对图片页的增量
- 比较 RULE-S42-01 / RULE-S42-02 / RULE-S25-02 / RULE-S6-03 / RULE-S5-10 / RULE-S9-09 / RULE-S16-07 / RULE-S6-05：findings — 候选冲突组：未发布前提下的兼容/收编类需求（当前版本）
- 比较 RULE-S38-05 / RULE-S39-17 / RULE-S54-02 / RULE-S53-22 / RULE-S51-J2 / RULE-S40-31：findings — 候选冲突组：聊天回答被停止/中断后的记录（同一聊天面板）
- 比较 RULE-S5-13 / RULE-S6-05 / RULE-S5-14：findings — 候选冲突组：收编既有权重 move 模式、源与目标同卷（2026-08-31 同版本）
- 比较 RULE-S26-15 / RULE-S9-08 / RULE-S10-06：findings — 候选冲突组：skill 选中状态的会话级持久化（skills 2026-09-23 与 library 会话存储 2026-08-31）
- 比较 RULE-S31-S13 / RULE-S31-S05 / RULE-S28-BWL / RULE-S28-B06 / RULE-S28-B13 / RULE-S28-B05：findings — 候选冲突组：视频配乐 3b 对媒体会话尝试记录的扩展
- 比较 RULE-S3-07 / RULE-S3-09 / RULE-S4-08 / RULE-S4-10 / RULE-S22-14 / RULE-S23-04 / RULE-S30-V20 / RULE-S30-V21 / RULE-S30-V61 / RULE-S30-VE2E：findings — 候选冲突组：视频面板/流程与素材库回填视频的验收；e2e 与 ui 为 2026-08-31，视频会话 2026-09-27
- 比较 RULE-S20-10 / RULE-S21-04 / RULE-S40-26：findings — 候选冲突组：菜单栏媒体作业状态文案
- 比较 RULE-S25-07 / RULE-S25-09 / RULE-S14-01 / RULE-S14-06 / RULE-S27-D00d / RULE-S28-B47：findings — 候选冲突组：多件媒体作业（视频+音乐、图片+视频）能否并行
- 比较 RULE-S25-14 / RULE-S25-19 / RULE-S25-15：findings — 候选冲突组：can_start_heavy 与 acquire_heavy 的一致性要求（同一 budget spec）
- 比较 RULE-S22-18 / RULE-S23-06 / RULE-S4-10 / RULE-S32-L00e / RULE-S32-L30：findings — 候选冲突组：素材库条目点击行为；ui/e2e 2026-08-31，素材库预览 2026-09-30
- 比较 RULE-S53-25 / RULE-S51-J2S / RULE-S51-J5S / RULE-S27-D78 / RULE-S48-VIEWPORTS / RULE-S29-M20 / RULE-S31-S35：findings — 候选冲突组：窄窗验收档位；2026-10-14 确认的视觉基线与旅程 vs 图片/音乐/配乐设计与图片会话视觉验收
- 比较 RULE-S53-09 / RULE-S52-03 / RULE-S27-D74 / RULE-S30-V32 / RULE-S29-M21 / RULE-S30-V21：findings — 候选冲突组：视频/音乐/图片页在最小窗口高度（600）下的结果卡片可见性
- 比较 RULE-S1-01 / RULE-S1-02 / RULE-S1-03 / RULE-S1-14 / RULE-S2-01 / RULE-S2-02 / RULE-S24-10 / RULE-S25-09 / RULE-S25-29：compatible — arbiter 互斥与 budget 改写：budget spec/design 以 supersedes 明确改写 R-arbiter-01/04/05/07（三态互斥、媒体在跑即拒绝、开媒体先全卸），属显式版本取代，不是同条件下的矛盾；驱逐过渡期快速拒绝在两版中均成立
- 比较 RULE-S1-10 / RULE-S1-15 / RULE-S14-03 / RULE-S2-05 / RULE-S2-06 / RULE-S2-08 / RULE-S24-12 / RULE-S25-15 / RULE-S25-22：compatible — 让出与拒绝：R-arbiter-04/05/07 原文已被 budget 显式改写（拒绝条件改为预算装不下、仅预算不足时最小让出、持续生效），收割失败即启动失败在新旧版本中一致
- 比较 RULE-S1-01 / RULE-S1-02 / RULE-S1-03 / RULE-S1-04 / RULE-S1-05 / RULE-S1-06 / RULE-S1-07 / RULE-S1-08 / RULE-S1-09 / RULE-S1-10 / RULE-S1-11 / RULE-S1-12 / RULE-S1-13 / RULE-S1-14 / RULE-S1-15 / RULE-S2-01 / RULE-S2-02 / RULE-S2-03 / RULE-S2-04 / RULE-S2-05 / RULE-S2-06 / RULE-S2-07 / RULE-S2-08：compatible — arbiter 模块内部：内存快照、按端口收割、token 化持有、事件派发等细则在 design 与 spec 间逐条一致；R-arbiter-02/03/06 被 budget 声明不变
- 比较 RULE-S24-01 / RULE-S24-02 / RULE-S24-03 / RULE-S24-04 / RULE-S24-05 / RULE-S24-06 / RULE-S24-07 / RULE-S24-08 / RULE-S24-09 / RULE-S24-10 / RULE-S24-11 / RULE-S24-12 / RULE-S24-13 / RULE-S24-14 / RULE-S24-15 / RULE-S24-16 / RULE-S24-17 / RULE-S24-18 / RULE-S24-19 / RULE-S25-01 / RULE-S25-02 / RULE-S25-03 / RULE-S25-04 / RULE-S25-05 / RULE-S25-06 / RULE-S25-07 / RULE-S25-08 / RULE-S25-09 / RULE-S25-10 / RULE-S25-11 / RULE-S25-12 / RULE-S25-13 / RULE-S25-14 / RULE-S25-15 / RULE-S25-16 / RULE-S25-17 / RULE-S25-18 / RULE-S25-19 / RULE-S25-20 / RULE-S25-21 / RULE-S25-22 / RULE-S25-23 / RULE-S25-24 / RULE-S25-25 / RULE-S25-26 / RULE-S25-27 / RULE-S25-28 / RULE-S25-29 / RULE-S25-30 / RULE-S25-31：findings — budget 模块内部：来源标注、声明窗口顺序、MLA 推算禁令、自校准与两个生效点、上下文压缩在 design 与 spec 间一致；R-budget-12/14/15 由 spec 显式作废；跨模块候选已在 RC1–RC4、RC39、RC40 单列；本组同时完整包含候选 RC40 的全部规则，其余规则兼容，候选见 findings
- 比较 RULE-S3-01 / RULE-S3-02 / RULE-S3-03 / RULE-S3-04 / RULE-S3-05 / RULE-S3-06 / RULE-S3-07 / RULE-S3-08 / RULE-S3-09 / RULE-S3-10 / RULE-S3-11 / RULE-S3-12 / RULE-S3-13 / RULE-S4-01 / RULE-S4-02 / RULE-S4-03 / RULE-S4-04 / RULE-S4-05 / RULE-S4-06 / RULE-S4-07 / RULE-S4-08 / RULE-S4-09 / RULE-S4-10 / RULE-S4-11 / RULE-S4-12 / RULE-S4-13 / RULE-S4-14：compatible — e2e 模块：测试态隔离（临时端口、假后端、不触真权重）与 12 条验收在 design 与 spec 一致；e2e 绑 127.0.0.1 是测试环境限定，0.0.0.0 归 gateway 自测，不与 R-gateway-07 冲突
- 比较 RULE-S5-01 / RULE-S5-02 / RULE-S5-03 / RULE-S5-04 / RULE-S5-05 / RULE-S5-06 / RULE-S5-07 / RULE-S5-08 / RULE-S5-09 / RULE-S5-10 / RULE-S5-11 / RULE-S5-12 / RULE-S5-13 / RULE-S5-14 / RULE-S5-15 / RULE-S5-16 / RULE-S5-17 / RULE-S5-18 / RULE-S5-19 / RULE-S5-20 / RULE-S6-01 / RULE-S6-02 / RULE-S6-03 / RULE-S6-04 / RULE-S6-05 / RULE-S6-06 / RULE-S6-07 / RULE-S6-08：findings — foundation 模块：路径单点、原子写、首运不回退、缺能力仍启动在 design 与 spec 一致；损坏配置报错与缺键补默认分属不同条件（损坏 vs 缺键），不冲突；本组同时完整包含候选 RC34 的全部规则，其余规则兼容，候选见 findings
- 比较 RULE-S7-01 / RULE-S7-02 / RULE-S7-03 / RULE-S7-04 / RULE-S7-05 / RULE-S7-06 / RULE-S7-07 / RULE-S7-08 / RULE-S7-09 / RULE-S7-10 / RULE-S7-11 / RULE-S7-12 / RULE-S7-13 / RULE-S7-14 / RULE-S7-15 / RULE-S7-16 / RULE-S7-17 / RULE-S7-18 / RULE-S7-19 / RULE-S7-20 / RULE-S7-21 / RULE-S8-01 / RULE-S8-02 / RULE-S8-03 / RULE-S8-04 / RULE-S8-05 / RULE-S8-06 / RULE-S8-07 / RULE-S8-08 / RULE-S8-09 / RULE-S8-10 / RULE-S8-11：findings — gateway 模块：方言形状、503 准入、错误信封、不自动加载在 design 与 spec 一致；测试绑 127.0.0.1 为测试环境限定；验收方式差异单列 RC6；本组同时完整包含候选 RC6 的全部规则，其余规则兼容，候选见 findings
- 比较 RULE-S10-01 / RULE-S10-02 / RULE-S10-03 / RULE-S10-04 / RULE-S10-05 / RULE-S10-06 / RULE-S10-07 / RULE-S9-01 / RULE-S9-02 / RULE-S9-03 / RULE-S9-04 / RULE-S9-05 / RULE-S9-06 / RULE-S9-07 / RULE-S9-08 / RULE-S9-09 / RULE-S9-10 / RULE-S9-11 / RULE-S9-12 / RULE-S9-13：compatible — library 模块：历史原子追加、Range、路径逃逸 404、会话 CRUD 与存储位置在 design 与 spec 一致
- 比较 RULE-S11-01 / RULE-S11-02 / RULE-S11-03 / RULE-S11-04 / RULE-S11-05 / RULE-S11-06 / RULE-S11-07 / RULE-S11-08 / RULE-S11-09 / RULE-S11-10 / RULE-S11-11 / RULE-S11-12 / RULE-S11-13 / RULE-S11-14 / RULE-S11-15 / RULE-S11-16 / RULE-S11-17 / RULE-S11-18 / RULE-S11-19 / RULE-S12-01 / RULE-S12-02 / RULE-S12-03 / RULE-S12-04 / RULE-S12-05 / RULE-S12-06 / RULE-S12-07 / RULE-S12-08 / RULE-S12-09：compatible — llm 模块：许可向 arbiter 申请、卸载以端口释放为准、reasoning 分离、失败带日志尾部在 design 与 spec 一致；reality gate 两处表述一致
- 比较 RULE-S13-01 / RULE-S13-02 / RULE-S13-03 / RULE-S13-04 / RULE-S13-05 / RULE-S13-06 / RULE-S13-07 / RULE-S13-08 / RULE-S13-09 / RULE-S13-10 / RULE-S13-11 / RULE-S13-12：compatible — Phase 0 总览：冻结决定与各模块 spec 逐项对应（自包含、收编、不自启、签名不公证、ES 模块、多会话、菜单栏+Dock、0.0.0.0 无鉴权、无模型 503）；后续版本冲突单列 RC1、RC9、RC11
- 比较 RULE-S14-01 / RULE-S14-02 / RULE-S14-03 / RULE-S14-04 / RULE-S14-05 / RULE-S14-06 / RULE-S14-07 / RULE-S14-08 / RULE-S14-09 / RULE-S14-10 / RULE-S14-11 / RULE-S14-12 / RULE-S14-13 / RULE-S14-14 / RULE-S14-15 / RULE-S14-16 / RULE-S14-17 / RULE-S15-01 / RULE-S15-02 / RULE-S15-03 / RULE-S15-04 / RULE-S15-05 / RULE-S15-06 / RULE-S15-07 / RULE-S15-08：compatible — media 模块：命令单点定义、启动顺序不 spawn、exit0 无文件判失败、取消优先在 design 与 spec 一致；后续会话版本的扩展（seed、continues、compose）由底座显式声明
- 比较 RULE-S16-01 / RULE-S16-02 / RULE-S16-03 / RULE-S16-04 / RULE-S16-05 / RULE-S16-06 / RULE-S16-07 / RULE-S16-08 / RULE-S16-09 / RULE-S16-10 / RULE-S16-11 / RULE-S16-12 / RULE-S16-13 / RULE-S16-14 / RULE-S16-15 / RULE-S16-16 / RULE-S17-01 / RULE-S17-02 / RULE-S17-03 / RULE-S17-04 / RULE-S17-05 / RULE-S17-06 / RULE-S17-07 / RULE-S17-08 / RULE-S17-09 / RULE-S17-10 / RULE-S17-11 / RULE-S17-12：compatible — packaging 模块：构建原子发布、内嵌运行时、由内向外签名、自包含扫描、卸载保护模型在 design 与 spec 一致；安装到真实 /Applications 只出现在人工 runbook 是验收环境限定，不与 R-packaging-06 冲突
- 比较 RULE-S18-01 / RULE-S18-02 / RULE-S18-03 / RULE-S18-04 / RULE-S18-05 / RULE-S18-06 / RULE-S18-07 / RULE-S18-08 / RULE-S18-09 / RULE-S18-10 / RULE-S18-11 / RULE-S18-12 / RULE-S18-13 / RULE-S18-14 / RULE-S18-15 / RULE-S18-16 / RULE-S18-17 / RULE-S19-01 / RULE-S19-02 / RULE-S19-03 / RULE-S19-04 / RULE-S19-05 / RULE-S19-06 / RULE-S19-07 / RULE-S19-08 / RULE-S19-09 / RULE-S19-10：compatible — resources 模块：目录单点、按字节完整度、unknown 降级、单飞下载、取消保留半成品、删除需 confirm=key 在 design 与 spec 一致；下载仅在媒体在跑时拒绝（LLM 驻留不拦）是对 R-resources-09「重活（媒体生成）」的同义细化
- 比较 RULE-S20-01 / RULE-S20-02 / RULE-S20-03 / RULE-S20-04 / RULE-S20-05 / RULE-S20-06 / RULE-S20-07 / RULE-S20-08 / RULE-S20-09 / RULE-S20-10 / RULE-S20-11 / RULE-S20-12 / RULE-S20-13 / RULE-S20-14 / RULE-S20-15 / RULE-S21-01 / RULE-S21-02 / RULE-S21-03 / RULE-S21-04 / RULE-S21-05 / RULE-S21-06 / RULE-S21-07 / RULE-S21-08 / RULE-S21-09 / RULE-S21-10：findings — shell 模块：内嵌运行时启动、关窗不退、退出收割、Dock 常规激活、不写登录项、首运原生面板、死亡提示在 design 与 spec 一致；验收方式差异单列 RC7；本组同时完整包含候选 RC7 的全部规则，其余规则兼容，候选见 findings
- 比较 RULE-S22-01 / RULE-S22-02 / RULE-S22-03 / RULE-S22-04 / RULE-S22-05 / RULE-S22-06 / RULE-S22-07 / RULE-S22-08 / RULE-S22-09 / RULE-S22-10 / RULE-S22-11 / RULE-S22-12 / RULE-S22-13 / RULE-S22-14 / RULE-S22-15 / RULE-S22-16 / RULE-S22-17 / RULE-S22-18 / RULE-S22-19 / RULE-S22-20 / RULE-S22-21 / RULE-S22-22 / RULE-S22-23 / RULE-S22-24 / RULE-S22-25 / RULE-S22-26 / RULE-S23-01 / RULE-S23-02 / RULE-S23-03 / RULE-S23-04 / RULE-S23-05 / RULE-S23-06 / RULE-S23-07 / RULE-S23-08 / RULE-S23-09：compatible — ui 模块：静态供给、api.js 单点、不直连 8767、错误原样、状态条真实内存、加载前警告、资源三态、首运与设置在 design 与 spec 一致；ui 的 DOM reality gate 与 e2e 自动验收（D-0001 后加）是补充关系，不是同条件下的矛盾
- 比较 RULE-S22-23 / RULE-S23-09 / RULE-S4-01 / RULE-S4-14：compatible — DOM 交互验收：ui spec 把 DOM 交互标 reality_gate（人工 runbook），e2e spec（D-0001，ui 模块保持原样）另增自动验收；二者叠加不互斥
- 比较 RULE-S26-01 / RULE-S26-02 / RULE-S26-03 / RULE-S26-04 / RULE-S26-05 / RULE-S26-06 / RULE-S26-07 / RULE-S26-08 / RULE-S26-09 / RULE-S26-10 / RULE-S26-11 / RULE-S26-12 / RULE-S26-13 / RULE-S26-14 / RULE-S26-15 / RULE-S26-16 / RULE-S26-17 / RULE-S26-18：compatible — skills 模块内部：不执行、原文注入、用户选中、system 置前不压缩、token 可见、坏 skill 列出、显式扫描、附件可见、安装先看全文与原子落盘；R-skill-12/13 与 R-context-01 的预算扣除方向一致；budget 非目标中的「不做 skill 机制」限定为 budget 本模块并注明另行立项，与 skills spec 不冲突
- 比较 RULE-S27-D00a / RULE-S27-D00b / RULE-S27-D00c / RULE-S27-D00d / RULE-S27-D00e / RULE-S27-D01 / RULE-S27-D02 / RULE-S27-D03 / RULE-S27-D04 / RULE-S27-D05 / RULE-S27-D06 / RULE-S27-D07 / RULE-S27-D08 / RULE-S27-D09 / RULE-S27-D10 / RULE-S27-D11 / RULE-S27-D12 / RULE-S27-D13 / RULE-S27-D14 / RULE-S27-D15 / RULE-S27-D16 / RULE-S27-D17 / RULE-S27-D18 / RULE-S27-D19 / RULE-S27-D20 / RULE-S27-D21 / RULE-S27-D22 / RULE-S27-D23 / RULE-S27-D24 / RULE-S27-D25 / RULE-S27-D26 / RULE-S27-D27 / RULE-S27-D30 / RULE-S27-D31 / RULE-S27-D40 / RULE-S27-D41 / RULE-S27-D42 / RULE-S27-D43 / RULE-S27-D44 / RULE-S27-D44a / RULE-S27-D45 / RULE-S27-D46 / RULE-S27-D47 / RULE-S27-D47a / RULE-S27-D47b / RULE-S27-D48 / RULE-S27-D49 / RULE-S27-D50 / RULE-S27-D50a / RULE-S27-D51 / RULE-S27-D60 / RULE-S27-D61 / RULE-S27-D62 / RULE-S27-D63 / RULE-S27-D64 / RULE-S27-D65 / RULE-S27-D66 / RULE-S27-D70 / RULE-S27-D71 / RULE-S27-D72 / RULE-S27-D73 / RULE-S27-D74 / RULE-S27-D75 / RULE-S27-D76 / RULE-S27-D77 / RULE-S27-D78 / RULE-S27-D80 / RULE-S27-D81 / RULE-S27-D82 / RULE-S27-D83 / RULE-S27-D84 / RULE-S27-D85 / RULE-S27-D86 / RULE-S27-D87 / RULE-S27-D88 / RULE-S27-D89 / RULE-S27-D90 / RULE-S27-D91 / RULE-S27-D92 / RULE-S27-D93 / RULE-S27-D94 / RULE-S27-D95 / RULE-S27-DACTIONS / RULE-S27-DBUSY / RULE-S27-DCONC / RULE-S27-DLIST4 / RULE-S27-DNEWBODY / RULE-S27-TAC-1 / RULE-S27-TAC-2 / RULE-S27-TAC-3 / RULE-S27-TAC-4 / RULE-S27-TAC-5 / RULE-S27-TAC-6 / RULE-S27-TAC-7 / RULE-S27-TBR-1 / RULE-S27-TBR-2 / RULE-S27-TBR-3 / RULE-S27-TBR-4 / RULE-S27-TBR-5 / RULE-S27-TBR-6 / RULE-S27-TBR-7 / RULE-S27-TBR-8 / RULE-S27-TBR-9：compatible — 图片会话设计内部其余条目：存储、标题、校验顺序、落定、删除语义、两个动作、种子文案范围（D-50a 为显式例外，限图片页）、布局与状态；D-62 首次自动新建附明确理由说明仍满足 BR-4 手动新建；跨源候选单列 RC12–RC16、RC29–RC31
- 比较 RULE-S27-D60 / RULE-S27-D61 / RULE-S27-D62 / RULE-S27-TBR-4 / RULE-S47-BR-4：compatible — 手动新建与首次自动新建：D-62 写明理由（与聊天页一致、空会话无代价、生成从不暗中另开会话），属于 BR-4 的显式解释例外，适用条件（首次进入且无会话）与「之后每个新分组由用户点新会话产生」不重叠
- 比较 RULE-S27-D50 / RULE-S27-D50a / RULE-S47-BR-7 / RULE-S48-GNOT：compatible — 种子文案范围：D-50a 为用户 2026-09-24 决定的显式例外，限定素材库页可显示「种子 N」，D-50 与视觉全局规则只适用于图片页，范围不重叠
- 比较 RULE-S27-D01 / RULE-S27-D16 / RULE-S28-B01 / RULE-S28-B02 / RULE-S28-B21：compatible — 图片会话存储迁移：底座 B-01/B-21 明确「取代 image_sessions_dir」「不再有 /api/image-sessions」，属显式取代（已记 supersedes）
- 比较 RULE-S27-D00a / RULE-S28-B73 / RULE-S28-BSID / RULE-S29-M00a / RULE-S29-M50 / RULE-S30-V01 / RULE-S47-BR-1：compatible — 分步上线：底座写明 video/music session_id 本块可省略、第 2/3 块各自改为必填；M-50/V-01 照此改为必填（已记 supersedes）；BR-1「只改图片页」限定 image-sessions 需求本身，后续块是新需求
- 比较 RULE-S28-B00a / RULE-S28-B00b / RULE-S28-B00c / RULE-S28-B00d / RULE-S28-B01 / RULE-S28-B02 / RULE-S28-B03 / RULE-S28-B04 / RULE-S28-B05 / RULE-S28-B06 / RULE-S28-B07 / RULE-S28-B08 / RULE-S28-B09 / RULE-S28-B10 / RULE-S28-B11 / RULE-S28-B12 / RULE-S28-B13 / RULE-S28-B20 / RULE-S28-B21 / RULE-S28-B22 / RULE-S28-B27 / RULE-S28-B28 / RULE-S28-B30 / RULE-S28-B31 / RULE-S28-B32 / RULE-S28-B33 / RULE-S28-B34 / RULE-S28-B35 / RULE-S28-B36 / RULE-S28-B37 / RULE-S28-B38 / RULE-S28-B38a / RULE-S28-B38b / RULE-S28-B39 / RULE-S28-B40 / RULE-S28-B41 / RULE-S28-B42 / RULE-S28-B43 / RULE-S28-B44 / RULE-S28-B45 / RULE-S28-B46 / RULE-S28-B47 / RULE-S28-B48 / RULE-S28-B50 / RULE-S28-B51 / RULE-S28-B52 / RULE-S28-B55 / RULE-S28-B56 / RULE-S28-B57 / RULE-S28-B58 / RULE-S28-B60 / RULE-S28-B61 / RULE-S28-B62 / RULE-S28-B70 / RULE-S28-B71 / RULE-S28-B72 / RULE-S28-B73 / RULE-S28-B74 / RULE-S28-B75 / RULE-S28-BCONT / RULE-S28-BE2E / RULE-S28-BNOLEG / RULE-S28-BRA / RULE-S28-BSCOPE / RULE-S28-BSEED / RULE-S28-BSID / RULE-S28-BWL：compatible — 媒体会话底座内部：白名单、续写链、作业内拼接与许可释放时机、手动合成、拼接规则、引用、ffmpeg 原语、前端重构在文中自洽；与第 2、3 块的衔接条款（B-70 移到第 2 块、B-75 给下游约束）由下游设计逐条承接
- 比较 RULE-S29-M00a / RULE-S29-M00b / RULE-S29-M00c / RULE-S29-M00d / RULE-S29-M01 / RULE-S29-M02 / RULE-S29-M03 / RULE-S29-M04 / RULE-S29-M05 / RULE-S29-M06 / RULE-S29-M07 / RULE-S29-M08 / RULE-S29-M09 / RULE-S29-M10 / RULE-S29-M11 / RULE-S29-M20 / RULE-S29-M21 / RULE-S29-M22 / RULE-S29-M23 / RULE-S29-M24 / RULE-S29-M25 / RULE-S29-M26 / RULE-S29-M27 / RULE-S29-M28 / RULE-S29-M30 / RULE-S29-M31 / RULE-S29-M32 / RULE-S29-M33 / RULE-S29-M34 / RULE-S29-M35 / RULE-S29-M36 / RULE-S29-M40 / RULE-S29-M41 / RULE-S29-M42 / RULE-S29-M50 / RULE-S29-M51 / RULE-S29-M52 / RULE-S29-M53 / RULE-S29-ME2E / RULE-S29-MSCOPE：compatible — 音乐会话内部：共用控制器职责、挑选合成、输入区、提示条、卡片、三个动作、重新拼接、接通与回填在文中自洽；M-11 界面不允许重复选段是对 B-44 后端允许的显式收窄
- 比较 RULE-S29-M30 / RULE-S29-M32 / RULE-S30-V10：compatible — 音乐卡片文件不在文案：V-10 明确把音乐卡片「文件已不在」改为「音频文件已不在」，属显式取代（已记 supersedes）
- 比较 RULE-S30-V00a / RULE-S30-V00b / RULE-S30-V00c / RULE-S30-V01 / RULE-S30-V02 / RULE-S30-V03 / RULE-S30-V04 / RULE-S30-V05 / RULE-S30-V10 / RULE-S30-V11 / RULE-S30-V20 / RULE-S30-V21 / RULE-S30-V22 / RULE-S30-V23 / RULE-S30-V24 / RULE-S30-V25 / RULE-S30-V30 / RULE-S30-V31 / RULE-S30-V32 / RULE-S30-V33 / RULE-S30-V34 / RULE-S30-V40 / RULE-S30-V41 / RULE-S30-V42 / RULE-S30-V43 / RULE-S30-V50 / RULE-S30-V51 / RULE-S30-V60 / RULE-S30-V61 / RULE-S30-VE2E / RULE-S30-VSCOPE：compatible — 视频会话内部：session 必填、first_frame 引用槽与冲突规则、三个动作、用这张生成视频的跨页通信、jobview 清除在文中自洽；V-00b 尾帧/参考视频来源限制与 V-22 一致
- 比较 RULE-S30-V21 / RULE-S30-V31 / RULE-S33-Z11 / RULE-S33-Z12 / RULE-S33-Z15：compatible — 画幅控件：视频画幅设计明确是对视频页「三档横屏」的扩展重做（方向×三档+自定义），默认仍为 512×288，与 V-21「画幅（现有三档）」是显式后续版本关系
- 比较 RULE-S31-S00a / RULE-S31-S00b / RULE-S31-S00c / RULE-S31-S01 / RULE-S31-S02 / RULE-S31-S03 / RULE-S31-S04 / RULE-S31-S05 / RULE-S31-S06 / RULE-S31-S07 / RULE-S31-S10 / RULE-S31-S11 / RULE-S31-S12 / RULE-S31-S13 / RULE-S31-S14 / RULE-S31-S20 / RULE-S31-S21 / RULE-S31-S30 / RULE-S31-S31 / RULE-S31-S32 / RULE-S31-S33 / RULE-S31-S34 / RULE-S31-S35：compatible — 视频配乐内部：soundtrack 接口校验顺序、命令替换 replace_audio（S-04 显式取代，已记 supersedes）、music_ref 冲突与截取、通用选择框、界面在文中自洽；不新增内存硬拒绝与硬件软限制一致
- 比较 RULE-S32-L00a / RULE-S32-L00b / RULE-S32-L00c / RULE-S32-L00d / RULE-S32-L00e / RULE-S32-L00f / RULE-S32-L01 / RULE-S32-L02 / RULE-S32-L03 / RULE-S32-L04 / RULE-S32-L05 / RULE-S32-L06 / RULE-S32-L10 / RULE-S32-L11 / RULE-S32-L12 / RULE-S32-L20 / RULE-S32-L21 / RULE-S32-L22 / RULE-S32-L23 / RULE-S32-L24 / RULE-S32-L25 / RULE-S32-L26 / RULE-S32-L27 / RULE-S32-L28 / RULE-S32-L30 / RULE-S32-L31 / RULE-S32-L32 / RULE-S32-L33 / RULE-S32-L40 / RULE-S32-L41 / RULE-S32-L42 / RULE-S32-L43 / RULE-S32-L44 / RULE-S32-L45 / RULE-S32-L50 / RULE-S32-L51 / RULE-S32-L52 / RULE-S32-L53 / RULE-S32-LDONE / RULE-S32-LSCOPE：compatible — 素材库预览内部：条目模型、筛选排序、三视图、选中与键盘、预览弹层、离开停声、测试迁移在文中自洽；取消顶部播放区为显式取代（已记 supersedes）
- 比较 RULE-S33-Z00a / RULE-S33-Z00b / RULE-S33-Z00c / RULE-S33-Z00d / RULE-S33-Z01 / RULE-S33-Z02 / RULE-S33-Z03 / RULE-S33-Z04 / RULE-S33-Z10 / RULE-S33-Z11 / RULE-S33-Z12 / RULE-S33-Z13 / RULE-S33-Z14 / RULE-S33-Z15 / RULE-S33-Z20 / RULE-S33-Z21 / RULE-S33-Z22 / RULE-S33-Z23 / RULE-S33-Z24 / RULE-S33-Z25 / RULE-S33-Z26 / RULE-S33-Z30 / RULE-S33-Z31 / RULE-S33-Z32 / RULE-S33-Z40 / RULE-S33-Z41 / RULE-S33-Z42 / RULE-S33-Z43 / RULE-S33-Z50 / RULE-S33-Z51 / RULE-S33-Z52 / RULE-S33-Z53 / RULE-S33-ZSCOPE：compatible — 视频画幅内部：前后端同一套尺寸规则、违规文案顺序、方向档位、首帧跟随与不跟随条件、续写锁定、只提醒不拦在文中自洽；只提醒不拦与硬件软限制一致
- 比较 RULE-S34-01 / RULE-S34-02 / RULE-S34-03 / RULE-S34-04 / RULE-S34-05 / RULE-S34-06 / RULE-S34-07 / RULE-S34-08 / RULE-S34-09 / RULE-S34-10 / RULE-S34-11 / RULE-S34-12 / RULE-S34-13 / RULE-S34-14：compatible — README 其余条目（本机对话、文生视频/歌曲、模型齐全、成品回填、安装卸载、安装后行为、adhoc 签名）与各模块 spec 一致；冲突单列 RC1、RC8–RC11
- 比较 RULE-S35-01 / RULE-S35-02 / RULE-S35-03 / RULE-S35-04 / RULE-S43-01 / RULE-S43-02：compatible — DeepSeek V4：ADR 与用户记忆一致（暂不收录、ds4 已撤回、mlx-lm 支持后以新目录项接入）；复议条件是条件句，不承诺条件可达
- 比较 RULE-S36-01 / RULE-S36-02 / RULE-S36-03 / RULE-S36-04 / RULE-S36-05 / RULE-S36-06 / RULE-S36-07 / RULE-S36-08 / RULE-S36-09 / RULE-S36-10 / RULE-S36-11 / RULE-S36-12 / RULE-S36-13：compatible — qwen-image 文档其余条目：权重来源、离线命令未接仲裁的提示、MLX 接入判据、最终产物验收与 packaging 自包含/签名要求一致；冲突单列 RC10、RC11、RC13
- 比较 RULE-S37-01 / RULE-S37-02 / RULE-S37-03 / RULE-S37-04 / RULE-S37-05 / RULE-S37-06 / RULE-S39-00 / RULE-S39-22：compatible — 视觉基线流程：候选不能当基线、确认后绑定 SHA-256、探针取证纪律在 README 与候选文件中一致；候选规则的 condition 均为「未经用户确认」，与已确认规则比较时只产出待澄清
- 比较 RULE-S38-01 / RULE-S38-02 / RULE-S38-03 / RULE-S38-04 / RULE-S38-05 / RULE-S38-06 / RULE-S38-07 / RULE-S38-08 / RULE-S38-09 / RULE-S38-10：compatible — 交互候选其余条目（Tab 遍历、⌘, 设置、访达中显示、长耗时可取消、危险动作确认焦点）与 ui/图片会话设计一致（如 D-90 默认焦点在取消）；冲突单列 RC1、RC18、RC20、RC33
- 比较 RULE-S39-00 / RULE-S39-01 / RULE-S39-02 / RULE-S39-03 / RULE-S39-04 / RULE-S39-05 / RULE-S39-06 / RULE-S39-07 / RULE-S39-08 / RULE-S39-09 / RULE-S39-10 / RULE-S39-11 / RULE-S39-12 / RULE-S39-13 / RULE-S39-14 / RULE-S39-15 / RULE-S39-16 / RULE-S39-17 / RULE-S39-18 / RULE-S39-19 / RULE-S39-20 / RULE-S39-21 / RULE-S39-22 / RULE-S39-23：compatible — 视觉候选其余条目（方向、配色、字体、间距、图标、按钮四级、K2 消息、反馈、焦点、深色环境）与 ui 设计「单一深色主题」、视觉方向记忆一致；按钮「安静」级是对记忆中主/次/危险三级的补充，候选待确认；已于 2026-10-14 被确认稿取代（supersedes）；冲突单列 RC15、RC16、RC20、RC24
- 比较 RULE-S40-01 / RULE-S40-02 / RULE-S40-03 / RULE-S40-04 / RULE-S40-05 / RULE-S40-06 / RULE-S40-07 / RULE-S40-08 / RULE-S40-09 / RULE-S40-10 / RULE-S40-11 / RULE-S40-12 / RULE-S40-13 / RULE-S40-14 / RULE-S40-15 / RULE-S40-16 / RULE-S40-17 / RULE-S40-18 / RULE-S40-19 / RULE-S40-20 / RULE-S40-21 / RULE-S40-22 / RULE-S40-23 / RULE-S40-24 / RULE-S40-25 / RULE-S40-26 / RULE-S40-27 / RULE-S40-28 / RULE-S40-29 / RULE-S40-30 / RULE-S40-31 / RULE-S40-32 / RULE-S40-33 / RULE-S40-34：compatible — 视觉修复计划其余任务（不用 innerHTML、token 色、间距基数、思考折叠两态、错误卡片统一、会话卡片动作列、驱逐后下拉框）与 ui 设计和视觉候选一致；K2 两态文案与候选 K2 逐字一致；冲突单列 RC23–RC25、RC33、RC38
- 比较 RULE-S41-01 / RULE-S41-02 / RULE-S41-03：compatible — 硬件软限制：与媒体会话底座「只提醒可确认、不新增硬拒绝、不设链长上限」、配乐 S-00c、画幅 Z-00c 一致；与 budget 拒绝的关系单列 RC4
- 比较 RULE-S42-01 / RULE-S42-02：compatible — 未发布前提：与 budget spec「不存在需要兼容的存量行为」、各会话设计「不谈兼容」一致；与 2026-08-31 兼容/收编条款的关系单列 RC32
- 比较 RULE-S27-D44a / RULE-S27-D47b / RULE-S44-01 / RULE-S44-02：compatible — 以图生图排期记忆（先 spike 再立项、设想入口为选一张作底稿+变化幅度）与 D-44a/D-47b 的实现相容：变化幅度落为两档固定强度；设想入口不是强制规则
- 比较 RULE-S45-01 / RULE-S45-02：compatible — 媒体会话计划记忆与底座 §0.1/§0.3 的用户决定与 spike 事实逐条一致
- 比较 RULE-S46-01 / RULE-S46-02 / RULE-S46-03 / RULE-S46-04：compatible — 视觉方向记忆与视觉候选的 K2 消息、按钮级别、消息列宽 min(区宽−48,1400) 一致；与修复计划旧列宽、Chromium 证据的关系单列 RC23、RC30
- 比较 RULE-S47-AC-1 / RULE-S47-AC-2 / RULE-S47-AC-3 / RULE-S47-AC-4 / RULE-S47-AC-5 / RULE-S47-AC-6 / RULE-S47-AC-7 / RULE-S47-BR-1 / RULE-S47-BR-2 / RULE-S47-BR-3 / RULE-S47-BR-4 / RULE-S47-BR-5 / RULE-S47-BR-6 / RULE-S47-BR-7 / RULE-S47-BR-8 / RULE-S47-BR-9 / RULE-S47-STATUS / RULE-S50-01 / RULE-S50-02 / RULE-S50-03 / RULE-S50-04 / RULE-S50-05：compatible — image-sessions 需求（revision 1）与 decision-journal 中的业务规则、验收、冻结范围逐字一致；与以图生图修订的关系单列 RC12
- 比较 RULE-S48-GNOT / RULE-S48-GSHOW / RULE-S48-STATUS / RULE-S48-VIEWPORTS / RULE-S48-attempt-cancelled / RULE-S48-attempt-failed / RULE-S48-attempt-file-missing / RULE-S48-attempt-interrupted / RULE-S48-attempt-selected-actions / RULE-S48-busy-other-media / RULE-S48-corrupt-session / RULE-S48-delete-confirm / RULE-S48-delete-confirm-running / RULE-S48-empty-session / RULE-S48-first-entry-auto-session / RULE-S48-library-after-delete / RULE-S48-model-missing / RULE-S48-refine-prefill / RULE-S48-rename / RULE-S48-running / RULE-S48-running-other-session / RULE-S48-runtime-unavailable / RULE-S48-session-list-load-failed / RULE-S48-timeline-three-rounds：compatible — 图片会话视觉验收各状态与 D-xx 设计条目一一对应（自动新建、空会话、生成中、别的会话在生成、三轮、失败/取消/中断/文件不在、模型/运行环境/忙碌、改名、删除、损坏）；冲突单列 RC14、RC15、RC29、RC31
- 比较 RULE-S27-D70 / RULE-S28-B73 / RULE-S29-M20 / RULE-S30-V20 / RULE-S39-08 / RULE-S52-03 / RULE-S53-09：compatible — 视频/音乐页布局：第 1 轮 RC17（候选左表单右任务 vs 会话式）由 2026-10-14 确认稿第 5 条「照实际+高度规则」取代候选，确认稿上下排布与会话式布局一致
- 比较 RULE-S37-06 / RULE-S39-01 / RULE-S39-21 / RULE-S46-02 / RULE-S52-02 / RULE-S53-01 / RULE-S53-07：compatible — 宽度范围：第 1 轮 RC21（900–1920 vs 2560）由用户 2026-10-14「900–2560（推荐）」与确认稿 width_range 取代候选值，与视觉方向记忆 2560 留白上限一致
- 比较 RULE-S51-00 / RULE-S51-J2 / RULE-S51-J2S / RULE-S51-J5 / RULE-S51-J5S：compatible — 旅程声明：J2/J5 及挤压版的完成与卡住判据与聊天会话持久化、停止、竖屏档位（Z-11）、视频会话要求一致；聊天模型可能已加载是前置状态，不承诺并存或驱逐中的哪一种；与最小高度、停止持久化的关系单列 RC33、RC42
- 比较 RULE-S52-01 / RULE-S52-02 / RULE-S52-03 / RULE-S52-04 / RULE-S52-05：compatible — 用户本 run 决定：截图用临时数据根与合成会话、宽度 900–2560、只验鼠标与 100% 字号、媒体页上下排布、上滚不再跟随，均被确认稿逐条吸收；上滚不再跟随与共用控制器「用户滚动后不拽」（M-01）一致
- 比较 RULE-S53-00 / RULE-S53-01 / RULE-S53-02 / RULE-S53-03 / RULE-S53-04 / RULE-S53-05 / RULE-S53-06 / RULE-S53-07 / RULE-S53-08 / RULE-S53-09 / RULE-S53-10 / RULE-S53-11 / RULE-S53-12 / RULE-S53-13 / RULE-S53-14 / RULE-S53-15 / RULE-S53-16 / RULE-S53-17 / RULE-S53-18 / RULE-S53-19 / RULE-S53-20 / RULE-S53-21 / RULE-S53-22 / RULE-S53-23 / RULE-S53-24 / RULE-S53-25：compatible — 视觉基线确认稿：由候选经用户逐类确认（已记 supersedes），与 ui 单一深色主题、视觉方向记忆一致；冲突单列 RC15、RC16、RC18、RC20、RC24、RC33、RC42、RC43
- 比较 RULE-S54-00 / RULE-S54-01 / RULE-S54-02 / RULE-S54-03 / RULE-S54-04 / RULE-S54-05：compatible — 交互基线确认稿：由候选经用户确认（已记 supersedes），危险动作默认焦点与 D-90 一致，上滚不跟随与 M-01 一致；冲突单列 RC1、RC18、RC20、RC33
- 比较 RULE-S49-01 / RULE-S49-02 / RULE-S49-03 / RULE-S49-04 / RULE-S49-05：compatible — 取证要求与视觉验收状态清单一一对应，DOM 断言与全局禁止项一致；证据来源与接口路径问题单列 RC29、RC30

### RC1 · version_conflict · 已澄清
共同条件：当前 README（@0d98e9e）与 2026-09-17 budget 改写同时适用于本机台面的重活并存行为；README 与 Phase 0 路线图未被 budget 文档列为改写对象（budget 只改写 R-arbiter-01/04/05/07）
README 与交互基线（候选，且已于 2026-10-14 经用户确认进待冻结稿）仍写「同一时刻只干一件重活」/「同一时刻只有一个模型持有内存」「聊天、视频、音乐不能同时驻留」「出片期间不能再加载聊天模型」，Phase 0 路线图把「70B 与 H3 同时驻留」列为本轮不做；budget spec/design 则规定并存由预算判定、预算足够时聊天与媒体共存、预算不足才退化为互斥
待确认：README「同一时刻只干一件重活」与交互候选「同一时刻只有一个模型持有内存」是否仍是产品承诺？若 budget 改写为准，README/路线图/候选规则中的互斥表述是否视为被取代？
- RULE-S34-01 SRC34:3-5 · release=README @ 0d98e9e（当前） / platform=unknown / role=all / condition=all
> 一台 Mac 上既要本地聊天，又要出视频、出歌。这几类模型都很大，统一内存里装不下两份。这个项目要解决的是：把它们收成一张日常能用的工作台，并且保证同一时刻只有一件重活占着机器。
> 
> 不上云。不为多人排队。不是通用模型市场。
- RULE-S34-06 SRC34:44-47 · release=README @ 0d98e9e（当前） / platform=unknown / role=all / condition=all
> - 聊天模型、视频生成、音乐生成不能同时驻留
> - 出视频或出歌前，自动让出内存
> - 出片期间不能再加载聊天模型，也不能开下一个生成任务
> - 台面上随时能看出：内存里是谁、媒体是否在跑、现在能不能开下一件
- RULE-S34-14 SRC34:108-110 · release=README @ 0d98e9e（当前） / platform=unknown / role=all / condition=all
> - 不把请求发到云端，也不给多人共用
> - 不收录任意模型，只服务这张台上选定的聊天、视频、音乐能力
> - 不追求 70B 对话和视频生成同时驻留
- RULE-S13-12 SRC13:115-121 · release=2026-08-31 首版模块化（Phase 0 冻结） / platform=unknown / role=all / condition=all
> ## Roadmap（本轮明确不做）
> 
> - 公证（notarize）与对外分发：需要 App Store Connect 凭据，人类已选择跳过。
> - 对外接口的令牌鉴权与 TLS。
> - 任意 HF 仓库的自由添加（目录仍是选定的 8 项）。
> - 多人排队、云端推理。
> - 70B 与 H3 同时驻留。
- RULE-S38-07 SRC38:33-33 · release=docs/visual @ 0d98e9e（候选 2026-09-16） / platform=unknown / role=all / condition=候选规则，未经用户确认
>         "同一时刻只有一个模型持有内存：切换模型时先驱逐再加载，界面显示谁被驱逐、为什么。",
- RULE-S54-03 SRC54:33-35 · release=interaction-baseline 待冻结稿（用户 2026-10-14 确认） / platform=unknown / role=all / condition=all
>     "同一时刻只有一个模型持有内存：切换模型时先驱逐再加载，界面显示谁被驱逐、为什么。",
>     "服务不可达时状态条转危险色并给出可操作的下一步（重试 / 看日志），不只是报错文本。",
>     "输入为空或模型未就绪时发送按钮禁用，且禁用原因写在旁边，不靠猜。"
- RULE-S24-10 SRC24:193-201 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> 本项目尚未发布，不存在存量行为需要兼容，因此不做「降级迁移」，直接按预算写。
> 
> | 现状 | 改为 |
> |---|---|
> | R-arbiter-01 三者互斥，持有者唯一 | 重活能否并存由预算判定；预算不足时结果即互斥。持有者从单个变为一组 |
> | R-arbiter-04 媒体在跑即拒绝加载 LLM | 拒绝条件改为 `fits()` 判否，理由码带数字（需要多少 / 现有多少 / 依据来源） |
> | R-arbiter-05 开媒体前自动卸 LLM | 仅在预算不足时让出，且最小让出（卸最省的那个，非全卸） |
> | R-arbiter-07 加载前比对一次体积 | 持续生效：会话中 KV 增长同样在预算内被监控 |
> | R-arbiter-02 / 03 / 06 | 不动 |
- RULE-S25-09 SRC25:51-54 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-budget-07** 重活能否并存由预算判定，预算不足时结果即互斥。
>   判定的输入是**一组**重活而非一对：`fits(workloads)`。三件能否共存不等于
>   三个两两判断的合取，「最小让出」也只有在集合上才算得出来。
>   拒绝必须带机器可读原因与数字：需要多少、现有多少、依据来源为预测还是实测。
- RULE-S25-17 SRC25:115-126 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-budget-17** 「能不能用这个模型」问的是**台面还持不持有它**，不是「有没有媒体作业在跑」。
> 
>   互斥时代这两个问题同义，所以处处写成后者。预算取代互斥之后它们分开了：媒体
>   与聊天可以共存，而共存的安全性在**授予那一刻**就算过了——`cost("llm")` 报的
>   `bytes_needed` 就是权重加满窗 KV，`fits()` 拿它跟媒体一起判。媒体作业能开，
>   恰恰证明「聊天用满窗口 + 媒体」一起装得下。真机实测（2026-09-22，M5 Max）：
>   聊天 80.1 GiB + 视频 27.0 GiB = 107.1 GiB ≤ 能力 107.5 GiB。
> 
>   所以在这之后再按 `media_busy` 拦一道，拦掉的是已经付过代价的能力：共存只剩
>   「省一次加载」，兑现不了「边渲染边聊」。曾有四处这样拦着——台面聊天、网关守卫、
>   提示词助手的可用性、断流原因的归因。
- RULE-S25-29 SRC25:188-192 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-arbiter-01** 改：重活能否并存由预算判定；预算不足时退化为互斥。持有者由单个变为一组。
> - **R-arbiter-04** 改：拒绝条件由「媒体在跑」变为「预算装不下」。
> - **R-arbiter-05** 改：仅在预算不足时让出，且最小让出。
> - **R-arbiter-07** 改：由加载时一次性检查，变为持续生效。
> - **R-arbiter-02 / 03 / 06** 不变。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：重活能否并存由预算判定（budget-spec 取代 README/路线图的「同一时刻只干一件重活」）；交互基线「同一时刻只有一个模型持有内存」改读为「预算装不下时先驱逐再加载，界面显示谁被驱逐、为什么」

### RC2 · version_conflict · 已澄清
共同条件：聊天模型已驻留且有媒体作业在跑时的台面聊天请求、网关请求与界面按钮可用性；release 维度：llm/gateway/e2e 为 2026-08-31，R-budget-17 为 2026-09-17
R-llm-06、R-gateway-08 及其设计要求「媒体作业进行中」即拒绝聊天/返回 503，e2e 要求媒体运行中加载按钮禁用；R-budget-17 明确说「能不能用这个模型」问的是台面是否仍持有它，再按 media_busy 拦一道是错误（点名台面聊天、网关守卫），但 budget spec 的改写清单只列 R-arbiter-01/04/05/07，未声明改写 R-llm-06 / R-gateway-08 / R-e2e-08
待确认：R-llm-06、R-gateway-08、R-e2e-08 中「媒体作业进行中即拒绝」是否已被 R-budget-17 取代？若取代，网关 503 原因码 media_job_running 与 e2e 互斥断言应以什么条件为准（still_holds 还是 media_busy）？
- RULE-S12-07 SRC12:20-20 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=媒体作业进行中或无模型
> - **R-llm-06** 媒体作业进行中、或当前没有加载模型时，聊天请求被拒绝并带明确原因，不得挂起等待。
- RULE-S11-10 SRC11:211-216 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=聊天请求
> 前置检查（两个 API 相同，同步、立即，**绝不等待**——R-llm-06）：
> 
> 1. `arbiter.desk_state()` 报媒体作业运行中 → 拒绝 `media_busy`。
> 2. `status != "loaded"` → 拒绝 `no_model_loaded`。
> 3. `request.model` 非空且既不等于当前 key、也不等于 `served_id` → 拒绝 `model_mismatch`
>    （gateway R-gateway-10 依赖这条：不静默换模型）。
- RULE-S11-14 SRC11:241-245 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> | POST | `/api/llm/load`（body `{key}`） | `202 {state}`（进入 loading） | `409 {error:{code,message}}`（media_busy / load_in_progress）、`404`（model_not_found / model_dir_missing） |
> | POST | `/api/llm/unload` | `200 {state}` | `409 {error:{code:"load_in_progress",...}}`（loading 中）、`500 {error:{code:"port_not_released",...}}` |
> | GET | `/api/llm/status` | `200 {state, loaded_model}` | — |
> | POST | `/api/llm/chat` | `200 {content, reasoning, usage, finish_reason, model}` | `409`（media_busy / model_mismatch）、`503 {error:{code:"no_model_loaded",...}}` |
> | POST | `/api/llm/chat/stream` | `200 text/event-stream` | 同上（前置拒绝发生在发头之前，用普通 JSON 状态码） |
- RULE-S8-03 SRC8:14-14 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=无模型驻留或媒体作业在跑
> **不自动加载模型**：外部请求到达时若没有模型驻留、或媒体作业在跑，一律报错，不抢内存、不排队。
- RULE-S8-08 SRC8:28-29 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=无模型驻留或媒体作业进行中
> - **R-gateway-08** 无模型驻留或媒体作业进行中：返回 `503`，带 `Retry-After` 头与机器可读原因码。
>   **绝不自动加载模型，绝不排队等待。**
- RULE-S7-07 SRC7:162-168 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> | 判定顺序 | 条件 | 结果 |
> |---|---|---|
> | 1 | `desk_state()["media_busy"]`（即 holder 非空且 `holder["kind"] ∈ {video, music}`） | 503 `media_job_running`（原因码取 `can_start_heavy("llm")` 返回的 `reason["code"]`（arbiter 原因），保持全台面同一套词汇；取不到时用本地常量 `media_job_running` 兜底） |
> | 2 | `llm_status().state != "loaded"` | 503 `no_model_loaded` |
> | 3 | `requested_model` 非空 且 不等于 `loaded.key` 且 不等于 `loaded.served_id` | 503 `model_not_loaded`，message 指明当前驻留的是谁（R-gateway-10：不静默换模型） |
> | 4 | 通过 | 返回 `loaded`（后续调用一律用 `loaded.served_id` 作下游 model） |
- RULE-S1-11 SRC1:292-293 · release=2026-08-31 首版模块化（arbiter/foundation 等） / platform=unknown / role=all / condition=all
> - gateway：读 `data:deskState`（`media_busy` 或无模型 → 503）。
> - llm / media：acquire 前用 `api:canStartHeavy` 预检给出友好拒绝，acquire 为准。
- RULE-S13-08 SRC13:42-44 · release=2026-08-31 首版模块化（Phase 0 冻结） / platform=unknown / role=all / condition=all
> | 对外 API | OpenAI + Anthropic 两种方言 | 人类 |
> | 监听 | `0.0.0.0`，**无令牌鉴权** | 人类 |
> | 无模型时 | 不自动加载，一律 503 报错 | 人类 |
- RULE-S4-09 SRC4:46-47 · release=2026-08-31 首版模块化 / platform=test harness / role=all / condition=媒体运行中
> - **R-e2e-08** 互斥在 UI 上可见：媒体运行中，加载按钮与另一媒体按钮均被禁用，状态条给出拒绝原因；
>   媒体结束后恢复可用。
- RULE-S3-08 SRC3:307-307 · release=2026-08-31 首版模块化 / platform=test harness / role=all / condition=视频作业运行中
> | test_mutex_ui.py | R-e2e-08 | 视频作业闸停在运行中 → 聊天面板「加载」按钮带 `disabled`、音乐面板「生成」带 `disabled`、状态条含拒绝原因文案（来自 `data:deskState.can_start` 的机器可读原因）；放行剧本至 done → 下一 tick 两按钮恢复可用（`not disabled`） |
- RULE-S25-17 SRC25:115-126 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-budget-17** 「能不能用这个模型」问的是**台面还持不持有它**，不是「有没有媒体作业在跑」。
> 
>   互斥时代这两个问题同义，所以处处写成后者。预算取代互斥之后它们分开了：媒体
>   与聊天可以共存，而共存的安全性在**授予那一刻**就算过了——`cost("llm")` 报的
>   `bytes_needed` 就是权重加满窗 KV，`fits()` 拿它跟媒体一起判。媒体作业能开，
>   恰恰证明「聊天用满窗口 + 媒体」一起装得下。真机实测（2026-09-22，M5 Max）：
>   聊天 80.1 GiB + 视频 27.0 GiB = 107.1 GiB ≤ 能力 107.5 GiB。
> 
>   所以在这之后再按 `media_busy` 拦一道，拦掉的是已经付过代价的能力：共存只剩
>   「省一次加载」，兑现不了「边渲染边聊」。曾有四处这样拦着——台面聊天、网关守卫、
>   提示词助手的可用性、断流原因的归因。
- RULE-S25-18 SRC25:127-129 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
>   判据统一为 `still_holds(desk_state, kind, label)`：在**全部**持有者里找自己。
>   只看 `holder`（最后授予的那件）是同一个错误的另一种写法——视频一授予它就成了
>   video，于是「别人也拿到了」被读成「我被驱逐了」。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：R-budget-17 取代 R-llm-06/R-gateway-08/R-e2e-08 的「媒体在跑即拒绝」：拒绝条件是预算装不下

### RC3 · version_conflict · 已澄清
共同条件：加载模型/开启重活前的容量判定与内存警告；budget design 与 budget spec 同属 2026-09-17 预算子系统，ui/arbiter 为 2026-08-31
budget design 冷启动额度写成 (available − 权重 − 安全余量)，ui 与 arbiter 的加载前警告以「模型字节 ≥ 当前 available_bytes」触发；budget spec R-budget-16 改为分母是 max_recommended_working_set_size（机器自报能力），明确不是此刻可用内存、不再拍留量、不计别的 app 占用
待确认：预算与加载前警告的分母是否统一为 R-budget-16 的机器能力？budget design 的 available−安全余量 公式与 ui 的 available_bytes 警告阈值是否已作废？
- RULE-S24-06 SRC24:138-148 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=本机首次装载该模型
> ```
> 加载请求
>   → estimate 读 config.json      ⇒ 每 token 字节（predicted）、声明窗口
>   → catalog 的 ModelEntry.gb     ⇒ 权重占用（已有字段）
>   → arbiter/memory 快照           ⇒ total / available / pressure
>   → 媒体余量：档案无记录 ⇒ unavailable，本次不允许并行
>   ⇒ 额度 = (available − 权重 − 安全余量) ÷ 每 token 字节
>   ⇒ launch_args: --prompt-cache-bytes <额度 × 每 token 字节>、--prompt-cache-size <条数>
> 起 mlx-lm，硬边界自此由它自己 trim 守护
> ```
- RULE-S25-11 SRC25:72-77 · release=2026-09-17 budget 改写 / platform=macOS Apple 芯片 / role=all / condition=all
> - **R-budget-16** 预算的分母是**机器自报的重活能力**，不是此刻的可用内存。
> 
>   取 `mlx.core.device_info()["max_recommended_working_set_size"]`——`mlx_lm/server.py`
>   启动时会 `mx.set_wired_limit()` 成这个值，而 **wired 的内存按定义不参与换页**，
>   所以它是硬上限：超过去不是慢一点，是分配失败或系统开始杀进程。虚拟内存在这里
>   帮不上忙。
- RULE-S25-13 SRC25:91-93 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
>   **别的 app 占的内存不在这个模型里，这是有意的。** 台面仲裁的是自己的重活，
>   别人的内存既管不了也拦不住；把它算进来只会让答案随浏览器开没开而变，
>   用户无法预期也无法规划。真撞上换页时由内存压力传感器兜底（R-budget-09）。
- RULE-S1-08 SRC1:237-240 · release=2026-08-31 首版模块化（arbiter/foundation 等） / platform=unknown / role=all / condition=all
> - 只读预检，不改状态。`ok/reason` 来自 `plan_acquire` 同一张转移表（与 acquire 判定必然一致）。
> - 传入 `estimated_bytes`（调用方从 `data:modelEntry` 的体积换算）时比对当前 `available_bytes`；
>   装不下**不置 `ok=false`**，而是附 `memory_warning`——按 spec 这是加载前警告（UI R-ui-08 弹确认框），
>   不是拒绝。不传体积则 `memory_warning` 恒为 `null`。
- RULE-S22-11 SRC22:120-126 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=加载模型前
> - 「加载」流程（R-ui-08）：
>   1. 取所选 `data:modelEntry` 的体积与最新 `api:memorySnapshot`；
>   2. `mem_warn.js` 纯函数 `needsWarning(modelBytes, snapshot) -> {warn, message}`——
>      判定规则：模型字节数 ≥ 快照可用字节数即警告，message 含双方数字；
>   3. `warn` 为真 → `confirm.js` 弹层，用户确认才继续，取消即中止；
>   4. `api.loadLlm(key)`；加载中轮询 `api:llmStatus` 展示 `loading`，失败展示服务端原因
>      （含 mlx-lm 日志尾部，R-llm-04 提供）。
- RULE-S2-08 SRC2:36-36 · release=2026-08-31 首版模块化（arbiter/foundation 等） / platform=unknown / role=all / condition=加载模型前
> - **R-arbiter-07** 加载某模型前比对其体积与当前可用内存，装不下要在加载前给出警告（不是加载失败后才说）。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：预算与加载前警告的分母统一为 R-budget-16 的机器能力

### RC4 · behavior_conflict · 已澄清
共同条件：开启重活时内存/预算不足的处置；硬件软限制记忆（2026-09-24/25）与 budget spec（2026-09-17）均适用于当前版本，平台均为 macOS 本机
用户确认的硬件软限制写「memory checks are soft warnings (confirmable), never hard blocks」「never a new hard rejection」；budget spec 规定预算不足时拒绝并带数字、需腾掉正在跑的媒体作业时查询与授予都答「不行」、压力升高时拒绝新的重活，budget design 规定未实测前媒体与聊天不并存——这些是不可用 force 越过的拒绝
待确认：「内存检查只提醒不硬拦」是否涵盖 budget 的 fits() 拒绝与压力闸，还是只约束新增作业种类的 estimate_bytes 预警？预算不足时是否应提供「仍要开始」的确认路径？
- RULE-S41-01 SRC41:3-3 · release=用户确认记忆 2026-09-24/25 / platform=unknown / role=all / condition=all
> description: "Design for varied Mac RAM sizes, but memory checks are soft warnings (confirmable), never hard blocks — macOS virtual memory absorbs overshoot"
- RULE-S41-02 SRC41:11-11 · release=用户确认记忆 2026-09-25 / platform=unknown / role=all / condition=all
> New features must work across different hardware (36 GB → 512 GB Macs), but memory checks must stay lenient: estimate → "内存可能不足 / 仍要生成" confirm with force, never a new hard rejection, never hide features by hardware.
- RULE-S28-BSCOPE SRC28:18-23 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> 整体已定的用户决定（本文只实现其中的底座部分，其余写给下游作约束）：
> - 视频、音乐都有「在这个基础上改」（回填参数、沿用种子）与「换个版本」（换种子直接重生）。
> - 音乐：调整重生 + 「接着写下一段」（同风格、新歌词，交叉淡化拼接；不是真正的音频续写）。
> - 视频：两个调整动作 + 从图片会话挑图作首帧 + 「接着往下生」（尾帧 → 下一段首帧）+ 用音乐会话的歌作配乐，两种都要：D1 参考模式（实验性）、D2 替换音轨（默认）。
> - 成片：续写时自动拼好、旧版本保留；也能手动挑片段排序合成。
> - 硬件：不同内存的机器都要能用；内存检查只提醒可确认，不新增硬拒绝，不按硬件隐藏功能；续写段数与成片长度不设上限。
- RULE-S31-S00c SRC31:16-17 · release=2026-09-27 视频配乐 3b / platform=unknown / role=all / condition=视频页
> - [S-00c] 不新增内存硬拒绝；D1 估算同普通视频。
> - 台面未发布，不谈兼容。
- RULE-S25-09 SRC25:51-54 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-budget-07** 重活能否并存由预算判定，预算不足时结果即互斥。
>   判定的输入是**一组**重活而非一对：`fits(workloads)`。三件能否共存不等于
>   三个两两判断的合取，「最小让出」也只有在集合上才算得出来。
>   拒绝必须带机器可读原因与数字：需要多少、现有多少、依据来源为预测还是实测。
- RULE-S25-15 SRC25:103-105 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
>   所以：最小让出只需卸聊天模型时，查询也答「能开」，并在 `release` 里说明会让出谁
>   （界面据此讲「会先卸掉聊天模型」）。要腾掉正在跑的媒体作业时两者都答「不行」——
>   为了开另一件重活静默杀掉用户正在跑的生成，不是台面该替他做的决定。
- RULE-S25-22 SRC25:153-159 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=内存压力升高
> - **R-budget-09** 内存压力升高时，按代价从轻到重处置：① 收紧对话额度并立即触发压缩；
>   ② 拒绝新的重活；③ 才是卸载模型或终止作业。压力传感器是兜底闸，不是决策者。
> 
>   **不包含「令 mlx-lm trim」**：已核实 mlx-lm 只暴露 `/v1/completions`、
>   `/v1/chat/completions`、`/chat/completions`、`/v1/models`、`/health` 五个路由，
>   没有管理端点；`trim_to()` 只在它自己的请求循环里按 `--prompt-cache-bytes` 调用，
>   外部既触发不了也改不了限额。收紧只能在下次加载时经命令行生效（见 R-budget-05）。
- RULE-S24-11 SRC24:203-205 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=本机无媒体实测峰值
> **未经本机实测不放宽**：媒体估算的标定值来自 2026-09-08 的一台机器，对别的机器只是预测。
> 预测可以用来**警告**（今天就在这么用），但不足以用来**放宽**限制——
> 在这台机器自己量出峰值之前，媒体与聊天不并存。
- RULE-S27-D20 SRC27:169-174 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-20] 校验与挂接顺序（`start_image_job` → `_start`）：
>   1. 参数校验（提示词、宽高、步数、种子、force）→ 400；
>   2. `session_id` 校验（D-18）→ 400 / 404；
>   3. 互斥 `media_busy` → 409；运行环境 `capability_missing` → 503；模型 `model_incomplete` → 409；arbiter 拒绝 → 409；内存警告 `insufficient_memory`（未 force）→ 409；
>   4. 启动子进程；`spawn_failed` → 500；
>   5. **子进程启动成功、`_state` 已为 running 之后**，在 `MediaService._lock` 内调用 `begin_attempt(session_id, attempt)`，`attempt.job_id` 为新作业号、`params` 为实际参数（含实际 seed）。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：内存/预算检查一律「提醒 + 确认仍要继续」，不硬拦（含 fits() 不足时）——沿用你此前「warn+confirm, never block」的决定

### RC5 · scope_dependency · 已澄清
共同条件：台面状态对象 deskState 的持有者表达；budget 改写后持有者可为一组，R-arbiter-06 声明不变
arbiter 设计的 deskState 只有单个 holder 与固定两键 can_start，shell 菜单栏标题按 holder.kind 映射（已加载/出片中），计划为 holder 加 display；budget spec 把持有者改为一组并指出「只看 holder（最后授予的那件）」是错误写法，却声明 R-arbiter-06 不变
待确认：多个持有者并存时 deskState 应如何表达（holders 数组还是保留 holder）？菜单栏与状态条在聊天+视频并存时应显示什么？
- RULE-S1-07 SRC1:207-211 · release=2026-08-31 首版模块化（arbiter/foundation 等） / platform=unknown / role=all / condition=all
> - `holder` 空闲时为 `null`；token 不出现在 deskState 里（只回给 acquire 调用方）。
> - `media_busy = holder.kind ∈ {video, music}`。
> - `can_start` 固定两个键：`llm` 与 `media`（video/music 在状态机里同态，合并回答）。
> - deskState **不内嵌内存数字**——「内存里是谁」由 `holder` 回答；
>   实时内存数字走 `api:memorySnapshot`（UI 的状态条两者都消费，避免每次状态读取都开子进程）。
- RULE-S2-07 SRC2:34-35 · release=2026-08-31 首版模块化（arbiter/foundation 等） / platform=unknown / role=all / condition=all
> - **R-arbiter-06** 暴露单一台面状态对象：内存里是谁、媒体是否在跑、现在能不能开下一件重活，
>   以及若不能、为什么。这是状态条与菜单栏的唯一数据来源。
- RULE-S20-10 SRC20:202-212 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
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
- RULE-S40-24 SRC40:1096-1096 · release=2026-09-11 视觉修复计划（cross-exam 0908 B） / platform=unknown / role=all / condition=all
> - Produces: `/api/state` 的 `holder` 增加 `display` 字段（人类可读名）；`menuTitle` 优先用 `display`
- RULE-S25-29 SRC25:188-192 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-arbiter-01** 改：重活能否并存由预算判定；预算不足时退化为互斥。持有者由单个变为一组。
> - **R-arbiter-04** 改：拒绝条件由「媒体在跑」变为「预算装不下」。
> - **R-arbiter-05** 改：仅在预算不足时让出，且最小让出。
> - **R-arbiter-07** 改：由加载时一次性检查，变为持续生效。
> - **R-arbiter-02 / 03 / 06** 不变。
- RULE-S25-18 SRC25:127-129 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
>   判据统一为 `still_holds(desk_state, kind, label)`：在**全部**持有者里找自己。
>   只看 `holder`（最后授予的那件）是同一个错误的另一种写法——视频一授予它就成了
>   video，于是「别人也拿到了」被读成「我被驱逐了」。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：台面状态以持有者数组表达；状态条与菜单栏并存时列出全部持有者

### RC6 · needs_clarification · 已澄清
共同条件：gateway 模块验收方式（2026-08-31 同版本）
gateway 设计把「另一台设备经局域网访问 + 两 SDK 真对话」列为不进自动验收的 reality gate runbook；gateway spec（决策 D-0002）写局域网可达性自动验收、「本模块无 reality gate」
待确认：gateway 是否保留人工 reality gate（SDK 真对话），还是以 D-0002 的自连自动验收为唯一验收、删除设计中的 runbook？
- RULE-S7-17 SRC7:364-366 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> **reality gate（不进自动验收，出 runbook）**：另一台设备经局域网访问
> `http://<本机IP>:8770/v1/models` 与两 SDK 各跑一次真对话。runbook 一行 curl + 两段
> 官方 SDK 最小脚本，人工执行。
- RULE-S8-11 SRC8:53-56 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
> 局域网可达性**自动验收**（决策 D-0002）：绑 `0.0.0.0:8770` 后，从本机以局域网 IP
> `http://192.168.31.68:8770/v1/models` 自连——该路径不走回环，足以证明非本地监听生效。
> IP 在测试中动态取自 `ipconfig getifaddr en0`，取不到则跳过并明确报告跳过原因（不得静默通过）。
> **本模块无 reality gate。**
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：网关以 D-0002 自连自动验收为准，设计里的人工 runbook 仅作补充

### RC7 · version_conflict · 已澄清
共同条件：shell 关窗不退、Quit 收割、服务死亡提示等窗口级行为的验收方式（2026-08-31）
shell 设计把关窗、退出端口为空、SIGTERM、kill -9 后错误页列为人工 reality-gate runbook；shell spec（决策 D-0002）规定这些用 orca computer 自动验收，仅菜单栏/Dock 外观与 NSOpenPanel 交互留 reality_gate
待确认：R-shell-03/04/08 的窗口级验收是否以 spec 的 orca 自动验收为准？设计中的人工 runbook 是否仅作补充？
- RULE-S20-13 SRC20:304-304 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
> 验收全部是快速确定性命令；需要真点击的项列 reality-gate runbook。
- RULE-S20-14 SRC20:344-352 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
> ### reality-gate runbook（人工，Phase 2 附证据）
> 
> 1. 双击 App：Dock 图标出现，⌘Tab 可切换（R-shell-05）。
> 2. 首运：NSOpenPanel 弹出，三条路径各走一遍（默认/自选/收编-指向），错误路径用只读目录验证报错文案（R-shell-07）。
> 3. 关窗：窗口消失，菜单栏项仍在，`lsof -iTCP:8766` 仍有监听；菜单「打开窗口」唤回原状态（R-shell-03）。
> 4. 加载一个 LLM / 起一个视频作业，看菜单栏在 10s 内变为「已加载 …」/「出片中」（R-shell-02）。
> 5. 菜单「退出」：App 消失且 `lsof -iTCP:8766 -iTCP:8767` 双双为空（R-shell-04 全景）。
> 6. `kill -TERM <App pid>` 重复第 5 步的断言（异常终止路径）。
> 7. 运行中 `kill -9` 掉 desk 服务进程：窗口 10s 内出现错误说明页而非空白（R-shell-08），「重试」能复活。
- RULE-S21-09 SRC21:41-46 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
> - **窗口级行为自动验收**（决策 D-0002，经 `orca computer capabilities` 实测）：
>   provider 支持 windows 表面与 click/hotkey/setValue/typeText/pressKey 动作，
>   accessibility 与 screenshots 权限均为 granted。因此以下用 `orca computer` 驱动、pytest 断言：
>   - R-shell-03 关窗口不退：`hotkey Cmd+W` 后断言进程仍在、8766 仍在监听、窗口可再次调回；
>   - R-shell-04 Quit 杀服务：`hotkey Cmd+Q` 后断言进程消失且 8766 无监听；
>   - R-shell-08 服务死亡提示：外部杀掉服务进程后，从无障碍树读到明确错误文案（非空白 WebView）。
- RULE-S21-10 SRC21:50-52 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
> - **仅以下留 `reality_gate`**（`orca computer` provider 报告 `menubar/dock/dialogs = false`，
>   无法读取这些表面，不得伪造证据）：菜单栏状态项与 Dock 图标的**视觉外观**、
>   首运 `NSOpenPanel` 原生对话框的真实交互。附人工 runbook。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：R-shell-03/04/08 以 spec 的自动验收为准，人工 runbook 仅作补充

### RC8 · behavior_conflict · 已澄清
共同条件：当前 README 文本（@0d98e9e）对推理与数据外流的陈述
README「谁用」一节仍写「推理不出门，成品不出门」，同一 README 后文又写网关默认监听 0.0.0.0:8770 无鉴权；packaging 设计要求 README 不得再写「推理不出门」并以测试断言过时表述已亡，gateway spec 记录人类已确认 0.0.0.0 无鉴权与「推理不出门」冲突
待确认：README「推理不出门」一句是否应删除或改写？在网关默认开启的前提下，它指的是不上云还是不离开本机？
- RULE-S34-02 SRC34:20-20 · release=README @ 0d98e9e（当前） / platform=unknown / role=all / condition=all
> 一个人、一台大内存 Mac、模型都放本机。推理不出门，成品不出门。
- RULE-S16-11 SRC16:228-240 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
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
- RULE-S17-11 SRC17:28-29 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **R-packaging-09** README 改写为安装后的真实行为，含：不自启、菜单栏形态、模型目录位置与收编、
>   以及对外 API 监听 `0.0.0.0` 且无鉴权这一事实。
- RULE-S8-01 SRC8:7-9 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> 监听 `0.0.0.0`，**无令牌鉴权**。已向人类声明：同网络任何设备、以及本机浏览器里任何知道端口的页面
> 都能驱动模型并读取输出，且与 README 原有的「推理不出门」冲突。人类确认后仍如此选择。
> README 将被改写为实际行为。
- RULE-S13-08 SRC13:42-44 · release=2026-08-31 首版模块化（Phase 0 冻结） / platform=unknown / role=all / condition=all
> | 对外 API | OpenAI + Anthropic 两种方言 | 人类 |
> | 监听 | `0.0.0.0`，**无令牌鉴权** | 人类 |
> | 无模型时 | 不自动加载，一律 503 报错 | 人类 |
- RULE-S34-11 SRC34:86-88 · release=README @ 0d98e9e（当前） / platform=macOS / role=all / condition=all
> - 安装后不会自动启动；从“应用程序”打开本地模型台后，服务才会随应用启动。关闭窗口不会退出，使用菜单栏图标或“退出本地模型台”才会停止它。
> - 首次打开时选择模型目录；默认目录是 `~/Library/Application Support/LocalModelDesk/models`。已有模型可收编已有模型目录：可以直接指向原目录，或把已识别的模型移入新目录，无须重新下载。
> - 默认网关监听 `0.0.0.0:8770`，同一局域网的设备可访问。本服务无鉴权；请只在可信网络中启用，或在设置中关闭网关。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：「推理不出门」指不上云；网关开启时局域网设备可调用本机模型，README 须如实说明

### RC9 · version_conflict · 暂缓决定
共同条件：构建产物签名与分发流程；README 为当前版本，packaging/overview 为 Phase 0 冻结
Phase 0 冻结决定与 packaging spec 写「不做公证」、公证与对外分发列入本轮不做；当前 README 写设置 LMD_NOTARY_PROFILE 时构建脚本自动提交公证并 staple，提供「分发给其他机器」流程
待确认：公证/分发是否已被重新纳入范围？若是，Phase 0「不做公证」与路线图是否视为被取代？
- RULE-S13-05 SRC13:38-38 · release=2026-08-31 首版模块化（Phase 0 冻结） / platform=macOS / role=all / condition=all
> | 签名 | Developer ID Application 签名 + hardened runtime；**不做公证** | 人类 |
- RULE-S13-12 SRC13:115-121 · release=2026-08-31 首版模块化（Phase 0 冻结） / platform=unknown / role=all / condition=all
> ## Roadmap（本轮明确不做）
> 
> - 公证（notarize）与对外分发：需要 App Store Connect 凭据，人类已选择跳过。
> - 对外接口的令牌鉴权与 TLS。
> - 任意 HF 仓库的自由添加（目录仍是选定的 8 项）。
> - 多人排队、云端推理。
> - 70B 与 H3 同时驻留。
- RULE-S17-01 SRC17:7-7 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
> 人类明示：Developer ID Application 签名 + hardened runtime，**不做公证**。
- RULE-S36-09 SRC36:66-66 · release=qwen-image-mlx.md @ 0d98e9e / platform=macOS / role=all / condition=all
> 修改安全权限或覆盖现有应用。签名不等于公证；本次不公证、不发布安装。
- RULE-S34-10 SRC34:73-82 · release=README @ 0d98e9e（当前） / platform=macOS / role=all / condition=all
> ### 分发给其他机器（需要 Apple 开发者账号）
> 
> 一次性准备：
> 
> ```bash
> xcrun notarytool store-credentials LocalModelDesk \
>   --apple-id <你的 Apple ID> --team-id <Team ID> --password <App 专用密码>
> ```
> 
> 之后出包时带上 `LMD_NOTARY_PROFILE=LocalModelDesk ./scripts/build-app.sh`，脚本会自动提交公证并 staple。不设该变量时只做 Developer ID 签名，本机可用、别的机器会被 Gatekeeper 拦。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）

### RC10 · version_conflict · 已澄清
共同条件：开发模式与打包的 Python 环境布局（macOS dev 与 bundle）
foundation 设计规定现有 .venv-desk/.venv-music3 双 venv 布局不被延续、dev 按单环境开发、bundle 为单解释器+三套 pylibs；当前 README 与 qwen-image 文档要求 dev 下视频/图片/音乐各用各的 venv（.venv-image 为 Python 3.12），构建另装第四套 pylibs/image
待确认：dev 环境是否改为每个媒体运行时独立 venv？foundation A8 的单环境假设与 packaging 三套 pylibs 的布局是否已被取代？
- RULE-S5-20 SRC5:462-464 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **A8 dev 态 venv**：`venv_python = sys.executable`（开发者从装齐依赖的 venv 里起服务）；
>   现有 `.venv-desk` / `.venv-music3` 双 venv 布局不被延续——bundle 是「单内嵌解释器 + 三套
>   pylibs」（packaging §1.3，无任何 venv），dev 按装齐全部依赖的单环境开发。
- RULE-S16-02 SRC16:59-62 · release=2026-08-31 首版模块化 / platform=macOS bundle / role=all / condition=all
> 上述所有进程一律带 `-s` 启动（禁用用户 site-packages），`PYTHONPATH` 显式给定——
> 否则内嵌解释器会静默读取 `~/.local/lib/python3.13/site-packages`，一个「碰巧靠用户机器上装过的包才能跑」
> 的 bundle 会通过一切检查。这是 R-packaging-02「不依赖用户级 site-packages」的**运行期强制点**
> （shell / foundation 拼命令时照此执行；verify 的 V6 以同样方式冒烟，见 2.4）。
- RULE-S34-13 SRC34:99-104 · release=README @ 0d98e9e（当前） / platform=macOS dev / role=all / condition=all
> - 服务：`.venv-desk/bin/python -m desk`（端口由 `LMD_SHELL_PORT` 指定，默认 8766；`LOCALMODELDESK_DATA_ROOT` 可换一个独立数据目录）。
> - 三个媒体运行时各用各的 venv，服务本身不装它们：
>   - 视频：`mlx-h3` 可执行文件（`uv tool install` 装在 `~/.local/bin`），或用 `LOCALMODELDESK_MLX_H3` 指定。
>   - 图片：`.venv-image`，安装见 `docs/qwen-image-mlx.md`；或用 `LOCALMODELDESK_IMAGE_PYTHON` 指定。
>   - 音乐：`uv venv --python 3.13 .venv-music3 && uv pip install --python .venv-music3/bin/python -r packaging/requirements-music.txt`；或用 `LOCALMODELDESK_MUSIC_PYTHON` 指定。
> - 缺哪个，`GET /api/capabilities` 的对应项会给出原因，对应页面的生成按钮禁用并显示原因。
- RULE-S36-05 SRC36:35-37 · release=qwen-image-mlx.md @ 0d98e9e / platform=macOS dev / role=all / condition=all
> uv venv --python 3.12 .venv-image
> uv pip install --python .venv-image/bin/python --excludes packaging/excludes-image.txt -r packaging/requirements-image.txt
> .venv-image/bin/python scripts/prepare-qwen-image.py \
- RULE-S36-07 SRC36:48-51 · release=qwen-image-mlx.md @ 0d98e9e / platform=unknown / role=all / condition=all
> 开发服务默认使用本工作树 `.venv-image/bin/python`；可用 `LOCALMODELDESK_IMAGE_PYTHON`
> 指定其他图片解释器。`GET /api/capabilities` 暴露 `image_runtime.present/detail`，
> 能力检查最多缓存 10 秒，修复运行环境后可自动恢复。构建脚本独立安装 `pylibs/image`，
> 图片工作进程不复用音乐或聊天依赖目录。
用户于 2026-10-14T18:30:00+09:00：澄清（推荐）
有效规则：dev 下各媒体运行时各用各的 venv，bundle 为单内嵌解释器 + 各运行时独立 pylibs（含 image），以 README 与 qwen-image 文档现行写法为准；foundation A8 的单环境假设已被取代；-s 与显式 PYTHONPATH 的运行期强制不变

### RC11 · scope_dependency · 暂缓决定
共同条件：模型目录（catalog）的单点与条目范围；图片会话与 qwen-image 文档为后续版本
resources 规定目录恰好 8 条（h3、music3 + 6 chat）且仓库内只能有一份模型 repo/路径清单，路线图写「目录仍是选定的 8 项」，README 写只服务聊天/视频/音乐能力；qwen-image 文档另有 desk/media/image_model.py 固定文件清单（含源仓库、revision、目标路径），relpath image-models/…，图片能力已上线
待确认：图片模型是否计入 catalog（目录是否扩为 9 项）？image_model.py 的固定文件清单是否构成 R-resources-01 禁止的第二份清单？README「明确不做」是否需包含图片？
- RULE-S18-03 SRC18:70-77 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> CATALOG: tuple[ModelEntry, ...]        # 恰好 8 条：h3、music3 + 6 个 chat
> def list_catalog() -> list[ModelEntry]  # api:listCatalog
> def entry(key: str) -> ModelEntry       # 未知 key 抛 UnknownModelError
> ```
> 
> 8 条数据从现 `initModels.sh` CATALOG（repo/relpath/size）与 `server.py` MODEL_CATALOG
> （name/vision/quant/params/gb）合并而来，落地后这两处删除（census A01/A02）。
> 这是仓库内**唯一**一处模型 repo/路径清单；前端经 HTTP 取目录，JS 里不复制。
- RULE-S19-01 SRC19:11-13 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> 目录共 8 项（3 组）：`h3`、`music3` 各一项，`llm` 组 6 项。
> 每项含：`key`、`name`、`group`(chat|video|music)、`hf_repo`、`relpath`、以及聊天模型的
> `vision`/`quant`/`params`/`gb`。这份目录在仓库里**只能存在一处**。
- RULE-S19-02 SRC19:17-18 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **R-resources-01** 单一目录定义，供服务端、前端、以及任何 CLI 入口共同消费；
>   仓库内不得存在第二份模型 repo/路径清单（`initModels.sh` 与 `server.py` 里现有的两份都要消失）。
- RULE-S13-12 SRC13:115-121 · release=2026-08-31 首版模块化（Phase 0 冻结） / platform=unknown / role=all / condition=all
> ## Roadmap（本轮明确不做）
> 
> - 公证（notarize）与对外分发：需要 App Store Connect 凭据，人类已选择跳过。
> - 对外接口的令牌鉴权与 TLS。
> - 任意 HF 仓库的自由添加（目录仍是选定的 8 项）。
> - 多人排队、云端推理。
> - 70B 与 H3 同时驻留。
- RULE-S34-14 SRC34:108-110 · release=README @ 0d98e9e（当前） / platform=unknown / role=all / condition=all
> - 不把请求发到云端，也不给多人共用
> - 不收录任意模型，只服务这张台上选定的聊天、视频、音乐能力
> - 不追求 70B 对话和视频生成同时驻留
- RULE-S36-06 SRC36:41-46 · release=qwen-image-mlx.md @ 0d98e9e / platform=unknown / role=all / condition=all
> 下载约 33 GB。重复执行同一命令可续传；不向已有未知模型目录覆盖文件。
> 目录内 `localmodeldesk-image.json` 记录两个源 revision 和下载完成状态。
> 资源目录相对于应用配置的 `models_root`：`image-models/qwen-image-2.1-heretic`。
> 资源页与准备脚本使用同一固定文件清单（`desk/media/image_model.py`），逐文件记录源仓库、
> revision、目标路径和精确字节数；两源都校验通过才显示已安装。字节数校验不是内容哈希校验。
> 下载保留 `.cache/localmodeldesk/parts/*.part`，失败后续传；已有完整文件会跳过。
- RULE-S27-D03 SRC27:32-32 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-03] 图片文件不进会话目录：仍由媒体作业写到 `outputs_root`（`qwen-image-<stamp>-<8hex>.png`），会话只存文件名。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）

### RC12 · version_conflict · 已澄清
共同条件：图片页会话动作的生成方式；local-requirements 仍为 revision 1（confirmed），D-44a/D-47a 标注「2026-09-24 修订，用户确认」
需求 BR-9、设计非目标 D-00b、冻结基线与 qwen-image 文档都写图生图不在范围；同一设计的 D-44a/D-47a/D-47b 与媒体会话底座 B-10 规定「在这张基础上改」「换个构图」以图生图（base strength 0.6/0.35），但 local-requirements 与 decision-journal 未出现修订记录
待确认：图生图修订是否取代 BR-9 与 D-00b？local-requirements / 冻结基线是否需要升 revision 记录这次范围变更？
- RULE-S27-D00b SRC27:18-18 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-00b] 局部重绘 / 图生图不做。
- RULE-S27-TBR-9 SRC27:405-405 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> | BR-9 | 局部重绘/图生图不在本次范围 | D-00b | — |
- RULE-S47-BR-9 SRC47:21-21 · release=image-sessions revision 1（confirmed 2026-09-24） / platform=unknown / role=all / condition=图片页
>         "局部重绘/图生图不在本次范围"
- RULE-S50-02 SRC50:25-35 · release=decision-journal（2026-09-24） / platform=unknown / role=all / condition=图片页
>             "business_rules": [
>               "只改图片页；视频、音乐页不动",
>               "会话持久化在本机，重启 app 后仍在，每个会话一个 JSON 文件，沿用聊天会话的存储方式",
>               "会话内按时间顺序列出每次尝试：图片、提示词、宽高、步数、种子；失败或取消的尝试也列出并写明原因",
>               "会话需手动新建（像聊天的「新建」）；未新建时生成接在当前会话；会话标题默认取第一次生成的提示词",
>               "会话可切换、重命名、删除；删除会话只删分组，图片文件保留并仍出现在素材库",
>               "打开任意一次尝试后给两个动作：「在这张基础上改」把提示词回填到输入框并沿用该张种子，用户改完再生成；「换个构图」提示词不变、换一个新随机种子直接再生成",
>               "界面主流程不出现「种子」一词；种子与宽高、步数一起收进「高级参数」",
>               "新尝试总是追加到当前会话末尾，不覆盖旧图",
>               "局部重绘/图生图不在本次范围"
>             ],
- RULE-S50-05 SRC50:89-98 · release=decision-journal（2026-09-24） / platform=unknown / role=all / condition=图片页
>                   "只改图片页；视频、音乐页不动",
>                   "会话持久化在本机，重启 app 后仍在，每个会话一个 JSON 文件，沿用聊天会话的存储方式",
>                   "会话内按时间顺序列出每次尝试：图片、提示词、宽高、步数、种子；失败或取消的尝试也列出并写明原因",
>                   "会话需手动新建（像聊天的「新建」）；未新建时生成接在当前会话；会话标题默认取第一次生成的提示词",
>                   "会话可切换、重命名、删除；删除会话只删分组，图片文件保留并仍出现在素材库",
>                   "打开任意一次尝试后给两个动作：「在这张基础上改」把提示词回填到输入框并沿用该张种子，用户改完再生成；「换个构图」提示词不变、换一个新随机种子直接再生成",
>                   "界面主流程不出现「种子」一词；种子与宽高、步数一起收进「高级参数」",
>                   "新尝试总是追加到当前会话末尾，不覆盖旧图",
>                   "局部重绘/图生图不在本次范围"
>                 ],
- RULE-S36-03 SRC36:15-17 · release=qwen-image-mlx.md @ 0d98e9e / platform=unknown / role=all / condition=all
> 模型或 MLX 环境未就绪时生成按钮禁用；运行中的作业不能重复提交。
> 分辨率必须为 256–2048 范围内的 16 倍数。文件写入当前配置的成品目录，
> 不会上传到云端。本次新增的是单张文生图，不包含图生图或提示词助手。
- RULE-S27-D44a SRC27:225-225 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-44a] 以图生图（2026-09-24 修订，用户确认）：被回填的尝试有图（`status == done`、有 `output` 且文件还在）时，提示条改为「以第 N 次为底稿」；提示条仍在时点「生成图片」，请求带 `base: {attempt_id, strength: 0.6}`，后端以那张图为底稿重绘（保留构图、重画细节），宽高取底稿的宽高。没图的尝试（失败、取消、文件不在）仍按 D-40–D-44 只回填、按文生图生成。提示条隐藏（改了种子或点 ×）后同样退回文生图。
- RULE-S27-D47a SRC27:231-231 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-47a] 以图生图（2026-09-24 修订）：该尝试有图时，提交带 `base: {attempt_id, strength: 0.35}`，以这张为底稿重绘（保留主体与色调、换构图）。没图的尝试「换个构图」不可用，按钮下方原因行为「这一次没有图片，不能以它为底稿换个构图」。
- RULE-S27-D47b SRC27:232-232 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-47b] 以图生图的强度只允许 0.6 与 0.35 两档（mflux 约定：强度越高越接近底稿）；后端校验底稿属于同一会话、状态为 done 且文件存在，否则分别返回 400 `invalid_params`、404 `base_not_found`、404 `base_missing`。尝试记录 `base: {attempt_id, strength}`（文生图为 `null`），卡片标题行显示「基于第 N 次」（底稿不在列表中则不显示）。
- RULE-S28-B10 SRC28:91-91 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-10] `base`：仅 image，含义同 IS D-47b；其他 kind 恒为 `null`。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：图生图修订（D-44a）取代 BR-9 与 D-00b 的「不做以图生图」

### RC13 · version_conflict · 已澄清
共同条件：图片生成的默认种子与界面说明；qwen-image 文档 @0d98e9e 与图片会话设计 2026-09-24
qwen-image 文档建议「保留 1024×1024、40 步、种子 42」并写 HTTP 默认 seed 42；图片会话设计规定去掉固定默认 42、省略时后端随机，种子框默认空，且「种子」不出现在主流程
待确认：qwen-image 文档中的「默认 seed 42 / 建议保留种子 42」是否已过时，应以 D-19 随机种子为准？
- RULE-S36-02 SRC36:11-11 · release=qwen-image-mlx.md @ 0d98e9e / platform=unknown / role=all / condition=图片页使用说明
> 2. 打开「图片」，填写提示词，建议保留 1024×1024、40 步、种子 42，然后点「生成图片」。
- RULE-S36-10 SRC36:68-72 · release=qwen-image-mlx.md @ 0d98e9e / platform=unknown / role=all / condition=all
> HTTP 参数：非空 `prompt`；`width/height` 为 256–2048 内的 16 倍数；
> `steps` 为 1–100，`seed` 为 uint32；默认 1024×1024、40 步、seed 42。
> 无效参数、缺失/不完整模型、缺失运行环境在启动前拒绝；内存预算沿用现有预警及显式确认。
> 图片内存是保守预测值（1024² 约 52 GiB，随更大画幅上调），不是实测 RSS。
> 每个任务输出唯一 PNG 名称和同名来源/参数 JSON；历史记录保存所有输入参数。
- RULE-S27-D19 SRC27:168-168 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-19] `seed` 可省略：省略时后端用 `secrets.randbelow(2**32)` 取随机值；不再有固定默认值 42（`start_image_job` 签名与 `routes.start_image` 里的 `seed=42` 默认都去掉）。给了就必须是 0–4294967295 的整数（现有校验）。
- RULE-S27-D66 SRC27:252-252 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-66] 新会话第一次生成使用随机种子：种子框默认为空（`placeholder="留空则每次随机"`），前端在提交时若种子框为空则不传 `seed`，由后端 D-19 取随机值。
- RULE-S27-D50 SRC27:238-238 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-50] 「种子」二字只出现在「高级参数」折叠区内（输入框标签「种子（留空则每次随机）」和尝试详情的高级参数列表）。会话列表、时间线卡片、提示条、两个动作按钮、状态文案、确认框、错误提示中都不出现「种子」。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：以 D-19 随机种子为准，qwen-image 文档的「默认 seed 42」已过时

### RC14 · behavior_conflict · 已澄清
共同条件：图片页失败/已取消/文件不在的尝试卡片（同一图片页、同一版本）
D-86 与视觉验收写这三种卡片都显示两个动作按钮且参数完整可用（文件不在态「两个动作按钮仍可用」）；D-47a 修订规定没图的尝试「换个构图」不可用并显示原因
待确认：失败/取消/文件不在的卡片上「换个构图」是否应可用？D-86 与视觉验收 attempt-file-missing 是否需按 D-47a 改为「显示但禁用并说明原因」？
- RULE-S27-D86 SRC27:314-314 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-86] 这三种卡片都显示两个动作按钮（§5），参数都完整可用。
- RULE-S27-DACTIONS SRC27:215-215 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> 打开（选中）任意一次尝试——包括失败、已取消、图片文件已不在的尝试——都显示这两个按钮（业务规则「打开任意一次尝试后给两个动作」）。正在生成的尝试不显示这两个按钮（它还没有结果）。
- RULE-S48-attempt-failed SRC48:346-376 · release=visual-acceptance-criteria（image-sessions rev1，status passed） / platform=unknown / role=all / condition=图片页；前置：脚本化执行器让作业非零退出（exit_nonzero，带日志尾部）
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
- RULE-S48-attempt-cancelled SRC48:391-420 · release=visual-acceptance-criteria（image-sessions rev1，status passed） / platform=unknown / role=all / condition=图片页；前置：脚本化执行器保持运行，用户点 running 卡片上的「取消」
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
- RULE-S48-attempt-file-missing SRC48:475-499 · release=visual-acceptance-criteria（image-sessions rev1，status passed） / platform=unknown / role=all / condition=图片页；前置：一次完成尝试后，从 outputs_root 删除其 PNG 文件
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
- RULE-S27-D47a SRC27:231-231 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-47a] 以图生图（2026-09-24 修订）：该尝试有图时，提交带 `base: {attempt_id, strength: 0.35}`，以这张为底稿重绘（保留主体与色调、换构图）。没图的尝试「换个构图」不可用，按钮下方原因行为「这一次没有图片，不能以它为底稿换个构图」。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：按 D-47a：无图的卡片上「换个构图」显示但禁用并写明原因

### RC15 · behavior_conflict · 已澄清
共同条件：图片页按钮级别（同一页面、同一版本）
D-74 规定「生成图片」是页面唯一主按钮；D-60 规定左上「新会话」为主按钮样式，视觉验收全局规则也写「新会话」主按钮在最上；视觉候选与 2026-10-14 确认稿均规定同一组操作最多一个主按钮
待确认：图片页是否允许「新会话」与「生成图片」同时为主按钮样式？「唯一主按钮」指整页还是输入区这一组操作？
- RULE-S27-D74 SRC27:282-282 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-74] 展开卡片额外显示：大图（宽度不超过时间线列宽、高度不超过 60vh，`object-fit: contain`，`alt` 为提示词）、完整提示词、「高级参数」折叠块（列出 宽度、高度、步数、种子 四项实际值，默认折叠）、两个动作按钮（次级按钮样式，「在这张基础上改」在左，「换个构图」在右；「生成图片」是页面唯一主按钮）。
- RULE-S27-D60 SRC27:246-246 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-60] 左上「新会话」按钮（主按钮样式、plus 图标，与聊天页同构）：`POST /api/image-sessions`，新会话成为当前会话、排在列表最上，时间线显示空会话态，焦点移到提示词输入框。每次点击都新建（与聊天页一致）。
- RULE-S48-GSHOW SRC48:22-26 · release=visual-acceptance-criteria（image-sessions rev1，status passed） / platform=unknown / role=all / condition=图片页
>     "must_show": [
>       "左侧会话列表（「新会话」主按钮在最上）",
>       "右侧时间线与底部输入区（提示词输入框 + 「生成图片」主按钮 + 折叠的「高级参数」）",
>       "当前会话在列表中高亮（aria-current=true）"
>     ],
- RULE-S39-13 SRC39:154-155 · release=docs/visual @ 0d98e9e（候选 2026-09-16/17） / platform=unknown / role=all / condition=候选规则，未经用户确认
>     "按钮只有三级加一个危险级：主（实心强调色）、次（面板底 + 描边）、安静（透明无边、次要文字色）、危险（实心危险色）。同一组操作里最多一个主按钮。",
>     "禁用按钮统一半透明 0.5 且鼠标显示禁止光标，不靠变色表达禁用。",
- RULE-S53-17 SRC53:160-161 · release=visual-baseline 待冻结稿（用户 2026-10-14 逐类确认） / platform=unknown / role=all / condition=all
>     "按钮只有三级加一个危险级：主（实心强调色）、次（面板底 + 描边）、安静（透明无边、次要文字色）、危险（实心危险色）。同一组操作里最多一个主按钮。",
>     "禁用按钮统一半透明 0.5 且鼠标显示禁止光标，不靠变色表达禁用。",
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：「同一组操作最多一个主按钮」按操作组算：会话栏的「新会话」与输入区的「生成」分属两组

### RC16 · needs_clarification · 已澄清
共同条件：会话列宽度；视觉基线（2026-10-14 用户确认稿）与图片/音乐会话设计
视觉候选与 2026-10-14 确认稿都把会话卡片描述为「固定 240px 的窄列」；图片会话设计规定左侧 aside.sessions 宽 248px，音乐/视频页沿用
待确认：会话列宽以 240px 还是 248px 为准（或 240 指卡片、248 指列含内边距）？
- RULE-S39-14 SRC39:156-156 · release=docs/visual @ 0d98e9e（候选 2026-09-16/17） / platform=unknown / role=all / condition=候选规则，未经用户确认
>     "列表项都是卡片：面板底、1px 描边、8px 圆角；选中的卡片改描边为强调色，不改底色。内边距分两种：内容卡片（资源页、素材库行）16px；会话卡片 12px——它是固定 240px 的窄列、高频扫视，收紧一档是有意的（2026-09-17 实拍对照：改成 16px 后一屏少显示一条会话、每条标题少一个字）。",
- RULE-S53-18 SRC53:162-162 · release=visual-baseline 待冻结稿（用户 2026-10-14 逐类确认） / platform=unknown / role=all / condition=all
>     "列表项都是卡片：面板底、1px 描边、8px 圆角；选中的卡片改描边为强调色，不改底色。内边距分两种：内容卡片（资源页、素材库行）16px；会话卡片 12px——它是固定 240px 的窄列、高频扫视，收紧一档是有意的（2026-09-17 实拍对照：改成 16px 后一屏少显示一条会话、每条标题少一个字）。",
- RULE-S27-D70 SRC27:278-278 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-70] `#pane-image` 与 `#pane-chat` 同构：左侧 `aside.sessions`（宽 248px，复用 `.sessions` 样式与 `card session` 卡片、`session-actions` 的改名/删除图标按钮），右侧 `.image-main` 占满剩余宽度，内容最大宽 1400px，外边距 24px（视觉基线）。`#pane-image` 原来的「表单 | 作业」两栏 grid 与右侧 `.job` 区块取消，作业展示移入时间线里的 running 卡片。
- RULE-S29-M20 SRC29:100-100 · release=2026-09-27 音乐会话 / platform=unknown / role=all / condition=音乐页
> - [M-20] 左栏、主区宽度、外边距、窄窗 900×700 规则同 IS D-70、D-78。原 `.form | .job` 两栏与 jobview 删除。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：240px 指会话列表最小宽（ul min-width），248px 指会话列含内边距

### RC18 · version_conflict · 已澄清
共同条件：主界面标签切换与地址栏 hash；ui 设计 2026-08-31，视觉候选 2026-09-16，修复计划 2026-09-11
ui 设计规定无前端路由/hash、面板切换纯内存态、刷新回到聊天；视觉/交互候选及 2026-10-14 用户确认稿规定标签切换同步地址栏 hash、改 hash 也切换，修复计划按 #tab= 恢复标签、非法值回落 chat
待确认：标签页 hash 路由是否为正式行为（取代 ui 设计 A4）？刷新/重启时应恢复上次标签还是总回到聊天？
- RULE-S22-24 SRC22:333-333 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **A4 · 无前端路由/hash**：面板切换纯内存态，刷新回到聊天面板。单窗口 WebView 内无深链诉求。
- RULE-S22-21 SRC22:256-258 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> 前端唯一的「写」出口是 api.js；面板之间不直接互调，跨面板动作（回填切 tab）经 main.js。
> store.js 只保存 tick 的最新快照与当前会话 id，供各 pane 订阅；不做任何缓存持久化
> （会话与历史的持久化全在 library 模块，前端无 localStorage 依赖）。
- RULE-S38-03 SRC38:13-13 · release=docs/visual @ 0d98e9e（候选 2026-09-16） / platform=unknown / role=all / condition=候选规则，未经用户确认
>         "点标签切换页面时地址栏 hash 同步改变，直接改 hash 也切换页面。",
- RULE-S39-16 SRC39:172-175 · release=docs/visual @ 0d98e9e（候选 2026-09-16/17） / platform=unknown / role=all / condition=候选规则，未经用户确认
>     "标签栏在状态条下方，活动标签用强调色文字 + 2px 强调色下划线，非活动为次要文字色、无下划线、无底色。",
>     "标签切换只换内容区，状态条与标签栏不动；地址栏 hash 与活动标签一致。",
>     "设置不是标签页：从右侧抽屉打开，抽屉头部固定在顶部，关闭后回到原来的标签。",
>     "首运页与致命错误页是全屏覆盖层，覆盖期间不显示标签栏。"
- RULE-S40-32 SRC40:1393-1393 · release=2026-09-11 视觉修复计划（cross-exam 0908 B） / platform=unknown / role=all / condition=all
> `pure/tab_hash.js` 导出 `initialTab(hash)`，对不在白名单内的值一律返回 `"chat"`（done, delegates to existing `tabFromHash`). `main.js` 启动时改用它，并在首运结束后显式 `location.hash = "#tab=chat"` — **BLOCKED**: `main.js` is owned by lane B-core; this lane owns only `pure/tab_hash.js` and `tests/js/main_hash.test.js`. Main session must wire `main.js` line 52 (`showTab(tabFromHash(...))`) to call `initialTab` instead and set `location.hash = "#tab=chat"` after first run.
- RULE-S53-21 SRC53:181-184 · release=visual-baseline 待冻结稿（用户 2026-10-14 逐类确认） / platform=unknown / role=all / condition=all
>     "标签栏在状态条下方，活动标签用强调色文字 + 2px 强调色下划线，非活动为次要文字色、无下划线、无底色。",
>     "标签切换只换内容区，状态条与标签栏不动；地址栏 hash 与活动标签一致。",
>     "设置不是标签页：从右侧抽屉打开，抽屉头部固定在顶部，关闭后回到原来的标签。",
>     "首运页与致命错误页是全屏覆盖层，覆盖期间不显示标签栏。"
- RULE-S54-01 SRC54:7-10 · release=interaction-baseline 待冻结稿（用户 2026-10-14 确认） / platform=macOS / role=all / condition=all
>     "Tab 遍历界面里每一个控件——包括按钮，而不只是链接与输入框（WebKit 默认跳过按钮，外壳用 tabFocusesLinks 打开）。",
>     "⌘, 打开设置抽屉，不论当前在哪个标签；再次触发或点关闭回到原标签。",
>     "点标签切换页面时地址栏 hash 同步改变，直接改 hash 也切换页面。",
>     "媒体库的「在访达中显示」打开文件夹，不自动播放也不自动打开文件。"
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：标签页 hash 路由是正式行为（取代 ui 设计 A4）；刷新时按 hash 恢复标签

### RC19 · version_conflict · 已澄清
共同条件：前端本机状态持久化；ui 设计 2026-08-31，素材库预览 2026-09-30
ui 设计写前端不做缓存持久化、无 localStorage 依赖（图片会话 D-63 也规定当前会话不用浏览器存储）；素材库预览规定视图/筛选/缩略图大小/排序记在 localStorage lmd.library
待确认：前端是否允许用 localStorage 记忆界面偏好？ui 设计「无 localStorage 依赖」是否只针对会话与历史数据？
- RULE-S22-21 SRC22:256-258 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> 前端唯一的「写」出口是 api.js；面板之间不直接互调，跨面板动作（回填切 tab）经 main.js。
> store.js 只保存 tick 的最新快照与当前会话 id，供各 pane 订阅；不做任何缓存持久化
> （会话与历史的持久化全在 library 模块，前端无 localStorage 依赖）。
- RULE-S32-L11 SRC32:36-36 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=素材库页
> - [L-11] 视图、筛选、缩略图大小、明细排序记在 `localStorage` 键 `lmd.library`（JSON）；读写都包 try/catch，读不到用默认值（缩略图、全部、200px、`ts desc`）；值非法时回落默认。缩略图大小滑块是普通 `input[type=range]`，方向键只调大小，不移动选中（L-31 只在条目区内生效）。
- RULE-S27-D63 SRC27:249-249 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-63] 当前会话的恢复（刷新页面或重启 app 后进入图片页）：优先选有 running 尝试的会话；否则选 `updated` 最新的会话。不用浏览器存储、不改地址栏 hash（与聊天页一致，状态只来自服务端）。同一次页面生命周期内切换 tab 再回来，当前会话不变。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：允许 localStorage 记忆界面偏好（视图、会话栏收起）；会话与历史数据不进 localStorage

### RC20 · behavior_conflict · 已澄清
共同条件：界面动效；视觉/交互基线（2026-10-14 用户确认稿，参考图含素材库预览弹层 vs-09）与素材库预览设计
视觉与交互候选及确认稿写只有抽屉与遮罩有 150ms 透明度过渡、列表/消息/标签切换没有动画；素材库预览规定预览弹层遮罩淡入、面板淡入+轻微缩放约 180ms
待确认：用户已确认「没有其它动效」：素材库预览弹层的 180ms 淡入+缩放是否须改为 150ms 仅透明度，还是确认稿 motion 类需补例外？
- RULE-S39-19 SRC39:210-211 · release=docs/visual @ 0d98e9e（候选 2026-09-16/17） / platform=unknown / role=all / condition=候选规则，未经用户确认
>     "只有抽屉与遮罩有动效：150ms ease 的透明度过渡。列表、消息、标签切换没有动画。",
>     "系统开启「减弱动态效果」时所有过渡与动画一律关闭。"
- RULE-S38-10 SRC38:52-53 · release=docs/visual @ 0d98e9e（候选 2026-09-16） / platform=unknown / role=all / condition=候选规则，未经用户确认
>         "抽屉与遮罩 150ms；没有其它动效，也没有加载骨架屏动画。",
>         "系统开启「减弱动态效果」时上述过渡关闭，功能不受影响。"
- RULE-S53-24 SRC53:222-223 · release=visual-baseline 待冻结稿（用户 2026-10-14 逐类确认） / platform=unknown / role=all / condition=all
>     "只有抽屉与遮罩有动效：150ms ease 的透明度过渡。列表、消息、标签切换没有动画。",
>     "系统开启「减弱动态效果」时所有过渡与动画一律关闭。"
- RULE-S54-05 SRC54:56-57 · release=interaction-baseline 待冻结稿（用户 2026-10-14 确认） / platform=unknown / role=all / condition=all
>     "抽屉与遮罩 150ms；没有其它动效，也没有加载骨架屏动画。",
>     "系统开启「减弱动态效果」时上述过渡关闭，功能不受影响。"
- RULE-S32-L44 SRC32:64-64 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=素材库页
> - [L-44] 动效：遮罩淡入、面板淡入+轻微缩放（180ms 左右）；全局 `prefers-reduced-motion` 规则生效。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：以确认基线为准：素材库预览弹层也只用 150ms 透明度过渡，不做缩放

### RC22 · needs_clarification · 已澄清
共同条件：H3 视频生成的内部预算数值
media 设计把 mlx-h3 --budget 固定为 70（仅一处定义）；视频画幅设计把「H3 内部 40 GiB 预算」作为提醒阈值，并以镜像测试锁定「预算 40」；底座与视频会话都声明不改 H3 --budget
待确认：「视频生成的 40 GiB 上限」与 commands.py 的 --budget 70 是否为同一量？若是，哪个数值正确；若不是，40 GiB 的来源是什么？
- RULE-S14-04 SRC14:54-54 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> H3_BUDGET_GB = 70   # mlx-h3 --budget，仅此一处
- RULE-S33-Z00c SRC33:16-16 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=视频页
> - [Z-00c] 不改整机内存的「警告 + 确认」（后端 `estimate_bytes` + `force`）；本次的预算提醒是 H3 内部 40 GiB 预算，另一回事，只提醒。
- RULE-S33-Z41 SRC33:55-55 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=视频页
> - [Z-41] H3 预算：`估算 = 27.0 + 1.4 × max(宽×高×帧数 ÷ (512×288×49) − 1, 0)` GiB，与 `memory_estimate.py` 同源；超过 40 时显示「按实测外推约需 N GiB，超过视频生成的 40 GiB 上限，可能中途失败。」（N 取整）。
- RULE-S33-Z04 SRC33:25-25 · release=2026-10-07 视频画幅 / platform=unknown / role=all / condition=视频页
> - [Z-04] 镜像测试：一个 Python 测试读出 JS 与 Python 两边的常量（32、256、1344、768×1344）和内存公式参数（27.0、1.4、草稿体积 512×288×49、预算 40），任何一边改了另一边不跟就失败。
- RULE-S28-B00d SRC28:48-48 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-00d] 不改 H3 `--budget`（属 budget 模块）。不设续写段数、成片时长上限。
- RULE-S30-V00c SRC30:24-25 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=视频页
> - [V-00c] 不改 H3 命令行、预算、耗时估算公式。
> - 台面未发布，不谈兼容。
用户于 2026-10-14T18:20:00+09:00：澄清为 40（推荐）
有效规则：H3 --budget 与「视频生成 40 GiB 上限」是同一量，有效值 40 GiB（desk/media/commands.py:8 与 video_size.js:90 现值）；media 设计的 70 已过时

### RC23 · version_conflict · 已澄清
共同条件：聊天消息列宽；修复计划 2026-09-11，用户更新 2026-09-15
修复计划 Task 1 把消息列与输入区上限定为 clamp(680px, 62vw, 1100px)；用户 2026-09-15 改选「消息列跟着窗口变宽」= min(对话区−48px, 1400px)，视觉候选与图片页布局沿用 1400/24
待确认：确认修复计划 Task 1 的 clamp(680px,62vw,1100px) 已被 2026-09-15 的 min(区宽−48px,1400px) 取代？
- RULE-S40-08 SRC40:111-119 · release=2026-09-11 视觉修复计划（cross-exam 0908 B） / platform=unknown / role=all / condition=all
> `desk/static/app.css`：把两处 `max-width:820px` 换成同一个可变上限。在文件顶部的 `:root` 变量块里加一行：
> 
> ```css
>   --chat-col: clamp(680px, 62vw, 1100px);
> ```
> 
> 第 52 行 `.messages` 与第 59 行 `.composer` 里的 `max-width:820px` 都改成 `max-width:var(--chat-col)`。
> 
> 理由：1440 窗口下 62vw ≈ 893px（留白 ≈ 24%，与参考图 21.7% 同档）；1920 下取上限 1100px（主区 1608px，留白 508px = 26.5%，进入 40% 以内）；900 窗口下取下限 680px 仍不挤压。
- RULE-S46-02 SRC46:15-15 · release=用户确认记忆 2026-09-15 / platform=unknown / role=all / condition=all
> **Update 2026-09-15:** after trying a ~1920px window the user rejected the centered narrow reading column (it left ~222px blank on each side) and chose "消息列跟着窗口变宽": message list and composer width = min(chat area − 48px, 1400px). Don't reintroduce a narrow centered chat column; the ≤40% side-whitespace cap from the 2026-09-13 baseline still applies at 2560.
- RULE-S39-06 SRC39:62-63 · release=docs/visual @ 0d98e9e（候选 2026-09-16/17） / platform=unknown / role=all / condition=候选规则，未经用户确认
>      "rule": "消息列表与输入区同宽同中心：宽度 = min(对话区宽 − 48px, 1400px)，未到上限时两侧各留 24px；到上限后居中，两侧留白合计不超过对话区宽的 40%（旧基线 L2 列宽子句按 2026-09-15 用户改选替换，L6 的 40% 上限原样保留）。",
>      "pinned": true,
- RULE-S27-D70 SRC27:278-278 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-70] `#pane-image` 与 `#pane-chat` 同构：左侧 `aside.sessions`（宽 248px，复用 `.sessions` 样式与 `card session` 卡片、`session-actions` 的改名/删除图标按钮），右侧 `.image-main` 占满剩余宽度，内容最大宽 1400px，外边距 24px（视觉基线）。`#pane-image` 原来的「表单 | 作业」两栏 grid 与右侧 `.job` 区块取消，作业展示移入时间线里的 running 卡片。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：修复计划的 clamp(680px,62vw,1100px) 已被 2026-09-15 的 min(区宽−48px,1400px) 取代

### RC24 · needs_clarification · 已澄清
共同条件：首运页内容列宽
修复计划 Task 2 定为 max-width:min(1100px, 100% − 48px)；视觉候选与 2026-10-14 确认稿写 min(1300px, 100% − 48px)
待确认：确认稿的 1300px 是否取代修复计划 Task 2 的 1100px（计划未标注被取代）？
- RULE-S40-09 SRC40:175-180 · release=2026-09-11 视觉修复计划（cross-exam 0908 B） / platform=unknown / role=all / condition=all
> `desk/static/app.css:124` 的 `.firstrun-wrap`：
> 
> ```css
> .firstrun-wrap{max-width:min(1100px,calc(100% - 48px));margin:0 auto;display:flex;flex-direction:column;gap:16px}
> .firstrun-wrap label{display:grid;gap:6px}
> .firstrun-wrap input:not([type=radio]){width:100%}
- RULE-S39-23 SRC39:94-94 · release=docs/visual @ 0d98e9e（候选 2026-09-16/17） / platform=unknown / role=all / condition=候选规则，未经用户确认
>      "rule": "首运页内容包在 max-width: min(1300px, 100% − 48px) 的居中列里。",
- RULE-S53-11 SRC53:95-104 · release=visual-baseline 待冻结稿（用户 2026-10-14 逐类确认） / platform=unknown / role=all / condition=all
>      "rule": "首运页内容包在 max-width: min(1300px, 100% − 48px) 的居中列里。",
>      "pinned": true,
>      "ends": {
>       "900": {
>        "empty": "两侧各 ≤ 24px"
>       },
>       "2560": {
>        "empty": "两侧各 ≤ 630px（内容列 1300px 居中）"
>       }
>      }
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：确认稿 1300px 取代修复计划的 1100px

### RC25 · needs_clarification · 已澄清
共同条件：状态条与菜单栏的内存读数格式
ui 设计状态条文案为「已用 X.X / 总 Y GB」（一位小数、GB）；修复计划要求菜单与网页状态条都改为整数 GiB 且两处必须同时改，但记录网页侧尚未改（一位小数）
待确认：内存读数统一为整数 GiB 还是一位小数？单位用 GB 还是 GiB？
- RULE-S22-09 SRC22:106-110 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - `desk_state.js` 纯函数 `renderState(deskState, memSnapshot) -> {memText, holderText, mediaText, nextText, tone}`：
>   - 内存显示 `已用 X.X / 总 Y GB（可用 Z GB）`，由快照字节数格式化，**不存在任何常量 128**；
>   - `holderText`：`空闲` / `LLM：<名称>` / `视频生成中` / `音乐生成中`；
>   - `nextText`：`可开下一件重活` 或 `不可：<机器可读原因的中文文案>`；
>   - `tone`: `ok | busy | error`，决定状态条配色。
- RULE-S20-11 SRC20:214-216 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
> - 菜单项：状态详情（禁用行：上表全文 + `内存 已用 x.x / 共 y GiB`，来自 `api:memorySnapshot`）、
>   分隔线、「打开窗口」（`showWindow`）、「退出」（`NSApp.terminate` ⇒ 走 `applicationWillTerminate` 收割）。
>   仅此四类，无更多菜单项（YAGNI）。
- RULE-S40-26 SRC40:1141-1149 · release=2026-09-11 视觉修复计划（cross-exam 0908 B） / platform=macOS / role=all / condition=all
> ```swift
>   switch kind {
>   case "llm": return "已加载 \(desk.holderDisplay ?? desk.holderLabel ?? "?")"
>   case "video", "music": return desk.holderDisplay ?? (kind == "video" ? "视频生成中" : "音乐生成中")
>   default: return "状态不可读"
>   }
> ```
> 
> `memoryMenuTitle` 的数值格式从 `%.1f` 改为 `%.0f`（N3：同屏三处读数因 0.4 GiB 抖动而不同，取整后一致）。同时把 web 侧 `pure/format.js` 里状态条的内存格式也改为整数 GiB，两处必须同时改，否则仍会出现 79 vs 79.4。
- RULE-S40-27 SRC40:1151-1151 · release=2026-09-11 视觉修复计划（cross-exam 0908 B） / platform=unknown / role=all / condition=all
> > **执行者注：** 状态条的内存文案实际由 `desk/static/js/pure/desk_state.js` 的 `renderState()` 内联拼出（局部 `gb = (n) => (n / GB).toFixed(1)`），并非走 `pure/format.js` 的 `formatBytes`——该文件不在本任务 owns 列表。已在 `format.js` 新增 `formatMemoryLine(used, total, available)`（取整 GiB，用法/取整方式与 Swift 侧 `memoryMenuTitle` 对齐，`tests/js/format.test.js` 覆盖），但 `desk_state.js` 尚未改为调用它，因此网页状态条本身此刻仍是一位小数——N3 在**菜单栏**一侧已修好，网页状态条一侧需要另一条拥有 `desk_state.js` 的泳道把 `gb()` 换成这个新函数才算全量修复。
- RULE-S40-10 SRC40:262-280 · release=2026-09-11 视觉修复计划（cross-exam 0908 B） / platform=unknown / role=all / condition=all
> 持有者文案：
> 
> ```js
>   const holderName = state.holder
>     ? (state.holder.kind === "llm" ? state.holder.label : MEDIA_LABEL[state.holder.kind])
>     : "无";
>   setPart(els.holder, `内存里：${holderName}`, holderName, doc);
> ```
> 
> `MEDIA_LABEL` 定义为 `{ video: "视频生成中", music: "音乐生成中" }`——注意这两句现在只出现在持有者部件里，右侧"媒体"部件改为只说忙闲（下一步）。
> 
> 媒体部件与可否开工部件：
> 
> ```js
>   setPart(els.media, `媒体：${mediaText}`, mediaText, doc);
>   setPart(els.next, nextText, nextShort, doc);
> ```
> 
> 其中 `nextText` 为 `"可开下一件重活"` / `"不可：媒体作业进行中"`，`nextShort` 为 `"可开工"` / `"忙"`。内存部件 `wide` 用现有完整文案，`narrow` 用 `已用 75.9/128 GiB`。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：内存读数用整数 GiB

### RC26 · exception_ambiguity · 已澄清
共同条件：只用 ffmpeg 的合成/配乐作业启动条件（2026-09-25/27 版本，R-media-05 未被改写）
R-media-05 要求任何重活占着 arbiter 时拒绝启动新作业、启动前必须成功取得许可；底座 compose 与配乐 soundtrack 不经 arbiter、不取许可，只查 media_busy
待确认：R-media-05 是否只适用于模型生成作业？ffmpeg-only 的 compose/soundtrack 作业豁免 arbiter 许可是否需要在 R-media-05 中写明例外？
- RULE-S15-05 SRC15:19-20 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=任何重活占着 arbiter
> - **R-media-05** 任何重活占着 `arbiter` 时拒绝启动新作业，拒绝带机器可读原因。
>   启动前必须成功取得许可（其副作用是卸掉 LLM），失败即失败。
- RULE-S14-01 SRC14:11-12 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> `media` 是 H3 文生视频与 Music 3 文生歌曲的**作业运行器**：一次至多一个作业，
> 启动前必须拿到 `arbiter` 许可，产出落 outputs 根，结束（成功/失败/取消）时写历史并释放许可。
- RULE-S28-B45 SRC28:194-194 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-45] 检查顺序：参数 → 会话 → parts → `media_busy` → ffmpeg 可用性 → 启动。**不经过** arbiter、模型检查、内存提醒（ffmpeg 开销小；符合「不要太严格」）。`force` 接受但无作用，保留只为前端统一重发逻辑。
- RULE-S28-B38b SRC28:181-181 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-38b] 重活许可在**模型子进程退出时**释放（拼接只用 ffmpeg，不该继续占着 arbiter 的内存额度挡住聊天加载）；`_finalize` 对已释放的许可不再释放（只释放一次）。compose 作业没有许可（B-45）。
- RULE-S31-S02 SRC31:24-24 · release=2026-09-27 视频配乐 3b / platform=unknown / role=all / condition=视频页
> - [S-02] 校验顺序：参数（`source` 字符串、`refs.soundtrack` 结构）→ 视频会话（必填，同 V-01）→ `source` 为本会话 done 且文件在的尝试（`segment_not_found` / `segment_missing`）→ 音乐引用解析（`ref_missing`「引用的音乐已不在」）→ `media_busy` → ffmpeg（503「需要 ffmpeg 才能拼接成片」）→ 启动。不走 arbiter、模型检查、内存提醒（同 B-45）。
- RULE-S41-03 SRC41:15-15 · release=用户确认记忆 2026-09-25 / platform=unknown / role=all / condition=all
> **How to apply:** new job kinds plug into `memory_estimate.estimate_bytes` soft-warning path; ffmpeg-only jobs skip memory checks; don't cap chain lengths for memory reasons. Related: [[project-visual-baseline-direction]]
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：R-media-05 只适用于模型生成作业；仅调 ffmpeg 的合成/配乐作业不经 arbiter 许可

### RC27 · version_conflict · 暂缓决定
共同条件：媒体作业启动前的模型完整度检查
media 设计规定不做模型完整度预检（权重不齐由子进程失败上报），e2e 据此默认铺 present；图片会话与媒体会话底座的启动顺序包含 model_incomplete → 409
待确认：媒体作业启动前是否做模型完整度预检？media 设计 Assumption 10 是否已被取代？
- RULE-S14-17 SRC14:364-365 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> 10. **media 不做模型完整度预检**：权重不齐由子进程失败如实上报（`exit_nonzero`）；
>     完整度是 resources 的职责，ui 在资源面板呈现。media 只对二进制/解释器缺失做快速拒绝。
- RULE-S3-03 SRC3:187-188 · release=2026-08-31 首版模块化 / platform=test harness / role=all / condition=all
> h3 / music3 条目默认铺 present（媒体流程不做完整度预检，media 设计 Assumption 10，
> 但资源面板会显示它们）。清单内容纯由 `FakeFetcher` 供给，manifest 缓存照常落
- RULE-S27-D20 SRC27:169-174 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-20] 校验与挂接顺序（`start_image_job` → `_start`）：
>   1. 参数校验（提示词、宽高、步数、种子、force）→ 400；
>   2. `session_id` 校验（D-18）→ 400 / 404；
>   3. 互斥 `media_busy` → 409；运行环境 `capability_missing` → 503；模型 `model_incomplete` → 409；arbiter 拒绝 → 409；内存警告 `insufficient_memory`（未 force）→ 409；
>   4. 启动子进程；`spawn_failed` → 500；
>   5. **子进程启动成功、`_state` 已为 running 之后**，在 `MediaService._lock` 内调用 `begin_attempt(session_id, attempt)`，`attempt.job_id` 为新作业号、`params` 为实际参数（含实际 seed）。
- RULE-S28-B32 SRC28:163-163 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-32] 校验与挂接顺序：参数 → 会话 → `continues`（§3.3）→ `refs`（§5）→ `_start` 的既有检查（`media_busy` → `capability_missing` → `model_incomplete` → arbiter → `insufficient_memory`）→ 若需拼接则检查 ffmpeg（§6）→ 启动子进程 → 成功后 `begin_attempt`。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）

### RC28 · version_conflict · 已澄清
共同条件：素材库成品列表与历史条目的媒体种类
library 设计成品扫描后缀限定 .mp4/.wav/.m4a/.webm、historyEntry.kind 为 video|music、spec 写列出视频/音频；图片会话要求删除会话后素材库仍能列出并打开 PNG，素材库预览条目 kind 含 image
待确认：library 的后缀集合与 kind 词汇是否已扩为包含 png/image？R-library-01「成品（视频/音频）」是否需改写？
- RULE-S9-05 SRC9:107-112 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - 扫描 `outputs_root` 一层，后缀 ∈ `{.mp4, .wav, .m4a, .webm}`（后两者兼容既有旧成品文件）；
>   目录不存在返回 `[]` 不报错。
> - 与 `HistoryStore.by_output()` 按文件名 join：有历史 → 取其 `kind/ts/id`；
>   无历史 → `orphan: true`，`kind` 按前缀推断（`h3-`→video、`music3-`→music、其余→file）。
>   历史里有、磁盘上没有的条目只出现在 `api:listHistory`（那是记录，不是成品）。
> - 排序 `ts` 降序。
- RULE-S9-02 SRC9:63-64 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
>   "kind": "video | music",
>   "status": "done | failed | cancelled",
- RULE-S10-02 SRC10:14-15 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **R-library-01** 列出成品（视频/音频），带时间、类别、字节数。列表来源同时覆盖历史记录与磁盘上的孤儿文件
>   （历史里没有但磁盘上有的成品也要看得见）。
- RULE-S27-D03 SRC27:32-32 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-03] 图片文件不进会话目录：仍由媒体作业写到 `outputs_root`（`qwen-image-<stamp>-<8hex>.png`），会话只存文件名。
- RULE-S27-D30 SRC27:207-207 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-30] 删除会话只删除 `image-sessions/<id>.json`。`outputs_root` 下的图片、`history.jsonl` 都不动；删除后 `GET /api/outputs` 与 `GET /api/history` 的结果与删除前相同，素材库仍能列出并打开这些图片。
- RULE-S32-L02 SRC32:27-27 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=素材库页
> - [L-02] 每条条目归一为：`{ key, kind: "image"|"video"|"music"|"file", status, ts, title, prompt, spec, duration_s?, width?, height?, bytes?, gen_s?, output?: name, missing: bool, entry?: 历史记录, error? }`。`key` 跨刷新稳定（L-32 靠它保持选中）：有文件用 `o:<文件名>`，否则 `h:<ts>:<kind>:<attempt_id 或空>`，同一次渲染内重复时追加 `#2`、`#3`。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：素材库成品含图片（png，kind image）；R-library-01「视频/音频」改读为「图片/视频/音频」

### RC29 · version_conflict · 已澄清
共同条件：图片会话视觉验收与取证（revision 1，status passed）与 2026-09-25 媒体会话底座
视觉验收与取证要求用 page.route 让 GET /api/image-sessions 返回 500；底座 B-21 规定仓库中不再有 /api/image-sessions 引用，接口改为 /api/media-sessions/{kind}
待确认：图片会话的视觉验收标准是否需要更新为 /api/media-sessions/image？revision 1 的 passed 状态在底座迁移后是否仍有效？
- RULE-S48-session-list-load-failed SRC48:772-793 · release=visual-acceptance-criteria（image-sessions rev1，status passed） / platform=unknown / role=all / condition=图片页；前置：Playwright page.route 让 GET /api/image-sessions 返回 500（需在证据里声明为 mock layer）
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
- RULE-S49-04 SRC49:410-410 · release=visual-evidence-requirements（image-sessions） / platform=test harness / role=all / condition=图片页
>       "data_precondition": "Playwright page.route 让 GET /api/image-sessions 返回 500（需在证据里声明为 mock layer）",
- RULE-S28-B21 SRC28:130-130 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-21] 接通要求：`runtime.py` 与 `desk/testing/harness.py` 都传 `media_sessions`；`/api/media-sessions/{kind}` 挂在生产路由与测试外壳路由上。仓库中不再有 `/api/image-sessions`、`ImageSessionStore`、`image_sessions_dir` 的引用。
- RULE-S28-B01 SRC28:57-57 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-01] 三个目录：`data_root/image-sessions`、`data_root/video-sessions`、`data_root/music-sessions`，由 `PathRoots.media_sessions_dirs: dict[kind, Path]` 给出（取代 `image_sessions_dir`）。互不可见。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：图片会话视觉验收标准按 /api/media-sessions/image 更新，revision 1 的 passed 不沿用

### RC30 · needs_clarification · 已澄清
共同条件：图片页视觉验收（AC-7）的截图证据来源
取证要求用 tests/e2e 的 Playwright（默认 Chromium）真实浏览器截图；用户确认的视觉方向记忆写 e2e 的 Chromium 截图不能作为 WKWebView 外观证据，素材库预览也要求另用 WebKit 核对
待确认：AC-7「在真实浏览器中截图」是否接受 Chromium 截图，还是必须用 WKWebView（探针取证）或 Playwright WebKit？
- RULE-S49-01 SRC49:4-14 · release=visual-evidence-requirements（image-sessions） / platform=test harness / role=all / condition=图片页
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
>   },
- RULE-S48-GSHOW SRC48:22-26 · release=visual-acceptance-criteria（image-sessions rev1，status passed） / platform=unknown / role=all / condition=图片页
>     "must_show": [
>       "左侧会话列表（「新会话」主按钮在最上）",
>       "右侧时间线与底部输入区（提示词输入框 + 「生成图片」主按钮 + 折叠的「高级参数」）",
>       "当前会话在列表中高亮（aria-current=true）"
>     ],
- RULE-S47-AC-7 SRC47:30-30 · release=image-sessions revision 1（confirmed 2026-09-24） / platform=unknown / role=all / condition=图片页
>         "在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误"
- RULE-S27-TAC-7 SRC27:412-412 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> | AC-7 | 在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误 | §7 全部、D-78；`.allforai/visual-qa/visual-acceptance-criteria.json` | image-session-verify |
- RULE-S46-03 SRC46:17-17 · release=用户确认记忆 2026-09-16 / platform=unknown / role=all / condition=all
> **Update 2026-09-16:** the frozen baseline files are GONE. `docs/cross-exam/` was dropped from the public tree (commit "chore: drop local review dumps from the public tree"), added to `.gitignore`, and is absent from git history and from disk (searched /Users/aa). Only fragments survive, quoted inside `docs/superpowers/plans/2026-09-11-cross-exam-0908-visual.md` and the 2026-09-14 recheck plans (rule ids K2, K4, L6…). A new visual acceptance therefore has to re-freeze the baseline by re-confirming the categories with the user — don't promise a re-run that "just reuses the old baseline". Candidates for all twelve categories were drafted from the code and committed at `docs/visual/*.candidate.json` (commit 064da3d), so the confirmation session starts from those, not from zero; `.gitignore` now tracks baselines and reports and ignores only `docs/cross-exam/**/evidence/` and recordings. Capturing the real app needs `LMD_PROBE_PORT` plus `scripts/visual-capture.py` — e2e's Chromium shots are not evidence for the WKWebView's look.
- RULE-S32-L53 SRC32:73-73 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=素材库页
> - [L-53] WebKit 核对：应用外壳是 WKWebView，而 e2e 默认跑 Chromium。视频首帧缩略图（`#t=0.1` + `preload="metadata"`）与悬停播放须另用 Playwright WebKit（本机已装 webkit-2272）跑一条用例确认能出首帧；不行则退回「视频图标 + 时长」占位并在本文件记下。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：界面截图证据须来自 WKWebView（探针取证），Chromium 截图只作辅助

### RC31 · needs_clarification · 已澄清
共同条件：图片页展开卡片上的按钮集合；视频会话 3a（2026-09-27）对图片页的增量
V-50 在图片卡片两个动作右侧新增「用这张生成视频」；D-74 规定展开卡片显示两个动作按钮，B-71 要求图片页 DOM 文本、按钮逐字不变，视觉验收全局禁止「视频页或音乐页的元素出现在图片页」
待确认：「用这张生成视频」按钮是否视为对 D-74/B-71 的认可例外？视觉验收中的「两个动作按钮」与全局禁止项是否需要更新？
- RULE-S30-V50 SRC30:73-73 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=视频页
> - [V-50] 图片卡片展开时，done 且图片在的卡片在两个动作右侧增加次级按钮「用这张生成视频」。点击：切到视频页，方式设为图生，首帧来源设为该图片的引用（`{kind:"image", session_id, attempt_id}`），首帧说明「首帧：图片会话「<标题>」第 N 次」，提示词不变，焦点到提示词。图片页其余行为不变（新增按钮不影响现有按钮与文案）。
- RULE-S27-D74 SRC27:282-282 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-74] 展开卡片额外显示：大图（宽度不超过时间线列宽、高度不超过 60vh，`object-fit: contain`，`alt` 为提示词）、完整提示词、「高级参数」折叠块（列出 宽度、高度、步数、种子 四项实际值，默认折叠）、两个动作按钮（次级按钮样式，「在这张基础上改」在左，「换个构图」在右；「生成图片」是页面唯一主按钮）。
- RULE-S28-B71 SRC28:254-254 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-71] 图片页改用该模块后，IS 全部 D-xx 仍成立；图片页 DOM 文本、按钮、文案逐字不变。
- RULE-S29-M04 SRC29:70-70 · release=2026-09-27 音乐会话 / platform=unknown / role=all / condition=音乐页
> - [M-04] **图片页零回归**：`tests/js/image_pane.test.js` 与 `tests/e2e/test_image_sessions.py`、`tests/e2e/test_image_flow.py` 的断言不改（只允许改 import 路径与挂载方式），全部通过。
- RULE-S48-GNOT SRC48:27-34 · release=visual-acceptance-criteria（image-sessions rev1，status passed） / platform=unknown / role=all / condition=图片页
>     "must_not_show": [
>       "主流程可见文字中出现「种子」一词（唯一例外：展开的「高级参数」折叠区内的标签与数值；本规则只适用于图片页，「素材库」页条目元数据中的「种子 N」按用户 2026-09-24 决定豁免，见设计 D-50a）",
>       "空白图片框：任何 <img> 的 naturalWidth 为 0、破图标，或没有图片的灰色/空占位框",
>       "页面横向滚动条（document.scrollingElement.scrollWidth > clientWidth）",
>       "按钮或会话标题文字被裁切（按钮 scrollWidth > clientWidth；省略号只允许出现在会话标题与提示词摘要）",
>       "元素互相遮挡（会话列表、时间线、输入区、弹层之外的任意两块可见区域重叠）",
>       "视频页或音乐页的元素出现在图片页"
>     ]
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：「用这张生成视频」是 V-50 认可的例外，不违反 D-74/B-71

### RC32 · needs_clarification · 已澄清
共同条件：未发布前提下的兼容/收编类需求（当前版本）
用户确认产品从未发布、没有需要兼容的既有行为、设计里不谈兼容与迁移；foundation 仍要求旧配置缺键补默认「不得因为旧配置缺键而崩」、未知键 round-trip「不丢新版本写入的键」，library 一次性收编旧 outputs/history.jsonl，packaging 卸载旧 LaunchAgent，foundation 收编既有 339G 权重
待确认：这些 2026-08-31 的兼容/收编要求是否仍需保留？「不谈兼容」是否只针对发布后存量行为，而不涉及收编用户已有的权重/数据？
- RULE-S42-01 SRC42:14-14 · release=用户确认记忆 2026-09-17 / platform=unknown / role=all / condition=all
> **Why:** LocalModelDesk 从未发布，没有存量用户、没有需要兼容的既有行为。
- RULE-S42-02 SRC42:19-20 · release=用户确认记忆 2026-09-17 / platform=unknown / role=all / condition=all
> **How to apply:** 改动现有子系统时，先问「这东西发布了吗、有人在用吗」。
> 没有就直接写对的设计，不谈兼容、不谈灰度、不谈行为不变。
- RULE-S25-02 SRC25:23-23 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> 本项目尚未发布，不存在需要兼容的存量行为。
- RULE-S6-03 SRC6:31-33 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **R-foundation-02** 配置持久化到 `<data root>/config.json`，字段至少含：
>   `models_root`、`outputs_root`、`first_run_done`、`gateway`（`enabled`/`host`/`port`）、`config_version`。
>   读取时缺字段用默认值补齐，不得因为旧配置缺键而崩。
- RULE-S5-10 SRC5:201-206 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **缺键补默认（R-foundation-02）**：`read_config` 对顶层与 `gateway` 子字典做
>   逐键合并——文件里有的键取文件值，缺的键取默认值；未知键忽略但在 `write_config`
>   时原样保留（round-trip 不丢新版本写入的键）。文件不存在 → 返回纯默认 +
>   `needs_setup=True`，**不创建文件**。
> - **损坏即报错**：`config.json` 存在但 JSON 解析失败 → 抛 `ConfigCorruptError`
>   （带文件路径与解析错误）。不静默重建、不回退默认——错误就是错误（见 §6 假设 A3）。
- RULE-S9-09 SRC9:180-185 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=数据根无历史且 outputs 根有历史
> **旧历史一次性收编（census A15，library 自己承担）**：构造时若
> `<data root>/history.jsonl` **不存在** 且 `<outputs root>/history.jsonl` **存在**
> （现状代码把历史写在 outputs 目录内；用户把 `outputs_root` 指回旧 outputs 目录即命中），
> 则把后者**逐字节复制**到数据根——只 copy，**绝不移动、绝不删除源文件**（outputs 目录
> 冻结不可动），复制经 同目录临时文件 + `os.replace` 落地。目标已存在则什么都不做
> （幂等；不合并、不覆盖用户已有新历史）。两个路径均来自 `pathRoots`，无硬编码。
- RULE-S16-07 SRC16:197-199 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
> 1. **卸 LaunchAgent**（吸收 census A11）：
>    `launchctl bootout gui/$(id -u)/com.aa.localmodeldesk`（容错 `|| true`）；
>    删 `<launch-agents-dir>/com.aa.localmodeldesk.plist`。
- RULE-S6-05 SRC6:37-40 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **R-foundation-04** 收编既有权重：给定一个 legacy 根（如 `~/LocalModelDesk`），
>   `api:adoptLegacyModels` 识别其中的 `llms/`、`minimax-h3/`、`minimax-music3/`，
>   以「指向」（把 models_root 设成该目录）或「移动」两种方式接管，**任何情况下都不得重新下载、不得删除源**。
>   移动模式必须先校验目标卷剩余空间，不足则拒绝并说明差多少。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：收编用户已有权重/数据的要求保留；「不谈兼容」只指产品自身未发布的旧版本

### RC33 · needs_clarification · 已澄清
共同条件：聊天回答被停止/中断后的记录（同一聊天面板）
交互/视觉基线（2026-10-14 已确认）写停止或出错后会话摘要写明「已停止」或错误原因；确认的旅程 J2 要求 ⌘Q 重开后被停止那轮保留已生成部分并标示已停止（即需持久化）；修复计划规定被媒体作业打断的回复标为已中断，但该消息不写进会话历史
待确认：被媒体作业驱逐而中断的回答是否也按 J2 的停止处理（持久化已生成部分并标示）？修复计划「不写进会话历史」是否只适用于无正文的半成品？
- RULE-S38-05 SRC38:22-23 · release=docs/visual @ 0d98e9e（候选 2026-09-16） / platform=unknown / role=all / condition=候选规则，未经用户确认
>         "发送后立刻出现助手占位并开始流式输出；期间发送按钮变「停止」，点它当场停下并保留已生成的内容。",
>         "停止或出错后，会话摘要写明「已停止」或错误原因，不留一条既无内容又无说明的回答。",
- RULE-S39-17 SRC39:184-188 · release=docs/visual @ 0d98e9e（候选 2026-09-16/17） / platform=unknown / role=all / condition=候选规则，未经用户确认
>     "任务状态一行字带前缀符号：完成「✓」用成功色，失败「✕」用危险色，进行中用进行色，不靠颜色单独表达。",
>     "错误分两处：表单级用危险色纯文字（空时折叠），任务级用带描边的错误块，详情折在 details 里。",
>     "空列表显示虚线框 + 居中次要文字，不显示空白区域。",
>     "长任务显示 6px 高进度条，进度条颜色用进行色；日志区最高 240px 后自己滚。",
>     "生成中发送按钮变成「停止」，停止后摘要显示「已停止」，不留一条无内容的回答。"
- RULE-S54-02 SRC54:20-23 · release=interaction-baseline 待冻结稿（用户 2026-10-14 确认） / platform=unknown / role=all / condition=all
>     "发送后立刻出现助手占位并开始流式输出；期间发送按钮变「停止」，点它当场停下并保留已生成的内容。",
>     "停止或出错后，会话摘要写明「已停止」或错误原因，不留一条既无内容又无说明的回答。",
>     "长耗时动作（下载、生成）显示进度与可取消入口；取消后状态回到可再次开始，不需要刷新。",
>     "危险动作（删除会话、删除模型）先弹确认对话框，默认焦点不在危险按钮上。"
- RULE-S53-22 SRC53:194-198 · release=visual-baseline 待冻结稿（用户 2026-10-14 逐类确认） / platform=unknown / role=all / condition=all
>     "任务状态一行字带前缀符号：完成「✓」用成功色，失败「✕」用危险色，进行中用进行色，不靠颜色单独表达。",
>     "错误分两处：表单级用危险色纯文字（空时折叠），任务级用带描边的错误块，详情折在 details 里。",
>     "空列表显示虚线框 + 居中次要文字，不显示空白区域。",
>     "长任务显示 6px 高进度条，进度条颜色用进行色；日志区最高 240px 后自己滚。",
>     "生成中发送按钮变成「停止」，停止后摘要显示「已停止」，不留一条无内容的回答。"
- RULE-S51-J2 SRC51:3-9 · release=旅程声明（用户 2026-10-14 确认） / platform=macOS dist app / role=日常用户 / condition=聊天模型已下载、可能已加载
> ## J2
> - who: 日常用户（单人在自己的 Mac 上用本地模型聊天）
> - circumstance: 模型目录里已下载聊天模型，app 正常在跑，可能已有聊天模型加载着（同此刻的真实状态）；在一个会话里连续问至少 3 轮、每条用户消息约 30 字，其中一轮回答中途按停止；然后 ⌘Q 退出 app 再打开
> - progress: 这段对话在重启后完整保留，并能在其中继续聊
> - preconditions: dist/LocalModelDesk.app 在跑（127.0.0.1:8766）；模型目录里至少有一个已下载完整的聊天模型
> - done_looks_like: 重开 app 后会话列表里有这段会话；打开它，所有轮次的用户消息与回答都在，被停止那轮保留已生成部分并标示已停止；重开后在该会话再发一条能得到回答
> - stuck_looks_like: 发送后超过 60 秒既无回答也无任何状态文字；停止后无法再发送；重开后会话不见或消息缺失；出现服务失联
- RULE-S40-31 SRC40:1331-1348 · release=2026-09-11 视觉修复计划（cross-exam 0908 B） / platform=unknown / role=all / condition=all
> 在流式错误/连接中断的收尾处（`stream.js` 的 error 回调进到 `chat.js` 的地方）加：
> 
> ```js
>   function interrupt(error) {
>     const why = error?.code === "evicted" ? "已中断：内存让给了媒体作业" : "已中断";
>     summary.textContent = why;
>     details.open = false;
>     if (!state.content) {
>       const note = doc.createElement("p");
>       note.className = "empty-answer";
>       note.textContent = "这条回答没有生成完，可重新发送。";
>       body.replaceChildren(note);
>     }
>     setComposerBusy(pane, false);
>   }
> ```
> 
> 并确保这条消息**不写进会话历史**（`send()` 的 push 只在正常结束时执行），避免把半成品持久化。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：被媒体作业驱逐而中断的回答按「停止」处理：持久化已生成部分并标示；无正文的半成品不写入

### RC34 · exception_ambiguity · 暂缓决定
共同条件：收编既有权重 move 模式、源与目标同卷（2026-08-31 同版本）
R-foundation-04 与设计总则写任何情况下不得删除源；同一设计的 move 同卷分支对子树 os.rename 到目标，执行后源侧子树消失（设计视其为不复制不删除）
待确认：同卷 move 的 rename 是否被视为满足「不得删除源」？「不得删除源」是否只禁止删除数据而不禁止移走路径？
- RULE-S5-13 SRC5:234-236 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> （R-foundation-04）识别 `legacy_root` 下的 `llms/`、`minimax-h3/`、`minimax-music3/`
> 三个子树（存在且为目录即认）；一个都没有 → `LegacyRootError`。
> **任何模式、任何分支都不重新下载、不删除源数据。**
- RULE-S6-05 SRC6:37-40 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **R-foundation-04** 收编既有权重：给定一个 legacy 根（如 `~/LocalModelDesk`），
>   `api:adoptLegacyModels` 识别其中的 `llms/`、`minimax-h3/`、`minimax-music3/`，
>   以「指向」（把 models_root 设成该目录）或「移动」两种方式接管，**任何情况下都不得重新下载、不得删除源**。
>   移动模式必须先校验目标卷剩余空间，不足则拒绝并说明差多少。
- RULE-S5-14 SRC5:240-251 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=mode=move
> - **move 模式**：`target_root` 缺省为 `data_root/models`。步骤：
>   1. 拒绝 `target_root` 等于或位于 `legacy_root` 之内（`Path.is_relative_to`）；
>   2. 逐子树统计字节数（`os.walk` 累加 `st_size`，不跟随符号链接）；
>   3. 判同卷：比较 `legacy_root` 与 `target_root`（先 mkdir）的 `st_dev`；
>   4. **同卷** → 空间检查恒过（rename 不占新空间），对每个子树
>      `os.rename(src, target_root/<name>)`；目标已存在同名非空目录 → 该子树抛
>      `AdoptConflictError`（不合并、不覆盖）；
>   5. **跨卷** → 先查 `shutil.disk_usage(target_root).free`，`free < total_bytes + 1GiB
>      安全余量` → 抛 `InsufficientSpaceError`，消息含 需要/可用/差额 三个字节数；
>      足够则逐文件复制（`copy2` 保时间戳；已存在且字节数一致的目标文件跳过，
>      使中断后重试可续）；**复制完成后源目录保持原样不删**，结果里注明
>      `source_retained=True` 由用户自行回收；
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）

### RC35 · scope_dependency · 已澄清
共同条件：skill 选中状态的会话级持久化（skills 2026-09-23 与 library 会话存储 2026-08-31）
R-skill-15 要求 skill 选中状态（含附件勾选）随会话存档；library 的 updateChatSession 只允许 title/model/messages，其他键 ValidationError
待确认：skill 选中状态存在会话文件的哪个字段？library 会话 patch 白名单是否需扩充？
- RULE-S26-15 SRC26:163-166 · release=2026-09-23 skills / platform=unknown / role=all / condition=all
> - **R-skill-15** 选中状态（含附件勾选）是**会话级**的，随会话存档。
> 
>   附件勾选不写回 skill 目录——自带目录是只读的（R-skill-07），写回会在那里破功；而且
>   同一个 skill 在不同会话里想带的附件本就可以不同。
- RULE-S9-08 SRC9:160-172 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - 每会话一个文件 `sessions/<id>.json`；`id` 由 library 生成（`uuid4().hex`），
>   `update`/`delete` 先用 `^[0-9a-f]{32}$` 校验 id，不匹配按不存在处理（顺带杜绝路径注入）。
> - **写入原子**：同目录临时文件 + `os.replace`（与 R-foundation-06 同款手法）；
>   序列化失败时旧文件完好。Store 内一把 `threading.Lock` 串行化写。
> - `create`：生成 id、`created`/`updated`、空 `messages`；`title` 缺省 `"新会话"`；落盘后返回。
> - `update`：patch 允许键 `title`（重命名）、`model`、`messages`（整体替换）；
>   其他键抛 `ValidationError`；`messages` 必须是 list（内部结构 library 不解释，原样存）；
>   每次 update 刷新 `updated`。id 不存在抛 `NotFoundError`——**不静默新建**。
> - `delete`：删除该文件即删除持久化（R-library-06 后半）；id 不存在抛 `NotFoundError`。
> - `list`：读目录下全部 `*.json`，返回**完整** `data:chatSession` 对象数组，按 `updated`
>   降序——前端切换会话直接用 list 结果，无需单独 get 接口（registry 无 get；见 Assumptions）。
>   某文件损坏时返回 `{"id": "<文件名>", "corrupt": true}` 占位——不隐藏、不伪造、不整表失败。
> - 「重启后仍在」：状态全在磁盘，Store 无内存缓存，重新构造对象读同一目录即还原（R-library-06）。
- RULE-S10-06 SRC10:21-22 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **R-library-05** 多会话聊天：新建、列出、切换、重命名、删除。
> - **R-library-06** 每个会话持久化其消息、所用模型、更新时间；重启后仍在。删除会话即删除其持久化文件。
用户于 2026-10-15T06:23:45+09:00：澄清（推荐）
有效规则：skill 选中状态（含附件勾选）存在会话文件的 skills 字段；会话 patch 白名单为 title/model/messages/skills（desk/library/sessions.py:16）；library 文档的三键白名单视为过时。

### RC36 · scope_dependency · 暂缓决定
共同条件：视频配乐 3b 对媒体会话尝试记录的扩展
底座规定 params 按 kind 白名单保存（白名单外不写入），第 3 块新增参数须在其 spec 中扩充白名单，op 只列 generate|compose；配乐设计 params 记 mode=music_ref、audio_start、ref_image，并新增 op=soundtrack，但未写明扩充白名单与 op 枚举
待确认：audio_start、ref_image 是否已加入 video 白名单？op 枚举是否正式加入 soundtrack？
- RULE-S31-S13 SRC31:36-36 · release=2026-09-27 视频配乐 3b / platform=unknown / role=all / condition=视频页
> - [S-13] 命令：`build_h3_command(..., ref_image=<path>, ref_audio=<path>)` 追加 `--ref-image <path> --ref-audio <path>`（H3 Ref2VA，spike 已验证可跑）。`params` 记 `mode="music_ref"`、`audio_start`、`ref_image`（上传 id 或 null），尝试 `refs` 记引用。
- RULE-S31-S05 SRC31:27-27 · release=2026-09-27 视频配乐 3b / platform=unknown / role=all / condition=视频页
> - [S-05] 尝试：`op = "soundtrack"`，`params = {"source": <attempt_id>}`，`refs = {"soundtrack": <music ref>}`，`continues = null`；成功 `output` 为 `h3-soundtrack-<stamp>-<8hex>.mp4`；失败 `failed` + `join_failed`，未完成时删除半成品（同合成）。
- RULE-S28-BWL SRC28:97-101 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> | kind | 白名单 | 标题来源 |
> |---|---|---|
> | image | `prompt, width, height, steps, seed` | `prompt` |
> | video | `prompt, width, height, frames, steps, seed, mode, use_audio, first_frame, last_frame, ref_video` | `prompt` |
> | music | `caption, lyrics, duration, seed` | `caption` |
- RULE-S28-B06 SRC28:87-87 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-06] `params` 按 kind 的白名单保存（§1.4），白名单外的键不写入。`seed` 一律是实际使用的值。
- RULE-S28-B13 SRC28:103-103 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-13] video/music 的白名单是**现有**生成参数加 `seed`；第 3 块若新增参数（如参考图、参考音频）在其 spec 中扩充白名单。
- RULE-S28-B05 SRC28:86-86 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-05] `op`：`generate` 为模型生成；`compose` 为手动合成（§4）。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）

### RC37 · version_conflict · 已澄清
共同条件：视频面板/流程与素材库回填视频的验收；e2e 与 ui 为 2026-08-31，视频会话 2026-09-27
e2e 设计断言视频表单 prompt/画幅/帧/步与回填五字段 prompt/width/height/frames/steps，ui 规定视频面板含「帧数」；视频会话删除原表单+jobview，输入区改为生成方式、视频时长（六档）等，回填改为打开原会话执行「在这段基础上改」，并要求把旧视频页 e2e 迁到新页面「保持意图」
待确认：R-e2e-06/09 与 R-ui-03 中「帧数」字段与「回填进对应表单逐字段」的断言是否改为会话页的时长档与会话回填？
- RULE-S3-07 SRC3:305-305 · release=2026-08-31 首版模块化 / platform=test harness / role=all / condition=all
> | test_video_flow.py | R-e2e-06 | 填 prompt/画幅/帧/步 → 生成 → 逐闸放行进度行，`<pre>` 日志增量出现「step 1/10」「step 5/10」→ Exit(0) 后 `<video controls>` 出现且 `src` 含 `h3-<FixedClock stamp>.mp4`；`outputs_root` 下该文件存在且字节 == TINY_MP4；对 src 发 GET 得 200/206 |
- RULE-S3-09 SRC3:308-308 · release=2026-08-31 首版模块化 / platform=test harness / role=all / condition=all
> | test_library_panel.py | R-e2e-09 | 先跑一次快进视频作业 + 一次音乐作业（复用剧本，不闸停）→ 素材库两条目；点视频历史「回填」→ 切到视频面板，prompt/width/height/frames/steps **五字段逐一等于**启动参数；音乐同理三字段；点成品条目 → 播放器 `src` 指向 `/api/outputs/<name>` |
- RULE-S4-08 SRC4:44-45 · release=2026-08-31 首版模块化 / platform=test harness / role=all / condition=all
> - **R-e2e-06** 视频流程：填参数 → 启动 → 进度可见 → 完成后播放器出现且 `src` 指向新成品。
> - **R-e2e-07** 音乐流程：同上。
- RULE-S4-10 SRC4:48-48 · release=2026-08-31 首版模块化 / platform=test harness / role=all / condition=all
> - **R-e2e-09** 素材库：点历史项把当时参数回填进对应表单（逐字段断言）；点成品可播放。
- RULE-S22-14 SRC22:151-159 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - 表单：提示词（textarea）、画幅（预设下拉 512×288 / 768×448 / 1024×576，值即 `宽x高`）、
>   帧数、步数（number，min/max 沿用现行）。
> - 「生成」→ `api.startVideoJob({prompt, width, height, frames, steps})`；
>   被拒（arbiter 占用）→ 按钮下内联展示机器可读原因的文案。
> - 进行中：轮询 `api:jobStatus` 渲染 状态 + 滚动日志（`<pre>` 尾随滚动）+「取消」按钮
>   （`api.cancelJob()`）。
> - `data:jobState` 转 done 且有产出 → 就地 `<video controls>`，src 为
>   `api.outputUrl(name)`（`api:serveOutput` 的 URL，支持 Range 拖动由 library 模块保证）。
> - 失败 → 展示状态与原因，日志保留。
- RULE-S23-04 SRC23:18-19 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **R-ui-03** 视频面板：提示词、画幅、帧数、步数、进度、完成后就地播放。
> - **R-ui-04** 音乐面板：风格描述、歌词、时长、进度、完成后就地播放。
- RULE-S30-V20 SRC30:46-46 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=视频页
> - [V-20] 左栏会话、头部「生成视频」+ 模型状态 + 「模型说明」（MiniMax H3 · MLX 本机推理；输出带声音的 MP4；「接着往下生」用上一段的最后一帧作首帧，拼接处可能有动作跳变）、时间线、底部输入区。原表单 + jobview 删除。
- RULE-S30-V21 SRC30:47-47 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=视频页
> - [V-21] 输入区（自上而下）：提示条（V-30）；「生成方式」`<select>`（文生视频 / 图生视频 / 视频参考生成）；素材行（按方式出现，V-22）；提示词 `<textarea>`（默认 3 行，聚焦/超出时增高，最高 40vh；placeholder 随方式变化，沿用现有三条）与「生成视频」主按钮（⌘Enter）；「AI 帮写」行；「高级参数」`<details>` 默认折叠：画幅（现有三档）、视频时长（现有六档）、耗时提示（`videoCostNote`）、步数（默认 16，4–50）、种子（留空则每次随机）、「使用素材的声音」勾选（仅图生/参考方式可见，默认勾选）；上传状态行；状态行；错误行。
- RULE-S30-V61 SRC30:79-79 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=视频页
> - [V-61] 素材库回填视频条目：同 M-52（找得到会话 → 打开并执行「在这段基础上改」；否则按字段回填、提示条「沿用素材库里这段」）。
- RULE-S30-VE2E SRC30:90-90 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=视频页
> - e2e `tests/e2e/test_video_sessions.py`：生成（文生）→ 接着往下生 → 成片切换出现 → 在图片页「用这张生成视频」→ 视频页首帧说明正确 → 生成 → 会话文件 `refs.first_frame` 正确；挑两段合成；900×700 无横向滚动。现有操作旧视频页的 e2e（`grep -rln "data-video-" tests/e2e`）迁到新页面并保持意图。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：R-e2e-06/09 与 R-ui-03 的「帧数」「逐字段回填」改读为会话页的时长档与会话回填

### RC38 · version_conflict · 已澄清
共同条件：菜单栏媒体作业状态文案
R-shell-02 与 shell 设计的菜单栏文案为「出片中 / 出歌中」；修复计划为统一措辞改为「视频生成中 / 音乐生成中」
待确认：菜单栏媒体状态文案以「出片中」还是「视频生成中」为准？R-shell-02 是否随之改写？
- RULE-S20-10 SRC20:202-212 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
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
- RULE-S21-04 SRC21:17-17 · release=2026-08-31 首版模块化 / platform=macOS / role=all / condition=all
> - **R-shell-02** 菜单栏项显示实时台面状态（空闲 / 已加载 XX / 出片中），菜单含「打开窗口」与「退出」。
- RULE-S40-26 SRC40:1141-1149 · release=2026-09-11 视觉修复计划（cross-exam 0908 B） / platform=macOS / role=all / condition=all
> ```swift
>   switch kind {
>   case "llm": return "已加载 \(desk.holderDisplay ?? desk.holderLabel ?? "?")"
>   case "video", "music": return desk.holderDisplay ?? (kind == "video" ? "视频生成中" : "音乐生成中")
>   default: return "状态不可读"
>   }
> ```
> 
> `memoryMenuTitle` 的数值格式从 `%.1f` 改为 `%.0f`（N3：同屏三处读数因 0.4 GiB 抖动而不同，取整后一致）。同时把 web 侧 `pure/format.js` 里状态条的内存格式也改为整数 GiB，两处必须同时改，否则仍会出现 79 vs 79.4。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：菜单栏媒体状态文案以「视频生成中」为准，R-shell-02「出片中」随之改读

### RC39 · needs_clarification · 已澄清
共同条件：多件媒体作业（视频+音乐、图片+视频）能否并行
R-budget-07 规定「重活能否并存由预算判定」、fits 输入为一组且讨论三件共存；media 设计规定一次至多一个作业，图片会话保持单作业互斥 media_busy，compose 与生成共用 _state 互斥
待确认：预算判定的并存是否包括两件媒体作业同时运行？若不包括，R-budget-07 的「三件能否共存」指聊天+两件什么？
- RULE-S25-07 SRC25:42-43 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-budget-05** 修正的两个生效点必须区分：软触发（压缩阈值）立即生效；
>   硬边界（`--prompt-cache-bytes`）下次加载生效。二者不得混淆。
- RULE-S25-09 SRC25:51-54 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-budget-07** 重活能否并存由预算判定，预算不足时结果即互斥。
>   判定的输入是**一组**重活而非一对：`fits(workloads)`。三件能否共存不等于
>   三个两两判断的合取，「最小让出」也只有在集合上才算得出来。
>   拒绝必须带机器可读原因与数字：需要多少、现有多少、依据来源为预测还是实测。
- RULE-S14-01 SRC14:11-12 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> `media` 是 H3 文生视频与 Music 3 文生歌曲的**作业运行器**：一次至多一个作业，
> 启动前必须拿到 `arbiter` 许可，产出落 outputs 根，结束（成功/失败/取消）时写历史并释放许可。
- RULE-S14-06 SRC14:137-138 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - 服务生命周期内 `job_id` 单调递增；`idle` 时保留上一个作业的终态（前端能看到「上一单结果」）。
> - 同一时刻至多一个 `running`。
- RULE-S27-D00d SRC27:20-20 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-00d] 批量出图、排队、模型常驻不做；单作业互斥（`MediaService._start` 的 `media_busy`）保持不变。
- RULE-S28-B47 SRC28:196-196 · release=2026-09-25 媒体会话底座 / platform=unknown / role=all / condition=all
> - [B-47] compose 作业与生成作业共用 `_state`、互斥、`job_status`、轮询、取消、`close()`、history（`kind` 为 `video|music`，`params.op = "compose"`）、落定。成功 → `output` 为成品；失败 → `failed` + `join_failed`。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：两件媒体作业不并存；预算并存指聊天模型与一件媒体作业

### RC40 · needs_clarification · 暂缓决定
共同条件：can_start_heavy 与 acquire_heavy 的一致性要求（同一 budget spec）
R-budget-18 要求二者对同一请求给同一答案；R-budget-13 要求无参 can_start_heavy(kind) 只回答归属问题不做预算算术，而授予总要做预算判定
待确认：无参查询与带参授予是否算「同一请求」？界面无参查询答「能开」而授予因预算拒绝时是否违反 R-budget-18？
- RULE-S25-14 SRC25:95-95 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-budget-18** `can_start_heavy` 与 `acquire_heavy` 对同一个请求必须给同一个答案。
- RULE-S25-19 SRC25:134-143 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
> - **R-budget-13** **无参的 `can_start_heavy(kind)` 只回答归属问题，绝不做预算算术。**
> 
>   今天有六个调用点不传 `params`/`key`（下载闸、网关守卫、台面状态的两个按钮、两处测试台面）。
>   它们问的是「现在谁占着、能不能开这一类」，不是「这个具体作业装不装得下」——后者需要参数。
>   无参调用走预算算术时，`cost()` 拿不到输入只能产出 `bytes_needed=0` 且 `source=unavailable`
>   的空壳 workload，再撞上 R-budget-10（有一件 unavailable 就整组保守），**与机器多大无关地恒为
>   `insufficient_budget`**。已复现的后果：驻留模型后「换模型」按钮灰掉、下载可能被误拒、
>   网关对外返回的错误码从 `media_busy` 漂移成 `insufficient_budget`。
> 
>   两个问题必须有各自的入口：归属查询不吃参数、不碰内存数字；容量判定必须带参数，
- RULE-S25-15 SRC25:103-105 · release=2026-09-17 budget 改写 / platform=unknown / role=all / condition=all
>   所以：最小让出只需卸聊天模型时，查询也答「能开」，并在 `release` 里说明会让出谁
>   （界面据此讲「会先卸掉聊天模型」）。要腾掉正在跑的媒体作业时两者都答「不行」——
>   为了开另一件重活静默杀掉用户正在跑的生成，不是台面该替他做的决定。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）

### RC41 · version_conflict · 已澄清
共同条件：素材库条目点击行为；ui/e2e 2026-08-31，素材库预览 2026-09-30
R-ui-06 与 ui 设计写点击条目在面板内就地播放，e2e 断言点成品可播放；素材库预览取消顶部播放区，单击条目为选中、双击或 Enter 打开预览弹层
待确认：R-ui-06「点击播放」与 R-e2e-09「点成品可播放」是否改为「双击/Enter 打开预览后播放」？
- RULE-S22-18 SRC22:193-201 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - 进入面板取 `api:listOutputs` + `api:listHistory` 合并渲染为一个时间倒序列表：
>   历史条目显示 提示词摘要 / 类别 / 时间 / 耗时 / 规格，孤儿成品（磁盘有、历史无）
>   显示文件名并标注「无历史记录」。
> - 点条目：有产出文件 → 面板内播放器就地播放（`api.outputUrl(name)`）。
> - 「回填」按钮（仅有 params 的历史条目显示）：
>   `history_fill.js` 纯函数 `fillPlan(historyEntry) -> {pane: 'video'|'music', fields: {...}} | null`
>   —— `kind` 为视频 → `{prompt, width, height, frames, steps}`；音乐 →
>   `{caption, lyrics, duration}`；未知 kind / 无参数 → null（不显示按钮）。
>   main.js 据此切换 tab 并写入对应表单。
- RULE-S23-06 SRC23:22-22 · release=2026-08-31 首版模块化 / platform=unknown / role=all / condition=all
> - **R-ui-06** 素材库面板：成品与历史，点击播放，点击把当时的参数回填进对应表单。
- RULE-S4-10 SRC4:48-48 · release=2026-08-31 首版模块化 / platform=test harness / role=all / condition=all
> - **R-e2e-09** 素材库：点历史项把当时参数回填进对应表单（逐字段断言）；点成品可播放。
- RULE-S32-L00e SRC32:18-18 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=素材库页
> - [L-00e] 页面顶部的播放区（`[data-lib-player]`）取消；播放、预览都进预览弹层（缩略图视图音乐卡片的就地试听除外，见 L-24）。
- RULE-S32-L30 SRC32:53-53 · release=2026-09-30 素材库预览 / platform=unknown / role=all / condition=素材库页
> - [L-30] 每个条目的主体是一个 `<button data-lib-item>`（缩略图视图是整张卡片的媒体+文字区，列表是缩略图+文字区，明细是提示词单元格），`aria-label` 为标题；动作按钮（试听、预览、在访达中显示、回填）是它的兄弟节点，不嵌套在里面（避免交互元素嵌套）。单击主体 = 选中（`aria-current="true"` + 选中样式）；双击主体，或焦点在主体上按 Enter/空格 = 打开预览（`preventDefault`，不再额外触发选中之外的点击）。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：R-ui-06/R-e2e-09 的「点击播放」改读为「双击或 Enter 打开预览后播放」

### RC42 · needs_clarification · 已澄清
共同条件：窄窗验收档位；2026-10-14 确认的视觉基线与旅程 vs 图片/音乐/配乐设计与图片会话视觉验收
确认稿环境规定窗口最小高度 600，挤压旅程 J2/J5 取 900×600；图片会话设计与视觉验收的窄窗档是 900×700，音乐与配乐设计沿用 900×700
待确认：窄窗验收是否统一为 900×600？D-78、视觉验收 narrow 视口与 S-35 的 900×700 是否需改写？
- RULE-S53-25 SRC53:233-238 · release=visual-baseline 待冻结稿（用户 2026-10-14 逐类确认） / platform=macOS / role=all / condition=all
>     "只支持深色：color-scheme: dark 写死，没有浅色变体，也不跟随系统外观。",
>     "只打包简体中文，没有语言切换，也没有缺失 key 的回落。",
>     "字号只验 100%：app 内 WKWebView 未开页面缩放，全站固定像素字号。",
>     "只有横向桌面窗口一种方向，窗口可拉伸，宽度范围 900 至 2560，窗口最小高度 600。",
>     "指点设备只验鼠标：macOS 接鼠标时滚动条常驻并占位，界面据此把滚动条画成 8px 深色。",
>     "悬停才出现的控件（会话卡片操作）在无悬停时必须另有到达路径——键盘焦点即是。"
- RULE-S51-J2S SRC51:11-17 · release=旅程声明（用户 2026-10-14 确认） / platform=macOS dist app / role=日常用户 / condition=窗口 900×600
> ## J2-squeezed
> - who: 日常用户（单人在自己的 Mac 上用本地模型聊天）
> - circumstance: 模型目录里已下载聊天模型，app 正常在跑，可能已有聊天模型加载着（同此刻的真实状态）；在一个会话里连续问至少 3 轮、每条用户消息约 30 字，其中一轮回答中途按停止；然后 ⌘Q 退出 app 再打开；窗口取 900×600（普查 width_range.min × height_range.min）；每条用户消息取真实使用的最长内容：约 2000 字（约 60 行）
> - progress: 这段对话在重启后完整保留，并能在其中继续聊
> - preconditions: dist/LocalModelDesk.app 在跑（127.0.0.1:8766）；模型目录里至少有一个已下载完整的聊天模型；窗口调到 900×600；普查列了 chat-messages/chat-composer/sessions-list 滚动区：回答流式进行中截一张整页图
> - done_looks_like: 重开 app 后会话列表里有这段会话；打开它，所有轮次的用户消息与回答都在，被停止那轮保留已生成部分并标示已停止；重开后在该会话再发一条能得到回答
> - stuck_looks_like: 发送后超过 60 秒既无回答也无任何状态文字；停止后无法再发送；重开后会话不见或消息缺失；出现服务失联
- RULE-S51-J5S SRC51:27-33 · release=旅程声明（用户 2026-10-14 确认） / platform=macOS dist app / role=创作者 / condition=窗口 900×600
> ## J5-squeezed
> - who: 创作者（为短视频平台做内容）
> - circumstance: 视频模型在模型目录里，聊天模型可能仍加载着（同此刻）；新建一个视频会话，写一段约 80 字的中文提示词，选竖屏；窗口取 900×600；提示词取真实使用的最长内容：约 600 字（约 15 行）
> - progress: 得到一段可播放的竖屏视频并留在会话里
> - preconditions: dist/LocalModelDesk.app 在跑（127.0.0.1:8766）；视频生成模型已在模型目录；窗口调到 900×600；普查列了 media-timeline/video-composer/video-prompt/video-materials 滚动区：作业进行中截一张整页图
> - done_looks_like: 卡片显示完成且视频能播放；视频高大于宽；切走会话再回来视频仍在
> - stuck_looks_like: 点生成后无进度无提示；作业失败或报错；产出横屏或方形；进度超过 30 分钟不变
- RULE-S27-D78 SRC27:286-286 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-78] 窄窗 900×700：左栏仍 248px，右侧约 600px；卡片、输入区、按钮不出现横向滚动和文字截断（按钮文字不换行不裁切）；两个动作按钮放不下时换到下一行而不是被裁切。
- RULE-S48-VIEWPORTS SRC48:9-20 · release=visual-acceptance-criteria（image-sessions rev1，status passed） / platform=unknown / role=all / condition=图片页
>   "viewports": [
>     {
>       "id": "wide",
>       "width": 1280,
>       "height": 800
>     },
>     {
>       "id": "narrow",
>       "width": 900,
>       "height": 700
>     }
>   ],
- RULE-S29-M20 SRC29:100-100 · release=2026-09-27 音乐会话 / platform=unknown / role=all / condition=音乐页
> - [M-20] 左栏、主区宽度、外边距、窄窗 900×700 规则同 IS D-70、D-78。原 `.form | .job` 两栏与 jobview 删除。
- RULE-S31-S35 SRC31:51-51 · release=2026-09-27 视频配乐 3b / platform=unknown / role=all / condition=视频页
> - [S-35] 900×700：新增的素材在已有可滚动的素材区内（V 块 50vh 规则），不增加输入区固定行。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：窄窗验收统一为 900×600（窗口最小尺寸），900×700 的写法改读为 900×600

### RC43 · scope_dependency · 已澄清
共同条件：视频/音乐/图片页在最小窗口高度（600）下的结果卡片可见性
确认稿要求任何窗口高度下一张结果卡片的标题、媒体与操作行在结果区内可完整看到、不被输入区遮挡；各页设计让输入框随内容增高到 40vh/50vh、展开卡片媒体高到 60vh（图片）/50vh（视频），在 600px 窗口下二者之和可能超出结果区
待确认：最小高度下媒体与输入框的高度上限是否需要按确认稿重新约束（例如媒体高按结果区而非 vh 计）？
- RULE-S53-09 SRC53:79-79 · release=visual-baseline 待冻结稿（用户 2026-10-14 逐类确认） / platform=unknown / role=all / condition=all
>      "rule": "视频、音乐与图片页是上下排布：结果区（时间线）在上随窗口伸缩，输入区在下。任何窗口高度（最矮到窗口最小高度）下，一张结果卡片的标题、媒体与操作行都能在结果区内完整看到（可滚动到完整可见），不被输入区遮挡、不被结果区硬边永久截断；输入内容超长时只在输入框内滚动，页面不出现第二条滚动条。",
- RULE-S52-03 SRC52:5-5 · release=用户本 run 原话（2026-10-14） / platform=unknown / role=all / condition=all
> - 视频/音乐页排布：「照实际+高度规则」——结果区在上、输入区在下；任何窗口高度下一张结果卡片的标题、媒体与操作行可完整看到，不被输入区遮挡或被硬边永久截断；输入超长只在输入框内滚动，页面不出现第二条滚动条。
- RULE-S27-D74 SRC27:282-282 · release=2026-09-24 图片会话 / platform=unknown / role=all / condition=图片页
> - [D-74] 展开卡片额外显示：大图（宽度不超过时间线列宽、高度不超过 60vh，`object-fit: contain`，`alt` 为提示词）、完整提示词、「高级参数」折叠块（列出 宽度、高度、步数、种子 四项实际值，默认折叠）、两个动作按钮（次级按钮样式，「在这张基础上改」在左，「换个构图」在右；「生成图片」是页面唯一主按钮）。
- RULE-S30-V32 SRC30:60-60 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=视频页
> - [V-32] 展开 done：`<video controls preload="metadata">`（宽不超过时间线列宽，高不超过 50vh），有可用成片时默认播成片，「成片 | 只看这一段」切换（同 M-31）；续写链说明「由：第 1 次 → 第 3 次」；成片问题行与「重新拼接」（同 M-40–M-42）；首帧来源行（图生且有 refs.first_frame：「首帧：图片会话「<标题>」第 N 次」；标题取不到时「首帧：来自图片会话」）；完整提示词；「高级参数」折叠（画幅、时长、步数、种子）；动作按钮。
- RULE-S29-M21 SRC29:101-101 · release=2026-09-27 音乐会话 / platform=unknown / role=all / condition=音乐页
> - [M-21] 输入区：提示条（M-26）；风格描述 `<input>`（`placeholder` 沿用「例如：温柔的民谣，木吉他伴奏，女声轻唱，慢速」，`aria-label="风格描述"`）；歌词 `<textarea>`（`placeholder="歌词（必填）"`，默认 4 行，聚焦或内容超出时增高，最高 `50vh`，失焦且内容不超 4 行时回落）；「AI 帮写」行（原 `data-music-assist`）；主按钮「生成歌曲」（sparkles 图标，⌘Enter 等同点击）；「高级参数」`<details>` 默认折叠，内含「时长（秒）」（10–300，默认 60，下方保留提示「成品时长由模型按歌词决定，常短于所填时长；素材库会标注实际时长。」）与「种子（留空则每次随机）」；状态行 `role=status`；错误行 `role=alert`。
- RULE-S30-V21 SRC30:47-47 · release=2026-09-27 视频会话 3a / platform=unknown / role=all / condition=视频页
> - [V-21] 输入区（自上而下）：提示条（V-30）；「生成方式」`<select>`（文生视频 / 图生视频 / 视频参考生成）；素材行（按方式出现，V-22）；提示词 `<textarea>`（默认 3 行，聚焦/超出时增高，最高 40vh；placeholder 随方式变化，沿用现有三条）与「生成视频」主按钮（⌘Enter）；「AI 帮写」行；「高级参数」`<details>` 默认折叠：画幅（现有三档）、视频时长（现有六档）、耗时提示（`videoCostNote`）、步数（默认 16，4–50）、种子（留空则每次随机）、「使用素材的声音」勾选（仅图生/参考方式可见，默认勾选）；上传状态行；状态行；错误行。
用户于 2026-10-14T18:05:00+09:00：全部按建议（盘问官建议见 evidence/rules/decision-proposal-r2.md）
有效规则：以确认基线为准：最小高度下媒体与输入框高度须让一张结果卡片能完整可见，设计里的 vh 上限不构成例外

## 需求覆盖（基准 416 条，有裁决 12 条，无裁决 404 条）
- R-library-05 多会话聊天：新建、列出、切换、重命名、删除。 — 实证完成（J2 走得通吗？） · 实证完成（J2-squeezed 走得通吗？）
- R-library-06 每个会话持久化其消息、所用模型、更新时间；重启后仍在。删除会话即删除其持久化文件。 — 实证完成（J2 走得通吗？） · 实证完成（J2-squeezed 走得通吗？）
- R-llm-01 按目录 key 加载聊天模型：先向 `arbiter` 申请许可，再启动 mlx-lm 服务， 轮询健康直到就绪。状态可查：`idle` / `loading` / `loaded` / `error`。 — 实证完成（J2 走得通吗？） · 实证完成（J2-squeezed 走得通吗？）
- R-media-01 启动文生视频作业：提示词、画幅（宽高）、帧数、步数。H3 命令行的构造只存在一处。 — 实证完成（J5 走得通吗？） · 实证完成（J5-squeezed 走得通吗？）
- R-media-03 作业运行中可流式读取进度/日志输出。 — 实证完成（J5 走得通吗？） · 实证完成（J5-squeezed 走得通吗？）
- R-media-04 作业产出落在 outputs 根，文件名带时间戳（视频 `h3-<stamp>.mp4`，音频 `music3-<stamp>.wav`）， 并通过 `api:appendHistory` 记录一条含全部参数的历史。 — 实证完成（J5 走得通吗？） · 实证完成（J5-squeezed 走得通吗？）
- R-ui-01 前端是静态文件（`index.html`、`app.css`、ES 模块），由服务端供给； Python 源码里不再存在内联 HTML/CSS/JS 字符串。 — 缺口（视觉验收 v05-chat A · gap） · 实证完成（视觉验收 v05-chat A · done） · 缺口（视觉验收 v05-chat B · gap） · 实证完成（视觉验收 v05-chat B · done） · 缺口（视觉验收 v05-chat C · gap） · 实证完成（视觉验收 v05-chat C · done） · 缺口（视觉验收 v06-video A · gap） · 实证完成（视觉验收 v06-video A · done） · 缺口（视觉验收 v06-video B · gap） · 实证完成（视觉验收 v06-video B · done） · 缺口（视觉验收 v06-video C · gap） · 实证完成（视觉验收 v06-video C · done） · 缺口（视觉验收 v07-image-music A · gap） · 无法自证（视觉验收 v07-image-music A-mid · unprovable） · 缺口（视觉验收 v07-image-music B · gap） · 无法自证（视觉验收 v07-image-music B-mid · unprovable） · 缺口（视觉验收 v07-image-music C · gap） · 无法自证（视觉验收 v07-image-music C-mid · unprovable） · 缺口（视觉验收 v08-resources-library A · gap） · 无法自证（视觉验收 v08-resources-library A-mid · unprovable） · 缺口（视觉验收 v08-resources-library B · gap） · 缺口（视觉验收 v08-resources-library C · gap） · 无法自证（视觉验收 v09-dialogs 900x600@1 · unprovable） · 无法自证（视觉验收 v09-dialogs mid · unprovable） · 无法自证（视觉验收 v09-dialogs 1400x900@1 · unprovable） · 无法自证（视觉验收 v09-dialogs 2560x1440@1 · unprovable） · 实证完成（视觉验收 v10-settings A · done） · 无法自证（视觉验收 v10-settings A-mid · unprovable） · 缺口（视觉验收 v11-firstrun-fatal-shellerror A · gap） · 无法自证（视觉验收 v11-firstrun-fatal-shellerror A-mid · unprovable） · 缺口（视觉验收 v11-firstrun-fatal-shellerror B · gap） · 缺口（视觉验收 v11-firstrun-fatal-shellerror C · gap）
- R-ui-02 聊天面板：模型选择、加载/卸载、流式回复、思考过程可展开、左侧会话列表（新建/切换/重命名/删除）。 — 实证完成（J2 走得通吗？） · 实证完成（J2-squeezed 走得通吗？）
- R-ui-03 视频面板：提示词、画幅、帧数、步数、进度、完成后就地播放。 — 实证完成（J5 走得通吗？） · 实证完成（J5-squeezed 走得通吗？）
- Z-10 方向：`landscape` 横屏 / `portrait` 竖屏 / `square` 方形。 — 实证完成（J5 走得通吗？） · 实证完成（J5-squeezed 走得通吗？）
- Z-11 档位（名称 草稿 / 标准 / 清晰）：横屏 512×288、768×448、1024×576；竖屏为横屏宽高对调；方形 384×384、576×576、768×768。全部满足 Z-01。 — 实证完成（J5 走得通吗？） · 实证完成（J5-squeezed 走得通吗？）
- Z-12 方向控件在输入区主行，是分段控件（复用 `widgets/segment_switch.js`，`ariaLabel`「画幅方向」）；档位下拉在「高级参数」的「画幅」处，选项随方向变，末项「自定义…」。 — 实证完成（J5 走得通吗？） · 实证完成（J5-squeezed 走得通吗？）
- R-arbiter-01 聊天 LLM、视频生成、音乐生成三者互斥；持有者唯一，任何时刻至多一个重活。 获取与释放必须是进程内串行化的（锁），并发获取只能有一个成功。 ｜budget-spec 改写：重活能否并存由预算判定；预算不足时退化为互斥。持有者由单个变为一组。 — 无裁决（面 F14 未盘问）
- R-arbiter-02 真实内存快照：总量、已用、可用、内存压力，取自操作系统（macOS 上 `vm_stat` / `sysctl`）， **不得出现写死的 128 之类常量**。 — 无裁决（面 F14 未盘问）
- R-arbiter-03 按端口收割 LLM：找出监听 LLM 端口的**任何**进程并终止（先 TERM 后 KILL）， 包含本服务未曾 spawn 的孤儿。收割后必须确认端口确已释放才算成功。 — 无裁决（面 F14 未盘问）
- R-arbiter-04 媒体作业进行中拒绝加载 LLM；已有媒体作业时拒绝启动第二个媒体作业。拒绝必须带机器可读原因。 ｜budget-spec 改写：拒绝条件由「媒体在跑」变为「预算装不下」。 — 无裁决（面 F14 未盘问）
- R-arbiter-05 启动媒体作业前自动让出内存（卸掉 LLM）；让出失败必须导致启动失败，不得带着 LLM 硬上。 ｜budget-spec 改写：仅在预算不足时让出，且最小让出。 — 无裁决（面 F14 未盘问）
- R-arbiter-06 暴露单一台面状态对象：内存里是谁、媒体是否在跑、现在能不能开下一件重活， 以及若不能、为什么。这是状态条与菜单栏的唯一数据来源。 — 无裁决（面 F14 未盘问）
- R-arbiter-07 加载某模型前比对其体积与当前可用内存，装不下要在加载前给出警告（不是加载失败后才说）。 ｜budget-spec 改写：由加载时一次性检查，变为持续生效。 — 无裁决（面 F14 未盘问）
- R-foundation-01 所有路径由本模块单点解析，区分「只读 bundle 资源根」与「可写用户数据根」； 其他模块只能通过 `api:resolvePaths` / `data:pathRoots` 取路径，仓库内不得出现第二处 `Path.home()` 拼接模型或输出目录。 — 无裁决（面 F2 未盘问）
- R-foundation-02 配置持久化到 `<data root>/config.json`，字段至少含： `models_root`、`outputs_root`、`first_run_done`、`gateway`（`enabled`/`host`/`port`）、`config_version`。 读取时缺字段用默认值补齐，不得因为旧配置缺键而崩。 — 无裁决（面 F2 未盘问）
- R-foundation-03 首运语义：无配置或 `first_run_done` 为假时，`api:readConfig` 必须能表达 needs-setup 状态； `api:completeFirstRun` 接受一个选定的 models 根目录（默认 `<data root>/models`），校验可写后落盘并置 `first_run_done`。 目录不可写必须返回明确错误，不得静默回退到默认目录。 — 无裁决（面 F2 未盘问）
- R-foundation-04 收编既有权重：给定一个 legacy 根（如 `~/LocalModelDesk`）， `api:adoptLegacyModels` 识别其中的 `llms/`、`minimax-h3/`、`minimax-music3/`， 以「指向」（把 models_root 设成该目录）或「移动」两种方式接管，**任何情况下都不得重新下载、不得删除源**。 移动模式必须先校验目标卷剩余空间，不足则拒绝并说明差多少。 — 无裁决（面 F2 未盘问）
- R-foundation-05 服务在 `mlx-h3`、内嵌 venv、模型目录任一缺失时仍能启动并提供状态接口； 缺失作为可查询的能力状态暴露，**不得 `SystemExit`**（现状是缺 `mlx-h3` 就整个服务起不来，聊天跟着死）。 — 无裁决（面 F2 未盘问）
- R-foundation-06 配置写入原子：先写同目录临时文件再 `os.replace`；写到一半崩掉不得留下损坏的 `config.json`。 — 无裁决（面 F2 未盘问）
- R-gateway-01 `GET /v1/models`：OpenAI 格式，列出当前可服务的模型。没有模型驻留时返回空列表而非报错。 — 无裁决（面 F15 未盘问）
- R-gateway-02 `POST /v1/chat/completions` 非流式：OpenAI 请求与响应形状，含 `usage`、`finish_reason`。 — 无裁决（面 F15 未盘问）
- R-gateway-03 同端点流式：SSE，`data:` 分块与 OpenAI 增量格式一致，以 `data: [DONE]` 结束。 — 无裁决（面 F15 未盘问）
- R-gateway-04 `POST /v1/messages` 非流式：Anthropic 请求形状（`model`/`max_tokens`/`messages`/`system`） 与响应形状（`type:"message"`、`content` 块数组、`stop_reason`、`usage.input_tokens`/`output_tokens`）。 — 无裁决（面 F15 未盘问）
- R-gateway-05 同端点流式：发出 `message_start`、`content_block_start`、`content_block_delta`、 `content_block_stop`、`message_delta`、`message_stop` 事件，每个事件带 `event:` 与 `data:` 两行。 — 无裁决（面 F15 未盘问）
- R-gateway-06 Anthropic 的 `system`（字符串或块数组）、多轮 `messages`、`stop_reason` （`end_turn` / `max_tokens`）与 token 用量必须正确映射到底层结果。 — 无裁决（面 F15 未盘问）
- R-gateway-07 绑定 `0.0.0.0` 于配置端口，使同网络其他设备可达；开关关闭时不监听。 — 无裁决（面 F15 未盘问）
- R-gateway-08 无模型驻留或媒体作业进行中：返回 `503`，带 `Retry-After` 头与机器可读原因码。 **绝不自动加载模型，绝不排队等待。** — 无裁决（面 F15 未盘问）
- R-gateway-09 错误按各自方言的原生错误信封返回（OpenAI 的 `{"error":{...}}`； Anthropic 的 `{"type":"error","error":{"type":...,"message":...}}`）。不得伪造成功响应。 — 无裁决（面 F15 未盘问）
- R-gateway-10 请求里的 `model` 既接受目录 key，也接受当前加载模型的标识符； 与当前驻留模型不符时按 R-gateway-08 报错说明，不静默换模型。 — 无裁决（面 F15 未盘问）
- R-library-04 ：`list` 返回的 entry 里 `params` 原样在场，前端「再做一版」直接从 `api:listHistory` 的结果取 `params` 回填，无需第二个取回接口（registry 中也没有）。 — 无裁决（面 F13 未盘问）
- R-library-01 列出成品（视频/音频），带时间、类别、字节数。列表来源同时覆盖历史记录与磁盘上的孤儿文件 （历史里没有但磁盘上有的成品也要看得见）。 — 无裁决（面 F13 未盘问）
- R-library-02 提供成品字节流并支持 HTTP `Range`，返回 `206` 与正确的 `Content-Range`，使播放器可拖动。 路径必须限制在 outputs 根内，逃逸请求返回 404。 — 无裁决（面 F13 未盘问）
- R-library-03 每个作业追加一条历史：类别、提示词/全部参数、耗时、状态、产出文件名、时间戳。 追加是原子的、并发安全的（多线程同时追加不得写坏行）。 — 无裁决（面 F13 未盘问）
- R-library-07 历史与会话一律存于用户数据根之下，不得写进 bundle 或代码目录。 — 无裁决（面 F13 未盘问）
- R-llm-02 卸载当前模型，并确认 LLM 端口确已释放（走 `api:reapLlmPort`，不只是终止自己的子进程）。 — 无裁决（面 F4 未盘问）
- R-llm-03 流式对话：逐 token 输出正文增量，并把思考/推理增量（`reasoning_content` / `reasoning`） 作为独立字段与正文分开传给上层，不混在一起。 — 无裁决（面 F4 未盘问）
- R-llm-04 加载失败必须给出原因（mlx-lm 日志尾部），不得只报一个「加载超时」。 — 无裁决（面 F4 未盘问）
- R-llm-05 报出当前加载的是哪个模型及其元数据（视觉能力、量化、参数量、体积）。 — 无裁决（面 F4 未盘问）
- R-llm-06 媒体作业进行中、或当前没有加载模型时，聊天请求被拒绝并带明确原因，不得挂起等待。 — 无裁决（面 F4 未盘问）
- R-llm-07 对话必须经由本服务转发；前端与外部客户端都不直连 mlx-lm 端口。 — 无裁决（面 F4 未盘问）
- R-media-02 启动文生歌曲作业：风格描述、歌词、时长。Music 3 调用的构造只存在一处。 — 无裁决（面 F12 未盘问）
- R-media-05 任何重活占着 `arbiter` 时拒绝启动新作业，拒绝带机器可读原因。 启动前必须成功取得许可（其副作用是卸掉 LLM），失败即失败。 — 无裁决（面 F12 未盘问）
- R-media-06 作业失败记录失败与原因；**产出文件不存在时绝不报成功**（退出码 0 但无文件也算失败）。 — 无裁决（面 F12 未盘问）
- R-media-07 取消运行中的作业：终止子进程并释放 `arbiter` 许可，状态转为已取消。 — 无裁决（面 F12 未盘问）
- R-packaging-01 一个构建脚本从干净 checkout 产出 `LocalModelDesk.app`；步骤可重复，中途失败要报错退出而非产出半成品。 — 无裁决（面 F17 未盘问）
- R-packaging-02 包内自带 Python 运行时与全部依赖；产物不依赖 `/opt/homebrew` 或任何用户级 site-packages。 — 无裁决（面 F17 未盘问）
- R-packaging-03 `Info.plist` 含 bundle id、版本、图标、`LSMinimumSystemVersion`。 — 无裁决（面 F17 未盘问）
- R-packaging-04 用 Developer ID Application 证书签名，启用 hardened runtime 与时间戳； 内嵌的二进制与动态库一并签（由内向外）。 — 无裁决（面 F17 未盘问）
- R-packaging-05 构建自动验证：`codesign --verify --deep --strict` 通过， 并验证自包含性（包内不存在指向 `/opt/homebrew` 或 home checkout 的路径引用）。 — 无裁决（面 F17 未盘问）
- R-packaging-06 安装步骤把 App 放到 `/Applications`。 — 无裁决（面 F17 未盘问）
- R-packaging-07 卸载步骤移除 App 与旧的 `com.aa.localmodeldesk` LaunchAgent； 用户数据仅在显式选择时删除；**模型权重在任何情况下都不得被自动删除**。 — 无裁决（面 F17 未盘问）
- R-packaging-08 根目录旧脚本（`initModels.sh`、`run-h3.sh`、`run-music3.py`、`unload-llm.sh`）删除， 并验证其行为在 App 内均可达（目录/下载、H3、Music、卸模型各有对应接口）。 — 无裁决（面 F17 未盘问）
- R-packaging-09 README 改写为安装后的真实行为，含：不自启、菜单栏形态、模型目录位置与收编、 以及对外 API 监听 `0.0.0.0` 且无鉴权这一事实。 — 无裁决（面 F17 未盘问）
- R-resources-01 单一目录定义，供服务端、前端、以及任何 CLI 入口共同消费； 仓库内不得存在第二份模型 repo/路径清单（`initModels.sh` 与 `server.py` 里现有的两份都要消失）。 — 无裁决（面 F3 未盘问）
- R-resources-02 完整度以 HF 仓库文件清单为准：取得每个期望文件的路径与字节数， 逐个比对本地是否存在、大小是否一致。清单可缓存到 `<data root>` 以便离线复用，缓存失效时明确降级说明，不得假装校验过。 — 无裁决（面 F3 未盘问）
- R-resources-03 每项报出 `present` | `partial` | `missing`；`partial` 必须带完成百分比 （按字节，不是按文件数）与缺失/短缺文件列表。 — 无裁决（面 F3 未盘问）
- R-resources-04 报出每项实际占盘字节数，以及 models 所在卷的剩余空间。 — 无裁决（面 F3 未盘问）
- R-resources-05 对某一目录项发起下载；中断后再次发起必须续传，已完整的文件不得重下。 — 无裁决（面 F3 未盘问）
- R-resources-06 取消/暂停进行中的下载；已下载的部分必须保持可续传状态，不得清空。 — 无裁决（面 F3 未盘问）
- R-resources-07 下载进行时可查询实时进度：已完成字节/总字节、当前文件、速率、预估剩余。 — 无裁决（面 F3 未盘问）
- R-resources-08 删除某一目录项的权重并回收磁盘，需要显式确认参数（无确认参数一律拒绝执行）。 删除只允许发生在 models 根之下，路径逃逸必须拒绝。 — 无裁决（面 F3 未盘问）
- R-resources-09 同时至多一个下载在跑；`arbiter` 报告有重活（媒体生成）在跑时，下载必须拒绝启动并说明原因。 — 无裁决（面 F3 未盘问）
- R-shell-01 App 从 `Contents/Resources/` 内的内嵌运行时启动服务； Swift 源码中不得出现任何指向 home 下 checkout 目录的路径。 — 无裁决（面 F1 未盘问）
- R-shell-02 菜单栏项显示实时台面状态（空闲 / 已加载 XX / 出片中），菜单含「打开窗口」与「退出」。 — 无裁决（面 F1 未盘问）
- R-shell-03 关闭窗口不退出应用；App 留在菜单栏，服务继续存活；再次「打开窗口」能把窗口调回来。 — 无裁决（面 F1 未盘问）
- R-shell-04 退出时终止内嵌服务；不得留下孤儿进程（退出后台面端口不再有监听）。 异常终止路径（如 SIGTERM）也要清理。 — 无裁决（面 F1 未盘问）
- R-shell-05 Dock 图标存在，App 可被正常激活与切换（不是 LSUIElement）。 — 无裁决（面 F1 未盘问）
- R-shell-06 App 不注册任何登录项、不写任何 LaunchAgent plist。 — 无裁决（面 F1 未盘问）
- R-shell-07 首运弹出 models 目录选择（`NSOpenPanel`），并可选择收编既有目录树。 — 无裁决（面 F1 未盘问）
- R-shell-08 服务意外死亡时在界面上说明，而不是显示一个空白 WebView。 — 无裁决（面 F1 未盘问）
- R-ui-04 音乐面板：风格描述、歌词、时长、进度、完成后就地播放。 — 无裁决（面 F16 未盘问）
- R-ui-05 资源面板：每个模型显示 `齐` / `一半 N%` / `没下`、体积、实际占盘， 以及 下载 / 续传 / 取消 / 删除 控件；`partial` 要能看到缺哪些文件；显示卷剩余空间。 — 无裁决（面 F16 未盘问）
- R-ui-06 素材库面板：成品与历史，点击播放，点击把当时的参数回填进对应表单。 — 无裁决（面 F16 未盘问）
- R-ui-07 常驻状态条：真实内存（不是写死的 128）、内存里是谁、媒体是否在跑、现在能不能开下一件重活。 — 无裁决（面 F16 未盘问）
- R-ui-08 加载装不下的模型前弹出内存警告，确认后才继续。 — 无裁决（面 F16 未盘问）
- R-ui-09 首运界面：选择 models 目录，或收编一个既有目录树。 — 无裁决（面 F16 未盘问）
- R-ui-10 设置界面：对外 API 的开关、主机、端口，并显示可复制的 base URL （OpenAI 与 Anthropic 各一条），旁边注明当前是无鉴权监听。 — 无裁决（面 F16 未盘问）
- R-budget-01 每个额度必须标注来源 `predicted` / `measured` / `unavailable`， 在台面状态对象与诊断输出中可见。预测与实测不可混为一谈。 — 无裁决（面 F14 未盘问）
- R-budget-02 模型声明窗口按序读取：`text_config.max_position_embeddings` → 顶层 `max_position_embeddings` → 记 `unavailable`。**禁止读取 `vision_config`**。 三条顺序不得调整，不得回落成默认值。 — 无裁决（面 F14 未盘问）
- R-budget-03 冷启动额度由 `config.json` 推算（每 token 字节）与内存快照合成， 并据此向 mlx-lm 传入 `--prompt-cache-bytes` 与 `--prompt-cache-size`。 不传限额等于无上限，是当前的缺陷。 — 无裁决（面 F14 未盘问）
- R-budget-04 自校准：每轮完成后，由 mlx-lm 日志的 `Prompt Cache` 字节数除以 该轮 `usage.prompt_tokens`，得出本机该模型的实测每 token 字节，写入实测档案。 档案条目须记录权重大小，与 `ModelEntry.gb` 不符即作废重测。 — 无裁决（面 F14 未盘问）
- R-budget-05 修正的两个生效点必须区分：软触发（压缩阈值）立即生效； 硬边界（`--prompt-cache-bytes`）下次加载生效。二者不得混淆。 — 无裁决（面 F14 未盘问）
- R-budget-06 保留 `memory_estimate.estimate_bytes(kind, params)` 的按参数估算形式—— 按作业种类给一个数会让不同分辨率的作业共用同一个估值，这是它当初就修掉的缺陷。 新增的是**标定来源**：每次媒体作业运行期采样 `available_bytes`（启动前基线、 运行中最低点、结束差值）得到本机实测峰值，写入实测档案，用于修正该公式的常数项。 本机尚无实测记录时，沿用代码内写死的 2026-09-08 标定值，并标 `predicted`。 — 无裁决（面 F14 未盘问）
- R-budget-07 重活能否并存由预算判定，预算不足时结果即互斥。 判定的输入是**一组**重活而非一对：`fits(workloads)`。三件能否共存不等于 三个两两判断的合取，「最小让出」也只有在集合上才算得出来。 拒绝必须带机器可读原因与数字：需要多少、现有多少、依据来源为预测还是实测。 — 无裁决（面 F14 未盘问）
- R-budget-16 预算的分母是**机器自报的重活能力**，不是此刻的可用内存。 — 无裁决（面 F14 未盘问）
- R-budget-18 `can_start_heavy` 与 `acquire_heavy` 对同一个请求必须给同一个答案。 — 无裁决（面 F14 未盘问）
- R-budget-19 拒绝的理由是给人看的，不是给日志看的。 — 无裁决（面 F14 未盘问）
- R-budget-17 「能不能用这个模型」问的是**台面还持不持有它**，不是「有没有媒体作业在跑」。 — 无裁决（面 F14 未盘问）
- R-budget-13 **无参的 `can_start_heavy(kind)` 只回答归属问题，绝不做预算算术。** — 无裁决（面 F14 未盘问）
- R-budget-10 一组重活的依据来源取其中最弱者：只要有一件是 `unavailable`， 整组按 `unavailable` 处理并走保守路径。不得让「两件实测加一件未量过」 被当作实测依据放行。 — 无裁决（面 F14 未盘问）
- R-budget-08 预算判定「装得下」而实际触发内存压力时，该次失败必须落盘， 并永久收紧该组合的预算。系统必须从失败中学习，不只从成功中学习。 — 无裁决（面 F14 未盘问）
- R-budget-09 内存压力升高时，按代价从轻到重处置：① 收紧对话额度并立即触发压缩； ② 拒绝新的重活；③ 才是卸载模型或终止作业。压力传感器是兜底闸，不是决策者。 — 无裁决（面 F14 未盘问）
- R-budget-11 每 token 开销的推算只对标准 MHA/GQA 成立。config 中出现 MLA 标记（`kv_lora_rank` / `qk_nope_head_dim` / `v_head_dim`）或缺少显式 `head_dim` 时， 一律返回「算不出」走保守路径，**禁止用 `hidden_size // num_attention_heads` 推导**。 本机 glm-4.7-flash 即属此类：该推导会凑出 102（2048/20 = 102.4，连整数都不是）， 得出约 375 KB/token 而实际约 53 KB——高估 7 倍。一个看起来合理、实际错 7 倍的数， 比没有数更危险。自校准会在一轮之后填入真值。 — 无裁决（面 F14 未盘问）
- R-context-01 会话发送给模型的内容受预算约束：超过 `Budget.for_chat()` 给出的 触发点时，较早消息由一条结构化摘要替代，尾部若干轮保持原文。 保留轮数由预算反推（尾部与摘要之和不超过触发点的一半，且至少保留最近一轮完整问答）， 不得写死为常数——各模型每 token 开销相差一个数量级。 — 无裁决（面 F5 已盘问但无裁决引用它）
- R-context-02 摘要按固定模板填写，模板含且至少含：用户原始意图、关键概念、 涉及文件与代码、错误与修法、**用户历次发言逐条列出**、待办与当前工作。 不得使用开放式「总结一下」指令。 — 无裁决（面 F5 已盘问但无裁决引用它）
- R-context-03 压缩只影响发送内容，不影响存储与展示。会话文件保留全部原始消息， 用户在界面上始终可以看到每一条。 — 无裁决（面 F5 已盘问但无裁决引用它）
- R-context-04 压缩在两轮之间进行，使用当前驻留模型，不加载第二个模型。 压缩过程对用户可见（明确的进行中提示），不得静默阻塞。 — 无裁决（面 F5 已盘问但无裁决引用它）
- R-context-05 摘要作为一条 `role: "summary"` 的会话消息存在，记录其替换的消息区间， 可被用户编辑，亦可在原文基础上重新生成。 — 无裁决（面 F5 已盘问但无裁决引用它）
- R-skill-01 skill 是**指令，不是能力**。台面不执行 skill 里的任何东西：不跑脚本、 不发请求、不自动跟随它写的链接。skill 唯一的作用是把文字放进上下文。 — 无裁决（面 F6 未盘问）
- R-skill-02 **进模型的每个字都是原文，台面不转述。** — 无裁决（面 F6 未盘问）
- R-skill-03 **选中由用户完成，不由模型判断。** — 无裁决（面 F6 未盘问）
- R-skill-04 可同时开多个，按选中顺序拼接。 — 无裁决（面 F6 未盘问）
- R-skill-05 skill 的文字作为 `system` 消息排在最前，**永不参与压缩**。 — 无裁决（面 F6 未盘问）
- R-skill-06 **skill 的 token 占用必须可见。** — 无裁决（面 F6 未盘问）
- R-skill-07 两个来源，用户的覆盖自带的。 — 无裁决（面 F6 未盘问）
- R-skill-08 **坏的 skill 照样列出来，并写明坏在哪。** — 无裁决（面 F6 未盘问）
- R-skill-09 发现是显式的：启动时扫一次，外加一个「重新扫描」按钮。 — 无裁决（面 F6 未盘问）
- R-skill-10 附件不隐身。 — 无裁决（面 F6 未盘问）
- R-skill-11 从外部装：先看全文，再落盘，装完不启用。 — 无裁决（面 F6 未盘问）
- R-skill-12 **压缩的预算必须扣掉 skill 的占用。** — 无裁决（面 F6 未盘问）
- R-skill-13 **skill 必须落在 `sentChars` 的度量范围之内。** — 无裁决（面 F6 未盘问）
- R-skill-14 选中集合与可用集合必须对账。 — 无裁决（面 F6 未盘问）
- R-skill-15 选中状态（含附件勾选）是**会话级**的，随会话存档。 — 无裁决（面 F6 未盘问）
- R-skill-16 扫描产出**唯一一份已解析列表**，注入只读它。 — 无裁决（面 F6 未盘问）
- R-skill-17 安装**全部成功才落盘**，任何中断清掉暂存。 — 无裁决（面 F6 未盘问）
- D-01 图片会话目录 `PathRoots.image_sessions_dir = data_root / "image-sessions"`，与聊天会话目录 `data_root / "sessions"` 分开；两边的文件互不可见（`GET /api/sessions` 不列出图片会话，反之亦然）。 — 无裁决（面 F8 未盘问）
- D-02 每个会话一个文件 `<id>.json`，`id` 为 32 位小写十六进制（`uuid4().hex`，与 `SessionStore._ID_RE` 相同规则）。写入沿用 `SessionStore._write` 的方式：同目录临时文件 `.tmp-XXXX.part` + `os.replace`；列目录时跳过点开头的文件。 — 无裁决（面 F8 未盘问）
- D-03 图片文件不进会话目录：仍由媒体作业写到 `outputs_root`（`qwen-image-<stamp>-<8hex>.png`），会话只存文件名。 — 无裁决（面 F8 未盘问）
- D-04 `created` / `updated` / 尝试的 `ts` / `finished` 都用 `%Y-%m-%dT%H:%M:%S` 本地时间（与聊天会话一致）。 — 无裁决（面 F8 未盘问）
- D-05 `updated` 在以下时刻刷新：新建、重命名、追加尝试、尝试落定。切换查看会话不刷新 `updated`。 — 无裁决（面 F8 未盘问）
- D-06 `id` 是尝试自己的标识（`uuid4().hex`）。`job_id` 只是进程内作业计数（`MediaService._state["job_id"]`，重启后从 0 重数），仅用于把当前轮询到的作业对上 `running` 尝试，不作为持久标识。 — 无裁决（面 F8 未盘问）
- D-07 `params` 恰好五个键：`prompt`（字符串，原样保存，不截断）、`width`、`height`、`steps`、`seed`（都是整数）。`seed` 一律是**实际使用的值**，即使用户没填（随机）也记录生成时取到的那个数。 — 无裁决（面 F8 未盘问）
- D-08 各状态下字段取值： — 无裁决（面 F8 未盘问）
- D-09 `error.code` 取值与含义（`message` 是存进文件的原话，界面显示规则见 §7.5）： — 无裁决（面 F8 未盘问）
- D-10 新建会话 `title = "新会话"`、`title_auto = true`。 — 无裁决（面 F8 未盘问）
- D-11 会话追加**第一个**尝试时（`attempts` 为空且 `title_auto == true`），标题改为该尝试的提示词：连续空白折叠为一个空格、去首尾空白，长度超过 24 个字符时取前 24 个字符加「…」（与聊天 `displayTitle` 的 24 字规则一致）。之后的尝试不再改标题。第一个尝试失败或取消也照样取它的提示词。 — 无裁决（面 F8 未盘问）
- D-12 重命名后 `title_auto = false`，此后任何生成都不再改标题。 — 无裁决（面 F8 未盘问）
- D-13 重命名的标题：去首尾空白后 1–80 个字符；空串或超长 → 400，文件不变。 — 无裁决（面 F8 未盘问）
- D-14 **尝试记录只由后端写**：追加 `running` 尝试和落定都在 `MediaService` 里、通过 `ImageSessionStore` 完成；前端从不 PATCH 尝试。前端轮询丢包、页面刷新、窗口关闭都不会丢写。 — 无裁决（面 F8 未盘问）
- D-15 `ImageSessionStore` 的每个写方法在同一把 `threading.Lock` 内「读文件 → 改 → 原子写回」，不持有内存副本；所以作业线程的落定和 HTTP 线程的重命名/删除交错时互不覆盖（重命名后落定，标题保留；落定后重命名，状态保留）。 — 无裁决（面 F8 未盘问）
- D-16 接通要求（Closure）：`runtime.py` 与 `desk/testing/harness.py` 构造 `MediaService` 时都传 `image_sessions=library.image_sessions`；`GET /api/image-sessions` 挂在生产路由和测试外壳路由上。只有文件存在、没人调用不算完成。 — 无裁决（面 F8 未盘问）
- D-17 `attempt_count` 计所有状态的尝试；`running` 为该会话是否有 `status == "running"` 的尝试；`cover` 是最后一个 `done` 尝试的 `output`，没有则 `null`。目录不存在时返回 `[]`。 — 无裁决（面 F8 未盘问）
- D-18 `session_id` 必填。缺失或不是字符串 → 400 `{"error":{"code":"session_required","message":"请先选择或新建一个会话"}}`。会话不存在 → 404 `{"error":{"code":"session_not_found","message":"这个会话已被删除，请选择或新建一个会话"}}`。 — 无裁决（面 F8 未盘问）
- D-19 `seed` 可省略：省略时后端用 `secrets.randbelow(2**32)` 取随机值；不再有固定默认值 42（`start_image_job` 签名与 `routes.start_image` 里的 `seed=42` 默认都去掉）。给了就必须是 0–4294967295 的整数（现有校验）。 — 无裁决（面 F8 未盘问）
- D-20 校验与挂接顺序（`start_image_job` → `_start`）： 1. 参数校验（提示词、宽高、步数、种子、force）→ 400； 2. `session_id` 校验（D-18）→ 400 / 404； 3. 互斥 `media_busy` → 409；运行环境 `capability_missing` → 503；模型 `model_incomplete` → 409；arbiter 拒绝 → 409；内存警告 `insufficient_memory`（未 force）→ 409； 4. 启动子进程；`spawn_failed` → 500； 5. **子进程启动成功、`_state` 已为 running 之后**，在 `MediaService._lock` 内调用 `begin_attempt(session_id, attempt)`，`attempt.job_id` 为新作业号、`params` 为实际参数（含实际 seed）。 — 无裁决（面 F8 未盘问）
- D-21 第 1–4 步任何一步失败都**不写**会话文件：没有 running 尝试，也没有失败尝试（启动失败以错误提示的方式出现在输入区，见 §7.7）。 — 无裁决（面 F8 未盘问）
- D-22 200 响应是现有 `job_status()` 快照，外加 `"session_id"` 与 `"attempt_id"` 两个字段；`job_status()` 在该作业存续期间也带这两个字段（其他 kind 为 null），前端据此把轮询到的作业对上尝试卡片。 — 无裁决（面 F8 未盘问）
- D-23 `begin_attempt` 返回 False（会话恰好在第 2 步和第 5 步之间被删）时作业照常运行，结束后图片照常进素材库，不再写任何会话。 — 无裁决（面 F8 未盘问）
- D-24 落定点是 `MediaService._finalize`：在写 history 之后、调用回调之前，对本作业调用 `settle_attempt(session_id, attempt_id, …)`： — 无裁决（面 F8 未盘问）
- D-25 启动恢复：`LibraryService` 构造时调用一次 `image_sessions.recover_running()`，把上次进程遗留的 running 尝试改为 `failed` + `interrupted`。进程内任何时刻，会话文件里的 running 尝试只可能属于当前进程正在跑的那个作业。 — 无裁决（面 F8 未盘问）
- D-26 history 条目：图片作业的 history 条目增加顶层字段 `session_id` 与 `attempt_id`（未挂上会话时为 null）。素材库回填据此找回会话（§8.4）。 — 无裁决（面 F8 未盘问）
- D-27 前端看到轮询作业已不在 running、而当前会话里对应尝试仍是 running 时，重新 `GET` 该会话；仍是 running 就在下一次 2 秒轮询时再取，直到落定。前端从不自行把尝试标成完成或失败。 — 无裁决（面 F8 未盘问）
- D-30 删除会话只删除 `image-sessions/<id>.json`。`outputs_root` 下的图片、`history.jsonl` 都不动；删除后 `GET /api/outputs` 与 `GET /api/history` 的结果与删除前相同，素材库仍能列出并打开这些图片。 — 无裁决（面 F8 未盘问）
- D-31 删除一个有 running 尝试的会话：作业不取消，完成后图片进素材库，但不出现在任何会话里；history 条目里的 `session_id` 指向已不存在的会话（回填时按「不属于任何会话」处理，§8.4）。 — 无裁决（面 F8 未盘问）
- D-40 点击后：把该尝试的 `prompt` 填进提示词输入框，`width`、`height`、`steps`、`seed` 填进「高级参数」对应输入框；焦点移到提示词输入框、光标放在末尾，输入区滚入可见区域。**不提交**。 — 无裁决（面 F8 未盘问）
- D-41 输入框上方出现一枚提示条：「沿用第 N 次的构图」，右侧 × 按钮（`aria-label="不再沿用这张的构图"`）。点 × 清空高级参数里的种子框并隐藏提示条。N 是该尝试在会话里的序号（从 1 起，按 `attempts` 顺序）。 — 无裁决（面 F8 未盘问）
- D-42 提示条只在「种子框的值 == 被引用尝试的 seed」时显示；用户在高级参数里手动改了种子框，提示条隐藏。 — 无裁决（面 F8 未盘问）
- D-43 「高级参数」保持用户当时的折叠/展开状态，不因回填而自动展开。 — 无裁决（面 F8 未盘问）
- D-44 回填后用户点「生成图片」：新尝试的 `params.seed` 等于原尝试的 `seed`（验收：种子相同）。 — 无裁决（面 F8 未盘问）
- D-45 生成中该按钮仍可用（它只改输入框，不提交）。 — 无裁决（面 F8 未盘问）
- D-46 点击后立即提交：`prompt`、`width`、`height`、`steps` 取该尝试的值，`seed` 取前端新生成的随机数（`crypto.getRandomValues` 取 32 位无符号整数，0–4294967295），若恰好等于原 seed 则重取直到不同。`session_id` 为当前会话。 — 无裁决（面 F8 未盘问）
- D-47 不改输入框和高级参数里的任何值；新尝试追加在时间线末尾。 — 无裁决（面 F8 未盘问）
- D-48 生成中、正在提交、模型缺失、运行环境不可用、其他媒体作业占用时，该按钮 `disabled`，`title` 与按钮下方一行提示为不可用原因（与「生成图片」按钮同一原因文本，见 §7）。 — 无裁决（面 F8 未盘问）
- D-49 遇到 `insufficient_memory` 走现有确认框（「内存可能不足」/「仍要生成」），确认后带 `force: true` 重发；取消则什么都不写。 — 无裁决（面 F8 未盘问）
- D-50 「种子」二字只出现在「高级参数」折叠区内（输入框标签「种子（留空则每次随机）」和尝试详情的高级参数列表）。会话列表、时间线卡片、提示条、两个动作按钮、状态文案、确认框、错误提示中都不出现「种子」。 — 无裁决（面 F8 未盘问）
- D-51 服务端校验错误原文（如「种子须为 0–4294967295 的整数」）只可能由高级参数里的输入触发；前端在提交前自行校验，错误提示为「高级参数里的数值有误：种子须为 0–4294967295 的整数」，出现在高级参数区内（该区自动展开以便看到）。 — 无裁决（面 F8 未盘问）
- D-60 左上「新会话」按钮（主按钮样式、plus 图标，与聊天页同构）：`POST /api/image-sessions`，新会话成为当前会话、排在列表最上，时间线显示空会话态，焦点移到提示词输入框。每次点击都新建（与聊天页一致）。 — 无裁决（面 F8 未盘问）
- D-61 未新建时，生成总是追加到**当前会话**末尾（D-20 的 `session_id` 就是当前会话）。新建后生成的图只进新会话。 — 无裁决（面 F8 未盘问）
- D-62 首次进入图片页且没有任何会话时，**自动新建一个「新会话」并选中**，不显示「请先新建」的提示。理由：与聊天页 `refreshSessions` 相同行为（保持两个页面一致）；用户第一次来要做的事就是写提示词生成，多一步「先新建」没有任何信息量；空会话没有代价。这仍满足「会话需手动新建」——之后的每个新分组都由用户点「新会话」产生，生成本身从不暗中另开会话。 — 无裁决（面 F8 未盘问）
- D-63 当前会话的恢复（刷新页面或重启 app 后进入图片页）：优先选有 running 尝试的会话；否则选 `updated` 最新的会话。不用浏览器存储、不改地址栏 hash（与聊天页一致，状态只来自服务端）。同一次页面生命周期内切换 tab 再回来，当前会话不变。 — 无裁决（面 F8 未盘问）
- D-64 切换会话：清空种子框、隐藏提示条（它指向的是上一个会话里的尝试）；提示词、宽、高、步数保持不动。 — 无裁决（面 F8 未盘问）
- D-65 生成成功启动后：提示词保留在输入框（方便继续微调），种子框清空、提示条隐藏（下一次直接「生成图片」就是新的随机构图；要沿用就再点一次「在这张基础上改」）。宽、高、步数保持。 — 无裁决（面 F8 未盘问）
- D-66 新会话第一次生成使用随机种子：种子框默认为空（`placeholder="留空则每次随机"`），前端在提交时若种子框为空则不传 `seed`，由后端 D-19 取随机值。 — 无裁决（面 F8 未盘问）
- D-70 `#pane-image` 与 `#pane-chat` 同构：左侧 `aside.sessions`（宽 248px，复用 `.sessions` 样式与 `card session` 卡片、`session-actions` 的改名/删除图标按钮），右侧 `.image-main` 占满剩余宽度，内容最大宽 1400px，外边距 24px（视觉基线）。`#pane-image` 原来的「表单 | 作业」两栏 grid 与右侧 `.job` 区块取消，作业展示移入时间线里的 running 卡片。 — 无裁决（面 F8 未盘问）
- D-71 时间线**旧在上、新在下**（与聊天一致，输入区在底部）。打开会话、追加新尝试、尝试落定时滚动到底部。 — 无裁决（面 F8 未盘问）
- D-72 打开会话时默认选中（展开）最后一个尝试；新尝试开始时它成为选中项。同一时刻只展开一个；点击另一张卡片（或在卡片上按 Enter/空格）切换选中。卡片是可聚焦元素（`tabindex=0`、`aria-expanded`）。 — 无裁决（面 F8 未盘问）
- D-73 折叠卡片内容：「第 N 次 · HH:MM」、缩略图（96×96 容器，`object-fit: contain`，仅 done 且文件在时出现）、提示词摘要（最多两行，超出用省略号，`title` 属性为完整提示词）、尺寸步数「1024×1024 · 40 步」、状态标记（生成中 / 失败 / 已取消 / 图片文件已不在；完成不加标记）。 — 无裁决（面 F8 未盘问）
- D-74 展开卡片额外显示：大图（宽度不超过时间线列宽、高度不超过 60vh，`object-fit: contain`，`alt` 为提示词）、完整提示词、「高级参数」折叠块（列出 宽度、高度、步数、种子 四项实际值，默认折叠）、两个动作按钮（次级按钮样式，「在这张基础上改」在左，「换个构图」在右；「生成图片」是页面唯一主按钮）。 — 无裁决（面 F8 未盘问）
- D-75 输入区：提示条（D-41，按需出现）、提示词 textarea（placeholder 沿用「例如：一只橘猫坐在窗边，午后阳光，细腻的水彩插画」，⌘Enter 等同点「生成图片」）、「生成图片」主按钮（sparkles 图标）、「高级参数」`<details>` **默认折叠**（宽度（像素）默认 1024、高度（像素）默认 1024、步数默认 40、种子（留空则每次随机）默认空；折叠区内保留现有提示「建议从 1024×1024、40 步开始；更大图片需要更多时间与内存。」）、一行状态提示 `role=status`、一行错误 `role=alert`。 — 无裁决（面 F8 未盘问）
- D-76 头部一行：「生成图片」标题、模型状态（现有 `data-image-model` 文案）、「模型说明」折叠（现有 Heretic 说明文字）。 — 无裁决（面 F8 未盘问）
- D-77 会话列表项：标题（单行省略，`title` 属性为全称）、元信息「N 次生成 · HH:MM」（N = `attempt_count`，时间取 `updated`）、有 running 尝试时标题右侧显示「生成中」小标记（`--busy` 色圆点 + 文字）。当前会话 `aria-current="true"` 与聊天页相同高亮。 — 无裁决（面 F8 未盘问）
- D-78 窄窗 900×700：左栏仍 248px，右侧约 600px；卡片、输入区、按钮不出现横向滚动和文字截断（按钮文字不换行不裁切）；两个动作按钮放不下时换到下一行而不是被裁切。 — 无裁决（面 F8 未盘问）
- D-80 时间线居中显示两行：「还没有图片」／「在下面写下想要的画面，点「生成图片」。之后可以在任意一张上「在这张基础上改」或「换个构图」。」不显示空白图片框、不显示进度条。 — 无裁决（面 F8 未盘问）
- D-81 running 卡片始终展开显示：「第 N 次 · 生成中…（已用 1 分 20 秒）」（沿用 jobview 的 `formatDuration` 文案）、`<progress>`（沿用 `parseStepProgress`：解析到步数时显示百分比，否则为不确定进度）、「取消」按钮（调用 `/api/media/cancel`）、「日志」折叠块（默认折叠）、提示词摘要与尺寸步数。**不显示图片框**，也不显示两个动作按钮。 — 无裁决（面 F8 未盘问）
- D-82 进度数据来源：`main.js` 的 2 秒轮询 `tickJob` 取到 `kind == "image"` 的作业时交给图片页，图片页按 `attempt_id`（D-22）找到对应卡片更新；当前查看的会话不是该作业的会话时只更新会话列表的「生成中」标记。 — 无裁决（面 F8 未盘问）
- D-83 生成中「生成图片」和「换个构图」禁用，原因见 §7.6；「在这张基础上改」、切换会话、新建会话、重命名、删除都可用。 — 无裁决（面 F8 未盘问）
- D-84 这三种卡片**不渲染 `<img>`、不留空白图片框**；在缩略图位置显示一个图标块（失败：`x` 图标 + `--danger` 色；已取消：`x` 图标 + `--muted` 色；文件不在：`image` 图标 + `--muted` 色），块内无图片占位。 — 无裁决（面 F8 未盘问）
- D-85 原因文案： — 无裁决（面 F8 未盘问）
- D-86 这三种卡片都显示两个动作按钮（§5），参数都完整可用。 — 无裁决（面 F8 未盘问）
- D-87 「会话标题」取 `title`；判定「别的会话在生成」用列表摘要的 `running` 字段（§3.1），列表在每次轮询看到作业开始/结束时刷新。 — 无裁决（面 F8 未盘问）
- D-88 `POST /api/media/image` 返回错误时不出现新卡片，错误显示在输入区错误行：`insufficient_memory` 走确认框（D-49）；`session_not_found` → 刷新列表、按 D-63 选中会话，错误行显示「这个会话已被删除，已切到「<标题>」，请重新点「生成图片」」；其他错误显示 `describeJobError(error).title`（如「已有作业在进行」「图片模型不完整，请到资源页检查」「无法启动生成程序」）。 — 无裁决（面 F8 未盘问）
- D-89 重命名：与聊天页相同——点铅笔图标（`aria-label="改名"`）→ 列表项变成输入框并聚焦，Enter 或失焦保存，内容为空或未变则不请求；失败时错误行显示后端原因（如「标题须为 1–80 个字」）。 — 无裁决（面 F8 未盘问）
- D-90 删除：点垃圾桶图标（`aria-label="删除会话：<标题>"`）→ 确认框（`confirmDialog`，危险样式，默认焦点在「取消」）： — 无裁决（面 F8 未盘问）
- D-91 图片页不再使用 `createJobView` 的固定 DOM（`[data-job-status]` 等）；running 卡片复用它的纯函数部分：`formatDuration`、`parseStepProgress`、`describeJobError` / `renderErrorBlock`。视频、音乐页的 jobview 用法不变。 — 无裁决（面 F8 未盘问）
- D-92 `applyHeavyAvailability` 继续调用 `panes.image.setHeavyAllowed` / 忙碌原因；`tickJob` 对 `kind == "image"` 的作业调用图片页的 `applyJob(payload)`（替代原 `jobView.apply`）；`showTab("image")` 时图片页刷新会话列表与当前会话。 — 无裁决（面 F8 未盘问）
- D-93 `fillPlan` 对图片条目返回 `{pane:"image", session_id, attempt_id, fields:{prompt,width,height,steps,seed}}`，`seed` 缺失时为 `null`（不再补 42）。 — 无裁决（面 F8 未盘问）
- D-94 该条目带 `session_id` 且 `GET /api/image-sessions/{session_id}` 成功、其中有 `attempt_id` 对应的尝试：切到图片页、打开那个会话、选中（展开）该尝试并滚动到它，同时执行该尝试的「在这张基础上改」（D-40–D-42）。 — 无裁决（面 F8 未盘问）
- D-95 否则（没有 `session_id`、会话已删、尝试找不到）：切到图片页，停在当前会话，把条目参数按 D-40 填入输入区；提示条文案为「沿用素材库里这张的构图」（此时没有序号可引用）。不新建会话。 — 无裁决（面 F8 未盘问）
- B-01 三个目录：`data_root/image-sessions`、`data_root/video-sessions`、`data_root/music-sessions`，由 `PathRoots.media_sessions_dirs: dict[kind, Path]` 给出（取代 `image_sessions_dir`）。互不可见。 — 无裁决（面 F12 未盘问）
- B-02 写入纪律、id 规则、坏文件处理、锁、「读 → 改 → 原子写回、不持内存副本」全部继承 IS D-02、D-15。 — 无裁决（面 F12 未盘问）
- B-03 `kind` 与所在目录一致；文件里写了别的 kind 视为坏文件；没写 `kind` 的按所在目录的 kind 读（下次写回时补上）。 — 无裁决（面 F12 未盘问）
- B-04 标题规则继承 IS D-10–D-13。自动标题取第一个尝试的「标题来源字段」：image/video 取 `prompt`，music 取 `caption`。 — 无裁决（面 F12 未盘问）
- B-05 `op`：`generate` 为模型生成；`compose` 为手动合成（§4）。 — 无裁决（面 F12 未盘问）
- B-06 `params` 按 kind 的白名单保存（§1.4），白名单外的键不写入。`seed` 一律是实际使用的值。 — 无裁决（面 F12 未盘问）
- B-07 `continues`：被续写的尝试 id，非续写为 `null`。仅 video/music。 — 无裁决（面 F12 未盘问）
- B-08 `joined_output` / `joined_error`：仅 `continues != null` 的尝试有意义；`done` 时二者恰有一个非空，其他状态都为 `null`。`compose` 尝试的成品放 `output`，这两个字段为 `null`。 — 无裁决（面 F12 未盘问）
- B-09 `refs`：`{名称: {"kind", "session_id", "attempt_id"}}`，名称由下游定义（例如视频的 `first_frame`、`soundtrack`）。本文只规定结构、校验与解析（§5）。 — 无裁决（面 F12 未盘问）
- B-10 `base`：仅 image，含义同 IS D-47b；其他 kind 恒为 `null`。 — 无裁决（面 F12 未盘问）
- B-11 状态与字段取值继承 IS D-08、D-09（含 `cancelled_on_quit`、`interrupted`）。 — 无裁决（面 F12 未盘问）
- B-12 `get(id)` 对每个 `done` 尝试附加 `output_missing`；对有 `joined_output` 的尝试再附加 `joined_missing`。都只出现在响应里，不写回文件。 — 无裁决（面 F12 未盘问）
- B-13 video/music 的白名单是**现有**生成参数加 `seed`；第 3 块若新增参数（如参考图、参考音频）在其 spec 中扩充白名单。 — 无裁决（面 F12 未盘问）
- B-20 尝试记录只由后端写（继承 IS D-14）。 — 无裁决（面 F12 未盘问）
- B-21 接通要求：`runtime.py` 与 `desk/testing/harness.py` 都传 `media_sessions`；`/api/media-sessions/{kind}` 挂在生产路由与测试外壳路由上。仓库中不再有 `/api/image-sessions`、`ImageSessionStore`、`image_sessions_dir` 的引用。 — 无裁决（面 F12 未盘问）
- B-22 `chain` 防御环：回溯时记录已访问 id，重复即停（正常数据不会有环，因为 `continues` 只能指向已存在的更早尝试）。 — 无裁决（面 F12 未盘问）
- B-30 `kind ∈ {image, video, music}`，其他 → 404 `不认识的媒体类型：<kind>`。 — 无裁决（面 F12 未盘问）
- B-31 `GET/POST /api/media-sessions/{kind}`、`GET/PATCH/DELETE /api/media-sessions/{kind}/{id}` 的请求、响应、错误与 IS §3.1–3.5 一致；列表摘要的 `cover` 对 video/music 取最后一个 `done` 尝试的 `joined_output`（没有则 `output`）。 — 无裁决（面 F12 未盘问）
- B-32 校验与挂接顺序：参数 → 会话 → `continues`（§3.3）→ `refs`（§5）→ `_start` 的既有检查（`media_busy` → `capability_missing` → `model_incomplete` → arbiter → `insufficient_memory`）→ 若需拼接则检查 ffmpeg（§6）→ 启动子进程 → 成功后 `begin_attempt`。 — 无裁决（面 F12 未盘问）
- B-33 B-32 任一步失败都不写会话（继承 IS D-21）。 — 无裁决（面 F12 未盘问）
- B-34 200 响应与 `job_status()` 对所有 kind 都带 `session_id`、`attempt_id`（IS D-22 推广）。 — 无裁决（面 F12 未盘问）
- B-35 被续写的尝试须在同一会话、`status == done`、`output` 文件存在；否则 404 `segment_not_found` / `segment_missing`。`op == compose` 的尝试也可被续写（在成片后接着生）。 — 无裁决（面 F12 未盘问）
- B-36 续写时模型的输入如何取自被续写的尝试： — 无裁决（面 F12 未盘问）
- B-37 截帧失败（ffmpeg 报错）→ 启动前 500 `frame_extract_failed`「没能从上一段截出最后一帧」，不写会话。 — 无裁决（面 F12 未盘问）
- B-38 `continues != null` 的作业：模型子进程成功产出后，**同一个工作线程**继续执行拼接，再落定。拼接期间作业仍是 `running`，日志追加一行 `[join] 正在拼接成片…`。 — 无裁决（面 F12 未盘问）
- B-39 拼接的片段 = `chain(本尝试)` 中每一项的「单段文件」按顺序；**不使用**上一段的 `joined_output` 再加一段。理由：片段各自独立，任何一次拼接都能只从单段文件重建。 — 无裁决（面 F12 未盘问）
- B-40 链断（某项文件不在、或 `broken`）→ 本尝试 `done`，`joined_output = null`，`joined_error = {"code": "segment_missing", "message": "第 N 段的文件已不在，无法拼成成片"}`（N 为链中序号，从 1 起）。 — 无裁决（面 F12 未盘问）
- B-41 拼接命令失败 → 本尝试 `done`，`joined_error = {"code": "join_failed", "message": "拼接成片失败", "log_tail": …}`。 — 无裁决（面 F12 未盘问）
- B-42 成片文件名：视频 `h3-joined-<stamp>-<8hex>.mp4`，音乐 `music3-joined-<stamp>-<8hex>.wav`，写在 `outputs_root`。 — 无裁决（面 F12 未盘问）
- B-43 history：所有 kind 的条目都带 `session_id`、`attempt_id`；拼接成功时再加 `joined_output`。`HistoryStore.by_output()` 同时按 `output` 与 `joined_output` 建索引，使素材库列出成片时带上它的 history（不显示为孤儿文件）。 — 无裁决（面 F12 未盘问）
- B-44 `kind` 为 image 或不认识 → 400；`parts` 须为 2 个及以上的字符串数组，可以重复同一个 id（允许同一段出现两次）；每项按 B-35 校验（`segment_not_found` / `segment_missing`）。 — 无裁决（面 F12 未盘问）
- B-45 检查顺序：参数 → 会话 → parts → `media_busy` → ffmpeg 可用性 → 启动。**不经过** arbiter、模型检查、内存提醒（ffmpeg 开销小；符合「不要太严格」）。`force` 接受但无作用，保留只为前端统一重发逻辑。 — 无裁决（面 F12 未盘问）
- B-46 启动成功后 `begin_attempt`：`op = "compose"`、`params = {"parts": [...]}`、`continues = null`、`refs = {}`。标题：会话第一个尝试是 compose 不可能发生（parts 需要已有尝试），故不涉及自动标题。 — 无裁决（面 F12 未盘问）
- B-47 compose 作业与生成作业共用 `_state`、互斥、`job_status`、轮询、取消、`close()`、history（`kind` 为 `video|music`，`params.op = "compose"`）、落定。成功 → `output` 为成品；失败 → `failed` + `join_failed`。 — 无裁决（面 F12 未盘问）
- B-48 片段用各自的「单段文件」：generate 尝试用 `output`（不用其 `joined_output`），compose 尝试用 `output`。 — 无裁决（面 F12 未盘问）
- B-50 video：重编码 concat（`libx264`、`yuv420p`、`aac`），**每个续写关系上的后一段丢首帧**：若 `parts[i+1].continues == parts[i].id`，则 `parts[i+1]` 丢首帧；否则不丢（手动乱序合成时不是尾帧接首帧的关系）。各段宽高不一致时按第一段宽高缩放并补边（`scale` + `pad`，保持比例）。 — 无裁决（面 F12 未盘问）
- B-51 music：相邻两段 `acrossfade=d=1.5:c1=tri:c2=tri`；任何一段短于 3 秒时该接缝改为直接拼接（不交叉淡化）。 — 无裁决（面 F12 未盘问）
- B-52 具体数值（丢帧数、淡化时长）写在 `compose.py` 常量里，第 2、3 块如需调整在其 spec 内改。 — 无裁决（面 F12 未盘问）
- B-55 每项 `{kind, session_id, attempt_id}`；`kind` 须为该引用名称注册的允许值；目标会话、尝试须存在、`done`、文件在；否则 404 `ref_missing`「引用的<图片/音乐/视频>已不在」（中文名按目标 kind）。 — 无裁决（面 F12 未盘问）
- B-56 解析结果是一个文件路径，由 `MediaService` 交给该 kind 的命令构造；尝试记录只存引用三元组，不存路径。 — 无裁决（面 F12 未盘问）
- B-57 引用是单向指针：删除被引用会话不影响已生成的尝试；再次用该尝试「在这个基础上改」时若引用失效，按 B-55 返回 404，由下游界面提示。 — 无裁决（面 F12 未盘问）
- B-58 本文**不注册任何引用名称**；机制以测试用的假名称验证。第 3 块注册 `first_frame`（image）、`soundtrack`（music）等。 — 无裁决（面 F12 未盘问）
- B-60 ffmpeg 不可用：只有**需要拼接或截帧**的请求返回 503 `capability_missing`「需要 ffmpeg 才能拼接成片」；普通生成不检查。 — 无裁决（面 F12 未盘问）
- B-61 拼接（自动与手动合成）的子进程经 `MediaService` 现有 executor 运行，日志进作业日志，取消走同一套 `terminate/kill`。截末帧在请求内同步执行（不到 1 秒，超时 60 秒），失败按 B-37 返回。 — 无裁决（面 F12 未盘问）
- B-62 内存：这些作业不接 `estimate_bytes`、不做内存提醒（B-45）。 — 无裁决（面 F12 未盘问）
- B-70 （**2026-09-25 修订：移到第 2 块**。理由：image.js 的会话逻辑与图片专属状态（提示条、种子框、底稿、大图自适应）交织很紧，只有一个使用方时抽出的接口只能靠猜；第 2 块有了音乐页这个真实的第二使用方再抽。本块前端只改接口路径与 `fillPlan`。以下为第 2 块的要求。）`panes/media_session.js` 导出一个工厂：参数为 `kind`、输入区与卡片内容的渲染回调；负责会话列表四种状态（IS §7.2）、自动新建首个会话（IS D-62）、当前会话恢复（IS D-63）、时间线骨架与选中展开（IS D-71、D-72）、running 卡片与轮询挂接（IS D-81、D-82）、改名删除（IS D-89、D-90）、忙碌原因中「别的会话在生成」（IS §7.6）。 — 无裁决（面 F12 未盘问）
- B-71 图片页改用该模块后，IS 全部 D-xx 仍成立；图片页 DOM 文本、按钮、文案逐字不变。 — 无裁决（面 F12 未盘问）
- B-72 删除确认正文中的「图片」按 kind 替换为「视频 / 音乐」由工厂参数提供；本文只要求 image 的文案不变。 — 无裁决（面 F12 未盘问）
- B-73 本文不改 `panes/video.js`、`panes/music.js`。它们不传 `session_id`，按 §3.2 照旧能生成；`main.js` 的 `tickJob` 对 video/music 作业（含 compose）仍交给它们的 jobView 显示。 — 无裁决（面 F12 未盘问）
- B-74 `fillPlan`：video/music 条目带出 `session_id`、`attempt_id`（同 IS D-93）；`params.op == "compose"` 的条目返回 `null`（没有可回填的参数，素材库不显示「回填参数」）。 — 无裁决（面 F12 未盘问）
- B-75 给下游的约束（第 2、3 块界面必须实现，本文后端已备好）：卡片的 `joined_error.code ∈ {join_failed, join_cancelled, interrupted}` 时提供「重新拼接」，行为是发起 `compose`，`parts = chain(该尝试)` 各项 id，结果作为新的成片卡片追加；`segment_missing` 不提供（缺的文件补不回来），只显示原因。 — 无裁决（面 F12 未盘问）
- M-01 控制器承担 IS §6–§7 与 §3.7 中与媒体种类无关的全部行为：会话列表四种状态（IS §7.2）、自动新建首个会话（IS D-62）、当前会话恢复（IS D-63）、切换（IS D-64，经 `composer.onSessionSwitch`）、时间线骨架与选中展开（IS D-71、D-72）、running 卡片进度与日志（IS D-81、D-82）、落定后重取（IS D-27）、改名删除（IS D-89、D-90）、忙碌原因（IS §7.6，名词取 `noun`）、「回到该会话」、内存确认重发（IS D-49）、`session_not_found` 自动切换（IS D-88）、滚动意图（贴底 / 对齐选中 / 用户滚动后不拽）与 ResizeObserver。 — 无裁决（面 F11 未盘问）
- M-02 图片页专属的「展开卡片大图自适应」（IS D-74 的 `fitExpandedImage`）经 `renderCard` 返回的 `image` 节点接入：控制器只在 `image` 存在时调用页面提供的适配（由 `image.js` 以回调形式传入 `fitExpanded(node, image)`），音乐页不传。 — 无裁决（面 F11 未盘问）
- M-03 纯逻辑参数化：`availability(state, {noun})`、`deleteMessage(summary, {noun})`、`runningSessionId(job, sessions, kind)`；其余（`sessionTitle`、`sessionMeta`、`attemptLabel`、`orderSessions`、`pickCurrent`、`randomSeed`、`ParamsError`、`autoTitle`）原样迁移。图片页调用时 `noun="图片"`，产出的文案与迁移前逐字相同。 — 无裁决（面 F11 未盘问）
- M-04 **图片页零回归**：`tests/js/image_pane.test.js` 与 `tests/e2e/test_image_sessions.py`、`tests/e2e/test_image_flow.py` 的断言不改（只允许改 import 路径与挂载方式），全部通过。 — 无裁决（面 F11 未盘问）
- M-05 时间线上方工具行出现次级按钮「挑几段合成…」（`data-<prefix>-compose-start`）。会话没有 ≥2 个 `done` 且文件在的尝试时按钮 `disabled`，`title`「至少要有两段完成的才能合成」。 — 无裁决（面 F11 未盘问）
- M-06 进入模式：每张 `done` 且文件在的卡片左侧出现勾选框（`aria-label="选中第 N 次"`）；其余卡片不可选、不变灰。卡片点击在此模式下切换勾选而非展开。 — 无裁决（面 F11 未盘问）
- M-07 勾选顺序即拼接顺序，已选卡片显示序号徽标 ①②③…；取消勾选后其后序号前移。 — 无裁决（面 F11 未盘问）
- M-08 底部输入区替换为合成栏：按顺序列出已选段（「第 N 次 · 时长」），每项「上移」「下移」「移除」（图标按钮，`aria-label` 同名）；右侧主按钮「合成（K 段）」，次级按钮「取消」。K<2 时主按钮 `disabled`，原因行「至少选两段」。有作业在跑或服务不可用时 `disabled`，原因同 IS §7.6 第一条可用原因。 — 无裁决（面 F11 未盘问）
- M-09 点「合成」：`POST /api/media/compose {kind, session_id, parts}`；成功启动 → 退出挑选模式、恢复输入区、新 compose 尝试追加并选中（running 卡片）；失败 → 留在模式内，错误显示在合成栏错误行（`describeJobError` 标题，`capability_missing` 显示后端原话「需要 ffmpeg 才能拼接成片」）。 — 无裁决（面 F11 未盘问）
- M-10 「取消」、切换会话、新建会话都退出挑选模式并清空已选。 — 无裁决（面 F11 未盘问）
- M-11 界面不允许同一段选两次（勾选框语义）。B-44 后端允许重复，界面不提供。 — 无裁决（面 F11 未盘问）
- M-20 左栏、主区宽度、外边距、窄窗 900×700 规则同 IS D-70、D-78。原 `.form | .job` 两栏与 jobview 删除。 — 无裁决（面 F11 未盘问）
- M-21 输入区：提示条（M-26）；风格描述 `<input>`（`placeholder` 沿用「例如：温柔的民谣，木吉他伴奏，女声轻唱，慢速」，`aria-label="风格描述"`）；歌词 `<textarea>`（`placeholder="歌词（必填）"`，默认 4 行，聚焦或内容超出时增高，最高 `50vh`，失焦且内容不超 4 行时回落）；「AI 帮写」行（原 `data-music-assist`）；主按钮「生成歌曲」（sparkles 图标，⌘Enter 等同点击）；「高级参数」`<details>` 默认折叠，内含「时长（秒）」（10–300，默认 60，下方保留提示「成品时长由模型按歌词决定，常短于所填时长；素材库会标注实际时长。」）与「种子（留空则每次随机）」；状态行 `role=status`；错误行 `role=alert`。 — 无裁决（面 F11 未盘问）
- M-22 头部：「生成歌曲」、模型状态（沿用现有音乐模型状态文案来源）、「模型说明」折叠（MiniMax Music 3 · MLX 本机推理；需要歌词；成品为 WAV）。 — 无裁决（面 F11 未盘问）
- M-23 空会话：「还没有歌曲」／「在下面写风格描述和歌词，点「生成歌曲」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着写下一段」。」 — 无裁决（面 F11 未盘问）
- M-24 生成成功启动后：风格描述、歌词、时长保留；种子框清空；提示条若为「沿用第 N 次」则隐藏，若为「接在第 N 次后面」也隐藏（下一次生成回到普通生成，除非再点「接着写下一段」）。 — 无裁决（面 F11 未盘问）
- M-25 「种子」二字只出现在「高级参数」内（同 IS D-50）。 — 无裁决（面 F11 未盘问）
- M-26 两种，互斥： — 无裁决（面 F11 未盘问）
- M-27 提示条可见时点「生成歌曲」的请求：沿用 → 带被引用尝试的 `continues`（若它有，M-31）；续写 → `continues = 被续写尝试 id`。提示条不可见 → 不带 `continues`。 — 无裁决（面 F11 未盘问）
- M-28 若被引用 / 被续写的尝试已不再是 `done` 且文件在（`output_missing` 或会话刷新后找不到），提示条改为「第 N 次的文件已不在，不能接着写」并带 ×，「生成歌曲」`disabled`、原因同文案；点 × 回到普通生成。后端返回 `segment_missing` / `segment_not_found` 时同样处理。 — 无裁决（面 F11 未盘问）
- M-30 折叠：标题行「第 N 次 · HH:MM」＋（续写）「接第 M 次」／（合成）「合成：第 a、b、c 次」（引用的尝试不在列表中时显示「合成」）；风格描述摘要（一行省略，`title` 全文）；歌词首个非空、非 `[段落标记]` 行（一行省略）；状态标记（生成中 / 失败 / 已取消 / 文件已不在；完成不标）。 — 无裁决（面 F11 未盘问）
- M-31 展开： — 无裁决（面 F11 未盘问）
- M-32 失败 / 已取消 / 文件不在：不渲染 `<audio>`，图标块与原因同 IS D-84、D-85；动作按钮按 M-33–M-35 的可用性显示。 — 无裁决（面 F11 未盘问）
- M-33 **在这段基础上改**：回填风格描述、歌词、时长、种子；提示条「沿用第 N 次」；焦点到歌词框末尾；不提交；生成中可用（同 IS D-45）。失败 / 取消的尝试也可用（参数完整）。 — 无裁决（面 F11 未盘问）
- M-34 **换个版本**：立即提交 `{session_id, caption, lyrics, duration, seed: 新随机数≠原值, continues: 原尝试的 continues}`；不改输入区。不可用条件同 IS D-48（生成中、提交中、模型缺失、运行环境不可用、其他作业占用）。 — 无裁决（面 F11 未盘问）
- M-35 **接着写下一段**：风格描述、时长 ← 该尝试（compose 尝试：保留输入区当前值）；歌词清空；种子框清空；提示条「接在第 N 次后面」；焦点到歌词框；不提交。仅 `done` 且文件在的尝试显示为可用；否则 `disabled`，下方原因「这一段没有生成好，不能接着写」。 — 无裁决（面 F11 未盘问）
- M-36 回填不改变「高级参数」的折叠状态（同 IS D-43）。 — 无裁决（面 F11 未盘问）
- M-40 尝试 `done` 且 `joined_error` 非空时，展开卡片在播放器下显示一行：「这一段生成好了，但成片没拼成：<原因>」，原因取 `joined_error.message`。 — 无裁决（面 F11 未盘问）
- M-41 `joined_error.code ∈ {join_failed, join_cancelled, interrupted}` 时该行带次级按钮「重新拼接」：提交 `compose`，`parts` = 前端回溯出的链（M-31）各项 id，全部可找到且 `done`、文件在时才可用，否则按钮 `disabled`、原因「链上有一段已不在」。成功后新合成卡片追加并选中（B-75）。成片文件被删（`joined_missing`）同样显示问题行并按 M-41 提供重新拼接；问题行文案为「这一段生成好了，但成片文件已不在」。 — 无裁决（面 F11 未盘问）
- M-42 `segment_missing` 不提供按钮，只显示原因。 — 无裁决（面 F11 未盘问）
- M-50 `start_music_job` 的 `session_id` 改为必填：缺失 / 非字符串 → 400 `session_required`，不存在 → 404 `session_not_found`（同 IS D-18 文案）。`continues`、`refs` 规则不变。 — 无裁决（面 F11 未盘问）
- M-51 `main.js`：`tickJob` 对 `kind == "music"`（含 compose 作业，`params.op == "compose"` 且 kind 为 music）调用 `panes.music.applyJob`；`showTab("music")` 调 `panes.music.refresh()`；`applyHeavyAvailability` 调 `panes.music.setHeavyAllowed`；删除对 `panes.music.jobView` 的所有调用。`kind == "video"` 仍走视频页 jobview。 — 无裁决（面 F11 未盘问）
- M-52 素材库回填：`applyFill` 对 `plan.pane == "music"` 调 `panes.music.applyFill(plan)`：有 `session_id`、`attempt_id` 且能找到 → 切到音乐页、打开会话、选中该尝试并执行「在这段基础上改」；否则停在当前会话按 M-33 回填字段，提示条文案「沿用素材库里这首」（同 IS D-94/95）。 — 无裁决（面 F11 未盘问）
- M-53 音乐模型状态与运行环境：`main.js` 以与图片页相同的方式接通（不新增后端）——资源页 `onModels` 回调里 `panes.music.setModelStatus(models?.find((m) => m.key === "music3"))`；能力探测处 `panes.music.setRuntimeStatus(capabilities?.music_runtime)`。文案：模型缺失「尚未安装音乐模型，请到「资源」页下载」，不完整「模型不完整，请到「资源」页继续下载或校验」，未知「暂时无法确认模型状态，请稍后重试」；运行环境不可用「音乐 MLX 运行环境不可用，请检查服务或应用安装」（`capability.detail` 优先）；就绪时头部显示「模型文件完整 · 可离线生成」。 — 无裁决（面 F11 未盘问）
- V-01 `start_video_job` 的 `session_id` 必填（同 M-50 文案与状态码）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-02 `MediaService` 默认注册引用槽 `{"video": {"first_frame": "image"}}`（构造参数 `ref_slots` 未传时使用该默认；测试可覆盖）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-03 请求带 `refs.first_frame`：要求 `mode == "image"`，且请求不再带 `first_frame` 素材 id；否则 400 `invalid_params`「首帧只能从上传或图片会话二选一」。`continues` 与 `refs.first_frame` 同时出现 → 400（沿用 CONTINUE_CONFLICT 文案）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-04 解析出的图片路径直接作为 H3 `--first-frame` 参数；`params.first_frame` 记为 `null`（尝试的 `refs` 已记下引用，B-56）。引用失效 → 404 `ref_missing`「引用的图片已不在」（B-55）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-05 历史条目与素材库不变；`fillPlan` 对 video 条目带出 `refs`（`entry.params` 不含 refs，故 history 条目增加顶层 `refs` 字段，只在非空时出现）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-10 `attemptView(attempt, {broken, noun})` 移到 `pure/media_session.js`：missing 文案「<noun>文件已不在」（图片页仍得到「图片文件已不在」，逐字不变）；音乐卡片改用它（传 `noun: "音频"`，文案「音频文件已不在」——音乐卡片当前的「文件已不在」改为此）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-11 控制器 `renderCard` 返回的 `recompose` 改名 `secondary`（`{button, hint}`），`composer.updateAvailability(state, {secondary})`；卡片参数 `noImageReason` 改名 `secondaryBlockedReason`。图片页行为与文案不变（M-04 规则同样适用：`tests/js/image_pane.test.js` 断言不改）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-20 左栏会话、头部「生成视频」+ 模型状态 + 「模型说明」（MiniMax H3 · MLX 本机推理；输出带声音的 MP4；「接着往下生」用上一段的最后一帧作首帧，拼接处可能有动作跳变）、时间线、底部输入区。原表单 + jobview 删除。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-21 输入区（自上而下）：提示条（V-30）；「生成方式」`<select>`（文生视频 / 图生视频 / 视频参考生成）；素材行（按方式出现，V-22）；提示词 `<textarea>`（默认 3 行，聚焦/超出时增高，最高 40vh；placeholder 随方式变化，沿用现有三条）与「生成视频」主按钮（⌘Enter）；「AI 帮写」行；「高级参数」`<details>` 默认折叠：画幅（现有三档）、视频时长（现有六档）、耗时提示（`videoCostNote`）、步数（默认 16，4–50）、种子（留空则每次随机）、「使用素材的声音」勾选（仅图生/参考方式可见，默认勾选）；上传状态行；状态行；错误行。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-22 素材行： — 无裁决（面 F9 已盘问但无裁决引用它）
- V-23 「从图片会话选…」打开选择框（`confirmDialog` 风格的模态，`role="dialog"`，标题「从图片会话选首帧」）：左侧图片会话列表（标题 + N 次生成），右侧该会话中 `done` 且文件在的图片缩略图网格；点缩略图即选中并关闭；「取消」关闭不改变。无可选图片时显示「这个会话还没有生成好的图片」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-24 空会话：「还没有视频」／「在下面写提示词，点「生成视频」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着往下生」。」 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-25 「种子」只出现在高级参数内。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-30 提示条三种（互斥）：沿用「沿用第 N 次」（规则同 M-26 沿用型）；续写「接在第 N 次后面」（同 M-26 续写型，续写目标失效同 M-28，文案「第 N 次的文件已不在，不能接着往下生」）；素材库「沿用素材库里这段」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-31 折叠：「第 N 次 · HH:MM」＋「接第 M 次」／「合成：第 a、b 次」；方式标签（文生 / 图生 / 参考）；提示词摘要（两行省略）；规格「512×288 · 约 3 秒 · 16 步」（时长文案取 DURATIONS 最接近项）；状态标记。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-32 展开 done：`<video controls preload="metadata">`（宽不超过时间线列宽，高不超过 50vh），有可用成片时默认播成片，「成片 | 只看这一段」切换（同 M-31）；续写链说明「由：第 1 次 → 第 3 次」；成片问题行与「重新拼接」（同 M-40–M-42）；首帧来源行（图生且有 refs.first_frame：「首帧：图片会话「<标题>」第 N 次」；标题取不到时「首帧：来自图片会话」）；完整提示词；「高级参数」折叠（画幅、时长、步数、种子）；动作按钮。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-33 失败 / 取消 / 文件不在：同图片卡片规则（图标块，无 `<video>`）。`<video>` 报错 → 文件不在状态。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-34 挑选合成模式：同 M-06/M-07 与最终修订（卡片只做勾选，不显示动作与「重新拼接」）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-40 **在这段基础上改**：回填方式、提示词、画幅、时长、步数、种子；图生时回填首帧来源（上传素材 id 作为已保存素材 / 图片会话引用 / 续写关系）与尾帧；参考时回填参考视频素材 id；提示条「沿用第 N 次」；不提交。若首帧来源为图片会话引用且已失效 → 首帧区显示「引用的图片已不在」并清空首帧来源。续写段回填后生成仍接在原位置（带原 `continues`）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-41 **换个版本**：立即提交原尝试参数（含素材 id / 引用 / `continues`），种子换新随机数≠原值。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-42 **接着往下生**：方式切到图生、首帧来源为续写（V-22 第三种说明）、尾帧清空；提示词清空；画幅、时长、步数沿用该段；种子清空；提示条「接在第 N 次后面」；焦点到提示词。仅 done 且文件在可用，否则原因「这一段没有生成好，不能接着往下生」。compose 尝试：画幅、时长、步数保留输入区当前值。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-43 生成成功启动后：提示词、方式、画幅、时长、步数保留；种子清空；沿用/续写提示条隐藏；续写的首帧来源清空（回到「未选择」）；上传与图片会话来源保留。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-50 图片卡片展开时，done 且图片在的卡片在两个动作右侧增加次级按钮「用这张生成视频」。点击：切到视频页，方式设为图生，首帧来源设为该图片的引用（`{kind:"image", session_id, attempt_id}`），首帧说明「首帧：图片会话「<标题>」第 N 次」，提示词不变，焦点到提示词。图片页其余行为不变（新增按钮不影响现有按钮与文案）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-51 跨页通信经 `main.js`：图片页 `ctx.onUseAsFirstFrame(ref, label)` → `showTab("video")` → `panes.video.useFirstFrame(ref, label)`。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-60 `main.js`：`tickJob` 对 `kind == "video"` 调 `panes.video.applyJob`；`showTab("video")` 调 `panes.video.refresh()`；`applyFill` 对 video 与 image/music 同样走 `panes.video.applyFill`；模型状态 `h3` 目录项、运行环境 `mlx_h3` 能力；删除所有 `jobView` 使用；`widgets/jobview.js` 若不再被任何页面使用则删除（其纯函数部分已在 `pure/`）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- V-61 素材库回填视频条目：同 M-52（找得到会话 → 打开并执行「在这段基础上改」；否则按字段回填、提示条「沿用素材库里这段」）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- S-01 新接口 `POST /api/media/soundtrack`，体 `{session_id, source, refs: {soundtrack: {kind:"music", session_id, attempt_id}}, force?}`；`kind` 固定 video。 — 无裁决（面 F10 未盘问）
- S-02 校验顺序：参数（`source` 字符串、`refs.soundtrack` 结构）→ 视频会话（必填，同 V-01）→ `source` 为本会话 done 且文件在的尝试（`segment_not_found` / `segment_missing`）→ 音乐引用解析（`ref_missing`「引用的音乐已不在」）→ `media_busy` → ffmpeg（503「需要 ffmpeg 才能拼接成片」）→ 启动。不走 arbiter、模型检查、内存提醒（同 B-45）。 — 无裁决（面 F10 未盘问）
- S-03 输入视频：`source` 有未缺失的 `joined_output` 用它，否则用 `output`。 — 无裁决（面 F10 未盘问）
- S-04 命令：`compose.soundtrack_command(ffmpeg, video, audio, output)`：视频流拷贝，音频 `aac`，音频 `apad` 补静音，时长以视频为准（`-shortest` 在 apad 之后生效）；输出最后一个参数（B §6 约定）。原 `replace_audio_command` 替换为此（仅此处用）。 — 无裁决（面 F10 未盘问）
- S-05 尝试：`op = "soundtrack"`，`params = {"source": <attempt_id>}`，`refs = {"soundtrack": <music ref>}`，`continues = null`；成功 `output` 为 `h3-soundtrack-<stamp>-<8hex>.mp4`；失败 `failed` + `join_failed`，未完成时删除半成品（同合成）。 — 无裁决（面 F10 未盘问）
- S-06 history 条目 `params.op = "soundtrack"`、顶层 `refs`；`fillPlan` 对 `op ∈ {compose, soundtrack}` 返回 null。 — 无裁决（面 F10 未盘问）
- S-07 配乐尝试可被续写（B-35 放宽到 op soundtrack）与参加合成（`find_done` 不区分 op）。 — 无裁决（面 F10 未盘问）
- S-10 `start_video_job` 接受 `mode = "music_ref"`：必须有参考图（`ref_image` 上传素材 id，或 `refs.ref_image = {kind:"image", …}`，二选一，否则 400「参考图只能从上传或图片会话二选一」/ 缺失 400「请先选择参考图」）与 `refs.ref_audio = {kind:"music", …}`（缺失 400「请先选择一首歌」），以及 `audio_start`（秒，≥0 的数，默认 0）。 — 无裁决（面 F10 未盘问）
- S-11 注册引用槽：`video.ref_image → image`、`video.ref_audio → music`（与 `first_frame` 并列）。`music_ref` 不能与 `continues`、`first_frame`、`last_frame`、`ref_video`、`refs.first_frame` 同用（400 invalid_params，文案「配乐参考不能和首帧、尾帧或续写同时使用」）。 — 无裁决（面 F10 未盘问）
- S-12 截取：服务端在启动前用 ffmpeg 从歌中 `audio_start` 起截取 `clip = clamp(frames / 24, 2, 15)` 秒到 `.inputs/<hex>.wav`；歌短于 `audio_start + 2` 秒 → 400「这首歌从第 N 秒起不足 2 秒」；截取失败 → 500 `audio_clip_failed`「没能截取这段音乐」；之后任一步失败删除截取文件（同 B-37 做法）。 — 无裁决（面 F10 未盘问）
- S-13 命令：`build_h3_command(..., ref_image=<path>, ref_audio=<path>)` 追加 `--ref-image <path> --ref-audio <path>`（H3 Ref2VA，spike 已验证可跑）。`params` 记 `mode="music_ref"`、`audio_start`、`ref_image`（上传 id 或 null），尝试 `refs` 记引用。 — 无裁决（面 F10 未盘问）
- S-14 估算同普通视频（`estimate_bytes("video", params)`），标 predicted。 — 无裁决（面 F10 未盘问）
- S-20 `widgets/media_picker.js::openMediaPicker(doc, {kind, title, emptyText, listSessions, getSession, serveOutput})`：`kind ∈ {image, music}`；图片为缩略图网格（同 V-23），音乐为列表：每项「第 N 次 · <风格描述摘要>」+ `<audio controls preload="none">` 试听 + 「选这首」按钮；只列 done 且文件在的尝试（音乐优先成片 `joined_output`，无则 `output`）。返回 `null | {ref, title, index, label}`（`label` 为风格描述摘要，图片为提示词摘要）。 — 无裁决（面 F10 未盘问）
- S-21 `widgets/image_picker.js` 删除，视频页首帧改用 `openMediaPicker({kind:"image", title:"从图片会话选首帧", emptyText:"这个会话还没有生成好的图片"})`；音乐 `title` 由调用方给，`emptyText`「这个会话还没有生成好的歌」。 — 无裁决（面 F10 未盘问）
- S-30 视频卡片（done 且文件在、非挑选模式）动作区增加次级按钮「配乐…」：打开音乐选择框（标题「选一首歌配到这段视频」）→ 选中即 `POST /api/media/soundtrack`（`source` = 该尝试）→ 新卡片追加并选中。不可用条件同「换个版本」（有作业在跑等），原因同一套。 — 无裁决（面 F10 未盘问）
- S-31 配乐卡片：折叠标题「第 N 次 · HH:MM · 配乐：<风格描述摘要> · 基于第 M 次」（M 取不到则省略该段；风格描述取不到显示「配乐」）；展开播放 `output`；动作只有「接着往下生」与「配乐…」。 — 无裁决（面 F10 未盘问）
- S-32 「生成方式」下拉新增「配乐参考（实验性）」。选中时素材区：参考图区（「上传图片」+「从图片会话选…」+ 说明）、歌区（「从音乐会话选…」+ 所选歌说明「歌：<风格描述摘要>」+ 试听）、数字框，标签「从第几秒开始」（默认 0，≥0）、说明「实验性：画面不保证跟随音乐节奏；参考图只影响画面风格，不作为第一帧。截取与视频等长、2–15 秒的一段音乐。」。 — 无裁决（面 F10 未盘问）
- S-33 提交：`mode:"music_ref"`、`audio_start`、`ref_image`（上传 id）或 `refs.ref_image`、`refs.ref_audio`。缺参考图「请先选择参考图」、缺歌「请先选择一首歌」（前端先校验）。 — 无裁决（面 F10 未盘问）
- S-34 「在这段基础上改」对 music_ref 尝试回填参考图来源、歌、起始秒；引用失效时对应说明「引用的图片已不在」/「引用的歌已不在」并清空。「换个版本」原样重发（新种子）。 — 无裁决（面 F10 未盘问）
- S-35 900×700：新增的素材在已有可滚动的素材区内（V 块 50vh 规则），不增加输入区固定行。 — 无裁决（面 F10 未盘问）
- L-01 合并规则沿用现状：历史与成品按文件名匹配；一条历史的 `output` 与 `joined_output` 各占一条（B-43）；没匹配到历史的成品单独一条（「无历史记录」）；有历史但文件都不在的也占一条。 — 无裁决（面 F13 未盘问）
- L-02 每条条目归一为：`{ key, kind: "image"|"video"|"music"|"file", status, ts, title, prompt, spec, duration_s?, width?, height?, bytes?, gen_s?, output?: name, missing: bool, entry?: 历史记录, error? }`。`key` 跨刷新稳定（L-32 靠它保持选中）：有文件用 `o:<文件名>`，否则 `h:<ts>:<kind>:<attempt_id 或空>`，同一次渲染内重复时追加 `#2`、`#3`。 — 无裁决（面 F13 未盘问）
- L-03 `missing`：有历史、状态为完成、`output` 名在成品列表里找不到。 — 无裁决（面 F13 未盘问）
- L-04 时长：音乐取 `audio_seconds`，否则 `params.duration`；视频取 `params.frames / 24`；图片无。画幅取 `params.width×height`。 — 无裁决（面 F13 未盘问）
- L-05 筛选：`all | image | video | music`；`file` 类只在 `all` 下出现。 — 无裁决（面 F13 未盘问）
- L-06 排序：键为 `ts`（生成时间）| `title`（提示词）| `kind`（类型）| `duration`（时长）| `dims`（画幅，按宽×高面积）| `bytes`（文件大小）| `gen`（耗时），方向 `asc | desc`；缩略列不可排序；缺值一律排在最后（不论方向）；`title` 用 `localeCompare(…, "zh")`；同值按 `ts` 倒序稳定。默认 `ts desc`。 — 无裁决（面 F13 未盘问）
- L-10 工具栏一行：左侧类型筛选分段控件（全部 / 图片 / 视频 / 音乐，复用 `widgets/segment_switch.js`，它按 `labels` 数组生成任意项数，只需改掉文件头「两项」的注释）；右侧视图切换三个图标按钮（缩略图 / 列表 / 明细，`aria-pressed`、`aria-label`），缩略图视图时出现大小滑块，最右「刷新」。 — 无裁决（面 F13 未盘问）
- L-11 视图、筛选、缩略图大小、明细排序记在 `localStorage` 键 `lmd.library`（JSON）；读写都包 try/catch，读不到用默认值（缩略图、全部、200px、`ts desc`）；值非法时回落默认。缩略图大小滑块是普通 `input[type=range]`，方向键只调大小，不移动选中（L-31 只在条目区内生效）。 — 无裁决（面 F13 未盘问）
- L-12 筛选后为空：显示「没有这类成品」并写明当前筛选（例：「当前筛选：视频」）；整体为空沿用现有引导语。 — 无裁决（面 F13 未盘问）
- L-20 缩略图：自适应网格 `repeat(auto-fill, minmax(var(--lib-thumb), 1fr))`，滑块调 `--lib-thumb` 140–320px。卡片：方形媒体区 + 提示词两行截断 + 时间一行。 — 无裁决（面 F13 未盘问）
- L-21 图片卡片：`<img loading="lazy">`，`object-fit: cover`。 — 无裁决（面 F13 未盘问）
- L-22 视频卡片：进入视口（IntersectionObserver；环境没有时直接加载）才设 `src=<url>#t=0.1`、`preload="metadata"`、`muted`、`playsinline`；角标显示时长。鼠标悬停静音播放，移开暂停并回到 0.1 秒；同一时刻最多一个卡片在悬停播放。 — 无裁决（面 F13 未盘问）
- L-23 音乐卡片：渐变底 + 音乐图标 + 时长。`file` 类（不认识的文件）：文件图标 + 文件名。 — 无裁决（面 F13 未盘问）
- L-24 音乐卡片右上角小播放按钮就地试听（右下角是时长角标）：页面只有一个隐藏的 `<audio>`；按钮 `aria-pressed` 与图标（播放/暂停）反映状态，再点暂停；开别的试听、打开预览、点「刷新」重画、离开素材库页时都停掉并复位按钮；点按钮不触发选中/打开。 — 无裁决（面 F13 未盘问）
- L-25 失败/取消（无成品）：灰卡 + 警示图标 + 状态字；`missing`：灰卡 + 「文件已不在」。 — 无裁决（面 F13 未盘问）
- L-26 媒体加载失败（img/video `error`）：该卡片退回类型图标占位，不影响其他卡片。 — 无裁决（面 F13 未盘问）
- L-27 列表：每行 48px 缩略图（规则同 L-21/L-22，但视频不悬停播放）+ 提示词 + 元信息行（类型 · 状态 · 时间 · 耗时 · 规格）+ 右侧动作（预览、在访达中显示、回填参数）；失败记录照旧显示错误块（F3）。 — 无裁决（面 F13 未盘问）
- L-28 明细：`<table>`，列：缩略（32px）、提示词、类型、生成时间、时长、画幅、大小、耗时。除缩略列外表头是按钮，点击按该列排序，再点反向，`aria-sort` 标当前列；缺值显示「—」。 — 无裁决（面 F13 未盘问）
- L-30 每个条目的主体是一个 `<button data-lib-item>`（缩略图视图是整张卡片的媒体+文字区，列表是缩略图+文字区，明细是提示词单元格），`aria-label` 为标题；动作按钮（试听、预览、在访达中显示、回填）是它的兄弟节点，不嵌套在里面（避免交互元素嵌套）。单击主体 = 选中（`aria-current="true"` + 选中样式）；双击主体，或焦点在主体上按 Enter/空格 = 打开预览（`preventDefault`，不再额外触发选中之外的点击）。 — 无裁决（面 F13 未盘问）
- L-31 roving tabindex：所有主体里只有选中项（没有选中时是第一项）`tabIndex=0`，其余 `-1`；方向键只在焦点位于某个主体上时处理，移动时同时移动选中与焦点并滚入视野（`block: "nearest"`）。缩略图视图 ←/→ 前后一个，↑/↓ 跳一行：列数 = 与第一项 `offsetTop` 相同的前导项个数，量不到（0）时 ↑/↓ 退化为 ←/→；列表/明细 ↑/↓ 前后一个。到头停住，不循环。 — 无裁决（面 F13 未盘问）
- L-32 切换筛选、排序、刷新后：原选中项仍在就保持，否则清空选中。 — 无裁决（面 F13 未盘问）
- L-33 动作按钮（预览、在访达中显示、回填、试听）点击与按键都不冒泡为选中/打开；各自行为同现状（reveal 失败把服务端文案写进错误行，issue #12）。 — 无裁决（面 F13 未盘问）
- L-40 复用遮罩 + `role=dialog` + `aria-modal` + Esc/点遮罩关闭的骨架；打开时焦点进弹层，关闭后焦点与选中回到最后预览的条目。 — 无裁决（面 F13 未盘问）
- L-41 主区：图片按窗口适配；视频 `controls autoplay`（有声）；音乐大卡片 + `<audio controls autoplay>`；失败显示错误块；`missing` 显示「文件已不在」；`file` 类显示「无法预览这种文件」，信息区照常。 — 无裁决（面 F13 未盘问）
- L-42 信息区（宽屏在右，窄于 900px 在下）：完整提示词、全部参数、生成时间、耗时、文件名与大小；按钮「回填参数」（有 fillPlan 时；调用 `ctx.applyFill(plan)` 并关闭弹层）、「在访达中显示」（有文件时）、「关闭」。 — 无裁决（面 F13 未盘问）
- L-43 ←/→ 在当前筛选+排序顺序里切上一件/下一件（到头不循环，按钮置灰）；Esc 关闭；空格仅在焦点不在媒体控件、按钮或输入框上时关闭（否则交给该控件，如视频暂停）。切换或关闭时停止并释放上一件媒体（`pause()` + 移除 `src`）。弹层打开期间遮罩挡住页面，素材库不会被刷新，弹层按打开时的条目快照翻页。 — 无裁决（面 F13 未盘问）
- L-44 动效：遮罩淡入、面板淡入+轻微缩放（180ms 左右）；全局 `prefers-reduced-motion` 规则生效。 — 无裁决（面 F13 未盘问）
- L-45 离开素材库页（`main.js` 的 `showTab` 切到别的页）时调用 `panes.library.onHide()`：停掉试听（L-24）与悬停播放（L-22）。现状顶部播放区切页后仍在后台出声，本条一并修掉。 — 无裁决（面 F13 未盘问）
- L-50 `node --test`：纯函数（合并含 B-43、missing、筛选、排序缺值在后）；假 DOM：视图切换与记忆（含存储抛错）、单击选中/双击打开、键盘移动、预览 ←/→ 与到头置灰、回填调用 applyFill 并关闭、reveal 失败文案、试听按钮不冒泡。现有 `library_pane.test.js` 中依赖顶部播放区的断言改为断言预览弹层。 — 无裁决（面 F13 未盘问）
- L-51 e2e（Playwright）：三视图渲染、预览打开/切换/关闭、键盘导航、回填回到对应页面（沿用 `test_library_panel.py` 的回填用例）、切页停声（L-45）；在 1280 与 900 宽截图目检，截图目录由 `$LMD_LIBRARY_SHOTS` 指定。 — 无裁决（面 F13 未盘问）
- L-52 迁移依赖 `[data-lib-player]` 的现有 e2e：`test_image_sessions.py`（约 329–355 行，含「预览与刷新按钮的间距」断言，改为断言弹层里图片的尺寸）、`test_image_flow.py`（约 466 行）；（`test_library_panel.py::test_audio_player_matches_the_dark_palette` 只查音乐会话卡片的播放器，不受影响）；`test_outputs_range.py` 只等 `[data-lib-list] li`，改为等 `[data-lib-item]`。 — 无裁决（面 F13 未盘问）
- L-53 WebKit 核对：应用外壳是 WKWebView，而 e2e 默认跑 Chromium。视频首帧缩略图（`#t=0.1` + `preload="metadata"`）与悬停播放须另用 Playwright WebKit（本机已装 webkit-2272）跑一条用例确认能出首帧；不行则退回「视频图标 + 时长」占位并在本文件记下。 — 无裁决（面 F13 未盘问）
- Z-01 合法画幅：宽、高都是整数且为 32 的倍数；每边 256–1344；`宽×高 ≤ 768×1344`。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-02 违规文案（按此顺序取第一条）：「宽和高须为整数」「宽和高须为 32 的倍数」「每边须在 256–1344 之间」「面积不能超过 768×1344（约 103 万像素）」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-03 后端 `start_video_job` 在任何会话写入之前做同样校验，违规返回 400 `invalid_params`，文案「画幅须为 32 的倍数，每边 256–1344，面积不超过 768×1344」；拒绝时会话不留尝试记录（B-33）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-04 镜像测试：一个 Python 测试读出 JS 与 Python 两边的常量（32、256、1344、768×1344）和内存公式参数（27.0、1.4、草稿体积 512×288×49、预算 40），任何一边改了另一边不跟就失败。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-13 切换方向时保持同一档（草稿→草稿……）；当前是自定义时切方向，取新方向的「标准」档。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-14 选「自定义…」出现宽、高两个数字输入，初值为切换前选中的那一档；输入框失焦时取最近的 32 的倍数（`snap32`）；提交前不合规按 Z-02 写在高级参数错误行并拦下（沿用现有 `ParamsError({advanced:true})`）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-15 默认：横屏 · 草稿（与现状 512×288 一致）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-20 形状判定：`0.9 ≤ 宽/高 ≤ 1.1` 为方形；否则宽>高为横屏、高>宽为竖屏。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-21 「图生」模式下首帧来源变化（上传选中、本页「从图片会话选…」、图片页「用这张生成视频」）且读到首帧尺寸后：若当前不是自定义且首帧方向 ≠ 当前方向，就切到首帧方向、保持档位（Z-13），在首帧说明旁提示「已按首帧切到<方向>」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-22 首帧尺寸来源：上传文件在浏览器里解码读 `naturalWidth/Height`；图片会话引用读该尝试的 `params.width/height`（`panes/video.js` 的 `lookupImage` 现只返回 `{output,title,index}`，需补上 `width,height`）；读不到（解码失败、参数缺失）就不跟随、不提示。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-23 跟随后用户手动改方向：照用户的，提示消失，同一个首帧不再自动切回。换了新的首帧重新判定。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-24 当前是自定义尺寸时不自动改，形状不一致时提示「首帧是<方向>，画幅是<方向>，画面会被拉伸变形」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-25 续写的首帧（上一段末帧）不触发跟随（见 Z-30）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-26 「在这段基础上改」「换个版本」与素材库「回填参数」恢复的是当时保存的尺寸（Z-31），带回的首帧不触发跟随，也不出提示。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-30 「接着往下生」时方向控件、档位下拉、自定义输入全部禁用，`title`「接着往下生沿用上一段的画幅」；点提示条 × 取消续写后恢复可用。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-31 续写、「换个版本」「在这张基础上改」、素材库「回填参数」带入的尺寸，用 `matchSize(width, height)` 找回方向与档位；不在任何档位里则选「自定义…」并填入宽高。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-32 卡片、素材库里显示的尺寸照旧是 `宽×高`，竖屏与自定义同样显示。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-40 耗时：`宽×高 ≥ 1024×576` 且帧数 ≥ 243（约 10 秒档）时显示「大画幅加 10 秒以上会非常慢：实测 1024×576 曾 20 分钟只走完 2/16 步，可能要一小时以上。建议先用草稿画幅试效果。」 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-41 H3 预算：`估算 = 27.0 + 1.4 × max(宽×高×帧数 ÷ (512×288×49) − 1, 0)` GiB，与 `memory_estimate.py` 同源；超过 40 时显示「按实测外推约需 N GiB，超过视频生成的 40 GiB 上限，可能中途失败。」（N 取整）。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-42 两条可同时出现，显示在现有耗时提醒位置（`[data-video-cost-note]`）；参数一变就更新。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-43 `pure/video_cost.js` 并入 `pure/video_size.js` 后删除。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-50 JS 单测：Z-01 边界（255/256、1344/1376、面积恰为上限与超 1 格）、Z-02 文案顺序、`snap32`、Z-11 全部档位合法、Z-13、Z-20 边界（0.9、1.1）、Z-21/23/24、Z-30、Z-31（档位内、竖屏、自定义）、Z-40/41 文案与阈值。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-51 Python：Z-03 各类违规 400 且会话无新尝试；合法竖屏与自定义能启动；Z-04 镜像测试。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-52 e2e：竖屏 · 标准与自定义 448×800 各生成一次，请求体与卡片尺寸正确；上传方图做首帧后方向切到方形并出提示；续写时画幅控件禁用；截图目检（1280 与 900 宽），截图目录 `$LMD_VIDEO_SIZE_SHOTS`。 — 无裁决（面 F9 已盘问但无裁决引用它）
- Z-53 实测（2026-10-07）：512×512 正圆首帧生成 512×288，第一帧圆被压成椭圆、8 条横线全在、输出 512×288——H3 **拉伸**首帧到画布，不裁切。Z-24 措辞据此为「拉伸变形」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- R-e2e-01 测试态服务可启动：注入假后端、临时数据根与临时模型根，浏览器可访问， 全流程确定性可重复；断言全程未触碰真实权重目录与真实 outputs。 — 无裁决（面 F18 未盘问）
- R-e2e-02 首运流程：无配置时呈现首运界面；选定 models 目录后进入主界面；配置确已落盘。 — 无裁决（面 F18 未盘问）
- R-e2e-03 聊天流程：选模型 → 加载 → 发消息 → 看到**逐步增长**的流式正文 → 思考块可展开 → 回复入库。 必须断言「增量确实是分批到达的」，而不是一次性出现（否则流式没被证明）。 — 无裁决（面 F18 未盘问）
- R-e2e-04 多会话：新建 / 切换 / 重命名 / 删除；**刷新页面后仍在**。 — 无裁决（面 F18 未盘问）
- R-e2e-05 资源面板：齐 / 一半 N% / 没下 三态正确渲染且百分比正确； 下载 → 进度推进 → 取消 → 续传 的控件流转；删除需二次确认；剩余空间可见。 — 无裁决（面 F18 未盘问）
- R-e2e-06 视频流程：填参数 → 启动 → 进度可见 → 完成后播放器出现且 `src` 指向新成品。 — 无裁决（面 F18 未盘问）
- R-e2e-07 音乐流程：同上。 — 无裁决（面 F18 未盘问）
- R-e2e-08 互斥在 UI 上可见：媒体运行中，加载按钮与另一媒体按钮均被禁用，状态条给出拒绝原因； 媒体结束后恢复可用。 — 无裁决（面 F18 未盘问）
- R-e2e-09 素材库：点历史项把当时参数回填进对应表单（逐字段断言）；点成品可播放。 — 无裁决（面 F18 未盘问）
- R-e2e-10 状态条显示**真实内存数值**并随状态变化；断言页面上不存在写死的 `128` 内存字面量。 — 无裁决（面 F18 未盘问）
- R-e2e-11 设置面板显示对外 API 的两条 base URL（OpenAI 与 Anthropic），并明示当前无鉴权。 — 无裁决（面 F18 未盘问）
- R-e2e-12 **零直连断言**：通过浏览器网络拦截，断言整场 e2e 期间前端**没有向 `127.0.0.1:8767` 发出任何请求**。这条以行为方式证明 census A17，比 grep 更强。 — 无裁决（面 F18 未盘问）
- D-44a 以图生图（2026-09-24 修订，用户确认）：被回填的尝试有图（`status == done`、有 `output` 且文件还在）时，提示条改为「以第 N 次为底稿」；提示条仍在时点「生成图片」，请求带 `base: {attempt_id, strength: 0.6}`，后端以那张图为底稿重绘（保留构图、重画细节），宽高取底稿的宽高。没图的尝试（失败、取消、文件不在）仍按 D-40–D-44 只回填、按文生图生成。提示条隐藏（改了种子或点 ×）后同样退回文生图。 — 无裁决（面 F8 未盘问）
- D-47a 以图生图（2026-09-24 修订）：该尝试有图时，提交带 `base: {attempt_id, strength: 0.35}`，以这张为底稿重绘（保留主体与色调、换构图）。没图的尝试「换个构图」不可用，按钮下方原因行为「这一次没有图片，不能以它为底稿换个构图」。 — 无裁决（面 F8 未盘问）
- D-47b 以图生图的强度只允许 0.6 与 0.35 两档（mflux 约定：强度越高越接近底稿）；后端校验底稿属于同一会话、状态为 done 且文件存在，否则分别返回 400 `invalid_params`、404 `base_not_found`、404 `base_missing`。尝试记录 `base: {attempt_id, strength}`（文生图为 `null`），卡片标题行显示「基于第 N 次」（底稿不在列表中则不显示）。 — 无裁决（面 F8 未盘问）
- D-50a 例外（用户 2026-09-24 决定）：「素材库」页不属于图片主流程，其条目元数据可以显示「种子 N」；本需求只改图片页（BR-1），素材库文案保持不变。D-50 与视觉标准的「种子」全局规则只适用于图片页。 — 无裁决（面 F8 未盘问）
- BR-1 只改图片页；视频、音乐页不动 — 无裁决（面 F8 未盘问）
- BR-2 会话持久化在本机，重启 app 后仍在，每个会话一个 JSON 文件，沿用聊天会话的存储方式 — 无裁决（面 F8 未盘问）
- BR-3 会话内按时间顺序列出每次尝试：图片、提示词、宽高、步数、种子；失败或取消的尝试也列出并写明原因 — 无裁决（面 F8 未盘问）
- BR-4 会话需手动新建（像聊天的「新建」）；未新建时生成接在当前会话；会话标题默认取第一次生成的提示词 — 无裁决（面 F8 未盘问）
- BR-5 会话可切换、重命名、删除；删除会话只删分组，图片文件保留并仍出现在素材库 — 无裁决（面 F8 未盘问）
- BR-6 打开任意一次尝试后给两个动作：「在这张基础上改」把提示词回填到输入框并沿用该张种子，用户改完再生成；「换个构图」提示词不变、换一个新随机种子直接再生成 — 无裁决（面 F8 未盘问）
- BR-7 界面主流程不出现「种子」一词；种子与宽高、步数一起收进「高级参数」 — 无裁决（面 F8 未盘问）
- BR-8 新尝试总是追加到当前会话末尾，不覆盖旧图 — 无裁决（面 F8 未盘问）
- BR-9 局部重绘/图生图不在本次范围 — 无裁决（面 F8 未盘问）
- AC-1 连续三轮「生成 → 在这张基础上改 → 再生成」后，三张图及各自参数都在同一个会话里按顺序显示 — 无裁决（面 F8 未盘问）
- AC-2 「在这张基础上改」生成的新图与原图种子相同；「换个构图」生成的新图提示词相同而种子不同 — 无裁决（面 F8 未盘问）
- AC-3 重启 app 后会话列表、每个会话的尝试和图片都还在 — 无裁决（面 F8 未盘问）
- AC-4 切到另一个会话再切回，内容不变；新建会话后生成的图只进新会话 — 无裁决（面 F8 未盘问）
- AC-5 删除会话后会话从列表消失，其中的图片仍能在素材库打开 — 无裁决（面 F8 未盘问）
- AC-6 失败或取消的尝试在会话里可见并显示原因，不会留下一张空白图 — 无裁决（面 F8 未盘问）
- AC-7 在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误 — 无裁决（面 F8 未盘问）
- B-38a 模型产出后、开始拼接前，先调用 `store.record_output(session_id, attempt_id, output)` 把单段文件名写进仍为 running 的尝试。之后任何中断都不丢这一段： — 无裁决（面 F12 未盘问）
- B-38b 重活许可在**模型子进程退出时**释放（拼接只用 ffmpeg，不该继续占着 arbiter 的内存额度挡住聊天加载）；`_finalize` 对已释放的许可不再释放（只释放一次）。compose 作业没有许可（B-45）。 — 无裁决（面 F12 未盘问）

## 逐面完成度

### 聊天会话持久化与上下文压缩（F5）— 0 问中 0 问实证通过 · 操作面 4 个，裁决触及 3 个，未触及：S46 删除聊天会话

### 视频会话：四种生成方式、画幅、首尾帧、续写、换版本、合成（F9）— 0 问中 0 问实证通过 · 操作面 4 个，裁决触及 2 个，未触及：S29 合成作业（把多段拼接起来）、S71 子进程契约：ffmpeg/ffprobe（拼接、取末帧、截取音频、素材探测，可用 LOCALMODELDESK_<NAME> 覆盖路径）

### visual-acceptance（视觉验收，双审）（F22）— 32 问中 7 问实证通过 · 操作面未登记，覆盖不可算
- **缺口** [G1] [F22] 视觉验收 v05-chat A · gap — 10 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v05-chat/）
- **实证完成** [F22] 视觉验收 v05-chat A · done — 3 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v05-chat/）
- **缺口** [G2] [F22] 视觉验收 v05-chat B · gap — 8 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v05-chat/）
- **实证完成** [F22] 视觉验收 v05-chat B · done — 2 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v05-chat/）
- **缺口** [G3] [F22] 视觉验收 v05-chat C · gap — 7 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v05-chat/）
- **实证完成** [F22] 视觉验收 v05-chat C · done — 3 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v05-chat/）
- **缺口** [G4] [F22] 视觉验收 v06-video A · gap — 15 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v06-video/）
- **实证完成** [F22] 视觉验收 v06-video A · done — 1 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v06-video/）
- **缺口** [G5] [F22] 视觉验收 v06-video B · gap — 7 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v06-video/）
- **实证完成** [F22] 视觉验收 v06-video B · done — 6 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v06-video/）
- **缺口** [G6] [F22] 视觉验收 v06-video C · gap — 7 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v06-video/）
- **实证完成** [F22] 视觉验收 v06-video C · done — 6 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v06-video/）
- **缺口** [G7] [F22] 视觉验收 v07-image-music A · gap — 16 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v07-image-music/）
- **无法自证** [F22] 视觉验收 v07-image-music A-mid · unprovable — 2 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v07-image-music/）
- **缺口** [G8] [F22] 视觉验收 v07-image-music B · gap — 16 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v07-image-music/）
- **无法自证** [F22] 视觉验收 v07-image-music B-mid · unprovable — 2 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v07-image-music/）
- **缺口** [G9] [F22] 视觉验收 v07-image-music C · gap — 16 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v07-image-music/）
- **无法自证** [F22] 视觉验收 v07-image-music C-mid · unprovable — 2 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v07-image-music/）
- **缺口** [G10] [F22] 视觉验收 v08-resources-library A · gap — 12 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v08-resources-library/）
- **无法自证** [F22] 视觉验收 v08-resources-library A-mid · unprovable — 6 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v08-resources-library/）
- **缺口** [G11] [F22] 视觉验收 v08-resources-library B · gap — 12 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v08-resources-library/）
- **缺口** [G12] [F22] 视觉验收 v08-resources-library C · gap — 12 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v08-resources-library/）
- **无法自证** [F22] 视觉验收 v09-dialogs 900x600@1 · unprovable — 20 例；dialogs 组缺 skill-install/preview（产品 404 造不出），整组无法裁决（证据：evidence/v09-dialogs/）
- **无法自证** [F22] 视觉验收 v09-dialogs mid · unprovable — 15 例；dialogs 组缺 skill-install/preview（产品 404 造不出），整组无法裁决（证据：evidence/v09-dialogs/）
- **无法自证** [F22] 视觉验收 v09-dialogs 1400x900@1 · unprovable — 20 例；dialogs 组缺 skill-install/preview（产品 404 造不出），整组无法裁决（证据：evidence/v09-dialogs/）
- **无法自证** [F22] 视觉验收 v09-dialogs 2560x1440@1 · unprovable — 20 例；dialogs 组缺 skill-install/preview（产品 404 造不出），整组无法裁决（证据：evidence/v09-dialogs/）
- **实证完成** [F22] 视觉验收 v10-settings A · done — 12 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v10-settings/）
- **无法自证** [F22] 视觉验收 v10-settings A-mid · unprovable — 3 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v10-settings/）
- **缺口** [G13] [F22] 视觉验收 v11-firstrun-fatal-shellerror A · gap — 10 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v11-firstrun-fatal-shellerror/）
- **无法自证** [F22] 视觉验收 v11-firstrun-fatal-shellerror A-mid · unprovable — 9 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v11-firstrun-fatal-shellerror/）
- **缺口** [G14] [F22] 视觉验收 v11-firstrun-fatal-shellerror B · gap — 10 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v11-firstrun-fatal-shellerror/）
- **缺口** [G15] [F22] 视觉验收 v11-firstrun-fatal-shellerror C · gap — 10 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v11-firstrun-fatal-shellerror/）

## 旅程完成度

### J2 日常用户（单人在自己的 Mac 上用本地模型聊天） · 模型目录里已下载聊天模型，app 正常在跑，可能已有聊天模型加载着（同此刻的真实状态）；在一个会话里连续问至少 3 轮、每条用户消息约 30 字，其中一轮回答中途按停止；然后 ⌘Q 退出 app 再打开 · 这段对话在重启后完整保留，并能在其中继续聊 — 实证完成
在此情形下走通（模型目录里已下载聊天模型，app 正常在跑，可能已有聊天模型加载着（同此刻的真实状态）；在一个会话里连续问至少 3 轮、每条用户消息约 30 字，其中一轮回答中途按停止；然后 ⌘Q 退出 app 再打开），17 步（证据：evidence/q03-J2/） · 实测处境：Started from existing state: 8 existing sessions in the session list; banner '内存里：无' at start；Created 1 new session; model SuperQwen3.8 27B 越狱 4bit (dropdown option 2 of 6)；Round 1 input: 28 characters; waited 30s；Round 2 input: 31 characters; pressed 停止 about 8-12s after sending, while the answer was streaming the '第 1 步' section；Round 3 input: 32 characters; waited 25s；Quit via cmd-Q keystroke; attempt 1 did not quit (front was pid 1446), attempt 2 quit within 1s；Reopened with open dist/LocalModelDesk.app; 8766 listening after about 2s; new pids: shell 41426, desk 41469；Round 4 after the restart: 27 characters; waited 25s; model re-selected by hand (dropdown had defaulted to GLM)；Browser viewport 1280x800, CSS scale; app window 1200x832 pt captured with screencapture and downscaled to 1x
- 1 done Clicked 新会话 → A '新会话 · 05:15' entry appeared at the top of the session list; the model row shows SuperQwen selected; banner '内存里：无'
- 2 done Clicked 加载 (SuperQwen3.8 27B 越狱 4bit) → Within 20s the status read '已加载：SuperQwen3.8 27B 越狱 4bit', the banner read '内存里：SuperQwen3.8 27B 越狱 4bit', and the empty-session hint '这是一个新会话。选好模型、点「加载」，然后在下面输入第一句。' was shown
- 3 done Typed round-1 message (28 chars) into the message box → The text was filled into the '输入消息，⌘Enter 发送' box (the snapshot taken after the send click shows it as a user bubble)
- 4 done Clicked 发送, waited 30s → Answer '三道适合新手的周末家常菜' with '已思考 11 秒', listing 西红柿炒鸡蛋 / 蒜蓉西兰花 / 紫菜蛋花汤; the button read 发送 again
- 5 done Typed round-2 message (31 chars) → The text was filled into the message box (shown as a user bubble in the post-send snapshot)
- 6 done Clicked 发送, waited 8s → The answer was streaming, at heading '正式'; the send button read '停止'
- 7 done Clicked 停止 → Streaming stopped at '> 火候要点：此步用中火而非大火，'; the label read '▸ 已停止'; red '已停止生成' and a '重试' button appeared; the button went back to 发送
- 8 done Typed round-3 message (32 chars) → The text was filled into the message box (shown as a user bubble in the post-send snapshot)
- 9 done Clicked 发送, waited 25s → Answer '大蒜（切末）、蚝油、盐。' (已思考 4 秒); the session list entry read '我想在周末做一顿… superqwen · 05:17'; '重试' still visible under round 2; message list scrolls under the model row; a second scrollbar at the lower right of the message area
- 10 done Sent cmd-Q (attempt 1, after activateWithOptions on pid 28670) → lsappinfo front reported pid 1446, not the app; after 10s processes 28670, 28677 and 25339 were still running and 8766 was still listening
- 11 done Sent cmd-Q (attempt 2, front pid confirmed 28670) → No dialog; within about 1s the shell, desk and mlx_lm processes were gone and nothing listened on 8766 or 8767
- 12 done Ran open /Users/aa/LocalModelDesk/dist/LocalModelDesk.app → 8766 listening after about 2s (shell 41426, desk 41469). The app window opened on 聊天 with my session selected at the top of the list, the stopped round 2 with '回答没有生成完：已停止生成', and round 3 below it; '内存里：无'; dropdown on GLM 4.7 Flash
- 13 done Re-navigated the browser to http://127.0.0.1:8766/ → The same session opened automatically. Compared with before the quit, all messages were present; differences were limited to the round-2 label, the stopped-notice wording and the missing 重试 button (see the diff file)
- 14 done Selected 'SuperQwen3.8 27B 越狱 4bit' in the model dropdown → The dropdown showed SuperQwen; status still read 未加载
- 15 done Clicked 加载 → '已加载：SuperQwen3.8 27B 越狱 4bit' appeared within a few seconds
- 16 done Typed round-4 message (27 chars) → The text was filled into the message box (shown as a user bubble in the post-send snapshot)
- 17 done Clicked 发送, waited 25s → Answer listed 西红柿炒鸡蛋 / 蒜蓉西兰花 / 紫菜蛋花汤 below the earlier turns in the same session; the session list entry time updated to 05:20

### J2-squeezed 日常用户（单人在自己的 Mac 上用本地模型聊天） · 模型目录里已下载聊天模型，app 正常在跑，可能已有聊天模型加载着（同此刻的真实状态）；在一个会话里连续问至少 3 轮、每条用户消息约 30 字，其中一轮回答中途按停止；然后 ⌘Q 退出 app 再打开；窗口取 900×600（普查 width_range.min × height_range.min）；每条用户消息取真实使用的最长内容：约 2000 字（约 60 行） · 这段对话在重启后完整保留，并能在其中继续聊 — 实证完成
在此情形下走通（模型目录里已下载聊天模型，app 正常在跑，可能已有聊天模型加载着（同此刻的真实状态）；在一个会话里连续问至少 3 轮、每条用户消息约 30 字，其中一轮回答中途按停止；然后 ⌘Q 退出 app 再打开；窗口取 900×600（普查 width_range.min × height_range.min）；每条用户消息取真实使用的最长内容：约 2000 字（约 60 行）），17 步（证据：evidence/q04-J2-squeezed/） · 实测处境：9 existing sessions in the session list (none opened or changed); I created 1 new session；Start: no model loaded (内存里：无); memory 已用 68 / 总 128 GiB；Model: first dropdown option, GLM 4.7 Flash 越狱 8bit · 29.7 GiB · 30B-A3B; load took under 20s；Messages pasted (textarea value set + input event): 2310 / 2318 / 2317 / 2336 chars, 60 lines each；3 rounds before the quit, 1 round after the restart；Stopped round 2 about 38s after sending, while the reply was at 第13-16行；Browser viewport 900x600 at DPR 1; app window resized to 900x600 (CG bounds 900x632)；First run of this journey by this prober; quit-to-reopen gap 8s
- 1 done Click 新会话 → Empty new session with hint 这是一个新会话。选好模型、点「加载」，然后在下面输入第一句。; 未加载
- 2 done Keep GLM 4.7 Flash selected, click 加载, wait 20s → 已加载：GLM 4.7 Flash 越狱 8bit; status bar 已用 89 GiB
- 3 done Paste message 1 (2310 chars / 60 lines) into the input box → Input box shows the first two lines with an internal scrollbar
- 4 done Click 发送; take a full-page screenshot while streaming → Thinking content streams in; button reads 停止; full-page screenshot is 900x600
- 5 done Wait for round 1 to finish → 已思考 28 秒 plus a 3-sentence summary; session title in the list becomes 第1行：甲组记录，…
- 6 done Paste message 2 (2318 chars, asks for a detailed line-by-line critique) → Text is in the input box
- 7 done Press ⌘Enter; full-page screenshot while the answer streams (38s in) → Answer text streaming, at 第13行 点评; button 停止
- 8 done Click 停止 → Text stops at 第16行： **点评; button back to 发送; the 已停止生成 line sits just below the visible scroll area; a 重试 row appears
- 9 done Paste message 3 (2317 chars) → Text is in the input box
- 10 done Press ⌘Enter and wait → Finished in 18s with a one-sentence answer; DOM has 3 user + 3 assistant messages + 重试 row
- 11 done Check for media jobs, then ⌘Q the app (pid 41426) → No media process; app and :8766 gone within 1s
- 12 done open dist/LocalModelDesk.app → Service up within 1s, pids 80020/80093; window 1200x832, resized to 900x600
- 13 done Reload http://127.0.0.1:8766/ in the browser → Lands in my session; all 6 messages present at the same lengths; stopped reply ends with 回答没有生成完：已停止生成; no 重试 row; 未加载
- 14 done Screenshot the reopened app window → App window shows my session, scrolled to the start of the round-2 reply, not the bottom
- 15 done Click 加载 → 已加载：GLM 4.7 Flash 越狱 8bit
- 16 done Paste message 4 (2336 chars, asks how many notes we discussed) → Text is in the input box
- 17 done Press ⌘Enter and wait → In 11s: 我们一共讨论了四份笔记，分别是甲组、乙组、丙组和丁组。; 8 messages, scrolled to the bottom

### J5 创作者（为短视频平台做内容） · 视频模型在模型目录里，聊天模型可能仍加载着（同此刻）；新建一个视频会话，写一段约 80 字的中文提示词，选竖屏 · 得到一段可播放的竖屏视频并留在会话里 — 实证完成
在此情形下走通（视频模型在模型目录里，聊天模型可能仍加载着（同此刻）；新建一个视频会话，写一段约 80 字的中文提示词，选竖屏），10 步（证据：evidence/q01-J5/） · 实测处境：The video session library already had 4 sessions (海边日落 3 次 / 江南水乡 1 次 / 方案一 2 次 / 竹林 1 次)；Started from existing state: chat model SuperQwen3.8 27B 越狱 4bit in memory, memory used 85/128 GiB；Created 1 new video session at 16:59；Prompt was 77 characters (Chinese characters plus punctuation), including an ambient-sound description；Mode left on 文生视频 as shown. Clicked 竖屏. Size preset left as shown, 草稿 288×512. Length left as shown, 约 2 秒（快速）. 16 steps. 高级参数 not opened；First run. Two waits: 60s, then 90s. Done about 2 minutes 45 seconds after clicking；Playwright viewport 1440x900, DPR 1, new tab in a regular browser (not the app window)
- 1 done Click the 视频 tab in the top navigation → The video page opened showing the existing session 「海边日落…」 with its 3 runs. Header reads 「生成视频 · 模型文件完整 · 可离线生成」. Below are 生成方式=文生视频, orientation 横屏/竖屏/方形 (横屏 selected), and the prompt box
- 2 done Click 新会话 in the left sidebar → The list gained an entry 「新会话 · 0 次生成 · 16:59」, now selected. The result area shows 「还没有视频」 plus usage hints, and 挑几段合成… is greyed out
- 3 done Click the 竖屏 orientation button → 竖屏 is highlighted. The size preset options in 高级参数 changed to 草稿 288×512 / 标准 448×768 / 清晰 576×1024
- 4 done Type the 77-character Chinese prompt into the prompt box → The prompt box shows the full text across two lines
- 5 done Click 生成视频 → No confirm dialog. The card shows 「第 1 次 · 生成中…（已用 5秒）」, 文生 · 288×512 · 约 2 秒 · 16 步, a progress bar and 取消. The list entry title became the start of the prompt with a 生成中 tag. The top bar shows 内存里：视频生成中 / 不可：媒体作业进行中. Below the form: 「正在生成这个会话里的第 1 次」
- 6 done Wait 60 seconds → The card shows 「第 1 次 · 生成中…（已用 1分15秒）」 and is still generating
- 7 done Wait 90 seconds → Generation finished. The card shows a portrait video with 0:00 / 0:02 controls, the prompt, and 在这段基础上改/换个版本/接着往下生/配乐…. The list entry reads 1 次生成 · 17:01. The top bar is back to SuperQwen3.8 27B 越狱 4bit in memory / 媒体：空闲. The card title and the top of the video were cut off at the top of the result area
- 8 done Scroll the result area to the top → The card title 「第 1 次 · 16:59 文生 · 288×512 · 约 2 秒 · 16 步」 shows. The video shows a girl in a red coat holding a transparent umbrella on a wet night street. The bottom of the card is cut off by the form. Video element: videoWidth 288, videoHeight 512, duration 2.33
- 9 done Click the play button on the video controls → The control changed to a pause icon and the frame changed (the girl moved). 1.2s later currentTime=1.14, paused=false, no error. The control bar still read 0:00 / 0:02
- 10 done Reload the page → Still on #tab=video. The first list entry 「夜晚的城市街头…」 1 次生成 · 17:01 is selected. The card shows the same video (same src, 288x512). The orientation control shows 横屏 and the prompt box is empty

### J5-squeezed 创作者（为短视频平台做内容） · 视频模型在模型目录里，聊天模型可能仍加载着（同此刻）；新建一个视频会话，写一段约 80 字的中文提示词，选竖屏；窗口取 900×600；提示词取真实使用的最长内容：约 600 字（约 15 行） · 得到一段可播放的竖屏视频并留在会话里 — 实证完成
在此情形下走通（视频模型在模型目录里，聊天模型可能仍加载着（同此刻）；新建一个视频会话，写一段约 80 字的中文提示词，选竖屏；窗口取 900×600；提示词取真实使用的最长内容：约 600 字（约 15 行）），11 步（证据：evidence/q02-J5-squeezed/） · 实测处境：viewport 900×600, devicePixelRatio 1, Chrome DevTools MCP isolatedContext page (app window not resized)；chat model loaded at start: SuperQwen3.8 27B 越狱 4bit; memory 已用 80 / 总 128 GiB (可用 48 GiB)；video page had 5 existing sessions; started from a new empty session created at 17:06；prompt is 15 lines, 655 characters with line breaks (641 without), filled in with one fill call; full text in q02-04-prompt-text.txt；生成方式 文生视频 (left as it was), 竖屏 clicked before filling the prompt, advanced params not touched；one generation, first run; clicked about 17:07:26, finish detected at 17:09:01 (about 95 s)；playback started with JS video.play(), not by clicking the control bar
- 0 done Opened http://127.0.0.1:8766/ at 900x600 DPR1 and recorded the starting state → Chat tab. The top bar shows SuperQwen3.8 27B 越狱 4bit loaded, 媒体：空闲, 可开工. The sidebar shows a native scrollbar.
- 1 done Clicked the 视频 tab → URL changed to #tab=video. There are 5 sessions and the 17:01 '夜晚的城市街头' session opened by itself. The heading reads '生成视频 · 模型文件完整 · 可离线生成'. The composer has 生成方式 文生视频 and 横屏 (selected) / 竖屏 / 方形.
- 2 done Clicked 新会话 → A '新会话 · 0 次生成 · 17:06' item appears at the top of the list. The result area reads '还没有视频' with usage hints.
- 3 done Clicked 竖屏 → 竖屏 is highlighted and 横屏 is no longer highlighted.
- 4 done Filled the 15-line, 655-character storyboard prompt into the 视频提示词 box → The prompt box grew to 240px and shows about 9 lines, with an inner scrollbar. The 生成方式/横竖方形 row is no longer visible (radios measured at y=288-314, under the prompt box top at y=290). The '还没有视频' area shrank to the top. The 生成视频 button is at the bottom right.
- 5 done Clicked 生成视频 → No dialog appeared. The session item shows '生成中'. The top bar shows '视频生成中 · 媒体：忙'. The card meta reads '288×512'. The 生成视频 button is disabled with the status text '正在生成这个会话里的第 1 次'. The result area shows only the 取消 and 日志 controls.
- 6 done Took a full-page screenshot while the job was running (11 s in) → The full page equals the viewport (document height 600). The result area is 94px tall and scrolled to its bottom. The visible text is 第 1 次 · 生成中…（已用 11秒）.
- 7 done Waited in the foreground until the card had a video and no '生成中' text (72 s inside the script, about 95 s since the click) → The card reads '第 1 次 · 17:07' and the top bar is back to the chat model and 媒体：空闲. The viewport shows the bottom of the card (高级参数 and the four action buttons). The video element is at y=-735, outside the visible area.
- 8 done Scrolled the result area until the video came into view → The lower part of the video shows (a lane picture and the control bar 0:00 / 0:02). The video top is at y=-30 and is cut off by the result area's top edge.
- 9 done Started playback (JS video.play()) → currentTime 1.09s after 1.2s, paused=false, duration 2.33s, 288x512. The frame shows a stacked bamboo steamer in a narrow vertical frame with black side bars.
- 10 done Reloaded the page to check the video stays in the session → The session '竖屏短视频分镜…' is first in the list with '1 次生成 · 17:09'. The card has the Video element (total time 0:02). The viewport shows the card's bottom text and buttons. The composer is reset to 横屏 with an empty prompt box.

## 缺口清单（按严重度）
- **high** **缺口** [G1] [F22] 视觉验收 v05-chat A · gap — 10 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v05-chat/）
- **high** **缺口** [G2] [F22] 视觉验收 v05-chat B · gap — 8 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v05-chat/）
- **high** **缺口** [G3] [F22] 视觉验收 v05-chat C · gap — 7 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v05-chat/）
- **high** **缺口** [G4] [F22] 视觉验收 v06-video A · gap — 15 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v06-video/）
- **high** **缺口** [G5] [F22] 视觉验收 v06-video B · gap — 7 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v06-video/）
- **high** **缺口** [G7] [F22] 视觉验收 v07-image-music A · gap — 16 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v07-image-music/）
- **high** **缺口** [G8] [F22] 视觉验收 v07-image-music B · gap — 16 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v07-image-music/）
- **high** **缺口** [G9] [F22] 视觉验收 v07-image-music C · gap — 16 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v07-image-music/）
- **medium** **缺口** [G6] [F22] 视觉验收 v06-video C · gap — 7 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v06-video/）
- **medium** **缺口** [G10] [F22] 视觉验收 v08-resources-library A · gap — 12 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v08-resources-library/）
- **medium** **缺口** [G11] [F22] 视觉验收 v08-resources-library B · gap — 12 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v08-resources-library/）
- **medium** **缺口** [G12] [F22] 视觉验收 v08-resources-library C · gap — 12 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v08-resources-library/）
- **medium** **缺口** [G13] [F22] 视觉验收 v11-firstrun-fatal-shellerror A · gap — 10 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v11-firstrun-fatal-shellerror/）
- **medium** **缺口** [G14] [F22] 视觉验收 v11-firstrun-fatal-shellerror B · gap — 10 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v11-firstrun-fatal-shellerror/）
- **medium** **缺口** [G15] [F22] 视觉验收 v11-firstrun-fatal-shellerror C · gap — 10 例；双审 claude+codex（gpt-5.6-sol）（证据：evidence/v11-firstrun-fatal-shellerror/）

## 无法自证清单（待人工验证，不计为完成也不计为失败）
- **无法自证** [F22] 视觉验收 v07-image-music A-mid · unprovable — 2 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v07-image-music/）
- **无法自证** [F22] 视觉验收 v07-image-music B-mid · unprovable — 2 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v07-image-music/）
- **无法自证** [F22] 视觉验收 v07-image-music C-mid · unprovable — 2 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v07-image-music/）
- **无法自证** [F22] 视觉验收 v08-resources-library A-mid · unprovable — 6 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v08-resources-library/）
- **无法自证** [F22] 视觉验收 v09-dialogs 900x600@1 · unprovable — 20 例；dialogs 组缺 skill-install/preview（产品 404 造不出），整组无法裁决（证据：evidence/v09-dialogs/）
- **无法自证** [F22] 视觉验收 v09-dialogs mid · unprovable — 15 例；dialogs 组缺 skill-install/preview（产品 404 造不出），整组无法裁决（证据：evidence/v09-dialogs/）
- **无法自证** [F22] 视觉验收 v09-dialogs 1400x900@1 · unprovable — 20 例；dialogs 组缺 skill-install/preview（产品 404 造不出），整组无法裁决（证据：evidence/v09-dialogs/）
- **无法自证** [F22] 视觉验收 v09-dialogs 2560x1440@1 · unprovable — 20 例；dialogs 组缺 skill-install/preview（产品 404 造不出），整组无法裁决（证据：evidence/v09-dialogs/）
- **无法自证** [F22] 视觉验收 v10-settings A-mid · unprovable — 3 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v10-settings/）
- **无法自证** [F22] 视觉验收 v11-firstrun-fatal-shellerror A-mid · unprovable — 9 例中间宽度比较组用例；校验器组规则与抽象冲突（证据：evidence/v11-firstrun-fatal-shellerror/）

## 未盘问声明（按风险排序）
- macOS 外壳：拉起服务、窗口、菜单、菜单栏、错误页、退出（F1）— 未盘问，不计入任何完成度 · 风险 high：外壳负责拉起服务与窗口、退出收割；坏了整个应用打不开或留孤儿进程
- 首次运行、配置与模型目录（含收编、重置、自动扫描、致命错误页）（F2）— 未盘问，不计入任何完成度 · 风险 high：首次运行与模型目录决定能否用起来；致命配置错误页是唯一恢复路径
- 聊天：模型加载/卸载/驱逐与流式对话（F4）— 未盘问，不计入任何完成度 · 风险 high：聊天是主线；加载/驱逐/流式坏了核心价值不可用（J2 旅程部分覆盖）
- 图片会话：生成、换构图、在此基础上改、用这张生成视频（F8）— 未盘问，不计入任何完成度 · 风险 high：图片会话 93 条需求，主打能力之一
- 音乐会话：风格+歌词、接着写、换版本、合成（F11）— 未盘问，不计入任何完成度 · 风险 high：音乐会话 34 条需求，主打能力之一
- 媒体会话底座：会话 CRUD、素材上传、作业控制与轮询（F12）— 未盘问，不计入任何完成度 · 风险 high：媒体会话底座 60 条需求，承载全部媒体会话的 CRUD 与作业控制
- 仲裁与额度：台面状态、内存快照、对话额度、重活许可（F14）— 未盘问，不计入任何完成度 · 风险 high：仲裁与额度决定重活能否并存、内存是否被压爆；坏了表现为卡死或崩溃
- [横切] 进程生命周期与孤儿收割：退出、看门狗、端口清理、子进程（F19）— 未盘问，不计入任何完成度 · 风险 high：孤儿进程会占内存与端口，同 bundle 实例互相收割
- [横切] 并发与互斥：两个重活、两个页面/标签同时操作、作业中切会话（F21）— 未盘问，不计入任何完成度 · 风险 high：两个重活并发可能压爆内存；多标签同时操作可能写坏会话
- 资源页：模型目录、校验、下载/续传/取消、删除、磁盘（F3）— 未盘问，不计入任何完成度 · 风险 medium：模型校验/下载/删除影响能否拿到模型，删除误伤破坏面大；本 run 禁真实下载
- 指令（skill）：列表、扫描、从 GitHub 安装（F6）— 未盘问，不计入任何完成度 · 风险 medium：指令从 GitHub 安装涉及外部代码落盘，17 条需求
- 配乐（给视频配一首歌）（F10）— 未盘问，不计入任何完成度 · 风险 medium：配乐 20 条需求，依赖视频与音乐两条链
- 素材库与预览弹层、成品与历史、访达显示（F13）— 未盘问，不计入任何完成度 · 风险 medium：素材库 39 条需求；删除成品涉及数据丢失
- 对外 API 网关（OpenAI/Anthropic 兼容、局域网、设置抽屉开关）（F15）— 未盘问，不计入任何完成度 · 风险 medium：对外网关暴露本地端口给其他程序，涉及安全边界
- Web 骨架：静态资源、2 秒 tick、状态栏、标签路由、错误信封、离线（F16）— 未盘问，不计入任何完成度 · 风险 medium：Web 骨架是全部页面的底座；标签路由与状态栏错乱影响全局
- 打包与安装（构建脚本、内嵌运行时、签名）——需求有、census 无（类别未枚举：scripts/ 被普查官按约束排除）（F17）— 未盘问，不计入任何完成度 · 风险 medium：打包/签名坏了用户拿不到可运行的 app；需求有、census 无
- [横切] 数据生命周期：删除会话/模型/成品后各处引用（文件已不在、引用的图或歌已不在）（F20）— 未盘问，不计入任何完成度 · 风险 medium：删除后残留引用导致界面报错或磁盘泄漏
- 提示词助手（优化/看手气/恢复原文）（F7）— 未盘问，不计入任何完成度 · 风险 low：提示词助手是辅助功能，坏了可手写
- 测试态组合根（e2e 确定性服务）——需求有、census 无（普查官列为 mock_layers 而非操作面）（F18）— 未盘问，不计入任何完成度 · 风险 low：测试态组合根只影响 e2e 确定性，不面向用户
- 旅程候选 新用户 · 本机已有模型目录、app 无配置 · 选好模型目录进入台面并看到哪些模型能跑（C1）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 重度用户 · 一个已有很长历史的会话 · 继续聊下去，模型仍记得早期意图（C3）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 进阶用户 · 有一个 GitHub 上的 skill 地址 · 装好并在聊天里用它得到受其影响的回答（C12）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 创作者 · 新会话 · 文生图→在这张基础上改→换个构图，三张都留在同一会话（C4）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 创作者 · 图片会话里已有满意的图 · 用它当首帧生成视频（C6）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 创作者 · 已有一段视频 · 接着往下生两段，挑几段合成一个成片（C7）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 创作者 · 有一段视频和音乐会话里的一首歌 · 得到带这首歌的视频（C8）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 创作者 · 新会话 · 风格+歌词生成一首，接着写下一段，合成成一首（C9）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 回头客 · 素材库里已有各类成品 · 找到一件旧视频、预览、回填参数并再生成一版（C10）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 不会写提示词的用户 · 只想到一句话 · 用助手优化后生成视频（C16）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 用户 · 某个功能提示模型不全 · 在资源页弄清缺什么、开始补下并能取消（C11）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 开发者 · 想让 OpenAI 客户端用本机模型 · 在设置开启对外 API 并完成一次对话（C13）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 用户 · 聊天模型已加载 · 去生成视频，生成完回聊天还能接着聊（C14）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）
- 旅程候选 用户 · 后台服务意外退出 · 窗口告诉他发生了什么并能恢复继续用（C15）— 用户未选，不计入任何完成度 · 用户原话：未勾选（2026-10-14 旅程多选四问中只选了 J2 聊天多轮、J5 竖屏文生视频）

## 未拉的线（已发现泄漏点、未实测——续盘从这里接手）
- [F9] 视频结果区里单张卡片比结果区高：1440x900 下滚到顶时卡片底部（播放控制条下沿与操作按钮）被下方表单挡住，滚到底时卡片标题被截 — 泄漏点：J5 第 8 步 incidental：'a single result card is taller than the result area… bottom cut off by the form below… card title is cut off'
- [F9] 视频生成完成后结果区自动停在下部，卡片标题与画面顶端被结果区上缘硬边截掉，用户要手动上滚才看见标题——是否所有完成/新增卡片都这样？ — 泄漏点：J5 第 7 步 incidental：'card title… and the top of the video frame were cut off by the hard edge at the top of the result area'
- [F9] 已有会话里「挑几段合成…」按钮压在结果区上缘，卡片顶部被截、标题不可见 — 泄漏点：J5 第 1 步 incidental
- [F9] 竖屏 288×512 视频在 1038×450 的播放框里两侧大面积黑边——播放框是否随画幅调整？ — 泄漏点：J5 第 8 步 incidental
- [F9] 播放中 currentTime=1.14s 而控制条仍显示 0:00 / 0:02——播放器时间显示是否刷新？ — 泄漏点：J5 第 9 步 incidental
- [F9] 重载后当前会话最后一次是竖屏，方向控件却回到横屏、提示词清空——回到会话时画幅/输入是否应恢复？ — 泄漏点：J5 第 10 步 incidental
- [F16] 新开页面在 #tab=chat，未操作就跳到 #tab=image——初始标签由什么决定？ — 泄漏点：J5 第 0 步 incidental
- [F16] 每次页面加载控制台 favicon.ico 404 — 泄漏点：J5 incidental；visual-style 实测官 console 也见 404
- [F4] 聊天回答里原样显示 '$\rightarrow$' 字符串，markdown 表格渲染成竖线分隔的纯文本——回答是否渲染 markdown/LaTeX？ — 泄漏点：visual-style 实测官 incidental（vs-01, vs-19）
- [F10] 素材选择对话框里歌曲播放器显示 0:00 / 0:00，而音乐页同一首显示 0:30——对话框里能否试听？ — 泄漏点：visual-style 实测官 incidental（vs-12）
- [F9] 视频页折叠着的「日志」details 仍是可滚动容器（pre 645/200）——折叠时是否占位/产生滚动？ — 泄漏点：visual-style 实测官 incidental
- [F9] 900×600 下视频提示词框随长内容长到 240px 后盖住「生成方式/横屏竖屏方形」行（radios y=288-314 在提示词框顶 y=290 之下）——长提示词时还能改画幅吗？ — 泄漏点：J5-squeezed 第 4 步 observed 与 incidental
- [F9] 900×600 长提示词时主列右侧两条竖向滚动条上下叠放（结果区一条、输入区 .image-composer 一条） — 泄漏点：J5-squeezed 第 4 步 incidental：'two vertical scrollbars are stacked on the right of the main column'
- [F9] 900×600 结果区只有 94px，300px 高的视频画面在任何滚动位置都无法完整可见 — 泄漏点：J5-squeezed 第 8 步 observed
- [F9] 生成中 94px 结果区只露出「取消」与「日志」，进度条与「已用 N 秒」被滚出可见区——窄窗生成中用户看得到进度吗？ — 泄漏点：J5-squeezed 第 6 步 incidental
- [F9] 提交后提示词框保持 240px 与全文，生成中与完成后占据下半屏大部分——提交后输入区是否应收起？ — 泄漏点：J5-squeezed 第 5 步 incidental
- [F9] .video-materials 高 0px 而 scrollHeight 39——素材区被压成 0 高？ — 泄漏点：J5-squeezed 第 4 步 incidental
- [F9] 进入视频标签自动打开最近会话时结果区停在卡片底部，视频画面被上缘截掉（重载后亦然） — 泄漏点：J5-squeezed 第 1、10 步 incidental
- [F5] 被停止那轮回答：重启前标「已停止」，重启后同一条变成「已思考 10 秒」——停止标识是否持久化？ — 泄漏点：J2 第 7/15 步 incidental 与 q03-16-diff-before-after.txt
- [F14] 对话额度读数 262144 → 39919 → 168715 字随轮次大幅跳动——额度口径是否稳定？ — 泄漏点：J2 第 4、8 步 incidental
- [F4] 重启后模型不自动恢复，下拉默认 GLM 而非会话上次所用 SuperQwen；未加载时发送无事前提示、直接 503 已中断 — 泄漏点：J2 第 15、17 步 incidental
- [F5] 未加载模型时失败回答标题为通用「模型」，会话列表模型标签随下拉变为 glm 而非实际回答的模型 — 泄漏点：J2 第 17 步 incidental
- [F1] app 重开后窗口尺寸 1200x832，未恢复退出前的 1512x883——窗口尺寸/位置是否记忆？ — 泄漏点：J2 第 13 步 incidental
- [F5] 流式进行中会话列表标题仍为「新会话」，回答结束后才改为首句标题 — 泄漏点：J2 第 3 步 incidental
- [F4] 打开聊天页自动打开最近会话而非空视图 — 泄漏点：J2 第 0 步 incidental
- [F19] 媒体作业结束后 mlx_lm 服务进程（8767）仍在跑，而横幅读「内存里：无」——媒体作业后聊天服务是否成了孤儿进程、占着内存？ — 泄漏点：q03 J2 重派 incidental：起点时 mlx_lm server pid 25339 在 8767 监听，横幅「内存里：无」，模型行「媒体任务已结束，可重新加载」
- [F14] 视频标签提示词框下出现「连接 mlx-lm 失败: Remote end closed connection without response」——视频页为何连 mlx-lm、何时出现？ — 泄漏点：q03 J2 重派 incidental 第 10 步（被删除的 app 窗口截图里看到）
- [F4] 被停止那轮下的「重试」按钮在后续轮次发送并回答后仍显示——旧轮次重试是否该保留，点了重试什么？ — 泄漏点：q03 J2 重派 第 9 步
- [F16] 聊天页每个快照都有游离文本节点「宽 × 高（32 的倍数）」在 main 之外——媒体页的提示漏到聊天页？ — 泄漏点：q03 J2 重派 incidental
- [F22] 聊天 1280×800：消息列表滚到模型选择行下方（行下露出被截的 ---），消息区右下另有一条较短的第二滚动条——聊天页是否有嵌套滚动区叠放？ — 泄漏点：q03 J2 重派 第 9 步截图 q03-05-round3-done.png
- [F22] 900×600 停止生成后「已停止生成」一行落在消息滚动区下缘之外（y=484 > 482），要手动滚动才看到——停止后是否滚到底？ — 泄漏点：q04 J2-squeezed 第 8 步
- [F5] app 窗口重开后会话停在第 2 轮回答开头而非底部，浏览器重载同会话在底部——重开时消息列表滚动位置由什么决定？ — 泄漏点：q04 J2-squeezed 第 14 步
- [F22] 900×600 app 窗口里滚动区顶部那条回答的模型标签被区域上缘截掉，紧贴「未加载/指令」行下——消息区顶部是否有遮挡？ — 泄漏点：q04 J2-squeezed 第 14 步
- [F22] 900×600 输入框贴入 60 行消息后只露约 2 行并出内部滚动条——长消息发送前能否审阅？ — 泄漏点：q04 J2-squeezed 第 3/6/9/16 步
- [F1] app 退出前调成 900×600，重开回到 1200×832——窗口尺寸不记忆（与 J2 重派观察一致，第二次出现） — 泄漏点：q04 J2-squeezed 第 12 步
- [F4] 缺 1 个权重分片（7 片少 1）的聊天模型点「加载」后 /api/llm/status 报 loaded、界面显示「已加载」，mlx-lm 日志 ValueError Missing 7 parameters，发消息卡在「思考中…」3 分钟无回答无报错——加载失败能否被察觉？ — 泄漏点：v05-chat 采集 incidental：临时根里 glm 克隆删了 model-00007-of-00007（为 partial-model 状态而造）
- [F4] 加载模型后空会话提示仍是「选好模型、点「加载」，然后在下面输入第一句」——提示是否随加载状态变？ — 泄漏点：v05-chat 采集 empty-session incidental
- [F5] 会话列表卡片标题显示首条消息截断「用三句话介绍一下…」而存储标题是「新会话」——列表标题与存储标题不一致？ — 泄漏点：v05-chat 采集 incidental
- [F22] resize 缩到最小后消息区 scrollTop 停在 1020（底部 3047），900×600 下看到的是旧代码块而非最新消息——缩窗后是否失去「贴底跟随」？ — 泄漏点：v05-chat resize-shrink-to-min 观察
- [F4] 回答里的 3 项有序列表每项序号都渲染成「1.」——markdown 有序列表编号是否被重置？ — 泄漏点：v05-chat 第三轮采集 incidental（conversation 截图）
- [F22] 会话卡片改名/删除按钮获键盘焦点时是 WebKit 默认 auto 5px 蓝圈，而卡片本身是统一的 2px 强调色圈——卡片内按钮焦点样式是否统一？ — 泄漏点：v05-chat 第三轮采集 incidental（keyboard-focus Tab 走查）
- [F22] 选中会话卡后卡片保留 DOM 焦点，悬停另一张卡时两张卡同时露出改名/删除——悬停与焦点是否会叠出两组操作？ — 泄漏点：v05-chat 第三轮采集 incidental（hover 首拍被弃）
- [F9] 展开的视频尝试在播放前是纯黑方块加播放图标（readyState 1、无封面帧）——结果卡片能否显示首帧/封面？ — 泄漏点：v06-video 采集 incidental（with-result / overflow-media-timeline）
- [F12] 同一分钟内新建的多个会话在列表里不按创建顺序排列（聊天与视频都见）——同时间戳的会话排序依据是什么？ — 泄漏点：v05-chat 与 v06-video 采集 incidental（overflow-sessions-list）
- [F16] 视频页空闲时提示区 innerText 含隐藏的「回到该会话」按钮文字——隐藏控件是否被读屏读出？ — 泄漏点：v06-video 采集 incidental（empty）
- [F16] 资源页与素材库是整个文档滚动，状态条与标签栏随内容滚出视口——窗口三层结构里顶层是否应固定？ — 泄漏点：v08 Claude reviewer C-5（low）
- [F22] WKWebView takeSnapshot 截图里看不到原生滚动条滑块，滚动条颜色规则无法从探针截图核对——验收需窗口级截图 — 泄漏点：v08 两位 Claude reviewer 证据不足说明
- [F6] 从 GitHub 安装指令（skill）是否总是失败？应用拼 codeload …/tar/refs/heads/<branch> 返回 404，同仓库 …/tar.gz/refs/heads/main 返回 200（desk/skills/service.py:17） — 泄漏点：v09-dialogs 采集 could_not ×3 与 incidental：预览公开仓库得「取不下来：取不到仓库内容：HTTP Error 404」
- [F13] 素材库预览弹层在 900×600 下信息列（标题、元数据、回填参数/在访达中显示/关闭）排到弹层可视区下方被 overflow:hidden 吞掉——窄窗下能否操作预览？ — 泄漏点：v09-dialogs 采集读回：grid 40px 698px 40px，.lib-preview-info y=561 h=207，弹层底 576
- [F12] 素材选择对话框的会话列表与 48 张缩略图网格超出对话框下沿且无内部滚动，「取消」按钮画在缩略图上——会话/尝试多时还能选吗？ — 泄漏点：v09-dialogs 采集 incidental（media-picker overflow，scrollHeight==clientHeight）
- [F6] 安装指令对话框打开后网址输入框未获焦点，且约 200px 宽、占位文字被截成「https://github.com/owner/re」——输入框宽度与焦点？ — 泄漏点：v09-dialogs 采集 skill-install input
- [F2] 设置抽屉「使用此目录」失败时显示英文原始服务端错误「models root not writable: …」，且把路径重复两遍——错误是否本地化、可读？ — 泄漏点：v10-settings 采集 incidental（overflow）
- [F15] 全新配置（无 gateway 键）首次打开即对外接口开启、监听 0.0.0.0:8770 无鉴权并显示本机局域网地址——默认开启是否为有意设计？ — 泄漏点：v10-settings 采集 incidental；desk/foundation/config.py:59 默认 enabled True host 0.0.0.0

## 缺陷模式（同类位点清点——未查位点不进任何完成度）

### P1 原生表单/进度控件只设 accent-color、未用伪元素自绘，渲染出主题令牌之外的颜色 — 共 13 位点：实证 4，未查 9
- **缺口** <progress class=attempt-progress>（视频卡） app.css:244 — 视觉验收 v06-video A · gap
- **缺口** <progress class=attempt-progress>（图片卡、音乐卡） app.css:244 — 视觉验收 v07-image-music A · gap
- **缺口** <progress class=res-progress>（资源下载） app.css:125 — 视觉验收 v08-resources-library B · gap
- **缺口** <input type=range class=lib-thumb-size>（素材库） app.css:364 — 视觉验收 v08-resources-library C · gap
- **未查** <input type=checkbox data-settings-enabled> app.css:169（[F22] 同类嫌疑，未实证）
- **未查** <input type=checkbox data-video-audio> app.css:317（[F22] 同类嫌疑，未实证）
- **未查** <input type=checkbox class=attempt-pick>（视频/音乐卡） app.css:278（[F22] 同类嫌疑，未实证）
- **未查** <input type=checkbox data-skill-attachment> chat.js:222（[F22] 同类嫌疑，未实证）
- **未查** <input type=radio name=fr-mode> index.html:147（[F22] 同类嫌疑，未实证）
- **未查** <select> 模型/生成方式/画幅/时长 app.css:8-9（[F22] 同类嫌疑，未实证）
- **未查** <audio>/<video> 原生控件 app.css:142（[F22] 同类嫌疑，未实证）
- **未查** <input type=file>×4 index.html（[F22] 同类嫌疑，未实证）
- **未查** macos/ShellStatus.swift:103 内嵌页 pre 滚动条（[F22] 同类嫌疑，未实证）

### P2 同列上下排布的结果区与随内容长高的输入区缺高度分配约束：输入区不封顶或只部分封顶、结果区无下限、单张媒体 max-height 不随结果区可视高度联动 — 共 5 位点：实证 3，未查 2
- **缺口** 视频页 .image-composer max-height:50vh、.attempt-video max-height:50vh（app.css:294/297） — 视觉验收 v06-video A · gap
- **缺口** 图片页 .image-composer 不封顶、fitExpanded 下限 192px（image.js:15/61） — 视觉验收 v07-image-music A · gap
- **缺口** 音乐页 .image-composer 不封顶、.music-lyrics max-height:50vh（app.css:273） — 视觉验收 v07-image-music B · gap
- **未查** 聊天页 .composer 不封顶（app.css:83）（[F22] 同类嫌疑，未实证）
- **未查** 媒体页共享 flex:none 页头/工具条（app.css:199/285）（[F22] 同类嫌疑，未实证）

### P3 可纵向滚动、承载固定宽度子项的容器未为 8px 经典滚动条预留空间，滚动条出现时子项被裁或挤出 — 共 7 位点：实证 1，未查 6
- **缺口** .sessions 会话列表（四页共用，ul min-width:240px） app.css:339/348 — 视觉验收 v05-chat A · gap
- **未查** .lib-preview-info 预览信息列（固定 300px） app.css:435（[F22] 同类嫌疑，未实证）
- **未查** #pane-settings 设置抽屉 app.css:165（[F22] 同类嫌疑，未实证）
- **未查** .skill-panel-box 技能面板 app.css:74（[F22] 同类嫌疑，未实证）
- **未查** .media-picker-sessions / -grid / -list app.css:322/325/330（[F22] 同类嫌疑，未实证）
- **未查** .video-materials app.css:298（[F22] 同类嫌疑，未实证）
- **未查** .messages / .image-timeline（相对宽度子项） app.css:54/204（[F22] 同类嫌疑，未实证）

## 视觉基线与矩阵覆盖

基线：confirmed · visual/visual-baseline.json · visual/interaction-baseline.json
审查模式：dual；文件校验不代替实际看图。
普查官原件：visual/census.json（摘要绑定）
done: 33 · gap: 168 · drift: 0 · unprovable: 99 · not_examined: 0 · not_applicable: 0 · abstracted: 210
独立性假设存疑（该轴的用例出了缺口，被它抽象掉的用例需重展开）：device ← V-1307c7a275d90b12ff0f50b5b2625465c6c9f4244f0df0b64f6ebf1ef484bc50, V-e60179fd890e9d199af6610b10cb88d0e60cb02f23e4495fc46ce751a64f7c45, V-43a1abb2f17028c7df1a7073dcfa33599febdf755c25737d33dcfb704d18cb7a, V-5dbe71c5dcb3e4c3840c0748d5fa460ade759473d2bf8e33e03d6c051ca626af, V-51ab810b42591fc7d2fc25a089363093d93bf28aff319d564f0d23a65fab7822, V-349fda354da23e474dee45e4daba2e62b6bd4fcade0d755553cc95d89946805d, V-7bfc7dcc9d244988a29c18fe53867e48f8dd9f6afe7613230e6202755b12ec38, V-48231c0590e4a7e5885b009960009355aa7d08842ea35d2522cde9d2914a9ab5, V-f85d14f486ac0f7450537dbb93707e8fb86a7cd8219c587826f3ca3090fef03e, V-ceb720d5f3dd7c1b87866f0f472ea8f44f18dbe7aa9a6b8263a7e7cfada9f62c, V-bbfb8000a0579aede67732e4a3d676436e44947566cf367a2e48af399bbbd3c3, V-f9abeb1a42917bdd581e54bcbd569d1c98ae9962a666a8d19ccbf6da8f56a949, V-fe7a0eb403a953ead3e06fe51c3dec6a3af5eebee23bdffa26288b75bc47fcd1, V-1b6f0c705f075131a3f256d04b722f31914fbb3d73fb7d3d6031b5c64b9b7e78, V-ec949d0e0f2c62324fc6289b7e275b8d3a60f5cb120b4a57b1d3ea7d56a31422, V-2fab7ca0618460bde4f8899efda82ebf3d5582761933cd99fe3232e87476ca09, V-c5111b01aae1552fae88c55a6b2a98cd276c6f8c9ec6816c454d68f20f965d4a, V-11d28bbef227d2b41d7b7551753c50292177dad78725c7de876e58b60946d4e9, V-b0bda429e0e9cb5d777f904bb6c913b12614cda890542d1434e26d1528acd3f7, V-965ec64c92db505773eb519dab6cee95b768497fb205af07d7b47028ddde072b, V-5681b04728e870448bde6ebe9c08385a2c72a1cf426b10444ae21921b3ba1a43, V-4a791f143dc7a0e8d8533af2b68599d679e3be892093322e86b8399971e8add7, V-a4e39d8994572845e53d31c6f057745ba699517244aa81f5f6c3b22dd0f0a038, V-e69345a354ba8cee9a0c9f13be163326d4f7f36bf96c02b4107b7e68d5dc197f, V-06279e8f79e318028393d699200967263459e5d5eeff86331a8e36499be0684d, V-a8be757120f1d485aac70cd2fccb7975fc35ee3126a6b22ff4f5458827463eb9, V-eb20adb7c56c9414aa1ba2598159d36ac912464823c9340f7b0b4dc3092b074c, V-379d29c298de16faf485a0cd81486bc178ad612d010462f1e96c55213609b5b4, V-95137582f6414162cd8d4c26dba940eb2d4515d25cd5a2ab1e849e323f902b76, V-6dd42cce21c75d70f3c68c909ceeba62fbc3db6f54e174dff6097a2db4380aab, V-7411f06ee163b87f730773987779874c473060f19d825d1a02ac12db17ce59ee, V-3e0f1fcfd8eb71db0882a09669a447152d0fdaa67bfc5d0bce520dddee71747f, V-e6a21917456977def09c8d1b4606edd98162c49cce089d4020bbfa0484e82288, V-72f93e3d06acfeabf344201e26cfcdcbff7622445b223804450429027720888f, V-103ae7b14ec790497be8e81733bf9960fb979f9c4c2b0188ca945ab2089d472e, V-a73036048f7f5fde4241ee0e963d3fa89f3435110469b5a55fd56c43333ac2f9, V-fb3d1d0b8e029cde8d9a73fc9c7bad25b28b2793b86d6360f26d6054556a8848, V-ca5719bea960e18eccdb1e595443798cba72ba6c5b90787bfbabfd4a01d07ccc, V-7e4401dc42f3a6ad25f99f437bf50422bfbc5e7a75172e172be02ae559c0c161, V-4cb7d7f98215c2dd0ab99a8c399ab06f9e546acd50e999a05f496eaaaf980ca0, V-e53e37fcd51cf8068f7b77fd89ac6ea9088ae4c0ce37842c38254577a018e8c1, V-d236d76ecd4ae1272092b7f49959d6dadb80ad15738ddcda21aecd5338fdc4d5, V-0571f85a9550efa938b35054cf17317009a07d52e289f6bee71ff4c8105989aa, V-0f3ad3bffff4072fadfccc18cf192bda7bf99eb139135a0886487a154f863f14, V-858c92ddc13e562999171779518176649e9314902c95525d5d95dce68f531feb, V-57015d546ae455f7126d995215deefd93d02f757c7c48ab1369e7f586bbbdd37, V-6ba7073902dad5786662ec5f1b5f6c5a117c1f489c10a356c316091a2865306b, V-d9602a13d75f70537f3a3b3b35cb71863ae63055846f9db7cda6bd22da9c85c2, V-53d09122738775b4156acef10a195d64c5730641258e150dcbd92b31890d4455, V-b6011101050f67c6fdf593c297e54f0cfcf00d34e81637e951f0470d32a043e8, V-06bda392e21a4c13192467ca3b742407c6c3821a88ef408509a7a05eac13124a, V-603ec5876f7c0cc5b4fa265285db640e0c8826d73ca89a1b9f9102aafbb3be67, V-e474dcc5d79c468b6acc79a1fe4188c06118392732fd63fd91d286aacba83566, V-7ee54c7aa153ff7882c152c427f73ccf71931173ae016476633e0adca522a9b6, V-dea045755c942e50cdb2e0748ee978deedec56e0ffe5199761827c7daba670d2, V-98ee41790ca78c63eb9864d09520187f53b4246705206ec52b588a638ff662b2, V-1176a570e571e3f8afc9dabd359f4948fe954a1c3fbc669cd5d9dd1c89c2bba1, V-7974bbb3e965b7528c89e673b9526cda03363571b608afcac9f748e2dded125e, V-8dd65dbd5fee14c669c723f8414063215eb2206b2fb774d7e5e6da966d559d49, V-d3da19665b4612d0294b06e9258b9f9b16fcdc1e386c75de6e3398bec953daef, V-5e2a2db45838cf6bd3d51f8fed85ebb910e65f3da6cde6829c0646464fccefbf, V-3119910b1662d8b48a3a1a8da4d3bf6b06831c865a6049dcddfeff070f188aaf, V-40e5ae43ea3272004ec64636a60c53f002e00454d5ad1c9c75b4fd67c0a3e7db, V-a6f0c3ec833362d4eff01121889aa018f398393006c3fe8755925c7d9d0da43a, V-6d05461bf712189847c9ec0f1f4992fc10b6ed5c492e2779583f9670a04c4665, V-f23e6a004809b8d515f2bcc73d474796f0a1607190c80a9c244757d354d0b2c9, V-924627442d393a77e22d9614296ad54babbc927b5824e12938512822b567c8e4, V-f25c056f92947609f717a212d5b13af1d3f60ab58649fc56a0306400d77210c3, V-98f0b95e71614572cd1d6c2ac094837f7718b68e7a8f6fc3999223b32391f2c2, V-6f94dd9ee045fdb0b5ab2ba88e5ae48618df335e2e73678fee5f679e733b00f0, V-05656fd68b8d0c249e64e692be188a31395ead3e9a24d1e4a1b2827c62165eae, V-0a83d0d869814b73f440e4e4282946988f4ea92cd7dc9da91fa2b7c45a00c38f, V-6260c47c6c75df6ce3100b9754d36ca09e0e5473c3cc0c4df7dda72f1a0d2de0, V-0928fd8cdf9efb94f76bd2cac066b1b07424de439ef13f4e7fdd23b8823aec72, V-e8ebb0cea965d4e0d2563645898d629f6929637436de5060a98e398013c33dcc, V-83a3850f561193dabb1528bac35e222780b48b7d80007c51f8583af3f55c5188, V-23d0b5c591ce8e13299a5451b657de8fb9b8fe872bc643b47a34632635058219, V-2d0ce2d0f1ee4738deb3257fcb0f0f49e59df28864b4f638ad5f5f0706b2412d, V-447b6568dfc361becf51845b2b9b987ab8ae98511dd84facd3a9f9696c232525, V-92979f9b5c22d0d2acd7cba59f382b3eb2492a78313ac3de44feffff14106f46, V-08d90236f256868044693aecefd2b13db4944ee3ae650cde0ef1c7dfd53d5a8b, V-f269d304e732de549bfb18b9e8fe9c188571e63f7cf6ab299fa45ccf2fbf80c3, V-f47ae3237e62a0149afce4e6754a70ab3d2f1326e74fed06391b1565ab61efd5, V-f5b5cabb586f6ee7aad9b5eabe0785b30d47ae197fe3e0fb56a9b4cdbeaa1362, V-e6fb7aaba16203c50bc6342f98ab179735cc6c524d13c59d0ceccd02e5c14933, V-72d897508af9ca60d496997c5bf47c18161b854abc7265bcb57f06bb80ba8a5d, V-440ab7ee7b62ddd3290aeb7d6d87d80c25b2b8bcef1e1cdd52676ddd60169f99, V-23a3bef44381d4fc0f6958901dbb9ba8c39f786504a2d1b66f45e66c95487d77, V-bc58a3a882dd3d214c9d5a59d67e59529331e2d33c96d71d2e9d425e3ff08b3e, V-1da68f840f0126b5d3a2df14d8bdece367325a06aac1afeee8e5f7fd3c97c54c, V-972aa32ca10a52065356dbfcbe753c943b1d56a3d39553f34feaf4a57c1087f2, V-46419464f009be0afa0859a0be1685cb10e20402fc4ccd1e5f5c97c74f4434b1, V-ecb48e88769c76f64b850d878337ccf9a515733da55eb0fab315d637beab4a01, V-276f737eed7b13f883f2b5ed87fddd78933333ccc09a7ede2eb322923f25e028, V-a9ff94304983ef13cab813035826e0a3efa6a9c0b825c0c29394185b8d8fe143, V-7d302def91a51daafc015dcaf9d34d0bbab5bcc116866a73e6de7c10d8f1f10b, V-695b77c08cf520dc870308a15aad99ef32c0bd0e1bca7efc4ed17991e77e2f22, V-c7ccae4221a2df337aa85342d10786187bef5c6c9409691b7e0326f4d8a2ba4a, V-d6daeb3a0680cdf8f673f787638bb2074dc8fece3e9b4be6f31d86ec4a773275, V-a4f090e50af024bda721a48dc507e05effa9fa022d9f0ac19a170f6d20078095, V-e97cdd6f8e5a30f109609b58bf7e9388ba87f892a3439e01d6d9f2ef9d8e93d4, V-27fc76fd2f8c599d8d3e9dae4cb51a8a55784397fba24ad6779a79567eae8d50, V-91313b5085fdd715da616d3af39b0ff3958a25145ce4b57e0499b632e22c16ac, V-2db547594784c563799547d4d8a842f89e975cc034d38585ace84ce46f5781a0, V-f26bb814c7a229d16dac977872df837dc7483452476792f90f28f447a10f837f, V-edcdd8bd544a4b839cd83eea87a8535b1432df08402aad27d123613e899cebd0, V-23d788134a478c63888ed1b1da491cb90ca46327b898fcd86c7feb0d157e990a, V-cb78edb40ca2118250bf042c974aa1ae24ffc93691dc57d0c7f6f1ba8248c96c, V-90300235498b9eaa37f755bc8411cef5a6ba84d9f5c65f68cf79b55d35f6b6c9, V-56a87a2ba00953a275b3030f213828d2eb183b7775e19071f8f93e629d2cbefa, V-e76c4ae00f8cf9def2a63c860843e44e8ddcba82a2115c50aeeb69f633d022bf, V-bddb6cc9a462cdeb05e0610f671e92c458e09777c4709af218f0c7271e5304f0, V-da17612f46f0c99c86dfeaac536cae27cf292c778ef0203b3d2e028a8bd75d33, V-6e755ebde140824c9b5ebccfdfed39f064fecfb4494cbe0699c33b99d5a84317, V-bd47b12ef08b60885771eeda88ee8a06387a1585b5ce0a0166af016b0abaf2a3

未验收 dynamic_type 值（用户确认放弃，不进任何计数）：WKWebView 没有开 allowsMagnification/pageZoom；在普通浏览器里可用浏览器缩放 — 只验 100%（推荐）

- V-1307c7a275d90b12ff0f50b5b2625465c6c9f4244f0df0b64f6ebf1ef484bc50 chat — gap · conversation / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-e60179fd890e9d199af6610b10cb88d0e60cb02f23e4495fc46ce751a64f7c45 chat — gap · conversation / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-43a1abb2f17028c7df1a7073dcfa33599febdf755c25737d33dcfb704d18cb7a chat — gap · conversation / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-5dbe71c5dcb3e4c3840c0748d5fa460ade759473d2bf8e33e03d6c051ca626af chat — gap · conversation / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-4ec0f44083b3a8320240dbe58d22dedc47db2e8313bcba030b30e7d0b2eefa8e chat — gap · conversation / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-51ab810b42591fc7d2fc25a089363093d93bf28aff319d564f0d23a65fab7822 chat — gap · conversation / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-349fda354da23e474dee45e4daba2e62b6bd4fcade0d755553cc95d89946805d chat — gap · empty-session / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-e215149ea087050334637a88e5b42785aca2dd242e1127865037b4c8f39185b4 chat — abstracted · empty-session / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-56312354343f0a22511a28c3a8b736e64e7f93cef7dc634304d519f1021151d1 chat — abstracted · empty-session / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-02cbb50ec2557411db60c202140ecd3e80ca26559585206b1b00eb7cc7c855cb chat — abstracted · empty-session / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ce8dc671b0e04181065d6ba8651f31c43c6b1ac7200600c23085d19a02e1ccc4 chat — gap · empty-session / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-7bfc7dcc9d244988a29c18fe53867e48f8dd9f6afe7613230e6202755b12ec38 chat — gap · empty-session / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-eeba607d5a33d879877ec31a79f6fdfd1ef749b963ade3a20d0911efcb61f3e9 chat — done · streaming / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-58e9b4e34590310cb8e50ab8c11a8541cd301891339fd265578326896ca61768 chat — abstracted · streaming / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c9fa507ab71fedb8cd19e4ad5d5eac275fcc65b1fcf3a047467a9935536b2771 chat — abstracted · streaming / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2cff58825ac770060cc5424b5087684dd3efebe8ece25b32b379b8ced6f72ee6 chat — abstracted · streaming / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8f84e00f9fd8a0a7820fa19e665ce452b863daf7069673694b7308f0359d5f9c chat — done · streaming / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-678b17c5783be84fb99dcb5e85ae795d4e5c4dbf7e9a6b6e8d4be7ca6f33d4ad chat — done · streaming / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-48231c0590e4a7e5885b009960009355aa7d08842ea35d2522cde9d2914a9ab5 chat — gap · model-unloaded / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-91d0bce11586847cbf15502c6c89624fb5562179b0944da5507b5341eb864d7c chat — abstracted · model-unloaded / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-52f9d1c498fc3d77f8090173debb6d3fb151759f9de75926666d25d3d8e4836c chat — abstracted · model-unloaded / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9d6f471650c8daf1fb85291d7c8a84cc8a12bf392f2471fbef836c437a1b3935 chat — abstracted · model-unloaded / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-438f3c035a2ebf91e694569a3cc3bcc4961840b59f674ee6a1b9cdcc680f4c0a chat — gap · model-unloaded / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-f85d14f486ac0f7450537dbb93707e8fb86a7cd8219c587826f3ca3090fef03e chat — gap · model-unloaded / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-ceb720d5f3dd7c1b87866f0f472ea8f44f18dbe7aa9a6b8263a7e7cfada9f62c chat — gap · session-hover-actions / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-fdab10bcda8df8647f771cafa8d6c4d4400ec7587eda8847bdb8ad857faece91 chat — abstracted · session-hover-actions / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-15e159241ed5cf5f4df534c52428cf638decc4b9bfe62377e838e59439a3df7a chat — abstracted · session-hover-actions / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3995a24987ad1566cd04151e60f9c9f2e51206e19579f45e4ee6670084f0f53a chat — abstracted · session-hover-actions / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-954080f6914b7b30acecd9b9a75b739a05c89093039810cc9736e178ed776f7b chat — gap · session-hover-actions / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-bbfb8000a0579aede67732e4a3d676436e44947566cf367a2e48af399bbbd3c3 chat — gap · session-hover-actions / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-f9abeb1a42917bdd581e54bcbd569d1c98ae9962a666a8d19ccbf6da8f56a949 chat — gap · keyboard-focus / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-fce68f90b5c0f9f8ae008f4a5c659c499b4448728c437b11dfacbf679c020da9 chat — abstracted · keyboard-focus / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-692b1d0ad60e379f513295be4d1519993da677e2ccbf32e27f41cb064f4e85d2 chat — abstracted · keyboard-focus / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b94a7d661c9d661c9e22441daa513a6d1ce31d91ffe02570cd7f1fe001499a17 chat — abstracted · keyboard-focus / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4565f1cd96f0065f5039ed141bd42d88fa2605002b63c1d6e53d18252ed53021 chat — gap · keyboard-focus / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-fe7a0eb403a953ead3e06fe51c3dec6a3af5eebee23bdffa26288b75bc47fcd1 chat — gap · keyboard-focus / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-140c60a3d0d6c2b2ee46577eade4cf5dcb76929dff5e78aea8624dbda64fc1c2 chat — done · overflow-chat-messages / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-72ae0b9e96a6aa1da779b66aba04fff7833f05e9202856b8a5c2e89f46dbc24b chat — abstracted · overflow-chat-messages / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-582a5013e058c9345e4e90aaf7596017022c6388b3e6edcef1a6067b3f5fb921 chat — abstracted · overflow-chat-messages / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-fde33c5b81b55c65386ad377ed2488f04125d5afbea4cf60018d58a11eefc86d chat — abstracted · overflow-chat-messages / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8f6c25c4141cafb98c10f2f8fad894fcbe14d7eb4406f0c062a366e0d42278b0 chat — gap · overflow-chat-messages / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-1b6f0c705f075131a3f256d04b722f31914fbb3d73fb7d3d6031b5c64b9b7e78 chat — gap · overflow-chat-messages / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-198676dcf2d540ba40e018c87ec88f1bdf20adca85d3c06d7d5bd2f469c240dc chat — done · overflow-chat-composer / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-8ac4a697c39459170b28bc04674ce6caa70b16e69a21d28997e0f0dcb7324708 chat — abstracted · overflow-chat-composer / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d3863928a9da6685ab24e5c30bc7fbe05660e72961adf91affa37b14afb1895d chat — abstracted · overflow-chat-composer / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4f5dd001c57cee7aa878e92c5489baf080b6b050dc8a6d02f6ac526bc34b8a96 chat — abstracted · overflow-chat-composer / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4fd4f0e6214507ab00649128f38f69a6c4e446afb22956c639b21e084b7617b5 chat — done · overflow-chat-composer / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-99c72fe5282f1b137c17bdef4eb4e1f0495d99130d4a9bb94baa4a78e5afd18c chat — done · overflow-chat-composer / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-ec949d0e0f2c62324fc6289b7e275b8d3a60f5cb120b4a57b1d3ea7d56a31422 chat — gap · overflow-sessions-list / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-dbdc4a287a00366d729b633c05802d0a26128af3ccd01718f1af7f137c42ded2 chat — abstracted · overflow-sessions-list / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7f955700e379395f831adcbf5e32fc9666e9bff02fd415a68da2df4f0067196f chat — abstracted · overflow-sessions-list / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b49703221a80500f2405cbac6e799abecbdcad9b299f17d923e21da3680c91c9 chat — abstracted · overflow-sessions-list / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-eb8276cdcaf38edb7f8696bde4e4f4020a9c8500689993e96e4b4b824d10570c chat — gap · overflow-sessions-list / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-013c070e6794dac5365cec1f72c0ec5ad4a63539f868ecb0eb56181e81b383ec chat — done · overflow-sessions-list / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-2fab7ca0618460bde4f8899efda82ebf3d5582761933cd99fe3232e87476ca09 chat — gap · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-A/report.json', 'v05-chat/review-codex-A/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/A.json · 降级：无
- V-35a9f72fcd7cb917f8629730a811201a1365d299b4352a6bd277a313223879e8 chat — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0a3770a5701acfab3b5a12fe7c08684d6df91dfed75c86ac6bc83241f2f80842 chat — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f12e1e51adf3c109bcc5114b002fceccc468ead3d551ebdb1e911c075d8bc259 chat — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-324f497b14c4e44899ff1f26899ef827756215a0a813551203f31349f62ae53f chat — gap · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-B/report.json', 'v05-chat/review-codex-B/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/B.json · 降级：无
- V-c5111b01aae1552fae88c55a6b2a98cd276c6f8c9ec6816c454d68f20f965d4a chat — gap · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v05-chat/manifest.json · reviewers：['v05-chat/review-claude-C/report.json', 'v05-chat/review-codex-C/report.json'] · 模式：dual · 分歧：v05-chat/reconcile/C.json · 降级：无
- V-11d28bbef227d2b41d7b7551753c50292177dad78725c7de876e58b60946d4e9 image — gap · empty / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-c739acac8eb5cb2c1f9f30faf726d071cf2c7f916297f195b943f68e1f7a72e8 image — unprovable · empty / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-4a7f59b25bee442d82ec9e84f54d14c6f5dd3c6d4406f6d342686bae77be484a image — unprovable · empty / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/reconcile/B-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-2f410d1ecbd67988b9539e979e027d257e90c74fa6ba251f9d7487ed238c79aa image — unprovable · empty / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/reconcile/C-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-eba70fe0d81b16d63f0afcfea524326c6129991be9818f582383e8deff1ad2ae image — gap · empty / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-b0bda429e0e9cb5d777f904bb6c913b12614cda890542d1434e26d1528acd3f7 image — gap · empty / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-965ec64c92db505773eb519dab6cee95b768497fb205af07d7b47028ddde072b image — gap · with-results / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-8146cad28bae12430fd79bcdd6829be4b2e16b9983d3c56ff7db643eea12ee0d image — abstracted · with-results / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c8ad8594eac1c27e1e349d94131ff3a6db8d184f612bb9e3f7fc5c3b7ad44f83 image — abstracted · with-results / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e8cfdba9c658a7eb4192a210530c4dd5b39982b62af9a66448925034c12db8eb image — abstracted · with-results / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5e18b9fa195da25c30a782d385f1a6306e7f433758e636344f8dfa4012e9dfe5 image — gap · with-results / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-5681b04728e870448bde6ebe9c08385a2c72a1cf426b10444ae21921b3ba1a43 image — gap · with-results / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-4a791f143dc7a0e8d8533af2b68599d679e3be892093322e86b8399971e8add7 image — gap · generating / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-eaeb40ff994a1d85a11391925731dbd492e260164cb8a758cd6002a6f3264559 image — abstracted · generating / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bee1a6f7d51bcd00bf25f545277a4a731812392ba73c0925644993844b51bea7 image — abstracted · generating / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-764764cfb9d55b547fd44ef95770f3e75c517785ad278dd10528795d4da0f58c image — abstracted · generating / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b0da3a64c22fc072eea50dd52e682ee83f8f9838a46fd83c22590095eb67990f image — gap · generating / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-a4e39d8994572845e53d31c6f057745ba699517244aa81f5f6c3b22dd0f0a038 image — gap · generating / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-e69345a354ba8cee9a0c9f13be163326d4f7f36bf96c02b4107b7e68d5dc197f image — gap · overflow-media-timeline / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-b7306e2644e9b94a72cd0517df596f5edbf6451ebf5226d87c143ef5d3dc834b image — abstracted · overflow-media-timeline / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-73bf809e778e085700135161404dbd4a988df28109eac792ff401d2f371398c4 image — abstracted · overflow-media-timeline / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3a66bd0d0c05f6ccd2f72b402d50d9f1bd2997cfda81ee61928b53af3d7a9c81 image — abstracted · overflow-media-timeline / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-007a244269479cd0a5edb57d1bb5db65f72c41f35c1896b0f8c0c7e9f19f2f36 image — gap · overflow-media-timeline / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-06279e8f79e318028393d699200967263459e5d5eeff86331a8e36499be0684d image — gap · overflow-media-timeline / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-a8be757120f1d485aac70cd2fccb7975fc35ee3126a6b22ff4f5458827463eb9 image — gap · overflow-image-composer / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-ba1dca9d2c1b4cce55f5e5f87acf18447b684fd84db389d25ed3502a2b7bb749 image — abstracted · overflow-image-composer / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d34a8bc121f34a0b9afa209eda6fc4dc0eb92ad8952988f98e1a7f9010d10e18 image — abstracted · overflow-image-composer / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-02e5d2dd172013ae1c0dfc743fc3b1efd64e1a17125a821a850bc8b17b6131b2 image — abstracted · overflow-image-composer / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b0d3360390e4c163494553a95cdcb0a199240b7c5325452c4a39962c10df14a1 image — gap · overflow-image-composer / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-eb20adb7c56c9414aa1ba2598159d36ac912464823c9340f7b0b4dc3092b074c image — gap · overflow-image-composer / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-379d29c298de16faf485a0cd81486bc178ad612d010462f1e96c55213609b5b4 image — gap · overflow-sessions-list / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-644b446ee0e963db442b9ed4964adc7a14766767f12c84be022e231b4f5fee1d image — abstracted · overflow-sessions-list / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2353438d5532df81d8a22d03db89bc3e38e915dd02a6f4ec50e95b7e729458d4 image — abstracted · overflow-sessions-list / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2c92cac824c4d76d6ff8d3850b9c6bd3309f95ad1aac04b4bed95ae2acbe94be image — abstracted · overflow-sessions-list / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7bac23900852becc9df3cfbfd3e41e64ced0d86e4d76cf2391b017b99d6a9ac2 image — gap · overflow-sessions-list / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-95137582f6414162cd8d4c26dba940eb2d4515d25cd5a2ab1e849e323f902b76 image — gap · overflow-sessions-list / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-6dd42cce21c75d70f3c68c909ceeba62fbc3db6f54e174dff6097a2db4380aab image — gap · overflow-attempt-media / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-9bdf6a6ed58a40113f83d99abf41031d709db1242ae49455fe17a669546b5071 image — abstracted · overflow-attempt-media / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8a34797e015b50a03c9a2bb792f6c1004b70892f416d3f52da9ceeb9d5cf7097 image — abstracted · overflow-attempt-media / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b7daea8d187f0cc9546218e36874544bc28ef06839f74aef0f0b456837047588 image — abstracted · overflow-attempt-media / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6bdfaff9e784e668e21cce819dbd265ca14aac7bc9cc0aeb0332ced3ac12ce67 image — gap · overflow-attempt-media / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-7411f06ee163b87f730773987779874c473060f19d825d1a02ac12db17ce59ee image — gap · overflow-attempt-media / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-3e0f1fcfd8eb71db0882a09669a447152d0fdaa67bfc5d0bce520dddee71747f image — gap · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-e78c2a225321b4b3e14c8389c9d0f9f7a4913e2d29d3a9f0c7486e8a0e7717f2 image — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9ef43519d94371c28d6efa397d18444c6f6639ad254088199446dccf7bb2458b image — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c3ddc44acc880bb33d96e02e474e5b561bd8857040da63e93ea368aa3911f8e6 image — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4c354f7e48a3ba1a3e98b4ce2b48035c0fe984c68d33792343229bb61a572a1f image — gap · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-e6a21917456977def09c8d1b4606edd98162c49cce089d4020bbfa0484e82288 image — gap · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-72f93e3d06acfeabf344201e26cfcdcbff7622445b223804450429027720888f video — gap · empty / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-103ae7b14ec790497be8e81733bf9960fb979f9c4c2b0188ca945ab2089d472e video — gap · empty / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-a73036048f7f5fde4241ee0e963d3fa89f3435110469b5a55fd56c43333ac2f9 video — gap · empty / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-fb3d1d0b8e029cde8d9a73fc9c7bad25b28b2793b86d6360f26d6054556a8848 video — gap · empty / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-2ff8598b2aca2d7f7535c339bc2b7dc8bab8c9c82f2e7be12c36a70f8450c60a video — gap · empty / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-ca5719bea960e18eccdb1e595443798cba72ba6c5b90787bfbabfd4a01d07ccc video — gap · empty / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-7e4401dc42f3a6ad25f99f437bf50422bfbc5e7a75172e172be02ae559c0c161 video — gap · with-result / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-1ac9e15b98c46d455f189ddd84e06effc220efb1799ea1b7130a70827253b1c2 video — abstracted · with-result / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-345157a8aae0eac59da602e41b6682a41afef4a695487eea59574fd1299ff9ee video — abstracted · with-result / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-53409122291e0eaf87bb15184f8b8bf374d88a625fcc9d582466dcf610976545 video — abstracted · with-result / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3a55e036c9bffe90f5a27bdbef419bd9f5728ee291672989c709bd39b11d2abd video — done · with-result / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-c12d9344706ac90db499313e4e90e3179657425a910f5ed5e60c709bdbffe65f video — done · with-result / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-4cb7d7f98215c2dd0ab99a8c399ab06f9e546acd50e999a05f496eaaaf980ca0 video — gap · generating / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-15829e1c65bc2965fe848063cf97e1b3da5d5744050a5ce881b9dc7d0677989d video — abstracted · generating / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ab5edcf8532aac582c255215f023aa84f87c02c436cc871d8b087ef5a36aa555 video — abstracted · generating / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2f41018c3c7c3ae5ce5d4f99d5c2e3dfa71b2fc896aafcb667fc301c4308b0c6 video — abstracted · generating / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8f090e293dd016b1a1c08edab2ad44f74fd1684c93930a01d5db2bfd721da911 video — gap · generating / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-e53e37fcd51cf8068f7b77fd89ac6ea9088ae4c0ce37842c38254577a018e8c1 video — gap · generating / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-d236d76ecd4ae1272092b7f49959d6dadb80ad15738ddcda21aecd5338fdc4d5 video — gap · mode-image-first-frame / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-889b341c7578b635d484ae11ca0e0f7ff7e12082b487f9418ce879ae15d3c7fd video — abstracted · mode-image-first-frame / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-579416465e0851ffb495b6df20edd145a70c23fd666ea20374e98591571bb32c video — abstracted · mode-image-first-frame / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-fd43342ccd6f22ba680e33a8754e73cb9a4b2f4ccbc6c0df5871464668cc2252 video — abstracted · mode-image-first-frame / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-70c6c41b5023c36c5dad7d07ce8a63f1a51bf55fdf67b7d88785a6a2e5345e6c video — gap · mode-image-first-frame / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-0571f85a9550efa938b35054cf17317009a07d52e289f6bee71ff4c8105989aa video — gap · mode-image-first-frame / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-0f3ad3bffff4072fadfccc18cf192bda7bf99eb139135a0886487a154f863f14 video — gap · custom-size / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-d9ffb8f5ef19f108ada6e0f8f2344de0632137ee8ddf1088828978a95fe7fdf7 video — abstracted · custom-size / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f9e61151400354897ca9d8bdef4631d38a9096db9eb870da0c2f6ba7a64aeac8 video — abstracted · custom-size / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-77622293badb72066fdee44afea58f62a0a7a6b99c75a6faa435fd2fe897d4dd video — abstracted · custom-size / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8d1017af3c6d4b3c0ecd5f8f8583d65de6efcc10a155328c7757267f8574fc01 video — gap · custom-size / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-858c92ddc13e562999171779518176649e9314902c95525d5d95dce68f531feb video — gap · custom-size / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-57015d546ae455f7126d995215deefd93d02f757c7c48ab1369e7f586bbbdd37 video — gap · continue-locked / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-c867c3c6e9ae04de85a4cf132e6732c1bc32e0ef19776f7a19415551354698ca video — abstracted · continue-locked / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-aaee4aee5223685142302cde70defd820e67ad159f219e832fb688fdaa1d2a4a video — abstracted · continue-locked / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a3ed518491f060e83f095d563100a1b97d568dc22011caa37ae7f40b2179ea34 video — abstracted · continue-locked / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3a3ba792228d49275394680d98c98b89df007aabd2ae760b09ad9c3e68d578a3 video — done · continue-locked / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-33891273fd46d8cff018046a2c3096dc91dd21fb9b0fba09a2512a1f2f2fbd19 video — done · continue-locked / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-6ba7073902dad5786662ec5f1b5f6c5a117c1f489c10a356c316091a2865306b video — gap · overflow-media-timeline / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-927ef075b7597fbad7a93e28a4868d4f952705a21b3fb14f8195ea3112f793fe video — abstracted · overflow-media-timeline / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ffa1815e454d89d04d592fd685694eb050354ecca6735285ecb3834599352ce0 video — abstracted · overflow-media-timeline / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0a737abc8995ebf8ab0585fa9b988ebdb3f5774d78e62c5745dffc4e75a27207 video — abstracted · overflow-media-timeline / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-19ccf71cbff4b246c1605f7f2c5f5afcc889c423c0a7731468b447ccea35ea3a video — done · overflow-media-timeline / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-d254a251f7a0dbb0bedb8f6a2e212c08a77f57a490b1671178ea283bed9e07c5 video — done · overflow-media-timeline / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-d9602a13d75f70537f3a3b3b35cb71863ae63055846f9db7cda6bd22da9c85c2 video — gap · overflow-video-composer / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-ab49d8b1e181e3a8a3c42e41aa2ae892073546fbc1f0abcfcda61d722f841be8 video — abstracted · overflow-video-composer / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-361987a53d932e29cfca3892c231e3b7b7e1fe223f0cb33f631ddbb135171796 video — abstracted · overflow-video-composer / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e6ccbb740ff8829db4f9fcf4333498bc364f9230a3f13ce97e9695d6e0ff1b64 video — abstracted · overflow-video-composer / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9724a115682cbae4997d5f2f02c39a56e2d98c22e9810f51d44913ae51605f0f video — gap · overflow-video-composer / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-53d09122738775b4156acef10a195d64c5730641258e150dcbd92b31890d4455 video — gap · overflow-video-composer / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-b6011101050f67c6fdf593c297e54f0cfcf00d34e81637e951f0470d32a043e8 video — gap · overflow-video-materials / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-34e7f290906b50e12cec715a0001470eee526aafaa24b727f3bb1f140cfedb8b video — abstracted · overflow-video-materials / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9ddad332a2f5b9435e7f2b6d9f85fb96215e29a12a10b76b9c3a2028b882f622 video — abstracted · overflow-video-materials / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2342d8e3638502956229debfb74a84cb377a5445b6309e3065460d546280576c video — abstracted · overflow-video-materials / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6ba206047e14dd3d00939e1c17de4a27aa761a7c24e654c73f6de2deee7c82a0 video — gap · overflow-video-materials / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-06bda392e21a4c13192467ca3b742407c6c3821a88ef408509a7a05eac13124a video — gap · overflow-video-materials / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-603ec5876f7c0cc5b4fa265285db640e0c8826d73ca89a1b9f9102aafbb3be67 video — gap · overflow-video-prompt / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-1e197a62e6bd6be2641682eff89e5e60f8ad943a528c76ea3ac8d74641961c42 video — abstracted · overflow-video-prompt / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-704ebdb15be88767227f2f8197c3657652a92be6d552158d8969c409eb9158d5 video — abstracted · overflow-video-prompt / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-44e163dd8370b8305a13d7e1df8097b46fabb61395fffa0577c52694e81e9ceb video — abstracted · overflow-video-prompt / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-103cdcc6e5f4c562959ac2fdbd9fa17454094ce3dbdd2e376060d3c301e0dda6 video — gap · overflow-video-prompt / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-e474dcc5d79c468b6acc79a1fe4188c06118392732fd63fd91d286aacba83566 video — gap · overflow-video-prompt / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-fc8ddc932551f0de4f9269f38b07b10a116f29e10379ec94f0773ff0b193a0ef video — done · overflow-sessions-list / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-9c9283b38b9bad01814c7144ff47647a7c18eb98902675eb671dab3a05c731e5 video — abstracted · overflow-sessions-list / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bee647a2531a9055ad1b662d13955f7d4b4e7bb9798bca01d21c155ba9c47de3 video — abstracted · overflow-sessions-list / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0467cc4370da9fed27b56613d709b16dbfa5a01a58fc9e091465545ea74a9b29 video — abstracted · overflow-sessions-list / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-502f8cbc559bd4d04eb04ac153bfce86a91c3eef40be53bd3bcf602438dd3522 video — done · overflow-sessions-list / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-7e6d2384c8d5cb1af7565e1ac9965e10228d3826a0903c41f78e3c4ce1a423b8 video — done · overflow-sessions-list / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-7ee54c7aa153ff7882c152c427f73ccf71931173ae016476633e0adca522a9b6 video — gap · overflow-attempt-media / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-0d587e7149aa489fdf8eb29c0144bbde4ab677bb8f757ebdf618e608424f3387 video — abstracted · overflow-attempt-media / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3b740f91763b6672868fa17d1cd71105f5aa938c63709eec33646e9a6a22c555 video — abstracted · overflow-attempt-media / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e228b2d1f7006ab0b7190f0396bb15f651bf5ff34bb906cd3fbbfa0d5037cdfc video — abstracted · overflow-attempt-media / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bc22c37dd5d72698ba28a37c66d1d23b2a19aa1754a96c12f78272704ed21928 video — done · overflow-attempt-media / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-0d3b978f3cc249a6c39424376d1ba57128804e8d3d45b6a3e58565681a62da83 video — done · overflow-attempt-media / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-dea045755c942e50cdb2e0748ee978deedec56e0ffe5199761827c7daba670d2 video — gap · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-A/report.json', 'v06-video/review-codex-A/report.json'] · 模式：dual · 分歧：v06-video/reconcile/A.json · 降级：无
- V-fe384e0500e06b43280e93942362de87ea347582ada5ab8da4cc91a4255e78aa video — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-dd821b398f8b564c4f4f0b16c22757f9203d5a0ded608d1365cbe9a54d48e02b video — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-41e66510b10680b0bd8d148e2acd62e928fce5d9912aaa154a04b29cd9f6a66f video — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9839211d43648cce4fa71888f385bbc35d60822cab649a622e1070384f5ed0c2 video — done · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-B/report.json', 'v06-video/review-codex-B/report.json'] · 模式：dual · 分歧：v06-video/reconcile/B.json · 降级：无
- V-6b1f3e882b13d3d60713f47bac71bcaa84d9904d59e29b0bcd5070b3d2957b3b video — done · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v06-video/manifest.json · reviewers：['v06-video/review-claude-C/report.json', 'v06-video/review-codex-C/report.json'] · 模式：dual · 分歧：v06-video/reconcile/C.json · 降级：无
- V-98ee41790ca78c63eb9864d09520187f53b4246705206ec52b588a638ff662b2 music — gap · empty / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-3ba07fdc8b339a3f503dccd7dec5d738cc08a494c897b87814d8b4ebcd27718e music — unprovable · empty / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-b5c669897aa3091b9e69cafc363060bd56b4012486f382e8547ef1b9a854a083 music — unprovable · empty / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/reconcile/B-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-a09335ab953415231e8dc5f007233861bbb42cccc9e2f749c98c5573eba76d7d music — unprovable · empty / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/reconcile/C-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-fed204a9ba3523a51a094af911560ea72b249460f482b6a62631455c5ed80d45 music — gap · empty / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-1176a570e571e3f8afc9dabd359f4948fe954a1c3fbc669cd5d9dd1c89c2bba1 music — gap · empty / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-7974bbb3e965b7528c89e673b9526cda03363571b608afcac9f748e2dded125e music — gap · with-result / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-c367e46fb68695dfd43e471b1b71f693ef39de198ad7d40b488ebe8a8b113117 music — abstracted · with-result / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2d0c509c5bc84116daab23c7d66876475c4e49bcda850911f0fe6d711abd9099 music — abstracted · with-result / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-acdd0af3ee9506ddb2743451b68d9ed942fa284502d225b4a3d71e53262e772c music — abstracted · with-result / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cc8903502b387bb114322af9c3eccd7a2fe4d0790ede7b2fdac36f24b6f48b33 music — gap · with-result / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-8dd65dbd5fee14c669c723f8414063215eb2206b2fb774d7e5e6da966d559d49 music — gap · with-result / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-d3da19665b4612d0294b06e9258b9f9b16fcdc1e386c75de6e3398bec953daef music — gap · generating / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-005f6c00e5adbda3d1d1d8cc2f6b9a204ca0561e0fe4354652971db39dad9cbc music — abstracted · generating / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-635c23afbd22a6a73c5372a356625d4f3bf34d076a717874643ed01d7814d226 music — abstracted · generating / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-434183e9dfe4d411c8607602639e71c709b2c2b7438abcb15cb5bc19ab9fed70 music — abstracted · generating / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cea450281db89a1b8fc34690e6ea699bc4380c8cded8057f030d12b87438b63e music — gap · generating / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-5e2a2db45838cf6bd3d51f8fed85ebb910e65f3da6cde6829c0646464fccefbf music — gap · generating / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-3119910b1662d8b48a3a1a8da4d3bf6b06831c865a6049dcddfeff070f188aaf music — gap · overflow-media-timeline / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-e63746c67a2375e62f99e8d487c186ce00e5c337e366df9cb48f23034406db72 music — abstracted · overflow-media-timeline / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-fd8240613a390a107e628c316ee35c165881590805dae7a3dbd7d52c38df3237 music — abstracted · overflow-media-timeline / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1e189b2dcd0514eeee616f44be5f2633575e91829f0a1498fae08ec3ab2e2b43 music — abstracted · overflow-media-timeline / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bf636bf89fb443221a7558df0613d14d3484a6714c46228f4901b877291482e0 music — gap · overflow-media-timeline / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-40e5ae43ea3272004ec64636a60c53f002e00454d5ad1c9c75b4fd67c0a3e7db music — gap · overflow-media-timeline / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-a6f0c3ec833362d4eff01121889aa018f398393006c3fe8755925c7d9d0da43a music — gap · overflow-music-lyrics / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-9f11d985ef216e9bca5759ee7acfd16cd9109a2906758827b6007d2b1f3ea41e music — abstracted · overflow-music-lyrics / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a13e0579f1313b41b17340372be2f29afa92e9845ee057ac55a371dead0383e3 music — abstracted · overflow-music-lyrics / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-df8ed6bf063c2a2f1d9a9f873025cc017a6d8e008ec95af221e2e8ae996fb0fe music — abstracted · overflow-music-lyrics / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ba10a2a348bf3f8542c3580dee2b59b604ea36fb30307ce97a1c7a6e1b2b3f65 music — gap · overflow-music-lyrics / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-6d05461bf712189847c9ec0f1f4992fc10b6ed5c492e2779583f9670a04c4665 music — gap · overflow-music-lyrics / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-f23e6a004809b8d515f2bcc73d474796f0a1607190c80a9c244757d354d0b2c9 music — gap · overflow-image-composer / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-015a6722da558ed503f6fc5badb051bef93bb4ed34b4990e66d0d48edb276de0 music — abstracted · overflow-image-composer / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7d2dbec1474a6092bf956dae0faf80476375b04b837b82c736094de9eac695b3 music — abstracted · overflow-image-composer / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a79ecaea1693270fad377d257d5bd7350d6c1ddb0c64e12222d8fa1b48bbdf61 music — abstracted · overflow-image-composer / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e0639450d8fee848f4db4fd17f434959fb183330bba189f0990ee46810cdd25b music — gap · overflow-image-composer / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-924627442d393a77e22d9614296ad54babbc927b5824e12938512822b567c8e4 music — gap · overflow-image-composer / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-f25c056f92947609f717a212d5b13af1d3f60ab58649fc56a0306400d77210c3 music — gap · overflow-sessions-list / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-f2f65f8f0c17c33ab4ef8fd0a77df5f27d068c303910e6aac15a205daea692d5 music — abstracted · overflow-sessions-list / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-fc25e0f367abe5d373f06531638660968e891ca2ac7a1de768928ca34687c5ec music — abstracted · overflow-sessions-list / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-490cb8fcaab8261bd9762cdaa510da917f6c919692c44a6eb84cd202feb7f650 music — abstracted · overflow-sessions-list / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0ea9b2c627b51cdae90ac3837317a2048b8c6ddc05fbf784b7570644eee7dffe music — gap · overflow-sessions-list / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-98f0b95e71614572cd1d6c2ac094837f7718b68e7a8f6fc3999223b32391f2c2 music — gap · overflow-sessions-list / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-6f94dd9ee045fdb0b5ab2ba88e5ae48618df335e2e73678fee5f679e733b00f0 music — gap · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-A/report.json', 'v07-image-music/review-codex-A/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/A.json · 降级：无
- V-f1d71ddeebce72e22d9a46dbb8cfc14e3c45d6a3055e91bfad7c4671de8b6d81 music — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c3fc504d0f4bbe3931f1b29a191021453bec3db45732b001626a063f1dab81b5 music — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3143c570f8139fce85e4a7c3ae3de597a521b6d63b6f7be6be260c3259d9a779 music — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4f89c0104d3234893808777bb83cb05161a3cdb41ec6548197f1004197c133a7 music — gap · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-B/report.json', 'v07-image-music/review-codex-B/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/B.json · 降级：无
- V-05656fd68b8d0c249e64e692be188a31395ead3e9a24d1e4a1b2827c62165eae music — gap · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v07-image-music/manifest.json · reviewers：['v07-image-music/review-claude-C/report.json', 'v07-image-music/review-codex-C/report.json'] · 模式：dual · 分歧：v07-image-music/reconcile/C.json · 降级：无
- V-0a83d0d869814b73f440e4e4282946988f4ea92cd7dc9da91fa2b7c45a00c38f resources — gap · default / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-93f1b82af37373e3ce6d209dda06cc7350419ba8bdad5d5345e18d68f7e842b3 resources — unprovable · default / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-12e6c43417da110053eb7dc6b86ab39f47f9a8f24b0adb87c7ecec2aecd6357e resources — unprovable · default / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-47f967b7fa4cd3970b33439bcbbdbb01315c30741c8b036fc02f71d187fc111a resources — unprovable · default / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-e728316407364479a39f8188f01a3e1a21e01aa9f697eb93310002d7b46c2054 resources — gap · default / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-6260c47c6c75df6ce3100b9754d36ca09e0e5473c3cc0c4df7dda72f1a0d2de0 resources — gap · default / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-0928fd8cdf9efb94f76bd2cac066b1b07424de439ef13f4e7fdd23b8823aec72 resources — gap · partial-model / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-982b8e0322aacde214d1733fb1169a012dcc4aaf748c587f248900e3b80767cf resources — abstracted · partial-model / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-05e87487277fedb2b1ee9df0770a46f6fdc671b278d70257cc5160fff51f91c1 resources — abstracted · partial-model / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0ab434f0232b0eaae0743d3774adbbca38275847d82e492bce2460395799a4d6 resources — abstracted · partial-model / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cef7872276b89d958df9c8d6ac2a7a94441c925f0e7f742592c60824e5e285fe resources — gap · partial-model / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-e8ebb0cea965d4e0d2563645898d629f6929637436de5060a98e398013c33dcc resources — gap · partial-model / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-83a3850f561193dabb1528bac35e222780b48b7d80007c51f8583af3f55c5188 resources — gap · scroll-top / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-430c1d5e9f42d4361c2da8353e371f42872f3fc2d8580303b8bf44cd9e5fe0e8 resources — abstracted · scroll-top / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-640baf30f421ac663a7cf36c06771b60884cca26f061a8c89dcb0bebe90dd0a7 resources — abstracted · scroll-top / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cea6f868bb2a42f94a99d13a675ff1ee7f83d1fce4d53220ea23e28cda63df0c resources — abstracted · scroll-top / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b053a612b29a89870f47af7b9d13fab3f4130ec385a3f1f13e84022c17580191 resources — gap · scroll-top / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-23d0b5c591ce8e13299a5451b657de8fb9b8fe872bc643b47a34632635058219 resources — gap · scroll-top / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-2d0ce2d0f1ee4738deb3257fcb0f0f49e59df28864b4f638ad5f5f0706b2412d resources — gap · scroll-bottom / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-3844b91d3dc20123ed232208b5853b6ac4ec3384f11bb4c3df24d9f49f4e446e resources — abstracted · scroll-bottom / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0ff23a1ebf4dd1a9ee9e83a23c3de6ef8f2ec2a3fe691e865f418c3434c28ce5 resources — abstracted · scroll-bottom / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1270ad07f68482a85348ae9eaf51ca6b8ef8a537000730c52996811d220184af resources — abstracted · scroll-bottom / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b4d01abc7a4722cec81cfa93c31abb4a8329621184af7a552d71bedac192da07 resources — gap · scroll-bottom / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-447b6568dfc361becf51845b2b9b987ab8ae98511dd84facd3a9f9696c232525 resources — gap · scroll-bottom / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-92979f9b5c22d0d2acd7cba59f382b3eb2492a78313ac3de44feffff14106f46 resources — gap · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-2f96917be3e18ed2de005ceffb6a1dc516bf5e50fded7bd2c52d8b3d843fda26 resources — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-68975ec68b994f6713a4c74eb355cdc2299ddf944d86d8c70472840c74e3efb0 resources — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-dfc217160e3d0e21c0acfd87e3397c1d00356afea921cbbf66890829ad36e875 resources — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-088bf970837e39bb58d43ce1f4b0ddb76605b76f6cf38dd216fa7b8e388d065a resources — gap · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-08d90236f256868044693aecefd2b13db4944ee3ae650cde0ef1c7dfd53d5a8b resources — gap · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-f269d304e732de549bfb18b9e8fe9c188571e63f7cf6ab299fa45ccf2fbf80c3 library — gap · grid / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-528031b636e4dc8acfa9cda0f78dddee4fe792c6d9230e50620eefe69fbd8e49 library — unprovable · grid / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-9eacf6399768ed8b99a6a514d641d9b4cf947f7923f583c750455067c5ffcc49 library — unprovable · grid / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-aa89c8cd558c507b3992ebb1f3c4b517f1d5977a10bbc0e3c9db71dcf1700d63 library — unprovable · grid / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-2eb856a2edc4e8c7fda5d82c7376a8d3d51f53352ea22066ae053b3af2f3f321 library — gap · grid / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-f47ae3237e62a0149afce4e6754a70ab3d2f1326e74fed06391b1565ab61efd5 library — gap · grid / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-f5b5cabb586f6ee7aad9b5eabe0785b30d47ae197fe3e0fb56a9b4cdbeaa1362 library — gap · list / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-bd03c1b4b459eb31151506fd5a008e301fc75f0e557de1aa9ef68fe00fcc8f15 library — abstracted · list / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cf4fb6981c645b24d26be7bdd01a076525a57b5c4982d0d4aec96df9a6fa8f58 library — abstracted · list / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b06b79479ae5b2b2772d551ac5eabeca8066e838e26627b839f0cf1ed5275769 library — abstracted · list / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6d4f78cc2e8a29eaee311ada102982e039114f15e311fb48aee5d7437beb438e library — gap · list / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-e6fb7aaba16203c50bc6342f98ab179735cc6c524d13c59d0ceccd02e5c14933 library — gap · list / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-72d897508af9ca60d496997c5bf47c18161b854abc7265bcb57f06bb80ba8a5d library — gap · detail / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-8438c7694c7ed83476b84086308be90cb9359b5489189fd484632385215310ac library — abstracted · detail / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-04808e18c430657a96d084221611cda29d35673868923744831e4bf9d286c257 library — abstracted · detail / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-82a8299c22b2b9c0636cb171bf936c070d8173cb732ae50ed0f17ca4b1f62fd0 library — abstracted · detail / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-915d2459b4083202306048b84f364ed13ea6c7dd6ff23f9b7c6256b581b80613 library — gap · detail / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-440ab7ee7b62ddd3290aeb7d6d87d80c25b2b8bcef1e1cdd52676ddd60169f99 library — gap · detail / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-23a3bef44381d4fc0f6958901dbb9ba8c39f786504a2d1b66f45e66c95487d77 library — gap · empty / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-43ea8173da9703a93a10b7f5c7388e51f8a59a289d82998800e31d8d24866db0 library — abstracted · empty / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a9c7f2159d54b5dca37daf686d80127d8f57da4c7f02e4a837f4a80880039c58 library — abstracted · empty / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b1d7b740b34ad389be80523368d2fd485984b6f7b539e39399b3dca5cdc3cc98 library — abstracted · empty / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c833590c6a6c416824fa0571afcef65cac6b03f0fe0aa2bc0446e4dc79d4691b library — gap · empty / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-bc58a3a882dd3d214c9d5a59d67e59529331e2d33c96d71d2e9d425e3ff08b3e library — gap · empty / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-1da68f840f0126b5d3a2df14d8bdece367325a06aac1afeee8e5f7fd3c97c54c library — gap · scroll-top / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-5f1657c3ba0a44aa2e8e305cba421416271febc2e85e07147cb927cf470a9b37 library — abstracted · scroll-top / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d53144a6b548ecca327fb1876ec2c698e7ca1376dfa51d6530c61632f8a4f830 library — abstracted · scroll-top / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-59fd34833cfacac68a3ac04660dac0a27e30c2108239fe8488b493f1202fc185 library — abstracted · scroll-top / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-666d5110ec85a4407dac1816138a9c5a2dd1abec40c152c87e8819c8d3d07502 library — gap · scroll-top / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-972aa32ca10a52065356dbfcbe753c943b1d56a3d39553f34feaf4a57c1087f2 library — gap · scroll-top / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-46419464f009be0afa0859a0be1685cb10e20402fc4ccd1e5f5c97c74f4434b1 library — gap · scroll-bottom / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-bcccf1f0949f7476d369f06ecf2dfec086d1813eb9ec654b16ebc33d909aff75 library — abstracted · scroll-bottom / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4ac5419094f977edb88387bd8a187ab8d17e0dbc974eef4e8064918f933d679e library — abstracted · scroll-bottom / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e5cc6593ea23d922f32d38e1ffe52679153d26697b6cf8e7a6ac16202fbad18f library — abstracted · scroll-bottom / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-90d29db9f9210037a59c1ec751b86ce6a576506ed8fe9f91a19c5f47b0130c9c library — gap · scroll-bottom / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-ecb48e88769c76f64b850d878337ccf9a515733da55eb0fab315d637beab4a01 library — gap · scroll-bottom / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-276f737eed7b13f883f2b5ed87fddd78933333ccc09a7ede2eb322923f25e028 library — gap · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-A/report.json', 'v08-resources-library/review-codex-A/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/A.json · 降级：无
- V-9dd4cf1b7cbe54f6106de0c36d3dab8061b07372a3e05a0a8f7d41994f85446c library — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2d15ce0c2f609f17513daaaaf2018f59d71048b3a1637ecac5f5fd9a6bd3f990 library — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6980a00083c5df8166283a1de268ba41ccbdc9db7a648f134d22c90ee39d71e8 library — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ebbf2703a9e28bd3ebb90dd50dd1ab576d37555888479a21f0e16280804aa910 library — gap · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-B/report.json', 'v08-resources-library/review-codex-B/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/B.json · 降级：无
- V-a9ff94304983ef13cab813035826e0a3efa6a9c0b825c0c29394185b8d8fe143 library — gap · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v08-resources-library/manifest.json · reviewers：['v08-resources-library/review-claude-C/report.json', 'v08-resources-library/review-codex-C/report.json'] · 模式：dual · 分歧：v08-resources-library/reconcile/C.json · 降级：无
- V-6fcc8746fec5d3dbc47a5f4b84c98e73d64bf14cdc921686fb164ec178c4a306 lib-preview — unprovable · image / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-10937c224744b0eb61aad985c49af998156927c1f3e7aebe2ce3b89bba397db5 lib-preview — unprovable · image / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-0669917117e9c8551b04e329b867761c3a10a1a3fb6c897779add77d0e93afb4 lib-preview — unprovable · image / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-5bfa51725f422b23af7bbad1fb5abd19b5e88c1785a9b4ce2025843160061978 lib-preview — unprovable · image / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-c1dd70e82001d2061d767d9250399307622c79c5f774f4f01f56ed364aaf25bb lib-preview — unprovable · image / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-997fe9fee632af774ceb21dad131f9003b054f09802712b16debc9ff273a9af0 lib-preview — unprovable · image / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-56a22a1f2c46192f912dd1690184a45d4b0b890bf02771e717c3da6b2b9b1a78 lib-preview — unprovable · video / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-16fcd07875c51cffdfe6e26ce3dc93b7049b218176b4172efaab6cc816ea9ec9 lib-preview — abstracted · video / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ea905d3840d9de6245bdc589ba81957c1f2b3de0d952211ee332995bba580fc8 lib-preview — abstracted · video / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b18c2fc1dc9ed43bdd7c353b62e1e3284767fa1f2c7956ca9a531301a46a95da lib-preview — abstracted · video / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a0b919077b93856f9d74d7d4365c50e01bc92a395f4032912d30e3e8712fbcc3 lib-preview — unprovable · video / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-6d0c6aa55e74d7b147051742bb09d090d36caf100a6a3ccd35cd51bca89f3ed1 lib-preview — unprovable · video / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-0b06d3ad7b601386036b598dd467435223808c1bc38da87af1a7a701a3857199 lib-preview — unprovable · music / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-4c81dd74f52c0116c827a89c476710560ad7c765b9fc9ee8e8424a79a12c5a7b lib-preview — abstracted · music / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c705a76dee1877dd562ecfac2f4b723a3262208a08d7253df9d29c211f9f8fe8 lib-preview — abstracted · music / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-629086a31bd2bb0294b5e3b1044499507a3334abc5c5eece5cab256808b98585 lib-preview — abstracted · music / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8e93afcb5bf236e1ada59a8ccca0798368867e8015d37df8a14daceb90355ee9 lib-preview — unprovable · music / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-18ce07751c32d933de262d5fb19903333403ba1df3d5777f1e1c0a7d06d5da02 lib-preview — unprovable · music / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-a12a7e10001b628c5b8c1d151ee51c420de8ee8a4b44196de8e9b46b88c7885b lib-preview — unprovable · overflow-lib-preview / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-f3fbc6cef7940c942237bf1e76621522a1f5b10d5f92e2a3238071ec80b1a9d3 lib-preview — abstracted · overflow-lib-preview / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7f20de3a4e72116ab94b5f0186fc8b99d3adcc4b0c50b832341580dff19a3e9c lib-preview — abstracted · overflow-lib-preview / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b692a40afcda42c300ff29d15a299a7c37ed33ced37f61e23dc7b15d0f9433c0 lib-preview — abstracted · overflow-lib-preview / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3d52827f0d1a6d8e7d557396cf1f56c3a754f03dfdae2d4218e35dd6fe737b67 lib-preview — unprovable · overflow-lib-preview / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-bd149db14ea9e3433ba6fab202808616aa9d3e5f1a21e9ad1c565a5073a5f00c lib-preview — unprovable · overflow-lib-preview / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-e8548df329d2cb813da5381c47cd9af332fa09894d213dfb22fe6adc2961a810 lib-preview — unprovable · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-146b3e8e37b044ce1220d5fb03cf6279ca14ed4254758cb7b42082ddbe44892d lib-preview — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b4eb82a0c9f10c3eb9fd21a1035f05336821e2eba77c17d0dd48d3b8e6201db6 lib-preview — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-395e78c77314d0495312c649ff91b8b25060653dc415960bfc51fde5141308f9 lib-preview — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-03193beb1308f09ca938ce87172d8ffec80e696d579391fa4336de1df01467c3 lib-preview — unprovable · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-9bd559ed3c8291826fea02b50d85bc30991a85b02f43ea29278c0b3d74b7d1e6 lib-preview — unprovable · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-04d99f337929afc0c4e1e4d3fb5b1bd8caff03a65476eba9ed62907a834abcb6 settings — done · default / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-09f9233a4db170f7312291d95a4dfe1da9408f69bfe5029915730b33ea588109 settings — unprovable · default / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-7a7a68e40a5f751f73a7d3887a52cea6b1df164d9ad787432719a5bf2f4fd42e settings — unprovable · default / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-f3d1de39500f2e5a6d38fb52575ef3a9d304f8e15b460cfd1a0bfd6c67238a5b settings — unprovable · default / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-676ae9607f50f95365bbc6a92ec043cb4be743cc6f51ae85547fb86e296e02f0 settings — done · default / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-fa642469b7c1a19a64bd45dfab40a5abce4966e41f85f95dcd9d6a49ae905add settings — done · default / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-ff26f28d2a7e2b4f3f702e520a0a7da631babd788392d29bcfb840d3540e8793 settings — done · gateway-on-warning / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-cfc7635c9c6f61d6eba7c2fe7ec846b0649fed3f9b347e2e8232c767785c6395 settings — abstracted · gateway-on-warning / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f36950714acd43df9e9bca0d5a79dce3aaec8b3f8799a01efaf1bda958f75586 settings — abstracted · gateway-on-warning / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8270e1876a1bd971f18282a9de87b04ea0630f8b8ebf309520e816689eea0cd5 settings — abstracted · gateway-on-warning / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f632333cb2a010ad2ef0eb0991e66efef0049ff118d2d3ff96a23940fe117878 settings — done · gateway-on-warning / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-e02dc22a2c58285921c4fd75dde1fb2b4050306a4dcc9d3101b5a8f4e458e224 settings — done · gateway-on-warning / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-1ffbf7825a3b6c20766ecb5f216be36244fa17063e8a4730dd3c0b32ed7fabf5 settings — done · overflow-settings-drawer / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-4cb63ce8c920e31944d3c7f02668a92ed0b5e799e58cdce328e820b823922e7d settings — abstracted · overflow-settings-drawer / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0dda15c15bbf9f77013c8a3f1fb2845c51548eee6348ca397773d11821c120d0 settings — abstracted · overflow-settings-drawer / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-534a874ae2d91ee1aa9af03e967f4e04687cb9dfe6570446cfb3cc547e6ede64 settings — abstracted · overflow-settings-drawer / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b077f5df7463fdfe9df893dc411618ea5989fb29fa05a1235025248f18830c56 settings — done · overflow-settings-drawer / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-2fe3f31f101a249dfc7c592e59d962eb4fca1be4d7f2456b0ae6a3a8bb4f6e73 settings — done · overflow-settings-drawer / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-1cff4666d7b38dcc0e07b95eae99f5fa220e9a0fcfb78bdbe7d3dc98d6effbab settings — done · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-b1b403dba777d50b43d7b1b6c03acd96f02a86885041ef2469c4bb93358c78e3 settings — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f4cda5a798e2a4a3084098ecb4c6c176af0a815719cd938fcaf63293955d5c3c settings — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0571a77aa331c37e38a132a4af7300612217ce444d00d1057940df2ec4ed5bff settings — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-90555e1390a13091e305fae2d8f69482c67d6bb5212363d831e687169b56acb5 settings — done · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-456514319ac24b229b9b91870dad42b6b170858178f59ba66940e2e034330495 settings — done · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v10-settings/manifest.json · reviewers：['v10-settings/review-claude-A/report.json', 'v10-settings/review-codex-A/report.json'] · 模式：dual · 分歧：v10-settings/reconcile/A.json · 降级：无
- V-7d302def91a51daafc015dcaf9d34d0bbab5bcc116866a73e6de7c10d8f1f10b firstrun — gap · default / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-95f7748aec7ef956040b2d51c0e3821be536a5dfcd480452f9e7f4bd58ab6aaa firstrun — unprovable · default / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-376907a5c63a1b517608c14094d1a8e83d93f02c7605cbc0bbd504e5d35b0b41 firstrun — unprovable · default / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-64cf47a73835dc7855888b6ae709b6f28b8c67489ad096d1c75930bd0a17ecd9 firstrun — unprovable · default / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-6ec3e52a6ea07023b5036af049d1525514ff14b037d6017360bc01d82dee84cf firstrun — gap · default / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-695b77c08cf520dc870308a15aad99ef32c0bd0e1bca7efc4ed17991e77e2f22 firstrun — gap · default / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无
- V-c7ccae4221a2df337aa85342d10786187bef5c6c9409691b7e0326f4d8a2ba4a firstrun — gap · adopt-candidates / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-b423be1a649d444a412bb45cea755b392720369d7d9ed7f998038a9fbda3e582 firstrun — abstracted · adopt-candidates / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2b43a41601162d3d55c72171c9f0b8eea797240884850c61c3b706c7936b740c firstrun — abstracted · adopt-candidates / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2d46c383bbe7105c4de14ebc31eba2f8bc335ed3c07366c6350a28622fa994e3 firstrun — abstracted · adopt-candidates / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4630a87ba717ae77c51ab95a75ef48aa0d34c6de861bf3dd9331e2af25cf88b5 firstrun — gap · adopt-candidates / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-d6daeb3a0680cdf8f673f787638bb2074dc8fece3e9b4be6f31d86ec4a773275 firstrun — gap · adopt-candidates / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无
- V-a4f090e50af024bda721a48dc507e05effa9fa022d9f0ac19a170f6d20078095 firstrun — gap · fit-report / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-f716d605ae580cbf8a347e571a9f99b3ce9a37a9bbfc64b4b32c5a851d2bc1dc firstrun — abstracted · fit-report / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b0e2b46afb999ea3db57b19b8358fdb659026f07506049aa8f3a5d5e036a9148 firstrun — abstracted · fit-report / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-edfefd037459e8ee5b5f62b820f0f8a79927f16abde1146ab446aeca3b379722 firstrun — abstracted · fit-report / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-475fdcc356fd03f55861b6bd1d252fb54b83edf66bdacdac0450999ecc6772d2 firstrun — gap · fit-report / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-e97cdd6f8e5a30f109609b58bf7e9388ba87f892a3439e01d6d9f2ef9d8e93d4 firstrun — gap · fit-report / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无
- V-27fc76fd2f8c599d8d3e9dae4cb51a8a55784397fba24ad6779a79567eae8d50 firstrun — gap · overflow-firstrun / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-1d597a0196d3e954857f8968c4c3ea0f14666280052df0e96d04e61b75a1e32b firstrun — abstracted · overflow-firstrun / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b4a9aeee8bbf58b050a20c5d93aa00ddf9aa5a3aee4b5267cb6f69cea8dc4841 firstrun — abstracted · overflow-firstrun / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-269004722ddbd5608030c225c8e812ca7143cc5c535058ebfb4b07c2a14671a4 firstrun — abstracted · overflow-firstrun / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-43903aab31cf45f9cfcc43546aa4dee71c158212ab055f7d7056c223e1882d8d firstrun — gap · overflow-firstrun / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-91313b5085fdd715da616d3af39b0ff3958a25145ce4b57e0499b632e22c16ac firstrun — gap · overflow-firstrun / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无
- V-2db547594784c563799547d4d8a842f89e975cc034d38585ace84ce46f5781a0 firstrun — gap · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-0981d43127be8c9d402cc6cda8c87bd94e5b55286485fbc691ba5dfee78e730e firstrun — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8ae72958f22a560817d1354d6865c9c9cf1327fe3453879fee91a3dfe930d70c firstrun — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-05f276a499c94db47e66456ac1fabac9bc6b764a51780af57f1016fdae085d31 firstrun — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6602243872fa4f13bc1b476d8163eaac80a9f386f65b8092cc01ac2a6c2ba7c3 firstrun — gap · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-f26bb814c7a229d16dac977872df837dc7483452476792f90f28f447a10f837f firstrun — gap · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无
- V-edcdd8bd544a4b839cd83eea87a8535b1432df08402aad27d123613e899cebd0 fatal — gap · config-corrupt / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-927ee8e27b8c6004cc76f1f6ae729341fbb9c2323724aaa6403ad7639b3eee9f fatal — unprovable · config-corrupt / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-abf24ca5666e818b945fec6b0c423cfc15640a0780f70448940cba2be5af3828 fatal — unprovable · config-corrupt / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-1b320428c62a6053145d4458ecd021428b28abf839c131d0fdf0350936fce15b fatal — unprovable · config-corrupt / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-9ef73e4fdb5c456af23a4b193be552fff457edcd4940593244bf4aba3b30dc43 fatal — gap · config-corrupt / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-23d788134a478c63888ed1b1da491cb90ca46327b898fcd86c7feb0d157e990a fatal — gap · config-corrupt / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无
- V-cb78edb40ca2118250bf042c974aa1ae24ffc93691dc57d0c7f6f1ba8248c96c fatal — gap · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-56f31c0e7d70e7c6c04aed9471a4abc98485745ac4f581e676653640e30b6665 fatal — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e6707fec5f2bb0732f4ca266878646e189443fadd407cdf3d6df7079f82eca7b fatal — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7ba8cc44639e5e208326c0d1856086e28d12f222210e8847f606fae93946c113 fatal — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f7f08ae8276640300b6c68093a8eefabd2e92346ee949f910d0a7aceb6e028c8 fatal — gap · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-90300235498b9eaa37f755bc8411cef5a6ba84d9f5c65f68cf79b55d35f6b6c9 fatal — gap · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无
- V-45cb93a5a4c24a931d1344b89b6614fe95ab0a4087ad6a64cc79e1b7a23f8f08 skill-panel — unprovable · list / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-5e6b6b3bfe8226a3d2425fff0e9ea5b8011c951b53d4c98bc00de2ce616b479e skill-panel — unprovable · list / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-d974d0d16a98096424436aefc8a2f98c72629bb7f36ec2862a285aa9b8c229a4 skill-panel — unprovable · list / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-1aeec1c91938521c5c47c8af372abf244df7a8d67e8fa1f7c2598ae5d82e5479 skill-panel — unprovable · list / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-16e1d5bea3ebf7ecbb05c8fa27300c71337455d23235e6c14cc5b7bd216ce00e skill-panel — unprovable · list / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-a9855f4b481082d8b9125efa59a6468d8567b6b1f7934b6bf293fa046be60bb7 skill-panel — unprovable · list / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-7d29aad51c297facadc1de73b7a28fcee8a43e44934aaa022df0325635359208 skill-panel — unprovable · overflow-skill-panel / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-78debe5fc8a4d83a8a158c694b5053477115f7702e8cde4ea1c9202ef7218122 skill-panel — abstracted · overflow-skill-panel / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8460066343a68841aa05fbf147f1c6054b66d183ddc0c55a207b7f807efde70a skill-panel — abstracted · overflow-skill-panel / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9606ce54ab9035c31d0ae0130476646da2e0c705fc7f0a771fa8d2fa2b40cdf8 skill-panel — abstracted · overflow-skill-panel / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8f6312a044f4426bebc975915747c0ae3aac5ec9655615abac1b8d0febc53c83 skill-panel — unprovable · overflow-skill-panel / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-478a20e2b25ad960577a66a926934437fd4ab9d81b0293d98c5af644a95e13f3 skill-panel — unprovable · overflow-skill-panel / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-116b89175d3f653e4a4c2f1d3406ae452fa729160f1a00a77db7adb81aee0ecd skill-panel — unprovable · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-f94987e42e6a61a2f1fab2b2d4a508cfca5df386bc2c3bc087672d419fb22180 skill-panel — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6fb2d5788287c5a56534af0a54b58b545034bf20d83fcf9239ee1a8f81b2d17e skill-panel — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7d6401edbfd752f9edf0ac908481f71ad133eafcd3035d4f48b1bb972487e6bd skill-panel — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c2a128108439dde54151a7ebbf8022c5ec3a6301b9c4fb639b70a821c46351a3 skill-panel — unprovable · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-d4206349b5bbcb213ec6eb73b71cc37497ba991628421db2c3ae8b782b83d440 skill-panel — unprovable · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-20d0cd204105928eea495758567e668267f8712094c21a849d7a8015a9335797 skill-install — unprovable · input / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-c80f278d100523e6af55796b72c8893b0c49ca13759a2071e864433d707dc7af skill-install — unprovable · input / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-5498e04dfaef0d40172bacce02d9cd0d39c7ab6d0911b51c7f6fb837cd288248 skill-install — unprovable · input / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-1845599d62c103304c90f2a3c11a5bab07408a5ebde7ff8eeb37f4ded0602ad4 skill-install — unprovable · input / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-708e1046fdd14ebebe0e9c6eb4c29f25cfdb20bd35b2aa1e423efb352ccff7e0 skill-install — unprovable · input / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-f431b5b9d20ea2f01803b85693f4cf44106aa7221f7f8f4ee50b34e4baf94bb8 skill-install — unprovable · input / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-595dfa0a2d20d7192bcdd6136d094bfbf32de7c1b547ff6499679a3f0a6e0d10 skill-install — unprovable · preview / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-c1be565d4853d0cb246212cfa2c58f5066622fee031b98e7a7b97baefef0813d skill-install — abstracted · preview / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c307cb8e4bb157336aca47351dd60ca14b692a732cb73da5f546048ea125a541 skill-install — abstracted · preview / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a18c2feafa4d699a0b86f30d7d5b368a864ed15fa2f3e82cacd710bfd2a1294d skill-install — abstracted · preview / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4e83549d495ece2dd087ce46659bdf88b070e55febcd8bb561f52aec806a16c3 skill-install — unprovable · preview / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-46bcdf75fcbb33f9e7f468121edf915af39cea7744db4012269acd7a9c76ab7c skill-install — unprovable · preview / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-b4620da3a70f99bcc931ca5bb3074752fda26fed3f4a058fd088979f944733de skill-install — unprovable · error / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-dbac6fd169978aa58305d4f83c294e38da1089841a8e7aee3a14a66672d419f2 skill-install — abstracted · error / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-47a8c5bc24313917604c16c27fa982dd8ccf1bb2223bc0ce5f3669bbce4c0b69 skill-install — abstracted · error / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2f67ab9a83309baa036357c149b5a6f330ebece0951db902e950d74bada17ffa skill-install — abstracted · error / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3f57cede05a286d15e5b0d21cea408c55be3cf82ec797591fc057a5e6dfe90fd skill-install — unprovable · error / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-e49777eca8fe358c7250400652f2c89896a05a1c09c524f145b9f4c0c4648dd9 skill-install — unprovable · error / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-add12ffe08efc439232f0610228010405d47049efef946268ca47ba0a31e59a3 skill-install — unprovable · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-fb5d7893ab2eb00d8efad10a6ab1cb994026ec5738d31946d674799d7392db46 skill-install — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-dee7a10256caf05c150fe896931332dfb73ae206342cebe464607c05a56c7955 skill-install — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-90d88e41c9415b93b0dee7cc6060370b4d7dace9a8ec081a34b188f4aa48dd3c skill-install — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-18e00fc0f781efee607562d5b07d0c070020c7d8a914070553a4c3603bed1201 skill-install — unprovable · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-6a8d4bba646e6377968b1edfae813d5a0727cb6e1875bd10931f9e8a85488a13 skill-install — unprovable · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-e65639f29bc16aa4d6be45d9f2911254a7c82e1fa09c56209d74270772e8fc31 confirm — unprovable · delete-session / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-f1c22f256d230e3fd0bdd81448d0e0618b29d5863fc9500a236430a329322021 confirm — unprovable · delete-session / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-d24893f049231bac908895ed5006605025e5b06c1e5123a2911e532225e1cb50 confirm — unprovable · delete-session / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-4473554e7272dacfd274c574eda5dd5e040bdb283e2ad6669627f7e173f0efd9 confirm — unprovable · delete-session / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-701c8ac1cf6d466eb29b48b1961836cc7b0c666d65c3738ec2f77c2c4e4f0093 confirm — unprovable · delete-session / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-d2eb3d934e191ca5f85df0ca248fc0bdf1d0c241646fc52a51fe3e5066d01ab7 confirm — unprovable · delete-session / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-e24c826c5bb5d678940c8036d1de9ff91e26013242e0e8b17ecceb6e8b3e4ff5 confirm — unprovable · memory-warning / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-f728e0d760f628c655b126b38d4032c4e97c64394361834de71a89a031862811 confirm — abstracted · memory-warning / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-15b7bb4fa68e37b30e5d37c03633d03a06d519783c727c99c9899accf30e9627 confirm — abstracted · memory-warning / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ebb05116a83201c2741368aeb4cd27e77ddd216f0c64f9581b4ef504d5e76287 confirm — abstracted · memory-warning / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cd5893953cdef632271a74603d2b08ebeb472447d54b74c2eefd3f7e5e4e3f80 confirm — unprovable · memory-warning / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-bd1e872e996730512fbd3d24940a1a5ec36fd4f11f0a5278d567e3603dbe509e confirm — unprovable · memory-warning / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-f952d8aaea0f85826b3cd6b870496bfd80ebe768190de838cd93441c8678c075 confirm — unprovable · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-8a15d3b59e2b17259c972e38c421e3274e9abeccfce624507304f02e0ab07046 confirm — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e1bdc440b9e6f61e7dbee118d782c99c15c9e55c303d6dbb9762e37fba14ed0e confirm — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-68787fef43c814519be4631bdba102b3ba9594ae9b46cf27d8b8130d7cdf76ab confirm — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bb64d6b33389b06ab2e1d5c24bd81b2461a0d0c3a3c7cb0271996d4dc363bb58 confirm — unprovable · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-280cc080ab10d866870e83832f323b41e095c3f842b40951f7f4a1dca1b140c4 confirm — unprovable · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-7aa029bcdce845e9400ee09a84ad03cc32351c55befca7026f73db2da61ffdf3 media-picker — unprovable · first-frame-grid / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-5b4743056f5a133ed4a0f68eea14882ce73f962b45775f5b3a8f3b05aa26f0bf media-picker — unprovable · first-frame-grid / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-f3be1d4924ecc2bffa3b1eb42c0a3996bb4c99b52b1c41419f34e543723f7397 media-picker — unprovable · first-frame-grid / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-fd2cf18ebca2d164e55aa950ac36619459df2dd40c374fc8cf3a9248d494b591 media-picker — unprovable · first-frame-grid / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-6e3dc42f347e3f0afba134cd8c8d71e25e7efacc03677f8d15726fc22f9c6a9c media-picker — unprovable · first-frame-grid / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-49c279b44e41bbe0c1154f4e35f32b246dbb64785acc44e7516215b0a39eb1d9 media-picker — unprovable · first-frame-grid / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-7cfec5d42bd517f638892b8e249961ea8f3d824326f984f0f9e52ac7b067e0b8 media-picker — unprovable · song-list / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-9bb03a0a62b8bd58596cd20e508d230aef3b228db77c95154a41e6e5056daeb6 media-picker — abstracted · song-list / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3b6387ac12a2a1bfc742d62cc042f885b80e8294a77d3429ec4e78e4b2e2a37d media-picker — abstracted · song-list / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bdda90d8ac5426fb3cca32454e1098699faa958c166e379bf9ef4c0c4b908f28 media-picker — abstracted · song-list / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8218eae108395ffd8234fd64f609ba3cbfdf142fae099fbf4e208188f976a3e2 media-picker — unprovable · song-list / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-6372e0158a86cdf0c10a38bcc24b9636262e9cb9557feafd07d3176d3971047b media-picker — unprovable · song-list / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-cc97fc93094124f3a252d778ed65cfdd2ad65b998a0dbc1468d8f4203ffeccf5 media-picker — unprovable · empty / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-fadf77e173a81cb725f388ab75ce59230e55f2a24fc1c924c5a7311498ad7a03 media-picker — abstracted · empty / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-de8605b078e219cfe4645e98b728160efb01f556d8267309898b9ead795be61b media-picker — abstracted · empty / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-615625d267486325447bd862ef02f7b78b6edfdd44c9b57707753cfd249f7876 media-picker — abstracted · empty / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5419b96bd70811240d22f40ae3bb8e1360e0e4c55194fe3cf32ebcf9d86d9245 media-picker — unprovable · empty / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-7f4d94818af7726cc910aa0c902e572a0fb11427858eca5dec042ba56201ffce media-picker — unprovable · empty / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-076197069aa9a6f20c19eea5e0898e2462ecfa24251313ced0e2baadaebb329a media-picker — unprovable · overflow-media-picker / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-11f6bbc0d426efc520a83082ee3e56567e7e4ceda6d9ecbfa0f7a6e3282cc5e0 media-picker — abstracted · overflow-media-picker / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-377bfdd46cb296ba650a219a79aeabffb5dcde787a1317b6d2acc212e006adca media-picker — abstracted · overflow-media-picker / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-390a306ee098a6b43a17e76864fa5dd0055ac2be23140ea77ea2a37defe6be86 media-picker — abstracted · overflow-media-picker / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a4dbbab951005dde6b9988438f38d0fb04e35377c2abf12bb3bb3d594ec17598 media-picker — unprovable · overflow-media-picker / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-00f478c31859e4685fd01ccc1165e24725d6d21cf5253cf7df9510c32dbccc02 media-picker — unprovable · overflow-media-picker / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-8a3b267e3efee72ca6ca68717a6be8b3a67e96b38053d81e0f8904e884e9de40 media-picker — unprovable · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-9250a2db5d4fd41ffea45d9acac5909d8097182b261046c534bda6c1378270c9 media-picker — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-261345cf30ed0d41114f00db8d280d1dcbed85e1dc2be391f077144ed50208a3 media-picker — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-756315f793eb6489f5d01b8569295a4e704375efeb1bd330e7a8f27f88edd7e6 media-picker — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f7f217a308a5f3e6c8225ea1d3bb9b94f5501a31660f08878238ccdb0c1d4db3 media-picker — unprovable · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-9d31a7569556c80a8a6203c5f0df3945933714767ff2e64d93ed2d01de35cbe7 media-picker — unprovable · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v09-dialogs/reconcile/unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-56a87a2ba00953a275b3030f213828d2eb183b7775e19071f8f93e629d2cbefa shell-error — gap · health-timeout / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-b90bad61dcc1ede28242fdfdde35684da92d8357e20126265fc7419a8ecf62e6 shell-error — unprovable · health-timeout / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-7794b9ccd9b174ceaf608fad72d490a9d6c58c6229c593e2f4e6516c6ab4bcf3 shell-error — unprovable · health-timeout / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-c8f52619de6cfb0f7bdcaab0d25ae659e11108d790af9a6bc00fa46f64431b38 shell-error — unprovable · health-timeout / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/reconcile/A-mid-unprovable.md · reviewers：[] · 模式：dual · 分歧：无 · 降级：无
- V-25f2ac4a228be223b5059fb50667af069a1f9aa2edab342902ae1698820c4a58 shell-error — gap · health-timeout / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-e76c4ae00f8cf9def2a63c860843e44e8ddcba82a2115c50aeeb69f633d022bf shell-error — gap · health-timeout / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无
- V-bddb6cc9a462cdeb05e0610f671e92c458e09777c4709af218f0c7271e5304f0 shell-error — gap · details-open / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-3511786653d086f574d8d951344ed71b4967d86c6df7515bd5befedd588bbe52 shell-error — abstracted · details-open / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-59fc6f9d745ee152dad66aa4b745da73227e4487c1bd34329f48b4cac7494d28 shell-error — abstracted · details-open / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-86b57d3932b30715c893ba58f5687c0414d1be45c8dce041e2a2452b5408759e shell-error — abstracted · details-open / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b3770e9a6f6f7239be3118c36915cbc0402060f336e8bf17bead6c96cb9b80cb shell-error — gap · details-open / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-da17612f46f0c99c86dfeaac536cae27cf292c778ef0203b3d2e028a8bd75d33 shell-error — gap · details-open / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无
- V-6e755ebde140824c9b5ebccfdfed39f064fecfb4494cbe0699c33b99d5a84317 shell-error — gap · resize-shrink-to-min / 900x600@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-A/report.json', 'v11-firstrun-fatal-shellerror/review-codex-A/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/A.json · 降级：无
- V-b14fa67996cdef1ef537b88a98ffa32fda1a4cffabca59ebbdc7b8fd1b003369 shell-error — abstracted · resize-shrink-to-min / 1100x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2b23475a78eca60fd212a166a2e52c92667bac2c35fcada75432f5b1ccb59a4b shell-error — abstracted · resize-shrink-to-min / 1200x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4db0200d2732b5cc5eaaaaa5e7f005f764ace16b4f9db887bbe376c6d1e61f8e shell-error — abstracted · resize-shrink-to-min / 1300x800@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5f4990536d6e3c1b99d5df8bbfe35dc46fc38fe694442472b0dcf026b499ef2b shell-error — gap · resize-shrink-to-min / 1400x900@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-B/report.json', 'v11-firstrun-fatal-shellerror/review-codex-B/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/B.json · 降级：无
- V-bd47b12ef08b60885771eeda88ee8a06387a1585b5ce0a0166af016b0abaf2a3 shell-error — gap · resize-shrink-to-min / 2560x1440@1 / WebKit (WKWebView, macOS 15+) / dark / 浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） / zh-CN / landscape / mouse
  证据：v11-firstrun-fatal-shellerror/manifest.json · reviewers：['v11-firstrun-fatal-shellerror/review-claude-C/report.json', 'v11-firstrun-fatal-shellerror/review-codex-C/report.json'] · 模式：dual · 分歧：v11-firstrun-fatal-shellerror/reconcile/C.json · 降级：无

逐轴覆盖（已抽象与不适用不计）：
- state：adopt-candidates 3/3 · config-corrupt 6/6 · continue-locked 3/3 · conversation 6/6 · custom-size 3/3 · default 18/18 · delete-session 6/6 · detail 3/3 · details-open 3/3 · empty 24/24 · empty-session 3/3 · error 3/3 · first-frame-grid 6/6 · fit-report 3/3 · gateway-on-warning 3/3 · generating 9/9 · grid 6/6 · health-timeout 6/6 · image 6/6 · input 6/6 · keyboard-focus 3/3 · list 9/9 · memory-warning 3/3 · mode-image-first-frame 3/3 · model-unloaded 3/3 · music 3/3 · overflow-attempt-media 6/6 · overflow-chat-composer 3/3 · overflow-chat-messages 3/3 · overflow-firstrun 3/3 · overflow-image-composer 6/6 · overflow-lib-preview 3/3 · overflow-media-picker 3/3 · overflow-media-timeline 9/9 · overflow-music-lyrics 3/3 · overflow-sessions-list 12/12 · overflow-settings-drawer 3/3 · overflow-skill-panel 3/3 · overflow-video-composer 3/3 · overflow-video-materials 3/3 · overflow-video-prompt 3/3 · partial-model 3/3 · preview 3/3 · resize-shrink-to-min 45/45 · scroll-bottom 6/6 · scroll-top 6/6 · session-hover-actions 3/3 · song-list 3/3 · streaming 3/3 · video 3/3 · with-result 6/6 · with-results 3/3
- device：1100x800@1 15/15 · 1200x800@1 15/15 · 1300x800@1 15/15 · 1400x900@1 85/85 · 2560x1440@1 85/85 · 900x600@1 85/85
- os：WebKit (WKWebView, macOS 15+) 300/300
- appearance：dark 300/300
- dynamic_type：浏览器缩放 100% + 固定 px 字号（app.css:7 14px，其余全是 px，没有 rem） 300/300
- locale：zh-CN 300/300
- orientation：landscape 300/300
- pointer：mouse 300/300
