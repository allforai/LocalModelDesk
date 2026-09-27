# 视频配乐（3b）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 给视频加配乐：D2 用音乐会话里的歌替换视频音轨（ffmpeg 作业），D1「配乐参考（实验性）」让 H3 以参考图 + 一段音乐生成；选择框泛化为图片/音乐通用。

**Architecture:** 后端在现有 compose（只跑 ffmpeg 的作业）路径上加 `op="soundtrack"`；`start_video_job` 新增 `music_ref` 方式，服务端截取音频片段后以 `--ref-image/--ref-audio` 调 H3；前端 `widgets/media_picker.js` 取代 `image_picker.js`，视频页加「配乐…」动作、配乐卡片与新方式素材区。

**Tech Stack:** Python（pytest）、ffmpeg、原生 ES module（`node --test`）、Playwright e2e。

**Spec:** `docs/superpowers/specs/2026-09-27-video-soundtrack-design.md`（S-xx）；上游 `2026-09-27-video-sessions-design.md`（V-xx）、`2026-09-25-media-sessions-base-design.md`（B-xx）。

## Global Constraints

- 文案（逐字）：「配乐…」「选一首歌配到这段视频」「从音乐会话选…」「选这首」「这个会话还没有生成好的歌」「配乐参考（实验性）」起始秒数框标签「从第几秒开始」、「歌：<风格描述摘要>」「请先选择参考图」「请先选择一首歌」「引用的歌已不在」「引用的音乐已不在」「参考图只能从上传或图片会话二选一」「配乐参考不能和首帧、尾帧或续写同时使用」「这首歌从第 N 秒起不足 2 秒」「没能截取这段音乐」；说明「实验性：画面不保证跟随音乐节奏；参考图只影响画面风格，不作为第一帧。截取与视频等长、2–15 秒的一段音乐。」；配乐卡片标题「第 N 次 · HH:MM · 配乐：<风格描述摘要> · 基于第 M 次」。
- 输出文件名 `h3-soundtrack-<stamp>-<8hex>.mp4`；D1 截取 `clip = clamp(frames/24, 2, 15)` 秒。
- 配乐作业不走 arbiter/模型/内存检查（同 compose），但受 `media_busy` 互斥；ffmpeg 缺失 503「需要 ffmpeg 才能拼接成片」。
- 图片、音乐页零回归（`tests/js/image_pane.test.js` 断言不改）；「种子」只在高级参数。
- 测试命令：`python3 -m pytest -q --ignore=tests/e2e`（`test_shell_window.py` 4 个间歇环境失败除外）、`node --test tests/js/`、改 `desk/static` 必跑 `python3 -m pytest tests/e2e -q`。
- 提交中文 `feat(video-soundtrack): …`，结尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## Review Focus

1. **配乐的歌比视频短**：输出时长仍等于视频（补静音）—— Task 1 真 ffmpeg 测试。
2. **D1 起始秒超出歌长**：400「这首歌从第 N 秒起不足 2 秒」，截取文件不残留 —— Task 2。
3. **配乐作业取消/失败**：半成品删除、尝试 failed/cancelled —— Task 1。
4. **选择框里音乐会话全空**：空态文案、取消可关 —— Task 3。
5. **music_ref 回填时歌已被删**：说明「引用的歌已不在」并清空，提交被前端拦下「请先选择一首歌」 —— Task 4。

---

### Task 1: D2 换音轨后端

**Files:** Modify `desk/media/compose.py`（`replace_audio_command` → `soundtrack_command`）、`desk/media/service.py`（`start_soundtrack_job`、`_start` 的 compose 分支支持 soundtrack、`_segment` 接受任意 op）、`desk/media/routes.py`（`POST /api/media/soundtrack`）、`desk/static/js/pure/history_fill.js`（op soundtrack → null）；Test `tests/test_media_soundtrack.py`（新建）、`tests/test_media_compose.py`、`tests/js/history_fill.test.js`、`tests/test_media_routes.py`（路由表）

**Interfaces:** Produces `compose.soundtrack_command(ffmpeg, video, audio, output) -> list[str]`；`MediaService.start_soundtrack_job(*, session_id, source, refs, force=False) -> dict`；注册引用槽 `video.soundtrack → music`；HTTP `POST /api/media/soundtrack`。

