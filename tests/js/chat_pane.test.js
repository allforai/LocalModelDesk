import test from "node:test";
import assert from "node:assert/strict";

class Element {
  constructor(tag = "div") {
    this.tagName = tag; this.dataset = {}; this.value = ""; this._text = "";
    this.children = []; this.listeners = {}; this.className = ""; this.disabled = false;
    this.hidden = false; this.open = false; this.scrollTop = 0; this.scrollHeight = 1;
    this.classList = { toggle: (name, on) => { if (on) this.className += ` ${name}`; } };
  }
  // Mirrors real DOM: reading textContent returns children's text when there are
  // any, and *writing* it wipes every child (this is exactly the F3 bug: writing
  // the send button's textContent used to blow away its icon <svg> sibling).
  get textContent() { return this.children.length ? this.children.map((c) => c.textContent ?? "").join("") : this._text; }
  set textContent(value) { this._text = value ?? ""; this.children = []; }
  querySelector(selector) {
    if (selector !== "[data-label]") return null;
    const walk = (node) => {
      for (const child of node.children) {
        if (child.dataset?.label) return child;
        const found = walk(child);
        if (found) return found;
      }
      return null;
    };
    return walk(this);
  }
  append(...nodes) {
    for (const node of nodes) {
      if (node && node.tagName === "#fragment") {
        for (const child of node.children) { child.parentNode = this; this.children.push(child); }
        node.children = [];
        continue;
      }
      node.parentNode = this; this.children.push(node);
      if (this.tagName === "select" && !this.value) this.value = node.value;
    }
  }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  setAttribute(name, value) { (this.attrs ??= {})[name] = value; }
  click() { return this.listeners.click?.({ preventDefault() {} }); }
  remove() { this.parentNode?.children.splice(this.parentNode.children.indexOf(this), 1); }
  focus() {}
}

function makePane() {
  const controls = new Map();
  for (const name of ["session-list", "session-new", "model-select", "load", "unload", "model-state", "messages", "chat-input", "send", "chat-error", "load-hint"]) controls.set(`[data-${name}]`, new Element(name === "model-select" ? "select" : "div"));
  const doc = {
    body: new Element("body"),
    createElement: (tag) => new Element(tag),
    createDocumentFragment: () => new Element("#fragment"),
    createTextNode: (text) => ({ tagName: "#text", textContent: text }),
  };
  return { controls, doc, root: { ownerDocument: doc, querySelector: (selector) => controls.get(selector) } };
}
const json = (payload) => new Response(JSON.stringify(payload), { status: 200 });
const stream = (lines) => new Response(new ReadableStream({ start(controller) {
  controller.enqueue(new TextEncoder().encode(lines.map((line) => `data: ${line}\n\n`).join(""))); controller.close();
} }), { status: 200 });

test("chat 面板初始化、加载和卸载模型会调用对应 API 并更新可见状态", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method ?? "GET", options.body]);
    if (path === "/api/resources/catalog") return json([{ key: "chat-a", group: "chat", name: "聊天 A", gb: 1, params: "7B" }]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [{ key: "chat-a", state: "present" }] });
    if (path === "/api/llm/status") return json({ state: { status: calls.some(([p]) => p === "/api/llm/load") ? "loaded" : "idle", model_key: "chat-a" }, loaded_model: { name: "聊天 A" } });
    if (path === "/api/sessions") return json([{ id: "s1", title: "第一会话", messages: [], updated: "2026-01-01" }]);
    if (path === "/api/memory") return json({ available_bytes: 99 * 1024 ** 3 });
    if (path === "/api/llm/load" || path === "/api/llm/unload") return json({});
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    assert.equal(controls.get("[data-model-state]").textContent, "未加载");
    assert.equal(controls.get("[data-model-select]").children[0].textContent.includes("聊天 A"), true);
    await controls.get("[data-load]").click();
    assert.deepEqual(calls.find(([path]) => path === "/api/llm/load").slice(0, 2), ["/api/llm/load", "POST"]);
    assert.equal(controls.get("[data-model-state]").textContent, "已加载：聊天 A");
    await controls.get("[data-unload]").click();
    assert.deepEqual(calls.find(([path]) => path === "/api/llm/unload").slice(0, 2), ["/api/llm/unload", "POST"]);
  } finally { globalThis.fetch = oldFetch; }
});

