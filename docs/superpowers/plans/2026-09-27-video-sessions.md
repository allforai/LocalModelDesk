# 视频会话（3a）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 视频页改成会话式（共用控制器第三个使用方），支持三个动作、成片、重新拼接、挑选合成、从图片会话选首帧，并清理控制器里的图片专属命名。

**Architecture:** 后端给视频加必填会话与 `first_frame → image` 引用槽；前端 `panes/video.js` 按 `panes/music.js` 的结构重写（`createSessionPane` + 卡片组件 + 纯逻辑），新增图片会话选择框组件，图片卡片加「用这张生成视频」，`main.js` 负责跨页。

**Tech Stack:** 原生 ES module（`node --test` 假 DOM）、Playwright e2e、Python 后端（pytest）。

**Spec:** `docs/superpowers/specs/2026-09-27-video-sessions-design.md`（V-xx）；上游 `2026-09-27-music-sessions-design.md`（M-xx）、`2026-09-25-media-sessions-base-design.md`（B-xx）、`2026-09-24-image-sessions-design.md`（IS D-xx）。

## Global Constraints

- 图片页零回归：`tests/js/image_pane.test.js` 断言不改（只可在 `makePane` 的 `names` 补元素名、改 import）；`tests/e2e/test_image_sessions.py` 断言不改；图片页现有文案逐字不变（新增「用这张生成视频」按钮除外，V-50）。
- 「种子」只出现在「高级参数」内。
- 视频文案（逐字）：空会话「还没有视频」／「在下面写提示词，点「生成视频」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着往下生」。」；提示条「沿用第 N 次」「接在第 N 次后面」「第 N 次的文件已不在，不能接着往下生」「沿用素材库里这段」；首帧说明「已选择：<文件名>」「首帧：图片会话「<标题>」第 N 次」「接在第 N 次后面（用它的最后一帧）」「首帧：来自图片会话」「引用的图片已不在」；按钮「生成视频」「在这段基础上改」「换个版本」「接着往下生」「从图片会话选…」「上传图片」「上传图片（可选）」「清除尾帧」「用这张生成视频」；原因「这一段没有生成好，不能接着往下生」；选择框标题「从图片会话选首帧」、空态「这个会话还没有生成好的图片」；分段切换「成片」「只看这一段」。
- 后端错误：视频缺会话 400 `session_required` / 404 `session_not_found`；`refs.first_frame` 与上传首帧同时给或非图生方式 → 400 `invalid_params`「首帧只能从上传或图片会话二选一」；与 `continues` 同时给 → 400 `invalid_params`（CONTINUE_CONFLICT 文案）；失效 → 404 `ref_missing`「引用的图片已不在」。
- 测试命令：`node --test tests/js/`；`python3 -m pytest -q --ignore=tests/e2e`（`tests/test_shell_window.py` 4 个环境失败除外）；改 `desk/static` 必跑 `python3 -m pytest tests/e2e -q`。
- 提交中文，`feat(video-sessions): …` 等，结尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## Review Focus

1. **图片会话里被引用的图后来被删**：视频「在这段基础上改」回填时首帧区显示「引用的图片已不在」并清空来源，「生成视频」在图生方式下因缺首帧给出「请先选择首帧图片」 —— Task 5「stale first-frame ref」。
2. **上传素材复用**：「换个版本」用原素材 id 直接提交，不要求重新上传 —— Task 3 纯逻辑 + Task 5。
3. **续写时用户切换方式**：续写来源存在时方式下拉被锁为图生（`disabled`），点提示条 × 解锁 —— Task 5「continue locks mode」。
4. **选择框里没有任何图片会话**：选择框显示空态、「取消」可关闭 —— Task 4。
5. **视频页首次打开前从图片页跳过来**：`useFirstFrame` 要先完成会话加载再填首帧，不被 `refresh` 覆盖 —— Task 5「useFirstFrame before first refresh」。

---

### Task 1: 后端——视频必须带会话、首帧引用

**Files:**
- Modify: `desk/media/service.py`（`__init__` 默认 `ref_slots`、`start_video_job`、`_start` 视频命令构造、`_history_entry`）
- Test: `tests/test_media_video_refs.py`（新建）；所有不带会话调用 `start_video_job` 的现有测试（`grep -rn "start_video_job(\|/api/media/video" tests desk/testing`）改为先建视频会话

