// 图片会话面板的控制逻辑（假 DOM）。真实浏览器里的布局与交互由 tests/e2e/test_image_flow.py 覆盖。
import test from "node:test";
import assert from "node:assert/strict";
import { createImagePane } from "../../desk/static/js/panes/image.js";

const SEED = "种子"; // 「种子」

class Element {
  constructor(tag = "div") {
    this.tagName = tag; this.children = []; this.listeners = {}; this.dataset = {}; this.attrs = {};
    this.value = ""; this.hidden = false; this.disabled = false; this.open = false;
    this.title = ""; this.className = ""; this.scrollTop = 0; this.scrollHeight = 100; this.focused = 0;
    const self = this;
    this.classList = {
      add(name) { if (!self.classList.contains(name)) self.className = `${self.className} ${name}`.trim(); },
      contains(name) { return self.className.split(/\s+/).includes(name); },
      toggle(name, on) { if (on) this.add(name); else self.className = self.className.split(/\s+/).filter((c) => c !== name).join(" "); },
    };
  }
  // 与真实 DOM 一致：写 textContent 换成一个文本子节点，之后 append 的图标与它并存。
  get textContent() { return this.children.map((c) => c.textContent).join(""); }
  set textContent(value) {
    const text = String(value ?? "");
    this.children = text ? [{ tagName: "#text", textContent: text, children: [], dataset: {}, attrs: {} }] : [];
  }
  append(...nodes) { for (const node of nodes) { node.parentNode = this; this.children.push(node); } }
  replaceChildren(...nodes) { this.children = []; this.append(...nodes); }
  addEventListener(type, listener) { (this.listeners[type] ??= []).push(listener); }
  dispatch(type, event = {}) { return Promise.all((this.listeners[type] ?? []).map((fn) => fn({ target: this, preventDefault() {}, stopPropagation() {}, ...event }))); }
  click() { return this.dispatch("click"); }
  setAttribute(name, value) { this.attrs[name] = String(value); }
  getAttribute(name) { return this.attrs[name] ?? null; }
  removeAttribute(name) { delete this.attrs[name]; if (name === "value") this.value = undefined; }
  focus() { this.focused += 1; }
  scrollIntoView() {}
  setSelectionRange(a, b) { this.selection = [a, b]; }
  remove() { const list = this.parentNode?.children; if (list) list.splice(list.indexOf(this), 1); }
  querySelectorAll(selector) {
    const key = selector.match(/^\[data-([\w-]+)\]$/)?.[1]?.replace(/-([a-z])/g, (_, c) => c.toUpperCase());
    const found = [];
    const walk = (node) => { for (const child of node.children ?? []) { if (key && key in child.dataset) found.push(child); walk(child); } };
    walk(this);
    return found;
  }
}

const walk = (node, visit) => { visit(node); for (const child of node.children ?? []) walk(child, visit); };
const findAll = (node, pred) => { const out = []; walk(node, (n) => { if (pred(n)) out.push(n); }); return out; };
const find = (node, pred) => findAll(node, pred)[0] ?? null;
const byData = (node, key) => find(node, (n) => key in (n.dataset ?? {}));
const button = (node, text) => find(node, (n) => n.tagName === "button" && n.textContent === text);
const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

// 主流程可见文字：跳过 hidden 节点与「高级参数」折叠块（D-50 唯一允许出现「种子」的地方）。
function mainFlowText(node) {
  if (node.hidden) return "";
  if (node.tagName === "details" && /image-advanced|attempt-advanced/.test(node.className)) return "";
  const own = node.tagName === "#text" ? node.textContent : node.children.map(mainFlowText).join(" ");
  return [own, node.title, node.attrs?.["aria-label"], node.attrs?.placeholder].filter(Boolean).join(" ");
}

