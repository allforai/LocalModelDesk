// 通用右键菜单（会话卡的动作入口）：只测这个浮层自己的契约——画什么、怎么关、焦点去哪。
// 会话卡怎么用它（右键 / Shift+F10）由 chat_pane.test.js 与 tests/e2e/test_sessions.py 覆盖。
import test from "node:test";
import assert from "node:assert/strict";
import { Element, find, findAll } from "./support/fake_dom.js";
import { openContextMenu } from "../../desk/static/js/widgets/context_menu.js";

function makeDoc() {
  const doc = {
    body: new Element("body"),
    createElement: (tag) => new Element(tag),
    listeners: {},
    addEventListener(type, listener) { (this.listeners[type] ??= []).push(listener); },
    removeEventListener(type, listener) {
      this.listeners[type] = (this.listeners[type] ?? []).filter((fn) => fn !== listener);
    },
    dispatch(type, event = {}) {
      return Promise.all((this.listeners[type] ?? []).map((fn) => fn({ preventDefault() {}, stopPropagation() {}, ...event })));
    },
  };
  return doc;
}

const menuOf = (doc) => doc.body.children.find((node) => node.className === "context-menu") ?? null;
const itemsOf = (doc) => menuOf(doc)?.children ?? [];
// 按钮里除图标还可能有文字节点（textContent 会落成 #text 子节点），只挑图标看。
const iconsOf = (button) => button.children.filter((child) => child.className).map((child) => child.className);

const open = (doc, extra = {}) => openContextMenu(doc, {
  label: "会话操作：甲组记录",
  items: [{ label: "改名", icon: "pencil", onSelect: extra.onRename }, { label: "删除", icon: "trash", danger: true, onSelect: extra.onDelete }],
  x: extra.x, y: extra.y, anchor: extra.anchor ?? null, trigger: extra.trigger ?? null,
  onClose: extra.onClose,
});

test("菜单挂在 body 上，role=menu 带名字，两项按「改名、删除」顺序且删除是危险项", () => {
  const doc = makeDoc();
  const handle = open(doc);
  const menu = menuOf(doc);
  assert.equal(menu.getAttribute("role"), "menu");
  assert.equal(menu.getAttribute("aria-label"), "会话操作：甲组记录");
  const items = itemsOf(doc);
  assert.equal(items.length, 2);
  assert.deepEqual(items.map((item) => item.getAttribute("role")), ["menuitem", "menuitem"]);
  assert.deepEqual(iconsOf(items[0]), ["icon icon-pencil"]);
  assert.deepEqual(iconsOf(items[1]), ["icon icon-trash"]);
  assert.equal(items[0].classList.contains("menu-item"), true);
  assert.equal(items[0].classList.contains("danger"), false);
  assert.equal(items[1].classList.contains("menu-item"), true);
  assert.equal(items[1].classList.contains("danger"), true, "删除是危险项");
  assert.equal(handle.element, menu);
});

test("点一项：先收菜单再执行动作（浮层不再挡着页面）", () => {
  const doc = makeDoc();
  const done = [];
  open(doc, { onRename: () => done.push(["rename", menuOf(doc)]), onClose: () => done.push(["close"]) });
  const [rename] = itemsOf(doc);
  rename.dispatch("click", {});
  assert.deepEqual(done[0], ["close"]);
  assert.equal(menuOf(doc), null, "动作执行时菜单已经收掉");
  assert.deepEqual(done[1], ["rename", null]);
});

test("Esc 与 Tab 都收菜单，焦点都还给触发元素（Tab 之后要继续从卡片往下走）", async () => {
  const doc = makeDoc();
  const card = new Element("li");
  const handle = open(doc, { trigger: card, anchor: card });
  assert.equal(itemsOf(doc)[0].focused, 1, "开菜单就把焦点放到第一项");
  handle.element.dispatch("keydown", { key: "Escape" });
  assert.equal(menuOf(doc), null);
  assert.equal(card.focused, 1, "焦点回到触发元素");

  const again = makeDoc();
  const card2 = new Element("li");
  const handle2 = open(again, { trigger: card2, anchor: card2 });
  handle2.element.dispatch("keydown", { key: "Tab" });
  assert.equal(menuOf(again), null);
  assert.equal(card2.focused, 1, "焦点先回卡片，Tab 的默认行为再从卡片往下走");
});

