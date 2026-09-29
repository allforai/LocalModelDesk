// ui:videoPane —— 会话式视频页（设计 docs/superpowers/specs/2026-09-27-video-sessions-design.md §3）。
// 会话列表、时间线、忙碌原因、作业轮询与挑选合成由共用会话控制器 panes/media_session.js 负责；
// 这里只有视频卡片、输入区（方式、首帧/尾帧/参考视频/配乐参考素材、提示词、高级参数、提示条）与三个动作、
// 「配乐…」（docs/superpowers/specs/2026-09-27-video-soundtrack-design.md §4）、重新拼接。
import * as api from "../api.js";
import { renderVideoCard } from "../widgets/video_session_card.js";
import { musicOutput, openMediaPicker } from "../widgets/media_picker.js";
import { createPromptAssist } from "../widgets/prompt_assist.js";
import { createSessionPane } from "./media_session.js";
import { ParamsError, autoTitle, randomSeed, sessionTitle } from "../pure/media_session.js";
import { hasImage } from "../pure/image_session.js";
import { videoCostNote } from "../pure/video_cost.js";
import {
  DURATIONS, SIZES, canContinue, chipText, firstFrameLabel, nextFields, readVideoParams, refImageOf, refineFields, sourceOf,
  versionParams,
} from "../pure/video_session.js";

