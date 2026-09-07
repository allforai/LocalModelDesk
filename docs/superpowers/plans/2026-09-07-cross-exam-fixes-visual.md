# Cross-Exam Fix List B · 视觉基线落地 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the shipped UI match the visual/interaction baseline the user confirmed on 2026-09-07 (reviewer findings F1–F29 web, N1–N14 native), so a re-run of the frozen 51-case visual matrix passes.

**Architecture:** One stylesheet (`desk/static/app.css`, currently 13 minified lines) becomes a small token-driven system; panes keep their DOM-building style (`createElement`/`textContent`) but adopt shared class names; a pure Markdown renderer lands as an ES module; the menubar icon becomes a template `NSImage` drawn in code with state variants. Every task is verified by `node --test`, a static CSS/HTML assertion in `tests/test_ui_static.py`, or the shell harness.

**Tech Stack:** plain CSS (custom properties, grid/flex), ES modules (no build), `node:test`, AppKit (`NSImage` template drawing), pytest

**Spec:** `docs/cross-exam/2026-09-06-localmodeldesk/visual/visual-baseline.json`, `visual/interaction-baseline.json` (rules D/C/T/L/S/I/K/N/F/ST/M), reference mockups `visual/refs/ref-chat-1440.png`, `visual/refs/ref-resources-1440.png`, reviewer reports `evidence/vis-web/review-claude.json`, `evidence/vis-b3/review-claude.json`.

## Global Constraints

- Keep the existing dark tokens exactly: `--bg #14161a --panel #1d2026 --border #2c313a --text #e7e9ee --muted #9aa3b2 --accent #4f8cff --danger #e5534b --ok #3fb950 --busy #d29922` (rule C1).
- Buttons: three levels only — `.btn-primary` (accent fill, white text), default (panel + 1px border), `.btn-danger` (danger fill, white text); disabled = `opacity:.5; cursor:not-allowed` (C2/K1).
- Font stack applies to controls too (`button, input, select, textarea { font: inherit }`) (T1); sizes 13/14/16/20 (T2).
- 4 px spacing base; cards padding 16, gap 12; main area full width with 24 px margins (S1, L1 — user chose full width).
- No `innerHTML`; Markdown renderer must build nodes.
- Chat: ChatGPT-style (K2): centred column ≤ 820 px, user bubble right (`#2a2e36`, radius 18), assistant plain left with dot + model name, thinking as 「已思考 N 秒」 collapsed quote block.
- Semantic colours only for state (C3): ok green, busy yellow, danger red; raw codes never red on their own.
- Run `node --test tests/js` and `python3 -m pytest tests/test_ui_static.py tests/e2e -q` after each task; e2e selectors (`data-*` attributes) must keep working.
- Commit trailers as in Plan A.

## File Structure

| File | Responsibility |
|---|---|
| `desk/static/app.css` | rewritten as sections: tokens · base · buttons · layout · statusbar/tabs · chat · lists/cards · forms · dialogs/drawer · states |
| `desk/static/index.html` | class hooks, new wrappers, custom file pickers, empty-state elements |
| `desk/static/js/pure/markdown.js` (new) | `renderMarkdown(doc, text) -> DocumentFragment` |
| `desk/static/js/pure/job_progress.js` (new) | `parseStepProgress(logText) -> {step, total, pct} \| null` |
| `desk/static/js/panes/chat.js`, `resources.js`, `library.js`, `video.js`, `music.js`, `firstrun.js`, `settings.js`, `widgets/*.js` | class names + structural DOM changes per task |
| `macos/ShellStatus.swift`, `macos/StatusItemController.swift`, `macos/harness/ShellHarness.swift` | menu glyph state mapping + template icon |
| `tests/test_ui_static.py`, `tests/js/*.test.js` | assertions |

---

### Task 1: Tokens, base, and the three button levels (F1, F19, T1, N6)

**Files:**
- Rewrite: `desk/static/app.css` (sections 1–3)
- Modify: `desk/static/index.html` (add `btn-primary`/`btn-danger` classes), `desk/static/js/widgets/confirm.js:17`, `desk/static/js/panes/resources.js:74-78`, `desk/static/js/panes/chat.js:173-176`
- Test: `tests/test_ui_static.py`, `tests/js/resources_pane.test.js`

**Interfaces:**
- Produces: CSS classes `.btn-primary`, `.btn-danger`, `.btn-quiet` (tab-like, no border); global `button:disabled` style; `addIcon` untouched.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_ui_static.py (append)
CSS = (STATIC_ROOT / "app.css").read_text(encoding="utf-8")       # STATIC_ROOT already defined in this file
HTML = (STATIC_ROOT / "index.html").read_text(encoding="utf-8")


def test_css_defines_three_button_levels_and_disabled_state():
    assert ".btn-primary{" in CSS.replace(" ", "") and "background:var(--accent)" in CSS
    assert ".btn-danger{" in CSS.replace(" ", "") and "background:var(--danger)" in CSS
    assert "button:disabled" in CSS and "cursor:not-allowed" in CSS and "opacity:.5" in CSS
    assert "button,input,select,textarea{font:inherit" in CSS.replace(" ", "")


def test_primary_actions_carry_the_primary_class():
    for hook in ("data-session-new", "data-send", "data-video-start", "data-music-start", "data-settings-save", "data-fr-complete"):
        assert f"{hook} " in HTML and "btn-primary" in HTML.split(hook, 1)[1].split(">", 1)[0], hook
