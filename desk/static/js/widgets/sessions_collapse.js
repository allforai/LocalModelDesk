// 会话栏收起/展开：四个页面（聊天、图片、音乐、视频）的 aside.sessions 共用一个开关。
// 收起后留一条窄轨，只剩「展开会话栏」与「新会话」两个图标按钮；状态记在本机存储里，
// 读写不了存储时默认展开（这只是个人偏好，丢了无妨）。动画全在 CSS 里。
import { setIcon } from "../icons.js";

export const STORAGE_KEY = "lmd.sessionsCollapsed";
const COLLAPSE = "收起会话栏";
const EXPAND = "展开会话栏";

const isText = (node) => node?.nodeType === 3 || node?.tagName === "#text";

// 把「新会话」按钮里的文字包进 span，收起时只藏文字、留图标（按钮仍有 aria-label）。
function wrapLabel(doc, button) {
  const label = String(button.textContent ?? "").trim();
  const nodes = [...(button.childNodes ?? button.children ?? [])];
  for (const node of nodes) {
    if (!isText(node)) continue;
    if (typeof node.remove === "function") node.remove();
    else button.children.splice(button.children.indexOf(node), 1);   // 测试用的假 DOM 文字节点没有 remove()
  }
  const span = doc.createElement("span");
  span.className = "sessions-new-label";
  span.textContent = label;
  button.append(span);
  button.setAttribute("aria-label", label);
  button.classList?.add?.("sessions-new");
  return label;
}

export function initSessionsCollapse(asides, { doc = globalThis.document, storage = globalThis.localStorage } = {}) {
  let collapsed = read();
  const toggles = [];

  for (const aside of asides) {
    const newBtn = [...(aside.children ?? [])].find((n) => String(n.tagName).toLowerCase() === "button");
    const head = doc.createElement("div");
    head.className = "sessions-head";
    const toggle = doc.createElement("button");
    toggle.type = "button";
    toggle.className = "btn-quiet sessions-toggle";
    toggle.dataset.sessionsToggle = "";
    toggle.addEventListener("click", () => set(!collapsed));
    if (newBtn) {
      const label = wrapLabel(doc, newBtn);
      newBtn.title = label;
      newBtn.remove();
      head.append(newBtn);
    }
    head.append(toggle);
    const first = aside.children?.[0] ?? null;
    if (first) aside.insertBefore(head, first); else aside.append(head);
    toggles.push({ aside, toggle });
  }
  apply();

  function read() {
    try { return storage?.getItem(STORAGE_KEY) === "1"; } catch { return false; }
  }
  function set(value) {
    collapsed = !!value;
    try { storage?.setItem(STORAGE_KEY, collapsed ? "1" : "0"); } catch { /* 偏好写不进去就只在本次生效 */ }
    apply();
  }
  function apply() {
    const label = collapsed ? EXPAND : COLLAPSE;
    for (const { aside, toggle } of toggles) {
      aside.classList.toggle("is-collapsed", collapsed);
      toggle.setAttribute("aria-label", label);
      toggle.setAttribute("aria-expanded", String(!collapsed));
      toggle.title = label;
      setIcon(toggle, collapsed ? "sidebar-open" : "sidebar-close", doc);
    }
  }
  return { isCollapsed: () => collapsed, set };
}
