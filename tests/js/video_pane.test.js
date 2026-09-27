// 会话式视频页的控制逻辑（假 DOM）。真实浏览器里的布局与交互由 tests/e2e/test_video_flow.py 等覆盖。
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createVideoPane } from "../../desk/static/js/panes/video.js";
import { Element, button, find, findAll, flush, mainFlowText, withBackend } from "./support/fake_dom.js";

// 浏览器的 FileReader：api.uploadMediaInput 用它把文件读成 base64。
globalThis.FileReader ??= class {
  readAsDataURL(file) {
    file.arrayBuffer().then((buffer) => {
      this.result = `data:${file.type};base64,${Buffer.from(buffer).toString("base64")}`;
      this.onload();
    });
  }
};

// 按 index.html 里 #pane-video 的 data 名建元素（V-21、V-22）。
function makeVideoPane(ctx = {}) {
  const tags = { mode: "select", prompt: "textarea", size: "select", frames: "select", steps: "input", seed: "input", start: "button",
    advanced: "details", audio: "input", "audio-row": "label", "first-upload": "input", "first-pick": "button", last: "input",
    "clear-last": "button", source: "input", "chip-clear": "button", chip: "div", assist: "div", return: "button",
    "ref-image-upload": "input", "ref-image-pick": "button", "song-pick": "button", "audio-start": "input",
    timeline: "div", composer: "div", "session-new": "button", "session-list": "ul" };
  const names = ["mode", "prompt", "size", "frames", "steps", "seed", "start", "advanced", "advanced-error", "cost-note", "audio",
    "audio-row", "upload-status", "chip", "chip-text", "chip-clear", "composer", "assist", "first-area", "first-upload", "first-pick",
    "first-label", "first-preview", "last-area", "last", "last-label", "last-preview", "clear-last", "reference-area", "source",
    "source-label", "source-preview", "music-area", "ref-image-upload", "ref-image-pick", "ref-image-label", "ref-image-preview",
    "song-pick", "song-label", "song-preview", "audio-start",
    "hint", "hint-text", "return", "error", "model", "timeline", "session-list", "session-new"];
  const parts = Object.fromEntries(names.map((name) => [name, new Element(tags[name] ?? "p")]));
  parts.mode.value = "text"; parts.steps.value = "16"; parts.seed.value = ""; parts.audio.checked = true;
  for (const name of ["first-upload", "last", "source", "ref-image-upload"]) parts[name].type = "file";
  parts["first-upload"].accept = parts.last.accept = parts["ref-image-upload"].accept = "image/png,image/jpeg,image/webp";
  parts["audio-start"].value = "0";
  parts.source.accept = "video/mp4,video/quicktime,video/webm";
  parts.advanced.className = "image-advanced video-advanced";
  parts.advanced.append(parts.size, parts.frames, parts.steps, parts.seed, parts["cost-note"], parts["audio-row"], parts["advanced-error"]);
  parts["audio-row"].append(parts.audio);
  parts.chip.append(parts["chip-text"], parts["chip-clear"]);
  parts.hint.append(parts["hint-text"], parts.return);
  parts["first-area"].append(parts["first-upload"], parts["first-pick"], parts["first-label"], parts["first-preview"]);
  parts["last-area"].append(parts.last, parts["last-label"], parts["clear-last"], parts["last-preview"]);
  parts["reference-area"].append(parts.source, parts["source-label"], parts["source-preview"]);
  parts["music-area"].append(parts["ref-image-upload"], parts["ref-image-pick"], parts["ref-image-label"], parts["ref-image-preview"],
    parts["song-pick"], parts["song-label"], parts["song-preview"], parts["audio-start"]);
  parts.composer.append(parts.chip, parts.mode, parts["first-area"], parts["last-area"], parts["reference-area"], parts["music-area"], parts.prompt,
    parts.start, parts.assist, parts.advanced, parts["upload-status"], parts.hint, parts.error);
  const main = new Element("div");
  main.append(parts.model, parts.timeline, parts.composer);
  const root = new Element("section");
  root.append(parts["session-new"], parts["session-list"], main);
  const doc = { body: new Element("body"), createElement: (tag) => new Element(tag) };
  root.ownerDocument = doc;
  root.querySelector = (selector) => parts[selector.match(/^\[data-video-([\w-]+)\]$/)?.[1]] ?? null;
  const pane = createVideoPane(root, { confirm: async () => true, ...ctx });
  return { root, parts, pane, ready() {
    pane.setHeavyAllowed(true); pane.setRuntimeStatus({ present: true }); pane.setModelStatus({ state: "present" });
  } };
}

const cards = (parts) => findAll(parts.timeline, (n) => "attemptId" in n.dataset);
const done = (id, extra = {}) => ({ id, job_id: 0, ts: "2026-09-27T09:00:00", status: "done", output: `${id}.mp4`, error: null,
  params: { prompt: `提示${id}`, width: 512, height: 288, frames: 73, steps: 16, seed: 11 }, refs: {}, ...extra });
const videoCalls = (backend) => backend.calls.filter((c) => c.url === "/api/media/video");
const uploadCalls = (backend) => backend.calls.filter((c) => c.url === "/api/media/inputs");
const png = (name = "cat.png") => new File([new Uint8Array([137, 80, 78, 71])], name, { type: "image/png" });
async function choose(input, file) {
  input.files = [file];
  await input.dispatch("change");
}

