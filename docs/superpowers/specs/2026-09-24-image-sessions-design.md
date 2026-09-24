# 模块设计：图片会话（image-sessions）

**日期** 2026-09-24
**需求来源** `.allforai/bootstrap/local-requirements.json` · id `image-sessions` · revision 1 · status confirmed
（用户 2026-09-24 确认：会话形式选 b、手动新建、删会话只删分组图片留素材库、「在这张基础上改 / 换个构图」两个动作、界面主流程不出现「种子」、单张尝试删除本次不做）
**下游** `image-session-backend`（数据模型、API、作业↔会话挂接）、`image-session-pane`（布局、动作、各状态文案）、`image-session-verify`（视觉验收 `.allforai/visual-qa/visual-acceptance-criteria.json` + 本文 §12 对照表）

本文每条以 **[D-xx]** 编号的陈述都可以写成测试断言。下游不需要再做任何用户可见的决定；本文没写到的用户可见行为不归下游发明（见 §11）。

---

## 0. 任务与非目标

**用户的任务（JTBD）**：把一张图调到满意。一个会话 = 围绕同一个想法的一串生成尝试；不满意就调整后再生，之前的尝试都留着，可以回头从任意一张接着改。

**非目标（本次不做）**
- [D-00a] 视频页、音乐页、它们的表单和作业展示不改。
- [D-00b] 局部重绘 / 图生图不做。
- [D-00c] 单张尝试的删除不做（用户 2026-09-24 明确决定）。尝试卡片上没有删除按钮。
- [D-00d] 批量出图、排队、模型常驻不做；单作业互斥（`MediaService._start` 的 `media_busy`）保持不变。
- [D-00e] 会话数量不设上限、不做搜索、不做导出。
- 台面未发布，本文不谈旧数据兼容或迁移。

---

## 1. 数据模型

### 1.1 存储位置

- [D-01] 图片会话目录 `PathRoots.image_sessions_dir = data_root / "image-sessions"`，与聊天会话目录 `data_root / "sessions"` 分开；两边的文件互不可见（`GET /api/sessions` 不列出图片会话，反之亦然）。
- [D-02] 每个会话一个文件 `<id>.json`，`id` 为 32 位小写十六进制（`uuid4().hex`，与 `SessionStore._ID_RE` 相同规则）。写入沿用 `SessionStore._write` 的方式：同目录临时文件 `.tmp-XXXX.part` + `os.replace`；列目录时跳过点开头的文件。
- [D-03] 图片文件不进会话目录：仍由媒体作业写到 `outputs_root`（`qwen-image-<stamp>-<8hex>.png`），会话只存文件名。

### 1.2 会话文件

```json
{
  "id": "3f0c…(32 hex)",
  "title": "一只橘猫坐在窗边，午后阳光，细腻的水…",
  "title_auto": true,
  "created": "2026-09-24T14:02:11",
  "updated": "2026-09-24T14:05:40",
  "attempts": [ /* Attempt，按开始时间升序；只追加，不重排、不覆盖 */ ]
}
```

- [D-04] `created` / `updated` / 尝试的 `ts` / `finished` 都用 `%Y-%m-%dT%H:%M:%S` 本地时间（与聊天会话一致）。
- [D-05] `updated` 在以下时刻刷新：新建、重命名、追加尝试、尝试落定。切换查看会话不刷新 `updated`。

### 1.3 尝试（Attempt）

```json
{
  "id": "a91e…(32 hex)",
  "job_id": 7,
  "ts": "2026-09-24T14:03:02",
  "finished": "2026-09-24T14:04:31",
  "status": "running | done | failed | cancelled",
  "params": {"prompt": "…", "width": 1024, "height": 1024, "steps": 40, "seed": 3021987455},
  "output": "qwen-image-20260924-140302-1a2b3c4d.png",
  "error": null
}
```

- [D-06] `id` 是尝试自己的标识（`uuid4().hex`）。`job_id` 只是进程内作业计数（`MediaService._state["job_id"]`，重启后从 0 重数），仅用于把当前轮询到的作业对上 `running` 尝试，不作为持久标识。
- [D-07] `params` 恰好五个键：`prompt`（字符串，原样保存，不截断）、`width`、`height`、`steps`、`seed`（都是整数）。`seed` 一律是**实际使用的值**，即使用户没填（随机）也记录生成时取到的那个数。
- [D-08] 各状态下字段取值：

| status | finished | output | error |
|---|---|---|---|
| running | null | null | null |
| done | 时间 | 文件名（非空） | null |
| failed | 时间 | null | `{code, message, log_tail?}` |
| cancelled | 时间 | null | `{code, message}` |

- [D-09] `error.code` 取值与含义（`message` 是存进文件的原话，界面显示规则见 §7.5）：

| code | 来源 | 存入的 message |
|---|---|---|
| `exit_nonzero` / `no_output` / `worker_failed` | `MediaService._worker` 原样 | 原样（如 `exit 1`），`exit_nonzero` 附 `log_tail` |
| `cancelled` | 用户点「取消」 | `已取消：这次生成被手动停止` |
| `cancelled_on_quit` | `MediaService.close()`（应用退出时仍在跑） | `应用退出时停止了这次生成` |
| `interrupted` | 启动恢复（上次进程没来得及落定，见 D-25） | `应用在生成途中关闭，这次没有完成` |

