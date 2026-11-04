---
{"node_id": "image-session-design", "capability": "ui-design", "goal": "产出图片会话的设计文档（数据模型、API 契约、作业与会话的挂接、界面布局与四态、文案）和可截图验收的视觉标准", "exit_artifacts": [{"path": "docs/superpowers/specs/2026-09-24-image-sessions-design.md", "validation_commands": ["grep -q '在这张基础上改' docs/superpowers/specs/2026-09-24-image-sessions-design.md", "grep -q '换个构图' docs/superpowers/specs/2026-09-24-image-sessions-design.md", "grep -q '/api/image-sessions' docs/superpowers/specs/2026-09-24-image-sessions-design.md"]}, {"path": ".allforai/visual-qa/visual-acceptance-criteria.json", "validation_commands": ["python3 -c \"import json; d=json.load(open('.allforai/visual-qa/visual-acceptance-criteria.json')); assert d.get('status')=='passed', d.get('status')\""]}, {"path": ".allforai/visual-qa/visual-acceptance-criteria.md", "validation_commands": []}, {"path": ".allforai/visual-qa/visual-evidence-requirements.json", "validation_commands": ["python3 -c \"import json; json.load(open('.allforai/visual-qa/visual-evidence-requirements.json'))\""]}], "responsibilities": ["documentation"], "source_inputs": [".allforai/bootstrap/local-requirements.json", "desk/library/sessions.py", "desk/library/history.py", "desk/static/js/panes/chat.js", "docs/superpowers/specs/2026-08-31-library-design.md"], "parallel_write_scopes": ["docs/superpowers/specs/2026-09-24-image-sessions-design.md"], "knowledge_refs": ["knowledge/capabilities/ui-design.md", "knowledge/defensive-patterns.md", "knowledge/cross-phase-protocols.md"], "consumers": ["image-session-backend", "image-session-pane", "image-session-verify"], "hard_blocked_by": [], "alignment_refs": [], "unlocks": ["image-session-backend"], "human_gate": false, "discipline_owner": null, "decision_mode": "none", "node_spec_path": ".allforai/bootstrap/node-specs/image-session-design.md", "profile_slice": {"tech_stacks": ["python backend desk/", "vanilla JS frontend desk/static/"], "test_commands": {"backend": "python3 -m pytest tests --ignore=tests/e2e -q", "frontend": "node --test tests/js/", "e2e": "python3 -m pytest tests/e2e -q"}}, "closure_verify": [], "requirement_refs": [{"path": ".allforai/bootstrap/local-requirements.json", "id": "image-sessions", "revision": 1}], "decision_inputs": [".allforai/bootstrap/local-requirements.json"], "product_goals": ["图片页像聊天一样有会话列表；一个会话是围绕同一想法的一串生成尝试，用户不满意时可以调整后继续生成，之前的尝试都留在会话里"], "acceptance": ["连续三轮「生成 → 在这张基础上改 → 再生成」后，三张图及各自参数都在同一个会话里按顺序显示", "「在这张基础上改」生成的新图与原图种子相同；「换个构图」生成的新图提示词相同而种子不同", "重启 app 后会话列表、每个会话的尝试和图片都还在", "切到另一个会话再切回，内容不变；新建会话后生成的图只进新会话", "删除会话后会话从列表消失，其中的图片仍能在素材库打开", "失败或取消的尝试在会话里可见并显示原因，不会留下一张空白图", "在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误"]}
---
## Project Context
LocalModelDesk：macOS 本地桌面应用（Python 后端 `desk/`，原生 ES module 前端 `desk/static/`，打包脚本 `scripts/build-app.sh`）。
聊天会话已有「一个会话一个 JSON 文件」的存储（`desk/library/sessions.py`，路由在 `desk/library/http.py`）。
图片生成走 `desk/media/service.py` 的单作业互斥（同时只允许一个媒体作业，`start_image_job`），
每次生成是一个新进程 `desk/media/image_cli.py`（Qwen-Image 2.1 / MLX）。作业结束写 `history`（`desk/library/history.py`）。
图片面板 `desk/static/js/panes/image.js` 目前只显示当前一个作业（`widgets/jobview.js`），没有会话、没有历史。
测试：`python3 -m pytest tests --ignore=tests/e2e -q`、`node --test tests/js/`、`python3 -m pytest tests/e2e -q`（Playwright，`desk.testing.launch_test_harness`）。
项目约定：台面未发布——设计里不谈兼容/迁移（memory: no-legacy-framing）；视觉基线是 ChatGPT 式聊天布局、按钮分级、卡片列表，聊天栏 24px 边距、最大 1400px（memory: visual-baseline-direction）；desk/static 改动必须跑 tests/e2e（memory: verify-gate-needs-e2e，假 DOM 单测漏过真实浏览器崩溃）。
需求来源：`.allforai/bootstrap/local-requirements.json` id `image-sessions` revision 1，用户在 2026-09-24 会话中确认（选择 b 会话形式、手动新建、删会话保留图片、「在这张基础上改 / 换个构图」且界面不出现「种子」）。

