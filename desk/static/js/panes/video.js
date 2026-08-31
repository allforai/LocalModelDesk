import * as api from "../api.js";
import { createJobView } from "../widgets/jobview.js";

const SIZES = [["512x288", "草稿 512×288"], ["768x448", "标准 768×448"], ["1024x576", "清晰 1024×576"]];

export function createVideoPane(root, ctx = {}) {
  const els = {
    prompt: root.querySelector("[data-video-prompt]"), size: root.querySelector("[data-video-size]"),
    frames: root.querySelector("[data-video-frames]"), steps: root.querySelector("[data-video-steps]"),
    startBtn: root.querySelector("[data-video-start]"), error: root.querySelector("[data-video-error]"),
  };
  for (const [value, label] of SIZES) {
    const option = root.ownerDocument.createElement("option");
    option.value = value; option.textContent = label; els.size.append(option);
  }
  const jobView = createJobView(root, { mediaTag: "video" });
  els.startBtn.addEventListener("click", async () => {
    els.error.textContent = "";
    const [width, height] = els.size.value.split("x").map(Number);
    try {
      const job = await api.startVideoJob({ prompt: els.prompt.value, width, height, frames: Number(els.frames.value), steps: Number(els.steps.value) });
      jobView.start(job); ctx.onStarted?.(job);
    } catch (error) { els.error.textContent = error.message; }
  });
  function fill(fields) {
    if (fields.prompt != null) els.prompt.value = fields.prompt;
    if (fields.width && fields.height) els.size.value = `${fields.width}x${fields.height}`;
    if (fields.frames != null) els.frames.value = String(fields.frames);
    if (fields.steps != null) els.steps.value = String(fields.steps);
  }
  return { fill, jobView };
}
