import test from "node:test";
import assert from "node:assert/strict";
import { skillInstallDialog } from "../../desk/static/js/widgets/skill_install.js";

// 跟 chat_pane.test.js 同一套假 DOM 风格（dataset、append、remove、textContent
// 写入即清空子节点），只是这里只需要弹层用得到的那一小撮方法，不复用整个
// makePane()——这个弹层本身不挂在任何 pane 的固定控件表里，是动态 append 到
// doc.body 的。
class Element {
  constructor(tag = "div") {
    this.tagName = tag; this.dataset = {}; this.value = "";
    this.children = []; this.listeners = {}; this.className = ""; this.disabled = false;
    this._text = "";
  }
  get textContent() { return this.children.length ? this.children.map((c) => c.textContent ?? "").join("") : this._text; }
  set textContent(value) { this._text = value ?? ""; this.children = []; }
  append(...nodes) { for (const node of nodes) { node.parentNode = this; this.children.push(node); } }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  setAttribute(name, value) { (this.attrs ??= {})[name] = value; }
  click() { return this.listeners.click?.({ preventDefault() {} }); }
  remove() { this.parentNode?.children.splice(this.parentNode.children.indexOf(this), 1); this.removed = true; }
  focus() { this.focused = true; }
}

function makeDoc() {
  const body = new Element("body");
  const doc = {
    body,
    createElement: (tag) => new Element(tag),
    addEventListener(type, listener) { (this.listeners ??= {})[type] = listener; },
    removeEventListener(type) { if (this.listeners) delete this.listeners[type]; },
  };
  return doc;
}

// 弹层永远是 doc.body 最新追加的那个 overlay——跟 confirm.test.js 找法一致。
const overlayOf = (doc) => doc.body.children.at(-1);
const boxOf = (doc) => overlayOf(doc).children[0];
const deep = (node, key) => {
  for (const child of node.children ?? []) {
    if (child.dataset && key in child.dataset) return child;
    const found = deep(child, key);
    if (found) return found;
  }
  return null;
};
const find = (doc, key) => deep(boxOf(doc), key);

const preview = {
  staging_id: "abc123", name: "示例 skill", description: "一个测试用的描述",
  body: "# 正文标题\n\n这是完整的 SKILL.md 正文，用来确认用户在装之前能看到全文。",
  attachments: ["ref.md", "notes.md"],
};

test("预览阶段：正文完整展示，install 还没被调用过", async () => {
  const doc = makeDoc();
  let installCalled = false;
  const api = {
    previewSkill: async (url) => { assert.equal(url, "https://github.com/o/r"); return preview; },
    installSkill: async () => { installCalled = true; return { installed: preview.name, enabled: false }; },
    discardSkill: async () => {},
  };
  const p = skillInstallDialog(doc, api);
  find(doc, "skillInstallUrl").value = "https://github.com/o/r";
  await find(doc, "skillInstallSubmit").click();
  await Promise.resolve(); // 让 preview 的 await 落地

  assert.equal(find(doc, "skillInstallBody").textContent, preview.body, "正文必须整段展示，不能截断或摘要");
  assert.equal(find(doc, "skillInstallAttachments").textContent, "附件：ref.md、notes.md");
  assert.equal(installCalled, false, "看完预览、确认之前不该调用 install");
  const offNotice = find(doc, "skillInstallOffNotice").textContent;
  assert.ok(offNotice.includes("关") && offNotice.includes("确认"), `必须明说装完是关的，不然用户会把「没生效」当成「装失败」：${offNotice}`);

  // 收尾，避免未 resolve 的 promise 挂起测试进程。
  await find(doc, "skillInstallCancel").click();
  await p;
});

