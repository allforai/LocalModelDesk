# Cross-Exam 2026-09-08 修复 · B 视觉与交互 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 关掉三份独立视觉评审（web 1440/900 的 F1–F15、原生 1200×832 的 N1–N7、宽窗 1920 的 W1–W8）报出的全部 finding，以及会话卡片点击被改名截胡这条交互缺口，使真实截图与冻结基线一致。

**Architecture:** 零依赖 ES module 前端（`desk/static/js`，`panes/` 每面一个模块、`widgets/` 共用组件、`pure/` 纯函数）、单文件样式 `desk/static/app.css`（129 行，按编号分段）、Swift AppKit 菜单栏（`macos/StatusItemController.swift` + `macos/ShellStatus.swift`，决策逻辑在后者以便无头测试）。纯函数改动进 `pure/` 并用 `node --test` 覆盖；DOM 行为用各 pane 测试里的假 DOM；跨面一致性用 Playwright e2e 兜底。

**Tech Stack:** 原生 CSS（无预处理器）· ES2022 模块 · Node 20+（`node:test`）· Swift 5 / AppKit · Playwright 1.62

**Spec:** 三份 reviewer 报告——
`docs/cross-exam/2026-09-08-localmodeldesk/evidence/vis-web/review-claude.json`（F1–F15）、
`docs/cross-exam/2026-09-08-localmodeldesk/evidence/vis-b3/review-claude.json`（N1–N7）、
`docs/cross-exam/2026-09-08-localmodeldesk-widewin/evidence/vis-web/review-claude.json`（W1–W8）。
冻结基线：`docs/cross-exam/2026-09-08-localmodeldesk-widewin/visual/visual-baseline.json`（含 2026-09-11 新增的 L6 留白上限）与同目录 `interaction-baseline.json`。

## Global Constraints

- 前端无构建步骤、无依赖；DOM 只用 `createElement`/`textContent`，永不 `innerHTML`（R-ui-01）。
- 颜色只用 `app.css` 顶部已定义的 token（`--panel #1d2026`、`--bg #14161a`、`--border #2c313a`、`--ok`、`--busy`、`--danger`、`--accent`、`--muted`）；不得引入新色值，除非该 token 一并加进基线。
- 间距走 4px 基数：控件内 8×12、卡片 16、面板外边距 24、段落间距 16（基线 S1/S2）。
- 所有面向用户的字符串是简体中文；同一状态跨面措辞必须一致（基线 D3）。
- 测试命令：`node --test tests/js/*.test.js`、`python3 -m pytest tests/e2e -q`（约 47 秒）、Swift 改动跑 `python3 -m pytest tests/test_shell_*.py`。
- **每个任务提交前必须跑 e2e**：假 DOM 单测漏过真实浏览器崩溃有前科。
- 每个任务结束后提交，trailer 同功能计划。

## 不修的两条（已判定为环境/工具产物，不是缺陷）

- **F12（弹层遮罩只压暗一条横带）**：宽窗 reviewer 在同一现象上自己给出了解释——"`position:fixed` 遮罩只覆盖视口 1200px 高，full_page 截图把它拍成横带，不计为缺陷"（widewin review 的 V-5c33ae 观察行）。两份报告结论相反时以带机制解释的那份为准。**不改代码**，但在 `visual-baseline.json` 的 K4 规则后追加一句说明，免得下一轮再报。
- **N7（输入框内"五"字徽标）**：reviewer 自己认定"更可能是系统输入法来源指示器而非应用自身控件"，同批整屏图的系统菜单栏里有同一图标。**不改代码**，基线 K5 后追加一句"系统输入法指示器不计入输入框元素"。

这两条的基线补注合并进 Task 16 一起提交。

## File Structure（改什么、各自一个职责）

| 文件 | 本计划中触及的职责 |
|---|---|
| `desk/static/app.css` | 主列宽度、状态条编排、间距、播放器配色、会话卡片布局 |
| `desk/static/js/widgets/statusbar.js` | 四状态的长/短两套文案与持有者前缀 |
| `desk/static/js/panes/chat.js` | 思考折叠标签、模型状态徽标、发送按钮、被打断的气泡、驱逐后下拉框 |
| `desk/static/js/panes/chat.js`（会话列表段） | 卡片点击只切换、动作按钮不再盖住正中 |
| `desk/static/js/widgets/jobview.js` | 空闲态文案、错误块与素材库对齐 |
| `desk/static/js/panes/library.js` | 失败行改用与作业面板同一错误组件 |
| `desk/static/js/panes/resources.js` | 卡片动作右对齐、头部模型目录、下载行细节 |
| `desk/static/js/panes/settings.js` | 未监听态的空态文案、关闭按钮 |
| `desk/static/js/panes/firstrun.js` | 输入框占满、主区走全宽 |
| `desk/static/js/pure/format.js` | 内存读数统一取整 |
| `macos/ShellStatus.swift` | 菜单文案用显示名、措辞与窗口一致、内存取整 |
| `macos/StatusItemController.swift` | 菜单状态行加图标与语义色 |

---

### Task 1: 聊天主列随窗口变宽（W1 high）

**finding 原文：** 消息列实测 682–1502 CSS px（820px 固定），1920 窗口下两侧留白合计 788–860px = 41.0%–44.8% 窗宽，超过 L6 的 40% 上限；参考图 1440 档同一列留白仅 21.7%。命中四张聊天图（未加载/已加载/流式/禁用）。

**Files:**
- Modify: `desk/static/app.css:52,59`
- Test: `tests/e2e/test_chat_layout.py`（新建）

**Interfaces:**
- Produces: `.messages` 与 `.composer` 共用同一个响应式宽度上限（两者必须一致，否则输入区与消息列错位）

- [x] **Step 1: 写失败测试**

新建 `tests/e2e/test_chat_layout.py`：

```python
"""L6：固定像素宽度居中的主列在宽窗下不许留白过半。"""
import pytest
from desk.testing import launch_test_harness

CASES = [(1440, 1000, 0.40), (1920, 1200, 0.40)]


@pytest.mark.parametrize("width,height,max_ratio", CASES)
def test_message_column_keeps_whitespace_under_the_cap(page, tmp_path, width, height, max_ratio):
    page.set_viewport_size({"width": width, "height": height})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".messages")
        box = page.evaluate(
            "() => { const m = document.querySelector('.messages').getBoundingClientRect();"
            " const host = document.querySelector('.chat-main').getBoundingClientRect();"
            " return {col: m.width, host: host.width}; }"
        )
        whitespace = box["host"] - box["col"]
        assert whitespace / width <= max_ratio, (
            f"{width} 宽下消息列两侧留白 {whitespace:.0f}px = {whitespace / width:.1%}")


def test_composer_tracks_the_message_column(page, tmp_path):
    page.set_viewport_size({"width": 1920, "height": 1200})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".composer")
        widths = page.evaluate(
            "() => [document.querySelector('.messages').getBoundingClientRect().width,"
            " document.querySelector('.composer').getBoundingClientRect().width]"
        )
        assert abs(widths[0] - widths[1]) < 2
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/e2e/test_chat_layout.py -q`
Expected: FAIL, `1920 宽下消息列两侧留白 788px = 41.0%`

- [x] **Step 3: 实现**

`desk/static/app.css`：把两处 `max-width:820px` 换成同一个可变上限。在文件顶部的 `:root` 变量块里加一行：

```css
  --chat-col: clamp(680px, 62vw, 1100px);
```

第 52 行 `.messages` 与第 59 行 `.composer` 里的 `max-width:820px` 都改成 `max-width:var(--chat-col)`。

