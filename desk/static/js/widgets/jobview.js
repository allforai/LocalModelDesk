// Shared media-job presentation: status, incremental log, cancellation, and playback.
import * as api from "../api.js";
import { formatDuration } from "../pure/format.js";
import { describeJobError } from "../pure/job_error.js";
import { parseStepProgress } from "../pure/job_progress.js";

const STATUS_LABEL = { idle: "空闲", running: "生成中…", done: "完成", error: "失败", cancelled: "已取消" };

export function createJobView(root, { mediaTag }) {
  const els = {
    status: root.querySelector("[data-job-status]"), log: root.querySelector("[data-job-log]"),
    cancelBtn: root.querySelector("[data-job-cancel]"), player: root.querySelector("[data-job-player]"),
    error: root.querySelector("[data-job-error]"), progress: root.querySelector("[data-job-progress]"),
    logDetails: root.querySelector(".job-log"),
  };
  let jobId = null;
  let logFrom = 0;
  let logText = "";
  function reset() {
    jobId = null; logFrom = 0; logText = "";
    els.log.textContent = ""; els.player.replaceChildren(); els.error.textContent = "";
    if (els.progress) els.progress.hidden = true;
    if (els.logDetails) els.logDetails.open = false;
  }
  function statusText(job) {
    if (job.status === "running" && typeof job.elapsed_s === "number") return `生成中…（已用 ${formatDuration(job.elapsed_s)}）`;
    const duration = job.started_at && job.finished_at ? `（耗时 ${formatDuration(job.finished_at - job.started_at)}）` : "";
    return `${STATUS_LABEL[job.status] ?? job.status}${duration}`;
  }
  function apply(payload) {
    els.status.textContent = statusText(payload);
    els.cancelBtn.hidden = payload.status !== "running";
    if (typeof payload.log === "string" && payload.log) {
      els.log.textContent += payload.log; els.log.scrollTop = els.log.scrollHeight; logText += payload.log;
    }
    if (els.progress) {
      const prog = parseStepProgress(logText);
      els.progress.hidden = !(payload.status === "running" && prog);
      if (prog) els.progress.value = prog.pct;
    }
    if (payload.status === "error" && payload.error) {
      const { title, detail } = describeJobError(payload.error);
      els.error.replaceChildren();
      const strong = root.ownerDocument.createElement("strong"); strong.textContent = title;
      const details = root.ownerDocument.createElement("details");
      const summary = root.ownerDocument.createElement("summary"); summary.textContent = "详情";
      const pre = root.ownerDocument.createElement("pre"); pre.textContent = detail;
      details.append(summary, pre); els.error.append(strong, details);
      if (els.logDetails) els.logDetails.open = true;
    }
    if (payload.status === "done" && payload.output && !els.player.firstChild) {
      const media = root.ownerDocument.createElement(mediaTag);
      media.controls = true; media.src = api.serveOutput(payload.output); els.player.append(media);
    }
    return payload;
  }
  function start(payload) {
    reset();
    jobId = payload.job_id ?? null;
    logFrom = payload.next_log_from ?? 0;
    apply(payload);
    return payload;
  }
  els.cancelBtn.addEventListener("click", async () => {
    try { apply(await api.cancelJob()); } catch (error) { els.error.textContent = error.message; }
  });
  async function sync() {
    try { apply(await api.jobStatus(0, null)); } catch { /* offline: keep what we have */ }
  }
  return { reset, apply, start, sync };
}
