import test from "node:test";
import assert from "node:assert/strict";
import { createPromptAssist } from "../../desk/static/js/widgets/prompt_assist.js";

class El {
  constructor(tag = "div") { this.tagName = tag; this.children = []; this.listeners = {}; this.hidden = false; this.disabled = false; this.textContent = ""; this.className = ""; this.dataset = {}; }
  append(...nodes) { this.children.push(...nodes); }
  addEventListener(type, fn) { this.listeners[type] = fn; }
  click() { return this.listeners.click?.(); }
}
const doc = { createElement: (tag) => new El(tag) };
const byData = (container, key) => container.children.find((node) => node.dataset[key]);

function setup({ fields = { text: "" }, confirmAnswer = true, task = "video" } = {}) {
  const container = new El();
  const state = { ...fields };
  const asked = [];
  const assist = createPromptAssist(doc, container, {
    task,
    read: () => ({ ...state }),
    write: (next) => Object.assign(state, next),
    mode: () => "image",
    confirm: async (options) => { asked.push(options); return confirmAnswer; },
  });
  return { container, state, asked, assist };
}

async function withFetch(reply, run) {
  const previous = globalThis.fetch; const bodies = [];
  globalThis.fetch = async (_url, options) => { bodies.push(JSON.parse(options.body)); return reply(); };
  try { await run(bodies); } finally { globalThis.fetch = previous; }
}
const ok = (payload) => new Response(JSON.stringify(payload), { status: 200 });

test("初始禁用并说明原因；可用后启用", () => {
  const { container, assist } = setup();
  assert.equal(byData(container, "assistLucky").disabled, true);
  assert.equal(byData(container, "assistHint").textContent, "先在「聊天」页加载一个模型");
  assert.equal(byData(container, "assistUndo").hidden, true);
  assist.setAvailable(true, "");
  assert.equal(byData(container, "assistLucky").disabled, false);
  assert.equal(byData(container, "assistHint").textContent, "");
});

test("看手气：空输入框直接写入，不打扰；带着生成方式请求", async () => {
  const { container, state, asked, assist } = setup();
  assist.setAvailable(true, "");
  await withFetch(() => ok({ task: "video", action: "lucky", text: "雨夜街角" }), async (bodies) => {
    await byData(container, "assistLucky").click();
    assert.deepEqual(bodies[0], { task: "video", action: "lucky", mode: "image", text: "" });
  });
  assert.equal(asked.length, 0);
  assert.equal(state.text, "雨夜街角");
  assert.equal(byData(container, "assistUndo").hidden, false);
});

test("看手气：输入框有内容时先提醒会被替换；取消则不请求", async () => {
  const { container, state, asked, assist } = setup({ fields: { text: "我写的" }, confirmAnswer: false });
  assist.setAvailable(true, "");
  await withFetch(() => { throw new Error("不应请求"); }, async () => {
    await byData(container, "assistLucky").click();
  });
  assert.equal(asked.length, 1);
  assert.equal(asked[0].confirmLabel, "替换");
  assert.match(asked[0].message, /替换输入框里现有的内容/);
  assert.equal(state.text, "我写的");
});

test("优化提示词：空输入框只提示不请求；有内容则替换并可恢复原文", async () => {
  const empty = setup();
  empty.assist.setAvailable(true, "");
  await withFetch(() => { throw new Error("不应请求"); }, async () => { await byData(empty.container, "assistRefine").click(); });
  assert.equal(byData(empty.container, "assistHint").textContent, "先在输入框里写点东西，再点「优化提示词」");

  const { container, state, assist } = setup({ fields: { text: "猫", lyrics: "啦" }, task: "music" });
  assist.setAvailable(true, "");
  await withFetch(() => ok({ task: "music", action: "refine", text: "木吉他民谣", lyrics: "啦" }), async (bodies) => {
    await byData(container, "assistRefine").click();
    assert.deepEqual(bodies[0], { task: "music", action: "refine", mode: "image", text: "猫", lyrics: "啦" });
  });
  assert.equal(state.text, "木吉他民谣");
  await byData(container, "assistUndo").click();
  assert.equal(state.text, "猫");
  assert.equal(byData(container, "assistUndo").hidden, true);
});

test("失败时写明原因、按钮恢复可用、输入框不变", async () => {
  const { container, state, assist } = setup({ fields: { text: "猫" } });
  assist.setAvailable(true, "");
  await withFetch(() => new Response(JSON.stringify({ error: { code: "no_model_loaded", message: "当前没有加载模型" } }), { status: 503 }), async () => {
    await byData(container, "assistRefine").click();
  });
  assert.equal(byData(container, "assistHint").textContent, "先在「聊天」页加载一个模型");
  assert.equal(byData(container, "assistRefine").disabled, false);
  assert.equal(state.text, "猫");
});

test("台面收回模型时提示重新加载，而不是留一句「媒体作业进行中」", async () => {
  // 服务端不再用 media_busy 拒聊天（媒体与聊天可以共存），这条路上真正会回来的
  // 是 evicted；旧映射里那个键已经不会出现，留着只会让这里落回裸错误文案。
  const { container, assist } = setup({ fields: { text: "猫" } });
  assist.setAvailable(true, "");
  await withFetch(() => new Response(
    JSON.stringify({ error: { code: "evicted", message: "模型已被台面收回" } }), { status: 503 }),
    async () => { await byData(container, "assistRefine").click(); });
  assert.equal(byData(container, "assistHint").textContent, "模型已被台面收回，请重新加载");
});
