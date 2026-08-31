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
  videoPane.fill({ prompt: "夜景", width: 1024, height: 576, frames: 57, steps: 20 });
  musicPane.fill({ caption: "爵士", lyrics: "la", duration: 75 });
  assert.equal(video.parts["video-size"].value, "1024x576");
  assert.equal(music.parts["music-duration"].value, "75");
  await withFetch([{ job_id: 7, status: "running", kind: "video", log: "started" }, { job_id: 8, status: "done", kind: "music", output: "song.wav" }], async (calls) => {
    await video.parts["video-start"].click(); await music.parts["music-start"].click();
    assert.deepEqual(calls.map(({ url, options }) => [url, JSON.parse(options.body)]), [
      ["/api/media/video", { prompt: "夜景", width: 1024, height: 576, frames: 57, steps: 20 }],
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
  assert.equal(video.parts["job-error"].textContent, "media_busy：忙");
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
