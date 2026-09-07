# Cross-exam Recheck Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close every gap and high/medium visual finding left by the recheck run `docs/cross-exam/2026-09-07-localmodeldesk-fixes/` (J16 model swap, web findings F1–F20, native findings N1–N8, functional observations G1 duplicated log and the open threads that describe defects).

**Architecture:** Same layering as Plans A/B: pure JS modules in `desk/static/js/pure/` own every string and decision, panes/widgets only write DOM, Python service owns validation copy, Swift shell owns the menubar/error page with pure mappings in `macos/ShellStatus.swift` tested through the headless harness. No new dependencies. Every task ends with `node --test "tests/js/*.test.js"` or `python3 -m pytest` green and a commit.

**Tech Stack:** Python 3.13 stdlib service, ES-module frontend (no build, `node --test`), Swift AppKit shell + `macos/harness/ShellHarness.swift` compiled by `tests/shell_helpers.py`, Playwright e2e (optional, `tests/e2e/`).

**Spec:** `docs/cross-exam/2026-09-07-localmodeldesk-fixes/completion-report.md` (gap list + `open_threads`), reviewer reports `evidence/vis-web/review-claude.json` (F1–F20) and `evidence/vis-b3/review-claude.json` (N1–N9), frozen baseline `visual/visual-baseline.json` + `visual/interaction-baseline.json`.

## Global Constraints

- Frontend: no `innerHTML`; `createElement`/`textContent` only; all copy in Chinese; tokens from `desk/static/app.css` `:root` (`--ok #3fb950`, `--busy #d29922`, `--danger #e5534b`, `--accent #4f8cff`).
- Baseline rules referenced by finding id: D3 status = colour + icon + text; C3 semantic colours only for state, error codes never shown red in body copy; F2 errors are plain Chinese + optional 「详情」; F3 long tasks show progress + collapsed log; ST1 five states per pane; ST2 disabled buttons carry a reason next to them; K1 three button levels, disabled = opacity .5; K2 ChatGPT-style messages (dot + model name, 「已思考 N 秒」); D1 single dark theme; ST3 outage page 「服务未响应」 + 重试.
- Tests: JS `node --test "tests/js/*.test.js"` (Node 26 — pass the glob, not the directory); Python `python3 -m pytest -q`; Swift pure logic via `harness_path()` subcommands in `tests/test_shell_status.py` / `tests/test_shell_window.py`.
- Never touch the user's models under `/Users/aa/LocalModelDesk` (llms/, minimax-*), never run against the dist instance on 8766 during development; use `LMD_SHELL_PORT`/`LOCALMODELDESK_DATA_ROOT` overrides.
- Commit after every task with a message prefixed `fix(recheck):`.

---

## File Structure

| File | Responsibility (after this plan) |
|---|---|
| `desk/static/js/pure/desk_state.js` | statusbar view model: adds `nextOk`, `nextIcon`, display-name mapping, exposes reason `code` |
| `desk/static/js/icons.js` | adds `setIcon(control, name)` to swap an existing icon |
| `desk/static/js/widgets/statusbar.js` | writes `data-ok` + swaps the next-step icon |
| `desk/static/js/pure/job_error.js` | human titles for `exit_nonzero`/`worker_failed`/`caption_required`/`prompt_required`; code never in title |
| `desk/static/js/widgets/jobview.js` | per-kind filtering, `sync()` replaces log, error state layout, indeterminate progress |
| `desk/static/js/panes/chat.js` | swap-model flow, unload disabled when idle, evicted copy, history message names, empty-content placeholder |
| `desk/static/js/panes/library.js` | failure details fold, playing-row highlight |
| `desk/static/js/panes/resources.js` + `pure/model_status.js` | disabled-download reason text in the card |
| `desk/static/js/panes/settings.js` | not-listening placeholder copy |
| `desk/static/js/panes/music.js` | front-end caption required check |
| `desk/static/js/main.js` | catalog names map for statusbar; llm swap allowed when `llm_already_held` |
| `desk/static/index.html`, `desk/static/app.css` | DOM order of job error block; state colours; overflow fix; cancel width; hint spacing; audio dark scheme |
| `desk/resources/verify.py` | percent counts in-flight `.incomplete` bytes |
| `desk/media/service.py` | Chinese `caption_required` / `prompt_required` errors |
| `macos/ShellStatus.swift` | `memoryMenuTitle`, error page with 「服务未响应」 + danger accent + folded log path |
| `macos/StatusItemController.swift`, `macos/StatusPoller.swift`, `macos/DeskAPI.swift`, `macos/AppDelegate.swift` | memory line refreshed every poll and on open (common run-loop modes), dark appearance, first-run dialog path |
| `macos/harness/ShellHarness.swift` | new `memory-line` subcommand |

---

### Task 1: Statusbar next-step icon, colour and display names (F1/N2, F2, F11)

**Files:**
- Modify: `desk/static/js/pure/desk_state.js`
- Modify: `desk/static/js/icons.js`
- Modify: `desk/static/js/widgets/statusbar.js`
- Modify: `desk/static/js/main.js:30-45,80-95`
- Modify: `desk/static/app.css` (section 4)
- Test: `tests/js/desk_state.test.js`, `tests/js/widgets.test.js`

**Interfaces:**
- Produces: `renderState(deskState, snapshot, download = null, names = {})` → adds `nextOk: boolean`, `nextIcon: "check" | "x"`; `holderText` and `mediaText` use `names[key] ?? key`.
- Produces: `heavyAvailability(deskState, kind)` → adds `code: string | null`.
- Produces: `setIcon(control, name, doc?)` in `icons.js` (replaces the first `.icon` child, or appends).
- Produces: `createStatusBar(root).update(deskState, snapshot, download, names)`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/js/desk_state.test.js`:

```js
test("下一件重活：图标与 ok 位随可否开工变化，不随 tone 变化（F1/F2）", () => {
  const ok = renderState(idle, snapA);
  assert.equal(ok.nextOk, true);
  assert.equal(ok.nextIcon, "check");
  const busy = renderState(
    { holder: { kind: "video", label: "3" }, media_busy: true, can_start: { ok: false, reason: "media_busy" } }, snapA);
  assert.equal(busy.nextOk, false);
  assert.equal(busy.nextIcon, "x");
  // downloading keeps tone busy but the next-step item stays ok
  const dl = renderState(idle, snapA, { state: "running", key: "superqwen" });
  assert.equal(dl.tone, "busy");
  assert.equal(dl.nextOk, true);
  assert.equal(dl.nextIcon, "check");
});

test("状态条用显示名而不是 key（F11）", () => {
  const names = { glm: "GLM 4.7 Flash 越狱 4bit", superqwen: "SuperQwen3.8 27B 越狱 4bit" };
  const loaded = { holder: { kind: "llm", label: "glm" }, media_busy: false, can_start: { ok: false, reason: "llm_already_held" } };
  assert.equal(renderState(loaded, snapA, null, names).holderText, "内存里：GLM 4.7 Flash 越狱 4bit");
  assert.equal(renderState(idle, snapA, { state: "running", key: "superqwen" }, names).mediaText, "媒体：空闲 · 下载中 SuperQwen3.8 27B 越狱 4bit");
  assert.equal(renderState(loaded, snapA).holderText, "内存里：glm");
});