## Attention Contract
- Primary outcome：一份让后端、前端、验收三个节点无需再做任何用户可见决定就能动手的设计文档 `docs/superpowers/specs/2026-09-24-image-sessions-design.md`，外加一份截图验收标准 `.allforai/visual-qa/visual-acceptance-criteria.json`。
- Non-goals：不写产品代码；不做视频/音乐会话；不做局部重绘/图生图；不设计批量出图、队列、模型常驻；不谈旧数据迁移（台面未发布）。
- Must-read inputs：`.allforai/bootstrap/local-requirements.json` 中 `image-sessions` rev 1 的 goal / business_rules / acceptance（用户确认）；`desk/library/sessions.py`（沿用的存储形态）；`desk/static/js/panes/chat.js`（会话列表交互基线）。缺失或状态非 confirmed → 返回 blocked。
- Optional inputs：`desk/library/history.py`；`desk/static/js/pure/history_fill.js`、`desk/static/js/panes/library.js`（素材库回填，下游会改写）、`docs/superpowers/specs/2026-08-31-library-design.md`；当前 `desk/static/js/panes/image.js`、`desk/static/index.html`、`desk/media/service.py` 可按需查看（记录在报告里），它们会被下游改写，所以不列入 source_inputs。
- Context budget：上述文件 + 本节点说明；不做全仓库扫描。
- Quality questions：
  1. 用户在「不满意 → 调整 → 再生」的循环里，每一步看到什么、点什么，是否一眼能懂而完全看不到「种子」一词？
  2. 生成进行中切换会话、生成失败/取消、app 重启时，尝试记录会不会丢、会不会出现一张空白图？
  3. 作业（单作业互斥）与会话的关系是否唯一确定：作业开始时就把尝试挂到哪个会话、结束时如何落定？
  4. 删除会话为什么不会删到素材库里的图？
- Stop conditions：需求未确认或与设计冲突；发现需要新的产品选择（例如会话数量上限、标题自动更新规则以外的行为）→ 记录为待决问题并返回 blocked，不自行决定。
- Repair targets：`contract_gaps`、`quality_gaps`。

## Theory Anchors
- Jobs-to-be-Done（ui-design.md）：设计围绕「把一张图调到满意」这个任务，而不是围绕功能清单。
- Nielsen 可见性/一致性原则（ui-design.md）：进行中、失败、空会话都有明确状态；会话列表交互与聊天页一致。
- 最小惊讶原则：「在这张基础上改」沿用种子，「换个构图」换种子，两者行为在文案里讲清楚后果而不是机制。

## Knowledge References
- `${CLAUDE_PLUGIN_ROOT}/knowledge/cross-phase-protocols.md#B.3`（Closure Thinking）：每个新建的模块必须有生产环境的调用方真正 import 并调用它；只存在文件不算接通。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/cross-phase-protocols.md#F`：每个上游拉取都是本节点守着的接缝——说明拿到的值什么情况下可用，同一内容多处出现时以设计文档为准。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/defensive-patterns.md#pattern-i`：上游设计文档没覆盖的用户可见决定不归执行者发明；不实现、不放占位，在 `contract_gaps` 追加 kind `unspecified_user_visible_decision`，完成并证明其余覆盖部分；由此导致的 `check_artifacts.py` 失败是预期结果。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/defensive-patterns.md#pattern-j`：每个配置项只有一个受众，只有 `end-user` 项可以出现在终端用户界面上；受众没人决定过的项按 Pattern I 升级，不要猜。


