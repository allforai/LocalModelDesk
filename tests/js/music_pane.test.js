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

test("「在这段基础上改」一个续写段后，它接的前段文件不在：提示条改为不能接着写，「生成歌曲」禁用（issue #19）", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1" })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await button(cards(parts)[1], "在这段基础上改").click();
    assert.equal(parts["chip-text"].textContent, "沿用第 2 次");
    backend.finish("a1", { output_missing: true });
    await pane.refresh();
    assert.equal(parts["chip-text"].textContent, "第 1 次的文件已不在，不能接着写");
    assert.equal(parts.start.disabled, true);
  });
});

test("上一条之后改种子：提示条隐藏且「生成歌曲」重新可用，生成不带 continues（final review Important 1）", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1" })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await button(cards(parts)[1], "在这段基础上改").click();
    backend.finish("a1", { output_missing: true });
    await pane.refresh();
    assert.equal(parts.start.disabled, true, "改种子之前仍是不能接着写的死路");
    parts.seed.value = "12"; await parts.seed.dispatch("input");
    assert.equal(parts.chip.hidden, true, "改种子后提示条本就该隐藏");
    assert.equal(parts.start.disabled, false, "改种子后不再沿用前段，不该被卡住");
    assert.equal(parts.start.title, "");
    await parts.start.click();
    assert.equal("continues" in musicCalls(backend)[0].body, false);
    assert.equal(musicCalls(backend)[0].body.seed, 12);
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
    assert.ok(find(cards(parts)[0], (n) => n.classList?.contains?.("icon-music")), "文件不在的音乐卡片应显示音乐图标而非图片图标");
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

test("挑选模式下卡片只做勾选：三个动作与重新拼接都不出现，文字说明还在；退出后恢复", async () => {
  await withBackend("music", async (backend) => {
    const failed = { code: "join_failed", message: "ffmpeg 出错" };
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1", joined_error: failed })]);
    const { root, parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    let card = cards(parts)[1]; // 默认选中最后一次，展开
    assert.equal(card.getAttribute("aria-expanded"), "true");
    assert.match(card.textContent, /这一段生成好了，但成片没拼成：ffmpeg 出错/);
    assert.ok(button(card, "在这段基础上改"));
    assert.ok(button(card, "换个版本"));
    assert.ok(button(card, "接着写下一段"));
    assert.ok(button(card, "重新拼接"));

    const start = find(root, (n) => "musicComposeStart" in n.dataset);
    await start.click();
    card = cards(parts)[1];
    assert.equal(button(card, "在这段基础上改"), null);
    assert.equal(button(card, "换个版本"), null);
    assert.equal(button(card, "接着写下一段"), null);
    assert.equal(button(card, "重新拼接"), null);
    assert.match(card.textContent, /这一段生成好了，但成片没拼成：ffmpeg 出错/, "出错说明文字仍留着");

    const bar = find(root, (n) => "musicComposeBar" in n.dataset);
    await button(bar, "取消").click();
    card = cards(parts)[1];
    assert.ok(button(card, "在这段基础上改"));
    assert.ok(button(card, "换个版本"));
    assert.ok(button(card, "接着写下一段"));
    assert.ok(button(card, "重新拼接"));
  });
});

test("素材库回填：原会话已不在时按字段回填，种子带着，提示条显示「沿用素材库里这首」（M-52）", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1")]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await pane.applyFill({ pane: "music", session_id: "gone", attempt_id: "x",
      fields: { caption: "旧风格", lyrics: "旧词", duration: 45, seed: 7 } });
    assert.equal(parts.caption.value, "旧风格");
    assert.equal(parts.lyrics.value, "旧词");
    assert.equal(parts.duration.value, "45");
    assert.equal(parts.seed.value, "7");
    assert.equal(parts.chip.hidden, false);
    assert.equal(parts["chip-text"].textContent, "沿用素材库里这首");
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

// ---------- issue #18 ----------
const composeCalls = (backend) => backend.calls.filter((c) => c.url === "/api/media/compose");
const sessionItem = (parts, id) => findAll(parts["session-list"], (n) => n.dataset?.sessionId === id)[0];
const cardOf = (parts, id) => cards(parts).find((n) => n.dataset.attemptId === id);

test("double rejoin sends once：第一次还没返回时再点「重新拼接」只发一个合成请求", async () => {
  await withBackend("music", async (backend) => {
    const failed = { code: "join_failed", message: "ffmpeg 出错" };
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1", joined_error: failed })]);
    backend.nextJob = 50;
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const rejoin = button(cardOf(parts, "a2"), "重新拼接");
    rejoin.click(); rejoin.click();
    await flush(); await flush();
    assert.equal(composeCalls(backend).length, 1);
  });
});

test("有作业在跑时「重新拼接」禁用并写忙碌原因；作业结束后同一张卡上的按钮自动恢复", async () => {
  await withBackend("music", async (backend) => {
    const failed = { code: "join_failed", message: "ffmpeg 出错" };
    const busy = backend.addSession("夏夜", [{ ...done("r1"), status: "running", output: null }]);
    const mine = backend.addSession("歌", [done("a1"), done("a2", { continues: "a1", joined_error: failed })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await sessionItem(parts, mine.id).click(); await flush();
    let rejoin = button(cardOf(parts, "a2"), "重新拼接");
    assert.equal(rejoin.disabled, true);
    assert.equal(rejoin.title, "「夏夜」正在生成歌曲");
    await rejoin.click(); await flush();
    assert.equal(composeCalls(backend).length, 0);

    backend.finish("r1", { status: "done", output: "r1.wav" });
    pane.applyJob({ job_id: 9, kind: "music", status: "done", session_id: busy.id, attempt_id: "r1" });
    await flush(); await flush();
    rejoin = button(cardOf(parts, "a2"), "重新拼接");
    assert.equal(rejoin.disabled, false);
    assert.equal(rejoin.title, "");
  });
});

test("成片播放出错：退回本段、去掉切换、不标文件不在、仍可接着写；本段再出错才标文件不在", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1", joined_output: "j2.wav" })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const card = cardOf(parts, "a2");
    const audio = find(card, (n) => n.tagName === "audio");
    assert.equal(audio.src, "/api/outputs/j2.wav");
    await audio.dispatch("error");
    assert.equal(audio.src, "/api/outputs/a2.wav");
    assert.equal(find(cardOf(parts, "a2"), (n) => n.attrs?.role === "radiogroup"), null);
    assert.doesNotMatch(cardOf(parts, "a2").textContent, /音频文件已不在/);
    assert.equal(button(cardOf(parts, "a2"), "接着写下一段").disabled, false);

    await audio.dispatch("error");
    assert.match(cardOf(parts, "a2").textContent, /音频文件已不在/);
    assert.equal(button(cardOf(parts, "a2"), "接着写下一段").disabled, true);
  });
});