// 图片会话「橘猫」：第 3 次（a3）是可选的图，文件在或不在由 missing 决定。
function imageSession({ missing = false } = {}) {
  const attempt = (id, extra = {}) => ({ id, status: "done", output: `${id}.png`, params: { prompt: "猫" }, ...extra });
  return { id: "img1", title: "橘猫", attempts: [attempt("i1"), attempt("i2"), attempt("i3", missing ? { output_missing: true } : {})] };
}
const pick = { ref: { kind: "image", session_id: "img1", attempt_id: "i3" }, title: "橘猫", index: 2 };
// 视频页读图片会话（首帧说明、失效检查）与音乐会话（配乐说明）：在假后端外面接一层。
// fail：读取时回 failStatus（默认 500，网络/服务瞬时错误）的 "kind/session_id" 集合（issue #19）。
function serveImages(backend, sessions, music = [], fail = new Set(), failStatus = 500) {
  const inner = backend.fetch;
  globalThis.fetch = async (url, options = {}) => {
    const match = url.match(/^\/api\/media-sessions\/(image|music)\/(\w+)$/);
    if (!match) return inner(url, options);
    if (fail.has(`${match[1]}/${match[2]}`)) return { ok: false, status: failStatus, statusText: "", json: async () => ({ error: "服务出错" }) };
    const found = (match[1] === "image" ? sessions : music).find((s) => s.id === match[2]);
    return found ? { ok: true, status: 200, json: async () => structuredClone(found) }
      : { ok: false, status: 404, statusText: "", json: async () => ({ error: "会话不存在" }) };
  };
}

test("文生：请求带当前会话，不带 mode 与空种子", async () => {
  await withBackend("video", async (backend) => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    assert.match(parts.timeline.textContent, /还没有视频/);
    parts.prompt.value = "海边日落";
    await parts.start.click();
    const [call] = videoCalls(backend);
    assert.deepEqual(call.body, { session_id: backend.sessions[0].id, prompt: "海边日落", width: 512, height: 288, frames: 49, steps: 16 });
    assert.equal(parts.prompt.value, "海边日落");
    assert.equal(cards(parts)[0].dataset.attemptStatus, "running");
  });
});

test("方式切换显隐素材区与声音选项；图生缺首帧、参考缺视频时本地拦截", async () => {
  await withBackend("video", async (backend) => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    assert.equal(parts["first-area"].hidden, true);
    assert.equal(parts["reference-area"].hidden, true);
    assert.equal(parts["audio-row"].hidden, true);
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    assert.equal(parts["first-area"].hidden, false);
    assert.equal(parts["last-area"].hidden, false);
    assert.equal(parts["audio-row"].hidden, false);
    assert.equal(parts["first-label"].textContent, "未选择");
    parts.prompt.value = "猫跳起来";
    await parts.start.click();
    assert.equal(parts.error.textContent, "请先选择首帧图片");
    parts.mode.value = "reference"; await parts.mode.dispatch("change");
    assert.equal(parts["first-area"].hidden, true);
    assert.equal(parts["reference-area"].hidden, false);
    await parts.start.click();
    assert.equal(parts.error.textContent, "请先选择参考视频");
    assert.equal(videoCalls(backend).length, 0);
  });
});

test("图生上传：选文件即预览；提交先上传再生成；「换个版本」沿用素材 id 不再上传", async () => {
  await withBackend("video", async (backend) => {
    const draws = [11, 99];
    const { parts, pane, ready } = makeVideoPane({ randomSeed: () => draws.shift() }); ready();
    await pane.refresh();
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    await choose(parts["first-upload"], png("cat.png"));
    assert.equal(parts["first-label"].textContent, "已选择：cat.png");
    assert.equal(parts["first-preview"].children[0].tagName, "img");
    parts.prompt.value = "猫跳起来";
    await parts.start.click();
    const order = backend.calls.filter((c) => c.url.startsWith("/api/media/")).map((c) => c.url);
    assert.deepEqual(order, ["/api/media/inputs", "/api/media/video"]);
    assert.deepEqual(videoCalls(backend)[0].body, { session_id: backend.sessions[0].id, prompt: "猫跳起来", width: 512, height: 288,
      frames: 49, steps: 16, mode: "image", first_frame: "in1.png", use_audio: true });
    assert.equal(parts["upload-status"].textContent, "");
    // 这一段跑完后，同一个来源再生成一次也不再上传
    const { session_id: _, ...recorded } = videoCalls(backend)[0].body;
    backend.finish("a1", { status: "done", output: "v1.mp4", params: { ...recorded, seed: 11 } });
    await pane.refresh();
    await parts.start.click();
    assert.equal(uploadCalls(backend).length, 1);
    assert.equal(videoCalls(backend)[1].body.first_frame, "in1.png");
    backend.finish("a2", { status: "done", output: "v2.mp4", params: { ...recorded, seed: 5 } });
    await pane.refresh();
    await cards(parts)[0].click();
    await button(cards(parts)[0], "换个版本").click();
    await flush();
    const again = videoCalls(backend)[2].body;
    assert.equal(again.first_frame, "in1.png");
    assert.equal(again.mode, "image");
    assert.notEqual(again.seed, 11);
    assert.equal(uploadCalls(backend).length, 1, "换个版本不再上传");
  });
});

test("从图片会话选首帧：说明带标题与序号，提交带 refs.first_frame、不带 first_frame", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [imageSession()]);
    let opened = 0;
    const { parts, pane, ready } = makeVideoPane({ pickImage: async () => { opened += 1; return pick; } }); ready();
    await pane.refresh();
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    await parts["first-pick"].click();
    await flush();
    assert.equal(opened, 1);
    assert.equal(parts["first-label"].textContent, "首帧：图片会话「橘猫」第 3 次");
    assert.equal(parts["first-preview"].children[0].src, "/api/outputs/i3.png");
    parts.prompt.value = "猫转头";
    await parts.start.click();
    const [call] = videoCalls(backend);
    assert.deepEqual(call.body.refs, { first_frame: pick.ref });
    assert.equal(call.body.mode, "image");
    assert.equal("first_frame" in call.body, false);
    assert.equal(uploadCalls(backend).length, 0);
  });
});

