# 音乐会话 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把图片页的会话前端抽成共用控制器，并在其上把音乐页改成会话式（三个动作、成片播放、重新拼接、挑选合成），图片页行为不变。

**Architecture:** `panes/media_session.js::createSessionPane` 承担与媒体种类无关的会话流程（列表、时间线、轮询、改名删除、忙碌原因、滚动、挑选合成）；页面通过 `renderCard` / `composer` / `startJob` 注入种类专属部分。纯逻辑分三层：`pure/media_session.js`（通用）、`pure/image_session.js`（图片）、`pure/music_session.js`（音乐）。后端只把音乐 `session_id` 改为必填。

**Tech Stack:** 原生 ES module 前端（`node --test` 假 DOM 单测）、Playwright e2e（`tests/e2e`）、Python 后端（pytest）。

**Spec:** `docs/superpowers/specs/2026-09-27-music-sessions-design.md`（M-xx）；上游 `2026-09-24-image-sessions-design.md`（IS D-xx）、`2026-09-25-media-sessions-base-design.md`（B-xx）。

## Global Constraints

- 图片页零回归（M-04）：`tests/js/image_pane.test.js`、`tests/e2e/test_image_sessions.py`、`tests/e2e/test_image_flow.py` 的断言不改，只允许改 import 路径与挂载方式；图片页 DOM 文本、按钮、文案逐字不变。
- 「种子」二字只出现在「高级参数」折叠区（IS D-50、M-25）。
- 音乐文案（逐字）：空会话「还没有歌曲」／「在下面写风格描述和歌词，点「生成歌曲」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着写下一段」。」；提示条「沿用第 N 次」「接在第 N 次后面」「沿用素材库里这首」「第 N 次的文件已不在，不能接着写」；按钮「生成歌曲」「在这段基础上改」「换个版本」「接着写下一段」「挑几段合成…」「合成（K 段）」「取消」「重新拼接」；原因「至少要有两段完成的才能合成」「至少选两段」「这一段没有生成好，不能接着写」「链上有一段已不在」；成片问题「这一段生成好了，但成片没拼成：<原因>」。
- 音乐参数：风格描述、歌词必填；时长 10–300 整数（默认 60）；种子 0–4294967295，留空不传；高级参数错误前缀「高级参数里的数值有误：」。
- 台面未发布：不留兼容层；`widgets/image_session_list.js` 改名后旧文件删除。
- 测试命令：`node --test tests/js/`；`python3 -m pytest -q --ignore=tests/e2e`（`tests/test_shell_window.py` 的 4 个失败在未改动的 main 上同样失败，属环境问题，只忽略这 4 个）；改了 `desk/static` 必须跑 `python3 -m pytest tests/e2e -q`。
- 提交信息中文，`feat(music-sessions): …` / `refactor(music-sessions): …`，结尾 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。

## Review Focus

1. **续写目标在用户写歌词期间被删掉（会话被删或文件没了）**：提示条变「第 N 次的文件已不在，不能接着写」，「生成歌曲」禁用，× 可回到普通生成 —— Task 5 纯逻辑测试 + Task 6 页面测试「stale continuation chip」。
2. **挑选合成中途作业开始 / 切换会话**：合成按钮禁用并显示忙碌原因；切会话退出模式、清空已选 —— Task 4「picking exits on switch」「picking disabled while busy」。
3. **compose 尝试上的动作**：只有「接着写下一段」，且回填不覆盖输入区的风格描述与时长 —— Task 5「compose attempt next-segment keeps inputs」。
4. **重新拼接的链中间缺一段**：按钮禁用、原因「链上有一段已不在」 —— Task 5「chain with gap」+ Task 6。
5. **图片页在重构后的忙碌原因文案**（「「<标题>」正在生成图片」「正在生成这个会话里的第 N 次」）逐字不变 —— Task 2 纯逻辑测试以 `noun: "图片"` 断言原文案。

---

## File Structure

| 文件 | 动作 | 职责 |
|---|---|---|
| `desk/media/service.py`、`tests/test_media_sessions_service.py`、`tests/test_media_service.py` 等 | 改 | 音乐 `session_id` 必填（Task 1） |
| `desk/static/js/pure/media_session.js` | 新建 | 通用纯逻辑（Task 2） |
| `desk/static/js/pure/image_session.js` | 改 | 只留图片专属（Task 2） |
| `desk/static/js/widgets/session_list.js` | 新建（由 `image_session_list.js` 改名） | 会话列表项（Task 3） |
| `desk/static/js/panes/media_session.js` | 新建 | 共用控制器（Task 3、4） |
| `desk/static/js/panes/image.js` | 改 | 用控制器（Task 3） |
| `desk/static/js/pure/music_session.js` | 新建 | 音乐纯逻辑（Task 5） |
| `desk/static/js/widgets/music_session_card.js` | 新建 | 音乐卡片（Task 6） |
| `desk/static/js/panes/music.js`、`desk/static/index.html`、`desk/static/app.css` | 改 | 音乐页（Task 6） |
| `desk/static/js/main.js`、`desk/static/js/api.js` | 改 | 接通（Task 6/7） |
| `tests/js/media_session_pane.test.js`、`tests/js/music_session.test.js`、`tests/js/music_pane.test.js`、`tests/e2e/test_music_sessions.py` | 新建 | 测试 |

---

### Task 1: 音乐生成必须带会话

**Files:**
- Modify: `desk/media/service.py`（`start_music_job` 里 `_check_session("music", session_id, required=...)`）
- Test: `tests/test_media_sessions_service.py`，以及所有不带 `session_id` 调 `start_music_job` 的现有测试（`grep -rn "start_music_job(" tests/`）

**Interfaces:**
- Produces: `start_music_job(..., session_id)` 缺失/非字符串 → `MediaError("session_required", "请先选择或新建一个会话", 400)`；不存在 → `MediaError("session_not_found", "这个会话已被删除，请选择或新建一个会话", 404)`

- [ ] **Step 1: 写失败测试**（追加到 `tests/test_media_sessions_service.py`）

```python
@pytest.mark.parametrize("session_id, code, status", [(None, "session_required", 400), (7, "session_required", 400),
                                                      ("f" * 32, "session_not_found", 404)])
def test_music_requires_a_session(tmp_path, session_id, code, status):
    service, deps = make_service(tmp_path)
    music_ready(service, tmp_path)
    with pytest.raises(MediaError) as exc:
        music(service, session_id=session_id)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert deps.executor.spawned == []
```

- [ ] **Step 2:** Run `python3 -m pytest tests/test_media_sessions_service.py -q -k music_requires` → FAIL（None 时作业照常启动）

- [ ] **Step 3: 实现**：`start_music_job` 里把 `required=refs is not None or continues is not None` 改为 `required=True`。删掉/改写 `test_video_and_music_without_session_still_run_unattached` 里音乐部分（视频仍可省略会话）。其余不带会话的音乐测试（`tests/test_media_service.py` 的音乐成功路径、`tests/test_media_routes.py`、`tests/test_media_memory_estimate.py` 等，按 grep 结果）改为先 `deps.media_sessions["music"].create()["id"]` 再传 `session_id=`；断言不放宽。

