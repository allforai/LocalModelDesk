---
{"node_id": "image-session-verify", "capability": "product-verify", "goal": "在真实 app 与真实 Qwen-Image 模型下走完用户验收旅程，截图并经两位独立评审，证明图片会话满足全部确认验收", "exit_artifacts": [{"path": ".allforai/verify/image-sessions-verify.json", "validation_commands": ["python3 -c \"import json; d=json.load(open('.allforai/verify/image-sessions-verify.json')); assert d.get('status')=='passed', d.get('status')\"", "python3 -m pytest tests/e2e/test_image_sessions.py -q"]}, {"path": ".allforai/verify/ui-screenshot-manifest.json", "validation_commands": ["python3 -c \"import json; json.load(open('.allforai/verify/ui-screenshot-manifest.json'))\""]}, {"path": ".allforai/verify/visual-review-1.json", "validation_commands": ["python3 -c \"import json; json.load(open('.allforai/verify/visual-review-1.json'))\""]}, {"path": ".allforai/verify/visual-review-1.md", "validation_commands": []}, {"path": ".allforai/verify/visual-review-2.json", "validation_commands": ["python3 -c \"import json; json.load(open('.allforai/verify/visual-review-2.json'))\""]}, {"path": ".allforai/verify/visual-review-2.md", "validation_commands": []}, {"path": ".allforai/verify/ui-visual-reconciliation.json", "validation_commands": ["python3 -c \"import json; json.load(open('.allforai/verify/ui-visual-reconciliation.json'))\""]}, {"path": ".allforai/verify/ui-visual-closure-audit.json", "validation_commands": ["python3 -c \"import json; json.load(open('.allforai/verify/ui-visual-closure-audit.json'))\""]}, {"path": ".allforai/verify/ui-visual-closure-audit.md", "validation_commands": []}], "responsibilities": ["verification"], "source_inputs": ["docs/superpowers/specs/2026-09-24-image-sessions-design.md", ".allforai/bootstrap/local-requirements.json"], "parallel_write_scopes": ["tests/e2e/test_image_sessions.py"], "knowledge_refs": ["knowledge/capabilities/product-verify.md", "knowledge/capabilities/visual-verify.md", "knowledge/verification-protocol.md"], "consumers": ["image-session-repair", "image-session-ship"], "hard_blocked_by": ["image-session-design", "image-session-backend", "image-session-pane"], "alignment_refs": [], "unlocks": ["image-session-repair", "image-session-ship"], "human_gate": false, "discipline_owner": null, "decision_mode": "none", "input_dependencies": [".allforai/visual-qa/**", ".allforai/image-sessions/backend-report.json", ".allforai/image-sessions/pane-report.json"], "node_spec_path": ".allforai/bootstrap/node-specs/image-session-verify.md", "profile_slice": {"tech_stacks": ["python backend desk/", "vanilla JS frontend desk/static/"], "test_commands": {"backend": "python3 -m pytest tests --ignore=tests/e2e -q", "frontend": "node --test tests/js/", "e2e": "python3 -m pytest tests/e2e -q"}}, "closure_verify": [], "requirement_refs": [{"path": ".allforai/bootstrap/local-requirements.json", "id": "image-sessions", "revision": 1}], "decision_inputs": [".allforai/bootstrap/local-requirements.json"], "product_goals": ["图片页像聊天一样有会话列表；一个会话是围绕同一想法的一串生成尝试，用户不满意时可以调整后继续生成，之前的尝试都留在会话里"], "acceptance": ["连续三轮「生成 → 在这张基础上改 → 再生成」后，三张图及各自参数都在同一个会话里按顺序显示", "「在这张基础上改」生成的新图与原图种子相同；「换个构图」生成的新图提示词相同而种子不同", "重启 app 后会话列表、每个会话的尝试和图片都还在", "切到另一个会话再切回，内容不变；新建会话后生成的图只进新会话", "删除会话后会话从列表消失，其中的图片仍能在素材库打开", "失败或取消的尝试在会话里可见并显示原因，不会留下一张空白图", "在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误"]}
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
- Primary outcome：以「证伪」姿态在真实环境证明（或推翻）图片会话满足 `image-sessions` rev 1 的全部验收，产出可复现证据与双评审截图结论。
- Non-goals：不修产品代码（发现问题按类别记入 gaps，交给 `image-session-repair`）；不扩大到视频/音乐；不以假执行器的结果代替真实出图的验收。
- Must-read inputs：`.allforai/bootstrap/local-requirements.json` rev 1 acceptance（逐条）、`.allforai/visual-qa/` 下由 image-session-design 产出的视觉验收标准（JSON + MD）与截图证据要求（截图状态清单）、`docs/superpowers/specs/2026-09-24-image-sessions-design.md`（选择器以外的行为）；上游 `backend-report.json`、`pane-report.json` 为 passed。缺失 → blocked。
- Optional inputs：`pane-report.json` 里列出的关键选择器。
- Context budget：上述文件 + `tests/e2e/conftest.py`、`desk/testing/harness.py`；按需扩展并记录。
- Quality questions：
  1. 验收的每一条是否都有一个真正会失败的检查（改坏实现时它会红）？
  2. 「重启 app 后仍在」是否真的停掉进程再起（同一数据目录），而不是刷新页面？
  3. 种子相同/不同的断言是否读的是后端落定的尝试参数，而不是前端表单？
  4. 截图是否覆盖 `.allforai/visual-qa/` 下由 image-session-design 产出的视觉验收标准（JSON + MD）与截图证据要求 的每个状态和两种视口？