理由：1440 窗口下 62vw ≈ 893px（留白 ≈ 24%，与参考图 21.7% 同档）；1920 下取上限 1100px（主区 1608px，留白 508px = 26.5%，进入 40% 以内）；900 窗口下取下限 680px 仍不挤压。

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/e2e/test_chat_layout.py -q`
Expected: PASS（3 passed）

- [x] **Step 5: 提交**

```bash
git add desk/static/app.css tests/e2e/test_chat_layout.py
git commit -m "fix(ui): chat column tracks window width instead of a fixed 820px (W1)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 2: 首运页走全宽、输入框占满（W2 high + F9 + F13 medium/low）

**finding 原文：** W2——首运页内容全部落在 640px 固定居中列内，两侧留白合计 1280px = 66.7%，是 L6 上限的 1.67 倍；F13 同一现象在 1440/900 档；F9——两个路径输入框把值截断在框右缘（约 155–170px 宽），而卡片右侧还有约 460px 空白。

**Files:**
- Modify: `desk/static/app.css:123-125`
- Test: `tests/e2e/test_firstrun.py`

- [x] **Step 1: 写失败测试**

`tests/e2e/test_firstrun.py` 追加：

```python
def test_firstrun_uses_the_window_and_inputs_show_full_paths(page, tmp_path):
    """W2/F9：首运页不许收在 640px 窄列里，路径输入框要能读完整值。"""
    page.set_viewport_size({"width": 1920, "height": 1200})
    with launch_test_harness(tmp_path, first_run=True) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".firstrun-wrap")
        measured = page.evaluate(
            "() => { const wrap = document.querySelector('.firstrun-wrap').getBoundingClientRect();"
            " const input = document.querySelector('[data-fr-models-root]').getBoundingClientRect();"
            " return {wrap: wrap.width, input: input.width}; }"
        )
        assert (1920 - measured["wrap"]) / 1920 <= 0.40
        assert measured["input"] >= 400
```

`launch_test_harness(..., first_run=True)` 用该文件既有用例造首运态的同一写法。

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/e2e/test_firstrun.py -q -k full_paths`
Expected: FAIL（留白 66.7%）

- [x] **Step 3: 实现**

`desk/static/app.css:124` 的 `.firstrun-wrap`：

```css
.firstrun-wrap{max-width:min(1100px,calc(100% - 48px));margin:0 auto;display:flex;flex-direction:column;gap:16px}
.firstrun-wrap label{display:grid;gap:6px}
.firstrun-wrap input:not([type=radio]){width:100%}
```

- [x] **Step 4: 跑测试确认通过**

Run: `python3 -m pytest tests/e2e/test_firstrun.py -q && node --test tests/js/firstrun_pane.test.js`
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add desk/static/app.css tests/e2e/test_firstrun.py
git commit -m "fix(ui): first-run page uses the window; path inputs show their value (W2/F9/F13)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 3: 状态条四状态任何宽度都读得全（F1 high + W4 medium + W6 low）

**finding 原文：** F1——900 宽下状态条把"媒体…"与"可开下一…"截成省略号，四状态之二不可辨；W4——媒体作业进行时持有者胶囊丢失"内存里："前缀，与右侧"媒体：生成中"重复陈述；W6——1920 下"可开下一件重活"与左侧三状态相隔 576px、与"设置"相隔 587px，孤立漂在栏中段。

**Files:**
- Modify: `desk/static/app.css:26-36`
- Modify: `desk/static/js/widgets/statusbar.js`
- Test: `tests/js/widgets.test.js`, `tests/e2e/test_statusbar_memory.py`

**Interfaces:**
- Produces: `createStatusBar(...).update(state)` 为每个部件同时写入长文案与短文案两个 span

- [x] **Step 1: 写失败测试（单元）**

`tests/js/widgets.test.js` 追加：

```js
test("holder chip keeps its label while media is busy", () => {
  const bar = makeStatusBar();
  bar.update({ holder: { kind: "video", label: "job-1" }, media_busy: true, can_start: { media: { ok: false, reason: { message: "媒体作业进行中" } } } });
  const holder = find(bar.root, (n) => n.className === "status-part status-holder");
  const text = holder.children.map((c) => c.textContent).join("");
  assert.ok(text.includes("内存里"), `持有者部件丢了前缀：${text}`);
});

test("every status part offers a compact alternative", () => {
  const bar = makeStatusBar();
  bar.update({ holder: null, media_busy: false, can_start: { media: { ok: true } } });
  for (const cls of ["status-mem", "status-holder", "status-media", "status-next"]) {
    const part = find(bar.root, (n) => (n.className || "").includes(cls));
    const wide = find(part, (n) => n.className === "wide-only");
    const narrow = find(part, (n) => n.className === "narrow-only");
    assert.ok(wide && narrow, `${cls} 缺长短两套文案`);
  }
});
```

`makeStatusBar()` 按该文件既有的 `createStatusBar` + `FakeElement` 用法写。

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/widgets.test.js`
Expected: FAIL（持有者文本为"视频生成中"，无"内存里"；无 wide/narrow 双文案）

- [x] **Step 3: 实现 —— 双文案与前缀**

`desk/static/js/widgets/statusbar.js` 里每个部件的写值处改为写两个 span。示例（持有者部件，其余三个同理）：

```js
function setPart(part, wide, narrow, doc) {
  part.replaceChildren();
  const long = doc.createElement("span");
  long.className = "wide-only";
  long.textContent = wide;
  const short = doc.createElement("span");
  short.className = "narrow-only";
  short.textContent = narrow;
  part.setAttribute?.("title", wide);
  part.append(long, short);
}
```

持有者文案：

```js
  const holderName = state.holder
    ? (state.holder.kind === "llm" ? state.holder.label : MEDIA_LABEL[state.holder.kind])
    : "无";
  setPart(els.holder, `内存里：${holderName}`, holderName, doc);
```

`MEDIA_LABEL` 定义为 `{ video: "视频生成中", music: "音乐生成中" }`——注意这两句现在只出现在持有者部件里，右侧"媒体"部件改为只说忙闲（下一步）。

媒体部件与可否开工部件：

```js
  setPart(els.media, `媒体：${mediaText}`, mediaText, doc);
  setPart(els.next, nextText, nextShort, doc);
```

其中 `nextText` 为 `"可开下一件重活"` / `"不可：媒体作业进行中"`，`nextShort` 为 `"可开工"` / `"忙"`。内存部件 `wide` 用现有完整文案，`narrow` 用 `已用 75.9/128 GiB`。

- [x] **Step 4: 实现 —— 编排与断点**

`desk/static/app.css:26` 的 `#statusbar` 改为：

```css
#statusbar{display:flex;align-items:center;gap:16px;height:48px;padding:0 var(--margin);background:var(--panel);border-bottom:2px solid var(--border);overflow:hidden}
#statusbar .status-part{flex:0 0 auto}
#statusbar [data-open-settings]{margin-left:auto}
.narrow-only{display:none}
@media (max-width:1100px){.wide-only{display:none}.narrow-only{display:inline}#statusbar{gap:10px}}
```

删除第 27 行 `.status-media{min-width:0;overflow:hidden}`、第 31 行 `.status-part>span` 的 `overflow:hidden;text-overflow:ellipsis`（不再需要截断），以及第 36 行整条 `@media (max-width:800px){...}`（它把两个状态整个隐藏，正是 F1 的成因之一）。

`margin-left:auto` 让"设置"贴右，四个状态部件紧挨成一组，消除 W6 的孤立漂浮。

- [x] **Step 5: 跑测试确认通过**

Run: `node --test tests/js/widgets.test.js`
Expected: PASS

- [x] **Step 6: 加 e2e 宽度回归**

`tests/e2e/test_statusbar_memory.py` 追加：

```python
@pytest.mark.parametrize("width", [900, 1440, 1920])
def test_four_states_are_never_truncated(page, tmp_path, width):
    """D3：四个状态在任何声明过的宽度下都要读得全（F1）。"""
    page.set_viewport_size({"width": width, "height": 800})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector("#statusbar")
        clipped = page.evaluate(
            "() => [...document.querySelectorAll('#statusbar .status-part span')]"
            ".filter(el => el.offsetParent !== null && el.scrollWidth > el.clientWidth + 1)"
            ".map(el => el.textContent)"
        )
        assert clipped == [], f"{width} 宽下被截断：{clipped}"
```