**Interfaces:**
- Produces: `start_video_job(..., session_id)` 必填；`refs={"first_frame": {"kind":"image","session_id":…,"attempt_id":…}}` 生效；history 条目在 `refs` 非空时带顶层 `refs`

- [ ] **Step 1: 写失败测试 `tests/test_media_video_refs.py`**

```python
"""Video sessions: required session, first frame from an image session (spec V-01–V-05)."""
import pytest

from desk.media.service import MediaError
from media_fakes import finished_snapshot, make_service
from test_media_sessions_service import done_image, video


def video_session(deps):
    return deps.media_sessions["video"].create()["id"]


@pytest.mark.parametrize("session_id, code, status", [(None, "session_required", 400), ("f" * 32, "session_not_found", 404)])
def test_video_requires_a_session(tmp_path, session_id, code, status):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=session_id)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert deps.executor.spawned == []


def image_ref(deps, tmp_path):
    return {"kind": "image", "session_id": done_image(deps, tmp_path), "attempt_id": "a" * 32}


def test_first_frame_ref_becomes_the_first_frame_argument(tmp_path):
    service, deps = make_service(tmp_path)
    sid, ref = video_session(deps), image_ref(deps, tmp_path)
    snap = finished_snapshot(service, lambda: video(service, session_id=sid, mode="image", refs={"first_frame": ref}))
    cmd = deps.executor.spawned[-1]["cmd"]
    assert cmd[cmd.index("--first-frame") + 1] == str(tmp_path / "outputs" / "cat.png")
    attempt = deps.media_sessions["video"].get(sid)["attempts"][0]
    assert attempt["refs"] == {"first_frame": ref} and attempt["params"].get("first_frame") is None
    assert deps.history.entries[-1]["refs"] == {"first_frame": ref}
    assert snap["status"] == "done"


def test_history_has_no_refs_key_without_refs(tmp_path):
    service, deps = make_service(tmp_path)
    finished_snapshot(service, lambda: video(service, session_id=video_session(deps)))
    assert "refs" not in deps.history.entries[-1]


@pytest.mark.parametrize("extra", [{"mode": "text"}, {"mode": "image", "first_frame": "a" * 32 + ".png"}])
def test_first_frame_ref_conflicts_are_400(tmp_path, extra):
    service, deps = make_service(tmp_path)
    sid, ref = video_session(deps), image_ref(deps, tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, refs={"first_frame": ref}, **extra)
    assert (exc.value.code, exc.value.message) == ("invalid_params", "首帧只能从上传或图片会话二选一")
    assert deps.media_sessions["video"].get(sid)["attempts"] == []


def test_first_frame_ref_with_continues_is_400(tmp_path):
    service, deps = make_service(tmp_path)
    sid, ref = video_session(deps), image_ref(deps, tmp_path)
    first = finished_snapshot(service, lambda: video(service, session_id=sid))["attempt_id"]
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, mode="image", refs={"first_frame": ref}, continues=first)
    assert exc.value.code == "invalid_params"


def test_gone_first_frame_ref_is_404(tmp_path):
    service, deps = make_service(tmp_path)
    sid, ref = video_session(deps), image_ref(deps, tmp_path)
    (tmp_path / "outputs" / "cat.png").unlink()
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, mode="image", refs={"first_frame": ref})
    assert (exc.value.code, exc.value.http_status, exc.value.message) == ("ref_missing", 404, "引用的图片已不在")
```

- [ ] **Step 2:** `python3 -m pytest tests/test_media_video_refs.py -q` → FAIL

- [ ] **Step 3: 实现**
  - `__init__`：`self._ref_slots = ref_slots if ref_slots is not None else {"video": {"first_frame": "image"}}`（原为 `ref_slots or {}`）。已有测试里显式传 `ref_slots`/改 `_ref_slots` 的保持有效。
  - `start_video_job`：`session_id = self._check_session("video", session_id, required=True)`；在参数校验阶段（`continues` 冲突检查旁）加：