test("接着往下生：提示词清空、方式锁图生、首帧说明；提交带 continues 不带 mode；点 × 解锁", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1", { params: { prompt: "第一段", width: 768, height: 448, frames: 124, steps: 20, seed: 3 } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    parts.prompt.value = "草稿"; parts.seed.value = "9";
    await button(cards(parts)[0], "接着往下生").click();
    assert.equal(parts.prompt.value, "");
    assert.equal(parts.seed.value, "");
    assert.equal(parts.size.value, "768x448");
    assert.equal(parts.frames.value, "124");
    assert.equal(parts.steps.value, "20");
    assert.equal(parts.mode.value, "image");
    assert.equal(parts.mode.disabled, true);
    assert.equal(parts["first-upload"].disabled, true);
    assert.equal(parts["first-pick"].disabled, true);
    assert.equal(parts["first-label"].textContent, "接在第 1 次后面（用它的最后一帧）");
    assert.equal(parts["chip-text"].textContent, "接在第 1 次后面");
    assert.ok(parts.prompt.focused > 0);
    parts.prompt.value = "第二段";
    await parts.start.click();
    const body = videoCalls(backend)[0].body;
    assert.equal(body.continues, "a1");
    assert.equal("mode" in body, false);
    assert.equal("first_frame" in body, false);
    // 生成后续写来源清空，方式解锁
    assert.equal(parts.chip.hidden, true);
    assert.equal(parts.mode.disabled, false);
    assert.equal(parts["first-label"].textContent, "未选择");

    await pane.refresh();
    await cards(parts)[0].click();
    await button(cards(parts)[0], "接着往下生").click();
    assert.equal(parts.mode.disabled, true);
    await parts["chip-clear"].click();
    assert.equal(parts.chip.hidden, true);
    assert.equal(parts.mode.disabled, false);
    assert.equal(parts["first-label"].textContent, "未选择");
  });
});

test("续写目标文件不在：提示条改为不能接着往下生，「生成视频」禁用", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1")]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await button(cards(parts)[0], "接着往下生").click();
    backend.finish("a1", { output_missing: true });
    await pane.refresh();
    assert.equal(parts["chip-text"].textContent, "第 1 次的文件已不在，不能接着往下生");
    assert.equal(parts.start.disabled, true);
  });
});

test("引用的图片已不在：「在这段基础上改」清空首帧来源并说明，生成报「请先选择首帧图片」", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [imageSession({ missing: true })]);
    backend.addSession("片", [done("a1", { params: { prompt: "猫", width: 512, height: 288, frames: 73, steps: 16, seed: 4,
      mode: "image", use_audio: true, first_frame: null }, refs: { first_frame: pick.ref } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await flush();
    assert.match(cards(parts)[0].textContent, /首帧：图片会话「橘猫」第 3 次/);
    await button(cards(parts)[0], "在这段基础上改").click();
    await flush();
    assert.equal(parts.mode.value, "image");
    assert.equal(parts.prompt.value, "猫");
    assert.equal(parts.frames.value, "73");
    assert.equal(parts.seed.value, "4");
    assert.equal(parts["chip-text"].textContent, "沿用第 1 次");
    assert.equal(parts["first-label"].textContent, "引用的图片已不在");
    await parts.start.click();
    assert.equal(parts.error.textContent, "请先选择首帧图片");
    assert.equal(videoCalls(backend).length, 0);
  });
});

test("引用查询网络失败（500）：「在这段基础上改」不清空首帧来源，只在错误行提示稍后重试（issue #19）", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [imageSession()], [], new Set(["image/img1"]));
    backend.addSession("片", [done("a1", { params: { prompt: "猫", width: 512, height: 288, frames: 73, steps: 16, seed: 4,
      mode: "image", use_audio: true, first_frame: null }, refs: { first_frame: pick.ref } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await flush();
    await button(cards(parts)[0], "在这段基础上改").click();
    await flush();
    assert.notEqual(parts["first-label"].textContent, "引用的图片已不在", "网络失败不当作已不在");
    assert.equal(parts.error.textContent, "暂时读不到图片会话，请稍后重试");
  });
});

test("引用的图片会话确实已被删除（404）：仍清空首帧来源并显示「引用的图片已不在」（原行为，issue #19）", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [], []); // 没有 img1 这个图片会话：真的 404
    backend.addSession("片", [done("a1", { params: { prompt: "猫", width: 512, height: 288, frames: 73, steps: 16, seed: 4,
      mode: "image", use_audio: true, first_frame: null }, refs: { first_frame: pick.ref } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await button(cards(parts)[0], "在这段基础上改").click();
    await flush();
    assert.equal(parts["first-label"].textContent, "引用的图片已不在");
    await parts.start.click();
    assert.equal(parts.error.textContent, "请先选择首帧图片");
  });
});

test("引用的图片会话已损坏（400）：当作已不在处理，清空首帧来源并显示「引用的图片已不在」（final review Minor 1）", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [imageSession()], [], new Set(["image/img1"]), 400);
    backend.addSession("片", [done("a1", { params: { prompt: "猫", width: 512, height: 288, frames: 73, steps: 16, seed: 4,
      mode: "image", use_audio: true, first_frame: null }, refs: { first_frame: pick.ref } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await flush();
    await button(cards(parts)[0], "在这段基础上改").click();
    await flush();
    assert.equal(parts["first-label"].textContent, "引用的图片已不在", "损坏的引用应定性为已不在，不是暂时读不到");
    await parts.start.click();
    assert.equal(parts.error.textContent, "请先选择首帧图片");
  });
});

