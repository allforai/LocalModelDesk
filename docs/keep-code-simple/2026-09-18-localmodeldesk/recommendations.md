# Keep code simple — 本地模型台（LocalModelDesk 全库）

## 范围与证据限制

- **repo/cwd**：`/Users/aa/LocalModelDesk`，分支 `main`。
- **版本漂移（重要）**：调查起点 `ae6c17a7e591eae41141e6f7f021ae92f03ceede`（工作区有 6 个未提交文件）。调查期间 `71ba54a feat(chat): 压缩的三块纯逻辑` 与 `250fb63 feat(chat): 在两轮之间压缩，失败时一个字都不写` 落地，工作区变干净，**报告以 `250fb63c81dd60996de92618316f9769f99bb68a` 为准**。漂移影响一条建议：`maybeCompact` 已由 `desk/static/js/panes/chat.js:496` 接线（S9 的"尚未通电"前提已失效，建议正文已按新状态写）。
- **调查时间**：2026-09-18（JST）。
- **需求来源**（引用时区分「明确承诺 / 代码现状 / 推断」）：
  - `README.md`「必须能做到」清单（本机对话、文生视频、文生歌曲、同一时刻只干一件重活、模型齐不齐一眼能看出来、成品不丢能再做一版、安装与卸载）——明确承诺。
  - `docs/superpowers/specs/2026-08-31-*-spec.md` / `-design.md`（foundation/resources/arbiter/llm/gateway/media/library/ui/e2e/shell/packaging）与 `2026-09-17-budget-spec.md` / `-design.md`——R-* 编号需求。
  - `docs/adr/0001-deepseek-v4-not-yet.md`——已决定（暂不收录 DeepSeek V4）。
  - `docs/superpowers/plans/*.md`——实现计划与历史（用于「为何存在」）。
  - `docs/cross-exam/*/completion-report.md`——历次完成度审查结论（作为有出处的输入，**不是本次已验证的事实**）。
  - **已确认取舍，不作为缺陷**：`0.0.0.0` 无鉴权（app-overview Phase 0，人类已确认并写入 README）、不做公证、前端零构建链（R-ui-01）、`desk/testing/` 随包分发为数 KB 无害（e2e-design §1.3 A1）。
- **分区覆盖**：
  - 已深入：`desk/llm`、`desk/gateway`、`desk/app.py`、`desk/runtime.py`、`desk/ui.py`；`desk/arbiter`、`desk/budget`、`desk/media`；`desk/resources`、`desk/library`、`desk/foundation`；`desk/static`（含上下文压缩 WIP）；`desk/testing` + `tests/`（抽样）；`macos/`、`scripts/`、`packaging/`。
  - 仅枚举：`tests/` 全部 142 个文件的逐行阅读（按重复模式抽样 14 个文件）；`tests/js/` 32 份（读了 store/main_hash/media_panes/compaction/summary_prompt/chat_stream 相关片段）；`tests/e2e/`（只作为调用方出现）。
  - 未查：`desk/static/app.css`、`docs/visual/` 正文、`docs/cross-exam/` 报告正文（只按分区 grep 相关裁决）；`arbiter-spec`/`media-spec` 正文（只读了与准入相关的段落）。
  - 排除范围：`dist/`、`.venv-desk/`、`.venv-music3/`、`llms/`、`minimax-h3/`、`minimax-music3/`、`outputs/`、`__pycache__`（`.gitignore` 已排除且未纳入版本控制）；`docs/` 只作需求来源，不审文案。
- **本次是静态审查**：未运行被审查项目的任何代码、测试、构建、安装脚本、迁移、业务请求或媒体作业；未安装依赖；未修改任何源码；未访问外部一手资料（无网络检索，故不引用记忆中的第三方 API）。
- **派发记录**（`requested` 来自本会话注册表，`resolved` 来自宿主 workflow receipt 元数据）：

| 任务 | 范围 | 角色 | requested | resolved | run | 状态 |
|---|---|---|---|---|---|---|
| p1-chat-gateway（首次） | desk/llm、gateway、app/runtime/ui | oracle | `openai-codex/gpt-5.6-sol` | `openai-codex/gpt-5.6-sol:high` | `7f33f7b1` | 失败：`Codex error: The usage limit has been reached` |
| p2-arbiter-budget-media | desk/arbiter、budget、media | oracle | `openrouter/anthropic/claude-opus-4.8` | `openrouter/anthropic/claude-opus-4.8:high` | `2ea62aaa` | 完成 |
| p3-resources-library-foundation（首次） | desk/resources、library、foundation | oracle | `openai-codex/gpt-5.6-terra` | `openai-codex/gpt-5.6-terra:high` | `d577c4e7` | 失败：同上配额错误 |
| p4-frontend-js | desk/static | oracle | `openrouter/deepseek/deepseek-v4-pro-0813` | `openrouter/deepseek/deepseek-v4-pro-0813:high` | `f6d80410` | 完成 |
| p5-tests-harness（首次） | tests/、desk/testing | oracle | `openai-codex/gpt-5.5` | `openai-codex/gpt-5.5:high` | `9310991f` | 失败：同上配额错误 |
| p6-shell-packaging | macos/、scripts/、packaging | oracle | `openrouter/anthropic/claude-opus-4.6` | `openrouter/anthropic/claude-opus-4.6:high` | `80548a1b` | 完成 |
| v2-frontend-tests-shell | 复核 p4/p5/p6 | reviewer | `openai-codex/gpt-6-astra` | `openai-codex/gpt-6-astra:high` | `e34ef26b` | 失败：同上配额错误 |
| v1-python-core | 复核 p1/p2/p3 | reviewer | `openrouter/anthropic/claude-opus-5` | `openrouter/anthropic/claude-opus-5:high` | `f36904be` | 完成（实际只复核到 p2，p1/p3 无报告） |
| 重跑 p1 | 同首次 | oracle | `openrouter/google/gemini-2.5-pro` | `openrouter/google/gemini-2.5-pro:high` | `d3d361f2` | 完成 |
| 重跑 p3 | 同首次 | oracle | `openrouter/anthropic/claude-opus-4.7` | `openrouter/anthropic/claude-opus-4.7:high` | `f3909260` | 完成 |
| 重跑 p5 | 同首次 | oracle | `openrouter/deepseek/deepseek-v4-pro` | `openrouter/deepseek/deepseek-v4-pro:high` | `9078d254` | 完成 |
| v3-recovery | 复核重跑的三条 | reviewer | `openrouter/anthropic/claude-opus-4.8` | `openrouter/anthropic/claude-opus-4.8:high` | `222a6fcc` | 完成 |

  - 工作流：`6dc1d55c-940f-4ea4-ac3f-fa74c8076730`（首轮 3 并发，`globalConcurrencyLimit:3`）、`b8f3fc07-a5d7-4636-880e-81f7933b9420`（同协议重试，3 并发上限，实际按 2 并发以连同 v1 不超 3）。两次派发均为 `context:"fresh"`、`cwd:/Users/aa/LocalModelDesk`、只读工具（read/grep/find/ls/bash，协议要求不执行）。subagent 子进程输出由宿主保留在会话 artifact 目录，未写入本仓库。
  - **失败与重试说明**：4 条通道因 `openai-codex` 订阅额度耗尽失败（与工作流本身无关）。按协议「已启动的派发失败不是自动换模式的许可」，未切换 CLI / 前台 / 其他执行协议，只做**同协议重试**并把模型路由改为 openrouter 系列。
  - **非独立限制**：调查员与复核者都是同一模型的静态阅读，不是独立第三方验证。v1/v3 的会话**没有 git 工具**，其引用的 commit/blame 结论一律标注「无法核对」，本报告中所有 git 结论均由主会话用 `git log/blame/-S` 亲自核对。
  - **主会话亲验清单**（不依赖二手摘要）：`llm/service.py:43,65` 双定义与 blame；9 处原子写/SSE/门控调用点；`arbiter/core.py:8-25,111-135,154-161,235-287`；`budget/budget.py:51-64,136-146,175-176`；`budget/estimate.py:16-51`；`arbiter/memory.py:18-23`；`media/service.py:140-175`；`resources/downloader.py:65-68`；`runtime.py:160-200`；`library/sessions.py:23-39,89-101`；`library/__init__.py:18-48`；`library/http.py:132-144`；前端 `store.js`、`tab_hash.js`、`desk_state.js`、`statusbar.js`、`main.js:19,77,90,118`、`chat.js:496`；`build-app.sh:34,49,54-135`、`verify-app.sh:92,107`、`install-app.sh:45`、`Info.plist.template:8`、`DeskPaths.swift:18`；`tests/media_fakes.py:75`、`tests/llm/llm_fakes.py:193`。另有两次 stdlib 语义核对（`pathlib` glob 是否匹配隐藏文件；`list.get` 不存在），在 `/tmp` 空目录执行，不涉及被审查项目代码。