## Guidance
设计文档至少要定下来（每一条写成可测试的陈述）：
1. **数据模型**：图片会话文件（放在数据目录下独立子目录，与聊天会话分开）字段：id、title、created、updated、attempts[]；每个 attempt：job_id、ts、status（running/done/failed/cancelled）、params（prompt,width,height,steps,seed）、output、error。标题规则：空会话首次生成时取提示词（截断长度写明），重命名后不再自动改。
2. **API 契约**：`/api/image-sessions` 的 list / create / get / rename / delete（路径、请求体、响应、错误码）；`start_image_job` 如何携带 `session_id`；缺失/不存在 session_id 的行为；作业开始时即追加 running 尝试、结束时由媒体服务落定状态（包括失败、取消、服务关闭时仍在跑的作业）——明确由哪个组件负责写入，避免前端轮询丢写。
3. **删除语义**：只删会话文件，`outputs/` 与 history 不动，素材库仍可见。
4. **两个动作**：「在这张基础上改」= 回填该尝试的提示词、宽高、步数、种子到表单并聚焦提示词输入框，不自动提交；「换个构图」= 用该尝试的参数、随机新种子（范围 0–4294967295）立即提交。生成中两个动作的禁用态与说明文案。
5. **新会话与当前会话**：手动「新建」；未新建时生成接在当前会话；首次进入且没有任何会话时的行为（自动建一个还是提示新建——选一种并写理由，这是界面细节而非产品方向，本节点可以决定）；当前会话 id 如何在刷新后恢复。
6. **布局**：左侧会话列表（与聊天页同构：新建、切换、重命名、删除确认），右侧为该会话的尝试时间线（最新在下或在上——写明）+ 底部提示词输入与「生成」按钮 + 可折叠「高级参数」（宽、高、步数、种子）。尝试卡片显示缩略图、提示词摘要、状态；点开看大图与参数。主流程任何可见文案不出现「种子」，只在高级参数里出现。
7. **各状态**：会话列表空、会话内无尝试、生成中（进度条沿用 jobview 的步数进度）、失败/取消（显示原因，不显示空白图）、模型缺失/运行环境不可用（沿用现有 setModelStatus/setRuntimeStatus 文案）、另一个媒体作业占用时的忙碌原因。
8. **自审闭环（2026-09-24，必须逐条落到文档）**：
   a. 作业运行中其会话被删：落定时丢弃会话记录、图片照常进素材库；删除确认框在该会话有运行中作业时明确提示。
   b. 只有作业真正开始（通过互斥、内存确认、参数校验）后才追加尝试；启动失败不留 running 尝试。
   c. 尝试的图片文件已不在（用户在访达删除）：显示「图片文件已不在」态，不显示破图。
   d. 素材库「回填」：若该图属于某会话，打开那个会话并选中该尝试；不属于任何会话的回填到当前会话。
   e. 跨会话可见：会话列表标记正在生成的会话；在别的会话里看到的忙碌提示写明是哪个会话在生成，并可一键回到它。
   f. 新会话第一次生成用随机种子（界面不可见），不再沿用固定默认值 42，避免每个会话首图构图相同。
   g. 单张尝试的删除本次不做（用户 2026-09-24 明确决定），文档写为非目标。
9. **visual-acceptance-criteria.json**：`status: "passed"` 仅在标准写完整时；`states[]` 列出需要截图的每个状态（上面 7 的各态 + 三轮迭代后的时间线 + 重命名/删除确认），每个状态给 `must_show`、`must_not_show`（如「种子」一词不得出现在主流程、不得出现空白图片框）、`viewport`（1280×800 和窄窗 900×700）。

## User-visible decisions
本节点是这些决定的来源，不实现界面。表中「Source artifact path」即本节点产出：

