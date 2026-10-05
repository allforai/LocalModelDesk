// 素材库预览弹层（素材库预览设计 L-40–L-44）：遮罩 + role=dialog + aria-modal + Esc/点遮罩关闭，骨架同 confirm.js、
// media_picker.js。←/→ 在打开时的条目快照里翻页、到头停住；空格在焦点不在控件上时关闭；翻页或关闭时停止并释放上一件媒体。
import { addIcon } from "../icons.js";
import { renderErrorBlock } from "./error_block.js";
import { clockText, hasMedia } from "../pure/library_view.js";
import { formatBytes, formatDuration, formatTimestamp } from "../pure/format.js";

const KIND_LABEL = { video: "视频", music: "音乐", image: "图片", file: "文件" };
const STATUS_LABEL = { done: "完成", failed: "失败", cancelled: "已取消" };
// 这些控件自己要用空格（按钮、播放器）或方向键（播放器进度、输入框），弹层不抢。
const SPACE_OWNERS = new Set(["button", "input", "textarea", "select", "video", "audio", "a"]);
const ARROW_OWNERS = new Set(["input", "textarea", "select", "video", "audio"]);
const tagOf = (target) => String(target?.tagName ?? "").toLowerCase();

export function openLibraryPreview(doc, { items, index = 0, serveOutput, onFill, onReveal, onClose }) {
  let at = Math.min(Math.max(0, index), items.length - 1);
  let media = null;
  let closed = false;
  const el = (tag, className = "") => {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    return node;
  };
  const button = (label, icon) => {
    const node = el("button");
    node.textContent = label;
    addIcon(node, icon, doc);
    return node;
  };
  const note = (text) => {
    const p = el("p", "lib-preview-note");
    p.textContent = text;
    return p;
  };

  const overlay = el("div", "overlay lib-preview-overlay");
  const box = el("div", "dialog lib-preview");
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-modal", "true");
  box.tabIndex = -1;
  const stage = el("div", "lib-preview-stage");
  stage.dataset.libPreviewStage = "";
  const info = el("div", "lib-preview-info");
  const nav = (label, icon, dataKey, step) => {
    const node = el("button", "btn-quiet lib-preview-nav");
    node.setAttribute("aria-label", label);
    node.title = label;
    node.dataset[dataKey] = "";
    addIcon(node, icon, doc);
    node.addEventListener("click", () => go(at + step));
    return node;
  };
  const prev = nav("上一件", "chevron-left", "libPrev", -1);
  const next = nav("下一件", "chevron-right", "libNext", 1);
  box.append(prev, stage, next, info);
  overlay.append(box);

  function release() {
    if (!media) return;
    media.pause?.();
    media.removeAttribute?.("src");
    media.load?.();
    media = null;
  }

  function stageNode(item) {
    if (item.missing) return note("文件已不在");
    if (!hasMedia(item)) {
      if (item.error) {
        const [code, ...rest] = item.error.split(": ");
        return renderErrorBlock(doc, { code, message: rest.join(": ") });
      }
      return note(STATUS_LABEL[item.status] ?? "没有成品");
    }
    const src = serveOutput(item.output);
    if (item.kind === "image") {
      const img = el("img");
      img.src = src;
      img.alt = item.title;
      return img;
    }
    if (item.kind === "video") {
      media = el("video");
      media.controls = true;
      media.autoplay = true;
      media.src = src;
      return media;
    }
    if (item.kind === "music") {
      const wrap = el("div", "lib-preview-music");
      const art = el("div", "lib-preview-art");
      addIcon(art, "music", doc);
      media = el("audio");
      media.controls = true;
      media.autoplay = true;
      media.src = src;
      wrap.append(art, media);
      return wrap;
    }
    return note("无法预览这种文件");
  }

  function infoNodes(item) {
    const title = el("h3", "lib-preview-title");
    title.textContent = item.title;
    const lines = [
      [KIND_LABEL[item.kind] ?? item.kind, STATUS_LABEL[item.status] ?? item.status, formatTimestamp(item.ts)].join(" · "),
      item.spec,
      item.duration_s != null ? `时长 ${clockText(item.duration_s)}` : "",
      item.gen_s != null ? `耗时 ${formatDuration(item.gen_s)}` : "",
      item.output ? `${item.output}${item.bytes != null ? ` · ${formatBytes(item.bytes)}` : ""}` : "",
    ].filter(Boolean).map((text) => {
      const p = el("p", "lib-meta");
      p.textContent = text;
      return p;
    });
    const error = el("p", "inline-error");
    error.dataset.libPreviewError = "";
    const actions = el("div", "lib-preview-actions");
    if (item.plan) {
      const fill = button("回填参数", "sliders");
      fill.addEventListener("click", () => {
        const plan = item.plan;
        close();
        onFill?.(plan);
      });
      actions.append(fill);
    }
    if (hasMedia(item)) {
      const reveal = button("在访达中显示", "folder");
      reveal.addEventListener("click", async () => {
        error.textContent = "";
        try { await onReveal?.(item.output); } catch (err) { error.textContent = err.message; }
      });
      actions.append(reveal);
    }
    const closeBtn = button("关闭", "x");
    closeBtn.dataset.libPreviewClose = "";
    closeBtn.addEventListener("click", () => close());
    actions.append(closeBtn);
    return [title, ...lines, actions, error];
  }

  function show(i) {
    release();
    at = i;
    const item = items[at];
    box.setAttribute("aria-label", item.title);
    stage.replaceChildren(stageNode(item));
    info.replaceChildren(...infoNodes(item));
    prev.disabled = at === 0;
    next.disabled = at === items.length - 1;
  }

  function go(i) {
    if (closed || i < 0 || i >= items.length || i === at) return;
    show(i);
  }

  function onKey(event) {
    if (closed) return;
    const tag = tagOf(event.target);
    if (event.key === "Escape") { event.preventDefault?.(); close(); return; }
    if ((event.key === "ArrowLeft" || event.key === "ArrowRight") && !ARROW_OWNERS.has(tag)) {
      event.preventDefault?.();
      go(at + (event.key === "ArrowLeft" ? -1 : 1));
      return;
    }
    if (event.key === " " && !SPACE_OWNERS.has(tag)) { event.preventDefault?.(); close(); }
  }

  function close() {
    if (closed) return;
    closed = true;
    release();
    doc.removeEventListener?.("keydown", onKey);
    overlay.remove();
    onClose?.(at);
  }

  overlay.addEventListener("click", (event) => { if (event.target === overlay) close(); });
  doc.addEventListener?.("keydown", onKey);
  doc.body.append(overlay);
  show(at);
  box.focus?.();
  return { close, current: () => at };
}