```python
        wants_ref_frame = isinstance(refs, dict) and "first_frame" in refs
        if wants_ref_frame and continues is not None:
            raise MediaError("invalid_params", CONTINUE_CONFLICT, 400)
        if wants_ref_frame and (mode != "image" or first_frame):
            raise MediaError("invalid_params", "首帧只能从上传或图片会话二选一", 400)
```

    `_video_assets(mode, …)` 在图生方式要求 `first_frame` 素材；有 `refs.first_frame` 时，素材表里不要求 `first_frame`（给 `_video_assets` 加参数 `first_from_ref: bool`，为真时图生只收 `last_frame`）。`_resolve_refs` 返回的 `paths["first_frame"]` 通过 `_start(..., ref_paths=paths)` 传入；`_start` 视频分支在构造 `command_params` 后：`if ref_paths.get("first_frame"): command_params["first_frame"] = ref_paths["first_frame"]`（`build_h3_command` 接受 Path）。`params` 中不写 `first_frame`（或写 `None` 且不传给命令）。
  - `_history_entry`：`if snap.get("refs"): entry["refs"] = snap["refs"]` —— 为此 `_state` 在作业开始时记 `refs`（由 `attempt_extra["refs"]` 取），`job_status` 快照里带出（`_state` 初值加 `"refs": None`，对应更新 `tests/test_media_service.py::test_initial_job_state_shape` 期望加 `"refs": None`）。
  - 所有不带会话的视频调用方改为建会话后传入（断言不放宽）。

- [ ] **Step 4:** `python3 -m pytest -q --ignore=tests/e2e` → 除 4 个已知外全过

- [ ] **Step 5: Commit** `feat(video-sessions): 视频必须带会话，首帧可引用图片会话里的图`

---

### Task 2: 控制器与卡片清理（通用 `attemptView`、`secondary` 命名）

**Files:**
- Modify: `desk/static/js/pure/media_session.js`、`desk/static/js/pure/image_session.js`、`desk/static/js/panes/media_session.js`、`desk/static/js/panes/image.js`、`desk/static/js/widgets/image_session_card.js`、`desk/static/js/widgets/music_session_card.js`
- Test: `tests/js/media_session.test.js`、`tests/js/music_pane.test.js`（文案「文件已不在」→「音频文件已不在」的断言按 V-10 更新）

**Interfaces:**
- Produces: `attemptView(attempt, {broken = false, noun = "图片"} = {})` 在 `pure/media_session.js`；控制器 `renderCard` 返回 `{node, running?, image?, secondary?}`，`composer.updateAvailability(state, {secondary})`；图片卡片参数 `secondaryBlockedReason`（原 `noImageReason`）

- [ ] **Step 1: 失败测试**（追加到 `tests/js/media_session.test.js`）

```js
import { attemptView } from "../../desk/static/js/pure/media_session.js";
test("attemptView names the missing file by noun", () => {
  const gone = { status: "done", output: "x", output_missing: true };
  assert.equal(attemptView(gone).title, "图片文件已不在");
  assert.equal(attemptView(gone, { noun: "音频" }).badge, "音频文件已不在");
  assert.equal(attemptView(gone, { noun: "视频" }).title, "视频文件已不在");
});
```

- [ ] **Step 2:** `node --test tests/js/media_session.test.js` → FAIL
- [ ] **Step 3: 实现**：把 `attemptView` 从 `pure/image_session.js` 移到 `pure/media_session.js`，missing 分支的 `badge`/`title` 用 `` `${noun}文件已不在` ``；`pure/image_session.js` 不再导出它（导入方改从 `media_session.js` 取）。音乐卡片删除自己的 missing 分支，改用 `attemptView(attempt, {broken, noun: "音频"})`。控制器与两张卡片、`image.js` 中 `recompose`→`secondary`、`recomposeRefs`→`secondaryRefs`、`noImageReason`→`secondaryBlockedReason` 全部改名（`grep -rn "recompose\b\|recomposeRefs\|noImageReason" desk/static tests/js`——`recomposeParams` 函数名保留，它是图片「换个构图」的业务名）。
- [ ] **Step 4:** `node --test tests/js/`（`image_pane.test.js` 不改断言仍全过）；`python3 -m pytest tests/e2e/test_image_sessions.py tests/e2e/test_music_sessions.py -q`
- [ ] **Step 5: Commit** `refactor(video-sessions): 卡片状态通用化，控制器接口去掉图片专属命名`

---

### Task 3: 视频纯逻辑 `pure/video_session.js`

