# 模块设计：媒体会话底座（media-sessions-base）

**日期** 2026-09-25
**来源** 用户 2026-09-24/25 对话确认：「音乐和视频也跟图片一样，会话管理，可以继续调整生成，以图生，以音乐继续生」。
**上游** `2026-09-24-image-sessions-design.md`（下称 IS，引用其 D-xx 编号）。
**下游** 第 2 块 `music-sessions`（音乐页界面与动作）、第 3 块 `video-sessions`（视频页界面、以图生视频、配乐）。

本文每条 **[B-xx]** 都可写成测试断言。本文没写到的用户可见行为不归实现者发明。

---

## 0. 背景、范围与非目标

### 0.1 整体拆分（用户已认可）

spike（已完成，见 §0.3） → **本文：媒体会话底座** → 音乐会话 → 视频会话。每块单独 spec → 计划 → 实现。

整体已定的用户决定（本文只实现其中的底座部分，其余写给下游作约束）：
- 视频、音乐都有「在这个基础上改」（回填参数、沿用种子）与「换个版本」（换种子直接重生）。
- 音乐：调整重生 + 「接着写下一段」（同风格、新歌词，交叉淡化拼接；不是真正的音频续写）。
- 视频：两个调整动作 + 从图片会话挑图作首帧 + 「接着往下生」（尾帧 → 下一段首帧）+ 用音乐会话的歌作配乐，两种都要：D1 参考模式（实验性）、D2 替换音轨（默认）。
- 成片：续写时自动拼好、旧版本保留；也能手动挑片段排序合成。
- 硬件：不同内存的机器都要能用；内存检查只提醒可确认，不新增硬拒绝，不按硬件隐藏功能；续写段数与成片长度不设上限。

### 0.2 本文范围

- 把图片会话存储泛化成按 `kind` 分的媒体会话存储；图片会话迁到新底座上，**图片页行为与文案不变**。
- 视频、音乐生成接口挂上会话（`session_id` 必填）、记录实际种子。
- 续写链（`continues`）与作业内自动拼接成片（`joined_output`）。
- 手动合成作业（`op: "compose"`）。
- 跨会话引用（`refs`）的存储与解析机制。
- 前端：把图片页里会话通用部分抽成共用模块。

### 0.3 spike 结论（2026-09-25，作为本文事实前提）

- H3 `--seed` 与 Music 3 `seed` 同值两次输出逐字节相同。现状：`build_h3_command` 不传 `--seed`；`music3_cli.py` 写死 `seed=0`。
- Music 3 运行库无音频输入入口，不能真正续写音频。
- H3：参考素材（`--ref-image` / `--ref-audio`）不能与首帧/尾帧同用；`--ref-audio` 必须同时有参考图或参考视频，且时长 2–15 秒。
- 尾帧接首帧的接缝画面连续；续写段首帧与上段末帧几乎相同（PSNR 32.7），拼接时丢掉续写段首帧。
- 视频拼接用重编码（流拷贝时长漂移 4.70 vs 4.67 秒）；音乐 `acrossfade` 1.5 秒可用。
- ffmpeg 替换音轨可用。

### 0.4 非目标

- [B-00a] 视频页、音乐页的界面本文不改（归第 2、3 块）。
- [B-00b] 图片会话不支持 `continues` 与 `compose`（请求带了 → 400 `invalid_params`）。
- [B-00c] D1 参考模式、D2 替换音轨、以图生视频的界面与参数规则归第 3 块；本文只提供 `refs` 机制与 `compose.py` 的 `replace_audio` / `last_frame` 原语。
- [B-00d] 不改 H3 `--budget`（属 budget 模块）。不设续写段数、成片时长上限。
- 台面未发布，不谈旧数据兼容或迁移：`image-sessions/` 目录沿用，文件格式按本文。

---

## 1. 数据模型

### 1.1 存储位置

- [B-01] 三个目录：`data_root/image-sessions`、`data_root/video-sessions`、`data_root/music-sessions`，由 `PathRoots.media_sessions_dirs: dict[kind, Path]` 给出（取代 `image_sessions_dir`）。互不可见。
- [B-02] 写入纪律、id 规则、坏文件处理、锁、「读 → 改 → 原子写回、不持内存副本」全部继承 IS D-02、D-15。

### 1.2 会话文件

