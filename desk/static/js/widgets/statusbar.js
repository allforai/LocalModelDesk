// ui:statusBar —— 只做 DOM 更新；文案与 tone 全部来自 pure/desk_state.js（R-ui-07）。
import { renderState } from "../pure/desk_state.js";
import { setIcon } from "../icons.js";

export function createStatusBar(root) {
  const mem = root.querySelector("[data-mem]");
  const holder = root.querySelector("[data-holder]");
  const media = root.querySelector("[data-media]");
  const next = root.querySelector("[data-next]");
  const nextPart = root.querySelector(".status-next");
  let isOffline = false;
  let lastIcon = null;
  return {
    update(deskState, snapshot, download = null, names = {}) {
      const view = renderState(deskState, snapshot, download, names);
      mem.textContent = view.memText;
      holder.textContent = view.holderText;
      media.textContent = view.mediaText;
      next.textContent = isOffline ? "服务失联" : view.nextText;
      root.dataset.tone = view.tone;
      if (nextPart) {
        nextPart.dataset.ok = isOffline ? "0" : view.nextOk ? "1" : "0";
        const icon = isOffline ? "x" : view.nextIcon;
        if (icon !== lastIcon) { setIcon(nextPart, icon, root.ownerDocument); lastIcon = icon; }
      }
    },
    offline(value) {
      isOffline = Boolean(value);
      root.dataset.offline = isOffline ? "1" : "0";
      if (isOffline) { next.textContent = "服务失联"; if (nextPart) { nextPart.dataset.ok = "0"; setIcon(nextPart, "x", root.ownerDocument); lastIcon = "x"; } }
    },
  };
}
