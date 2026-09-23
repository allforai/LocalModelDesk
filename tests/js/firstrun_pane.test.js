import test from "node:test";
import assert from "node:assert/strict";

const GIB = 1024 ** 3;

class Element {
  constructor(tag = "div") {
    this.tagName = tag; this.value = ""; this.textContent = ""; this.listeners = {};
    this.hidden = false; this.children = []; this.className = ""; this.attrs = {};
  }
  addEventListener(type, listener) { this.listeners[type] = listener; }
  click() { return this.listeners.click?.(); }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this.children = nodes; }
  setAttribute(name, value) { this.attrs[name] = value; }
}

const CONTROL_NAMES = [
  "models-root", "complete", "legacy", "adopt", "error", "keep-card", "keep-note", "keep", "found",
  "setup", "report", "report-summary", "report-list", "report-error", "report-continue",
];

function makePane(mode = "point") {
  const controls = new Map();
  for (const name of CONTROL_NAMES) controls.set(`[data-fr-${name}]`, new Element());
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

function catalogFetch(calls, models) {
  return async (path, options = {}) => {
    calls.push([path, options.method, options.body]);
    if (path === "/api/resources/catalog") return new Response(JSON.stringify(models), { status: 200 });
    return new Response(JSON.stringify({ first_run_done: true }), { status: 200 });
  };
}

test("firstrun 面板用预填目录完成首运，先看适配报告，点进入台面才算完", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = catalogFetch(calls, [
    { key: "glm", name: "GLM", fit: { level: "fits", needed_bytes: 16 * GIB, available_bytes: 100 * GIB, headroom_bytes: 84 * GIB, shortfall_bytes: 0 } },
  ]);
  try {
    const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
    const { root, controls } = makePane();
    let done = 0;
    const pane = createFirstRunPane(root, { onDone: () => { done += 1; } });
    pane.init({ models_root: "/default/models" });
    assert.equal(controls.get("[data-fr-models-root]").value, "/default/models");
    controls.get("[data-fr-models-root]").value = "  /external/models  ";
    await controls.get("[data-fr-complete]").click();

    assert.deepEqual(calls[0], ["/api/first-run", "POST", JSON.stringify({ models_root: "/external/models" })]);
    assert.equal(done, 0, "选完目录先看报告，不直接进台面");
    assert.equal(controls.get("[data-fr-setup]").hidden, true);
    assert.equal(controls.get("[data-fr-report]").hidden, false);
    assert.equal(controls.get("[data-fr-report-list]").children.length, 1);
    assert.equal(controls.get("[data-fr-report-list]").children[0].textContent, "GLM");

    await controls.get("[data-fr-report-continue]").click();
    assert.equal(done, 1);
  } finally { globalThis.fetch = oldFetch; }
});

test("firstrun 面板按所选模式收编，错误原样显示且不离开本页", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options = {}) => {
    calls.push([path, options.method, options.body]);
    if (path === "/api/adopt") {
      const attempt = calls.filter(([p]) => p === "/api/adopt").length;
      if (attempt === 1) return new Response(JSON.stringify({ first_run_done: true }), { status: 200 });
      return new Response(JSON.stringify({ error: { code: "no_space", message: "空间不足：还差 1 GB" } }), { status: 400 });
    }
    return new Response(JSON.stringify([]), { status: 200 });   // 成功那次收编后会拉一次目录看报告
  };
  try {
    const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
    const { root, controls } = makePane("point");
    let done = 0;
    createFirstRunPane(root, { onDone: () => { done += 1; } });
    controls.get("[data-fr-legacy]").value = " /old/models ";
    await controls.get("[data-fr-adopt]").click();
    const adoptCalls = calls.filter(([p]) => p === "/api/adopt");
    assert.deepEqual(adoptCalls[0], ["/api/adopt", "POST", JSON.stringify({ legacy_root: "/old/models", mode: "point" })]);
    assert.equal(done, 0, "收编成功先看报告，不直接进台面");

    // 报告页替换掉了收编卡片，第二次点收编要先切回设置页；这条用例只关心
    // 「失败原样显示在本页」，不再重复走一遍报告流程。
    controls.get("[data-fr-setup]").hidden = false;
    controls.get("[data-fr-report]").hidden = true;
    root.querySelector = (selector) => selector === 'input[name="fr-mode"]:checked' ? { value: "move" } : controls.get(selector);
    await controls.get("[data-fr-adopt]").click();
    const adoptCalls2 = calls.filter(([p]) => p === "/api/adopt");
    assert.deepEqual(adoptCalls2[1], ["/api/adopt", "POST", JSON.stringify({ legacy_root: "/old/models", mode: "move" })]);
    assert.equal(controls.get("[data-fr-error]").textContent, "空间不足：还差 1 GB");
    assert.equal(done, 0);
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
  assert.equal(items[0].children[1].attrs["aria-label"], "填入 /Users/me/LocalModelDesk");
  items[0].children[1].click();
  assert.equal(legacy.value, "/Users/me/LocalModelDesk");
  assert.equal(controls.get("[data-fr-keep-card]").hidden, true);
});