- [ ] **Step 1: 失败测试**
  - `tests/test_media_compose.py` 追加：`soundtrack_command` argv 以 `-y` 开头、输出最后、含 `apad` 与 `-shortest`、`-c:v copy`；真 ffmpeg（有则跑）：1 秒视频 + 5 秒歌 → 输出 1 秒；3 秒视频 + 1 秒歌 → 输出 3 秒。
  - `tests/test_media_soundtrack.py`（用 `media_fakes.make_service`、`tests/test_media_continue.py` 的 `fake_ffmpeg` 夹具思路、`test_media_sessions_service.py` 的 `video`/`music_ready` 辅助）：
    1. 成功：视频会话里一段 done 视频 + 音乐会话一首 done 歌 → `start_soundtrack_job` → 新尝试 `op=="soundtrack"`、`params=={"source": <id>}`、`refs=={"soundtrack": ref}`、`output` 以 `h3-soundtrack-` 开头；ffmpeg 命令输入视频为 `joined_output`（若有）否则 `output`；不调用 arbiter（`deps.arbiter.acquired`/`precheck_calls` 不增）；history `params.op=="soundtrack"`、顶层 `refs`。
    2. 错误顺序与不写会话：缺会话 400 `session_required`；`source` 不存在 404 `segment_not_found`；`source` 文件不在 404 `segment_missing`；歌引用失效 404 `ref_missing`「引用的音乐已不在」；有作业在跑 409 `media_busy`；ffmpeg 缺失 503。每种情况会话尝试数不变。
    3. 失败与取消：`join_script="fail"` → 尝试 `failed` + `error.code=="join_failed"`，无 `h3-soundtrack-*` 残留；阻塞中取消 → `cancelled`，无残留。
    4. 可续写：对配乐尝试 `video(continues=<配乐尝试>)` 成功。
  - `tests/js/history_fill.test.js`：`params.op === "soundtrack"` → `null`。
- [ ] **Step 2:** 运行确认失败。
- [ ] **Step 3: 实现**
  - `compose.py`：

```python
def soundtrack_command(ffmpeg: str, video: Path, audio: Path, output: Path) -> list[str]:
    """Replace the video's audio with `audio`, padded with silence or cut so the video length wins (S-04)."""
    return [ffmpeg, "-y", "-v", "error", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-af", "apad", "-c:a", "aac", "-shortest", str(output)]
```

    删除 `replace_audio_command` 及其测试（改为测 `soundtrack_command`）。
  - `service.py`：默认引用槽加 `"soundtrack": "music"`。`start_soundtrack_job` 按 S-02 顺序校验（`refs` 必须恰为 `{"soundtrack": {...}}`，否则 400 invalid_params；复用 `_check_session("video", …, required=True)`、`_segment("video", …)`、`_resolve_refs("video", refs)`），然后走现有 compose 路径：`_start("video", {"op": "soundtrack", "source": source}, session_id=…, attempt_extra={"op": "soundtrack", "refs": stored}, compose_parts=…)`——为此把 `_start` 的 compose 分支泛化为接收一个「ffmpeg 命令构造器」：`compose_command: Callable[[str ffmpeg, Path output], list[str]]` 与 `output_prefix`（compose 用 `h3-compose`/`music3-compose`，soundtrack 用 `h3-soundtrack`），原 `compose_parts` 调用处改为传构造器。`media_sessions.begin_attempt` 对 `op == "soundtrack"` 的参数白名单为 `("source",)`（`desk/library/media_sessions.py` 加 `SOUNDTRACK_PARAM_KEYS`）。worker 中 compose 与 soundtrack 共用「非 done 删除半成品」「错误映射为 join_failed」逻辑（按 per-job `compose` 标志，soundtrack 也置真）。
  - `routes.py`：`("POST", "/api/media/soundtrack", …)` 透传 `session_id`、`source`、`refs`、`force`。
  - `history_fill.js`：`if (params.op === "compose" || params.op === "soundtrack") return null;`
- [ ] **Step 4:** `python3 -m pytest -q --ignore=tests/e2e`；`node --test tests/js/`
- [ ] **Step 5: Commit** `feat(video-soundtrack): 用音乐会话里的歌替换视频音轨的作业`

---

### Task 2: D1 配乐参考后端

**Files:** Modify `desk/media/service.py`（`start_video_job` 的 `music_ref` 方式、音频截取、`_start` 传 ref 路径）、`desk/media/commands.py`（`build_h3_command` 加 `ref_image`/`ref_audio`）、`desk/media/compose.py`（`audio_clip_command`）、`desk/media/routes.py`（透传 `ref_image`、`audio_start`）、`desk/library/media_sessions.py`（video 白名单加 `audio_start`、`ref_image`）；Test `tests/test_media_music_ref.py`（新建）、`tests/test_media_commands.py`、`tests/test_media_compose.py`

**Interfaces:** Produces `start_video_job(..., mode="music_ref", ref_image=None, audio_start=0, refs={"ref_image"?: image ref, "ref_audio": music ref})`；`compose.audio_clip_command(ffmpeg, audio, start, seconds, output_wav)`；`build_h3_command(..., ref_image: Path|None=None, ref_audio: Path|None=None)`。

