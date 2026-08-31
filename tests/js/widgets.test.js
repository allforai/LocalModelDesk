import test from "node:test";
import assert from "node:assert/strict";
import { createStatusBar } from "../../desk/static/js/widgets/statusbar.js";
import { confirmDialog } from "../../desk/static/js/widgets/confirm.js";

class FakeElement {
  constructor(tagName = "div") {
    this.tagName = tagName;
    this.children = [];
    this.dataset = {};
    this.listeners = {};
    this.textContent = "";
    this.className = "";
    this.parentNode = null;
  }

  append(...children) {
    for (const child of children) {
      child.parentNode = this;
      this.children.push(child);
    }
  }

  remove() {
    const siblings = this.parentNode?.children;
    if (siblings) siblings.splice(siblings.indexOf(this), 1);
    this.parentNode = null;
  }

  addEventListener(type, listener) {
    this.listeners[type] = listener;
  }

  click() {
    this.listeners.click?.();
  }
}

function find(node, predicate) {
  if (predicate(node)) return node;
  for (const child of node.children) {
    const result = find(child, predicate);
    if (result) return result;
  }
  return null;
}

test("statusbar 将 desk state 和内存快照更新到 DOM，离线时保留失联提示", () => {
  const parts = Object.fromEntries(["mem", "holder", "media", "next"]
    .map((name) => [name, new FakeElement("span")]));
  const root = new FakeElement("header");
  root.querySelector = (selector) => parts[selector.slice(6, -1)];
  const bar = createStatusBar(root);
  const state = { holder: { kind: "llm", label: "Qwen" }, media_busy: false, can_start: { ok: true } };
  const snapshot = { total_bytes: 16 * 1024 ** 3, used_bytes: 6 * 1024 ** 3, available_bytes: 10 * 1024 ** 3 };

  bar.update(state, snapshot);
  assert.equal(parts.mem.textContent, "已用 6.0 / 总 16.0 GB（可用 10.0 GB）");
  assert.equal(parts.holder.textContent, "LLM：Qwen");
  assert.equal(parts.media.textContent, "媒体：空闲");
  assert.equal(parts.next.textContent, "可开下一件重活");
  assert.equal(root.dataset.tone, "busy");

  bar.offline(true);
  bar.update(state, snapshot);
  assert.equal(root.dataset.offline, "1");
  assert.equal(parts.next.textContent, "服务失联");

  bar.offline(false);
  bar.update(state, snapshot);
  assert.equal(root.dataset.offline, "0");
  assert.equal(parts.next.textContent, "可开下一件重活");
});

test("confirmDialog 渲染文案，确认或取消后移除弹层并返回选择", async () => {
  const doc = { body: new FakeElement("body"), createElement: (tag) => new FakeElement(tag) };
  const cancelled = confirmDialog(doc, { title: "删除模型？", message: "将回收 2 GB", confirmLabel: "删除", cancelLabel: "保留" });
  const cancelOverlay = doc.body.children[0];
  assert.equal(find(cancelOverlay, (el) => el.tagName === "h3").textContent, "删除模型？");
  assert.equal(find(cancelOverlay, (el) => el.tagName === "p").textContent, "将回收 2 GB");
  find(cancelOverlay, (el) => el.tagName === "button" && el.textContent === "保留").click();
  assert.equal(await cancelled, false);
  assert.equal(doc.body.children.length, 0);

  const confirmed = confirmDialog(doc, { title: "继续？", message: "不可撤销" });
  const confirmOverlay = doc.body.children[0];
  const confirmButton = find(confirmOverlay, (el) => el.tagName === "button" && el.textContent === "确定");
  assert.equal(confirmButton.className, "danger");
  confirmButton.click();
  assert.equal(await confirmed, true);
  assert.equal(doc.body.children.length, 0);
});
