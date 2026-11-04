---
{"node_id": "image-session-pane", "capability": "ui-forge", "goal": "把图片页改成会话式界面：会话列表、尝试时间线、「在这张基础上改 / 换个构图」、折叠的高级参数，接到 /api/image-sessions", "exit_artifacts": [{"path": ".allforai/image-sessions/pane-report.json", "validation_commands": ["python3 -c \"import json; d=json.load(open('.allforai/image-sessions/pane-report.json')); assert d.get('status')=='passed', d.get('status')\"", "node --test tests/js/*.test.js"]}], "responsibilities": ["implementation", "verification"], "source_inputs": ["docs/superpowers/specs/2026-09-24-image-sessions-design.md", ".allforai/bootstrap/local-requirements.json", "desk/static/js/panes/chat.js", "desk/static/js/icons.js", "desk/static/js/widgets/confirm.js", "desk/static/js/widgets/error_block.js"], "parallel_write_scopes": ["desk/static/index.html", "desk/static/app.css", "desk/static/js/panes/image.js", "desk/static/js/api.js", "desk/static/js/main.js", "desk/static/js/store.js", "desk/static/js/pure/image_session*.js", "desk/static/js/widgets/image_session*.js", "desk/static/js/widgets/jobview.js", "tests/js/image*.test.js", "tests/js/api.test.js", "tests/js/jobview*.test.js", "tests/e2e/test_image_flow.py", "desk/static/js/panes/library.js", "desk/static/js/pure/history_fill.js", "tests/js/history_fill.test.js", "tests/js/library_pane.test.js", "tests/e2e/test_library_panel.py", "tests/js/media_panes.test.js"], "knowledge_refs": ["knowledge/capabilities/ui-forge.md", "knowledge/cross-phase-protocols.md", "knowledge/defensive-patterns.md"], "consumers": ["image-session-verify"], "hard_blocked_by": ["image-session-design", "image-session-backend"], "alignment_refs": [], "unlocks": ["image-session-verify"], "human_gate": false, "discipline_owner": null, "decision_mode": "none", "downstream_effect_owner": "image-session-verify", "input_dependencies": [".allforai/visual-qa/**", ".allforai/image-sessions/backend-report.json"], "node_spec_path": ".allforai/bootstrap/node-specs/image-session-pane.md", "profile_slice": {"tech_stacks": ["python backend desk/", "vanilla JS frontend desk/static/"], "test_commands": {"backend": "python3 -m pytest tests --ignore=tests/e2e -q", "frontend": "node --test tests/js/", "e2e": "python3 -m pytest tests/e2e -q"}}, "closure_verify": [], "requirement_refs": [{"path": ".allforai/bootstrap/local-requirements.json", "id": "image-sessions", "revision": 1}], "decision_inputs": [".allforai/bootstrap/local-requirements.json"], "product_goals": ["图片页像聊天一样有会话列表；一个会话是围绕同一想法的一串生成尝试，用户不满意时可以调整后继续生成，之前的尝试都留在会话里"], "acceptance": ["连续三轮「生成 → 在这张基础上改 → 再生成」后，三张图及各自参数都在同一个会话里按顺序显示", "「在这张基础上改」生成的新图与原图种子相同；「换个构图」生成的新图提示词相同而种子不同", "重启 app 后会话列表、每个会话的尝试和图片都还在", "切到另一个会话再切回，内容不变；新建会话后生成的图只进新会话", "删除会话后会话从列表消失，其中的图片仍能在素材库打开", "失败或取消的尝试在会话里可见并显示原因，不会留下一张空白图", "在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误"]}
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
- Primary outcome：用户在图片页里能新建/切换/重命名/删除会话，看到该会话的全部尝试，点任意一张用「在这张基础上改」或「换个构图」继续生成，新尝试接在会话末尾——在真实浏览器里可用。
- Non-goals：不改后端契约（有偏离写 `contract_gaps` 交回）；不改聊天/视频/音乐面板；不做局部重绘；不重做全局视觉风格。
- Must-read inputs：`docs/superpowers/specs/2026-09-24-image-sessions-design.md`（布局、动作行为、四态文案、当前会话恢复）、`.allforai/visual-qa/` 下由 image-session-design 产出的视觉验收标准（JSON + MD）与截图证据要求（每个状态的 must_show/must_not_show）、`.allforai/bootstrap/local-requirements.json` rev 1；后端 `backend-report.json` 为 passed。任一缺失 → blocked。
- Optional inputs：`desk/static/js/panes/chat.js` 的会话列表实现（结构与交互一致性）、`widgets/confirm.js`；后端实现 `desk/library/image_sessions.py`、`desk/library/http.py` 可按需查看以核对契约（契约以设计文档为准，读取记入报告）。
- Context budget：`desk/static/js/panes/image.js`、`index.html` 图片段、`app.css` 相关段、`api.js`、`main.js` 的图片装配与 tick、`widgets/jobview.js`，以及上面 Must-read；按需扩展并记录。
- Quality questions：
  1. 生成中切到别的会话再切回，进度与结果是否出现在正确的会话里，而不是当前正看着的会话？
  2. 主流程任何可见文字（含 title/tooltip/aria-label）是否出现「种子」？
  3. 失败/取消的尝试是否显示原因而不是空白图框？
  4. 窄窗（900×700）下会话列表与时间线是否不重叠、不截断？
