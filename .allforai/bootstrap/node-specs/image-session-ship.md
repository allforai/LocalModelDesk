---
{"node_id": "image-session-ship", "capability": "launch-prep", "goal": "验收通过后重建用户日常使用的 dist/LocalModelDesk.app 并重新启动，冒烟确认图片会话在正式 app 里可用", "exit_artifacts": [{"path": ".allforai/image-sessions/ship-report.json", "validation_commands": ["python3 -c \"import json; d=json.load(open('.allforai/image-sessions/ship-report.json')); assert d.get('status')=='passed', d.get('status')\"", "codesign --verify --deep --strict dist/LocalModelDesk.app"]}], "responsibilities": ["implementation", "verification"], "source_inputs": ["desk/**", "macos/**", "packaging/**", "scripts/build-app.sh", "scripts/sign-app.sh"], "parallel_write_scopes": ["dist/LocalModelDesk.app/**"], "knowledge_refs": ["knowledge/capabilities/launch-prep.md", "knowledge/verification-protocol.md"], "consumers": [], "hard_blocked_by": ["image-session-design", "image-session-verify", "image-session-repair"], "alignment_refs": [], "unlocks": [], "human_gate": false, "discipline_owner": null, "decision_mode": "none", "input_dependencies": [".allforai/verify/image-sessions-verify.json", ".allforai/image-sessions/repair-report.json"], "node_spec_path": ".allforai/bootstrap/node-specs/image-session-ship.md", "profile_slice": {"tech_stacks": ["python backend desk/", "vanilla JS frontend desk/static/"], "test_commands": {"backend": "python3 -m pytest tests --ignore=tests/e2e -q", "frontend": "node --test tests/js/", "e2e": "python3 -m pytest tests/e2e -q"}}, "closure_verify": [], "requirement_refs": [{"path": ".allforai/bootstrap/local-requirements.json", "id": "image-sessions", "revision": 1}], "decision_inputs": [".allforai/bootstrap/local-requirements.json"], "product_goals": ["图片页像聊天一样有会话列表；一个会话是围绕同一想法的一串生成尝试，用户不满意时可以调整后继续生成，之前的尝试都留在会话里"], "acceptance": ["连续三轮「生成 → 在这张基础上改 → 再生成」后，三张图及各自参数都在同一个会话里按顺序显示", "「在这张基础上改」生成的新图与原图种子相同；「换个构图」生成的新图提示词相同而种子不同", "重启 app 后会话列表、每个会话的尝试和图片都还在", "切到另一个会话再切回，内容不变；新建会话后生成的图只进新会话", "删除会话后会话从列表消失，其中的图片仍能在素材库打开", "失败或取消的尝试在会话里可见并显示原因，不会留下一张空白图", "在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误"]}
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
- Primary outcome：用户常用的 `dist/LocalModelDesk.app` 换成含图片会话的新构建，以相同签名身份签名，重新启动后图片会话可用。用户在 2026-09-24 选择「验收通过后自动重建」。
- Non-goals：不改任何源码；不改签名身份；不安装到 /Applications（不运行 install-app.sh）；不清理用户数据目录。
- Must-read inputs：`.allforai/verify/image-sessions-verify.json` 为 passed，且 `.allforai/image-sessions/repair-report.json` 存在（否则 blocked，不重建）；`codesign -dv dist/LocalModelDesk.app` 的 TeamIdentifier（当前 B49F324XWZ）。
- Optional inputs：`scripts/build-app.sh --help`、`scripts/sign-app.sh`。
- Context budget：构建/签名脚本与 macos/ServerController.swift 的退出路径；按需扩展并记录。
- Quality questions：
  1. 退出正在运行的 app 时，会不会打断用户正在进行的生成或聊天？
  2. 新 bundle 的签名身份与旧的一致吗（否则钥匙串/权限提示会变）？
  3. 重启后用的是用户原来的数据目录，已有聊天会话、配置、素材都还在吗？
- Stop conditions：
  - 运行中的 app 有进行中的媒体作业或聊天流（查询它的服务端口 `/api/desk-state` 之类的状态接口）→ 每 60 秒复查，最多 30 分钟，仍忙 → `BLOCKED_ENV`「用户正在使用」，不强退。
  - 找不到与 TeamIdentifier 匹配的签名身份（`security find-identity -v -p codesigning`）→ `BLOCKED_ENV`，不降级为 ad-hoc 覆盖用户的 app。
  - 构建失败 → 旧 bundle 必须原样保留（build-app.sh 先在 staging 构建）；报告失败，不删除旧 app。
- Repair targets：`environment_blockers`、`code_gaps`（仅报告，不修源码）。

## Theory Anchors
- 发布即可回退：先构建成功再替换，失败时旧版本原样可用（launch-prep.md）。

## Knowledge References
- `${CLAUDE_PLUGIN_ROOT}/knowledge/verification-protocol.md#the-one-rule`：「已重建」需要真实证据：新 bundle 的构建时间/签名、重启后进程 pid 变化、正式 app 服务对 `/api/image-sessions` 的真实响应。
- 项目 memory（cross-exam-prober-hygiene）：同 bundle 双开会互相误杀；System Events 按名称寻址会找错实例。退出与激活一律按 pid 经 `NSRunningApplication`（JXA）进行，并先确认验收节点的临时 bundle 实例都已停止。

## Guidance
1. 确认验收用的临时 bundle 进程已全部退出（按 `<scratchpad>/verify-bundle` 路径查 pid）。
2. 记录当前 dist 实例 pid；检查它是否空闲（见 Stop conditions）。
3. 先构建：`bash scripts/build-app.sh --identity "<与 TeamIdentifier 匹配的身份>"`，输出到默认 `dist`（脚本先在 staging 构建再替换）。
4. 空闲时按 pid 优雅退出旧实例（JXA `NSRunningApplication.runningApplicationWithProcessIdentifier(pid).terminate()`），确认它的 python 服务进程也已退出；如果构建步骤要求先退出才能替换，则调换 3、4 的顺序，但仍须保证构建失败时旧 bundle 保留。
5. `open dist/LocalModelDesk.app`，等待服务就绪；用 capture_evidence 采集对 `/api/image-sessions` 的真实请求与响应；把窗口激活到前台后截一张图片页的图。
6. 写 `ship-report.json`：`status`、旧/新 pid、`codesign -dv` 输出摘要、构建时间、证据路径。

## User-visible decisions
Not applicable — no end-user surface（只重建与重启，不改界面）

## Exit Artifacts
- `.allforai/image-sessions/ship-report.json`：`status` 仅在新 app 已启动且真实请求成功时为 `passed`。

## Effect Verification
- `real-run`：构建命令输出（capture_evidence）；`real-api`：新实例对 `/api/image-sessions` 的响应，served_by `{host: 127.0.0.1, process: dist/LocalModelDesk.app 新 pid, mock_layers: []}`；`screenshot`：正式 app 图片页。

## Quality Acceptance
- 签名 TeamIdentifier 与重建前一致；重启后原有聊天会话数量不变（重建前后各查一次 `/api/sessions` 计数）。
- 失败码：`interrupted_user_work`、`signature_changed`、`old_bundle_lost`、`service_not_ready` → 不完成。


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