test("聊天面板在媒体作业期间禁用加载，并在作业结束后恢复", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.setHeavyAllowed(false, "媒体作业进行中");
  assert.equal(controls.get("[data-load]").disabled, true);
  assert.equal(controls.get("[data-load-hint]").textContent, "媒体作业进行中");
  assert.equal(controls.get("[data-chat-error]").textContent, "");
  pane.setHeavyAllowed(true);
  assert.equal(controls.get("[data-load]").disabled, false);
  assert.equal(controls.get("[data-load-hint]").textContent, "");
});

test("驱逐后 tick 推送的 llm 状态会把『已加载』改成让出内存说明（N4）", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  controls.set("[data-load-hint]", new Element()); root.querySelector = (s) => controls.get(s);
  const pane = createChatPane(root);
  pane.applyLlmStatus({ state: { status: "loaded", model_key: "glm" }, loaded_model: { name: "GLM" } });
  assert.equal(controls.get("[data-model-state]").textContent, "已加载：GLM");
  pane.applyLlmStatus({ state: { status: "error", model_key: "glm", error: { code: "evicted", message: "LLM 已被媒体任务驱逐" } }, loaded_model: null });
  assert.equal(controls.get("[data-model-state]").textContent, "已被媒体任务让出内存，可重新加载");
});

test("互斥原因显示在加载按钮旁的提示里，不再是红色错误", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  controls.set("[data-load-hint]", new Element()); root.querySelector = (s) => controls.get(s);
  const pane = createChatPane(root);
  pane.setHeavyAllowed(false, "已有聊天模型驻留：先卸载，再加载另一个");
  assert.equal(controls.get("[data-load-hint]").textContent, "已有聊天模型驻留：先卸载，再加载另一个");
  assert.equal(controls.get("[data-chat-error]").textContent, "");
  assert.equal(controls.get("[data-load]").disabled, true);
  pane.setHeavyAllowed(true, "");
  assert.equal(controls.get("[data-load-hint]").textContent, "");
});

test("chat 面板发送流式回复、折叠思考并把完整消息写回当前会话", async () => {
  const oldFetch = globalThis.fetch;
  const patches = [];
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([{ id: "s1", title: "第一会话", messages: [], updated: "2026-01-01" }]);
    if (path === "/api/llm/chat/stream") {
      assert.deepEqual(JSON.parse(options.body).messages, [{ role: "user", content: "你好" }]);
      return stream(['{"type":"delta","reasoning":"先想"}', '{"type":"delta","text":"你好"}', '{"type":"done"}']);
    }
    if (path === "/api/sessions/s1") { patches.push(JSON.parse(options.body)); return json({ id: "s1", title: "第一会话", updated: "2026-01-02", ...patches.at(-1) }); }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    controls.get("[data-chat-input]").value = "  你好  ";
    await controls.get("[data-send]").click();
    assert.deepEqual(patches, [{ messages: [{ role: "user", content: "你好" }, { role: "assistant", content: "你好", reasoning: "先想", thinking_s: 0 }], model: null }]);
    const assistant = controls.get("[data-messages]").children[1];
    assert.equal(assistant.children[1].hidden, false);
    assert.equal(assistant.children[1].open, false);
    assert.equal(assistant.children[2].children[0].children[0].textContent, "你好");
  } finally { globalThis.fetch = oldFetch; }
});