- [ ] **Step 1: 失败测试**
  - `test_media_commands.py`：给了 `ref_image`、`ref_audio` → argv 含 `--ref-image <p> --ref-audio <p>`，不含 `--first-frame`。
  - `test_media_compose.py`：`audio_clip_command` argv（`-ss start -t seconds`、输出 wav 最后）；真 ffmpeg：5 秒 wav 从 1 秒截 2 秒 → 2 秒。
  - `test_media_music_ref.py`（`fake_ffmpeg` 同 continue 测试，另 patch `wav_seconds` 返回歌长）：
    1. 上传参考图 + 歌引用、`frames=73` → 截取 `seconds == 73/24` 的片段写入 `.inputs/*.wav`，H3 命令含 `--ref-image <上传图路径>`、`--ref-audio <片段路径>`；尝试 `params.mode=="music_ref"`、`audio_start==0`、`refs.ref_audio==ref`。
    2. `frames=362` → seconds 夹到 15；`frames=24`（若允许）→ 夹到 2（以 `max(2, min(15, frames/24))` 断言）。
    3. 图片会话参考图（`refs.ref_image`）→ `--ref-image` 为该图路径、`params.ref_image is None`。
    4. 错误：同时给上传与引用参考图 → 400「参考图只能从上传或图片会话二选一」；都没给 → 400「请先选择参考图」；无 `ref_audio` → 400「请先选择一首歌」；与 `continues`/`first_frame`/`last_frame`/`ref_video`/`refs.first_frame` 同用 → 400「配乐参考不能和首帧、尾帧或续写同时使用」；歌长 3 秒、`audio_start=2` → 400「这首歌从第 2 秒起不足 2 秒」；截取命令失败 → 500 `audio_clip_failed`「没能截取这段音乐」；`media_busy` 拒绝后 `.inputs` 中无新增 wav；以上都不写会话。
    5. `audio_start` 非数或负 → 400 invalid_params。
- [ ] **Step 2:** 确认失败。
- [ ] **Step 3: 实现**：默认引用槽加 `"ref_image": "image", "ref_audio": "music"`。`mode` 允许集合加 `music_ref`；`_video_assets` 对 `music_ref` 要求 `ref_image`（上传）或来自引用；截取用 `compose.audio_clip_command` 同步 `subprocess.run`（超时 60 秒），生成 `.inputs/<uuid>.wav`，与 V 块首帧截取相同的「后续失败即删除」try/except 结构；`_start` 视频分支把 `ref_paths["ref_image"]`（或上传素材解析的路径）与片段路径传给 `build_h3_command(ref_image=…, ref_audio=…)`。歌路径取 music 尝试的 `joined_output`（未缺失）否则 `output`——为此 `_resolve_refs` 对 music 目标优先返回 `joined_output`。`audio_start` 记入 `params`，白名单加入。
- [ ] **Step 4:** 全量 Python 单测。
- [ ] **Step 5: Commit** `feat(video-soundtrack): 配乐参考（实验性）——参考图加一段音乐生成视频`

---

### Task 3: 通用媒体选择框

**Files:** Create `desk/static/js/widgets/media_picker.js`；Delete `desk/static/js/widgets/image_picker.js` 与 `tests/js/image_picker.test.js`（用例迁到新测试，断言保留）；Modify `desk/static/js/panes/video.js`（首帧选择改用新组件）、`desk/static/app.css`（`.image-picker*` 改为 `.media-picker*`，加音乐列表样式）；Test `tests/js/media_picker.test.js`

**Interfaces:** Produces `openMediaPicker(doc, {kind, title, emptyText, listSessions, getSession, serveOutput}) → Promise<null | {ref:{kind, session_id, attempt_id}, title, index, label}>`

- [ ] **Step 1: 失败测试**：迁移原 image_picker 四个用例（kind image，标题与空态由参数给，断言不变）；新增音乐：两首 done（一首有 `joined_output`）+ 一首 failed → 列表 2 项，每项「第 N 次 · <风格描述摘要>」、`<audio>` 的 src 取 `joined_output` 优先、「选这首」按钮；点第二首 → 解析 `{ref:{kind:"music",…}, title, index, label}`；空会话显示 `emptyText`；取消 → null。
- [ ] **Step 2:** 确认失败。
- [ ] **Step 3: 实现**：把 `image_picker.js` 改名重写为 `media_picker.js`，图片分支保持原行为；音乐分支渲染列表。`video.js` 首帧处调用 `openMediaPicker(doc, {kind:"image", title:"从图片会话选首帧", emptyText:"这个会话还没有生成好的图片", …})`（`ctx.pickImage` 注入点保留）。
- [ ] **Step 4:** `node --test tests/js/`；`python3 -m pytest tests/e2e/test_video_sessions.py -q`
- [ ] **Step 5: Commit** `refactor(video-soundtrack): 选择框泛化为图片/音乐通用`