- [x] **Step 7: 跑 e2e 并提交**

Run: `python3 -m pytest tests/e2e/test_statusbar_memory.py -q`
Expected: PASS

```bash
git add desk/static/app.css desk/static/js/widgets/statusbar.js tests/js/widgets.test.js tests/e2e/test_statusbar_memory.py
git commit -m "fix(ui): status bar keeps all four states readable and grouped (F1/W4/W6)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 4: 思考块里的 Markdown 要渲染（F2 high）

**finding 原文：** 聊天主列"思考中…"展开块内 Markdown 源码原样显示：可读到 `**目标：**`、`**约束：**` 与 `* 我是谁？…` 形式的列表项，星号未被渲染。正文走的是 `.md` 渲染，思考块没走。

**Files:**
- Modify: `desk/static/js/panes/chat.js`（思考块渲染处）
- Modify: `desk/static/app.css:69`
- Test: `tests/js/chat_pane.test.js`

**Interfaces:**
- Consumes: `desk/static/js/pure/markdown.js` 已有的渲染函数（与正文同一个）

- [x] **Step 1: 写失败测试**

`tests/js/chat_pane.test.js` 追加：

```js
test("thinking block renders markdown like the answer does", () => {
  const pane = makePane();
  renderMessages(pane, [{ role: "assistant", content: "答案", reasoning: "**目标：** 五句话\n* 第一点", thinking_s: 5 }]);
  const think = find(pane.root, (n) => (n.className || "").includes("thinking"));
  const flat = JSON.stringify(think);
  assert.ok(!flat.includes("**目标：**"), "思考块里出现了未渲染的 Markdown 源码");
  assert.ok(flat.includes("目标："), "思考块内容丢了");
});
```

用该文件既有的 `makePane()`/`find()` 与实际导出的渲染函数名。

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL（`**目标：**` 原样出现）

- [x] **Step 3: 实现**

`desk/static/js/panes/chat.js` 里构造思考块正文的地方，当前是往 `<p>` 里塞 `textContent`。改为复用正文的 Markdown 渲染：

```js
  const body = renderMarkdown(doc, reasoning);   // 与答案正文同一个函数
  body.classList?.add?.("md");
  details.append(summary, body);
```

`renderMarkdown` 用 `pure/markdown.js` 的实际导出名（正文渲染处已经在用，照抄那一行的调用形式）。

`desk/static/app.css:69` 的 `.thinking p` 规则扩到整个块，保持灰色小字与左竖线：

```css
.thinking .md{margin:8px 0 0 10px;padding-left:12px;border-left:2px solid var(--border)}
.thinking .md p{margin:0 0 8px}
.thinking .md ul,.thinking .md ol{margin:0 0 8px 18px}
```

- [x] **Step 4: 跑测试确认通过**

Run: `node --test tests/js/chat_pane.test.js tests/js/markdown.test.js && python3 -m pytest tests/e2e/test_chat_stream.py -q`
Expected: PASS

- [x] **Step 5: 提交**

```bash
git add desk/static/js/panes/chat.js desk/static/app.css tests/js/chat_pane.test.js
git commit -m "fix(ui): render markdown inside the thinking fold (F2)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 5: 思考折叠标签统一（N1 medium + W5 low，连续三轮复现）

**finding 原文：** 历史消息折叠行文字为"▸ 思考过程"，没有秒数；同一 run 的新消息为"已思考 5 秒"。同一组件两种口径。

**根因：** `chat.js` 的 `send()` 只在有 `reasoning` 时写 `assistant.thinking_s`，历史会话里更早写入的消息没有这个字段，渲染时回落到"思考过程"。旧数据的秒数无法追溯——不能编造。

**Files:**
- Modify: `desk/static/js/panes/chat.js`（渲染 + 落盘两处）
- Modify: `docs/cross-exam/2026-09-08-localmodeldesk-widewin/visual/visual-baseline.json`（K2 补两态定义，**需用户确认**）
- Test: `tests/js/chat_pane.test.js`

- [x] **Step 1: 写失败测试**

```js
test("thinking fold always states the duration when it was recorded", () => {
  const pane = makePane();
  renderMessages(pane, [{ role: "assistant", content: "a", reasoning: "r", thinking_s: 7 }]);
  assert.ok(JSON.stringify(pane.root).includes("已思考 7 秒"));
});

test("thinking fold says so plainly when the duration was never recorded", () => {
  const pane = makePane();
  renderMessages(pane, [{ role: "assistant", content: "a", reasoning: "r" }]);
  const flat = JSON.stringify(pane.root);
  assert.ok(flat.includes("思考过程（未记录时长）"), flat);
});
```

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL（第二条：现文案是裸"思考过程"）

- [x] **Step 3: 实现**

`chat.js` 渲染折叠标题处：

```js
  summary.textContent = Number.isFinite(message.thinking_s)
    ? `已思考 ${Math.max(1, Math.round(message.thinking_s))} 秒`
    : "思考过程（未记录时长）";
```

并在 `send()` 里把 `thinking_s` 的写入移出 `if (state.reasoning)`，改为只要这轮有思考就记（含流式中断的情况）：

```js
  const assistant = { role: "assistant", content: state.content };
  if (state.reasoning) assistant.reasoning = state.reasoning;
  if (state.reasoning || state.thinkingStarted) assistant.thinking_s = thinkingSeconds;
```

- [x] **Step 4: 补基线两态定义（需用户确认后再提交）**

在 `visual-baseline.json` 的 `categories.components`（K2 所在类）规则数组里，把 K2 那条改为：

> K2 消息（ChatGPT 式）：思考过程为答案上方一行灰色折叠；记录了时长的显示"已思考 N 秒"，早于该字段存在的历史消息显示"思考过程（未记录时长）"——两者都是定义内状态。

**先把改动内容读给用户确认**（这是冻结基线，改动会影响后续所有轮次），得到同意再写入。

- [x] **Step 5: 跑测试确认通过并提交**

Run: `node --test tests/js/chat_pane.test.js && python3 -m pytest tests/e2e/test_chat_stream.py -q`
Expected: PASS

```bash
git add desk/static/js/panes/chat.js tests/js/chat_pane.test.js docs/cross-exam/2026-09-08-localmodeldesk-widewin/visual/visual-baseline.json
git commit -m "fix(ui): one wording for the thinking fold, both states defined (N1/W5)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 6: 发送按钮在任何状态都带图标（F3 medium）

**finding 原文：** 同一个"发送"主按钮在 idle/loaded 态是"纸飞机图标 + 发送"，在 disabled-with-reason 态只剩"发送"二字、按钮随之变窄。

**根因：** 禁用分支用 `textContent = "发送"` 整体覆写，把 `setIcon` 插进去的 `<svg>` 一起冲掉。

**Files:**
- Modify: `desk/static/js/panes/chat.js`（发送按钮状态切换处）
- Test: `tests/js/chat_pane.test.js`

- [x] **Step 1: 写失败测试**

```js
test("send button keeps its icon in every state", () => {
  const pane = makePane();
  for (const busy of [false, true]) {
    setComposerBusy(pane, busy);
    const icon = find(pane.els.send, (n) => (n.getAttribute?.("class") || "").includes("icon"));
    assert.ok(icon, `busy=${busy} 时发送按钮丢了图标`);
  }
});
```

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL（busy=true 时无 icon）

- [x] **Step 3: 实现**

把按钮文案的写法从"整体覆写 textContent"改成"只改文字节点"：

```js
function setButtonLabel(button, text, doc) {
  const label = button.querySelector?.("[data-label]");
  if (label) { label.textContent = text; return; }
  const span = doc.createElement("span");
  span.dataset.label = "1";
  span.textContent = text;
  button.append(span);
}
```

发送按钮初始化时用 `setButtonLabel(els.send, "发送", doc)` 并 `addIcon(els.send, "send", doc)`；状态切换处只调 `setButtonLabel`，不再碰 `textContent`。

- [x] **Step 4: 跑测试确认通过并提交**

Run: `node --test tests/js/chat_pane.test.js && python3 -m pytest tests/e2e/test_chat_stream.py tests/e2e/test_mutex_ui.py -q`
Expected: PASS

```bash
git add desk/static/js/panes/chat.js tests/js/chat_pane.test.js
git commit -m "fix(ui): send button never loses its icon (F3)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 7: 设置抽屉关闭按钮与未监听空态（F4 + F5 medium）

