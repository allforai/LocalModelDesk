// 图片会话时间线里的一张尝试卡片（设计 §7.3–§7.5）。只画 DOM，不发请求：
// 点击、两个动作、取消、图片加载失败都经回调交还给 panes/image.js。
import { addIcon } from "../icons.js";
import { renderErrorBlock } from "./error_block.js";
import { attemptLabel, attemptView, runningLabel, specLine } from "../pure/image_session.js";

function el(doc, tag, className, text) {
  const node = doc.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function iconBlock(doc, view) {
  const block = el(doc, "div", `attempt-thumb attempt-icon tone-${view.tone}`);
  block.setAttribute("aria-hidden", "true");
  addIcon(block, view.icon, doc);
  return block;
}

function advancedList(doc, params) {
  const details = el(doc, "details", "attempt-advanced");
  details.append(el(doc, "summary", "", "高级参数"));
  const list = el(doc, "dl", "attempt-params");
  for (const [label, value] of [["宽度", params?.width], ["高度", params?.height], ["步数", params?.steps], ["种子", params?.seed]]) {
    list.append(el(doc, "dt", "", label), el(doc, "dd", "", value == null ? "—" : String(value)));
  }
  details.append(list);
  return details;
}

// 返回 {node, running, recompose, image}：running 是 running 卡片里轮询要就地更新的几个元素，
// recompose 是「换个构图」按钮与其下方原因行（不可用时由面板更新），image 是展开卡片的大图
// （面板按时间线高度给它定上限，让标题、整张图与两个动作能同时看到）。
export function renderAttemptCard(doc, opts) {
  const { attempt, index, selected, broken = false, serveOutput } = opts;
  const view = attemptView(attempt, { broken });
  const running = view.kind === "running";
  const expanded = running || selected;
  const card = el(doc, "li", `card attempt attempt-${view.kind}`);
  card.dataset.attemptId = attempt.id;
  card.dataset.attemptStatus = view.kind;
  card.tabIndex = 0;
  card.setAttribute("aria-expanded", expanded ? "true" : "false");
  if (selected) card.classList.add("selected");
  const prompt = attempt?.params?.prompt ?? "";

  const row = el(doc, "div", "attempt-row");
  // 展开的 done 卡片不再在标题行放缩略图：下面的大图就是它（§7.1 草图；缩略图与大图并列时
  // 窄窗里大图会被挤到缩略图大小，见 B-01）。失败、取消、文件不在的图标块照旧（D-84）。
  if (view.kind === "done" && !expanded) {
    const thumb = el(doc, "div", "attempt-thumb");
    const img = el(doc, "img");
    img.alt = prompt || "生成的图片";
    img.addEventListener("error", () => opts.onBroken?.(attempt));
    img.src = serveOutput(attempt.output);
    thumb.append(img);
    row.append(thumb);
  } else if (view.icon) {
    row.append(iconBlock(doc, view));
  }
  const summary = el(doc, "div", "attempt-summary");
  const head = el(doc, "div", "attempt-head");
  const label = el(doc, "span", "attempt-label", running ? runningLabel(index, opts.elapsed) : attemptLabel(index, attempt));
  head.append(label);
  if (view.badge && !running) head.append(el(doc, "span", `badge attempt-badge tone-${view.tone}`, view.badge));
  summary.append(head);
  const promptLine = el(doc, "p", "attempt-prompt", prompt);
  promptLine.title = prompt;
  summary.append(promptLine, el(doc, "p", "attempt-spec", specLine(attempt.params)));
  if (view.title && view.title !== view.badge) summary.append(el(doc, "p", `attempt-reason tone-${view.tone}`, view.title));
  if (view.sub) summary.append(el(doc, "p", "attempt-reason-sub", view.sub));
  row.append(summary);
  card.append(row);

  const result = { node: card, running: null, recompose: null, image: null };
  if (running) {
    const detail = el(doc, "div", "attempt-detail");
    const progress = el(doc, "progress", "attempt-progress");
    progress.max = 100;
    progress.setAttribute("aria-label", "图片生成进度");
    const cancel = el(doc, "button", "btn-secondary attempt-cancel", "取消");
    cancel.dataset.attemptCancel = "";
    addIcon(cancel, "x", doc);
    cancel.addEventListener("click", (event) => { event.stopPropagation?.(); opts.onCancel?.(attempt); });
    const log = el(doc, "details", "job-log attempt-log");
    const pre = el(doc, "pre");
    log.append(el(doc, "summary", "", "日志"), pre);
    detail.append(progress, cancel, log);
    card.append(detail);
    result.running = { label, progress, log: pre, index };
    return result;
  }
  if (!expanded) return result;

  const detail = el(doc, "div", "attempt-detail");
  if (view.kind === "done") {
    const big = el(doc, "img", "attempt-image");
    big.alt = prompt || "生成的图片";
    big.addEventListener("error", () => opts.onBroken?.(attempt));
    big.addEventListener("load", () => opts.onImageLoad?.(attempt));
    big.src = serveOutput(attempt.output);
    detail.append(big);
    result.image = big;
  }
  detail.append(el(doc, "p", "attempt-full-prompt", prompt));
  if (view.kind === "failed" && attempt.error) {
    const block = renderErrorBlock(doc, attempt.error);
    const more = [...(block.children ?? [])].find((child) => String(child.tagName).toLowerCase() === "details");
    if (more) { more.classList?.add?.("attempt-error-details"); detail.append(more); }
  }
  detail.append(advancedList(doc, attempt.params));
  const actions = el(doc, "div", "attempt-actions");
  const refine = el(doc, "button", "btn-secondary", "在这张基础上改");
  refine.dataset.attemptRefine = "";
  addIcon(refine, "pencil", doc);
  refine.addEventListener("click", (event) => { event.stopPropagation?.(); opts.onRefine?.(attempt, index); });
  const recompose = el(doc, "button", "btn-secondary", "换个构图");
  recompose.dataset.attemptRecompose = "";
  addIcon(recompose, "refresh", doc);
  recompose.addEventListener("click", (event) => {
    event.stopPropagation?.();
    if (!recompose.disabled) opts.onRecompose?.(attempt, index);
  });
  actions.append(refine, recompose);
  const hint = el(doc, "p", "hint hint-busy attempt-action-hint");
  hint.setAttribute("role", "status");
  detail.append(actions, hint);
  card.append(detail);
  result.recompose = { button: recompose, hint };
  return result;
}
