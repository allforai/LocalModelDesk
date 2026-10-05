# 素材库预览 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把素材库从纯文字列表改成类访达的缩略图 / 列表 / 明细三视图，加类型筛选、预览弹层与键盘操作。

**Architecture:** 纯前端。条目模型（合并、筛选、排序、偏好归一）放进纯函数模块 `pure/library_view.js`；预览弹层是独立小部件 `widgets/library_preview.js`；`panes/library.js` 重写为工具栏 + 三视图渲染 + 选中/键盘/试听，并把顶部播放区去掉。`main.js` 在离开素材库页时调 `onHide()` 停声。

**Tech Stack:** 原生 ES 模块、无框架；测试 `node --test`（`tests/js/support/fake_dom.js` 的假 DOM）、Playwright（`tests/e2e`，Chromium + 一条 WebKit 用例）。

**Spec:** `docs/superpowers/specs/2026-09-30-library-preview-design.md`（L-xx）。执行者两份都读。

## Global Constraints

- 纯前端，不改后端接口（L-00a）：`GET /api/outputs`、`GET /api/history?limit=200`、`/api/outputs/<name>`、`POST /api/outputs/<name>/reveal`。
- 偏好存 `localStorage` 键 `lmd.library`（JSON），读写都 try/catch；默认：缩略图视图、全部、200px、`ts desc`（L-11）。
- 缩略图大小 140–320px，步长 20（L-20）。
- 条目主体是 `<button data-lib-item>`，动作按钮是它的兄弟节点，不嵌套（L-30）。
- 文案（逐字使用）：「全部 / 图片 / 视频 / 音乐」「缩略图 / 列表 / 明细」「刷新」「预览」「在访达中显示」「回填参数」「试听」「暂停试听」「上一件」「下一件」「关闭」「文件已不在」「无法预览这种文件」「没有这类成品。当前筛选：<类型>」「还没有成品。去「图片」「视频」或「音乐」面板生成第一件，它会出现在这里。」
- 台面只有深色一套配色；动效受全局 `prefers-reduced-motion` 规则约束（`app.css` 已有，不另写）。
- 台面未发布，不谈兼容、不留旧代码路径。
- 测试命令：`node --test tests/js/`；`python3 -m pytest -q --ignore=tests/e2e`；`python3 -m pytest tests/e2e -q`（系统 python3；`.venv-desk` 没有 pytest）。`desk/static` 有改动就必须跑 e2e。

## Rulings made while planning (spec vs. code)

- L-24 写「右下角」试听按钮，但右下角已放时长角标（L-22/L-23）→ 试听按钮放**右上角**。代价：只是位置。
- L-52 把 `test_library_panel.py::test_audio_player_matches_the_dark_palette` 列为要迁移，核对后它只检查音乐会话卡片里的播放器，不碰素材库 → 不改它。
- L-43 只说空格要让给控件；同理 ←/→ 在焦点位于 `video/audio/input/textarea/select` 上时也让给控件（视频进度键）。

## Review Focus

1. 一页有几十段视频时缩略图不能一次全拉：没有进视口的视频不设 `src`（Task 3 测试「懒加载」钉住）。
2. 文件名带空格/中文时缩略图、预览、试听的地址要编码：`/api/outputs/a%20b.png`（Task 3、Task 2 测试钉住）。
3. 在筛选后的视图里打开预览，←/→ 只在这个筛选 + 排序的顺序里翻，不会翻到别的类型（Task 3 测试钉住）。
4. 试听中点「刷新」、切换筛选或离开页面，声音必须停、按钮复位（Task 3 测试钉住）。
5. 焦点在试听/动作按钮上按 Enter 或空格，不能误开预览；焦点在条目上按 Enter/空格打开预览后，同一次按键不能把刚开的预览关掉（Task 3 测试钉住）。

---

## File Structure

- Create `desk/static/js/pure/library_view.js` — 条目模型：`buildItems`、`filterItems`、`sortItems`、`visibleItems`、`normalizePrefs`、`specText`、`clockText`、`hasMedia`、常量。无 DOM。
- Create `desk/static/js/widgets/library_preview.js` — `openLibraryPreview(doc, opts)`：遮罩弹层、翻页、键盘、释放媒体。
- Rewrite `desk/static/js/panes/library.js` — 工具栏、三视图、缩略图（懒加载/悬停播放/失败回落）、选中、键盘、试听、`onHide`。
- Modify `desk/static/index.html:134` — 素材库 section 改为 `toolbar / error / view` 三个容器。
- Modify `desk/static/js/main.js:99-111` — `showTab` 离开素材库时调 `panes.library.onHide()`。
- Modify `desk/static/js/icons.js` — 加 `grid list table file alert chevron-left chevron-right`。
- Modify `desk/static/js/widgets/segment_switch.js:1` — 文件头注释「两项」改为任意项。
- Modify `desk/static/app.css` — 去掉旧 `[data-lib-player]`/`[data-lib-list]`/`.lib-row` 规则，新增第 16 节。
- Create `tests/js/library_view.test.js`、`tests/js/library_preview.test.js`；Rewrite `tests/js/library_pane.test.js`。
- Create `tests/e2e/test_library_views.py`、`tests/e2e/test_library_webkit.py`；Modify `tests/e2e/test_library_panel.py`、`tests/e2e/test_image_sessions.py`、`tests/e2e/test_image_flow.py`、`tests/e2e/test_outputs_range.py`。

---

### Task 1: 条目模型 `pure/library_view.js`

**Files:**
- Create: `desk/static/js/pure/library_view.js`
- Test: `tests/js/library_view.test.js`

**Interfaces:**
- Consumes: `fillPlan(entry)` from `desk/static/js/pure/history_fill.js`（返回回填计划或 `null`）。
- Produces（后续任务逐字使用）:
  - `FILTERS = ["all","image","video","music"]`，`VIEWS = ["grid","list","table"]`，`SORT_KEYS = ["ts","title","kind","duration","dims","bytes","gen"]`，`THUMB_MIN = 140`，`THUMB_MAX = 320`，`DEFAULT_PREFS`。
  - `normalizePrefs(raw) -> {view, filter, thumb, sort:{key, dir}}`
  - `buildItems(outputs, history) -> Item[]`（已按 `ts desc` 排好）
  - `Item = { key, kind, status, ts, title, prompt, spec, duration_s, width, height, bytes, gen_s, output, missing, entry, error, plan }`（缺值为 `null`）
  - `filterItems(items, filter)`、`sortItems(items, {key, dir})`、`visibleItems(items, prefs)`
  - `specText(entry) -> string`、`clockText(seconds) -> "m:ss"`、`hasMedia(item) -> boolean`

- [ ] **Step 1: Write the failing tests**

```js
// tests/js/library_view.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  buildItems, clockText, DEFAULT_PREFS, filterItems, hasMedia, normalizePrefs, sortItems, specText, visibleItems,
} from "../../desk/static/js/pure/library_view.js";

const video = (extra = {}) => ({ kind: "video", status: "done", ts: "2026-09-25T10:00:00Z", output: "h3-1.mp4",
  params: { prompt: "海边", width: 768, height: 448, frames: 48, steps: 16 }, duration_s: 80, ...extra });

test("合并：历史按文件名配成品；output 与 joined_output 各占一条（B-43）；孤儿成品单独一条；新的在前", () => {
  const outputs = [
    { name: "h3-1.mp4", kind: "video", bytes: 10, ts: "2026-09-25T10:00:00Z" },
    { name: "h3-joined-1.mp4", kind: "video", bytes: 20, ts: "2026-09-25T10:05:00Z" },
    { name: "orphan.wav", kind: "music", bytes: 5, ts: "2026-09-26T09:00:00Z" },
  ];
  const items = buildItems(outputs, [video({ joined_output: "h3-joined-1.mp4", ts: "2026-09-25T10:05:00Z" })]);
  assert.deepEqual(items.map((i) => i.key), ["o:orphan.wav", "o:h3-1.mp4", "o:h3-joined-1.mp4"]);
  assert.equal(items[0].title, "orphan.wav");
  assert.equal(items[0].entry, null);
  assert.equal(items[0].plan, null);
  for (const item of items.slice(1)) {
    assert.equal(item.title, "海边");
    assert.ok(item.plan, "有历史的条目带回填计划");
  }
  assert.equal(items[1].bytes, 10);
  assert.equal(items[2].bytes, 20);
});

test("条目字段：时长、画幅、耗时、规格", () => {
  const [v] = buildItems([{ name: "h3-1.mp4", kind: "video", bytes: 10 }], [video()]);
  assert.equal(v.duration_s, 2);
  assert.equal(v.width, 768);
  assert.equal(v.height, 448);
  assert.equal(v.gen_s, 80);
  assert.equal(v.spec, "768×448 · 约 2 秒 · 16步");
  const music = { kind: "music", status: "done", ts: "t", output: "music3-1.wav",
    params: { caption: "民谣", lyrics: "啦", duration: 300 }, audio_seconds: 29.71 };
  const [m] = buildItems([{ name: "music3-1.wav", kind: "music" }], [music]);
  assert.equal(m.title, "民谣");
  assert.equal(m.duration_s, 29.71);
  assert.equal(m.width, null);
  assert.equal(m.spec, "成品 30 秒（请求 300 秒）");
  const [m2] = buildItems([], [{ ...music, audio_seconds: undefined, output: null, status: "failed" }]);
  assert.equal(m2.duration_s, 300);
  assert.equal(specText({ kind: "image", params: { width: 1024, height: 768, steps: 40, seed: 0 } }), "1024×768 · 40步 · 种子 0");
});

test("missing：完成但文件不在；失败记录不算 missing；hasMedia 只认有文件的条目", () => {
  const items = buildItems([], [
    video({ ts: "2026-09-25T10:00:00Z" }),
    video({ ts: "2026-09-24T10:00:00Z", status: "failed", output: null, error: "exit_nonzero: exit 1" }),
  ]);
  assert.equal(items[0].missing, true);
  assert.equal(items[0].output, "h3-1.mp4");
  assert.equal(hasMedia(items[0]), false);
  assert.equal(items[1].missing, false);
  assert.equal(items[1].error, "exit_nonzero: exit 1");
  assert.equal(hasMedia(items[1]), false);
  const [orphan] = buildItems([{ name: "x.bin", kind: "file", bytes: 1 }], []);
  assert.equal(hasMedia(orphan), true);
});

test("key 跨刷新稳定且同一次渲染内不重复", () => {
  const entry = { kind: "music", status: "failed", ts: "2026-09-25T10:00:00Z", output: null, params: {} };
  const once = buildItems([], [entry, { ...entry }]);
  assert.deepEqual(once.map((i) => i.key), ["h:2026-09-25T10:00:00Z:music:", "h:2026-09-25T10:00:00Z:music:#2"]);
  const again = buildItems([], [entry, { ...entry }]);
  assert.deepEqual(again.map((i) => i.key), once.map((i) => i.key));
  const [withAttempt] = buildItems([], [{ ...entry, attempt_id: "a7" }]);
  assert.equal(withAttempt.key, "h:2026-09-25T10:00:00Z:music:a7");
});

test("筛选：file 只在 all 下出现", () => {
  const items = buildItems(
    [{ name: "a.png", kind: "image" }, { name: "b.wav", kind: "music" }, { name: "c.bin", kind: "file" }], []);
  assert.deepEqual(filterItems(items, "all").length, 3);
  assert.deepEqual(filterItems(items, "image").map((i) => i.key), ["o:a.png"]);
  assert.deepEqual(filterItems(items, "music").map((i) => i.key), ["o:b.wav"]);
  assert.deepEqual(filterItems(items, "video"), []);
});

test("排序：缺值不论方向都在最后；提示词按中文排；同值按时间倒序", () => {
  const items = [
    { key: "a", ts: "2026-01-01", title: "乙", bytes: 5, kind: "image", duration_s: null, width: 2, height: 2, gen_s: 1 },
    { key: "b", ts: "2026-01-03", title: "甲", bytes: null, kind: "video", duration_s: 3, width: null, height: null, gen_s: null },
    { key: "c", ts: "2026-01-02", title: "丙", bytes: 9, kind: "image", duration_s: 1, width: 4, height: 4, gen_s: 1 },
  ];
  const keys = (sort) => sortItems(items, sort).map((i) => i.key);
  assert.deepEqual(keys({ key: "bytes", dir: "desc" }), ["c", "a", "b"]);
  assert.deepEqual(keys({ key: "bytes", dir: "asc" }), ["a", "c", "b"]);
  assert.deepEqual(keys({ key: "duration", dir: "asc" }), ["c", "b", "a"]);
  assert.deepEqual(keys({ key: "dims", dir: "desc" }), ["c", "a", "b"]);
  assert.deepEqual(keys({ key: "gen", dir: "asc" }), ["c", "a", "b"], "同值（1）按时间倒序");
  assert.deepEqual(keys({ key: "ts", dir: "desc" }), ["b", "c", "a"]);
  assert.deepEqual(keys({ key: "title", dir: "asc" }), ["c", "b", "a"], "中文排序：丙 甲 乙");
  assert.deepEqual(keys({ key: "nonsense", dir: "desc" }), ["b", "c", "a"], "未知键按时间倒序");
});

test("visibleItems 先筛后排", () => {
  const items = buildItems([{ name: "a.png", kind: "image", bytes: 1, ts: "2026-01-01" },
    { name: "b.png", kind: "image", bytes: 9, ts: "2026-01-02" }, { name: "c.wav", kind: "music", bytes: 5 }], []);
  assert.deepEqual(visibleItems(items, { filter: "image", sort: { key: "bytes", dir: "asc" } }).map((i) => i.key),
    ["o:a.png", "o:b.png"]);
});

test("偏好归一：非法值回落默认，大小夹在 140–320", () => {
  assert.deepEqual(normalizePrefs(null), { view: "grid", filter: "all", thumb: 200, sort: { key: "ts", dir: "desc" } });
  assert.deepEqual(normalizePrefs("garbage"), normalizePrefs(null));
  assert.deepEqual(normalizePrefs({ view: "table", filter: "music", thumb: 999, sort: { key: "bytes", dir: "asc" } }),
    { view: "table", filter: "music", thumb: 320, sort: { key: "bytes", dir: "asc" } });
  assert.deepEqual(normalizePrefs({ view: "column", filter: "file", thumb: "x", sort: { key: "x", dir: "up" } }), normalizePrefs(null));
  assert.equal(normalizePrefs({ thumb: 10 }).thumb, 140);
  assert.equal(DEFAULT_PREFS.view, "grid");
});

test("clockText", () => {
  assert.equal(clockText(0), "0:00");
  assert.equal(clockText(29.71), "0:30");
  assert.equal(clockText(125), "2:05");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/library_view.test.js`