**finding 原文：** F4——抽屉右上角"× 关闭"在未监听态截图里完全没有边框与底色，呈裸文字，同抽屉其他次按钮都有 1px 描边；F5——未监听态"OpenAI base URL"与"Anthropic base URL"两个标签照常渲染但其下无任何控件，各自留一大段空白（约 90px 纯空），引导句被推到底部。

**Files:**
- Modify: `desk/static/js/panes/settings.js`
- Modify: `desk/static/app.css`
- Test: `tests/js/settings_pane.test.js`

- [x] **Step 1: 写失败测试**

```js
test("not-listening hides the url labels and puts the hint where they were", () => {
  const pane = makeSettings();
  render(pane, { status: { listening: false, enabled: false } });
  const flat = JSON.stringify(pane.root);
  assert.ok(!flat.includes("OpenAI base URL"), "未监听态不该留下无内容的标签");
  assert.ok(flat.includes("开启对外接口"), "缺引导句");
});

test("drawer close button is a secondary button", () => {
  const pane = makeSettings();
  assert.ok((pane.els.close.className || "").includes("btn-secondary"));
});
```

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/settings_pane.test.js`
Expected: FAIL

- [x] **Step 3: 实现**

`settings.js` 渲染 base URL 区块处，把"标签 + 值"整组用一个容器包起来，未监听时整组 `hidden`，并把引导句放在该容器的位置（而不是区块底部）：

```js
  const hasUrls = Boolean(status.listening);
  els.urlGroup.hidden = !hasUrls;
  els.urlHint.hidden = hasUrls;
```

`index.html` 里把两条 base URL 的 `<label>` 和复制按钮包进 `<div data-url-group>`，引导句 `<p class="hint" data-url-hint>` 紧随其后。

关闭按钮补类名：`els.close.className = "btn-secondary btn-sm"`（若该按钮在 `index.html` 里是静态的，直接在标签上加 `class="btn-secondary btn-sm"`）。

`app.css` 确认 `.btn-secondary` 存在且为 `background:var(--panel);border:1px solid var(--border)`；若当前抽屉关闭按钮用的是别的类名，统一到 `.btn-secondary`。

- [x] **Step 4: 跑测试确认通过并提交**

Run: `node --test tests/js/settings_pane.test.js && python3 -m pytest tests/e2e/test_settings_api.py -q`
Expected: PASS

```bash
git add desk/static/js/panes/settings.js desk/static/index.html desk/static/app.css tests/js/settings_pane.test.js
git commit -m "fix(ui): settings drawer empty state and close button (F4/F5)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 8: 列表工具条与列表之间留间距、卡片动作右对齐（F6 medium + F11 + W8 low）

**finding 原文：** F6——"刷新"按钮下边缘与虚线空态框上边框相接，间距为 0；资源面板"重新校验"按钮同样紧贴第一张卡片。F11/W8——卡片操作按钮在第三行左侧，参考图是右侧垂直居中；1920 下卡内内容只占左端约 340px、右侧约 1550px 恒空；资源头部缺"模型目录：…"，下载行缺"已下 X · 速率 · 剩余时间 · 当前文件"。

**Files:**
- Modify: `desk/static/app.css`
- Modify: `desk/static/js/panes/resources.js`
- Test: `tests/js/resources_pane.test.js`, `tests/e2e/test_resources_panel.py`

- [x] **Step 1: 写失败测试**

`tests/js/resources_pane.test.js` 追加：

```js
test("resources header shows the models root", () => {
  const pane = makeResources();
  render(pane, { paths: { models_root: "/Users/aa/LocalModelDesk" }, disk: { free: 1, total: 2 }, models: [] });
  assert.ok(JSON.stringify(pane.root).includes("/Users/aa/LocalModelDesk"));
});

test("downloading row names the current file and the rate", () => {
  const pane = makeResources();
  render(pane, { models: [{ key: "m", state: "partial" }],
                 progress: { key: "m", state: "running", bytes_done: 5, bytes_total: 10,
                             rate_bps: 42e6, eta_seconds: 480, current_file: "model-00003.safetensors" } });
  const flat = JSON.stringify(pane.root);
  assert.ok(flat.includes("model-00003.safetensors"));
  assert.ok(flat.includes("MB/s"));
});
```

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/resources_pane.test.js`
Expected: FAIL

- [x] **Step 3: 实现 —— 卡片布局**

`app.css` 的 6b 段加：

```css
.res-row,.lib-row{display:grid;grid-template-columns:minmax(0,1fr) max-content;column-gap:16px;align-items:center}
.res-row>.res-actions,.lib-row>.lib-actions{grid-column:2;grid-row:1/span 3;display:flex;gap:8px;align-items:center}
.res-progress{grid-column:1;width:100%}
[data-res-list],[data-lib-list]{margin-top:16px}
.res-head,.lib-head{margin-top:0}
```

`.sessions ul,[data-res-list],[data-lib-list]` 那条已有 `margin:0`，上面的 `margin-top:16px` 需写在其后才生效——放在 6b 段末尾即可。

- [x] **Step 4: 实现 —— 头部与下载行文案**

`resources.js` 头部渲染处加一行模型目录（`paths.models_root` 从 `/api/paths` 取；`main.js` 里已有 paths 数据则复用，否则在 `refresh()` 里 `api.paths()` 拉一次）：

```js
  const rootLine = doc.createElement("p");
  rootLine.className = "hint res-root";
  rootLine.textContent = `模型目录：${paths.models_root}`;
  els.head.append(rootLine);
```

下载中的 `meta` 文案扩展：

```js
  if (progress && progress.key === entry.key && progress.state === "running") {
    meta.textContent = [
      `已下 ${formatBytes(progress.bytes_done)} / ${formatBytes(progress.bytes_total)}`,
      progress.rate_bps ? `${formatBytes(progress.rate_bps)}/s` : null,
      Number.isFinite(progress.eta_seconds) ? `剩约 ${formatDuration(progress.eta_seconds)}` : null,
      progress.current_file,
    ].filter(Boolean).join(" · ");
  } else {
    meta.textContent = `预计 ${view.sizeText} · 占用 ${view.diskText}`;
  }
```

`formatBytes`/`formatDuration` 从 `pure/format.js` 导入（该模块已有）。

- [x] **Step 5: 跑测试确认通过并提交**

Run: `node --test tests/js/resources_pane.test.js tests/js/library_pane.test.js && python3 -m pytest tests/e2e/test_resources_panel.py -q`
Expected: PASS

```bash
git add desk/static/app.css desk/static/js/panes/resources.js tests/js/resources_pane.test.js
git commit -m "fix(ui): card actions align right, list gets its 16px, download row gains detail (F6/F11/W8)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 9: 禁用原因与按钮的间距两面板一致（F7 + W7）

**finding 原文：** 同一句"媒体作业进行中"在视频面板出现在按钮下方约 49px 处，在音乐面板是 11–16px，差三倍；49px 既非 8 也非 16。

