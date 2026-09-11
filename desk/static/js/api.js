// The browser's only HTTP boundary. UI modules consume named operations, never routes.
const ROUTES = {
  config: "/api/config", firstRun: "/api/first-run", adopt: "/api/adopt", discoverModels: "/api/models/discover",
  catalog: "/api/resources/catalog", status: "/api/resources/status",
  download: "/api/resources/download", cancelDownload: "/api/resources/download/cancel",
  deleteModel: "/api/resources/delete", disk: "/api/resources/disk", memory: "/api/memory", deskState: "/api/state",
  llmLoad: "/api/llm/load", llmUnload: "/api/llm/unload", llmStatus: "/api/llm/status",
  chatStream: "/api/llm/chat/stream", video: "/api/media/video", music: "/api/media/music",
  cancelJob: "/api/media/cancel", job: "/api/media/job", outputs: "/api/outputs",
  history: "/api/history", sessions: "/api/sessions", gatewayConfig: "/api/gateway/config",
};

export class DeskApiError extends Error {
  constructor(status, code, message, detail) {
    super(message);
    this.name = "DeskApiError";
    this.status = status;
    this.code = code;
    this.detail = detail;
  }
}

async function toError(response) {
  let code = `http_${response.status}`;
  let message = `${response.status} ${response.statusText}`.trim();
  let detail;
  try {
    const payload = await response.json();
    const error = payload && typeof payload.error === "object" ? payload.error : null;
    if (error) {
      code = error.code || code;
      message = error.message || message;
      detail = error.detail;
    }
  } catch { /* Preserve the HTTP status line for non-JSON responses. */ }
  return new DeskApiError(response.status, code, message, detail);
}

// setRequestTimeout 已删（零调用点，F13 census 2026-09-08）。
const REQUEST_TIMEOUT_MS = 8000;

async function request(path, { method = "GET", body, stream = false } = {}) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }
  let timer = null;
  if (!stream && typeof AbortController === "function") {
    const controller = new AbortController();
    options.signal = controller.signal;
    timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  }
  let response;
  try {
    response = await globalThis.fetch(path, options);
  } catch (error) {
    if (error?.name === "AbortError") throw new DeskApiError(0, "timeout", `请求超时（${REQUEST_TIMEOUT_MS / 1000} 秒无响应）`);
    throw error;
  } finally { if (timer) clearTimeout(timer); }
  if (!response.ok) throw await toError(response);
  return stream ? response.body : response.json();
}

const json = (path, method, body) => request(path, { method, body });
const encoded = (value) => encodeURIComponent(value);

export const readConfig = () => request(ROUTES.config);
export const writeConfig = (patch) => json(ROUTES.config, "PUT", patch);
export const completeFirstRun = (modelsRoot) =>
  json(ROUTES.firstRun, "POST", modelsRoot ? { models_root: modelsRoot } : {});
export const adoptLegacyModels = (legacyRoot, mode) =>
  json(ROUTES.adopt, "POST", { legacy_root: legacyRoot, mode });
export const discoverModels = () => json(ROUTES.discoverModels, "POST");

export const listCatalog = () => request(ROUTES.catalog);
export const verifyAllModels = async (refresh = false) => {
  const [status, progress] = await Promise.all([
    request(`${ROUTES.status}?refresh=${refresh ? 1 : 0}`),
    request(ROUTES.download).catch(() => null),
  ]);
  return { ...status, download: progress?.state ? progress : status.download };
};
export const startDownload = (key) => json(ROUTES.download, "POST", { key });
export const cancelDownload = () => json(ROUTES.cancelDownload, "POST");
export const deleteModel = (key) => json(ROUTES.deleteModel, "POST", { key, confirm: key });
export const diskUsage = () => request(ROUTES.disk);
export const memorySnapshot = () => request(ROUTES.memory);
export const deskState = () => request(ROUTES.deskState);

export const loadLlm = (key) => json(ROUTES.llmLoad, "POST", { key });
export const unloadLlm = () => json(ROUTES.llmUnload, "POST");
export const llmStatus = () => request(ROUTES.llmStatus);
export const chatStream = (messages) => request(ROUTES.chatStream, {
  method: "POST", body: { messages }, stream: true,
});

export const startVideoJob = (params) => json(ROUTES.video, "POST", params);
export async function uploadMediaInput(file) {
  if (!file.size || file.size > 32 * 1024 * 1024) throw new Error("请选择非空且不超过 32 MB 的素材");
  const data = await new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",")[1]);
    reader.onerror = () => reject(new Error("无法读取文件，请重新选择"));
    reader.readAsDataURL(file);
  });
  return json("/api/media/inputs", "POST", { name: file.name, data });
}
export const startMusicJob = (params) => json(ROUTES.music, "POST", params);
export const cancelJob = () => json(ROUTES.cancelJob, "POST");
export const jobStatus = (logFrom = 0, jobId = null) =>
  request(`${ROUTES.job}?log_from=${logFrom}${jobId === null ? "" : `&job_id=${jobId}`}`);

export const listOutputs = () => request(ROUTES.outputs);
export const serveOutput = (name) => `${ROUTES.outputs}/${encoded(name)}`;
export const revealOutput = (name) =>
  json(name ? `${ROUTES.outputs}/${encoded(name)}/reveal` : `${ROUTES.outputs}/reveal`, "POST");
export const listHistory = (limit = 200) => request(`${ROUTES.history}?limit=${limit}`);
export const listChatSessions = () => request(ROUTES.sessions);
export const createChatSession = (init = {}) => json(ROUTES.sessions, "POST", init);
export const updateChatSession = (id, patch) => json(`${ROUTES.sessions}/${encoded(id)}`, "PATCH", patch);
export const deleteChatSession = (id) => json(`${ROUTES.sessions}/${encoded(id)}`, "DELETE");
export const gatewayConfig = (apply = false) => request(ROUTES.gatewayConfig, { method: apply ? "POST" : "GET" });
