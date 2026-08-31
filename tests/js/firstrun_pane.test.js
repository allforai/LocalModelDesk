import test from "node:test";
import assert from "node:assert/strict";

class Element {
  constructor() { this.value = ""; this.textContent = ""; this.listeners = {}; }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { return this.listeners.click?.(); }
}

function makePane(mode = "point") {
  const controls = new Map();
  for (const name of ["models-root", "complete", "legacy", "adopt", "error"]) {
    controls.set(`[data-fr-${name}]`, new Element());
  }
  const selectedMode = new Element();
  selectedMode.value = mode;
  return {
    controls,
    root: { querySelector: (selector) => selector === 'input[name="fr-mode"]:checked' ? selectedMode : controls.get(selector) },
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
