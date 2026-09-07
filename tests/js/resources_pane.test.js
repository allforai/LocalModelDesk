import test from "node:test";
import assert from "node:assert/strict";
import { createResourcesPane } from "../../desk/static/js/panes/resources.js";

class FakeElement {
  constructor(tagName = "div") { this.tagName = tagName; this.children = []; this.listeners = {}; this.textContent = ""; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { return this.listeners.click?.({ preventDefault() {} }); }
}

function find(node, predicate) {
  if (predicate(node)) return node;
  for (const child of node.children) { const found = find(child, predicate); if (found) return found; }
  return null;
}

test("resources 面板渲染三态、磁盘占用和可展开的缺失清单", async (t) => {
  const originalFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (path) => ({ ok: true, json: async () => {
    if (path === "/api/resources/catalog") return [
      { key: "present", name: "已齐", gb: 2 }, { key: "partial", name: "未完", gb: 3 }, { key: "missing", name: "未下", gb: 4 },
    ];
    if (String(path).startsWith("/api/resources/status")) return { models: [
      { key: "present", state: "present", disk_bytes: 2048 },
      { key: "partial", state: "partial", percent: 40, disk_bytes: 1024, gaps: [{ path: "weights.bin", expected_size: 10, local_size: 4 }] },
      { key: "missing", state: "missing", disk_bytes: 0 },
    ] };
    return { free_bytes: 2048, total_bytes: 4096, per_model: {} };
  }});
  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "list", "error", "disk"].map((name) => [name, new FakeElement()]));
  const root = new FakeElement(); root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-res-(.+)\]/)[1]];
  const pane = createResourcesPane(root);

  await pane.refresh();

  assert.equal(elements.list.children.length, 3);
  assert.match(elements.list.children[0].children[1].textContent, /齐/);
  assert.match(elements.list.children[1].children[1].textContent, /一半 40%/);
  assert.equal(find(elements.list.children[1], (el) => el.tagName === "details").children[1].children[0].textContent, "weights.bin");
  assert.match(elements.disk.textContent, /可用 2 KiB/);
  assert.ok(find(elements.list.children[2], (el) => el.tagName === "button" && el.textContent === "下载"));
});

test("resources 面板将下载、续传、取消和删除操作路由到资源 API", async (t) => {
  const originalFetch = globalThis.fetch;
  const calls = [];
  let running = false;
  t.after(() => { globalThis.fetch = originalFetch; });
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options]);
    return { ok: true, json: async () => {
      if (path === "/api/resources/catalog") return [
        { key: "present", name: "已齐", gb: 1 }, { key: "partial", name: "未完", gb: 1 },
        { key: "running", name: "进行中", gb: 1 }, { key: "missing", name: "未下", gb: 1 },
      ];
      if (String(path).startsWith("/api/resources/status")) return { download: running ? { state: "running", key: "running" } : null, models: [
        { key: "present", state: "present", disk_bytes: 1 }, { key: "partial", state: "partial", percent: 1, disk_bytes: 1 },
        { key: "running", state: "partial", percent: 1, disk_bytes: 1 }, { key: "missing", state: "missing", disk_bytes: 0 },
      ] };
      return { free_bytes: 1, total_bytes: 2 };
    }};
  };
  const doc = { createElement: (tag) => new FakeElement(tag) };
  const elements = Object.fromEntries(["refresh", "list", "error", "disk"].map((name) => [name, new FakeElement()]));
  const root = new FakeElement(); root.ownerDocument = doc;
  root.querySelector = (selector) => elements[selector.match(/data-res-(.+)\]/)[1]];
  const pane = createResourcesPane(root);
  await pane.refresh();

  await find(elements.list.children[0], (el) => el.tagName === "button" && el.textContent === "删除").click();
  await find(elements.list.children[1], (el) => el.tagName === "button" && el.textContent === "续传").click();
  await find(elements.list.children[3], (el) => el.tagName === "button" && el.textContent === "下载").click();
  running = true;
  await pane.refresh();
  await find(elements.list.children[2], (el) => el.tagName === "button" && el.textContent === "取消").click();
  assert.deepEqual(calls.filter(([path, options]) => options.method === "POST").map(([path, options]) => [path, options.body]), [
    ["/api/resources/delete", '{"key":"present","confirm":"present"}'],
    ["/api/resources/download", '{"key":"partial"}'],
    ["/api/resources/download", '{"key":"missing"}'],
    ["/api/resources/download/cancel", undefined],
  ]);
});