**Files:**
- Create: `desk/static/js/pure/video_session.js`
- Test: `tests/js/video_session.test.js`

**Interfaces:**
- Consumes: `pure/media_session.js`（`ParamsError`、`SEED_MAX`、`randomSeed`、`attemptLabel`、`chainOf`）、`pure/music_session.js` 中可复用的 `chipText`/`submitContinues` 思路（不导入，视频文案不同）
- Produces:

```js
export const SIZES = [["512x288", "草稿 512×288"], ["768x448", "标准 768×448"], ["1024x576", "清晰 1024×576"]];
export const DURATIONS = [[49, "约 2 秒（快速）"], [73, "约 3 秒"], [124, "约 5 秒（常用）"], [192, "约 8 秒"], [243, "约 10 秒"], [362, "约 15 秒（最长）"]];
export const MODES = { text: "文生", image: "图生", reference: "参考" };
export const CANNOT_CONTINUE = "这一段没有生成好，不能接着往下生";
export function readVideoParams(values) → {prompt, width, height, frames, steps, seed?}        // 抛 ParamsError
export function durationLabel(frames) → string        // 最接近的 DURATIONS 标签去掉括号说明，如「约 3 秒」
export function specLine(params) → "512×288 · 约 3 秒 · 16 步"
export function sourceOf(attempt) → {type:"upload", id} | {type:"ref", ref} | {type:"continue", attemptId} | null   // 图生首帧来源
export function refineFields(attempt) → {mode, prompt, size:"WxH", frames, steps, seed, first, last, refVideo, useAudio}
export function versionParams(attempt, sessionId, draw = randomSeed) → 请求体（原参数 + 新种子 + 原 refs/continues/素材 id）
export function nextFields(attempt, current) → {size, frames, steps}     // compose 尝试返回 current
export function canContinue(attempt) → boolean
export function chipText(ref) → string       // {type:"refine"|"continue"|"library", index, missing?}
export function firstFrameLabel(source, {fileName, imageTitle, imageIndex, continueIndex}) → string
export function cardTitle(attempt, index, attempts) → string   // 同音乐规则
```

- [ ] **Step 1: 失败测试**