function makePane(ctx = {}) {
  const names = ["prompt", "width", "height", "steps", "seed", "start", "error", "hint", "hint-text", "return", "model",
    "advanced", "advanced-error", "refine", "refine-text", "refine-clear", "timeline", "session-list", "session-new", "composer"];
  const parts = Object.fromEntries(names.map((name) => [name, new Element(
    name === "advanced" ? "details" : name === "prompt" ? "textarea" : name === "timeline" ? "div" : "p")]));
  parts.width.value = "1024"; parts.height.value = "1024"; parts.steps.value = "40"; parts.seed.value = "";
  parts.advanced.className = "image-advanced";
  parts.advanced.append(parts.width, parts.height, parts.steps, parts.seed, parts["advanced-error"]);
  parts.hint.append(parts["hint-text"], parts.return);
  const root = new Element("section");
  root.append(parts["session-new"], parts["session-list"], parts.model, parts.timeline, parts.composer);
  parts.composer.append(parts.refine, parts.prompt, parts.start, parts.advanced, parts.hint, parts.error);
  parts.refine.append(parts["refine-text"], parts["refine-clear"]);
  const doc = { body: new Element("body"), createElement: (tag) => new Element(tag) };
  root.ownerDocument = doc;
  root.querySelector = (selector) => parts[selector.match(/^\[data-image-([\w-]+)\]$/)?.[1]] ?? null;
  const pane = createImagePane(root, ctx);
  return { root, parts, pane, ready() {
    pane.setHeavyAllowed(true); pane.setRuntimeStatus({ present: true }); pane.setModelStatus({ state: "present" });
  } };
}

// 一个极小的后端：会话存在内存里，按路由回应；每次调用记下来。
function fakeBackend() {
  const state = { sessions: [], calls: [], nextJob: 1, startResult: null };
  const summary = (s) => ({ id: s.id, title: s.title, created: s.created, updated: s.updated,
    attempt_count: s.attempts.length, running: s.attempts.some((a) => a.status === "running"),
    cover: s.attempts.filter((a) => a.status === "done").at(-1)?.output ?? null });
  const reply = (status, body) => ({ ok: status < 400, status, statusText: "", json: async () => body });
  let clock = 0;
  const stamp = () => `2026-09-24T10:${String(clock++).padStart(2, "0")}:00`;
  state.addSession = (title = "新会话", attempts = []) => {
    const s = { id: `s${state.sessions.length + 1}`, title, title_auto: true, created: stamp(), updated: stamp(), attempts };
    state.sessions.push(s);
    return s;
  };
  state.fetch = async (url, options = {}) => {
    const method = options.method ?? "GET";
    const body = options.body ? JSON.parse(options.body) : undefined;
    state.calls.push({ url, method, body });
    if (url === "/api/image-sessions" && method === "GET")
      return reply(200, [...state.sessions].sort((a, b) => b.updated.localeCompare(a.updated)).map(summary));
    if (url === "/api/image-sessions" && method === "POST") return reply(200, state.addSession());
    const one = url.match(/^\/api\/image-sessions\/(\w+)$/);
    if (one) {
      const s = state.sessions.find((item) => item.id === one[1]);
      if (!s) return reply(404, { error: `会话不存在：${one[1]}` });
      if (method === "DELETE") { state.sessions.splice(state.sessions.indexOf(s), 1); return reply(200, { deleted: s.id }); }
      if (method === "PATCH") { s.title = body.title; s.title_auto = false; s.updated = stamp(); }
      return reply(200, structuredClone(s));
    }
    if (url === "/api/media/image") {
      if (state.startResult) return state.startResult(body);
      const s = state.sessions.find((item) => item.id === body.session_id);
      if (!s) return reply(404, { error: { code: "session_not_found", message: "这个会话已被删除，请选择或新建一个会话" } });
      const attempt = { id: `a${state.nextJob}`, job_id: state.nextJob, ts: stamp(), status: "running",
        params: { prompt: body.prompt, width: body.width, height: body.height, steps: body.steps, seed: body.seed ?? 555 }, output: null, error: null };
      if (!s.attempts.length && s.title_auto) s.title = body.prompt.slice(0, 24);
      s.attempts.push(attempt); s.updated = stamp();
      return reply(200, { job_id: state.nextJob++, kind: "image", status: "running", session_id: s.id, attempt_id: attempt.id, log: "" });
    }
    if (url === "/api/media/cancel") return reply(200, { job_id: 1, kind: "image", status: "cancelled" });
    throw new Error(`unexpected ${method} ${url}`);
  };
  state.finish = (attemptId, patch) => {
    for (const s of state.sessions) for (const a of s.attempts) if (a.id === attemptId) Object.assign(a, patch);
  };
  return state;
}

