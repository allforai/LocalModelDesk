---
{"node_id": "image-session-backend", "capability": "translate", "goal": "实现图片会话的本地持久化、/api/image-sessions 路由，以及图片作业开始/结束时把尝试写进所属会话", "exit_artifacts": [{"path": ".allforai/image-sessions/backend-report.json", "validation_commands": ["python3 -c \"import json; d=json.load(open('.allforai/image-sessions/backend-report.json')); assert d.get('status')=='passed', d.get('status')\"", "python3 -m pytest tests/test_image_sessions.py tests/test_library_http.py tests/test_media_image_service.py -q"]}], "responsibilities": ["implementation", "verification"], "source_inputs": ["docs/superpowers/specs/2026-09-24-image-sessions-design.md", ".allforai/bootstrap/local-requirements.json", "desk/library/sessions.py", "desk/library/history.py", "desk/library/errors.py", "desk/media/commands.py", "desk/media/image_cli.py"], "parallel_write_scopes": ["desk/library/image_sessions.py", "desk/library/http.py", "desk/library/__init__.py", "desk/media/service.py", "desk/media/routes.py", "desk/foundation/paths.py", "desk/foundation/routes.py", "desk/app.py", "desk/runtime.py", "desk/testing/**", "tests/test_image_sessions*.py", "tests/test_library_*.py", "tests/test_media_*.py", "tests/media_fakes.py", "tests/test_foundation_paths.py"], "knowledge_refs": ["knowledge/cross-phase-protocols.md", "knowledge/defensive-patterns.md"], "consumers": ["image-session-pane", "image-session-verify"], "hard_blocked_by": ["image-session-design"], "alignment_refs": [], "unlocks": ["image-session-pane"], "human_gate": false, "discipline_owner": null, "decision_mode": "none", "downstream_effect_owner": "image-session-verify", "input_dependencies": [".allforai/visual-qa/**"], "node_spec_path": ".allforai/bootstrap/node-specs/image-session-backend.md", "profile_slice": {"tech_stacks": ["python backend desk/", "vanilla JS frontend desk/static/"], "test_commands": {"backend": "python3 -m pytest tests --ignore=tests/e2e -q", "frontend": "node --test tests/js/", "e2e": "python3 -m pytest tests/e2e -q"}}, "closure_verify": [], "requirement_refs": [{"path": ".allforai/bootstrap/local-requirements.json", "id": "image-sessions", "revision": 1}], "decision_inputs": [".allforai/bootstrap/local-requirements.json"], "product_goals": ["图片页像聊天一样有会话列表；一个会话是围绕同一想法的一串生成尝试，用户不满意时可以调整后继续生成，之前的尝试都留在会话里"], "acceptance": ["连续三轮「生成 → 在这张基础上改 → 再生成」后，三张图及各自参数都在同一个会话里按顺序显示", "「在这张基础上改」生成的新图与原图种子相同；「换个构图」生成的新图提示词相同而种子不同", "重启 app 后会话列表、每个会话的尝试和图片都还在", "切到另一个会话再切回，内容不变；新建会话后生成的图只进新会话", "删除会话后会话从列表消失，其中的图片仍能在素材库打开", "失败或取消的尝试在会话里可见并显示原因，不会留下一张空白图", "在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误"]}
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
- Primary outcome：后端能按设计文档的契约增删改查图片会话，并且每次图片作业（成功/失败/取消/服务关闭）都在所属会话里留下一条状态正确的尝试，重启后仍在。
- Non-goals：不改前端；不改聊天会话存储的行为；不做视频/音乐会话；不引入作业队列；不做数据迁移。
- Must-read inputs：`docs/superpowers/specs/2026-09-24-image-sessions-design.md`（数据模型、API 契约、落定职责、删除语义）；`.allforai/bootstrap/local-requirements.json` image-sessions rev 1。设计文档缺失或 `.allforai/visual-qa/` 下由 image-session-design 产出的视觉验收标准（JSON + MD）与截图证据要求 非 passed → 返回 blocked。
- Optional inputs：`desk/library/sessions.py`（原子写、锁、corrupt 处理可照搬）、`desk/media/service.py` 当前的 `_start/_finalize/close`。
- Context budget：`desk/library/*`、`desk/media/service.py`、`desk/media/routes.py`、`desk/foundation/paths.py`、`desk/app.py` 的装配处及对应测试；按需扩展并在报告里记录。
- Quality questions：
  1. 作业在运行中时服务被关闭/崩溃，重启后该尝试是 running 永远挂着，还是被落定成可理解的失败状态？
  2. 两个请求同时写同一个会话（落定 + 重命名）时会不会丢写？
  3. 删除会话时 outputs/ 和 history 是否完全不受影响？
  4. 路径参数能否穿越到数据目录外（沿用 `_ID_RE` 校验）？
- Stop conditions：设计契约与现有单作业互斥冲突且设计未说明 → `contract_gaps` 并 blocked；无法在不改前端的前提下满足契约 → blocked。
- Repair targets：`code_gaps`、`test_gaps`、`contract_gaps`。