**Files:**
- Modify: `desk/static/app.css`
- Modify: `desk/static/js/panes/video.js`, `desk/static/js/panes/music.js`（若原因元素位置不同）
- Test: `tests/e2e/test_mutex_ui.py`

- [x] **Step 1: 写失败测试**

`tests/e2e/test_mutex_ui.py` 追加：

```python
def test_disabled_reason_sits_the_same_distance_in_both_panes(page, tmp_path):
    """S2：同一组件跨面板间距必须一致（F7/W7）。"""
    with launch_test_harness(tmp_path, video_running=True) as harness:
        page.goto(harness.base_url)
        gaps = {}
        for tab, button in (("视频", "[data-video-start]"), ("音乐", "[data-music-start]")):
            page.get_by_role("button", name=tab).click()
            gaps[tab] = page.evaluate(
                "(sel) => { const b = document.querySelector(sel).getBoundingClientRect();"
                " const r = document.querySelector(sel).closest('.form').querySelector('.hint');"
                " return r ? r.getBoundingClientRect().top - b.bottom : null; }", button)
        assert abs(gaps["视频"] - gaps["音乐"]) <= 1, gaps
        assert gaps["视频"] in (8, 12, 16), gaps
```

选择器与造忙态的方式照该文件既有用例调整。

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/e2e/test_mutex_ui.py -q -k distance`
Expected: FAIL（49 vs 11）

- [x] **Step 3: 实现**

在 `app.css` 的表单段加一条统一规则，并删掉两个 pane 各自的临时 margin：

```css
.form .hint{margin:12px 0 0}
.form .settings-actions+.hint,.form button+.hint{margin-top:12px}
```

检查 `video.js` 是否把原因元素放在了 `.form` 之外（这会产生额外的父级间距）——若是，移到与 `music.js` 同一层级：紧随生成按钮所在的 `.settings-actions` 之后。

- [x] **Step 4: 跑测试确认通过并提交**

Run: `python3 -m pytest tests/e2e/test_mutex_ui.py -q && node --test tests/js/media_panes.test.js`
Expected: PASS

```bash
git add desk/static/app.css desk/static/js/panes/video.js desk/static/js/panes/music.js tests/e2e/test_mutex_ui.py
git commit -m "fix(ui): one spacing for the disabled reason in both media panes (F7/W7)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 10: 失败呈现在作业面板与素材库一致（F8 medium）

**finding 原文：** 同一条"生成程序异常退出"在视频作业面板是红色 1px 描边、暗红底色的错误卡片；在素材库失败行只是一行裸红字加"▶ 详情"，没有描边与底色。

**根因：** `jobview.js:renderError` 用 `<strong>` + `<details>` 装进 `.job-error`；`library.js` 用 `<p class="inline-error">` + `<details class="lib-error-details">`。两条路径各写各的。

**Files:**
- Create: `desk/static/js/widgets/error_block.js`
- Modify: `desk/static/js/widgets/jobview.js:31-39`
- Modify: `desk/static/js/panes/library.js:90-104`
- Modify: `desk/static/app.css`
- Test: `tests/js/widgets.test.js`, `tests/js/library_pane.test.js`

**Interfaces:**
- Produces: `renderErrorBlock(doc, { code, message, log_tail }) -> HTMLElement`（`.job-error` 卡片，内含 `<strong>` 标题与"详情"折叠）

- [ ] **Step 1: 写失败测试**

`tests/js/library_pane.test.js` 追加：

```js
test("library failure uses the same error card as the job pane", () => {
  const doc = { createElement: (t) => new FakeElement(t) };
  const row = rowNode(doc, { title: "x", kind: "video", status: "error", error: "exit_nonzero: exit -9" });
  const block = find(row, (n) => (n.className || "").includes("job-error"));
  assert.ok(block, "素材库失败行没用统一的错误卡片");
  assert.ok(find(block, (n) => n.tagName === "STRONG"));
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/library_pane.test.js`
Expected: FAIL

- [ ] **Step 3: 实现**

新建 `desk/static/js/widgets/error_block.js`：

```js
// 作业失败的统一呈现：一张错误卡片 + 可选「详情」折叠（基线 F2）。
import { describeJobError } from "../pure/job_error.js";

export function renderErrorBlock(doc, error) {
  const { title, detail } = describeJobError(error);
  const box = doc.createElement("div");
  box.className = "inline-error job-error";
  const strong = doc.createElement("strong");
  strong.textContent = title;
  box.append(strong);
  if (detail) {
    const details = doc.createElement("details");
    const summary = doc.createElement("summary");
    summary.textContent = "详情";
    const pre = doc.createElement("pre");
    pre.textContent = detail;
    details.append(summary, pre);
    box.append(details);
  }
  return box;
}
```

`jobview.js:renderError` 改为：

```js
function renderError(error) {
  els.error.replaceChildren(renderErrorBlock(root.ownerDocument, error));
}
```

`library.js:90-104` 改为：

```js
  if (entry.error) {
    const [code, ...rest] = entry.error.split(": ");
    head.append(renderErrorBlock(doc, { code, message: rest.join(": ") }));
  }
```

`app.css` 确认 `.job-error` 有描边与底色；若目前只作用于 `[data-job-error]`，把选择器改成 `.job-error`：

```css
.job-error{border:1px solid var(--danger);background:rgba(229,83,75,.08);border-radius:var(--radius);padding:12px;display:grid;gap:8px}
```

- [ ] **Step 4: 跑测试确认通过并提交**

Run: `node --test tests/js/*.test.js && python3 -m pytest tests/e2e/test_library_panel.py tests/e2e/test_video_flow.py -q`
Expected: PASS

```bash
git add desk/static/js/widgets/error_block.js desk/static/js/widgets/jobview.js desk/static/js/panes/library.js desk/static/app.css tests/js/
git commit -m "fix(ui): one error card for job pane and library (F8)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 11: 音频播放器套用暗色 token（F10 low + W3 medium）

**finding 原文：** 音频播放器沿用浏览器默认控件：条底色 #373737、滑轨 #b5b5b5，均不在 C1 token 表内，且与同屏面板 #1d2026 明显不同；在素材库满宽 1872px 时是整屏最亮的一块；与视频播放器（控件底色近黑）形成同组件不同外观。

**Files:**
- Modify: `desk/static/app.css`
- Test: `tests/e2e/test_library_panel.py`

- [ ] **Step 1: 写失败测试**

```python
def test_audio_player_matches_the_dark_palette(page, tmp_path):
    """C1：播放器不能是整屏最亮的一块（F10/W3）。"""
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.get_by_role("button", name="音乐").click()
        page.wait_for_selector("audio")
        scheme = page.evaluate("() => getComputedStyle(document.querySelector('audio')).colorScheme")
        assert "dark" in scheme
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/e2e/test_library_panel.py -q -k palette`
Expected: FAIL（`colorScheme` 为 `normal`）

- [ ] **Step 3: 实现**

`app.css` 的播放器段：

```css
[data-job-player] video,[data-job-player] audio,[data-lib-player] video,[data-lib-player] audio{
  max-width:100%;border-radius:var(--radius);color-scheme:dark;background:var(--panel)}
[data-job-player] audio,[data-lib-player] audio{width:100%;border:1px solid var(--border)}
```

`color-scheme:dark` 让 WebKit/Chromium 用暗色原生控件（这是唯一不写死厂商私有伪元素就能改原生控件配色的办法）。

- [ ] **Step 4: 跑测试确认通过并提交**

Run: `python3 -m pytest tests/e2e/test_library_panel.py tests/e2e/test_music_flow.py -q`
Expected: PASS

```bash
git add desk/static/app.css tests/e2e/test_library_panel.py
git commit -m "fix(ui): audio player follows the dark palette (F10/W3)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 12: 空闲面板显示空态引导句（F14 low + 未拉的线 #9）

