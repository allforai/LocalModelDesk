# 视频画幅 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 视频页画幅从「三档横屏」扩展为「横屏/竖屏/方形 × 草稿/标准/清晰 + 自定义」，前后端同一套 H3 画布校验，首帧形状自动跟随，续写锁定，回填找回方向档位，按面积与 H3 预算提醒。

**Architecture:** 纯规则放进新模块 `pure/video_size.js`（取代 `pure/video_cost.js`），后端 `start_video_job` 镜像同一套校验并由镜像测试钉住；视频页的下拉框值仍是 `"宽x高"` 档位字符串，另加 `"custom"` 与宽、高输入，所以 `nextFields`/`refineFields`/`versionParams` 的形状不变；方向控件复用 `segment_switch.js`（加 `setChecked`/`setDisabled` 两个方法）。

**Tech Stack:** 原生 ES 模块；`node --test`（`tests/js/support/fake_dom.js`）；pytest；Playwright e2e。

**Spec:** `docs/superpowers/specs/2026-10-07-video-size-design.md`（Z-xx）。执行者两份都读。

## Global Constraints

- 画布规则（Z-01）：宽、高为 32 的倍数；每边 256–1344；`宽×高 ≤ 768×1344`。
- 前端违规文案（Z-02，按此顺序取第一条，前缀「高级参数里的数值有误：」）：「宽和高须为整数」「宽和高须为 32 的倍数」「每边须在 256–1344 之间」「面积不能超过 768×1344（约 103 万像素）」；非 `宽x高` 格式的档位值为「画幅无效」。
- 后端违规（Z-03）：400 `invalid_params`，文案「画幅须为 32 的倍数，每边 256–1344，面积不超过 768×1344」，在任何会话写入、仲裁、启动之前。
- 档位（Z-11）：横屏 512×288 / 768×448 / 1024×576；竖屏为对调；方形 384² / 576² / 768²；名称「草稿 / 标准 / 清晰」，选项文字形如「标准 448×768」；末项「自定义…」，值 `custom`。
- 方向（Z-10）：值 `landscape/portrait/square`，文字「横屏/竖屏/方形」；分段控件 `ariaLabel`「画幅方向」。
- 首帧跟随文案（Z-21/24）：「已按首帧切到<方向>」；自定义时「首帧是<方向>，画幅是<方向>，画面会被拉伸变形」（Z-53 实测 H3 拉伸首帧）。
- 续写锁定 `title`（Z-30）：「接着往下生沿用上一段的画幅」。
- 提醒（Z-40/41）：耗时「大画幅加 10 秒以上会非常慢：实测 1024×576 曾 20 分钟只走完 2/16 步，可能要一小时以上。建议先用草稿画幅试效果。」；预算「按实测外推约需 N GiB，超过视频生成的 40 GiB 上限，可能中途失败。」；估算 `27.0 + 1.4 × max(宽×高×帧数 ÷ (512×288×49) − 1, 0)`。只提醒不拦。
- 默认横屏 · 草稿 512×288（Z-15）。台面未发布，不谈兼容、不留旧路径（`video_cost.js` 删除）。
- 测试命令：`node --test tests/js/`；`python3 -m pytest -q --ignore=tests/e2e`；`python3 -m pytest tests/e2e -q`（系统 python3）。`desk/static` 有改动必须跑 e2e。

## Rulings made while planning

- 下拉框值保持 `"宽x高"` 字符串（加 `"custom"`），不改成对象：现有 `nextFields`/`refineFields`/`versionParams`/素材库回填与它们的测试全部沿用。代价若错：只是内部表示，可后改。
- Z-14「失焦时取 32 的倍数」用数字输入的 `change` 事件实现（浏览器在失焦时才对改过的数字框发 `change`）。
- Z-53 已在写计划时实测完：H3 拉伸首帧到画布（spec 已记）。

## Review Focus

1. 回填一个竖屏或自定义尺寸的旧尝试（「在这段基础上改」「换个版本」「接着往下生」、素材库「回填参数」）——方向、档位、自定义框都要对上，并且带回来的首帧不能把尺寸改掉（Task 4、Task 5 测试钉住）。
2. 先选自定义、再切方向，或先切方向、再选自定义——自定义框的初值要等于切换前那一档，切方向时取新方向「标准」档（Task 4 测试钉住）。
3. 首帧尺寸异步读回来之前用户已经换了首帧或手动改了方向——迟到的结果不能覆盖用户的选择（Task 5 测试钉住）。
4. 自定义框留空或填小数直接点生成——前端拦下并写明原因，不发请求；后端遇到同样的值也 400 且会话不留记录（Task 3、Task 2 测试钉住）。
5. 续写时画幅控件全部锁住，键盘也改不了方向；点 × 取消续写后恢复（Task 3 的 `setDisabled`、Task 4 测试钉住）。

---

## File Structure

- Create `desk/static/js/pure/video_size.js` — 方向、档位、32 取整、校验、形状判定、`matchSize`、`frameFollow`、内存估算与提醒。
- Delete `desk/static/js/pure/video_cost.js`、`tests/js/video_cost.test.js`。
- Modify `desk/media/service.py` — 画布常量与校验；Create `tests/test_video_size_mirror.py`；Modify `tests/test_media_service.py`、`tests/test_media_sessions_service.py`。
- Modify `desk/static/js/widgets/segment_switch.js` — `group.setChecked(i)`、`group.setDisabled(on, title)`；Create `tests/js/segment_switch.test.js`。
- Modify `desk/static/js/pure/video_session.js` — `readVideoParams` 接受 `custom` + 宽高并用新校验；删 `SIZES`。
- Modify `desk/static/js/panes/video.js`、`desk/static/index.html`、`desk/static/app.css` — 方向控件、档位下拉、自定义框、`applySize`、提醒、续写锁定、首帧跟随。
- Modify `tests/js/video_session.test.js`、`tests/js/video_pane.test.js`；Create `tests/e2e/test_video_size.py`。

---

### Task 1: 规则模块 `pure/video_size.js`

**Files:**
- Create: `desk/static/js/pure/video_size.js`
- Create: `tests/js/video_size.test.js`
- Delete: `desk/static/js/pure/video_cost.js`、`tests/js/video_cost.test.js`
- Modify: `desk/static/js/panes/video.js:12`（import）与 `updateCost`（约 :232-234）

**Interfaces:**
- Produces（后续任务逐字使用）：`ORIENTATIONS: {value,label}[]`、`CUSTOM = "custom"`、`presetsFor(orientation) -> {value,width,height,tier,label}[]`、`tierOf(value) -> 0|1|2|-1`、`parseSize("WxH") -> {width,height}|null`、`snap32(value) -> number|NaN`、`sizeError(width,height) -> string`（空串为合法）、`shapeOf(width,height) -> orientation`、`matchSize(width,height) -> {orientation, size}`（`size` 为档位值或 `CUSTOM`）、`frameFollow({orientation, custom}, {width,height}|null) -> {orientation|null, note}`、`estimateGiB(width,height,frames)`、`H3_BUDGET_GIB = 40`、`videoCostNote(width,height,frames) -> string`。
- 镜像测试（Task 2）用正则读这些顶层常量：`MULTIPLE`、`SIDE_MIN`、`SIDE_MAX`、`MAX_PIXELS = 768 * 1344`、`FIXED_GIB`、`PER_VOLUME_GIB`、`H3_BUDGET_GIB`——写法必须是 `NAME = 数字;`。

- [ ] **Step 1: Write the failing tests**