- Stop conditions：需要设计文档没写的用户可见决定 → Pattern I；后端契约与设计不符 → `contract_gaps` 并 blocked。
- Repair targets：`code_gaps`、`test_gaps`、`contract_gaps`、`visual_quality_gaps`。

## Theory Anchors
- Nielsen 一致性：会话列表与聊天页同构（ui-forge.md）。
- 渐进披露：高级参数默认折叠（ui-forge.md）。

## Knowledge References
- `${CLAUDE_PLUGIN_ROOT}/knowledge/cross-phase-protocols.md#B.3`（Closure Thinking）：每个新建的模块必须有生产环境的调用方真正 import 并调用它；只存在文件不算接通。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/cross-phase-protocols.md#F`：每个上游拉取都是本节点守着的接缝——说明拿到的值什么情况下可用，同一内容多处出现时以设计文档为准。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/defensive-patterns.md#pattern-i`：上游设计文档没覆盖的用户可见决定不归执行者发明；不实现、不放占位，在 `contract_gaps` 追加 kind `unspecified_user_visible_decision`，完成并证明其余覆盖部分；由此导致的 `check_artifacts.py` 失败是预期结果。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/defensive-patterns.md#pattern-j`：每个配置项只有一个受众，只有 `end-user` 项可以出现在终端用户界面上；受众没人决定过的项按 Pattern I 升级，不要猜。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/verification-protocol.md`：desk/static 改动必须跑真实浏览器 e2e（项目 memory 记录过假 DOM 单测漏掉的真实崩溃）。

## Guidance
- 纯逻辑（尝试 → 表单回填、换构图的新参数、标题截断、状态文案）放 `desk/static/js/pure/image_session*.js` 并写 `node --test` 单测；DOM 组装放 pane/widget。
- `api.js` 增加 image-sessions 的调用；`startImageJob` 带 `session_id`。
- `main.js` 的 tick/jobView 逻辑需要知道作业属于哪个会话：结果写入由后端负责，前端结束时刷新该会话，不在前端拼尝试。
- 「换个构图」随机种子用 `crypto.getRandomValues`，范围 0–4294967295。
- 现有 `tests/e2e/test_image_flow.py` 断言了旧的 seed 默认值与布局，按新设计更新（不是删除覆盖）。
- 素材库回填按设计文档自审闭环 d 改：`history_fill.js` / `library.js` / `main.js applyFill`，并更新其单测与 `tests/e2e/test_library_panel.py`。
- 会话列表的「正在生成」标记与跨会话忙碌提示按自审闭环 e；「图片文件已不在」态按 c。
- 完成后自测：`node --test tests/js/`、`python3 -m pytest tests/e2e -q`（全量，防止素材库/标签页等回归）。

