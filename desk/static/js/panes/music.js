// ui:musicPane —— 会话式音乐页（设计 docs/superpowers/specs/2026-09-27-music-sessions-design.md §2）。
// 会话列表、时间线、忙碌原因、作业轮询与挑选合成由共用会话控制器 panes/media_session.js 负责；
// 这里只有音乐卡片、输入区（风格描述、歌词、高级参数、提示条）与三个动作、重新拼接。
import * as api from "../api.js";
import { renderMusicCard } from "../widgets/music_session_card.js";
import { createPromptAssist } from "../widgets/prompt_assist.js";
import { createSessionPane } from "./media_session.js";
import { ParamsError, randomSeed } from "../pure/media_session.js";
import {
  canContinue, chipText, nextFields, readMusicParams, refineFields, submitContinues, versionParams,
} from "../pure/music_session.js";

// 歌词框默认 4 行；内容多时长高到 50vh，失焦且不超 4 行时回落（M-21）。
const LYRICS_ROWS = 4;
const SEGMENT_ERRORS = new Set(["segment_missing", "segment_not_found"]);

export function createMusicPane(root, ctx = {}) {
  const q = (name) => root.querySelector(`[data-music-${name}]`);
  const els = {
    caption: q("caption"), lyrics: q("lyrics"), duration: q("duration"), seed: q("seed"),
    start: q("start"), advanced: q("advanced"), advancedError: q("advanced-error"),
    chip: q("chip"), chipText: q("chip-text"), chipClear: q("chip-clear"), composer: q("composer"), assist: q("assist"),
  };
  const doc = root.ownerDocument;
  const drawSeed = ctx.randomSeed ?? randomSeed;
  // 提示条引用：{type:"refine"|"continue", index, attemptId, seed?, continues?, missing?}（M-26）。
  let ref = null;
  let segmentError = null;
  const brokenIds = new Set();
  let pane = null;

  // ---------- 提示条（M-26–M-28） ----------
  function chipVisible() {
    if (!ref) return false;
    if (ref.type === "continue") return true;
    return Number.isInteger(ref.seed) && String(els.seed.value ?? "").trim() === String(ref.seed);
  }
  // 续写目标在会话刷新后已不是「完成且文件在」：提示条改为不能接着写（M-28）。
  function checkMissing() {
    if (ref?.type !== "continue" || ref.missing) return;
    const session = pane?.currentSession();
    if (!session) return;
    const target = (session.attempts ?? []).find((a) => a.id === ref.attemptId);
    if (!target || !canContinue(target) || brokenIds.has(target.id)) ref = { ...ref, missing: true };
  }
  function syncChip() {
    checkMissing();
    const visible = chipVisible();
    els.chip.hidden = !visible;
    els.chipText.textContent = visible ? chipText(ref) : "";
  }
  function clearChip() {
    if (ref?.type !== "continue") els.seed.value = "";
    ref = null;
    syncChip();
    if (pane) refreshAvailability();
  }

  // 「生成歌曲」与展开卡片上「换个版本」的可用状态；续写目标已不在时「生成歌曲」也不可用（M-28、M-34）。
  let lastState = null;
  function updateAvailability(state, { recompose }) {
    lastState = { state, recompose };
    syncChip();
    const missing = !!ref?.missing;
    els.start.disabled = state.disabled || missing;
    els.start.title = state.disabled ? state.reason : missing ? chipText(ref) : "";
    if (recompose) {
      recompose.button.disabled = state.disabled;
      recompose.button.title = state.disabled ? state.reason : "";
      recompose.hint.textContent = state.disabled ? state.reason : "";
    }
  }
  function refreshAvailability() {
    if (lastState) updateAvailability(pane.availability(), { recompose: lastState.recompose });
  }

  async function startJob(params) {
    try { return await api.startMusicJob(params); }
    catch (error) {
      if (SEGMENT_ERRORS.has(error?.code)) {
        segmentError = error;
        if (params.continues && ref?.type === "continue" && ref.attemptId === params.continues) ref = { ...ref, missing: true };
      }
      throw error;
    }
  }

  pane = createSessionPane(root, {
    kind: "music", noun: "歌曲", dataPrefix: "music", canCompose: true,
    emptyLines: ["还没有歌曲", "在下面写风格描述和歌词，点「生成歌曲」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着写下一段」。"],
    modelTexts: { missing: "尚未安装音乐模型，请到「资源」页下载", runtime: "音乐 MLX 运行环境不可用，请检查服务或应用安装" },
    renderCard: (d, o) => {
      if (o.broken) brokenIds.add(o.attempt.id);
      const ours = o.job && o.job.attempt_id === o.attempt.id && o.job.status === "running";
      return renderMusicCard(d, {
        ...o, elapsed: ours ? o.job.elapsed_s : undefined, serveOutput: api.serveOutput,
        onRefine: refine, onVersion: version, onContinue: continueAfter,
        onRejoin: (parts) => pane.startCompose(parts), onCancel: () => pane.cancelJob(),
        onTogglePick: (a) => pane.togglePick(a.id),
      });
    },
    composer: {
      startLabel: "生成歌曲",
      afterStart: ({ fromInputs }) => { if (fromInputs) { els.seed.value = ""; ref = null; syncChip(); } },
      onSessionSwitch: clearChip,
      focus: () => els.lyrics.focus?.(),
      updateAvailability,
    },
    startJob, confirm: ctx.confirm, onStarted: ctx.onStarted,
  });

  // 后端说续写的那一段已不在：错误行用后端原话（M-28），不笼统写成「生成失败」。
  async function generate(params, options) {
    segmentError = null;
    await pane.startGeneration(params, options);
    if (segmentError) { pane.setError(segmentError.message); segmentError = null; }
  }

  // ---------- 生成 ----------
  async function startFromInputs() {
    if (els.start.disabled) return;
    els.advancedError.textContent = ""; pane.setError("");
    let params;
    try {
      params = readMusicParams({
        caption: els.caption.value, lyrics: els.lyrics.value, duration: els.duration.value, seed: els.seed.value,
      });
    } catch (error) {
      if (!(error instanceof ParamsError)) throw error;
      if (error.advanced) { els.advanced.open = true; els.advancedError.textContent = error.message; }
      else pane.setError(error.message);
      return;
    }
    const continues = submitContinues(ref, els.seed.value);
    await generate({ session_id: pane.currentId(), ...params, ...(continues ? { continues } : {}) }, { fromInputs: true });
  }

  // ---------- 三个动作（M-33–M-36）：回填不改变「高级参数」的折叠状态 ----------
  function focusLyricsEnd() {
    els.composer?.scrollIntoView?.({ block: "nearest" });
    els.lyrics.focus?.();
    const end = els.lyrics.value.length;
    els.lyrics.setSelectionRange?.(end, end);
    fitLyrics();
  }

  function prefill(fields, nextRef) {
    els.caption.value = fields.caption ?? "";
    els.lyrics.value = fields.lyrics ?? "";
    if (fields.duration != null) els.duration.value = String(fields.duration);
    els.seed.value = fields.seed == null ? "" : String(fields.seed);
    ref = fields.seed == null ? null : nextRef;
    syncChip();
    refreshAvailability();
    focusLyricsEnd();
  }

  function refine(attempt, index) {
    const fields = refineFields(attempt);
    pane.keepInView(attempt.id);
    prefill(fields, { type: "refine", index, attemptId: attempt.id, seed: fields.seed, continues: attempt.continues ?? null });
    pane.settleView();
  }

  function version(attempt) {
    const sessionId = pane.currentId();
    if (pane.availability().disabled || !sessionId) return;
    generate(versionParams(attempt, sessionId, drawSeed), { fromInputs: false });
  }

  function continueAfter(attempt, index) {
    if (!canContinue(attempt) || brokenIds.has(attempt.id)) return;
    const fields = nextFields(attempt, { caption: els.caption.value, duration: Number(els.duration.value) });
    els.caption.value = fields.caption ?? "";
    if (Number.isFinite(fields.duration)) els.duration.value = String(fields.duration);
    els.lyrics.value = "";
    els.seed.value = "";
    ref = { type: "continue", index, attemptId: attempt.id };
    syncChip();
    refreshAvailability();
    pane.keepInView(attempt.id);
    focusLyricsEnd();
    pane.settleView();
  }

  // ---------- 歌词框自适应高度（M-21；field-sizing 不支持时的退路） ----------
  function fitLyrics() {
    const box = els.lyrics;
    if (!box.style) return;
    const view = doc?.defaultView;
    box.style.height = "auto";
    box.style.height = `${Math.min(box.scrollHeight, (view?.innerHeight ?? 800) * 0.5)}px`;
  }
  function relaxLyrics() {
    if (!els.lyrics.style) return;
    if (els.lyrics.value.split("\n").length <= LYRICS_ROWS) els.lyrics.style.height = "";
  }

  // ---------- AI 帮写 ----------
  const assist = els.assist ? createPromptAssist(doc, els.assist, {
    task: "music",
    read: () => ({ text: els.caption.value, lyrics: els.lyrics.value }),
    write: ({ text, lyrics }) => { els.caption.value = text; if (lyrics !== undefined) els.lyrics.value = lyrics; fitLyrics(); },
    confirm: ctx.confirm ? (options) => ctx.confirm(doc, options) : undefined,
  }) : null;

  // ---------- 事件 ----------
  els.start.addEventListener("click", startFromInputs);
  for (const field of [els.caption, els.lyrics]) {
    field.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault?.(); startFromInputs(); }
    });
  }
  els.lyrics.addEventListener("input", fitLyrics);
  els.lyrics.addEventListener("focus", fitLyrics);
  els.lyrics.addEventListener("blur", relaxLyrics);
  els.seed.addEventListener("input", () => { syncChip(); refreshAvailability(); });
  els.chipClear.addEventListener("click", clearChip);

  syncChip();
  return {
    refresh: pane.refresh, applyJob: pane.applyJob, poll: pane.poll,
    applyFill: (plan) => pane.applyFill(plan, {
      refine,
      prefillOnly: (fields) => prefill({ ...fields, lyrics: fields.lyrics ?? "" }, { type: "refine", index: null, seed: fields.seed ?? null }),
    }),
    setHeavyAllowed: pane.setHeavyAllowed, setModelStatus: pane.setModelStatus, setRuntimeStatus: pane.setRuntimeStatus,
    setAssistAvailable: (allowed, reason) => assist?.setAvailable(allowed, reason),
  };
}