```js
// tests/js/video_size.test.js —— 视频画幅规则（视频画幅设计 Z-01–Z-41）
import test from "node:test";
import assert from "node:assert/strict";
import {
  CUSTOM, ORIENTATIONS, estimateGiB, frameFollow, matchSize, parseSize, presetsFor, shapeOf, sizeError, snap32, tierOf,
  videoCostNote,
} from "../../desk/static/js/pure/video_size.js";

test("方向与档位：横屏三档、竖屏对调、方形三档，全部合法（Z-10/11）", () => {
  assert.deepEqual(ORIENTATIONS.map((o) => [o.value, o.label]), [["landscape", "横屏"], ["portrait", "竖屏"], ["square", "方形"]]);
  assert.deepEqual(presetsFor("landscape").map((p) => p.label), ["草稿 512×288", "标准 768×448", "清晰 1024×576"]);
  assert.deepEqual(presetsFor("portrait").map((p) => p.value), ["288x512", "448x768", "576x1024"]);
  assert.deepEqual(presetsFor("square").map((p) => p.value), ["384x384", "576x576", "768x768"]);
  for (const { value } of ORIENTATIONS) for (const p of presetsFor(value)) assert.equal(sizeError(p.width, p.height), "", p.value);
  assert.equal(tierOf("448x768"), 1);
  assert.equal(tierOf("768x768"), 2);
  assert.equal(tierOf("448x800"), -1);
  assert.equal(CUSTOM, "custom");
});

test("画布规则边界与文案顺序（Z-01/02）", () => {
  assert.equal(sizeError(Number.NaN, 288), "宽和高须为整数");
  assert.equal(sizeError(512.5, 288), "宽和高须为整数");
  assert.equal(sizeError(500, 288), "宽和高须为 32 的倍数");
  assert.equal(sizeError(224, 288), "每边须在 256–1344 之间");
  assert.equal(sizeError(256, 256), "");
  assert.equal(sizeError(1344, 768), "");
  assert.equal(sizeError(1376, 512), "每边须在 256–1344 之间");
  assert.equal(sizeError(1344, 800), "面积不能超过 768×1344（约 103 万像素）");
  assert.equal(sizeError(1344, 1024), "面积不能超过 768×1344（约 103 万像素）");
});

test("parseSize 与 snap32", () => {
  assert.deepEqual(parseSize("448x768"), { width: 448, height: 768 });
  assert.equal(parseSize("custom"), null);
  assert.equal(parseSize(""), null);
  assert.equal(snap32("450"), 448);
  assert.equal(snap32(500), 512);
  assert.ok(Number.isNaN(snap32("")));
  assert.ok(Number.isNaN(snap32("abc")));
});

test("形状判定：0.9–1.1 为方形（Z-20）", () => {
  assert.equal(shapeOf(1024, 1024), "square");
  assert.equal(shapeOf(990, 1100), "square"); // 0.9
  assert.equal(shapeOf(1100, 1000), "square"); // 1.1
  assert.equal(shapeOf(890, 1000), "portrait");
  assert.equal(shapeOf(1120, 1000), "landscape");
});

test("matchSize：档位找回方向与档位，不在档位里是自定义（Z-31）", () => {
  assert.deepEqual(matchSize(448, 768), { orientation: "portrait", size: "448x768" });
  assert.deepEqual(matchSize(576, 576), { orientation: "square", size: "576x576" });
  assert.deepEqual(matchSize(448, 800), { orientation: "portrait", size: CUSTOM });
  assert.deepEqual(matchSize(1024, 1000), { orientation: "square", size: CUSTOM });
});

test("frameFollow：方向不同就切并提示；自定义只提示拉伸；读不到尺寸不动（Z-21/22/24）", () => {
  assert.deepEqual(frameFollow({ orientation: "landscape", custom: false }, { width: 1024, height: 1024 }),
    { orientation: "square", note: "已按首帧切到方形" });
  assert.deepEqual(frameFollow({ orientation: "square", custom: false }, { width: 1000, height: 1050 }), { orientation: null, note: "" });
  assert.deepEqual(frameFollow({ orientation: "landscape", custom: true }, { width: 720, height: 1280 }),
    { orientation: null, note: "首帧是竖屏，画幅是横屏，画面会被拉伸变形" });
  assert.deepEqual(frameFollow({ orientation: "landscape", custom: false }, null), { orientation: null, note: "" });
  assert.deepEqual(frameFollow({ orientation: "landscape", custom: false }, { width: undefined, height: 5 }), { orientation: null, note: "" });
});

test("提醒：按面积判断很慢，按公式外推超 40 GiB 提醒（Z-40/41）", () => {
  assert.equal(estimateGiB(512, 288, 49), 27);
  assert.equal(videoCostNote(512, 288, 49), "");
  const slow = videoCostNote(1024, 576, 243);
  assert.match(slow, /^大画幅加 10 秒以上会非常慢：实测 1024×576 曾 20 分钟只走完 2\/16 步/);
  assert.match(slow, /超过视频生成的 40 GiB 上限，可能中途失败。$/);
  assert.equal(videoCostNote(1024, 576, 192), "按实测外推约需 48 GiB，超过视频生成的 40 GiB 上限，可能中途失败。");
  assert.equal(videoCostNote(576, 1024, 192), videoCostNote(1024, 576, 192), "按面积，不分横竖");
  assert.equal(videoCostNote(768, 1344, 49), "");
  assert.equal(videoCostNote(768, 448, 362), "按实测外推约需 50 GiB，超过视频生成的 40 GiB 上限，可能中途失败。");
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `node --test tests/js/video_size.test.js`
Expected: FAIL — `Cannot find module …/pure/video_size.js`

- [ ] **Step 3: Write the module**

```js
// desk/static/js/pure/video_size.js
// 视频画幅（视频画幅设计 Z-01–Z-41，重做 42f8062）：方向 × 档位或自定义、H3 画布规则、首帧形状跟随、提醒。
// 规则与 desk/media/service.py 的 VIDEO_* 常量、内存公式与 desk/media/memory_estimate.py 一致（tests/test_video_size_mirror.py 钉住）。
export const ORIENTATIONS = [
  { value: "landscape", label: "横屏" },
  { value: "portrait", label: "竖屏" },
  { value: "square", label: "方形" },
];
export const CUSTOM = "custom";
const LABEL = Object.fromEntries(ORIENTATIONS.map((o) => [o.value, o.label]));
const TIERS = ["草稿", "标准", "清晰"];
const LANDSCAPE = [[512, 288], [768, 448], [1024, 576]];
const SQUARE = [[384, 384], [576, 576], [768, 768]];

const MULTIPLE = 32;
const SIDE_MIN = 256;
const SIDE_MAX = 1344;
const MAX_PIXELS = 768 * 1344;

export function presetsFor(orientation) {
  const rows = orientation === "square" ? SQUARE
    : orientation === "portrait" ? LANDSCAPE.map(([w, h]) => [h, w]) : LANDSCAPE;
  return rows.map(([width, height], tier) => ({
    value: `${width}x${height}`, width, height, tier, label: `${TIERS[tier]} ${width}×${height}`,
  }));
}

// 档位值在它那个方向里是第几档（0–2）；不是档位返回 -1。三个方向的档位值互不相同。
export function tierOf(value) {
  for (const { value: orientation } of ORIENTATIONS) {
    const preset = presetsFor(orientation).find((p) => p.value === value);
    if (preset) return preset.tier;
  }
  return -1;
}

export function parseSize(value) {
  const match = /^(\d+)x(\d+)$/.exec(String(value ?? ""));
  return match ? { width: Number(match[1]), height: Number(match[2]) } : null;
}

export function snap32(value) {
  if (value === "" || value == null) return Number.NaN;
  const n = Number(value);
  return Number.isFinite(n) ? Math.round(n / MULTIPLE) * MULTIPLE : Number.NaN;
}

// Z-01/02：合法返回空串，否则返回第一条违规说明。
export function sizeError(width, height) {
  if (![width, height].every(Number.isInteger)) return "宽和高须为整数";
  if (width % MULTIPLE || height % MULTIPLE) return `宽和高须为 ${MULTIPLE} 的倍数`;
  if ([width, height].some((n) => n < SIDE_MIN || n > SIDE_MAX)) return `每边须在 ${SIDE_MIN}–${SIDE_MAX} 之间`;
  if (width * height > MAX_PIXELS) return "面积不能超过 768×1344（约 103 万像素）";
  return "";
}

// Z-20：宽高比 0.9–1.1 算方形。
export function shapeOf(width, height) {
  const ratio = width / height;
  if (ratio >= 0.9 && ratio <= 1.1) return "square";
  return width > height ? "landscape" : "portrait";
}

// Z-31：按尺寸找回方向与档位；不在任何档位里就是自定义（方向按形状）。
export function matchSize(width, height) {
  for (const { value: orientation } of ORIENTATIONS) {
    const preset = presetsFor(orientation).find((p) => p.width === width && p.height === height);
    if (preset) return { orientation, size: preset.value };
  }
  return { orientation: shapeOf(width, height), size: CUSTOM };
}

// Z-21/22/24：current = {orientation, custom}；frame = 首帧尺寸或 null（读不到）。
// 返回要切到的方向（不切为 null）与提示文案。
export function frameFollow(current, frame) {
  if (!frame || !(frame.width > 0) || !(frame.height > 0)) return { orientation: null, note: "" };
  const shape = shapeOf(frame.width, frame.height);
  if (shape === current.orientation) return { orientation: null, note: "" };
  if (current.custom) {
    return { orientation: null, note: `首帧是${LABEL[shape]}，画幅是${LABEL[current.orientation]}，画面会被拉伸变形` };
  }
  return { orientation: shape, note: `已按首帧切到${LABEL[shape]}` };
}

