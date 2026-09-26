// 会话式音乐页的控制逻辑（假 DOM）。真实浏览器里的布局与交互由 tests/e2e/test_music_flow.py 覆盖。
import test from "node:test";
import assert from "node:assert/strict";
import { createMusicPane } from "../../desk/static/js/panes/music.js";
import { Element, button, find, findAll, flush, mainFlowText, withBackend } from "./support/fake_dom.js";

const SEED = "种子";

// 按 index.html 里 #pane-music 的 data 名建元素（M-21）。
function makeMusicPane(ctx = {}) {
  const tags = { caption: "input", lyrics: "textarea", duration: "input", seed: "input", start: "button",
    advanced: "details", timeline: "div", composer: "div", "session-new": "button", "session-list": "ul",
    chip: "div", "chip-clear": "button", assist: "div", return: "button" };
  const names = ["caption", "lyrics", "duration", "seed", "start", "advanced", "advanced-error", "chip", "chip-text", "chip-clear",
    "assist", "hint", "hint-text", "return", "error", "model", "timeline", "session-list", "session-new", "composer"];
  const parts = Object.fromEntries(names.map((name) => [name, new Element(tags[name] ?? "p")]));
  parts.duration.value = "60"; parts.seed.value = "";
  parts.advanced.className = "image-advanced music-advanced";
  parts.advanced.append(parts.duration, parts.seed, parts["advanced-error"]);
  parts.chip.append(parts["chip-text"], parts["chip-clear"]);
  parts.hint.append(parts["hint-text"], parts.return);
  parts.composer.append(parts.chip, parts.caption, parts.lyrics, parts.start, parts.assist, parts.advanced, parts.hint, parts.error);
  const main = new Element("div");
  main.append(parts.model, parts.timeline, parts.composer);
  const root = new Element("section");
  root.append(parts["session-new"], parts["session-list"], main);
  const doc = { body: new Element("body"), createElement: (tag) => new Element(tag) };
  root.ownerDocument = doc;
  root.querySelector = (selector) => parts[selector.match(/^\[data-music-([\w-]+)\]$/)?.[1]] ?? null;
  const pane = createMusicPane(root, { confirm: async () => true, ...ctx });
  return { root, parts, pane, ready() {
    pane.setHeavyAllowed(true); pane.setRuntimeStatus({ present: true }); pane.setModelStatus({ state: "present" });
  } };
}

const cards = (parts) => findAll(parts.timeline, (n) => "attemptId" in n.dataset);
const done = (id, extra = {}) => ({ id, job_id: 0, ts: "2026-09-27T09:00:00", status: "done", output: `${id}.wav`, error: null,
  params: { caption: `风格${id}`, lyrics: `[verse]\n歌词${id}`, duration: 30, seed: 11 }, ...extra });
const musicCalls = (backend) => backend.calls.filter((c) => c.url === "/api/media/music");

test("生成：带当前会话，不带空种子与 continues", async () => {
  await withBackend("music", async (backend) => {
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    assert.match(parts.timeline.textContent, /还没有歌曲/);
    parts.caption.value = "民谣"; parts.lyrics.value = "第一行";
    await parts.start.click();
    const [call] = musicCalls(backend);
    assert.deepEqual(call.body, { session_id: backend.sessions[0].id, caption: "民谣", lyrics: "第一行", duration: 60 });
    assert.equal(parts.caption.value, "民谣");
    assert.equal(parts.lyrics.value, "第一行");
    assert.equal(cards(parts)[0].dataset.attemptStatus, "running");
  });
});

test("空歌词本地拦截；高级参数有误写在高级参数区", async () => {
  await withBackend("music", async (backend) => {
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    parts.caption.value = "民谣"; parts.lyrics.value = " ";
    await parts.start.click();
    assert.equal(parts.error.textContent, "请填写歌词：Music 3 需要歌词才能生成");
    parts.lyrics.value = "la"; parts.duration.value = "5";
    await parts.start.click();
    assert.equal(parts.advanced.open, true);
    assert.equal(parts["advanced-error"].textContent, "高级参数里的数值有误：时长须为 10–300 的整数");
    assert.equal(musicCalls(backend).length, 0);
  });
});