---

## 建议

排序按「收益 × 影响」，同类已合并。所有行数/文件数为**未实测估算**。

### S1 — 删除 `desk/llm/service.py` 中重复的 `_read_model_config`，保留带类型守卫的那一份，并补一条非 dict config 的回归测试

- **类型**：实现等价 + 修一处未加防护的分支；依据：**已查证**（主会话 + p1 调查 + v3 复核 CONFIRM）
- **现状与证据**：同名函数定义两次。`desk/llm/service.py:43-54`（英文 docstring，`return data if isinstance(data, dict) else {}`）与 `desk/llm/service.py:65-70`（中文 docstring，无守卫）。Python 自上而下执行，**生效的是 65 行这份**。
  ```python
  # 43（被遮蔽）
  return data if isinstance(data, dict) else {}
  # 65（生效）
  return json.loads((Path(model_dir) / "config.json").read_text(encoding="utf-8"))
  ```
  下游：`desk/llm/service.py:179`（`acquire_heavy(params={"config": …})`，该路径有 `config or {}` 兜底）与 `:239-240`（`self._budget.launch_args(entry.key, _read_model_config(model_dir), entry.gb)`，**无兜底**）→ `desk/budget/budget.py:175-176` → `_per_token` → `desk/budget/estimate.py:16` `_text_scope` 的 `config.get(...)`。`json.loads("[]")` 得到 `list`，`.get` 不存在 → `AttributeError`。
- **为何存在**：`43` 行由 `f707089`（feat(llm): 起 mlx-lm 时传限额）引入，`65` 行由 `6ce32a1`（feat(budget): Task 9 接线）在同一天引入，后者覆盖前者；两份内容与 docstring 语言都不同，属两次会话各写一份、未发现已存在。
- **推荐方案**：删除 `:65-70`（连同其上多余空行），保留 `:43-54`。无需新依赖。
- **商业功能**：保留读取 `config.json` 供预算与准入使用的能力；变化是「合法但非 dict 的 config.json」不再穿透到预算估算。商业功能只增不减。
- **净收益与代价**：触及 1 文件、净减约 6 行；**完全机械**（删一段）。无迁移。
- **数据/资金/安全**：删掉的是无防护的那份，方向是加固。已核实 `desk/budget/budget.py:141` 的 `config or {}` 只保护 `cost()` 路径，`launch_args` 路径没有保护，所以这不是纯风格问题。
- **验证方法**：新增一条测试：模型目录写入 `config.json` 内容 `"[]"`，走 `LlmService.load()`，断言不抛 `AttributeError` 且状态收敛（当前会崩，见 F6 的失败终态）。本次未执行。
- **关联**：与 F6 同一根因，建议把 S1 与 F6 的失败终态一起处理。

### S2 — 把 4 处 `tempfile + os.replace` 原子写收敛为一个公共 helper，统一采用**不带 `.json` 后缀**的临时名，并给缺 fsync 的两处补上

- **类型**：实现等价（统一保留最强语义）；依据：**已查证**（主会话 + p3 调查 + v3 复核 CONFIRM，并修正了 p3 的一处安全叙述）
- **现状与证据**：骨架相同、差异只有 payload 类型 / 临时名 / 是否 fsync。
  | 位置 | payload | 临时名 | fsync |
  |---|---|---|---|
  | `desk/foundation/config.py:187-201` `_atomic_write` | dict→json | `{name}.tmp-{pid}-{rand}` | 有（flush+fsync） |
  | `desk/resources/manifest.py:118-138` `_write_cache` | dict→json | `mkstemp(prefix=name, suffix=".tmp")` | 有 |
  | `desk/library/sessions.py:89-101` `_write` | dict→json | `mkstemp(prefix=".tmp-", **suffix=".json"**)` | **无** |
  | `desk/library/__init__.py:49-66` `_adopt_legacy_history` | bytes | `mkstemp(prefix=".tmp-history-")` | **无** |
- **为何存在**：四处分别来自 `T-foundation-03`(`8db8af0`)、`T-resources-03`(`4374d91`)、`T-library-08`(`ca29f3a`)、`T-library-09`(`3fd4fb6`)；`git log -S "os.fsync"` 只有前两处落地过 fsync，**未能确定** library 侧为何没跟进（无提交讨论）。
- **推荐方案**：在 `desk/foundation/`（`paths.py` 已是路径与运行时唯一真相源）新增 `atomic_write_bytes(path, data)` 与 `atomic_write_json(path, obj, *, indent=None)`，四处改调；统一 `flush + fsync`，临时名**不含 `.json` 后缀**。
- **商业功能**：保留「读者永远看到旧文件或新文件、崩溃后旧文件仍在」。变化（加固）：sessions 与 legacy 拷贝获得 fsync。副作用是修掉 F5。
- **净收益与代价**：触及 4 个调用点 + 1 个新 helper，净减约 40 行样板；机械替换为主，唯一人工判断是临时名与 fsync 默认值。测试成本：`tests/test_foundation_config.py`、`tests/test_resources_manifest.py`、`tests/test_library_sessions.py`、`tests/test_library_history.py` 断言的是功能而非实现细节，预期不动；本次未跑。
- **数据/资金/安全**：`os.replace` 只保证目录项切换原子性，**不得借统一之名删掉既有两处的 `flush+fsync`**。给 sessions 补 fsync 属加固（崩溃回滚窗口变小），不改任何用户可见语义。
- **验证方法**：① 任意工况下 `.tmp*` 残留为 0；② monkeypatch `os.replace` 抛错 → 临时文件被清理且原文件不变；③ monkeypatch `os.fsync` → 四处都必须被调用（sessions 也要）；④ 目录里放 `.tmp-x.json` 时 `SessionStore.list()` 不再返回它。本次未执行。
- **关联**：与 F5 同源；与 S3/S5 都改 library 的 import 面，可合批但独立成立。