test("当前目录已有模型时可以原样返回台面，同样先看报告", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = catalogFetch(calls, []);
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

    assert.deepEqual(calls[0], ["/api/first-run", "POST", JSON.stringify({ models_root: "/Users/me/LocalModelDesk" })]);
    assert.equal(done, 0);
    await controls.get("[data-fr-report-continue]").click();
    assert.equal(done, 1);
  } finally { globalThis.fetch = oldFetch; }
});

test("机器能力算不出来时报告老实说不知道，不推荐任何模型", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = catalogFetch(calls, [
    { key: "glm", name: "GLM", fit: { level: "unknown" } },
    { key: "h3", name: "H3", fit: { level: "unknown" } },
  ]);
  try {
    const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
    const { root, controls } = makePane();
    createFirstRunPane(root, { onDone() {} });
    await controls.get("[data-fr-complete]").click();

    assert.equal(controls.get("[data-fr-report-list]").children.length, 0);
    assert.match(controls.get("[data-fr-report-summary]").textContent, /算不出|不知道|说不准/);
  } finally { globalThis.fetch = oldFetch; }
});

test("适配报告读取失败不拦着首运——报错误，继续按钮仍能进台面", async () => {
  const oldFetch = globalThis.fetch;
  let n = 0;
  globalThis.fetch = async (path) => {
    n += 1;
    if (path === "/api/first-run") return new Response(JSON.stringify({ first_run_done: true }), { status: 200 });
    return new Response(JSON.stringify({ error: { code: "boom", message: "读取失败" } }), { status: 500 });
  };
  try {
    const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
    const { root, controls } = makePane();
    let done = 0;
    createFirstRunPane(root, { onDone: () => { done += 1; } });
    await controls.get("[data-fr-complete]").click();

    assert.equal(controls.get("[data-fr-setup]").hidden, true);
    assert.equal(controls.get("[data-fr-report]").hidden, false);
    assert.match(controls.get("[data-fr-report-error]").textContent, /读取失败/);
    await controls.get("[data-fr-report-continue]").click();
    assert.equal(done, 1);
  } finally { globalThis.fetch = oldFetch; }
});

test("偏紧的模型也列出但标注偏紧", async () => {
  const oldFetch = globalThis.fetch;
  const calls = [];
  globalThis.fetch = catalogFetch(calls, [
    { key: "glm", name: "GLM", fit: { level: "fits" } },
    { key: "llama70", name: "Llama70", fit: { level: "tight" } },
    { key: "h3", name: "H3", fit: { level: "too_big" } },
  ]);
  try {
    const { createFirstRunPane } = await import("../../desk/static/js/panes/firstrun.js");
    const { root, controls } = makePane();
    createFirstRunPane(root, { onDone() {} });
    await controls.get("[data-fr-complete]").click();

    const items = controls.get("[data-fr-report-list]").children;
    assert.equal(items.length, 2);
    assert.equal(items[0].textContent, "GLM");
    assert.equal(items[1].textContent, "Llama70（偏紧）");
  } finally { globalThis.fetch = oldFetch; }
});
