import test from "node:test";
import assert from "node:assert/strict";
import { summaryLabel } from "../../desk/static/js/pure/compaction.js";

test("分隔条说清压了多少条", () => {
  assert.equal(summaryLabel(24), "这里压缩了 24 条消息");
});

test("一条也要说人话", () => {
  assert.equal(summaryLabel(1), "这里压缩了 1 条消息");
});

test("数目缺失时不编一个数", () => {
  assert.equal(summaryLabel(undefined), "这里有一段压缩过的对话");
  assert.equal(summaryLabel(0), "这里有一段压缩过的对话");
});

// ---- 假 DOM：与 tests/js/chat_pane.test.js 同一套写法，照着搭，不新造一套 ----
class Element {
  constructor(tag = "div") {
    this.tagName = tag; this.dataset = {}; this.value = ""; this._text = "";
    this.children = []; this.listeners = {}; this.className = ""; this.disabled = false;
    this.hidden = false; this.open = false; this.scrollTop = 0; this.scrollHeight = 1;
    this.classList = { toggle: (name, on) => { if (on) this.className += ` ${name}`; } };
  }
  get textContent() { return this.children.length ? this.children.map((c) => c.textContent ?? "").join("") : this._text; }
  set textContent(value) { this._text = value ?? ""; this.children = []; }
  querySelector() { return null; }
  append(...nodes) {
    for (const node of nodes) {
      if (node && node.tagName === "#fragment") {
        for (const child of node.children) { child.parentNode = this; this.children.push(child); }
        node.children = [];
        continue;
      }
      node.parentNode = this; this.children.push(node);
    }
  }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  prepend(...nodes) { for (const node of nodes.reverse()) { node.parentNode = this; this.children.unshift(node); } }
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

test("summary 消息渲染成分隔条：文案、可展开摘要全文、改/重压按钮；被替代的消息各自仍是自己的节点（R-context-03/05）", async () => {
  const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
  const { root, controls } = makePane();
  const pane = createChatPane(root);
  pane.showMessages([
    { role: "summary", content: "摘要正文", replaced_through: 2 },
    { role: "user", content: "被替代的问" },
    { role: "assistant", content: "被替代的答" },
    { role: "user", content: "还在的问" },
  ]);
  const rows = controls.get("[data-messages]").children;
  assert.equal(rows.length, 4, "被替代的消息没有被删除，仍然各自渲染成自己的节点");

  const summaryRow = rows[0];
  assert.equal(summaryRow.className, "msg msg-summary");
  const details = summaryRow.children[0];
  assert.equal(details.tagName, "details");
  const [summaryEl, body, actions] = details.children;
  assert.equal(summaryEl.tagName, "summary");
  assert.equal(summaryEl.textContent, "这里压缩了 2 条消息");
  assert.equal(body.className, "md");
  assert.ok(body.textContent.includes("摘要正文"), "摘要全文没有渲染出来");
  assert.equal(actions.className, "summary-actions");
  const [edit, redo] = actions.children;
  assert.equal(edit.textContent, "改");
  assert.equal(redo.textContent, "重压");

  assert.equal(rows[1].className, "msg msg-user");
  assert.equal(rows[1].children[0].textContent, "被替代的问");
  assert.equal(rows[2].className, "msg msg-assistant");
  assert.equal(rows[3].className, "msg msg-user");
  assert.equal(rows[3].children[0].textContent, "还在的问");
});

// R-context-05 明说摘要「可被用户编辑，亦可在原文基础上重新生成」——按钮存在
// 不等于这条需求被满足，这两条测试对着 spec 的动词（编辑、重新生成）验证
// 点击之后真的发生了什么，而不是只验证按钮渲染出来。
function sessionFixture(overrides = {}) {
  return { id: "s1", title: "t", model: null, updated: "2026-01-01", messages: [
    { role: "summary", content: "旧摘要", replaced_through: 1 },
    { role: "user", content: "被替代的问" },
    { role: "user", content: "还在的问" },
  ], ...overrides };
}

test("点「改」就地编辑摘要正文，写回后持久化到会话（R-context-05：摘要可被用户编辑）", async () => {
  const oldFetch = globalThis.fetch;
  const patches = [];
  const session = sessionFixture();
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([session]);
    if (path === "/api/sessions/s1") { patches.push(JSON.parse(options.body)); return json({ id: "s1", title: "t", updated: "2026-01-02", ...patches.at(-1) }); }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    const details = controls.get("[data-messages]").children[0].children[0];
    const [edit] = details.children[2].children;
    edit.click();
    const textarea = details.children[1].children[0];
    assert.equal(textarea.value, "旧摘要");
    textarea.value = "改过的摘要";
    textarea.listeners.blur();
    await new Promise((resolve) => setTimeout(resolve, 0));
    assert.deepEqual(patches.at(-1).messages[0], { role: "summary", content: "改过的摘要", replaced_through: 1 });
  } finally { globalThis.fetch = oldFetch; }
});

test("点「重压」拿被替代的原文重新生成，成功后覆盖旧摘要正文（R-context-05：可在原文基础上重新生成）", async () => {
  const oldFetch = globalThis.fetch;
  const patches = [];
  const session = sessionFixture();
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([session]);
    if (path === "/api/llm/chat/stream") {
      const sent = JSON.parse(options.body).messages;
      assert.equal(sent.length, 1, "重压只应发一条填表提示词，不带别的历史");
      assert.match(sent[0].content, /被替代的问/, "重压必须用被替代的原文，不是随便一句话");
      return stream(['{"type":"delta","text":"重压后的摘要"}', '{"type":"done"}']);
    }
    if (path === "/api/sessions/s1") { patches.push(JSON.parse(options.body)); return json({ id: "s1", title: "t", updated: "2026-01-02", ...patches.at(-1) }); }
    throw new Error(`unexpected request ${path} ${options.method ?? "GET"}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    const details = controls.get("[data-messages]").children[0].children[0];
    const [, redo] = details.children[2].children;
    await redo.click();
    assert.deepEqual(patches.at(-1).messages[0], { role: "summary", content: "重压后的摘要", replaced_through: 1 });
  } finally { globalThis.fetch = oldFetch; }
});

test("重压失败时保留旧摘要，不写半截（同一条『失败时一个字都不写』的纪律）", async () => {
  const oldFetch = globalThis.fetch;
  const patches = [];
  const session = sessionFixture();
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/resources/catalog") return json([]);
    if (String(path).startsWith("/api/resources/status")) return json({ models: [] });
    if (path === "/api/llm/status") return json({ state: { status: "idle" } });
    if (path === "/api/sessions") return json([session]);
    if (path === "/api/llm/chat/stream") return stream(['{"type":"error","code":"boom","message":"模型炸了"}']);
    if (path === "/api/sessions/s1") { patches.push(JSON.parse(options.body)); return json({ id: "s1", title: "t", updated: "2026-01-02", ...patches.at(-1) }); }
    throw new Error(`unexpected request ${path}`);
  };
  try {
    const { createChatPane } = await import("../../desk/static/js/panes/chat.js");
    const { root, controls } = makePane();
    const pane = createChatPane(root);
    await pane.init();
    const details = controls.get("[data-messages]").children[0].children[0];
    const [, redo] = details.children[2].children;
    await redo.click();
    assert.equal(patches.length, 0, "生成失败不该有任何一次会话保存");
    assert.match(controls.get("[data-chat-error]").textContent, /重新生成摘要失败/);
    assert.equal(details.children[1].textContent, "旧摘要", "失败后旧摘要必须原样保留");
  } finally { globalThis.fetch = oldFetch; }
});