```js
import test from "node:test";
import assert from "node:assert/strict";
import * as v from "../../desk/static/js/pure/video_session.js";

const T = (id, extra = {}) => ({ id, status: "done", output: `${id}.mp4`, ts: "2026-09-27T10:00:00",
  params: { prompt: "雨夜街道", width: 512, height: 288, frames: 73, steps: 16, seed: 9 }, refs: {}, ...extra });

test("readVideoParams", () => {
  assert.deepEqual(v.readVideoParams({ prompt: "p", size: "768x448", frames: "124", steps: "16", seed: "" }),
    { prompt: "p", width: 768, height: 448, frames: 124, steps: 16 });
  assert.throws(() => v.readVideoParams({ prompt: " ", size: "512x288", frames: "49", steps: "16" }), /请填写视频提示词/);
  assert.throws(() => v.readVideoParams({ prompt: "p", size: "512x288", frames: "49", steps: "3" }), (e) => e.advanced && /步数须为 4–50 的整数/.test(e.message));
  assert.throws(() => v.readVideoParams({ prompt: "p", size: "512x288", frames: "49", steps: "16", seed: "x" }), /种子须为 0–4294967295 的整数/);
});

test("spec line and duration label", () => {
  assert.equal(v.specLine({ width: 512, height: 288, frames: 73, steps: 16 }), "512×288 · 约 3 秒 · 16 步");
  assert.equal(v.durationLabel(125), "约 5 秒");
});

test("sourceOf distinguishes upload, ref and continuation", () => {
  assert.deepEqual(v.sourceOf(T("a", { params: { ...T("a").params, mode: "image", first_frame: "f.png" } })), { type: "upload", id: "f.png" });
  const ref = { kind: "image", session_id: "s", attempt_id: "i" };
  assert.deepEqual(v.sourceOf(T("b", { params: { ...T("b").params, mode: "image" }, refs: { first_frame: ref } })), { type: "ref", ref });
  assert.deepEqual(v.sourceOf(T("c", { continues: "a", params: { ...T("c").params, mode: "image", first_frame: "x.png" } })), { type: "continue", attemptId: "a" });
  assert.equal(v.sourceOf(T("d")), null);
});

test("versionParams keeps assets, refs and continues with a new seed", () => {
  const ref = { kind: "image", session_id: "s", attempt_id: "i" };
  const a = T("b", { params: { ...T("b").params, mode: "image", use_audio: true, last_frame: "l.png" }, refs: { first_frame: ref } });
  const seeds = [9, 10];
  assert.deepEqual(v.versionParams(a, "s1", () => seeds.shift()), {
    session_id: "s1", prompt: "雨夜街道", width: 512, height: 288, frames: 73, steps: 16, seed: 10,
    mode: "image", use_audio: true, last_frame: "l.png", refs: { first_frame: ref } });
  const c = T("c", { continues: "a", params: { ...T("c").params, mode: "image", first_frame: "x.png", use_audio: true } });
  const p = v.versionParams(c, "s1", () => 1);
  assert.equal(p.continues, "a"); assert.equal("first_frame" in p, false); assert.equal("mode" in p, false);   // 续写由后端决定首帧与方式
});

test("next segment keeps size/frames/steps; compose keeps current", () => {
  assert.deepEqual(v.nextFields(T("a"), { size: "1024x576", frames: 49, steps: 20 }), { size: "512x288", frames: 73, steps: 16 });
  assert.deepEqual(v.nextFields({ id: "c", status: "done", output: "c.mp4", op: "compose", params: { parts: ["a", "b"] } }, { size: "1024x576", frames: 49, steps: 20 }),
    { size: "1024x576", frames: 49, steps: 20 });
});

test("chip and first-frame labels", () => {
  assert.equal(v.chipText({ type: "continue", index: 0 }), "接在第 1 次后面");
  assert.equal(v.chipText({ type: "continue", index: 0, missing: true }), "第 1 次的文件已不在，不能接着往下生");
  assert.equal(v.chipText({ type: "library" }), "沿用素材库里这段");
  assert.equal(v.firstFrameLabel({ type: "upload" }, { fileName: "cat.png" }), "已选择：cat.png");
  assert.equal(v.firstFrameLabel({ type: "ref" }, { imageTitle: "橘猫", imageIndex: 2 }), "首帧：图片会话「橘猫」第 3 次");
  assert.equal(v.firstFrameLabel({ type: "ref" }, {}), "首帧：来自图片会话");
  assert.equal(v.firstFrameLabel({ type: "continue" }, { continueIndex: 1 }), "接在第 2 次后面（用它的最后一帧）");
});
```

- [ ] **Step 2:** `node --test tests/js/video_session.test.js` → FAIL
- [ ] **Step 3: 实现**：照 `pure/music_session.js` 的写法实现上述函数（`readVideoParams`：提示词必填「请填写视频提示词」；`size` 形如 `WxH` 取自 SIZES 之一，否则高级参数错误「画幅无效」；`frames` 为 DURATIONS 中的值之一，否则「视频时长无效」；步数 4–50 整数「步数须为 4–50 的整数」；种子同音乐）。`versionParams`：续写尝试（`continues` 非空）只带 `session_id, prompt, width, height, frames, steps, seed, continues`；否则带原 `mode`（非 text 时）、`use_audio`、素材 id（`first_frame`/`last_frame`/`ref_video` 中非空者）、`refs`（非空时）。
- [ ] **Step 4:** `node --test tests/js/` 全过
- [ ] **Step 5: Commit** `feat(video-sessions): 视频会话纯逻辑`

---

### Task 4: 图片会话选择框 + 图片页「用这张生成视频」

**Files:**
- Create: `desk/static/js/widgets/image_picker.js`
- Modify: `desk/static/js/widgets/image_session_card.js`、`desk/static/js/panes/image.js`
- Test: `tests/js/image_picker.test.js`（新建）；`tests/js/image_pane.test.js` 只**新增**一个用例（不改旧断言）

**Interfaces:**
- Produces: `openImagePicker(doc, {listSessions, getSession, serveOutput}) → Promise<null | {ref:{kind:"image", session_id, attempt_id}, title, index}>`；图片页 `ctx.onUseAsFirstFrame(pick)`（pick 同上结构）