- [ ] **Step 4:** Run `python3 -m pytest -q --ignore=tests/e2e` → 除 4 个已知 shell_window 外全过

- [ ] **Step 5: Commit** `feat(music-sessions): 音乐生成必须带会话`

---

### Task 2: 通用纯逻辑 `pure/media_session.js`

**Files:**
- Create: `desk/static/js/pure/media_session.js`
- Modify: `desk/static/js/pure/image_session.js`（删掉移走的函数，改为从 `media_session.js` 导入自用的）、所有 import 这些函数的文件（`grep -rn "pure/image_session.js" desk/static tests/js`）
- Test: `tests/js/media_session.test.js`（新建）；`tests/js/image_session.test.js` 中针对被移走函数的用例移到新文件（断言不变）

**Interfaces:**
- Produces（`pure/media_session.js` 导出）：`SEED_MAX`、`autoTitle(text)`、`sessionTitle(summary)`、`sessionMeta(summary)`、`attemptLabel(index, attempt)`、`runningLabel(index, elapsedSeconds)`、`randomSeed(cryptoImpl?)`、`orderSessions(list, freshId?)`、`pickCurrent(sessions, preferredId?)`、`ParamsError`、`runningSessionId(job, sessions, kind)`、`availability(state, {noun})`、`deleteMessage(summary, {noun})`、`startErrorText(error)`、`chainOf(attempt, attempts) → {items, gap}`（Task 5 用，见下）。
- `pure/image_session.js` 保留：`DEFAULT_PARAMS`、`specLine`、`attemptView`、`refineFields`、`REFINE_STRENGTH`、`RECOMPOSE_STRENGTH`、`NO_IMAGE_REASON`、`hasImage`、`recomposeParams`、`submitBase`、`baseLabel`、`refineChipVisible`、`refineChipText`、`readImageParams`（`readImageParams` 与 `recomposeParams` 从 `media_session.js` 导入 `ParamsError`、`SEED_MAX`、`randomSeed`）。

- [ ] **Step 1: 写失败测试 `tests/js/media_session.test.js`**

```js
import test from "node:test";
import assert from "node:assert/strict";
import { availability, deleteMessage, runningSessionId, chainOf } from "../../desk/static/js/pure/media_session.js";

const ready = { listState: "ready", currentId: "s1", current: { attempts: [] }, sessions: [{ id: "s1" }, { id: "s2", title: "旧歌", running: true }],
  allowed: true, busyReason: "", runtimeReason: "", modelReason: "" };

test("availability keeps the image wording with noun 图片 and says 歌曲 for music", () => {
  const job = { kind: "image", status: "running", session_id: "s2" };
  assert.equal(availability({ ...ready, job }, { noun: "图片" }).reason, "「旧歌」正在生成图片");
  const music = { kind: "music", status: "running", session_id: "s2" };
  assert.equal(availability({ ...ready, job: music, kind: "music" }, { noun: "歌曲" }).reason, "「旧歌」正在生成歌曲");
});

test("runningSessionId only follows jobs of its own kind", () => {
  const sessions = [{ id: "s1" }];
  assert.equal(runningSessionId({ kind: "music", status: "running", session_id: "s1" }, sessions, "image"), null);
  assert.equal(runningSessionId({ kind: "music", status: "running", session_id: "s1" }, sessions, "music"), "s1");
});

test("deleteMessage names the noun", () => {
  assert.equal(deleteMessage({ title: "晚风" }, { noun: "歌曲" }),
    "确定删除「晚风」？只删除这个会话分组，其中的歌曲仍保留在素材库。");
  assert.match(deleteMessage({ title: "猫", running: true }, { noun: "图片" }), /这个会话正在生成图片，生成会继续完成，图片会进入素材库/);
});

test("chainOf walks continues back and reports a gap", () => {
  const attempts = [{ id: "a" }, { id: "b", continues: "a" }, { id: "c", continues: "b" }, { id: "d", continues: "zz" }];
  assert.deepEqual(chainOf(attempts[2], attempts).items.map((x) => x.id), ["a", "b", "c"]);
  assert.equal(chainOf(attempts[2], attempts).gap, false);
  const broken = chainOf(attempts[3], attempts);
  assert.deepEqual(broken.items.map((x) => x.id), ["d"]); assert.equal(broken.gap, true);
});
```

- [ ] **Step 2:** `node --test tests/js/media_session.test.js` → FAIL（模块不存在）

- [ ] **Step 3: 实现**：把 `pure/image_session.js` 中列在 Produces 里的函数**原样**搬到新文件（含注释），做且只做这些参数化：
  - `runningSessionId(job, sessions, kind)`：原来的两处 `job.kind === "image"` 改为 `job.kind === kind`。
  - `availability(state, { noun })`：调用 `runningSessionId(s.job, s.sessions, s.kind ?? "image")`；「正在生成图片」改为 `` `「${sessionTitle(other)}」正在生成${noun}` ``。
  - `deleteMessage(summary, { noun })`：两处「图片」换成 `${noun}`。
  - 新增：

```js
// 沿 continues 在同一会话的尝试里回溯到链首（M-31、M-41）；前段不在列表里时 gap=true。
export function chainOf(attempt, attempts) {
  const byId = new Map((attempts ?? []).map((a) => [a?.id, a]));
  const items = []; const seen = new Set(); let cursor = attempt; let gap = false;
  while (cursor) {
    if (seen.has(cursor.id)) { gap = true; break; }
    seen.add(cursor.id); items.push(cursor);
    if (!cursor.continues) break;
    cursor = byId.get(cursor.continues);
    if (!cursor) gap = true;
  }
  return { items: items.reverse(), gap };
}
```

  `image.js` 调用改为 `availability({...}, { noun: "图片" })`、`deleteMessage(summary, { noun: "图片" })`（本任务先改调用点，Task 3 再整体搬走）；`image_session_list.js` 的 import 改到 `media_session.js`。

- [ ] **Step 4:** `node --test tests/js/` → 全过（`image_pane.test.js` 断言未改）

- [ ] **Step 5: Commit** `refactor(music-sessions): 会话通用纯逻辑移到 pure/media_session.js`

---

### Task 3: 共用会话控制器，图片页改用它

**Files:**
- Create: `desk/static/js/panes/media_session.js`
- Create: `desk/static/js/widgets/session_list.js`（`git mv desk/static/js/widgets/image_session_list.js desk/static/js/widgets/session_list.js`；类名 `image-session` 保留在图片页生成的项上——`renderSessionItem` 增加 `{kindClass}` 参数，图片页传 `"image-session"`，音乐页传 `"music-session"`）
- Modify: `desk/static/js/panes/image.js`
- Test: `tests/js/image_pane.test.js`（只允许改 import 与 `makePane` 挂载）、`tests/js/media_session_pane.test.js`（新建）

**Interfaces:**
- Consumes: Task 2 的 `pure/media_session.js`
- Produces:

```js
export function createSessionPane(root, {
  kind, noun, dataPrefix, emptyLines,
  renderCard,            // (doc, {attempt, index, attempts, selected, job, broken, onBroken, onImageLoad, picking, pickIndex}) → {node, running?, image?, recompose?}
  fitExpanded,           // 可选 (image, roomPx) → void，只有图片页传（IS D-74 大图自适应）
  composer,              // {read(), afterStart({fromInputs}), onSessionSwitch(), focus(), updateAvailability(state)}
  startJob,              // (params) → Promise<job>
  canCompose = false,    // Task 4
  confirm, onStarted,
}) → {
  refresh, applyJob, poll, applyFill, setHeavyAllowed, setModelStatus, setRuntimeStatus,
  startGeneration(params, {fromInputs}), currentId(), currentSession(), selectAttempt(id, {scrollIntent}),
  availability(), setError(text), settleView(), rerender(),
}
```

`setModelStatus(status)` / `setRuntimeStatus(capability)` 的文案由参数 `modelTexts = {missing, runtime}` 提供（图片：「尚未安装图片模型，请到「资源」页下载」「图片 MLX 运行环境不可用，请检查服务或应用安装」；音乐见 Task 6）。

- [ ] **Step 1: 控制器搬迁清单（逐项照搬 `panes/image.js` 现有代码，只做列出的替换）**

| `image.js` 现有部分 | 去向 | 替换 |
|---|---|---|
| 状态变量（sessions/listState/…/scrollIntent/broken） | 控制器 | 去掉 `refineRef` |
| `currentAvailability` / `updateAvailability` | 控制器 | `availability({...state, kind}, {noun})`；按钮与提示行的 DOM 更新交给 `composer.updateAvailability(state)`（图片页里放原来操作 `els.start`/`els.hint*`/`els.returnBtn`/`els.model`/`recomposeRefs` 的代码）；「回到该会话」按钮由控制器绑定 |
| `setModelStatus` / `setRuntimeStatus` / `setHeavyAllowed` | 控制器 | 文案取 `modelTexts` |
| `renderList` / `beginRename` / `removeSession` / `reloadList` | 控制器 | api 调用用 `kind`；`deleteMessage(summary, {noun})`；重试按钮 dataset 名 `${dataPrefix}SessionsRetry` |
| `emptyBlock` / `renderTimeline` | 控制器 | 空态文案 `emptyLines`；卡片由 `renderCard` 产出；`ol` 类名 `image-attempts` 改为 `session-attempts ${dataPrefix}-attempts`（CSS 同步：给 `.image-attempts` 现有规则加上 `.session-attempts` 选择器） |
| 滚动与大图（`IMAGE_FLOOR`…`selectAttempt`） | 控制器 | `fitExpandedImage` 改为：有 `expandedRefs.image` 且传了 `fitExpanded` 时计算 room 后调用 `fitExpanded(image, room)` |
| `applyRunningDetails` | 控制器 | 不变（`runningLabel`、`parseStepProgress`） |
| `loadSession` / `switchTo` / `selectSession` / `focusSession` / `refresh` / `createSession` | 控制器 | `switchTo` 里原 `clearSeedAndChip()` 改为 `composer.onSessionSwitch()`；新建后 `composer.focus()` |
| `submitWithMemoryConfirm` / `startGeneration` | 控制器 | `api.startImageJob` → `startJob`；`if (fromInputs) clearSeedAndChip()` → `composer.afterStart({fromInputs})`；session_not_found 文案中「生成图片」改为从 `composer.startLabel`（图片「生成图片」，音乐「生成歌曲」）取 |
| `cancelJob` / `applyJob` / `poll` | 控制器 | `payload.kind !== "image"` → `!== kind` |
| `applyFill` | 控制器 | 参数 `(plan, {refine, prefillOnly})`：找到尝试时调 `refine(attempt, index)`，否则调 `prefillOnly(fields)` —— 两个回调由页面传入 |
| `syncChip` / `clearSeedAndChip` / `prefill` / `refine` / `recompose` / `readInputs` / `startFromInputs` / 事件绑定里与输入区相关的 | 留在 `image.js` | `startFromInputs` 调 `pane.startGeneration(...)`；`recompose` 调 `pane.startGeneration(recomposeParams(attempt, pane.currentId(), drawSeed), {fromInputs:false})` |

`image.js` 变为：

```js
export function createImagePane(root, ctx = {}) {
  // els（只剩输入区元素）、refineRef、drawSeed、prefill/refine/recompose/syncChip…
  const pane = createSessionPane(root, {
    kind: "image", noun: "图片", dataPrefix: "image",
    emptyLines: ["还没有图片", "在下面写下想要的画面，点「生成图片」。之后可以在任意一张上「在这张基础上改」或「换个构图」。"],
    modelTexts: { missing: "尚未安装图片模型，请到「资源」页下载", runtime: "图片 MLX 运行环境不可用，请检查服务或应用安装" },
    renderCard: (doc, o) => renderAttemptCard(doc, { ...o, serveOutput: api.serveOutput,
      baseText: baseLabel(o.attempt, o.attempts), noImageReason: hasImage(o.attempt) ? "" : NO_IMAGE_REASON,
      onRefine: refine, onRecompose: recompose, onCancel: () => pane.cancelJob() }),
    fitExpanded: (image, room) => { image.style.maxHeight = `min(60vh, ${Math.max(192, Math.floor(room))}px)`; },
    composer: { startLabel: "生成图片", afterStart, onSessionSwitch: clearSeedAndChip, focus: () => els.prompt.focus?.(), updateAvailability },
    startJob: api.startImageJob, confirm: ctx.confirm, onStarted: ctx.onStarted,
  });
  // …输入区事件绑定…
  return { refresh: pane.refresh, applyJob: pane.applyJob, poll: pane.poll,
    applyFill: (plan) => pane.applyFill(plan, { refine, prefillOnly: (fields) => prefill(fields, { seed: fields.seed ?? null, index: null }) }),
    setHeavyAllowed: pane.setHeavyAllowed, setModelStatus: pane.setModelStatus, setRuntimeStatus: pane.setRuntimeStatus };
}
```

（`cancelJob` 也作为控制器返回值导出。）

- [ ] **Step 2: 控制器通用测试 `tests/js/media_session_pane.test.js`**：新建 `tests/js/support/fake_dom.js`，导出从 `image_pane.test.js` 顶部复制的 `Element`、`walk`/`findAll`/`find`/`byData`/`button`/`flush`、`mainFlowText(node, advancedClassRe)`，以及参数化的 `fakeBackend(kind)`（URL 用 `/api/media-sessions/${kind}` 与 `/api/media/${kind}`，另回应 `POST /api/media/compose` 追加一个 `op:"compose"` 的 running 尝试）和 `makeGenericPane(options)`（按 `dataPrefix` 建好控制器需要的 data 元素并挂一个最小假页面）。`image_pane.test.js` 不改，保留自己的副本。本测试文件从 support 导入；用一个最小假页面（`renderCard` 画一个 `li` 带 `dataset.attemptId`，`composer` 全部空函数）挂 `kind: "music", noun: "歌曲"`，测试：
  1. 首次 `refresh()` 列表为空 → 自动 `POST /api/media-sessions/music` 并选中；
  2. 有 running 尝试的会话优先被选中；
  3. `applyJob({kind:"image",…})` 被忽略，`applyJob({kind:"music", status:"running", session_id, attempt_id})` 更新该卡片；
  4. 删除当前会话后按 `pickCurrent` 重选，列表空了自动新建；
  5. 别的会话在生成时 `availability().reason === "「<标题>」正在生成歌曲"`。
  每条写成独立 `test(...)`，断言对 `state.calls` 与 DOM。

