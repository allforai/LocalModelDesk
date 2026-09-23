import test from "node:test";
import assert from "node:assert/strict";
import { createVideoPane } from "../../desk/static/js/panes/video.js";
import { createMusicPane } from "../../desk/static/js/panes/music.js";
import { createImagePane } from "../../desk/static/js/panes/image.js";

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
  for (const name of ["job-status", "job-cancel", "job-log", "job-progress", "job-player", "job-error", "job-log-details", "video-error", "music-error", "video-hint", "music-hint", "video-first-name", "video-last-name", "video-source-name", "video-size", "video-frames"]) parts[name] ??= new Element();
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

function imagePane(ctx = {}) {
  const root = pane({ "image-prompt": "橘猫", "image-width": "1024", "image-height": "1024", "image-steps": "40", "image-seed": "42", "image-start": "", "image-error": "", "image-hint": "", "image-model": "" });
  const controller = createImagePane(root, ctx);
  return { root, controller, ready() {
    controller.setHeavyAllowed(true);
    controller.setRuntimeStatus({ present: true });
    controller.setModelStatus({ state: "present" });
  } };
}

test("图片页需要模型、运行时和仲裁同时就绪，轮询不能误解禁", () => {
  const { root, controller, ready } = imagePane();
  assert.equal(root.parts["image-start"].disabled, true);
  ready(); assert.equal(root.parts["image-start"].disabled, false);
  controller.setModelStatus({ state: "partial" });
  controller.setHeavyAllowed(true);
  assert.equal(root.parts["image-start"].disabled, true);
  assert.match(root.parts["image-hint"].textContent, /不完整/);
  ready(); controller.setRuntimeStatus({ present: false, detail: "运行环境缺失" });
  assert.equal(root.parts["image-start"].disabled, true);
  assert.match(root.parts["image-hint"].textContent, /运行环境缺失/);
});

test("图片页回填并提交完整参数，PNG 无音视频控件", async () => {
  const { root, controller, ready } = imagePane(); ready();
  const params = { prompt: "蓝杯子", width: 512, height: 768, steps: 30, seed: 0 };
  controller.fill(params);
  await withFetch([{ job_id: 8, kind: "image", status: "done", params, output: "qwen-image-1.png" }], async (calls) => {
    await root.parts["image-start"].click();
    assert.equal(calls[0].url, "/api/media/image");
    assert.deepEqual(JSON.parse(calls[0].options.body), params);
  });
  const img = root.parts["job-player"].firstChild;
  assert.equal(img.tagName, "img"); assert.equal(img.controls, false);
  assert.equal(img.alt, "蓝杯子");
  assert.equal(img.src, "/api/outputs/qwen-image-1.png");
});

test("图片页输入不合法时不请求；失败后可以重新提交", async () => {
  const { root, controller, ready } = imagePane(); ready();
  for (const invalid of [{ width: 257 }, { steps: 0 }, { seed: -1 }, { prompt: " " }, { seed: "" }]) {
    controller.fill({ prompt: "猫", width: 1024, height: 1024, steps: 40, seed: 42, ...invalid });
    await withFetch([], async (calls) => { await root.parts["image-start"].click(); assert.equal(calls.length, 0); });
    assert.ok(root.parts["image-error"].textContent);
    assert.equal(root.parts["image-start"].disabled, false);
  }
});

test("图片页提交中阻止双击，即使仲裁轮询暂时空闲", async () => {
  const { root, controller, ready } = imagePane(); ready();
  const previous = globalThis.fetch; let calls = 0, release;
  globalThis.fetch = async () => { calls += 1; await new Promise((r) => { release = r; }); return { ok: true, json: async () => ({ job_id: 4, kind: "image", status: "running" }) }; };
  try {
    const first = root.parts["image-start"].click();
    controller.setHeavyAllowed(true);
    await root.parts["image-start"].click();
    assert.equal(calls, 1); release(); await first;
    assert.equal(root.parts["image-start"].disabled, true);
  } finally { globalThis.fetch = previous; }
});