- Stop conditions：模型或 MLX 运行环境不可用 → `BLOCKED_ENV`（不用假执行器冒充）；浏览器起不来 → `BLOCKED_ENV`；截图缺失/不可读 → `blocked_by_missing_screenshots` / `blocked_by_unreadable_screenshot`。
- Repair targets：`code_gaps`、`test_gaps`、`contract_gaps`、`environment_blockers`、`visual_quality_gaps`、`experience_gaps`。

## Theory Anchors
- 证伪优先（verification-protocol.md「Disprove, don't confirm」）。
- 双评审（ADR-0003，bootstrap-planning「UI screenshot + reviewer two visual review hard gate」）。

## Knowledge References
- `${CLAUDE_PLUGIN_ROOT}/knowledge/verification-protocol.md#the-one-rule`：只有真实外部证据才算 verified；没跑过就写 `method: none`。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/verification-protocol.md#anti-fabrication-capture-dont-author-l1--reproduce-l2`：命令类证据必须用 `capture_evidence.py` 采集，不得手写。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/verification-protocol.md`（rule 6）：运行时证据写 `served_by: {host, process, mock_layers, fixtures}`；mock_layers 非空的条目不能判 done。
- `${CLAUDE_PLUGIN_ROOT}/skills/visual-qa/40-qa/batch-visual-acceptance/SKILL.md`：截图后的批量视觉验收流程；评审二优先用另一平台 CLI（`codex`），不可用时用第二个全新上下文子代理。

## Guidance
两层验收：
0. 先跑全量 `python3 -m pytest tests --ignore=tests/e2e -q`、`node --test tests/js/`、`python3 -m pytest tests/e2e -q`，任何失败记 gaps。
1. **自动化回归（假执行器，快速、可重复）**：新增 `tests/e2e/test_image_sessions.py`，用 `launch_test_harness` 覆盖：三轮迭代留在同一会话且顺序正确；「在这张基础上改」尝试种子与原图相同、「换个构图」提示词相同而种子不同（读 `/api/image-sessions/{id}` 落定数据断言）；切换会话再切回内容不变；新建会话后的生成只进新会话；删除会话后该会话从列表消失且切到其他会话、其中图片仍能在素材库打开；空会话首次生成后标题取提示词（按设计文档的截断规则）、重命名后标题不再被自动改；首次进入且没有任何会话时的行为符合设计文档；生成中删除所属会话不报错且图进素材库；素材库回填打开所属会话并选中该尝试；图片文件被删后显示「图片文件已不在」；新会话首图种子不是固定默认值；失败与取消的尝试显示原因且无空白图；harness 重启（同数据目录）后会话仍在；主流程文本不含「种子」。这是本节点 exit 的 validation command。
2. **真实验收（真实模型，served_by 无 mock）**：源码目录没有 `.venv-image`，图片运行时只在打包 app 里；用户正在运行 `dist/LocalModelDesk.app`，同 bundle 双开会互相误杀（memory: cross-exam-prober-hygiene）。因此：`bash scripts/build-app.sh --adhoc --output <scratchpad>/verify-bundle` 构建独立副本，用独立数据目录启动，只按自己记录的 pid 停止与重启，绝不碰 `dist/` 及其进程；截图复用 `scripts/visual-capture.py`，截图前按 pid 用 NSRunningApplication 激活到前台（被遮挡时 WebKit 不出图）。模型用 `image-models/qwen-image-2.1-heretic`，参数取小（如 512×512、步数 4–8）以控制时长，走一遍「生成 → 在这张基础上改 → 生成 → 换个构图」，然后停掉服务进程再启动、确认会话与图片仍在。按 `.allforai/visual-qa/` 下由 image-session-design 产出的视觉验收标准（JSON + MD）与截图证据要求 截图（1280×800 与 900×700），写 `ui-screenshot-manifest.json`。
3. **双评审**：评审一（全新上下文子代理）与评审二（codex CLI 或第二个全新子代理）各自独立看截图写报告，互不先读；评审一再做 reconciliation 与 closure audit。阻断项为两者并集。
4. `image-sessions-verify.json`：`status`（全部 acceptance 均有 verified 证据且双评审无 blocker/major 时才为 `passed`），`acceptance[]` 逐条 `{statement, method, evidence_path, served_by, verdict}`，以及按类别分的 gaps。