test("heavyAvailability 透出原因码", () => {
  const held = { holder: { kind: "llm", label: "glm" }, media_busy: false, can_start: { llm: { ok: false, reason: { code: "llm_already_held" } } } };
  assert.equal(heavyAvailability(held, "llm").code, "llm_already_held");
  assert.equal(heavyAvailability(idle, "llm").code, null);
});
```

Append to `tests/js/widgets.test.js` (uses its `FakeElement`; add `querySelector` support inside the test):

```js
test("statusbar 写 data-ok 并换图标（F1）", () => {
  const parts = { mem: new FakeElement(), holder: new FakeElement(), media: new FakeElement(), next: new FakeElement() };
  const nextPart = new FakeElement(); nextPart.append(parts.next);
  const icon = new FakeElement("svg"); icon.className = "icon"; nextPart.children.unshift(icon);
  const root = new FakeElement();
  root.ownerDocument = { createElement: (tag) => new FakeElement(tag) };
  root.querySelector = (selector) => ({ "[data-mem]": parts.mem, "[data-holder]": parts.holder, "[data-media]": parts.media, "[data-next]": parts.next, ".status-next": nextPart })[selector];
  const bar = createStatusBar(root);
  bar.update({ holder: { kind: "video", label: "1" }, media_busy: true, can_start: { ok: false, reason: "media_busy" } }, { total_bytes: 2, used_bytes: 1, available_bytes: 1 });
  assert.equal(nextPart.dataset.ok, "0");
  assert.equal(nextPart.children[0].className, "icon icon-x");
  bar.update({ holder: null, media_busy: false, can_start: { ok: true } }, { total_bytes: 2, used_bytes: 1, available_bytes: 1 });
  assert.equal(nextPart.dataset.ok, "1");
  assert.equal(nextPart.children[0].className, "icon icon-check");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/desk_state.test.js tests/js/widgets.test.js`
Expected: FAIL (`nextOk` undefined, `code` undefined, `setIcon` missing).

- [ ] **Step 3: Implement**

`desk/static/js/pure/desk_state.js` — replace `heavyAvailability` and `renderState`:

```js
export function heavyAvailability(deskState, kind) {
  const decision = decisionFor(deskState, kind);
  const reason = decision?.reason;
  const code = (typeof reason === "object" ? reason?.code : reason) ?? null;
  return {
    allowed: decision?.ok !== false,
    code,
    reason: REASON_TEXT[code] ?? (code ? `暂不可用（${code}）` : ""),
  };
}

export function renderState(deskState, snapshot, download = null, names = {}) {
  const gb = (n) => (n / GB).toFixed(1);
  const display = (key) => names?.[key] ?? key;
  const memText = snapshot && Number.isFinite(snapshot.total_bytes)
    ? `已用 ${gb(snapshot.used_bytes)} / 总 ${gb(snapshot.total_bytes)} GiB（可用 ${gb(snapshot.available_bytes)} GiB）`
    : "内存读数不可用";

  const holder = deskState?.holder ?? null;
  let holderText = "内存里：无";
  if (holder) {
    if (holder.kind === "llm") holderText = `内存里：${display(holder.label)}`;
    else if (holder.kind === "video") holderText = "视频生成中";
    else if (holder.kind === "music") holderText = "音乐生成中";
    else holderText = `${holder.kind}：${holder.label}`;
  }

  const downloading = download?.state === "running" ? download.key : null;
  const mediaText = `${deskState?.media_busy ? "媒体：生成中" : "媒体：空闲"}${downloading ? ` · 下载中 ${display(downloading)}` : ""}`;

  const nextKind = deskState?.media_busy || holder?.kind === "llm" ? "media" : "llm";
  const can = decisionFor(deskState, nextKind);
  const reason = typeof can?.reason === "object" ? can?.reason?.code : can?.reason;
  const ok = can ? can.ok !== false : false;
  const nextText = ok ? "可开下一件重活" : `不可：${REASON_TEXT[reason] ?? reason ?? "状态未知"}`;
  const tone = deskState?.media_busy || downloading ? "busy" : holder ? "ok" : ok ? "ok" : "error";
  return { memText, holderText, mediaText, nextText, nextOk: ok, nextIcon: ok ? "check" : "x", tone };
}
```

`desk/static/js/icons.js` — add after `addIcon`:

```js
export function setIcon(control, name, doc = control?.ownerDocument ?? globalThis.document) {
  if (!control || !doc) return control;
  const fresh = iconNode(doc, name);
  fresh.className = fresh.className ? fresh.className : "icon";
  if (fresh.setAttribute) fresh.setAttribute("class", `icon icon-${name}`); else fresh.className = `icon icon-${name}`;
  const existing = control.children ? [...control.children].find((child) => String(child.className ?? "").includes("icon")) : control.querySelector?.(".icon");
  if (existing && control.replaceChild) control.replaceChild(fresh, existing);
  else if (existing && control.children) control.children[control.children.indexOf(existing)] = fresh;
  else { control.append(fresh); control.classList?.add?.("with-icon"); }
  return control;
}
```

(`iconNode` already returns `<svg class="icon">`; `setAttribute("class", …)` keeps the `icon` base class so CSS still applies.)

`desk/static/js/widgets/statusbar.js`:

```js
import { renderState } from "../pure/desk_state.js";
import { setIcon } from "../icons.js";

export function createStatusBar(root) {
  const mem = root.querySelector("[data-mem]");
  const holder = root.querySelector("[data-holder]");
  const media = root.querySelector("[data-media]");
  const next = root.querySelector("[data-next]");
  const nextPart = root.querySelector(".status-next");
  let isOffline = false;
  let lastIcon = null;
  return {
    update(deskState, snapshot, download = null, names = {}) {
      const view = renderState(deskState, snapshot, download, names);
      mem.textContent = view.memText;
      holder.textContent = view.holderText;
      media.textContent = view.mediaText;
      next.textContent = isOffline ? "服务失联" : view.nextText;
      root.dataset.tone = view.tone;
      if (nextPart) {
        nextPart.dataset.ok = isOffline ? "0" : view.nextOk ? "1" : "0";
        const icon = isOffline ? "x" : view.nextIcon;
        if (icon !== lastIcon) { setIcon(nextPart, icon, root.ownerDocument); lastIcon = icon; }
      }
    },
    offline(value) {
      isOffline = Boolean(value);
      root.dataset.offline = isOffline ? "1" : "0";
      if (isOffline) { next.textContent = "服务失联"; if (nextPart) { nextPart.dataset.ok = "0"; setIcon(nextPart, "x", root.ownerDocument); lastIcon = "x"; } }
    },
  };
}
```

`desk/static/js/main.js` — hold a names map and pass it:

```js
let modelNames = {};
// in enterDesk(), right after `statusbar = createStatusBar(...)`:
    api.listCatalog().then((entries) => { modelNames = Object.fromEntries((entries.models ?? entries).map((e) => [e.key, e.name])); }).catch(() => {});
// in tick(): replace `statusbar.update(deskState, memory, download);` with
    statusbar.update(deskState, memory, download, modelNames);
// in applyHeavyAvailability(): allow the swap path (Task 6 uses it)
  const llm = heavyAvailability(deskState, "llm");
  const llmAllowed = llm.allowed || llm.code === "llm_already_held";
  panes.chat.setHeavyAllowed(llmAllowed, llmAllowed ? "" : llm.reason);
```

`desk/static/app.css` section 4 — replace the three `.status-next` colour lines with:

```css
.status-next{color:var(--muted)}.status-next>span{color:inherit}
.status-next[data-ok="1"]{color:var(--ok)}.status-next[data-ok="0"]{color:var(--busy)}
#statusbar[data-offline="1"] .status-next,#statusbar[data-tone="error"] .status-next{color:var(--danger)}
```

- [ ] **Step 4: Run tests**

Run: `node --test "tests/js/*.test.js"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/pure/desk_state.js desk/static/js/icons.js desk/static/js/widgets/statusbar.js desk/static/js/main.js desk/static/app.css tests/js/desk_state.test.js tests/js/widgets.test.js
git commit -m "fix(recheck): statusbar next-step icon/colour follow can_start, display names (F1 F2 F11 N2)"
```

---

### Task 2: Error titles never carry the machine code (F3, F18)

**Files:**
- Modify: `desk/static/js/pure/job_error.js`
- Modify: `desk/static/js/panes/library.js:75-90`
- Test: `tests/js/job_error.test.js`, `tests/js/library_pane.test.js`

**Interfaces:**
- Produces: `describeJobError(error)` → `{ title, detail }` where `title` is plain Chinese without parentheses-code; `detail` always begins with `${code}: ${message}`.

- [ ] **Step 1: Write the failing tests**

Replace the last two assertions in `tests/js/job_error.test.js` and add cases:

```js
  assert.equal(describeJobError({ code: "no_output", message: "exit 0 but output file missing" }).title, "生成结束但没有产出文件");
  assert.equal(describeJobError({ code: "exit_nonzero", message: "exit -9" }).title, "生成程序异常退出");
  assert.equal(describeJobError({ code: "worker_failed", message: "boom" }).title, "生成程序意外退出");
  assert.equal(describeJobError({ code: "caption_required", message: "请填写风格描述" }).title, "请填写风格描述");
  assert.equal(describeJobError({ code: "prompt_required", message: "请填写视频提示词" }).title, "请填写视频提示词");
  const weird = describeJobError({ code: "weird", message: "?" });
  assert.equal(weird.title, "生成失败");
  assert.ok(!/weird/.test(weird.title));
  assert.equal(weird.detail, "weird: ?");
```

Append to `tests/js/library_pane.test.js` a test that a failed history entry renders a `details` fold with the raw code:

```js
test("失败记录：标题是人话，原始码收进「详情」（F3）", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (path) => ({ ok: true, json: async () => path === "/api/outputs" ? [] : [{
    kind: "video", status: "failed", ts: "2026-09-07T03:35:00Z", output: null, error: "exit_nonzero: exit 1",
    params: { prompt: "镜头缓慢推近", width: 512, height: 288, frames: 49, steps: 16 } }] });
  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "player", "list", "error"].map((name) => [name, new FakeElement()]));
  const root = new FakeElement(); root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-lib-(.+)\]/)[1]];
  await createLibraryPane(root, { applyFill() {} }).refresh();
  const row = elements.list.children[0];
  const title = find(row, (n) => n.className === "inline-error");
  assert.equal(title.textContent, "生成程序异常退出");
  const details = find(row, (n) => n.tagName === "details");
  assert.ok(details, "缺少详情折叠");
  assert.equal(find(details, (n) => n.tagName === "pre").textContent, "exit_nonzero: exit 1");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/job_error.test.js tests/js/library_pane.test.js`
Expected: FAIL (`生成失败（exit_nonzero）`, no `details`).

- [ ] **Step 3: Implement**

`desk/static/js/pure/job_error.js`:

```js
const RULES = [
  [/BudgetExceeded|out of memory|SWAPPING/i, "内存不足，生成被中止"],
  [/load_rgb_image|ffmpeg|decode|Invalid data/i, "素材无法解码，请换一张图片或视频"],
  [/lyrics must be a non-empty/i, "请填写歌词"],
];
const CODE_TITLE = {
  lyrics_required: null, caption_required: null, prompt_required: null,
  no_output: "生成结束但没有产出文件", spawn_failed: "无法启动生成程序",
  worker_failed: "生成程序意外退出", exit_nonzero: "生成程序异常退出",
  insufficient_memory: "可用内存不足", media_busy: "已有作业在进行",
};

