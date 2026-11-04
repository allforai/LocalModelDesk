// No inference or network: exercise the provider with Pi's real request converter
// and SSE parser over a mocked desk/gateway. Requires an installed Pi package.
// PI_PACKAGE=/path/to/pi-coding-agent node integrations/pi/test.mjs
import assert from "node:assert/strict";
import test from "node:test";
import { createRequire } from "node:module";
import { pathToFileURL } from "node:url";
import path from "node:path";

const root = process.env.PI_PACKAGE || "/opt/homebrew/lib/node_modules/@earendil-works/pi-coding-agent";
const require = createRequire(path.join(root, "package.json"));
const { createJiti } = require("jiti");
const ai = path.join(root, "node_modules/@earendil-works/pi-ai/dist");
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

async function fixture(t, { env = {}, status, media, precheck, load, gateway } = {}) {
  const previous = { ...process.env };
  Object.assign(process.env, { LMDESK_AUTOLOAD: "1", LMDESK_LOAD_TIMEOUT_MS: "10000", LMDESK_TOOLS: "", ...env });
  const oldFetch = globalThis.fetch;
  t.after(() => { globalThis.fetch = oldFetch; process.env = previous; });
  let selected = "qwen35";
  const calls = [];
  globalThis.fetch = async (input, init) => {
    const url = new URL(typeof input === "string" ? input : input.url);
    const body = init?.body ? JSON.parse(init.body) : undefined;
    calls.push({ path: url.pathname, body });
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
  return { calls, run };
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