| Decision | Kind | Source artifact path | Audience |
|---|---|---|---|
| 会话列表（新建/切换/重命名/删除） | screen | .allforai/bootstrap/local-requirements.json | end-user |
| 「在这张基础上改」「换个构图」两个动作 | entry | .allforai/bootstrap/local-requirements.json | end-user |
| 高级参数（宽、高、步数、种子）默认折叠 | setting | .allforai/bootstrap/local-requirements.json | end-user |
| 删除会话只删分组、图片留在素材库 | copy promise | .allforai/bootstrap/local-requirements.json | end-user |

## Exit Artifacts
- `docs/superpowers/specs/2026-09-24-image-sessions-design.md`：设计文档，覆盖 Guidance 1–7，每节给出可被测试断言的陈述。
- `.allforai/visual-qa/visual-acceptance-criteria.json`：视觉验收标准，JSON，`status` 只在完整时为 `passed`，否则为 `blocked` 并在 `contract_gaps` 写明缺什么。
- `.allforai/visual-qa/visual-acceptance-criteria.md`：同一标准的人读版本。
- `.allforai/visual-qa/visual-evidence-requirements.json`：每个状态需要的截图证据（视口、数据前置条件、文件命名），供验收节点照单截图。

## Effect Verification
本节点的效果是「下游无需再做用户可见决定」。证明方式：逐条把 `image-sessions` rev 1 的 business_rules 和 acceptance 映射到设计文档的章节（写在文档末尾的对照表里），任何映射不到的条目 → `quality_gaps`，本节点不通过。完整产品效果由 `image-session-verify` 在真实浏览器中证明。

## Quality Acceptance
- 每条 business_rule 与 acceptance 在对照表中都有落点；API 契约包含错误码与并发边界（单作业互斥下切换会话、服务关闭时的 running 尝试）。
- 视觉标准的每个状态都有 must_show / must_not_show，且包含「主流程不出现『种子』」与「失败不显示空白图」两条。
- 失败码：`missing_rule_mapping`、`ambiguous_api_contract`、`missing_state_criteria` → 节点不完成。

## Downstream Contract
→ image-session-backend reads：数据模型、API 契约、作业↔会话挂接与落定职责、删除语义。
→ image-session-pane reads：布局、两个动作的行为、四态文案、当前会话恢复规则、API 契约。
→ image-session-verify reads：`.allforai/visual-qa/visual-acceptance-criteria.json` 全部 states，以及对照表中的每条验收。


Confirmed product goals:
- 图片页像聊天一样有会话列表；一个会话是围绕同一想法的一串生成尝试，用户不满意时可以调整后继续生成，之前的尝试都留在会话里

Confirmed acceptance (inherited requirement scope, complete and unmodifiable):
- 连续三轮「生成 → 在这张基础上改 → 再生成」后，三张图及各自参数都在同一个会话里按顺序显示
- 「在这张基础上改」生成的新图与原图种子相同；「换个构图」生成的新图提示词相同而种子不同
- 重启 app 后会话列表、每个会话的尝试和图片都还在
- 切到另一个会话再切回，内容不变；新建会话后生成的图只进新会话
- 删除会话后会话从列表消失，其中的图片仍能在素材库打开
- 失败或取消的尝试在会话里可见并显示原因，不会留下一张空白图
- 在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误

Stage obligation:
- The acceptance above is the complete user-confirmed acceptance of the requirements this node consumes. It is the scope this node serves, not a claim that this node proves all of it. Nothing in it may be dropped, reworded or narrowed here; acceptance that differs from the confirmed requirement is refused as stale_requirement.
- Prove what this node's declared responsibilities (documentation) can actually produce at this stage, against those same statements, and record it under Quality Acceptance and Effect Verification. Documentation proves that the documents describe current behavior accurately and passes its declared document_verification; writing a guide is not proof that the behavior it describes was built.
- Where a statement's full product effect first exists at a later stage, state the stage-local proof in Effect Verification and name the node that proves the full effect as downstream_effect_owner; a deferral with no owner, or one whose owner does not carry these requirements, is refused as unowned_effect_stage. A stage-local pass is not product completion: the nodes holding the implementation and verification responsibilities for these requirements still owe the full effect.
