# Cross-Exam 2026-09-13 修复 · E 界面细节（键盘可达、宽屏、音乐时长、标签页 hash）Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 不用鼠标也能切换/改名/删除会话、选择素材文件；危险确认默认聚焦「取消」；2560 宽屏聊天列留白回到 40% 以内；素材库按成品实际时长标注歌曲；外部改 `#tab=` 能切换标签页。

**Architecture:** 纯前端为主：会话卡片可聚焦并响应 Enter/Space；文件选择把原生 `input[type=file]` 从 `hidden` 改成视觉隐藏，让它留在 Tab 序列里；`confirmDialog` 按 `danger` 决定初始焦点；`--chat-col` 上限 1100→1400px；`main.js` 监听 `hashchange`。服务端一处：音乐作业完成时用 stdlib `wave` 读出成品秒数写进历史记录 `audio_seconds`。

**Tech Stack:** 零依赖 ES modules · CSS · Python 3.13 stdlib（`wave`）· node:test · Playwright

**Spec:** `docs/cross-exam/2026-09-13-localmodeldesk-recheck/completion-report.md` §缺口清单 G5、G10、G13，§缺陷模式 P2（6 位点），未拉的线「删除确认默认焦点在危险按钮」「location.hash 改变不切换标签页」「全屏 2560 聊天不铺开」；证据 `evidence/q10/`、`q19/`、`q40/`。视觉基线：`docs/cross-exam/2026-09-13-localmodeldesk-recheck/visual/visual-baseline.json`（L2/L6：宽端两侧留白合计 ≤ 窗口宽 40%，遮罩不算留白）。需求：`docs/superpowers/specs/2026-08-31-ui-spec.md` R-ui-06、R-ui-09，`2026-08-31-media-spec.md` R-media-07。

## Global Constraints