- [ ] **Step 1: 失败测试 `tests/js/image_picker.test.js`**（假 DOM 从 `tests/js/support/fake_dom.js`）：
  1. 两个会话，第一个有 done 图 2 张 + failed 1 张：打开后 `role=dialog`、标题「从图片会话选首帧」、左侧两项、右侧 2 个缩略图（failed 不出现）；点第二张 → Promise 解析为 `{ref:{kind:"image", session_id:"s1", attempt_id:"a2"}, title:"橘猫", index:1}`，对话框移除。
  2. 切到没有 done 图的会话 → 显示「这个会话还没有生成好的图片」。
  3. 点「取消」→ 解析为 `null`。
  4. 图片页：done 卡片展开后有按钮「用这张生成视频」，点击调用 `ctx.onUseAsFirstFrame` 参数 `{ref:{kind:"image", session_id:<当前会话>, attempt_id:<该尝试>}, title:<会话标题>, index:<序号>}`；文件不在的卡片没有该按钮。
- [ ] **Step 2:** `node --test tests/js/image_picker.test.js tests/js/image_pane.test.js` → 新用例 FAIL
- [ ] **Step 3: 实现**：选择框组件（结构参照 `widgets/confirm.js` 的模态做法：遮罩 + `role=dialog` + `aria-modal` + Esc/取消关闭 + 初始焦点在第一个会话）；缩略图 `<img alt=提示词摘要>`，`serveOutput(output)`；打开时 `listSessions()` 并默认选中第一个非坏会话，切换会话 `getSession(id)`。图片卡片在两个动作右侧加次级按钮（done 且 `!output_missing` 且未 broken 时），回调由 `image.js` 传入。
- [ ] **Step 4:** `node --test tests/js/`；`python3 -m pytest tests/e2e/test_image_sessions.py -q`
- [ ] **Step 5: Commit** `feat(video-sessions): 图片会话选择框，图片卡片可「用这张生成视频」`

---

### Task 5: 视频页

**Files:**
- Create: `desk/static/js/widgets/video_session_card.js`
- Modify: `desk/static/js/panes/video.js`（重写）、`desk/static/index.html:14-29`（`#pane-video`）、`desk/static/app.css`、`desk/static/js/main.js`；删除 `desk/static/js/widgets/jobview.js`（若不再被引用；同时删其专属测试用例）
- Test: `tests/js/video_pane.test.js`（新建）、`tests/js/media_panes.test.js`（删旧视频表单用例）；迁移 e2e：`tests/e2e/test_video_flow.py`、`test_image_flow.py`、`test_prompt_assist.py`、`test_library_panel.py`、`test_statusbar_memory.py`、`test_mutex_ui.py` 中的视频页交互

**Interfaces:**
- Consumes: `createSessionPane`（含 `togglePick`、`startCompose`、`cancelJob`、`keepInView`、`selectAttempt(id,{focus})`、`composer.updateAvailability(state,{secondary})`；挑选模式下控制器已处理卡片点击，卡片只接勾选框 `change`）、Task 3 纯逻辑、Task 4 选择框、`api.uploadMediaInput`、`api.startVideoJob`、`createPromptAssist`（task "video"、`mode()`）、`videoCostNote`
- Produces: `createVideoPane(root, ctx)` → `{refresh, applyJob, poll, applyFill, setHeavyAllowed, setModelStatus, setRuntimeStatus, setAssistAvailable, useFirstFrame(pick)}`