export function describeJobError(error) {
  if (!error) return { title: "", detail: "" };
  const tail = typeof error.log_tail === "string" ? error.log_tail : "";
  const detail = [`${error.code}: ${error.message}`, tail].filter(Boolean).join("\n");
  const hit = RULES.find(([re]) => re.test(tail) || re.test(error.message ?? ""));
  if (hit) return { title: hit[1], detail };
  if (error.code in CODE_TITLE) return { title: CODE_TITLE[error.code] ?? error.message, detail };
  return { title: "生成失败", detail };
}
```

`desk/static/js/panes/library.js` — inside `rowNode`, replace the `if (entry.error) { … }` block:

```js
      if (entry.error) {
        const [code, ...rest] = entry.error.split(": ");
        const { title: errorTitle, detail } = describeJobError({ code, message: rest.join(": ") });
        const error = doc.createElement("p");
        error.className = "inline-error";
        error.textContent = errorTitle;
        const details = doc.createElement("details");
        details.className = "lib-error-details";
        const summary = doc.createElement("summary");
        summary.textContent = "详情";
        const pre = doc.createElement("pre");
        pre.textContent = detail;
        details.append(summary, pre);
        head.append(error, details);
      }
```

`desk/static/app.css` section 6b — add:

```css
.lib-error-details{font-size:13px;color:var(--muted)}.lib-error-details pre{margin:4px 0 0;white-space:pre-wrap;font:12px ui-monospace,Menlo,monospace}
```

- [ ] **Step 4: Run tests**

Run: `node --test "tests/js/*.test.js"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/pure/job_error.js desk/static/js/panes/library.js desk/static/app.css tests/js/job_error.test.js tests/js/library_pane.test.js
git commit -m "fix(recheck): plain-language job error titles, code folded into details (F3 F18)"
```

---

### Task 3: Job view — per-kind filtering, sync without duplicate log, error layout, indeterminate progress (G1, F7/N3, F19, F20, F12, shared-poll thread)

**Files:**
- Modify: `desk/static/js/widgets/jobview.js`
- Modify: `desk/static/js/panes/video.js:28`, `desk/static/js/panes/music.js:11`
- Modify: `desk/static/index.html` (both `.job` blocks)
- Modify: `desk/static/app.css` section 8
- Test: `tests/js/media_panes.test.js`

**Interfaces:**
- Produces: `createJobView(root, { mediaTag, kind })`; `apply(payload, { replaceLog = false } = {})`; `sync()` fetches `jobStatus(0, null)` and applies with `replaceLog: true`; payloads whose `kind` is set and differs from `kind` render the idle state and return `null`.
- Consumes: `describeJobError` from Task 2.

- [ ] **Step 1: Write the failing tests**

Append to `tests/js/media_panes.test.js`:

```js
test("sync 用全量日志替换而不是追加（G1），且不显示别的面板的作业（共用轮询）", async () => {
  const video = pane({ "video-prompt": "雾", "video-size": "512x288", "video-frames": "49", "video-steps": "8", "video-start": "" });
  const videoPane = createVideoPane(video, {});
  await withFetch([{ job_id: 3, status: "running", kind: "video", log: "step 1/16\n", next_log_from: 10 }], async () => {
    await video.parts["video-start"].click();
  });
  assert.equal(video.parts["job-log"].textContent, "step 1/16\n");
  await withFetch([{ job_id: 3, status: "done", kind: "video", output: "a.mp4", log: "step 1/16\nstep 16/16\nwrote a.mp4\n", next_log_from: 40 }], async () => {
    await videoPane.jobView.sync();
  });
  assert.equal(video.parts["job-log"].textContent, "step 1/16\nstep 16/16\nwrote a.mp4\n");
  await withFetch([{ job_id: 4, status: "done", kind: "music", output: "b.wav", log: "music log\n", next_log_from: 10 }], async () => {
    await videoPane.jobView.sync();
  });
  assert.equal(video.parts["job-status"].textContent, "空闲 · 填好左侧参数后点「生成」");
  assert.equal(video.parts["job-log"].textContent, "");
});

test("error 态：错误块先于日志、日志不自动展开、状态行带 data-state（F19/F20）", () => {
  const video = pane({ "video-prompt": "雾", "video-size": "512x288", "video-frames": "49", "video-steps": "8", "video-start": "" });
  video.parts["job-log-details"] = new Element("", "details");
  const view = createVideoPane(video, {}).jobView;
  view.apply({ job_id: 5, status: "error", kind: "video", error: { code: "exit_nonzero", message: "exit -9" }, log: "step 1/16\n" });
  assert.equal(video.parts["job-status"].dataset.state, "error");
  assert.equal(video.parts["job-log-details"].open, false);
  assert.equal(video.parts["job-error"].children[0].textContent, "生成程序异常退出");
});

test("running 且日志无 step 行时进度条为不定态（F7/N3）", () => {
  const music = pane({ "music-caption": "民谣", "music-lyrics": "一二三", "music-duration": "10", "music-start": "" });
  const view = createMusicPane(music, {}).jobView;
  view.apply({ job_id: 6, status: "running", kind: "music", log: "loading model\n", elapsed_s: 4 });
  assert.equal(music.parts["job-progress"].hidden, false);
  assert.equal(music.parts["job-progress"].indeterminate, true);
  view.apply({ job_id: 6, status: "running", kind: "music", log: "step 2/8\n", elapsed_s: 9 });
  assert.equal(music.parts["job-progress"].indeterminate, false);
  assert.equal(music.parts["job-progress"].value, 25);
});
```

Extend the test `pane()` helper so `[data-job-log-details]` and `dataset` exist: in `class Element` constructor add `this.dataset = {}; this.indeterminate = false;` and add `removeAttribute(name) { if (name === "value") { this.value = ""; this.indeterminate = true; } }` plus in `pane()` add `"job-log-details"` to the defaulted names list and make `querySelector` also answer `.job-log` with `parts["job-log-details"]`:

```js
  return { parts, ownerDocument: doc, querySelector(selector) {
    if (selector === ".job-log") return parts["job-log-details"];
    return parts[selector.match(/^\[data-([\w-]+)\]$/)?.[1]] || null; } };
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/media_panes.test.js`
Expected: FAIL (log duplicated, music job applied to video pane, `data-state` missing).

- [ ] **Step 3: Implement**

`desk/static/js/widgets/jobview.js`:

```js
import * as api from "../api.js";
import { formatDuration } from "../pure/format.js";
import { describeJobError } from "../pure/job_error.js";
import { parseStepProgress } from "../pure/job_progress.js";