test("配乐参考——歌引用查询网络失败（500）：不清空歌来源，只提示稍后重试；确实 404 时清空并说明（issue #19）", async () => {
  for (const fail of [true, false]) {
    await withBackend("video", async (backend) => {
      const musicSessions = fail ? [musicSession()] : [];
      serveImages(backend, [imageSession()], musicSessions, fail ? new Set(["music/m1"]) : new Set());
      backend.addSession("片", [done("a1", { params: { prompt: "奔跑", width: 512, height: 288, frames: 73, steps: 16, seed: 4,
        mode: "music_ref", use_audio: true, audio_start: 12, ref_image: null }, refs: { ref_image: pick.ref, ref_audio: song.ref } })]);
      const { parts, pane, ready } = makeVideoPane(); ready();
      await pane.refresh();
      await button(cards(parts)[0], "在这段基础上改").click();
      await flush();
      if (fail) {
        assert.notEqual(parts["song-label"].textContent, "引用的歌已不在", "网络失败不当作已不在");
        assert.equal(parts.error.textContent, "暂时读不到音乐会话，请稍后重试");
      } else {
        assert.equal(parts["song-label"].textContent, "引用的歌已不在");
      }
    });
  }
});

test("「在这段基础上改」一个续写段：首帧说明为续写、方式锁定，生成仍接在原位置", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1"), done("a2", { continues: "a1", params: { ...done("a2").params, mode: "image", use_audio: true } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await button(cards(parts)[1], "在这段基础上改").click();
    assert.equal(parts["chip-text"].textContent, "沿用第 2 次");
    assert.equal(parts["first-label"].textContent, "接在第 1 次后面（用它的最后一帧）");
    assert.equal(parts.mode.disabled, true);
    await parts.start.click();
    const body = videoCalls(backend)[0].body;
    assert.equal(body.continues, "a1");
    assert.equal(body.seed, 11);
  });
});

test("「在这段基础上改」一个续写段后，它接的前段文件不在：提示条改为不能接着往下生，「生成视频」禁用（issue #19）", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1"), done("a2", { continues: "a1", params: { ...done("a2").params, mode: "image", use_audio: true } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await button(cards(parts)[1], "在这段基础上改").click();
    assert.equal(parts["chip-text"].textContent, "沿用第 2 次");
    backend.finish("a1", { output_missing: true });
    await pane.refresh();
    assert.equal(parts["chip-text"].textContent, "第 1 次的文件已不在，不能接着往下生");
    assert.equal(parts.start.disabled, true);
  });
});

test("上一条之后改种子：video 不受 music 那个死路影响，方式仍锁定为续写，「生成视频」仍禁用（final review Important 1 一并确认）", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1"), done("a2", { continues: "a1", params: { ...done("a2").params, mode: "image", use_audio: true } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await button(cards(parts)[1], "在这段基础上改").click();
    backend.finish("a1", { output_missing: true });
    await pane.refresh();
    assert.equal(parts.start.disabled, true);
    parts.seed.value = "999"; await parts.seed.dispatch("input");
    // video 的 refine 续写段回填时首帧来源本身就是 {type:"continue"}（sourceOf），chip 因此恒可见，
    // 改种子不会像 music 那样隐藏提示条，所以这里仍应保持禁用。
    assert.equal(parts.chip.hidden, false, "video 续写提示条不因改种子隐藏");
    assert.equal(parts.start.disabled, true, "仍会带 continues，禁用是对的，不是死路");
  });
});

test("图片页跳过来时视频页还没打开过：先加载会话，再填首帧，不被覆盖", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [imageSession()]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    const refreshing = pane.refresh(); // main.js 里 showTab("video") 先触发一次
    await pane.useFirstFrame(pick);
    await refreshing;
    await flush();
    assert.equal(backend.sessions.length, 1, "自动建了会话");
    assert.match(parts.timeline.textContent, /还没有视频/);
    assert.equal(parts.mode.value, "image");
    assert.equal(parts["first-area"].hidden, false);
    assert.equal(parts["first-label"].textContent, "首帧：图片会话「橘猫」第 3 次");
    assert.ok(parts.prompt.focused > 0);
  });
});

test("有成片的卡片「成片」「只看这一段」切换；成片没拼成可「重新拼接」", async () => {
  await withBackend("video", async (backend) => {
    const failed = { code: "join_failed", message: "ffmpeg 出错" };
    backend.addSession("片", [done("a1"), done("a2", { continues: "a1", joined_output: "j2.mp4" }),
      done("a3", { continues: "a2", joined_error: failed })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    let card = cards(parts)[2];
    assert.match(card.textContent, /这一段生成好了，但成片没拼成：ffmpeg 出错/);
    await button(card, "重新拼接").click();
    await flush();
    const compose = backend.calls.find((c) => c.url === "/api/media/compose");
    assert.deepEqual(compose.body, { kind: "video", session_id: backend.sessions[0].id, parts: ["a1", "a2", "a3"] });

    await pane.refresh();
    await cards(parts)[1].click();
    card = cards(parts)[1];
    const video = find(card, (n) => n.tagName === "video");
    assert.equal(video.src, "/api/outputs/j2.mp4");
    assert.equal(video.getAttribute("preload"), "metadata");
    const group = find(card, (n) => n.attrs?.role === "radiogroup");
    await button(group, "只看这一段").click();
    assert.equal(video.src, "/api/outputs/a2.mp4");
    assert.match(card.textContent, /第 2 次 · 09:00 · 接第 1 次/);
    assert.match(card.textContent, /图生|文生/);
    assert.match(card.textContent, /512×288 · 约 3 秒 · 16 步/);
  });
});

test("合成尝试只有「接着往下生」；没生成好的尝试不能接着往下生；视频报错变成文件不在", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1"), done("a2"),
      { id: "a3", ts: "2026-09-27T09:05:00", status: "done", op: "compose", params: { parts: ["a1", "a2"] }, output: "c3.mp4", error: null },
      { ...done("a4"), status: "failed", output: null, error: { code: "exit_nonzero", message: "x" } }]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await cards(parts)[2].click();
    let card = cards(parts)[2];
    assert.match(card.textContent, /合成：第 1、2 次/);
    assert.equal(button(card, "在这段基础上改"), null);
    assert.equal(button(card, "换个版本"), null);
    parts.size.value = "1024x576"; parts.prompt.value = "旧";
    await button(card, "接着往下生").click();
    assert.equal(parts.size.value, "1024x576");
    assert.equal(parts["chip-text"].textContent, "接在第 3 次后面");

    await cards(parts)[3].click();
    card = cards(parts)[3];
    assert.equal(button(card, "接着往下生").disabled, true);
    assert.match(card.textContent, /这一段没有生成好，不能接着往下生/);
    assert.equal(find(card, (n) => n.tagName === "video"), null);

    await cards(parts)[0].click();
    await find(cards(parts)[0], (n) => n.tagName === "video").dispatch("error");
    assert.match(cards(parts)[0].textContent, /视频文件已不在/);
    assert.ok(find(cards(parts)[0], (n) => n.classList?.contains?.("icon-video")), "文件不在的视频卡片应显示视频图标而非图片图标");
  });
});