### 1.4 标题规则

- [D-10] 新建会话 `title = "新会话"`、`title_auto = true`。
- [D-11] 会话追加**第一个**尝试时（`attempts` 为空且 `title_auto == true`），标题改为该尝试的提示词：连续空白折叠为一个空格、去首尾空白，长度超过 24 个字符时取前 24 个字符加「…」（与聊天 `displayTitle` 的 24 字规则一致）。之后的尝试不再改标题。第一个尝试失败或取消也照样取它的提示词。
- [D-12] 重命名后 `title_auto = false`，此后任何生成都不再改标题。
- [D-13] 重命名的标题：去首尾空白后 1–80 个字符；空串或超长 → 400，文件不变。

---

## 2. 组件与职责（谁写什么）

```
desk/library/image_sessions.py   ImageSessionStore  —— 唯一读写 image-sessions/*.json 的组件
desk/library/__init__.py         LibraryService.image_sessions = ImageSessionStore(roots.image_sessions_dir)
desk/library/http.py             /api/image-sessions 路由（复用 dispatch 的错误映射）
desk/media/service.py            MediaService(image_sessions=…)：作业开始时挂尝试、结束时落定
desk/runtime.py、desk/testing/harness.py   把 library.image_sessions 传给 MediaService（生产与测试外壳都要接通）
desk/foundation/paths.py         PathRoots.image_sessions_dir
desk/static/js/panes/image.js    图片页（会话列表 + 时间线 + 输入区），只读会话、不写尝试
desk/static/js/api.js            listImageSessions / createImageSession / getImageSession / renameImageSession / deleteImageSession
```

- [D-14] **尝试记录只由后端写**：追加 `running` 尝试和落定都在 `MediaService` 里、通过 `ImageSessionStore` 完成；前端从不 PATCH 尝试。前端轮询丢包、页面刷新、窗口关闭都不会丢写。
- [D-15] `ImageSessionStore` 的每个写方法在同一把 `threading.Lock` 内「读文件 → 改 → 原子写回」，不持有内存副本；所以作业线程的落定和 HTTP 线程的重命名/删除交错时互不覆盖（重命名后落定，标题保留；落定后重命名，状态保留）。
- [D-16] 接通要求（Closure）：`runtime.py` 与 `desk/testing/harness.py` 构造 `MediaService` 时都传 `image_sessions=library.image_sessions`；`GET /api/image-sessions` 挂在生产路由和测试外壳路由上。只有文件存在、没人调用不算完成。

`ImageSessionStore` 接口：

| 方法 | 行为 |
|---|---|
| `list() -> list[dict]` | 摘要列表（见 §3.1），按 `updated` 降序；坏文件给 `{"id", "corrupt": true}` |
| `create() -> dict` | 新会话（D-10），返回完整会话 |
| `get(id) -> dict` | 完整会话；每个 `done` 尝试附加 `output_missing: bool`（`outputs_root/<output>` 不是文件时为 true）。该字段只出现在响应里，不写回文件 |
| `rename(id, title) -> dict` | D-12/D-13 |
| `delete(id) -> None` | 只 unlink `<id>.json`（D-30） |
| `exists(id) -> bool` | 文件存在且 id 合法 |
| `begin_attempt(id, attempt) -> bool` | 追加 running 尝试并按 D-11 设标题；会话不存在返回 False、不抛错 |
| `settle_attempt(id, attempt_id, status, output, error) -> bool` | 找到该尝试且其状态为 running 才改；会话或尝试不存在返回 False、不抛错（D-31） |
| `recover_running() -> int` | 把所有 running 尝试改为 `failed` + `interrupted`（D-25），返回改动条数 |

---

## 3. API 契约

所有路由挂在 library 路由表，错误走 `desk/library/http.py` 的 `dispatch`：`ValidationError → 400 {"error": "<中文原因>"}`，`NotFoundError → 404 {"error": "<中文原因>"}`。

### 3.1 `GET /api/image-sessions` — 列表

200，数组，按 `updated` 降序：

```json
[{"id": "…", "title": "…", "created": "…", "updated": "…",
  "attempt_count": 3, "running": false, "cover": "qwen-image-….png"}]
```

- [D-17] `attempt_count` 计所有状态的尝试；`running` 为该会话是否有 `status == "running"` 的尝试；`cover` 是最后一个 `done` 尝试的 `output`，没有则 `null`。目录不存在时返回 `[]`。
- 坏文件项 `{"id": "<文件名>", "corrupt": true}`，排在最后。

### 3.2 `POST /api/image-sessions` — 新建

- 请求体为空或 `{}`；有任何键 → 400 `不认识的字段：[…]`。
- 200，返回完整会话（`attempts: []`）。

### 3.3 `GET /api/image-sessions/{id}` — 读取