- [ ] **Step 3:** `node --test tests/js/` → 新测试 FAIL（控制器不存在）

- [ ] **Step 4: 实现**：按 Step 1 清单完成搬迁。`tests/js/image_pane.test.js` 只允许两处变化：import 不变（仍 `createImagePane`）；若 `makePane` 的 `root.querySelector` 需要额外 data 名（如控制器新增的工具行容器），在 `names` 数组里补名字——**不改任何断言**。

- [ ] **Step 5:** `node --test tests/js/` 全过；`python3 -m pytest tests/e2e -q` 全过（图片 e2e 不改）

- [ ] **Step 6: Commit** `refactor(music-sessions): 会话流程抽成共用控制器，图片页改用它`

---

### Task 4: 挑选合成模式（控制器）

**Files:**
- Modify: `desk/static/js/panes/media_session.js`、`desk/static/js/api.js`
- Test: `tests/js/media_session_pane.test.js`

**Interfaces:**
- Consumes: Task 3 控制器
- Produces: 控制器返回值新增 `togglePick(attemptId)`、`startCompose(parts) → Promise`（提交 compose；成功选中新尝试，失败把错误写到合成栏错误行——不在挑选模式时写到页面错误行）、`cancelJob()`；`api.startComposeJob({kind, session_id, parts})` → `POST /api/media/compose`；控制器选项 `canCompose: true` 时启用；DOM：工具行按钮 `[data-<prefix>-compose-start]`（控制器在时间线容器之前插入一个 `div.session-toolbar`，由控制器创建，不要求 HTML 预置）、合成栏 `div.compose-bar[data-<prefix>-compose-bar]`（控制器创建，插在 composer 容器位置，进入模式时隐藏 `[data-<prefix>-composer]`）；`renderCard` 收到 `picking`（bool）与 `pickIndex`（0 起，未选为 -1），页面负责画勾选框与序号，勾选框 `change`/卡片点击调用控制器传入的 `onTogglePick(attempt)`。

- [ ] **Step 1: 写失败测试**（追加）

```js
test("compose picking: order, reorder, min two, submit, exit", async () => {
  const backend = fakeBackend("music");
  const s = backend.addSession("歌", [done("a1", "x.wav"), done("a2", "y.wav"), done("a3", "z.wav")]);
  globalThis.fetch = backend.fetch;
  const { pane, root } = makeGenericPane({ kind: "music", noun: "歌曲", canCompose: true }); pane.ready(); await pane.refresh();
  const startBtn = byData(root, "musicComposeStart"); assert.equal(startBtn.disabled, false);
  await startBtn.click();
  pane.togglePick("a3"); pane.togglePick("a1");
  const bar = byData(root, "musicComposeBar");
  assert.match(bar.textContent, /第 3 次.*第 1 次/s);
  assert.equal(button(bar, "合成（2 段）").disabled, false);
  await button(bar, "上移第 1 次").click();           // a1 升到第一
  await button(bar, "合成（2 段）").click();
  const call = backend.calls.at(-1);
  assert.deepEqual(call, { url: "/api/media/compose", method: "POST", body: { kind: "music", session_id: s.id, parts: ["a1", "a3"] } });
  assert.equal(byData(root, "musicComposeBar")?.hidden ?? true, true);   // 退出模式
});

test("compose picking needs two done segments and exits on session switch", async () => { /* 仅 1 个 done → 按钮 disabled 且 title「至少要有两段完成的才能合成」；进入模式后切换会话 → 合成栏隐藏、已选清空 */ });

test("compose picking disabled while a job runs", async () => { /* 有 running 作业时「合成（2 段）」disabled，原因行为 IS §7.6 第一条原因 */ });
```

（`done(id, output)` 辅助：`{id, status:"done", output, params:{caption:"c", lyrics:"l", duration:20, seed:1}}`；`makeGenericPane` 是 Task 3 测试文件里的假页面工厂，返回的 `pane` 另暴露测试用 `togglePick(id)`——控制器把 `togglePick` 作为返回值的一部分导出，页面卡片也用它。后两个测试按注释写出完整断言。）

- [ ] **Step 2:** `node --test tests/js/media_session_pane.test.js` → FAIL

- [ ] **Step 3: 实现**：控制器新增状态 `picking=false`、`picks=[]`（attempt id 顺序）；`togglePick(id)` 只接受 `done` 且未 `output_missing` 的尝试；合成栏内容：每项「第 N 次」+ 三个图标按钮（`aria-label` 为「上移第 N 次」「下移第 N 次」「移除第 N 次」），主按钮文本 `合成（${picks.length} 段）`，`disabled = picks.length < 2 || availability().disabled`，原因行 `picks.length < 2 ? "至少选两段" : availability().reason`；「取消」退出；`switchTo`、`createSession` 退出模式；提交成功（调用 `api.startComposeJob`，经与生成相同的 `submitWithMemoryConfirm` 以外的直接调用——compose 没有内存确认）后退出模式、`onStarted`、`selectedId = started.attempt_id`、重载会话；失败时错误写在合成栏错误行（`describeJobError(error).title || error.message`，`capability_missing` 显示 `error.message`）。工具行按钮在不足两段可合成时 `disabled` + `title = "至少要有两段完成的才能合成"`。`api.js` 增加 `export const startComposeJob = (params) => json("/api/media/compose", "POST", params);`（`ROUTES.compose`）。

- [ ] **Step 4:** `node --test tests/js/` 全过

- [ ] **Step 5: Commit** `feat(music-sessions): 共用控制器支持挑选几段合成`

---

### Task 5: 音乐纯逻辑 `pure/music_session.js`

**Files:**
- Create: `desk/static/js/pure/music_session.js`
- Test: `tests/js/music_session.test.js`

**Interfaces:**
- Consumes: `pure/media_session.js`（`ParamsError`、`SEED_MAX`、`randomSeed`、`chainOf`）、`pure/job_error.js::describeJobError`
- Produces:

```js
export const DEFAULT_DURATION = 60;
export function readMusicParams({caption, lyrics, duration, seed}) → {caption, lyrics, duration, seed?}   // 抛 ParamsError
export function refineFields(attempt) → {caption, lyrics, duration, seed}
export function nextFields(attempt, current) → {caption, duration}      // M-35：compose 尝试返回 current 的值
export function versionParams(attempt, sessionId, draw = randomSeed) → {session_id, caption, lyrics, duration, seed, continues?}
export function canContinue(attempt) → boolean                          // done 且 output 在
export const CANNOT_CONTINUE = "这一段没有生成好，不能接着写";
export function chipText(ref) → string      // ref: {type:"refine"|"continue", index|null, missing?}
export function submitContinues(ref, seedInput) → string|null           // M-27
export function cardTitle(attempt, index, attempts) → string            // M-30 标题行
export function lyricsPreview(lyrics) → string                          // 首个非空非 [标记] 行
export function chainLine(attempt, attempts) → string                   // 「由：第 1 次 → 第 3 次」，gap 时以「… → 」开头；单段返回 ""
export function joinProblem(attempt, attempts) → null | {text, rejoin: null | {parts} , reason}
```

- [ ] **Step 1: 写失败测试**

```js
import test from "node:test";
import assert from "node:assert/strict";
import * as m from "../../desk/static/js/pure/music_session.js";

const A = (id, extra = {}) => ({ id, status: "done", output: `${id}.wav`, ts: "2026-09-27T10:0" + id.length + ":00",
  params: { caption: "民谣", lyrics: "[verse]\n早晨的风\n吹过窗", duration: 30, seed: 11 }, ...extra });

test("readMusicParams validates and omits empty seed", () => {
  assert.deepEqual(m.readMusicParams({ caption: "民谣", lyrics: "la", duration: "30", seed: "" }), { caption: "民谣", lyrics: "la", duration: 30 });
  assert.throws(() => m.readMusicParams({ caption: " ", lyrics: "la", duration: "30" }), /请填写风格描述/);
  assert.throws(() => m.readMusicParams({ caption: "a", lyrics: " ", duration: "30" }), /请填写歌词/);
  assert.throws(() => m.readMusicParams({ caption: "a", lyrics: "l", duration: "5" }), (e) => e.advanced && /高级参数里的数值有误：时长须为 10–300 的整数/.test(e.message));
  assert.throws(() => m.readMusicParams({ caption: "a", lyrics: "l", duration: "30", seed: "-1" }), /种子须为 0–4294967295 的整数/);
});

test("versionParams keeps continues and draws a different seed", () => {
  const seeds = [11, 11, 42];
  const p = m.versionParams(A("b", { continues: "a" }), "s1", () => seeds.shift());
  assert.deepEqual(p, { session_id: "s1", caption: "民谣", lyrics: "[verse]\n早晨的风\n吹过窗", duration: 30, seed: 42, continues: "a" });
  assert.equal("continues" in m.versionParams(A("a"), "s1", () => 5), false);
});

test("next segment: keeps caption/duration; compose attempt keeps inputs", () => {
  assert.deepEqual(m.nextFields(A("a"), { caption: "x", duration: 99 }), { caption: "民谣", duration: 30 });
  assert.deepEqual(m.nextFields({ id: "c", status: "done", output: "c.wav", params: { parts: ["a", "b"] } }, { caption: "x", duration: 99 }),
    { caption: "x", duration: 99 });
  assert.equal(m.canContinue(A("a")), true);
  assert.equal(m.canContinue(A("a", { output_missing: true })), false);
  assert.equal(m.canContinue({ id: "f", status: "failed" }), false);
});

test("chip texts and stale continuation", () => {
  assert.equal(m.chipText({ type: "refine", index: 1 }), "沿用第 2 次");
  assert.equal(m.chipText({ type: "refine", index: null }), "沿用素材库里这首");
  assert.equal(m.chipText({ type: "continue", index: 2 }), "接在第 3 次后面");
  assert.equal(m.chipText({ type: "continue", index: 2, missing: true }), "第 3 次的文件已不在，不能接着写");
  assert.equal(m.submitContinues({ type: "continue", attemptId: "c" }, ""), "c");
  assert.equal(m.submitContinues({ type: "refine", attemptId: "b", continues: "a", seed: 11 }, "11"), "a");
  assert.equal(m.submitContinues({ type: "refine", attemptId: "b", continues: "a", seed: 11 }, "12"), null);   // 改了种子→提示条隐藏→不续写
  assert.equal(m.submitContinues(null, ""), null);
});

test("card title, lyrics preview, chain line with gap", () => {
  const attempts = [A("a"), A("bb", { continues: "a" }), { id: "c", status: "done", output: "c.wav", op: "compose", params: { parts: ["a", "bb"] } }, A("ddd", { continues: "zz" })];
  assert.match(m.cardTitle(attempts[1], 1, attempts), /^第 2 次 · \d\d:\d\d · 接第 1 次$/);
  assert.match(m.cardTitle(attempts[2], 2, attempts), /合成：第 1、2 次$/);
  assert.equal(m.lyricsPreview("[verse]\n\n早晨的风\n"), "早晨的风");
  assert.equal(m.chainLine(attempts[1], attempts), "由：第 1 次 → 第 2 次");
  assert.equal(m.chainLine(attempts[0], attempts), "");
  assert.equal(m.chainLine(attempts[3], attempts), "由：… → 第 4 次");
});

test("join problem offers rejoin only for recoverable codes and complete chains", () => {
  const a = A("a"), b = A("b", { continues: "a", joined_error: { code: "join_failed", message: "拼接成片失败" } });
  assert.deepEqual(m.joinProblem(b, [a, b]), { text: "这一段生成好了，但成片没拼成：拼接成片失败", rejoin: { parts: ["a", "b"] }, reason: "" });
  const gone = { ...a, output_missing: true };
  assert.deepEqual(m.joinProblem(b, [gone, b]).rejoin, null);
  assert.equal(m.joinProblem(b, [gone, b]).reason, "链上有一段已不在");
  const missing = A("b", { continues: "a", joined_error: { code: "segment_missing", message: "第 1 段的文件已不在，无法拼成成片" } });
  assert.deepEqual(m.joinProblem(missing, [a, missing]), { text: "这一段生成好了，但成片没拼成：第 1 段的文件已不在，无法拼成成片", rejoin: null, reason: "" });
  assert.equal(m.joinProblem(a, [a]), null);
});
```

- [ ] **Step 2:** `node --test tests/js/music_session.test.js` → FAIL

- [ ] **Step 3: 实现 `desk/static/js/pure/music_session.js`**

