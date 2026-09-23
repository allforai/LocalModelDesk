import test from "node:test";
import assert from "node:assert/strict";
import { createChatPane } from "../../desk/static/js/panes/chat.js";

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
  for (const name of ["session-list", "session-new", "model-select", "load", "unload", "model-state", "messages", "chat-input", "send", "chat-error", "load-hint", "skill-bar", "skill-notice", "skill-cost", "skill-rescan"]) controls.set(`[data-${name}]`, new Element(name === "model-select" ? "select" : "div"));
  const doc = {
    body: new Element("body"),
    createElement: (tag) => new Element(tag),
    createDocumentFragment: () => new Element("#fragment"),
    createTextNode: (text) => ({ tagName: "#text", textContent: text }),
  };
  // 顶层控件走原来那条扁平表；skill 芯片是动态生成、名字不定的，找不到扁平项时
  // 退到在已知控件的子树里递归找 [data-x] / [data-x="y"]——真实 DOM 的 querySelector
  // 本就是递归的，这里只是把伪 DOM 补齐到够用，不改变任何既有选择器的返回值。
  const deepFind = (node, key, want) => {
    for (const child of node.children ?? []) {
      if (child.dataset && key in child.dataset && (want === undefined || child.dataset[key] === want)) return child;
      const found = deepFind(child, key, want);
      if (found) return found;
    }
    return null;
  };
  const querySelector = (selector) => {
    if (controls.has(selector)) return controls.get(selector);
    const m = /^\[data-([a-z-]+)(?:="([^"]*)")?\]$/.exec(selector);
    if (!m) return null;
    const key = m[1].replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    const want = m[2];
    for (const el of controls.values()) {
      const found = deepFind(el, key, want);
      if (found) return found;
    }
    return null;
  };
  return { controls, doc, root: { ownerDocument: doc, querySelector } };
}
const json = (payload) => new Response(JSON.stringify(payload), { status: 200 });
const stream = (lines) => new Response(new ReadableStream({ start(controller) {
  controller.enqueue(new TextEncoder().encode(lines.map((line) => `data: ${line}\n\n`).join(""))); controller.close();
} }), { status: 200 });

