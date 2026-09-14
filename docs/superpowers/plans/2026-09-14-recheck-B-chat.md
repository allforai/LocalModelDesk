# Cross-Exam 2026-09-13 修复 · B 聊天 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 推理模型不再"想完了却没有回答"；回答不管以什么方式中断，问句和已输出内容都留在会话里、标明原因、可一键重试；驱逐提示在媒体作业结束后不再是橙色告警。

**Architecture:** 服务端两处：`LlmService._upstream_payload` 在请求没带 `max_tokens` 时补上 `DEFAULT_CHAT_MAX_TOKENS`（面板和网关同时受益）；`_stream_events` 在上游断流时查看自身状态，被驱逐就发 `evicted` 而不是 `upstream_error`。前端 `chat.js` 把 `send()` 拆成"写入问句"与 `streamReply(session)` 两段：结束时无论成功、截断还是中断都把助手消息推进会话并 PATCH，中断的消息带 `interrupted` 字段；发给模型的历史经纯函数 `wireMessages` 只留 role/content。

**Tech Stack:** Python 3.13 stdlib · 零依赖 ES modules · node:test · Playwright（pytest-playwright 1.62）

**Spec:** `docs/cross-exam/2026-09-13-localmodeldesk-recheck/completion-report.md` §缺口清单 J1、G15、G11，§缺陷模式 P3（10 位点），未拉的线「流结束后思考摘要仍显示思考中」「媒体作业结束后仍持续橙色」「模型根为空时加载按钮外观可用」；证据 `evidence/q17/`、`evidence/q24/`、`evidence/q25/`、`evidence/q41/`。需求：`docs/superpowers/specs/2026-08-31-llm-spec.md` R-llm-05/06，`2026-08-31-ui-spec.md` R-ui-02、R-ui-08。

## Global Constraints

- Python：`desk/` 内禁止第三方包（stdlib only）。
- 前端：零依赖 ES modules；一律 `createElement` / `textContent`，禁止 `innerHTML`。
- 所有面向用户的字符串是简体中文；机器码（如 `upstream_error`）永远不作为唯一解释出现。
- 测试命令：`python3 -m pytest -q`、`node --test tests/js/*.test.js`、`python3 -m pytest tests/e2e -q`。
- 验证门必须包含 e2e：`desk/static/` 任一改动，提交前跑 `python3 -m pytest tests/e2e -q`（fake DOM 单测曾漏掉真浏览器崩溃）。
- 测试永不触碰 `~/LocalModelDesk` 模型权重或真实数据根：一律 `tmp_path` + harness。
- 每个任务结束后提交，commit message 末尾带两行 trailer：
  `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`
  `Claude-Session: https://claude.ai/code/session_017SVdZi6MbtQeTc87fBLvUx`

## File Structure

| 文件 | 本计划中触及的职责 |
|---|---|
| `desk/llm/state.py` | 新增常量 `DEFAULT_CHAT_MAX_TOKENS = 8192` |
| `desk/llm/service.py` | 默认 `max_tokens`；断流时按状态区分 `evicted` |
| `desk/app.py` | SSE 写入时客户端断开：停止迭代并关闭生成器，不打 traceback |
| `desk/testing/scripts.py`、`desk/testing/fakes.py` | 新增 `Break` 步骤：让 e2e 能模拟上游断流 |
| `desk/static/js/pure/chat_stream.js` | 新增 `wireMessages(messages)` |
| `desk/static/js/api.js` | `updateChatSession(id, patch, { keepalive })` |
| `desk/static/js/panes/chat.js` | `streamReply`、中断持久化与重试、长度截断提示、思考时长、驱逐徽章、无模型时禁用加载、`pagehide` 保存 |
| `desk/static/js/main.js` | `applyLlmStatus(llm, deskState)` |
| `desk/static/app.css` | `.retry-row` 布局 |

---

### Task 1: 请求未带 max_tokens 时补默认上限

**Files:**
- Modify: `desk/llm/state.py`（常量区）
- Modify: `desk/llm/service.py`（`_upstream_payload`）
- Test: `tests/llm/test_llm_chat_stream.py`、`tests/llm/test_llm_chat_completion.py`

**Interfaces:**
- Produces: `DEFAULT_CHAT_MAX_TOKENS = 8192`（`desk.llm.state`）
- Produces: 上游 payload 永远带 `max_tokens`；调用方给了就原样用。

- [ ] **Step 1: Write the failing test**

在 `tests/llm/test_llm_chat_stream.py` 末尾追加：

```python
def test_stream_supplies_default_max_tokens_when_request_omits_it(tmp_path):
    """mlx_lm 默认 512 token，推理模型会把预算全花在思考上（cross-exam 2026-09-13 J1/G15）。"""
    from desk.llm.state import DEFAULT_CHAT_MAX_TOKENS

    testbed = make_loaded(tmp_path, backend_kw={"chunks": CONTENT_CHUNKS})
    list(testbed.service.chat_stream({"messages": []}))
    _, _, payload = next(call for call in testbed.calls if call[0] == "chat_stream")
    assert payload["max_tokens"] == DEFAULT_CHAT_MAX_TOKENS == 8192


def test_stream_keeps_caller_max_tokens(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chunks": CONTENT_CHUNKS})
    list(testbed.service.chat_stream({"messages": [], "max_tokens": 64}))
    _, _, payload = next(call for call in testbed.calls if call[0] == "chat_stream")
    assert payload["max_tokens"] == 64
```