const STATUS_LABEL = { idle: "空闲 · 填好左侧参数后点「生成」", running: "生成中…", done: "完成", error: "失败", cancelled: "已取消" };
const IDLE = { job_id: null, status: "idle", kind: null, log: "" };

export function createJobView(root, { mediaTag, kind = null }) {
  const els = {
    status: root.querySelector("[data-job-status]"), log: root.querySelector("[data-job-log]"),
    cancelBtn: root.querySelector("[data-job-cancel]"), player: root.querySelector("[data-job-player]"),
    error: root.querySelector("[data-job-error]"), progress: root.querySelector("[data-job-progress]"),
    logDetails: root.querySelector(".job-log"),
  };
  let jobId = null;
  let logText = "";
  function reset() {
    jobId = null; logText = "";
    els.log.textContent = ""; els.player.replaceChildren(); els.error.textContent = "";
    if (els.error.replaceChildren) els.error.replaceChildren();
    if (els.progress) { els.progress.hidden = true; els.progress.indeterminate = false; }
    if (els.logDetails) els.logDetails.open = false;
  }
  function statusText(job) {
    if (job.status === "running" && typeof job.elapsed_s === "number") return `生成中…（已用 ${formatDuration(job.elapsed_s)}）`;
    const duration = job.started_at && job.finished_at ? `（耗时 ${formatDuration(job.finished_at - job.started_at)}）` : "";
    return `${STATUS_LABEL[job.status] ?? job.status}${duration}`;
  }
  function renderError(error) {
    const { title, detail } = describeJobError(error);
    els.error.replaceChildren();
    const strong = root.ownerDocument.createElement("strong"); strong.textContent = title;
    const details = root.ownerDocument.createElement("details");
    const summary = root.ownerDocument.createElement("summary"); summary.textContent = "详情";
    const pre = root.ownerDocument.createElement("pre"); pre.textContent = detail;
    details.append(summary, pre); els.error.append(strong, details);
  }
  function apply(payload, { replaceLog = false } = {}) {
    if (kind && payload.kind && payload.kind !== kind) { reset(); apply(IDLE); return null; }
    if (payload.job_id !== jobId) { reset(); jobId = payload.job_id ?? null; replaceLog = true; }
    els.status.textContent = statusText(payload);
    if (els.status.dataset) els.status.dataset.state = payload.status ?? "idle";
    els.cancelBtn.hidden = payload.status !== "running";
    if (typeof payload.log === "string") {
      if (replaceLog) { logText = payload.log; els.log.textContent = payload.log; }
      else if (payload.log) { logText += payload.log; els.log.textContent += payload.log; }
      els.log.scrollTop = els.log.scrollHeight;
    }
    if (els.progress) {
      const prog = parseStepProgress(logText);
      const running = payload.status === "running";
      els.progress.hidden = !running;
      if (running && prog) { els.progress.indeterminate = false; els.progress.value = prog.pct; }
      else if (running) { els.progress.indeterminate = true; els.progress.removeAttribute?.("value"); }
    }
    if (payload.status === "error" && payload.error) renderError(payload.error);
    if (payload.status === "done" && payload.output && !els.player.firstChild) {
      const media = root.ownerDocument.createElement(mediaTag);
      media.controls = true; media.src = api.serveOutput(payload.output); els.player.append(media);
    }
    return payload;
  }
  function start(payload) { reset(); jobId = payload.job_id ?? null; return apply(payload, { replaceLog: true }); }
  els.cancelBtn.addEventListener("click", async () => {
    try { apply(await api.cancelJob()); } catch (error) { els.error.textContent = error.message; }
  });
  async function sync() {
    try { apply(await api.jobStatus(0, null), { replaceLog: true }); } catch { /* offline: keep what we have */ }
  }
  return { reset, apply, start, sync };
}
```

Note the log details are no longer force-opened on error (F19) and the progress bar is shown for any running job (indeterminate when no step line yet; F7/N3).

`desk/static/js/panes/video.js:28` → `const jobView = createJobView(root, { mediaTag: "video", kind: "video" });`
`desk/static/js/panes/music.js:11` → `const jobView = createJobView(root, { mediaTag: "audio", kind: "music" });`

`desk/static/js/main.js` `tickJob` — since the view now filters by kind, keep routing but pass `replaceLog` when the id changes:

```js
async function tickJob() {
  const payload = await api.jobStatus(jobLogFrom, lastJobId);
  const pane = payload.kind === "music" ? panes.music : panes.video;
  const changed = payload.job_id !== lastJobId;
  if (changed) { lastJobId = payload.job_id; jobLogFrom = 0; }
  pane.jobView.apply(payload, { replaceLog: changed }); jobLogFrom = payload.next_log_from ?? jobLogFrom;
  if (payload.status !== "running") jobActive = false;
}
```

`desk/static/index.html` — in both `.job` blocks move the error block before the log, and give the status line an icon slot. The video block becomes:

```html
<div class="job"><p class="job-status" data-job-status data-state="idle">空闲</p><progress data-job-progress max="100" hidden></progress><button data-job-cancel data-icon-name="x" hidden>取消</button><div class="inline-error job-error" data-job-error></div><details class="job-log"><summary>日志</summary><pre data-job-log></pre></details><div data-job-player></div></div>
```

(Same for the music block.)

`desk/static/app.css` section 8 — add:

```css
.job-status{margin:0;font-weight:600}
.job-status[data-state="running"]{color:var(--busy)}.job-status[data-state="done"]{color:var(--ok)}
.job-status[data-state="error"]{color:var(--danger)}.job-status[data-state="error"]::before{content:"✕ ";}
.job-status[data-state="done"]::before{content:"✓ ";}
.job [data-job-cancel]{align-self:flex-start}
.job-error{padding:12px;border:1px solid var(--danger);border-radius:var(--radius);background:rgba(229,83,75,.08)}
.job-error:empty{display:none}.job-error details{margin-top:8px;color:var(--muted);font-size:13px}.job-error pre{white-space:pre-wrap;margin:4px 0 0;font:12px ui-monospace,Menlo,monospace}
.form>.hint-busy{margin:-4px 0 0}
[data-job-player] audio,[data-lib-player] audio{width:100%;color-scheme:dark}
```

- [ ] **Step 4: Run tests**

Run: `node --test "tests/js/*.test.js"` and `python3 -m pytest tests/test_shell_static.py tests/test_ui_static.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/widgets/jobview.js desk/static/js/panes/video.js desk/static/js/panes/music.js desk/static/js/main.js desk/static/index.html desk/static/app.css tests/js/media_panes.test.js
git commit -m "fix(recheck): jobview per-kind, sync replaces log, error layout, indeterminate progress (G1 F7 F12 F19 F20 N3)"
```

---

### Task 4: Resource cards — disabled-download reason and in-flight bytes in percent (F4, F5, F6)

**Files:**
- Modify: `desk/resources/verify.py`
- Modify: `desk/static/js/panes/resources.js:95-115`
- Modify: `desk/static/app.css` section 4 (overflow) + 6b
- Test: `tests/test_resources_verify.py`, `tests/js/resources_pane.test.js`

**Interfaces:**
- Produces: `verify_tree(entry, manifest, models_root)` counts `<model_dir>/.cache/huggingface/download/**/*.incomplete` bytes into `percent` (capped at the file's remaining bytes) and reports them as `bytes_in_flight`; `bytes_local` unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_resources_verify.py`:

```python
def test_incomplete_cache_bytes_count_toward_percent_but_not_bytes_local(tmp_path):
    directory = model_dir(tmp_path)
    (directory / "tokenizer.json").write_bytes(b"b" * 60)
    cache = directory / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    (cache / "model.safetensors.abc123.incomplete").write_bytes(b"x" * 70)
    status = verify_tree(GLM, MANIFEST, tmp_path)
    assert status.state == "partial"
    assert status.bytes_local == 60
    assert status.bytes_in_flight == 70
    assert status.percent == 65.0          # (60 + 70) / 200


def test_incomplete_bytes_are_capped_at_expected_total(tmp_path):
    directory = model_dir(tmp_path)
    cache = directory / ".cache" / "huggingface" / "download"
    cache.mkdir(parents=True)
    (cache / "big.incomplete").write_bytes(b"x" * 500)
    status = verify_tree(GLM, MANIFEST, tmp_path)
    assert status.state == "partial"
    assert status.percent == 100.0 or status.percent < 100.0 and status.bytes_in_flight == 200
```

(Second test pins the cap: `percent` never exceeds 100 and `bytes_in_flight` is capped at `expected_total - local_total`.)