```json
{"id": "…32hex", "kind": "video", "title": "…", "title_auto": true,
 "created": "…", "updated": "…", "attempts": []}
```

- [B-03] `kind` 与所在目录一致；读到不一致视为坏文件。
- [B-04] 标题规则继承 IS D-10–D-13。自动标题取第一个尝试的「标题来源字段」：image/video 取 `prompt`，music 取 `caption`。

### 1.3 尝试

```json
{"id": "…", "job_id": 3, "ts": "…", "finished": "…",
 "status": "running|done|failed|cancelled",
 "op": "generate|compose",
 "params": {…},
 "continues": null,
 "refs": {},
 "output": "h3-….mp4",
 "joined_output": null,
 "joined_error": null,
 "error": null,
 "base": null}
```

- [B-05] `op`：`generate` 为模型生成；`compose` 为手动合成（§4）。
- [B-06] `params` 按 kind 的白名单保存（§1.4），白名单外的键不写入。`seed` 一律是实际使用的值。
- [B-07] `continues`：被续写的尝试 id，非续写为 `null`。仅 video/music。
- [B-08] `joined_output` / `joined_error`：仅 `continues != null` 的尝试有意义；`done` 时二者恰有一个非空，其他状态都为 `null`。`compose` 尝试的成品放 `output`，这两个字段为 `null`。
- [B-09] `refs`：`{名称: {"kind", "session_id", "attempt_id"}}`，名称由下游定义（例如视频的 `first_frame`、`soundtrack`）。本文只规定结构、校验与解析（§5）。
- [B-10] `base`：仅 image，含义同 IS D-47b；其他 kind 恒为 `null`。
- [B-11] 状态与字段取值继承 IS D-08、D-09（含 `cancelled_on_quit`、`interrupted`）。
- [B-12] `get(id)` 对每个 `done` 尝试附加 `output_missing`；对有 `joined_output` 的尝试再附加 `joined_missing`。都只出现在响应里，不写回文件。

### 1.4 各 kind 的参数白名单

| kind | 白名单 | 标题来源 |
|---|---|---|
| image | `prompt, width, height, steps, seed` | `prompt` |
| video | `prompt, width, height, frames, steps, seed, mode, use_audio, first_frame, last_frame, ref_video` | `prompt` |
| music | `caption, lyrics, duration, seed` | `caption` |

- [B-13] video/music 的白名单是**现有**生成参数加 `seed`；第 3 块若新增参数（如参考图、参考音频）在其 spec 中扩充白名单。

---

## 2. 组件与职责

```
desk/library/media_sessions.py  MediaSessionStore(kind, sessions_dir, outputs_root)
                                 取代 image_sessions.py（删除旧文件）
desk/library/__init__.py        LibraryService.media_sessions: dict[kind, MediaSessionStore]
                                 构造时对三者各调一次 recover_running()
desk/library/http.py            /api/media-sessions/{kind}[/{id}]（取代 /api/image-sessions）
desk/foundation/paths.py        PathRoots.media_sessions_dirs
desk/media/compose.py           新增：ffmpeg 原语（§6）
desk/media/commands.py          build_h3_command 加 seed；build_music_command 加 seed
desk/media/routes.py            生成路由透传 session_id / seed / continues / refs；新增 POST /api/media/compose
desk/library/history.py         by_output() 同时索引 joined_output（B-43）
desk/media/music3_cli.py        新增 --seed 参数，去掉写死的 seed=0
desk/media/service.py           MediaService(media_sessions=…)：所有 kind 挂会话；continues/refs 解析；
                                 作业内拼接；compose 作业
desk/runtime.py、desk/testing/harness.py  传 media_sessions=library.media_sessions（生产与测试外壳都接通）
desk/static/js/panes/media_session.js  新增：会话列表、时间线骨架、轮询挂接、改名删除（从 image.js 抽出）
desk/static/js/panes/image.js   只保留图片专属的输入区与卡片内容，其余用 media_session.js
desk/static/js/api.js           mediaSessions(kind) 系列取代 imageSessions 系列
desk/static/js/pure/history_fill.js  fillPlan 对所有 kind 带出 session_id/attempt_id（界面如何用归第 2、3 块）
```

- [B-20] 尝试记录只由后端写（继承 IS D-14）。
- [B-21] 接通要求：`runtime.py` 与 `desk/testing/harness.py` 都传 `media_sessions`；`/api/media-sessions/{kind}` 挂在生产路由与测试外壳路由上。仓库中不再有 `/api/image-sessions`、`ImageSessionStore`、`image_sessions_dir` 的引用。