- 200，完整会话（含 §2 接口表里 `get` 附加的 `output_missing`）。
- id 不合法或文件不存在 → 404 `会话不存在：<id>`。文件损坏（非 JSON 或非对象）→ 400 `会话文件已损坏，无法读取`。

### 3.4 `PATCH /api/image-sessions/{id}` — 重命名

- 请求体 `{"title": "…"}`，只接受 `title` 一个键；其他键 → 400；标题不合 D-13 → 400 `标题须为 1–80 个字`。
- 200，返回完整会话；不存在 → 404。

### 3.5 `DELETE /api/image-sessions/{id}` — 删除

- 200 `{"deleted": "<id>"}`；不存在 → 404。
- 有 running 尝试也允许删除（D-31）。

### 3.6 `POST /api/media/image` — 生成（在现有路由上加 `session_id`）

请求体：`{"session_id": "…", "prompt": "…", "width": 1024, "height": 1024, "steps": 40, "seed": 123, "force": false}`

- [D-18] `session_id` 必填。缺失或不是字符串 → 400 `{"error":{"code":"session_required","message":"请先选择或新建一个会话"}}`。会话不存在 → 404 `{"error":{"code":"session_not_found","message":"这个会话已被删除，请选择或新建一个会话"}}`。
- [D-19] `seed` 可省略：省略时后端用 `secrets.randbelow(2**32)` 取随机值；不再有固定默认值 42（`start_image_job` 签名与 `routes.start_image` 里的 `seed=42` 默认都去掉）。给了就必须是 0–4294967295 的整数（现有校验）。
- [D-20] 校验与挂接顺序（`start_image_job` → `_start`）：
  1. 参数校验（提示词、宽高、步数、种子、force）→ 400；
  2. `session_id` 校验（D-18）→ 400 / 404；
  3. 互斥 `media_busy` → 409；运行环境 `capability_missing` → 503；模型 `model_incomplete` → 409；arbiter 拒绝 → 409；内存警告 `insufficient_memory`（未 force）→ 409；
  4. 启动子进程；`spawn_failed` → 500；
  5. **子进程启动成功、`_state` 已为 running 之后**，在 `MediaService._lock` 内调用 `begin_attempt(session_id, attempt)`，`attempt.job_id` 为新作业号、`params` 为实际参数（含实际 seed）。
- [D-21] 第 1–4 步任何一步失败都**不写**会话文件：没有 running 尝试，也没有失败尝试（启动失败以错误提示的方式出现在输入区，见 §7.7）。
- [D-22] 200 响应是现有 `job_status()` 快照，外加 `"session_id"` 与 `"attempt_id"` 两个字段；`job_status()` 在该作业存续期间也带这两个字段（其他 kind 为 null），前端据此把轮询到的作业对上尝试卡片。
- [D-23] `begin_attempt` 返回 False（会话恰好在第 2 步和第 5 步之间被删）时作业照常运行，结束后图片照常进素材库，不再写任何会话。

### 3.7 落定（后端，无前端参与）

- [D-24] 落定点是 `MediaService._finalize`：在写 history 之后、调用回调之前，对本作业调用 `settle_attempt(session_id, attempt_id, …)`：
  - `done` → `status=done`, `output=<文件名>`；
  - `error` → `status=failed`, `error=_state.error`（原样，含 `log_tail`）；
  - `cancelled` 且由用户取消 → `status=cancelled`, `error={"code":"cancelled", …}`；
  - `cancelled` 且由 `close()` 触发 → `status=cancelled`, `error={"code":"cancelled_on_quit", …}`（`MediaService` 用一个 `_cancel_origin ∈ {"user","quit"}` 区分）。
  - `settle_attempt` 抛出的异常被捕获并写日志，不影响 arbiter 释放、history 追加和其他回调。
- [D-25] 启动恢复：`LibraryService` 构造时调用一次 `image_sessions.recover_running()`，把上次进程遗留的 running 尝试改为 `failed` + `interrupted`。进程内任何时刻，会话文件里的 running 尝试只可能属于当前进程正在跑的那个作业。
- [D-26] history 条目：图片作业的 history 条目增加顶层字段 `session_id` 与 `attempt_id`（未挂上会话时为 null）。素材库回填据此找回会话（§8.4）。
- [D-27] 前端看到轮询作业已不在 running、而当前会话里对应尝试仍是 running 时，重新 `GET` 该会话；仍是 running 就在下一次 2 秒轮询时再取，直到落定。前端从不自行把尝试标成完成或失败。

### 3.8 并发边界汇总

| 情形 | 结果 |
|---|---|
| 生成中切到别的会话 | 尝试已挂在发起时的会话（D-20 第 5 步），切换只改变查看对象；落定写回原会话 |
| 生成中新建会话并点生成 | 409 `media_busy`，不写任何会话；输入区显示忙碌原因（§7.6） |
| 生成中重命名其会话 | 标题更新；落定后标题仍是新名字（D-15） |
| 生成中删除其会话 | 删除成功；作业继续；落定时 `settle_attempt` 返回 False 并丢弃；图片进素材库（D-31） |
| 生成中关闭应用（正常退出） | `close()` 取消作业，落定为 `cancelled_on_quit` |
| 生成中进程被杀 / 崩溃 | 下次启动 `recover_running()` 落定为 `failed` + `interrupted` |
| 两个窗口同时点生成 | 互斥只放行一个；另一个 409，不留尝试 |

