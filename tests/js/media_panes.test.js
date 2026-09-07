import test from "node:test";
import assert from "node:assert/strict";
import { createVideoPane } from "../../desk/static/js/panes/video.js";
import { createMusicPane } from "../../desk/static/js/panes/music.js";

class Element {
  constructor(value = "", tagName = "div") {
    this.value = value; this.tagName = tagName; this.textContent = "";
    this.children = []; this.listeners = {}; this.hidden = false; this.controls = false;
    this.scrollTop = 0; this.scrollHeight = 40;
  }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { return this.listeners.click?.(); }
  get firstChild() { return this.children[0] || null; }
}

function pane(values) {
  const parts = Object.fromEntries(Object.entries(values).map(([name, value]) => [name, new Element(value)]));
  for (const name of ["job-status", "job-cancel", "job-log", "job-player", "job-error", "video-error", "music-error"]) parts[name] ??= new Element();
  const doc = { createElement: (tag) => new Element("", tag) };
  return { parts, ownerDocument: doc, querySelector(selector) { return parts[selector.match(/^\[data-([\w-]+)\]$/)?.[1]] || null; } };
}

function withFetch(responses, run) {
  const previous = globalThis.fetch; const calls = [];
  globalThis.fetch = async (url, options = {}) => { calls.push({ url, options }); return { ok: true, json: async () => responses.shift() }; };
  return Promise.resolve(run(calls)).finally(() => { globalThis.fetch = previous; });
}

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
  controller.jobView.apply({ status: "running", log: "one" });
  controller.jobView.apply({ status: "error", log: "two", error: { code: "media_busy", message: "忙" } });
  assert.equal(video.parts["job-log"].textContent, "onetwo");
  assert.equal(video.parts["job-log"].scrollTop, 40);
  assert.equal(video.parts["job-error"].children[0].textContent, "生成失败（media_busy）");
  assert.equal(video.parts["job-cancel"].hidden, true);
  await withFetch([{ status: "cancelled" }], async (calls) => { await video.parts["job-cancel"].click(); assert.equal(calls[0].url, "/api/media/cancel"); });
  assert.equal(video.parts["job-status"].textContent, "已取消");
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
  videoPane.jobView.apply({ status: "done", log: "two", output: "clip.mp4" });
  musicPane.jobView.apply({ status: "done", log: "four", output: "song.wav" });
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
  assert.equal(video.parts["video-error"].textContent, "媒体作业进行中");
  videoPane.setHeavyAllowed(true);
  musicPane.setHeavyAllowed(true);
  assert.equal(video.parts["video-start"].disabled, false);
  assert.equal(music.parts["music-start"].disabled, false);
});