async function withBackend(run) {
  const backend = fakeBackend();
  const previous = globalThis.fetch;
  globalThis.fetch = backend.fetch;
  try { await run(backend); } finally { globalThis.fetch = previous; }
}

const cards = (parts) => findAll(parts.timeline, (n) => "attemptId" in n.dataset);
const done = (id, seed, prompt) => ({ id, job_id: 0, ts: "2026-09-24T09:00:00", finished: "2026-09-24T09:01:00", status: "done",
  params: { prompt, width: 1024, height: 1024, steps: 40, seed }, output: `${id}.png`, error: null });

test("首次进入没有任何会话：自动新建一个并选中，时间线显示空会话两行（D-62、D-80）", async () => {
  await withBackend(async (backend) => {
    const { parts, pane, ready } = makePane(); ready();
    assert.equal(parts["session-list"].children[0].textContent, "正在加载会话…");
    assert.equal(parts.start.disabled, true);
    await pane.refresh();
    assert.equal(backend.sessions.length, 1);
    const items = parts["session-list"].children;
    assert.equal(items.length, 1);
    assert.equal(items[0].attrs["aria-current"], "true");
    assert.match(items[0].textContent, /新会话/);
    assert.match(parts.timeline.textContent, /还没有图片/);
    assert.match(parts.timeline.textContent, /在下面写下想要的画面/);
    assert.equal(parts.start.disabled, false);
    assert.equal(parts.advanced.open, false);
    assert.ok(!mainFlowText(parts.timeline.parentNode ?? parts.timeline).includes(SEED));
  });
});

test("生成带当前会话、不传空种子；成功后提示词保留、种子框清空（D-61、D-65、D-66）", async () => {
  await withBackend(async (backend) => {
    const started = [];
    const { parts, pane, ready } = makePane({ onStarted: (job) => started.push(job) }); ready();
    await pane.refresh();
    parts.prompt.value = "一只橘猫";
    await parts.start.click();
    const call = backend.calls.find((c) => c.url === "/api/media/image");
    assert.deepEqual(call.body, { session_id: backend.sessions[0].id, prompt: "一只橘猫", width: 1024, height: 1024, steps: 40 });
    assert.equal(started.length, 1);
    assert.equal(parts.prompt.value, "一只橘猫");
    assert.equal(parts.seed.value, "");
    const [card] = cards(parts);
    assert.equal(card.dataset.attemptStatus, "running");
    assert.equal(card.attrs["aria-expanded"], "true");
    assert.equal(find(card, (n) => n.tagName === "img"), null, "running 卡片不画图片框");
    assert.equal(button(card, "在这张基础上改"), null);
    assert.ok(find(card, (n) => n.tagName === "progress"));
    assert.equal(parts.start.disabled, true);
    assert.equal(parts["hint-text"].textContent, "正在生成这个会话里的第 1 次");
  });
});

test("高级参数里的数值有误：不请求，错误写在高级参数区并展开它（D-51）", async () => {
  await withBackend(async (backend) => {
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    parts.prompt.value = "猫"; parts.seed.value = "-3";
    await parts.start.click();
    assert.equal(backend.calls.filter((c) => c.url === "/api/media/image").length, 0);
    assert.equal(parts.advanced.open, true);
    assert.equal(parts["advanced-error"].textContent, "高级参数里的数值有误：种子须为 0–4294967295 的整数");
    assert.equal(parts.error.textContent, "");
    parts.prompt.value = " "; parts.seed.value = "";
    await parts.start.click();
    assert.equal(parts.error.textContent, "请填写图片提示词");
  });
});