Append to `tests/js/resources_pane.test.js` (uses the file's `FakeElement` and `find` helpers):

```js
test("别的模型下载中：本行「下载」禁用且卡片内写原因（F4）", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (path) => ({ ok: true, json: async () => {
    if (path === "/api/resources/catalog") return [{ key: "a", name: "甲", gb: 1 }, { key: "b", name: "乙", gb: 1 }];
    if (String(path).startsWith("/api/resources/status")) return {
      download: { state: "running", key: "a" },
      models: [{ key: "a", state: "partial", percent: 5, disk_bytes: 1 }, { key: "b", state: "missing", disk_bytes: 0 }],
    };
    return { free_bytes: 1, total_bytes: 2 };
  }});
  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "list", "error", "disk"].map((name) => [name, new FakeElement()]));
  const root = new FakeElement(); root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-res-(.+)\]/)[1]];
  await createResourcesPane(root).refresh();
  const rowB = elements.list.children[1];
  const download = find(rowB, (el) => el.tagName === "button" && el.textContent === "下载");
  assert.equal(download.disabled, true);
  const why = find(rowB, (el) => el.className === "hint res-disabled-reason");
  assert.equal(why.textContent, "已有一个下载在进行（同时只允许一个）");
  assert.equal(find(elements.list.children[0], (el) => el.className === "hint res-disabled-reason"), null);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_resources_verify.py -q` and `node --test tests/js/resources_pane.test.js`
Expected: FAIL (`bytes_in_flight` attribute missing; no reason node).

- [ ] **Step 3: Implement**

`desk/resources/verify.py` — add the field and the cache scan:

```python
@dataclass(frozen=True)
class ModelStatus:
    key: str
    state: str
    percent: float
    bytes_expected: int
    bytes_local: int
    disk_bytes: int
    gaps: tuple[FileGap, ...]
    manifest_source: str
    manifest_fetched_at: str | None
    reason: str | None = None
    bytes_in_flight: int = 0

    def to_json(self) -> dict:
        payload = asdict(self)
        payload["gaps"] = [asdict(gap) for gap in self.gaps]
        return payload


def _in_flight_bytes(model_dir: Path) -> int:
    """Bytes sitting in hf's .incomplete files: downloaded but not yet moved into place."""
    cache = model_dir / ".cache" / "huggingface" / "download"
    total = 0
    try:
        for path in cache.rglob("*.incomplete"):
            try:
                if path.is_file():
                    total += path.stat().st_size
            except OSError:
                continue
    except OSError:
        return 0
    return total


def verify_tree(entry: ModelEntry, manifest: Manifest, models_root: Path) -> ModelStatus:
    """Stat manifest paths and return their byte-accurate completeness status."""
    model_dir = Path(models_root) / entry.relpath
    expected_total = manifest.total_bytes
    local_total = 0
    gaps: list[FileGap] = []

    for file in manifest.files:
        try:
            local_size = (model_dir / file.path).lstat().st_size
        except OSError:
            local_size = 0
        local_total += min(local_size, file.size)
        if local_size != file.size:
            gaps.append(FileGap(file.path, file.size, local_size))

    in_flight = 0 if not gaps else min(_in_flight_bytes(model_dir), max(expected_total - local_total, 0))
    counted = local_total + in_flight
    state = "present" if not gaps else "missing" if counted == 0 else "partial"
    percent = round(min(counted / expected_total, 1.0) * 100.0, 2) if expected_total else 0.0
    return ModelStatus(
        key=entry.key,
        state=state,
        percent=percent,
        bytes_expected=expected_total,
        bytes_local=local_total,
        disk_bytes=dir_bytes(model_dir),
        gaps=tuple(gaps),
        manifest_source=manifest.source,
        manifest_fetched_at=manifest.fetched_at,
        bytes_in_flight=in_flight,
    )
```

`desk/static/js/panes/resources.js` — in `rowNode`, after the actions loop and before `li.append(actions)`:

```js
    if (view.downloadDisabled && view.downloadDisabledReason) {
      const why = doc.createElement("p");
      why.className = "hint res-disabled-reason";
      why.textContent = view.downloadDisabledReason;
      actions.append(why);
    }
```

`desk/static/app.css` — section 4 statusbar: make the media column shrinkable so a long "下载中 …" cannot push the settings button past the viewport (F6):

```css
#statusbar{display:grid;grid-template-columns:max-content max-content minmax(0,max-content) minmax(96px,1fr) max-content;gap:16px;align-items:center;height:48px;padding:0 var(--margin);background:var(--panel);border-bottom:2px solid var(--border);overflow:hidden}
.status-media{min-width:0;overflow:hidden}
```

Section 6b: `.res-actions{align-items:center;flex-wrap:wrap}.res-disabled-reason{margin:0;color:var(--busy)}`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_resources_verify.py tests/test_resources_service.py tests/test_resources_downloader.py -q` and `node --test "tests/js/*.test.js"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desk/resources/verify.py desk/static/js/panes/resources.js desk/static/app.css tests/test_resources_verify.py tests/js/resources_pane.test.js
git commit -m "fix(recheck): partial percent counts in-flight bytes, disabled download shows reason, statusbar cannot overflow (F4 F5 F6)"
```

---

### Task 5: Music/video validation copy in Chinese (music caption thread, ST1)

**Files:**
- Modify: `desk/media/service.py:20-25,70-78`
- Modify: `desk/static/js/panes/music.js:20-24`
- Modify: `desk/static/index.html` (music caption label)
- Test: `tests/test_media_service.py`, `tests/js/media_panes.test.js`

**Interfaces:**
- Produces: `MediaError("caption_required", "请填写风格描述", 400)` and `MediaError("prompt_required", "请填写视频提示词", 400)`; other `_nonempty` failures unchanged.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_media_service.py`:

```python
def test_missing_caption_and_prompt_have_chinese_codes(tmp_path):
    service = make_service(tmp_path)[0]
    with pytest.raises(MediaError) as exc:
        service.start_music_job(caption="  ", lyrics="la", duration=10)
    assert (exc.value.code, exc.value.message, exc.value.http_status) == ("caption_required", "请填写风格描述", 400)
    with pytest.raises(MediaError) as exc:
        service.start_video_job(prompt="", width=512, height=288, frames=49, steps=16)
    assert (exc.value.code, exc.value.message) == ("prompt_required", "请填写视频提示词")
```

Check the existing parametrised invalid-params test around line 185 (`dict(caption="")`, `dict(caption=None)`): keep `caption=None` expecting `invalid_params`? No — update it so both `""` and `None` expect `caption_required`.

Append to `tests/js/media_panes.test.js`:

```js
test("音乐面板：风格描述留空时前端直接提示，不发请求", async () => {
  const music = pane({ "music-caption": "   ", "music-lyrics": "一二三", "music-duration": "10", "music-start": "" });
  createMusicPane(music, {});
  await withFetch([], async (calls) => { await music.parts["music-start"].click(); assert.equal(calls.length, 0); });
  assert.equal(music.parts["music-error"].textContent, "请填写风格描述");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_media_service.py -q -k "caption or prompt"` and `node --test tests/js/media_panes.test.js`
Expected: FAIL.

- [ ] **Step 3: Implement**

`desk/media/service.py`:

```python
def _nonempty(name: str, value: Any, *, code: str = "invalid_params", message: str | None = None) -> None:
    if not isinstance(value, str) or not value.strip():
        raise MediaError(code, message or f"{name} must be a non-empty string", 400)
```

In `start_video_job`: `_nonempty("prompt", prompt, code="prompt_required", message="请填写视频提示词")`.
In `start_music_job`: `_nonempty("caption", caption, code="caption_required", message="请填写风格描述")`.

`desk/static/js/panes/music.js` click handler:

```js
      if (!els.caption.value.trim()) throw new Error("请填写风格描述");
      if (!els.lyrics.value.trim()) throw new Error("请填写歌词：Music 3 需要歌词才能生成");
```

`desk/static/index.html` music label: `<label>风格描述（必填） <textarea data-music-caption required placeholder="例如：温柔的民谣，木吉他伴奏，女声轻唱，慢速"></textarea></label>`.

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_media_service.py tests/test_media_routes.py -q` and `node --test "tests/js/*.test.js"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desk/media/service.py desk/static/js/panes/music.js desk/static/index.html tests/test_media_service.py tests/js/media_panes.test.js
git commit -m "fix(recheck): caption/prompt required errors in Chinese with front-end precheck"
```

---

### Task 6: Chat pane — one-click model swap, no select revert, unload disabled when idle, evicted copy, history names, empty answers, loaded badge, duplicate quant (J16, N4, N6, F8, F9, F10, evicted thread)

**Files:**
- Modify: `desk/static/js/panes/chat.js`
- Modify: `desk/static/app.css` section 5
- Test: `tests/js/chat_pane.test.js`

**Interfaces:**
- Consumes: `panes.chat.setHeavyAllowed(allowed, reason)` now receives `allowed = true` when the only blocker is `llm_already_held` (Task 1 main.js change).
- Produces: `loadSelected()` — when a different model is resident, asks `confirmDialog({ title: "换模型", message: "将先卸载「A」，再加载「B」。", confirmLabel: "换模型", danger: false })`, then `unloadLlm()` → `loadLlm(B)`.
- Produces: `renderLlm(payload)` only writes `modelSelect.value` when the loaded key changes (tracked in `lastLoadedKey`); `unloadBtn.disabled = status in {idle, loading}`; error code `evicted` renders `已被媒体任务让出内存，可重新加载`.
- Produces: `showMessages(list, fallbackModelName = "")` — assistant rows use `message.model ?? fallbackModelName ?? "模型"`; empty content renders `<p class="empty-answer">（这条回答没有内容）</p>`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/js/chat_pane.test.js` (reuse `makePane`, `json`):

```js
test("换模型：A 驻留时选 B 点加载 → 确认 → 先卸载再加载（J16）", async () => {
  const oldFetch = globalThis.fetch; const calls = [];
  let loaded = "a";
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method ?? "GET", options.body]);
    if (path === "/api/resources/catalog") return json([{ key: "a", group: "chat", name: "模型 A", gb: 1 }, { key: "b", group: "chat", name: "模型 B", gb: 1 }]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [{ key: "a", state: "present" }, { key: "b", state: "present" }] });
    if (path === "/api/llm/status") return json(loaded ? { state: { status: "loaded", model_key: loaded }, loaded_model: { name: loaded === "a" ? "模型 A" : "模型 B" } } : { state: { status: "idle", model_key: null } });
    if (path === "/api/sessions") return json([{ id: "s1", title: "t", messages: [], updated: "2026-01-01" }]);
    if (path === "/api/memory") return json({ available_bytes: 99 * 1024 ** 3 });
    if (path === "/api/llm/unload") { loaded = null; return json({}); }
    if (path === "/api/llm/load") { loaded = JSON.parse(options.body).key; return json({}); }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { controls, root } = makePane();
    const pane = createChatPane(root, { confirm: async () => true });
    await pane.init();
    assert.equal(controls.get("[data-unload]").disabled, false);
    controls.get("[data-model-select]").value = "b";
    pane.applyLlmStatus({ state: { status: "loaded", model_key: "a" }, loaded_model: { name: "模型 A" } });
    assert.equal(controls.get("[data-model-select]").value, "b", "轮询不得把用户的选择改回 A");
    await controls.get("[data-load]").click();
    const order = calls.filter(([p]) => p === "/api/llm/unload" || p === "/api/llm/load").map(([p]) => p);
    assert.deepEqual(order, ["/api/llm/unload", "/api/llm/load"]);
    assert.equal(loaded, "b");
  } finally { globalThis.fetch = oldFetch; }
});

test("未加载时「卸载」禁用；被驱逐显示让出文案而非加载失败（N4）", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { controls, root } = makePane();
  const pane = createChatPane(root);
  pane.applyLlmStatus({ state: { status: "idle", model_key: null } });
  assert.equal(controls.get("[data-unload]").disabled, true);
  pane.applyLlmStatus({ state: { status: "error", model_key: "glm", error: { code: "evicted", message: "LLM 已被媒体任务驱逐" } } });
  assert.equal(controls.get("[data-model-state]").textContent, "已被媒体任务让出内存，可重新加载");
  assert.equal(controls.get("[data-unload]").disabled, false);
});

test("历史消息用会话模型名，空回答有占位（F8/F9）", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { controls, root } = makePane();
  const pane = createChatPane(root);
  pane.showMessages([{ role: "user", content: "hi" }, { role: "assistant", content: "" }], "GLM 4.7 Flash");
  const rows = controls.get("[data-messages]").children;
  const who = rows[1].children[0];
  assert.equal(who.children[1].textContent, "GLM 4.7 Flash");
  const body = rows[1].children[2];
  assert.equal(body.children[0].className, "empty-answer");
});
```

Note: `createChatPane(root, ctx = {})` gains an optional `ctx.confirm` for tests, mirroring video/music panes.

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL.

- [ ] **Step 3: Implement**

`desk/static/js/panes/chat.js` — apply these edits:

Signature: `export function createChatPane(root, ctx = {}) {` and add state `let lastLoadedKey = null; let llmStatus = "idle";`.

`refreshModels` option text — avoid repeating the quant when the name already contains it:

```js
      const marks = [entry.params, entry.name?.includes(entry.quant ?? " ") ? null : entry.quant, entry.vision ? "视觉" : null].filter(Boolean).join(" · ");
```

`renderLlm`:

```js
  function renderLlm(payload) {
    const state = payload.state;
    llmStatus = state.status;
    els.modelState.dataset.status = state.status;
    if (state.status === "idle") els.modelState.textContent = "未加载";
    else if (state.status === "loading") els.modelState.textContent = `加载中：${state.model_key ?? ""}`;
    else if (state.status === "loaded") {
      els.modelState.textContent = `已加载：${payload.loaded_model?.name ?? state.model_key}`;
      if (state.model_key && state.model_key !== lastLoadedKey) { els.modelSelect.value = state.model_key; lastLoadedKey = state.model_key; }
    } else if (state.error?.code === "evicted") {
      els.modelState.textContent = "已被媒体任务让出内存，可重新加载";
    } else {
      const tail = state.error?.log_tail ? `\n${state.error.log_tail}` : "";
      els.modelState.textContent = `加载失败（${state.error?.code ?? "?"}）：${state.error?.message ?? ""}${tail}`;
    }
    if (state.status !== "loaded") lastLoadedKey = state.status === "loading" ? lastLoadedKey : null;
    els.unloadBtn.disabled = state.status === "idle" || state.status === "loading";
    modelName = payload.loaded_model?.name ?? state.model_key ?? modelName;
  }
```

`loadSelected` (swap flow):

```js
  async function loadSelected() {
    setError("");
    const entry = catalog.find((item) => item.key === els.modelSelect.value);
    if (!entry) return;
    const confirm = ctx.confirm ?? ((options) => confirmDialog(doc, options));
    try {
      if (llmStatus === "loaded" && lastLoadedKey && lastLoadedKey !== entry.key) {
        const from = catalog.find((item) => item.key === lastLoadedKey)?.name ?? lastLoadedKey;
        const go = await confirm({ title: "换模型", message: `将先卸载「${from}」，再加载「${entry.name}」。`, confirmLabel: "换模型", danger: false });
        if (!go) return;
        await api.unloadLlm();
        renderLlm(await api.llmStatus());
      } else if (llmStatus === "loaded" && lastLoadedKey === entry.key) {
        return;
      }
      const snapshot = await api.memorySnapshot();
      const { warn, message } = needsWarning(Math.round(entry.gb * 1024 ** 3), snapshot);
      if (warn && !await confirm({ title: "内存警告", message, confirmLabel: "仍要加载", danger: false })) return;
      await api.loadLlm(entry.key);
      await pollUntilSettled();
    } catch (error) { setError(error.message); }
  }
```

`messageNode(message, live = false, fallbackName = "")` — name line and empty content:

```js
    name.textContent = message.model ?? fallbackName ?? (modelName || "模型");
    ...
    const contentEl = doc.createElement("div");
    contentEl.className = "md";
    if (!live && !(message.content ?? "").trim()) {
      const empty = doc.createElement("p"); empty.className = "empty-answer"; empty.textContent = "（这条回答没有内容）"; contentEl.append(empty);
    } else contentEl.append(renderMarkdown(doc, message.content ?? ""));
```

`showMessages(list, fallbackModelName = "")` passes the name: `for (const message of list) messageNode(message, false, fallbackModelName);` and `renderMessages()` calls `showMessages(current()?.messages ?? [], sessionModelName(current()))` with:

```js
  const sessionModelName = (session) => catalog.find((item) => item.key === session?.model)?.name ?? session?.model ?? "";
```

`setHeavyAllowed(allowed, reason)` unchanged (main.js now passes `allowed = true` for `llm_already_held`); keep the hint for other reasons.

`desk/static/app.css` section 5 — add:

```css
[data-model-state][data-status="loaded"]{color:var(--ok)}[data-model-state][data-status="error"]{color:var(--busy)}
.empty-answer{color:var(--muted);font-style:italic}
```

- [ ] **Step 4: Run tests**

Run: `node --test "tests/js/*.test.js"`
Expected: PASS (fix any existing chat test that asserted the old evicted/idle behaviour).

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/chat.js desk/static/app.css tests/js/chat_pane.test.js
git commit -m "fix(recheck): one-click model swap, stable select, unload disabled when idle, evicted copy, history names (J16 N4 N6 F8 F9 F10)"
```

---

### Task 7: Settings not-listening placeholder and library playing highlight (F15, F16)

**Files:**
- Modify: `desk/static/js/panes/settings.js:44-52`
- Modify: `desk/static/js/panes/library.js` (`rowNode`, `playOutput`)
- Modify: `desk/static/app.css` section 6b
- Test: `tests/js/settings_pane.test.js`, `tests/js/library_pane.test.js`

- [ ] **Step 1: Write the failing tests**

Append to `tests/js/settings_pane.test.js` (uses its `makePane`):

```js
test("未监听时地址区显示引导文案而不是空白（F15）", async () => {
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/config" && (options.method ?? "GET") === "GET") return new Response(JSON.stringify({ models_root: "/models" }), { status: 200 });
    return new Response(JSON.stringify({
      config: { enabled: false, host: "0.0.0.0", port: 8770 },
      status: { enabled: false, listening: false, host: "0.0.0.0", port: 8770, auth: "none", last_error: null },
    }), { status: 200 });
  };
  try {
    const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
    const { root, controls } = makePane();
    await createSettingsPane(root).init();
    const note = controls.get("[data-settings-lan-note]");
    assert.equal(note.hidden, false);
    assert.equal(note.textContent, "开启对外接口并「保存并应用」后，这里会显示可复制的地址。");
    assert.equal(controls.get("[data-settings-openai-url]").hidden, true);
  } finally { globalThis.fetch = oldFetch; }
});
```

Also relax the first settings test's `assert.match(lan-note, /局域网 IP/)` line: that payload is not listening, so the note is now the placeholder — change it to `assert.equal(controls.get("[data-settings-lan-note]").textContent, "开启对外接口并「保存并应用」后，这里会显示可复制的地址。")`.

In `tests/js/library_pane.test.js`, extend the first test right after `elements.list.children[1].click();`:

```js
  assert.match(elements.list.children[1].className, /\bplaying\b/);
  assert.doesNotMatch(elements.list.children[0].className, /\bplaying\b/);
  assert.equal(elements.player.children[1].textContent, "正在播放：海边");