---

## 4. 删除语义

- [D-30] 删除会话只删除 `image-sessions/<id>.json`。`outputs_root` 下的图片、`history.jsonl` 都不动；删除后 `GET /api/outputs` 与 `GET /api/history` 的结果与删除前相同，素材库仍能列出并打开这些图片。
- [D-31] 删除一个有 running 尝试的会话：作业不取消，完成后图片进素材库，但不出现在任何会话里；history 条目里的 `session_id` 指向已不存在的会话（回填时按「不属于任何会话」处理，§8.4）。
- 为什么不会删到素材库的图：会话文件只保存图片**文件名**，`ImageSessionStore.delete` 不接触 `outputs_root`，素材库从 `outputs_root` + history 列出成品，与会话目录无关。

---

## 5. 两个动作

打开（选中）任意一次尝试——包括失败、已取消、图片文件已不在的尝试——都显示这两个按钮（业务规则「打开任意一次尝试后给两个动作」）。正在生成的尝试不显示这两个按钮（它还没有结果）。

### 5.1 「在这张基础上改」

- [D-40] 点击后：把该尝试的 `prompt` 填进提示词输入框，`width`、`height`、`steps`、`seed` 填进「高级参数」对应输入框；焦点移到提示词输入框、光标放在末尾，输入区滚入可见区域。**不提交**。
- [D-41] 输入框上方出现一枚提示条：「沿用第 N 次的构图」，右侧 × 按钮（`aria-label="不再沿用这张的构图"`）。点 × 清空高级参数里的种子框并隐藏提示条。N 是该尝试在会话里的序号（从 1 起，按 `attempts` 顺序）。
- [D-42] 提示条只在「种子框的值 == 被引用尝试的 seed」时显示；用户在高级参数里手动改了种子框，提示条隐藏。
- [D-43] 「高级参数」保持用户当时的折叠/展开状态，不因回填而自动展开。
- [D-44] 回填后用户点「生成图片」：新尝试的 `params.seed` 等于原尝试的 `seed`（验收：种子相同）。
- [D-45] 生成中该按钮仍可用（它只改输入框，不提交）。
- [D-44a] 以图生图（2026-09-24 修订，用户确认）：被回填的尝试有图（`status == done`、有 `output` 且文件还在）时，提示条改为「以第 N 次为底稿」；提示条仍在时点「生成图片」，请求带 `base: {attempt_id, strength: 0.6}`，后端以那张图为底稿重绘（保留构图、重画细节），宽高取底稿的宽高。没图的尝试（失败、取消、文件不在）仍按 D-40–D-44 只回填、按文生图生成。提示条隐藏（改了种子或点 ×）后同样退回文生图。

### 5.2 「换个构图」

- [D-46] 点击后立即提交：`prompt`、`width`、`height`、`steps` 取该尝试的值，`seed` 取前端新生成的随机数（`crypto.getRandomValues` 取 32 位无符号整数，0–4294967295），若恰好等于原 seed 则重取直到不同。`session_id` 为当前会话。
- [D-47] 不改输入框和高级参数里的任何值；新尝试追加在时间线末尾。
- [D-47a] 以图生图（2026-09-24 修订）：该尝试有图时，提交带 `base: {attempt_id, strength: 0.35}`，以这张为底稿重绘（保留主体与色调、换构图）。没图的尝试「换个构图」不可用，按钮下方原因行为「这一次没有图片，不能以它为底稿换个构图」。
- [D-47b] 以图生图的强度只允许 0.6 与 0.35 两档（mflux 约定：强度越高越接近底稿）；后端校验底稿属于同一会话、状态为 done 且文件存在，否则分别返回 400 `invalid_params`、404 `base_not_found`、404 `base_missing`。尝试记录 `base: {attempt_id, strength}`（文生图为 `null`），卡片标题行显示「基于第 N 次」（底稿不在列表中则不显示）。
- [D-48] 生成中、正在提交、模型缺失、运行环境不可用、其他媒体作业占用时，该按钮 `disabled`，`title` 与按钮下方一行提示为不可用原因（与「生成图片」按钮同一原因文本，见 §7）。
- [D-49] 遇到 `insufficient_memory` 走现有确认框（「内存可能不足」/「仍要生成」），确认后带 `force: true` 重发；取消则什么都不写。

### 5.3 种子在界面上的出现范围

- [D-50] 「种子」二字只出现在「高级参数」折叠区内（输入框标签「种子（留空则每次随机）」和尝试详情的高级参数列表）。会话列表、时间线卡片、提示条、两个动作按钮、状态文案、确认框、错误提示中都不出现「种子」。
- [D-50a] 例外（用户 2026-09-24 决定）：「素材库」页不属于图片主流程，其条目元数据可以显示「种子 N」；本需求只改图片页（BR-1），素材库文案保持不变。D-50 与视觉标准的「种子」全局规则只适用于图片页。
- [D-51] 服务端校验错误原文（如「种子须为 0–4294967295 的整数」）只可能由高级参数里的输入触发；前端在提交前自行校验，错误提示为「高级参数里的数值有误：种子须为 0–4294967295 的整数」，出现在高级参数区内（该区自动展开以便看到）。