test("「在这张基础上改」回填并沿用种子、不提交、高级参数不展开；改种子后提示条消失（D-40–D-43）", async () => {
  await withBackend(async (backend) => {
    backend.addSession("橘猫", [done("a1", 11, "橘猫一"), done("a2", 22, "橘猫二")]);
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    assert.equal(cards(parts).length, 2);
    assert.equal(cards(parts)[1].attrs["aria-expanded"], "true", "默认展开最后一张");
    await cards(parts)[0].click();
    assert.equal(cards(parts)[0].attrs["aria-expanded"], "true");
    assert.equal(cards(parts)[1].attrs["aria-expanded"], "false");
    const before = backend.calls.length;
    await button(cards(parts)[0], "在这张基础上改").click();
    assert.equal(backend.calls.length, before, "不提交");
    assert.equal(parts.prompt.value, "橘猫一");
    assert.equal(parts.seed.value, "11");
    assert.equal(parts.refine.hidden, false);
    assert.equal(parts["refine-text"].textContent, "以第 1 次为底稿"); // 以图生图：有图的尝试当底稿
    assert.equal(parts.advanced.open, false);
    assert.ok(parts.prompt.focused > 0);
    assert.deepEqual(parts.prompt.selection, [3, 3]);
    parts.seed.value = "12"; await parts.seed.dispatch("input");
    assert.equal(parts.refine.hidden, true);
    parts.seed.value = "11"; await parts.seed.dispatch("input");
    assert.equal(parts.refine.hidden, false);
    await parts["refine-clear"].click();
    assert.equal(parts.seed.value, ""); assert.equal(parts.refine.hidden, true);
    await button(cards(parts)[0], "在这张基础上改").click();
    parts.prompt.value = "橘猫一，黄昏";
    await parts.start.click();
    const call = backend.calls.filter((c) => c.url === "/api/media/image").at(-1);
    assert.equal(call.body.seed, 11, "新尝试沿用原种子（D-44）");
    assert.equal(call.body.prompt, "橘猫一，黄昏");
    assert.equal(parts.refine.hidden, true);
  });
});

test("「换个构图」立即提交同参数与不同的新种子，不改输入框（D-46、D-47）", async () => {
  await withBackend(async (backend) => {
    backend.addSession("橘猫", [done("a1", 11, "橘猫一")]);
    const draws = [11, 42];
    const { parts, pane, ready } = makePane({ randomSeed: () => draws.shift() }); ready();
    await pane.refresh();
    parts.prompt.value = "别的草稿"; parts.seed.value = "";
    await button(cards(parts)[0], "换个构图").click();
    await flush();
    const call = backend.calls.find((c) => c.url === "/api/media/image");
    assert.deepEqual(call.body, { session_id: backend.sessions[0].id, prompt: "橘猫一", width: 1024, height: 1024, steps: 40, seed: 42,
      base: { attempt_id: "a1", strength: 0.35 } }); // 以图生图：以这张为底稿换构图
    assert.equal(parts.prompt.value, "别的草稿");
    assert.equal(cards(parts).length, 2);
    assert.equal(cards(parts)[1].dataset.attemptStatus, "running");
  });
});

test("生成中「换个构图」禁用并写明原因，「在这张基础上改」可用（D-48、D-83）", async () => {
  await withBackend(async (backend) => {
    backend.addSession("橘猫", [done("a1", 11, "橘猫一")]);
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    pane.setHeavyAllowed(false, "媒体作业进行中");
    const card = cards(parts)[0];
    const recompose = button(card, "换个构图");
    assert.equal(recompose.disabled, true);
    assert.equal(recompose.title, "媒体作业进行中");
    assert.equal(find(card, (n) => /attempt-action-hint/.test(n.className)).textContent, "媒体作业进行中");
    assert.equal(button(card, "在这张基础上改").disabled, false);
    assert.equal(parts.return.hidden, true, "占用者不是图片会话时没有「回到该会话」");
  });
});