```

(The row `className` is a plain string in the fake DOM; the implementation must toggle the class by string, not via `classList`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/settings_pane.test.js tests/js/library_pane.test.js`
Expected: FAIL.

- [ ] **Step 3: Implement**

`settings.js` `render()` — replace the hide loop tail:

```js
    const listening = Boolean(status.listening);
    for (const el of [els.authWarning, els.openaiUrl, els.anthropicUrl, els.copyOpenai, els.copyAnthropic]) if (el) el.hidden = !listening;
    els.authWarning.textContent = listening ? "当前为无鉴权监听：同一网络任何设备都能调用本机模型" : "";
    els.lanNote.hidden = false;
    els.lanNote.textContent = listening ? (urls.note ?? "") : "开启对外接口并「保存并应用」后，这里会显示可复制的地址。";
```

`library.js` — in `rowNode` record the playable name on the row (`li.outputName = playable?.name ?? null;` — a plain property, since the fake DOM has no `dataset`) and keep the row title; in `playOutput(output, title)`:

```js
  function playOutput(output, title = "") {
    for (const row of els.list.children ?? []) {
      const base = String(row.className ?? "").replace(/\s*\bplaying\b/, "");
      row.className = row.outputName === output.name ? `${base} playing` : base;
    }
    els.player.replaceChildren();
    const isVideo = output.kind === "video" || /\.(mp4|webm)$/i.test(output.name);
    const media = doc.createElement(isVideo ? "video" : "audio");
    media.controls = true; media.autoplay = true; media.src = api.serveOutput(output.name);
    const caption = doc.createElement("p");
    caption.className = "hint";
    caption.textContent = `正在播放：${title || output.name}`;
    els.player.append(media, caption);
    els.player.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }
```

