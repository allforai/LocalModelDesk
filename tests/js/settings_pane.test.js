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
  for (const name of ["enabled", "host", "port", "save", "listening", "error", "openai-url", "anthropic-url", "lan-note", "auth-warning", "copy-openai", "copy-anthropic", "models-root", "models-apply", "models-scan", "models-reset", "models-result"]) {
    controls.set(`[data-settings-${name}]`, new Element());
  }
  return { controls, root: { querySelector: (selector) => controls.get(selector) } };
}

test("settings 面板两步保存，并以 apply 后的实测状态、URL 与无鉴权警示刷新", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method, options.body]);
    if (path === "/api/config" && options.method === "GET") return new Response(JSON.stringify({ models_root: "/models" }), { status: 200 });
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
    assert.equal(controls.get("[data-settings-lan-note]").textContent, "开启对外接口并「保存并应用」后，这里会显示可复制的地址。");
    // 未监听（含绑定失败）时不展示无鉴权警示与 base URL 区（G30 G27）。
    assert.equal(controls.get("[data-settings-auth-warning]").hidden, true);
    assert.equal(controls.get("[data-settings-openai-url]").hidden, true);
    assert.equal(controls.get("[data-settings-auth-warning]").textContent, "");

    controls.get("[data-settings-enabled]").checked = false;
    controls.get("[data-settings-host]").value = " 127.0.0.1 ";
    controls.get("[data-settings-port]").value = "9001";
    await controls.get("[data-settings-save]").click();
    assert.deepEqual(calls, [
      ["/api/gateway/config", "GET", undefined],
      ["/api/config", "GET", undefined],
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
    if (path === "/api/config" && (options.method ?? "GET") === "GET") return new Response(JSON.stringify({ models_root: "/models" }), { status: 200 });
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

test("settings 面板可扫描、应用并重新进入模型目录设置", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  let reset = 0;
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method ?? "GET", options.body]);
    if (path === "/api/gateway/config") return new Response(JSON.stringify({ config: {}, status: {} }), { status: 200 });
    if (path === "/api/config" && (options.method ?? "GET") === "GET") return new Response(JSON.stringify({ models_root: "/wrong" }), { status: 200 });
    if (path === "/api/models/discover") return new Response(JSON.stringify({ found: true, models_root: "/found", candidates: [{ model_keys: ["h3", "glm"] }] }), { status: 200 });
    if (path === "/api/first-run") return new Response(JSON.stringify({ models_root: "/manual" }), { status: 200 });
    return new Response(JSON.stringify({ first_run_done: false }), { status: 200 });
  };
  try {
    const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
    const { root, controls } = makePane();
    const pane = createSettingsPane(root, { onReset: () => { reset += 1; } });
    await pane.init();
    assert.equal(controls.get("[data-settings-models-root]").value, "/wrong");
    await controls.get("[data-settings-models-scan]").click();
    assert.equal(controls.get("[data-settings-models-root]").value, "/found");
    assert.match(controls.get("[data-settings-models-result]").textContent, /识别 2 个模型/);
    controls.get("[data-settings-models-root]").value = "/manual";
    await controls.get("[data-settings-models-apply]").click();
    await controls.get("[data-settings-models-reset]").click();
    assert.equal(reset, 1);
    assert.ok(calls.some(([path]) => path === "/api/models/discover"));
    assert.ok(calls.some(([path]) => path === "/api/first-run"));
    assert.ok(calls.some(([path, method, body]) => path === "/api/config" && method === "PUT" && body === '{"first_run_done":false}'));
  } finally { globalThis.fetch = oldFetch; }
});

test("端口越界时不发请求并给出中文错误", async () => {
  const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
  const { root, controls } = makePane();
  const previous = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; return new Response("{}", { status: 200 }); };
  try {
    const pane = createSettingsPane(root);
    controls.get("[data-settings-port]").value = "99999";
    await controls.get("[data-settings-save]").click();
    assert.equal(calls, 0);
    assert.equal(controls.get("[data-settings-error]").textContent, "端口须在 1 到 65535 之间");
  } finally { globalThis.fetch = previous; }
});

test("未监听时隐藏无鉴权警告与 base URL 区", async () => {
  const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
  const { root, controls } = makePane();
  const previous = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => new Response(JSON.stringify(
    path === "/api/config"
      ? { models_root: "/m" }
      : {
          config: { enabled: false, host: "0.0.0.0", port: 8770 },
          status: {
            enabled: false, listening: false, host: "0.0.0.0", port: 8770,
            lan_host: "192.168.1.2", auth: "none", last_error: null,
          },
        }), { status: 200 });
  try {
    const pane = createSettingsPane(root);
    await pane.init();
    assert.equal(controls.get("[data-settings-auth-warning]").hidden, true);
    assert.equal(controls.get("[data-settings-openai-url]").hidden, true);
    assert.equal(controls.get("[data-settings-copy-openai]").hidden, true);
  } finally { globalThis.fetch = previous; }});

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

test("未监听时地址区显示引导文案而不是空白（F15）", async () => {
  const oldFetch = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    if (path === "/api/config" && (options.method ?? "GET") === "GET") return new Response(JSON.stringify({ models_root: "/models" }), { status: 200 });
    return new Response(JSON.stringify({
      config: { enabled: false, host: "0.0.0.0", port: 8770 },
      status: { enabled: false, listening: false, host: "0.0.0.0", port: 8770, auth: "none", last_error: null },
    }), { status: 200 });
  };
  try {
    const { createSettingsPane } = await import("../../desk/static/js/panes/settings.js");
    const { root, controls } = makePane();
    await createSettingsPane(root).init();
    const note = controls.get("[data-settings-lan-note]");
    assert.equal(note.hidden, false);
    assert.equal(note.textContent, "开启对外接口并「保存并应用」后，这里会显示可复制的地址。");
    assert.equal(controls.get("[data-settings-openai-url]").hidden, true);
  } finally { globalThis.fetch = oldFetch; }
});