test("焦点被别处抢走时 Esc 照样收菜单，且不把焦点拽回卡片", async () => {
  // 真事：右键的同时「新会话」刚创建完，异步把焦点放回聊天输入框，菜单项就没焦点了。
  const doc = makeDoc();
  const card = new Element("li");
  const input = new Element("textarea");
  open(doc, { trigger: card, anchor: card });
  assert.equal(menuOf(doc) !== null, true);
  await doc.dispatch("keydown", { key: "Escape", target: input });
  assert.equal(menuOf(doc), null);
  assert.equal(card.focused, 0, "焦点在别处时按 Esc，不该把焦点拽回卡片");
});

test("上下键在项之间循环，Home/End 到两头", () => {
  const doc = makeDoc();
  const handle = open(doc);
  const [rename, remove] = itemsOf(doc);
  // 焦点计数只增不减，拿它的相对大小认「现在焦点在哪一项」比数次数稳。
  const focused = () => (rename.focused > remove.focused ? "改名" : "删除");
  assert.equal(focused(), "改名", "开菜单先落在第一项");
  handle.element.dispatch("keydown", { key: "ArrowDown" });
  assert.equal(focused(), "删除");
  handle.element.dispatch("keydown", { key: "ArrowDown" });
  assert.equal(focused(), "改名", "到底再往下回到第一项");
  handle.element.dispatch("keydown", { key: "ArrowUp" });
  assert.equal(focused(), "删除", "到头再往上回到最后一项");
  handle.element.dispatch("keydown", { key: "Home" });
  assert.equal(focused(), "改名");
  handle.element.dispatch("keydown", { key: "End" });
  assert.equal(focused(), "删除");
  assert.equal(menuOf(doc), handle.element, "方向键不关菜单");
});

test("外部按下指针收菜单；按在菜单自己身上不收（那是选项按钮）", async () => {
  const doc = makeDoc();
  const handle = open(doc);
  await doc.dispatch("pointerdown", { target: itemsOf(doc)[0] });
  assert.equal(menuOf(doc), handle.element, "菜单内的按下不能先把菜单撤了");
  await doc.dispatch("pointerdown", { target: new Element("div") });
  assert.equal(menuOf(doc), null);
  assert.equal(doc.listeners.pointerdown.length, 0, "收掉之后不留全局监听");
});

test("有指针坐标就落在坐标上；只给锚点（键盘打开）就贴着它的左下角", () => {
  const pointed = makeDoc();
  open(pointed, { x: 120, y: 260 });
  assert.equal(menuOf(pointed).style.left, "120px");
  assert.equal(menuOf(pointed).style.top, "260px");

  const keyboard = makeDoc();
  const card = new Element("li");
  card.getBoundingClientRect = () => ({ left: 10, top: 20, right: 200, bottom: 60, width: 190, height: 40 });
  open(keyboard, { anchor: card });
  assert.equal(menuOf(keyboard).style.left, "18px");
  assert.equal(menuOf(keyboard).style.top, "64px");
});

test("自己 close 一次之后再 close 不会重复回调（关菜单是幂等的）", () => {
  const doc = makeDoc();
  let closes = 0;
  const handle = open(doc, { onClose: () => { closes += 1; } });
  handle.close();
  handle.close();
  assert.equal(closes, 1);
  assert.equal(find(doc.body, (node) => node.className === "context-menu"), null);
  assert.equal(findAll(doc.body, (node) => node.className === "context-menu").length, 0);
});