class Element { constructor(tag = "div") { this.tagName = tag; this.dataset = {}; this.textContent = ""; this.children = []; this.listeners = {}; this.disabled = false; this.className = ""; this.title = ""; this.hidden = false; }
  append(...n) { this.children.push(...n); } replaceChildren(...n) { this.children = n; }
  addEventListener(t, l) { this.listeners[t] = l; } click() { return this.listeners.click?.(); } }
function makePane() {
  const parts = { "res-refresh": new Element("button"), "res-list": new Element("ul"), "res-error": new Element("p"), "res-disk": new Element("span") };
  return { parts, root: { ownerDocument: { body: new Element("body"), createElement: (t) => new Element(t) }, querySelector: (s) => parts[s.match(/^\[data-([\w-]+)\]$/)[1]] } };
}

test("点『重新校验』发 refresh=1，按钮期间禁用并显示校验中", async () => {
  const { root, parts } = makePane();
  const urls = []; const releases = [];
  const previous = globalThis.fetch;
  globalThis.fetch = (url) => {
    urls.push(String(url));
    return new Promise((resolve) => {
      releases.push(() => resolve({ ok: true, status: 200, json: async () => (String(url).includes("catalog") ? [] : { models: [], disk: { free_bytes: 1, total_bytes: 2 } }) }));
    });
  };
  try {
    createResourcesPane(root);
    const clicking = parts["res-refresh"].click();
    // The refresh button, per Task 16's UI note, wraps its label in a
    // `[data-label]` span; the test double has no querySelector so the
    // implementation falls back to the button's own textContent.
    assert.equal(parts["res-refresh"].disabled, true);
    assert.equal(parts["res-refresh"].textContent, "校验中…");
    while (releases.length < 4) await Promise.resolve();
    for (const release of releases) release();
    await clicking;
    assert.ok(urls.some((u) => u.includes("/api/resources/status?refresh=1")));
    assert.equal(parts["res-refresh"].disabled, false);
    assert.equal(parts["res-refresh"].textContent, "重新校验");
  } finally { globalThis.fetch = previous; }
});

test("删除按钮带 btn-danger，下载带 btn-primary", async () => {
  const { root, parts } = makePane();
  const previous = globalThis.fetch;
  globalThis.fetch = async (url) => ({ ok: true, status: 200, json: async () => String(url).includes("catalog") ? [{ key: "glm", name: "GLM", gb: 16.9 }] : String(url).includes("download") ? { state: "idle" } : { models: [{ key: "glm", state: "partial", percent: 40, disk_bytes: 10, bytes_expected: 20 }], disk: { free_bytes: 1, total_bytes: 2 } } });
  try {
    const pane = createResourcesPane(root); await pane.refresh();
    const li = parts["res-list"].children[0];
    const buttons = li.children.at(-1).children;
    assert.equal(buttons.find((b) => b.textContent === "删除").className.includes("btn-danger"), true);
    assert.equal(buttons.find((b) => b.textContent === "续传").className.includes("btn-primary"), true);
  } finally { globalThis.fetch = previous; }
});

test("每行只渲染一次名称与状态", async () => {
  const { root, parts } = makePane();
  const previous = globalThis.fetch;
  globalThis.fetch = async (url) => ({ ok: true, status: 200, json: async () => String(url).includes("catalog") ? [{ key: "glm", name: "GLM", gb: 16.9 }] : String(url).includes("download") ? { state: "idle" } : { models: [{ key: "glm", state: "present", disk_bytes: 10, bytes_expected: 10 }], disk: { free_bytes: 1, total_bytes: 2 } } });
  try {
    const pane = createResourcesPane(root); await pane.refresh();
    const li = parts["res-list"].children[0];
    assert.equal(li.textContent, "");
    assert.equal(li.children.filter((c) => c.textContent.includes("GLM")).length, 1);
  } finally { globalThis.fetch = previous; }
});