在 `tests/llm/test_llm_chat_completion.py` 末尾追加（该文件已导入 `make_loaded`；若没有，补 `from tests.llm.llm_fakes import make_loaded`）：

```python
def test_completion_supplies_default_max_tokens(tmp_path):
    from desk.llm.state import DEFAULT_CHAT_MAX_TOKENS

    testbed = make_loaded(tmp_path, backend_kw={"chat_result": {
        "choices": [{"message": {"content": "答"}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 1},
    }})
    testbed.service.chat_completion({"messages": []})
    _, _, payload = next(call for call in testbed.calls if call[0] == "chat")
    assert payload["max_tokens"] == DEFAULT_CHAT_MAX_TOKENS
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/llm/test_llm_chat_stream.py tests/llm/test_llm_chat_completion.py -k max_tokens -q`
Expected: FAIL，`ImportError: cannot import name 'DEFAULT_CHAT_MAX_TOKENS'`

- [ ] **Step 3: Write minimal implementation**

`desk/llm/state.py` 在 `DEFAULT_LLM_PORT = 8767` 下一行加：

```python
# mlx_lm.server falls back to 512 tokens, which a reasoning model can spend
# entirely on thinking and return an empty answer (cross-exam 2026-09-13 J1).
DEFAULT_CHAT_MAX_TOKENS = 8192
```

`desk/llm/service.py`：从 `.state` 的 import 列表加入 `DEFAULT_CHAT_MAX_TOKENS`，`_upstream_payload` 改为：

```python
    @staticmethod
    def _upstream_payload(request: dict[str, Any], entry: Any) -> dict[str, Any]:
        # mlx_lm.server maps this stable alias to the model supplied on its
        # command line. Sending the public HF repository id makes it resolve
        # and download a second model from the Hub instead of using the
        # already resident local path.
        payload: dict[str, Any] = {"model": "default_model", "messages": request["messages"]}
        for key in ("temperature", "top_p", "max_tokens"):
            if request.get(key) is not None:
                payload[key] = request[key]
        payload.setdefault("max_tokens", DEFAULT_CHAT_MAX_TOKENS)
        return payload
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/llm tests/test_gateway_openai.py tests/test_gateway_anthropic.py -q`
Expected: PASS（若网关测试逐字断言上游 payload 不含 `max_tokens`，把期望改为含 `"max_tokens": 8192`）

- [ ] **Step 5: Commit**

```bash
git add desk/llm/state.py desk/llm/service.py tests/llm/test_llm_chat_stream.py tests/llm/test_llm_chat_completion.py tests/test_gateway_*.py
git commit -m "fix(llm): default max_tokens so reasoning models still answer (J1, G15)"
```

---

### Task 2: 流被驱逐打断时报 evicted

**Files:**
- Modify: `desk/llm/service.py`（`_stream_events`）
- Test: `tests/llm/test_llm_chat_stream.py`

**Interfaces:**
- Consumes: `ERR_EVICTED`（`desk.llm.state`，已存在）
- Produces: 断流且服务状态的 `error.code == "evicted"` 时，末帧为 `{"type": "error", "code": "evicted", "message": "内存让给了媒体作业，回答被中断"}`

- [ ] **Step 1: Write the failing test**

```python
def test_stream_cut_by_eviction_reports_evicted_not_upstream_error(tmp_path):
    testbed = make_loaded(
        tmp_path, backend_kw={"chunks": CONTENT_CHUNKS[:2], "stream_error_after": 1}
    )
    events = testbed.service.chat_stream({"messages": []})
    first = next(events)
    testbed.arbiter.emit({"holder": {"kind": "media", "label": "h3"}, "media_busy": True})

    rest = list(events)

    assert first["type"] == "delta"
    assert rest[-1] == {"type": "error", "code": "evicted", "message": "内存让给了媒体作业，回答被中断"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/llm/test_llm_chat_stream.py -k eviction -q`
Expected: FAIL，末帧 `code` 为 `upstream_error`

- [ ] **Step 3: Write minimal implementation**

`desk/llm/service.py`：import 列表加 `ERR_EVICTED`（若尚未导入）。在 `_stream_events` 上方新增：

```python
    def _interruption_event(self, fallback_message: str) -> dict[str, Any]:
        """Name the real cause when the resident model was taken away mid-stream."""
        with self._lock:
            error = self._state.error
        if error is not None and error.code == ERR_EVICTED:
            return error_event(ERR_EVICTED, "内存让给了媒体作业，回答被中断")
        return error_event(ERR_UPSTREAM_ERROR, fallback_message)
```

