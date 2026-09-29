// ui:imagePane —— 会话式图片页（设计 docs/superpowers/specs/2026-09-24-image-sessions-design.md §5–§8）。
// 会话列表、时间线、忙碌原因与作业轮询由共用会话控制器 panes/media_session.js 负责；
// 这里只有图片卡片、输入区（提示词、高级参数、「在这张基础上改」的提示条）与「换个构图」。
import * as api from "../api.js";
import { renderAttemptCard } from "../widgets/image_session_card.js";
import { createSessionPane } from "./media_session.js";
import {
  readImageParams, recomposeParams,
  refineChipText, refineChipVisible, refineFields,
  hasImage, submitBase, baseLabel, NO_IMAGE_REASON,
} from "../pure/image_session.js";
import { randomSeed, sessionTitle } from "../pure/media_session.js";

// 展开卡片的大图不会为了整张放进时间线而缩到这个高度（缩略图的两倍）以下（IS D-74、B-01）。
const IMAGE_FLOOR = 192;

export function createImagePane(root, ctx = {}) {
  const q = (name) => root.querySelector(`[data-image-${name}]`);
  const els = {
    prompt: q("prompt"), width: q("width"), height: q("height"), steps: q("steps"), seed: q("seed"),
    start: q("start"), advanced: q("advanced"), advancedError: q("advanced-error"),
    refine: q("refine"), refineText: q("refine-text"), refineClear: q("refine-clear"), composer: q("composer"),
  };
  const drawSeed = ctx.randomSeed ?? randomSeed;
  let refineRef = null;

  // ---------- 提示条（D-41/D-42） ----------
  function syncChip() {
    const visible = refineChipVisible(els.seed.value, refineRef);
    els.refine.hidden = !visible;
    els.refineText.textContent = visible ? refineChipText(refineRef) : "";
  }
  function clearSeedAndChip() { els.seed.value = ""; refineRef = null; syncChip(); }

  // 生成按钮与展开卡片上「换个构图」的可用状态（§7.6）。
  function updateAvailability(state, { secondary }) {
    els.start.disabled = state.disabled;
    els.start.title = state.reason;
    if (secondary) {
      const reason = secondary.secondaryBlockedReason || (state.disabled ? state.reason : "");
      secondary.button.disabled = state.disabled || !!secondary.secondaryBlockedReason;
      secondary.button.title = reason;
      secondary.hint.textContent = reason;
    }
  }

  const pane = createSessionPane(root, {
    kind: "image", noun: "图片", dataPrefix: "image",
    emptyLines: ["还没有图片", "在下面写下想要的画面，点「生成图片」。之后可以在任意一张上「在这张基础上改」或「换个构图」。"],
    modelTexts: { missing: "尚未安装图片模型，请到「资源」页下载", runtime: "图片 MLX 运行环境不可用，请检查服务或应用安装" },
    renderCard: (doc, o) => {
      const ours = o.job && o.job.attempt_id === o.attempt.id && o.job.status === "running";
      return renderAttemptCard(doc, {
        attempt: o.attempt, index: o.index, selected: o.selected, broken: o.broken,
        elapsed: ours ? o.job.elapsed_s : undefined, serveOutput: api.serveOutput,
        baseText: baseLabel(o.attempt, o.attempts), secondaryBlockedReason: hasImage(o.attempt) ? "" : NO_IMAGE_REASON,
        onBroken: o.onBroken, onImageLoad: o.onImageLoad, onRefine: refine, onRecompose: recompose, onCancel: () => pane.cancelJob(),
        onUseAsFirstFrame: useAsFirstFrame,
      });
    },
    fitExpanded: (image, room) => { image.style.maxHeight = `min(60vh, ${Math.max(IMAGE_FLOOR, Math.floor(room))}px)`; },
    composer: {
      startLabel: "生成图片",
      afterStart: ({ fromInputs }) => { if (fromInputs) clearSeedAndChip(); },
      onSessionSwitch: clearSeedAndChip,
      onNewSession: () => { els.prompt.value = ""; clearSeedAndChip(); },
      focus: () => els.prompt.focus?.(),
      updateAvailability,
    },
    startJob: api.startImageJob, confirm: ctx.confirm, onStarted: ctx.onStarted,
  });

  // ---------- 生成 ----------
  function readInputs() {
    return { prompt: els.prompt.value, width: els.width.value, height: els.height.value, steps: els.steps.value, seed: els.seed.value };
  }

  async function startFromInputs() {
    if (els.start.disabled) return;
    els.advancedError.textContent = ""; pane.setError("");
    let params;
    try { params = readImageParams(readInputs()); }
    catch (error) {
      if (error.advanced) { els.advanced.open = true; els.advancedError.textContent = error.message; }
      else pane.setError(error.message);
      return;
    }
    const base = submitBase(els.seed.value, refineRef);
    await pane.startGeneration({ session_id: pane.currentId(), ...params, ...(base ? { base } : {}) }, { fromInputs: true });
  }

  // D-40–D-43：回填、沿用种子、不提交；高级参数保持原折叠状态。
  function prefill(fields, ref) {
    els.prompt.value = fields.prompt ?? "";
    for (const name of ["width", "height", "steps"]) if (fields[name] != null) els[name].value = String(fields[name]);
    els.seed.value = fields.seed == null ? "" : String(fields.seed);
    refineRef = fields.seed == null ? null : ref;
    syncChip();
    els.composer?.scrollIntoView?.({ block: "nearest" });
    els.prompt.focus?.();
    const end = els.prompt.value.length;
    els.prompt.setSelectionRange?.(end, end);
  }

  function refine(attempt, index) {
    const fields = refineFields(attempt);
    pane.keepInView(attempt.id);
    prefill(fields, { seed: fields.seed, index, attemptId: attempt.id, image: hasImage(attempt) });
    pane.settleView(); // 提示条出现、输入区变高后，被点的这张仍整张可见（ResizeObserver 之外的同步一次）
  }

  function recompose(attempt) {
    const sessionId = pane.currentId();
    if (pane.availability().disabled || !sessionId) return;
    pane.startGeneration(recomposeParams(attempt, sessionId, drawSeed), { fromInputs: false });
  }

  // V-50：跨页到视频页当首帧——只交出引用与展示用的标题/序号，切页与回填是 main.js 与视频页的事。
  function useAsFirstFrame(attempt, index) {
    const sessionId = pane.currentId();
    if (!sessionId) return;
    ctx.onUseAsFirstFrame?.({
      ref: { kind: "image", session_id: sessionId, attempt_id: attempt.id },
      title: sessionTitle(pane.currentSession()),
      index,
    });
  }

  // ---------- 事件 ----------
  els.start.addEventListener("click", startFromInputs);
  els.prompt.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault?.(); startFromInputs(); }
  });
  els.seed.addEventListener("input", syncChip);
  els.refineClear.addEventListener("click", clearSeedAndChip);

  syncChip();
  return {
    refresh: pane.refresh, applyJob: pane.applyJob, poll: pane.poll,
    applyFill: (plan) => pane.applyFill(plan, {
      refine, prefillOnly: (fields) => prefill(fields, { seed: fields.seed ?? null, index: null }),
    }),
    setHeavyAllowed: pane.setHeavyAllowed, setModelStatus: pane.setModelStatus, setRuntimeStatus: pane.setRuntimeStatus,
  };
}