- [ ] **Step 1: HTML**：`#pane-video` 按 `#pane-music` 骨架重写，data 前缀 `video`：`data-video-session-new/-session-list/-model/-timeline/-composer/-chip/-chip-text/-chip-clear/-mode/-first-area/-first-upload`（隐藏 file input + 「上传图片」label）`/-first-pick`（「从图片会话选…」按钮）`/-first-label/-first-preview/-last-area/-last`（file input，「上传图片（可选）」）`/-last-label/-last-preview/-clear-last/-reference-area/-source/-source-label/-source-preview/-prompt/-start/-assist/-advanced/-size/-frames/-cost-note/-steps/-seed/-audio-row/-audio/-advanced-error/-upload-status/-hint/-hint-text/-return/-error`。拖放行沿用 `.file-row` 结构（issue #15 行为保留）。「模型说明」文案取 V-20。
- [ ] **Step 2: CSS**：所有 `#pane-image, #pane-music` 选择器扩成加 `#pane-video`；新增 `.video-prompt { min-height: calc(3 * 1.5em + 16px); max-height: 40vh; resize: none; }`、`.attempt-video { width: 100%; max-height: 50vh; background: #000; }`、首帧预览 `max-height: 160px`。
- [ ] **Step 3: 卡片 `widgets/video_session_card.js`**：以 `music_session_card.js` 为模板，差异：`<video controls preload="metadata" class="attempt-video">`；切换按钮文案「成片」「只看这一段」；折叠行加方式标签 `MODES[mode ?? "text"]` 与 `specLine`；首帧来源行（`sourceOf` 为 ref 时，文案由面板传入的 `firstFrameText(attempt)` 决定——面板从已加载的图片会话摘要里查标题与序号，查不到用「首帧：来自图片会话」）；动作「在这段基础上改」「换个版本」「接着往下生」（compose 尝试只有「接着往下生」；不可续写时 disabled + `CANNOT_CONTINUE`）；missing 用 `attemptView(attempt, {broken, noun:"视频"})`。
- [ ] **Step 4: 面板 `panes/video.js`**：以 `panes/music.js` 为模板，状态：`ref`（提示条）、`first`（首帧来源：`null | {type:"upload", file?, id?, name} | {type:"ref", ref, title, index} | {type:"continue", attemptId, index}`）、`last`、`refVideo`（`{file?, id?, name}`）。要点：
  - 方式切换显隐素材区；续写来源存在时方式下拉 `disabled` 且值为 image，首帧区按钮 disabled。
  - 上传：选择文件即预览（沿用现有 32 MB 与类型检查、拖放）；提交时未上传的先 `api.uploadMediaInput(file)` 得 id（上传状态行「正在上传 <文件名>…」→「正在提交生成任务…」），id 缓存到来源对象，重复生成不再上传。
  - 「从图片会话选…」：`openImagePicker(doc, {listSessions: () => api.listMediaSessions("image"), getSession: (id) => api.getMediaSession("image", id), serveOutput: api.serveOutput})`，选中 → `first = {type:"ref", …}`，首帧说明 `firstFrameLabel`，预览图。
  - 提交：`readVideoParams` → 组请求：`{session_id, …params}`；方式 image：续写来源 → `continues`（不带 mode/first_frame）；ref → `mode:"image", refs:{first_frame: ref}`；upload → `mode:"image", first_frame:id`；再加 `last_frame`（若有）与 `use_audio`；方式 reference → `mode:"reference", ref_video:id, use_audio`；缺首帧/参考视频时错误「请先选择首帧图片」/「请先选择参考视频」。沿用型提示条可见且被引用尝试有 `continues` → 带 `continues`（同 M-27，续写段「改」后仍接原位）。
  - 三个动作按 V-40–V-42；`refine` 回填 ref 首帧时检查该图是否仍 done 且在（`api.getMediaSession("image", ref.session_id)`；失败或找不到 → 首帧说明「引用的图片已不在」、`first = null`）。
  - `afterStart` 按 V-43。
  - `useFirstFrame(pick)`：`await pane.refresh()`（首次打开时加载会话），再设方式 image、`first = {type:"ref", …pick}`、说明、焦点到提示词。
  - 失效续写目标同音乐 M-28 逻辑（文案用 `chipText`）。
  - AI 帮写：`createPromptAssist(doc, els.assist, {task:"video", read: () => ({text: prompt}), write: ({text}) => …, mode: () => els.mode.value, confirm})`。
  - 耗时提示随画幅/时长变化（`videoCostNote`）。
- [ ] **Step 5: `main.js`**：
  - `onModels` 加 `panes.video.setModelStatus(models?.find((m) => m.key === "h3"))`；`tick` 加 `panes.video.setRuntimeStatus(capabilities?.mlx_h3)`、`await panes.video.poll(deskState)`，catch 分支加 `panes.video.setHeavyAllowed(false, "服务状态暂不可用，请稍后重试")`；
  - `showTab("video")` → `panes.video.refresh()`；`applyFill` 三种媒体统一 `showTab(plan.pane); panes[plan.pane].applyFill(plan)`；
  - `tickJob`：`panes[payload.kind]?.applyJob(payload, {replaceLog: changed})`（三种都走会话页）；删除 `jobView`、`mediaBusyReason` 中仅供 jobview 的部分；
  - 图片页构造传 `onUseAsFirstFrame: (pick) => { showTab("video"); panes.video.useFirstFrame(pick); }`。
  - `modelTexts`：视频「尚未安装视频模型，请到「资源」页下载」「视频 MLX 运行环境不可用，请检查服务或应用安装」。
