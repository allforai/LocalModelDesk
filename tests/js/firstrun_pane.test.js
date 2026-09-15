import test from "node:test";
import assert from "node:assert/strict";

class Element {
  constructor(tag = "div") {
    this.tagName = tag; this.value = ""; this.textContent = ""; this.listeners = {};
    this.hidden = false; this.children = []; this.className = "";
  }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { return this.listeners.click?.(); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
}

function makePane(mode = "point") {
  const controls = new Map();
  for (const name of ["models-root", "complete", "legacy", "adopt", "error", "keep-card", "keep-note", "keep", "found"]) {
    controls.set(`[data-fr-${name}]`, new Element());
  }
  const selectedMode = new Element();
  selectedMode.value = mode;
  return {
    controls,
    root: {
      ownerDocument: { createElement: (tag) => new Element(tag) },
      querySelector: (selector) => selector === 'input[name="fr-mode"]:checked' ? selectedMode : controls.get(selector),
    },
  };
}

test("firstrun 面板用预填目录完成首运，成功后进入台面", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method, options.body]);
    return new Response(JSON.stringify({ first_run_done: true }), { status: 200 });
  };
  try {
    const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
    const { root, controls } = makePane();
    let done = 0;
    const pane = createFirstRunPane(root, { onDone: () => { done += 1; } });
    pane.init({ models_root: "/default/models" });
    assert.equal(controls.get("[data-fr-models-root]").value, "/default/models");
    controls.get("[data-fr-models-root]").value = "  /external/models  ";
    await controls.get("[data-fr-complete]").click();
    assert.deepEqual(calls, [["/api/first-run", "POST", JSON.stringify({ models_root: "/external/models" })]]);
    assert.equal(done, 1);
  } finally { globalThis.fetch = oldFetch; }
});

test("firstrun 面板按所选模式收编，错误原样显示且不离开本页", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method, options.body]);
    if (calls.length === 1) return new Response(JSON.stringify({ first_run_done: true }), { status: 200 });
    return new Response(JSON.stringify({ error: { code: "no_space", message: "空间不足：还差 1 GB" } }), { status: 400 });
  };
  try {
    const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
    const { root, controls } = makePane("point");
    let done = 0;
    createFirstRunPane(root, { onDone: () => { done += 1; } });
    controls.get("[data-fr-legacy]").value = " /old/models ";
    await controls.get("[data-fr-adopt]").click();
    assert.deepEqual(calls[0], ["/api/adopt", "POST", JSON.stringify({ legacy_root: "/old/models", mode: "point" })]);
    assert.equal(done, 1);

    root.querySelector = (selector) => selector === 'input[name="fr-mode"]:checked' ? { value: "move" } : controls.get(selector);
    await controls.get("[data-fr-adopt]").click();
    assert.deepEqual(calls[1], ["/api/adopt", "POST", JSON.stringify({ legacy_root: "/old/models", mode: "move" })]);
    assert.equal(controls.get("[data-fr-error]").textContent, "空间不足：还差 1 GB");
    assert.equal(done, 1);
  } finally { globalThis.fetch = oldFetch; }
});

test("发现的目录列成可点的建议，不再悄悄填进收编框", async () => {
  const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
  const { root, controls } = makePane();
  const pane = createFirstRunPane(root, { onDone() {} });
  pane.init({ models_root: "/data/models", discovered: ["/data/models", "/Users/me/LocalModelDesk"], models_root_models: [] });

  const legacy = controls.get("[data-fr-legacy]");
  assert.equal(legacy.value, "");
  const items = controls.get("[data-fr-found]").children;
  assert.equal(items.length, 1);
  assert.equal(items[0].children[0].textContent, "/Users/me/LocalModelDesk");
  assert.equal(items[0].children[1].textContent, "填入");
  items[0].children[1].click();
  assert.equal(legacy.value, "/Users/me/LocalModelDesk");
  assert.equal(controls.get("[data-fr-keep-card]").hidden, true);
});

test("当前目录已有模型时可以原样返回台面", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.body]);
    return new Response(JSON.stringify({ first_run_done: true }), { status: 200 });
  };
  try {
    const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
    const { root, controls } = makePane();
    let done = 0;
    const pane = createFirstRunPane(root, { onDone: () => { done += 1; } });
    pane.init({ models_root: "/Users/me/LocalModelDesk", discovered: ["/Users/me/LocalModelDesk"], models_root_models: ["glm", "music3"] });

    assert.equal(controls.get("[data-fr-keep-card]").hidden, false);
    assert.equal(controls.get("[data-fr-keep-note]").textContent, "/Users/me/LocalModelDesk 里已有 2 个模型，可以不改目录直接回去。");
    assert.equal(controls.get("[data-fr-found]").children.length, 0);
    controls.get("[data-fr-models-root]").value = "/somewhere/else";
    await controls.get("[data-fr-keep]").click();

    assert.deepEqual(calls, [["/api/first-run", JSON.stringify({ models_root: "/Users/me/LocalModelDesk" })]]);
    assert.equal(done, 1);
  } finally { globalThis.fetch = oldFetch; }
});