test("切换会话后 brokenIds 清空：切回并刷新、文件已恢复时这段可以接着写", async () => {
  await withBackend("music", async (backend) => {
    const a = backend.addSession("甲", [done("a1")]);
    const b = backend.addSession("乙", [done("b1")]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    await sessionItem(parts, a.id).click(); await flush();
    await find(cardOf(parts, "a1"), (n) => n.tagName === "audio").dispatch("error");
    assert.equal(button(cardOf(parts, "a1"), "接着写下一段").disabled, true);
    await sessionItem(parts, b.id).click(); await flush();
    await sessionItem(parts, a.id).click(); await flush();
    await pane.refresh();
    const next = button(cardOf(parts, "a1"), "接着写下一段");
    assert.equal(next.disabled, false);
    await next.click();
    assert.equal(parts["chip-text"].textContent, "接在第 1 次后面");
  });
});

test("分段切换可用方向键：ArrowRight 到「只听这一段」并聚焦、换源；ArrowLeft 回到「成片」", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1", joined_output: "j2.wav" })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const card = cardOf(parts, "a2");
    const audio = find(card, (n) => n.tagName === "audio");
    const group = find(card, (n) => n.attrs?.role === "radiogroup");
    const whole = button(group, "成片"); const part = button(group, "只听这一段");
    assert.equal(whole.tabIndex, 0);
    assert.equal(part.tabIndex, -1);
    await whole.dispatch("keydown", { key: "ArrowRight" });
    assert.equal(part.attrs["aria-checked"], "true");
    assert.equal(whole.attrs["aria-checked"], "false");
    assert.equal(part.focused, 1);
    assert.equal(part.tabIndex, 0);
    assert.equal(audio.src, "/api/outputs/a2.wav");
    await part.dispatch("keydown", { key: "ArrowLeft" });
    assert.equal(whole.attrs["aria-checked"], "true");
    assert.equal(whole.focused, 1);
    assert.equal(audio.src, "/api/outputs/j2.wav");
    await whole.dispatch("keydown", { key: "End" });
    assert.equal(part.attrs["aria-checked"], "true");
    await part.dispatch("keydown", { key: "Home" });
    assert.equal(whole.attrs["aria-checked"], "true");
  });
});

test("成片文件被删（joined_missing）：显示问题行并可「重新拼接」整条链", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2", { continues: "a1", joined_output: "j2.wav", joined_missing: true })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const card = cardOf(parts, "a2");
    assert.match(card.textContent, /这一段生成好了，但成片文件已不在/);
    assert.equal(find(card, (n) => n.tagName === "audio").src, "/api/outputs/a2.wav");
    const rejoin = button(card, "重新拼接");
    assert.equal(rejoin.disabled, false);
    await rejoin.click(); await flush();
    assert.deepEqual(composeCalls(backend).map((c) => c.body.parts), [["a1", "a2"]]);
  });
});


test("忙碌原因变化只就地更新「重新拼接」，不重建正在播放的音频（#21）", async () => {
  await withBackend("music", async (backend) => {
    const failed = { code: "join_failed", message: "ffmpeg 出错" };
    backend.addSession("片", [done("a1"), done("a2", { continues: "a1", joined_error: failed })]);
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    const card = cardOf(parts, "a2");
    const player = find(card, (n) => n.tagName === "audio");
    const rejoin = button(card, "重新拼接");
    assert.ok(player && rejoin);
    assert.equal(rejoin.disabled, false);
    pane.setHeavyAllowed(false, "对话模型正在占用内存");
    assert.equal(find(cardOf(parts, "a2"), (n) => n.tagName === "audio"), player);
    assert.equal(button(cardOf(parts, "a2"), "重新拼接"), rejoin);
    assert.equal(rejoin.disabled, true);
    assert.equal(rejoin.title, "对话模型正在占用内存");
    pane.setHeavyAllowed(true);
    assert.equal(find(cardOf(parts, "a2"), (n) => n.tagName === "audio"), player);
    assert.equal(rejoin.disabled, false);
  });
});

test("新会话清空风格、歌词与种子，时长保留", async () => {
  await withBackend("music", async (backend) => {
    const { parts, pane, ready } = makeMusicPane(); ready();
    await pane.refresh();
    parts.caption.value = "民谣"; parts.lyrics.value = "第一行"; parts.seed.value = "7"; parts.duration.value = "90";
    await parts["session-new"].click();
    assert.equal(parts.caption.value, "");
    assert.equal(parts.lyrics.value, "");
    assert.equal(parts.seed.value, "");
    assert.equal(parts.duration.value, "90");
  });
});