---

## 6. 新会话与当前会话

- [D-60] 左上「新会话」按钮（主按钮样式、plus 图标，与聊天页同构）：`POST /api/image-sessions`，新会话成为当前会话、排在列表最上，时间线显示空会话态，焦点移到提示词输入框。每次点击都新建（与聊天页一致）。
- [D-61] 未新建时，生成总是追加到**当前会话**末尾（D-20 的 `session_id` 就是当前会话）。新建后生成的图只进新会话。
- [D-62] 首次进入图片页且没有任何会话时，**自动新建一个「新会话」并选中**，不显示「请先新建」的提示。理由：与聊天页 `refreshSessions` 相同行为（保持两个页面一致）；用户第一次来要做的事就是写提示词生成，多一步「先新建」没有任何信息量；空会话没有代价。这仍满足「会话需手动新建」——之后的每个新分组都由用户点「新会话」产生，生成本身从不暗中另开会话。
- [D-63] 当前会话的恢复（刷新页面或重启 app 后进入图片页）：优先选有 running 尝试的会话；否则选 `updated` 最新的会话。不用浏览器存储、不改地址栏 hash（与聊天页一致，状态只来自服务端）。同一次页面生命周期内切换 tab 再回来，当前会话不变。
- [D-64] 切换会话：清空种子框、隐藏提示条（它指向的是上一个会话里的尝试）；提示词、宽、高、步数保持不动。
- [D-65] 生成成功启动后：提示词保留在输入框（方便继续微调），种子框清空、提示条隐藏（下一次直接「生成图片」就是新的随机构图；要沿用就再点一次「在这张基础上改」）。宽、高、步数保持。
- [D-66] 新会话第一次生成使用随机种子：种子框默认为空（`placeholder="留空则每次随机"`），前端在提交时若种子框为空则不传 `seed`，由后端 D-19 取随机值。

---

## 7. 布局与状态

### 7.1 布局（`#pane-image`）

```
┌──────────────┬──────────────────────────────────────────────────────┐
│ [+ 新会话]    │  生成图片  · 模型文件完整 · 可离线生成   [模型说明 ▸]      │  ← 头部一行
│ ┌──────────┐ │ ┌──────────────────────────────────────────────────┐ │
│ │会话标题 ●│ │ │ 第 1 次 · 14:02   [缩略图] 提示词摘要…  1024×1024·40 步│ │  ← 时间线（旧在上、新在下，
│ │3 次 14:05│ │ ├──────────────────────────────────────────────────┤ │     可滚动，flex:1）
│ └──────────┘ │ │ 第 2 次（选中，展开）                              │ │
│ ┌──────────┐ │ │   大图                                           │ │
│ │ …        │ │ │   完整提示词   ▸ 高级参数                         │ │
│ └──────────┘ │ │   [在这张基础上改] [换个构图]                     │ │
│              │ └──────────────────────────────────────────────────┘ │
│              │ ┌ 沿用第 2 次的构图 × ┐                               │  ← 输入区（固定在底部）
│              │ │ 提示词 textarea                          [生成图片] │ │
│              │ ▸ 高级参数（宽度、高度、步数、种子）                     │
│              │ 提示/忙碌原因 · 错误                                    │
└──────────────┴──────────────────────────────────────────────────────┘
```