**finding 原文：** F14——标为 idle 的音乐面板右列直接显示上一单的"✓ 完成（耗时 30秒）"与播放器，而同状态的视频面板显示"空闲 · 填好左侧参数后点「生成」"。未拉的线 #9——视频作业进行时，音乐面板按钮已禁用并标"媒体作业进行中"，按钮下方仍显示"空闲 · 填好左侧参数后点「生成」"，同一面板两处文案矛盾。

**根因：** `jobview.sync()` 拉的是服务端最后一次作业状态，终态会一直留在面板上；且空闲文案不随互斥态更新。

**Files:**
- Modify: `desk/static/js/widgets/jobview.js:7,26-30,69-71`
- Test: `tests/js/widgets.test.js`, `tests/e2e/test_mutex_ui.py`

**Interfaces:**
- Produces: `apply(payload, { busyReason })`——忙态时空闲文案让位给原因

- [ ] **Step 1: 写失败测试**

```js
test("a finished job from another pane does not masquerade as this pane's state", () => {
  const view = makeJobView("music");
  view.apply({ job_id: 3, status: "done", kind: "video", started_at: 1, finished_at: 31 });
  assert.ok(JSON.stringify(view.root).includes("空闲"), "别的面板的作业终态串台了");
});

test("busy reason replaces the idle hint", () => {
  const view = makeJobView("music");
  view.apply({ job_id: null, status: "idle", kind: null }, { busyReason: "媒体作业进行中" });
  const flat = JSON.stringify(view.root);
  assert.ok(flat.includes("媒体作业进行中"));
  assert.ok(!flat.includes("填好左侧参数"), "忙态还挂着空闲引导句");
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/widgets.test.js`
Expected: FAIL

- [ ] **Step 3: 实现**

`jobview.js`：`apply` 已有 `kind` 不匹配就回落 `IDLE` 的分支（第 41 行），确认音乐面板拿到 video 作业时走这条；若条件写成了"kind 为空才回落"，改为严格相等比较：

```js
  if (payload.kind && payload.kind !== kind) return apply(IDLE);
```

`statusText` 增加忙态优先：

```js
function statusText(job, opts = {}) {
  if (job.status === "idle" && opts.busyReason) return opts.busyReason;
  ...
}
```

`apply(payload, opts)` 把 `opts` 透传给 `statusText`；`main.js` 的 tick 在调用 `jobview.apply`/`sync` 时传入 `{ busyReason: state.can_start?.media?.ok ? null : state.can_start?.media?.reason?.message }`。

- [ ] **Step 4: 跑测试确认通过并提交**

Run: `node --test tests/js/widgets.test.js tests/js/media_panes.test.js && python3 -m pytest tests/e2e/test_mutex_ui.py -q`
Expected: PASS

```bash
git add desk/static/js/widgets/jobview.js desk/static/js/main.js tests/js/
git commit -m "fix(ui): idle panes show an idle state, busy panes show why (F14)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 13: 聊天模型驻留状态用徽标（F15 low）

**finding 原文：** 聊天顶行显示绿色纯文字"已加载：GLM 4.7 Flash 越狱 4bit"，参考图同位置是带绿色底色的圆角徽标；同一屏顶部状态条的"内存里：无"却是有底色的胶囊，两处状态表达方式不一致。

**Files:**
- Modify: `desk/static/js/panes/chat.js:66-84`
- Modify: `desk/static/app.css:62`
- Test: `tests/js/chat_pane.test.js`

- [x] **Step 1: 写失败测试**

```js
test("model state renders as a badge in the shared family", () => {
  const pane = makePane();
  renderLlm(pane, { state: { status: "loaded", model_key: "glm" }, loaded_model: { name: "GLM" } });
  assert.ok((pane.els.modelState.className || "").includes("badge"));
  assert.ok((pane.els.modelState.className || "").includes("badge-ok"));
});
```

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL

- [x] **Step 3: 实现**

`chat.js:renderLlm` 每个分支在写完文案后设类名：

```js
  const KIND = { idle: "none", loading: "busy", loaded: "ok", error: "unknown" };
  els.modelState.className = `badge badge-${KIND[state.status] ?? "unknown"}`;
```

驱逐态（`state.error?.code === "evicted"`）用 `badge-busy`。

`app.css:62` 删掉 `[data-model-state][data-status=...]` 两条颜色规则（改由 `.badge-*` 提供），并让状态条胶囊也复用同一族：`.status-holder>span` 改为 `.status-holder>span{}` 留空并在 `statusbar.js` 里给该 span 加 `className = "badge badge-none"`（持有者为模型时 `badge-ok`，媒体忙时 `badge-busy`）。

- [x] **Step 4: 跑测试确认通过并提交**

Run: `node --test tests/js/chat_pane.test.js tests/js/widgets.test.js && python3 -m pytest tests/e2e -q`
Expected: PASS

```bash
git add desk/static/js/panes/chat.js desk/static/js/widgets/statusbar.js desk/static/app.css tests/js/
git commit -m "fix(ui): model residency reads as a badge like every other status (F15)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 14: 消息列底部与输入区留出间距（N6 low）

**finding 原文：** 原生窗口里消息滚动区下沿与输入框之间只有约 7px（=3.5pt），最后一条助手消息的模型名整行正好被裁在输入框上边缘只剩上半行；列表并未滚到底，是滚动裁切。

**Files:**
- Modify: `desk/static/app.css:52,59`
- Test: `tests/e2e/test_chat_layout.py`

- [x] **Step 1: 写失败测试**

`tests/e2e/test_chat_layout.py` 追加：

```python
def test_messages_and_composer_keep_a_16px_gap(page, tmp_path):
    page.set_viewport_size({"width": 1200, "height": 832})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".composer")
        gap = page.evaluate(
            "() => document.querySelector('.composer').getBoundingClientRect().top"
            " - document.querySelector('.messages').getBoundingClientRect().bottom")
        assert gap >= 16, gap
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/e2e/test_chat_layout.py -q -k gap`
Expected: FAIL（约 7px）

- [x] **Step 3: 实现**

`.messages` 的 `padding:16px 4px` 改为 `padding:16px 4px 0`，并在 `.composer` 加 `margin-top:16px`；`#pane-chat` 的高度计算已用 `calc(100vh - 94px)`，多出的 16px 由 `.messages` 的 `flex:1` 吸收，不会溢出。

- [x] **Step 4: 跑测试确认通过并提交**

Run: `python3 -m pytest tests/e2e/test_chat_layout.py -q`
Expected: PASS

```bash
git add desk/static/app.css tests/e2e/test_chat_layout.py
git commit -m "fix(ui): 16px between the message list and the composer (N6)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 15: 菜单栏用显示名、统一措辞、取整内存、加语义色（N2 medium + N3/N4/N5 low）

**finding 原文：** N2——菜单第一行"状态：已加载 glm"用内部短标签，同一时刻窗口写"内存里：GLM 4.7 Flash 越狱 4bit"；N3——同屏三处内存读数 79.0/79.4/79.2 互不相同；N4——同一状态三种措辞"出歌中"/"音乐生成中"/"生成中…"；N5——菜单状态行与内存行三态渲染完全相同，无图标无语义色，而下方四个菜单项都有图标。

**Files:**
- Modify: `macos/ShellStatus.swift:56-76,49-53`
- Modify: `macos/StatusItemController.swift:54-58,88-96`
- Modify: `desk/arbiter/state.py`（`holder.label` 带显示名）
- Test: `tests/test_shell_status.py`, `tests/test_arbiter_state.py`

**Interfaces:**
- Produces: `/api/state` 的 `holder` 增加 `display` 字段（人类可读名）；`menuTitle` 优先用 `display`

- [x] **Step 1: 写失败测试（Python 侧）**

`tests/test_arbiter_state.py` 追加：

```python
def test_holder_carries_a_human_readable_name():
    """菜单栏只拿得到 /api/state，它必须带显示名（N2）。"""
    state = arbiter_state_with_llm(key="glm", display="GLM 4.7 Flash 越狱 4bit")
    assert state["holder"]["display"] == "GLM 4.7 Flash 越狱 4bit"