// Z-41：与 desk/media/memory_estimate.py 的视频公式同源——27 GiB 固定开销 + 每多一个草稿体积（512×288×49 帧）1.4 GiB。
// 只有两个实测点，更大的组合是外推。
const DRAFT_VOLUME = 512 * 288 * 49;
const FIXED_GIB = 27.0;
const PER_VOLUME_GIB = 1.4;
export const H3_BUDGET_GIB = 40;

export function estimateGiB(width, height, frames) {
  const volume = (width * height * Number(frames)) / DRAFT_VOLUME;
  return FIXED_GIB + PER_VOLUME_GIB * Math.max(volume - 1, 0);
}

// Z-40：「很慢」只对有实测依据的面积——cross-exam 2026-09-13 q16，1024×576 × 15 秒在 128 GB 机器上 20 分钟只走完 2/16 步。
const SLOW_PIXELS = 1024 * 576;
const SLOW_FRAMES = 243; // 「约 10 秒」档

export function videoCostNote(width, height, frames) {
  const notes = [];
  if (width * height >= SLOW_PIXELS && Number(frames) >= SLOW_FRAMES) {
    notes.push("大画幅加 10 秒以上会非常慢：实测 1024×576 曾 20 分钟只走完 2/16 步，可能要一小时以上。建议先用草稿画幅试效果。");
  }
  const need = estimateGiB(width, height, frames);
  if (need > H3_BUDGET_GIB) notes.push(`按实测外推约需 ${need.toFixed(0)} GiB，超过视频生成的 ${H3_BUDGET_GIB} GiB 上限，可能中途失败。`);
  return notes.join("");
}
```

- [ ] **Step 4: Switch the page to the new note and delete the old module**

`desk/static/js/panes/video.js` 第 12 行：

```js
import { videoCostNote } from "../pure/video_cost.js";
```

改为：

```js
import { parseSize, videoCostNote } from "../pure/video_size.js";
```

`updateCost`（约第 232–234 行）：

```js
  function updateCost() {
    if (els.costNote) els.costNote.textContent = videoCostNote(els.size.value, els.frames.value);
  }
```

改为（Task 4 会再换成按当前画幅取宽高）：

```js
  function updateCost() {
    const size = parseSize(els.size.value);
    if (els.costNote) els.costNote.textContent = size ? videoCostNote(size.width, size.height, els.frames.value) : "";
  }
```

然后：

```bash
git rm desk/static/js/pure/video_cost.js tests/js/video_cost.test.js
```

- [ ] **Step 5: Run tests**

Run: `node --test tests/js/video_size.test.js` → PASS（7 tests）
Run: `node --test tests/js/` → 全部 PASS（`video_pane.test.js` 里「耗时提示随画幅与时长变化」仍过：1024×576×243 含「非常慢」，512×288×243 估算约 32.5 GiB 无提醒）

- [ ] **Step 6: Commit**

```bash
git add desk/static/js/pure/video_size.js tests/js/video_size.test.js desk/static/js/panes/video.js
git commit -m "feat(video): 画幅规则模块——方向×档位、H3 画布校验、首帧跟随、按面积与预算提醒（Z-01–Z-41）"
```

---

### Task 2: 后端画布校验 + 镜像测试

**Files:**
- Modify: `desk/media/service.py`（常量放在 `VIDEO_REF_NAMES` 定义之前；校验放在 `start_video_job` 的 `_positive_int` 循环之后，约 :285-286）
- Create: `tests/test_video_size_mirror.py`
- Modify: `tests/test_media_service.py:197-200`（参数化列表）、`tests/test_media_sessions_service.py`（加一条）

**Interfaces:**
- Consumes: Task 1 的 `desk/static/js/pure/video_size.js` 顶层常量写法。
- Produces: `service.VIDEO_CANVAS_MULTIPLE = 32`、`VIDEO_SIDE_MIN = 256`、`VIDEO_SIDE_MAX = 1344`、`VIDEO_MAX_PIXELS = 768 * 1344`。

- [ ] **Step 1: Write the failing tests**

`tests/test_media_service.py` 中 `test_invalid_video_params_never_touch_arbiter_or_spawn` 的参数化列表改为：

```python
    @pytest.mark.parametrize("bad", [
        dict(width=0), dict(width=-1), dict(width="512"), dict(width=True),
        dict(height=0), dict(frames=0), dict(steps=0),
        # H3 画布规则（视频画幅设计 Z-01/Z-03）：每边 32 的倍数且在 256–1344，面积不超过 768×1344。
        dict(width=500), dict(height=300), dict(width=224), dict(height=1376),
        dict(width=1344, height=1024),
    ])
```

并在同一个类里加：

```python
    def test_canvas_violation_message_is_the_shared_rule(self, tmp_path):
        service, deps = make_service(tmp_path)
        with pytest.raises(MediaError) as err:
            service.start_video_job(**{**self.VALID, "width": 500})
        assert str(err.value) == "画幅须为 32 的倍数，每边 256–1344，面积不超过 768×1344"

    @pytest.mark.parametrize("size", [dict(width=288, height=512), dict(width=448, height=800), dict(width=768, height=1344)])
    def test_portrait_and_custom_canvases_are_accepted(self, tmp_path, size):
        service, deps = make_service(tmp_path)
        service.start_video_job(**{**self.VALID, **size})
        assert deps.executor.spawned
```

（`MediaError.__init__` 把文案交给 `Exception`，所以 `str(err.value)` 就是文案。）

`tests/test_media_sessions_service.py` 末尾加：

```python
def test_bad_canvas_is_refused_before_the_session_is_touched(tmp_path):
    service, deps = make_service(tmp_path)
    sid = deps.media_sessions["video"].create()["id"]
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, width=1344, height=1024)
    assert (exc.value.code, exc.value.http_status) == ("invalid_params", 400)
    assert deps.media_sessions["video"].get(sid)["attempts"] == []
    assert deps.executor.spawned == [] and deps.arbiter.acquired == []
```

新建 `tests/test_video_size_mirror.py`：

```python
"""视频画幅规则与内存公式以 Python 为准，desk/static/js/pure/video_size.js 镜像一份给页面即时反馈（视频画幅设计 Z-04）。
两边一旦不一致，页面就会放行后端拒绝的尺寸，或报错误的 GiB 数——所以把 JS 常量钉在 Python 的值上。"""
import re
from pathlib import Path

from desk.media import memory_estimate, service
from desk.media.commands import H3_BUDGET_GB

JS = (Path(__file__).resolve().parents[1] / "desk/static/js/pure/video_size.js").read_text(encoding="utf-8")


def _js_number(name: str) -> float:
    match = re.search(rf"\b{name}\s*=\s*([0-9.]+)\s*;", JS)
    assert match, f"{name} not found in video_size.js"
    return float(match.group(1))


def test_canvas_rules_match_the_backend():
    assert _js_number("MULTIPLE") == service.VIDEO_CANVAS_MULTIPLE
    assert _js_number("SIDE_MIN") == service.VIDEO_SIDE_MIN
    assert _js_number("SIDE_MAX") == service.VIDEO_SIDE_MAX
    assert "MAX_PIXELS = 768 * 1344;" in JS and service.VIDEO_MAX_PIXELS == 768 * 1344


def test_memory_formula_and_budget_match_the_backend():
    fixed, per_unit = memory_estimate._VIDEO
    assert _js_number("FIXED_GIB") * memory_estimate.GIB == fixed
    assert _js_number("PER_VOLUME_GIB") * memory_estimate.GIB == per_unit
    assert "DRAFT_VOLUME = 512 * 288 * 49;" in JS and memory_estimate._DRAFT_VOLUME == 512 * 288 * 49
    assert _js_number("H3_BUDGET_GIB") == H3_BUDGET_GB
```

- [ ] **Step 2: Run to verify they fail**

Run: `python3 -m pytest tests/test_media_service.py tests/test_media_sessions_service.py tests/test_video_size_mirror.py -q`
Expected: FAIL — 新增的违规尺寸没有被拒；镜像测试 `AttributeError: VIDEO_CANVAS_MULTIPLE`

- [ ] **Step 3: Implement**

`desk/media/service.py`，在 `# Which cross-session references each video request may carry` 注释行之前加：