test("挑选模式：卡片只做勾选，不显示动作", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1"), done("a2")]);
    const { root, parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await find(root, (n) => "videoComposeStart" in n.dataset).click();
    const card = cards(parts)[1];
    assert.equal(button(card, "在这段基础上改"), null);
    assert.equal(button(card, "接着往下生"), null);
    await find(cards(parts)[0], (n) => n.tagName === "input" && n.type === "checkbox").dispatch("change");
    await cards(parts)[1].click();
    await button(find(root, (n) => "videoComposeBar" in n.dataset), "合成（2 段）").click();
    await flush();
    assert.deepEqual(backend.calls.find((c) => c.url === "/api/media/compose").body.parts, ["a1", "a2"]);
  });
});

test("素材库回填：原会话不在时按字段回填，提示条「沿用素材库里这段」", async () => {
  await withBackend("video", async (backend) => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await pane.applyFill({ pane: "video", session_id: "gone", attempt_id: "x",
      fields: { prompt: "旧提示", width: 768, height: 448, frames: 57, steps: 20, seed: 7 } });
    assert.equal(parts.prompt.value, "旧提示");
    assert.equal(parts.size.value, "768x448");
    assert.equal(parts.frames.value, "49");
    assert.equal(parts.steps.value, "20");
    assert.equal(parts.seed.value, "7");
    assert.equal(parts["chip-text"].textContent, "沿用素材库里这段");
  });
});

test("素材库回填：music_ref 条目原会话不在时，参考图与起始秒也按字段回填", async () => {
  await withBackend("video", async (backend) => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await pane.applyFill({ pane: "video", session_id: "gone", attempt_id: "x",
      fields: { prompt: "旧提示", width: 768, height: 448, frames: 57, steps: 20, seed: 7,
        mode: "music_ref", ref_image: "in1.png", audio_start: 12 } });
    assert.equal(parts.mode.value, "music_ref");
    assert.equal(parts["ref-image-label"].textContent, "已选择：之前上传的图片");
    assert.equal(parts["audio-start"].value, "12");
  });
});

test("耗时提示随画幅与时长变化；AI 帮写按当前方式写回提示词", async () => {
  await withBackend("video", async (backend) => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    assert.equal(parts["cost-note"].textContent, "");
    parts.size.value = "1024x576"; parts.frames.value = "243";
    await parts.frames.dispatch("change");
    assert.match(parts["cost-note"].textContent, /非常慢/);
    parts.size.value = "512x288"; await parts.size.dispatch("change");
    assert.equal(parts["cost-note"].textContent, "");

    const [lucky] = parts.assist.children;
    pane.setAssistAvailable(true, "");
    parts.mode.value = "image"; await parts.mode.dispatch("change");
    const previous = globalThis.fetch;
    let sent = null;
    globalThis.fetch = async (url, options) => {
      if (url !== "/api/llm/prompt-assist") return previous(url, options);
      sent = JSON.parse(options.body);
      return { ok: true, status: 200, json: async () => ({ task: "video", action: "lucky", text: "雨夜街角" }) };
    };
    await lucky.click();
    await flush();
    assert.equal(sent.task, "video");
    assert.equal(sent.mode, "image");
    assert.equal(parts.prompt.value, "雨夜街角");
  });
});

test("主流程文字不含「种子」", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1"), done("a2", { continues: "a1" })]);
    const { root, parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await button(cards(parts)[1], "在这段基础上改").click();
    assert.ok(!mainFlowText(root, /video-advanced|attempt-advanced/).includes("种子"));
  });
});

test("回填之前上传的素材：说明写「之前上传的…」，不露出素材 id", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1", { params: { ...done("a1").params, mode: "image", use_audio: true,
      first_frame: "f00d.png", last_frame: "beef.png" } }), done("a2", { params: { ...done("a2").params, mode: "reference",
      use_audio: false, ref_video: "cafe.mp4" } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await cards(parts)[0].click();
    await button(cards(parts)[0], "在这段基础上改").click();
    assert.equal(parts["first-label"].textContent, "已选择：之前上传的图片");
    assert.equal(parts["last-label"].textContent, "已选择：之前上传的图片");
    await parts.start.click();
    assert.equal(videoCalls(backend)[0].body.first_frame, "f00d.png");
    assert.equal(videoCalls(backend)[0].body.last_frame, "beef.png");
    assert.equal(uploadCalls(backend).length, 0);
    await pane.refresh();
    await cards(parts)[1].click();
    await button(cards(parts)[1], "在这段基础上改").click();
    assert.equal(parts["source-label"].textContent, "已选择：之前上传的视频");
    assert.equal(parts.audio.checked, false);
  });
});