`MediaSessionStore` 接口 = IS §2 接口表的全部方法（`list/create/get/rename/delete/exists/begin_attempt/settle_attempt/recover_running`），另加：

| 方法 | 行为 |
|---|---|
| `find_done(id, attempt_id) -> dict` | 返回该会话中的该尝试；会话/尝试不存在 → `NotFoundError`；未完成或文件不在 → `SegmentMissing`（§7 映射错误码） |
| `chain(id, attempt_id) -> list[dict]` | 沿 `continues` 回溯，返回从链首到该尝试的有序列表（含自身）；遇到环或缺环返回到断点为止并标记 `broken=True` |
| `settle_attempt(…, joined_output=None, joined_error=None)` | 增加两个可选参数，按 B-08 写入 |
| `record_output(id, attempt_id, output) -> bool` | 仅对 running 尝试写 `output`（B-38a）；不存在返回 False |

- [B-22] `chain` 防御环：回溯时记录已访问 id，重复即停（正常数据不会有环，因为 `continues` 只能指向已存在的更早尝试）。

---

## 3. API

### 3.1 会话接口 `/api/media-sessions/{kind}`

- [B-30] `kind ∈ {image, video, music}`，其他 → 404 `不认识的媒体类型：<kind>`。
- [B-31] `GET/POST /api/media-sessions/{kind}`、`GET/PATCH/DELETE /api/media-sessions/{kind}/{id}` 的请求、响应、错误与 IS §3.1–3.5 一致；列表摘要的 `cover` 对 video/music 取最后一个 `done` 尝试的 `joined_output`（没有则 `output`）。

### 3.2 生成接口

`POST /api/media/{image|video|music}` 在现有字段外统一接受：

| 字段 | 规则 |
|---|---|
| `session_id` | image：必填，规则同 IS D-18。video/music：**本块内可省略**——省略时作业照旧运行、不挂会话（`attempt_id` 为 null），保证第 2、3 块上线前现有视频页、音乐页不坏；给了就按 IS D-18 校验。第 2、3 块各自把本 kind 改为必填。带 `continues` 或 `refs` 时必填（它们只在会话内有意义） |
| `seed` | 可省略；省略时后端 `secrets.randbelow(2**32)`；给了须为 0–4294967295 的整数（IS D-19，推广到 video/music） |
| `continues` | 可选，尝试 id 字符串；仅 video/music（image 带 → 400） |
| `refs` | 可选对象；名称与允许的 kind 由各 kind 的 spec 注册，未注册的名称 → 400 `invalid_params` |

- [B-32] 校验与挂接顺序：参数 → 会话 → `continues`（§3.3）→ `refs`（§5）→ `_start` 的既有检查（`media_busy` → `capability_missing` → `model_incomplete` → arbiter → `insufficient_memory`）→ 若需拼接则检查 ffmpeg（§6）→ 启动子进程 → 成功后 `begin_attempt`。
- [B-33] B-32 任一步失败都不写会话（继承 IS D-21）。
- [B-34] 200 响应与 `job_status()` 对所有 kind 都带 `session_id`、`attempt_id`（IS D-22 推广）。

### 3.3 续写（`continues`）

- [B-35] 被续写的尝试须在同一会话、`status == done`、`output` 文件存在；否则 404 `segment_not_found` / `segment_missing`。`op == compose` 的尝试也可被续写（在成片后接着生）。
- [B-36] 续写时模型的输入如何取自被续写的尝试：
  - video：用 `compose.last_frame(被续写尝试的成片或输出)` 截取末帧，作为本次的 `first_frame`，`mode` 置 `image`；请求里若另带 `first_frame` → 400（二者冲突）。被续写尝试有 `joined_output` 时从 `joined_output` 截，否则从 `output` 截（两者末帧相同，这样写只为不依赖单段文件）。截帧文件写入 `outputs_root` 的输入素材区（沿用 `save_input` 的命名），`params.first_frame` 记该素材 id。
  - music：模型输入不取任何东西；风格、歌词、时长以本次请求为准（「写下一段」由第 2 块界面负责预填）。
- [B-37] 截帧失败（ffmpeg 报错）→ 启动前 500 `frame_extract_failed`「没能从上一段截出最后一帧」，不写会话。