```js
// 音乐会话的纯逻辑（设计 docs/superpowers/specs/2026-09-27-music-sessions-design.md）。零 DOM、零 fetch。
import { ParamsError, SEED_MAX, attemptLabel, chainOf, randomSeed } from "./media_session.js";

export const DEFAULT_DURATION = 60;
export const CANNOT_CONTINUE = "这一段没有生成好，不能接着写";
const REJOINABLE = new Set(["join_failed", "join_cancelled", "interrupted"]);

export function readMusicParams(values) {
  const caption = String(values?.caption ?? "");
  const lyrics = String(values?.lyrics ?? "");
  if (!caption.trim()) throw new ParamsError("请填写风格描述");
  if (!lyrics.trim()) throw new ParamsError("请填写歌词：Music 3 需要歌词才能生成");
  const advanced = (reason) => new ParamsError(`高级参数里的数值有误：${reason}`, { advanced: true });
  const duration = Number(String(values?.duration ?? "").trim());
  if (!Number.isInteger(duration) || duration < 10 || duration > 300) throw advanced("时长须为 10–300 的整数");
  const params = { caption, lyrics, duration };
  const seedRaw = String(values?.seed ?? "").trim();
  if (seedRaw) {
    const seed = Number(seedRaw);
    if (!Number.isInteger(seed) || seed < 0 || seed > SEED_MAX) throw advanced("种子须为 0–4294967295 的整数");
    params.seed = seed;
  }
  return params;
}

export function refineFields(attempt) {
  const p = attempt?.params ?? {};
  return { caption: typeof p.caption === "string" ? p.caption : "", lyrics: typeof p.lyrics === "string" ? p.lyrics : "",
    duration: Number.isFinite(p.duration) ? p.duration : DEFAULT_DURATION, seed: Number.isInteger(p.seed) ? p.seed : null };
}

export function nextFields(attempt, current) {
  if (attempt?.op === "compose" || Array.isArray(attempt?.params?.parts)) return { caption: current.caption, duration: current.duration };
  const f = refineFields(attempt);
  return { caption: f.caption, duration: f.duration };
}

export function canContinue(attempt) {
  return attempt?.status === "done" && typeof attempt.output === "string" && !!attempt.output && !attempt.output_missing;
}

export function versionParams(attempt, sessionId, draw = randomSeed) {
  const f = refineFields(attempt);
  let seed = draw();
  while (seed === f.seed) seed = draw();
  const params = { session_id: sessionId, caption: f.caption, lyrics: f.lyrics, duration: f.duration, seed };
  if (attempt?.continues) params.continues = attempt.continues;
  return params;
}

const ordinal = (index) => (Number.isInteger(index) ? `第 ${index + 1} 次` : "");

export function chipText(ref) {
  if (!ref) return "";
  if (ref.type === "continue") return ref.missing ? `${ordinal(ref.index)}的文件已不在，不能接着写` : `接在${ordinal(ref.index)}后面`;
  return Number.isInteger(ref.index) ? `沿用${ordinal(ref.index)}` : "沿用素材库里这首";
}

// 提示条可见时才续写（M-27）：续写提示条总是可见；沿用提示条要求种子框仍等于被引用的种子（IS D-42）。
export function submitContinues(ref, seedInput) {
  if (!ref) return null;
  if (ref.type === "continue") return ref.missing ? null : ref.attemptId;
  if (!Number.isInteger(ref.seed) || String(seedInput ?? "").trim() !== String(ref.seed)) return null;
  return ref.continues ?? null;
}

export function cardTitle(attempt, index, attempts) {
  const base = attemptLabel(index, attempt);
  const position = (id) => (attempts ?? []).findIndex((a) => a?.id === id);
  if (attempt?.op === "compose" || Array.isArray(attempt?.params?.parts)) {
    const nums = (attempt.params?.parts ?? []).map(position);
    return nums.length && nums.every((n) => n >= 0) ? `${base} · 合成：第 ${nums.map((n) => n + 1).join("、")} 次` : `${base} · 合成`;
  }
  if (attempt?.continues) {
    const n = position(attempt.continues);
    if (n >= 0) return `${base} · 接第 ${n + 1} 次`;
  }
  return base;
}

export function lyricsPreview(lyrics) {
  return String(lyrics ?? "").split("\n").map((line) => line.trim()).find((line) => line && !/^\[[^\]]*\]$/.test(line)) ?? "";
}

export function chainLine(attempt, attempts) {
  const { items, gap } = chainOf(attempt, attempts);
  if (items.length < 2 && !gap) return "";
  const position = (id) => (attempts ?? []).findIndex((a) => a?.id === id);
  return `由：${gap ? "… → " : ""}${items.map((a) => `第 ${position(a.id) + 1} 次`).join(" → ")}`;
}

export function joinProblem(attempt, attempts) {
  const error = attempt?.joined_error;
  if (attempt?.status !== "done" || !error) return null;
  const text = `这一段生成好了，但成片没拼成：${error.message ?? ""}`;
  if (!REJOINABLE.has(error.code)) return { text, rejoin: null, reason: "" };
  const { items, gap } = chainOf(attempt, attempts);
  if (gap || !items.every(canContinue)) return { text, rejoin: null, reason: "链上有一段已不在" };
  return { text, rejoin: { parts: items.map((a) => a.id) }, reason: "" };
}
```

- [ ] **Step 4:** `node --test tests/js/music_session.test.js` → PASS

- [ ] **Step 5: Commit** `feat(music-sessions): 音乐会话纯逻辑`

---

### Task 6: 音乐页、卡片与接通

**Files:**
- Create: `desk/static/js/widgets/music_session_card.js`
- Modify: `desk/static/js/panes/music.js`（重写）、`desk/static/index.html:30`（`#pane-music` 重写）、`desk/static/app.css`、`desk/static/js/main.js`、`desk/static/js/pure/history_fill.js`（无需改，Task 8 of base 已带会话字段）
- Test: `tests/js/music_pane.test.js`（新建）、`tests/js/media_panes.test.js`（删掉音乐旧表单用例，保留视频）

**Interfaces:**
- Consumes: Task 3/4 控制器、Task 5 纯逻辑、`widgets/session_list.js`、`widgets/error_block.js`、`widgets/prompt_assist.js`、`api.serveOutput`、`api.startMusicJob`
- Produces: `createMusicPane(root, ctx)` → `{refresh, applyJob, poll, applyFill, setHeavyAllowed, setModelStatus, setRuntimeStatus, setAssistAvailable}`

- [ ] **Step 1: HTML**（替换 `index.html` 第 30 行整段 `#pane-music`）

```html
<section id="pane-music" data-pane="music" hidden>
  <aside class="sessions" aria-label="音乐会话"><button data-music-session-new data-icon-name="plus" class="btn-primary">新会话</button><ul data-music-session-list></ul></aside>
  <div class="image-main music-main">
    <div class="image-head">
      <h2>生成歌曲</h2>
      <span class="hint" data-music-model role="status">正在检查模型…</span>
      <details class="image-model-note"><summary>模型说明</summary><p class="hint">MiniMax Music 3 · MLX 本机推理。需要风格描述和歌词；成品为 WAV。「接着写下一段」按同样的风格写下一段歌词，拼接处用 1.5 秒交叉淡入淡出，不是真正的音频续写。</p></details>
    </div>
    <div class="image-timeline" data-music-timeline></div>
    <div class="image-composer" data-music-composer role="form" aria-label="生成歌曲">
      <div class="refine-chip" data-music-chip hidden><span data-music-chip-text></span><button class="btn-quiet btn-sm" data-music-chip-clear data-icon-name="x" aria-label="取消沿用或续写"></button></div>
      <input data-music-caption aria-label="风格描述" placeholder="例如：温柔的民谣，木吉他伴奏，女声轻唱，慢速">
      <div class="image-input-row">
        <textarea data-music-lyrics class="music-lyrics" aria-label="歌词" placeholder="歌词（必填）"></textarea>
        <button data-music-start data-icon-name="sparkles" class="btn-primary" disabled>生成歌曲</button>
      </div>
      <div class="assist-row" data-music-assist></div>
      <details class="image-advanced music-advanced" data-music-advanced><summary>高级参数</summary>
        <div class="image-params">
          <label>时长（秒） <input data-music-duration type="number" value="60" min="10" max="300" step="1" required></label>
          <label>种子（留空则每次随机） <input data-music-seed type="number" min="0" max="4294967295" step="1" placeholder="留空则每次随机"></label>
        </div>
        <p class="hint">成品时长由模型按歌词决定，常短于所填时长；素材库会标注实际时长。</p>
        <p class="inline-error" data-music-advanced-error role="alert"></p>
      </details>
      <p class="hint hint-busy image-hint" data-music-hint role="status"><span data-music-hint-text></span><button class="btn-secondary btn-sm" data-music-return hidden>回到该会话</button></p>
      <p class="inline-error" data-music-error role="alert"></p>
    </div>
  </div>
</section>
```