and pass the row title from `rowNode`: `const rowTitle = entry ? summarize(entry).text : output.name;` → `playOutput(playable, rowTitle)` in both click handlers.

`app.css` 6b: `.lib-row.playing{border-color:var(--accent)}.lib-row.playing .lib-title::before{content:"▶ ";color:var(--accent)}`.

- [ ] **Step 4: Run tests**

Run: `node --test "tests/js/*.test.js"`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/settings.js desk/static/js/panes/library.js desk/static/app.css tests/js/settings_pane.test.js tests/js/library_pane.test.js
git commit -m "fix(recheck): settings not-listening placeholder, library playing row highlight (F15 F16)"
```

---

### Task 8: Menubar memory line refreshed every poll and on open (N1)

**Files:**
- Modify: `macos/DeskAPI.swift:12-16,47-58`
- Modify: `macos/ShellStatus.swift` (add `memoryMenuTitle`)
- Modify: `macos/StatusItemController.swift`
- Modify: `macos/StatusPoller.swift`, `macos/AppDelegate.swift:handlePoll`
- Modify: `macos/harness/ShellHarness.swift`
- Test: `tests/test_shell_status.py`

**Interfaces:**
- Produces: `struct MemoryLine { usedBytes, totalBytes, availableBytes: Int64 }`.
- Produces: `func memoryMenuTitle(used: Int64, total: Int64, available: Int64) -> String` → `"内存 已用 58.2 / 总 128.0 GiB（可用 69.8 GiB）"` (one decimal everywhere, same wording as the web statusbar).
- Produces: `StatusItemController.renderMemory(_ line: MemoryLine?)`; `StatusPoller.onMemory: ((Result<MemoryLine, DeskAPIError>) -> Void)?` invoked on every poll.
- Harness: `shellharness memory-line <used> <total> <available>` prints the title.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_shell_status.py`:

```python
@pytest.mark.parametrize("used,total,available,expected", [
    (62_461_775_872, 137_438_953_472, 74_977_177_600, "内存 已用 58.2 / 总 128.0 GiB（可用 69.8 GiB）"),
    (0, 137_438_953_472, 137_438_953_472, "内存 已用 0.0 / 总 128.0 GiB（可用 128.0 GiB）"),
])
def test_memory_menu_title_matches_web_wording(used, total, available, expected):
    proc = subprocess.run([harness_path(), "memory-line", str(used), str(total), str(available)],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_shell_status.py -q -k memory`
Expected: FAIL (`unknown subcommand memory-line`).

- [ ] **Step 3: Implement**

`macos/ShellStatus.swift` — append:

```swift
/// The sole formatter for the menubar memory row; wording mirrors the web statusbar (N1).
func memoryMenuTitle(used: Int64, total: Int64, available: Int64) -> String {
  let gib = 1_073_741_824.0
  return String(format: "内存 已用 %.1f / 总 %.1f GiB（可用 %.1f GiB）",
                Double(used) / gib, Double(total) / gib, Double(available) / gib)
}
```

`macos/harness/ShellHarness.swift` — add a case:

```swift
    case "memory-line":
      guard args.count >= 4, let used = Int64(args[1]), let total = Int64(args[2]), let available = Int64(args[3]) else { exit(64) }
      print(memoryMenuTitle(used: used, total: total, available: available))
```

`macos/DeskAPI.swift`:

```swift
struct MemoryLine {
  var usedBytes: Int64
  var totalBytes: Int64
  var availableBytes: Int64
}
// in memorySnapshot(): also read available_bytes
        guard let dictionary = object as? [String: Any],
              let total = (dictionary["total_bytes"] as? NSNumber)?.int64Value,
              let used = (dictionary["used_bytes"] as? NSNumber)?.int64Value,
              let available = (dictionary["available_bytes"] as? NSNumber)?.int64Value else {
          return .failure(DeskAPIError(code: "bad_shape", message: "memory snapshot is incomplete"))
        }
        return .success(MemoryLine(usedBytes: used, totalBytes: total, availableBytes: available))
```