// 提示词框默认 3 行；内容多时长高到 40vh，失焦且不超 3 行时回落（V-21）。
const PROMPT_ROWS = 3;
const MAX_UPLOAD = 32 * 1024 * 1024;
// 回填时只知道之前上传的素材 id，不知道原文件名：不把 id 露给用户。
const EARLIER_IMAGE = "之前上传的图片";
const EARLIER_VIDEO = "之前上传的视频";
const SEGMENT_ERRORS = new Set(["segment_missing", "segment_not_found"]);
// 配乐作业与配乐参考生成的这些错误显示后端原话（「需要 ffmpeg 才能拼接成片」「引用的音乐已不在」
// 「这首歌从第 N 秒起不足 2 秒」「没能截取这段音乐」等），同合成（S-02、S-12）。
const SOUNDTRACK_ERRORS = new Set([...SEGMENT_ERRORS, "capability_missing", "ref_missing", "invalid_params"]);
const MUSIC_REF_ERRORS = new Set(["segment_missing", "capability_missing", "ref_missing", "invalid_params", "audio_clip_failed"]);
const PLACEHOLDERS = {
  text: "视频提示词（含环境声描述）",
  image: "描述图片中的动作、镜头变化和声音",
  reference: "描述参考视频的哪些内容，以及想生成的新画面和声音",
  music_ref: "描述想生成的画面和动作",
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
    musicArea: q("music-area"), refImageUpload: q("ref-image-upload"), refImagePick: q("ref-image-pick"),
    refImageLabel: q("ref-image-label"), refImagePreview: q("ref-image-preview"),
    songPick: q("song-pick"), songLabel: q("song-label"), songPreview: q("song-preview"), audioStart: q("audio-start"),
  };
  const doc = root.ownerDocument;
  const drawSeed = ctx.randomSeed ?? randomSeed;
  const pickFrom = (kind, title, emptyText) => openMediaPicker(doc, {
    kind, title, emptyText,
    listSessions: () => api.listMediaSessions(kind),
    getSession: (id) => api.getMediaSession(kind, id),
    serveOutput: api.serveOutput,
  });
  // pickImage/pickMusic({title}) → null | {ref, title, index, label?}；测试可经 ctx 注入。
  const pickImage = ctx.pickImage ?? (({ title }) => pickFrom("image", title, "这个会话还没有生成好的图片"));
  const pickMusic = ctx.pickMusic ?? (({ title }) => pickFrom("music", title, "这个会话还没有生成好的歌"));

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
  // 配乐参考（S-32）：参考图来源同首帧的 upload/ref 两种；歌 {ref, label?}；引用失效时对应说明（S-34）。
  let refImage = null;
  let refImageGone = false;
  let song = null;
  let songGone = false;
  let uploading = false;
  let verbatimError = null; // 要显示后端原话的启动错误
  const brokenIds = new Set();
  // 图片、音乐会话（按 kind/id）：卡片首帧来源行、配乐标题与输入区说明要它们的标题、序号与风格描述；null 表示确认不在（404），
  // 只有请求成功（含 404）才写缓存；其他失败（网络、5xx）不写缓存，避免把「暂时读不到」当成「已不在」（issue #19）。
  const linkedSessions = new Map();
  const linkedLoading = new Set();
  const linkedFailedAt = new Map(); // key -> 最近一次读取失败的时间戳：5 秒内不重复请求（issue #19）
  const LINKED_RETRY_MS = 5000;
  let pane = null;

  const continuing = () => first?.type === "continue";
  const position = (id) => (pane?.currentSession()?.attempts ?? []).findIndex((a) => a.id === id);

  // ---------- 图片、音乐会话查找 ----------
  // 返回 session | null | undefined：null 表示 404（真的不在），undefined 表示读取失败（未知，不当作「已不在」）。
  async function loadLinked(kind, id) {
    const key = `${kind}/${id}`;
    try { linkedSessions.set(key, await api.getMediaSession(kind, id)); }
    catch (error) {
      // 404：真的不在。400：会话文件本身已损坏（media_session.js:351），同样是定性结论，不是暂时读不到，
      // 不然会一直显示「暂时读不到…请稍后重试」（final review Minor 1）。其余状态才是网络/服务瞬时错误。
      if (error?.status === 404 || error?.status === 400) linkedSessions.set(key, null);
      else return undefined; // 读取失败：不缓存，不当作「已不在」
    }
    return linkedSessions.get(key);
  }
  // 画卡片时用：还没读过就返回 undefined，读完重画一次；读取失败 5 秒内不重复请求。
  function linkedForCard(kind, id) {
    const key = `${kind}/${id}`;
    if (linkedSessions.has(key)) return linkedSessions.get(key);
    const failedAt = linkedFailedAt.get(key);
    if (failedAt != null && Date.now() - failedAt < LINKED_RETRY_MS) return undefined;
    if (!linkedLoading.has(key)) {
      linkedLoading.add(key);
      loadLinked(kind, id).then((result) => {
        linkedLoading.delete(key);
        if (result === undefined) linkedFailedAt.set(key, Date.now());
        else linkedFailedAt.delete(key);
        pane?.rerender();
      });
    }
    return undefined;
  }
  // 引用的那张图：仍是 done 且文件在才算数（V-40）；返回 {output, title, index} | null（已不在） | undefined（读取失败）。
  async function lookupImage(imageRef) {
    const session = await loadLinked("image", imageRef.session_id);
    if (session === undefined) return undefined;
    const attempts = session?.attempts ?? [];
    const index = attempts.findIndex((a) => a.id === imageRef.attempt_id);
    return index >= 0 && hasImage(attempts[index]) ? { output: attempts[index].output, title: sessionTitle(session), index } : null;
  }
  // 引用的那首歌：仍是 done 且有可用文件才算数（S-34）；返回 {file, label} | null（已不在） | undefined（读取失败）。
  async function lookupSong(songRef) {
    const session = await loadLinked("music", songRef.session_id);
    if (session === undefined) return undefined;
    const attempt = (session?.attempts ?? []).find((a) => a.id === songRef.attempt_id);
    const file = attempt?.status === "done" ? musicOutput(attempt) : null;
    return file ? { file, label: autoTitle(attempt.params?.caption) } : null;
  }
  // 卡片上的「首帧：图片会话「<标题>」第 N 次」：会话还没读过就先给通用说明，读完重画一次。
  function firstFrameText(attempt) {
    const imageRef = attempt?.refs?.first_frame;
    if (!imageRef?.session_id) return "";
    const session = linkedForCard("image", imageRef.session_id);
    if (session === undefined) return firstFrameLabel({ type: "ref" });
    const index = (session?.attempts ?? []).findIndex((a) => a.id === imageRef.attempt_id);
    return firstFrameLabel({ type: "ref" }, { imageTitle: session ? sessionTitle(session) : "", imageIndex: index >= 0 ? index : undefined });
  }
  // 配乐卡片标题里的风格描述摘要（S-31）：取不到给空串（标题只写「配乐」）。
  function songLabel(attempt) {
    const songRef = attempt?.refs?.soundtrack;
    if (!songRef?.session_id) return "";
    const found = (linkedForCard("music", songRef.session_id)?.attempts ?? []).find((a) => a.id === songRef.attempt_id);
    return found ? autoTitle(found.params?.caption) : "";
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
    if (tag === "img") media.alt = name;
    else media.controls = true;
    if (tag === "audio") media.setAttribute("preload", "none");
    box.append(media);
  }
  const fileUrl = (file) => (typeof URL.createObjectURL === "function" ? URL.createObjectURL(file) : "");

  function firstText() {
    if (first) {
      return firstFrameLabel(first, { fileName: first.name, imageTitle: first.title, imageIndex: first.index, continueIndex: first.index });
    }
    return firstGone ? "引用的图片已不在" : firstFrameLabel(null);
  }
  function refImageText() {
    if (refImage?.type === "upload") return `已选择：${refImage.name}`;
    if (refImage?.type === "ref") {
      return refImage.title && Number.isInteger(refImage.index)
        ? `参考图：图片会话「${refImage.title}」第 ${refImage.index + 1} 次` : "参考图：来自图片会话";
    }
    return refImageGone ? "引用的图片已不在" : "未选择";
  }
  function songText() {
    if (song) return `歌：${song.label || "来自音乐会话"}`;
    return songGone ? "引用的歌已不在" : "未选择";
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
    if (els.musicArea) els.musicArea.hidden = mode !== "music_ref";
    // 配乐参考没有素材自带的声音（音频来自所选的歌），不给「使用素材的声音」。
    if (els.audioRow) els.audioRow.hidden = mode === "text" || mode === "music_ref";
    els.prompt.placeholder = PLACEHOLDERS[mode] ?? PLACEHOLDERS.text;
    els.firstLabel.textContent = firstText();
    for (const control of [els.firstUpload, els.firstPick, els.last, els.clearLast]) if (control) control.disabled = locked || uploading;
    for (const control of [els.source, els.refImageUpload, els.refImagePick, els.songPick]) if (control) control.disabled = uploading;
    els.lastLabel.textContent = last ? `已选择：${last.name}` : "未选择";
    els.sourceLabel.textContent = refVideo ? `已选择：${refVideo.name}` : "未选择";
    if (els.refImageLabel) els.refImageLabel.textContent = refImageText();
    if (els.songLabel) els.songLabel.textContent = songText();
  }
  function updateCost() {
    if (els.costNote) els.costNote.textContent = videoCostNote(els.size.value, els.frames.value);
  }

  function setFirst(source) {
    first = source;
    firstGone = false;
    if (source?.type === "upload" && source.file) setPreview(els.firstPreview, "img", fileUrl(source.file), { name: source.name, objectUrl: true });
    else setPreview(els.firstPreview, "img", null);
    if (source?.type === "ref") checkImageRef(source, () => first, () => { first = null; firstGone = true; }, els.firstPreview);
    renderInputs();
  }
  function setRefImage(source) {
    refImage = source;
    refImageGone = false;
    if (source?.type === "upload" && source.file) setPreview(els.refImagePreview, "img", fileUrl(source.file), { name: source.name, objectUrl: true });
    else setPreview(els.refImagePreview, "img", null);
    if (source?.type === "ref") {
      checkImageRef(source, () => refImage, () => { refImage = null; refImageGone = true; }, els.refImagePreview);
    }
    renderInputs();
  }
  // 图片会话引用（首帧或参考图）：取到那张图就补标题、序号与预览；已不在就清空该来源并说明（V-40、S-34）；
  // 读取失败（未知）保留当前选择，只在页面错误行提示稍后重试（issue #19）。
  // current() 取槽里当前来源（这期间换过就作罢），gone() 清空并标记失效，box 是预览框。
  async function checkImageRef(source, current, gone, box) {
    const found = await lookupImage(source.ref);
    if (current() !== source) return;
    if (found === undefined) { pane.setError("暂时读不到图片会话，请稍后重试"); return; }
    if (!found) { gone(); renderInputs(); return; }
    source.title = found.title; source.index = found.index;
    setPreview(box, "img", api.serveOutput(found.output), { name: found.title });
    renderInputs();
  }
  // 歌 {ref, label?}：取到那首歌就补风格描述摘要与试听；已不在就清空并说明「引用的歌已不在」（S-34）。
  function setSong(value) {
    song = value;
    songGone = false;
    setPreview(els.songPreview, "audio", null);
    if (value) checkSong(value);
    renderInputs();
  }
  async function checkSong(value) {
    const found = await lookupSong(value.ref);
    if (song !== value) return;
    if (found === undefined) { pane.setError("暂时读不到音乐会话，请稍后重试"); return; }
    if (!found) { song = null; songGone = true; renderInputs(); return; }
    value.label = found.label;
    setPreview(els.songPreview, "audio", api.serveOutput(found.file));
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
    { input: els.refImageUpload, tag: "img", take: (file) => setRefImage({ type: "upload", file, name: file.name }) },
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
  // 续写型提示条：目标段本身要 canContinue。「在这段基础上改」一个续写段（ref.continues 指向它接的前段）时，
  // 前段同样要 canContinue，否则这段本身也生不了（issue #19）。
  function checkMissing() {
    if (!ref || ref.missing) return;
    const session = pane?.currentSession();
    if (!session) return;
    const attempts = session.attempts ?? [];
    const targetId = ref.type === "continue" ? ref.attemptId : ref.type === "refine" && ref.continues ? ref.continues : null;
    if (!targetId) return;
    const target = attempts.find((a) => a.id === targetId);
    if (!target || !canContinue(target) || brokenIds.has(target.id)) ref = { ...ref, missing: true };
  }
  // ref.type === "refine" 且已判定 missing 时，文案走续写型的「第 N 次的文件已不在」，N 是它接的那个前段的序号。
  function chipTextFor(r) {
    if (r?.type === "refine" && r.missing) return chipText({ type: "continue", index: position(r.continues), missing: true });
    return chipText(r);
  }
  function syncChip() {
    checkMissing();
    const visible = chipVisible();
    els.chip.hidden = !visible;
    els.chipText.textContent = visible ? chipTextFor(ref) : "";
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
    // 不需要 music.js 那个 ref.type==="continue"||chipVisible() 判断（final review Important 1）：一个续写段的
    // refine 会把 first 也设成 {type:"continue"}（sourceOf, L46-49），chipVisible() 因 continuing() 恒真，改种子不隐藏提示条。
    const missing = !!ref?.missing;
    els.start.disabled = state.disabled || missing || uploading;
    els.start.title = state.disabled ? state.reason : missing ? chipTextFor(ref) : "";
    if (secondary) {
      for (const button of secondary.buttons) {
        button.disabled = state.disabled;
        button.title = state.disabled ? state.reason : "";
      }
      secondary.hint.textContent = state.disabled ? state.reason : "";
    }
  }
  function refreshAvailability() {
    if (lastState) updateAvailability(pane.availability(), { secondary: lastState.secondary });
  }

  async function startJob(params) {
    try { return await api.startVideoJob(params); }
    catch (error) {
      if (SEGMENT_ERRORS.has(error?.code) || (params.mode === "music_ref" && MUSIC_REF_ERRORS.has(error?.code))) {
        verbatimError = error;
        if (params.continues && ref?.type === "continue" && ref.attemptId === params.continues) ref = { ...ref, missing: true };
      }
      throw error;
    }
  }
  async function startSoundtrack(params) {
    try { return await api.startSoundtrackJob(params); }
    catch (error) {
      if (SOUNDTRACK_ERRORS.has(error?.code)) verbatimError = error;
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
        ...o, elapsed: ours ? o.job.elapsed_s : undefined, serveOutput: api.serveOutput, firstFrameText, songLabel,
        onRefine: refine, onVersion: version, onContinue: continueAfter, onSoundtrack: soundtrack,
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
      onSessionSwitch: () => { brokenIds.clear(); clearChip(); }, // 播放出错的标记只在本会话内有效（issue #18）
      // 新会话：提示词、种子与已选素材清空；方式、画幅、时长、步数保留。
      onNewSession: () => {
        els.prompt.value = ""; els.seed.value = ""; ref = null;
        setFirst(null); setLast(null); setRefVideo(null); setRefImage(null); setSong(null);
        syncChip(); refreshAvailability();
      },
      focus: () => els.prompt.focus?.(),
      updateAvailability,
    },
    startJob, confirm: ctx.confirm, onStarted: ctx.onStarted,
  });

  async function generate(params, options) {
    verbatimError = null;
    await pane.startGeneration(params, options);
    if (verbatimError) { pane.setError(verbatimError.message); verbatimError = null; }
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
    } else if (mode === "music_ref") {
      if (!refImage) { pane.setError("请先选择参考图"); return; }
      if (!song) { pane.setError("请先选择一首歌"); return; }
      const raw = String(els.audioStart?.value ?? "").trim();
      const audioStart = raw ? Number(raw) : 0;
      if (!Number.isFinite(audioStart) || audioStart < 0) { pane.setError("起始秒数须为不小于 0 的数"); return; }
      body.mode = "music_ref";
      body.audio_start = audioStart;
      body.refs = { ref_audio: song.ref };
      if (refImage.type === "ref") body.refs.ref_image = refImage.ref;
      else uploads.push(["ref_image", refImage]);
    }
    if (mode !== "text" && mode !== "music_ref") body.use_audio = !!els.audio?.checked;
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

  // fields 同 refineFields 的形状，另带配乐参考的 refImageSource（参考图来源）与 song（音乐引用）；
  // nextFirst 是首帧来源；nextRef 是提示条引用。
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
    if (els.audioStart) els.audioStart.value = String(fields.audioStart ?? 0);
    setRefImage(fields.refImageSource ?? null);
    setSong(fields.song ? { ref: fields.song } : null);
    setFirst(nextFirst);
    ref = fields.seed == null && nextFirst?.type !== "continue" ? null : nextRef;
    updateCost();
    syncChip();
    refreshAvailability();
    focusPromptEnd();
  }

  // 首帧来源、配乐参考的参考图来源共用（refImageOf 只给 ref/upload 两种）。
  function firstFromSource(source) {
    if (source?.type === "continue") return { type: "continue", attemptId: source.attemptId, index: position(source.attemptId) };
    if (source?.type === "ref") return { type: "ref", ref: source.ref };
    if (source?.type === "upload") return { type: "upload", id: source.id, name: EARLIER_IMAGE };
    return null;
  }

  function refine(attempt, index) {
    const fields = refineFields(attempt);
    const music = fields.mode === "music_ref"
      ? { refImageSource: firstFromSource(refImageOf(attempt)), song: attempt.refs?.ref_audio ?? null } : {};
    pane.keepInView(attempt.id);
    prefill({ ...fields, ...music }, firstFromSource(sourceOf(attempt)),
      { type: "refine", index, attemptId: attempt.id, seed: fields.seed, continues: attempt.continues ?? null });
    pane.settleView();
  }

  function version(attempt) {
    const sessionId = pane.currentId();
    if (pane.availability().disabled || !sessionId) return;
    generate(versionParams(attempt, sessionId, drawSeed), { fromInputs: false });
  }

  // 「配乐…」（S-30）：选一首歌 → 配乐作业走同一条生成路径（提交 → onStarted → 选中新尝试 → 重载会话）。
  async function soundtrack(attempt) {
    const sessionId = pane.currentId();
    if (pane.availability().disabled || !sessionId) return;
    const choice = await pickMusic({ title: "选一首歌配到这段视频" });
    if (!choice?.ref || pane.currentId() !== sessionId) return;
    const body = { session_id: sessionId, source: attempt.id, refs: { soundtrack: choice.ref } };
    await generate(body, { fromInputs: false, via: startSoundtrack });
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
    const musicRef = fields.mode === "music_ref";
    const refImageSource = !musicRef ? null : fields.refs?.ref_image ? { type: "ref", ref: fields.refs.ref_image }
      : fields.ref_image ? { type: "upload", id: fields.ref_image, name: EARLIER_IMAGE } : null;
    prefill({
      mode: fields.mode ?? "text", prompt: fields.prompt ?? "", size, frames: fields.frames, steps: fields.steps, seed,
      last: fields.last_frame ?? null, refVideo: fields.ref_video ?? null, useAudio: fields.use_audio !== false,
      audioStart: Number.isFinite(fields.audio_start) ? fields.audio_start : 0,
      refImageSource, song: musicRef ? fields.refs?.ref_audio ?? null : null,
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
    const pick = await pickImage({ title: "从图片会话选首帧" });
    if (pick) useImageRef(pick);
  });
  els.refImagePick?.addEventListener("click", async () => {
    if (els.refImagePick.disabled) return;
    const pick = await pickImage({ title: "从图片会话选参考图" });
    if (pick?.ref) { pane.setError(""); setRefImage({ type: "ref", ref: pick.ref, title: pick.title, index: pick.index }); }
  });
  els.songPick?.addEventListener("click", async () => {
    if (els.songPick.disabled) return;
    const pick = await pickMusic({ title: "从音乐会话选一首歌" });
    if (pick?.ref) { pane.setError(""); setSong({ ref: pick.ref, label: pick.label }); }
  });

  renderInputs();
  updateCost();
  syncChip();
  return {
    // 每次打开视频页重读图片、音乐会话：卡片上的标题与风格描述可能在别的页改过。
    refresh: () => { linkedSessions.clear(); linkedFailedAt.clear(); return pane.refresh(); },
    applyJob: pane.applyJob, poll: pane.poll,
    applyFill: (plan) => pane.applyFill(plan, { refine, prefillOnly: prefillFromLibrary }),
    setHeavyAllowed: pane.setHeavyAllowed, setModelStatus: pane.setModelStatus, setRuntimeStatus: pane.setRuntimeStatus,
    setAssistAvailable: (allowed, reason) => assist?.setAvailable(allowed, reason),
    useFirstFrame,
  };
}
