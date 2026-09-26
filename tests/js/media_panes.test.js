import test from "node:test";
import assert from "node:assert/strict";
import { createVideoPane } from "../../desk/static/js/panes/video.js";

class Element {
  constructor(value = "", tagName = "div") {
    this.value = value; this.tagName = tagName; this.textContent = "";
    this.children = []; this.listeners = {}; this.hidden = false; this.controls = false;
    this.scrollTop = 0; this.scrollHeight = 40; this.dataset = {}; this.indeterminate = false;
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { return this.listeners.click?.(); }
  removeAttribute(name) { if (name === "value") { this.value = ""; this.indeterminate = true; } }
  get firstChild() { return this.children[0] || null; }
}

function pane(values) {
  const parts = Object.fromEntries(Object.entries(values).map(([name, value]) => [name, new Element(value)]));
  for (const name of ["job-status", "job-cancel", "job-log", "job-progress", "job-player", "job-error", "job-log-details", "video-error", "video-hint", "video-first-name", "video-last-name", "video-source-name", "video-size", "video-frames"]) parts[name] ??= new Element();
  const doc = { createElement: (tag) => new Element("", tag) };
  return { parts, ownerDocument: doc, querySelector(selector) {
    if (selector === ".job-log") return parts["job-log-details"];
    return parts[selector.match(/^\[data-([\w-]+)\]$/)?.[1]] || null; } };
}

function withFetch(responses, run) {
  const previous = globalThis.fetch; const calls = [];
  globalThis.fetch = async (url, options = {}) => { calls.push({ url, options }); return { ok: true, json: async () => responses.shift() }; };
  return Promise.resolve(run(calls)).finally(() => { globalThis.fetch = previous; });
}

// 图片页、音乐页已改为会话式界面，它们的面板测试在 image_pane.test.js、music_pane.test.js。

test("video pane uses documented DOM selectors, submit media APIs, and fill saved fields", async () => {
  const video = pane({ "video-prompt": "海边", "video-size": "768x448", "video-frames": "49", "video-steps": "16", "video-start": "" });
  const started = [];
  const videoPane = createVideoPane(video, { onStarted: (job) => started.push(job) });
  assert.deepEqual(video.parts["video-size"].children.map((option) => option.value), ["512x288", "768x448", "1024x576"]);
  assert.deepEqual(video.parts["video-frames"].children.map((option) => option.textContent), ["约 2 秒（快速）", "约 3 秒", "约 5 秒（常用）", "约 8 秒", "约 10 秒", "约 15 秒（最长）"]);
  videoPane.fill({ prompt: "夜景", width: 1024, height: 576, frames: 57, steps: 20 });
  assert.equal(video.parts["video-size"].value, "1024x576");
  await withFetch([{ job_id: 7, status: "running", kind: "video", log: "started" }], async (calls) => {
    await video.parts["video-start"].click();
    assert.deepEqual(calls.map(({ url, options }) => [url, JSON.parse(options.body)]), [
      ["/api/media/video", { prompt: "夜景", width: 1024, height: 576, frames: 49, steps: 20 }],
    ]);
  });
  assert.equal(video.parts["job-status"].textContent, "生成中…");
  assert.equal(video.parts["job-cancel"].hidden, false);
  assert.equal(video.parts["job-log"].textContent, "started");
  assert.deepEqual(started.map(({ job_id }) => job_id), [7]);
});

test("jobview appends polling logs, shows failures, and cancels through documented controls", async () => {
  const video = pane({ "video-prompt": "雾", "video-size": "512x288", "video-frames": "25", "video-steps": "8", "video-start": "" });
  const controller = createVideoPane(video);
  controller.jobView.apply({ job_id: 1, status: "running", log: "one" });
  controller.jobView.apply({ job_id: 1, status: "error", log: "two", error: { code: "media_busy", message: "忙" } });
  assert.equal(video.parts["job-log"].textContent, "onetwo");
  assert.equal(video.parts["job-log"].scrollTop, 40);
  assert.equal(video.parts["job-error"].children[0].textContent, "已有作业在进行");
  assert.equal(video.parts["job-cancel"].hidden, true);
  await withFetch([{ status: "cancelled" }], async (calls) => { await video.parts["job-cancel"].click(); assert.equal(calls[0].url, "/api/media/cancel"); });
  assert.equal(video.parts["job-status"].textContent, "已取消");
});

test("视频面板有看手气与优化提示词，写回输入框", async () => {
  const video = pane({ "video-prompt": "", "video-size": "768x448", "video-frames": "49", "video-steps": "16", "video-start": "", "video-assist": "" });
  const videoPane = createVideoPane(video);
  const videoButtons = video.parts["video-assist"].children;
  assert.deepEqual(videoButtons.slice(0, 3).map((b) => b.textContent), ["看手气", "优化提示词", "恢复原文"]);

  videoPane.setAssistAvailable(true, "");
  const previous = globalThis.fetch;
  const replies = [{ task: "video", action: "lucky", text: "雨夜街角" }];
  globalThis.fetch = async () => new Response(JSON.stringify(replies.shift()), { status: 200 });
  try {
    await videoButtons[0].click();
  } finally { globalThis.fetch = previous; }
  assert.equal(video.parts["video-prompt"].value, "雨夜街角");
});

test("job views do not create independent polling timers and still apply shell-delivered job updates", async () => {
  const video = pane({ "video-prompt": "海浪", "video-size": "512x288", "video-frames": "25", "video-steps": "8", "video-start": "" });
  const videoPane = createVideoPane(video);
  const previousSetInterval = globalThis.setInterval;
  let intervals = 0;
  globalThis.setInterval = () => { intervals += 1; return intervals; };
  try {
    await withFetch([{ job_id: 12, status: "running", kind: "video", log: "one" }], async () => {
      await video.parts["video-start"].click();
    });
  } finally {
    globalThis.setInterval = previousSetInterval;
  }
  assert.equal(intervals, 0);
  videoPane.jobView.apply({ job_id: 12, status: "done", kind: "video", log: "two", output: "clip.mp4" });
  assert.equal(video.parts["job-log"].textContent, "onetwo");
  assert.equal(video.parts["job-player"].firstChild.tagName, "video");
});

test("内存不足被拒时先确认再以 force 重提", async () => {
  const video = pane({ "video-prompt": "海边", "video-size": "512x288", "video-frames": "49", "video-steps": "16", "video-start": "" });
  const doc = video.ownerDocument; doc.body = new Element();
  const confirmed = []; globalThis.__confirmForTest = async () => { confirmed.push(1); return true; };
  const responses = [
    { ok: false, status: 409, json: async () => ({ error: { code: "insufficient_memory", message: "需 103 GB，可用 60 GB" } }) },
    { ok: true, status: 200, json: async () => ({ job_id: 1, status: "running" }) },
  ];
  const previous = globalThis.fetch; const calls = [];
  globalThis.fetch = async (url, options = {}) => { calls.push({ url, options }); return responses.shift(); };
  try {
    createVideoPane(video, { confirm: globalThis.__confirmForTest });
    await video.parts["video-start"].click();
    assert.equal(confirmed.length, 1);
    assert.equal(JSON.parse(calls[1].options.body).force, true);
  } finally { globalThis.fetch = previous; delete globalThis.__confirmForTest; }
});

test("回到面板时 sync 会补画已完成作业的播放器，并显示已用时长", async () => {
  const video = pane({ "video-prompt": "", "video-size": "512x288", "video-frames": "49", "video-steps": "16", "video-start": "" });
  const p = createVideoPane(video, {});
  await withFetch([{ job_id: 3, status: "done", output: "h3-1.mp4", started_at: 10, finished_at: 87 }], async () => { await p.jobView.sync(); });
  assert.equal(video.parts["job-player"].firstChild.tagName, "video");
  p.jobView.apply({ job_id: 4, status: "running", elapsed_s: 12 });
  assert.equal(video.parts["job-status"].textContent, "生成中…（已用 12秒）");
});

test("媒体面板在其他重作业运行时禁用开始按钮，并在结束后恢复", () => {
  const video = pane({ "video-prompt": "海浪", "video-size": "512x288", "video-frames": "25", "video-steps": "8", "video-start": "" });
  const videoPane = createVideoPane(video);
  videoPane.setHeavyAllowed(false, "媒体作业进行中");
  assert.equal(video.parts["video-start"].disabled, true);
  assert.equal(video.parts["video-hint"].textContent, "媒体作业进行中");
  assert.equal(video.parts["video-error"].textContent, "");
  videoPane.setHeavyAllowed(true);
  assert.equal(video.parts["video-start"].disabled, false);
});

test("idle 状态文案给出下一步", () => {
  const video = pane({ "video-prompt": "", "video-size": "512x288", "video-frames": "49", "video-steps": "16", "video-start": "" });
  const p = createVideoPane(video, {});
  p.jobView.apply({ job_id: 0, status: "idle" });
  assert.equal(video.parts["job-status"].textContent, "空闲 · 填好左侧参数后点「生成」");
});

test("running 时按日志渲染进度条；选择文件后显示文件名", async () => {
  const video = pane({ "video-prompt": "", "video-size": "512x288", "video-frames": "49", "video-steps": "16", "video-start": "", "video-first-name": "" });
  const p = createVideoPane(video, {});
  p.jobView.apply({ job_id: 1, status: "running", log: "step 8/16 3s\n" });
  assert.equal(video.parts["job-progress"].value, 50);
  assert.equal(video.parts["job-progress"].hidden, false);
});

test("互斥原因用 busy 提示而不是 inline-error", () => {
  const video = pane({ "video-start": "", "video-hint": "" });
  const p = createVideoPane(video, {});
  p.setHeavyAllowed(false, "媒体作业进行中");
  assert.equal(video.parts["video-hint"].textContent, "媒体作业进行中");
  assert.equal(video.parts["video-error"].textContent, "");
});

test("sync 用全量日志替换而不是追加（G1），且不显示别的面板的作业（共用轮询）", async () => {
  const video = pane({ "video-prompt": "雾", "video-size": "512x288", "video-frames": "49", "video-steps": "8", "video-start": "" });
  const videoPane = createVideoPane(video, {});
  await withFetch([{ job_id: 3, status: "running", kind: "video", log: "step 1/16\n", next_log_from: 10 }], async () => {
    await video.parts["video-start"].click();
  });
  assert.equal(video.parts["job-log"].textContent, "step 1/16\n");
  await withFetch([{ job_id: 3, status: "done", kind: "video", output: "a.mp4", log: "step 1/16\nstep 16/16\nwrote a.mp4\n", next_log_from: 40 }], async () => {
    await videoPane.jobView.sync();
  });
  assert.equal(video.parts["job-log"].textContent, "step 1/16\nstep 16/16\nwrote a.mp4\n");
  await withFetch([{ job_id: 4, status: "done", kind: "music", output: "b.wav", log: "music log\n", next_log_from: 10 }], async () => {
    await videoPane.jobView.sync();
  });
  assert.equal(video.parts["job-status"].textContent, "空闲 · 填好左侧参数后点「生成」");
  assert.equal(video.parts["job-log"].textContent, "");
});

test("error 态：错误块先于日志、日志不自动展开、状态行带 data-state（F19/F20）", () => {
  const video = pane({ "video-prompt": "雾", "video-size": "512x288", "video-frames": "49", "video-steps": "8", "video-start": "" });
  video.parts["job-log-details"] = new Element("", "details");
  const view = createVideoPane(video, {}).jobView;
  view.apply({ job_id: 5, status: "error", kind: "video", error: { code: "exit_nonzero", message: "exit -9" }, log: "step 1/16\n" });
  assert.equal(video.parts["job-status"].dataset.state, "error");
  assert.equal(video.parts["job-log-details"].open, false);
  assert.equal(video.parts["job-error"].children[0].textContent, "生成程序异常退出");
});

test("清晰画幅加 10 秒以上时视频面板提示很慢，改小后提示消失", () => {
  const video = pane({ "video-prompt": "", "video-size": "768x448", "video-frames": "49", "video-steps": "16", "video-start": "", "video-cost-note": "" });
  const videoPane = createVideoPane(video);
  assert.equal(video.parts["video-cost-note"].textContent, "");

  videoPane.fill({ width: 1024, height: 576, frames: 362 });
  assert.match(video.parts["video-cost-note"].textContent, /20 分钟只走完 2\/16 步/);

  video.parts["video-size"].value = "512x288";
  video.parts["video-size"].listeners.change();
  assert.equal(video.parts["video-cost-note"].textContent, "");
});