（控制器用 `data-music-timeline`、`data-music-session-list`、`data-music-session-new`、`data-music-composer`、`data-music-return`、`data-music-model` 等与图片同名后缀；Task 3 的控制器按 `dataPrefix` 查询这些名字——图片页 HTML 已有的 data 名即为约定。）

- [ ] **Step 2: CSS**（追加到 `app.css`）

```css
#pane-music { /* 与 #pane-image 同构：复制 #pane-image 的 display/grid 规则，选择器改为 #pane-music */ }
.music-lyrics { min-height: calc(4 * 1.5em + 16px); max-height: 50vh; resize: none; field-sizing: content; }
.attempt-audio { width: 100%; margin: 8px 0; }
.segment-switch { display: inline-flex; gap: 4px; }
.attempt-pick { margin-right: 8px; }
.pick-badge { display: inline-block; min-width: 1.5em; text-align: center; border-radius: 999px; background: var(--accent); color: var(--accent-fg, #fff); font-size: 12px; }
.compose-bar { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; padding: 8px 0; }
.compose-bar ol { display: flex; flex-wrap: wrap; gap: 6px; margin: 0; padding: 0; list-style: none; }
.session-toolbar { display: flex; justify-content: flex-end; padding: 0 0 8px; }
```

`#pane-music` 那一行：在 `app.css` 找到所有以 `#pane-image` 开头的规则，把选择器扩成 `#pane-image, #pane-music`（不复制规则体）。`field-sizing: content` 不支持时 `textarea` 仍按 `min-height` 显示——另在 `music.js` 的 `input` 事件里设 `style.height = "auto"; style.height = Math.min(scrollHeight, innerHeight*0.5) + "px"`，失焦且行数 ≤4 时清掉 `style.height`（M-21）。

- [ ] **Step 3: 卡片 `widgets/music_session_card.js`**：结构仿 `image_session_card.js`（`el`、`iconBlock`、`attemptView` 用法相同——`attemptView` 在 `pure/image_session.js`，其 missing 文案是「图片文件已不在」；音乐卡片自己算：done+文件不在 → 标记「文件已不在」、标题「文件已不在」、副标题「可能已在访达中移动或删除」，其余状态同 `attemptView`）。要点：
  - 折叠：`cardTitle(...)`、风格描述摘要 `.attempt-prompt`（`title` 全文）、`lyricsPreview`、状态标记。
  - 展开 done：`<audio controls class="attempt-audio" preload="metadata">`，`src = serveOutput(joined && !joined_missing ? joined_output : output)`；有可用成片时加 `div.segment-switch[role=radiogroup]`，两个 `button[role=radio]`「成片」「只听这一段」，切换改 `audio.src` 与 `aria-checked`；`audio` `error` → `onBroken(attempt)`。
  - `chainLine` 非空时一行 `.hint`。
  - `joinProblem` 非空：一行 `.inline-error` 文案 + （有 `rejoin`）按钮「重新拼接」→ `onRejoin(parts)`；（无 rejoin 且有 reason）按钮 disabled + 下方原因行。
  - 风格描述全文、`<details class="attempt-lyrics"><summary>歌词</summary><pre>…</pre></details>`、`<details class="attempt-advanced"><summary>高级参数</summary>` 列时长、种子（compose 尝试不画高级参数）。
  - 动作：非 compose：「在这段基础上改」→`onRefine(attempt,index)`；「换个版本」→`onVersion(attempt)`（由面板按可用性 disabled）；「接着写下一段」→`onContinue(attempt,index)`，`canContinue` 为假时 disabled 且下方原因 `CANNOT_CONTINUE`。compose：只有「接着写下一段」。
  - 挑选模式（`picking`）：`canContinue(attempt)` 的卡片前加 `input[type=checkbox].attempt-pick`（`aria-label="选中第 N 次"`，`checked = pickIndex >= 0`）与序号徽标 `.pick-badge`（①② 用 `String.fromCharCode(0x2460 + pickIndex)`）；卡片点击调用 `onTogglePick(attempt)` 而非展开。
  - running：同图片卡片的 running 结构（label/progress/取消/日志），返回 `{node, running:{label, progress, log, index}}`。

- [ ] **Step 4: 面板 `panes/music.js`**（重写）：元素查询 `data-music-*`；状态 `ref`（提示条：`{type, index, attemptId, seed?, continues?, missing?}`）；

```js
const pane = createSessionPane(root, {
  kind: "music", noun: "歌曲", dataPrefix: "music", canCompose: true,
  emptyLines: ["还没有歌曲", "在下面写风格描述和歌词，点「生成歌曲」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着写下一段」。"],
  modelTexts: { missing: "尚未安装音乐模型，请到「资源」页下载", runtime: "音乐 MLX 运行环境不可用，请检查服务或应用安装" },
  renderCard: (doc, o) => renderMusicCard(doc, { ...o, serveOutput: api.serveOutput,
    onRefine: refine, onVersion: version, onContinue: continueAfter,
    onRejoin: (parts) => pane.startCompose(parts), onCancel: () => pane.cancelJob(), onTogglePick: (a) => pane.togglePick(a.id) }),
  composer: { startLabel: "生成歌曲", afterStart, onSessionSwitch: clearChip, focus: () => els.lyrics.focus?.(), updateAvailability },
  startJob: api.startMusicJob, confirm: ctx.confirm, onStarted: ctx.onStarted,
});
```