`macos/StatusPoller.swift` — poll memory alongside desk state:

```swift
  var onMemory: ((Result<MemoryLine, DeskAPIError>) -> Void)?
  // inside pollOnce(), after the deskState request:
    api.memorySnapshot { [weak self] result in
      RunLoop.main.perform(inModes: [.common]) { self?.onMemory?(result) }
    }
```

`macos/StatusItemController.swift`:

```swift
  func renderMemory(_ result: Result<MemoryLine, DeskAPIError>) {
    switch result {
    case .success(let line):
      memoryItem.title = memoryMenuTitle(used: line.usedBytes, total: line.totalBytes, available: line.availableBytes)
    case .failure:
      memoryItem.title = "内存 不可读"
    }
  }

  /// Refreshes the memory row when the menu opens. Menu tracking runs the run loop in event-tracking
  /// mode, where `DispatchQueue.main.async` blocks do not fire until the menu closes; use common modes.
  func menuWillOpen(_ menu: NSMenu) {
    api.memorySnapshot { [weak self] result in
      RunLoop.main.perform(inModes: [.common, .eventTracking]) { self?.renderMemory(result) }
    }
    onMenuOpened?()
  }
```

(Delete the old `menuWillOpen` body that formatted inline.)

`macos/AppDelegate.swift` — after `poller.onUpdate = …` add `poller.onMemory = { [weak self] result in self?.statusController.renderMemory(result) }`.

- [ ] **Step 4: Run tests and build**

Run: `python3 -m pytest tests/test_shell_status.py -q` then `scripts/build-app.sh --output /tmp/lmd-build` (Developer ID; add `LMD_ALLOW_ADHOC=1 … --adhoc` only if the identity is absent).
Expected: PASS; build verify OK. Manual check: launch the built app with `LMD_SHELL_PORT=8776 LOCALMODELDESK_DATA_ROOT=<scratch>` , start a 10 s music job from the web UI, open the status-item menu during the job: the memory row must be within 1 GiB of the window statusbar and read `内存 已用 X / 总 Y GiB（可用 Z GiB）`.

- [ ] **Step 5: Commit**

```bash
git add macos/ShellStatus.swift macos/harness/ShellHarness.swift macos/DeskAPI.swift macos/StatusPoller.swift macos/StatusItemController.swift macos/AppDelegate.swift tests/test_shell_status.py
git commit -m "fix(recheck): menubar memory row refreshed each poll and on open with common run-loop modes (N1)"
```

---

### Task 9: Error page wording, danger accent, folded log path; dark appearance; first-run dialog path (N7, N8, N5, first-run thread)

**Files:**
- Modify: `macos/ShellStatus.swift:errorPageHTML`
- Modify: `macos/AppDelegate.swift:applicationDidFinishLaunching`
- Modify: `macos/FirstRunFlow.swift:15-17`
- Test: `tests/test_shell_window.py::test_error_page_is_dark_themed_and_names_the_reason`, `tests/test_shell_window.py::test_server_death_shows_error_text`

- [ ] **Step 1: Update the failing tests**

In `tests/test_shell_window.py` change the two assertions:

```python
    assert "<h1>服务未响应</h1>" in html and "服务无响应" in html
    assert 'class="danger"' in html and "<details>" in html and "/tmp/x.log" in html
```

and in `test_server_death_shows_error_text` accept the new title: `if "服务未响应" in tree or "意外退出" in tree:`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_shell_window.py -q -k error_page`
Expected: FAIL.

- [ ] **Step 3: Implement**

`macos/ShellStatus.swift` `errorPageHTML`:

```swift
  return """
  <!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>LocalModelDesk</title>
  <style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#14161a;color:#e7e9ee;font:14px/1.6 -apple-system,"PingFang SC",sans-serif}
  main{max-width:36em;padding:32px;background:#1d2026;border:1px solid #2c313a;border-left:4px solid #e5534b;border-radius:8px}
  h1{font-size:20px;margin:0 0 12px;color:#e5534b}h1::before{content:"✕ "}
  .danger{color:#e5534b}details{margin-top:12px;color:#9aa3b2;font-size:13px}summary{cursor:pointer}
  code{font:13px ui-monospace,Menlo,monospace;color:#9aa3b2;word-break:break-all}
  button{margin-top:16px;padding:8px 12px;border-radius:6px;border:1px solid #4f8cff;background:#4f8cff;color:#fff;font:inherit;cursor:pointer}</style></head>
  <body><main><h1 class="danger">服务未响应</h1><p id="reason">\(esc(reason))</p>
  <details><summary>详情</summary><p>日志：<code>\(esc(logPath))</code></p></details>
  <button onclick="window.webkit.messageHandlers.shellRetry.postMessage('retry')">重试</button></main></body></html>
  """
```

`macos/AppDelegate.swift` first line of `applicationDidFinishLaunching`, before `NSApp.setActivationPolicy(.regular)`:

```swift
    NSApp.appearance = NSAppearance(named: .darkAqua)   // D1 single dark theme: native chrome follows the web content
```

`macos/FirstRunFlow.swift:17`:

```swift
      alert.informativeText = "默认位置是「\(DeskPaths.userDataRoot.appendingPathComponent("models").path)」。"
```

- [ ] **Step 4: Run tests and build**

Run: `python3 -m pytest tests/test_shell_window.py tests/test_shell_status.py -q` then rebuild via `scripts/build-app.sh --output /tmp/lmd-build`.
Expected: PASS; the launched app shows a dark title bar and dark status-item menu; `kill -9` of the service shows the red-accented 「服务未响应」 page with the log path folded.

- [ ] **Step 5: Commit**

```bash
git add macos/ShellStatus.swift macos/AppDelegate.swift macos/FirstRunFlow.swift tests/test_shell_window.py
git commit -m "fix(recheck): error page wording/accent, forced dark appearance, first-run dialog shows real default path (N5 N7 N8)"
```

---

### Task 10: Regression, build, and re-acceptance

- [ ] **Step 1:** `python3 -m pytest -q` (all Python incl. shell harness), `node --test "tests/js/*.test.js"`, `python3 -m pytest tests/e2e -q` (Playwright; requires `tests/e2e/requirements.txt`).
- [ ] **Step 2:** `scripts/build-app.sh --output <scratch>/build` and `scripts/verify-app.sh <scratch>/build/LocalModelDesk.app --source-root "$PWD"` (Developer ID; `LMD_ALLOW_ADHOC=1` + `--adhoc` only if no identity).
- [ ] **Step 3:** Start a new cross-exam run `docs/cross-exam/<date>-localmodeldesk-recheck-2/`: copy `visual/` verbatim from `2026-09-07-localmodeldesk-fixes`, recompute `build.json`, launch the bundle isolated (`LMD_SHELL_PORT=8776 LOCALMODELDESK_DATA_ROOT=<scratch>/D`), re-run journey J16 and the three visual batches (idle, active incl. worker-kill error state, native by window id) with fresh-context probers, one Claude reviewer per environment, then `render_report.py`. Target: 0 high findings; J16 done.

---

## Self-Review

- **Spec coverage:** J16 → T6; F1/N2 → T1; F2 → T1; F3/F18 → T2; F4/F5/F6 → T4; F7/N3, F12, F13, F14, F19, F20, G1 duplicated log, shared job poll → T3; F8/F9/F10, N4, N6, evicted wording → T6; F11 → T1; F15/F16 → T7; N1 → T8; N5/N7/N8, first-run dialog path → T9; music caption English error → T5. Not fixed by design (recorded as decisions in `open_threads`): F17 (rule text vs reference image on card button alignment), first-run two-layer UI, `内存里：` item hidden during media jobs, form reset after retry.
- **Placeholder scan:** every test step contains the test code; every implementation step contains the code. No TBD/TODO.
- **Type consistency:** `renderState(..., names)`/`nextOk`/`nextIcon` (T1) used by `statusbar.js` (T1); `heavyAvailability().code` (T1) used by `main.js` (T1) and relied on by chat swap (T6); `describeJobError` (T2) used by `jobview.js` (T3) and `library.js` (T2); `createJobView(root, { mediaTag, kind })` and `apply(payload, { replaceLog })` (T3) used by `video.js`/`music.js`/`main.js` (T3); `MemoryLine.availableBytes`, `memoryMenuTitle`, `renderMemory`, `onMemory` (T8) consistent across DeskAPI/StatusPoller/StatusItemController/AppDelegate; `bytes_in_flight` (T4) only read by tests.