## Theory Anchors
- Clean Architecture 分层（cross-phase-protocols）：存储（library）与作业（media）通过注入的回调/接口挂接，media 不直接读写会话文件格式。
- 原子写 + 单进程锁（沿用 SessionStore 做法）。

## Knowledge References
- `${CLAUDE_PLUGIN_ROOT}/knowledge/cross-phase-protocols.md#B.3`：新建的 ImageSessionStore 必须在 `desk/app.py` 生产装配中被构造并传给路由与媒体服务；只在测试里构造不算接通（blocking `code_gaps`）。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/cross-phase-protocols.md#F`：从设计文档拉取的 API 契约是本节点守着的接缝；设计文档与需求冲突时以需求为准并记 `contract_gaps`。
- `${CLAUDE_PLUGIN_ROOT}/knowledge/verification-protocol.md`：测试必须走真实路径（真实文件系统上的 store、真实 HTTP 路由分发），不能只对 mock 断言；证据用 `capture_evidence.py` 采集。

## Guidance
- 新模块 `desk/library/image_sessions.py`：仿照 `SessionStore`（独立目录、原子写、锁、corrupt 标记、id 正则）。路径加到 `desk/foundation/paths.py`。
- 路由加到 `desk/library/http.py`，契约严格按设计文档（含错误码）。
- 媒体服务：`start_image_job` 接收 `session_id` 并校验存在；作业开始即追加 running 尝试，`_finalize`（以及 `close()` 取消路径）落定状态、output、error。挂接方式用注入回调（类似 `on_job_finished`），不要让 media 依赖 library 内部格式。
- 只有作业真正开始后才追加 running 尝试（互斥 409、insufficient_memory、参数校验失败都不留记录），测试覆盖；落定时会话已被删除 → 丢弃记录不报错，图片照常写 outputs 与 history，测试覆盖。
- 启动时把残留的 running 尝试（上次进程被杀）落定为 failed 并写明原因——具体文案取设计文档。
- 测试：`tests/test_image_sessions.py`（store 与 HTTP 往返、删除不碰 outputs/history、路径穿越拒绝、并发写）、扩充 `tests/test_media_image_service.py`（成功/失败/取消/close 四种落定）。`desk/testing` 的 harness/fakes 若需要支持图片会话，一并更新，供 e2e 使用。

## User-visible decisions
Not applicable — no end-user surface

## Exit Artifacts
- `.allforai/image-sessions/backend-report.json`：`status`（仅当下列证据都在且通过时为 `passed`）、`evidence`（capture_evidence 记录路径：pytest 输出、一次真实 HTTP 往返的请求/响应）、`consumers`（ImageSessionStore 在 desk/app.py 被构造的位置）、`code_gaps`/`test_gaps`/`contract_gaps`（非空则不是 passed）。

## Effect Verification
- `real-test`：`python3 -m pytest tests --ignore=tests/e2e -q` 全量通过（不只新测试，防止回归），用 `capture_evidence.py` 采集。
- `real-api`：启动 `launch_test_harness`，对 `/api/image-sessions` 做 create → 用 session_id 启动图片作业（harness 的假执行器可接受，因为此处验证的是会话落定而非出图；served_by 如实写 mock_layers）→ 作业结束后 GET 会话看到 done 尝试 → 重启 harness（同一数据目录）后仍在 → DELETE 后 outputs 文件仍可 GET。
- 完整的用户可见效果（真实模型出图、界面）由 `image-session-verify` 证明，本节点声明 `downstream_effect_owner: image-session-verify`。

## Quality Acceptance
- 四种落定（done/failed/cancelled/服务关闭）都有测试且断言尝试字段完整；重启后没有永远 running 的尝试。
- 删除会话前后 `outputs/` 文件列表与 history 条目完全相同（测试断言）。
- 失败码：`unwired_store`、`lost_attempt_on_shutdown`、`delete_touches_outputs`、`test_regression` → 不完成。

## Downstream Contract
→ image-session-pane reads：`/api/image-sessions` 各端点响应结构、`start_image_job` 的 `session_id` 参数、尝试的 status 枚举。
→ image-session-verify reads：同上，以及 harness 对图片会话的支持方式。

## Integration Points
← image-session-design 产出 API 契约 → 本节点实现后，`image-session-pane` 只通过 `desk/static/js/api.js` 消费；契约有任何偏离必须写回报告的 `contract_gaps`，不能只改代码。


## Freshness registration rule（2026-09-24 诊断后追加）
执行中额外读取的文件，只有在它**不属于任何下游节点的 `parallel_write_scopes`** 时，才可以用 freshness `read` 登记。下游会改写的文件只能读，读过的记进报告，不能登记——登记它们会让下游一交付就把本节点判为过期（inverted_source_inputs）。本 run 的 image-session-design 就是这样出的故障。

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