- 前端：零依赖 ES modules；`createElement` / `textContent`，禁止 `innerHTML`。
- 所有面向用户的字符串是简体中文。
- 界面自适应：800–2560 七档宽度无横向溢出；宽端两侧留白合计 ≤ 窗口宽 40%。
- 测试命令：`python3 -m pytest -q`、`node --test tests/js/*.test.js`、`python3 -m pytest tests/e2e -q`。
- 验证门必须包含 e2e（`desk/static/` 改动）。
- 测试永不触碰 `~/LocalModelDesk` 或真实数据根。
- 每个任务结束后提交，commit message 末尾带两行 trailer：
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_017SVdZi6MbtQeTc87fBLvUx`

## File Structure

| 文件 | 本计划中触及的职责 |
|---|---|
| `desk/static/js/panes/chat.js` | 会话卡片 `tabIndex`、`aria-current`、Enter/Space |
| `desk/static/index.html` | 文件输入去掉 `hidden` 改 `class="visually-hidden"`；音乐时长说明 |
| `desk/static/app.css` | `.visually-hidden`、`.file-pick:focus-within`、`.session:focus-visible`、`--chat-col` 上限 |
| `desk/static/js/widgets/confirm.js` | 危险确认聚焦取消 |
| `desk/media/audio.py`（新） | `wav_seconds(path)` |
| `desk/media/service.py` | 历史记录 `audio_seconds` |
| `desk/static/js/panes/library.js` | 歌曲规格显示「成品 N 秒（请求 M 秒）」 |
| `desk/static/js/main.js` | `hashchange` |

---

### Task 1: 会话卡片键盘可达

**Files:**
- Modify: `desk/static/js/panes/chat.js`（`renderSessionList`）
- Modify: `desk/static/app.css`（会话卡片焦点样式）
- Test: `tests/js/chat_pane.test.js`、`tests/e2e/test_sessions.py`

**Interfaces:**
- Produces: 每个 `li.session` 有 `tabIndex = 0`；当前项 `aria-current="true"`；Enter 或 Space 切换到该会话（`preventDefault`，避免 Space 滚动页面）；改名/删除按钮沿用已有 `:focus-within` 显隐。

- [ ] **Step 1: Write the failing unit test**

在 `tests/js/chat_pane.test.js` 末尾追加：

```javascript
test("会话卡片可 Tab 聚焦，Enter/Space 切换（P2，cross-exam 2026-09-13 G5）", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const previous = globalThis.fetch;
  globalThis.fetch = async (path) => {
    if (path === "/api/sessions") return json([
      { id: "s1", title: "一", messages: [], updated: "2026-09-07T10:05:00" },
      { id: "s2", title: "二", messages: [], updated: "2026-09-07T10:04:00" },
    ]);
    if (String(path).includes("catalog")) return json([]);
    if (String(path).includes("status")) return json({ models: [] });
    return json({ state: { status: "idle" } });
  };
  try {
    const pane = createChatPane(root);
    await pane.init();
    const list = controls.get("[data-session-list]");
    assert.equal(list.children[0].tabIndex, 0);
    assert.equal(list.children[0].attrs["aria-current"], "true");
    let prevented = false;
    list.children[1].listeners.keydown({ key: " ", preventDefault() { prevented = true; } });
    assert.equal(prevented, true);
    assert.match(list.children[1].className, /\bactive\b/);
    list.children[0].listeners.keydown({ key: "Enter", preventDefault() {} });
    assert.match(list.children[0].className, /\bactive\b/);
    list.children[1].listeners.keydown({ key: "a", preventDefault() { throw new Error("不应拦截普通按键"); } });
  } finally { globalThis.fetch = previous; }
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/js/chat_pane.test.js`
Expected: FAIL（`tabIndex` 为 undefined）

- [ ] **Step 3: Write the implementation**

`desk/static/js/panes/chat.js` 的 `renderSessionList` 中：

在 `li.classList.toggle("active", session.id === currentId);` 之后加：

```javascript
      li.tabIndex = 0;
      if (session.id === currentId) li.setAttribute?.("aria-current", "true");
```

把现有 `li.addEventListener("click", () => {...});` 整段替换为：

```javascript
      const select = () => {
        currentId = session.id;
        renderSessionList();
        renderMessages();
        [...(els.sessionList.children ?? [])].find((node) => node.dataset?.sessionId === session.id)?.focus?.();
      };
      (li.dataset ??= {}).sessionId = session.id;
      li.addEventListener("click", select);
      li.addEventListener("keydown", (event) => {
        if (event.target && event.target !== li) return; // buttons and the rename input handle their own keys
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        select();
      });
```

（重绘后把焦点放回新生成的同一张卡片，键盘用户不会丢失位置。按键若来自卡片内的按钮或改名输入框，交给它们自己处理——否则在改名框里敲空格会被拦下。）

`desk/static/app.css` 在 `.session:hover .session-actions,...` 那行之后加：

```css
.session:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
```

- [ ] **Step 4: Run unit tests**

Run: `node --test tests/js/*.test.js`
Expected: PASS

- [ ] **Step 5: Add an e2e keyboard path**

`tests/e2e/test_sessions.py` 末尾追加：

```python
def test_sessions_are_reachable_by_keyboard(page, tmp_path, audit_violations):
    from playwright.sync_api import expect

    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.get_by_role("button", name="新会话").click()
        cards = pane.locator("li.session")
        expect(cards).to_have_count(2)

        target_id = cards.nth(1).get_attribute("data-session-id")
        cards.nth(1).focus()
        page.keyboard.press("Enter")
        expect(pane.locator(f'li.session.active[data-session-id="{target_id}"]')).to_have_count(1)

        page.keyboard.press("Tab")
        expect(pane.get_by_role("button", name="改名").first).to_be_visible()
    assert audit_violations == []
```

（`launch_test_harness` 已在该文件顶部导入；若没有，补 `from desk.testing import launch_test_harness`。）

- [ ] **Step 6: Run e2e**

Run: `python3 -m pytest tests/e2e/test_sessions.py -q && python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add desk/static/js/panes/chat.js desk/static/app.css tests/js/chat_pane.test.js tests/e2e/test_sessions.py
git commit -m "fix(ui): session cards are focusable and switch with Enter/Space (G5, P2)"
```

---

### Task 2: 素材文件选择键盘可达；危险确认默认聚焦取消

**Files:**
- Modify: `desk/static/index.html:17,19,24`
- Modify: `desk/static/app.css:129`
- Modify: `desk/static/js/widgets/confirm.js`
- Test: `tests/test_ui_static.py`、`tests/js/confirm.test.js`、`tests/e2e/test_video_flow.py`

**Interfaces:**
- Produces: 三个文件输入保留在 Tab 序列中（无 `hidden` 属性，`class="visually-hidden"`）；`label.file-pick` 在其输入获得焦点时显示焦点环。
- Produces: `confirmDialog({danger: true})` 初始焦点在「取消」；`danger: false` 仍聚焦确认按钮。

- [ ] **Step 1: Write the failing tests**

`tests/test_ui_static.py` 末尾追加（该文件已有读取 `index.html` 的方式；下面直接读文件）：

```python
def test_file_inputs_stay_in_the_tab_order():
    """hidden 的 input 不可聚焦，键盘用户选不了首帧/参考视频（P2）。"""
    import re
    from pathlib import Path

    html = (Path(__file__).resolve().parent.parent / "desk" / "static" / "index.html").read_text(encoding="utf-8")
    inputs = re.findall(r'<input type="file"[^>]*>', html)
    assert len(inputs) == 3
    for tag in inputs:
        assert " hidden" not in tag
        assert 'class="visually-hidden"' in tag
```

`tests/js/confirm.test.js`：把第一个测试名与断言改为危险确认聚焦取消，并追加非危险用例：

```javascript
test("弹层带 role/aria-modal，取消在左确认在右，Esc 等于取消，危险确认默认聚焦取消", async () => {
  const p = confirmDialog(doc, { title: "删除模型", message: "确定？", confirmLabel: "删除" });
  const overlay = doc.body.children.at(-1); const box = overlay.children[0];
  assert.equal(box.attrs.role, "dialog"); assert.equal(box.attrs["aria-modal"], "true");
  const actions = box.children[2]; assert.equal(actions.children[0].textContent, "取消"); assert.equal(actions.children[1].className, "btn-danger");
  assert.equal(actions.children[0].focused, true);
  assert.notEqual(actions.children[1].focused, true);
  doc.listeners.keydown({ key: "Escape" });
  assert.equal(await p, false);
});

test("非危险确认（内存警告、换模型）仍聚焦确认按钮", async () => {
  const p = confirmDialog(doc, { title: "内存警告", message: "可能不足", confirmLabel: "仍要加载", danger: false });
  const actions = doc.body.children.at(-1).children[0].children[2];
  assert.equal(actions.children[1].focused, true);
  doc.listeners.keydown({ key: "Escape" });
  await p;
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_ui_static.py -k tab_order -q; node --test tests/js/confirm.test.js`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

`desk/static/index.html` 三处 `<input type="file" ... hidden>` 去掉末尾的 ` hidden`，在 `type="file"` 后加 `class="visually-hidden"`，例如第 17 行变为：

```html
<div class="file-row"><label class="file-pick"><span class="btn">选择首帧图片</span><input type="file" class="visually-hidden" data-video-first accept="image/png,image/jpeg,image/webp"></label><span class="file-name hint" data-video-first-name>未选择文件</span></div>
```

（第 19、24 行同样处理。）

`desk/static/app.css:129` 行尾追加：

```css
.visually-hidden{position:absolute;width:1px;height:1px;margin:-1px;padding:0;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap;border:0}
.file-pick{position:relative}.file-pick:focus-within .btn{outline:2px solid var(--accent);outline-offset:2px}
```

`desk/static/js/widgets/confirm.js` 最后的 `okBtn.focus?.();` 改为：

```javascript
    // A destructive dialog must not delete on a reflexive Return (cross-exam open thread, F7).
    (danger ? cancelBtn : okBtn).focus?.();
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_ui_static.py -q && node --test tests/js/*.test.js`
Expected: PASS

- [ ] **Step 5: e2e keyboard file pick**

在 `tests/e2e/test_video_flow.py` 末尾追加：

```python
def test_first_frame_picker_is_reachable_by_keyboard(page, tmp_path, audit_violations):
    from playwright.sync_api import expect

    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=video")
        page.locator("[data-video-mode]").select_option("image")
        picker = page.locator("[data-video-first]")
        picker.focus()
        assert page.evaluate("document.activeElement.matches('[data-video-first]')")
        with page.expect_file_chooser() as chooser_info:
            page.keyboard.press("Space")
        chooser_info.value.set_files(files=[{"name": "a.png", "mimeType": "image/png", "buffer": b"\x89PNG\r\n\x1a\n" + b"0" * 64}])
        expect(page.locator("[data-video-first-name]")).to_have_text("a.png")
    assert audit_violations == []
```

（`launch_test_harness` 已在文件顶部导入；若没有，补上。）

- [ ] **Step 6: Run e2e**

Run: `python3 -m pytest tests/e2e/test_video_flow.py -q && python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add desk/static/index.html desk/static/app.css desk/static/js/widgets/confirm.js tests/test_ui_static.py tests/js/confirm.test.js tests/e2e/test_video_flow.py
git commit -m "fix(ui): file pickers are keyboard reachable; destructive dialogs focus 取消 (P2)"
```

---

### Task 3: 2560 宽屏聊天列留白 ≤ 40%

**Files:**
- Modify: `desk/static/app.css:2`（`--chat-col`）
- Test: `tests/e2e/test_chat_layout.py`

**Interfaces:**
- Produces: `--chat-col: clamp(680px, 62vw, 1400px)`。计算：2560 宽时 `.chat-main` = 2560 − 2×24 − 220 − 16 = 2276px，列宽 1400 → 留白 876px = 34.2%；1920 宽列宽 min(1190, 1400) = 1190 → 留白 466px = 24.3%。

- [ ] **Step 1: Write the failing test**

`tests/e2e/test_chat_layout.py` 的 `CASES` 改为覆盖冻结基线的七档宽度：

```python
CASES = [(800, 832, 0.40), (1024, 768, 0.40), (1280, 800, 0.40), (1440, 1000, 0.40),
         (1920, 1200, 0.40), (2240, 1260, 0.40), (2560, 1440, 0.40)]
```

并在文件末尾追加无横向溢出检查：

```python
@pytest.mark.parametrize("width", [800, 2560])
def test_no_horizontal_overflow_at_the_extremes(page, tmp_path, width):
    page.set_viewport_size({"width": width, "height": 900})
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url)
        page.wait_for_selector(".messages")
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/e2e/test_chat_layout.py -q`
Expected: `2560` 档 FAIL（约 46.7%），其余 PASS

- [ ] **Step 3: Write the implementation**

`desk/static/app.css:2` 中 `--chat-col:clamp(680px,62vw,1100px)` 改为 `--chat-col:clamp(680px,62vw,1400px)`。

- [ ] **Step 4: Run e2e**

Run: `python3 -m pytest tests/e2e/test_chat_layout.py -q && python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/app.css tests/e2e/test_chat_layout.py
git commit -m "fix(ui): widen the chat column cap so 2560px keeps whitespace under 40% (G13)"
```

---

### Task 4: 歌曲按成品实际时长标注

**Files:**
- Create: `desk/media/audio.py`
- Modify: `desk/media/service.py`（`_history_entry`）
- Modify: `desk/static/js/panes/library.js`（`summarize`）
- Modify: `desk/static/index.html:30`（时长说明）
- Test: `tests/test_media_audio.py`（新）、`tests/test_media_service.py`、`tests/js/library_pane.test.js`、`tests/test_ui_static.py`

**Interfaces:**
- Produces: `wav_seconds(path: Path) -> float | None`（非 WAV、读失败返回 None；保留两位小数）
- Produces: 音乐作业 `status == "done"` 的历史记录多一个键 `audio_seconds: float | None`；视频记录不变。
- Produces: 素材库歌曲规格：有 `audio_seconds` → `成品 {round} 秒（请求 {duration} 秒）`；否则保持 `{duration}s`。

- [ ] **Step 1: Write the failing tests**

新建 `tests/test_media_audio.py`：

```python
import wave

from desk.media.audio import wav_seconds


def test_wav_seconds_reads_the_real_length(tmp_path):
    path = tmp_path / "a.wav"
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(8000)
        out.writeframes(b"\x00\x00" * 8000 * 3)
    assert wav_seconds(path) == 3.0


def test_wav_seconds_is_none_for_non_wav(tmp_path):
    path = tmp_path / "a.wav"
    path.write_bytes(b"fake-media-bytes")
    assert wav_seconds(path) is None
    assert wav_seconds(tmp_path / "missing.wav") is None
```

`tests/test_media_service.py` 末尾追加：

```python
def test_music_history_records_the_real_output_length(tmp_path, monkeypatch):
    """请求 300 秒、成品 29.7 秒时素材库不能写 300s（cross-exam 2026-09-13 G10）。"""
    import desk.media.service as service_mod

    monkeypatch.setattr(service_mod, "wav_seconds", lambda path: 29.71)
    service, deps = make_service(tmp_path)
    roots = SimpleNamespace(
        outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
        music_python=Path("/fake/bin/music-python"), media_cli_dir=Path("/fake/media"),
        music_env={},
    )
    service._resolve_paths = lambda: roots
    service._probe_capabilities = lambda: {"music_runtime": SimpleNamespace(present=True, detail="")}
    service._list_catalog = lambda: [SimpleNamespace(key="music3", relpath="minimax-music3", gb=27.0)]

    finished_snapshot(service, lambda: service.start_music_job(caption="c", lyrics="l", duration=300))

    assert deps.history.entries[-1]["audio_seconds"] == 29.71
```

`tests/js/library_pane.test.js` 末尾追加（复用文件内 `FakeElement`、`find`）：

```javascript
test("歌曲记录按成品实际时长标注，并注明请求值", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (path) => ({
    ok: true,
    json: async () => path === "/api/outputs"
      ? [{ name: "music3-1.wav", kind: "music", ts: "2026-09-13T10:00:00Z" }]
      : [{ kind: "music", status: "done", ts: "2026-09-13T10:00:00Z", output: "music3-1.wav",
           params: { caption: "民谣", lyrics: "啦", duration: 300 }, audio_seconds: 29.71 }],
  });
  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "player", "list", "error"].map((name) => [name, new FakeElement()]));
  const root = new FakeElement();
  root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-lib-(.+)\]/)[1]];
  const pane = createLibraryPane(root, { applyFill() {} });

  await pane.refresh();

  const meta = find(elements.list.children[0], (el) => el.className === "lib-meta");
  assert.ok(meta.textContent.includes("成品 30 秒（请求 300 秒）"), meta.textContent);
  assert.ok(!meta.textContent.includes("300s"), meta.textContent);
});
```

`tests/test_ui_static.py` 末尾追加：

```python
def test_music_duration_field_explains_the_real_length():
    from pathlib import Path

    html = (Path(__file__).resolve().parent.parent / "desk" / "static" / "index.html").read_text(encoding="utf-8")
    assert "成品时长由模型按歌词决定" in html
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_media_audio.py tests/test_media_service.py tests/test_ui_static.py -q; node --test tests/js/library_pane.test.js`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

新建 `desk/media/audio.py`：

```python
"""Measure what a media worker actually produced, not what was requested (G10)."""
from __future__ import annotations

import wave
from pathlib import Path


def wav_seconds(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as audio:
            rate = audio.getframerate()
            return round(audio.getnframes() / rate, 2) if rate else None
    except (OSError, EOFError, wave.Error):
        return None
```

`desk/media/service.py`：import 区加 `from .audio import wav_seconds`；`_history_entry` 改为：

```python
    def _history_entry(self, snap: dict) -> dict:
        error = snap["error"]
        entry = {"kind": snap["kind"], "status": {"done": "done", "error": "failed", "cancelled": "cancelled"}[snap["status"]],
            "params": snap["params"], "output": snap["output"], "duration_s": snap["finished_at"] - snap["started_at"],
            "error": f"{error['code']}: {error['message']}" if error else None}
        if snap["kind"] == "music" and snap["status"] == "done" and snap["output"]:
            entry["audio_seconds"] = wav_seconds(Path(self._resolve_paths().outputs_root) / snap["output"])
        return entry
```

`desk/static/js/panes/library.js` 的 `summarize` 中音乐分支：

```javascript
      : [params.duration ? `${params.duration}s` : null];
```

改为：

```javascript
      : [Number.isFinite(entry.audio_seconds)
          ? `成品 ${Math.round(entry.audio_seconds)} 秒${params.duration ? `（请求 ${params.duration} 秒）` : ""}`
          : params.duration ? `${params.duration}s` : null];
```

（`summarize(entry)` 的参数名就是 `entry`。）

`desk/static/index.html:30` 的时长 `<label>` 之后插入：

```html
<p class="hint" data-music-duration-note>成品时长由模型按歌词决定，常短于所填时长；素材库会标注实际时长。</p>
```

- [ ] **Step 4: Run tests**

Run: `python3 -m pytest tests/test_media_audio.py tests/test_media_service.py tests/test_ui_static.py -q && node --test tests/js/*.test.js && python3 -m pytest tests/e2e/test_music_flow.py tests/e2e/test_library_panel.py -q`
Expected: PASS（`test_media_service.py:80` 的视频历史精确字典不含 `audio_seconds`，不受影响）

- [ ] **Step 5: Commit**

```bash
git add desk/media/audio.py desk/media/service.py desk/static/js/panes/library.js desk/static/index.html tests/test_media_audio.py tests/test_media_service.py tests/js/library_pane.test.js tests/test_ui_static.py
git commit -m "fix(media): library labels songs with their real length (G10)"
```

---

### Task 5: 外部修改 `#tab=` 时切换标签页

**Files:**
- Modify: `desk/static/js/main.js`（`enterDesk`）
- Test: `tests/e2e/test_tabs_hash.py`（新）

**Interfaces:**
- Consumes: `initialTab(hash)`（`pure/tab_hash.js`，已存在）
- Produces: `hashchange` 时若解析出的标签页与当前不同则 `showTab`（`showTab` 自己 `replaceState`，不会再触发 `hashchange`）。

- [ ] **Step 1: Write the failing e2e test**

新建 `tests/e2e/test_tabs_hash.py`：

```python
"""Restoring a #tab fragment from outside (a link, the native shell) switches the pane."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness


def test_hashchange_switches_the_visible_pane(page, tmp_path, audit_violations):
    with launch_test_harness(tmp_path) as harness:
        page.goto(harness.base_url + "#tab=library")
        expect(page.locator("#pane-library")).to_be_visible()

        page.evaluate("location.hash = '#tab=chat'")
        expect(page.locator("#pane-chat")).to_be_visible()
        expect(page.locator("#pane-library")).to_be_hidden()

        page.evaluate("location.hash = '#tab=music'")
        expect(page.locator("#pane-music")).to_be_visible()
    assert audit_violations == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/e2e/test_tabs_hash.py -q`
Expected: FAIL（改 hash 后仍停在素材库）

- [ ] **Step 3: Write the implementation**

`desk/static/js/main.js` 的 `enterDesk()` 里，`for (const button of document.querySelectorAll("#tabs [data-tab]")) ...` 那行之后加：

```javascript
    globalThis.addEventListener?.("hashchange", () => {
      const wanted = initialTab(globalThis.location?.hash);
      if (wanted !== activeTab) showTab(wanted);
    });
```

`store` 只有 `set`（`get` 已在 2026-09-08 删除），所以用模块级变量记当前标签：`main.js:20` 行尾加 ` let activeTab = "chat";`，`showTab(name)` 函数体第一行加 `activeTab = name;`。

- [ ] **Step 4: Run e2e**

Run: `python3 -m pytest tests/e2e/test_tabs_hash.py -q && python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/main.js tests/e2e/test_tabs_hash.py
git commit -m "fix(ui): changing #tab from outside switches the pane"
```
