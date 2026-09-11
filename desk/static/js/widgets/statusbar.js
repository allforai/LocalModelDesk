// ui:statusBar —— 只做 DOM 更新；文案与 tone 全部来自 pure/desk_state.js（R-ui-07）。
// 每个部件同时写长/短两套文案（wide-only/narrow-only），CSS 按宽度切换可见的一套，
// 永不用 overflow:hidden 截断，也永不整块隐藏某个状态（F1/W4/W6）。
import { renderState } from "../pure/desk_state.js";
import { setIcon } from "../icons.js";

const MEDIA_HOLDER_LABEL = { video: "视频生成中", music: "音乐生成中" };

// desk_state.js 的 holderText 对媒体持有者省去了「内存里：」前缀（与右侧媒体状态重复陈述，
// W4）。这里直接从 deskState 派生，不依赖 pure/desk_state.js 的现成字符串。
function holderName(deskState, names) {
  const holder = deskState?.holder;
  if (!holder) return "无";
  if (holder.kind === "llm") return names?.[holder.label] ?? holder.label;
  return MEDIA_HOLDER_LABEL[holder.kind] ?? `${holder.kind}：${holder.label}`;
}

function setPart(doc, el, wide, narrow) {
  if (!el || !doc) return;
  const w = doc.createElement("span");
  w.className = "wide-only";
  w.textContent = wide;
  const n = doc.createElement("span");
  n.className = "narrow-only";
  n.textContent = narrow;
  if (el.replaceChildren) el.replaceChildren(w, n);
  else { el.textContent = ""; el.append(w, n); }
  el.setAttribute?.("title", wide);
}

export function createStatusBar(root) {
  const doc = root.ownerDocument;
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
      const name = holderName(deskState, names);
      const nextNarrow = view.nextOk ? "可开工" : "忙";
      setPart(doc, mem, view.memText, view.memText);
      setPart(doc, holder, `内存里：${name}`, name);
      // Same badge family as the chat pane's model-state pill (F15): loaded llm
      // holds it (ok), a media job holds it (busy), nothing holds it (none).
      if (holder) holder.className = `badge badge-${deskState?.holder ? (deskState.holder.kind === "llm" ? "ok" : "busy") : "none"}`;
      setPart(doc, media, view.mediaText, `媒体：${deskState?.media_busy ? "忙" : "空闲"}`);
      setPart(doc, next, isOffline ? "服务失联" : view.nextText, isOffline ? "服务失联" : nextNarrow);
      root.dataset.tone = view.tone;
      if (nextPart) {
        nextPart.dataset.ok = isOffline ? "0" : view.nextOk ? "1" : "0";
        const icon = isOffline ? "x" : view.nextIcon;
        if (icon !== lastIcon) { setIcon(nextPart, icon, doc); lastIcon = icon; }
      }
    },
    offline(value) {
      isOffline = Boolean(value);
      root.dataset.offline = isOffline ? "1" : "0";
      if (isOffline) {
        setPart(doc, next, "服务失联", "服务失联");
        if (nextPart) { nextPart.dataset.ok = "0"; setIcon(nextPart, "x", doc); lastIcon = "x"; }
      }
    },
  };
}