Expected: FAIL — `Cannot find module …/pure/library_view.js`

- [ ] **Step 3: Write the implementation**

```js
// desk/static/js/pure/library_view.js
// 素材库条目模型（素材库预览设计 L-01–L-06）：合并成品与历史、筛选、排序、偏好归一。纯函数，无 DOM。
import { fillPlan } from "./history_fill.js";

export const FILTERS = ["all", "image", "video", "music"];
export const VIEWS = ["grid", "list", "table"];
export const SORT_KEYS = ["ts", "title", "kind", "duration", "dims", "bytes", "gen"];
export const THUMB_MIN = 140;
export const THUMB_MAX = 320;
export const DEFAULT_PREFS = Object.freeze({
  view: "grid", filter: "all", thumb: 200, sort: Object.freeze({ key: "ts", dir: "desc" }),
});

// L-11：读到什么都归一成合法偏好；大小夹在 140–320。
export function normalizePrefs(raw) {
  const p = raw && typeof raw === "object" ? raw : {};
  const sort = p.sort && typeof p.sort === "object" ? p.sort : {};
  const thumb = typeof p.thumb === "number" ? p.thumb : Number.NaN;
  return {
    view: VIEWS.includes(p.view) ? p.view : DEFAULT_PREFS.view,
    filter: FILTERS.includes(p.filter) ? p.filter : DEFAULT_PREFS.filter,
    thumb: Number.isFinite(thumb) ? Math.min(THUMB_MAX, Math.max(THUMB_MIN, Math.round(thumb))) : DEFAULT_PREFS.thumb,
    sort: {
      key: SORT_KEYS.includes(sort.key) ? sort.key : DEFAULT_PREFS.sort.key,
      dir: sort.dir === "asc" || sort.dir === "desc" ? sort.dir : DEFAULT_PREFS.sort.dir,
    },
  };
}

// 一行规格（沿用原素材库的写法）：图片「宽×高 · 步数 · 种子」，视频「宽×高 · 约 N 秒 · 步数」，歌曲按成品实际时长并注明请求值。
export function specText(entry) {
  const params = entry.params ?? {};
  const parts = entry.kind === "image"
    ? [params.width && params.height ? `${params.width}×${params.height}` : null,
      params.steps ? `${params.steps}步` : null, params.seed != null ? `种子 ${params.seed}` : null]
    : entry.kind === "video"
    ? [params.width && params.height ? `${params.width}×${params.height}` : null,
      params.frames ? `约 ${Math.round(params.frames / 24)} 秒` : null, params.steps ? `${params.steps}步` : null]
    : [Number.isFinite(entry.audio_seconds)
      ? `成品 ${Math.round(entry.audio_seconds)} 秒${params.duration ? `（请求 ${params.duration} 秒）` : ""}`
      : params.duration ? `${params.duration}s` : null];
  return parts.filter(Boolean).join(" · ");
}

export function clockText(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

// 有能播/能看的文件：有文件名且不是 missing（失败、取消、文件已不在的条目都没有）。
export const hasMedia = (item) => !!item.output && !item.missing;

// L-04：音乐取成品实际时长，否则请求时长；视频按 24 帧/秒；图片没有。
function mediaSeconds(entry) {
  const params = entry.params ?? {};
  if (entry.kind === "music") {
    if (Number.isFinite(entry.audio_seconds)) return entry.audio_seconds;
    const requested = Number(params.duration);
    return params.duration != null && params.duration !== "" && Number.isFinite(requested) ? requested : null;
  }
  if (entry.kind === "video" && Number(params.frames) > 0) return Number(params.frames) / 24;
  return null;
}

function fromEntry(entry, output) {
  const params = entry.params ?? {};
  const prompt = String(params.prompt ?? params.caption ?? "");
  const sized = entry.kind === "image" || entry.kind === "video";
  const missing = !output && entry.status === "done" && !!entry.output;
  return {
    key: output ? `o:${output.name}` : `h:${entry.ts ?? ""}:${entry.kind}:${entry.attempt_id ?? ""}`,
    kind: entry.kind,
    status: entry.status,
    ts: entry.ts ?? output?.ts ?? "",
    title: prompt || "（无提示词）",
    prompt,
    spec: specText(entry),
    duration_s: mediaSeconds(entry),
    width: sized ? Number(params.width) || null : null,
    height: sized ? Number(params.height) || null : null,
    bytes: output?.bytes ?? null,
    gen_s: Number.isFinite(entry.duration_s) ? entry.duration_s : null,
    output: output?.name ?? (missing ? entry.output : null),
    missing,
    entry,
    error: entry.error ?? null,
    plan: fillPlan(entry),
  };
}

function fromOutput(output) {
  return {
    key: `o:${output.name}`, kind: output.kind ?? "file", status: "done", ts: output.ts ?? "",
    title: output.name, prompt: "", spec: "", duration_s: null, width: null, height: null,
    bytes: output.bytes ?? null, gen_s: null, output: output.name, missing: false, entry: null, error: null, plan: null,
  };
}

// L-01：历史按文件名配成品；一条历史的 output 与 joined_output 各占一条（B-43）；没配上的历史、没配上的成品各占一条。
export function buildItems(outputs = [], history = []) {
  const byName = new Map(outputs.map((output) => [output.name, output]));
  const matched = new Set();
  const items = [];
  for (const entry of history) {
    let hit = false;
    for (const name of [entry.output, entry.joined_output].filter(Boolean)) {
      const output = byName.get(name);
      if (!output) continue;
      matched.add(name);
      hit = true;
      items.push(fromEntry(entry, output));
    }
    if (!hit) items.push(fromEntry(entry, null));
  }
  for (const output of outputs) if (!matched.has(output.name)) items.push(fromOutput(output));
  const seen = new Map();
  for (const item of items) {
    const count = (seen.get(item.key) ?? 0) + 1;
    seen.set(item.key, count);
    if (count > 1) item.key = `${item.key}#${count}`;
  }
  return sortItems(items, DEFAULT_PREFS.sort);
}

export function filterItems(items, filter) {
  return filter === "all" ? [...items] : items.filter((item) => item.kind === filter);
}

const SORT_VALUE = {
  ts: (item) => item.ts || null,
  title: (item) => item.title || null,
  kind: (item) => item.kind || null,
  duration: (item) => item.duration_s ?? null,
  dims: (item) => (item.width && item.height ? item.width * item.height : null),
  bytes: (item) => item.bytes ?? null,
  gen: (item) => item.gen_s ?? null,
};
const plain = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

// L-06：缺值不论方向都排最后；提示词按中文排；同值按时间倒序。
export function sortItems(items, { key = "ts", dir = "desc" } = {}) {
  const value = SORT_VALUE[key] ?? SORT_VALUE.ts;
  const sign = dir === "asc" ? 1 : -1;
  const compare = key === "title" ? (a, b) => a.localeCompare(b, "zh") : plain;
  return [...items].sort((x, y) => {
    const a = value(x);
    const b = value(y);
    if (a == null && b != null) return 1;
    if (b == null && a != null) return -1;
    if (a != null && b != null) {
      const diff = compare(a, b);
      if (diff) return sign * diff;
    }
    return plain(String(y.ts ?? ""), String(x.ts ?? ""));
  });
}