```

- [x] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/test_arbiter_state.py -q`
Expected: FAIL, `KeyError: 'display'`

- [ ] **Step 3: 实现 Python 侧**

`desk/arbiter/state.py` 的 holder 序列化处加 `"display": self._display or self._label`；`desk/llm/service.py` 取得许可时把模型 `name` 作为 display 传进去；媒体作业传 `"视频生成中"` / `"音乐生成中"`（与窗口状态条同一措辞，解决 N4）。

> **部分完成 / blocked（执行者注）：** `Holder` 数据类与其序列化落在 `desk/arbiter/state.py`（已加 `display` 字段与 `Holder.public_view()`，测试见 Step 1/2），但真正拼进 `/api/state` 响应的持有者字典由 `desk/arbiter/core.py` 的 `Arbiter._public_holder` / `acquire_heavy` 构造——该文件不在本任务 owns 列表内，也不是额外说明里点名的例外（例外只覆盖 `llm/service.py`、`media/service.py` 各一行传参）。`acquire_heavy(kind, label)` 当前不接受 display 参数，`_public_holder` 也不读取它，所以在 `core.py` 跟进之前，`display` 不会真正出现在线上 `/api/state` 里，`llm/service.py`/`media/service.py` 那一行传参也无处可传（对应关键字参数尚不存在）。N4 的措辞统一已经在 `ShellStatus.swift` 的默认兜底文案里独立解决（`holderDisplay` 缺失时回退到 `"视频生成中"`/`"音乐生成中"`），不依赖这条链路。跟进需要：`core.py` 的 `Holder(...)` 构造调用加 `display=`、`acquire_heavy` 加 `display` 形参、`_public_holder` 输出 `display` 字段，然后才能加上 `llm/service.py`/`media/service.py` 的那一行传参。

- [x] **Step 4: 写失败测试（Swift 侧）**

`tests/test_shell_status.py` 的 parametrize 里加：

```python
    ({"holder": {"kind": "llm", "label": "glm", "display": "GLM 4.7 Flash 越狱 4bit"}},
     "已加载 GLM 4.7 Flash 越狱 4bit"),
    ({"holder": {"kind": "music", "label": "job-2", "display": "音乐生成中"}}, "音乐生成中"),
```

并加一条内存取整用例：`memoryMenuTitle` 对 `used=79.4 GiB` 输出 `已用 79 / 总 128 GiB（可用 49 GiB）`。

- [x] **Step 5: 跑测试确认失败**

Run: `python3 -m pytest tests/test_shell_status.py -q`
Expected: FAIL

- [x] **Step 6: 实现 Swift 侧**

`ShellStatus.swift`：`DeskStateSnapshot` 加 `var holderDisplay: String?` 并在 `parse` 里读 `holder["display"]`；`menuTitle` 改为：

```swift
  switch kind {
  case "llm": return "已加载 \(desk.holderDisplay ?? desk.holderLabel ?? "?")"
  case "video", "music": return desk.holderDisplay ?? (kind == "video" ? "视频生成中" : "音乐生成中")
  default: return "状态不可读"
  }
```

`memoryMenuTitle` 的数值格式从 `%.1f` 改为 `%.0f`（N3：同屏三处读数因 0.4 GiB 抖动而不同，取整后一致）。同时把 web 侧 `pure/format.js` 里状态条的内存格式也改为整数 GiB，两处必须同时改，否则仍会出现 79 vs 79.4。

> **执行者注：** 状态条的内存文案实际由 `desk/static/js/pure/desk_state.js` 的 `renderState()` 内联拼出（局部 `gb = (n) => (n / GB).toFixed(1)`），并非走 `pure/format.js` 的 `formatBytes`——该文件不在本任务 owns 列表。已在 `format.js` 新增 `formatMemoryLine(used, total, available)`（取整 GiB，用法/取整方式与 Swift 侧 `memoryMenuTitle` 对齐，`tests/js/format.test.js` 覆盖），但 `desk_state.js` 尚未改为调用它，因此网页状态条本身此刻仍是一位小数——N3 在**菜单栏**一侧已修好，网页状态条一侧需要另一条拥有 `desk_state.js` 的泳道把 `gb()` 换成这个新函数才算全量修复。

`StatusItemController.swift:54-58` 给状态行与内存行加图标与语义色：

```swift
    detailItem.title = "状态：\(title)"
    detailItem.image = NSImage(systemSymbolName: glyphName(for: status), accessibilityDescription: nil)
    detailItem.attributedTitle = NSAttributedString(
      string: "状态：\(title)",
      attributes: [.foregroundColor: tintColor(for: status)])
```

`glyphName(for:)` 返回 `"circle"`/`"circle.fill"`/`"waveform"`，`tintColor(for:)` 返回 `NSColor.secondaryLabelColor` / `systemGreen` / `systemOrange`，与窗口状态条的 `--ok`/`--busy` 对应。

- [x] **Step 7: 跑测试确认通过并提交**

Run: `python3 -m pytest tests/test_shell_status.py tests/test_arbiter_state.py -q && node --test tests/js/format.test.js && python3 -m pytest tests/e2e/test_statusbar_memory.py -q`
Expected: PASS

```bash
git add macos/ desk/arbiter/state.py desk/llm/service.py desk/static/js/pure/format.js tests/
git commit -m "fix(shell): menu shows display names, one wording, rounded memory, semantic colors (N2-N5)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 16: 会话卡片点中间就是切换（F7 功能缺口 medium）+ 两条基线补注

**缺口原文：** Playwright 对 240×70.5px 的会话卡片做 hover+click 中心点，卡片被替换为裸 `<input>`——进入改名而非切换。CSS 上 `.session-actions` 仅 hover 时 `display:flex`、绝对定位在右下并与标题/meta 纵向重叠，hover 唤出的"改名"按钮正落在点击点上。

**Files:**
- Modify: `desk/static/app.css:70-72`
- Test: `tests/js/sessions.test.js`, `tests/e2e/test_sessions.py`

- [ ] **Step 1: 写失败测试**

`tests/e2e/test_sessions.py` 追加：

```python
def test_clicking_a_card_switches_instead_of_renaming(page, tmp_path):
    """F7：主动作不许被 hover 唤出的动作按钮截胡。"""
    with launch_test_harness(tmp_path, sessions=3) as harness:
        page.goto(harness.base_url)
        cards = page.locator(".sessions li.session")
        cards.nth(1).click()
        assert cards.nth(1).locator("input").count() == 0
        assert "active" in (cards.nth(1).get_attribute("class") or "")
```

- [ ] **Step 2: 跑测试确认失败**

Run: `python3 -m pytest tests/e2e/test_sessions.py -q -k switches`
Expected: FAIL（出现 `<input>`）

- [ ] **Step 3: 实现**

`app.css` 把动作按钮从"绝对定位覆盖卡片"改成"卡片自己的一列"，hover 只切换可见性而不改变布局：

```css
.session{cursor:pointer;padding:12px;display:grid;grid-template-columns:minmax(0,1fr) max-content;column-gap:8px;align-items:center}
.session-title,.session-meta{grid-column:1}
.session-actions{grid-column:2;grid-row:1/span 2;display:flex;gap:6px;visibility:hidden}
.session:hover .session-actions,.session:focus-within .session-actions{visibility:visible}
```

删除原 `.session{position:relative}` 与 `.session-actions{position:absolute;right:8px;bottom:8px}`。这样标题区永远占据卡片中心，动作按钮只在右侧自己的列里出现/隐藏，不再与点击点重叠。

- [ ] **Step 4: 两条基线补注（Task 开头"不修的两条"）**

在 `docs/cross-exam/2026-09-08-localmodeldesk-widewin/visual/visual-baseline.json` 的 `categories.components` 规则数组里，K4 后追加：

> K4 附注：full_page 截图里 `position:fixed` 遮罩只覆盖视口高度，表现为一条横带，这是截图方式的产物，不作为缺陷。

`categories.components` 的 K5 后追加：

> K5 附注：系统输入法来源指示器出现在输入框内是 macOS 行为，不计入输入框元素。

- [ ] **Step 5: 跑测试确认通过并提交**

Run: `python3 -m pytest tests/e2e/test_sessions.py -q && node --test tests/js/sessions.test.js`
Expected: PASS

```bash
git add desk/static/app.css docs/cross-exam/2026-09-08-localmodeldesk-widewin/visual/visual-baseline.json tests/
git commit -m "fix(ui): session card click switches; note two screenshot artifacts in the baseline (F7)

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 17: 驱逐后下拉框停在被驱逐的模型（未拉的线 #10）