### S3 — 删除 `LibraryService` 的 8 个一行转发方法，统一为直穿 store

- **类型**：实现等价；依据：**已查证**（p3 调查 + v3 复核 CONFIRM；主会话已核对代码形态）
- **现状与证据**：`desk/library/__init__.py:22-45` 有 8 个一行代理（`append_history/list_history/list_outputs/serve_output/list_chat_sessions/create_chat_session/update_chat_session/delete_chat_session`），全部转发 `self.history / self.outputs / self.sessions`。同一个消费方文件已自己打破这层抽象：`desk/library/http.py:80,84,103,107,116,123,129` 走包装，而 `:88,:93` 直接 `service.outputs.reveal(...)`（因为 facade 没包装它）。
- **为何存在**：`3fd4fb6 T-library-09` 落地时即如此，**未能确定**为何选包装（推测想隐藏 store 结构）。无 commit 说明。
- **推荐方案**：删 8 个方法，调用点改为 `service.history.append` / `service.outputs.list` / `service.sessions.list()` 等。
- **商业功能**：完全保留（仅调用形态变化）。
- **净收益与代价**：触及 `library/__init__.py`（−25 行）、`library/http.py`（7 处）、`runtime.py:192` 与 `desk/testing/harness.py:302`（`library.append_history` → `library.history.append`）、e2e 与单测约 6-10 处方法名（`harness.library.list_chat_sessions()` → `.sessions.list()`）。**可机械**（sed/AST 重写），机械部分与人工判断不混：唯一人工项是确认没有外部（macos/脚本）以字符串方式调用这些名字。
- **数据/资金/安全**：不适用，无副作用变化。
- **验证方法**：`tests/test_library_*.py` 与 `tests/e2e/test_*.py` 全绿。本次未执行。
- **关联**：与 S2、S5 同改 library；独立成立。

### S4 — 合并 3 处相同的 `data:` SSE 帧构造（Anthropic 的事件帧保持独立）

- **类型**：实现等价；依据：**已查证**（p1 调查 + 主会话核对三处文本）
- **现状与证据**：三处逐字相同 `b"data: " + json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n\n"`：`desk/gateway/openai_dialect.py:112` `_frame`、`desk/app.py:126`（内联）、`desk/testing/harness.py:327`（内联）。第四处 `desk/gateway/anthropic_dialect.py:108` 是 `f"event: {name}\ndata: ...\n\n"`，**形态不同，不合并**。
- **为何存在**：**未能确定**（三处由不同任务各自实现，无共享先例）。
- **推荐方案**：在 `desk/foundation/` 放一个 `sse_data_frame(payload) -> bytes`，三处改调；Anthropic 保留自己的 `_frame`。
- **商业功能**：保留 OpenAI 兼容流式、app 内 SSE、e2e 夹具的 SSE 行为，逐字不变。
- **净收益与代价**：触及 4 文件、净减约 10-15 行；机械替换。
- **数据/资金/安全**：不适用（纯字节构造）。
- **验证方法**：`tests/test_gateway_openai.py`、`tests/js`（无关）、`tests/e2e/test_chat_stream.py` 绿；本次未执行。
- **关联**：无。

### S5 — 统一三个子系统的 HTTP 错误信封（条件：先核对前端消费方）

- **类型**：实现等价 + 输出契约收紧（覆盖取舍）；依据：**条件性**（v3 明确「前端消费未核对」，不得当作已查证）
- **现状与证据**：`desk/app.py:99-101` 只对 `FoundationError` 做顶层包装成 `{"error":{"code","message",...}}`；`desk/resources/errors.py:4-19` 的 `ResourceError` 不继承它，于是在 `desk/resources/http.py:15-22` 用 `@_guarded` 给 8 个 handler 逐个贴装饰器（`:30,34,42,47,51,55,59,64`）；`desk/library/errors.py` 全文没有 `code/http_status`，`desk/library/http.py:132-144` 手工映射，且**同一函数产出两种 shape**：
  ```python
  except OutputsRootMissingError as exc: return _json_response(404, {"error": {"code": exc.code, "message": str(exc)}})
  except NotFoundError as exc:          return _json_response(404, {"error": str(exc)})   # 扁平
  except ValidationError as exc:        return _json_response(400, {"error": str(exc)})   # 扁平
  ```
  `tests/test_library_http.py` 一批用例断言扁平形态，另一批断言对象形态。
- **为何存在**：foundation 最早成形（`8db8af0 T-foundation-03`），resources/library 后续各自设计错误处理；**未能确定**为何不复用顶层捕获（推断是模块发展节奏差，非刻意隔离）。`desk/library/http.py:9-25` 声称把两个错误类放这里是为避开 `errors.py ↔ outputs.py` 循环，p3 质疑该环不存在，v3 判定**该质疑本身未经充分核对，降为待验证**——不要基于这句话去搬到 `errors.py`。
- **推荐方案**：让 `ResourceError` / `LibraryError` 挂到共同基类（`FoundationError` 或改名后的 `ApiError`），app.py 的顶层捕获直接接住三边；删 `_guarded` 与 `dispatch`。前端同步收紧一次错误 shape。
- **商业功能**：保留每个错误的状态码与语义；变化：`{"error":"..."}` 扁平形态升级为 `{"error":{"code","message"}}`——**这是客户端可见变更**。
- **净收益与代价**：触及 `resources/http.py`、`library/http.py`、`library/errors.py`、`library/outputs.py`、`app.py` + 若干测试；净减约 50-80 行。机械替换与人工判断混合：shape 变更必须逐条核对断言与前端分支，不可机械批处理。
- **数据/资金/安全**：无写入路径变化；最坏后果是前端漏改时用户看到「未知错误」（可见事件，不静默丢数据）。
- **验证方法**：① 先把 `tests/test_library_http.py` 的扁平断言改为读 `["error"]["message"]` 作为回归门；② 新加「所有 4xx/5xx 都是对象 shape」的断言；③ 手工回归前端错误提示。本次未执行。
- **关联**：与 S2、S3 同改 library；独立成立。

### S6 — 删除两个已无生产消费者的前端残骸：`store.js` 与 `tabFromHash`

