import test from "node:test";
import assert from "node:assert/strict";

class Element {
  constructor() {
    this.value = "";
    this.checked = false;
    this.textContent = "";
    this.className = "";
    this.hidden = false;
    this.dataset = {};
    this.listeners = {};
  }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { return this.listeners.click?.(); }
}

function makePane() {
  const controls = new Map();
  for (const name of ["enabled", "host", "port", "save", "listening", "error", "openai-url", "anthropic-url", "lan-note", "auth-warning", "copy-openai", "copy-anthropic"]) {
    controls.set(`[data-settings-${name}]`, new Element());
  }
  return { controls, root: { querySelector: (selector) => controls.get(selector) } };
}

test("settings 面板两步保存，并以 apply 后的实测状态、URL 与无鉴权警示刷新", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method, options.body]);
    if (options.method === "PUT") return new Response(JSON.stringify({ gateway: { enabled: false, host: "127.0.0.1", port: 9001 } }), { status: 200 });
    return new Response(JSON.stringify({
      config: { enabled: true, host: "0.0.0.0", port: 8770 },
      status: { enabled: true, listening: false, host: "0.0.0.0", port: 8770, auth: "none", last_error: "Address already in use" },
    }), { status: 200 });
  };
  try {
    const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
    const { root, controls } = makePane();
    const pane = createSettingsPane(root);
    await pane.init();

    assert.equal(controls.get("[data-settings-enabled]").checked, true);
    assert.equal(controls.get("[data-settings-listening]").textContent, "未监听");
    assert.equal(controls.get("[data-settings-error]").textContent, "Address already in use");
    assert.equal(controls.get("[data-settings-openai-url]").textContent, "http://<本机局域网地址>:8770/v1");
    assert.equal(controls.get("[data-settings-anthropic-url]").textContent, "http://<本机局域网地址>:8770");
    assert.match(controls.get("[data-settings-lan-note]").textContent, /局域网 IP/);
    assert.match(controls.get("[data-settings-auth-warning]").textContent, /无鉴权/);

    controls.get("[data-settings-enabled]").checked = false;
    controls.get("[data-settings-host]").value = " 127.0.0.1 ";
    controls.get("[data-settings-port]").value = "9001";
    await controls.get("[data-settings-save]").click();
    assert.deepEqual(calls, [
      ["/api/gateway/config", "GET", undefined],
      ["/api/config", "PUT", JSON.stringify({ gateway: { enabled: false, host: "127.0.0.1", port: 9001 } })],
      ["/api/gateway/config", "POST", undefined],
    ]);
  } finally { globalThis.fetch = oldFetch; }
});

test("settings 面板的两条 URL 可分别复制，保存失败原样显示", async () => {
  const oldFetch = globalThis.fetch;
  const oldClipboard = globalThis.navigator?.clipboard;
  const copied = [];
  Object.defineProperty(globalThis, "navigator", { configurable: true, value: { clipboard: { writeText: async (text) => copied.push(text) } } });
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/gateway/config") return new Response(JSON.stringify({
      config: { enabled: true, host: "127.0.0.1", port: 8770 },
      status: { listening: true, host: "127.0.0.1", port: 8770, auth: "none", last_error: null },
    }), { status: 200 });
    return new Response(JSON.stringify({ error: { message: "端口不合法" } }), { status: 400 });
  };
  try {
    const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
    const { root, controls } = makePane();
    const pane = createSettingsPane(root);
    await pane.init();
    await controls.get("[data-settings-copy-openai]").click();
    await controls.get("[data-settings-copy-anthropic]").click();
    await controls.get("[data-settings-save]").click();
    assert.deepEqual(copied, ["http://127.0.0.1:8770/v1", "http://127.0.0.1:8770"]);
    assert.equal(controls.get("[data-settings-error]").textContent, "端口不合法");
  } finally {
    globalThis.fetch = oldFetch;
    Object.defineProperty(globalThis, "navigator", { configurable: true, value: { clipboard: oldClipboard } });
  }
});

test("监听状态用徽标类表达", async () => {
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async () => new Response(JSON.stringify({
    config: { enabled: true, host: "127.0.0.1", port: 8770 },
    status: { enabled: true, listening: true, host: "127.0.0.1", port: 8770, auth: "none", last_error: null },
  }), { status: 200 });
  try {
    const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
    const { root, controls } = makePane();
    const pane = createSettingsPane(root);
    await pane.init();
    assert.equal(controls.get("[data-settings-listening]").className, "badge badge-ok");
  } finally { globalThis.fetch = oldFetch; }
});