- [D-70] `#pane-image` 与 `#pane-chat` 同构：左侧 `aside.sessions`（宽 248px，复用 `.sessions` 样式与 `card session` 卡片、`session-actions` 的改名/删除图标按钮），右侧 `.image-main` 占满剩余宽度，内容最大宽 1400px，外边距 24px（视觉基线）。`#pane-image` 原来的「表单 | 作业」两栏 grid 与右侧 `.job` 区块取消，作业展示移入时间线里的 running 卡片。
- [D-71] 时间线**旧在上、新在下**（与聊天一致，输入区在底部）。打开会话、追加新尝试、尝试落定时滚动到底部。
- [D-72] 打开会话时默认选中（展开）最后一个尝试；新尝试开始时它成为选中项。同一时刻只展开一个；点击另一张卡片（或在卡片上按 Enter/空格）切换选中。卡片是可聚焦元素（`tabindex=0`、`aria-expanded`）。
- [D-73] 折叠卡片内容：「第 N 次 · HH:MM」、缩略图（96×96 容器，`object-fit: contain`，仅 done 且文件在时出现）、提示词摘要（最多两行，超出用省略号，`title` 属性为完整提示词）、尺寸步数「1024×1024 · 40 步」、状态标记（生成中 / 失败 / 已取消 / 图片文件已不在；完成不加标记）。
- [D-74] 展开卡片额外显示：大图（宽度不超过时间线列宽、高度不超过 60vh，`object-fit: contain`，`alt` 为提示词）、完整提示词、「高级参数」折叠块（列出 宽度、高度、步数、种子 四项实际值，默认折叠）、两个动作按钮（次级按钮样式，「在这张基础上改」在左，「换个构图」在右；「生成图片」是页面唯一主按钮）。
- [D-75] 输入区：提示条（D-41，按需出现）、提示词 textarea（placeholder 沿用「例如：一只橘猫坐在窗边，午后阳光，细腻的水彩插画」，⌘Enter 等同点「生成图片」）、「生成图片」主按钮（sparkles 图标）、「高级参数」`<details>` **默认折叠**（宽度（像素）默认 1024、高度（像素）默认 1024、步数默认 40、种子（留空则每次随机）默认空；折叠区内保留现有提示「建议从 1024×1024、40 步开始；更大图片需要更多时间与内存。」）、一行状态提示 `role=status`、一行错误 `role=alert`。
- [D-76] 头部一行：「生成图片」标题、模型状态（现有 `data-image-model` 文案）、「模型说明」折叠（现有 Heretic 说明文字）。
- [D-77] 会话列表项：标题（单行省略，`title` 属性为全称）、元信息「N 次生成 · HH:MM」（N = `attempt_count`，时间取 `updated`）、有 running 尝试时标题右侧显示「生成中」小标记（`--busy` 色圆点 + 文字）。当前会话 `aria-current="true"` 与聊天页相同高亮。
- [D-78] 窄窗 900×700：左栏仍 248px，右侧约 600px；卡片、输入区、按钮不出现横向滚动和文字截断（按钮文字不换行不裁切）；两个动作按钮放不下时换到下一行而不是被裁切。

### 7.2 会话列表的四种状态

| 状态 | 显示 |
|---|---|
| 加载中 | 列表位置显示「正在加载会话…」；「生成图片」禁用，原因「会话还没加载好」 |
| 读取失败 | 列表位置显示「会话列表读不出来：<错误原因>」+「重试」按钮；「生成图片」禁用，原因同上 |
| 空 | 不出现：D-62 自动新建一个 |
| 有坏文件 | 该项标题「无法读取的会话」，元信息「文件已损坏」，只有删除按钮；点开时时间线显示「这个会话文件已损坏，无法显示。可以删除它，素材库里的图片不受影响。」，「生成图片」禁用，原因「请选择其他会话或新建一个」 |

### 7.3 会话内无尝试

- [D-80] 时间线居中显示两行：「还没有图片」／「在下面写下想要的画面，点「生成图片」。之后可以在任意一张上「在这张基础上改」或「换个构图」。」不显示空白图片框、不显示进度条。

### 7.4 生成中（running 尝试卡片）

- [D-81] running 卡片始终展开显示：「第 N 次 · 生成中…（已用 1 分 20 秒）」（沿用 jobview 的 `formatDuration` 文案）、`<progress>`（沿用 `parseStepProgress`：解析到步数时显示百分比，否则为不确定进度）、「取消」按钮（调用 `/api/media/cancel`）、「日志」折叠块（默认折叠）、提示词摘要与尺寸步数。**不显示图片框**，也不显示两个动作按钮。
- [D-82] 进度数据来源：`main.js` 的 2 秒轮询 `tickJob` 取到 `kind == "image"` 的作业时交给图片页，图片页按 `attempt_id`（D-22）找到对应卡片更新；当前查看的会话不是该作业的会话时只更新会话列表的「生成中」标记。
- [D-83] 生成中「生成图片」和「换个构图」禁用，原因见 §7.6；「在这张基础上改」、切换会话、新建会话、重命名、删除都可用。

### 7.5 失败 / 已取消 / 图片文件已不在

- [D-84] 这三种卡片**不渲染 `<img>`、不留空白图片框**；在缩略图位置显示一个图标块（失败：`x` 图标 + `--danger` 色；已取消：`x` 图标 + `--muted` 色；文件不在：`image` 图标 + `--muted` 色），块内无图片占位。
- [D-85] 原因文案：
  - 失败：标题用 `describeJobError(error).title`（如「生成程序异常退出」「内存不足，生成被中止」），`interrupted` 显示「应用在生成途中关闭，这次没有完成」；展开时下面「详情」折叠显示 `code: message` 与 `log_tail`（沿用 `renderErrorBlock`）。
  - 已取消：`cancelled` 显示「已取消」，`cancelled_on_quit` 显示「应用退出时停止了这次生成」。
  - 图片文件已不在（`output_missing: true`，或 `<img>` 触发 `error` 事件）：「图片文件已不在」／「可能已在访达中移动或删除」。前端在 `<img>` 出错时立即替换成这个状态，不显示浏览器的破图标。
- [D-86] 这三种卡片都显示两个动作按钮（§5），参数都完整可用。

### 7.6 不可用 / 忙碌原因（输入区状态提示与按钮 title）

优先级从高到低，只显示第一条：