test("别的会话在生成：列表标「生成中」、状态行点名该会话并能回去；进度不进当前会话（D-82、D-87）", async () => {
  await withBackend(async (backend) => {
    const a = backend.addSession("会话甲", []);
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    parts.prompt.value = "甲的图";
    await parts.start.click();
    const running = a.attempts[0];
    await parts["session-new"].click();
    const b = backend.sessions.at(-1);
    assert.equal(parts["session-list"].children[0].dataset.sessionId, b.id, "新会话在最上");
    assert.equal(parts["session-list"].children[0].attrs["aria-current"], "true");
    assert.match(parts.timeline.textContent, /还没有图片/);
    const job = { job_id: running.job_id, kind: "image", status: "running", session_id: a.id, attempt_id: running.id, log: "step 3/10\n", elapsed_s: 5 };
    pane.applyJob(job, { replaceLog: true });
    await flush();
    assert.equal(cards(parts).length, 0, "甲的 running 卡片不出现在乙的时间线");
    assert.equal(parts.start.disabled, true);
    assert.equal(parts["hint-text"].textContent, "「甲的图」正在生成图片");
    assert.equal(parts.return.hidden, false);
    const aItem = parts["session-list"].children.find((li) => li.dataset.sessionId === a.id);
    assert.ok(byData(aItem, "sessionRunning"), "会话甲带「生成中」标记");
    await parts.return.click();
    await flush();
    const [card] = cards(parts);
    assert.equal(card.dataset.attemptId, running.id);
    pane.applyJob({ ...job, log: "step 5/10\n", elapsed_s: 80 });
    assert.equal(find(card, (n) => n.tagName === "progress").value, 50);
    assert.match(card.textContent, /第 1 次 · 生成中…（已用 1分20秒）/);
    backend.finish(running.id, { status: "done", output: "x.png", finished: "2026-09-24T10:59:00" });
    pane.applyJob({ ...job, status: "done", log: "" });
    await flush(); await flush();
    assert.equal(cards(parts)[0].dataset.attemptStatus, "done");
    assert.ok(find(cards(parts)[0], (n) => n.tagName === "img"));
    assert.equal(b.attempts.length, 0, "乙没有被写入任何尝试");
  });
});

test("失败、已取消、文件不在：不画图片框，写明原因，仍给两个动作（D-84–D-86）", async () => {
  await withBackend(async (backend) => {
    backend.addSession("混合", [
      { ...done("a1", 1, "失败的"), status: "failed", output: null, error: { code: "exit_nonzero", message: "exit 1", log_tail: "Traceback boom" } },
      { ...done("a2", 2, "取消的"), status: "cancelled", output: null, error: { code: "cancelled", message: "已取消：这次生成被手动停止" } },
      { ...done("a3", 3, "中断的"), status: "failed", output: null, error: { code: "interrupted", message: "应用在生成途中关闭，这次没有完成" } },
      { ...done("a4", 4, "文件没了"), output_missing: true },
    ]);
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    const list = cards(parts);
    assert.deepEqual(list.map((c) => c.dataset.attemptStatus), ["failed", "cancelled", "failed", "missing"]);
    for (const card of list) assert.equal(find(card, (n) => n.tagName === "img"), null, card.dataset.attemptId);
    assert.match(list[0].textContent, /失败.*生成程序异常退出/);
    assert.match(list[1].textContent, /已取消.*这次生成被手动停止/);
    assert.match(list[2].textContent, /应用在生成途中关闭，这次没有完成/);
    assert.match(list[3].textContent, /图片文件已不在.*可能已在访达中移动或删除/);
    await list[0].click();
    const failed = cards(parts)[0];
    assert.ok(button(failed, "在这张基础上改") && button(failed, "换个构图"));
    assert.match(failed.textContent, /exit_nonzero: exit 1\nTraceback boom/);
    assert.ok(!mainFlowText(parts.timeline).includes(SEED));
  });
});