并把 `_stream_events` 的两处错误出口改为：

```python
        except BackendHttpError as exc:
            yield self._interruption_event(str(exc))
            return
        if usage is None or finish_reason is None:
            yield self._interruption_event("上游流终止但缺 usage/finish_reason")
            return
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/llm -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/llm/service.py tests/llm/test_llm_chat_stream.py
git commit -m "fix(llm): a stream cut by eviction says so instead of upstream_error (P3 path 9)"
```

---

### Task 3: SSE 客户端断开不再抛进日志、及时停止上游

**Files:**
- Modify: `desk/app.py:114-126`（`_send_response` 的 SSE 分支）
- Test: `tests/test_foundation_routes.py`

**Interfaces:**
- Produces: 写 SSE 帧遇到 `BrokenPipeError` / `ConnectionResetError` 时停止迭代，并调用生成器的 `close()`（让 `LlmService._stream_events` 里 `for chunk in backend.chat_stream(...)` 的上游连接随之关闭）。

- [ ] **Step 1: Write the failing test**

在 `tests/test_foundation_routes.py` 末尾追加：

```python
def test_sse_client_disconnect_closes_the_event_generator():
    import socket
    import threading

    from desk.app import DeskApp, Response

    closed = threading.Event()

    def events():
        try:
            for index in range(10_000):
                yield {"type": "delta", "text": "x" * 512, "index": index}
        finally:
            closed.set()

    app = DeskApp(port=0)
    app.add_routes([("GET", "/sse", lambda _req: Response(sse=events()))])
    app.start_background()
    try:
        with socket.create_connection(("127.0.0.1", app.port), timeout=5) as sock:
            sock.sendall(b"GET /sse HTTP/1.1\r\nHost: x\r\n\r\n")
            sock.recv(1024)
        assert closed.wait(5.0)
    finally:
        app.shutdown()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_foundation_routes.py -k disconnect -q`
Expected: FAIL（`closed.wait` 超时，或断言失败；日志里有 `BrokenPipeError` traceback）

- [ ] **Step 3: Write minimal implementation**

把 `desk/app.py` SSE 分支里的循环替换为：

```python
                    events = response.sse
                    try:
                        for event in events:
                            frame = b"data: " + json.dumps(
                                event, ensure_ascii=False
                            ).encode("utf-8") + b"\n\n"
                            self.wfile.write(frame)
                            self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        log.info("sse client went away on %s", self.path)
                    finally:
                        close = getattr(events, "close", None)
                        if callable(close):
                            close()
                    return
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_foundation_routes.py tests/llm -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/app.py tests/test_foundation_routes.py
git commit -m "fix(app): stop the upstream stream when the SSE client disconnects (P3 path 10)"
```

---

### Task 4: 发给模型的历史只含 role/content

**Files:**
- Modify: `desk/static/js/pure/chat_stream.js`
- Test: `tests/js/chat_stream.test.js`

**Interfaces:**
- Produces: `wireMessages(messages: Array<{role, content, reasoning?, thinking_s?, interrupted?}>) -> Array<{role, content}>` —— 丢弃"中断且无正文"的助手消息；其余只保留 `role` 与 `content`（`content` 缺省为 `""`）。

- [ ] **Step 1: Write the failing test**

在 `tests/js/chat_stream.test.js` 末尾追加（文件顶部已 `import test` 与 `assert`）：

```javascript
test("wireMessages 只发 role/content，并跳过没有正文的中断回答", async () => {
  const { wireMessages } = await import("../../desk/static/js/pure/chat_stream.js");
  const history = [
    { role: "user", content: "问一" },
    { role: "assistant", content: "答一", reasoning: "想", thinking_s: 3 },
    { role: "user", content: "问二" },
    { role: "assistant", content: "", reasoning: "想了一半", interrupted: { code: "evicted", message: "让出内存" } },
    { role: "user", content: "问三" },
    { role: "assistant", content: "半句", interrupted: { code: "upstream_error", message: "断流" } },
  ];
  assert.deepEqual(wireMessages(history), [
    { role: "user", content: "问一" },
    { role: "assistant", content: "答一" },
    { role: "user", content: "问二" },
    { role: "user", content: "问三" },
    { role: "assistant", content: "半句" },
  ]);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/js/chat_stream.test.js`
Expected: FAIL，`wireMessages is not a function`

- [ ] **Step 3: Write minimal implementation**

`desk/static/js/pure/chat_stream.js` 末尾追加：

```javascript
// 发给模型的历史：只要 role/content；中断且一个字都没出的回答不算一轮（P3）。
export function wireMessages(messages) {
  return messages
    .filter((message) => !(message.role === "assistant" && message.interrupted && !(message.content ?? "").trim()))
    .map((message) => ({ role: message.role, content: message.content ?? "" }));
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/js/chat_stream.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/pure/chat_stream.js tests/js/chat_stream.test.js
git commit -m "feat(ui): wireMessages keeps model history to role/content"
```

---

### Task 5: 回答结束的三种结局都写回会话（完成 / 截断 / 中断）并可重试