- **类型**：实现等价（死代码）；依据：**已查证**（p4 调查 + 主会话在 `250fb63` 上复核）
- **现状与证据**：
  - `desk/static/js/store.js:3-10` 只返回 `{ set }`，没有 `get/subscribe`。全库引用只有 `main.js:3`（import）、`main.js:19`（`createStore`）、`main.js:77`、`main.js:118`（两次 `store.set`）——**零读取方**；`activeTab` 由 `main.js` 自己的局部变量承担。`c996965`(F13) 删除 get/subscribe 时留下注释自承「目前只有 main.js 写入」。
  - `desk/static/js/pure/tab_hash.js:5-8` 的 `tabFromHash` 生产调用方为 0（只有 `:19` 的 `initialTab` 转发和 `tests/js/main_hash.test.js:6-8`）；`main.js:53,59` 两处都用 `initialTab`。`f67bf5d` 的提交信息说明当年导出它是为等 main.js 接线，现已接上。
- **为何存在**：`store.js` 源于 ui-design「store 供各 pane 订阅」的响应式设计，F13 已放弃该方向（删 API 留壳）；`tabFromHash` 是接线前的过渡导出。
- **推荐方案**：删 `store.js`、`tests/js/store.test.js`、`main.js` 的三处使用；删 `tabFromHash` 并把体内联进 `initialTab`，删 `main_hash.test.js` 前 3 条重复断言。
- **商业功能**：无变化（写进去的值无人读；两函数规则逐字相同）。
- **净收益与代价**：−3 文件、约 −25 行；全机械。依赖/迁移零。
- **数据/资金/安全**：不适用（纯内存与纯函数）。
- **验证方法**：JS 测试与 e2e 全绿。本次未执行。
- **关联**：**决策前提**：若仍打算实现「store 供 pane 订阅」，`store.js` 应改为真正接上订阅者而不是删除——这条前提需要你来定，见「用户选择」。

### S7 — `desk_state.js` 的 `holderText` 是被测试却无人消费的字段，媒体持有者文案因此重复一份

- **类型**：实现等价（对外显示文案逐字不变）；依据：**已查证**（p4 调查 + 主会话复核）
- **现状与证据**：`desk/static/js/pure/desk_state.js:38-43` 拼 `holderText`（前缀还不一致：llm/none 带「内存里：」，媒体不带），`:57` 把它放进返回值；但生产消费者为 0（只有 `tests/js/desk_state.test.js:23-25` 读它）。真正显示状态的是 `desk/static/js/widgets/statusbar.js:8` 自己那份 `MEDIA_HOLDER_LABEL = {video:"视频生成中", music:"音乐生成中"}` 与 `:18-24` 的本地 `holderName`（注释里正是解释为什么它不直接用 `holderText`）。
- **为何存在**：statusbar 注释（W4）说媒体持有者省前缀是为避免与右侧媒体状态重复陈述；desk_state 那段不对称是上一个用法的残留。
- **推荐方案**：`renderState` 只返回**不带前缀**的 `holderName`，删 `holderText`；`statusbar.js` 删 `MEDIA_HOLDER_LABEL` 与本地 `holderName`，统一由 statusbar 拼「内存里：+ view.holderName」。
- **商业功能**：状态条四段文案逐字不变。
- **净收益与代价**：触及 3 文件、约 −15 行；去重一组文案。需要人工过一遍状态条 tone/badge 逻辑，并改 `desk_state.test.js` 6 条断言（机械但要点数）。
- **数据/资金/安全**：不适用（纯展示）。
- **验证方法**：`tests/js/desk_state.test.js` + 状态条相关测试绿，且 UI 三段文案与现在一致。本次未执行。
- **关联**：无。

### S8 — `video.js` / `music.js` 的「内存不足 → 确认 → force 重试」逐字重复，抽共享函数并统一 `confirm` 签名

- **类型**：实现等价；依据：**已查证**（p4 调查，主会话未逐行复看该两段，标为二手但位置明确）
- **现状与证据**：`desk/static/js/panes/video.js:88-99` 与 `desk/static/js/panes/music.js:20-28` 是同一段逻辑（只差 `startVideoJob` / `startMusicJob`）：先 start → 捕获 `error.code === "insufficient_memory"` → `confirm` → `{...params, force:true}` 重试。`git log -S insufficient_memory -- panes/video.js panes/music.js` → 单提交 `3f2f059`(G23 J2) 一次性把两处写进去。附带发现：`ctx.confirm` 有**两套签名**（chat/settings/prompt_assist 用 `confirm(options)`，video/music 用 `confirm(doc, options)`），测试里的 `async () => true` 掩盖了差异。
- **为何存在**：同一功能的两次实现，非刻意。
- **推荐方案**：widgets 下新增 `submitWithMemoryForce({ start, params, doc, confirm })`，两处调用；`confirm` 签名统一为 `(options)` 并让 doc 走闭包（与多数 pane 一致）。
- **商业功能**：保留「内存不足时弹窗 + 仍要生成 → force 重试」，语义零变化。
- **净收益与代价**：−2 处 12 行 → +1 处 12 行 helper，净约 −12 行 + 去漂移；可脚本化改两个调用点。测试成本：`tests/js/media_panes.test.js` 的 insufficient_memory 用例。
- **数据/资金/安全**：不新增副作用；前端不改后端幂等/预检契约（媒体作业的扣费与终态在服务端）。
- **验证方法**：改后 `media_panes.test.js` 正常路径与 insufficient_memory 用例绿。本次未执行。
- **关联**：与 S10 同属前端分层批次，可合批。

### S9 — 把 `maybeCompact` 从 `pure/` 移到 `panes/`；删掉无消费者的 `created_at`

- **类型**：实现等价（分层一致性）；依据：**已查证**（p4 调查 + 主会话在漂移后的 HEAD 复核）
- **现状与证据**：`desk/static/js/pure/compaction.js:65` 的 `maybeCompact` 是 `async`，内部 `await summarise(head)`（生产注入的 `api.chatStream`，即 fetch）并在 `:89` 附近写入 `created_at: new Date().toISOString()`。而 `docs/superpowers/specs/2026-08-31-ui-design.md` 第 41 行写明 `pure/` =「零 DOM、零 fetch、零计时器」，第 60 行「pane/widget 只做取数→调纯函数→写 DOM」。`created_at` 全库无读取方（只有构造处）。**版本漂移提示**：`maybeCompact` 现已被 `desk/static/js/panes/chat.js:496` 接线（提交 `250fb63`），所以这项已不再是「未通电时纠偏」，而是一次搬迁。
- **为何存在**：计划 `docs/superpowers/plans/2026-09-18-context-compaction.md` Task 4 显式要求把编排放在 `compaction.js`；`created_at` 是计划里预留但无人读的字段。
- **推荐方案**：`maybeCompact` 整段移到 `panes/chat.js`（或新 `panes/chat_compaction.js`），`created_at` 改为调用方传入或删除；`pure/compaction.js` 只留 `charsPerToken/needsCompaction/splitForCompaction`。
- **商业功能**：不改功能。**必须原样保留** `maybeCompact` 的失败路径：`summarise` 抛错或返回空串 → `{compacted:false, messages: 原数组}`、一个字都不写（`250fb63` 的提交信息把这称为最要紧的一条：否则会留下「老消息已标替代、摘要却没生成」的静默上下文丢失）。
- **净收益与代价**：约 40 行挪位、1-2 文件；机械搬运 + 一个人工决定（新落点文件名）。测试 `tests/js/compaction.test.js`、`tests/js/chat_compaction_flow.test.js` 的 import 路径需同步。
- **数据/资金/安全**：不新增副作用；落盘仍走既有 `updateChatSession`。删 `created_at` 前已确认无读取方，属安全。
- **验证方法**：`pure/compaction.js` 在 node 下不再依赖 `Date`/`fetch`；`chat_compaction_flow.test.js` 7 条仍绿；手工跑一次真实压缩确认失败路径。本次未执行。
- **关联**：与 S8 同批。