### 3.4 自动拼接成片

- [B-38] `continues != null` 的作业：模型子进程成功产出后，**同一个工作线程**继续执行拼接，再落定。拼接期间作业仍是 `running`，日志追加一行 `[join] 正在拼接成片…`。
- [B-38a] 模型产出后、开始拼接前，先调用 `store.record_output(session_id, attempt_id, output)` 把单段文件名写进仍为 running 的尝试。之后任何中断都不丢这一段：
  - 拼接阶段用户取消或应用退出：终止 ffmpeg、删临时文件，尝试落定为 **`done`**（单段已生成），`joined_error = {"code": "join_cancelled", "message": "成片拼接被中止"}`。取消在模型阶段仍按 IS D-24 落定为 `cancelled`。
  - 拼接阶段进程崩溃：`recover_running()` 对「running 且 `output` 非空」的尝试落定为 `done` + `joined_error = {"code": "interrupted", "message": "应用在拼接成片时关闭"}`；`output` 为空的仍按 IS D-25 落定为 `failed` + `interrupted`。
- [B-38b] 重活许可在**模型子进程退出时**释放（拼接只用 ffmpeg，不该继续占着 arbiter 的内存额度挡住聊天加载）；`_finalize` 对已释放的许可不再释放（只释放一次）。compose 作业没有许可（B-45）。
- [B-39] 拼接的片段 = `chain(本尝试)` 中每一项的「单段文件」按顺序；**不使用**上一段的 `joined_output` 再加一段。理由：片段各自独立，任何一次拼接都能只从单段文件重建。
  - 例外：链中某项为 `compose` 尝试时，它的 `output` 视为一个整段（合成成品本身就是整段）。
- [B-40] 链断（某项文件不在、或 `broken`）→ 本尝试 `done`，`joined_output = null`，`joined_error = {"code": "segment_missing", "message": "第 N 段的文件已不在，无法拼成成片"}`（N 为链中序号，从 1 起）。
- [B-41] 拼接命令失败 → 本尝试 `done`，`joined_error = {"code": "join_failed", "message": "拼接成片失败", "log_tail": …}`。
- [B-42] 成片文件名：视频 `h3-joined-<stamp>-<8hex>.mp4`，音乐 `music3-joined-<stamp>-<8hex>.wav`，写在 `outputs_root`。
- [B-43] history：所有 kind 的条目都带 `session_id`、`attempt_id`；拼接成功时再加 `joined_output`。`HistoryStore.by_output()` 同时按 `output` 与 `joined_output` 建索引，使素材库列出成片时带上它的 history（不显示为孤儿文件）。

### 3.5 手动合成 `POST /api/media/compose`

请求体 `{"kind": "video|music", "session_id": "…", "parts": ["attempt_id", …], "force": false}`

- [B-44] `kind` 为 image 或不认识 → 400；`parts` 须为 2 个及以上的字符串数组，可以重复同一个 id（允许同一段出现两次）；每项按 B-35 校验（`segment_not_found` / `segment_missing`）。
- [B-45] 检查顺序：参数 → 会话 → parts → `media_busy` → ffmpeg 可用性 → 启动。**不经过** arbiter、模型检查、内存提醒（ffmpeg 开销小；符合「不要太严格」）。`force` 接受但无作用，保留只为前端统一重发逻辑。
- [B-46] 启动成功后 `begin_attempt`：`op = "compose"`、`params = {"parts": [...]}`、`continues = null`、`refs = {}`。标题：会话第一个尝试是 compose 不可能发生（parts 需要已有尝试），故不涉及自动标题。
- [B-47] compose 作业与生成作业共用 `_state`、互斥、`job_status`、轮询、取消、`close()`、history（`kind` 为 `video|music`，`params.op = "compose"`）、落定。成功 → `output` 为成品；失败 → `failed` + `join_failed`。
- [B-48] 片段用各自的「单段文件」：generate 尝试用 `output`（不用其 `joined_output`），compose 尝试用 `output`。

---

## 4. 各 kind 的拼接规则（compose 与自动拼接共用）

