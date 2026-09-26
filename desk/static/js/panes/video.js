// ui:videoPane —— 会话式视频页（设计 docs/superpowers/specs/2026-09-27-video-sessions-design.md §3）。
// 会话列表、时间线、忙碌原因、作业轮询与挑选合成由共用会话控制器 panes/media_session.js 负责；
// 这里只有视频卡片、输入区（方式、首帧/尾帧/参考视频素材、提示词、高级参数、提示条）与三个动作、重新拼接。
import * as api from "../api.js";
import { renderVideoCard } from "../widgets/video_session_card.js";
import { openImagePicker } from "../widgets/image_picker.js";
import { createPromptAssist } from "../widgets/prompt_assist.js";
import { createSessionPane } from "./media_session.js";
import { ParamsError, randomSeed, sessionTitle } from "../pure/media_session.js";
import { hasImage } from "../pure/image_session.js";
import { videoCostNote } from "../pure/video_cost.js";
import {
  DURATIONS, SIZES, canContinue, chipText, firstFrameLabel, nextFields, readVideoParams, refineFields, sourceOf, versionParams,
} from "../pure/video_session.js";

// 提示词框默认 3 行；内容多时长高到 40vh，失焦且不超 3 行时回落（V-21）。
const PROMPT_ROWS = 3;
const MAX_UPLOAD = 32 * 1024 * 1024;
// 回填时只知道之前上传的素材 id，不知道原文件名：不把 id 露给用户。
const EARLIER_IMAGE = "之前上传的图片";
const EARLIER_VIDEO = "之前上传的视频";
const SEGMENT_ERRORS = new Set(["segment_missing", "segment_not_found"]);
const PLACEHOLDERS = {
  text: "视频提示词（含环境声描述）",
  image: "描述图片中的动作、镜头变化和声音",
  reference: "描述参考视频的哪些内容，以及想生成的新画面和声音",
};

function acceptsType(accept, type) {
  return !accept || accept.split(",").map((item) => item.trim()).includes(type);
}

// 素材库条目或旧参数里的帧数不一定正好是某一档：取最接近的一档。
function closestFrames(frames) {
  const target = Number(frames);
  return DURATIONS.reduce((best, item) => (Math.abs(item[0] - target) < Math.abs(best[0] - target) ? item : best))[0];
}