test("「接着写下一段」：歌词清空、风格描述取该段、提示条「接在第 1 次后面」；生成带 continues，之后提示条隐藏", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1", { params: { caption: "民谣", lyrics: "一", duration: 45, seed: 11 } })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    parts.caption.value = "别的"; parts.lyrics.value = "草稿"; parts.seed.value = "9";
    await button(cards(parts)[0], "接着写下一段").click();
    assert.equal(parts.lyrics.value, "");
    assert.equal(parts.caption.value, "民谣");
    assert.equal(parts.duration.value, "45");
    assert.equal(parts.seed.value, "");
    assert.equal(parts.chip.hidden, false);
    assert.equal(parts["chip-text"].textContent, "接在第 1 次后面");
    assert.ok(parts.lyrics.focused > 0);
    assert.equal(musicCalls(backend).length, 0, "不提交");
    parts.lyrics.value = "第二段";
    await parts.start.click();
    assert.deepEqual(musicCalls(backend)[0].body, { session_id: backend.sessions[0].id, caption: "民谣", lyrics: "第二段", duration: 45, continues: "a1" });
    assert.equal(parts.chip.hidden, true);
    assert.equal(parts.lyrics.value, "第二段");
  });
});

test("续写段的「换个版本」带原 continues 与不同的新种子，不改输入区", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1" })]);
    const draws = [11, 77];
    const { parts, pane, ready } = makeMusicPane({ randomSeed: () => draws.shift() }); ready();
    await pane.refresh();
    parts.caption.value = "草稿";
    await button(cards(parts)[1], "换个版本").click();
    await flush();
    const [call] = musicCalls(backend);
    assert.deepEqual(call.body, { session_id: backend.sessions[0].id, caption: "风格a2", lyrics: "[verse]\n歌词a2", duration: 30, seed: 77, continues: "a1" });
    assert.equal(parts.caption.value, "草稿");
  });
});

test("「在这段基础上改」回填四项；改种子后提示条隐藏，生成不带 continues", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1" })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await button(cards(parts)[1], "在这段基础上改").click();
    assert.equal(parts.caption.value, "风格a2");
    assert.equal(parts.lyrics.value, "[verse]\n歌词a2");
    assert.equal(parts.duration.value, "30");
    assert.equal(parts.seed.value, "11");
    assert.equal(parts.chip.hidden, false);
    assert.equal(parts["chip-text"].textContent, "沿用第 2 次");
    assert.equal(parts.advanced.open, false);
    parts.seed.value = "12"; await parts.seed.dispatch("input");
    assert.equal(parts.chip.hidden, true);
    await parts.start.click();
    const [call] = musicCalls(backend);
    assert.equal("continues" in call.body, false);
    assert.equal(call.body.seed, 12);
  });
});

test("沿用提示条可见时生成带被引用尝试的 continues", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1" })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await button(cards(parts)[1], "在这段基础上改").click();
    await parts.start.click();
    assert.equal(musicCalls(backend)[0].body.continues, "a1");
    assert.equal(musicCalls(backend)[0].body.seed, 11);
  });
});

test("续写目标在会话刷新后文件不在：提示条改为不能接着写，「生成歌曲」禁用；点 × 恢复", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1")]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await button(cards(parts)[0], "接着写下一段").click();
    parts.lyrics.value = "第二段";
    backend.finish("a1", { output_missing: true });
    await pane.refresh();
    assert.equal(parts["chip-text"].textContent, "第 1 次的文件已不在，不能接着写");
    assert.equal(parts.start.disabled, true);
    assert.equal(parts.start.title, "第 1 次的文件已不在，不能接着写");
    await parts["chip-clear"].click();
    assert.equal(parts.chip.hidden, true);
    assert.equal(parts.start.disabled, false);
    await parts.start.click();
    assert.equal("continues" in musicCalls(backend)[0].body, false);
  });
});

test("后端回 segment_missing：错误行写后端原话，提示条改为不能接着写", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1")]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await button(cards(parts)[0], "接着写下一段").click();
    parts.lyrics.value = "第二段";
    backend.startResult = () => ({ ok: false, status: 404, statusText: "",
      json: async () => ({ error: { code: "segment_missing", message: "要接着写的那一段文件已不在" } }) });
    await parts.start.click();
    assert.equal(parts.error.textContent, "要接着写的那一段文件已不在");
    assert.equal(parts["chip-text"].textContent, "第 1 次的文件已不在，不能接着写");
    assert.equal(parts.start.disabled, true);
  });
});

test("有成片的展开卡片：「成片」「只听这一段」切换，默认播放成片", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1", joined_output: "j2.wav" })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const card = cards(parts)[1];
    const audio = find(card, (n) => n.tagName === "audio");
    assert.equal(audio.src, "/api/outputs/j2.wav");
    const group = find(card, (n) => n.attrs?.role === "radiogroup");
    const whole = button(group, "成片"); const part = button(group, "只听这一段");
    assert.equal(whole.attrs["aria-checked"], "true");
    await part.click();
    assert.equal(audio.src, "/api/outputs/a2.wav");
    assert.equal(part.attrs["aria-checked"], "true");
    assert.equal(whole.attrs["aria-checked"], "false");
    assert.match(card.textContent, /由：第 1 次 → 第 2 次/);
    assert.match(card.textContent, /第 2 次 · 09:00 · 接第 1 次/);
    // 没有成片的卡片只播这一段，不显示切换
    await cards(parts)[0].click();
    const first = cards(parts)[0];
    assert.equal(find(first, (n) => n.tagName === "audio").src, "/api/outputs/a1.wav");
    assert.equal(find(first, (n) => n.attrs?.role === "radiogroup"), null);
  });
});

