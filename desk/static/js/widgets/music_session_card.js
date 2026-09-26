// 音乐会话时间线里的一张尝试卡片（设计 docs/superpowers/specs/2026-09-27-music-sessions-design.md §2.3–§2.5）。
// 只画 DOM，不发请求：三个动作、重新拼接、取消、挑选勾选、音频加载失败都经回调交还给 panes/music.js。
import { addIcon } from "../icons.js";
import { renderErrorBlock } from "./error_block.js";
import { attemptView } from "../pure/image_session.js";
import { runningLabel } from "../pure/media_session.js";
import { CANNOT_CONTINUE, canContinue, cardTitle, chainLine, joinProblem, lyricsPreview } from "../pure/music_session.js";

function el(doc, tag, className, text) {
  const node = doc.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

// 图片的 attemptView 之外，文件不在时的文案不说「图片」（M-32 / IS D-85）。
function musicView(attempt, broken) {
  const view = attemptView(attempt, { broken });
  if (view.kind !== "missing") return view;
  return { ...view, badge: "文件已不在", title: "文件已不在", sub: "可能已在访达中移动或删除", icon: "music" };
}

const isCompose = (attempt) => attempt?.op === "compose" || Array.isArray(attempt?.params?.parts);

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
  for (const [label, value] of [["时长（秒）", params?.duration], ["种子", params?.seed]]) {
    list.append(el(doc, "dt", "", label), el(doc, "dd", "", value == null ? "—" : String(value)));
  }
  details.append(list);
  return details;
}

function actionButton(doc, text, icon, onClick) {
  const btn = el(doc, "button", "btn-secondary", text);
  addIcon(btn, icon, doc);
  btn.addEventListener("click", (event) => {
    event.stopPropagation?.();
    if (!btn.disabled) onClick();
  });
  return btn;
}

// 播放器：有可用成片时默认放成片，旁边「成片 | 只听这一段」切换（M-31）。
function player(doc, attempt, { serveOutput, onBroken }) {
  const box = el(doc, "div", "attempt-player");
  const audio = el(doc, "audio", "attempt-audio");
  audio.setAttribute("controls", "");
  audio.setAttribute("preload", "metadata");
  audio.addEventListener("error", () => onBroken?.(attempt));
  const joined = typeof attempt.joined_output === "string" && attempt.joined_output && !attempt.joined_missing;
  audio.src = serveOutput(joined ? attempt.joined_output : attempt.output);
  box.append(audio);
  if (!joined) return box;
  const group = el(doc, "div", "segment-switch");
  group.setAttribute("role", "radiogroup");
  group.setAttribute("aria-label", "播放哪一版");
  const choices = [["成片", attempt.joined_output], ["只听这一段", attempt.output]].map(([label, file], i) => {
    const btn = el(doc, "button", "btn-secondary btn-sm", label);
    btn.setAttribute("role", "radio");
    btn.setAttribute("aria-checked", i === 0 ? "true" : "false");
    btn.addEventListener("click", (event) => {
      event.stopPropagation?.();
      for (const other of choices) other.setAttribute("aria-checked", other === btn ? "true" : "false");
      audio.src = serveOutput(file);
    });
    return btn;
  });
  group.append(...choices);
  box.append(group);
  return box;
}

