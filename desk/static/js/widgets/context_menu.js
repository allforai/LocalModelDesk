// 通用右键菜单（会话卡改造，2026-10-25）：会话卡（聊天页与图片/音乐/视频页）的动作不再靠「悬停才露出的按钮列」——
// 那条列常驻在卡片右侧一直扣标题宽度，标题被挤成「第1行：甲组记录，…」。改成右键落一个浮层，
// 动作仍由调用方给（items），这里只管画菜单、收边、键盘与关闭。
//
// 关法：选中一项、外部按下指针、Esc、窗口滚动/改尺寸。开菜单就把焦点放到第一项，
// 上下键/Home/End 在项间走，Tab 往下走前先把焦点还给触发元素，Esc 关掉并把焦点还给触发元素
// （焦点已经不在菜单里时只关、不抢焦点）。
import { addIcon } from "../icons.js";

const EDGE = 8; // 浮层与视口边缘至少留的空隙

const inside = (node, target) => {
  for (let walk = target; walk; walk = walk.parentNode) if (walk === node) return true;
  return false;
};

// 键盘上开右键菜单的两个按键（Windows 菜单键 / macOS Shift+F10），会话卡与媒体会话卡共用这一个口径。
export const isContextMenuKey = (event) => event?.key === "ContextMenu" || (event?.shiftKey === true && event?.key === "F10");

// 把一个菜单挂在某个节点上：右键开、吃掉浏览器自己的菜单。
// 改名输入框（正在改名时那块）里的右键留着不动——那里的菜单是粘贴/全选。
// 返回 open 供键盘那一侧复用（调用方自己判 isContextMenuKey）。
export function attachContextMenu(doc, node, { label, items, trigger = node }) {
  const open = (event) => openContextMenu(doc, { label, x: event?.clientX, y: event?.clientY, anchor: node, trigger, items });
  node.addEventListener("contextmenu", (event) => {
    if (/^(input|textarea)$/i.test(event.target?.tagName ?? "")) return;
    event.preventDefault?.();
    event.stopPropagation?.();
    open(event);
  });
  return open;
}

export function openContextMenu(doc, { items = [], x, y, anchor = null, label = "菜单", trigger = null, onClose } = {}) {
  const menu = doc.createElement("div");
  menu.className = "context-menu";
  menu.setAttribute("role", "menu");
  menu.setAttribute("aria-label", label);

  const buttons = [];
  const offs = [];
  const state = { closed: false, index: 0 };
  const listen = (target, type, handler, options) => {
    if (!target?.addEventListener) return;
    target.addEventListener(type, handler, options);
    offs.push(() => target.removeEventListener?.(type, handler, options));
  };
  const close = ({ restoreFocus = false } = {}) => {
    if (state.closed) return;
    state.closed = true;
    for (const off of offs) off();
    offs.length = 0;
    menu.remove?.();
    if (restoreFocus) trigger?.focus?.();
    onClose?.();
  };
  const focusItem = (index) => {
    if (!buttons.length) return;
    state.index = ((index % buttons.length) + buttons.length) % buttons.length;
    buttons[state.index].focus?.();
  };

  for (const item of items) {
    const button = doc.createElement("button");
    button.className = item.danger ? "menu-item danger" : "menu-item";
    button.setAttribute("type", "button");
    button.setAttribute("role", "menuitem");
    button.textContent = item.label;
    if (item.icon) addIcon(button, item.icon, doc);
    button.addEventListener("click", () => { close(); item.onSelect?.(); });
    menu.append(button);
    buttons.push(button);
  }

  menu.addEventListener("keydown", (event) => {
    if (event.key === "Escape") { event.preventDefault?.(); event.stopPropagation?.(); return close({ restoreFocus: true }); }
    // Tab 不接管（不 preventDefault），但焦点要先还给触发元素：菜单项马上要被移除，
    // 不还的话焦点会掉回 body，下一次 Tab 从页面开头数起。
    if (event.key === "Tab") return close({ restoreFocus: true });
    if (event.key === "ArrowDown") { event.preventDefault?.(); return focusItem(state.index + 1); }
    if (event.key === "ArrowUp") { event.preventDefault?.(); return focusItem(state.index - 1); }
    if (event.key === "Home") { event.preventDefault?.(); return focusItem(0); }
    if (event.key === "End") { event.preventDefault?.(); return focusItem(buttons.length - 1); }
  });

  // 摆位：优先用指针坐标，没有（键盘打开）就贴着触发元素的左下角；两种都要收回视口内，
  // 下方放不下时翻到指针/锚点上方。
  const place = () => {
    const style = menu.style;
    if (!style) return;
    const win = doc.defaultView;
    const rect = anchor?.getBoundingClientRect?.();
    const px = Number.isFinite(x) ? x : (rect?.left ?? 0) + 8;
    const py = Number.isFinite(y) ? y : (rect?.bottom ?? 0) + 4;
    let left = px;
    let top = py;
    style.left = `${left}px`;
    style.top = `${top}px`;
    const size = menu.getBoundingClientRect?.();
    const vw = win?.innerWidth ?? 0;
    const vh = win?.innerHeight ?? 0;
    if (!size || !vw || !vh) return;
    if (left + (size.width ?? 0) > vw - EDGE) left = Math.max(EDGE, vw - (size.width ?? 0) - EDGE);
    if (top + (size.height ?? 0) > vh - EDGE) top = Math.max(EDGE, py - (size.height ?? 0) - 4);
    style.left = `${left}px`;
    style.top = `${top}px`;
  };

  // Esc 也要在文档层面听一份：焦点可能不在菜单里（开菜单之后别处的异步代码抢走焦点，比如
  // 「新会话」把焦点放回输入框），那时候按 Esc 总得能关掉这个浮层——跟 confirm.js 同一个办法。
  // 这份只关不收焦点：焦点本来就该留在用户手上那个控件上。
  listen(doc, "keydown", (event) => { if (event.key === "Escape") close(); });
  listen(doc, "pointerdown", (event) => { if (!inside(menu, event.target)) close(); }, true);
  listen(doc.defaultView, "resize", () => close());
  listen(doc.defaultView, "scroll", () => close(), true);

  doc.body.append(menu);
  place();
  focusItem(0);
  return { close, element: menu };
}