// name → 属性值的映射进 data-skill-chip 这种属性的值里，不拼进属性名（R-skill-08 附近的实现要求）。
const chipFor = (root, name) => root.querySelector(`[data-skill-chip="${name}"]`);
const byData = (root, name) => root.querySelector(`[data-${name.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`)}]`);

test("chat 面板初始化、加载和卸载模型会调用对应 API 并更新可见状态", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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

test("下拉按状态分三档：present 无后缀，missing/partial 沿用资源页说法，unknown 说明拿不到清单而非「未下载」", async () => {
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async (path) => {
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
    if (path === "/api/resources/catalog") return json([
      { key: "a", group: "chat", name: "模型 A", gb: 1 },
      { key: "b", group: "chat", name: "模型 B", gb: 1 },
      { key: "c", group: "chat", name: "模型 C", gb: 1 },
      { key: "d", group: "chat", name: "模型 D", gb: 1 },
    ]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [
      { key: "a", state: "present" },
      { key: "b", state: "missing", percent: 0 },
      { key: "c", state: "partial", percent: 41.7 },
      { key: "d", state: "unknown", percent: 0, reason: "manifest_unavailable" },
    ] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.refreshModels();
    const [optA, optB, optC, optD] = controls.get("[data-model-select]").children;

    assert.equal(optA.disabled, false);
    assert.equal(optA.textContent, "模型 A · 1 GiB（目录）", "present 选项不该带状态后缀");

    assert.equal(optB.disabled, true);
    assert.ok(optB.textContent.includes("没下"), `missing 应沿用资源页说法「没下」：${optB.textContent}`);

    assert.equal(optC.disabled, true);
    assert.ok(optC.textContent.includes("一半 42%"), `partial 应沿用资源页说法「一半 N%」：${optC.textContent}`);

    assert.equal(optD.disabled, true);
    assert.ok(optD.textContent.includes("拿不到文件清单"), `unknown 应说明拿不到文件清单：${optD.textContent}`);
    assert.ok(!optD.textContent.includes("未下载"), `unknown 不该被说成「未下载」：${optD.textContent}`);
  } finally { globalThis.fetch = oldFetch; }
});

test("流式中页面关闭：把问句和已出的半句带 keepalive 写回会话（P3 路径 6）", async () => {
  const oldFetch = globalThis.fetch;
  const saved = [];
  let releaseStream;
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
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

test("加载失败时徽章只写原因，日志尾部放进悬停提示，不塞满页面", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.applyLlmStatus({ state: { status: "error", model_key: "glm",
    error: { code: "backend_exited", message: "mlx-lm 进程已退出，退出码 1", log_tail: "Traceback\nboom" } } });
  const badge = controls.get("[data-model-state]");
  assert.equal(badge.textContent, "加载失败（backend_exited）：mlx-lm 进程已退出，退出码 1");
  assert.equal(badge.title, "Traceback\nboom");
  pane.applyLlmStatus({ state: { status: "idle" } });
  assert.equal(badge.title, "");
});

test("生成中「发送」变「停止」：点了中止请求，已出内容存为已停止（真机 2026-09-15 复读停不下来）", async () => {
  const oldFetch = globalThis.fetch;
  const patches = [];
  let streamSignal;
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [] });
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([{ id: "s1", title: "t", messages: [], updated: "2026-01-01" }]);
    if (path === "/api/llm/chat/stream") {
      streamSignal = options.signal;
      return new Response(new ReadableStream({ start(controller) {
        controller.enqueue(new TextEncoder().encode('data: {"type":"delta","reasoning":"重复重复"}\n\n'));
        options.signal?.addEventListener("abort", () => controller.error(new DOMException("The operation was aborted.", "AbortError")));
      } }), { status: 200 });
    }
    if (path === "/api/sessions/s1") { patches.push(JSON.parse(options.body)); return json({ id: "s1", title: "t", updated: "2026-01-02" }); }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    const send = controls.get("[data-send]");
    controls.get("[data-chat-input]").value = "你是谁";
    const sending = send.click();
    await new Promise((resolve) => setTimeout(resolve, 20));

    assert.equal(send.disabled, false);
    assert.equal(send.textContent, "停止");
    assert.ok(streamSignal, "流式请求没有带 AbortSignal");

    await send.click();
    await sending;

    assert.equal(streamSignal.aborted, true);
    assert.equal(send.textContent, "发送");
    const assistant = controls.get("[data-messages]").children[1];
    assert.equal(assistant.children[1].children[0].textContent, "已停止");
    assert.equal(assistant.children[3].textContent, "已停止生成");
    const saved = patches.at(-1).messages[1];
    assert.deepEqual(saved.interrupted, { code: "stopped", message: "已停止生成" });
    assert.equal(saved.reasoning, "重复重复");
  } finally { globalThis.fetch = oldFetch; }
});

// ---- Task 8：输入框上方的芯片——选中、勾附件、占用可见、坏的点不动 ----
//
// setupChat 同步返回（不 await），selectSkill/sendAndCaptureRequest 等方法内部
// 自己等 ready：这样才能照抄 brief 给的调用写法（`const pane = setupChat(...)`
// 不带 await）。ready 里若给了 charsPerToken，会先悄悄发一轮「热身」消息，让
// 每 token 字符数从一次真实请求里量出来——这与生产代码完全同一条路径
// （compaction.js 的自校准），只是测试需要在断言前就把这个数吃到肚子里。
const attachmentCheckbox = (root, name, file) => root.querySelector(`[data-skill-attachment="${name}/${file}"]`);

// tokenLimit 与 compactAt 是两个不同的数，各喂各的用途——tokenLimit 是显示的
// 额度分母和三成警告的分母（budget.for_chat(...).token_limit），compactAt 只
// 喂给 maybeCompact 触发压缩（= token_limit × 0.75，两者不是同一个数）。
function setupChat({ skills = [], charsPerToken, compactAt, tokenLimit, sessionSkills = [], omitSkillsKey = false, initialMessages = [] } = {}) {
  const { root, controls } = makePane();
  let skillsPayload = skills;
  const savedSession = { id: "s1", title: "t", messages: [...initialMessages], updated: "2026-01-01" };
  if (!omitSkillsKey) savedSession.skills = sessionSkills;
  let lastRequestMessages = null;
  // 分开计数：重新扫描按钮点错接口（打到 list 而不是 rescan）跟按对了接口但
  // 界面没刷新（新 skill 还是看不见）是两种不同的坏法，得能分别抓到。
  let listCalls = 0;
  let rescanCalls = 0;

  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/skills") { listCalls += 1; return json({ skills: skillsPayload }); }
    if (path === "/api/skills/rescan") { rescanCalls += 1; return json({ skills: skillsPayload }); }
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([savedSession]);
    if (path === "/api/sessions/s1" && (options.method ?? "GET") === "PATCH") {
      Object.assign(savedSession, JSON.parse(options.body));
      return json({ ...savedSession });
    }
    if (path === "/api/budget") return json({ chat: { compact_at: compactAt ?? null, token_limit: tokenLimit ?? null }, pressure: "normal" });
    if (path === "/api/llm/chat/stream") {
      const messages = JSON.parse(options.body).messages;
      lastRequestMessages = messages;
      const sentChars = JSON.stringify(messages).length;
      const lines = ['{"type":"delta","text":"ok"}'];
      lines.push(charsPerToken !== undefined
        ? `{"type":"done","usage":{"prompt_tokens":${Math.max(1, Math.round(sentChars / charsPerToken))}}}`
        : '{"type":"done"}');
      return stream(lines);
    }
    throw new Error(`setupChat 没处理的请求：${path} ${options.method ?? "GET"}`);
  };

  const pane = createChatPane(root);
  const ready = (async () => {
    await pane.init();
    if (charsPerToken !== undefined) {
      // 热身一轮：只为了让 lastCharsPerToken 在断言前就有值，走的还是 send() 这条真实代码路径。
      controls.get("[data-chat-input]").value = "热身";
      await controls.get("[data-send]").click();
    }
  })();

  return {
    container: root,
    controls,
    ready,
    async selectSkill(name) {
      await ready;
      const chip = chipFor(root, name);
      if (!chip) throw new Error(`没找到芯片：${name}`);
      await chip.click();
    },
    async sendAndCaptureRequest(text) {
      await ready;
      controls.get("[data-chat-input]").value = text;
      await controls.get("[data-send]").click();
      return lastRequestMessages;
    },
    async sendAndCaptureSentChars(text) {
      const messages = await this.sendAndCaptureRequest(text);
      return JSON.stringify(messages).length;
    },
    async rescanWith(list) {
      await ready;
      skillsPayload = list;
      await pane.rescanSkills();
    },
    // 只换服务端下次会答的内容，不触发任何请求——模拟「用户在编辑器里存了
    // 新的 SKILL.md，但台面还没有人告诉它去看一眼」。
    setSkillsPayload(list) {
      skillsPayload = list;
    },
    async clickRescanButton() {
      await ready;
      await controls.get("[data-skill-rescan]").click();
    },
    skillCallCounts: () => ({ list: listCalls, rescan: rescanCalls }),
    currentSelection() {
      return savedSession.skills ?? [];
    },
    savedSession: () => ({ ...savedSession }),
    // finding 2 的测试要在一轮真实测量之后模拟模型驻留状态变化（卸载/换模型），
    // 直接把 createChatPane 的 applyLlmStatus 递出去，不用另起一套 llm/status mock。
    applyLlmStatus: (...args) => pane.applyLlmStatus(...args),
  };
}

test("选中 skill 后，发出去的消息第一条是它的正文", async () => {
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: false,
      body: "审查指令", chars: 4, attachments: [], ok: true, error: null },
  ] });
  await pane.selectSkill("review");
  const sent = await pane.sendAndCaptureRequest("你好");
  assert.equal(sent[0].role, "system");
  assert.ok(sent[0].content.includes("审查指令"));
});

test("占用显示在芯片上；量不到比值时显示字符数而不是猜一个 token 数", async () => {
  // R-skill-06 是两条独立的要求：芯片自己写明它占多少（brief 原来的断言），
  // 加上输入框上方的聚合行（另一条测试已经在测）——两个都得有，不是二选一。
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: false,
      body: "x".repeat(400), chars: 400, attachments: [], ok: true, error: null },
  ] });
  await pane.selectSkill("review");
  const chipLabel = chipFor(pane.container, "review").textContent;
  assert.ok(chipLabel.includes("字符"), `芯片自己没写占用，或量不到比值却显示了 token：${chipLabel}`);
  const costLabel = byData(pane.container, "skillCost").textContent;
  assert.ok(costLabel.includes("字符"), `聚合行量不到比值却显示了 token：${costLabel}`);
});

test("零占用的 skill 芯片不该带一条空占用后缀", async () => {
  // chipCostText 的 chars===0 早退：0 字符的 skill（正文为空但条目本身仍然
  // ok）不该在芯片名字后面拖一条「0 字符（还没量过 token）」的尾巴。
  const pane = setupChat({ skills: [
    { name: "empty", description: "d", source: "user", overrides_bundled: false,
      body: "", chars: 0, attachments: [], ok: true, error: null },
  ] });
  await pane.ready;
  const chip = chipFor(pane.container, "empty");
  assert.equal(chip.textContent, "empty", `零占用的芯片不该带占用后缀：${chip.textContent}`);
});

test("重新扫描：按钮打的是 rescan 接口而不是普通列表接口，并且能看到点击前才出现的新 skill", async () => {
  // R-skill-09：发现是显式的——没有文件监听，用户改完 SKILL.md 得靠这个按钮
  // 才能让台面看见。这里刻意测两件不同的事：接口打没打对、界面刷没刷新——
  // 一个是「问错了人」，一个是「问对了人但没把答案画出来」，谁坏了都不该被
  // 另一个测试盖住。
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: false,
      body: "正文", chars: 2, attachments: [], ok: true, error: null },
  ] });
  await pane.ready;
  assert.deepEqual(pane.skillCallCounts(), { list: 1, rescan: 0 }, "启动时该扫一次列表接口");
  assert.equal(chipFor(pane.container, "newone"), null, "点击前不该看到还没扫到的新 skill");

  pane.setSkillsPayload([
    { name: "review", description: "d", source: "user", overrides_bundled: false,
      body: "正文", chars: 2, attachments: [], ok: true, error: null },
    { name: "newone", description: "d", source: "user", overrides_bundled: false,
      body: "新正文", chars: 3, attachments: [], ok: true, error: null },
  ]);
  await pane.clickRescanButton();

  const counts = pane.skillCallCounts();
  assert.equal(counts.rescan, 1, "点『重新扫描』该打 rescan 接口");
  assert.equal(counts.list, 1, "不该顺手又打一次普通列表接口");
  assert.ok(chipFor(pane.container, "newone"), "点击后该能看到新出现的 skill");
});

test("skill 计入 sentChars，否则每 token 字符数会被悄悄带偏", async () => {
  // R-skill-13：ratio = sentChars / promptTokens，而 skill 必然计入上游的 promptTokens。
  // 它若没计入 sentChars，比值偏小，之后所有由它换算的字符预算跟着偏小——没有任何迹象。
  const pane = setupChat({ skills: [
    { name: "big", description: "d", source: "user", overrides_bundled: false,
      body: "z".repeat(500), chars: 500, attachments: [], ok: true, error: null },
  ] });
  const bare = await pane.sendAndCaptureSentChars("你好");
  await pane.selectSkill("big");
  const withSkill = await pane.sendAndCaptureSentChars("你好");
  assert.ok(withSkill - bare >= 500, `sentChars 没把 skill 算进去：${bare} → ${withSkill}`);
});

test("占用超过额度三成时警告，但不禁止发送", async () => {
  // 是用户的机器，由他决定（R-skill-06）。
  const pane = setupChat({
    skills: [{ name: "huge", description: "d", source: "user", overrides_bundled: false,
               body: "w".repeat(4000), chars: 4000, attachments: [], ok: true, error: null }],
    charsPerToken: 4, tokenLimit: 1000,          // 4000 字符 ÷ 4 = 1000 token，远超三成
  });
  await pane.selectSkill("huge");
  assert.equal(byData(pane.container, "skillCost").dataset.warn, "1");
  assert.equal(byData(pane.container, "send").disabled, false, "警告不该变成禁止");
});

test("占用不到三成时不警告", async () => {
  const pane = setupChat({
    skills: [{ name: "tiny", description: "d", source: "user", overrides_bundled: false,
               body: "w".repeat(40), chars: 40, attachments: [], ok: true, error: null }],
    charsPerToken: 4, tokenLimit: 1000,          // 40 字符 ÷ 4 = 10 token，远低于三成
  });
  await pane.selectSkill("tiny");
  assert.equal(byData(pane.container, "skillCost").dataset.warn, "");
});

test("量到比值但还没量到额度上限时：只报 token 数，不编一个『/ 额度』", async () => {
  const pane = setupChat({
    skills: [{ name: "review", description: "d", source: "user", overrides_bundled: false,
               body: "w".repeat(40), chars: 40, attachments: [], ok: true, error: null }],
    charsPerToken: 4, // tokenLimit 不传：额度还没量到
  });
  await pane.selectSkill("review");
  const text = byData(pane.container, "skillCost").textContent;
  assert.ok(!text.includes("额度"), `没有额度上限却编出了一个：${text}`);
  assert.equal(byData(pane.container, "skillCost").dataset.warn, "", "没有额度上限时不该警告");
});

test("额度的分母是 token_limit，不是 compact_at——两者是不同用途的两个数", async () => {
  // R-skill-06：「额度取自驻留模型的 budget.for_chat(...).token_limit」。compact_at
  // 是触发压缩的那条线（= token_limit × 0.75，只喂给 maybeCompact），拿它顶替
  // token_limit 当分母会把额度算小、把警告算得过于敏感。这里 token_limit=1000、
  // compact_at=300：200 token 的占用是 token_limit 的 20%（不该警告），但如果
  // 错拿 300 当分母会变成 66.7%（会误警告）——两个门槛这条测试都过一遍。
  const pane = setupChat({
    skills: [{ name: "review", description: "d", source: "user", overrides_bundled: false,
               body: "w".repeat(800), chars: 800, attachments: [], ok: true, error: null }],
    charsPerToken: 4, tokenLimit: 1000, compactAt: 300, // 800 字符 ÷ 4 = 200 token
  });
  await pane.selectSkill("review");
  const text = byData(pane.container, "skillCost").textContent;
  assert.ok(text.includes("额度 1000"), `额度分母不是 token_limit：${text}`);
  assert.ok(!text.includes("额度 300"), `额度分母混进了 compact_at：${text}`);
  assert.equal(byData(pane.container, "skillCost").dataset.warn, "", "对 token_limit 算只占两成，不该警告");
});

test("没有选中任何 skill 时聚合占用行是空的——哪怕已经量过比值，不会卡在『skill 占用 0』", async () => {
  // renderSkillCost 的 chars===0 早退不是边缘情况：这是「没选任何 skill」这个
  // 最常见状态本身。没有它，热身一轮量到比值之后，这一行会卡成「skill 占用
  // 0 / 额度 …」，永久挂着，哪怕用户从没选过任何 skill。
  const pane = setupChat({
    skills: [{ name: "review", description: "d", source: "user", overrides_bundled: false,
               body: "正文", chars: 2, attachments: [], ok: true, error: null }],
    charsPerToken: 4, tokenLimit: 1000, // 触发热身，量到比值；但故意不选中 review
  });
  await pane.ready;
  assert.equal(byData(pane.container, "skillCost").textContent, "", "没选 skill 却显示了占用");
});

test("坏的 skill 列出来但点不动", async () => {
  const pane = setupChat({ skills: [
    { name: "bad", description: "", source: "user", overrides_bundled: false,
      body: "", chars: 0, attachments: [], ok: false, error: "frontmatter 缺 description" },
  ] });
  await pane.ready;
  const chip = chipFor(pane.container, "bad");
  assert.equal(chip.disabled, true);
  assert.ok(chip.title.includes("缺 description"));
});

test("坏的 skill 点了也不会被选中——守卫在 toggleSkill 自己身上，不只是 chip 的 disabled 属性", async () => {
  // 上一条测的是 disabled 属性；伪 DOM 的 click() 不看 disabled，点了照样会
  // 调到 toggleSkill(entry)——这条测的是 toggleSkill 自己那句
  // `if (!entry.ok) return`，R-skill-08「坏的 skill 不可被选中」真正的强制点
  // 在这里，不在 disabled 属性上（那只是给人看的提示，不是强制）。
  const pane = setupChat({ skills: [
    { name: "bad", description: "", source: "user", overrides_bundled: false,
      body: "", chars: 0, attachments: [], ok: false, error: "frontmatter 缺 description" },
  ] });
  await pane.selectSkill("bad"); // 伪 DOM 的 click() 不管 disabled，这里确实点了下去
  assert.deepEqual(pane.currentSelection(), [], "坏的 skill 被点一下就进了选中列表");
});

test("好的 skill 芯片 title 是给用户看的 description，不是 error", async () => {
  // description 今天的消费者是用户（他靠这句话决定点不点这个芯片），不是模型。
  const pane = setupChat({ skills: [
    { name: "review", description: "审查一遍代码风格", source: "user", overrides_bundled: false,
      body: "正文", chars: 2, attachments: [], ok: true, error: "不该被读到" },
  ] });
  await pane.ready;
  const chip = chipFor(pane.container, "review");
  assert.equal(chip.title, "审查一遍代码风格");
});

test("overrides_bundled 为真时芯片上标出已覆盖自带——覆盖不能是静默的", async () => {
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: true,
      body: "正文", chars: 2, attachments: [], ok: true, error: null },
  ] });
  await pane.ready;
  const chip = chipFor(pane.container, "review");
  assert.match(chip.textContent, /已覆盖自带/);
});

test("再点一次已选中的芯片会取消选中", async () => {
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: false,
      body: "正文", chars: 2, attachments: [], ok: true, error: null },
  ] });
  await pane.selectSkill("review");
  assert.deepEqual(pane.currentSelection().map((s) => s.name), ["review"]);
  await pane.selectSkill("review");
  assert.deepEqual(pane.currentSelection(), []);
});

test("勾中的附件原文进入发出去的消息，没勾的不进去（R-skill-10）", async () => {
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: false, body: "正文", chars: 2,
      attachments: [{ file: "A.md", chars: 5, text: "附件A原文" }, { file: "B.md", chars: 5, text: "附件B原文" }],
      ok: true, error: null },
  ] });
  await pane.selectSkill("review");
  const boxA = attachmentCheckbox(pane.container, "review", "A.md");
  assert.equal(boxA.disabled, false, "选中 skill 后附件勾选框该能点了");
  boxA.checked = true;
  await boxA.listeners.change();
  const sent = await pane.sendAndCaptureRequest("你好");
  assert.ok(sent[0].content.includes("附件A原文"), "勾中的附件原文没有进去");
  assert.ok(!sent[0].content.includes("附件B原文"), "没勾的附件原文不该进去");
});

test("放不进上下文的附件（缺失或读不出）勾选框禁用，理由写在界面上（finding 4）", async () => {
  // 后端（store.py）现在把缺失/读不出的附件也列进 attachments，用 available: false
  // 和 reason 标出来——这份附件不可能拼出东西，勾选框必须永远禁用，且「没放进去」
  // 这件事必须写在明处，不能只在 chars 上体现（2026-09-23 finding 4，R-skill-10）。
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: false, body: "正文", chars: 2,
      attachments: [
        { file: "OK.md", chars: 5, text: "好附件", available: true, reason: null },
        { file: "GONE.md", chars: 0, text: null, available: false, reason: "引用的文件不存在" },
      ],
      ok: true, error: null },
  ] });
  await pane.selectSkill("review");

  const boxOk = attachmentCheckbox(pane.container, "review", "OK.md");
  assert.equal(boxOk.disabled, false, "可用的附件不该被这个改动误伤");

  const boxGone = attachmentCheckbox(pane.container, "review", "GONE.md");
  assert.equal(boxGone.disabled, true, "放不进上下文的附件，勾选框必须禁用");
  const label = boxGone.parentNode;
  const reasonText = label.children.map((c) => c.textContent ?? "").join("");
  assert.match(reasonText, /没有放进上下文/, "「没放进去」这件事必须写在界面明处");
  assert.match(reasonText, /引用的文件不存在/, "具体原因也要显示出来");
});

test("旧会话没有 skills 这个键时不报错，芯片照常渲染（这个功能上线前存的会话）", async () => {
  const pane = setupChat({
    skills: [{ name: "review", description: "d", source: "user", overrides_bundled: false,
               body: "正文", chars: 2, attachments: [], ok: true, error: null }],
    omitSkillsKey: true,
  });
  await pane.ready; // 裸读 session.skills 会在这里炸——ready 内部走的就是 init() → refreshSkills()
  const chip = chipFor(pane.container, "review");
  assert.ok(chip, "旧会话不该让芯片条整个渲染不出来");
  assert.equal(chip.className.includes("active"), false, "旧会话没有选中记录，不该有芯片是 active 的");
  // 点一下选中它：这条路走的是 toggleSkill 自己的 `session.skills ?? []`——
  // resolveSelection 内部对 undefined 也有防御，光测「渲染不炸」盖不到这一条，
  // 得真的点一次才会经过它。
  await pane.selectSkill("review");
  assert.deepEqual(pane.currentSelection().map((s) => s.name), ["review"]);
});

test("选中的 skill 消失后，界面说明并取消选中", async () => {
  const pane = setupChat({ skills: [
    { name: "gone", description: "d", source: "user", overrides_bundled: false,
      body: "正文", chars: 2, attachments: [], ok: true, error: null },
  ] });
  await pane.selectSkill("gone");
  await pane.rescanWith([]);                       // 用户在文件夹里删掉了它
  assert.match(byData(pane.container, "skillNotice").textContent, /已不存在/);
  assert.deepEqual(pane.currentSelection(), []);
});

test("skillChars 没被传进 maybeCompact 的话，该触发的压缩会悄悄不触发（两处 wiring 之一）", async () => {
  // 用一个很大的 skill 把预算几乎占满：compactAt(100) × ratio(≈4) − skillChars(≈2000) ≤ 0，
  // 尾部预算被压到 0，哪怕最早那一轮很短也会被推进 head、触发压缩。
  // 如果 chat.js 忘了把 skillChars 传给 maybeCompact（默认值 0），同样这几条消息的
  // 尾部预算是 100×4=400，两条 20 字符的旧消息都装得下尾部，压缩根本不会发生——
  // 这正是 brief 点名的「两处 wiring 点」之一，必须有一条测试在它被短接时会红。
  const oldTurn = [
    { role: "user", content: "问".repeat(20) },
    { role: "assistant", content: "答".repeat(20) },
  ];
  const pane = setupChat({
    skills: [{ name: "big", description: "d", source: "user", overrides_bundled: false,
               body: "k".repeat(2000), chars: 2000, attachments: [], ok: true, error: null }],
    sessionSkills: [{ name: "big", attachments: [] }],
    initialMessages: oldTurn,
    charsPerToken: 4, compactAt: 100,
  });
  await pane.sendAndCaptureRequest("你");
  const saved = pane.savedSession();
  assert.ok(saved.messages.some((m) => m.role === "summary"),
    `skill 占用没有挤压尾部预算，压缩没有被触发：${JSON.stringify(saved.messages)}`);
});

// ---- 2026-09-23 全分支复审：finding 1/2/3/6 ----

test("切到另一个会话也要对账：消失的 skill 在目标会话上被发现，通知和写回都跟着切换（finding 1）", async () => {
  // 会话 A 正开着；会话 B 存的 skill 已经从磁盘删掉。之前的实现只在扫描时
  // 对账「当前」会话，切到 B 时既不提示也不发 PATCH，B.skills 里那个已经不存在
  // 的选中原样留着——磁盘上的目录哪天恢复了它就会悄悄重新生效。
  const oldFetch = globalThis.fetch;
  const sessions = [
    { id: "s1", title: "一", messages: [], updated: "2026-01-02", skills: [{ name: "keep", attachments: [] }] },
    { id: "s2", title: "二", messages: [], updated: "2026-01-01", skills: [{ name: "gone", attachments: [] }] },
  ];
  globalThis.fetch = async (path, options = {}) => {
    // 「gone」已经不在扫描结果里——文件夹里被删掉了。
    if (path === "/api/skills" || path === "/api/skills/rescan") return json({ skills: [
      { name: "keep", description: "d", source: "user", overrides_bundled: false,
        body: "正文", chars: 2, attachments: [], ok: true, error: null },
    ] });
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions" && (options.method ?? "GET") === "GET") return json(sessions);
    if (String(path).startsWith("/api/sessions/") && options.method === "PATCH") {
      const id = path.split("/").pop();
      const idx = sessions.findIndex((s) => s.id === id);
      sessions[idx] = { ...sessions[idx], ...JSON.parse(options.body) };
      return json({ ...sessions[idx] });
    }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    // s1（更新时间更晚）是启动后默认打开的会话，它自己的选中没问题，通知该是空的。
    assert.equal(byData(root, "skillNotice").textContent, "", "s1 没有消失的 skill，不该带通知");

    const s2Item = [...controls.get("[data-session-list]").children].find((li) => li.dataset.sessionId === "s2");
    await s2Item.click();

    assert.match(byData(root, "skillNotice").textContent, /已不存在/, "切到 s2 后该看到 s2 自己的对账通知，不是空着或留着 s1 的");
    assert.deepEqual(sessions.find((s) => s.id === "s2").skills, [], "s2 消失的选中该被摘掉并写回磁盘，不是静默留着");
    assert.deepEqual(sessions.find((s) => s.id === "s1").skills, [{ name: "keep", attachments: [] }],
      "对账 s2 不该牵连 s1 的选中");
  } finally { globalThis.fetch = oldFetch; }
});

test("选中一个 skill 会清掉屏幕上留着的旧对账通知，不用等下一次扫描才消失（finding 1）", async () => {
  const pane = setupChat({
    skills: [{ name: "good", description: "d", source: "user", overrides_bundled: false,
               body: "正文", chars: 2, attachments: [], ok: true, error: null }],
    sessionSkills: [{ name: "gone", attachments: [] }], // 启动对账就会先炸出一条通知
  });
  await pane.ready;
  assert.match(byData(pane.container, "skillNotice").textContent, /已不存在/, "启动时该有一条对账通知打底");

  await pane.selectSkill("good"); // 用户接着手动选中另一个 skill
  assert.equal(byData(pane.container, "skillNotice").textContent, "",
    "选中动作发生之后，旧通知（说的是另一个 skill）不该继续挂在屏幕上");
});

test("勾选附件也会清掉屏幕上留着的旧对账通知（finding 1）", async () => {
  const pane = setupChat({
    skills: [{ name: "good", description: "d", source: "user", overrides_bundled: false, body: "正文", chars: 2,
      attachments: [{ file: "A.md", chars: 5, text: "附件原文", available: true, reason: null }],
      ok: true, error: null }],
  });
  await pane.selectSkill("good");
  // 手动塞回一条通知，模拟它由别的路径（比如另一次扫描）留下——跟上一条测试
  // 分开验证 toggleAttachment 自己的清空逻辑，不跟 toggleSkill 那条混在一起。
  byData(pane.container, "skillNotice").textContent = "手动塞回去模拟的旧通知";
  const boxA = attachmentCheckbox(pane.container, "good", "A.md");
  boxA.checked = true;
  await boxA.listeners.change();
  assert.equal(byData(pane.container, "skillNotice").textContent, "",
    "勾选附件之后，旧通知不该继续挂在屏幕上");
});

test("卸载模型后，芯片占用的额度分母和上一次量到的比值都清空，不留着上一个模型的数字（finding 2）", async () => {
  const pane = setupChat({
    skills: [{ name: "review", description: "d", source: "user", overrides_bundled: false,
               body: "w".repeat(400), chars: 400, attachments: [], ok: true, error: null }],
    charsPerToken: 4, tokenLimit: 1000,
  });
  // 先等 setupChat 内部的 init()+热身彻底跑完，再开始摆弄驻留状态——不然下面
  // 手动喂的 applyLlmStatus 会跟仍在飞行中的初始化异步操作赛跑，谁的状态后到
  // 谁说了算，测试就变得不可靠。
  await pane.ready;
  // 先让驻留模型「已知」是 chat-a，再让warm-up 之后的测量落在这个已知模型上——
  // 从「不知道」变成「知道是谁」不算变化，不该牵连这一步；之后从「chat-a」变
  // 成别的才算（见 chat.js renderLlm 里的注释）。
  pane.applyLlmStatus({ state: { status: "loaded", model_key: "chat-a" }, loaded_model: { name: "模型 A" } });
  await pane.selectSkill("review");
  const before = byData(pane.container, "skillCost").textContent;
  assert.ok(before.includes("额度 1000"), `加载中该显示额度：${before}`);

  pane.applyLlmStatus({ state: { status: "idle" } }); // 卸载
  const after = byData(pane.container, "skillCost").textContent;
  assert.ok(!after.includes("额度"), `卸载后不该继续显示上一个模型的额度：${after}`);
  assert.equal(byData(pane.container, "skillCost").dataset.warn, "", "分母清空后不该继续用旧数字判警告");
});

test("换成另一个模型后，上一个模型量到的每 token 字符数也要清空（finding 2）", async () => {
  const pane = setupChat({
    skills: [{ name: "review", description: "d", source: "user", overrides_bundled: false,
               body: "w".repeat(400), chars: 400, attachments: [], ok: true, error: null }],
    charsPerToken: 4, tokenLimit: 1000,
  });
  await pane.ready; // 理由同上一条测试：先让内部初始化彻底落定
  pane.applyLlmStatus({ state: { status: "loaded", model_key: "chat-a" }, loaded_model: { name: "模型 A" } });
  await pane.selectSkill("review");
  const before = byData(pane.container, "skillCost").textContent;
  assert.ok(!before.includes("字符"), `该用已经量到的比值换算成 token，不是回退成字符数：${before}`);

  pane.applyLlmStatus({ state: { status: "loaded", model_key: "chat-b" }, loaded_model: { name: "模型 B" } });
  const after = byData(pane.container, "skillCost").textContent;
  assert.ok(after.includes("字符"),
    `换模型后不该再用旧模型量到的比值把字符数换算成 token：${after}`);
});

test("芯片自己的占用只算已勾选的附件，没勾的不计入（finding 3）", async () => {
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: false, body: "", chars: 0,
      attachments: [
        { file: "A.md", chars: 100, text: "A原文", available: true, reason: null },
        { file: "B.md", chars: 300, text: "B原文", available: true, reason: null },
      ], ok: true, error: null },
  ] });
  await pane.selectSkill("review");
  assert.equal(chipFor(pane.container, "review").textContent, "review", "还没勾任何附件，芯片不该带占用后缀");

  const boxA = attachmentCheckbox(pane.container, "review", "A.md");
  boxA.checked = true;
  await boxA.listeners.change();
  const onlyA = chipFor(pane.container, "review").textContent;
  assert.ok(onlyA.includes("100 字符"), `只勾 A 后芯片该显示 100 字符：${onlyA}`);
  assert.ok(!onlyA.includes("400"), `不该把没勾的 B 也算进这个芯片的占用：${onlyA}`);

  const boxB = attachmentCheckbox(pane.container, "review", "B.md");
  boxB.checked = true;
  await boxB.listeners.change();
  const both = chipFor(pane.container, "review").textContent;
  assert.ok(both.includes("400 字符"), `两个都勾了之后芯片该显示 400 字符：${both}`);
});

test("单个芯片报的字符数与输入框上方聚合行报的字符数口径一致（finding 5）", async () => {
  // 附件的 text 原文故意跟声明的 chars 字段对不上（现实里也是这样：chars 是
  // Python len，text 是给模型看的原文）——如果聚合行悄悄改回去数
  // skillSystemMessage(...).content.length（拼出来的 system 消息，JS 字符串），
  // 它量到的会是 text 的真实长度加上 HEADER/`##`/`###` 框架字，跟芯片用的
  // chars 字段对不上，这条测试就会抓到。
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: false,
      body: "x".repeat(400), chars: 400,
      attachments: [{ file: "A.md", chars: 100, text: "短", available: true, reason: null }],
      ok: true, error: null },
  ] });
  await pane.selectSkill("review");
  const boxA = attachmentCheckbox(pane.container, "review", "A.md");
  boxA.checked = true;
  await boxA.listeners.change();

  const chipChars = Number(chipFor(pane.container, "review").textContent.match(/(\d+) 字符/)[1]);
  const aggChars = Number(byData(pane.container, "skillCost").textContent.match(/skill 占用 (\d+) 字符/)[1]);
  assert.equal(chipChars, 500, `芯片本身该是 400（正文）+100（勾中的附件）：${chipChars}`);
  assert.equal(aggChars, chipChars, `聚合行和芯片自己报的字符数口径对不上：芯片=${chipChars}，聚合=${aggChars}`);
});

test("未选中的 skill 不在芯片条上铺开附件勾选框，选中才展开，取消选中就收起（finding 6）", async () => {
  const pane = setupChat({ skills: [
    { name: "review", description: "d", source: "user", overrides_bundled: false, body: "正文", chars: 2,
      attachments: [{ file: "A.md", chars: 5, text: "附件A原文", available: true, reason: null }],
      ok: true, error: null },
  ] });
  await pane.ready;
  assert.equal(attachmentCheckbox(pane.container, "review", "A.md"), null,
    "没选中就不该看到这个 skill 的附件勾选框（哪怕永远禁用）");

  await pane.selectSkill("review");
  assert.ok(attachmentCheckbox(pane.container, "review", "A.md"), "选中后该展开这个 skill 的附件勾选框");

  await pane.selectSkill("review"); // 再点一次取消选中
  assert.equal(attachmentCheckbox(pane.container, "review", "A.md"), null,
    "取消选中后附件勾选框该收起来，不是留着变成一堆灰色的");
});