**Files:**
- Modify: `desk/static/js/panes/chat.js`（`send`、`messageNode`、`showMessages`，新增 `streamReply`、`appendRetry`）
- Modify: `desk/static/app.css`（`.retry-row`）
- Test: `tests/js/chat_pane.test.js`（改写 `an interrupted answer is labelled, not left mid-thought`，新增两个测试）

**Interfaces:**
- Consumes: `wireMessages`（Task 4）
- Produces: 会话消息新字段 `interrupted: {code: string, message: string}` 与 `truncated: true`（服务端 `SessionStore.update` 的 `messages` 是自由列表，无需改服务端）。
- Produces: 最后一条为中断回答时，消息区末尾有 `button[data-retry]`「重试」；点击移除该中断回答并用相同历史重新生成。

- [ ] **Step 1: Write the failing tests**

把 `tests/js/chat_pane.test.js` 中 `test("an interrupted answer is labelled, not left mid-thought", ...)` 整个替换为：

```javascript
test("中断的回答带原因写回会话，并出现重试按钮（P3）", async () => {
  const oldFetch = globalThis.fetch;
  const patches = [];
  const streamBodies = [];
  let streamCalls = 0;
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([{ id: "s1", title: "t", messages: [], updated: "2026-01-01" }]);
    if (path === "/api/llm/chat/stream") {
      streamCalls += 1;
      streamBodies.push(JSON.parse(options.body).messages);
      if (streamCalls === 1) return stream(['{"type":"delta","reasoning":"想了一半"}', '{"type":"error","code":"evicted","message":"内存让给了媒体作业，回答被中断"}']);
      return stream(['{"type":"delta","text":"好的"}', '{"type":"done","finish_reason":"stop"}']);
    }
    if (path === "/api/sessions/s1") { patches.push(JSON.parse(options.body)); return json({ id: "s1", title: "t", updated: `2026-01-0${patches.length + 1}`, ...patches.at(-1) }); }
    throw new Error(`unexpected request ${path} ${options.method ?? "GET"}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    controls.get("[data-chat-input]").value = "你好";
    await controls.get("[data-send]").click();

    const messagesEl = controls.get("[data-messages]");
    const assistant = messagesEl.children[1];
    assert.ok(assistant.children[1].children[0].textContent.includes("已中断"));
    assert.equal(assistant.children[2].children[0].className, "empty-answer");
    assert.equal(controls.get("[data-send]").disabled, false);
    assert.deepEqual(patches[0].messages, [
      { role: "user", content: "你好" },
      { role: "assistant", content: "", reasoning: "想了一半", thinking_s: patches[0].messages[1].thinking_s,
        interrupted: { code: "evicted", message: "内存让给了媒体作业，回答被中断" } },
    ]);

    const retryRow = messagesEl.children.at(-1);
    const retry = retryRow.children[0];
    assert.equal(retry.dataset.retry, "1");
    assert.equal(retry.textContent, "重试");
    await retry.click();

    assert.deepEqual(streamBodies[1], [{ role: "user", content: "你好" }]);
    assert.deepEqual(patches.at(-1).messages, [
      { role: "user", content: "你好" },
      { role: "assistant", content: "好的" },
    ]);
  } finally { globalThis.fetch = oldFetch; }
});

test("推理用完预算只剩思考时：摘要给出时长，正文说明没有回答并提示截断", async () => {
  const oldFetch = globalThis.fetch;
  const patches = [];
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([{ id: "s1", title: "t", messages: [], updated: "2026-01-01" }]);
    if (path === "/api/llm/chat/stream") return stream(['{"type":"delta","reasoning":"一直在想"}', '{"type":"done","finish_reason":"length"}']);
    if (path === "/api/sessions/s1") { patches.push(JSON.parse(options.body)); return json({ id: "s1", title: "t", updated: "2026-01-02", ...patches.at(-1) }); }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    controls.get("[data-chat-input]").value = "你好";
    await controls.get("[data-send]").click();

    const assistant = controls.get("[data-messages]").children[1];
    assert.match(assistant.children[1].children[0].textContent, /^已思考 \d+ 秒$/);
    assert.equal(assistant.children[2].children[0].textContent, "模型只输出了思考，没有给出回答。");
    assert.equal(assistant.children[3].textContent, "已达到长度上限，回答被截断。");
    assert.equal(patches[0].messages[1].truncated, true);
  } finally { globalThis.fetch = oldFetch; }
});