## User-visible decisions
Not applicable — no end-user surface（本节点只验证，不实现界面）

## Exit Artifacts
- `.allforai/verify/image-sessions-verify.json`
- `.allforai/verify/ui-screenshot-manifest.json`
- `.allforai/verify/visual-review-1.json`
- `.allforai/verify/visual-review-1.md`
- `.allforai/verify/visual-review-2.json`
- `.allforai/verify/visual-review-2.md`
- `.allforai/verify/ui-visual-reconciliation.json`
- `.allforai/verify/ui-visual-closure-audit.json`
- `.allforai/verify/ui-visual-closure-audit.md`

## Effect Verification
- `real-test`：`python3 -m pytest tests/e2e/test_image_sessions.py -q`（capture_evidence）。
- `real-run` + `screenshot`：真实模型、真实进程重启的旅程，served_by 的 mock_layers 为 `[]`。
- 双评审报告与 closure audit。任一缺失即不通过。

## Quality Acceptance
- rev 1 的 7 条验收每条都有 verdict=verified 的条目；「重启」条目证据显示进程 pid 变化；种子断言来自后端数据。
- 失败码：`failed_visual_review`、`blocked_by_missing_second_review`、`unverified_acceptance`、`BLOCKED_ENV` → 不完成，gaps 交 `image-session-repair`。

## Downstream Contract
→ image-session-repair reads：`image-sessions-verify.json` 的 gaps（code/test/contract/visual_quality/experience）与对应证据路径。


## Freshness registration rule（2026-09-24 诊断后追加）
执行中额外读取的文件，只有在它**不属于任何下游节点的 `parallel_write_scopes`** 时，才可以用 freshness `read` 登记。下游会改写的文件只能读，读过的记进报告，不能登记——登记它们会让下游一交付就把本节点判为过期（inverted_source_inputs）。本 run 的 image-session-design 就是这样出的故障。

## Node 26 注意（2026-09-24 诊断后追加）
本机 Node v26 把 `node --test tests/js/` 的目录参数当成模块路径而失败；凡本说明或 Project Context 写 `node --test tests/js/` 之处，一律执行 `node --test tests/js/*.test.js`。

## 用户决定（2026-09-24，U-06）
素材库条目元数据里的「种子 N」豁免：素材库不属于图片主流程，本需求只改图片页（BR-1）。设计文档 D-50a 与视觉标准已写明。U-06 不再是 contract gap，不要改素材库文案；repair-report 的 contract_gaps 中移除 U-06。

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
- Prove what this node's declared responsibilities (verification) can actually produce at this stage, against those same statements, and record it under Quality Acceptance and Effect Verification. Documentation proves that the documents describe current behavior accurately and passes its declared document_verification; writing a guide is not proof that the behavior it describes was built.
- Where a statement's full product effect first exists at a later stage, state the stage-local proof in Effect Verification and name the node that proves the full effect as downstream_effect_owner; a deferral with no owner, or one whose owner does not carry these requirements, is refused as unowned_effect_stage. A stage-local pass is not product completion: the nodes holding the implementation and verification responsibilities for these requirements still owe the full effect.