- [ ] **Step 6: 视频页单测 `tests/js/video_pane.test.js`**（假 DOM 与 `fakeBackend("video")`；`fakeBackend` 需支持 `/api/media/inputs` 上传，返回 `{id}`）：
  1. 文生提交 body：含 `session_id`，无 `mode`、无 `seed`；
  2. 图生上传：选文件 → 提交先 `POST /api/media/inputs` 再 `POST /api/media/video` 带 `mode:"image", first_frame:<id>`；「换个版本」不再上传；
  3. 从图片会话选：打开选择框（调用注入的 picker 返回 pick）→ 首帧说明「首帧：图片会话「橘猫」第 3 次」→ 提交带 `refs.first_frame`、不带 `first_frame`；
  4. 接着往下生：提示词清空、方式锁图生、首帧说明「接在第 1 次后面（用它的最后一帧）」、提交带 `continues`、不带 `mode`；点提示条 × 解锁方式；
  5. stale first-frame ref：「在这段基础上改」一个 ref 首帧的尝试，而图片会话里那张已 `output_missing` → 首帧说明「引用的图片已不在」、提交报「请先选择首帧图片」；
  6. useFirstFrame before first refresh：未 refresh 时调用 `useFirstFrame(pick)` → 会话加载完成且首帧说明正确（不被覆盖）；
  7. 成片切换「成片」「只看这一段」；重新拼接；compose 尝试只有「接着往下生」；
  8. 主流程文本无「种子」。
  （为可测，`createVideoPane(root, ctx)` 接受 `ctx.pickImage`（默认 `openImagePicker` 包装）注入。）
- [ ] **Step 7: e2e 迁移**：`grep -rln "data-video-" tests/e2e` 中各文件的视频页交互改到新 DOM（保持各测试意图；原来断言 jobview 播放器的改为断言卡片 `<video>`；逐条写进报告）。
- [ ] **Step 8:** `node --test tests/js/`；`python3 -m pytest -q --ignore=tests/e2e`；`python3 -m pytest tests/e2e -q` 全过；`grep -rn "jobView\|jobview" desk/static` 无输出（`jobview.js` 已删则连文件名也无）。
- [ ] **Step 9: Commit** `feat(video-sessions): 视频页改成会话式——三个动作、成片、从图片会话选首帧`

---

### Task 6: 视频会话 e2e

**Files:**
- Create: `tests/e2e/test_video_sessions.py`

- [ ] **Step 1: 写测试**（夹具与脚本化作业照 `tests/e2e/test_music_sessions.py`）：
  1. `#tab=video` 自动新会话；文生：写提示词 → 生成 → 完成 → 第 1 张卡展开有 `<video>`；
  2. 「接着往下生」→ 提示条「接在第 1 次后面」、首帧说明「接在第 1 次后面（用它的最后一帧）」、方式下拉 disabled → 写提示词 → 生成 → 第 2 张卡「接第 1 次」，展开有「成片」「只看这一段」；会话文件 `continues` 正确、`joined_output` 非空；
  3. 切到 `#tab=image`，生成一张图 → 展开卡片点「用这张生成视频」→ 回到视频页，方式为图生、首帧说明「首帧：图片会话「<标题>」第 1 次」→ 生成 → 会话文件里该尝试 `refs.first_frame == {kind:"image", session_id, attempt_id}`；
  4. 「挑几段合成…」选两段 → 合成 → 合成卡片出现；
  5. 900×700：无横向滚动；主流程文本（排除高级参数折叠）无「种子」。
- [ ] **Step 2:** `python3 -m pytest tests/e2e/test_video_sessions.py -q`（失败则修页面，不改期望）
- [ ] **Step 3: 全量回归**三条命令全过
- [ ] **Step 4: Commit** `test(video-sessions): 视频会话 e2e——续写、用图片作首帧、挑选合成`