- [B-50] video：重编码 concat（`libx264`、`yuv420p`、`aac`），**每个续写关系上的后一段丢首帧**：若 `parts[i+1].continues == parts[i].id`，则 `parts[i+1]` 丢首帧；否则不丢（手动乱序合成时不是尾帧接首帧的关系）。各段宽高不一致时按第一段宽高缩放并补边（`scale` + `pad`，保持比例）。
- [B-51] music：相邻两段 `acrossfade=d=1.5:c1=tri:c2=tri`；任何一段短于 3 秒时该接缝改为直接拼接（不交叉淡化）。
- [B-52] 具体数值（丢帧数、淡化时长）写在 `compose.py` 常量里，第 2、3 块如需调整在其 spec 内改。

---

## 5. 跨会话引用 `refs`

- [B-55] 每项 `{kind, session_id, attempt_id}`；`kind` 须为该引用名称注册的允许值；目标会话、尝试须存在、`done`、文件在；否则 404 `ref_missing`「引用的<图片/音乐/视频>已不在」（中文名按目标 kind）。
- [B-56] 解析结果是一个文件路径，由 `MediaService` 交给该 kind 的命令构造；尝试记录只存引用三元组，不存路径。
- [B-57] 引用是单向指针：删除被引用会话不影响已生成的尝试；再次用该尝试「在这个基础上改」时若引用失效，按 B-55 返回 404，由下游界面提示。
- [B-58] 本文**不注册任何引用名称**；机制以测试用的假名称验证。第 3 块注册 `first_frame`（image）、`soundtrack`（music）等。

---

## 6. `compose.py`（ffmpeg 原语）

纯函数构造命令 + 一个执行入口；不读会话、不做业务判断。

| 函数 | 作用 |
|---|---|
| `concat_video_command(parts: list[(path, drop_first_frame)], output) -> list[str]` | B-50 |
| `crossfade_audio_command(parts: list[path], output) -> list[str]` | B-51 |
| `last_frame_command(video, output_png) -> list[str]` | B-36，`-sseof -0.1 … -frames:v 1 -update 1` |
| `replace_audio_command(video, audio, output) -> list[str]` | 供第 3 块 D2；视频流拷贝、音频 aac、`-shortest` |
| `ffmpeg_path() -> str | None` | 复用 `desk/media/inputs.py` 的 `_tool` 查找规则（`LOCALMODELDESK_FF*` 覆盖，再 PATH） |

- [B-60] ffmpeg 不可用：只有**需要拼接或截帧**的请求返回 503 `capability_missing`「需要 ffmpeg 才能拼接成片」；普通生成不检查。
- [B-61] 拼接与截帧的子进程经 `MediaService` 现有 executor 运行，日志进作业日志，取消走同一套 `terminate/kill`。
- [B-62] 内存：这些作业不接 `estimate_bytes`、不做内存提醒（B-45）。

---

## 7. 错误码汇总（新增）

| code | HTTP | message | 何时 |
|---|---|---|---|
| `segment_not_found` | 404 | 找不到要接着的那一段 | continues / parts 指向本会话中不存在的尝试 |
| `segment_missing` | 404 | 那一段的文件已不在，无法接着生成 | 指向的尝试未完成或文件不在 |
| `ref_missing` | 404 | 引用的<图片/音乐/视频>已不在 | B-55 |
| `frame_extract_failed` | 500 | 没能从上一段截出最后一帧 | B-37 |
| `capability_missing` | 503 | 需要 ffmpeg 才能拼接成片 | B-60 |
| `invalid_params` | 400 | （具体原因） | image 带 continues、compose 参数错误、未注册的 ref 名称、continues 与 first_frame 冲突 |

作业内（不影响启动，写进尝试）：`joined_error.code ∈ {segment_missing, join_failed}`；compose 失败 `error.code = join_failed`。

---

## 8. 前端（本文只做重构）