test("展开卡片只放一张图：大图代替标题行的缩略图；折叠卡片仍是缩略图（D-73、D-74、§7.1 草图；B-01）", async () => {
  await withBackend(async (backend) => {
    backend.addSession("灯塔", [done("a1", 1, "灯塔一"), done("a2", 2, "灯塔二")]);
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    const images = (card) => findAll(card, (n) => n.tagName === "img").map((img) => ({
      big: /attempt-image/.test(img.className), inThumb: /attempt-thumb/.test(img.parentNode?.className ?? ""), src: img.src }));
    let [first, last] = cards(parts);
    assert.equal(last.getAttribute("aria-expanded"), "true");
    assert.deepEqual(images(last), [{ big: true, inThumb: false, src: "/api/outputs/a2.png" }]);
    assert.equal(find(last, (n) => /attempt-thumb/.test(n.className)), null);
    assert.deepEqual(images(first), [{ big: false, inThumb: true, src: "/api/outputs/a1.png" }]);
    await first.click();
    [first, last] = cards(parts);
    assert.deepEqual(images(first), [{ big: true, inThumb: false, src: "/api/outputs/a1.png" }]);
    assert.deepEqual(images(last), [{ big: false, inThumb: true, src: "/api/outputs/a2.png" }]);
    // 摘要行仍在（title 为完整提示词），完整提示词仍在大图下面。
    assert.equal(find(first, (n) => /attempt-prompt/.test(n.className)).title, "灯塔一");
    assert.equal(find(first, (n) => /attempt-full-prompt/.test(n.className)).textContent, "灯塔一");
  });
});

test("图片加载出错时立即换成「图片文件已不在」（D-85）", async () => {
  await withBackend(async (backend) => {
    backend.addSession("橘猫", [done("a1", 1, "橘猫")]);
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    const img = find(cards(parts)[0], (n) => n.tagName === "img");
    await img.dispatch("error");
    assert.equal(cards(parts)[0].dataset.attemptStatus, "missing");
    assert.equal(find(cards(parts)[0], (n) => n.tagName === "img"), null);
  });
});

test("切换会话清空种子框与提示条，提示词保留；切回内容不变（D-64、AC-4）", async () => {
  await withBackend(async (backend) => {
    const a = backend.addSession("甲", [done("a1", 11, "甲一")]);
    backend.addSession("乙", [done("b1", 22, "乙一")]);
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    const first = parts["session-list"].children[0].dataset.sessionId;
    await button(cards(parts)[0], "在这张基础上改").click();
    assert.equal(parts.refine.hidden, false);
    const other = parts["session-list"].children.find((li) => li.dataset.sessionId !== first);
    await other.click(); await flush();
    assert.equal(parts.seed.value, ""); assert.equal(parts.refine.hidden, true);
    assert.ok(parts.prompt.value.length > 0);
    const shown = cards(parts).map((c) => c.dataset.attemptId);
    await parts["session-list"].children.find((li) => li.dataset.sessionId === first).click(); await flush();
    const back = cards(parts).map((c) => c.dataset.attemptId);
    assert.notDeepEqual(shown, back);
    await parts["session-list"].children.find((li) => li.dataset.sessionId === other.dataset.sessionId).click(); await flush();
    assert.deepEqual(cards(parts).map((c) => c.dataset.attemptId), shown);
    assert.ok(a);
  });
});

test("删除会话：确认正文说明图片留在素材库；删的是当前就按规则换一个；删空了自动新建（D-90）", async () => {
  await withBackend(async (backend) => {
    backend.addSession("只有这个", [done("a1", 1, "猫")]);
    const prompts = [];
    const { parts, pane, ready } = makePane({ confirm: async (_doc, opts) => { prompts.push(opts); return true; } }); ready();
    await pane.refresh();
    const item = parts["session-list"].children[0];
    await find(item, (n) => n.attrs?.["aria-label"] === "删除会话：只有这个").click();
    await flush(); await flush();
    assert.equal(prompts[0].title, "删除会话");
    assert.equal(prompts[0].message, "确定删除「只有这个」？只删除这个会话分组，其中的图片仍保留在素材库。");
    assert.equal(prompts[0].confirmLabel, "删除");
    assert.equal(backend.sessions.length, 1);
    assert.equal(backend.sessions[0].title, "新会话");
    assert.match(parts.timeline.textContent, /还没有图片/);
  });
});