test("内存可能不足：确认后带 force 重发；取消则不再发请求", async () => {
  for (const answer of [true, false]) {
    await withBackend("video", async (backend) => {
      const asked = [];
      const { parts, pane, ready } = makeVideoPane({ confirm: async (_doc, options) => { asked.push(options); return answer; } }); ready();
      await pane.refresh();
      backend.startResult = (body) => (body.force
        ? { ok: true, status: 200, json: async () => ({ job_id: 9, kind: "video", status: "running", session_id: body.session_id, attempt_id: "a9", log: "" }) }
        : { ok: false, status: 409, statusText: "", json: async () => ({ error: { code: "insufficient_memory", message: "内存可能不够" } }) });
      parts.prompt.value = "海边";
      await parts.start.click();
      await flush();
      assert.equal(asked.length, 1);
      assert.equal(asked[0].message, "内存可能不够");
      assert.equal(asked[0].confirmLabel, "仍要生成");
      const calls = videoCalls(backend);
      if (answer) {
        assert.equal(calls.length, 2);
        assert.equal(calls[1].body.force, true);
        assert.equal(calls[1].body.prompt, "海边");
        assert.equal(parts.error.textContent, "");
      } else {
        assert.equal(calls.length, 1, "取消后不再发第二次");
        assert.equal("force" in calls[0].body, false);
        assert.equal(parts.error.textContent, "");
      }
    });
  }
});

// 音乐会话「夏夜」：第 2 次（t2）是可选的歌，文件在或不在由 missing 决定。
function musicSession({ missing = false } = {}) {
  const attempt = (id, extra = {}) => ({ id, status: "done", output: `${id}.wav`, params: { caption: "轻快钢琴 夏夜海边" }, ...extra });
  return { id: "m1", title: "夏夜", attempts: [attempt("t1"), attempt("t2", missing ? { output_missing: true } : {})] };
}
const song = { ref: { kind: "music", session_id: "m1", attempt_id: "t2" }, title: "夏夜", index: 1, label: "轻快钢琴 夏夜海边" };
const soundtrackCalls = (backend) => backend.calls.filter((c) => c.url === "/api/media/soundtrack");

test("「配乐…」：选一首歌即提交配乐，新卡片被选中；挑选模式下没有这个按钮", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [], [musicSession()]);
    const titles = [];
    backend.addSession("片", [done("a1"), done("a2")]);
    const { root, parts, pane, ready } = makeVideoPane({ pickMusic: async (options) => { titles.push(options?.title); return song; } }); ready();
    await pane.refresh();
    await cards(parts)[0].click();
    await button(cards(parts)[0], "配乐…").click();
    await flush();
    assert.deepEqual(titles, ["选一首歌配到这段视频"]);
    const [call] = soundtrackCalls(backend);
    assert.deepEqual(call.body, { session_id: backend.sessions[0].id, source: "a1", refs: { soundtrack: song.ref } });
    const added = cards(parts)[2];
    assert.equal(added.dataset.attemptStatus, "running");
    assert.equal(added.getAttribute("aria-expanded"), "true");
    assert.equal(parts.error.textContent, "");

    backend.finish("a3", { status: "done", output: "s3.mp4" });
    await pane.refresh();
    await find(root, (n) => "videoComposeStart" in n.dataset).click();
    assert.equal(button(cards(parts)[1], "配乐…"), null);
  });
});

test("「配乐…」：有作业在跑时禁用；选择框取消不发请求；ffmpeg 缺失显示后端原话", async () => {
  await withBackend("video", async (backend) => {
    backend.addSession("片", [done("a1")]);
    let answer = null;
    const { parts, pane, ready } = makeVideoPane({ pickMusic: async () => answer }); ready();
    await pane.refresh();
    await button(cards(parts)[0], "配乐…").click();
    await flush();
    assert.equal(soundtrackCalls(backend).length, 0);
    answer = song;
    backend.soundtrackResult = () => ({ ok: false, status: 503, statusText: "",
      json: async () => ({ error: { code: "capability_missing", message: "需要 ffmpeg 才能拼接成片" } }) });
    await button(cards(parts)[0], "配乐…").click();
    await flush();
    assert.equal(parts.error.textContent, "需要 ffmpeg 才能拼接成片");
    pane.setHeavyAllowed(false, "已有作业在进行");
    const btn = button(cards(parts)[0], "配乐…");
    assert.equal(btn.disabled, true);
    assert.equal(btn.title, "已有作业在进行");
    const before = soundtrackCalls(backend).length;
    await btn.click();
    await flush();
    assert.equal(soundtrackCalls(backend).length, before, "禁用时点击不发请求");
  });
});

test("配乐卡片：标题带歌的风格描述摘要与基于第几次，动作只有「接着往下生」「配乐…」", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [], [musicSession()]);
    backend.addSession("片", [done("a1"), { id: "a2", ts: "2026-09-27T09:05:00", status: "done", op: "soundtrack",
      params: { source: "a1" }, refs: { soundtrack: song.ref }, output: "s2.mp4", error: null }]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    await flush();
    const card = cards(parts)[1];
    assert.match(card.textContent, /第 2 次 · 09:05 · 配乐：轻快钢琴 夏夜海边 · 基于第 1 次/);
    assert.equal(find(card, (n) => n.tagName === "video").src, "/api/outputs/s2.mp4");
    const labels = findAll(find(card, (n) => n.classList?.contains?.("attempt-actions")), (n) => n.tagName === "button").map((b) => b.textContent);
    assert.deepEqual(labels, ["接着往下生", "配乐…"]);
  });
});