```

```js
// tests/js/resources_pane.test.js (append)
test("删除按钮带 btn-danger，下载带 btn-primary", async () => { /* same fetch stub as the row test */
  ... const buttons = li.children.at(-1).children;
  assert.equal(buttons.find((b) => b.textContent === "删除").className.includes("btn-danger"), true);
});
```

- [ ] **Step 2: Run to verify they fail** — `python3 -m pytest tests/test_ui_static.py -q -k button && node --test tests/js/resources_pane.test.js`

- [ ] **Step 3: Implement** — new `app.css` opening sections (replace lines 1–13 of the old file; later tasks append their sections):

```css
/* 1. tokens */
:root{color-scheme:dark;--bg:#14161a;--panel:#1d2026;--border:#2c313a;--text:#e7e9ee;--muted:#9aa3b2;--accent:#4f8cff;--danger:#e5534b;--ok:#3fb950;--busy:#d29922;--bubble:#2a2e36;--radius:6px;--radius-card:8px;--gap:8px;--pad:16px;--margin:24px}
/* 2. base */
[hidden]{display:none !important}
*{box-sizing:border-box}
body{margin:0;min-height:100vh;background:var(--bg);color:var(--text);font:14px/1.5 -apple-system,"PingFang SC",sans-serif}
button,input,select,textarea{font:inherit;color:inherit;background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:8px 12px}
input:focus,select:focus,textarea:focus{outline:none;border-color:var(--accent)}
textarea{width:100%;min-height:72px;resize:vertical}
h1{font-size:20px;margin:0 0 12px}h2{font-size:20px;margin:0 0 12px}h3{font-size:16px;margin:0 0 8px}
.hint{color:var(--muted);font-size:13px}
.inline-error{color:var(--danger);white-space:pre-wrap}.inline-error:empty{display:none}
.icon{width:16px;height:16px;flex:none;fill:none;stroke:currentColor;stroke-width:1.5;stroke-linecap:round;stroke-linejoin:round;pointer-events:none}
.with-icon{display:inline-flex;align-items:center;justify-content:center;gap:6px}.with-icon>.icon{order:-1}
/* 3. buttons: exactly three levels */
button{cursor:pointer;line-height:1.2}
button:hover{border-color:var(--muted)}
.btn-primary{background:var(--accent);border-color:var(--accent);color:#fff}
.btn-primary:hover{filter:brightness(1.08);border-color:var(--accent)}
.btn-danger{background:var(--danger);border-color:var(--danger);color:#fff}
.btn-quiet{background:transparent;border-color:transparent;color:var(--muted)}
button:disabled,button[aria-disabled="true"]{opacity:.5;cursor:not-allowed;filter:none}
```

`index.html`: add `class="btn-primary"` to `[data-session-new]`, `[data-send]`, `[data-video-start]`, `[data-music-start]`, `[data-settings-save]`, `[data-fr-complete]`, `[data-fr-adopt]`. `confirm.js:17`: `okBtn.className = confirmLabel === "取消" ? "" : "btn-danger";` — better: accept `danger = true` option; callers for 内存警告 pass `danger:false` → `btn-primary`. `resources.js:74`: `button.className = action === "delete" ? "btn-danger" : action === "download" || action === "resume" ? "btn-primary" : "";`. `chat.js:173`: `remove.className = "btn-danger btn-sm";` (`.btn-sm{padding:4px 8px;font-size:13px}` appended to section 3).

- [ ] **Step 4: Run** — `python3 -m pytest tests/test_ui_static.py -q && node --test tests/js`

- [ ] **Step 5: Commit**

```bash
git add desk/static/app.css desk/static/index.html desk/static/js/widgets/confirm.js desk/static/js/panes/resources.js desk/static/js/panes/chat.js tests/test_ui_static.py tests/js/resources_pane.test.js
git commit -m "style: tokens, control font, and three-level buttons with real disabled state (F1 F19 N6)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 2: Tabs with an indicator line; status bar with labelled chips and download state (F13, F14, N11, N13, D3)

**Files:**
- Modify: `desk/static/app.css` (section 4), `desk/static/index.html:10-11`
- Modify: `desk/static/js/pure/desk_state.js:26-50`, `desk/static/js/widgets/statusbar.js`, `desk/static/js/main.js:80-88`
- Test: `tests/js/desk_state.test.js`

**Interfaces:**
- Produces: `renderState(deskState, snapshot, download = null)` → `{memText, holderText, mediaText, nextText, tone}` where `holderText` is `内存里：无` / `内存里：<label>`; `mediaText` is `媒体：空闲` / `媒体：生成中` / `媒体：空闲 · 下载中 <key>` when `download?.state === "running"`; `tone` becomes `"busy"` while downloading.

- [ ] **Step 1: Write the failing test**

```js
// tests/js/desk_state.test.js (append)
test("状态条四格带字段名，下载中并入媒体格并转为 busy", () => {
  const idle = renderState({ holder: null, media_busy: false, can_start: { llm: { ok: true } } }, null, { state: "running", key: "gemma" });
  assert.equal(idle.holderText, "内存里：无");
  assert.equal(idle.mediaText, "媒体：空闲 · 下载中 gemma");
  assert.equal(idle.tone, "busy");
  const held = renderState({ holder: { kind: "llm", label: "glm" }, media_busy: false, can_start: { llm: { ok: false, reason: { code: "llm_already_held" } }, media: { ok: true } } }, null);
  assert.equal(held.holderText, "内存里：glm");
  assert.equal(held.nextText, "可开下一件重活");
});
```

(Note the last assertion: while an LLM is held, `nextText` must follow `can_start.media` — the next heavy thing that could start — not `can_start.llm`.)

- [ ] **Step 2: Run to verify it fails** — `node --test tests/js/desk_state.test.js`

- [ ] **Step 3: Implement**

```js
export function renderState(deskState, snapshot, download = null) {
  ...memText unchanged (GiB from Plan A)...
  const holder = deskState?.holder ?? null;
  let holderText = "内存里：无";
  if (holder) holderText = holder.kind === "llm" ? `内存里：${holder.label}` : holder.kind === "video" ? "视频生成中" : holder.kind === "music" ? "音乐生成中" : `${holder.kind}：${holder.label}`;
  const downloading = download?.state === "running" ? download.key : null;
  const mediaText = `${deskState?.media_busy ? "媒体：生成中" : "媒体：空闲"}${downloading ? ` · 下载中 ${downloading}` : ""}`;
  const nextKind = deskState?.media_busy || holder?.kind === "llm" ? "media" : "llm";
  const can = decisionFor(deskState, nextKind);
  ...nextText as before...
  const tone = deskState?.media_busy || downloading ? "busy" : holder ? "ok" : ok ? "ok" : "error";
  return { memText, holderText, mediaText, nextText, tone };
}
```

`statusbar.js` `update(deskState, snapshot, download)` passes the third argument; `main.js` `tick()` keeps the last `download` from `panes.resources.refresh()` (make `refresh()` return `downloadProgress`) and calls `statusbar.update(deskState, memory, download)`.

CSS section 4:

```css
/* 4. statusbar + tabs */
#statusbar{display:grid;grid-template-columns:max-content max-content max-content minmax(120px,1fr) max-content;gap:16px;align-items:center;height:48px;padding:0 var(--margin);background:var(--panel);border-bottom:2px solid var(--border)}
#statusbar[data-tone="ok"]{border-color:var(--ok)}#statusbar[data-tone="busy"]{border-color:var(--busy)}#statusbar[data-offline="1"],#statusbar[data-tone="error"]{border-color:var(--danger)}
.status-part{display:inline-flex;align-items:center;gap:6px;min-width:0;color:var(--muted);white-space:nowrap}
.status-part>span{overflow:hidden;text-overflow:ellipsis;color:var(--text)}
.status-holder>span{padding:2px 8px;border:1px solid var(--border);border-radius:999px;background:var(--bg)}
.status-next{color:var(--ok)}.status-next>span{color:inherit}
#statusbar[data-tone="busy"] .status-next{color:var(--busy)}#statusbar[data-offline="1"] .status-next,#statusbar[data-tone="error"] .status-next{color:var(--danger)}
#tabs{display:flex;gap:4px;padding:0 var(--margin);border-bottom:1px solid var(--border)}
#tabs button{min-width:78px;background:transparent;border:0;border-bottom:2px solid transparent;border-radius:0;color:var(--muted);padding:10px 12px}
#tabs button:hover{color:var(--text)}#tabs button.active{color:var(--accent);border-bottom-color:var(--accent)}
@media (max-width:800px){#statusbar{grid-template-columns:max-content minmax(100px,1fr) max-content;gap:10px}.status-holder,.status-media{display:none}}
```

- [ ] **Step 4: Run** — `node --test tests/js && python3 -m pytest tests/e2e/test_statusbar_memory.py tests/e2e/test_mutex_ui.py -q`

- [ ] **Step 5: Commit**

```bash
git add desk/static/app.css desk/static/index.html desk/static/js/pure/desk_state.js desk/static/js/widgets/statusbar.js desk/static/js/main.js desk/static/js/panes/resources.js tests/js/desk_state.test.js
git commit -m "style: tab indicator line; status bar chips with labels, download state, whole-line colour (F13 F14 N11 N13)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 3: Markdown renderer (pure, node-building) (G14, T3)

**Files:**
- Create: `desk/static/js/pure/markdown.js`
- Test: `tests/js/markdown.test.js`

**Interfaces:**
- Produces: `renderMarkdown(doc, text) -> DocumentFragment` supporting: `#`/`##`/`###` headings, paragraphs, `**bold**`, `` `code` ``, fenced ``` code blocks, `-`/`*` bullet lists, `1.` numbered lists, line breaks inside paragraphs. Anything else stays literal text. No HTML passthrough.

- [ ] **Step 1: Write the failing test**

```js
import test from "node:test"; import assert from "node:assert/strict";
import { renderMarkdown } from "../../desk/static/js/pure/markdown.js";
class Node { constructor(tag) { this.tagName = tag; this.children = []; this.textContent = ""; this.className = ""; } append(...n) { for (const c of n) this.children.push(typeof c === "string" ? { tagName: "#text", textContent: c } : c); } }
const doc = { createElement: (t) => new Node(t), createDocumentFragment: () => new Node("#fragment"), createTextNode: (t) => ({ tagName: "#text", textContent: t }) };
const flat = (n) => n.tagName === "#text" ? n.textContent : `<${n.tagName}>${n.children.map(flat).join("")}</${n.tagName}>`;

test("标题、粗体、行内代码、围栏代码、列表都变成节点，HTML 原样当文本", () => {
  const frag = renderMarkdown(doc, "# 标题\n\n我是**通义千问**，用 `x`。\n\n```py\nprint(1)\n```\n\n- a\n- b\n\n<b>no</b>");
  assert.equal(frag.children.map(flat).join(""),
    "<h3>标题</h3><p>我是<strong>通义千问</strong>，用 <code>x</code>。</p><pre><code>print(1)\n</code></pre><ul><li>a</li><li>b</li></ul><p>&lt;b&gt;no&lt;/b&gt;</p>".replaceAll("&lt;", "<").replaceAll("&gt;", ">"));
});
```

- [ ] **Step 2: Run to verify it fails** — `node --test tests/js/markdown.test.js`

- [ ] **Step 3: Implement**

```js
// 极小 Markdown → DOM 节点（不经 innerHTML）。只覆盖模型回复常见语法；其余按纯文本。
function inline(doc, text) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(doc.createTextNode(text.slice(last, m.index)));
    const tok = m[0];
    if (tok.startsWith("**")) { const b = doc.createElement("strong"); b.textContent = tok.slice(2, -2); out.push(b); }
    else { const c = doc.createElement("code"); c.textContent = tok.slice(1, -1); out.push(c); }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(doc.createTextNode(text.slice(last)));
  return out;
}

export function renderMarkdown(doc, text) {
  const frag = doc.createDocumentFragment();
  const lines = String(text ?? "").replace(/\r\n?/g, "\n").split("\n");
  let i = 0;
  const para = [];
  const flushPara = () => { if (!para.length) return; const p = doc.createElement("p"); para.forEach((l, idx) => { if (idx) p.append(doc.createElement("br")); p.append(...inline(doc, l)); }); frag.append(p); para.length = 0; };
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) { flushPara(); const buf = []; i += 1; while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]); i += 1;
      const pre = doc.createElement("pre"); const code = doc.createElement("code"); code.textContent = buf.join("\n") + "\n"; pre.append(code); frag.append(pre); continue; }
    const h = /^(#{1,3})\s+(.*)$/.exec(line);
    if (h) { flushPara(); const el = doc.createElement(h[1].length === 1 ? "h3" : "h4"); el.append(...inline(doc, h[2])); frag.append(el); i += 1; continue; }
    const li = /^\s*(?:[-*]|\d+\.)\s+(.*)$/.exec(line);
    if (li) { flushPara(); const ordered = /^\s*\d+\./.test(line); const list = doc.createElement(ordered ? "ol" : "ul");
      while (i < lines.length && /^\s*(?:[-*]|\d+\.)\s+/.test(lines[i])) { const item = doc.createElement("li"); item.append(...inline(doc, lines[i].replace(/^\s*(?:[-*]|\d+\.)\s+/, ""))); list.append(item); i += 1; }
      frag.append(list); continue; }
    if (line.trim() === "") { flushPara(); i += 1; continue; }
    para.push(line); i += 1;
  }
  flushPara();
  return frag;
}
```

(The test's expected string treats `<b>no</b>` as a literal text node — it is, because the renderer only ever calls `createTextNode`.)

- [ ] **Step 4: Run** — `node --test tests/js/markdown.test.js`

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/pure/markdown.js tests/js/markdown.test.js
git commit -m "feat(ui): minimal node-building Markdown renderer for model replies (G14)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 4: ChatGPT-style conversation column (F7, F29, G10, K2)

**Files:**
- Modify: `desk/static/js/panes/chat.js:98-125,190-234`, `desk/static/index.html:13`, `desk/static/app.css` (section 5)
- Test: `tests/js/chat_pane.test.js`

**Interfaces:**
- Produces: message DOM: `div.msg.msg-user > div.bubble` (right); `div.msg.msg-assistant > div.who (span.dot + span.name) + details.thinking (summary "已思考 N 秒" | "思考中…") + div.md` (Markdown); `messageNode(message, {live, modelName})`; streaming sets `sendBtn` label to 「生成中…」 and `data-streaming="1"` on the messages container.

- [ ] **Step 1: Write the failing test**

```js
// tests/js/chat_pane.test.js (append)
test("消息按角色分结构：用户气泡、助手带模型名与已思考折叠", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  controls.set("[data-load-hint]", new Element()); root.querySelector = (s) => controls.get(s);
  const pane = createChatPane(root);
  pane.applyLlmStatus({ state: { status: "loaded", model_key: "glm" }, loaded_model: { name: "GLM 4.7" } });
  pane.showMessages([{ role: "user", content: "你好" }, { role: "assistant", content: "**hi**", reasoning: "想一想", thinking_s: 3 }]);
  const [user, ai] = controls.get("[data-messages]").children;
  assert.equal(user.className, "msg msg-user"); assert.equal(user.children[0].className, "bubble");
  assert.equal(ai.className, "msg msg-assistant");
  assert.equal(ai.children[0].children[1].textContent, "GLM 4.7");
  assert.equal(ai.children[1].children[0].textContent, "已思考 3 秒");
  assert.equal(ai.children[2].children[0].children[0].tagName, "strong");
});
```

(`showMessages(list)` is a new public helper that renders a list into the container — it lets tests avoid session fetches.)

- [ ] **Step 2: Run to verify it fails** — `node --test tests/js/chat_pane.test.js`

- [ ] **Step 3: Implement**

`chat.js`:

```js
import { renderMarkdown } from "../pure/markdown.js";
  let modelName = "";
  function renderLlm(payload) { ...existing...; modelName = payload.loaded_model?.name ?? payload.state?.model_key ?? modelName; }

  function messageNode(message, live = false) {
    const wrap = doc.createElement("div");
    wrap.className = `msg msg-${message.role}`;
    if (message.role === "user") {
      const bubble = doc.createElement("div"); bubble.className = "bubble"; bubble.textContent = message.content ?? "";
      wrap.append(bubble); els.messages.append(wrap); return { wrap };
    }
    const who = doc.createElement("div"); who.className = "who";
    const dot = doc.createElement("span"); dot.className = "dot";
    const name = doc.createElement("span"); name.textContent = message.model ?? modelName || "模型";
    who.append(dot, name);
    const details = doc.createElement("details"); details.className = "thinking";
    const summary = doc.createElement("summary");
    summary.textContent = live ? "思考中…" : message.thinking_s ? `已思考 ${Math.round(message.thinking_s)} 秒` : "思考过程";
    const reasoningEl = doc.createElement("p"); reasoningEl.textContent = message.reasoning ?? "";
    details.append(summary, reasoningEl);
    const contentEl = doc.createElement("div"); contentEl.className = "md";
    contentEl.append(renderMarkdown(doc, message.content ?? ""));
    const errorEl = doc.createElement("p"); errorEl.className = "inline-error";
    wrap.append(who, details, contentEl, errorEl);
    details.hidden = !message.reasoning && !live; details.open = live;
    els.messages.append(wrap); els.messages.scrollTop = els.messages.scrollHeight;
    return { wrap, details, summary, reasoningEl, contentEl, errorEl };
  }
  function showMessages(list) { els.messages.replaceChildren(); for (const m of list) messageNode(m); }
  function renderMessages() { showMessages(current()?.messages ?? []); }
```

In `send()`: during streaming set `els.sendBtn.textContent = "生成中…"` (restore 「发送」 in `finally`), track `const thinkStart = Date.now()`; on each chunk render `live.contentEl.replaceChildren(renderMarkdown(doc, state.content))` (throttle: only when `state.content` changed since last render); when the first content char arrives set `live.summary.textContent = \`已思考 ${Math.round((Date.now() - thinkStart) / 1000)} 秒\`` and `live.details.open = false`; persist `thinking_s` on the assistant message. Export `showMessages` in the returned object.

CSS section 5:

```css
/* 5. chat (ChatGPT-style) */
#pane-chat{display:flex;gap:var(--margin)}
.sessions{width:240px;flex:none}
.chat-main{flex:1;display:flex;flex-direction:column;min-width:0}
.model-row{display:flex;gap:var(--gap);align-items:center;flex-wrap:wrap}
.messages{flex:1;min-height:300px;overflow:auto;display:flex;flex-direction:column;gap:32px;max-width:820px;width:100%;margin:0 auto;padding:16px 4px}
.msg-user{align-self:flex-end;max-width:70%}.msg-user .bubble{background:var(--bubble);border-radius:18px;padding:10px 16px;line-height:1.6;white-space:pre-wrap}
.msg-assistant{align-self:flex-start;max-width:100%;line-height:1.7}
.who{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--muted);margin-bottom:10px}.who .dot{width:20px;height:20px;border-radius:50%;background:var(--accent)}
.thinking{margin:0 0 12px;color:var(--muted);font-size:13px}.thinking summary{cursor:pointer;list-style:none;display:inline-flex;gap:6px}.thinking summary::before{content:"▸";font-size:11px}.thinking[open] summary::before{content:"▾"}
.thinking p{margin:8px 0 0 10px;padding-left:12px;border-left:2px solid var(--border);white-space:pre-wrap}
.md p{margin:0 0 12px}.md h3{font-size:16px;margin:12px 0 6px}.md h4{font-size:14px;margin:10px 0 4px}.md pre{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius);padding:12px;overflow:auto}.md code{font:13px ui-monospace,Menlo,monospace}.md ul,.md ol{margin:0 0 12px 20px}
.composer{display:flex;gap:var(--gap);align-items:flex-end;max-width:820px;width:100%;margin:0 auto}
.composer textarea{flex:1;background:var(--panel);border-radius:16px;padding:12px 16px}
.messages[data-streaming="1"]~.composer textarea{opacity:.7}
```

`index.html`: no structural change beyond Plan A's hint span; ensure `<div class="messages" data-messages>` and `<div class="composer">` remain.

- [ ] **Step 4: Run** — `node --test tests/js/chat_pane.test.js && python3 -m pytest tests/e2e/test_chat_stream.py -q`

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/chat.js desk/static/app.css desk/static/index.html tests/js/chat_pane.test.js
git commit -m "style(chat): ChatGPT-style column — user bubbles, model-named answers, thinking quote block, streaming indicator (F7 F29 G10)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 5: Session list as cards with hover actions and a selected state (F4, N3)

**Files:**
- Modify: `desk/static/js/panes/chat.js:156-188`, `desk/static/app.css` (section 6a)
- Test: `tests/js/chat_pane.test.js`

- [ ] **Step 1: Write the failing test**

```js
test("会话卡片：标题行、元信息行、动作区，当前项 active", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane(); controls.set("[data-load-hint]", new Element()); root.querySelector = (s) => controls.get(s);
  const previous = globalThis.fetch;
  globalThis.fetch = async (path) => json(path === "/api/sessions" ? [{ id: "s1", title: "第一会话", model: "glm", messages: [], updated: "2026-09-07T10:05:00" }] : path.includes("catalog") ? [] : path.includes("status") ? { models: [] } : { state: { status: "idle" } });
  try {
    const pane = createChatPane(root); await pane.init();
    const li = controls.get("[data-session-list]").children[0];
    assert.equal(li.className.trim(), "card session active");
    assert.equal(li.children[0].className, "session-title");
    assert.equal(li.children[1].className, "session-meta"); assert.equal(li.children[1].textContent, "glm · 10:05");
    assert.equal(li.children[2].className, "session-actions");
  } finally { globalThis.fetch = previous; }
});
```

- [ ] **Step 2: Run to verify it fails** — `node --test tests/js/chat_pane.test.js`

- [ ] **Step 3: Implement**

```js
  function renderSessionList() {
    els.sessionList.replaceChildren();
    for (const session of sessions) {
      const li = doc.createElement("li");
      li.className = "card session";
      li.classList.toggle("active", session.id === currentId);
      const title = doc.createElement("div"); title.className = "session-title"; title.textContent = displayTitle(session);
      const meta = doc.createElement("div"); meta.className = "session-meta";
      meta.textContent = [session.model, formatTimestamp(session.updated).slice(11)].filter(Boolean).join(" · ");
      const actions = doc.createElement("div"); actions.className = "session-actions";
      ...rename/remove buttons as before, appended to actions; remove gets class "btn-danger btn-sm", rename "btn-sm"...
      li.addEventListener("click", () => { currentId = session.id; renderSessionList(); renderMessages(); });
      li.append(title, meta, actions);
      els.sessionList.append(li);
    }
  }
```

(import `formatTimestamp` from `../pure/format.js`; `beginRename` keeps replacing `li` children with the input.) The test's `Element.classList.toggle` appends ` active`, hence `.trim()`.

CSS section 6a:

```css
/* 6a. cards + session list */
.card{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius-card);padding:12px}
.sessions ul,[data-res-list],[data-lib-list]{list-style:none;padding:0;margin:0;display:flex;flex-direction:column;gap:12px}
.session{cursor:pointer;position:relative}.session.active{border-color:var(--accent)}
.session-title{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.session-meta{font-size:13px;color:var(--muted);margin-top:4px}
.session-actions{display:none;position:absolute;right:8px;top:8px;gap:6px}
.session:hover .session-actions,.session:focus-within .session-actions{display:flex}
```

Because `main > section` still paints `--panel`, give the chat pane the page background so cards read as cards: `main>section{background:var(--bg)}` (added in Task 6 with layout).

- [ ] **Step 4: Run** — `node --test tests/js/chat_pane.test.js && python3 -m pytest tests/e2e/test_sessions.py -q`

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/chat.js desk/static/app.css tests/js/chat_pane.test.js
git commit -m "style(chat): session cards with meta, hover actions and selected state (F4 N3)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 6: Layout shell (full-width, margins) and resource / library cards with coloured badges (F4, F5, F17, K3, K6)

**Files:**
- Modify: `desk/static/app.css` (sections 6b/7), `desk/static/js/panes/resources.js:48-104`, `desk/static/js/panes/library.js:63-122`, `desk/static/index.html:31-32`
- Test: `tests/js/resources_pane.test.js`, `tests/js/library_pane.test.js`, `tests/test_ui_static.py`

**Interfaces:**
- Produces: resources row DOM `li.card.res-row[data-model] > div.res-head (h4.res-name + span.badge.badge-{ok|busy|none|unknown}) + p.res-meta + progress.res-progress? + details.res-missing? + div.res-actions`; library row `li.card.lib-row > div (p.lib-title, p.lib-meta, div.inline-error?) + div.lib-actions`.

- [ ] **Step 1: Write the failing tests**

```js
// resources_pane.test.js (append to the row test)
    assert.equal(li.className, "card res-row");
    assert.equal(li.children[0].children[1].className, "badge badge-ok");
// and a partial fixture: state:"partial", percent:37 → className "badge badge-busy" and a progress child with className "res-progress"
```

```python
# tests/test_ui_static.py (append)
def test_layout_is_full_width_with_24px_margins_and_cards():
    assert "main>section{" in CSS.replace(" ", "") and "padding:var(--margin)" in CSS
    assert ".badge-ok{" in CSS.replace(" ", "") and ".badge-busy{" in CSS.replace(" ", "") and ".badge-none{" in CSS.replace(" ", "")
```

- [ ] **Step 2: Run to verify they fail**

- [ ] **Step 3: Implement**

`resources.js rowNode` (replace lines 49-70):

```js
    const li = doc.createElement("li");
    li.className = "card res-row";
    (li.dataset ??= {}).model = entry.key;
    const head = doc.createElement("div"); head.className = "res-head";
    const name = doc.createElement("h4"); name.className = "res-name"; name.textContent = entry.name;
    const badge = doc.createElement("span");
    badge.className = `badge badge-${view.badgeKind}`; badge.textContent = view.badge;
    head.append(name, badge);
    const meta = doc.createElement("p"); meta.className = "res-meta";
    meta.textContent = `${entry.group === "chat" ? "聊天" : entry.group === "video" ? "视频" : "音乐"} · 目录 ${view.sizeText} · 占用 ${view.diskText}`;
    li.append(head, meta);
    if (view.pct > 0 && view.pct < 100) { const progress = doc.createElement("progress"); progress.className = "res-progress"; progress.value = view.pct; progress.max = 100; li.append(progress); }
```

`pure/model_status.js`: add `badgeKind: status.state === "present" ? "ok" : status.state === "partial" ? "busy" : status.state === "missing" ? "none" : "unknown"` to the returned view.

`library.js rowNode`: `li.className = "card lib-row"`, `title.className = "lib-title"`, actions container `actions.className = "lib-actions"`; the failed row's error goes through `describeJobError` (Plan A Task 13): `const [code, ...rest] = entry.error.split(": "); const { title } = describeJobError({ code, message: rest.join(": ") }); error.textContent = title;`.

CSS sections 6b/7:

```css
/* 6b. layout */
main>section{min-height:calc(100vh - 48px - 42px);padding:var(--margin);background:var(--bg)}
.res-head,.lib-head{display:flex;align-items:center;gap:8px}
.res-name{margin:0;font-size:16px;font-weight:600}
.res-meta,.lib-meta{color:var(--muted);font-size:13px;margin:4px 0 0}
.res-actions,.lib-actions{display:flex;gap:8px;margin-top:12px}
.res-progress{width:100%;height:6px;margin-top:8px;accent-color:var(--busy)}
.res-missing{margin-top:8px;color:var(--muted);font-size:13px}
/* 7. badges */
.badge{font-size:13px;padding:2px 8px;border-radius:999px}
.badge-ok{background:rgba(63,185,80,.15);color:var(--ok)}
.badge-busy{background:rgba(210,153,34,.15);color:var(--busy)}
.badge-none{background:rgba(154,163,178,.15);color:var(--muted)}
.badge-unknown{background:rgba(229,83,75,.15);color:var(--danger)}
```

- [ ] **Step 4: Run** — `node --test tests/js && python3 -m pytest tests/test_ui_static.py tests/e2e/test_resources_panel.py tests/e2e/test_library_panel.py -q`

- [ ] **Step 5: Commit**

```bash
git add desk/static/app.css desk/static/js/panes/resources.js desk/static/js/panes/library.js desk/static/js/pure/model_status.js desk/static/index.html tests/js tests/test_ui_static.py
git commit -m "style: full-width layout, card rows for resources and library, colour-coded badges (F4 F5 F17)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 7: Video/music two-column layout, step progress bar, custom file picker (F9, F20, F28, G26)

**Files:**
- Modify: `desk/static/index.html:14-30`, `desk/static/app.css` (section 8), `desk/static/js/panes/video.js:27-51`, `desk/static/js/widgets/jobview.js`
- Create: `desk/static/js/pure/job_progress.js`
- Test: `tests/js/job_progress.test.js`, `tests/js/media_panes.test.js`

**Interfaces:**
- Produces: `parseStepProgress(logText) -> {step, total, pct} | null` (last `step N/M` occurrence); job view renders `<progress data-job-progress>` while running when parse succeeds; file pickers become `<label class="file-pick"><span class="btn">选择图片</span><input type=file hidden …></label><span class="file-name" data-video-first-name>未选择文件</span>`.

- [ ] **Step 1: Write the failing tests**

```js
// tests/js/job_progress.test.js
import test from "node:test"; import assert from "node:assert/strict";
import { parseStepProgress } from "../../desk/static/js/pure/job_progress.js";
test("从日志里取最后一个 step N/M", () => {
  assert.deepEqual(parseStepProgress("start\nstep 1/16 12.2s\nstep 5/16 4.1s\n"), { step: 5, total: 16, pct: 31 });
  assert.equal(parseStepProgress("text encoder\n"), null);
});
// media_panes.test.js (append)
test("running 时按日志渲染进度条；选择文件后显示文件名", async () => {
  const video = pane({ "video-prompt": "", "video-size": "512x288", "video-frames": "49", "video-steps": "16", "video-start": "", "video-first-name": "" });
  video.parts["job-progress"] = new Element();
  const p = createVideoPane(video, {});
  p.jobView.apply({ job_id: 1, status: "running", log: "step 8/16 3s\n" });
  assert.equal(video.parts["job-progress"].value, 50); assert.equal(video.parts["job-progress"].hidden, false);
});
```

- [ ] **Step 2: Run to verify they fail**

- [ ] **Step 3: Implement**

```js
// pure/job_progress.js
export function parseStepProgress(logText) {
  const all = [...String(logText ?? "").matchAll(/step\s+(\d+)\s*\/\s*(\d+)/g)];
  if (!all.length) return null;
  const [, s, t] = all.at(-1); const step = Number(s), total = Number(t);
  return total > 0 ? { step, total, pct: Math.round(step / total * 100) } : null;
}
```

`jobview.js`: keep an accumulated `logText`; in `apply`, after appending log: `const prog = parseStepProgress(logText); if (els.progress) { els.progress.hidden = !(payload.status === "running" && prog); if (prog) els.progress.value = prog.pct; }`; add `progress: root.querySelector("[data-job-progress]")` to `els`. `index.html` job blocks: `<div class="job card"><p data-job-status>空闲</p><progress data-job-progress max="100" hidden></progress><button data-job-cancel data-icon-name="x" hidden>取消</button><details class="job-log"><summary>日志</summary><pre data-job-log></pre></details><div class="inline-error" data-job-error></div><div data-job-player></div></div>` (log collapsed by default, F20 "日志折叠区"; open it automatically on error in `apply`).

File pickers in `index.html`:

```html
<div class="file-row"><label class="file-pick"><span class="btn">选择首帧图片</span><input type="file" data-video-first accept="image/png,image/jpeg,image/webp" hidden></label><span class="file-name hint" data-video-first-name>未选择文件</span></div>
```

(same for last frame `data-video-last-name` and reference `data-video-source-name`); `video.js` change handler sets `root.querySelector(\`[data-video-${name}-name]\`).textContent = file ? file.name : "未选择文件"`.

CSS section 8:

```css
/* 8. media panes: form left, job right */
#pane-video,#pane-music{display:grid;grid-template-columns:minmax(0,520px) minmax(0,1fr);gap:var(--margin);align-items:start}
@media (max-width:899px){#pane-video,#pane-music{grid-template-columns:1fr}}
.form{display:flex;flex-direction:column;gap:12px}.form label{display:grid;gap:4px;font-size:13px;color:var(--muted)}.form label>select,.form label>input{color:var(--text)}
.job{display:flex;flex-direction:column;gap:12px}
[data-job-progress]{width:100%;height:6px;accent-color:var(--busy)}
.job-log pre{max-height:240px;overflow:auto;white-space:pre-wrap;font:13px ui-monospace,Menlo,monospace;color:var(--muted);margin:8px 0 0}
[data-job-player] video,[data-job-player] audio,[data-lib-player] video{max-width:100%;border-radius:var(--radius)}
.file-row{display:flex;align-items:center;gap:8px}.file-pick .btn{display:inline-block;padding:8px 12px;border:1px solid var(--border);border-radius:var(--radius);cursor:pointer}
```

- [ ] **Step 4: Run** — `node --test tests/js && python3 -m pytest tests/e2e/test_video_flow.py tests/e2e/test_music_flow.py -q`

- [ ] **Step 5: Commit**

```bash
git add desk/static/index.html desk/static/app.css desk/static/js/panes/video.js desk/static/js/widgets/jobview.js desk/static/js/pure/job_progress.js tests/js
git commit -m "style(media): two-column panes, step progress bar, collapsed log, Chinese file pickers (F9 F20 F28 G26)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 8: Dialogs: role, right-aligned actions, Escape, focus (F2, K4, open thread「弹层 role」)

**Files:**
- Modify: `desk/static/js/widgets/confirm.js`, `desk/static/app.css` (section 9)
- Test: `tests/js/confirm.test.js` (new)

- [ ] **Step 1: Write the failing test**

```js
import test from "node:test"; import assert from "node:assert/strict";
import { confirmDialog } from "../../desk/static/js/widgets/confirm.js";
class El { constructor(t) { this.tagName = t; this.children = []; this.attrs = {}; this.listeners = {}; this.className = ""; this.textContent = ""; } append(...n) { this.children.push(...n); } setAttribute(k, v) { this.attrs[k] = v; } addEventListener(t, l) { this.listeners[t] = l; } remove() { this.removed = true; } focus() { this.focused = true; } }
const doc = { body: new El("body"), createElement: (t) => new El(t), addEventListener(t, l) { this.listeners = { [t]: l }; }, removeEventListener() {} };

test("弹层带 role/aria-modal，取消在左确认在右，Esc 等于取消，确认按钮获焦", async () => {
  const p = confirmDialog(doc, { title: "删除模型", message: "确定？", confirmLabel: "删除" });
  const overlay = doc.body.children.at(-1); const box = overlay.children[0];
  assert.equal(box.attrs.role, "dialog"); assert.equal(box.attrs["aria-modal"], "true");
  const actions = box.children[2]; assert.equal(actions.children[0].textContent, "取消"); assert.equal(actions.children[1].className, "btn-danger");
  assert.equal(actions.children[1].focused, true);
  doc.listeners.keydown({ key: "Escape" });
  assert.equal(await p, false);
});
```

- [ ] **Step 2: Run to verify it fails** — `node --test tests/js/confirm.test.js`

- [ ] **Step 3: Implement**

```js
export function confirmDialog(doc, { title, message, confirmLabel = "确定", cancelLabel = "取消", danger = true }) {
  return new Promise((resolve) => {
    const overlay = doc.createElement("div"); overlay.className = "overlay";
    const box = doc.createElement("div"); box.className = "dialog";
    box.setAttribute("role", "dialog"); box.setAttribute("aria-modal", "true"); box.setAttribute("aria-label", title);
    const h = doc.createElement("h3"); h.textContent = title;
    const p = doc.createElement("p"); p.textContent = message;
    const row = doc.createElement("div"); row.className = "dialog-actions";
    const cancelBtn = doc.createElement("button"); cancelBtn.textContent = cancelLabel;
    const okBtn = doc.createElement("button"); okBtn.className = danger ? "btn-danger" : "btn-primary"; okBtn.textContent = confirmLabel;
    const onKey = (event) => { if (event.key === "Escape") finish(false); };
    const finish = (val) => { doc.removeEventListener?.("keydown", onKey); overlay.remove(); resolve(val); };
    cancelBtn.addEventListener("click", () => finish(false));
    okBtn.addEventListener("click", () => finish(true));
    overlay.addEventListener("click", (event) => { if (event.target === overlay) finish(false); });
    doc.addEventListener?.("keydown", onKey);
    row.append(cancelBtn, okBtn); box.append(h, p, row); overlay.append(box); doc.body.append(overlay);
    okBtn.focus?.();
  });
}
```

CSS section 9:

```css
/* 9. dialogs + drawer */
.overlay{position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:#0009;z-index:30}
.dialog{background:var(--panel);border:1px solid var(--border);border-radius:var(--radius-card);padding:20px;min-width:320px;max-width:480px}
.dialog h3{font-size:20px;margin:0 0 8px}.dialog p{margin:0 0 16px}
.dialog-actions{display:flex;justify-content:flex-end;gap:8px}
```

Callers: the memory warning in `chat.js` passes `danger: false` so 「仍要加载」 is primary (blue), not red.

- [ ] **Step 4: Run** — `node --test tests/js`

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/widgets/confirm.js desk/static/js/panes/chat.js desk/static/app.css tests/js/confirm.test.js
git commit -m "style(dialog): role=dialog, right-aligned actions, Esc/backdrop cancel, danger vs primary confirm (F2 K4)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 9: Settings drawer and first-run page styled like the rest (F10, F11, F16, N-drawer)

**Files:**
- Modify: `desk/static/index.html:34-35`, `desk/static/app.css` (section 10), `desk/static/js/panes/settings.js:35-36`
- Test: `tests/test_ui_static.py`, `tests/js/settings_pane.test.js`

- [ ] **Step 1: Write the failing tests**

```python
def test_drawer_and_firstrun_markup_use_shared_form_language():
    assert 'class="check-row"' in HTML and "data-settings-enabled" in HTML.split('class="check-row"', 1)[1].split("</label>", 1)[0]
    assert '<fieldset' not in HTML          # first-run uses cards, not browser fieldsets
    assert 'class="drawer-head"' in HTML and 'data-close-settings' in HTML.split('class="drawer-head"', 1)[1].split("</div>", 1)[0]
```

```js
// settings_pane.test.js (append)
test("监听状态用徽标类表达", async () => { /* init with listening:true */ assert.equal(controls.get("[data-settings-listening]").className, "badge badge-ok"); });
```

- [ ] **Step 2: Run to verify they fail**

- [ ] **Step 3: Implement**

`index.html` settings aside:

```html
<aside id="pane-settings" hidden><div class="drawer-head"><h2>设置</h2><button data-close-settings data-icon-name="x" class="btn-quiet" aria-label="关闭设置">关闭</button></div>
<section class="settings-section"><h3>模型目录</h3><label>当前目录 <input data-settings-models-root></label><div class="settings-actions"><button data-settings-models-apply data-icon-name="folder" class="btn-primary">使用此目录</button><button data-settings-models-scan data-icon-name="refresh">自动扫描本机</button></div><p data-settings-models-result class="hint"></p><button data-settings-models-reset class="btn-quiet">重新设置模型目录…</button></section>
<section class="settings-section"><h3>对外 API</h3><label class="check-row"><input type="checkbox" data-settings-enabled><span>开启对外接口</span></label><label>主机 <input data-settings-host></label><label>端口 <input data-settings-port type="number" min="1" max="65535"></label><div class="settings-actions"><button data-settings-save data-icon-name="check" class="btn-primary">保存并应用</button><span data-settings-listening class="badge"></span></div><p data-settings-auth-warning class="warn"></p><p class="hint">OpenAI base URL</p><div class="url-row"><code data-settings-openai-url></code><button data-settings-copy-openai data-icon-name="copy" class="btn-sm">复制</button></div><p class="hint">Anthropic base URL</p><div class="url-row"><code data-settings-anthropic-url></code><button data-settings-copy-anthropic data-icon-name="copy" class="btn-sm">复制</button></div><p data-settings-lan-note class="hint"></p></section>
<p class="inline-error" data-settings-error></p></aside>
```

`settings.js render`: `els.listening.className = \`badge ${listening ? "badge-ok" : "badge-none"}\``.

First-run section:

```html
<section id="pane-firstrun" hidden><div class="firstrun-wrap"><h1>LocalModelDesk 首次运行</h1><p class="hint">选择模型存放目录，或收编一份已有的模型目录树。</p>
<div class="card"><h3>选择 models 目录</h3><label>目录 <input data-fr-models-root></label><div class="settings-actions"><button data-fr-complete data-icon-name="folder" class="btn-primary">使用该目录</button></div></div>
<div class="card"><h3>收编既有目录树</h3><label>已有根目录 <input data-fr-legacy placeholder="/path/to/existing/models"></label><label class="check-row"><input type="radio" name="fr-mode" value="point" checked><span>指向：原地使用旧目录</span></label><label class="check-row"><input type="radio" name="fr-mode" value="move"><span>移动：搬进新的 models 根</span></label><div class="settings-actions"><button data-fr-adopt data-icon-name="import" class="btn-primary">收编</button></div></div>
<p class="inline-error" data-fr-error></p></div></section>
```

CSS section 10:

```css
/* 10. drawer + first run */
#pane-settings{position:fixed;top:0;right:0;bottom:0;z-index:25;width:min(420px,100%);overflow:auto;background:var(--panel);border-left:1px solid var(--border);padding:0 20px 20px}
.drawer-head{position:sticky;top:0;display:flex;justify-content:space-between;align-items:center;padding:16px 0;background:var(--panel);z-index:1}.drawer-head h2{margin:0}
.settings-section{display:grid;gap:10px;padding:4px 0 20px;border-bottom:1px solid var(--border);margin-bottom:18px}
.settings-section label{display:grid;gap:5px;font-size:13px;color:var(--muted)}.settings-section input:not([type="checkbox"]):not([type="radio"]){width:100%;color:var(--text)}
.check-row{display:flex !important;align-items:center;gap:8px;color:var(--text) !important}.check-row input{width:auto;margin:0;accent-color:var(--accent)}
.settings-actions{display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.url-row{display:flex;gap:8px;align-items:center}.url-row code{flex:1;padding:8px 12px;background:var(--bg);border:1px solid var(--border);border-radius:var(--radius);font:13px ui-monospace,Menlo,monospace;overflow:auto}
.warn{color:var(--busy)}
#pane-firstrun{position:fixed;inset:0;z-index:20;overflow:auto;background:var(--bg);padding:var(--margin)}
.firstrun-wrap{max-width:640px;margin:0 auto;display:flex;flex-direction:column;gap:16px}
#fatal{position:fixed;inset:0;z-index:40;display:grid;place-items:center;padding:48px;color:var(--danger);background:var(--bg)}
```

- [ ] **Step 4: Run** — `python3 -m pytest tests/test_ui_static.py tests/e2e/test_settings_api.py tests/e2e/test_firstrun.py -q && node --test tests/js`

- [ ] **Step 5: Commit**

```bash
git add desk/static/index.html desk/static/app.css desk/static/js/panes/settings.js tests/test_ui_static.py tests/js/settings_pane.test.js
git commit -m "style: drawer with sticky header and check rows; first-run page as cards (F10 F11 F16)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 10: Empty and idle states say what to do next (F12, ST1)

**Files:**
- Modify: `desk/static/js/panes/library.js:29-45`, `desk/static/js/widgets/jobview.js` (idle text), `desk/static/js/panes/chat.js` (empty session)
- Test: `tests/js/library_pane.test.js`, `tests/js/media_panes.test.js`

- [ ] **Step 1: Write the failing tests**

```js
// library_pane.test.js
test("没有成品时显示引导语", async () => { const { root, parts } = makeLibrary([], []); const pane = createLibraryPane(root, { applyFill() {} }); await pane.refresh(); assert.equal(parts["lib-list"].children[0].className, "empty"); assert.equal(parts["lib-list"].children[0].textContent, "还没有成品。去「视频」或「音乐」面板生成第一件，它会出现在这里。"); });
// media_panes.test.js
test("idle 状态文案给出下一步", () => { const video = pane({ "video-start": "" }); const p = createVideoPane(video, {}); p.jobView.apply({ job_id: 0, status: "idle" }); assert.equal(video.parts["job-status"].textContent, "空闲 · 填好左侧参数后点「生成」"); });
```

- [ ] **Step 2: Run to verify they fail**

- [ ] **Step 3: Implement** — `library.js render`: `if (!rows.length) { const li = doc.createElement("li"); li.className = "empty"; li.textContent = "还没有成品。去「视频」或「音乐」面板生成第一件，它会出现在这里。"; els.list.append(li); return; }`. `jobview.js`: `STATUS_LABEL.idle = "空闲 · 填好左侧参数后点「生成」"`. `chat.js showMessages`: when `list.length === 0` append `<p class="empty">这是一个新会话。选好模型、点「加载」，然后在下面输入第一句。</p>`. CSS: `.empty{color:var(--muted);padding:24px;text-align:center;border:1px dashed var(--border);border-radius:var(--radius-card)}`.

- [ ] **Step 4: Run** — `node --test tests/js`

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/library.js desk/static/js/widgets/jobview.js desk/static/js/panes/chat.js desk/static/app.css tests/js
git commit -m "style: empty and idle states carry a next step (F12)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 11: Menubar template icon with state variants; consistent menu items (N1, I2, N14)

**Files:**
- Modify: `macos/ShellStatus.swift` (pure `menuGlyphState`), `macos/StatusItemController.swift:19-38,49-60`, `macos/harness/ShellHarness.swift`
- Test: `tests/test_shell_status.py`

**Interfaces:**
- Produces:
  ```swift
  enum MenuGlyphState: String { case down, idle, loaded, busy }
  func menuGlyphState(for status: ShellStatus) -> MenuGlyphState
  ```
  Harness `glyph-state` reads the same fixture JSON as `map-status` and prints the raw value. `StatusItemController` draws an 18×18 template image: a rounded "desk" rectangle outline; `loaded` adds a filled dot bottom-right; `busy` adds a filled triangle (play) bottom-right; `down` draws the outline with a slash.

- [ ] **Step 1: Write the failing test**

```python
@pytest.mark.parametrize("fixture,expected", [
    ({"server": "failed", "needs_setup": False, "desk_state": None}, "down"),
    ({"server": "owned", "needs_setup": False, "desk_state": IDLE}, "idle"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_LLM}, "loaded"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_VIDEO}, "busy"),
    ({"server": "owned", "needs_setup": False, "desk_state": None}, "down"),
])
def test_menu_glyph_state(fixture, expected):
    proc = subprocess.run([harness_path(), "glyph-state"], input=json.dumps(fixture), capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected
```

- [ ] **Step 2: Run to verify it fails** — `python3 -m pytest tests/test_shell_status.py -q -k glyph`

- [ ] **Step 3: Implement**

`ShellStatus.swift`:

```swift
enum MenuGlyphState: String { case down, idle, loaded, busy }

func menuGlyphState(for status: ShellStatus) -> MenuGlyphState {
  switch status.server {
  case .starting, .stopped, .failed: return .down
  case .runningOwned, .runningAttached: break
  }
  guard let desk = status.desk else { return .down }
  guard let kind = desk.holderKind else { return .idle }
  return kind == "llm" ? .loaded : .busy
}
```

Harness: factor the fixture parsing of `runMapStatus` into `parseStatusFixture() -> ShellStatus` and add `case "glyph-state": print(menuGlyphState(for: parseStatusFixture()).rawValue)`.

`StatusItemController.swift`:

```swift
  func render(_ status: ShellStatus) {
    let title = menuTitle(for: status)
    configureStatusButton(label: title, glyph: menuGlyphState(for: status))
    detailItem.title = "状态：\(title)"
  }

  private func configureStatusButton(label: String, glyph: MenuGlyphState) {
    guard let button = statusItem.button else { return }
    let image = NSImage(size: NSSize(width: 18, height: 18), flipped: false) { rect in
      NSColor.black.setStroke(); NSColor.black.setFill()
      let body = NSBezierPath(roundedRect: rect.insetBy(dx: 2, dy: 3), xRadius: 3, yRadius: 3)
      body.lineWidth = 1.5; body.stroke()
      switch glyph {
      case .idle: break
      case .loaded: NSBezierPath(ovalIn: NSRect(x: 11, y: 3, width: 5, height: 5)).fill()
      case .busy:
        let tri = NSBezierPath(); tri.move(to: NSPoint(x: 11, y: 3)); tri.line(to: NSPoint(x: 16, y: 5.5)); tri.line(to: NSPoint(x: 11, y: 8)); tri.close(); tri.fill()
      case .down:
        let slash = NSBezierPath(); slash.move(to: NSPoint(x: 3, y: 3)); slash.line(to: NSPoint(x: 15, y: 15)); slash.lineWidth = 1.5; slash.stroke()
      }
      return true
    }
    image.isTemplate = true
    image.accessibilityDescription = "LocalModelDesk：\(label)"
    button.image = image; button.imagePosition = .imageOnly; button.title = ""
    button.toolTip = "LocalModelDesk · \(label)"
    button.setAccessibilityLabel("LocalModelDesk：\(label)")
  }
```

Menu consistency (N14): give every actionable item an SF Symbol image (`macwindow` for 打开窗口, `folder` for 打开成品目录, `gearshape` for 设置…, `power` for 退出) via `NSImage(systemSymbolName:accessibilityDescription:)`, and `indentationLevel = 0` for all items.

- [ ] **Step 4: Run** — `python3 -m pytest tests/test_shell_status.py -q && scripts/build-shell-app.sh`; then launch and capture the menubar in idle / after loading GLM / during a music job (`screencapture -R`) — the three icons must differ and render as monochrome template glyphs; attach the three PNG paths in the commit body.

- [ ] **Step 5: Commit**

```bash
git add macos/ShellStatus.swift macos/StatusItemController.swift macos/harness/ShellHarness.swift tests/test_shell_status.py
git commit -m "feat(shell): template menubar glyph with idle/loaded/busy/down variants; consistent menu items (N1 I2 N14)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 12: Semantic colour audit and reduced-motion (C3, M1/M2, F18, N8)

**Files:**
- Modify: `desk/static/app.css` (section 11), `desk/static/js/panes/video.js:124-130`, `desk/static/js/panes/music.js:23-27`
- Test: `tests/test_ui_static.py`, `tests/js/media_panes.test.js`

- [ ] **Step 1: Write the failing tests**

```python
def test_reason_hints_are_not_error_red_and_motion_is_limited():
    assert ".hint-busy{" in CSS.replace(" ", "") and "color:var(--busy)" in CSS
    assert "prefers-reduced-motion" in CSS
```

```js
test("互斥原因用 busy 提示而不是 inline-error", () => { const video = pane({ "video-start": "", "video-hint": "" }); const p = createVideoPane(video, {}); p.setHeavyAllowed(false, "媒体作业进行中"); assert.equal(video.parts["video-hint"].textContent, "媒体作业进行中"); assert.equal(video.parts["video-error"].textContent, ""); });
```

- [ ] **Step 2: Run to verify they fail**

- [ ] **Step 3: Implement** — `index.html`: add `<p class="hint hint-busy" data-video-hint></p>` next to 生成视频 and `<p class="hint hint-busy" data-music-hint></p>` next to 生成歌曲; `video.js`/`music.js` `setHeavyAllowed` write `reason` into `[data-*-hint]` (and `startBtn.title`), leave `[data-*-error]` for real errors. CSS section 11:

```css
/* 11. state colours + motion */
.hint-busy{color:var(--busy)}.hint-busy:empty{display:none}
#pane-settings,.overlay{transition:opacity 150ms ease}
@media (prefers-reduced-motion:reduce){*{transition:none !important;animation:none !important}}
```

Grep the codebase for `inline-error` writes that carry non-errors (`chat.js setHeavyAllowed` already moved in Plan A) and leave only genuine failures red.

- [ ] **Step 4: Run** — `python3 -m pytest tests/test_ui_static.py -q && node --test tests/js && python3 -m pytest tests/e2e/test_mutex_ui.py -q` (update the e2e selector if it read the reason from `[data-video-error]`: it now lives in `[data-video-hint]`).

- [ ] **Step 5: Commit**

```bash
git add desk/static/app.css desk/static/index.html desk/static/js/panes/video.js desk/static/js/panes/music.js tests
git commit -m "style: busy hints in busy colour, errors only in red, reduced-motion respected (C3 M2 F18 N8)" -m "Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>" -m "Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 13: Visual re-acceptance against the frozen baseline

- [ ] **Step 1:** Rebuild `dist/LocalModelDesk.app` (`scripts/build-app.sh`; `LMD_ALLOW_ADHOC=1` if no Developer ID), launch it.
- [ ] **Step 2:** Recompute the build id (commit + dirty digest + dist digest, same recipe as `docs/cross-exam/2026-09-06-localmodeldesk/visual/build.json`); start a new cross-exam run directory `docs/cross-exam/<date>-localmodeldesk-visual-recheck/`, copy the frozen `visual/` folder (baselines, inventory, matrix, refs) verbatim, and record the new build in `frozen-run-config.json`.
- [ ] **Step 3:** Re-run the three capture batches (`vis-b1` idle on real + isolated instance, `vis-b2` active, `vis-b3` native) with the prober prompts from the previous run, then a single Claude reviewer over the merged web manifest and one over native.
- [ ] **Step 4:** Adjudicate: every case with no high/medium finding → `done`; render with `render_report.py`. Target: 0 high findings; medium only where the baseline itself needs a decision (record those as `open_threads`).

---

## Self-Review

- Spec coverage: F1/F19/N6 → T1; F13/F14/N11/N13 → T2; G14/T3 → T3; F7/F29/G10 → T4; F4/N3 → T5; F4/F5/F17/K3/K6 → T6; F9/F20/F28/G26 → T7; F2/K4/dialog-role thread → T8; F10/F11/F16 → T9; F12 → T10; N1/I2/N14 → T11; C3/F18/N8/M1/M2 → T12; F3 (mask only one viewport tall) is a full-page-screenshot artefact of `position:fixed`, documented in T8 and not a code change; F6/F21/F26/G32 (raw traceback/paths in failure text) are covered by Plan A Task 13 and reused here in T6; N2/G29 (error page) is Plan A Task 20; N10/G2 (units) is Plan A Task 22.
- Placeholder scan: every code step contains code; the only manual steps are native screenshots (T11) and the re-acceptance run (T13), each with exact commands and pass criteria.
- Type consistency: `renderMarkdown`, `parseStepProgress`, `menuGlyphState`, `showMessages`, `badgeKind`, `setDrawerOpen` (from Plan A) are defined once and used with the same names.
