// 会话式媒体页测试共用的假 DOM、假后端与最小挂载（从 tests/js/image_pane.test.js 顶部复制并参数化；
// 那个文件保留自己的副本，断言冻结，见音乐会话设计 M-04）。
import { createSessionPane } from "../../../desk/static/js/panes/media_session.js";

export class Element {
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
  insertBefore(node, ref) {
    const at = this.children.indexOf(ref);
    node.parentNode = this;
    this.children.splice(at < 0 ? this.children.length : at, 0, node);
    return node;
  }
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

export const walk = (node, visit) => { visit(node); for (const child of node.children ?? []) walk(child, visit); };
export const findAll = (node, pred) => { const out = []; walk(node, (n) => { if (pred(n)) out.push(n); }); return out; };
export const find = (node, pred) => findAll(node, pred)[0] ?? null;
export const byData = (node, key) => find(node, (n) => key in (n.dataset ?? {}));
export const button = (node, text) => find(node, (n) => n.tagName === "button" && n.textContent === text);
export const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

// 主流程可见文字：跳过 hidden 节点与类名匹配 advancedClassRe 的「高级参数」折叠块。
export function mainFlowText(node, advancedClassRe = /image-advanced|attempt-advanced/) {
  if (node.hidden) return "";
  if (node.tagName === "details" && advancedClassRe.test(node.className)) return "";
  const own = node.tagName === "#text" ? node.textContent : node.children.map((c) => mainFlowText(c, advancedClassRe)).join(" ");
  return [own, node.title, node.attrs?.["aria-label"], node.attrs?.placeholder].filter(Boolean).join(" ");
}

// 一个极小的后端：某一种媒体的会话存在内存里，按路由回应；每次调用记下来。
// startResult / composeResult / soundtrackResult 设成函数时，生成 / 合成 / 配乐请求改由它回应（造错误用）。
export function fakeBackend(kind) {
  const state = { sessions: [], calls: [], nextJob: 1, startResult: null, composeResult: null, uploads: 0 };
  const summary = (s) => ({ id: s.id, title: s.title, created: s.created, updated: s.updated,
    attempt_count: s.attempts.length, running: s.attempts.some((a) => a.status === "running"),
    cover: s.attempts.filter((a) => a.status === "done").at(-1)?.output ?? null });
  const reply = (status, body) => ({ ok: status < 400, status, statusText: "", json: async () => body });
  let clock = 0; let nextSession = 1; // 会话 id 不复用：删光后新建的不会与删掉的同名
  const stamp = () => `2026-09-24T10:${String(clock++).padStart(2, "0")}:00`;
  const sessionsUrl = `/api/media-sessions/${kind}`;
  state.addSession = (title = "新会话", attempts = []) => {
    const s = { id: `s${nextSession++}`, title, title_auto: true, created: stamp(), updated: stamp(), attempts };
    state.sessions.push(s);
    return s;
  };
  const addRunning = (s, extra) => {
    const attempt = { id: `a${state.nextJob}`, job_id: state.nextJob, ts: stamp(), status: "running", output: null, error: null, ...extra };
    s.attempts.push(attempt); s.updated = stamp();
    return reply(200, { job_id: state.nextJob++, kind, status: "running", session_id: s.id, attempt_id: attempt.id, log: "" });
  };
  const missing = () => reply(404, { error: { code: "session_not_found", message: "这个会话已被删除，请选择或新建一个会话" } });
  state.fetch = async (url, options = {}) => {
    const method = options.method ?? "GET";
    const body = options.body ? JSON.parse(options.body) : undefined;
    state.calls.push({ url, method, body });
    if (url === sessionsUrl && method === "GET")
      return reply(200, [...state.sessions].sort((a, b) => b.updated.localeCompare(a.updated)).map(summary));
    if (url === sessionsUrl && method === "POST") return reply(200, state.addSession());
    const one = url.startsWith(`${sessionsUrl}/`) ? url.slice(sessionsUrl.length + 1) : null;
    if (one && /^\w+$/.test(one)) {
      const s = state.sessions.find((item) => item.id === one);
      if (!s) return reply(404, { error: `会话不存在：${one}` });
      if (method === "DELETE") { state.sessions.splice(state.sessions.indexOf(s), 1); return reply(200, { deleted: s.id }); }
      if (method === "PATCH") { s.title = body.title; s.title_auto = false; s.updated = stamp(); }
      return reply(200, structuredClone(s));
    }
    if (url === `/api/media/${kind}`) {
      if (state.startResult) return state.startResult(body);
      const s = state.sessions.find((item) => item.id === body.session_id);
      if (!s) return missing();
      const { session_id: _, force: __, ...params } = body;
      if (!s.attempts.length && s.title_auto && typeof body.prompt === "string") s.title = body.prompt.slice(0, 24);
      return addRunning(s, { params });
    }
    if (url === "/api/media/compose" && method === "POST") {
      if (state.composeResult) return state.composeResult(body);
      const s = state.sessions.find((item) => item.id === body.session_id);
      if (!s) return missing();
      return addRunning(s, { op: "compose", params: { parts: body.parts } });
    }
    if (url === "/api/media/soundtrack" && method === "POST") {
      if (state.soundtrackResult) return state.soundtrackResult(body);
      const s = state.sessions.find((item) => item.id === body.session_id);
      if (!s) return missing();
      return addRunning(s, { op: "soundtrack", params: { source: body.source }, refs: body.refs });
    }
    if (url === "/api/media/cancel") return reply(200, { job_id: 1, kind, status: "cancelled" });
    // 素材上传（视频的首帧、尾帧、参考视频）：回一个按次数编号、保留扩展名的 id。
    if (url === "/api/media/inputs" && method === "POST")
      return reply(200, { id: `in${++state.uploads}${String(body.name).match(/\.\w+$/)?.[0] ?? ""}` });
    throw new Error(`unexpected ${method} ${url}`);
  };
  state.finish = (attemptId, patch) => {
    for (const s of state.sessions) for (const a of s.attempts) if (a.id === attemptId) Object.assign(a, patch);
  };
  return state;
}

// 把 fetch 换成假后端跑一段测试。
export async function withBackend(kind, run) {
  const backend = fakeBackend(kind);
  const previous = globalThis.fetch;
  globalThis.fetch = backend.fetch;
  try { await run(backend); } finally { globalThis.fetch = previous; }
}

// 按 dataPrefix 建好控制器要的 data 元素，挂一个最小假页面：renderCard 画一个带 dataset.attemptId 的 li，
// composer 全是空函数（记下 updateAvailability 收到的状态）。options 里的字段覆盖默认值。
export function makeGenericPane(options = {}) {
  const { kind = "music", noun = "歌曲", dataPrefix = kind } = options;
  const names = ["timeline", "session-list", "session-new", "composer", "return", "model", "hint", "hint-text", "error"];
  const parts = Object.fromEntries(names.map((name) => [name, new Element(name === "timeline" ? "div" : "p")]));
  parts.hint.append(parts["hint-text"], parts.return);
  parts.composer.append(parts.hint, parts.error);
  const root = new Element("section");
  root.append(parts["session-new"], parts["session-list"], parts.model, parts.timeline, parts.composer);
  const doc = { body: new Element("body"), createElement: (tag) => new Element(tag) };
  root.ownerDocument = doc;
  const pattern = new RegExp(`^\\[data-${dataPrefix}-([\\w-]+)\\]$`);
  root.querySelector = (selector) => parts[selector.match(pattern)?.[1]] ?? null;
  const seen = { availability: [], switches: 0, starts: [] };
  const pane = createSessionPane(root, {
    kind, noun, dataPrefix,
    emptyLines: ["还没有内容", "在下面写点什么。"],
    modelTexts: { missing: "尚未安装模型", runtime: "运行环境不可用" },
    renderCard: (d, o) => {
      const li = d.createElement("li");
      li.dataset.attemptId = o.attempt.id;
      li.dataset.attemptStatus = o.attempt.status;
      li.dataset.pickIndex = String(o.pickIndex ?? -1);
      if (o.picking) li.dataset.picking = "";
      li.setAttribute("aria-expanded", o.selected || o.attempt.status === "running" ? "true" : "false");
      li.textContent = `${o.index + 1}:${o.attempt.status}`;
      return { node: li };
    },
    composer: {
      startLabel: "生成",
      afterStart: (info) => { seen.starts.push(info); },
      onSessionSwitch: () => { seen.switches += 1; },
      focus: () => {},
      updateAvailability: (state) => { seen.availability.push(state); },
    },
    startJob: (params) => fetch(`/api/media/${kind}`, { method: "POST", body: JSON.stringify(params) })
      .then(async (r) => { const body = await r.json(); if (!r.ok) throw Object.assign(new Error(body.error?.message ?? "失败"), { code: body.error?.code, status: r.status }); return body; }),
    confirm: async () => true,
    ...options,
  });
  return { root, parts, pane, seen, ready() {
    pane.setHeavyAllowed(true); pane.setRuntimeStatus({ present: true }); pane.setModelStatus({ state: "present" });
  } };
}