- [B-70] `panes/media_session.js` 导出一个工厂：参数为 `kind`、输入区与卡片内容的渲染回调；负责会话列表四种状态（IS §7.2）、自动新建首个会话（IS D-62）、当前会话恢复（IS D-63）、时间线骨架与选中展开（IS D-71、D-72）、running 卡片与轮询挂接（IS D-81、D-82）、改名删除（IS D-89、D-90）、忙碌原因中「别的会话在生成」（IS §7.6）。
- [B-71] 图片页改用该模块后，IS 全部 D-xx 仍成立；图片页 DOM 文本、按钮、文案逐字不变。
- [B-72] 删除确认正文中的「图片」按 kind 替换为「视频 / 音乐」由工厂参数提供；本文只要求 image 的文案不变。
- [B-73] 本文不改 `panes/video.js`、`panes/music.js`。它们不传 `session_id`，按 §3.2 照旧能生成；`main.js` 的 `tickJob` 对 video/music 作业（含 compose）仍交给它们的 jobView 显示。
- [B-74] `fillPlan`：video/music 条目带出 `session_id`、`attempt_id`（同 IS D-93）；`params.op == "compose"` 的条目返回 `null`（没有可回填的参数，素材库不显示「回填参数」）。
- [B-75] 给下游的约束（第 2、3 块界面必须实现，本文后端已备好）：卡片的 `joined_error.code ∈ {join_failed, join_cancelled, interrupted}` 时提供「重新拼接」，行为是发起 `compose`，`parts = chain(该尝试)` 各项 id，结果作为新的成片卡片追加；`segment_missing` 不提供（缺的文件补不回来），只显示原因。

---

## 9. 测试与完成标准

- 存储单测：`test_image_sessions.py` 改为 `test_media_sessions.py`，按三种 kind 参数化；另测 B-03、B-08、B-12、`chain`（正常、分叉、缺环、环）、`find_done`。
- `compose.py` 单测：命令构造（B-50 丢首帧判断、缩放补边、B-51 短段直拼）；真 ffmpeg 小测（lavfi 生成两段 1 秒 testsrc/sine，拼接后 ffprobe 时长），无 ffmpeg 时 skip。
- `MediaService` 单测（假 executor、假 store）：B-32/B-33 每种启动失败不写会话；video/music 记录实际 seed 且命令带 `--seed`；B-36 截帧注入 `first_frame`；B-38 拼接中取消；B-40/B-41 拼接失败仍 `done`；B-44–B-47 compose 互斥、落定、history。
- HTTP 单测：`/api/media-sessions/{kind}` 全路由 × 三 kind、B-30；`/api/media/compose`；生成接口 `session_id` 对 video/music 必填。
- 前端单测（`node --test tests/js/`）：现有图片会话前端测试全部通过（改 import 即可，断言不改）。
- e2e：`python3 -m pytest tests/e2e -q` 全过（desk/static 改动必须跑真实浏览器）。

**完成标准**
1. 图片页行为与文案不变：上述前端单测与 e2e 全过。
2. 在测试外壳里仅用 HTTP（不经界面），对 video 与 music 各完成：新建会话 → 生成 → `continues` 续写一段 → 尝试带 `joined_output` 且 ffprobe 时长 ≈ 两段之和（视频减一帧；音乐减 1.5 秒）→ `compose` 两段 → `output` 存在。可用假 executor 产出真实的小文件（lavfi）来跑，不必加载真模型。
3. B-21 接通检查：`grep` 不到旧名字；生产 `runtime.py` 与 harness 都传 `media_sessions`。

---

## 10. 自审闭环（2026-09-25）

| 环 | 检查 | 落点 |
|---|---|---|
| 生产 ↔ 消费 | 成片文件进素材库时带 history，不成孤儿 | B-43 |
| | compose 条目在素材库不给坏的「回填参数」 | B-74 |
| | `joined_error` 有出路（重新拼接） | B-75 |
| | 截出的末帧写在 `.inputs/`（点目录，素材库不列），与上传素材同生命周期 | B-36 |
| 中断 ↔ 恢复 | 拼接阶段取消/退出/崩溃都不丢已生成的单段 | B-38a |
| 资源 获取 ↔ 释放 | 重活许可在模型退出时释放、只释放一次；compose 不拿许可 | B-38b、B-45 |
| 分步上线 | 本块上线后、第 2/3 块上线前视频页音乐页仍可用 | §3.2 `session_id` 行、B-73 |
| 接通 | 路由、runtime、harness、routes.py 都接上；旧名字清零 | B-21、§2 |
| 删除 | 删会话只删分组；成片、单段、截帧都保留在 outputs | B-02（继承 IS D-30）、B-57 |

## 11. 待决问题

无。以下细节由本文决定并写明理由：B-39 拼接只从单段文件重建（可重现、断链可诊断）；B-44 允许重复片段（用户手动合成的自由，无害）；B-45 compose 不做内存与 arbiter 检查（ffmpeg 开销小，遵循「不要太严格」）；B-50 仅在真实续写关系上丢首帧；B-51 短段不淡化（避免 1.5 秒淡化吃掉大半段）。