### S10 — 让 `Downloader._sample` 复用 `verify_tree`（**覆盖取舍**：进度口径会变，不是纯等价）

- **类型**：覆盖取舍；依据：**条件性**（p3 调查 + v3 复核 PARTIAL，并修正了 p3 的「实现等价」暗示）
- **现状与证据**：`desk/resources/verify.py:52-104` 的 `verify_tree` 已做全套（逐文件比 size、`part_bytes` 累加、把 `.cache/huggingface/download/*.incomplete` 按 `active_since` 拆成 fresh/stale）；`desk/resources/downloader.py:169-207` 的 `_sample` 又遍历一次 `manifest.files`，并把**所有** `.incomplete` 字节都算成 `stale_bytes`。两条路径的 `stale_bytes` 口径不同 → 同一时刻 UI 从 `progress.stale_bytes` 与 `/api/resources/status` 读到的数不一样（既有不一致）。
- **为何存在**：`_sample` 与 `verify_tree` 分属 `T-resources-04` 与 `T-resources-03`，各自演进；**未能确定**为何不回填。
- **推荐方案**：`_sample` 改为 `status = verify_tree(model, manifest, roots.models_root, active_since=self._attempt_wall)`，再从 `status` 组装 `done`/`current_file`/速率/ETA（`current_file` 仍需一次 mtime 扫描或从 `status.gaps` 取）。
- **商业功能**：保留进度百分比、速率、ETA、`current_file`、`stale_bytes` 展示。**减少/改变的行为**：`stale_bytes` 从「所有 incomplete」变为「非当前 attempt 的 incomplete」，**下载中这个数字会明显变小**；且若按 v3 的提示把 `bytes_in_flight` 计入 `done`，**百分比与 ETA 也会变**。受影响场景：下载中同时看 stale 数字的用户（用量未知）。
- **净收益与代价**：`downloader.py` 主体缩到约 15 行，净减约 20 行；需人工核对 `tests/test_resources_downloader.py` 的进度断言口径（未逐条核对）。锁：`_sample` 持 `RLock`，`verify_tree` 是无锁纯函数，安全，但 `active_since` 要在锁内取快照。
- **数据/资金/安全**：只读遍历，无副作用。
- **验证方法**：新断言「下载中 `verify_model(key)` 与 `download_progress()` 的 `bytes_in_flight + stale_bytes` 相等」；保留现有百分比与终态断言；手工回归下载页。本次未执行。
- **关联**：无。

### S11 — 收敛 «同一时刻只干一件重活» 的两套准入实现（**条件性，且顺序有依赖**）

- **类型**：覆盖取舍；依据：**条件性**（p2 调查 + v1 复核 PARTIAL，v1 修正了顺序与改写面）
- **现状与证据**：`desk/arbiter/core.py:83-101 _legacy_decision` + `:146-152 _replace_all` + `acquire_heavy` 的 `evict_then_grant` 分支是一套约 40 行的种类硬编码规则表（legacy，`budget=None`）；`desk/arbiter/state.py:47-75 plan_acquire` + `desk/budget/budget.py:51-105 fits/plan` 是另一套（budget）。生产 `desk/runtime.py:180` 走 budget；而**集成/e2e 夹具 `desk/testing/harness.py:274-276` 用 `Arbiter(0, memory=..., reaper=..., clock=...)`（无 budget）→ 全量走 legacy**，`tests/test_arbiter_core.py` 前 311 行专测 legacy。也就是说集成测试测的是与生产不同的一条判定路径（保真缺口）。其它读取点（`gateway/guard.py:19`、`llm/service.py:427`、`llm/service.py:343`）都只是消费 `desk_state()`，**不构成第三套**（已核实）。
- **为何存在**：`9fc578e`(R-arbiter-01 重写) 故意把种类硬编码从纯状态机删掉、改由预算判定，同时把旧规则表留在 `core.py` 作私有兜底（docstring 自述「不是近似，就是旧行为」），以便尚未接预算的调用方/测试仍可用。
- **推荐方案**：① 先修 F1/F2（`can_start_heavy` 的无参语义），② 再让 `harness.py` 构造注入式 Budget（budget 的纯函数本就为「不起服务、不装模型」设计），③ 最后删 `_legacy_decision`/`_replace_all` 与 `evict_then_grant` 分支。
- **商业功能**：生产行为不变（生产只走 budget）。改变的是测试保真度与代码量。
- **净收益与代价**：删约 40 行平行逻辑 + core.py 的双模式分支。代价是改写 `desk/testing/harness.py` 与 `tests/test_arbiter_core.py:1-311`（含 `estimated_bytes` 告警用例、`can_start_heavy` 的 `estimated_bytes` 形参本身）、以及前端 `desk_state.js:5-11` 里 `media_busy`/`llm_already_held`/`evict_failed` 三条在生产变为不可达的文案与 `main.js:90` 的特例分支。**非机械**：需确认 `transition_in_progress`/`evict_failed` 对外契约（尤其 gateway 503 code 列表）是否一并收敛，`resources-design.md:429-431` 仍把它们当合法透传原因。
- **数据/资金/安全**：合并本身不改生产判定。风险在测试改写期间遗漏 legacy 段覆盖的边界；`reap_llm_port`/`llm_port_listeners`（`core.py:219-226`）由 `llm/service.py:207,222,382` 独立使用，删 legacy 不影响收割能力（已核实）。
- **验证方法**：迁移后跑 arbiter 单测 + 集成套件，确认覆盖等价；特别确认「媒体在跑且预算够时 `can_start_heavy("llm")` 为 ok」这条计划要求（`docs/superpowers/plans/2026-09-17-budget-subsystem.md:1417`）在新路径下真的成立。本次未执行。
- **关联**：**依赖 F1/F2 先修**；与 S15（注释）联动。

### S12 — `desk/llm/backend.py` 换用已装的 `httpx`（**收益被高估**，评估后不建议现在做）