export function createVideoPane(root, ctx = {}) {
  const q = (name) => root.querySelector(`[data-video-${name}]`);
  const els = {
    mode: q("mode"), prompt: q("prompt"), size: q("size"), frames: q("frames"), steps: q("steps"), seed: q("seed"),
    start: q("start"), advanced: q("advanced"), advancedError: q("advanced-error"), costNote: q("cost-note"),
    audio: q("audio"), audioRow: q("audio-row"), uploadStatus: q("upload-status"),
    chip: q("chip"), chipText: q("chip-text"), chipClear: q("chip-clear"), composer: q("composer"), assist: q("assist"),
    firstArea: q("first-area"), firstUpload: q("first-upload"), firstPick: q("first-pick"),
    firstLabel: q("first-label"), firstPreview: q("first-preview"),
    lastArea: q("last-area"), last: q("last"), lastLabel: q("last-label"), lastPreview: q("last-preview"), clearLast: q("clear-last"),
    referenceArea: q("reference-area"), source: q("source"), sourceLabel: q("source-label"), sourcePreview: q("source-preview"),
  };
  const doc = root.ownerDocument;
  const drawSeed = ctx.randomSeed ?? randomSeed;
  const pickImage = ctx.pickImage ?? (() => openImagePicker(doc, {
    listSessions: () => api.listMediaSessions("image"),
    getSession: (id) => api.getMediaSession("image", id),
    serveOutput: api.serveOutput,
  }));

  for (const [value, label] of SIZES) {
    const option = doc.createElement("option");
    option.value = value; option.textContent = label; els.size.append(option);
  }
  for (const [value, label] of DURATIONS) {
    const option = doc.createElement("option");
    option.value = String(value); option.textContent = label; els.frames.append(option);
  }
  els.size.value = SIZES[0][0];
  els.frames.value = String(DURATIONS[0][0]);

  // 提示条引用：{type:"refine"|"continue"|"library", index, attemptId, seed?, missing?}（V-30）。
  let ref = null;
  // 首帧来源（V-22）：null | {type:"upload", file?, id?, name} | {type:"ref", ref, title?, index?} | {type:"continue", attemptId, index}。
  let first = null;
  let firstGone = false; // 回填的图片会话引用已失效：首帧说明「引用的图片已不在」（V-40）
  let last = null; // {file?, id?, name}
  let refVideo = null; // {file?, id?, name}
  let uploading = false;
  let segmentError = null;
  const brokenIds = new Set();
  // 图片会话（按 id）：卡片首帧来源行与首帧说明要它的标题与序号；null 表示读不出来。
  const imageSessions = new Map();
  const imageLoading = new Set();
  let pane = null;

  const continuing = () => first?.type === "continue";
  const position = (id) => (pane?.currentSession()?.attempts ?? []).findIndex((a) => a.id === id);

  // ---------- 图片会话查找 ----------
  async function loadImageSession(id) {
    try { imageSessions.set(id, await api.getMediaSession("image", id)); }
    catch { imageSessions.set(id, null); }
    return imageSessions.get(id);
  }
  // 引用的那张图：仍是 done 且文件在才算数（V-40）；返回 {output, title, index} 或 null。
  async function lookupImage(imageRef) {
    const session = await loadImageSession(imageRef.session_id);
    const attempts = session?.attempts ?? [];
    const index = attempts.findIndex((a) => a.id === imageRef.attempt_id);
    return index >= 0 && hasImage(attempts[index]) ? { output: attempts[index].output, title: sessionTitle(session), index } : null;
  }
  // 卡片上的「首帧：图片会话「<标题>」第 N 次」：会话还没读过就先给通用说明，读完重画一次。
  function firstFrameText(attempt) {
    const imageRef = attempt?.refs?.first_frame;
    if (!imageRef?.session_id) return "";
    if (!imageSessions.has(imageRef.session_id)) {
      if (!imageLoading.has(imageRef.session_id)) {
        imageLoading.add(imageRef.session_id);
        loadImageSession(imageRef.session_id).then(() => { imageLoading.delete(imageRef.session_id); pane?.rerender(); });
      }
      return firstFrameLabel({ type: "ref" });
    }
    const session = imageSessions.get(imageRef.session_id);
    const index = (session?.attempts ?? []).findIndex((a) => a.id === imageRef.attempt_id);
    return firstFrameLabel({ type: "ref" }, { imageTitle: session ? sessionTitle(session) : "", imageIndex: index >= 0 ? index : undefined });
  }

  // ---------- 素材区（V-22） ----------
  const previewUrls = new Map();
  function setPreview(box, tag, src, { name = "", objectUrl = false } = {}) {
    if (!box) return;
    const previous = previewUrls.get(box);
    if (previous) { URL.revokeObjectURL?.(previous); previewUrls.delete(box); }
    box.replaceChildren();
    if (!src) return;
    if (objectUrl) previewUrls.set(box, src);
    const media = doc.createElement(tag);
    media.src = src;
    media.className = "video-preview-media";
    if (tag === "video") media.controls = true;
    else media.alt = name;
    box.append(media);
  }
  const fileUrl = (file) => (typeof URL.createObjectURL === "function" ? URL.createObjectURL(file) : "");

  function firstText() {
    if (first) {
      return firstFrameLabel(first, { fileName: first.name, imageTitle: first.title, imageIndex: first.index, continueIndex: first.index });
    }
    return firstGone ? "引用的图片已不在" : firstFrameLabel(null);
  }

  // 方式决定素材区显隐与提示词占位（V-21、V-22）；续写来源存在时方式锁为图生、首帧与尾帧按钮禁用。
  function renderInputs() {
    const locked = continuing();
    if (locked) els.mode.value = "image";
    els.mode.disabled = locked;
    const mode = els.mode.value || "text";
    els.firstArea.hidden = mode !== "image";
    els.lastArea.hidden = mode !== "image";
    els.referenceArea.hidden = mode !== "reference";
    if (els.audioRow) els.audioRow.hidden = mode === "text";
    els.prompt.placeholder = PLACEHOLDERS[mode] ?? PLACEHOLDERS.text;
    els.firstLabel.textContent = firstText();
    for (const control of [els.firstUpload, els.firstPick, els.last, els.clearLast]) if (control) control.disabled = locked || uploading;
    if (els.source) els.source.disabled = uploading;
    els.lastLabel.textContent = last ? `已选择：${last.name}` : "未选择";
    els.sourceLabel.textContent = refVideo ? `已选择：${refVideo.name}` : "未选择";
  }
  function updateCost() {
    if (els.costNote) els.costNote.textContent = videoCostNote(els.size.value, els.frames.value);
  }

  function setFirst(source) {
    first = source;
    firstGone = false;
    if (source?.type === "upload" && source.file) setPreview(els.firstPreview, "img", fileUrl(source.file), { name: source.name, objectUrl: true });
    else setPreview(els.firstPreview, "img", null);
    if (source?.type === "ref") checkRef(source);
    renderInputs();
  }
  // 图片会话引用：取到那张图就补标题、序号与预览；已不在就清空首帧来源并说明（V-40）。
  async function checkRef(source) {
    const found = await lookupImage(source.ref);
    if (first !== source) return; // 这期间首帧来源已换
    if (!found) { first = null; firstGone = true; renderInputs(); return; }
    source.title = found.title; source.index = found.index;
    setPreview(els.firstPreview, "img", api.serveOutput(found.output), { name: found.title });
    renderInputs();
  }
  function setLast(value) {
    last = value;
    setPreview(els.lastPreview, "img", value?.file ? fileUrl(value.file) : null, { name: value?.name, objectUrl: !!value?.file });
    renderInputs();
  }
  function setRefVideo(value) {
    refVideo = value;
    setPreview(els.sourcePreview, "video", value?.file ? fileUrl(value.file) : null, { objectUrl: !!value?.file });
    renderInputs();
  }

  // 三个上传入口：选中即预览（32 MB 与类型检查）；拖到所在行上的文件同样处理（issue #15）。
  const slots = [
    { input: els.firstUpload, tag: "img", take: (file) => setFirst({ type: "upload", file, name: file.name }) },
    { input: els.last, tag: "img", take: (file) => setLast({ file, name: file.name }) },
    { input: els.source, tag: "video", take: (file) => setRefVideo({ file, name: file.name }) },
  ];
  function takeFile(slot, file) {
    if (!file) return;
    if (!file.size || file.size > MAX_UPLOAD) { pane.setError("请选择非空且不超过 32 MB 的素材"); return; }
    pane.setError("");
    slot.take(file);
  }
  for (const slot of slots) {
    const { input } = slot;
    if (!input) continue;
    input.addEventListener("change", () => {
      const file = input.files?.[0];
      takeFile(slot, file);
      if (file) input.value = ""; // 再次选同一个文件也要触发 change
    });
    // issue #15: the input is visually hidden, so a dragged file has to be accepted by its row.
    // `accept` only filters the picker, never a drop, hence the explicit type check.
    const row = input.closest?.(".file-row");
    row?.addEventListener("dragover", (event) => { event.preventDefault(); row.classList.add("drag-over"); });
    row?.addEventListener("dragleave", () => row.classList.remove("drag-over"));
    row?.addEventListener("drop", (event) => {
      event.preventDefault();
      row.classList.remove("drag-over");
      const file = event.dataTransfer?.files?.[0];
      if (!file || input.disabled) return;
      if (!acceptsType(input.accept, file.type)) {
        pane.setError(slot.tag === "img" ? "这里只支持 PNG、JPEG、WebP 图片" : "这里只支持 MP4、MOV、WebM 视频");
        return;
      }
      takeFile(slot, file);
    });
  }

  // ---------- 提示条（V-30；规则同 M-26–M-28） ----------
  function chipVisible() {
    if (!ref) return false;
    if (ref.type === "continue" || continuing()) return true;
    return Number.isInteger(ref.seed) && String(els.seed.value ?? "").trim() === String(ref.seed);
  }
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
  // 点 ×：不再沿用或续写；续写的首帧来源一起清掉，方式下拉解锁。
  function clearChip() {
    if (ref?.type !== "continue") els.seed.value = "";
    ref = null;
    if (continuing()) first = null;
    renderInputs();
    syncChip();
    if (pane) refreshAvailability();
  }

  let lastState = null;
  function updateAvailability(state, { secondary }) {
    lastState = { state, secondary };
    syncChip();
    const missing = !!ref?.missing;
    els.start.disabled = state.disabled || missing || uploading;
    els.start.title = state.disabled ? state.reason : missing ? chipText(ref) : "";
    if (secondary) {
      secondary.button.disabled = state.disabled;
      secondary.button.title = state.disabled ? state.reason : "";
      secondary.hint.textContent = state.disabled ? state.reason : "";
    }
  }
  function refreshAvailability() {
    if (lastState) updateAvailability(pane.availability(), { secondary: lastState.secondary });
  }

  async function startJob(params) {
    try { return await api.startVideoJob(params); }
    catch (error) {
      if (SEGMENT_ERRORS.has(error?.code)) {
        segmentError = error;
        if (params.continues && ref?.type === "continue" && ref.attemptId === params.continues) ref = { ...ref, missing: true };
      }
      throw error;
    }
  }

  pane = createSessionPane(root, {
    kind: "video", noun: "视频", dataPrefix: "video", canCompose: true,
    emptyLines: ["还没有视频", "在下面写提示词，点「生成视频」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着往下生」。"],
    modelTexts: { missing: "尚未安装视频模型，请到「资源」页下载", runtime: "视频 MLX 运行环境不可用，请检查服务或应用安装" },
    renderCard: (d, o) => {
      if (o.broken) brokenIds.add(o.attempt.id);
      const ours = o.job && o.job.attempt_id === o.attempt.id && o.job.status === "running";
      return renderVideoCard(d, {
        ...o, elapsed: ours ? o.job.elapsed_s : undefined, serveOutput: api.serveOutput, firstFrameText,
        onRefine: refine, onVersion: version, onContinue: continueAfter,
        onRejoin: (parts) => pane.startCompose(parts), onCancel: () => pane.cancelJob(),
        onTogglePick: (a) => pane.togglePick(a.id),
      });
    },
    composer: {
      startLabel: "生成视频",
      // V-43：提示词、方式、画幅、时长、步数保留；种子清空；提示条隐藏；续写的首帧来源清空，上传与图片会话来源保留。
      afterStart: ({ fromInputs }) => {
        if (!fromInputs) return;
        els.seed.value = ""; ref = null;
        if (continuing()) first = null;
        renderInputs(); syncChip();
      },
      onSessionSwitch: clearChip,
      focus: () => els.prompt.focus?.(),
      updateAvailability,
    },
    startJob, confirm: ctx.confirm, onStarted: ctx.onStarted,
  });

  async function generate(params, options) {
    segmentError = null;
    await pane.startGeneration(params, options);
    if (segmentError) { pane.setError(segmentError.message); segmentError = null; }
  }

  // ---------- 生成 ----------
  // 本地选的文件第一次提交时才上传，拿到的 id 记在来源上：之后重复生成不再上传。
  async function ensureUploaded(source) {
    if (source.id) return source.id;
    els.uploadStatus.textContent = `正在上传 ${source.name}…`;
    source.id = (await api.uploadMediaInput(source.file)).id;
    return source.id;
  }

  async function startFromInputs() {
    if (els.start.disabled || uploading) return;
    els.advancedError.textContent = ""; pane.setError("");
    let params;
    try {
      params = readVideoParams({
        prompt: els.prompt.value, size: els.size.value, frames: els.frames.value, steps: els.steps.value, seed: els.seed.value,
      });
    } catch (error) {
      if (!(error instanceof ParamsError)) throw error;
      if (error.advanced) { els.advanced.open = true; els.advancedError.textContent = error.message; }
      else pane.setError(error.message);
      return;
    }
    const mode = els.mode.value || "text";
    const body = { session_id: pane.currentId(), ...params };
    const uploads = [];
    if (continuing()) {
      body.continues = first.attemptId; // 首帧由后端取前一段的最后一帧（B-56），不带 mode 与首帧
    } else if (mode === "image") {
      if (!first) { pane.setError("请先选择首帧图片"); return; }
      body.mode = "image";
      if (first.type === "ref") body.refs = { first_frame: first.ref };
      else uploads.push(["first_frame", first]);
      if (last) uploads.push(["last_frame", last]);
    } else if (mode === "reference") {
      if (!refVideo) { pane.setError("请先选择参考视频"); return; }
      body.mode = "reference";
      uploads.push(["ref_video", refVideo]);
    }
    if (mode !== "text") body.use_audio = !!els.audio?.checked;
    if (uploads.length) {
      uploading = true; renderInputs(); refreshAvailability();
      try {
        for (const [key, source] of uploads) body[key] = await ensureUploaded(source);
        els.uploadStatus.textContent = "正在提交生成任务…";
      } catch (error) {
        els.uploadStatus.textContent = "";
        pane.setError(error.message);
        return;
      } finally { uploading = false; renderInputs(); refreshAvailability(); }
    }
    try { await generate(body, { fromInputs: true }); }
    finally { els.uploadStatus.textContent = ""; }
  }

  // ---------- 三个动作（V-40–V-42）：回填不改变「高级参数」的折叠状态 ----------
  function focusPromptEnd() {
    els.composer?.scrollIntoView?.({ block: "nearest" });
    els.prompt.focus?.();
    const end = els.prompt.value.length;
    els.prompt.setSelectionRange?.(end, end);
    fitPrompt();
  }

  // fields 同 refineFields 的形状；nextFirst 是首帧来源；nextRef 是提示条引用。
  function prefill(fields, nextFirst, nextRef) {
    els.mode.value = fields.mode ?? "text";
    els.prompt.value = fields.prompt ?? "";
    if (fields.size) els.size.value = fields.size;
    if (fields.frames != null) els.frames.value = String(closestFrames(fields.frames));
    if (fields.steps != null) els.steps.value = String(fields.steps);
    els.seed.value = fields.seed == null ? "" : String(fields.seed);
    if (els.audio) els.audio.checked = fields.useAudio !== false;
    setLast(fields.last ? { id: fields.last, name: EARLIER_IMAGE } : null);
    setRefVideo(fields.refVideo ? { id: fields.refVideo, name: EARLIER_VIDEO } : null);
    setFirst(nextFirst);
    ref = fields.seed == null && nextFirst?.type !== "continue" ? null : nextRef;
    updateCost();
    syncChip();
    refreshAvailability();
    focusPromptEnd();
  }

  function firstFromSource(source) {
    if (source?.type === "continue") return { type: "continue", attemptId: source.attemptId, index: position(source.attemptId) };
    if (source?.type === "ref") return { type: "ref", ref: source.ref };
    if (source?.type === "upload") return { type: "upload", id: source.id, name: EARLIER_IMAGE };
    return null;
  }

  function refine(attempt, index) {
    const fields = refineFields(attempt);
    pane.keepInView(attempt.id);
    prefill(fields, firstFromSource(sourceOf(attempt)), { type: "refine", index, attemptId: attempt.id, seed: fields.seed });
    pane.settleView();
  }

  function version(attempt) {
    const sessionId = pane.currentId();
    if (pane.availability().disabled || !sessionId) return;
    generate(versionParams(attempt, sessionId, drawSeed), { fromInputs: false });
  }

  function continueAfter(attempt, index) {
    if (!canContinue(attempt) || brokenIds.has(attempt.id)) return;
    const fields = nextFields(attempt, { size: els.size.value, frames: Number(els.frames.value), steps: Number(els.steps.value) });
    els.size.value = fields.size;
    if (Number.isFinite(fields.frames)) els.frames.value = String(closestFrames(fields.frames));
    if (Number.isFinite(fields.steps)) els.steps.value = String(fields.steps);
    els.prompt.value = "";
    els.seed.value = "";
    setLast(null);
    ref = { type: "continue", index, attemptId: attempt.id };
    setFirst({ type: "continue", attemptId: attempt.id, index });
    updateCost();
    syncChip();
    refreshAvailability();
    pane.keepInView(attempt.id);
    focusPromptEnd();
    pane.settleView();
  }

  // 素材库回填里找不到原会话时按字段回填（V-61，同 M-52）。
  function prefillFromLibrary(fields) {
    const size = fields.width && fields.height ? `${fields.width}x${fields.height}` : null;
    const imageRef = fields.refs?.first_frame;
    const nextFirst = imageRef ? { type: "ref", ref: imageRef }
      : fields.first_frame ? { type: "upload", id: fields.first_frame, name: EARLIER_IMAGE } : null;
    const seed = Number.isInteger(fields.seed) ? fields.seed : null;
    prefill({
      mode: fields.mode ?? "text", prompt: fields.prompt ?? "", size, frames: fields.frames, steps: fields.steps, seed,
      last: fields.last_frame ?? null, refVideo: fields.ref_video ?? null, useAudio: fields.use_audio !== false,
    }, nextFirst, { type: "library", index: null, seed });
  }

  // 图片页「用这张生成视频」、本页「从图片会话选…」（V-50、V-23）：首帧来源设为图片会话引用。
  function useImageRef(pick) {
    if (!pick?.ref) return;
    if (ref?.type === "continue") ref = null;
    if (continuing()) first = null;
    els.mode.value = "image";
    pane.setError("");
    setFirst({ type: "ref", ref: pick.ref, title: pick.title, index: pick.index });
    syncChip();
    refreshAvailability();
  }

  async function useFirstFrame(pick) {
    await pane.refresh(); // 视频页第一次打开时先把会话加载完，回填不被之后的会话切换清掉
    useImageRef(pick);
    focusPromptEnd();
  }

  // ---------- 提示词框自适应高度（V-21；field-sizing 不支持时的退路） ----------
  function fitPrompt() {
    const box = els.prompt;
    if (!box.style) return;
    const view = doc?.defaultView;
    box.style.height = "auto";
    box.style.height = `${Math.min(box.scrollHeight, (view?.innerHeight ?? 800) * 0.4)}px`;
  }
  function relaxPrompt() {
    if (!els.prompt.style) return;
    if (els.prompt.value.split("\n").length <= PROMPT_ROWS) els.prompt.style.height = "";
  }

  // ---------- AI 帮写 ----------
  const assist = els.assist ? createPromptAssist(doc, els.assist, {
    task: "video",
    read: () => ({ text: els.prompt.value }),
    write: ({ text }) => { els.prompt.value = text; fitPrompt(); },
    mode: () => els.mode.value || "text",
    confirm: ctx.confirm ? (options) => ctx.confirm(doc, options) : undefined,
  }) : null;

  // ---------- 事件 ----------
  els.start.addEventListener("click", startFromInputs);
  els.prompt.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault?.(); startFromInputs(); }
  });
  els.prompt.addEventListener("input", fitPrompt);
  els.prompt.addEventListener("focus", fitPrompt);
  els.prompt.addEventListener("blur", relaxPrompt);
  els.mode.addEventListener("change", () => { pane.setError(""); renderInputs(); });
  els.size.addEventListener("change", updateCost);
  els.frames.addEventListener("change", updateCost);
  els.seed.addEventListener("input", () => { syncChip(); refreshAvailability(); });
  els.chipClear.addEventListener("click", clearChip);
  els.clearLast?.addEventListener("click", () => { if (!els.clearLast.disabled) setLast(null); });
  els.firstPick?.addEventListener("click", async () => {
    if (els.firstPick.disabled) return;
    const pick = await pickImage();
    if (pick) useImageRef(pick);
  });

  renderInputs();
  updateCost();
  syncChip();
  return {
    // 每次打开视频页重读图片会话：卡片首帧来源行里的标题可能在图片页改过。
    refresh: () => { imageSessions.clear(); return pane.refresh(); },
    applyJob: pane.applyJob, poll: pane.poll,
    applyFill: (plan) => pane.applyFill(plan, { refine, prefillOnly: prefillFromLibrary }),
    setHeavyAllowed: pane.setHeavyAllowed, setModelStatus: pane.setModelStatus, setRuntimeStatus: pane.setRuntimeStatus,
    setAssistAvailable: (allowed, reason) => assist?.setAvailable(allowed, reason),
    useFirstFrame,
  };
}
