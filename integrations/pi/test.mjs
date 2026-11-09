// No inference or network: exercise the provider with Pi's real request converter
// and SSE parser over a mocked desk/gateway. Requires an installed Pi package.
// PI_PACKAGE=/path/to/pi-coding-agent node integrations/pi/test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import path from "node:path";
import { existsSync, mkdtempSync, mkdirSync, writeFileSync, rmSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";

const root = process.env.PI_PACKAGE || "/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent";
const require = createRequire(path.join(root, "package.json"));
const { createJiti } = require("jiti");
// npm may hoist Pi AI, while global/Homebrew installs may nest it.
const ai = require.resolve.paths("@earendil-works/pi-ai")
  .map((base) => path.join(base, "@earendil-works/pi-ai/dist"))
  .find((base) => existsSync(path.join(base, "index.js")));
assert.ok(ai, "Pi AI package must be installed alongside the tested Pi");
const { normalizeContext } = await import(pathToFileURL(path.join(ai, "index.js")));
const source = path.join(import.meta.dirname, "lmdesk.ts");
const tools = [{ name: "read", description: "Read a file", parameters: {
  type: "object", required: ["path"], properties: { path: { type: "string" } },
}}];
const usage = { prompt_tokens: 22, completion_tokens: 11, total_tokens: 33 };
const call = { index: 0, id: "native_read_1", type: "function", function: { name: "read", arguments: '{"path":"a.txt"}' } };
const context = () => normalizeContext({ systemPrompt: "Be helpful.", tools,
  messages: [{ role: "user", content: [{ type: "text", text: "Read a.txt" }], timestamp: 1 }],
});
const response = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json" } });
function sse() {
  return new Response([
    { choices: [{ delta: { role: "assistant", tool_calls: [call] }, finish_reason: null }] },
    { choices: [{ delta: {}, finish_reason: "tool_calls" }], usage },
  ].map((event) => `data: ${JSON.stringify(event)}\n\n`).join("") + "data: [DONE]\n\n",
  { headers: { "content-type": "text/event-stream" } });
}

async function fixture(t, { env = {}, receipt, status, media, precheck, load, gateway } = {}) {
  const previous = { ...process.env };
  const home = mkdtempSync(path.join(tmpdir(), "lmdesk-pi-test-"));
  if (receipt !== undefined) {
    mkdirSync(path.join(home, ".pi/agent"), { recursive: true });
    writeFileSync(path.join(home, ".pi/agent/localmodeldesk.json"), typeof receipt === "string" ? receipt : JSON.stringify(receipt));
  }
  for (const name of ["LMDESK_GATEWAY", "LMDESK_DESK_URL", "LMD_SHELL_PORT"]) delete process.env[name];
  Object.assign(process.env, { HOME: home, LMDESK_AUTOLOAD: "1", LMDESK_LOAD_TIMEOUT_MS: "10000", LMDESK_TOOLS: "", ...env });
  const oldFetch = globalThis.fetch;
  t.after(() => {
    globalThis.fetch = oldFetch;
    // Preserve Node's native env proxy: replacing process.env breaks os.homedir().
    for (const key of Object.keys(process.env)) if (!(key in previous)) delete process.env[key];
    Object.assign(process.env, previous);
    rmSync(home, { recursive: true, force: true });
  });
  let selected = "qwen35";
  const calls = [];
  globalThis.fetch = async (input, init) => {
    const url = new URL(typeof input === "string" ? input : input.url);
    const body = init?.body ? JSON.parse(init.body) : undefined;
    calls.push({ path: url.pathname, url: url.href, body });
    if (url.pathname === "/api/llm/status") return status
      ? status({ selected, calls, signal: init.signal })
      : response({ state: { status: "loaded", model_key: selected } });
    if (url.pathname === "/api/media/job") return media ? media() : response({ status: "idle" });
    if (url.pathname === "/api/agent/precheck") return precheck ? precheck() : response({ ok: true });
    if (url.pathname === "/api/llm/load") {
      selected = body.key;
      return load ? load(body) : response({ state: { status: "loading", model_key: selected } }, 202);
    }
    assert.equal(url.pathname, "/v1/chat/completions", "must never connect directly to mlx or to a cloud service");
    return gateway ? gateway(body) : sse();
  };
  const jiti = createJiti(import.meta.url, { moduleCache: false, fsCache: false, alias: {
    "@earendil-works/pi-ai/compat": path.join(ai, "compat.js"),
    "@earendil-works/pi-ai": path.join(ai, "index.js"),
  }});
  const factory = await jiti.import(source, { default: true });
  let config;
  factory({ on() {}, registerProvider(name, value) { assert.equal(name, "lmdesk"); config = value; } });
  assert.equal(calls.length, 0, "registration and /model discovery must not load weights");
  const model = { ...config.models.find((m) => m.id === "qwen35"), provider: "lmdesk", api: config.api, baseUrl: config.baseUrl };
  const run = async (options = {}, ctx = context()) => {
    const stream = config.streamSimple(model, ctx, { apiKey: "lmdesk", maxRetries: 0, ...options });
    const events = [];
    for await (const event of stream) events.push(event);
    return { events, message: await stream.result() };
  };
  return { calls, run, config, model };
}

test("native tools and real usage pass through; no prompt protocol", async (t) => {
  const f = await fixture(t);
  const { events, message } = await f.run();
  assert.equal(message.stopReason, "toolUse");
  assert.equal(message.usage.input, 22);
  assert.equal(message.usage.output, 11);
  assert.equal(message.content[0].name, "read");
  assert.deepEqual(message.content[0].arguments, { path: "a.txt" });
  assert.equal(events.filter((e) => e.type === "start").length, 1);
  assert.equal(events.filter((e) => e.type === "done").length, 1);
  const request = f.calls.find((c) => c.path === "/v1/chat/completions").body;
  assert.equal(request.tools[0].function.name, "read");
  assert.equal(request.max_tokens, 8192);
  assert.ok(!JSON.stringify(request.messages).includes("<pi_call>"));
  assert.ok(!f.calls.some((c) => c.path === "/api/llm/load"));
});

test("switch loads with origin agent, then sends native request", async (t) => {
  const f = await fixture(t, { status: ({ selected, calls }) => response({ state: {
    status: "loaded", model_key: calls.some((c) => c.path === "/api/llm/load") ? selected : "superqwen",
  } }) });
  const { message } = await f.run();
  assert.equal(message.stopReason, "toolUse");
  assert.deepEqual(f.calls.find((c) => c.path === "/api/llm/load").body, { key: "qwen35", origin: "agent" });
  assert.ok(f.calls.findIndex((c) => c.path === "/api/llm/load") < f.calls.findIndex((c) => c.path === "/v1/chat/completions"));
});

test("memory refusal never loads or sends inference", async (t) => {
  const f = await fixture(t, {
    status: () => response({ state: { status: "idle", model_key: null } }),
    precheck: () => response({ ok: false, release: [], reason: { message: "内存不足" } }),
  });
  const { message } = await f.run();
  assert.equal(message.stopReason, "error");
  assert.match(message.errorMessage, /内存不足/);
  assert.ok(!f.calls.some((c) => ["/api/llm/load", "/v1/chat/completions"].includes(c.path)));
});

test("cancel while loading is aborted, not an error or fake success", async (t) => {
  const controller = new AbortController();
  const f = await fixture(t, {
    status: () => response({ state: { status: "idle", model_key: null } }),
    load: () => { controller.abort(); return response({ state: { status: "loading" } }, 202); },
  });
  const { message } = await f.run({ signal: controller.signal });
  assert.equal(message.stopReason, "aborted");
  assert.ok(!f.calls.some((c) => c.path === "/v1/chat/completions"));
});

test("load timeout also bounds a hung control-plane HTTP request", async (t) => {
  const f = await fixture(t, { env: { LMDESK_LOAD_TIMEOUT_MS: "30" },
    status: ({ signal }) => new Promise((_, reject) => {
      const timer = setTimeout(() => reject(new Error("test guard")), 1000);
      signal.addEventListener("abort", () => { clearTimeout(timer); reject(signal.reason); }, { once: true });
    }),
  });
  const { message } = await f.run();
  assert.equal(message.stopReason, "error");
  assert.match(message.errorMessage, /超时/);
});

test("native call IDs and Unicode tool results survive the follow-up", async (t) => {
  const f = await fixture(t);
  const { message } = await f.run();
  const actualCall = message.content.find((block) => block.type === "toolCall");
  const history = normalizeContext({ systemPrompt: "Be helpful.", tools, messages: [
    { role: "user", content: "Read a.txt", timestamp: 1 }, message,
    { role: "toolResult", toolCallId: actualCall.id, toolName: "read", isError: false,
      content: [{ type: "text", text: "第一行" }], timestamp: 2 },
  ] });
  await f.run({}, history);
  const request = f.calls.filter((c) => c.path === "/v1/chat/completions").at(-1).body;
  const assistant = request.messages.find((m) => m.tool_calls);
  const result = request.messages.find((m) => m.role === "tool");
  assert.equal(assistant.tool_calls[0].id, result.tool_call_id);
  assert.equal(result.content, "第一行");
});

test("media and releasable budget cause waiting, never forced eviction", async (t) => {
  let mediaChecks = 0;
  let budgetChecks = 0;
  const f = await fixture(t, {
    status: ({ calls, selected }) => response({ state: { status: "loaded",
      model_key: calls.some((c) => c.path === "/api/llm/load") ? selected : "superqwen" } }),
    media: () => response({ status: ++mediaChecks === 1 ? "running" : "idle" }),
    precheck: () => response(++budgetChecks === 1
      ? { ok: false, release: [{ kind: "video" }], reason: { message: "busy" } }
      : { ok: true }),
    load: () => { assert.ok(mediaChecks >= 3); assert.ok(budgetChecks >= 2);
      return response({ state: { status: "loading" } }, 202); },
  });
  assert.equal((await f.run()).message.stopReason, "toolUse");
  assert.equal(f.calls.filter((c) => c.path === "/api/llm/load").length, 1);
});

test("failed load reports the desk's error; no inference or cloud fallback", async (t) => {
  const f = await fixture(t, { status: ({ calls }) => response({ state: calls.some((c) => c.path === "/api/llm/load")
    ? { status: "error", model_key: "qwen35", error: { message: "backend failed" } }
    : { status: "idle", model_key: null } }) });
  const { message } = await f.run();
  assert.equal(message.stopReason, "error");
  assert.match(message.errorMessage, /backend failed/);
  assert.ok(!f.calls.some((c) => c.path === "/v1/chat/completions"));
});

test("tool allowlist is applied to native declarations", async (t) => {
  const f = await fixture(t, { env: { LMDESK_TOOLS: "read" } });
  const ctx = normalizeContext({ systemPrompt: "Be helpful.", tools: [
    ...tools, { name: "other", description: "Other tool", parameters: { type: "object" } },
  ], messages: [{ role: "user", content: "Read a.txt", timestamp: 1 }] });
  await f.run({}, ctx);
  assert.deepEqual(f.calls.find((c) => c.path === "/v1/chat/completions").body.tools.map((t) => t.function.name), ["read"]);
});

test("autoload off skips control plane entirely", async (t) => {
  const f = await fixture(t, { env: { LMDESK_AUTOLOAD: "0" } });
  assert.equal((await f.run()).message.stopReason, "toolUse");
  assert.deepEqual(f.calls.map((c) => c.path), ["/v1/chat/completions"]);
});

const installed = { owner: "LocalModelDesk", format: 1, gateway_url: "http://127.0.0.1:18770/v1", desk_url: "http://127.0.0.1:18766" };
test("managed receipt routes both public endpoints without loading at registration", async (t) => {
  const f = await fixture(t, { receipt: installed });
  assert.equal(f.config.baseUrl, installed.gateway_url);
  assert.equal((await f.run()).message.stopReason, "toolUse");
  assert.ok(f.calls.some((c) => c.url === installed.desk_url + "/api/llm/status"));
  assert.ok(f.calls.some((c) => c.url === installed.gateway_url + "/chat/completions"));
});

test("explicit environment endpoints override installed defaults", async (t) => {
  const f = await fixture(t, { receipt: installed, env: { LMDESK_GATEWAY: "http://127.0.0.1:19770/v1", LMD_SHELL_PORT: "19766" } });
  await f.run();
  assert.equal(f.config.baseUrl, "http://127.0.0.1:19770/v1");
  assert.ok(f.calls.some((c) => c.url === "http://127.0.0.1:19766/api/llm/status"));
});

test("corrupt managed config fails clearly rather than silently using the wrong endpoint", async (t) => {
  await assert.rejects(fixture(t, { receipt: "{broken" }), /pi 连接配置无效/);
});

test("all six stable IDs carry full version and use-case names", async (t) => {
  const f = await fixture(t);
  assert.deepEqual(f.config.models.map((m) => m.id), ["qwen38-flash-next", "qwen35", "superqwen", "glm", "gemma", "arete"]);
  const names = Object.fromEntries(f.config.models.map((m) => [m.id, m.name]));
  assert.match(names.qwen35, /35B-A3B.*最推荐编程/);
  assert.match(names.superqwen, /SuperQwen3.8 27B.*省内存/);
  assert.match(names.glm, /GLM 4.7 Flash 30B-A3B/);
  assert.match(names.gemma, /Gemma 4 31B.*看图/);
  assert.match(names.arete, /Arete-27B 4bit.*价值/);
  assert.deepEqual(f.config.models.filter((m) => m.input.includes("image")).map((m) => m.id), ["qwen38-flash-next", "superqwen", "gemma", "arete"]);
  const metadata = JSON.parse(readFileSync(path.join(import.meta.dirname, "../../desk/pi_integration/models.json"), "utf8"));
  for (const row of metadata) {
    const actual = f.config.models.find((m) => m.id === row.key);
    assert.equal(actual.contextWindow, row.context_window);
    assert.deepEqual(actual.input, row.input);
  }
});


test("vision models retain image blocks through Pi real converter", async (t) => {
  const f = await fixture(t);
  Object.assign(f.model, f.config.models.find((m) => m.id === "superqwen"));
  const ctx = normalizeContext({ systemPrompt: "Describe images.", messages: [{ role: "user", content: [
    { type: "text", text: "What is shown?" }, { type: "image", mimeType: "image/png", data: "aGVsbG8=" },
  ], timestamp: 1 }] });
  await f.run({ reasoning: "off" }, ctx);
  const req = f.calls.find((c) => c.path === "/v1/chat/completions").body;
  assert.equal(req.enable_thinking, false);
  assert.ok(req.messages.some((m) => Array.isArray(m.content) && m.content.some((b) => b.type === "image_url")));
  assert.equal(f.config.models.find((m) => m.id === "glm").contextWindow, 202752);
  assert.equal(f.config.models.find((m) => m.id === "gemma").contextWindow, 262144);
});