```python
# H3 画布规则（mlx_h3.layout）：每边 32 的倍数，面积不超过 768×1344；256 的下限与每边 1344 的上限是我们加的
# （面积上限已经限住了长边）。desk/static/js/pure/video_size.js 镜像这些值（tests/test_video_size_mirror.py）。
VIDEO_CANVAS_MULTIPLE = 32
VIDEO_SIDE_MIN, VIDEO_SIDE_MAX = 256, 1344
VIDEO_MAX_PIXELS = 768 * 1344
VIDEO_CANVAS_MESSAGE = "画幅须为 32 的倍数，每边 256–1344，面积不超过 768×1344"
```

`start_video_job` 里这两行之后：

```python
        for name, value in (("width", width), ("height", height), ("frames", frames), ("steps", steps)):
            _positive_int(name, value)
```

插入：

```python
        if (any(value % VIDEO_CANVAS_MULTIPLE or not VIDEO_SIDE_MIN <= value <= VIDEO_SIDE_MAX for value in (width, height))
                or width * height > VIDEO_MAX_PIXELS):
            raise MediaError("invalid_params", VIDEO_CANVAS_MESSAGE, 400)
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_media_service.py tests/test_media_sessions_service.py tests/test_video_size_mirror.py -q` → PASS
Run: `python3 -m pytest -q --ignore=tests/e2e` → 全部 PASS（`tests/test_shell_window.py` 有 4 条已知环境性偶发失败，出现就单独重跑该文件确认）。若有别的测试用了非 32 倍数的视频尺寸（grep `start_video_job(` 与 `"width":`），把它们改成合法尺寸并在报告里列出。

- [ ] **Step 5: Commit**

```bash
git add desk/media/service.py tests/test_media_service.py tests/test_media_sessions_service.py tests/test_video_size_mirror.py
git commit -m "feat(video): 后端按 H3 画布规则拒绝不合法画幅，JS 镜像由测试钉住（Z-03/Z-04）"
```

---

### Task 3: `readVideoParams` 支持自定义 + 分段控件的程序化选中与禁用

**Files:**
- Modify: `desk/static/js/pure/video_session.js:1-31`
- Modify: `tests/js/video_session.test.js:14-15`（一条旧断言）并加新测试
- Modify: `desk/static/js/widgets/segment_switch.js`（返回前加两个方法）
- Create: `tests/js/segment_switch.test.js`

**Interfaces:**
- Consumes: Task 1 `CUSTOM`、`parseSize`、`sizeError`。
- Produces: `readVideoParams({prompt, size, width?, height?, frames, steps, seed})`——`size === "custom"` 时读 `width/height`；`renderSegmentSwitch(...)` 返回的 `group` 多两个方法：`group.setChecked(index)`（不触发 `onChange`）、`group.setDisabled(disabled, title = "")`。`SIZES` 仍导出（Task 4 删除）。

- [ ] **Step 1: Write the failing tests**

`tests/js/video_session.test.js` 里这条：

```js
  assert.throws(() => v.readVideoParams({ prompt: "p", size: "999x999", frames: "49", steps: "16" }),
    (e) => e.advanced && /高级参数里的数值有误：画幅无效/.test(e.message));
```

改为：

```js
  assert.throws(() => v.readVideoParams({ prompt: "p", size: "999x999", frames: "49", steps: "16" }),
    (e) => e.advanced && e.message === "高级参数里的数值有误：宽和高须为 32 的倍数");
```

并加：

```js
test("画幅：档位值或自定义宽高，按 H3 规则校验（Z-01/02/14）", () => {
  const base = { prompt: "p", frames: "49", steps: "16" };
  assert.deepEqual(v.readVideoParams({ ...base, size: "448x768" }), { prompt: "p", width: 448, height: 768, frames: 49, steps: 16 });
  assert.deepEqual(v.readVideoParams({ ...base, size: "custom", width: "448", height: " 800 " }),
    { prompt: "p", width: 448, height: 800, frames: 49, steps: 16 });
  const refused = (values, text) => assert.throws(() => v.readVideoParams({ ...base, ...values }),
    (e) => e.advanced && e.message === `高级参数里的数值有误：${text}`);
  refused({ size: "abc" }, "画幅无效");
  refused({ size: "custom", width: "", height: "800" }, "宽和高须为整数");
  refused({ size: "custom", width: "448.5", height: "800" }, "宽和高须为整数");
  refused({ size: "custom", width: "450", height: "800" }, "宽和高须为 32 的倍数");
  refused({ size: "custom", width: "224", height: "800" }, "每边须在 256–1344 之间");
  refused({ size: "custom", width: "1344", height: "1024" }, "面积不能超过 768×1344（约 103 万像素）");
});
```

新建 `tests/js/segment_switch.test.js`：

```js
import test from "node:test";
import assert from "node:assert/strict";
import { Element } from "./support/fake_dom.js";
import { renderSegmentSwitch } from "../../desk/static/js/widgets/segment_switch.js";

const doc = { createElement: (tag) => new Element(tag) };

test("setChecked 改选中但不触发 onChange；之后点任意一项按新选中判断（视频画幅方向）", async () => {
  const changes = [];
  const group = renderSegmentSwitch(doc, { labels: ["横屏", "竖屏", "方形"], ariaLabel: "画幅方向", onChange: (i) => changes.push(i) });
  group.setChecked(2);
  assert.deepEqual(group.children.map((b) => b.attrs["aria-checked"]), ["false", "false", "true"]);
  assert.deepEqual(group.children.map((b) => b.tabIndex), [-1, -1, 0]);
  assert.deepEqual(changes, []);
  await group.children[2].click();
  assert.deepEqual(changes, [], "点已选中的项不算变化");
  await group.children[0].click();
  assert.deepEqual(changes, [0]);
});

test("setDisabled 同时设每个按钮的 disabled 与 title；解除后清空 title", () => {
  const group = renderSegmentSwitch(doc, { labels: ["横屏", "竖屏"], ariaLabel: "画幅方向" });
  group.setDisabled(true, "接着往下生沿用上一段的画幅");
  assert.deepEqual(group.children.map((b) => [b.disabled, b.title]),
    [[true, "接着往下生沿用上一段的画幅"], [true, "接着往下生沿用上一段的画幅"]]);
  group.setDisabled(false);
  assert.deepEqual(group.children.map((b) => [b.disabled, b.title]), [[false, ""], [false, ""]]);
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `node --test tests/js/video_session.test.js tests/js/segment_switch.test.js`
Expected: FAIL — 自定义宽高被当作「画幅无效」；`group.setChecked is not a function`

- [ ] **Step 3: Implement**

`desk/static/js/pure/video_session.js` 顶部 import 之后加：

```js
import { CUSTOM, parseSize, sizeError } from "./video_size.js";
```

把 `const DEFAULT_SIZE = SIZES[0][0];` 改为 `const DEFAULT_SIZE = "512x288";`。

`readVideoParams` 里这三行：

```js
  const size = String(values?.size ?? "");
  if (!SIZES.some(([v]) => v === size)) throw advanced("画幅无效");
  const [width, height] = size.split("x").map(Number);
```

改为：

```js
  // 档位值「宽x高」或自定义（Z-14）：自定义读宽、高两个输入；都按 H3 画布规则校验（Z-01/02）。
  const size = String(values?.size ?? "");
  const number = (value) => { const text = String(value ?? "").trim(); return text ? Number(text) : Number.NaN; };
  const dims = size === CUSTOM ? { width: number(values?.width), height: number(values?.height) } : parseSize(size);
  if (!dims) throw advanced("画幅无效");
  const sizeProblem = sizeError(dims.width, dims.height);
  if (sizeProblem) throw advanced(sizeProblem);
  const { width, height } = dims;
```

`desk/static/js/widgets/segment_switch.js` 里 `mark(checked);` 那一行之后、`group.append(...buttons);` 之前加：

```js
  // 程序化改选中（不触发 onChange，如视频页回填画幅）与整组禁用（如续写时锁住画幅方向）。
  group.setChecked = (index) => { current = index; mark(index); };
  group.setDisabled = (disabled, title = "") => {
    for (const btn of buttons) { btn.disabled = disabled; btn.title = title; }
  };
```

- [ ] **Step 4: Run tests**

Run: `node --test tests/js/video_session.test.js tests/js/segment_switch.test.js` → PASS
Run: `node --test tests/js/` → 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/pure/video_session.js tests/js/video_session.test.js desk/static/js/widgets/segment_switch.js tests/js/segment_switch.test.js
git commit -m "feat(video): 参数读取支持自定义宽高并按画布规则校验；分段控件可程序化选中与禁用（Z-14）"
```

