// Shared media-job presentation: status, incremental log, cancellation, and playback.
import * as api from "../api.js";
import { formatDuration } from "../pure/format.js";
import { parseStepProgress } from "../pure/job_progress.js";
import { renderErrorBlock } from "./error_block.js";

const STATUS_LABEL = { idle: "空闲 · 填好左侧参数后点「生成」", running: "生成中…", done: "完成", error: "失败", cancelled: "已取消" };
const IDLE = { job_id: null, status: "idle", kind: null, log: "" };

export function createJobView(root, { mediaTag, kind = null }) {
  const els = {
    status: root.querySelector("[data-job-status]"), log: root.querySelector("[data-job-log]"),
    cancelBtn: root.querySelector("[data-job-cancel]"), player: root.querySelector("[data-job-player]"),
    error: root.querySelector("[data-job-error]"), progress: root.querySelector("[data-job-progress]"),
    logDetails: root.querySelector(".job-log"),
  };
  let jobId = null;
  let logText = "";
  let lastStatus = "idle";
  function reset() {
    jobId = null; logText = "";
    els.log.textContent = ""; els.player.replaceChildren(); els.error.textContent = "";
    if (els.error.replaceChildren) els.error.replaceChildren();
    if (els.progress) { els.progress.hidden = true; els.progress.indeterminate = false; }
    if (els.logDetails) els.logDetails.open = false;
  }
  function statusText(job, opts = {}) {
    // A busy reason from the mutex (another heavy job holding memory) must
    // replace the idle hint outright — showing both "空闲…生成" and "媒体作业
    // 进行中" in the same spot is a direct contradiction (widewin gap #9).
    if (job.status === "idle" && opts.busyReason) return opts.busyReason;
    if (job.status === "running" && typeof job.elapsed_s === "number") return `生成中…（已用 ${formatDuration(job.elapsed_s)}）`;
    const duration = job.started_at && job.finished_at ? `（耗时 ${formatDuration(job.finished_at - job.started_at)}）` : "";
    return `${STATUS_LABEL[job.status] ?? job.status}${duration}`;
  }
  function renderError(error) {
    // [data-job-error] already carries the .job-error card class in markup, so
    // unwrap the shared block's children into it rather than nesting another
    // card inside it (library.js, which has no such wrapper, appends the
    // block itself — see error_block.js).
    const block = renderErrorBlock(root.ownerDocument, error);
    els.error.replaceChildren(...block.children);
  }
  function apply(payload, { replaceLog = false, busyReason = "" } = {}) {
    if (kind && payload.kind && payload.kind !== kind) { reset(); apply(IDLE, { busyReason }); return null; }
    if (payload.job_id !== jobId) { reset(); jobId = payload.job_id ?? null; replaceLog = true; }
    lastStatus = payload.status ?? "idle";
    els.status.textContent = statusText(payload, { busyReason });
    if (els.status.dataset) els.status.dataset.state = payload.status ?? "idle";
    els.cancelBtn.hidden = payload.status !== "running";
    if (typeof payload.log === "string") {
      if (replaceLog) { logText = payload.log; els.log.textContent = payload.log; }
      else if (payload.log) { logText += payload.log; els.log.textContent += payload.log; }
      els.log.scrollTop = els.log.scrollHeight;
    }
    if (els.progress) {
      const prog = parseStepProgress(logText);
      const running = payload.status === "running";
      els.progress.hidden = !running;
      if (running && prog) { els.progress.indeterminate = false; els.progress.value = prog.pct; }
      else if (running) { els.progress.indeterminate = true; els.progress.removeAttribute?.("value"); }
    }
    if (payload.status === "error" && payload.error) renderError(payload.error);
    if (payload.status === "done" && payload.output && !els.player.firstChild) {
      const media = root.ownerDocument.createElement(mediaTag);
      if (mediaTag === "img") media.alt = payload.params?.prompt || "生成的图片";
      else media.controls = true;
      media.src = api.serveOutput(payload.output); els.player.append(media);
    }
    return payload;
  }
  function start(payload) { reset(); jobId = payload.job_id ?? null; return apply(payload, { replaceLog: true }); }
  els.cancelBtn.addEventListener("click", async () => {
    try { apply(await api.cancelJob()); } catch (error) { els.error.textContent = error.message; }
  });
  async function sync(opts = {}) {
    try { apply(await api.jobStatus(0, null), { replaceLog: true, busyReason: opts.busyReason }); } catch { /* offline: keep what we have */ }
  }
  // Called every tick regardless of whether this pane's own job is being
  // polled — so a pane sitting idle on screen while the *other* kind starts
  // a job updates its caption immediately, not only on the next tab switch
  // (widewin gap #9). Never touches a running/done/error caption.
  function setBusyReason(reason) {
    // The backend's "never started a job yet" sentinel is job_id 0, not null —
    // only a genuinely non-zero job id should block this.
    if (lastStatus !== "idle" || jobId) return;
    els.status.textContent = statusText({ status: "idle" }, { busyReason: reason });
  }
  return { reset, apply, start, sync, setBusyReason };
}