（控制器导出 `startCompose(parts)`：Task 4 的提交逻辑抽成它，重新拼接也用它。）
  - `refine(attempt, index)`：`refineFields` 回填四项；`ref = {type:"refine", index, attemptId, seed, continues: attempt.continues ?? null}`；焦点歌词末尾。
  - `version(attempt)`：`pane.startGeneration(versionParams(attempt, pane.currentId(), drawSeed), {fromInputs:false})`。
  - `continueAfter(attempt, index)`：`nextFields(attempt, {caption: els.caption.value, duration: Number(els.duration.value)})` 回填 caption/duration；歌词清空；种子清空；`ref = {type:"continue", index, attemptId: attempt.id}`；焦点歌词。
  - `syncChip()`：沿用型按 `refineChipVisible` 规则（种子框==ref.seed）显隐；续写型总显示；每次 `rerender`/会话加载后检查续写目标仍 `canContinue`，否则 `ref.missing = true`（M-28）。文案 `chipText(ref)`。
  - `startFromInputs()`：`readMusicParams` → 错误按 `advanced` 分区显示；`continues = submitContinues(ref, els.seed.value)`；`pane.startGeneration({session_id: pane.currentId(), ...params, ...(continues ? {continues} : {})}, {fromInputs:true})`。`ref.missing` 时 `updateAvailability` 让「生成歌曲」disabled，原因 = `chipText(ref)`。
  - `afterStart({fromInputs})`：`fromInputs` 时清种子、`ref = null`、隐藏提示条（M-24）；风格描述、歌词、时长保留。
  - 后端返回 `segment_missing` / `segment_not_found`：`ref.missing = true`，错误行 `error.message`。
  - AI 帮写：沿用现有 `createPromptAssist(doc, els.assist, {task:"music", read, write, confirm})`，`read` 返回 `{text: caption, lyrics}`，`write` 写回两框。
  - 歌词框自适应高度（Step 2 注释）。
  - 返回 `{refresh, applyJob, poll, applyFill: (plan) => pane.applyFill(plan, {refine, prefillOnly}), setHeavyAllowed, setModelStatus, setRuntimeStatus, setAssistAvailable}`；`prefillOnly(fields)` 回填并 `ref = {type:"refine", index:null, seed: fields.seed ?? null}`（文案「沿用素材库里这首」）。

- [ ] **Step 5: `main.js` 接通**（M-51–M-53）

```js
// createResourcesPane onModels：
onModels: (models) => {
  panes.image.setModelStatus(models?.find((m) => m.key === "qwen-image"));
  panes.music.setModelStatus(models?.find((m) => m.key === "music3"));
},
// showTab：
if (name === "music") panes.music.refresh();          // 替换原 jobView.sync
// applyFill：
if (plan.pane === "image" || plan.pane === "music") { showTab(plan.pane); panes[plan.pane].applyFill(plan); return; }
// applyHeavyAvailability：删 panes.music.jobView.setBusyReason 行
// tickJob：
if (payload.kind === "image" || payload.kind === "music") panes[payload.kind].applyJob(payload, { replaceLog: changed });
else (panes[payload.kind] ?? panes.video).jobView.apply(payload, { replaceLog: changed, busyReason: mediaBusyReason });
// tick：
panes.music.setRuntimeStatus(capabilities?.music_runtime);
await panes.music.poll(deskState);                     // 紧跟 panes.image.poll
// catch 分支：
panes.music.setHeavyAllowed(false, "服务状态暂不可用，请稍后重试");
```

- [ ] **Step 6: 音乐页单测 `tests/js/music_pane.test.js`**：从 `tests/js/support/fake_dom.js`（Task 3 建）导入假 DOM 与 `fakeBackend("music")`，另写 `makeMusicPane()` 按 Step 1 的 data 名建元素。测试：
  1. 生成：填风格描述+歌词 → 点「生成歌曲」→ `POST /api/media/music` body 含 `session_id`、无 `seed`、无 `continues`；
  2. 「接着写下一段」：歌词清空、风格描述=该段、提示条「接在第 1 次后面」→ 生成 body `continues:"a1"`；生成后提示条隐藏；
  3. 续写段的「换个版本」：body 带原 `continues`、`seed`≠原值；
  4. 「在这段基础上改」后改种子框 → 提示条隐藏 → 生成不带 `continues`；
  5. stale continuation chip：续写目标在会话刷新后变成 `output_missing` → 提示条「第 1 次的文件已不在，不能接着写」、「生成歌曲」disabled；点 × 恢复可用；
  6. 成片播放器：有 `joined_output` 的展开卡片出现「成片」「只听这一段」且默认 src 为成片；
  7. 重新拼接：`joined_error.code="join_failed"` → 点「重新拼接」→ `POST /api/media/compose {kind:"music", parts:[链]}`；链缺段 → 按钮 disabled、原因「链上有一段已不在」；
  8. compose 尝试只有「接着写下一段」，点它不改风格描述与时长；
  9. 主流程 DOM 文本不含「种子」（`mainFlowText` 同图片测试，跳过 `music-advanced`/`attempt-advanced`）。

- [ ] **Step 7:** `node --test tests/js/` 全过；`python3 -m pytest tests/e2e -q` 全过

- [ ] **Step 8: Commit** `feat(music-sessions): 音乐页改成会话式——三个动作、成片播放、重新拼接、挑选合成`

---

### Task 7: 音乐会话 e2e

**Files:**
- Create: `tests/e2e/test_music_sessions.py`
- Test: 同上

**Interfaces:**
- Consumes: 测试外壳（`desk/testing/harness.py`，`FakeMediaExecutor` 对 `--output` 命令写 `TINY_WAV`，对 ffmpeg 命令按输出后缀写假文件）；现有 e2e 夹具（仿 `tests/e2e/test_image_sessions.py` 的 `harness`、`page`、脚本化媒体作业写法——先读该文件前 120 行照抄夹具与辅助函数）

- [ ] **Step 1: 写测试**：一个测试走完整流程（每步断言 DOM 与 `GET /api/media-sessions/music/{id}`）：
  1. 打开 `#tab=music`，自动新会话；填风格描述、歌词，点「生成歌曲」，脚本让作业完成 → 出现「第 1 次」卡片且展开带 `audio`；
  2. 点「接着写下一段」→ 提示条「接在第 1 次后面」、歌词框为空；填歌词、生成、完成 → 第 2 张卡「接第 1 次」，展开有「成片」「只听这一段」；会话文件中该尝试 `continues == 第1次id` 且 `joined_output` 非空；
  3. 在第 2 张卡点「换个版本」→ 第 3 张卡「接第 1 次」；
  4. 点「挑几段合成…」，勾第 3 张再勾第 1 张，在合成栏点「上移第 1 次」，点「合成（2 段）」→ 第 4 张卡「合成：第 1、3 次」；会话文件里 `params.parts == [第1次id, 第3次id]`；
  5. 视口 900×700 截图（存 `tests/e2e/artifacts/` 同图片 e2e 约定）；断言 `document.documentElement.scrollWidth <= innerWidth`，主按钮 `scrollWidth <= clientWidth`；
  6. 主流程可见文本（排除 `details.music-advanced` 与 `details.attempt-advanced`）不含「种子」。

- [ ] **Step 2:** `python3 -m pytest tests/e2e/test_music_sessions.py -q` → 首次运行若失败，修的是页面实现（回到 Task 6 的文件），不改期望。

- [ ] **Step 3: 全量回归**：`python3 -m pytest -q --ignore=tests/e2e`、`node --test tests/js/`、`python3 -m pytest tests/e2e -q`；`grep -n "music.jobView\|panes.music.fill" desk/static/js/main.js` 无输出。

- [ ] **Step 4: Commit** `test(music-sessions): 音乐会话 e2e——续写、换版本、挑选合成`
