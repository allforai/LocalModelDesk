import test from "node:test";
import assert from "node:assert/strict";
import * as api from "../../desk/static/js/api.js";

function withFetch(response, run) {
  const previous = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    const result = {
      ok: response.ok ?? true, status: response.status ?? 200, statusText: response.statusText ?? "OK",
      body: response.stream ?? new ReadableStream(),
      json: async () => {
        if (response.jsonError) throw response.jsonError;
        return response.body ?? { ok: true };
      },
    };
    calls.push({ url, options, result });
    return result;
  };
  return Promise.resolve(run(calls)).finally(() => { globalThis.fetch = previous; });
}

test("每个 api 消费项恰有一个公开函数，且以合同签名发出正确 HTTP 请求", async () => {
  const expected = [
    ["readConfig", [], "/api/config", "GET"],
    ["writeConfig", [{ gateway: { port: 9000 } }], "/api/config", "PUT", { gateway: { port: 9000 } }],
    ["completeFirstRun", ["/models"], "/api/first-run", "POST", { models_root: "/models" }],
    ["adoptLegacyModels", ["/old", "point"], "/api/adopt", "POST", { legacy_root: "/old", mode: "point" }],
    ["discoverModels", [], "/api/models/discover", "POST"],
    ["listCatalog", [], "/api/resources/catalog", "GET"],
    ["verifyAllModels", [], "/api/resources/status?refresh=0", "GET"],
    ["verifyAllModels", [true], "/api/resources/status?refresh=1", "GET"],
    ["startDownload", ["glm"], "/api/resources/download", "POST", { key: "glm" }],
    ["cancelDownload", [], "/api/resources/download/cancel", "POST"],
    ["deleteModel", ["glm"], "/api/resources/delete", "POST", { key: "glm", confirm: "glm" }],
    ["diskUsage", [], "/api/resources/disk", "GET"],
    ["memorySnapshot", [], "/api/memory", "GET"],
    ["deskState", [], "/api/state", "GET"],
    ["budget", [], "/api/budget", "GET"],
    ["loadLlm", ["glm"], "/api/llm/load", "POST", { key: "glm" }],
    ["unloadLlm", [], "/api/llm/unload", "POST"],
    ["llmStatus", [], "/api/llm/status", "GET"],
    ["chatStream", [[{ role: "user", content: "hi" }]], "/api/llm/chat/stream", "POST", { messages: [{ role: "user", content: "hi" }] }],
    ["startVideoJob", [{ prompt: "sky" }], "/api/media/video", "POST", { prompt: "sky" }],
    ["startMusicJob", [{ caption: "calm" }], "/api/media/music", "POST", { caption: "calm" }],
    ["cancelJob", [], "/api/media/cancel", "POST"],
    ["jobStatus", [120, 3], "/api/media/job?log_from=120&job_id=3", "GET"],
    ["jobStatus", [], "/api/media/job?log_from=0", "GET"],
    ["listOutputs", [], "/api/outputs", "GET"],
    ["revealOutput", ["clip.mp4"], "/api/outputs/clip.mp4/reveal", "POST"],
    ["revealOutput", [], "/api/outputs/reveal", "POST"],
    ["listHistory", [], "/api/history?limit=200", "GET"],
    ["listChatSessions", [], "/api/sessions", "GET"],
    ["createChatSession", [{ title: "Draft" }], "/api/sessions", "POST", { title: "Draft" }],
    ["updateChatSession", ["a/b", { title: "Named" }], "/api/sessions/a%2Fb", "PATCH", { title: "Named" }],
    ["deleteChatSession", ["a/b"], "/api/sessions/a%2Fb", "DELETE"],
    ["gatewayConfig", [], "/api/gateway/config", "GET"],
    ["gatewayConfig", [true], "/api/gateway/config", "POST"],
    ["listSkills", [], "/api/skills", "GET"],
    ["rescanSkills", [], "/api/skills/rescan", "POST", {}],
  ];
  const names = [
    "readConfig", "writeConfig", "resetConfig", "completeFirstRun", "adoptLegacyModels", "discoverModels", "listCatalog", "verifyAllModels",
    "startDownload", "cancelDownload", "deleteModel", "diskUsage", "memorySnapshot", "deskState", "budget", "loadLlm", "unloadLlm",
    "llmStatus", "chatStream", "promptAssist", "startVideoJob", "startMusicJob", "cancelJob", "jobStatus", "listOutputs",
    "serveOutput", "revealOutput", "listHistory", "listChatSessions", "createChatSession", "updateChatSession", "deleteChatSession", "gatewayConfig",
    "listSkills", "rescanSkills",
  ];
  assert.deepEqual(Object.keys(api).sort(), [...names, "uploadMediaInput", "DeskApiError"].sort());
  await withFetch({}, async (calls) => {
    for (const [name, args, url, method, body] of expected) {
      const result = await api[name](...args);
      const call = calls.at(-1);
      if (name === "verifyAllModels") {
        assert.equal(calls.at(-2).url, url, name);
        assert.equal(calls.at(-2).options.method, method, name);
        assert.equal(call.url, "/api/resources/download", name);
        continue;
      }
      assert.equal(call.url, url, name);
      assert.equal(call.options.method, method, name);
      assert.deepEqual(call.options.body && JSON.parse(call.options.body), body, name);
      assert.equal(call.options.headers?.["Content-Type"], body === undefined ? undefined : "application/json", name);
      if (name === "chatStream") assert.equal(result, call.result.body);
    }
  });
  assert.equal(api.serveOutput("clip one.mp4"), "/api/outputs/clip%20one.mp4");
});

