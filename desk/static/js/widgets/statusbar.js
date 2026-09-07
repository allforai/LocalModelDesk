// ui:statusBar —— 只做 DOM 更新；文案与 tone 全部来自 pure/desk_state.js（R-ui-07）。
import { renderState } from "../pure/desk_state.js";

export function createStatusBar(root) {
  const mem = root.querySelector("[data-mem]");
  const holder = root.querySelector("[data-holder]");
  const media = root.querySelector("[data-media]");
  const next = root.querySelector("[data-next]");
  let isOffline = false;
  return {
    update(deskState, snapshot, download = null) {
      const view = renderState(deskState, snapshot, download);
      mem.textContent = view.memText;
      holder.textContent = view.holderText;
      media.textContent = view.mediaText;
      next.textContent = isOffline ? "服务失联" : view.nextText;
      root.dataset.tone = view.tone;
    },
    offline(value) {
      isOffline = Boolean(value);
      root.dataset.offline = isOffline ? "1" : "0";
      if (isOffline) next.textContent = "服务失联";
    },
  };
}
