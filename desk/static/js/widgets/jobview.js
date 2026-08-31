// Shared media-job presentation: status, incremental log, cancellation, and playback.
import * as api from "../api.js";
import { formatDuration } from "../pure/format.js";

const STATUS_LABEL = { idle: "空闲", running: "生成中…", done: "完成", error: "失败", cancelled: "已取消" };

export function createJobView(root, { mediaTag }) {
  const els = {
    status: root.querySelector("[data-job-status]"), log: root.querySelector("[data-job-log]"),
    cancelBtn: root.querySelector("[data-job-cancel]"), player: root.querySelector("[data-job-player]"),
    error: root.querySelector("[data-job-error]"),
  };
  let jobId = null;
  let logFrom = 0;
  let pollTimer = null;
  let polling = false;

  function stopPolling() {
    if (pollTimer !== null) globalThis.clearInterval(pollTimer);
    pollTimer = null;
  }
  function reset() {
    stopPolling();
    jobId = null; logFrom = 0;
    els.log.textContent = ""; els.player.replaceChildren(); els.error.textContent = "";
  }
  function statusText(job) {
    const duration = job.started_at && job.finished_at ? `（耗时 ${formatDuration(job.finished_at - job.started_at)}）` : "";
    return `${STATUS_LABEL[job.status] ?? job.status}${duration}`;
  }
  function apply(payload) {
    els.status.textContent = statusText(payload);
    els.cancelBtn.hidden = payload.status !== "running";
    if (typeof payload.log === "string" && payload.log) { els.log.textContent += payload.log; els.log.scrollTop = els.log.scrollHeight; }
    if (payload.status === "error" && payload.error) els.error.textContent = `${payload.error.code}：${payload.error.message}`;
    if (payload.status === "done" && payload.output && !els.player.firstChild) {
      const media = root.ownerDocument.createElement(mediaTag);
      media.controls = true; media.src = api.serveOutput(payload.output); els.player.append(media);
    }
    if (payload.status !== "running") stopPolling();
    return payload;
  }
  async function poll() {
    if (polling || jobId === null) return;
    polling = true;
    try {
      const payload = await api.jobStatus(logFrom, jobId);
      apply(payload);
      logFrom = payload.next_log_from ?? logFrom;
    } catch (error) {
      els.error.textContent = error.message;
    } finally {
      polling = false;
    }
  }
  function start(payload) {
    reset();
    jobId = payload.job_id ?? null;
    logFrom = payload.next_log_from ?? 0;
    apply(payload);
    if (payload.status === "running" && jobId !== null) pollTimer = globalThis.setInterval(poll, 2000);
    return payload;
  }
  els.cancelBtn.addEventListener("click", async () => {
    try { apply(await api.cancelJob()); } catch (error) { els.error.textContent = error.message; }
  });
  return { reset, apply, start };
}