test("video/music panes use documented DOM selectors, submit media APIs, and fill saved fields", async () => {
  const video = pane({ "video-prompt": "海边", "video-size": "768x448", "video-frames": "49", "video-steps": "16", "video-start": "" });
  const music = pane({ "music-caption": "民谣", "music-lyrics": "一二三", "music-duration": "90", "music-start": "" });
  const started = [];
  const videoPane = createVideoPane(video, { onStarted: (job) => started.push(job) });
  const musicPane = createMusicPane(music, { onStarted: (job) => started.push(job) });
  assert.deepEqual(video.parts["video-size"].children.map((option) => option.value), ["512x288", "768x448", "1024x576"]);
  assert.deepEqual(video.parts["video-frames"].children.map((option) => option.textContent), ["约 2 秒（快速）", "约 3 秒", "约 5 秒（常用）", "约 8 秒", "约 10 秒", "约 15 秒（最长）"]);
  videoPane.fill({ prompt: "夜景", width: 1024, height: 576, frames: 57, steps: 20 });
  musicPane.fill({ caption: "爵士", lyrics: "la", duration: 75 });
  assert.equal(video.parts["video-size"].value, "1024x576");
  assert.equal(music.parts["music-duration"].value, "75");
  await withFetch([{ job_id: 7, status: "running", kind: "video", log: "started" }, { job_id: 8, status: "done", kind: "music", output: "song.wav" }], async (calls) => {
    await video.parts["video-start"].click(); await music.parts["music-start"].click();
    assert.deepEqual(calls.map(({ url, options }) => [url, JSON.parse(options.body)]), [
      ["/api/media/video", { prompt: "夜景", width: 1024, height: 576, frames: 49, steps: 20 }],
      ["/api/media/music", { caption: "爵士", lyrics: "la", duration: 75 }],
    ]);
  });
  assert.equal(video.parts["job-status"].textContent, "生成中…");
  assert.equal(video.parts["job-cancel"].hidden, false);
  assert.equal(video.parts["job-log"].textContent, "started");
  assert.equal(music.parts["job-player"].firstChild.tagName, "audio");
  assert.equal(music.parts["job-player"].firstChild.src, "/api/outputs/song.wav");
  assert.deepEqual(started.map(({ job_id }) => job_id), [7, 8]);
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

test("a finished job from another pane does not masquerade as this pane's state (F14)", () => {
  const music = pane({ "music-caption": "x", "music-lyrics": "y", "music-duration": "30", "music-start": "" });
  const musicPane = createMusicPane(music);
  musicPane.jobView.apply({ job_id: 3, status: "done", kind: "video", started_at: 1, finished_at: 31 });
  assert.ok(music.parts["job-status"].textContent.includes("空闲"), music.parts["job-status"].textContent);
});

test("视频/音乐面板各有看手气与优化提示词，写回各自的输入框", async () => {
  const video = pane({ "video-prompt": "", "video-size": "768x448", "video-frames": "49", "video-steps": "16", "video-start": "", "video-assist": "" });
  const music = pane({ "music-caption": "民谣", "music-lyrics": "", "music-duration": "60", "music-start": "", "music-assist": "" });
  const videoPane = createVideoPane(video);
  const musicPane = createMusicPane(music);
  const videoButtons = video.parts["video-assist"].children;
  const musicButtons = music.parts["music-assist"].children;
  assert.deepEqual(videoButtons.slice(0, 3).map((b) => b.textContent), ["看手气", "优化提示词", "恢复原文"]);
  assert.deepEqual(musicButtons.slice(0, 2).map((b) => b.textContent), ["看手气", "优化提示词"]);

  videoPane.setAssistAvailable(true, "");
  musicPane.setAssistAvailable(true, "");
  const previous = globalThis.fetch;
  const replies = [{ task: "video", action: "lucky", text: "雨夜街角" }, { task: "music", action: "refine", text: "木吉他民谣", lyrics: "第一行" }];
  globalThis.fetch = async () => new Response(JSON.stringify(replies.shift()), { status: 200 });
  try {
    await videoButtons[0].click();
    await musicButtons[1].click();
  } finally { globalThis.fetch = previous; }
  assert.equal(video.parts["video-prompt"].value, "雨夜街角");
  assert.equal(music.parts["music-caption"].value, "木吉他民谣");
  assert.equal(music.parts["music-lyrics"].value, "第一行");
});

test("busy reason replaces the idle hint instead of a stale finished-job caption (F14)", () => {
  const music = pane({ "music-caption": "x", "music-lyrics": "y", "music-duration": "30", "music-start": "" });
  const musicPane = createMusicPane(music);
  musicPane.jobView.apply({ job_id: null, status: "idle", kind: null }, { busyReason: "媒体作业进行中" });
  const text = music.parts["job-status"].textContent;
  assert.ok(text.includes("媒体作业进行中"), text);
  assert.ok(!text.includes("填好左侧参数"), "忙态还挂着空闲引导句");
});

test("setBusyReason updates an idle pane in place, but never a running/done one (F14)", () => {
  const music = pane({ "music-caption": "x", "music-lyrics": "y", "music-duration": "30", "music-start": "" });
  const musicPane = createMusicPane(music);
  musicPane.jobView.setBusyReason("媒体作业进行中");
  assert.ok(music.parts["job-status"].textContent.includes("媒体作业进行中"), music.parts["job-status"].textContent);

  musicPane.jobView.apply({ job_id: 9, status: "done", kind: "music", started_at: 1, finished_at: 5 });
  musicPane.jobView.setBusyReason("媒体作业进行中");
  assert.ok(!music.parts["job-status"].textContent.includes("媒体作业进行中"), "已完成的状态被忙态覆盖了");
});

test("setBusyReason still applies after a sync() against the backend's never-started sentinel (job_id 0)", () => {
  const music = pane({ "music-caption": "x", "music-lyrics": "y", "music-duration": "30", "music-start": "" });
  const musicPane = createMusicPane(music);
  // The real backend's idle sentinel is job_id 0, not null — a naive `!= null`
  // guard would treat that as "a job exists" and never let the reason through.
  musicPane.jobView.apply({ job_id: 0, status: "idle", kind: null, log: "" });
  musicPane.jobView.setBusyReason("媒体作业进行中");
  assert.ok(music.parts["job-status"].textContent.includes("媒体作业进行中"), music.parts["job-status"].textContent);
});

test("job views do not create independent polling timers and still apply shell-delivered job updates", async () => {
  const video = pane({ "video-prompt": "海浪", "video-size": "512x288", "video-frames": "25", "video-steps": "8", "video-start": "" });
  const music = pane({ "music-caption": "轻快", "music-lyrics": "la", "music-duration": "30", "music-start": "" });
  const videoPane = createVideoPane(video);
  const musicPane = createMusicPane(music);
  const previousSetInterval = globalThis.setInterval;
  let intervals = 0;
  globalThis.setInterval = () => { intervals += 1; return intervals; };
  try {
    await withFetch([{ job_id: 12, status: "running", kind: "video", log: "one" }, { job_id: 13, status: "running", kind: "music", log: "three" }], async () => {
      await video.parts["video-start"].click();
      await music.parts["music-start"].click();
    });
  } finally {
    globalThis.setInterval = previousSetInterval;
  }
  assert.equal(intervals, 0);
  videoPane.jobView.apply({ job_id: 12, status: "done", kind: "video", log: "two", output: "clip.mp4" });
  musicPane.jobView.apply({ job_id: 13, status: "done", kind: "music", log: "four", output: "song.wav" });
  assert.equal(video.parts["job-log"].textContent, "onetwo");
  assert.equal(video.parts["job-player"].firstChild.tagName, "video");
  assert.equal(music.parts["job-log"].textContent, "threefour");
  assert.equal(music.parts["job-player"].firstChild.tagName, "audio");
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

test("音乐面板空歌词时本地拦截并提示", async () => {
  const music = pane({ "music-caption": "民谣", "music-lyrics": "", "music-duration": "10", "music-start": "" });
  const previous = globalThis.fetch; let calls = 0;
  globalThis.fetch = async () => { calls += 1; return { ok: true, json: async () => ({}) }; };
  try {
    createMusicPane(music, {});
    await music.parts["music-start"].click();
    assert.equal(calls, 0);
    assert.equal(music.parts["music-error"].textContent, "请填写歌词：Music 3 需要歌词才能生成");
  } finally { globalThis.fetch = previous; }
});

test("音乐面板：风格描述留空时前端直接提示，不发请求", async () => {
  const music = pane({ "music-caption": "   ", "music-lyrics": "一二三", "music-duration": "10", "music-start": "" });
  createMusicPane(music, {});
  await withFetch([], async (calls) => { await music.parts["music-start"].click(); assert.equal(calls.length, 0); });
  assert.equal(music.parts["music-error"].textContent, "请填写风格描述");
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
  const music = pane({ "music-caption": "轻快", "music-lyrics": "la", "music-duration": "30", "music-start": "" });
  const videoPane = createVideoPane(video);
  const musicPane = createMusicPane(music);
  videoPane.setHeavyAllowed(false, "媒体作业进行中");
  musicPane.setHeavyAllowed(false, "媒体作业进行中");
  assert.equal(video.parts["video-start"].disabled, true);
  assert.equal(music.parts["music-start"].disabled, true);
  assert.equal(video.parts["video-hint"].textContent, "媒体作业进行中");
  assert.equal(video.parts["video-error"].textContent, "");
  videoPane.setHeavyAllowed(true);
  musicPane.setHeavyAllowed(true);
  assert.equal(video.parts["video-start"].disabled, false);
  assert.equal(music.parts["music-start"].disabled, false);
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

test("running 且日志无 step 行时进度条为不定态（F7/N3）", () => {
  const music = pane({ "music-caption": "民谣", "music-lyrics": "一二三", "music-duration": "10", "music-start": "" });
  const view = createMusicPane(music, {}).jobView;
  view.apply({ job_id: 6, status: "running", kind: "music", log: "loading model\n", elapsed_s: 4 });
  assert.equal(music.parts["job-progress"].hidden, false);
  assert.equal(music.parts["job-progress"].indeterminate, true);
  view.apply({ job_id: 6, status: "running", kind: "music", log: "step 2/8\n", elapsed_s: 9 });
  assert.equal(music.parts["job-progress"].indeterminate, false);
  assert.equal(music.parts["job-progress"].value, 25);
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