test("配乐参考方式：显示参考图区、歌区、起始秒与实验说明，隐藏首帧/尾帧/参考视频区", async () => {
  await withBackend("video", async (backend) => {
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    assert.equal(parts["music-area"].hidden, true);
    parts.mode.value = "music_ref"; await parts.mode.dispatch("change");
    assert.equal(parts["music-area"].hidden, false);
    assert.equal(parts["first-area"].hidden, true);
    assert.equal(parts["last-area"].hidden, true);
    assert.equal(parts["reference-area"].hidden, true);
    assert.equal(parts["audio-row"].hidden, true, "配乐参考没有素材声音可用");
    assert.equal(parts["ref-image-label"].textContent, "未选择");
    assert.equal(parts["song-label"].textContent, "未选择");
    assert.equal(parts["audio-start"].value, "0");
    parts.prompt.value = "海边奔跑";
    await parts.start.click();
    assert.equal(parts.error.textContent, "请先选择参考图");
    await choose(parts["ref-image-upload"], png("style.png"));
    await parts.start.click();
    assert.equal(parts.error.textContent, "请先选择一首歌");
    assert.equal(videoCalls(backend).length, 0);
    assert.equal(uploadCalls(backend).length, 0);
  });
});

test("配乐参考提交：上传参考图先上传再生成；图片会话参考图带 refs.ref_image 不带 ref_image", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [imageSession()], [musicSession()]);
    const imageTitles = [];
    const { parts, pane, ready } = makeVideoPane({
      pickMusic: async () => song, pickImage: async (options) => { imageTitles.push(options?.title); return pick; } }); ready();
    await pane.refresh();
    parts.mode.value = "music_ref"; await parts.mode.dispatch("change");
    await choose(parts["ref-image-upload"], png("style.png"));
    assert.equal(parts["ref-image-label"].textContent, "已选择：style.png");
    await parts["song-pick"].click();
    await flush();
    assert.equal(parts["song-label"].textContent, "歌：轻快钢琴 夏夜海边");
    assert.equal(find(parts["song-preview"], (n) => n.tagName === "audio").src, "/api/outputs/t2.wav");
    parts.prompt.value = "海边奔跑";
    await parts.start.click();
    const order = backend.calls.filter((c) => c.url.startsWith("/api/media/")).map((c) => c.url);
    assert.deepEqual(order, ["/api/media/inputs", "/api/media/video"]);
    assert.deepEqual(videoCalls(backend)[0].body, { session_id: backend.sessions[0].id, prompt: "海边奔跑", width: 512, height: 288,
      frames: 49, steps: 16, mode: "music_ref", ref_image: "in1.png", audio_start: 0, refs: { ref_audio: song.ref } });

    await parts["ref-image-pick"].click();
    await flush();
    assert.deepEqual(imageTitles, ["从图片会话选参考图"]);
    assert.equal(parts["ref-image-label"].textContent, "参考图：图片会话「橘猫」第 3 次");
    parts["audio-start"].value = "7.5";
    backend.finish("a1", { status: "done", output: "v1.mp4" });
    await pane.refresh();
    await parts.start.click();
    const body = videoCalls(backend)[1].body;
    assert.deepEqual(body.refs, { ref_image: pick.ref, ref_audio: song.ref });
    assert.equal("ref_image" in body, false);
    assert.equal(body.audio_start, 7.5);
    assert.equal(uploadCalls(backend).length, 1);
  });
});

test("「在这段基础上改」配乐参考：回填参考图、歌与起始秒；歌已被删时说明并拦下提交；「换个版本」原样重发", async () => {
  for (const missing of [false, true]) {
    await withBackend("video", async (backend) => {
      serveImages(backend, [imageSession()], [musicSession({ missing })]);
      backend.addSession("片", [done("a1", { params: { prompt: "奔跑", width: 512, height: 288, frames: 73, steps: 16, seed: 4,
        mode: "music_ref", use_audio: true, audio_start: 12, ref_image: null }, refs: { ref_image: pick.ref, ref_audio: song.ref } })]);
      const { root, parts, pane, ready } = makeVideoPane({ randomSeed: () => 77 }); ready();
      await pane.refresh();
      await button(cards(parts)[0], "在这段基础上改").click();
      await flush();
      assert.equal(parts.mode.value, "music_ref");
      assert.equal(parts["music-area"].hidden, false);
      assert.equal(parts["audio-start"].value, "12");
      assert.equal(parts["ref-image-label"].textContent, "参考图：图片会话「橘猫」第 3 次");
      assert.ok(!mainFlowText(root, /video-advanced|attempt-advanced/).includes("种子"));
      if (missing) {
        assert.equal(parts["song-label"].textContent, "引用的歌已不在");
        await parts.start.click();
        assert.equal(parts.error.textContent, "请先选择一首歌");
        assert.equal(videoCalls(backend).length, 0);
      } else {
        assert.equal(parts["song-label"].textContent, "歌：轻快钢琴 夏夜海边");
        await button(cards(parts)[0], "换个版本").click();
        await flush();
        assert.deepEqual(videoCalls(backend)[0].body, { session_id: backend.sessions[0].id, prompt: "奔跑", width: 512, height: 288,
          frames: 73, steps: 16, seed: 77, mode: "music_ref", audio_start: 12,
          refs: { ref_image: pick.ref, ref_audio: song.ref } });
      }
    });
  }
});

test("配乐参考：上传参考图与从图片会话选互相替换；引用的参考图已不在时说明", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [imageSession({ missing: true })], [musicSession()]);
    const { parts, pane, ready } = makeVideoPane({ pickImage: async () => pick }); ready();
    await pane.refresh();
    parts.mode.value = "music_ref"; await parts.mode.dispatch("change");
    await parts["ref-image-pick"].click();
    await flush();
    assert.equal(parts["ref-image-label"].textContent, "引用的图片已不在");
    await choose(parts["ref-image-upload"], png("b.png"));
    assert.equal(parts["ref-image-label"].textContent, "已选择：b.png");
  });
});