| 条件 | 文案 |
|---|---|
| 正在提交 | 正在提交… |
| 会话未加载 / 当前会话损坏 | 会话还没加载好 / 请选择其他会话或新建一个 |
| 图片作业在**当前会话**生成中 | 正在生成这个会话里的第 N 次 |
| 图片作业在**别的会话**生成中 | 「<会话标题>」正在生成图片 + 行内按钮「回到该会话」（点击切换过去并滚动到 running 卡片） |
| 其他媒体作业（视频/音乐）或 arbiter 拒绝 | 现有 `heavyAvailability(deskState,"media").reason` 文案（如「媒体作业进行中」） |
| 运行环境不可用 | 现有 `setRuntimeStatus` 文案（`capability.detail` 或「图片 MLX 运行环境不可用，请检查服务或应用安装」） |
| 模型缺失 / 不完整 / 未知 | 现有 `setModelStatus` 文案（「尚未安装图片模型，请到「资源」页下载」等） |
| 服务状态读不到 | 服务状态暂不可用，请稍后重试 |

- [D-87] 「会话标题」取 `title`；判定「别的会话在生成」用列表摘要的 `running` 字段（§3.1），列表在每次轮询看到作业开始/结束时刷新。

### 7.7 启动失败（没有产生尝试）

- [D-88] `POST /api/media/image` 返回错误时不出现新卡片，错误显示在输入区错误行：`insufficient_memory` 走确认框（D-49）；`session_not_found` → 刷新列表、按 D-63 选中会话，错误行显示「这个会话已被删除，已切到「<标题>」，请重新点「生成图片」」；其他错误显示 `describeJobError(error).title`（如「已有作业在进行」「图片模型不完整，请到资源页检查」「无法启动生成程序」）。

### 7.8 重命名与删除

- [D-89] 重命名：与聊天页相同——点铅笔图标（`aria-label="改名"`）→ 列表项变成输入框并聚焦，Enter 或失焦保存，内容为空或未变则不请求；失败时错误行显示后端原因（如「标题须为 1–80 个字」）。
- [D-90] 删除：点垃圾桶图标（`aria-label="删除会话：<标题>"`）→ 确认框（`confirmDialog`，危险样式，默认焦点在「取消」）：
  - 标题「删除会话」，确认按钮「删除」；
  - 正文：「确定删除「<标题>」？只删除这个会话分组，其中的图片仍保留在素材库。」
  - 该会话有 running 尝试时正文追加一句：「这个会话正在生成图片，生成会继续完成，图片会进入素材库，但不会再出现在任何会话里。」
  - 删除后若删的是当前会话，按 D-63 选中下一个；列表因此变空时按 D-62 自动新建。

---

## 8. 与现有模块的衔接

### 8.1 jobview

- [D-91] 图片页不再使用 `createJobView` 的固定 DOM（`[data-job-status]` 等）；running 卡片复用它的纯函数部分：`formatDuration`、`parseStepProgress`、`describeJobError` / `renderErrorBlock`。视频、音乐页的 jobview 用法不变。

### 8.2 main.js

- [D-92] `applyHeavyAvailability` 继续调用 `panes.image.setHeavyAllowed` / 忙碌原因；`tickJob` 对 `kind == "image"` 的作业调用图片页的 `applyJob(payload)`（替代原 `jobView.apply`）；`showTab("image")` 时图片页刷新会话列表与当前会话。

### 8.3 history_fill

- [D-93] `fillPlan` 对图片条目返回 `{pane:"image", session_id, attempt_id, fields:{prompt,width,height,steps,seed}}`，`seed` 缺失时为 `null`（不再补 42）。

### 8.4 素材库「回填参数」

- [D-94] 该条目带 `session_id` 且 `GET /api/image-sessions/{session_id}` 成功、其中有 `attempt_id` 对应的尝试：切到图片页、打开那个会话、选中（展开）该尝试并滚动到它，同时执行该尝试的「在这张基础上改」（D-40–D-42）。
- [D-95] 否则（没有 `session_id`、会话已删、尝试找不到）：切到图片页，停在当前会话，把条目参数按 D-40 填入输入区；提示条文案为「沿用素材库里这张的构图」（此时没有序号可引用）。不新建会话。

---

## 9. 文案清单（主流程，均不含「种子」）

新会话 · 改名 · 删除会话：<标题> · 正在加载会话… · 会话列表读不出来：<原因> · 重试 · 无法读取的会话 · 文件已损坏 · N 次生成 · 生成中 · 还没有图片 · 第 N 次 · 生成中…（已用 …） · 取消 · 日志 · 失败 · 已取消 · 应用退出时停止了这次生成 · 应用在生成途中关闭，这次没有完成 · 图片文件已不在 · 可能已在访达中移动或删除 · 详情 · 在这张基础上改 · 换个构图 · 沿用第 N 次的构图 · 沿用素材库里这张的构图 · 生成图片 · 高级参数 · 正在提交… · 正在生成这个会话里的第 N 次 · 「<标题>」正在生成图片 · 回到该会话 · 删除会话确认正文（§7.8）

