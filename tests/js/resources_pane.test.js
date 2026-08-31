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
  assert.match(elements.list.children[0].textContent, /齐/);
  assert.match(elements.list.children[1].textContent, /一半 40%/);
  assert.equal(find(elements.list.children[1], (el) => el.tagName === "details").children[1].children[0].textContent, "weights.bin");
  assert.match(elements.disk.textContent, /可用 2 KB/);
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