export function visibleItems(items, prefs) {
  return sortItems(filterItems(items, prefs.filter), prefs.sort);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/js/library_view.test.js`
Expected: PASS（9 tests）

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/pure/library_view.js tests/js/library_view.test.js
git commit -m "feat(library): 素材库条目模型——合并、筛选、排序、偏好归一（L-01–L-06）"
```

---

### Task 2: 图标 + 预览弹层 `widgets/library_preview.js`

**Files:**
- Modify: `desk/static/js/icons.js`（`PATHS` 里加 7 个图标）
- Create: `desk/static/js/widgets/library_preview.js`
- Test: `tests/js/library_preview.test.js`

**Interfaces:**
- Consumes: Task 1 的 `buildItems`、`clockText`、`hasMedia`；`renderErrorBlock(doc, {code, message})`（`widgets/error_block.js`）；`formatBytes`、`formatDuration`、`formatTimestamp`（`pure/format.js`）；`addIcon(control, name, doc)`。
- Produces: `openLibraryPreview(doc, { items, index, serveOutput, onFill, onReveal, onClose }) -> { close(), current() }`
  - `items`：Item 数组快照；`index`：起始下标；`serveOutput(name) -> url`；`onFill(plan)`；`onReveal(name) -> Promise`；`onClose(index)` 关闭后调用一次，参数是最后看的下标。
  - DOM：`div.overlay.lib-preview-overlay > div.dialog.lib-preview[role=dialog][aria-modal=true]`，子节点依次 `button[data-lib-prev]`、`div.lib-preview-stage[data-lib-preview-stage]`、`button[data-lib-next]`、`div.lib-preview-info`；关闭按钮 `[data-lib-preview-close]`；错误行 `[data-lib-preview-error]`。
  - 新图标名：`grid list table file alert chevron-left chevron-right`。

- [ ] **Step 1: Add the icons**

在 `desk/static/js/icons.js` 的 `PATHS` 对象里、`"sidebar-open"` 一行之后加：

```js
  grid: "M4 4h7v7H4V4Zm9 0h7v7h-7V4ZM4 13h7v7H4v-7Zm9 0h7v7h-7v-7Z",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  table: "M3 4h18v16H3V4Zm0 5h18M3 14h18M9 9v11",
  file: "M14 3H6a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V9l-6-6Zm0 0v6h6",
  alert: "M12 3 2 21h20L12 3Zm0 6v5m0 3h.01",
  "chevron-left": "m15 18-6-6 6-6",
  "chevron-right": "m9 18 6-6-6-6",
```

- [ ] **Step 2: Write the failing tests**

```js
// tests/js/library_preview.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { Element, find, byData } from "./support/fake_dom.js";
import { buildItems } from "../../desk/static/js/pure/library_view.js";
import { openLibraryPreview } from "../../desk/static/js/widgets/library_preview.js";

function makeDoc() {
  const doc = {
    body: new Element("body"), listeners: {},
    createElement: (tag) => new Element(tag),
    addEventListener(type, fn) { (doc.listeners[type] ??= []).push(fn); },
    removeEventListener(type, fn) { doc.listeners[type] = (doc.listeners[type] ?? []).filter((f) => f !== fn); },
    key(key, target = doc.body) {
      for (const fn of [...(doc.listeners.keydown ?? [])]) fn({ key, target, preventDefault() {}, stopPropagation() {} });
    },
  };
  return doc;
}
const serveOutput = (name) => `/api/outputs/${encodeURIComponent(name)}`;
const outputs = [
  { name: "a b.png", kind: "image", bytes: 2048, ts: "2026-09-25T10:03:00Z" },
  { name: "h3-1.mp4", kind: "video", bytes: 10, ts: "2026-09-25T10:02:00Z" },
  { name: "music3-1.wav", kind: "music", bytes: 10, ts: "2026-09-25T10:01:00Z" },
];
const history = [
  { kind: "image", status: "done", ts: "2026-09-25T10:03:00Z", output: "a b.png", duration_s: 65,
    params: { prompt: "橘猫", width: 1024, height: 768, steps: 40, seed: 0 }, session_id: "s1", attempt_id: "a1" },
  { kind: "video", status: "failed", ts: "2026-09-24T10:00:00Z", output: null, error: "exit_nonzero: exit 1",
    params: { prompt: "失败的视频", frames: 48 } },
  { kind: "video", status: "done", ts: "2026-09-23T10:00:00Z", output: "gone.mp4", params: { prompt: "删掉的视频" } },
];
const items = buildItems(outputs, history);
const open = (doc, extra = {}) => openLibraryPreview(doc, { items, index: 0, serveOutput, ...extra });
const stage = (doc) => byData(doc.body, "libPreviewStage");
const dialog = (doc) => find(doc.body, (n) => n.attrs?.role === "dialog");

test("打开：遮罩 + 对话框，图片按地址编码显示，信息区有提示词、规格、耗时、文件与大小，焦点进弹层", () => {
  const doc = makeDoc();
  open(doc);
  const box = dialog(doc);
  assert.equal(box.attrs["aria-modal"], "true");
  assert.equal(box.attrs["aria-label"], "橘猫");
  assert.ok(box.focused > 0);
  const img = stage(doc).children[0];
  assert.equal(img.tagName, "img");
  assert.equal(img.src, "/api/outputs/a%20b.png");
  assert.equal(img.alt, "橘猫");
  const text = box.textContent;
  for (const piece of ["橘猫", "1024×768 · 40步 · 种子 0", "耗时 1分05秒", "a b.png · 2 KiB"]) assert.ok(text.includes(piece), piece);
  assert.equal(byData(doc.body, "libPrev").disabled, true);
  assert.equal(byData(doc.body, "libNext").disabled, false);
});

test("←/→ 翻页到头停住；视频有声自动播放，音乐有大卡片 + 播放器；翻走时停止并释放上一件", () => {
  const doc = makeDoc();
  const preview = open(doc);
  doc.key("ArrowLeft");
  assert.equal(preview.current(), 0);
  doc.key("ArrowRight");
  const v = stage(doc).children[0];
  assert.equal(v.tagName, "video");
  assert.equal(v.controls, true);
  assert.equal(v.autoplay, true);
  assert.equal(v.muted, undefined);
  let paused = 0; v.pause = () => { paused += 1; };
  byData(doc.body, "libNext").click();
  assert.equal(paused, 1);
  assert.equal(v.attrs.src, undefined);
  const music = stage(doc).children[0];
  assert.match(music.className, /lib-preview-music/);
  assert.ok(find(music, (n) => n.tagName === "audio" && n.autoplay === true));
  assert.equal(preview.current(), 2);
});

test("失败记录显示错误块；文件已不在显示说明；不认识的文件显示无法预览", () => {
  const doc = makeDoc();
  const failed = items.findIndex((i) => i.status === "failed");
  open(doc, { index: failed });
  assert.ok(find(stage(doc), (n) => n.className === "inline-error job-error"));
  const gone = items.findIndex((i) => i.missing);
  const doc2 = makeDoc();
  open(doc2, { index: gone });
  assert.equal(stage(doc2).textContent, "文件已不在");
  assert.equal(find(doc2.body, (n) => n.tagName === "button" && n.textContent === "在访达中显示"), null);
  const doc3 = makeDoc();
  openLibraryPreview(doc3, { items: buildItems([{ name: "x.bin", kind: "file", bytes: 1 }], []), index: 0, serveOutput });
  assert.equal(stage(doc3).textContent, "无法预览这种文件");
});

test("Esc 关闭并回报最后看的下标；空格只在焦点不在控件上时关闭", () => {
  const doc = makeDoc();
  const closed = [];
  open(doc, { onClose: (i) => closed.push(i) });
  doc.key("ArrowRight");
  doc.key(" ", new Element("button"));
  doc.key(" ", new Element("video"));
  assert.ok(dialog(doc), "焦点在按钮或视频上时空格交给控件");
  doc.key("ArrowRight", new Element("video"));
  assert.equal(closed.length, 0);
  doc.key(" ", new Element("div"));
  assert.deepEqual(closed, [1], "视频上按 → 不翻页，仍停在第 2 件");
  assert.equal(dialog(doc), null);
  assert.deepEqual(doc.listeners.keydown, []);
  doc.key("Escape");
  assert.deepEqual(closed, [1], "关闭只回报一次");
});

test("回填参数：关闭弹层再调 onFill；在访达中显示失败写进弹层错误行；点遮罩关闭", async () => {
  const doc = makeDoc();
  const fills = []; const closed = [];
  open(doc, {
    onFill: (plan) => fills.push(plan), onClose: (i) => closed.push(i),
    onReveal: async () => { throw new Error("成品目录还不存在，生成第一个作品后会自动创建"); },
  });
  find(doc.body, (n) => n.tagName === "button" && n.textContent === "在访达中显示").click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(byData(doc.body, "libPreviewError").textContent, "成品目录还不存在，生成第一个作品后会自动创建");
  find(doc.body, (n) => n.tagName === "button" && n.textContent === "回填参数").click();
  assert.deepEqual(closed, [0]);
  assert.equal(fills.length, 1);
  assert.equal(fills[0].pane, "image");
  const doc2 = makeDoc();
  const closed2 = [];
  open(doc2, { onClose: (i) => closed2.push(i) });
  const overlay = doc2.body.children[0];
  await overlay.dispatch("click", { target: overlay });
  assert.deepEqual(closed2, [0]);
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `node --test tests/js/library_preview.test.js`
Expected: FAIL — `Cannot find module …/widgets/library_preview.js`

- [ ] **Step 4: Write the implementation**

```js
// desk/static/js/widgets/library_preview.js
// 素材库预览弹层（素材库预览设计 L-40–L-44）：遮罩 + role=dialog + aria-modal + Esc/点遮罩关闭，骨架同 confirm.js、
// media_picker.js。←/→ 在打开时的条目快照里翻页、到头停住；空格在焦点不在控件上时关闭；翻页或关闭时停止并释放上一件媒体。
import { addIcon } from "../icons.js";
import { renderErrorBlock } from "./error_block.js";
import { clockText, hasMedia } from "../pure/library_view.js";
import { formatBytes, formatDuration, formatTimestamp } from "../pure/format.js";

const KIND_LABEL = { video: "视频", music: "音乐", image: "图片", file: "文件" };
const STATUS_LABEL = { done: "完成", failed: "失败", cancelled: "已取消" };
// 这些控件自己要用空格（按钮、播放器）或方向键（播放器进度、输入框），弹层不抢。
const SPACE_OWNERS = new Set(["button", "input", "textarea", "select", "video", "audio", "a"]);
const ARROW_OWNERS = new Set(["input", "textarea", "select", "video", "audio"]);
const tagOf = (target) => String(target?.tagName ?? "").toLowerCase();

export function openLibraryPreview(doc, { items, index = 0, serveOutput, onFill, onReveal, onClose }) {
  let at = Math.min(Math.max(0, index), items.length - 1);
  let media = null;
  let closed = false;
  const el = (tag, className = "") => {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    return node;
  };
  const button = (label, icon) => {
    const node = el("button");
    node.textContent = label;
    addIcon(node, icon, doc);
    return node;
  };
  const note = (text) => {
    const p = el("p", "lib-preview-note");
    p.textContent = text;
    return p;
  };

  const overlay = el("div", "overlay lib-preview-overlay");
  const box = el("div", "dialog lib-preview");
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-modal", "true");
  box.tabIndex = -1;
  const stage = el("div", "lib-preview-stage");
  stage.dataset.libPreviewStage = "";
  const info = el("div", "lib-preview-info");
  const nav = (label, icon, dataKey, step) => {
    const node = el("button", "btn-quiet lib-preview-nav");
    node.setAttribute("aria-label", label);
    node.title = label;
    node.dataset[dataKey] = "";
    addIcon(node, icon, doc);
    node.addEventListener("click", () => go(at + step));
    return node;
  };
  const prev = nav("上一件", "chevron-left", "libPrev", -1);
  const next = nav("下一件", "chevron-right", "libNext", 1);
  box.append(prev, stage, next, info);
  overlay.append(box);

  function release() {
    if (!media) return;
    media.pause?.();
    media.removeAttribute?.("src");
    media.load?.();
    media = null;
  }

  function stageNode(item) {
    if (item.missing) return note("文件已不在");
    if (!hasMedia(item)) {
      if (item.error) {
        const [code, ...rest] = item.error.split(": ");
        return renderErrorBlock(doc, { code, message: rest.join(": ") });
      }
      return note(STATUS_LABEL[item.status] ?? "没有成品");
    }
    const src = serveOutput(item.output);
    if (item.kind === "image") {
      const img = el("img");
      img.src = src;
      img.alt = item.title;
      return img;
    }
    if (item.kind === "video") {
      media = el("video");
      media.controls = true;
      media.autoplay = true;
      media.src = src;
      return media;
    }
    if (item.kind === "music") {
      const wrap = el("div", "lib-preview-music");
      const art = el("div", "lib-preview-art");
      addIcon(art, "music", doc);
      media = el("audio");
      media.controls = true;
      media.autoplay = true;
      media.src = src;
      wrap.append(art, media);
      return wrap;
    }
    return note("无法预览这种文件");
  }

  function infoNodes(item) {
    const title = el("h3", "lib-preview-title");
    title.textContent = item.title;
    const lines = [
      [KIND_LABEL[item.kind] ?? item.kind, STATUS_LABEL[item.status] ?? item.status, formatTimestamp(item.ts)].join(" · "),
      item.spec,
      item.duration_s != null ? `时长 ${clockText(item.duration_s)}` : "",
      item.gen_s != null ? `耗时 ${formatDuration(item.gen_s)}` : "",
      item.output ? `${item.output}${item.bytes != null ? ` · ${formatBytes(item.bytes)}` : ""}` : "",
    ].filter(Boolean).map((text) => {
      const p = el("p", "lib-meta");
      p.textContent = text;
      return p;
    });
    const error = el("p", "inline-error");
    error.dataset.libPreviewError = "";
    const actions = el("div", "lib-preview-actions");
    if (item.plan) {
      const fill = button("回填参数", "sliders");
      fill.addEventListener("click", () => {
        const plan = item.plan;
        close();
        onFill?.(plan);
      });
      actions.append(fill);
    }
    if (hasMedia(item)) {
      const reveal = button("在访达中显示", "folder");
      reveal.addEventListener("click", async () => {
        error.textContent = "";
        try { await onReveal?.(item.output); } catch (err) { error.textContent = err.message; }
      });
      actions.append(reveal);
    }
    const closeBtn = button("关闭", "x");
    closeBtn.dataset.libPreviewClose = "";
    closeBtn.addEventListener("click", () => close());
    actions.append(closeBtn);
    return [title, ...lines, actions, error];
  }

  function show(i) {
    release();
    at = i;
    const item = items[at];
    box.setAttribute("aria-label", item.title);
    stage.replaceChildren(stageNode(item));
    info.replaceChildren(...infoNodes(item));
    prev.disabled = at === 0;
    next.disabled = at === items.length - 1;
  }

  function go(i) {
    if (closed || i < 0 || i >= items.length || i === at) return;
    show(i);
  }

  function onKey(event) {
    if (closed) return;
    const tag = tagOf(event.target);
    if (event.key === "Escape") { event.preventDefault?.(); close(); return; }
    if ((event.key === "ArrowLeft" || event.key === "ArrowRight") && !ARROW_OWNERS.has(tag)) {
      event.preventDefault?.();
      go(at + (event.key === "ArrowLeft" ? -1 : 1));
      return;
    }
    if (event.key === " " && !SPACE_OWNERS.has(tag)) { event.preventDefault?.(); close(); }
  }

  function close() {
    if (closed) return;
    closed = true;
    release();
    doc.removeEventListener?.("keydown", onKey);
    overlay.remove();
    onClose?.(at);
  }

  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  doc.addEventListener?.("keydown", onKey);
  doc.body.append(overlay);
  show(at);
  box.focus?.();
  return { close, current: () => at };
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `node --test tests/js/library_preview.test.js`
Expected: PASS（5 tests）

- [ ] **Step 6: Commit**

```bash
git add desk/static/js/icons.js desk/static/js/widgets/library_preview.js tests/js/library_preview.test.js
git commit -m "feat(library): 素材库预览弹层——翻页、键盘、释放媒体、回填与访达（L-40–L-44）"
```

---

### Task 3: 重写素材库页 `panes/library.js`（工具栏、三视图、选中、键盘、试听、切页停声）

**Files:**
- Rewrite: `desk/static/js/panes/library.js`
- Modify: `desk/static/index.html:134`
- Modify: `desk/static/js/main.js:99-100`
- Modify: `desk/static/js/widgets/segment_switch.js:1`
- Rewrite: `tests/js/library_pane.test.js`

**Interfaces:**
- Consumes: Task 1 全部导出；Task 2 `openLibraryPreview`；`renderSegmentSwitch(doc, {labels, checked, onChange, ariaLabel})`（`widgets/segment_switch.js`，按 `labels` 生成任意项）；`api.listOutputs()`、`api.listHistory()`、`api.serveOutput(name)`、`api.revealOutput(name)`；`addIcon`、`setIcon`；`renderErrorBlock`；`formatBytes`、`formatDuration`、`formatTimestamp`。
- Produces:
  - `createLibraryPane(root, ctx) -> { refresh(), onHide() }`；`ctx.applyFill(plan)`；`ctx.storage`（可选，测试注入；缺省 `globalThis.localStorage`）。
  - `PREFS_KEY = "lmd.library"`。
  - DOM 钩子（e2e 用）：`[data-lib-toolbar]`、`[data-lib-error]`、`[data-lib-view]`（属性 `data-lib-mode=grid|list|table`）、`[data-lib-filter]`、`[data-lib-view-btn=grid|list|table]`、`[data-lib-thumb]`、`[data-lib-refresh]`、`[data-lib-list]`、`[data-lib-key]`（每行/卡片）、`[data-output-name]`、`[data-lib-item]`、`[data-lib-audition-btn]`、`[data-lib-audition]`（隐藏 audio）、`[data-lib-sort=<key>]`、`[data-lib-empty]`。

- [ ] **Step 1: Change the markup and the tab hook**

`desk/static/index.html` 第 134 行整行换成：

```html
    <section id="pane-library" data-pane="library" hidden><div class="lib-toolbar" data-lib-toolbar></div><p class="inline-error" data-lib-error></p><div class="lib-view" data-lib-view></div></section>
```

`desk/static/js/main.js` 的 `showTab` 开头两行：

```js
function showTab(name) {
  activeTab = name;
```

改为：

```js
function showTab(name) {
  if (activeTab === "library" && name !== "library") panes.library.onHide(); // L-45：离开素材库停掉试听与悬停播放
  activeTab = name;
```

`desk/static/js/widgets/segment_switch.js` 第 1 行注释里的「两项的分段切换」改为「分段切换（项数由 labels 决定）」，其余不动。

- [ ] **Step 2: Write the failing tests**（整个文件替换）

```js
// tests/js/library_pane.test.js —— 素材库页（素材库预览设计 L-10–L-45）
import test from "node:test";
import assert from "node:assert/strict";
import { Element, find, findAll, byData, flush } from "./support/fake_dom.js";
import { createLibraryPane, PREFS_KEY } from "../../desk/static/js/panes/library.js";

function makeDoc() {
  const doc = {
    body: new Element("body"), listeners: {},
    createElement: (tag) => new Element(tag),
    addEventListener(type, fn) { (doc.listeners[type] ??= []).push(fn); },
    removeEventListener(type, fn) { doc.listeners[type] = (doc.listeners[type] ?? []).filter((f) => f !== fn); },
    key(key, target = doc.body) {
      for (const fn of [...(doc.listeners.keydown ?? [])]) fn({ key, target, preventDefault() {}, stopPropagation() {} });
    },
  };
  return doc;
}
function memoryStorage(initial = {}) {
  const data = { ...initial };
  return { data, getItem: (k) => data[k] ?? null, setItem: (k, v) => { data[k] = String(v); } };
}
function serve(outputs, history, { reveal } = {}) {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push([url, options.method ?? "GET"]);
    if (url.endsWith("/reveal")) return reveal ?? { ok: true, status: 200, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => (url === "/api/outputs" ? outputs : history) };
  };
  return calls;
}
async function mount({ outputs = [], history = [], storage = memoryStorage(), applyFill = () => {}, reveal } = {}) {
  const calls = serve(outputs, history, { reveal });
  const doc = makeDoc();
  const parts = { toolbar: new Element("div"), error: new Element("p"), view: new Element("div") };
  const root = new Element("section");
  root.append(parts.toolbar, parts.error, parts.view);
  root.ownerDocument = doc;
  root.querySelector = (selector) => parts[selector.match(/^\[data-lib-([\w-]+)\]$/)?.[1]] ?? null;
  const pane = createLibraryPane(root, { applyFill, storage });
  await pane.refresh();
  return { doc, parts, pane, root, calls, storage };
}
const rows = (parts) => findAll(parts.view, (n) => "libKey" in (n.dataset ?? {}));
const items = (parts) => findAll(parts.view, (n) => "libItem" in (n.dataset ?? {}));
const viewBtn = (parts, key) => find(parts.toolbar, (n) => n.dataset?.libViewBtn === key);
const filterBtn = (parts, label) => find(byData(parts.toolbar, "libFilter"), (n) => n.tagName === "button" && n.textContent === label);
const btn = (node, text) => find(node, (n) => n.tagName === "button" && n.textContent === text);
const dialog = (doc) => find(doc.body, (n) => n.attrs?.role === "dialog");

const OUTPUTS = [
  { name: "cat 1.png", kind: "image", bytes: 2048, ts: "2026-09-25T10:03:00Z" },
  { name: "h3-1.mp4", kind: "video", bytes: 4096, ts: "2026-09-25T10:02:00Z" },
  { name: "music3-1.wav", kind: "music", bytes: 1024, ts: "2026-09-25T10:01:00Z" },
];
const HISTORY = [
  { kind: "image", status: "done", ts: "2026-09-25T10:03:00Z", output: "cat 1.png", session_id: "s1", attempt_id: "a1",
    params: { prompt: "橘猫", width: 1024, height: 768, steps: 40, seed: 0 } },
  { kind: "video", status: "done", ts: "2026-09-25T10:02:00Z", output: "h3-1.mp4", duration_s: 80,
    params: { prompt: "海边", width: 768, height: 448, frames: 48, steps: 16 } },
  { kind: "music", status: "done", ts: "2026-09-25T10:01:00Z", output: "music3-1.wav", audio_seconds: 29.71,
    params: { caption: "民谣", lyrics: "啦", duration: 300 } },
  { kind: "video", status: "failed", ts: "2026-09-24T10:00:00Z", output: null, error: "exit_nonzero: exit 1",
    params: { prompt: "镜头缓慢推近", frames: 48 } },
];

test("默认缩略图视图：新的在前，工具栏有筛选、三个视图按钮、大小滑块、刷新", async () => {
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  assert.equal(parts.view.dataset.libMode, "grid");
  assert.deepEqual(rows(parts).map((r) => r.dataset.libKey),
    ["o:cat 1.png", "o:h3-1.mp4", "o:music3-1.wav", "h:2026-09-24T10:00:00Z:video:"]);
  assert.equal(viewBtn(parts, "grid").attrs["aria-pressed"], "true");
  assert.equal(viewBtn(parts, "list").attrs["aria-pressed"], "false");
  assert.equal(viewBtn(parts, "table").attrs["aria-label"], "明细");
  assert.equal(byData(parts.toolbar, "libThumb").hidden, false);
  assert.ok(byData(parts.toolbar, "libRefresh"));
  assert.deepEqual(findAll(byData(parts.toolbar, "libFilter"), (n) => n.tagName === "button").map((b) => b.textContent),
    ["全部", "图片", "视频", "音乐"]);
});

test("缩略图：图片地址编码；无 IntersectionObserver 时视频直接设首帧地址；时长角标；失败与文件已不在是灰卡", async () => {
  const history = [...HISTORY, { kind: "video", status: "done", ts: "2026-09-20T00:00:00Z", output: "gone.mp4", params: { prompt: "删了" } }];
  const { parts } = await mount({ outputs: OUTPUTS, history });
  const [image, video, music, failed, gone] = rows(parts);
  assert.equal(find(image, (n) => n.tagName === "img").src, "/api/outputs/cat%201.png");
  assert.equal(find(image, (n) => n.tagName === "img").loading, "lazy");
  const v = find(video, (n) => n.tagName === "video");
  assert.equal(v.src, "/api/outputs/h3-1.mp4#t=0.1");
  assert.equal(v.muted, true);
  assert.equal(v.preload, "metadata");
  assert.equal(find(video, (n) => n.className === "lib-badge").textContent, "0:02");
  assert.equal(find(music, (n) => n.className === "lib-badge").textContent, "0:30");
  assert.match(find(failed, (n) => /lib-thumb/.test(n.className)).className, /is-empty/);
  assert.equal(find(gone, (n) => n.className === "lib-thumb-note").textContent, "文件已不在");
});

test("懒加载：有 IntersectionObserver 时视频进视口才设地址（Review Focus 1）", async (t) => {
  class FakeObserver {
    constructor(callback) { this.callback = callback; this.targets = []; FakeObserver.last = this; }
    observe(target) { this.targets.push(target); }
    unobserve(target) { this.targets = this.targets.filter((x) => x !== target); }
    fire() { this.callback(this.targets.map((target) => ({ target, isIntersecting: true }))); }
  }
  globalThis.IntersectionObserver = FakeObserver;
  t.after(() => { delete globalThis.IntersectionObserver; });
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const v = find(parts.view, (n) => n.tagName === "video");
  assert.equal(v.src, undefined);
  FakeObserver.last.fire();
  assert.equal(v.src, "/api/outputs/h3-1.mp4#t=0.1");
  assert.deepEqual(FakeObserver.last.targets, []);
});

test("图片加载失败退回类型图标，不影响其他卡片", async () => {
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const [image, video] = rows(parts);
  const img = find(image, (n) => n.tagName === "img");
  await img.dispatch("error");
  assert.equal(find(image, (n) => n.tagName === "img"), null);
  assert.match(find(image, (n) => /lib-thumb/.test(n.className)).className, /is-broken/);
  assert.ok(find(video, (n) => n.tagName === "video"));
});

test("视图切换写进本机存储，下次打开沿用；存储坏了或抛错照常显示默认视图", async () => {
  const { parts, storage } = await mount({ outputs: OUTPUTS, history: HISTORY });
  await viewBtn(parts, "table").click();
  assert.equal(parts.view.dataset.libMode, "table");
  assert.equal(JSON.parse(storage.data[PREFS_KEY]).view, "table");
  assert.equal(byData(parts.toolbar, "libThumb").hidden, true);
  const again = await mount({ outputs: OUTPUTS, history: HISTORY, storage });
  assert.equal(again.parts.view.dataset.libMode, "table");
  const broken = await mount({ outputs: OUTPUTS, history: HISTORY, storage: memoryStorage({ [PREFS_KEY]: "{oops" }) });
  assert.equal(broken.parts.view.dataset.libMode, "grid");
  const throwing = { getItem() { throw new Error("denied"); }, setItem() { throw new Error("denied"); } };
  const locked = await mount({ outputs: OUTPUTS, history: HISTORY, storage: throwing });
  assert.equal(locked.parts.view.dataset.libMode, "grid");
  await viewBtn(locked.parts, "list").click();
  assert.equal(locked.parts.view.dataset.libMode, "list");
});

test("筛选：只看视频；某类没有时写明当前筛选；整个库为空时是引导语", async () => {
  const { parts } = await mount({ outputs: OUTPUTS.slice(0, 2), history: HISTORY.slice(0, 2) });
  await filterBtn(parts, "视频").click();
  assert.deepEqual(rows(parts).map((r) => r.dataset.libKey), ["o:h3-1.mp4"]);
  await filterBtn(parts, "音乐").click();
  assert.equal(byData(parts.view, "libEmpty").textContent, "没有这类成品。当前筛选：音乐");
  const empty = await mount();
  assert.equal(byData(empty.parts.view, "libEmpty").textContent,
    "还没有成品。去「图片」「视频」或「音乐」面板生成第一件，它会出现在这里。");
});

test("列表视图：元信息、失败错误块（F3）、在访达中显示（含 issue #12 失败文案）、回填参数", async () => {
  const fills = [];
  const reveal = { ok: false, status: 404,
    json: async () => ({ error: { code: "outputs_root_missing", message: "成品目录还不存在，生成第一个作品后会自动创建" } }) };
  const storage = memoryStorage({ [PREFS_KEY]: JSON.stringify({ view: "list" }) });
  const { parts, calls } = await mount({ outputs: OUTPUTS, history: HISTORY, storage, applyFill: (p) => fills.push(p), reveal });
  const [image, , music, failed] = rows(parts);
  assert.match(find(image, (n) => n.className === "lib-meta").textContent, /图片 · 完成 · 2026-09-25 10:03 · 1024×768 · 40步 · 种子 0/);
  assert.ok(find(music, (n) => n.className === "lib-meta").textContent.includes("成品 30 秒（请求 300 秒）"));
  const block = find(failed, (n) => n.className === "inline-error job-error");
  assert.equal(find(block, (n) => n.tagName === "strong").textContent, "生成程序异常退出");
  assert.equal(find(find(block, (n) => n.tagName === "details"), (n) => n.tagName === "pre").textContent, "exit_nonzero: exit 1");
  await btn(image, "在访达中显示").click();
  await flush();
  assert.ok(calls.some(([url, method]) => url === "/api/outputs/cat%201.png/reveal" && method === "POST"));
  assert.equal(parts.error.textContent, "成品目录还不存在，生成第一个作品后会自动创建");
  await btn(image, "回填参数").click();
  assert.deepEqual(fills, [{ pane: "image", session_id: "s1", attempt_id: "a1",
    fields: { prompt: "橘猫", width: 1024, height: 768, steps: 40, seed: 0 } }]);
  assert.equal(btn(failed, "在访达中显示"), null);
});

test("明细视图：表头点一下按该列排序、再点反向，aria-sort 标当前列，缺值显示「—」", async () => {
  const storage = memoryStorage({ [PREFS_KEY]: JSON.stringify({ view: "table" }) });
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY, storage });
  const header = (key) => find(parts.view, (n) => n.dataset?.libSort === key);
  assert.equal(header("ts").parentNode.attrs["aria-sort"], "descending");
  await header("bytes").click();
  assert.deepEqual(rows(parts).map((r) => r.dataset.libKey),
    ["o:h3-1.mp4", "o:cat 1.png", "o:music3-1.wav", "h:2026-09-24T10:00:00Z:video:"]);
  assert.equal(header("bytes").parentNode.attrs["aria-sort"], "descending");
  await header("bytes").click();
  assert.equal(header("bytes").parentNode.attrs["aria-sort"], "ascending");
  assert.deepEqual(rows(parts).map((r) => r.dataset.libKey).slice(0, 3), ["o:music3-1.wav", "o:cat 1.png", "o:h3-1.mp4"]);
  assert.equal(JSON.parse(storage.data[PREFS_KEY]).sort.dir, "asc");
  const imageRow = rows(parts).find((r) => r.dataset.libKey === "o:cat 1.png");
  assert.deepEqual(imageRow.children.slice(2).map((td) => td.textContent),
    ["图片", "2026-09-25 10:03", "—", "1024×768", "2 KiB", "—"]);
});

test("选中与键盘：单击选中（aria-current、roving tabIndex）；方向键移动；到头停住", async () => {
  const storage = memoryStorage({ [PREFS_KEY]: JSON.stringify({ view: "list" }) });
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY, storage });
  const mains = items(parts);
  assert.deepEqual(mains.map((m) => m.tabIndex), [0, -1, -1, -1], "没有选中时第一项可 Tab 到");
  await mains[1].click();
  assert.equal(mains[1].attrs["aria-current"], "true");
  assert.match(rows(parts)[1].className, /is-selected/);
  assert.deepEqual(mains.map((m) => m.tabIndex), [-1, 0, -1, -1]);
  await mains[1].dispatch("keydown", { key: "ArrowDown" });
  assert.equal(mains[2].attrs["aria-current"], "true");
  assert.equal(mains[1].attrs["aria-current"], undefined);
  assert.ok(mains[2].focused > 0);
  await mains[2].dispatch("keydown", { key: "ArrowDown" });
  await mains[3].dispatch("keydown", { key: "ArrowDown" });
  assert.equal(mains[3].attrs["aria-current"], "true", "最后一项再往下停住");
  await viewBtn(parts, "grid").click();
  const grid = items(parts);
  assert.equal(grid[3].attrs["aria-current"], "true", "切视图保留选中");
  await grid[3].dispatch("keydown", { key: "ArrowLeft" });
  assert.equal(grid[2].attrs["aria-current"], "true");
  await grid[2].dispatch("keydown", { key: "ArrowUp" });
  assert.equal(grid[1].attrs["aria-current"], "true", "量不到列数时 ↑ 退化为前一个");
});

test("Enter/双击打开预览；同一次按键不会把刚开的预览关掉；关闭后选中与焦点回到最后看的那件", async () => {
  const { doc, parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const mains = items(parts);
  let stopped = 0;
  await mains[0].dispatch("keydown", { key: " ", stopPropagation() { stopped += 1; } });
  assert.ok(dialog(doc), "空格打开");
  assert.equal(stopped, 1, "打开预览的这次按键不再往外冒泡");
  doc.key("ArrowRight");
  doc.key("Escape");
  assert.equal(dialog(doc), null);
  const after = items(parts);
  assert.equal(after[1].attrs["aria-current"], "true");
  assert.ok(after[1].focused > 0);
  await after[2].dispatch("dblclick");
  assert.equal(dialog(doc).attrs["aria-label"], "民谣");
});

test("在筛选后的视图里预览只在该筛选与排序里翻页（Review Focus 3）", async () => {
  const { doc, parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  await filterBtn(parts, "视频").click();
  await items(parts)[0].dispatch("keydown", { key: "Enter" });
  assert.equal(dialog(doc).attrs["aria-label"], "海边");
  doc.key("ArrowRight");
  assert.equal(dialog(doc).attrs["aria-label"], "镜头缓慢推近");
  assert.equal(byData(doc.body, "libNext").disabled, true);
});

test("试听：点按钮播放并显示暂停，再点停；不触发选中；动作按钮上按 Enter 不开预览（Review Focus 5）", async () => {
  const { doc, parts, root } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const player = byData(root, "libAudition");
  let paused = 0; player.pause = () => { paused += 1; };
  const button = byData(parts.view, "libAuditionBtn");
  await button.click();
  assert.equal(player.src, "/api/outputs/music3-1.wav");
  assert.equal(button.attrs["aria-pressed"], "true");
  assert.equal(button.attrs["aria-label"], "暂停试听");
  assert.equal(items(parts).some((m) => m.attrs["aria-current"] === "true"), false);
  await button.dispatch("keydown", { key: "Enter" });
  assert.equal(dialog(doc), null);
  await button.click();
  assert.equal(paused, 1);
  assert.equal(button.attrs["aria-pressed"], "false");
  assert.equal(button.attrs["aria-label"], "试听");
});

test("试听中刷新、切筛选、离开页面、打开预览都会停声（Review Focus 4）", async () => {
  const { doc, parts, pane, root } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const player = byData(root, "libAudition");
  let paused = 0; player.pause = () => { paused += 1; };
  const start = async () => byData(parts.view, "libAuditionBtn").click();
  await start(); await pane.refresh(); assert.equal(paused, 1);
  await start(); await filterBtn(parts, "音乐").click(); assert.equal(paused, 2);
  await start(); pane.onHide(); assert.equal(paused, 3);
  assert.equal(byData(parts.view, "libAuditionBtn").attrs["aria-pressed"], "false");
  await start(); await items(parts)[0].dispatch("dblclick"); assert.equal(paused, 4);
  assert.ok(dialog(doc));
});

test("刷新后原选中项还在就保持，不在了就清空", async () => {
  const { parts, pane } = await mount({ outputs: OUTPUTS, history: HISTORY });
  await items(parts)[1].click();
  await pane.refresh();
  assert.equal(items(parts)[1].attrs["aria-current"], "true");
  serve(OUTPUTS.slice(0, 1), HISTORY.slice(0, 1));
  await pane.refresh();
  assert.equal(items(parts).some((m) => m.attrs["aria-current"] === "true"), false);
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `node --test tests/js/library_pane.test.js`
Expected: FAIL — `PREFS_KEY` 未导出 / 断言失败

- [ ] **Step 4: Write the implementation**（整个文件替换）

```js
// desk/static/js/panes/library.js
// ui:libraryPane —— 素材库（素材库预览设计 L-10–L-45）：类访达的缩略图 / 列表 / 明细三视图 + 类型筛选 + 预览弹层。
// 条目模型在 pure/library_view.js，弹层在 widgets/library_preview.js；「回填」经 main 切 tab 写表单（R-ui-06）。
import * as api from "../api.js";
import { buildItems, clockText, hasMedia, normalizePrefs, THUMB_MAX, THUMB_MIN, visibleItems } from "../pure/library_view.js";
import { formatBytes, formatDuration, formatTimestamp } from "../pure/format.js";
import { addIcon, setIcon } from "../icons.js";
import { renderErrorBlock } from "../widgets/error_block.js";
import { renderSegmentSwitch } from "../widgets/segment_switch.js";
import { openLibraryPreview } from "../widgets/library_preview.js";

export const PREFS_KEY = "lmd.library";
const KIND_LABEL = { video: "视频", music: "音乐", image: "图片", file: "文件" };
const STATUS_LABEL = { done: "完成", failed: "失败", cancelled: "已取消" };
const KIND_ICON = { image: "image", video: "video", music: "music", file: "file" };
const FILTERS = [["all", "全部"], ["image", "图片"], ["video", "视频"], ["music", "音乐"]];
const VIEWS = [["grid", "缩略图", "grid"], ["list", "列表", "list"], ["table", "明细", "table"]];
const COLUMNS = [[null, "缩略"], ["title", "提示词"], ["kind", "类型"], ["ts", "生成时间"], ["duration", "时长"],
  ["dims", "画幅"], ["bytes", "大小"], ["gen", "耗时"]];
const ASCENDING_FIRST = new Set(["title", "kind"]);
const EMPTY_ALL = "还没有成品。去「图片」「视频」或「音乐」面板生成第一件，它会出现在这里。";

export function createLibraryPane(root, ctx) { // ctx.applyFill(plan)；ctx.storage 可注入（测试）
  const doc = root.ownerDocument;
  const storage = "storage" in ctx ? ctx.storage : globalThis.localStorage;
  const q = (name) => root.querySelector(`[data-lib-${name}]`);
  const els = { toolbar: q("toolbar"), error: q("error"), view: q("view") };
  const el = (tag, className = "") => {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    return node;
  };
  const text = (tag, className, value) => {
    const node = el(tag, className);
    node.textContent = value;
    return node;
  };

  let prefs = readPrefs();
  let items = [];
  let shown = [];
  let rows = []; // 当前视图里的 [{item, main, row}]，顺序同 shown
  let selectedKey = null;
  let preview = null;
  let hovering = null;
  let audition = { key: null, button: null };

  // L-24：整页只有一个试听播放器。
  const player = el("audio");
  player.hidden = true;
  player.dataset.libAudition = "";
  player.addEventListener("ended", () => stopAudition());
  root.append(player);

  // L-22：视频缩略图进视口才设地址；环境没有 IntersectionObserver 时直接设。
  const observer = typeof globalThis.IntersectionObserver === "function"
    ? new globalThis.IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        loadVideo(entry.target);
        observer.unobserve(entry.target);
      }
    }, { rootMargin: "200px" })
    : null;

  function readPrefs() {
    try { return normalizePrefs(JSON.parse(storage?.getItem(PREFS_KEY) ?? "null")); } catch { return normalizePrefs(null); }
  }
  function writePrefs() {
    try { storage?.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch { /* 本机存储不可用：只是记不住，不影响使用 */ }
  }

  const toolbar = buildToolbar();
  syncToolbar();
  applyThumb();

  function buildToolbar() {
    const filter = renderSegmentSwitch(doc, {
      labels: FILTERS.map(([, label]) => label),
      checked: FILTERS.findIndex(([key]) => key === prefs.filter),
      ariaLabel: "类型",
      onChange: (index) => setPrefs({ filter: FILTERS[index][0] }),
    });
    filter.dataset.libFilter = "";
    const views = el("div", "lib-views");
    views.setAttribute("role", "group");
    views.setAttribute("aria-label", "视图");
    const viewButtons = VIEWS.map(([key, label, icon]) => {
      const b = el("button", "btn-quiet lib-view-btn");
      b.dataset.libViewBtn = key;
      b.setAttribute("aria-label", label);
      b.title = label;
      addIcon(b, icon, doc);
      b.addEventListener("click", () => setPrefs({ view: key }));
      return b;
    });
    views.append(...viewButtons);
    const size = el("input", "lib-thumb-size");
    size.type = "range";
    size.min = String(THUMB_MIN);
    size.max = String(THUMB_MAX);
    size.step = "20";
    size.value = String(prefs.thumb);
    size.dataset.libThumb = "";
    size.setAttribute("aria-label", "缩略图大小");
    size.addEventListener("input", () => setPrefs({ thumb: Number(size.value) }, { rerender: false }));
    const refresh = el("button");
    refresh.dataset.libRefresh = "";
    refresh.textContent = "刷新";
    addIcon(refresh, "refresh", doc);
    refresh.addEventListener("click", () => refreshPane());
    els.toolbar.replaceChildren(filter, el("span", "lib-toolbar-spacer"), size, views, refresh);
    return { viewButtons, size };
  }

  function syncToolbar() {
    for (const b of toolbar.viewButtons) b.setAttribute("aria-pressed", b.dataset.libViewBtn === prefs.view ? "true" : "false");
    toolbar.size.hidden = prefs.view !== "grid";
  }
  function applyThumb() {
    els.view.style?.setProperty?.("--lib-thumb", `${prefs.thumb}px`);
  }
  function setPrefs(patch, { rerender = true } = {}) {
    prefs = normalizePrefs({ ...prefs, ...patch });
    writePrefs();
    syncToolbar();
    applyThumb();
    if (rerender) render();
  }

  async function refreshPane() {
    els.error.textContent = "";
    stopAudition();
    try {
      const [outputs, history] = await Promise.all([api.listOutputs(), api.listHistory()]);
      items = buildItems(outputs, history);
      render();
    } catch (err) {
      els.error.textContent = err.message;
    }
  }

  function render() {
    stopAudition();
    stopHover();
    shown = visibleItems(items, prefs);
    if (selectedKey && !shown.some((item) => item.key === selectedKey)) selectedKey = null;
    els.view.dataset.libMode = prefs.view;
    rows = [];
    if (!shown.length) {
      els.view.replaceChildren(emptyNode());
      return;
    }
    els.view.replaceChildren(prefs.view === "table" ? renderTable() : prefs.view === "list" ? renderList() : renderGrid());
    syncSelection();
  }

  function emptyNode() {
    const label = FILTERS.find(([key]) => key === prefs.filter)?.[1] ?? "全部";
    const node = text("p", "empty", items.length ? `没有这类成品。当前筛选：${label}` : EMPTY_ALL);
    node.dataset.libEmpty = "";
    return node;
  }

  function tagRow(row, item) {
    row.dataset.libKey = item.key;
    if (hasMedia(item)) row.dataset.outputName = item.output;
  }

  // L-30：条目主体是一个按钮；动作按钮是它的兄弟节点。
  function mainButton(item) {
    const b = el("button", "lib-item");
    b.dataset.libItem = "";
    b.setAttribute("aria-label", item.title);
    b.tabIndex = -1;
    b.addEventListener("click", () => select(item.key));
    b.addEventListener("dblclick", () => open(item.key));
    b.addEventListener("keydown", (event) => onItemKey(event, item.key));
    return b;
  }

  function renderGrid() {
    const list = el("ul", "lib-grid");
    list.dataset.libList = "";
    for (const item of shown) {
      const li = el("li", "lib-card");
      tagRow(li, item);
      const main = mainButton(item);
      // <button> 里只能放短语内容：标题、时间、缩略图都用 span（CSS 里设成块）。
      main.append(thumbNode(item, { hover: true }), text("span", "lib-title", item.title), text("span", "lib-meta", formatTimestamp(item.ts)));
      li.append(main);
      if (item.kind === "music" && hasMedia(item)) li.append(auditionButton(item));
      list.append(li);
      rows.push({ item, main, row: li });
    }
    return list;
  }

  function metaLine(item) {
    if (!item.entry) return `无历史记录 · ${formatBytes(item.bytes)} · ${formatTimestamp(item.ts)}`;
    return [
      KIND_LABEL[item.kind] ?? item.kind,
      STATUS_LABEL[item.status] ?? item.status,
      formatTimestamp(item.ts),
      item.gen_s != null ? `耗时 ${formatDuration(item.gen_s)}` : null,
      item.spec,
    ].filter(Boolean).join(" · ");
  }

  function renderList() {
    const list = el("ul", "lib-rows");
    list.dataset.libList = "";
    for (const item of shown) {
      const li = el("li", "lib-row");
      tagRow(li, item);
      const main = mainButton(item);
      const body = el("span", "lib-row-text");
      body.append(text("span", "lib-title", item.title), text("span", "lib-meta", metaLine(item)));
      main.append(thumbNode(item, { hover: false }), body);
      li.append(main, actionsNode(item));
      if (item.error) {
        const [code, ...rest] = item.error.split(": ");
        li.append(renderErrorBlock(doc, { code, message: rest.join(": ") }));
      }
      list.append(li);
      rows.push({ item, main, row: li });
    }
    return list;
  }

  function actionsNode(item) {
    const actions = el("div", "lib-actions");
    const action = (label, icon, run) => {
      const b = el("button");
      b.textContent = label;
      addIcon(b, icon, doc);
      b.addEventListener("click", (event) => { event.stopPropagation?.(); run(); });
      actions.append(b);
    };
    action("预览", item.kind === "image" ? "image" : "play", () => open(item.key));
    if (hasMedia(item)) {
      action("在访达中显示", "folder", async () => {
        try { await api.revealOutput(item.output); } catch (error) { els.error.textContent = error.message; }
      });
    }
    if (item.plan) action("回填参数", "sliders", () => ctx.applyFill(item.plan));
    return actions;
  }

  function renderTable() {
    const table = el("table", "lib-table");
    const head = el("thead");
    const headRow = el("tr");
    for (const [key, label] of COLUMNS) {
      const th = el("th");
      th.setAttribute("scope", "col");
      if (!key) {
        th.className = "lib-col-thumb";
        th.textContent = label;
      } else {
        const b = text("button", "lib-sort", label);
        b.dataset.libSort = key;
        if (prefs.sort.key === key) {
          th.setAttribute("aria-sort", prefs.sort.dir === "asc" ? "ascending" : "descending");
          addIcon(b, prefs.sort.dir === "asc" ? "chevron-up" : "chevron-down", doc);
        }
        b.addEventListener("click", () => {
          const dir = prefs.sort.key === key
            ? (prefs.sort.dir === "desc" ? "asc" : "desc")
            : (ASCENDING_FIRST.has(key) ? "asc" : "desc");
          setPrefs({ sort: { key, dir } });
        });
        th.append(b);
      }
      headRow.append(th);
    }
    head.append(headRow);
    const body = el("tbody");
    body.dataset.libList = "";
    for (const item of shown) {
      const tr = el("tr");
      tagRow(tr, item);
      const main = mainButton(item);
      main.append(text("span", "lib-title", item.title));
      const cells = [
        thumbNode(item, { hover: false }), main, KIND_LABEL[item.kind] ?? item.kind, formatTimestamp(item.ts),
        item.duration_s != null ? clockText(item.duration_s) : "—",
        item.width && item.height ? `${item.width}×${item.height}` : "—",
        item.bytes != null ? formatBytes(item.bytes) : "—",
        item.gen_s != null ? formatDuration(item.gen_s) : "—",
      ];
      for (const cell of cells) {
        const td = el("td");
        if (typeof cell === "string") td.textContent = cell; else td.append(cell);
        tr.append(td);
      }
      body.append(tr);
      rows.push({ item, main, row: tr });
    }
    table.append(head, body);
    return table;
  }

  // L-21–L-26：缩略图。
  function thumbNode(item, { hover }) {
    const box = el("span", "lib-thumb");
    box.dataset.kind = item.kind;
    if (!hasMedia(item)) {
      box.classList.add("is-empty");
      addIcon(box, item.status === "done" && !item.missing ? KIND_ICON[item.kind] ?? "file" : "alert", doc);
      box.append(text("span", "lib-thumb-note", item.missing ? "文件已不在" : STATUS_LABEL[item.status] ?? item.status));
      return box;
    }
    const src = api.serveOutput(item.output);
    const fallback = (node) => () => {
      node.remove();
      box.classList.add("is-broken");
      addIcon(box, KIND_ICON[item.kind] ?? "file", doc);
    };
    if (item.kind === "image") {
      const img = el("img");
      img.loading = "lazy";
      img.alt = "";
      img.src = src;
      img.addEventListener("error", fallback(img));
      box.append(img);
    } else if (item.kind === "video") {
      const video = el("video");
      video.muted = true;
      video.playsInline = true;
      video.setAttribute("playsinline", "");
      video.preload = "metadata";
      video.dataset.src = `${src}#t=0.1`;
      video.addEventListener("error", fallback(video));
      box.append(video);
      if (observer) observer.observe(video); else loadVideo(video);
      if (hover) {
        box.addEventListener("mouseenter", () => startHover(video));
        box.addEventListener("mouseleave", () => stopHover());
      }
    } else {
      addIcon(box, KIND_ICON[item.kind] ?? "file", doc);
    }
    if (item.duration_s != null) box.append(text("span", "lib-badge", clockText(item.duration_s)));
    return box;
  }
  function loadVideo(video) {
    if (!video.dataset.src) return;
    video.src = video.dataset.src;
    delete video.dataset.src;
  }
  function startHover(video) {
    stopHover();
    loadVideo(video);
    hovering = video;
    video.play?.()?.catch?.(() => {});
  }
  function stopHover() {
    if (!hovering) return;
    const video = hovering;
    hovering = null;
    video.pause?.();
    try { video.currentTime = 0.1; } catch { /* 元数据还没到 */ }
  }

  // L-24：试听。
  function auditionButton(item) {
    const b = el("button", "btn-quiet lib-audition");
    b.dataset.libAuditionBtn = "";
    b.setAttribute("aria-pressed", "false");
    b.setAttribute("aria-label", "试听");
    b.title = "试听";
    addIcon(b, "play", doc);
    b.addEventListener("click", (event) => { event.stopPropagation?.(); toggleAudition(item, b); });
    return b;
  }
  function toggleAudition(item, button) {
    if (audition.key === item.key) { stopAudition(); return; }
    stopAudition();
    player.src = api.serveOutput(item.output);
    player.play?.()?.catch?.(() => {});
    audition = { key: item.key, button };
    button.setAttribute("aria-pressed", "true");
    button.setAttribute("aria-label", "暂停试听");
    button.title = "暂停试听";
    setIcon(button, "pause", doc);
  }
  function stopAudition() {
    const { key, button } = audition;
    audition = { key: null, button: null };
    if (!key) return;
    player.pause?.();
    player.removeAttribute?.("src");
    player.load?.();
    button.setAttribute("aria-pressed", "false");
    button.setAttribute("aria-label", "试听");
    button.title = "试听";
    setIcon(button, "play", doc);
  }

  // L-30–L-32：选中、roving tabindex、键盘。
  function select(key, { focus = false } = {}) {
    selectedKey = key;
    syncSelection();
    const row = rows.find((r) => r.item.key === key);
    if (!row) return;
    row.row.scrollIntoView?.({ block: "nearest" });
    if (focus) row.main.focus?.();
  }
  function syncSelection() {
    const anchor = rows.find((r) => r.item.key === selectedKey) ?? rows[0];
    for (const r of rows) {
      const on = r.item.key === selectedKey;
      r.row.classList.toggle("is-selected", on);
      if (on) r.main.setAttribute("aria-current", "true"); else r.main.removeAttribute("aria-current");
      r.main.tabIndex = r === anchor ? 0 : -1;
    }
  }
  function columns() {
    const top = (r) => r.row.getBoundingClientRect?.().top;
    const first = rows.length ? top(rows[0]) : undefined;
    if (!Number.isFinite(first)) return 1;
    let count = 0;
    for (const r of rows) {
      if (Math.abs(top(r) - first) < 1) count += 1; else break;
    }
    return Math.max(1, count);
  }
  function stepFor(key) {
    const grid = prefs.view === "grid";
    if (key === "ArrowDown") return grid ? columns() : 1;
    if (key === "ArrowUp") return grid ? -columns() : -1;
    if (grid && key === "ArrowRight") return 1;
    if (grid && key === "ArrowLeft") return -1;
    return 0;
  }
  function onItemKey(event, key) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault?.();
      event.stopPropagation?.(); // 打开预览的这次按键不能再传到弹层的 keydown 上把它关掉
      open(key);
      return;
    }
    const step = stepFor(event.key);
    if (!step) return;
    event.preventDefault?.();
    const from = rows.findIndex((r) => r.item.key === key);
    const to = from + step;
    if (from < 0 || to < 0 || to >= rows.length) return;
    select(rows[to].item.key, { focus: true });
  }

  // L-40–L-43：预览弹层，按打开时的筛选 + 排序快照翻页。
  function open(key) {
    const snapshot = shown;
    const index = snapshot.findIndex((item) => item.key === key);
    if (index < 0 || preview) return;
    stopAudition();
    stopHover();
    select(key);
    preview = openLibraryPreview(doc, {
      items: snapshot,
      index,
      serveOutput: api.serveOutput,
      onFill: (plan) => ctx.applyFill(plan),
      onReveal: (name) => api.revealOutput(name),
      onClose: (at) => {
        preview = null;
        const item = snapshot[at];
        if (item) select(item.key, { focus: true });
      },
    });
  }

  // L-45：离开素材库页。
  function onHide() {
    stopAudition();
    stopHover();
  }

  return { refresh: refreshPane, onHide };
}
```

- [ ] **Step 5: Run the pane tests, then the whole JS suite**

Run: `node --test tests/js/library_pane.test.js`
Expected: PASS（14 tests）

Run: `node --test tests/js/`
Expected: 全部 PASS（`main.js` 没有单测；其余文件不受影响）

- [ ] **Step 6: Commit**

```bash
git add desk/static/js/panes/library.js desk/static/index.html desk/static/js/main.js desk/static/js/widgets/segment_switch.js tests/js/library_pane.test.js
git commit -m "feat(library): 素材库三视图、筛选、选中与键盘、试听、切页停声（L-10–L-45）"
```

---

### Task 4: 样式 `app.css`

**Files:**
- Modify: `desk/static/app.css`（第 43、102、117–121 行附近的旧素材库规则；文件末尾加第 16 节）

**Interfaces:**
- Consumes: Task 2/3 的类名：`lib-toolbar lib-toolbar-spacer lib-views lib-view-btn lib-thumb-size lib-view lib-item lib-thumb lib-thumb-note lib-badge is-empty is-broken lib-grid lib-card lib-title lib-meta lib-audition lib-rows lib-row lib-row-text lib-actions lib-table lib-col-thumb lib-sort is-selected lib-preview-overlay lib-preview lib-preview-nav lib-preview-stage lib-preview-note lib-preview-music lib-preview-art lib-preview-info lib-preview-title lib-preview-actions`；CSS 变量 `--lib-thumb`；令牌 `--bg --panel --border --muted --accent --radius --radius-card`。
- Produces: 无（纯样式）。

- [ ] **Step 1: Remove the old library rules**

在 `desk/static/app.css` 中：
1. 第 43 行：把 `.sessions ul,[data-res-list],[data-lib-list] { list-style:none; padding:0; }` 改成 `.sessions ul,[data-res-list] { list-style:none; padding:0; }`，并删掉同一行末尾的 ` [data-lib-player] video { max-width:100%; }`。
2. 第 102 行：选择器 `.sessions ul,[data-res-list],[data-lib-list]` 改成 `.sessions ul,[data-res-list]`。
3. 第 117–119 行：三处选择器里的 `,.lib-row`、`,.lib-row>*`、`,.lib-row>.lib-actions` 去掉（只留 `.res-row…`）。
4. 第 120 行：`[data-res-list],[data-lib-list]{margin-top:16px}` 改成 `[data-res-list]{margin-top:16px}`。
5. 删掉第 121 行 `[data-lib-player]:not(:empty){margin-top:16px}`。

改完运行 `grep -n "lib-player\|data-lib-list\|\.lib-row" desk/static/app.css`，期望无输出。

- [ ] **Step 2: Append section 16**

文件末尾追加：

```css