test("配乐参考：起始秒不是不小于 0 的数时本地拦截", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [imageSession()], [musicSession()]);
    const { parts, pane, ready } = makeVideoPane({ pickMusic: async () => song, pickImage: async () => pick }); ready();
    await pane.refresh();
    parts.mode.value = "music_ref"; await parts.mode.dispatch("change");
    await parts["ref-image-pick"].click();
    await parts["song-pick"].click();
    await flush();
    parts.prompt.value = "奔跑";
    parts["audio-start"].value = "-1";
    await parts.start.click();
    assert.equal(parts.error.textContent, "起始秒数须为不小于 0 的数");
    assert.equal(videoCalls(backend).length, 0);
  });
});

test("index.html：配乐参考区在可滚动素材区内，带「从第几秒开始」与实验说明（S-32、S-35）", () => {
  const html = readFileSync(new URL("../../desk/static/index.html", import.meta.url), "utf8");
  const materials = html.slice(html.indexOf('<div class="video-materials">'), html.indexOf('<div class="image-input-row">'));
  const area = materials.slice(materials.indexOf("data-video-music-area"));
  assert.ok(materials.includes("data-video-music-area"), "配乐参考区在 .video-materials 内");
  assert.ok(materials.includes('<option value="music_ref">配乐参考（实验性）</option>'));
  assert.ok(area.includes("从第几秒开始"));
  assert.ok(area.includes("实验性：画面不保证跟随音乐节奏；参考图只影响画面风格，不作为第一帧。截取与视频等长、2–15 秒的一段音乐。"));
});

// 配乐参考已选好参考图与歌，提示词写好；返回 {parts, pane}。
async function readyMusicRef(backend, ctx = {}) {
  serveImages(backend, [imageSession()], [musicSession()]);
  const made = makeVideoPane({ pickMusic: async () => song, pickImage: async () => pick, ...ctx }); made.ready();
  await made.pane.refresh();
  made.parts.mode.value = "music_ref"; await made.parts.mode.dispatch("change");
  await made.parts["ref-image-pick"].click();
  await made.parts["song-pick"].click();
  await flush();
  made.parts.prompt.value = "奔跑";
  return made;
}
const refusal = (status, code, message) => () => ({ ok: false, status, statusText: "", json: async () => ({ error: { code, message } }) });

test("配乐参考被后端拒绝：显示后端原话（起始秒超出、截取失败、缺 ffmpeg）", async () => {
  for (const [status, code, message] of [[400, "invalid_params", "这首歌从第 30 秒起不足 2 秒"],
    [500, "audio_clip_failed", "没能截取这段音乐"], [503, "capability_missing", "需要 ffmpeg 才能拼接成片"]]) {
    await withBackend("video", async (backend) => {
      const { parts } = await readyMusicRef(backend);
      backend.startResult = refusal(status, code, message);
      await parts.start.click();
      await flush();
      assert.equal(parts.error.textContent, message);
    });
  }
});

test("配乐参考「换个版本」时引用已不在：显示后端原话", async () => {
  await withBackend("video", async (backend) => {
    serveImages(backend, [imageSession()], [musicSession()]);
    backend.addSession("片", [done("a1", { params: { ...done("a1").params, mode: "music_ref", audio_start: 0, ref_image: "r.png" },
      refs: { ref_audio: song.ref } })]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    backend.startResult = refusal(400, "ref_missing", "引用的音乐已不在");
    await button(cards(parts)[0], "换个版本").click();
    await flush();
    assert.equal(videoCalls(backend).length, 1);
    assert.equal(parts.error.textContent, "引用的音乐已不在");
  });
});

// ---------- issue #18 ----------
test("成片播放出错退回本段、不标文件不在；分段切换可用方向键；切换会话后 brokenIds 清空", async () => {
  await withBackend("video", async (backend) => {
    const a = backend.addSession("甲", [done("a1"), done("a2", { continues: "a1", joined_output: "j2.mp4" })]);
    const b = backend.addSession("乙", [done("b1")]);
    const { parts, pane, ready } = makeVideoPane(); ready();
    await pane.refresh();
    const item = (id) => findAll(parts["session-list"], (n) => n.dataset?.sessionId === id)[0];
    const cardOf = (id) => cards(parts).find((n) => n.dataset.attemptId === id);
    await item(a.id).click(); await flush();

    let video = find(cardOf("a2"), (n) => n.tagName === "video");
    const group = find(cardOf("a2"), (n) => n.attrs?.role === "radiogroup");
    const whole = button(group, "成片"); const part = button(group, "只看这一段");
    await whole.dispatch("keydown", { key: "ArrowRight" });
    assert.equal(part.attrs["aria-checked"], "true");
    assert.equal(part.focused, 1);
    assert.equal(video.src, "/api/outputs/a2.mp4");
    await part.dispatch("keydown", { key: "ArrowLeft" });
    assert.equal(whole.attrs["aria-checked"], "true");
    assert.equal(video.src, "/api/outputs/j2.mp4");

    await video.dispatch("error");
    assert.equal(video.src, "/api/outputs/a2.mp4");
    assert.equal(find(cardOf("a2"), (n) => n.attrs?.role === "radiogroup"), null);
    assert.doesNotMatch(cardOf("a2").textContent, /视频文件已不在/);
    assert.equal(button(cardOf("a2"), "接着往下生").disabled, false);
    await video.dispatch("error");
    assert.match(cardOf("a2").textContent, /视频文件已不在/);

    await item(b.id).click(); await flush();
    await item(a.id).click(); await flush();
    await pane.refresh();
    const next = button(cardOf("a2"), "接着往下生");
    assert.equal(next.disabled, false);
    await next.click();
    assert.equal(parts["chip-text"].textContent, "接在第 2 次后面");
  });
});