test("坏文件会话：只有删除按钮，点开说明损坏，「生成图片」禁用（§7.2）", async () => {
  await withBackend(async (backend) => {
    backend.addSession("正常", []);
    const inner = backend.fetch;
    backend.fetch = async (url, options = {}) => {
      if (url === "/api/image-sessions" && (options.method ?? "GET") === "GET") {
        const list = await (await inner(url, options)).json();
        return { ok: true, status: 200, json: async () => [...list, { id: "deadbeef", corrupt: true }] };
      }
      if (url === "/api/image-sessions/deadbeef") return { ok: false, status: 400, statusText: "", json: async () => ({ error: "会话文件已损坏，无法读取" }) };
      return inner(url, options);
    };
    globalThis.fetch = backend.fetch;
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    const bad = parts["session-list"].children.find((li) => li.dataset.sessionId === "deadbeef");
    assert.match(bad.textContent, /无法读取的会话.*文件已损坏/);
    assert.equal(find(bad, (n) => n.attrs?.["aria-label"] === "改名"), null);
    assert.ok(find(bad, (n) => n.attrs?.["aria-label"] === "删除会话：无法读取的会话"));
    await bad.click(); await flush();
    assert.match(parts.timeline.textContent, /这个会话文件已损坏，无法显示。可以删除它，素材库里的图片不受影响。/);
    assert.equal(parts.start.disabled, true);
    assert.equal(parts["hint-text"].textContent, "请选择其他会话或新建一个");
  });
});

test("会话列表读不出来：说明原因并给重试；「生成图片」禁用（§7.2）", async () => {
  const previous = globalThis.fetch;
  let fail = true;
  const backend = fakeBackend();
  globalThis.fetch = async (url, options) => (fail && url === "/api/image-sessions"
    ? { ok: false, status: 500, statusText: "Internal Server Error", json: async () => ({ error: "磁盘读不出来" }) }
    : backend.fetch(url, options));
  try {
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    assert.match(parts["session-list"].textContent, /会话列表读不出来：磁盘读不出来/);
    assert.equal(parts.start.disabled, true);
    assert.equal(parts["hint-text"].textContent, "会话还没加载好");
    fail = false;
    await button(parts["session-list"], "重试").click();
    await flush(); await flush();
    assert.equal(parts["session-list"].children[0].attrs["aria-current"], "true");
    assert.equal(parts.start.disabled, false);
  } finally { globalThis.fetch = previous; }
});

test("会话已被删除时点生成：切到别的会话并说明，不留卡片（D-88）", async () => {
  await withBackend(async (backend) => {
    backend.addSession("还在的", []);
    const gone = backend.addSession("要被删的", []);
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    assert.equal(parts["session-list"].children[0].dataset.sessionId, gone.id);
    backend.sessions.splice(backend.sessions.indexOf(gone), 1);
    parts.prompt.value = "猫";
    await parts.start.click();
    assert.equal(parts.error.textContent, "这个会话已被删除，已切到「还在的」，请重新点「生成图片」");
    assert.equal(parts["session-list"].children.length, 1);
  });
});