## User-visible decisions
| Decision | Kind | Source artifact path | Audience |
|---|---|---|---|
| 会话列表：新建、切换、重命名、删除（删除有确认，说明图片留在素材库） | screen | docs/superpowers/specs/2026-09-24-image-sessions-design.md | end-user |
| 尝试时间线：缩略图、提示词摘要、状态；失败/取消显示原因 | screen | docs/superpowers/specs/2026-09-24-image-sessions-design.md | end-user |
| 「在这张基础上改」：回填提示词与参数、沿用种子、不自动提交 | entry | docs/superpowers/specs/2026-09-24-image-sessions-design.md | end-user |
| 「换个构图」：同参数、新随机种子、立即提交 | entry | docs/superpowers/specs/2026-09-24-image-sessions-design.md | end-user |
| 高级参数（宽、高、步数、种子）默认折叠 | setting | docs/superpowers/specs/2026-09-24-image-sessions-design.md | end-user |
| 空会话 / 生成中 / 忙碌 / 模型缺失 各态文案 | copy promise | docs/superpowers/specs/2026-09-24-image-sessions-design.md | end-user |

## Exit Artifacts
- `.allforai/image-sessions/pane-report.json`：`status`、`evidence`（`node --test` 与 `tests/e2e/test_image_flow.py` 的 capture_evidence 记录）、`consumers`（新模块在 main.js/image.js 的调用处）、`contract_gaps`/`code_gaps`/`visual_quality_gaps`（非空则不是 passed）。

## Effect Verification
- `real-test`：`node --test tests/js/` 与 `python3 -m pytest tests/e2e -q`（全量，真实 Chromium），用 capture_evidence 采集。
- `screenshot`（自检，非最终验收）：harness 下截图空会话、三条尝试的时间线、失败尝试三张，对照 `.allforai/visual-qa/` 下由 image-session-design 产出的视觉验收标准（JSON + MD）与截图证据要求 自查。
- 完整用户可见效果（真实模型、重启、双评审）由 `image-session-verify` 证明：`downstream_effect_owner: image-session-verify`。

## Quality Acceptance
- 用户可见决定表每一行都有实现且在自检截图中可见；主流程不出现「种子」（在 e2e 里用文本断言）。
- 失败码：`seed_word_in_main_flow`、`blank_image_on_failure`、`attempt_in_wrong_session`、`e2e_not_run` → 不完成。

## Downstream Contract
→ image-session-verify reads：完整界面与 data-* 选择器（在报告中列出关键选择器，供 e2e 使用）。

## Integration Points
← image-session-backend 产出 `/api/image-sessions` 与 `start_image_job(session_id)` → 本节点只经 `api.js` 调用；尝试的状态由后端落定，前端不自行写尝试。


## Freshness registration rule（2026-09-24 诊断后追加）
执行中额外读取的文件，只有在它**不属于任何下游节点的 `parallel_write_scopes`** 时，才可以用 freshness `read` 登记。下游会改写的文件只能读，读过的记进报告，不能登记——登记它们会让下游一交付就把本节点判为过期（inverted_source_inputs）。本 run 的 image-session-design 就是这样出的故障。

## Node 26 注意（2026-09-24 诊断后追加）
本机 Node v26 把 `node --test tests/js/` 的目录参数当成模块路径而失败；凡本说明或 Project Context 写 `node --test tests/js/` 之处，一律执行 `node --test tests/js/*.test.js`。

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
- Prove what this node's declared responsibilities (implementation, verification) can actually produce at this stage, against those same statements, and record it under Quality Acceptance and Effect Verification. Documentation proves that the documents describe current behavior accurately and passes its declared document_verification; writing a guide is not proof that the behavior it describes was built.
- Where a statement's full product effect first exists at a later stage, state the stage-local proof in Effect Verification and name the node that proves the full effect as downstream_effect_owner; a deferral with no owner, or one whose owner does not carry these requirements, is refused as unowned_effect_stage. A stage-local pass is not product completion: the nodes holding the implementation and verification responsibilities for these requirements still owe the full effect.
