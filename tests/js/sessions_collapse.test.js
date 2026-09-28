// 会话栏收起/展开（四个页面共用一个开关，记在本机存储里）。
import test from "node:test";
import assert from "node:assert/strict";
import { Element, find } from "./support/fake_dom.js";
import { initSessionsCollapse, STORAGE_KEY } from "../../desk/static/js/widgets/sessions_collapse.js";

function makeAside() {
  const aside = new Element("aside");
  aside.className = "sessions";
  const newBtn = new Element("button");
  newBtn.textContent = "新会话";
  newBtn.className = "btn-primary";
  const list = new Element("ul");
  aside.append(newBtn, list);
  return { aside, newBtn, list };
}
const doc = { createElement: (tag) => new Element(tag) };
const memoryStorage = (initial = {}) => {
  const data = { ...initial };
  return { data, getItem: (k) => (k in data ? data[k] : null), setItem: (k, v) => { data[k] = String(v); } };
};
const toggleOf = (aside) => find(aside, (n) => "sessionsToggle" in (n.dataset ?? {}));

test("默认展开：每个会话栏顶部有「收起会话栏」按钮，新会话按钮的文字被单独包起来", () => {
  const parts = [makeAside(), makeAside()];
  initSessionsCollapse(parts.map((p) => p.aside), { doc, storage: memoryStorage() });
  for (const { aside, newBtn } of parts) {
    const toggle = toggleOf(aside);
    assert.ok(toggle);
    assert.equal(toggle.getAttribute("aria-label"), "收起会话栏");
    assert.equal(toggle.getAttribute("aria-expanded"), "true");
    assert.equal(aside.classList.contains("is-collapsed"), false);
    assert.equal(newBtn.getAttribute("aria-label"), "新会话");
    assert.ok(find(newBtn, (n) => n.className === "sessions-new-label" && n.textContent === "新会话"));
    assert.ok(newBtn.classList.contains("sessions-new"));
  }
});

test("点任一个收起按钮：所有会话栏一起收起，标签与 aria 跟着变，状态写进存储；再点展开", async () => {
  const parts = [makeAside(), makeAside(), makeAside()];
  const storage = memoryStorage();
  initSessionsCollapse(parts.map((p) => p.aside), { doc, storage });
  await toggleOf(parts[1].aside).click();
  for (const { aside } of parts) {
    assert.equal(aside.classList.contains("is-collapsed"), true);
    assert.equal(toggleOf(aside).getAttribute("aria-label"), "展开会话栏");
    assert.equal(toggleOf(aside).getAttribute("aria-expanded"), "false");
    assert.equal(toggleOf(aside).title, "展开会话栏");
  }
  assert.equal(storage.data[STORAGE_KEY], "1");
  await toggleOf(parts[0].aside).click();
  for (const { aside } of parts) assert.equal(aside.classList.contains("is-collapsed"), false);
  assert.equal(storage.data[STORAGE_KEY], "0");
});

test("重新初始化时从存储恢复收起状态", () => {
  const { aside } = makeAside();
  initSessionsCollapse([aside], { doc, storage: memoryStorage({ [STORAGE_KEY]: "1" }) });
  assert.equal(aside.classList.contains("is-collapsed"), true);
  assert.equal(toggleOf(aside).getAttribute("aria-expanded"), "false");
});

test("存储读写抛异常：默认展开，切换照常工作，不报错", async () => {
  const broken = { getItem() { throw new Error("denied"); }, setItem() { throw new Error("denied"); } };
  const { aside } = makeAside();
  const ctl = initSessionsCollapse([aside], { doc, storage: broken });
  assert.equal(ctl.isCollapsed(), false);
  await toggleOf(aside).click();
  assert.equal(ctl.isCollapsed(), true);
  assert.equal(aside.classList.contains("is-collapsed"), true);
});

test("没有存储对象（null）也能用", async () => {
  const { aside } = makeAside();
  const ctl = initSessionsCollapse([aside], { doc, storage: null });
  await toggleOf(aside).click();
  assert.equal(ctl.isCollapsed(), true);
});