---

### Task 4: 视频页——方向控件、档位下拉、自定义框、回填找回、提醒、续写锁定

**Files:**
- Modify: `desk/static/index.html`（`#pane-video` 的 `.video-materials` 与「高级参数」）
- Modify: `desk/static/js/panes/video.js`
- Modify: `desk/static/js/pure/video_session.js:4`（删 `SIZES`）
- Modify: `desk/static/app.css`（末尾加一小节）
- Modify: `tests/js/video_pane.test.js`（`makeVideoPane` 与新测试）

**Interfaces:**
- Consumes: Task 1 `ORIENTATIONS, CUSTOM, matchSize, parseSize, presetsFor, snap32, tierOf, videoCostNote`；Task 3 `group.setChecked`、`group.setDisabled`、`readVideoParams` 的 `custom`。
- Produces（Task 5 用）：页面内函数 `chooseOrientation(value)`、`currentSize() -> {width,height}`、状态变量 `orientation`；DOM 钩子 `[data-video-orientation]`（里面是分段控件 `role=radiogroup`）、`[data-video-custom]`、`[data-video-width]`、`[data-video-height]`、`[data-video-shape-note]`（Task 4 先放进标记，Task 5 才用）。

- [ ] **Step 1: Markup**

`desk/static/index.html` 里：

```html
            <label class="video-mode">生成方式 <select data-video-mode>
```

这一整行（到 `</select></label>`）之后插入一行：

```html
            <div class="video-orientation" data-video-orientation></div>
```

`data-video-first-preview` 那一行（`<div class="video-preview" data-video-first-preview></div>`）之后插入：

```html
              <p class="hint" data-video-shape-note role="status"></p>
```

高级参数里：

```html
              <label>画幅 <select data-video-size></select></label>
```

改为：

```html
              <label>画幅 <select data-video-size></select></label>
              <span class="video-custom-size" data-video-custom hidden><input type="number" data-video-width min="256" max="1344" step="32" aria-label="自定义宽"> × <input type="number" data-video-height min="256" max="1344" step="32" aria-label="自定义高"></span>
```

- [ ] **Step 2: Update the test mount and write the failing tests**

`tests/js/video_pane.test.js` 的 `makeVideoPane`：
- `tags` 对象里加：`orientation: "div", custom: "span", width: "input", height: "input",`
- `names` 数组里加：`"orientation", "custom", "width", "height", "shape-note",`
- `parts.advanced.append(parts.size, parts.frames, …)` 改为 `parts.advanced.append(parts.size, parts.custom, parts.frames, …)`（其余参数不变），并在它前面加 `parts.custom.append(parts.width, parts.height);`
- `parts["first-area"].append(...)` 末尾加 `parts["shape-note"]`
- `parts.composer.append(parts.chip, parts.mode, …)` 改为在 `parts.mode` 后面插入 `parts.orientation`

在 `const cards = …` 之后加：

```js
const orientationButtons = (parts) => parts.orientation.children[0].children;
const checkedOrientation = (parts) => orientationButtons(parts).find((b) => b.attrs["aria-checked"] === "true")?.textContent;
const sizeOptions = (parts) => parts.size.children.map((o) => o.value);
```

（`videoCalls`、`done`、`button` 已在文件里定义/导入。）在文件末尾加：

```js
test("画幅方向：默认横屏草稿；切竖屏保持同一档；自定义框初值是切换前那一档；自定义时切方向取标准档（Z-12–15）", async () => {
  await withBackend("video", async () => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    assert.deepEqual(orientationButtons(parts).map((b) => b.textContent), ["横屏", "竖屏", "方形"]);
    assert.equal(parts.orientation.children[0].attrs["aria-label"], "画幅方向");
    assert.equal(checkedOrientation(parts), "横屏");
    assert.deepEqual(sizeOptions(parts), ["512x288", "768x448", "1024x576", "custom"]);
    assert.equal(parts.size.value, "512x288");
    assert.equal(parts.custom.hidden, true);
    parts.size.value = "768x448"; await parts.size.dispatch("change");
    await orientationButtons(parts)[1].click();
    assert.equal(checkedOrientation(parts), "竖屏");
    assert.deepEqual(sizeOptions(parts), ["288x512", "448x768", "576x1024", "custom"]);
    assert.equal(parts.size.value, "448x768");
    parts.size.value = "custom"; await parts.size.dispatch("change");
    assert.equal(parts.custom.hidden, false);
    assert.equal(parts.width.value, "448");
    assert.equal(parts.height.value, "768");
    await orientationButtons(parts)[2].click();
    assert.equal(parts.size.value, "576x576");
    assert.equal(parts.custom.hidden, true);
  });
});

test("自定义宽高：改完取 32 的倍数；不合规写在高级参数里并拦下；合规按宽高提交（Z-14）", async () => {
  await withBackend("video", async (backend) => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    parts.prompt.value = "竖屏街景";
    parts.size.value = "custom"; await parts.size.dispatch("change");
    parts.width.value = "450"; await parts.width.dispatch("change");
    assert.equal(parts.width.value, "448");
    parts.height.value = "1376"; await parts.height.dispatch("change");
    await parts.start.click();
    assert.equal(parts["advanced-error"].textContent, "高级参数里的数值有误：每边须在 256–1344 之间");
    assert.equal(videoCalls(backend).length, 0);
    parts.height.value = ""; await parts.height.dispatch("change");
    await parts.start.click();
    assert.equal(parts["advanced-error"].textContent, "高级参数里的数值有误：宽和高须为整数");
    assert.equal(videoCalls(backend).length, 0);
    parts.height.value = "800"; await parts.height.dispatch("change");
    await parts.start.click();
    const [call] = videoCalls(backend);
    assert.equal(call.body.width, 448);
    assert.equal(call.body.height, 800);
  });
});

test("接着往下生时画幅控件全部锁住并说明，取消续写后恢复（Z-30）", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1", { params: { prompt: "p", width: 448, height: 768, frames: 73, steps: 16, seed: 1 } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await button(cards(parts)[0], "接着往下生").click();
    assert.equal(checkedOrientation(parts), "竖屏");
    assert.equal(parts.size.value, "448x768");
    for (const control of [parts.size, parts.width, parts.height, ...orientationButtons(parts)]) {
      assert.equal(control.disabled, true);
      assert.equal(control.title, "接着往下生沿用上一段的画幅");
    }
    await parts["chip-clear"].click();
    for (const control of [parts.size, parts.width, parts.height, ...orientationButtons(parts)]) {
      assert.equal(control.disabled, false);
      assert.equal(control.title, "");
    }
  });
});

test("回填按尺寸找回方向与档位，不在档位里填进自定义（Z-31）", async () => {
  await withBackend("video", async () => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await pane.applyFill({ pane: "video", session_id: "gone", attempt_id: "x",
      fields: { prompt: "竖", width: 448, height: 768, frames: 73, steps: 16 } });
    assert.equal(checkedOrientation(parts), "竖屏");
    assert.equal(parts.size.value, "448x768");
    assert.equal(parts.custom.hidden, true);
    await pane.applyFill({ pane: "video", session_id: "gone", attempt_id: "y",
      fields: { prompt: "自", width: 448, height: 800, frames: 73, steps: 16 } });
    assert.equal(checkedOrientation(parts), "竖屏");
    assert.equal(parts.size.value, "custom");
    assert.equal(parts.custom.hidden, false);
    assert.equal(parts.width.value, "448");
    assert.equal(parts.height.value, "800");
  });
});

test("在这段基础上改：竖屏尝试回填竖屏（Z-31）", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1", { params: { prompt: "p", width: 576, height: 1024, frames: 73, steps: 16, seed: 1 } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await button(cards(parts)[0], "在这段基础上改").click();
    assert.equal(checkedOrientation(parts), "竖屏");
    assert.equal(parts.size.value, "576x1024");
  });
});

test("提醒按面积与 H3 预算；自定义尺寸也算（Z-40/41）", async () => {
  await withBackend("video", async () => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    parts.size.value = "1024x576"; parts.frames.value = "192"; await parts.frames.dispatch("change");
    assert.equal(parts["cost-note"].textContent, "按实测外推约需 48 GiB，超过视频生成的 40 GiB 上限，可能中途失败。");
    parts.size.value = "custom"; await parts.size.dispatch("change");
    parts.width.value = "768"; await parts.width.dispatch("change");
    parts.height.value = "1344"; await parts.height.dispatch("change");
    parts.frames.value = "49"; await parts.frames.dispatch("change");
    assert.equal(parts["cost-note"].textContent, "");
  });
});
```