---

### Task 4: 视频页——「配乐…」、配乐卡片、配乐参考方式

**Files:** Modify `desk/static/js/panes/video.js`、`desk/static/js/widgets/video_session_card.js`、`desk/static/js/pure/video_session.js`、`desk/static/index.html`（`#pane-video` 素材区加 music_ref 区块、方式下拉加选项）、`desk/static/js/api.js`（`startSoundtrackJob`）、`desk/static/app.css`；Test `tests/js/video_pane.test.js`、`tests/js/video_session.test.js`

**Interfaces:** Consumes Task 1–3；Produces `api.startSoundtrackJob({session_id, source, refs})`；`pure/video_session.js` 新增 `soundtrackTitle(attempt, index, attempts)`、`refineFields`/`versionParams` 支持 `music_ref`（带 `audio_start`、`ref_image` 或 `refs.ref_image`、`refs.ref_audio`）、`MODES.music_ref = "配乐参考"`。

- [ ] **Step 1: 失败测试**（`video_session.test.js` + `video_pane.test.js`，按 S-30–S-35 与 Global Constraints 文案）：
  1. 「配乐…」：done 卡片有该按钮（挑选模式下没有）；点击 → 注入的 `ctx.pickMusic` 返回 pick → `POST /api/media/soundtrack {session_id, source:<该尝试>, refs:{soundtrack: pick.ref}}`；新卡片被选中。
  2. 配乐卡片标题「第 2 次 · HH:MM · 配乐：<摘要> · 基于第 1 次」，动作只有「接着往下生」「配乐…」。
  3. 方式选「配乐参考（实验性）」→ 参考图区、歌区、「从第几秒开始」、实验说明可见；首帧/尾帧/参考视频区隐藏。
  4. 提交体：上传参考图 → 先上传再 `{mode:"music_ref", ref_image:<id>, audio_start:0, refs:{ref_audio}}`；图片会话参考图 → `refs:{ref_image, ref_audio}` 且无 `ref_image` 字段；缺图「请先选择参考图」、缺歌「请先选择一首歌」（不发请求）。
  5. 「在这段基础上改」music_ref 尝试 → 回填参考图、歌说明「歌：<摘要>」、起始秒；歌已被删 → 说明「引用的歌已不在」、提交报「请先选择一首歌」。
  6. 「换个版本」music_ref → 原样重发（新种子，含 `audio_start`、refs）。
  7. 主流程无「种子」。
- [ ] **Step 2:** 确认失败。
- [ ] **Step 3: 实现**：卡片按 op 分支；面板状态加 `refImage`（同首帧来源的 upload/ref 两种）、`song`（`{ref, label}`）、`audioStart`；音乐选择调用 `openMediaPicker(doc, {kind:"music", title: 方式区用「从音乐会话选一首歌」/ 配乐动作用「选一首歌配到这段视频」, emptyText:"这个会话还没有生成好的歌", listSessions: () => api.listMediaSessions("music"), getSession: (id) => api.getMediaSession("music", id), serveOutput: api.serveOutput})`，可经 `ctx.pickMusic` 注入；配乐作业经控制器的生成路径提交（与 `startCompose` 同样的「提交 → onStarted → 选中新尝试 → 重载会话」流程；可在控制器加通用 `startJobVia(apiCall, params)` 或在 video.js 内调用 `pane.startGeneration(params, {fromInputs:false, via: api.startSoundtrackJob})`——选一种并在报告说明）。素材区新块放在已可滚动的 `.video-materials` 内（S-35）。
- [ ] **Step 4:** `node --test tests/js/`；`python3 -m pytest tests/e2e -q`
- [ ] **Step 5: Commit** `feat(video-soundtrack): 视频页可配乐，新增配乐参考方式`

---

### Task 5: e2e

**Files:** Create `tests/e2e/test_video_soundtrack.py`

- [ ] **Step 1:** 照 `tests/e2e/test_video_sessions.py` 夹具写：音乐页生成一首歌 → 视频页生成一段 → 展开卡片点「配乐…」→ 选择框（标题「选一首歌配到这段视频」）点「选这首」→ 配乐卡片出现（标题含「配乐：」「基于第 1 次」）→ 会话文件 `op=="soundtrack"`、`refs.soundtrack.kind=="music"`；再切方式「配乐参考（实验性）」→ 「从图片会话选…」（先在图片页生成一张）→ 「从音乐会话选…」→ 生成 → 会话文件 `params.mode=="music_ref"`、`refs.ref_audio`、`refs.ref_image`；900×700 无横向滚动、「生成视频」按钮在视口内。
- [ ] **Step 2:** 运行（失败修页面，不改期望）；全量三组测试。
- [ ] **Step 3: Commit** `test(video-soundtrack): 配乐与配乐参考的 e2e`
