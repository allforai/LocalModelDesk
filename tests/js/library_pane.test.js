import test from "node:test";
import assert from "node:assert/strict";
import { createLibraryPane } from "../../desk/static/js/panes/library.js";

class FakeElement {
  constructor(tagName = "div") {
    this.tagName = tagName;
    this.children = [];
    this.listeners = {};
    this.textContent = "";
  }

  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { this.listeners.click?.({ stopPropagation() {} }); }
}

function find(node, predicate) {
  if (predicate(node)) return node;
  for (const child of node.children) {
    const found = find(child, predicate);
    if (found) return found;
  }
  return null;
}

test("library 面板合并倒序渲染，点击成品就地播放并回填历史参数", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (path) => ({
    ok: true,
    json: async () => path === "/api/outputs"
      ? [
          { name: "video old.mp4", kind: "video", ts: "2026-08-30T10:00:00Z" },
          { name: "orphan.wav", kind: "music", orphan: true, bytes: 1024, ts: "2026-08-31T12:00:00Z" },
        ]
      : [{
          kind: "video", status: "done", ts: "2026-08-31T11:00:00Z", output: "video old.mp4",
          params: { prompt: "海边", width: 768, height: 448, frames: 49, steps: 16 },
        }],
  });

  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "player", "list", "error"]
    .map((name) => [name, new FakeElement()]));
  const root = new FakeElement();
  root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-lib-(.+)\]/)[1]];
  const fills = [];
  const pane = createLibraryPane(root, { applyFill: (plan) => fills.push(plan) });

  await pane.refresh();

  assert.equal(elements.list.children.length, 2);
  assert.equal(elements.list.children[0].className, "card lib-row");
  assert.equal(elements.list.children[0].children[0].children[0].className, "lib-title");
  assert.equal(elements.list.children[0].children[0].children[0].textContent, "orphan.wav");
  assert.equal(elements.list.children[1].children[0].children[0].textContent, "海边");

  elements.list.children[1].click();
  assert.equal(elements.player.children[0].tagName, "video");
  assert.equal(elements.player.children[0].src, "/api/outputs/video%20old.mp4");

  find(elements.list.children[1], (el) => el.tagName === "button" && el.textContent === "回填参数").click();
  assert.deepEqual(fills, [{ pane: "video", fields: { prompt: "海边", width: 768, height: 448, frames: 49, steps: 16 } }]);
});

test("library 面板保留未返回匹配历史的成品", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (path) => ({
    ok: true,
    json: async () => path === "/api/outputs"
      ? [{ name: "unmatched.mp3", kind: "music", ts: "2026-08-31T13:00:00Z" }]
      : [],
  });

  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "player", "list", "error"]
    .map((name) => [name, new FakeElement()]));
  const root = new FakeElement();
  root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-lib-(.+)\]/)[1]];
  const pane = createLibraryPane(root, { applyFill() {} });

  await pane.refresh();

  assert.equal(elements.list.children.length, 1);
  assert.equal(elements.list.children[0].children[0].children[0].textContent, "unmatched.mp3");
  elements.list.children[0].click();
  assert.equal(elements.player.children[0].tagName, "audio");
});

test("每条成品有『在访达中显示』并调用 reveal 接口", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method ?? "GET"]);
    return {
      ok: true,
      json: async () => path === "/api/outputs"
        ? [{ name: "h3-1.mp4", kind: "video", bytes: 1, ts: "2026-09-07T01:00:00" }]
        : [],
    };
  };

  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "player", "list", "error"]
    .map((name) => [name, new FakeElement()]));
  const root = new FakeElement();
  root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-lib-(.+)\]/)[1]];
  const pane = createLibraryPane(root, { applyFill() {} });

  await pane.refresh();

  const buttons = elements.list.children[0].children[1].children;
  assert.ok(buttons.map((b) => b.textContent).includes("在访达中显示"));
  buttons.find((b) => b.textContent === "在访达中显示").click();
  assert.ok(calls.some(([url, method]) => url === "/api/outputs/h3-1.mp4/reveal" && method === "POST"));
});

test("播放时播放器滚入视野且标注正在播放的记录", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (path) => ({
    ok: true,
    json: async () => path === "/api/outputs"
      ? [{ name: "m.wav", kind: "music", bytes: 1, ts: "2026-09-07T01:00:00" }]
      : [],
  });

  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "player", "list", "error"]
    .map((name) => [name, new FakeElement()]));
  const root = new FakeElement();
  root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-lib-(.+)\]/)[1]];
  let scrolled = 0;
  elements.player.scrollIntoView = () => { scrolled += 1; };
  const pane = createLibraryPane(root, { applyFill() {} });

  await pane.refresh();
  elements.list.children[0].click();

  assert.equal(scrolled, 1);
  assert.equal(elements.player.children[1].textContent, "正在播放：m.wav");
});

test("失败记录：标题是人话，原始码收进「详情」（F3）", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (path) => ({ ok: true, json: async () => path === "/api/outputs" ? [] : [{
    kind: "video", status: "failed", ts: "2026-09-07T03:35:00Z", output: null, error: "exit_nonzero: exit 1",
    params: { prompt: "镜头缓慢推近", width: 512, height: 288, frames: 49, steps: 16 } }] });
  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "player", "list", "error"].map((name) => [name, new FakeElement()]));
  const root = new FakeElement(); root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-lib-(.+)\]/)[1]];
  await createLibraryPane(root, { applyFill() {} }).refresh();
  const row = elements.list.children[0];
  const title = find(row, (n) => n.className === "inline-error");
  assert.equal(title.textContent, "生成程序异常退出");
  const details = find(row, (n) => n.tagName === "details");
  assert.ok(details, "缺少详情折叠");
  assert.equal(find(details, (n) => n.tagName === "pre").textContent, "exit_nonzero: exit 1");
});

function makeLibrary(outputs, history) {
  globalThis.fetch = async (path) => ({
    ok: true,
    json: async () => (path === "/api/outputs" ? outputs : history),
  });
  const doc = { createElement: (tag) => new FakeElement(tag) };
  const parts = Object.fromEntries(["refresh", "player", "list", "error"]
    .map((name) => [`lib-${name}`, new FakeElement()]));
  const root = new FakeElement();
  root.ownerDocument = doc;
  root.querySelector = (selector) => parts[`lib-${selector.match(/data-lib-(.+)\]/)[1]}`];
  return { root, parts };
}

test("没有成品时显示引导语", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  const { root, parts } = makeLibrary([], []);
  const pane = createLibraryPane(root, { applyFill() {} });

  await pane.refresh();

  assert.equal(parts["lib-list"].children[0].className, "empty");
  assert.equal(parts["lib-list"].children[0].textContent, "还没有成品。去「视频」或「音乐」面板生成第一件，它会出现在这里。");
});