注意第一条测试里「自定义框初值」：切到竖屏后 `lastPreset` 是 `448x768`（`chooseOrientation` 会更新它），所以选「自定义…」后框里是 448 和 768。

- [ ] **Step 3: Run to verify they fail**

Run: `node --test tests/js/video_pane.test.js`
Expected: FAIL — `parts.orientation.children[0]` 为 undefined 等

- [ ] **Step 4: Implement in `desk/static/js/panes/video.js`**

1) 第 12 行（Task 1 改过的）import 换成：

```js
import { CUSTOM, ORIENTATIONS, matchSize, parseSize, presetsFor, snap32, tierOf, videoCostNote } from "../pure/video_size.js";
import { renderSegmentSwitch } from "../widgets/segment_switch.js";
```

2) `from "../pure/video_session.js"` 的 import 列表里删去 `SIZES`。

3) `els` 对象里 `mode: q("mode"), prompt: …` 那一行末尾追加：`orientation: q("orientation"), custom: q("custom"), width: q("width"), height: q("height"), shapeNote: q("shape-note"),`

4) 删除这段：

```js
  for (const [value, label] of SIZES) {
    const option = doc.createElement("option");
    option.value = value; option.textContent = label; els.size.append(option);
  }
```

和这一行：

```js
  els.size.value = SIZES[0][0];
```

5) 在 `els.frames.value = String(DURATIONS[0][0]);` 之后加：

```js
  // ---------- 画幅（视频画幅设计 Z-10–Z-31）：方向 × 档位或自定义 ----------
  let orientation = "landscape";
  let lastPreset = presetsFor("landscape")[0].value; // 最近选中的档位：选「自定义…」时框里的初值（Z-14）
  const orientationIndex = (value) => ORIENTATIONS.findIndex((o) => o.value === value);
  const orientationSwitch = els.orientation ? renderSegmentSwitch(doc, {
    labels: ORIENTATIONS.map((o) => o.label), checked: 0, ariaLabel: "画幅方向",
    onChange: (index) => chooseOrientation(ORIENTATIONS[index].value),
  }) : null;
  if (orientationSwitch) els.orientation.append(orientationSwitch);

  function renderSizeOptions() {
    els.size.replaceChildren();
    for (const preset of presetsFor(orientation)) {
      const option = doc.createElement("option");
      option.value = preset.value; option.textContent = preset.label; els.size.append(option);
    }
    const custom = doc.createElement("option");
    custom.value = CUSTOM; custom.textContent = "自定义…"; els.size.append(custom);
  }
  function setSizeValue(value) {
    els.size.value = value;
    if (value !== CUSTOM) lastPreset = value;
    if (els.custom) els.custom.hidden = value !== CUSTOM;
  }
  // 当前画幅：档位值或自定义两个框；读不出的边为 NaN（提交时由 readVideoParams 拦下）。
  function currentSize() {
    if (els.size.value === CUSTOM) {
      const read = (input) => { const text = String(input?.value ?? "").trim(); return text ? Number(text) : Number.NaN; };
      return { width: read(els.width), height: read(els.height) };
    }
    return parseSize(els.size.value) ?? { width: Number.NaN, height: Number.NaN };
  }
  // Z-13：切方向保持同一档；当前是自定义时取新方向的「标准」档。
  function chooseOrientation(next) {
    const tier = els.size.value === CUSTOM ? 1 : Math.max(0, tierOf(els.size.value));
    orientation = next;
    orientationSwitch?.setChecked(orientationIndex(next));
    renderSizeOptions();
    setSizeValue(presetsFor(next)[tier].value);
    updateCost();
  }
  // Z-31：按「宽x高」找回方向与档位；不在档位里就填进自定义。
  function applySize(size) {
    const parsed = parseSize(size);
    if (!parsed) return;
    const match = matchSize(parsed.width, parsed.height);
    orientation = match.orientation;
    orientationSwitch?.setChecked(orientationIndex(orientation));
    renderSizeOptions();
    if (match.size === CUSTOM) {
      els.width.value = String(parsed.width);
      els.height.value = String(parsed.height);
    }
    setSizeValue(match.size);
    updateCost();
  }
  renderSizeOptions();
  setSizeValue(lastPreset);
```

6) `renderInputs()` 里 `els.mode.disabled = locked;` 之后加：

```js
    // Z-30：续写沿用上一段的画幅。
    const sizeLock = locked ? "接着往下生沿用上一段的画幅" : "";
    for (const control of [els.size, els.width, els.height]) if (control) { control.disabled = locked; control.title = sizeLock; }
    orientationSwitch?.setDisabled(locked, sizeLock);
```

7) `updateCost` 换成：

```js
  function updateCost() {
    const { width, height } = currentSize();
    if (!els.costNote) return;
    els.costNote.textContent = Number.isFinite(width) && Number.isFinite(height) ? videoCostNote(width, height, els.frames.value) : "";
  }
```

8) `startFromInputs` 里 `readVideoParams({` 的参数对象改为：

```js
      params = readVideoParams({
        prompt: els.prompt.value, size: els.size.value, width: els.width?.value, height: els.height?.value,
        frames: els.frames.value, steps: els.steps.value, seed: els.seed.value,
      });
```

9) `prefill` 里 `if (fields.size) els.size.value = fields.size;` 改为 `if (fields.size) applySize(fields.size);`

10) `continueAfter` 里 `els.size.value = fields.size;` 改为 `applySize(fields.size);`

11) 事件区 `els.size.addEventListener("change", updateCost);` 换成：

```js
  els.size.addEventListener("change", () => {
    if (els.size.value === CUSTOM) {
      const from = parseSize(lastPreset);
      els.width.value = String(from.width);
      els.height.value = String(from.height);
    }
    setSizeValue(els.size.value);
    updateCost();
  });
  // Z-14：自定义宽高改完（数字框失焦时才发 change）取最近的 32 的倍数；清空就留空，提交时拦下。
  for (const input of [els.width, els.height]) {
    input?.addEventListener("change", () => {
      const snapped = snap32(input.value);
      if (Number.isFinite(snapped)) input.value = String(snapped);
      updateCost();
    });
  }
```

`desk/static/js/pure/video_session.js` 删除第 4 行 `export const SIZES = …;`。

- [ ] **Step 5: Style**

`desk/static/app.css` 末尾加：

```css

/* 17. 视频画幅（视频画幅设计 Z-12/Z-14）：方向分段控件在输入区主行，自定义宽高跟在画幅下拉后面 */
.video-orientation{display:inline-flex;align-items:center}
.video-custom-size{display:inline-flex;align-items:center;gap:6px;color:var(--muted)}
.video-custom-size[hidden]{display:none}
.video-custom-size input{width:84px}
[data-video-shape-note]:empty{display:none}
```

- [ ] **Step 6: Run tests**

Run: `node --test tests/js/video_pane.test.js` → PASS
Run: `node --test tests/js/` → 全部 PASS。若旧测试因 `SIZES` 删除而报错（`grep -rn SIZES tests/js desk/static/js` 应无结果），按新接口改断言并在报告里列出。

- [ ] **Step 7: Commit**

```bash
git add desk/static/index.html desk/static/js/panes/video.js desk/static/js/pure/video_session.js desk/static/app.css tests/js/video_pane.test.js
git commit -m "feat(video): 视频页画幅方向×档位与自定义，回填找回方向档位，续写锁定画幅（Z-12–Z-31）"
```

---

### Task 5: 首帧形状自动跟随

**Files:**
- Modify: `desk/static/js/panes/video.js`（`lookupImage`、`checkImageRef`、`setFirst`、上传槽 `slots`、`prefill`、方向控件的 `onChange`）
- Modify: `tests/js/video_pane.test.js`（新测试）

**Interfaces:**
- Consumes: Task 1 `frameFollow`、`shapeOf`；Task 4 `chooseOrientation`、`currentSize`、`orientation`、`els.shapeNote`、`CUSTOM`。
- Produces: `createVideoPane(root, ctx)` 新增可注入 `ctx.imageSize(file) -> Promise<{width,height}|null>`（测试用；缺省用 `createImageBitmap` 解码）。

- [ ] **Step 1: Write the failing tests**

