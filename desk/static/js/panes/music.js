import * as api from "../api.js";
import { createJobView } from "../widgets/jobview.js";

export function createMusicPane(root, ctx = {}) {
  const els = {
    caption: root.querySelector("[data-music-caption]"), lyrics: root.querySelector("[data-music-lyrics]"),
    duration: root.querySelector("[data-music-duration]"), startBtn: root.querySelector("[data-music-start]"),
    error: root.querySelector("[data-music-error]"),
  };
  const jobView = createJobView(root, { mediaTag: "audio" });
  els.startBtn.addEventListener("click", async () => {
    els.error.textContent = "";
    try {
      const job = await api.startMusicJob({ caption: els.caption.value, lyrics: els.lyrics.value, duration: Number(els.duration.value) });
      jobView.start(job); ctx.onStarted?.(job);
    } catch (error) { els.error.textContent = error.message; }
  });
  function fill(fields) {
    if (fields.caption != null) els.caption.value = fields.caption;
    if (fields.lyrics != null) els.lyrics.value = fields.lyrics;
    if (fields.duration != null) els.duration.value = String(fields.duration);
  }
  function setHeavyAllowed(allowed, reason = "") {
    els.startBtn.disabled = !allowed;
    if (!allowed) els.error.textContent = reason;
    else if (els.error.textContent === reason || reason === "") els.error.textContent = "";
  }
  return { fill, jobView, setHeavyAllowed };
}