/* 16. 素材库（素材库预览设计 L-10–L-44）：工具栏 + 缩略图 / 列表 / 明细三视图 + 预览弹层 */
#pane-library{display:flex;flex-direction:column;gap:12px}
.lib-toolbar{display:flex;align-items:center;gap:12px;flex-wrap:wrap;position:sticky;top:0;z-index:2;background:var(--bg);padding:4px 0}
.lib-toolbar-spacer{flex:1}
.lib-views{display:inline-flex;gap:2px;padding:2px;border:1px solid var(--border);border-radius:var(--radius)}
.lib-view-btn{width:32px;height:28px;padding:0;display:inline-grid;place-items:center}
.lib-view-btn[aria-pressed=true]{background:var(--panel);color:var(--accent)}
.lib-thumb-size{width:120px;accent-color:var(--accent)}
.lib-thumb-size[hidden]{display:none}
.lib-view{min-width:0}
.lib-view[data-lib-mode=table]{overflow-x:auto}
.lib-item{all:unset;box-sizing:border-box;display:block;width:100%;border-radius:var(--radius);cursor:default}
.lib-item:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.lib-thumb{position:relative;overflow:hidden;border-radius:var(--radius);background:var(--panel);display:grid;place-items:center;color:var(--muted)}
.lib-thumb>img,.lib-thumb>video{width:100%;height:100%;object-fit:cover;display:block}
.lib-thumb>.icon{width:32%;height:32%;max-width:48px;max-height:48px}
.lib-thumb[data-kind=music]{background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 35%,var(--panel)),var(--panel))}
.lib-thumb.is-empty{background:transparent;border:1px dashed var(--border)}
.lib-thumb-note{position:absolute;left:6px;right:6px;bottom:6px;font-size:12px;text-align:center;color:var(--muted)}
.lib-badge{position:absolute;right:6px;bottom:6px;padding:1px 6px;border-radius:999px;background:#000a;color:#fff;font-size:11px;font-variant-numeric:tabular-nums}
.lib-title{margin:0;overflow-wrap:anywhere}
.lib-item .lib-title,.lib-item .lib-meta,.lib-row-text{display:block}

/* 缩略图视图 */
.lib-grid{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fill,minmax(var(--lib-thumb,200px),1fr));gap:12px}
.lib-card{position:relative}
.lib-card>.lib-item{padding:6px;transition:background 120ms ease,box-shadow 120ms ease}
.lib-card>.lib-item:hover{background:color-mix(in srgb,var(--panel) 60%,transparent)}
.lib-card.is-selected>.lib-item{background:var(--panel);box-shadow:inset 0 0 0 2px var(--accent)}
.lib-card .lib-thumb{aspect-ratio:1}
.lib-card .lib-title{margin-top:8px;font-size:13px;line-height:1.4;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.lib-card .lib-meta{margin:2px 0 0;font-size:12px}
.lib-audition{position:absolute;top:12px;right:12px;width:32px;height:32px;padding:0;border-radius:999px;display:grid;place-items:center;background:#000a;color:#fff;opacity:.85;transition:opacity 120ms ease,transform 120ms ease}
.lib-audition:hover,.lib-audition[aria-pressed=true]{opacity:1;transform:scale(1.06)}

/* 列表视图 */
.lib-rows{list-style:none;margin:0;padding:0;display:flex;flex-direction:column;gap:4px}
.lib-row{display:flex;flex-wrap:wrap;align-items:center;gap:12px;padding:6px 8px;border-radius:var(--radius);transition:background 120ms ease}
.lib-row.is-selected{background:var(--panel);box-shadow:inset 0 0 0 2px var(--accent)}
.lib-row>.lib-item{flex:1;min-width:0;display:flex;align-items:center;gap:12px}
.lib-row .lib-thumb{width:48px;height:48px;flex:none}
.lib-row-text{min-width:0}
.lib-row .lib-title{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lib-row>.lib-actions{margin-top:0}
.lib-row>.job-error{flex-basis:100%}

/* 明细视图 */
.lib-table{width:100%;border-collapse:collapse;font-size:13px}
.lib-table th{text-align:left;font-weight:500;color:var(--muted);padding:6px 8px;border-bottom:1px solid var(--border);white-space:nowrap}
.lib-sort{all:unset;cursor:pointer;display:inline-flex;align-items:center;gap:4px;border-radius:4px}
.lib-sort:hover{color:var(--text)}
.lib-sort:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.lib-sort>.icon{width:14px;height:14px}
.lib-table td{padding:4px 8px;border-bottom:1px solid color-mix(in srgb,var(--border) 50%,transparent);white-space:nowrap;font-variant-numeric:tabular-nums}
.lib-table td:nth-child(2){white-space:normal;width:100%;max-width:0}
.lib-table td:nth-child(2) .lib-title{display:block;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.lib-table tr.is-selected>td{background:var(--panel)}
.lib-table .lib-thumb{width:32px;height:32px}
.lib-table .lib-thumb>.icon{width:16px;height:16px}
.lib-table .lib-badge,.lib-table .lib-thumb-note{display:none}

/* 预览弹层 */
.lib-preview-overlay{animation:lib-fade 180ms ease both}
.dialog.lib-preview{width:100%;max-width:min(1200px,calc(100vw - 48px));max-height:calc(100vh - 48px);display:grid;grid-template-columns:auto minmax(0,1fr) auto 300px;align-items:center;gap:12px;outline:none;animation:lib-pop 180ms cubic-bezier(.2,.8,.2,1) both}
.lib-preview-nav{width:36px;height:36px;padding:0;border-radius:999px;display:grid;place-items:center}
.lib-preview-stage{display:grid;place-items:center;min-height:240px;max-height:calc(100vh - 96px);min-width:0}
.lib-preview-stage>img,.lib-preview-stage>video{max-width:100%;max-height:calc(100vh - 96px);object-fit:contain;border-radius:var(--radius)}
.lib-preview-note{color:var(--muted)}
.lib-preview-music{display:grid;gap:16px;justify-items:center;width:100%}
.lib-preview-art{width:200px;height:200px;border-radius:var(--radius-card);display:grid;place-items:center;color:var(--muted);background:linear-gradient(135deg,color-mix(in srgb,var(--accent) 35%,var(--panel)),var(--panel))}
.lib-preview-art>.icon{width:72px;height:72px}
.lib-preview-music>audio{width:100%;max-width:420px}
.lib-preview-info{align-self:stretch;display:flex;flex-direction:column;gap:6px;min-width:0;overflow:auto;border-left:1px solid var(--border);padding-left:16px}
.lib-preview-title{margin:0;font-size:15px;line-height:1.5;overflow-wrap:anywhere}
.lib-preview-info>.lib-meta{margin:0}
.lib-preview-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:auto;padding-top:12px}
@keyframes lib-fade{from{opacity:0}}
@keyframes lib-pop{from{opacity:0;transform:scale(.97)}}
@media (max-width:900px){
  .dialog.lib-preview{grid-template-columns:auto minmax(0,1fr) auto;overflow:auto}
  .lib-preview-info{grid-column:1/-1;border-left:0;border-top:1px solid var(--border);padding:12px 0 0}
}
```

- [ ] **Step 3: Sanity check**

Run: `node --test tests/js/ 2>&1 | tail -3`
Expected: 全部 PASS（样式不影响单测；这一步确认没误删 JS）。目检留到 Task 5 的截图。

- [ ] **Step 4: Commit**

```bash
git add desk/static/app.css
git commit -m "style(library): 素材库三视图与预览弹层样式，去掉顶部播放区旧规则"
```

---

### Task 5: e2e——迁移旧用例、新增三视图/预览/键盘/切页停声用例、WebKit 首帧核对、截图目检

**Files:**
- Modify: `tests/e2e/test_library_panel.py`（`test_history_refill_and_playback` 最后一段）
- Modify: `tests/e2e/test_image_sessions.py:324-372`
- Modify: `tests/e2e/test_image_flow.py:463-469`
- Modify: `tests/e2e/test_outputs_range.py:13-18`
- Create: `tests/e2e/test_library_views.py`
- Create: `tests/e2e/test_library_webkit.py`

**Interfaces:**
- Consumes: Task 3 的 DOM 钩子；`launch_test_harness(tmp_path)`（`desk.testing`，有 `base_url`、`outputs_root`、`media_script`）；`fast_media_steps()`（`desk.testing.scripts`）；`TINY_PNG`（`desk.testing.seed`）。
- Produces: 截图写到 `$LMD_LIBRARY_SHOTS`（设置时）。

- [ ] **Step 1: Migrate the existing e2e**

`tests/e2e/test_library_panel.py`，`test_history_refill_and_playback` 里这段：

```python
        page.locator("#tabs [data-tab='library']").click()
        video_entry.click()
        player = library.locator("video[controls]")
```

改为（双击条目主体打开预览，播放器在弹层里）：

```python
        page.locator("#tabs [data-tab='library']").click()
        video_entry.locator("[data-lib-item]").dblclick()
        player = page.locator(".lib-preview video[controls]")
```

同一测试里 `video_entry`、`music_entry` 用 `library.locator("li")` 找条目——默认缩略图视图的条目就是 `li.lib-card`，保持不变；但缩略图视图没有「回填参数」按钮，所以在 `page.locator("#tabs [data-tab='library']").click()` 第一次出现之后、`video_entry = …` 之前插入一行切到列表视图：

```python
        library.locator("[data-lib-view-btn='list']").click()
```

`tests/e2e/test_image_sessions.py`：
- 第 324–331 行这段：

```python
        entry.get_by_role("button", name="预览").click()
        preview = library.locator("[data-lib-player] img")
        expect(preview).to_have_attribute("src", f"/api/outputs/{output}")
        page.wait_for_function("() => document.querySelector('[data-lib-player] img')?.naturalWidth > 0")
```

改为（先切列表视图才有「预览」按钮）：

```python
        library.locator("[data-lib-view-btn='list']").click()
        entry.get_by_role("button", name="预览").click()
        preview = page.locator(".lib-preview [data-lib-preview-stage] img")
        expect(preview).to_have_attribute("src", f"/api/outputs/{output}")
        page.wait_for_function("() => document.querySelector('.lib-preview img')?.naturalWidth > 0")
```

  `entry = library.locator("li").filter(has_text=…)` 这一行要移到切视图之后（列表视图重画了条目）：把 `library.locator("[data-lib-view-btn='list']").click()` 放在 `entry = …` 之前，`expect(entry).to_be_visible()` 不变。
- `_check_library` 里：
  - `page.wait_for_function("() => document.querySelector('[data-lib-player] img')?.naturalWidth > 0")` → `page.wait_for_function("() => document.querySelector('.lib-preview img')?.naturalWidth > 0")`
  - 删除 `page.locator("[data-lib-player]").scroll_into_view_if_needed()`，换成等列表缩略图加载完（否则 `blank_images` 会偶发不为 0）：

```python
        page.wait_for_function(
            "() => [...document.querySelectorAll('#pane-library .lib-thumb img')].every((i) => i.complete && i.naturalWidth > 0)")
```
  - JS 里 `preview_natural_width: pane.querySelector('[data-lib-player] img')?.naturalWidth ?? 0,` → `preview_natural_width: document.querySelector('.lib-preview img')?.naturalWidth ?? 0,`
  - JS 里 `preview_gap: …`（两行）换成：

```js
            preview_in_view: (() => { const r = document.querySelector('.lib-preview img').getBoundingClientRect();
              return r.top >= 0 && r.left >= 0 && r.bottom <= innerHeight && r.right <= innerWidth; })(),
```

  - 断言 `assert checks["preview_gap"] >= 8, …` → `assert checks["preview_in_view"], ("preview image overflows the viewport", state, name)`

`tests/e2e/test_image_flow.py` 第 463–469 行：

```python
        entry = library.locator("li").filter(has_text="要被删掉分组的图")
        expect(entry).to_be_visible()
        entry.get_by_role("button", name="预览").click()
        preview = library.locator("[data-lib-player] img")
        expect(preview).to_have_attribute("src", f"/api/outputs/{output}")
        page.wait_for_function("() => document.querySelector('[data-lib-player] img').naturalWidth > 0")
        expect(library.locator("li").filter(has_text="删除时还在生成")).to_be_visible(timeout=15_000)
```

改为：

```python
        library.locator("[data-lib-view-btn='list']").click()
        entry = library.locator("li").filter(has_text="要被删掉分组的图")
        expect(entry).to_be_visible()
        entry.get_by_role("button", name="预览").click()
        preview = page.locator(".lib-preview [data-lib-preview-stage] img")
        expect(preview).to_have_attribute("src", f"/api/outputs/{output}")
        page.wait_for_function("() => document.querySelector('.lib-preview img').naturalWidth > 0")
        page.keyboard.press("Escape")
        library.locator("[data-lib-refresh]").click()
        expect(library.locator("li").filter(has_text="删除时还在生成")).to_be_visible(timeout=15_000)
```

（原来这行靠播放区不挡住列表；现在先关弹层。若原测试依赖自动刷新才出现第二条，`[data-lib-refresh]` 点击代替原来的隐式刷新；若该条目在点击前已在，点击无害。）

`tests/e2e/test_outputs_range.py` 第 13–18 行：

```python
        page.wait_for_selector("[data-lib-list] li")

        found_name = page.evaluate(
            "() => document.querySelector('[data-lib-list] [data-output-name]')?.dataset.outputName"
        )
```

改为：

```python
        page.wait_for_selector("[data-lib-item]")

        found_name = page.evaluate(
            "() => document.querySelector('[data-lib-view] [data-output-name]')?.dataset.outputName"
        )
```

Run: `python3 -m pytest tests/e2e/test_library_panel.py tests/e2e/test_image_sessions.py tests/e2e/test_image_flow.py tests/e2e/test_outputs_range.py -q`
Expected: PASS

- [ ] **Step 2: Write the new e2e**

```python
# tests/e2e/test_library_views.py
"""素材库预览（设计 L-10–L-51）：三视图、预览弹层、键盘、切页停声；截图写到 $LMD_LIBRARY_SHOTS。"""
import os
from pathlib import Path

from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.seed import TINY_PNG


def _seed(harness, count=6):
    harness.outputs_root.mkdir(parents=True, exist_ok=True)
    for i in range(count):
        (harness.outputs_root / f"seed {i}.png").write_bytes(TINY_PNG)


def _open_library(page, harness):
    page.goto(harness.base_url + "#tab=library")
    expect(page.locator("[data-lib-item]").first).to_be_visible()
    return page.locator("#pane-library")


def _shot(page, name):
    shots = os.environ.get("LMD_LIBRARY_SHOTS")
    if shots:
        Path(shots).mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(Path(shots) / f"{name}.png"))


def _no_horizontal_scroll(page):
    return page.evaluate("() => document.scrollingElement.scrollWidth <= document.scrollingElement.clientWidth")


def test_three_views_render_and_are_remembered(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        _seed(harness)
        for width in (1280, 900):
            page.set_viewport_size({"width": width, "height": 800})
            library = _open_library(page, harness)
            for view in ("grid", "list", "table"):
                library.locator(f"[data-lib-view-btn='{view}']").click()
                expect(library.locator("[data-lib-view]")).to_have_attribute("data-lib-mode", view)
                expect(library.locator("[data-lib-item]")).to_have_count(6)
                page.wait_for_function(
                    "() => [...document.querySelectorAll('#pane-library .lib-thumb img')].every((i) => i.complete && i.naturalWidth > 0)")
                assert _no_horizontal_scroll(page), (view, width)
                _shot(page, f"{view}-{width}")
        page.reload()
        expect(page.locator("[data-lib-view]")).to_have_attribute("data-lib-mode", "table")


def test_preview_opens_pages_and_closes_with_keyboard(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        _seed(harness, 3)
        page.set_viewport_size({"width": 1280, "height": 800})
        library = _open_library(page, harness)
        first = library.locator("[data-lib-item]").first
        first.click()
        expect(first).to_have_attribute("aria-current", "true")
        page.keyboard.press("ArrowRight")
        second = library.locator("[data-lib-item]").nth(1)
        expect(second).to_have_attribute("aria-current", "true")
        expect(second).to_be_focused()
        page.keyboard.press("Enter")
        dialog = page.locator(".lib-preview[role=dialog]")
        expect(dialog).to_be_visible()
        expect(dialog.locator("[data-lib-preview-stage] img")).to_be_visible()
        _shot(page, "preview-1280")
        page.keyboard.press("ArrowRight")
        expect(dialog.locator("[data-lib-next]")).to_be_disabled()
        page.keyboard.press("Escape")
        expect(dialog).to_have_count(0)
        third = library.locator("[data-lib-item]").nth(2)
        expect(third).to_have_attribute("aria-current", "true")
        expect(third).to_be_focused()
        page.set_viewport_size({"width": 900, "height": 700})
        third.dblclick()
        expect(dialog).to_be_visible()
        _shot(page, "preview-900")
        dialog.get_by_role("button", name="关闭").click()
        expect(dialog).to_have_count(0)


def test_leaving_the_library_stops_audition(page, tmp_path):
    with launch_test_harness(tmp_path) as harness:
        harness.outputs_root.mkdir(parents=True, exist_ok=True)
        (harness.outputs_root / "music3-seed.wav").write_bytes(_silent_wav())
        library = _open_library(page, harness)
        audition = library.locator("[data-lib-audition-btn]")
        audition.click()
        expect(audition).to_have_attribute("aria-pressed", "true")
        page.locator("#tabs [data-tab='chat']").click()
        assert page.evaluate("() => !document.querySelector('[data-lib-audition]').getAttribute('src')")
        page.locator("#tabs [data-tab='library']").click()
        expect(library.locator("[data-lib-audition-btn]")).to_have_attribute("aria-pressed", "false")


def _silent_wav(seconds=1, rate=8000):
    import struct
    frames = seconds * rate
    data = b"\x00\x00" * frames
    return (b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(data)) + data)
```

```python
# tests/e2e/test_library_webkit.py
"""L-53：外壳是 WKWebView，视频首帧缩略图（#t=0.1 + preload=metadata）要在 WebKit 上确认能出画面。"""
import shutil
import subprocess

import pytest
from playwright.sync_api import expect, sync_playwright

from desk.testing import launch_test_harness


def test_video_thumbnail_shows_a_frame_in_webkit(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("没有 ffmpeg，造不出测试视频")
    clip = tmp_path / "clip.mp4"
    subprocess.run([ffmpeg, "-loglevel", "error", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=24", "-t", "1",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(clip)], check=True)
    with sync_playwright() as playwright:
        try:
            browser = playwright.webkit.launch()
        except Exception as error:  # 没装 WebKit 时不算失败，但要在报告里看得到
            pytest.skip(f"WebKit 不可用：{error}")
        try:
            with launch_test_harness(tmp_path / "harness") as harness:
                harness.outputs_root.mkdir(parents=True, exist_ok=True)
                (harness.outputs_root / "h3-webkit.mp4").write_bytes(clip.read_bytes())
                page = browser.new_page(viewport={"width": 1280, "height": 800})
                page.goto(harness.base_url + "#tab=library")
                expect(page.locator("[data-lib-view] .lib-thumb video")).to_have_count(1)
                page.wait_for_function(
                    "() => { const v = document.querySelector('[data-lib-view] .lib-thumb video');"
                    " return v && v.readyState >= 2 && v.videoWidth > 0; }", timeout=15_000)
        finally:
            browser.close()
```

- [ ] **Step 3: Run the new e2e**

Run: `LMD_LIBRARY_SHOTS=/tmp/lmd-library-shots python3 -m pytest tests/e2e/test_library_views.py tests/e2e/test_library_webkit.py -q`
Expected: PASS（WebKit 那条若 skip，报告里写明原因）

若 WebKit 用例**失败**（首帧出不来）：按 L-53 退回占位——在 `panes/library.js` 的 `thumbNode` 里视频分支改成与音乐相同的「类型图标 + 时长角标」（不建 `<video>`、不悬停播放），删掉 Task 3 测试里与视频 `src`/懒加载相关的两条断言并改为断言 `.icon` 存在，把 WebKit 用例改为断言卡片里没有 `<video>`，并在 spec 第 7 节追加一条「L-53 结果：WebKit 出不来首帧，已退回占位」。

- [ ] **Step 4: Look at the screenshots**

用 Read 工具逐张看 `/tmp/lmd-library-shots/*.png`（grid/list/table × 1280/900、preview-1280、preview-900），核对：
- 缩略图网格整齐、选中项有描边、标题两行截断；
- 列表行左缩略图、右动作按钮不被挤出；
- 明细表头对齐、提示词列截断、没有横向滚动条（900 宽也没有）；
- 弹层居中、图片不溢出、信息区在 1280 时在右、900 时在下。
有问题就改 `app.css` 第 16 节并重跑 Step 3。

- [ ] **Step 5: Full suites**

Run: `node --test tests/js/`
Expected: 全部 PASS

Run: `python3 -m pytest -q --ignore=tests/e2e`
Expected: PASS（`tests/test_shell_window.py` 有 4 条已知的环境性偶发失败，与本改动无关；如出现，重跑该文件确认）

Run: `python3 -m pytest tests/e2e -q`
Expected: 全部 PASS

- [ ] **Step 6: Commit**

```bash
git add tests/e2e/test_library_panel.py tests/e2e/test_image_sessions.py tests/e2e/test_image_flow.py tests/e2e/test_outputs_range.py tests/e2e/test_library_views.py tests/e2e/test_library_webkit.py desk/static/app.css
git commit -m "test(library): e2e 迁移到预览弹层，新增三视图/键盘/切页停声与 WebKit 首帧核对"
```