`tests/js/video_pane.test.js` 末尾加：

```js
// 图片会话 img2：一张已生成的图，宽高由参数给（Z-22 从那次生成的参数里读）。
function sizedImage(backend, width, height) {
  serveImages(backend, [{ id: "img2", title: "图", attempts: [
    { id: "s1", status: "done", output: "s1.png", params: { prompt: "图", width, height } }] }]);
}
const pickSized = async () => ({ ref: { kind: "image", session_id: "img2", attempt_id: "s1" }, title: "图", index: 0 });

test("上传方图做首帧：方向切到方形、档位不变并提示；手动改回后同一张首帧不再切（Z-21/23）", async () => {
  await withBackend("video", async () => {
    const { parts, pane, ready } = makeVideoPane({ imageSize: async () => ({ width: 1024, height: 1024 }) }); ready();
    await pane.refresh();
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    parts.size.value = "768x448"; await parts.size.dispatch("change");
    await choose(parts["first-upload"], png("square.png"));
    await flush();
    assert.equal(checkedOrientation(parts), "方形");
    assert.equal(parts.size.value, "576x576");
    assert.equal(parts["shape-note"].textContent, "已按首帧切到方形");
    await orientationButtons(parts)[0].click();
    await flush();
    assert.equal(checkedOrientation(parts), "横屏");
    assert.equal(parts.size.value, "768x448");
    assert.equal(parts["shape-note"].textContent, "");
  });
});

test("首帧尺寸迟到：用户已手动改方向就不再切（Review Focus 3）", async () => {
  await withBackend("video", async () => {
    let resolveSize;
    const { parts, pane, ready } = makeVideoPane({ imageSize: () => new Promise((resolve) => { resolveSize = resolve; }) }); ready();
    await pane.refresh();
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    await choose(parts["first-upload"], png("tall.png"));
    await orientationButtons(parts)[2].click();
    resolveSize({ width: 720, height: 1280 });
    await flush();
    assert.equal(checkedOrientation(parts), "方形");
    assert.equal(parts["shape-note"].textContent, "");
  });
});

test("首帧尺寸迟到：已经换了别的首帧，旧结果不生效（Review Focus 3）", async () => {
  await withBackend("video", async () => {
    const pending = [];
    const { parts, pane, ready } = makeVideoPane({ imageSize: () => new Promise((resolve) => pending.push(resolve)) }); ready();
    await pane.refresh();
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    await choose(parts["first-upload"], png("tall.png"));
    await choose(parts["first-upload"], png("wide.png"));
    pending[0]({ width: 720, height: 1280 });
    await flush();
    assert.equal(checkedOrientation(parts), "横屏", "第一张的尺寸迟到，不能用");
    pending[1]({ width: 1280, height: 720 });
    await flush();
    assert.equal(checkedOrientation(parts), "横屏");
    assert.equal(parts["shape-note"].textContent, "");
  });
});

test("自定义尺寸时不自动改，只提示会拉伸变形（Z-24）", async () => {
  await withBackend("video", async () => {
    const { parts, pane, ready } = makeVideoPane({ imageSize: async () => ({ width: 720, height: 1280 }) }); ready();
    await pane.refresh();
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    parts.size.value = "custom"; await parts.size.dispatch("change");
    await choose(parts["first-upload"], png("tall.png"));
    await flush();
    assert.equal(parts.size.value, "custom");
    assert.equal(parts["shape-note"].textContent, "首帧是竖屏，画幅是横屏，画面会被拉伸变形");
  });
});

test("读不到首帧尺寸：不切也不提示（Z-22）", async () => {
  await withBackend("video", async () => {
    const { parts, pane, ready } = makeVideoPane({ imageSize: async () => null }); ready();
    await pane.refresh();
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    await choose(parts["first-upload"], png("broken.png"));
    await flush();
    assert.equal(checkedOrientation(parts), "横屏");
    assert.equal(parts["shape-note"].textContent, "");
  });
});

test("从图片会话选竖图做首帧：按那次生成的宽高切到竖屏（Z-21/22）", async () => {
  await withBackend("video", async (backend) => {
    sizedImage(backend, 768, 1344);
    const { parts, pane, ready } = makeVideoPane({ pickImage: pickSized }); ready();
    await pane.refresh();
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    await parts["first-pick"].click();
    await flush(); await flush();
    assert.equal(checkedOrientation(parts), "竖屏");
    assert.equal(parts.size.value, "288x512");
    assert.equal(parts["shape-note"].textContent, "已按首帧切到竖屏");
  });
});

test("在这段基础上改：恢复保存的尺寸，带回的首帧不触发跟随（Z-26，Review Focus 1）", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1", {
      params: { prompt: "p", mode: "image", width: 512, height: 288, frames: 73, steps: 16, seed: 3 },
      refs: { first_frame: { kind: "image", session_id: "img2", attempt_id: "s1" } } })]);
    sizedImage(backend, 1024, 1024);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await button(cards(parts)[0], "在这段基础上改").click();
    await flush(); await flush();
    assert.equal(checkedOrientation(parts), "横屏");
    assert.equal(parts.size.value, "512x288");
    assert.equal(parts["shape-note"].textContent, "");
  });
});

test("接着往下生的首帧（上一段末帧）不触发跟随（Z-25）", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1")]);
    let asked = 0;
    const { parts, pane, ready } = makeVideoPane({ imageSize: async () => { asked += 1; return { width: 1, height: 1 }; } }); ready();
    await pane.refresh();
    await button(cards(parts)[0], "接着往下生").click();
    await flush();
    assert.equal(asked, 0);
    assert.equal(checkedOrientation(parts), "横屏");
    assert.equal(parts["shape-note"].textContent, "");
  });
});
```

- [ ] **Step 2: Run to verify they fail**

Run: `node --test tests/js/video_pane.test.js`
Expected: FAIL — 上传方图后方向仍是横屏、`shape-note` 为空

- [ ] **Step 3: Implement in `desk/static/js/panes/video.js`**

1) Task 4 改过的 `video_size.js` import 加上 `frameFollow, shapeOf`：

```js
import { CUSTOM, ORIENTATIONS, frameFollow, matchSize, parseSize, presetsFor, shapeOf, snap32, tierOf, videoCostNote } from "../pure/video_size.js";
```

2) 文件顶部 `function closestFrames` 之后加：

```js
// Z-22：本地选的首帧在浏览器里解码读尺寸；解码不了返回 null（不跟随）。
async function decodeImageSize(file) {
  try {
    if (typeof globalThis.createImageBitmap !== "function") return null;
    const bitmap = await globalThis.createImageBitmap(file);
    const size = { width: bitmap.width, height: bitmap.height };
    bitmap.close?.();
    return size;
  } catch { return null; }
}
```

3) `const drawSeed = ctx.randomSeed ?? randomSeed;` 之后加：

```js
  const readFrameSize = ctx.imageSize ?? decodeImageSize;
```

4) `lookupImage` 的 return 行：

```js
    return index >= 0 && hasImage(attempts[index]) ? { output: attempts[index].output, title: sessionTitle(session), index } : null;
```

改为：

```js
    const attempt = attempts[index];
    return index >= 0 && hasImage(attempt)
      ? { output: attempt.output, title: sessionTitle(session), index, width: attempt.params?.width, height: attempt.params?.height } : null;
```

5) Task 4 加的 `let lastPreset = …` 之后加：

```js
  // Z-23/Z-26：这个首帧来源的画幅由用户（手动改方向）或回填（保存的尺寸）定了，迟到的首帧尺寸不再改它。
  let pinnedFor = null;
  function setShapeNote(text) { if (els.shapeNote) els.shapeNote.textContent = text; }
  // Z-21/24/25：首帧尺寸读回来后，仍是当前「图生」首帧、且没被定住，才按形状切方向或提示。
  function followFirstFrame(source, frame) {
    if (first !== source || source?.type === "continue" || pinnedFor === source || els.mode.value !== "image") return;
    const custom = els.size.value === CUSTOM;
    const size = currentSize();
    const current = { orientation: custom ? shapeOf(size.width, size.height) : orientation, custom };
    const result = frameFollow(current, frame);
    if (result.orientation) chooseOrientation(result.orientation);
    setShapeNote(result.note);
  }
```

6) Task 4 的方向控件 `onChange` 改为（手动改方向：定住当前首帧，清提示）：

```js
    onChange: (index) => { pinnedFor = first; setShapeNote(""); chooseOrientation(ORIENTATIONS[index].value); },
```