仅在「高级参数」折叠区出现：宽度（像素） · 高度（像素） · 步数 · 种子（留空则每次随机） · 高级参数里的数值有误：…

---

## 10. 测试要点（给下游）

- Store 单测（`tmp_path`）：D-02、D-10–D-13、D-15（并发 rename + settle）、D-17、D-24 各分支、D-25、D-30、D-31。
- MediaService 单测（假 executor / 假 store）：D-18–D-23（尤其 D-21：每种启动失败都不写会话）、D-24 的 `_cancel_origin`、D-26。
- HTTP 单测：§3 每条路由的成功与错误码。
- 前端单测（`node --test tests/js/`）：D-11 标题截断同规则、D-42 提示条显隐、D-46 新随机数不等于原值、D-50 主流程 DOM 文本不含「种子」、D-93。
- e2e（`python3 -m pytest tests/e2e -q`，真实浏览器，desk/static 改动必须跑）：§12 对照表里标注的每条验收；截图按 `.allforai/visual-qa/visual-evidence-requirements.json`。

---

## 11. 待决问题

无。所有用户可见行为已在上文定下；Guidance 允许本节点决定的界面细节（D-62 自动新建首个会话、D-63 恢复规则、D-65 生成后种子框清空、D-71 旧在上新在下、D-72 默认展开最后一个）已写明理由。下游若遇到本文未覆盖的用户可见行为，按 defensive-patterns Pattern I 记为 `unspecified_user_visible_decision`，不自行发明。

---

## 12. 需求对照表（business_rules / acceptance → 本文落点）

| 编号 | 需求原文 | 本文落点 | 完整效果由谁证明 |
|---|---|---|---|
| BR-1 | 只改图片页；视频、音乐页不动 | D-00a、D-91 | image-session-verify |
| BR-2 | 会话持久化在本机，重启 app 后仍在，每个会话一个 JSON 文件，沿用聊天会话的存储方式 | D-01–D-05、§2 | image-session-backend / image-session-verify |
| BR-3 | 会话内按时间顺序列出每次尝试：图片、提示词、宽高、步数、种子；失败或取消的尝试也列出并写明原因 | D-06–D-09、D-71、D-73–D-74、D-84–D-85 | image-session-pane / image-session-verify |
| BR-4 | 会话需手动新建（像聊天的「新建」）；未新建时生成接在当前会话；会话标题默认取第一次生成的提示词 | D-60–D-62、D-10–D-12 | image-session-backend / image-session-pane |
| BR-5 | 会话可切换、重命名、删除；删除会话只删分组，图片文件保留并仍出现在素材库 | D-63–D-64、D-89–D-90、D-30–D-31、§3.4–3.5 | image-session-verify |
| BR-6 | 打开任意一次尝试后给两个动作：「在这张基础上改」把提示词回填到输入框并沿用该张种子，用户改完再生成；「换个构图」提示词不变、换一个新随机种子直接再生成 | §5.1（D-40–D-45）、§5.2（D-46–D-49）、D-86 | image-session-pane / image-session-verify |
| BR-7 | 界面主流程不出现「种子」一词；种子与宽高、步数一起收进「高级参数」 | D-50–D-51、D-75、D-74、§9 | image-session-verify（视觉标准 global rule） |
| BR-8 | 新尝试总是追加到当前会话末尾，不覆盖旧图 | D-06、D-20 第 5 步、D-61、D-71 | image-session-backend |
| BR-9 | 局部重绘/图生图不在本次范围 | D-00b | — |
| AC-1 | 连续三轮「生成 → 在这张基础上改 → 再生成」后，三张图及各自参数都在同一个会话里按顺序显示 | D-40、D-44、D-61、D-65、D-71、D-74；视觉状态 `timeline-three-rounds` | image-session-verify |
| AC-2 | 「在这张基础上改」生成的新图与原图种子相同；「换个构图」生成的新图提示词相同而种子不同 | D-44、D-46、D-07 | image-session-verify |
| AC-3 | 重启 app 后会话列表、每个会话的尝试和图片都还在 | D-01–D-03、D-25、D-63 | image-session-verify |
| AC-4 | 切到另一个会话再切回，内容不变；新建会话后生成的图只进新会话 | D-05、D-60–D-61、D-64、§3.8 | image-session-verify |
| AC-5 | 删除会话后会话从列表消失，其中的图片仍能在素材库打开 | D-30–D-31、D-90 | image-session-verify |
| AC-6 | 失败或取消的尝试在会话里可见并显示原因，不会留下一张空白图 | D-08–D-09、D-24–D-25、D-84–D-85；视觉状态 `attempt-failed`、`attempt-cancelled` | image-session-verify |
| AC-7 | 在真实浏览器中截图检查图片页的会话列表、尝试列表和两个动作按钮，无遮挡、截断或空白态错误 | §7 全部、D-78；`.allforai/visual-qa/visual-acceptance-criteria.json` | image-session-verify |

自审闭环（Guidance 8）落点：a → D-31、D-90；b → D-20、D-21；c → D-85；d → D-94、D-95；e → D-77、§7.6「回到该会话」；f → D-19、D-66；g → D-00c。
