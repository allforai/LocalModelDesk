import test from "node:test"; import assert from "node:assert/strict";
import { confirmDialog } from "../../desk/static/js/widgets/confirm.js";
class El { constructor(t) { this.tagName = t; this.children = []; this.attrs = {}; this.listeners = {}; this.className = ""; this.textContent = ""; } append(...n) { this.children.push(...n); } setAttribute(k, v) { this.attrs[k] = v; } addEventListener(t, l) { this.listeners[t] = l; } remove() { this.removed = true; } focus() { this.focused = true; } }
const doc = { body: new El("body"), createElement: (t) => new El(t), addEventListener(t, l) { this.listeners = { [t]: l }; }, removeEventListener() {} };

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
