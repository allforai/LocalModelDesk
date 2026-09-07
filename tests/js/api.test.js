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
    ["listCatalog", [], "/api/resources/catalog", "GET"],
    ["verifyAllModels", [], "/api/resources/status?refresh=0", "GET"],
    ["verifyAllModels", [true], "/api/resources/status?refresh=1", "GET"],
    ["startDownload", ["glm"], "/api/resources/download", "POST", { key: "glm" }],
    ["cancelDownload", [], "/api/resources/download/cancel", "POST"],
    ["deleteModel", ["glm"], "/api/resources/delete", "POST", { key: "glm", confirm: "glm" }],
    ["diskUsage", [], "/api/resources/disk", "GET"],
    ["memorySnapshot", [], "/api/memory", "GET"],
    ["deskState", [], "/api/state", "GET"],
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
    ["listHistory", [], "/api/history?limit=200", "GET"],
    ["listChatSessions", [], "/api/sessions", "GET"],
    ["createChatSession", [{ title: "Draft" }], "/api/sessions", "POST", { title: "Draft" }],
    ["updateChatSession", ["a/b", { title: "Named" }], "/api/sessions/a%2Fb", "PATCH", { title: "Named" }],
    ["deleteChatSession", ["a/b"], "/api/sessions/a%2Fb", "DELETE"],
    ["gatewayConfig", [], "/api/gateway/config", "GET"],
    ["gatewayConfig", [true], "/api/gateway/config", "POST"],
  ];
  const names = [
    "readConfig", "writeConfig", "completeFirstRun", "adoptLegacyModels", "listCatalog", "verifyAllModels",
    "startDownload", "cancelDownload", "deleteModel", "diskUsage", "memorySnapshot", "deskState", "loadLlm", "unloadLlm",
    "llmStatus", "chatStream", "startVideoJob", "startMusicJob", "cancelJob", "jobStatus", "listOutputs",
    "serveOutput", "listHistory", "listChatSessions", "createChatSession", "updateChatSession", "deleteChatSession", "gatewayConfig",
  ];
  assert.deepEqual(Object.keys(api).sort(), [...names, "DeskApiError", "setRequestTimeout"].sort());
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
  const previous = globalThis.fetch;
  globalThis.fetch = (_url, options = {}) => new Promise((_resolve, reject) => {
    options.signal?.addEventListener("abort", () => reject(new DOMException("aborted", "AbortError")));
  });
  api.setRequestTimeout(20);
  try {
    await assert.rejects(api.deskState(), (error) => error.name === "DeskApiError" && error.code === "timeout");
  } finally { api.setRequestTimeout(8000); globalThis.fetch = previous; }
});