test("素材库回填：会话还在就打开并选中那张、执行「在这张基础上改」；否则停在当前会话（D-94、D-95）", async () => {
  await withBackend(async (backend) => {
    const a = backend.addSession("甲", [done("a1", 11, "甲一"), done("a2", 22, "甲二")]);
    backend.addSession("乙", []);
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    await pane.applyFill({ pane: "image", session_id: a.id, attempt_id: "a1", fields: { prompt: "甲一", width: 1024, height: 1024, steps: 40, seed: 11 } });
    assert.equal(parts["session-list"].children.find((li) => li.attrs["aria-current"] === "true").dataset.sessionId, a.id);
    assert.equal(cards(parts)[0].attrs["aria-expanded"], "true");
    assert.equal(parts["refine-text"].textContent, "以第 1 次为底稿");
    assert.equal(parts.seed.value, "11");
    const sessionsBefore = backend.sessions.length;
    await pane.applyFill({ pane: "image", session_id: "gone", attempt_id: "x", fields: { prompt: "旧图", width: 512, height: 768, steps: 20, seed: 5 } });
    assert.equal(backend.sessions.length, sessionsBefore, "不新建会话");
    assert.equal(parts.prompt.value, "旧图"); assert.equal(parts.width.value, "512"); assert.equal(parts.seed.value, "5");
    assert.equal(parts["refine-text"].textContent, "沿用素材库里这张的构图");
  });
});

test("需要模型、运行环境和仲裁同时就绪，轮询不能误解禁（§7.6 优先级）", async () => {
  await withBackend(async () => {
    const { parts, pane, ready } = makePane();
    await pane.refresh();
    assert.equal(parts.start.disabled, true);
    ready(); assert.equal(parts.start.disabled, false);
    pane.setModelStatus({ state: "partial" });
    pane.setHeavyAllowed(true);
    assert.equal(parts.start.disabled, true);
    assert.match(parts["hint-text"].textContent, /不完整/);
    assert.match(parts.model.textContent, /不完整/);
    ready(); pane.setRuntimeStatus({ present: false, detail: "运行环境缺失" });
    assert.equal(parts.start.disabled, true);
    assert.equal(parts["hint-text"].textContent, "运行环境缺失");
    pane.setRuntimeStatus({ present: true }); pane.setModelStatus({ state: "missing" });
    assert.equal(parts["hint-text"].textContent, "尚未安装图片模型，请到「资源」页下载");
    ready(); assert.equal(parts.hint.hidden, true);
  });
});

test("提交中阻止双击，即使仲裁轮询暂时空闲", async () => {
  await withBackend(async (backend) => {
    const { parts, pane, ready } = makePane(); ready();
    await pane.refresh();
    let release; let calls = 0;
    const inner = backend.fetch;
    globalThis.fetch = async (url, options) => {
      if (url === "/api/media/image") { calls += 1; await new Promise((resolve) => { release = resolve; }); }
      return inner(url, options);
    };
    parts.prompt.value = "猫";
    const first = parts.start.click();
    await flush();
    assert.equal(parts["hint-text"].textContent, "正在提交…");
    pane.setHeavyAllowed(true);
    await parts.start.click();
    assert.equal(calls, 1);
    release(); await first;
    assert.equal(parts.start.disabled, true, "作业已在跑");
  });
});

test("内存不足被拒时先确认再以 force 重提；取消则什么都不写（D-49）", async () => {
  await withBackend(async (backend) => {
    let answer = false; const asked = [];
    const { parts, pane, ready } = makePane({ confirm: async (_doc, opts) => { asked.push(opts); return answer; } }); ready();
    await pane.refresh();
    const bodies = [];
    backend.startResult = (body) => {
      bodies.push(body);
      if (!body.force) return { ok: false, status: 409, statusText: "", json: async () => ({ error: { code: "insufficient_memory", message: "需 40 GB，可用 20 GB" } }) };
      backend.startResult = null;
      return backend.fetch("/api/media/image", { method: "POST", body: JSON.stringify(body) });
    };
    parts.prompt.value = "猫";
    await parts.start.click();
    assert.equal(asked[0].title, "内存可能不足"); assert.equal(asked[0].confirmLabel, "仍要生成");
    assert.equal(cards(parts).length, 0);
    answer = true;
    await parts.start.click();
    assert.equal(bodies.at(-1).force, true);
    assert.equal(cards(parts).length, 1);
  });
});
