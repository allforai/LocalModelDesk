// 会话式视频页的控制逻辑（假 DOM）。真实浏览器里的布局与交互由 tests/e2e/test_video_flow.py 等覆盖。
import test from "node:test";
import assert from "node:assert/strict";
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
    timeline: "div", composer: "div", "session-new": "button", "session-list": "ul" };
  const names = ["mode", "prompt", "size", "frames", "steps", "seed", "start", "advanced", "advanced-error", "cost-note", "audio",
    "audio-row", "upload-status", "chip", "chip-text", "chip-clear", "composer", "assist", "first-area", "first-upload", "first-pick",
    "first-label", "first-preview", "last-area", "last", "last-label", "last-preview", "clear-last", "reference-area", "source",
    "source-label", "source-preview", "hint", "hint-text", "return", "error", "model", "timeline", "session-list", "session-new"];
  const parts = Object.fromEntries(names.map((name) => [name, new Element(tags[name] ?? "p")]));
  parts.mode.value = "text"; parts.steps.value = "16"; parts.seed.value = ""; parts.audio.checked = true;
  for (const name of ["first-upload", "last", "source"]) parts[name].type = "file";
  parts["first-upload"].accept = parts.last.accept = "image/png,image/jpeg,image/webp";
  parts.source.accept = "video/mp4,video/quicktime,video/webm";
  parts.advanced.className = "image-advanced video-advanced";
  parts.advanced.append(parts.size, parts.frames, parts.steps, parts.seed, parts["cost-note"], parts["audio-row"], parts["advanced-error"]);
  parts["audio-row"].append(parts.audio);
  parts.chip.append(parts["chip-text"], parts["chip-clear"]);
  parts.hint.append(parts["hint-text"], parts.return);
  parts["first-area"].append(parts["first-upload"], parts["first-pick"], parts["first-label"], parts["first-preview"]);
  parts["last-area"].append(parts.last, parts["last-label"], parts["clear-last"], parts["last-preview"]);
  parts["reference-area"].append(parts.source, parts["source-label"], parts["source-preview"]);
  parts.composer.append(parts.chip, parts.mode, parts["first-area"], parts["last-area"], parts["reference-area"], parts.prompt,
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
// 视频页读图片会话（首帧说明、失效检查）：在假后端外面接一层。
function serveImages(backend, sessions) {
  const inner = backend.fetch;
  globalThis.fetch = async (url, options = {}) => {
    const match = url.match(/^\/api\/media-sessions\/image\/(\w+)$/);
    if (!match) return inner(url, options);
    const found = sessions.find((s) => s.id === match[1]);
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