- **类型**：实现等价（需逐条保住失败语义）；依据：**条件性**（p1 建议 + v3 复核 PARTIAL）
- **现状与证据**：`desk/llm/backend.py:100-138` 手写 `http.client` + `_iter_sse`，携带 5 类明确失败语义：`timeout=300.0`；`OSError → BackendHttpError("连接 mlx-lm 失败…")`；非 200 时读 2048 字节 → `BackendHttpError("上游状态码…")`；SSE 逐行解析、`[DONE]` 哨兵、跳过非 `data:` 行、坏 JSON 跳过；`finally: conn.close()`。`packaging/requirements-desk.txt` 有 `httpx==0.28.1`（p1 声明，v3 未核对该行，主会话未核对）。
- **为何存在**：**未能确定**（无提交讨论）。
- **推荐方案**：A 不做（推荐）/ B 重写但逐条保住上述 5 类语义并保留中文错误消息 / C 只替换非流式的 `health`/`chat`，保留 `_iter_sse` 手写。
- **商业功能**：保留与 mlx-lm 子进程的通信（健康检查、非流式、流式聊天）。
- **净收益与代价**：p1 估「删 30-40 行」偏乐观——**httpx 不原生解析 SSE**，`chat_stream` 仍需手写逐行/`[DONE]`/跳坏行逻辑，而且这是重写而非删除。属低优先。
- **数据/资金/安全**：仅本机 loopback 子进程通信，无资金/隐私面；但流式失败语义（缺 finish、连接断）关系到用户可见终态，重写必须逐条复刻。
- **验证方法**：`tests/llm/test_llm_backend_http.py`、`test_llm_chat_stream.py` 全绿 + 手工制造上游中断。本次未执行。
- **关联**：无。

### S13 — 删除/订正两处「生产未接线」的过期 docstring（并如实说明 legacy 的可达性）

- **类型**：实现等价（纯注释）；依据：**已查证**（p2 调查 + v1 复核 CONFIRM，并扩大了范围）
- **现状与证据**：
  - `desk/arbiter/core.py:8-16` 称「today that is every production call site: `desk/runtime.py` builds `Arbiter(DEFAULT_LLM_PORT)` with no budget」——被 `desk/runtime.py:180` (`Arbiter(DEFAULT_LLM_PORT, budget=budget)`) 直接反证。
  - `desk/media/service.py:46-51` 称三个校准参数「the production default today — … desk/runtime.py has not been updated」——被 `desk/runtime.py:189-197`（传 `measurements`/`measurements_path`/`available_bytes`）反证；`tests/test_budget_wiring_production.py` 有专门断言锁这两处接线。
  - **v1 补充的第二句假话**：`desk/arbiter/core.py:22-25` 称 budget 模式下「the caller learns the minimal release set from `can_start_heavy` and releases those tokens itself before retrying」。生产两个调用方都没做：`desk/media/service.py:152-155` 直接抛 `MediaError`、`desk/llm/service.py:178-187` 直接 `raise LlmRejected`，都不读 `release` 字段（`release` 的消费者只有 `core.py:266-272` 与 `tests/test_arbiter_core.py:368-370`）。
- **为何存在**：注释写于 `9fc578e`(Task 7)，`6ce32a1`(Task 9) 修好了它们描述的偏差却没回头改注释（git 已证先后顺序）。
- **推荐方案**：改这三处注释；同时把 legacy 段落如实标为「仅测试夹具可达」。
- **商业功能**：无变化。
- **净收益与代价**：2 文件、约 10-20 行注释；纯人工措辞。收益是消除会误导读者的错误陈述（**本轮审查差点被它带偏**）。
- **数据/资金/安全**：不适用。
- **验证方法**：改后与 `runtime.py` 实际接线逐句对照。本次未执行。
- **关联**：与 S11 联动（legacy 是否保留决定措辞）。

### S14 — 构建脚本与打包的 4 个小项（合并为一题）

- **类型**：实现等价 / 覆盖取舍（d 项）；依据：**已查证**（p6 调查 + 主会话逐条核对）
- **现状与证据**：
  - **a. `MIN_OS` 两份**：`packaging/Info.plist.template:26` 硬编码 `15.0`，`scripts/build-app.sh:34` 也硬编码 `MIN_OS="15.0"`（用于 `:46` 的 `-target arm64-apple-macos$MIN_OS`）。为何存在：`b62a206 T-packaging-06` 起初如此；plist 在步骤 5 才渲染，而编译在步骤 1，故当时无法从模板读。
  - **b. `python3.13` 11 处**：`scripts/build-app.sh` 8 处（`:54,68,69,77,82,87,127,135`）、`scripts/verify-app.sh` 2 处（`:92,107`）、`macos/DeskPaths.swift:18` 1 处；而 `packaging/python-version.txt` 已是版本真相源。
  - **c. bundle id 两份**：`packaging/Info.plist.template:8` 是真相源，`scripts/install-app.sh:45` 又硬编码 `com.aa.localmodeldesk`。（`uninstall-app.sh:6` 的硬编码是**合理**的：R-packaging-07 要求卸载能在没有仓库的机器上工作。）
  - **d. `desk/testing/` 随包分发**：`scripts/build-app.sh:49` 的 `rsync -a --exclude '__pycache__' --exclude '.pytest_cache' "$REPO/desk/" "$RES/desk/"` 无条件复制整个 `desk/`（含 902 行测试基建）；`verify-app.sh` 无对应检查。生产代码零 import（`tests/test_production_runtime.py` 有断言）。
- **推荐方案**：a 用 `PlistBuddy -c 'Print :LSMinimumSystemVersion'` 从模板读（该值无占位符，可直接解析）；b 从 `python-version.txt` 提取 minor 版本到 `PYMINOR`（Swift 侧若也要同步需生成常量文件，**这一步可能得不偿失**，可只做脚本侧）；c install-app.sh 从模板读，uninstall 保持；d 加 `--exclude 'testing'`。
- **商业功能**：a/b/c 保留全部构建与安装行为；d 保留全部测试能力，只让生产 `.app` 不再携带测试假件。README 逐个列出的 `scripts/*.sh` 入口都是对外承诺，**不改入口**。
- **净收益与代价**：a/b/c 各 1-2 行，可机械；d 单行 `rsync` 参数。b 的 Swift 侧若引入构建期常量生成，整体负担反而上升——建议只做脚本侧（把 11 处降到 2 处）。
- **数据/资金/安全**：不适用（构建期）。
- **验证方法**：`build-app.sh` + `verify-app.sh` 全绿；手工把 `python-version.txt` 改成假版本确认脚本报错；构建后确认 `dist/LocalModelDesk.app/Contents/Resources/desk/testing/` 不存在。本次未执行。
- **关联**：d 项**触碰已确认决定**（e2e-design §1.3 A1 明说随包分发无害），收益仅数 KB，属最低优先。

### S15 — 重命名 `gateway/errors.py` 里两个易混常量（**只改名安全；改值必须单列**）