**缺口原文：** LLM 被媒体作业驱逐后，聊天面板提示"已被媒体任务让出内存，可重新加载"，但模型下拉框回到了列表第一项 GLM 而非被驱逐的 SuperQwen——此时点"加载"会装错模型。

**Files:**
- Modify: `desk/static/js/panes/chat.js:66-84`
- Test: `tests/js/chat_pane.test.js`

- [x] **Step 1: 写失败测试**

```js
test("after eviction the dropdown still points at the evicted model", () => {
  const pane = makePane();
  pane.els.modelSelect.options = ["glm", "superqwen"];
  renderLlm(pane, { state: { status: "error", model_key: "superqwen", error: { code: "evicted" } } });
  assert.equal(pane.els.modelSelect.value, "superqwen");
});
```

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL（value 为 `glm`）

- [x] **Step 3: 实现**

`renderLlm` 的驱逐分支加一行，把选择器对回被驱逐的 key（仅当用户没有手动改过选择时）：

```js
  } else if (state.error?.code === "evicted") {
    els.modelState.textContent = "已被媒体任务让出内存，可重新加载";
    if (state.model_key && !els.modelSelect.dataset.userPicked) {
      els.modelSelect.value = state.model_key;
    }
  }
```

并在下拉框的 `change` 监听里设 `els.modelSelect.dataset.userPicked = "1"`，在成功加载后清除。

- [x] **Step 4: 跑测试确认通过并提交**

Run: `node --test tests/js/chat_pane.test.js && python3 -m pytest tests/e2e/test_mutex_ui.py -q`
Expected: PASS

```bash
git add desk/static/js/panes/chat.js tests/js/chat_pane.test.js
git commit -m "fix(ui): keep the evicted model selected so reload reloads it

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 18: 被媒体作业打断的回复标为已中断（widewin 未拉的线 #1）

**缺口原文：** 聊天回复仍在流式/收尾时提交视频作业，LLM 被驱逐后前端遗留一个停在"思考中…"、只有部分推理文字、没有正文的半成品气泡。

**Files:**
- Modify: `desk/static/js/panes/chat.js`（流式失败/驱逐处理）
- Test: `tests/js/chat_pane.test.js`

- [x] **Step 1: 写失败测试**

```js
test("an interrupted answer is labelled, not left mid-thought", () => {
  const pane = makePane();
  const live = beginAssistantMessage(pane);
  live.pushReasoning("想了一半");
  live.interrupt({ code: "evicted" });
  const flat = JSON.stringify(pane.root);
  assert.ok(flat.includes("已中断"), flat);
  assert.ok(!flat.includes("思考中…"), "中断后还挂着进行中的文案");
});
```

按 `chat.js` 实际的流式状态对象命名调整方法名。

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL

- [x] **Step 3: 实现**

在流式错误/连接中断的收尾处（`stream.js` 的 error 回调进到 `chat.js` 的地方）加：

```js
  function interrupt(error) {
    const why = error?.code === "evicted" ? "已中断：内存让给了媒体作业" : "已中断";
    summary.textContent = why;
    details.open = false;
    if (!state.content) {
      const note = doc.createElement("p");
      note.className = "empty-answer";
      note.textContent = "这条回答没有生成完，可重新发送。";
      body.replaceChildren(note);
    }
    setComposerBusy(pane, false);
  }
```

并确保这条消息**不写进会话历史**（`send()` 的 push 只在正常结束时执行），避免把半成品持久化。

- [x] **Step 4: 跑测试确认通过并提交**

Run: `node --test tests/js/chat_pane.test.js tests/js/chat_stream.test.js && python3 -m pytest tests/e2e/test_chat_stream.py -q`
Expected: PASS

```bash
git add desk/static/js/panes/chat.js tests/js/
git commit -m "fix(ui): label an answer the media job interrupted

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

### Task 19: 首屏标签稳定（未拉的线 #11）

**缺口原文：** J6 起点窗口停在"音乐"标签，重启后停在"聊天"——首屏状态不确定。

**根因候选：** `pure/tab_hash.js` 从 `location.hash` 恢复标签；原生壳重新加载时 hash 可能残留上一次的值，也可能为空。

**Files:**
- Modify: `desk/static/js/main.js`（启动时的标签决定）
- Test: `tests/js/main_hash.test.js`

- [x] **Step 1: 写失败测试**

```js
test("a fresh load with no hash always lands on chat", () => {
  assert.equal(initialTab(""), "chat");
  assert.equal(initialTab("#"), "chat");
  assert.equal(initialTab("#tab=music"), "music");
  assert.equal(initialTab("#tab=nonsense"), "chat");
});
```

- [x] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/main_hash.test.js`
Expected: FAIL（未知值未回落到 chat，或函数未导出）

- [x] **Step 3 (partial — pure module only): 实现**

`pure/tab_hash.js` 导出 `initialTab(hash)`，对不在白名单内的值一律返回 `"chat"`（done, delegates to existing `tabFromHash`). `main.js` 启动时改用它，并在首运结束后显式 `location.hash = "#tab=chat"` — **BLOCKED**: `main.js` is owned by lane B-core; this lane owns only `pure/tab_hash.js` and `tests/js/main_hash.test.js`. Main session must wire `main.js` line 52 (`showTab(tabFromHash(...))`) to call `initialTab` instead and set `location.hash = "#tab=chat"` after first run.

- [ ] **Step 4: 跑测试确认通过并提交**

Run: `node --test tests/js/main_hash.test.js && python3 -m pytest tests/e2e -q`
Expected: PASS

```bash
git add desk/static/js/pure/tab_hash.js desk/static/js/main.js tests/js/main_hash.test.js
git commit -m "fix(ui): a fresh window always opens on the chat tab

Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01KWaBrH4VVDiYDGZiKms5kK"
```

---

## 收尾：整包回归与复盘截图

- [ ] **Step 1: 全量测试**

```bash
node --test tests/js/*.test.js
python3 -m pytest -q
python3 -m pytest tests/e2e -q
```

- [ ] **Step 2: 重新出包**

```bash
./scripts/build-app.sh && ./scripts/verify-app.sh --app dist/LocalModelDesk.app
```

- [ ] **Step 3: 三个宽度各拍一张聊天页自查**

用 Playwright 在 900 / 1440 / 1920 三个宽度各截一张聊天页，肉眼确认：四个状态都读得全、消息列两侧留白明显收窄、发送按钮带图标、思考折叠有秒数。截图存 `/private/tmp/claude-502/.../scratchpad/`，**不要**写进 `docs/cross-exam/`——那是盘问的证据目录，修复过程不往里写。

- [ ] **Step 4: 交回用户**

告诉用户两件事：(1) Task 5 的基线 K2 两态定义与 Task 16 的两条附注需要他确认；(2) 复验要重新跑 `/superstorm:cross-exam`，本计划不自行宣布视觉通过——判定权在独立 reviewer。