test("消息按角色分结构：用户气泡、助手带模型名与已思考折叠", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.applyLlmStatus({ state: { status: "loaded", model_key: "glm" }, loaded_model: { name: "GLM 4.7" } });
  pane.showMessages([{ role: "user", content: "你好" }, { role: "assistant", content: "**hi**", reasoning: "想一想", thinking_s: 3 }]);
  const [user, ai] = controls.get("[data-messages]").children;
  assert.equal(user.className, "msg msg-user");
  assert.equal(user.children[0].className, "bubble");
  assert.equal(ai.className, "msg msg-assistant");
  assert.equal(ai.children[0].children[1].textContent, "GLM 4.7");
  assert.equal(ai.children[1].children[0].textContent, "已思考 3 秒");
  assert.equal(ai.children[2].children[0].children[0].tagName, "strong");
});

test("会话卡片：标题行、元信息行、动作区，当前项 active", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const previous = globalThis.fetch;
  globalThis.fetch = async (path) => {
    if (path === "/api/sessions") return json([{ id: "s1", title: "第一会话", model: "glm", messages: [], updated: "2026-09-07T10:05:00" }]);
    if (String(path).includes("catalog")) return json([]);
    if (String(path).includes("status")) return json({ models: [] });
    return json({ state: { status: "idle" } });
  };
  try {
    const pane = createChatPane(root);
    await pane.init();
    const li = controls.get("[data-session-list]").children[0];
    assert.equal(li.className.trim(), "card session active");
    assert.equal(li.children[0].className, "session-title");
    assert.equal(li.children[1].className, "session-meta");
    assert.equal(li.children[1].textContent, "glm · 10:05");
    assert.equal(li.children[2].className, "session-actions");
  } finally { globalThis.fetch = previous; }
});

test("chat 面板的新建、改名和确认删除会写入会话 API 并重绘列表", async () => {
  const oldFetch = globalThis.fetch;
  let sessions = [{ id: "s1", title: "旧标题", messages: [], updated: "2026-01-01" }];
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method ?? "GET", options.body]);
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions" && (options.method ?? "GET") === "GET") return json(sessions);
    if (path === "/api/sessions" && options.method === "POST") {
      const created = { id: "s2", title: "新会话", messages: [], updated: "2026-01-02" }; sessions = [created, ...sessions]; return json(created);
    }
    if (path === "/api/sessions/s2" && options.method === "PATCH") {
      sessions = sessions.map((session) => session.id === "s2" ? { ...session, ...JSON.parse(options.body) } : session); return json(sessions[0]);
    }
    if (path === "/api/sessions/s2" && options.method === "DELETE") { sessions = sessions.filter((session) => session.id !== "s2"); return json({}); }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls, doc } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    await controls.get("[data-session-new]").click();
    let list = controls.get("[data-session-list]");
    assert.equal(list.children[0].children[0].textContent, "新会话");

    list.children[0].children[2].children[0].click();
    const input = list.children[0].children[0];
    input.value = "已改名";
    input.listeners.keydown({ key: "Enter" });
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.deepEqual(JSON.parse(calls.find(([path, method]) => path === "/api/sessions/s2" && method === "PATCH")[2]), { title: "已改名" });

    list = controls.get("[data-session-list]");
    const removing = list.children[0].children[2].children[1].click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    const confirm = doc.body.children[0].children[0].children[2].children[1];
    confirm.click();
    await removing;
    assert.equal(calls.some(([path, method]) => path === "/api/sessions/s2" && method === "DELETE"), true);
    assert.equal(controls.get("[data-session-list]").children[0].children[0].textContent, "旧标题");
  } finally { globalThis.fetch = oldFetch; }
});

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

function textOf(node) {
  if (!node) return "";
  if (!node.children || !node.children.length) return node.textContent ?? "";
  return node.children.map(textOf).join("");
}

test("thinking block renders markdown like the answer does (F2)", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.showMessages([{ role: "assistant", content: "答案", reasoning: "**目标：** 五句话\n* 第一点", thinking_s: 5 }]);
  const details = controls.get("[data-messages]").children[0].children[1];
  const flat = textOf(details);
  assert.ok(!flat.includes("**目标：**"), `思考块里出现了未渲染的 Markdown 源码：${flat}`);
  assert.ok(flat.includes("目标："), "思考块内容丢了");
  const reasoningEl = details.children[1];
  assert.equal(reasoningEl.className, "md");
});