- **类型**：实现等价（改名）；依据：**条件性**（p1 建议 + v3 复核 PARTIAL）
- **现状与证据**：`desk/gateway/errors.py:5-6` 同时存在 `REASON_NO_MODEL_LOADED = "no_model_loaded"` 与 `REASON_MODEL_NOT_LOADED = "model_not_loaded"`，在 `desk/gateway/guard.py` 用于两种不同拒绝（完全没有模型 vs 已加载但不匹配）。p1 称两者同由 `9bc3942b` 引入；**主会话未亲验该 blame**，标为调查员结论。
- **为何存在**：**未能确定**（p1 归因于初始设计，无提交说明）。
- **推荐方案**：A 只重命名 Python 常量（如 `REASON_SERVICE_IDLE` / `REASON_MODEL_MISMATCH`）/ B 连字符串值一起改 / C 保留现状。
- **商业功能**：A 无外部可见变化；**B 会改 `X-LocalModelDesk-Reason` 响应头的值，是客户端可见契约变更**，必须核对前端与 macos 消费方。
- **净收益与代价**：2 文件、约 4 行；改名可机械；改值需人工核对消费方。收益主要是降低未来误用风险。
- **数据/资金/安全**：不适用。
- **验证方法**：`tests/test_gateway_guard.py` 断言两种场景的 header code 符合预期。本次未执行。
- **关联**：无。

### S16 — 测试基建两个小合并

- **类型**：实现等价；依据：**条件性**（p5 调查，主会话仅核对了两个 `FakeArbiter` 的存在与行数）
- **现状与证据**：
  - `tests/media_fakes.py:75` 的 `FakeArbiter`（媒体只用 `can_start_heavy/acquire_heavy/release_heavy`）与 `tests/llm/llm_fakes.py:193` 的 `FakeArbiter`（另需 `reap_llm_port/desk_state/subscribe/emit/llm_port_listeners`）结构同源。引用面：`llm_fakes` 12 文件、`media_fakes` 4 文件。
  - `wait_until`/`_wait_for` 轮询等待重复：`tests/test_resources_downloader.py:21`、`tests/test_media_service.py:25`、`:416`；`tests/e2e/conftest.py:100` 是 Playwright fixture，**不可共用**。
- **为何存在**：分别由 `T-llm-02`/`T-media-05` 独立开发（p5 的 git 结论）；等待函数是各自本地定义。
- **推荐方案**：A 抽 `MinimalArbiterBase` 到 `tests/` 共享模块，`llm_fakes` 继承扩充；把 `test_media_service.py` 的 `wait_until` 提到 `tests/http_helpers.py` 供另两处复用 / B 只做后者（低风险、约 8 行）/ C 保留现状。
- **商业功能**：保留全部断言能力。
- **净收益与代价**：A 净减约 30 行，但改动 16 个引用文件的导入路径，建议分两批（先 media 的 4 个调用方，再 llm 的 12 个）；B 只触及 1-2 个文件。
- **数据/资金/安全**：不适用。
- **验证方法**：`pytest tests/media_fakes` 相关 + `tests/llm/` 全绿。本次未执行。
- **关联**：无。
- **不推荐**：p5 的 `H4`（6 处 HTTP stub server）与 `H5`（`http_helpers.http_call` vs `gateway_client.json_request`）经查证后**不应合并**——各自 serve 的协议行为（纯 GET / Range 截断 / SSE / 子进程假 API）差异承重，参数化统一会让每一处更复杂（符合原则 5）。

---

## 安全发现与未决限制

以下为审查中发现的行为/安全类问题。**它们不是简化收益，不能作为「顺手删掉」的理由**；均需你单独裁决。

- **F1（高）预算接线使「LLM 驻留」可能阻塞模型下载，与 already-approved 的需求冲突。**
  `desk/runtime.py:181-183` 把下载闸装配为 `can_start_heavy=lambda: arbiter.can_start_heavy("video")`（**无 params/key**）；`desk/resources/downloader.py:65-68` 在 `ok=false` 时抛 `MediaBusyError` 并原样透传 reason。budget 模式下 `desk/arbiter/core.py:117-118` 用 `fits(list(resident) + [workload], available_bytes)` 判定，其中 `available_bytes` 是**当前可用内存**（`desk/arbiter/memory.py:18-23`：free+inactive+purgeable+speculative），而 resident 的 `bytes_needed` 已包含该模型**已经常驻的权重**——两者相加会把已占用的权重算第二遍。于是内存吃紧时下载被拒，错误码是 `insufficient_budget` 却以 `media_busy` 的语义抛出。需求出处：`docs/superpowers/specs/2026-08-31-resources-spec.md:29`(R-resources-09)「`arbiter` 报告有重活（**媒体生成**）在跑时，下载必须拒绝」，以及 `docs/superpowers/design` 的 `2026-08-31-resources-design.md:426-431` 逐字写明「LLM 驻留不阻塞（spec R-09 只提「媒体生成」）」，并**明确依赖 legacy 转移表 `llm_held → evict_then_grant 计 ok:true`**——该依赖已随 budget 接线失效。**源码可证明的部分**：调用点无参、默认估值、residency 被计入、available 语义；**未验证**：真机（尤其内存吃紧的机器）是否实际触发、`resident` 双计的净效果（mlx-lm 的 KV 尚未分配，故只有权重部分被重算）。建议：先定「无参 `can_start_heavy` 的语义」，给下载闸一条显式的、不做预算算术的查询（或专用 `media_busy` 查询），再谈 S11。

- **F2（中）驻留模型时前端「换模型」放行分支失效，用户看到原始错误码。**
  `desk/arbiter/core.py:157-161` 的 `_state_for` → `can_start("llm")` 走 `_decide_from(kind, None, None, …)`，于是 `budget.cost("llm", key=None, config=None, weights_gb=None)` → `desk/budget/budget.py:156-176 for_chat(None, {}, 0.0)` → `per_token_bytes({})` 在 `desk/budget/estimate.py:44-51` 返回 `None` → `Workload("llm", None, 0, "unavailable")`；与驻留模型组成两件后，`desk/budget/budget.py:58-60` 的规则（`source == "unavailable" and len>1 → ok=False`）使其**与机器多大无关地**恒为 `insufficient_budget`。前端 `desk/static/js/main.js:90` 只对 `llm_already_held` 放行，`desk/static/js/pure/desk_state.js:5-11` 的 `REASON_TEXT` 没有 `insufficient_budget` 条目 → 按钮禁用并显示「暂不可用（insufficient_budget）」。而 `desk/llm/service.py:151-168` 的 `reusing_existing_token` 分支本来支持直接换模型。**源码可证明**；未在真机/集成上复现。

- **F3（中）规格承诺「媒体在跑、预算够、聊天照样装得下」在聊天路径上不可达。**
  R-arbiter-01 的改写（`docs/superpowers/specs/2026-09-17-budget-spec.md` 背景与 R-budget-07）把互斥降级为「预算不足的结果」，但 `desk/llm/service.py:427-429` 的 `_chat_precheck` 与 `desk/gateway/guard.py:19-27` 仍**无条件**在 `media_busy` 时拒绝聊天。budget 侧的共存能力在 chat 路径上没有出口。**源码可证明**；是否属于刻意保守（安全方向）需你判断——我按协议不把它写成必然事故。

- **F4（低）契约漂移**：网关在媒体忙时返回给 OpenAI/Anthropic 客户端的 `code` 由 `media_busy` 变为 `insufficient_budget`（`desk/gateway/guard.py:22` 透传 arbiter 的 reason）；`tests/test_gateway_guard.py` 用注入假件，结构上发现不了（v1 指出）。