test("从会话历史打开时，最后一条中断回答显示原因与重试按钮", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.showMessages([
    { role: "user", content: "你好" },
    { role: "assistant", content: "半句", interrupted: { code: "upstream_error", message: "上游断流" } },
  ]);
  const messagesEl = controls.get("[data-messages]");
  const assistant = messagesEl.children[1];
  assert.equal(assistant.children[3].textContent, "回答没有生成完：上游断流");
  assert.equal(messagesEl.children.at(-1).children[0].textContent, "重试");
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/chat_pane.test.js`
Expected: 3 个新测试 FAIL（没有 PATCH、没有重试按钮、正文文案不符）

- [ ] **Step 3: Write the implementation**

`desk/static/js/panes/chat.js`：

1. import 行改为：

```javascript
import { initialStream, reduceChunk, wireMessages } from "../pure/chat_stream.js";
```

2. 在 `messageNode` 里 `const errorEl = doc.createElement("p"); errorEl.className = "inline-error";` 之后加入：

```javascript
    if (!live && message.interrupted) errorEl.textContent = `回答没有生成完：${message.interrupted.message}`;
    else if (!live && message.truncated) errorEl.textContent = "已达到长度上限，回答被截断。";
```

3. `showMessages` 末尾（`for` 循环之后）加入：

```javascript
    if (list.at(-1)?.interrupted) appendRetry();
```

4. 在 `showMessages` 之前新增：

```javascript
  function appendRetry() {
    const row = doc.createElement("div");
    row.className = "retry-row";
    const button = doc.createElement("button");
    (button.dataset ??= {}).retry = "1";
    button.textContent = "重试";
    button.addEventListener("click", () => retry());
    row.append(button);
    els.messages.append(row);
  }

  async function retry() {
    const session = current();
    if (streaming || !session?.messages?.at(-1)?.interrupted) return;
    session.messages.pop();
    renderMessages();
    await streamReply(session);
  }
```

5. 用下面整段替换现有 `send()`：

```javascript
  async function send() {
    if (streaming) return;
    const text = els.input.value.trim();
    const session = current();
    if (!text || !session) return;
    setError("");
    session.messages = session.messages ?? [];
    if (session.messages.length === 0) els.messages.replaceChildren();
    session.messages.push({ role: "user", content: text });
    els.input.value = "";
    messageNode({ role: "user", content: text });
    await streamReply(session);
  }

  // One reply, from first frame to saved turn. Every ending — done, truncated,
  // interrupted — is pushed into the session and saved (P3).
  async function streamReply(session) {
    setError("");
    const live = messageNode({ role: "assistant", content: "", reasoning: "" }, true);
    streaming = true;
    els.sendBtn.disabled = true;
    setButtonLabel(els.sendBtn, "生成中…");
    els.messages.dataset.streaming = "1";
    const thinkStart = Date.now();
    const elapsed = () => Math.round((Date.now() - thinkStart) / 1000);
    let firstContentSeen = false;
    let thinkingSeconds = 0;
    let state = initialStream();
    liveTurn = { session, state };
    try {
      const body = await api.chatStream(wireMessages(session.messages));
      for await (const line of sseDataLines(body)) {
        state = reduceChunk(state, line);
        liveTurn.state = state;
        live.reasoningEl.replaceChildren(renderMarkdown(doc, state.reasoning));
        live.details.hidden = !state.reasoning;
        if (state.content && !firstContentSeen) {
          firstContentSeen = true;
          thinkingSeconds = elapsed();
          live.summary.textContent = `已思考 ${thinkingSeconds} 秒`;
          live.details.open = false;
        }
        live.contentEl.replaceChildren(renderMarkdown(doc, state.content));
        if (state.done || state.error) break;
      }
      if (!state.done && !state.error) state = { ...state, error: { code: "stream_interrupted", message: "连接在回答完成前断开" } };
    } catch (error) {
      state = { ...state, error: { code: error.code ?? "stream_error", message: error.message } };
    } finally {
      liveTurn = null;
      streaming = false;
      els.sendBtn.disabled = false;
      setButtonLabel(els.sendBtn, "发送");
      delete els.messages.dataset.streaming;
    }
    if (!firstContentSeen && state.reasoning) thinkingSeconds = elapsed();
    const assistant = { role: "assistant", content: state.content };
    if (state.reasoning) { assistant.reasoning = state.reasoning; assistant.thinking_s = thinkingSeconds; }
    if (state.error) {
      // Widewin gap #1 / P3: label it plainly, keep what was said, offer a retry.
      assistant.interrupted = { code: state.error.code, message: state.error.message };
      live.summary.textContent = state.error.code === "evicted" ? "已中断：内存让给了媒体作业" : "已中断";
      live.details.open = false;
      if (!state.content) {
        const note = doc.createElement("p");
        note.className = "empty-answer";
        note.textContent = "这条回答没有生成完，可点「重试」重新生成。";
        live.contentEl.replaceChildren(note);
      }
      live.errorEl.textContent = `回答没有生成完：${state.error.message}`;
    } else {
      if (state.reasoning && !firstContentSeen) live.summary.textContent = `已思考 ${Math.max(1, thinkingSeconds)} 秒`;
      if (!state.content) {
        const note = doc.createElement("p");
        note.className = "empty-answer";
        note.textContent = state.reasoning ? "模型只输出了思考，没有给出回答。" : "（这条回答没有内容）";
        live.contentEl.replaceChildren(note);
      }
      if (state.finishReason === "length") {
        assistant.truncated = true;
        live.errorEl.textContent = "已达到长度上限，回答被截断。";
      }
    }
    session.messages.push(assistant);
    if (state.error && currentId === session.id) appendRetry();
    try {
      const updated = await api.updateChatSession(session.id, { messages: session.messages, model: els.modelSelect.value || null });
      sessions = sortSessions(sessions.map((item) => item.id === updated.id ? updated : item));
      renderSessionList();
    } catch (error) { setError(`会话保存失败：${error.message}`); }
  }
```

6. 在 `let llmStatus = "idle";` 下一行声明：

```javascript
  let liveTurn = null; // { session, state } while a reply is streaming — read by the pagehide saver
```

`desk/static/app.css` 末尾追加：

```css
.retry-row{display:flex;justify-content:flex-start;padding-block:4px}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/js/*.test.js`
Expected: PASS。原测试「chat 面板发送流式回复」断言的 PATCH 仍是 `{ role:"assistant", content:"你好", reasoning:"先想", thinking_s:0 }`（完成的回答不带 `interrupted`/`truncated` 键）。

- [ ] **Step 5: Add the e2e break step**

`desk/testing/scripts.py` 在 `class Done` 之后加：

```python
@dataclass(frozen=True)
class Break:
    """Upstream connection drops mid-stream."""
    message: str = "fake upstream dropped"
```

`desk/testing/fakes.py`：import 处加入 `Break`（与 `Delta, Done` 同一 import），并 `from desk.llm.backend import BackendHttpError`；`_iter_steps` 的类型判断改为 `elif isinstance(step, (Delta, Done, Break)):`；`chat_stream` 循环体最前面加：

```python
            if isinstance(step, Break):
                raise BackendHttpError(step.message)
```

`chat()` 循环里加 `elif isinstance(step, Break): raise BackendHttpError(step.message)`（放在 `if isinstance(step, Delta)` 分支之后、`else` 之前）。`desk/testing/__init__.py` 只导出 harness，不用改。

- [ ] **Step 6: Write the e2e test**

新建 `tests/e2e/test_chat_interrupted.py`：

```python
"""P3: an answer cut off mid-stream keeps the question and partial text in the session."""
from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import Break, ChatScript, Delta, Gate


def test_interrupted_answer_is_persisted_and_labelled(page, tmp_path, audit_violations, wait_until):
    script = ChatScript([Delta(content="半句话"), Gate(), Break("上游断开")])
    with launch_test_harness(tmp_path, chat_script=script) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.locator("[data-model-select]").select_option("glm")
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")

        pane.locator("[data-chat-input]").fill("你好")
        pane.get_by_role("button", name="发送").click()
        expect(pane.locator(".msg-assistant .md").last).to_have_text("半句话")
        harness.chat_script.step()

        expect(pane.locator(".msg-assistant .inline-error").last).to_contain_text("回答没有生成完")
        expect(pane.get_by_role("button", name="重试")).to_be_visible()

        def persisted():
            sessions = harness.library.list_chat_sessions()
            messages = sessions[0]["messages"] if sessions else []
            return (len(messages) == 2 and messages[0]["content"] == "你好"
                    and messages[1]["content"] == "半句话"
                    and messages[1].get("interrupted", {}).get("message"))

        wait_until(persisted)
        page.reload()
        expect(page.locator("#pane-chat .msg-assistant .inline-error").last).to_contain_text("回答没有生成完")
    assert audit_violations == []
```

- [ ] **Step 7: Run e2e**

Run: `python3 -m pytest tests/e2e/test_chat_interrupted.py tests/e2e/test_chat_stream.py tests/e2e/test_sessions.py -q`
Expected: PASS；然后跑全量 `python3 -m pytest tests/e2e -q` 仍 PASS。

- [ ] **Step 8: Commit**

```bash
git add desk/static/js/panes/chat.js desk/static/app.css desk/testing/scripts.py desk/testing/fakes.py tests/js/chat_pane.test.js tests/e2e/test_chat_interrupted.py
git commit -m "fix(ui): every reply ending is saved; interrupted turns keep their text and can retry (P3, G11)"
```

---

### Task 6: 页面关闭时正在流的回答也写回会话

**Files:**
- Modify: `desk/static/js/api.js`（`request` 支持 `keepalive`；`updateChatSession` 第三参数）
- Modify: `desk/static/js/panes/chat.js`（注册 `pagehide`）
- Test: `tests/js/api.test.js`、`tests/js/chat_pane.test.js`

**Interfaces:**
- Consumes: `liveTurn`（Task 5）
- Produces: `api.updateChatSession(id, patch, { keepalive = false } = {})`
- Produces: `createChatPane(root, { window })` —— `ctx.window` 缺省为 `globalThis`；监听其 `pagehide`。

- [ ] **Step 1: Write the failing tests**

`tests/js/api.test.js` 末尾追加：

```javascript
test("updateChatSession 可带 keepalive，页面关闭时请求不被浏览器丢弃", async () => {
  const oldFetch = globalThis.fetch;
  const seen = [];
  globalThis.fetch = async (path, options) => { seen.push([path, options]); return new Response("{}", { status: 200 }); };
  try {
    const api = await import("../../desk/static/js/api.js");
    await api.updateChatSession("s1", { messages: [] }, { keepalive: true });
    assert.equal(seen[0][0], "/api/sessions/s1");
    assert.equal(seen[0][1].method, "PATCH");
    assert.equal(seen[0][1].keepalive, true);
  } finally { globalThis.fetch = oldFetch; }
});
```

`tests/js/chat_pane.test.js` 末尾追加：

```javascript
test("流式中页面关闭：把问句和已出的半句带 keepalive 写回会话（P3 路径 6）", async () => {
  const oldFetch = globalThis.fetch;
  const saved = [];
  let releaseStream;
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([{ id: "s1", title: "t", messages: [], updated: "2026-01-01" }]);
    if (path === "/api/llm/chat/stream") {
      return new Response(new ReadableStream({ start(controller) {
        controller.enqueue(new TextEncoder().encode('data: {"type":"delta","text":"半句"}\n\n'));
        releaseStream = () => controller.close();
      } }), { status: 200 });
    }
    if (path === "/api/sessions/s1") { saved.push([JSON.parse(options.body), options.keepalive]); return json({ id: "s1", title: "t", updated: "2026-01-02" }); }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const listeners = {};
    const pane = createChatPane(root, { window: { addEventListener: (type, fn) => { listeners[type] = fn; } } });
    await pane.init();
    controls.get("[data-chat-input]").value = "你好";
    const sending = controls.get("[data-send]").click();
    await new Promise((resolve) => setTimeout(resolve, 20));

    listeners.pagehide();

    assert.equal(saved[0][1], true);
    assert.deepEqual(saved[0][0].messages, [
      { role: "user", content: "你好" },
      { role: "assistant", content: "半句", interrupted: { code: "page_closed", message: "页面关闭时回答还没生成完" } },
    ]);
    releaseStream();
    await sending;
  } finally { globalThis.fetch = oldFetch; }
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/api.test.js tests/js/chat_pane.test.js`
Expected: FAIL（`keepalive` 为 undefined；`listeners.pagehide` 不是函数）

- [ ] **Step 3: Write the implementation**

`desk/static/js/api.js`：

```javascript
async function request(path, { method = "GET", body, stream = false, keepalive = false } = {}) {
  const options = { method };
  if (keepalive) options.keepalive = true;
```

（函数其余部分不变。）并把 `updateChatSession` 改为：

```javascript
export const updateChatSession = (id, patch, { keepalive = false } = {}) =>
  request(`${ROUTES.sessions}/${encoded(id)}`, { method: "PATCH", body: patch, keepalive });
```

`desk/static/js/panes/chat.js`：在 `els.sendBtn.addEventListener("click", send);` 之前加入：

```javascript
  // Closing or reloading the page mid-reply must not lose the question (P3 path 6).
  function saveLiveTurnOnPageHide() {
    if (!liveTurn) return;
    const { session, state } = liveTurn;
    const partial = { role: "assistant", content: state.content };
    if (state.reasoning) partial.reasoning = state.reasoning;
    partial.interrupted = { code: "page_closed", message: "页面关闭时回答还没生成完" };
    api.updateChatSession(session.id, { messages: [...session.messages, partial], model: els.modelSelect.value || null }, { keepalive: true })
      .catch(() => {});
  }
  (ctx.window ?? globalThis).addEventListener?.("pagehide", saveLiveTurnOnPageHide);
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/js/*.test.js && python3 -m pytest tests/e2e -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/api.js desk/static/js/panes/chat.js tests/js/api.test.js tests/js/chat_pane.test.js
git commit -m "fix(ui): save the streaming turn with keepalive when the page closes (P3 path 6)"
```

---

### Task 7: 驱逐徽章在媒体作业结束后变为中性；没有已下载模型时加载按钮禁用并说明

**Files:**
- Modify: `desk/static/js/panes/chat.js`（`renderLlm`、`refreshModels`、`setHeavyAllowed`）
- Modify: `desk/static/js/main.js:107`
- Test: `tests/js/chat_pane.test.js`

**Interfaces:**
- Produces: `applyLlmStatus(payload, deskState?)` —— `deskState` 缺省视为"重活仍被占用"（向后兼容现有调用）。
- Produces: `refreshModels()` 之后若没有任何 `present` 的聊天模型，`[data-load]` 禁用，`[data-load-hint]` 为「还没有下载好的聊天模型，去「资源」页下载」；互斥原因优先显示。

- [ ] **Step 1: Write the failing tests**

```javascript
test("媒体作业已结束时，被驱逐状态显示中性徽章和可重新加载", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  const evicted = { state: { status: "error", model_key: "glm", error: { code: "evicted", message: "让出内存" } } };
  pane.applyLlmStatus(evicted, { holder: { kind: "media", label: "h3" }, media_busy: true });
  assert.ok(controls.get("[data-model-state]").className.includes("badge-busy"));
  pane.applyLlmStatus(evicted, { holder: null, media_busy: false });
  assert.ok(controls.get("[data-model-state]").className.includes("badge-none"));
  assert.equal(controls.get("[data-model-state]").textContent, "媒体任务已结束，可重新加载");
});

test("没有下载好的聊天模型时加载按钮禁用并指向资源页", async () => {
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async (path) => {
    if (path === "/api/resources/catalog") return json([{ key: "glm", group: "chat", name: "GLM", gb: 60 }]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [{ key: "glm", state: "missing" }] });
    if (path === "/api/resources/download") return json({});
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.refreshModels();
    pane.setHeavyAllowed(true, "");
    assert.equal(controls.get("[data-load]").disabled, true);
    assert.equal(controls.get("[data-load-hint]").textContent, "还没有下载好的聊天模型，去「资源」页下载");
    pane.setHeavyAllowed(false, "媒体作业进行中");
    assert.equal(controls.get("[data-load-hint]").textContent, "媒体作业进行中");
  } finally { globalThis.fetch = oldFetch; }
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/chat_pane.test.js`
Expected: 两个新测试 FAIL

- [ ] **Step 3: Write the implementation**

`desk/static/js/panes/chat.js`：

在 `let liveTurn = null;` 下方声明：

```javascript
  let readyModels = null; // null until the catalog has been read once
  let heavyAllowed = true;
  let heavyReason = "";
```

`refreshModels()` 中 `renderLlm(status);` 之前加入：

```javascript
    readyModels = catalog.filter((entry) => byKey.get(entry.key)?.state === "present").length;
    syncLoadButton();
```

用下面两段替换现有 `setHeavyAllowed`：

```javascript
  function syncLoadButton() {
    const noModels = readyModels === 0;
    els.loadBtn.disabled = !heavyAllowed || noModels;
    const hint = !heavyAllowed ? heavyReason : noModels ? "还没有下载好的聊天模型，去「资源」页下载" : "";
    els.loadBtn.title = hint;
    if (els.loadHint) els.loadHint.textContent = hint;
  }

  function setHeavyAllowed(allowed, reason = "") {
    heavyAllowed = allowed;
    heavyReason = reason;
    syncLoadButton();
  }
```

`renderLlm` 签名改为 `function renderLlm(payload, deskState) {`，并把驱逐分支与徽章行替换为：

```javascript
    } else if (state.error?.code === "evicted") {
      els.modelState.textContent = mediaStillHolds(deskState) ? "已被媒体任务让出内存，可重新加载" : "媒体任务已结束，可重新加载";
      if (state.model_key && !els.modelSelect.dataset.userPicked) els.modelSelect.value = state.model_key;
    } else {
```

```javascript
    const badgeKind = state.error?.code === "evicted"
      ? (mediaStillHolds(deskState) ? "busy" : "none")
      : (BADGE_KIND[state.status] ?? "unknown");
```

并在 `renderLlm` 之前新增：

```javascript
  // Without a desk snapshot (older callers) assume the media job still holds memory.
  const mediaStillHolds = (deskState) => !deskState || Boolean(deskState.media_busy || (deskState.holder && deskState.holder.kind !== "llm"));
```

`desk/static/js/main.js:107` 改为：

```javascript
    panes.chat.applyLlmStatus(llm, deskState);
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/js/*.test.js && python3 -m pytest tests/e2e -q`
Expected: PASS（`test_mutex_ui.py` 覆盖真实互斥提示）

- [ ] **Step 5: Commit**

```bash
git add desk/static/js/panes/chat.js desk/static/js/main.js tests/js/chat_pane.test.js
git commit -m "fix(ui): evicted badge calms down after the media job; no-model load is explained"
```

---

### Task 8: 真机复核 J1

**Files:** 无代码改动。

- [ ] **Step 1: 全量测试**

Run: `python3 -m pytest -q && node --test tests/js/*.test.js && python3 -m pytest tests/e2e -q`
Expected: 全部 PASS

- [ ] **Step 2: 真实推理模型问一句**

用 Plan A Task 2 Step 5 的方式构建隔离副本（数据根 `/tmp/lmd-planB-iso/data`，端口 8839），加载 `superqwen`（q24 证据里空回答的模型），在面板里问「用一句话介绍你自己」。

Expected: 回答区出现非空正文；思考摘要为「已思考 N 秒」，N 与实际等待时间相符（误差 ≤ 2 秒）；刷新后仍相同。

- [ ] **Step 3: 驱逐中断**

同一实例里让模型长答（「写一篇 800 字散文」），流到一半切到视频页提交最小视频。

Expected: 聊天回答保留已出的正文，摘要「已中断：内存让给了媒体作业」，底部「重试」；视频结束后徽章为中性「媒体任务已结束，可重新加载」；刷新页面后中断回答仍在。

- [ ] **Step 4: 清理副本**

```bash
pkill -f 'lmd-planB-iso' ; rm -rf /tmp/lmd-planB /tmp/lmd-planB-iso
```
