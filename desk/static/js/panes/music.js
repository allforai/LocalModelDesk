import * as api from "../api.js";
import { createJobView } from "../widgets/jobview.js";
import { confirmDialog } from "../widgets/confirm.js";
import { createPromptAssist } from "../widgets/prompt_assist.js";

export function createMusicPane(root, ctx = {}) {
  const els = {
    caption: root.querySelector("[data-music-caption]"), lyrics: root.querySelector("[data-music-lyrics]"),
    duration: root.querySelector("[data-music-duration]"), startBtn: root.querySelector("[data-music-start]"),
    error: root.querySelector("[data-music-error]"), hint: root.querySelector("[data-music-hint]"),
  };
  const jobView = createJobView(root, { mediaTag: "audio", kind: "music" });
  const assistRoot = root.querySelector("[data-music-assist]");
  const assist = assistRoot ? createPromptAssist(root.ownerDocument, assistRoot, {
    task: "music",
    read: () => ({ text: els.caption.value, lyrics: els.lyrics.value }),
    write: ({ text, lyrics }) => { els.caption.value = text; if (lyrics !== undefined) els.lyrics.value = lyrics; },
    confirm: ctx.confirm ? (options) => ctx.confirm(root.ownerDocument, options) : undefined,
  }) : null;
  async function submit(params) {
    try { return await api.startMusicJob(params); }
    catch (error) {
      if (error.code !== "insufficient_memory") throw error;
      const ok = await (ctx.confirm ?? confirmDialog)(root.ownerDocument, { title: "内存可能不足", message: error.message, confirmLabel: "仍要生成" });
      if (!ok) return null;
      return api.startMusicJob({ ...params, force: true });
    }
  }
  els.startBtn.addEventListener("click", async () => {
    els.error.textContent = "";
    try {
      if (!els.caption.value.trim()) throw new Error("请填写风格描述");
      if (!els.lyrics.value.trim()) throw new Error("请填写歌词：Music 3 需要歌词才能生成");
      const job = await submit({ caption: els.caption.value, lyrics: els.lyrics.value, duration: Number(els.duration.value) });
      if (!job) return;
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
    if (!allowed) { if (els.hint) els.hint.textContent = reason; els.startBtn.title = reason; }
    else { if (els.hint) els.hint.textContent = ""; els.startBtn.title = ""; }
  }
  return { fill, jobView, setHeavyAllowed, setAssistAvailable: (allowed, reason) => assist?.setAvailable(allowed, reason) };
}