- **F5（中，数据完整性）会话列表存在**既有**竞态：写入窗口内 `list()` 可能返回幽灵损坏会话。**
  `desk/library/sessions.py:92` 的临时文件是 `mkstemp(prefix=".tmp-", suffix=".json")` → 形如 `.tmp-XXXX.json`；`desk/library/sessions.py:23-39` 的 `list()` 用 `self._dir.glob("*.json")` 且**不持 `self._lock`**（`_write` 持锁）。我在 `/tmp` 用 stdlib 实测确认 `pathlib` 的 `glob("*.json")` **会**匹配 `.tmp-abcd.json`。因此并发读时可能读到空/半写文件 → `json.loads` 抛 `ValueError` → 被记为 `{"id": ".tmp-XXXX", "corrupt": True}` 混入返回列表（用户看到幽灵会话）。**这是 S2 之前就存在的**，不是 S2 引入；S2 统一采用无 `.json` 后缀的临时名会顺带修掉它。未验证实际触发概率（窗口很短）。

- **F6（中，条件性）`_read_model_config` 遮蔽版的失败终态是「卡在加载中」而非报错。**
  S1 的根因之外：`launch_args` 在 `desk/llm/service.py:239-240` 的 `_load_worker` 里被调用，且**在 `spawn` 之前**；`_load_worker` 没有 try/except，`AttributeError` 会让该线程直接死掉 → `self._state` 停在 `STATUS_LOADING`，`acquire_heavy` 拿到的 token 也不释放。**触发前提**（未验证）：模型目录的 `config.json` 是合法但非 dict 的 JSON，且该模型尚无实测记录（`_per_token` 先查 measured）。影响：用户看到永久「加载中」，需手动取消。

- **F7（未决）`available_bytes` 语义与 `fits` 的 resident 求和是否一致，需要一次夹具或真机验证。** 见 F1 的机制说明。若结论是「resident 已从 available 中扣过」，那么 budget 模式在**所有**共存判定上都偏保守（拒绝得比实际更早）——这是功能问题而非安全洞；若结论相反，则相反方向才需要担心。**在验证之前，不要按「resident 双计」去改算术**。

- **未决限制**：
  - 本次没有任何真机或集成运行，F1/F2/F3/F6/F7 全部是源码/规格静态推导；采纳前应有一次复现（前置条件已在各条写明）。
  - v1/v3 两个复核会话**无 git 工具**，其 commit/blame 归因未采信；本报告引用的 git 结论均由主会话亲验（见亲验清单）。
  - `tests/` 13k 行只按重复模式抽样 14 个文件，`tests/e2e/`、`tests/js/` 未逐行读；「某行为只有 N 个调用方」的断言覆盖范围是 `desk/` + `tests/` + `scripts/` + `macos/` 的 grep，未验证 e2e 注入串是否以字符串方式间接引用。
  - 未查外部一手资料，故 S12（httpx）未核对 `httpx` 的 SSE 支持细节，仅按 p1/v3 的静态阅读结论标注；`packaging/requirements-desk.txt` 中 `httpx==0.28.1` 未由主会话核对。
  - 未找到针对「非 dict config.json」的负向测试；未找到 `_sample`/`verify_tree` 口径一致性的断言。

---

## 用户选择

待用户选择；接受建议不代表授权实施。以下每项可选 A / B / C（C 一律为「暂缓」）。互斥项已合并为同一题。

| 编号 | 建议 | A（推荐项） | B | C |
|---|---|---|---|---|
| S1 | 删重复 `_read_model_config` | 删 `:65-70`、保 `:43-54` + 补回归测试 | 只删不补测试 | 暂缓 |
| S2 | 原子写收敛 | 新增 helper、统一无 `.json` 临时名、全部 fsync | 只统一命名与复用，sessions/legacy 保持不 fsync | 暂缓 |
| S3 | 删 `LibraryService` 8 个转发 | 全部直穿 | 反向补齐 `reveal` 包装 | 暂缓 |
| S4 | SSE 帧合并（3 处） | 抽公共函数，Anthropic 独立 | 只合并 `app.py` 与 harness | 暂缓 |
| S5 | 错误信封统一 | 共同基类 + 前端同步收紧（**条件：先核对前端消费方**） | 只把 library 扁平形态改成对象 | 暂缓 |
| S6 | 前端残骸 | 删 `store.js` + `tabFromHash` | 只删 `tabFromHash` | 暂缓（若要重做订阅式 store，见下） |
| S7 | `holderText` 去重 | 返回 `holderName`，文案归 statusbar | 只删媒体分支 | 暂缓 |
| S8 | video/music 重试去重 | 抽共享函数 + 统一 `confirm(options)` 签名 | 只去重不改签名 | 暂缓 |
| S9 | `maybeCompact` 分层 | 移到 `panes/`，`created_at` 删或改为传参 | 只删 `created_at`，位置不动 | 暂缓 |
| S10 | `_sample` 复用 `verify_tree` | 采用 fresh/stale 拆分（口径与 status 对齐，**进度百分比可能变**） | 只抽「遍历 manifest 算 done」内部函数，stale 口径不变 | 暂缓 |
| S11 | 收敛两套准入 | 先修 F1/F2 → 迁 harness 到 budget → 删 legacy | 保留 legacy，只订正注释（S13） | 暂缓 |
| S12 | httpx 重写 | **不做**（收益被高估） | 只替换非流式两个方法 | 全量重写 |
| S13 | 订正过期 docstring | 改全部三处（含 `core.py:22-25`） | 只改被 runtime 反证的两处 | 暂缓 |
| S14 | 构建/打包 4 小项 | a+b+c+d 全做 | 只做 a+b+c（不动 `desk/testing` 分发，尊重 A1） | 暂缓 |
| S15 | 易混常量 | 只改名 | 改名 + 改字符串值（**响应头契约变更**） | 暂缓 |
| S16 | 测试基建 | 抽 `MinimalArbiterBase` + 统一 `wait_until` | 只统一 `wait_until` | 暂缓 |

**另需你定一个前提**（决定 S6 的选项）：设计里「`store.js` 供各 pane 订阅」这个响应式方向，是打算重做，还是彻底放弃？若重做，S6 应改为「真正接上订阅者」而非删除。

**反过来，以下是我核实后判定「不该动」的**（避免下次重复讨论）：`pure/` 下的 18 个极小程序（一个概念 + 1 个生产调用方 + 1 份同名测试，是 1:1:1 的一致套路，合并会降低可发现性）；`setHeavyAllowed` ×3（禁用条件真的不同）；5 个进程站点（streaming / `start_new_session`+killpg / 日志目标 / 超时各不相同，抽共享包装要靠模式参数把差异塞回来）；`resources/parts.py` 与 `fetch_cli.py` 各自的 `PARTS_DIR`（fetch_cli 必须在无包导入的裸 python 下运行）；`packaging/*.in` 与 `*.txt`（声明 vs 编译锁文件）；6 处测试 HTTP stub server（协议行为不同）；`http_helpers.http_call` 与 `gateway_client.json_request`（后者要底层 `http.client` 做 SSE）。
