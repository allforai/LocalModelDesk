import * as api from "../api.js";
import { createJobView } from "../widgets/jobview.js";
import { confirmDialog } from "../widgets/confirm.js";
import { createPromptAssist } from "../widgets/prompt_assist.js";
import { videoCostNote } from "../pure/video_cost.js";

const SIZES = [["512x288", "草稿 512×288"], ["768x448", "标准 768×448"], ["1024x576", "清晰 1024×576"]];
const DURATIONS = [[49, "约 2 秒（快速）"], [73, "约 3 秒"], [124, "约 5 秒（常用）"], [192, "约 8 秒"], [243, "约 10 秒"], [362, "约 15 秒（最长）"]];

function acceptsType(accept, type) {
  return !accept || accept.split(",").map((item) => item.trim()).includes(type);
}

export function createVideoPane(root, ctx = {}) {
  const els = {
    prompt: root.querySelector("[data-video-prompt]"), size: root.querySelector("[data-video-size]"),
    frames: root.querySelector("[data-video-frames]"), steps: root.querySelector("[data-video-steps]"),
    startBtn: root.querySelector("[data-video-start]"), error: root.querySelector("[data-video-error]"),
    hint: root.querySelector("[data-video-hint]"),
  };
  for (const [value, label] of SIZES) {
    const option = root.ownerDocument.createElement("option");
    option.value = value; option.textContent = label; els.size.append(option);
  }
  for (const [value, label] of DURATIONS) {
    const option = root.ownerDocument.createElement("option");
    option.value = String(value); option.textContent = label; els.frames.append(option);
  }
  const jobView = createJobView(root, { mediaTag: "video", kind: "video" });
  const mode = root.querySelector("[data-video-mode]");
  const uploadStatus = root.querySelector("[data-video-upload-status]");
  let submitting = false, heavyAllowed = true, blockedReason = "";
  const saved = {};
  const inputs = {};
  for (const [key, name, tag] of [["first_frame", "first", "img"], ["last_frame", "last", "img"], ["ref_video", "source", "video"]]) {
    const input = root.querySelector(`[data-video-${name}]`);
    const preview = root.querySelector(`[data-video-${name}-preview]`);
    const nameLabel = root.querySelector(`[data-video-${name}-name]`);
    inputs[key] = input;
    let url;
    input?.addEventListener("change", () => {
      delete saved[key];
      if (url) URL.revokeObjectURL(url);
      preview.replaceChildren();
      const file = input.files?.[0];
      if (nameLabel) nameLabel.textContent = file ? file.name : "未选择文件";
      if (!file) return;
      if (!file.size || file.size > 32 * 1024 * 1024) {
        input.value = "";
        if (nameLabel) nameLabel.textContent = "未选择文件";
        els.error.textContent = "请选择非空且不超过 32 MB 的素材";
        return;
      }
      els.error.textContent = "";
      const media = root.ownerDocument.createElement(tag);
      url = URL.createObjectURL(file); media.src = url;
      media.style.cssText = "max-width:100%;max-height:200px;display:block;margin:8px 0";
      if (tag === "video") media.controls = true;
      else media.alt = file.name;
      preview.append(media);
    });
    // issue #15: the input is visually hidden, so a dragged file has to be accepted by its row.
    // `accept` only filters the picker, never a drop, hence the explicit type check.
    const row = input?.closest(".file-row");
    row?.addEventListener("dragover", (event) => { event.preventDefault(); row.classList.add("drag-over"); });
    row?.addEventListener("dragleave", () => row.classList.remove("drag-over"));
    row?.addEventListener("drop", (event) => {
      event.preventDefault();
      row.classList.remove("drag-over");
      const file = event.dataTransfer?.files?.[0];
      if (!file) return;
      if (!acceptsType(input.accept, file.type)) {
        els.error.textContent = tag === "img" ? "这里只支持 PNG、JPEG、WebP 图片" : "这里只支持 MP4、MOV、WebM 视频";
        return;
      }
      const transfer = new DataTransfer();
      transfer.items.add(file);
      input.files = transfer.files;
      input.dispatchEvent(new Event("change"));
    });
  }
  function updateMode() {
    if (!mode) return;
    root.querySelector("[data-video-images]").hidden = mode.value !== "image";
    root.querySelector("[data-video-reference]").hidden = mode.value !== "reference";
    els.prompt.placeholder = mode.value === "image" ? "描述图片中的动作、镜头变化和声音" :
      mode.value === "reference" ? "描述参考视频的哪些内容，以及想生成的新画面和声音" : "视频提示词（含环境声描述）";
    els.error.textContent = "";
  }
  mode?.addEventListener("change", updateMode);
  const costNote = root.querySelector("[data-video-cost-note]");
  function updateCost() {
    if (costNote) costNote.textContent = videoCostNote(els.size.value, els.frames.value);
  }
  els.size.addEventListener("change", updateCost);
  els.frames.addEventListener("change", updateCost);
  updateCost();
  const assistRoot = root.querySelector("[data-video-assist]");
  const assist = assistRoot ? createPromptAssist(root.ownerDocument, assistRoot, {
    task: "video",
    read: () => ({ text: els.prompt.value }),
    write: ({ text }) => { els.prompt.value = text; },
    mode: () => mode?.value || "text",
    confirm: ctx.confirm ? (options) => ctx.confirm(root.ownerDocument, options) : undefined,
  }) : null;
  root.querySelector("[data-video-clear-last]")?.addEventListener("click", () => {
    if (submitting) return;
    inputs.last_frame.value = "";
    inputs.last_frame.dispatchEvent(new Event("change"));
  });
  async function submit(params) {
    try { return await api.startVideoJob(params); }
    catch (error) {
      if (error.code !== "insufficient_memory") throw error;
      const ok = await (ctx.confirm ?? confirmDialog)(root.ownerDocument, { title: "内存可能不足", message: error.message, confirmLabel: "仍要生成" });
      if (!ok) return null;
      return api.startVideoJob({ ...params, force: true });
    }
  }
  els.startBtn.addEventListener("click", async () => {
    if (submitting || !heavyAllowed) return;
    els.error.textContent = "";
    const [width, height] = els.size.value.split("x").map(Number);
    const selectedMode = mode?.value || "text";
    const params = { prompt: els.prompt.value, width, height, frames: Number(els.frames.value), steps: Number(els.steps.value) };
    try {
      if (!params.prompt.trim()) throw new Error("请填写视频提示词");
      const keys = selectedMode === "image" ? ["first_frame", "last_frame"] : selectedMode === "reference" ? ["ref_video"] : [];
      if (keys.length && !inputs[keys[0]].files?.[0] && !saved[keys[0]]) throw new Error(selectedMode === "image" ? "请先选择首帧图片" : "请先选择参考视频");
      submitting = true; els.startBtn.disabled = true;
      if (mode) mode.disabled = true;
      for (const input of Object.values(inputs)) if (input) input.disabled = true;
      if (selectedMode !== "text") {
        params.mode = selectedMode;
        params.use_audio = root.querySelector("[data-video-audio]").checked;
      }
      for (const key of keys) {
        const file = inputs[key].files?.[0];
        if (file && !saved[key]) {
          uploadStatus.textContent = `正在上传 ${file.name}…`;
          saved[key] = (await api.uploadMediaInput(file)).id;
        }
        if (saved[key]) params[key] = saved[key];
      }
      if (uploadStatus) uploadStatus.textContent = "正在提交生成任务…";
      const job = await submit(params);
      if (!job) return;
      jobView.start(job); ctx.onStarted?.(job);
    } catch (error) { els.error.textContent = error.message; }
    finally {
      submitting = false; els.startBtn.disabled = !heavyAllowed;
      if (mode) mode.disabled = false;
      for (const input of Object.values(inputs)) if (input) input.disabled = false;
      if (uploadStatus) uploadStatus.textContent = "";
    }
  });
  function fill(fields) {
    if (mode) {
      mode.value = fields.mode || "text";
      for (const key of Object.keys(inputs)) {
        inputs[key].value = "";
        inputs[key].dispatchEvent(new Event("change"));
        if (fields[key]) saved[key] = fields[key];
      }
      root.querySelector("[data-video-audio]").checked = fields.use_audio !== false;
      updateMode();
      if (fields.mode && uploadStatus) uploadStatus.textContent = "已恢复历史素材，可直接生成或重新选择文件。";
    }
    if (fields.prompt != null) els.prompt.value = fields.prompt;
    if (fields.width && fields.height) els.size.value = `${fields.width}x${fields.height}`;
    if (fields.frames != null) {
      const closest = DURATIONS.reduce((best, item) =>
        Math.abs(item[0] - fields.frames) < Math.abs(best[0] - fields.frames) ? item : best
      );
      els.frames.value = String(closest[0]);
    }
    if (fields.steps != null) els.steps.value = String(fields.steps);
    updateCost();
  }
  function setHeavyAllowed(allowed, reason = "") {
    heavyAllowed = allowed;
    els.startBtn.disabled = submitting || !allowed;
    if (!allowed) { blockedReason = reason; if (els.hint) els.hint.textContent = reason; els.startBtn.title = reason; }
    else { blockedReason = ""; if (els.hint) els.hint.textContent = ""; els.startBtn.title = ""; }
  }
  return { fill, jobView, setHeavyAllowed, setAssistAvailable: (allowed, reason) => assist?.setAvailable(allowed, reason) };
}