test("确认安装会调用 install（带 staging_id），并把后端的返回值解出来", async () => {
  const doc = makeDoc();
  const calls = [];
  const api = {
    previewSkill: async () => preview,
    installSkill: async (stagingId) => { calls.push(["install", stagingId]); return { installed: "示例 skill", enabled: false }; },
    discardSkill: async (stagingId) => { calls.push(["discard", stagingId]); },
  };
  const p = skillInstallDialog(doc, api);
  find(doc, "skillInstallUrl").value = "u";
  await find(doc, "skillInstallSubmit").click();
  await Promise.resolve();
  const overlay = overlayOf(doc);
  await find(doc, "skillInstallConfirm").click();

  const result = await p;
  assert.deepEqual(calls, [["install", "abc123"]], "确认要打 install，且只打 install，不该再打 discard");
  assert.deepEqual(result, { installed: "示例 skill", enabled: false });
  assert.equal(overlay.removed, true, "确认之后弹层要关掉");
});

test("预览阶段点取消：调用 discard 而不是 install，弹层 resolve 为假值", async () => {
  const doc = makeDoc();
  const calls = [];
  const api = {
    previewSkill: async () => preview,
    installSkill: async (stagingId) => { calls.push(["install", stagingId]); return {}; },
    discardSkill: async (stagingId) => { calls.push(["discard", stagingId]); },
  };
  const p = skillInstallDialog(doc, api);
  find(doc, "skillInstallUrl").value = "u";
  await find(doc, "skillInstallSubmit").click();
  await Promise.resolve();
  await find(doc, "skillInstallCancel").click();

  const result = await p;
  assert.deepEqual(calls, [["discard", "abc123"]], "取消要打 discard，且不该打 install");
  assert.equal(result, null);
});

test("URL 输入阶段直接取消：还没有暂存，discard 和 install 都不该被调用", async () => {
  const doc = makeDoc();
  let previewCalled = false;
  const api = {
    previewSkill: async () => { previewCalled = true; return preview; },
    installSkill: async () => { throw new Error("不该被调用"); },
    discardSkill: async () => { throw new Error("不该被调用——还没有暂存"); },
  };
  const p = skillInstallDialog(doc, api);
  await find(doc, "skillInstallCancel").click();
  const result = await p;
  assert.equal(result, null);
  assert.equal(previewCalled, false);
});

test("Esc 在预览阶段等同于点取消，也会 discard", async () => {
  const doc = makeDoc();
  const calls = [];
  const api = {
    previewSkill: async () => preview,
    installSkill: async () => { throw new Error("不该被调用"); },
    discardSkill: async (id) => { calls.push(id); },
  };
  const p = skillInstallDialog(doc, api);
  find(doc, "skillInstallUrl").value = "u";
  await find(doc, "skillInstallSubmit").click();
  await Promise.resolve();
  await doc.listeners.keydown({ key: "Escape" });
  const result = await p;
  assert.deepEqual(calls, ["abc123"]);
  assert.equal(result, null);
});

test("预览失败（409）：原样显示后端自己的消息，不换成通用的「安装失败」，也不落任何暂存", async () => {
  const doc = makeDoc();
  const backendMessage = "这个地址里没有 SKILL.md"; // 摘自 install.py 真实的错误文案
  const api = {
    previewSkill: async () => { const e = new Error(backendMessage); e.code = "install_failed"; throw e; },
    installSkill: async () => { throw new Error("不该被调用"); },
    discardSkill: async () => { throw new Error("不该被调用——预览就失败了，没有暂存"); },
  };
  const p = skillInstallDialog(doc, api);
  find(doc, "skillInstallUrl").value = "https://github.com/o/bad";
  await find(doc, "skillInstallSubmit").click();
  await Promise.resolve();
  await Promise.resolve();

  assert.equal(find(doc, "skillInstallError").textContent, backendMessage, "必须是后端原文，不是自造的通用文案");
  assert.equal(overlayOf(doc).removed, undefined, "失败之后弹层还在，用户可以改地址重试");

  await find(doc, "skillInstallCancel").click();
  await p;
});