// 返回 {node, running, recompose}：running 是 running 卡片里轮询要就地更新的几个元素；
// recompose 是「换个版本」按钮与其下方原因行（由面板按生成可用性更新，与图片页「换个构图」同一机制）。
export function renderMusicCard(doc, opts) {
  const { attempt, index, attempts, selected, broken = false, serveOutput, picking = false, pickIndex = -1 } = opts;
  const view = musicView(attempt, broken);
  const running = view.kind === "running";
  const expanded = running || selected;
  const compose = isCompose(attempt);
  const params = attempt?.params ?? {};
  const caption = typeof params.caption === "string" ? params.caption : "";
  const lyrics = typeof params.lyrics === "string" ? params.lyrics : "";

  const card = el(doc, "li", `card attempt music-attempt attempt-${view.kind}`);
  card.dataset.attemptId = attempt.id;
  card.dataset.attemptStatus = view.kind;
  card.tabIndex = 0;
  card.setAttribute("aria-expanded", expanded ? "true" : "false");
  if (selected) card.classList.add("selected");

  const row = el(doc, "div", "attempt-row");
  // 挑选模式：能接着写（完成且文件在）的卡片前面有勾选框与序号（M-06）。卡片本身的点击由控制器切换勾选，
  // 这里只接勾选框的 change，不再接卡片点击（否则一次点击切两次）。
  if (picking && canContinue(attempt) && !broken) {
    const pick = el(doc, "input", "attempt-pick");
    pick.type = "checkbox";
    pick.checked = pickIndex >= 0;
    pick.setAttribute("aria-label", `选中第 ${index + 1} 次`);
    pick.addEventListener("change", () => opts.onTogglePick?.(attempt));
    row.append(pick);
    if (pickIndex >= 0) row.append(el(doc, "span", "pick-badge", String.fromCharCode(0x2460 + pickIndex)));
  }
  if (view.icon) row.append(iconBlock(doc, view));
  const summary = el(doc, "div", "attempt-summary");
  const head = el(doc, "div", "attempt-head");
  const label = el(doc, "span", "attempt-label", running ? runningLabel(index, opts.elapsed) : cardTitle(attempt, index, attempts));
  head.append(label);
  if (view.badge && !running) head.append(el(doc, "span", `badge attempt-badge tone-${view.tone}`, view.badge));
  summary.append(head);
  if (caption) {
    const captionLine = el(doc, "p", "attempt-prompt", caption);
    captionLine.title = caption;
    summary.append(captionLine);
  }
  const preview = lyricsPreview(lyrics);
  if (preview) summary.append(el(doc, "p", "attempt-spec attempt-lyrics-preview", preview));
  if (view.title && view.title !== view.badge) summary.append(el(doc, "p", `attempt-reason tone-${view.tone}`, view.title));
  if (view.sub) summary.append(el(doc, "p", "attempt-reason-sub", view.sub));
  row.append(summary);
  card.append(row);

  const result = { node: card, running: null, recompose: null, image: null };
  if (running) {
    const detail = el(doc, "div", "attempt-detail");
    const progress = el(doc, "progress", "attempt-progress");
    progress.max = 100;
    progress.setAttribute("aria-label", "歌曲生成进度");
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
  if (view.kind === "done") detail.append(player(doc, attempt, { serveOutput, onBroken: opts.onBroken }));
  const chain = chainLine(attempt, attempts);
  if (chain) detail.append(el(doc, "p", "hint attempt-chain", chain));
  const problem = joinProblem(attempt, attempts);
  if (problem) {
    const line = el(doc, "div", "attempt-join-problem");
    line.append(el(doc, "p", "inline-error", problem.text));
    // 挑选模式：卡片只做勾选，重新拼接按钮（连同它下面的原因行）不画；出错的说明文字仍留着。
    if (!picking && (problem.rejoin || problem.reason)) {
      const rejoin = actionButton(doc, "重新拼接", "refresh", () => opts.onRejoin?.(problem.rejoin.parts));
      rejoin.dataset.attemptRejoin = "";
      rejoin.disabled = !problem.rejoin;
      if (problem.reason) rejoin.title = problem.reason;
      line.append(rejoin);
      if (problem.reason) line.append(el(doc, "p", "hint", problem.reason));
    }
    detail.append(line);
  }
  if (caption) detail.append(el(doc, "p", "attempt-full-prompt", caption));
  if (lyrics) {
    const words = el(doc, "details", "attempt-lyrics");
    words.append(el(doc, "summary", "", "歌词"), el(doc, "pre", "", lyrics));
    detail.append(words);
  }
  if (view.kind === "failed" && attempt.error) {
    const block = renderErrorBlock(doc, attempt.error);
    const more = [...(block.children ?? [])].find((child) => String(child.tagName).toLowerCase() === "details");
    if (more) { more.classList?.add?.("attempt-error-details"); detail.append(more); }
  }
  if (!compose) detail.append(advancedList(doc, params));

  // 挑选模式：卡片只做勾选，三个动作按钮都不画（控制器裁定：卡片是勾选目标，不是隐藏表单的入口）。
  if (!picking) {
    const actions = el(doc, "div", "attempt-actions");
    let version = null;
    if (!compose) {
      const refine = actionButton(doc, "在这段基础上改", "pencil", () => opts.onRefine?.(attempt, index));
      refine.dataset.attemptRefine = "";
      version = actionButton(doc, "换个版本", "refresh", () => opts.onVersion?.(attempt, index));
      version.dataset.attemptVersion = "";
      actions.append(refine, version);
    }
    const next = actionButton(doc, "接着写下一段", "plus", () => opts.onContinue?.(attempt, index));
    next.dataset.attemptContinue = "";
    const continuable = canContinue(attempt) && !broken;
    next.disabled = !continuable;
    if (!continuable) next.title = CANNOT_CONTINUE;
    actions.append(next);
    detail.append(actions);
    if (!continuable) detail.append(el(doc, "p", "hint attempt-continue-reason", CANNOT_CONTINUE));
    const hint = el(doc, "p", "hint hint-busy attempt-action-hint");
    hint.setAttribute("role", "status");
    detail.append(hint);
    if (version) result.recompose = { button: version, hint, noImageReason: "" };
  }
  card.append(detail);
  return result;
}