test("thinking fold always states the duration when it was recorded (N1/W5)", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.showMessages([{ role: "assistant", content: "a", reasoning: "r", thinking_s: 7 }]);
  const details = controls.get("[data-messages]").children[0].children[1];
  assert.equal(details.children[0].textContent, "已思考 7 秒");
});

test("thinking fold says so plainly when the duration was never recorded (N1/W5)", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.showMessages([{ role: "assistant", content: "a", reasoning: "r" }]);
  const details = controls.get("[data-messages]").children[0].children[1];
  assert.equal(details.children[0].textContent, "思考过程（未记录时长）");
});

test("send button keeps its icon in every state (F3)", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const send = controls.get("[data-send]");
  const icon = new Element("svg");
  icon.className = "icon icon-send";
  send.append(icon);
  const oldFetch = globalThis.fetch;
  let releaseStream;
  globalThis.fetch = async (path) => {
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([{ id: "s1", title: "t", messages: [], updated: "2026-01-01" }]);
    if (path === "/api/llm/chat/stream") {
      return new Response(new ReadableStream({
        start(controller) {
          releaseStream = () => {
            controller.enqueue(new TextEncoder().encode('data: {"type":"done"}\n\n'));
            controller.close();
          };
        },
      }), { status: 200 });
    }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const pane = createChatPane(root);
    await pane.init();
    controls.get("[data-chat-input]").value = "hi";
    const clicked = send.click();
    await new Promise((resolve) => setTimeout(resolve, 0));
    const hasIcon = send.children.some((n) => (n.className || "").includes("icon"));
    assert.ok(hasIcon, "busy=true 时发送按钮丢了图标");
    releaseStream();
    await clicked;
    const hasIconAfter = send.children.some((n) => (n.className || "").includes("icon"));
    assert.ok(hasIconAfter, "busy=false 时发送按钮丢了图标");
  } finally { globalThis.fetch = oldFetch; }
});

test("model state renders as a badge in the shared family (F15)", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  const badge = controls.get("[data-model-state]");

  pane.applyLlmStatus({ state: { status: "idle" } });
  assert.ok(badge.className.includes("badge"), badge.className);
  assert.ok(badge.className.includes("badge-none"), badge.className);

  pane.applyLlmStatus({ state: { status: "loaded", model_key: "glm" }, loaded_model: { name: "GLM" } });
  assert.ok(badge.className.includes("badge-ok"), badge.className);

  pane.applyLlmStatus({ state: { status: "error", model_key: "glm", error: { code: "evicted", message: "让出内存" } } });
  assert.ok(badge.className.includes("badge-busy"), badge.className);
});

test("after eviction the dropdown still points at the evicted model", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const select = controls.get("[data-model-select]");
  const optionA = new Element("option"); optionA.value = "glm";
  const optionB = new Element("option"); optionB.value = "superqwen";
  select.append(optionA, optionB);
  select.value = "glm";
  const pane = createChatPane(root);
  pane.applyLlmStatus({ state: { status: "error", model_key: "superqwen", error: { code: "evicted", message: "让出内存" } } });
  assert.equal(select.value, "superqwen");
});

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

test("加载中卸载按钮可用并显示『取消加载』，其余状态显示『卸载』", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.applyLlmStatus({ state: { status: "loading", model_key: "glm" }, loaded_model: null });
  assert.equal(controls.get("[data-unload]").disabled, false);
  assert.equal(controls.get("[data-unload]").textContent, "取消加载");
  pane.applyLlmStatus({ state: { status: "loaded", model_key: "glm" }, loaded_model: { name: "GLM" } });
  assert.equal(controls.get("[data-unload]").textContent, "卸载");
});

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