7) `setFirst` 改为：

```js
  function setFirst(source) {
    first = source;
    firstGone = false;
    setShapeNote("");
    if (source?.type === "upload" && source.file) setPreview(els.firstPreview, "img", fileUrl(source.file), { name: source.name, objectUrl: true });
    else setPreview(els.firstPreview, "img", null);
    if (source?.type === "ref") {
      checkImageRef(source, () => first, () => { first = null; firstGone = true; }, els.firstPreview,
        (found) => followFirstFrame(source, { width: found.width, height: found.height }));
    }
    renderInputs();
  }
```

8) `checkImageRef` 签名加第五个参数 `onFound`，在函数末尾 `renderInputs();` 之后调用：

```js
  async function checkImageRef(source, current, gone, box, onFound) {
    const found = await lookupImage(source.ref);
    if (current() !== source) return;
    if (found === undefined) { pane.setError("暂时读不到图片会话，请稍后重试"); return; }
    if (!found) { gone(); renderInputs(); return; }
    source.title = found.title; source.index = found.index;
    setPreview(box, "img", api.serveOutput(found.output), { name: found.title });
    renderInputs();
    onFound?.(found);
  }
```

9) `slots` 里首帧那一项：

```js
    { input: els.firstUpload, tag: "img", take: (file) => setFirst({ type: "upload", file, name: file.name }) },
```

改为：

```js
    { input: els.firstUpload, tag: "img", take: (file) => {
      const source = { type: "upload", file, name: file.name };
      setFirst(source);
      readFrameSize(file).then((frame) => followFirstFrame(source, frame));
    } },
```

10) `prefill` 里 `setFirst(nextFirst);` 之后加一行：

```js
    pinnedFor = nextFirst; // Z-26：回填恢复的是当时保存的尺寸，带回的首帧不改它
```

- [ ] **Step 4: Run tests**

Run: `node --test tests/js/video_pane.test.js` → PASS
Run: `node --test tests/js/` → 全部 PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/video.js tests/js/video_pane.test.js
git commit -m "feat(video): 首帧形状自动跟随——方向不同就切并提示，自定义只提示拉伸，回填与续写不跟随（Z-21–Z-26）"
```

---

### Task 6: e2e + 截图目检

**Files:**
- Create: `tests/e2e/test_video_size.py`

**Interfaces:**
- Consumes: Task 4/5 的 DOM 钩子；`launch_test_harness(tmp_path, model_states=…, media_script=…)`、`MediaScript`、`fast_media_steps`（`desk.testing`、`desk.testing.scripts`）。

- [ ] **Step 1: Write the e2e**

```python
# tests/e2e/test_video_size.py
"""视频画幅（视频画幅设计 Z-52）：竖屏档位与自定义尺寸真的按选的宽高生成；上传方图做首帧时方向切到方形；
续写时画幅控件锁住。截图写到 $LMD_VIDEO_SIZE_SHOTS（未设置时写 tmp_path）。"""
from __future__ import annotations

import os
import struct
import zlib
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, fast_media_steps


def _png(width: int, height: int) -> bytes:
    raw = b"".join(b"\x00" + b"\x80\x80\x80" * width for _ in range(height))
    chunk = lambda tag, data: struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def _shot(page, tmp_path, name):
    folder = Path(os.environ.get("LMD_VIDEO_SIZE_SHOTS") or tmp_path)
    folder.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(folder / f"{name}.png"))


def _orientation(pane):
    return pane.locator("[data-video-orientation] [role=radio][aria-checked=true]")


def _attempts(page, harness):
    sessions = page.request.get(f"{harness.base_url}/api/media-sessions/video").json()
    session = page.request.get(f"{harness.base_url}/api/media-sessions/video/{sessions[0]['id']}").json()
    return session["attempts"]


def test_portrait_and_custom_sizes_generate_with_those_dimensions(page, tmp_path):
    with launch_test_harness(tmp_path, model_states={"h3": "present"},
                             media_script=MediaScript([fast_media_steps(), fast_media_steps()])) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(harness.base_url + "#tab=video")
        pane = page.locator("#pane-video")
        pane.locator("[data-video-orientation] [role=radio]", has_text="竖屏").click()
        expect(_orientation(pane)).to_have_text("竖屏")
        pane.locator("[data-video-advanced] summary").click()
        pane.locator("[data-video-size]").select_option("448x768")
        pane.locator("[data-video-prompt]").fill("竖屏的雨夜街道")
        pane.locator("[data-video-start]").click()
        expect(pane.locator("[data-video-timeline] .attempt").first).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        _shot(page, tmp_path, "portrait-1280")

        pane.locator("[data-video-size]").select_option("custom")
        pane.locator("[data-video-height]").fill("810")
        pane.locator("[data-video-height]").blur()
        expect(pane.locator("[data-video-height]")).to_have_value("800")
        pane.locator("[data-video-start]").click()
        expect(pane.locator("[data-video-timeline] .attempt")).to_have_count(2)
        expect(pane.locator("[data-video-timeline] .attempt").nth(1)).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        page.set_viewport_size({"width": 900, "height": 700})
        _shot(page, tmp_path, "custom-900")

        sizes = [(a["params"]["width"], a["params"]["height"]) for a in _attempts(page, harness)]
        assert sizes == [(448, 768), (448, 800)]


def test_square_first_frame_switches_orientation_and_continuation_locks_size(page, tmp_path):
    with launch_test_harness(tmp_path, model_states={"h3": "present"},
                             media_script=MediaScript([fast_media_steps()])) as harness:
        page.set_viewport_size({"width": 1280, "height": 800})
        page.goto(harness.base_url + "#tab=video")
        pane = page.locator("#pane-video")
        pane.locator("[data-video-mode]").select_option("image")
        square = tmp_path / "square.png"
        square.write_bytes(_png(600, 600))
        pane.locator("[data-video-first-upload]").set_input_files(str(square))
        expect(_orientation(pane)).to_have_text("方形")
        expect(pane.locator("[data-video-shape-note]")).to_have_text("已按首帧切到方形")
        _shot(page, tmp_path, "square-first-frame-1280")

        pane.locator("[data-video-prompt]").fill("方形的猫")
        pane.locator("[data-video-start]").click()
        card = pane.locator("[data-video-timeline] .attempt").first
        expect(card).to_have_attribute("data-attempt-status", "done", timeout=15_000)
        assert [(a["params"]["width"], a["params"]["height"]) for a in _attempts(page, harness)] == [(384, 384)]

        card.get_by_role("button", name="接着往下生").click()
        expect(pane.locator("[data-video-size]")).to_be_disabled()
        for radio in pane.locator("[data-video-orientation] [role=radio]").all():
            expect(radio).to_be_disabled()
        expect(pane.locator("[data-video-size]")).to_have_attribute("title", "接着往下生沿用上一段的画幅")
        pane.locator("[data-video-chip-clear]").click()
        expect(pane.locator("[data-video-size]")).to_be_enabled()
```

若「接着往下生」在卡片收起时不可见，先点卡片的 `.attempt-row` 展开（参照 `tests/e2e/test_video_sessions.py` 的 `_expanded`）。若 harness 的会话列表接口返回结构不同（例如带 `sessions` 键），按 `tests/e2e/test_video_sessions.py` 的 `_session` 写法取会话。

- [ ] **Step 2: Run**

Run: `LMD_VIDEO_SIZE_SHOTS=/tmp/lmd-video-size-shots python3 -m pytest tests/e2e/test_video_size.py -q`
Expected: PASS

- [ ] **Step 3: Look at the screenshots**

用 Read 工具逐张看 `/tmp/lmd-video-size-shots/*.png`：方向分段控件与「生成方式」同一行对齐、不挤压素材区；自定义宽高框在画幅下拉后面、900 宽不换行错位；方形首帧提示在预览下方、不与按钮重叠。有问题改 `app.css` 第 17 节并重跑 Step 2。

- [ ] **Step 4: Full suites**

Run: `node --test tests/js/` → 全部 PASS
Run: `python3 -m pytest -q --ignore=tests/e2e` → PASS
Run: `python3 -m pytest tests/e2e -q` → 全部 PASS（`test_video_flow.py`、`test_video_sessions.py`、`test_video_soundtrack.py` 里若有按旧下拉值 `select_option("1024x576")` 之类仍可用：档位值没变）

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/test_video_size.py desk/static/app.css
git commit -m "test(video): e2e——竖屏与自定义尺寸、方形首帧跟随、续写锁定画幅（Z-52）"
```