test("成片没拼成：「重新拼接」提交整条链；链缺段时禁用并写原因", async () => {
  await withBackend("music", async (backend) => {
    const failed = { code: "join_failed", message: "ffmpeg 出错" };
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1", joined_error: failed })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    let card = cards(parts)[1];
    assert.match(card.textContent, /这一段生成好了，但成片没拼成：ffmpeg 出错/);
    await button(card, "重新拼接").click();
    await flush();
    const compose = backend.calls.find((c) => c.url === "/api/media/compose");
    assert.deepEqual(compose.body, { kind: "music", session_id: backend.sessions[0].id, parts: ["a1", "a2"] });

    backend.sessions.length = 0;
    backend.addSession("歌二", [done("b1", { output_missing: true }), done("b2", { continues: "b1", joined_error: failed })]);
    const other = makeMusicPane(); other.ready();
    await other.pane.refresh();
    card = cards(other.parts).find((n) => n.dataset.attemptId === "b2");
    const rejoin = button(card, "重新拼接");
    assert.equal(rejoin.disabled, true);
    assert.match(card.textContent, /链上有一段已不在/);
  });
});

test("合成尝试只有「接着写下一段」，点它不改风格描述与时长", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2"),
      { id: "a3", ts: "2026-09-27T09:05:00", status: "done", op: "compose", params: { parts: ["a1", "a2"] }, output: "c3.wav", error: null }]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const card = cards(parts)[2];
    assert.match(card.textContent, /合成：第 1、2 次/);
    assert.equal(button(card, "在这段基础上改"), null);
    assert.equal(button(card, "换个版本"), null);
    parts.caption.value = "我的风格"; parts.duration.value = "90"; parts.lyrics.value = "旧";
    await button(card, "接着写下一段").click();
    assert.equal(parts.caption.value, "我的风格");
    assert.equal(parts.duration.value, "90");
    assert.equal(parts.lyrics.value, "");
    assert.equal(parts["chip-text"].textContent, "接在第 3 次后面");
  });
});

test("没生成好的尝试：「接着写下一段」禁用并写原因", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [{ ...done("a1"), status: "failed", output: null, error: { code: "exit_nonzero", message: "x" } }]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const card = cards(parts)[0];
    assert.equal(button(card, "接着写下一段").disabled, true);
    assert.match(card.textContent, /这一段没有生成好，不能接着写/);
    assert.equal(find(card, (n) => n.tagName === "audio"), null);
    assert.equal(button(card, "在这段基础上改").disabled, false);
  });
});

test("挑选模式：只接勾选框的 change，点卡片由控制器切换一次", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2")]);
    const { root, parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const start = find(root, (n) => "musicComposeStart" in n.dataset);
    await start.click();
    let box = find(cards(parts)[0], (n) => n.tagName === "input" && n.type === "checkbox");
    assert.equal(box.attrs["aria-label"], "选中第 1 次");
    await box.dispatch("change");
    assert.equal(find(cards(parts)[0], (n) => n.className === "pick-badge").textContent, "①");
    await cards(parts)[1].click();
    assert.equal(find(cards(parts)[1], (n) => n.className === "pick-badge").textContent, "②");
    box = find(cards(parts)[1], (n) => n.tagName === "input" && n.type === "checkbox");
    assert.equal(box.checked, true);
  });
});

test("AI 帮写写回风格描述与歌词", async () => {
  await withBackend("music", async (backend) => {
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const [, refine] = parts.assist.children;
    assert.equal(refine.textContent, "优化提示词");
    pane.setAssistAvailable(true, "");
    parts.caption.value = "民谣";
    const previous = backend.fetch;
    globalThis.fetch = async (url, options) => (url === "/api/llm/prompt-assist"
      ? { ok: true, status: 200, json: async () => ({ task: "music", action: "refine", text: "木吉他民谣", lyrics: "第一行" }) }
      : previous(url, options));
    await refine.click();
    await flush();
    assert.equal(parts.caption.value, "木吉他民谣");
    assert.equal(parts.lyrics.value, "第一行");
  });
});

test("主流程文字不含「种子」", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1" })]);
    const { root, parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await button(cards(parts)[1], "在这段基础上改").click();
    assert.ok(!mainFlowText(root, /music-advanced|attempt-advanced/).includes(SEED));
  });
});