test("模型状态读取会携带当前下载进度", async () => {
  const previous = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (url) => {
    calls.push(url);
    return {
      ok: true,
      json: async () => url === "/api/resources/status?refresh=0"
        ? { models: [{ key: "glm", state: "partial" }] }
        : { key: "glm", state: "running", percent: 42 },
    };
  };
  try {
    const status = await api.verifyAllModels();
    assert.deepEqual(calls, ["/api/resources/status?refresh=0", "/api/resources/download"]);
    assert.deepEqual(status.download, { key: "glm", state: "running", percent: 42 });
  } finally {
    globalThis.fetch = previous;
  }
});

test("DeskApiError 保留 HTTP 状态与服务端 error 信封", async () => {
  await withFetch({ ok: false, status: 409, body: { error: { code: "media_busy", message: "媒体作业进行中", detail: { holder: "video" } } } }, async () => {
    await assert.rejects(api.loadLlm("glm"), (error) => {
      assert.ok(error instanceof api.DeskApiError);
      assert.equal(error.status, 409);
      assert.equal(error.code, "media_busy");
      assert.equal(error.message, "媒体作业进行中");
      assert.deepEqual(error.detail, { holder: "video" });
      return true;
    });
  });
});

test("DeskApiError 在非 JSON 错误时使用 HTTP 状态行", async () => {
  await withFetch({ ok: false, status: 502, statusText: "Bad Gateway", jsonError: new SyntaxError("not JSON") }, async () => {
    await assert.rejects(api.readConfig(), (error) => {
      assert.equal(error.status, 502);
      assert.equal(error.code, "http_502");
      assert.equal(error.message, "502 Bad Gateway");
      return true;
    });
  });
});

test("挂起的请求在超时后以 timeout 错误拒绝，而不是永远等待", async () => {
  // setRequestTimeout 已删（零调用点，F13）：改为伪造 setTimeout 立即触发，
  // 不依赖模块内固定的超时常量即可验证 abort 路径。
  const previousFetch = globalThis.fetch;
  const previousSetTimeout = globalThis.setTimeout;
  globalThis.fetch = (_url, options = {}) => new Promise((_resolve, reject) => {
    options.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
  });
  globalThis.setTimeout = (fn) => previousSetTimeout(fn, 0);
  try {
    await assert.rejects(api.deskState(), (error) => error.name === "DeskApiError" && error.code === "timeout");
  } finally {
    globalThis.fetch = previousFetch;
    globalThis.setTimeout = previousSetTimeout;
  }
});

test("updateChatSession 可带 keepalive，页面关闭时请求不被浏览器丢弃", async () => {
  const oldFetch = globalThis.fetch;
  const seen = [];
  globalThis.fetch = async (path, options) => { seen.push([path, options]); return new Response("{}", { status: 200 }); };
  try {
    const api = await import("../../desk/static/js/api.js");
    await api.updateChatSession("s1", { messages: [] }, { keepalive: true });
    assert.equal(seen[0][0], "/api/sessions/s1");
    assert.equal(seen[0][1].method, "PATCH");
    assert.equal(seen[0][1].keepalive, true);
  } finally { globalThis.fetch = oldFetch; }
});

test("promptAssist 以 POST 发往 prompt-assist，且不受 8 秒默认超时限制", async () => {
  const oldFetch = globalThis.fetch;
  const oldSetTimeout = globalThis.setTimeout;
  const delays = [];
  globalThis.setTimeout = (fn, ms) => { delays.push(ms); return oldSetTimeout(() => {}, 0); };
  globalThis.fetch = async (path, options) => new Response(JSON.stringify({ path, method: options.method }), { status: 200 });
  try {
    const api = await import("../../desk/static/js/api.js");
    const result = await api.promptAssist({ task: "video", action: "lucky" });
    assert.deepEqual(result, { path: "/api/llm/prompt-assist", method: "POST" });
    assert.deepEqual(delays, [180000]);
  } finally { globalThis.fetch = oldFetch; globalThis.setTimeout = oldSetTimeout; }
});

test("chatStream 把调用方的 AbortSignal 交给 fetch，停止生成时能断开流", async () => {
  const oldFetch = globalThis.fetch;
  const seen = [];
  globalThis.fetch = async (path, options) => { seen.push(options); return new Response("data: {}\n\n", { status: 200 }); };
  try {
    const controller = new AbortController();
    await api.chatStream([{ role: "user", content: "hi" }], { signal: controller.signal });
    assert.equal(seen[0].signal, controller.signal);
  } finally { globalThis.fetch = oldFetch; }
});
