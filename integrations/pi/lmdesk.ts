/**
 * Pi on LocalModelDesk: native OpenAI tool calls through the desk gateway.
 * Control plane: desk API (8766), for automatic loading with agent scheduling.
 * Data plane: gateway (8770), for native tools, actual usage and desk accounting.
 * Never connects to the private mlx port. Requires the tools-capable gateway.
 * Install: copy this file to ~/.pi/agent/extensions/lmdesk.ts, then /reload.
 */
import {
  collapseSystemMessages,
  createAssistantMessageEventStream,
  type AssistantMessage,
  type Model,
  type SimpleStreamOptions,
  type TranscriptContext,
} from "@earendil-works/pi-ai";
import { openAICompletionsApi } from "@earendil-works/pi-ai/compat";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

// Settings installs an exact provider copy plus this managed connection receipt.
// Keep explicit environment overrides; never touch Pi's default model/settings.
function installedDefaults(): { gateway_url?: string; desk_url?: string } {
  try {
    const config = JSON.parse(readFileSync(join(homedir(), ".pi/agent/localmodeldesk.json"), "utf8"));
    if (config.owner !== "LocalModelDesk" || config.format !== 1 ||
        typeof config.gateway_url !== "string" || typeof config.desk_url !== "string") {
      throw new Error("invalid managed connection configuration");
    }
    for (const value of [config.gateway_url, config.desk_url]) {
      const url = new URL(value);
      if (url.protocol !== "http:" || url.username || url.password) throw new Error("invalid local endpoint");
    }
    return config;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === "ENOENT") return {};
    throw new Error("台面 pi 连接配置无效；请在台面设置中重新安装或更新 pi 接入");
  }
}
const defaults = installedDefaults();
const GATEWAY = (process.env.LMDESK_GATEWAY || defaults.gateway_url || "http://127.0.0.1:8770/v1").replace(/\/+$/, "");
const DESK = (process.env.LMDESK_DESK_URL ||
  (process.env.LMD_SHELL_PORT ? `http://127.0.0.1:${process.env.LMD_SHELL_PORT}` : defaults.desk_url) ||
  "http://127.0.0.1:8766").replace(/\/+$/, "");
const AUTOLOAD = process.env.LMDESK_AUTOLOAD !== "0";
const LOAD_TIMEOUT = positiveNumber("LMDESK_LOAD_TIMEOUT_MS", 45 * 60 * 1000);
const MAX_TOKENS = positiveNumber("LMDESK_MAX_TOKENS", 8192);
const ALLOWLIST = (process.env.LMDESK_TOOLS || "").split(",").map((s) => s.trim()).filter(Boolean);
const COST = { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 };
const native = openAICompletionsApi();
const MODELS = [
  ["qwen38-flash-next", "Qwen3.8 Flash Next oQ5e MTP · 综合主力候选·编程与看图"],
  // Keep IDs stable. Names mirror desk/pi_integration/models.json (contract-tested).
  ["qwen35", "Qwen3.6 35B-A3B 8bit · 最推荐编程"],
  ["superqwen", "SuperQwen3.8 27B 4bit · 擅长对话·省内存"],
  ["glm", "GLM 4.7 Flash 30B-A3B 8bit · 快速问答"],
  ["gemma", "Gemma 4 31B 8bit · 擅长看图"],
  ["arete", "Arete-27B 4bit · 价值观对齐·看图"],
];
// Local checkpoint config.json text_config.max_position_embeddings, not a tested
// full-window promise. Actual memory allowance is shown by the desk budget API.
const CAPABILITIES: Record<string, { context: number; vision: boolean }> = {
  "qwen38-flash-next": { context: 262144, vision: true },
  qwen35: { context: 262144, vision: false },
  superqwen: { context: 262144, vision: true },
  glm: { context: 202752, vision: false },
  gemma: { context: 262144, vision: true },
  arete: { context: 262144, vision: true },
};

function positiveNumber(name: string, fallback: number): number {
  const value = Number(process.env[name] ?? fallback);
  if (!Number.isSafeInteger(value) || value <= 0) throw new Error(`${name} must be a positive integer`);
  return value;
}

function debug(message: string) {
  // Never dump prompts, tool arguments, responses or credentials.
  if (process.env.LMDESK_DEBUG === "1") console.error(`[lmdesk] ${message}`);
}

type Status = {
  state: { status: string; model_key: string | null; error?: { message?: string } };
  active_chats?: number;
  ui_chat_recent?: boolean;
};

class DeskError extends Error {
  constructor(message: string, readonly code: string) { super(message); }
}

async function json(path: string, signal: AbortSignal, body?: object): Promise<any> {
  const response = await fetch(`${DESK}${path}`, {
    method: body ? "POST" : "GET",
    headers: { "content-type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
    signal,
  });
  const result = await response.json();
  if (!response.ok) throw new DeskError(result?.error?.message || `desk HTTP ${response.status}`, result?.error?.code || String(response.status));
  return result;
}

function pause(signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    signal.throwIfAborted();
    const abort = () => { clearTimeout(timer); reject(signal.reason); };
    const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, 1000);
    signal.addEventListener("abort", abort, { once: true });
  });
}

/** Same scheduling policy as lmdesk ask: don't evict recent UI chats or media. */
async function ensureResident(key: string, cancel?: AbortSignal, note: (text: string) => void = debug) {
  if (!AUTOLOAD) return;
  const deadline = AbortSignal.timeout(LOAD_TIMEOUT);
  const signal = cancel ? AbortSignal.any([cancel, deadline]) : deadline;
  let requested = false;
  let lastNote = "";
  const report = (text: string) => { if (text !== lastNote) { lastNote = text; note(text); } };
  try {
    for (;;) {
      signal.throwIfAborted();
      const current: Status = await json("/api/llm/status", signal);
      const state = current.state;
      if (!state || typeof state.status !== "string") throw new Error("台面返回了无效的模型状态");
      if (state.status === "loaded" && state.model_key === key) return;
      if (requested && state.status === "error" && state.model_key === key) {
        throw new Error(`台面装载 ${key} 失败：${state.error?.message || "未知错误"}`);
      }
      if (state.status === "loading") {
        report(`正在加载 ${state.model_key || key}…`);
      } else if ((current.active_chats || 0) > 0 || (current.ui_chat_recent && state.status === "loaded")) {
        report("等待台面里的对话结束…");
      } else {
        const job = await json("/api/media/job", signal);
        if (job.status === "running") {
          report("等待媒体任务结束…");
        } else {
          const check = await json(`/api/agent/precheck?op=chat&model=${encodeURIComponent(key)}`, signal);
          if (!check.ok) {
            if (!check.release?.length) throw new Error(`${check.reason?.message || "内存不足"}；请换更小的模型，不会强制加载`);
            report(check.reason?.message || "等待内存释放…");
          } else {
            if (requested && state.status === "idle") throw new Error(`台面装载 ${key} 已被取消`);
            report(`加载 ${key}…`);
            try {
              await json("/api/llm/load", signal, { key, origin: "agent" });
              requested = true;
            } catch (error) {
              if (!(error instanceof DeskError) || !["load_in_progress", "media_busy"].includes(error.code)) throw error;
            }
          }
        }
      }
      await pause(signal);
    }
  } catch (error) {
    if (cancel?.aborted) throw error;
    if (deadline.aborted) throw new Error(`等待台面加载 ${key} 超时（${LOAD_TIMEOUT / 1000}s）；请检查台面窗口`);
    if (error instanceof TypeError) throw new Error(`无法连接台面 ${DESK}；请先打开「本地模型台」`);
    throw error;
  }
}

function codingContext(context: TranscriptContext): TranscriptContext {
  if (!ALLOWLIST.length) return context;
  const collapsed = collapseSystemMessages(context);
  return {
    ...collapsed,
    messages: collapsed.messages.map((message) => message.role === "system"
      ? { ...message, toolsAdded: message.toolsAdded?.filter((tool) => ALLOWLIST.includes(tool.name)) }
      : message),
  };
}

function streamNative(model: Model<any>, context: TranscriptContext, options?: SimpleStreamOptions,
                      note?: (text: string) => void) {
  const stream = createAssistantMessageEventStream();
  (async () => {
    try {
      await ensureResident(model.id, options?.signal, note);
      const upstream: Model<"openai-completions"> = {
        ...model,
        api: "openai-completions",
        // Verified gateway differences; use Pi's built-in conversion/parser.
        compat: {
          maxTokensField: "max_tokens",
          supportsStore: false,
          supportsDeveloperRole: false,
          supportsReasoningEffort: false,
          supportsUsageInStreaming: true,
          supportsStrictMode: false,
        },
      };
      const inner = native.streamSimple(upstream, codingContext(context), {
        ...options,
        async onPayload(payload, target) {
          const replacement = await options?.onPayload?.(payload, target);
          return { ...(replacement ?? payload), enable_thinking: !!options?.reasoning && options.reasoning !== "off" };
        },
      });
      for await (const event of inner) stream.push(event);
      stream.end();
    } catch (error) {
      const reason = options?.signal?.aborted ? "aborted" : "error";
      const message: AssistantMessage = {
        role: "assistant", content: [], api: model.api, provider: model.provider,
        model: model.id, timestamp: Date.now(), stopReason: reason,
        errorMessage: error instanceof Error ? error.message : String(error),
        usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 0,
                 cost: { ...COST, total: 0 } },
      };
      stream.push({ type: "error", reason, error: message });
      stream.end();
    }
  })();
  return stream;
}

export default function (pi: ExtensionAPI) {
  // Only capture UI at session start. Loading is lazy, on the first request after
  // /model changes; list-models/discovery never spawns processes or loads weights.
  let ui: { setStatus(key: string, text: string | undefined): void } | undefined;
  pi.on("session_start", (_event, ctx) => { ui = ctx.hasUI ? ctx.ui : undefined; });
  pi.registerProvider("lmdesk", {
    baseUrl: GATEWAY, api: "lmdesk-native-tools", apiKey: "lmdesk",
    models: MODELS.map(([id, name]) => ({
      id, name: `${name} (本机)`, reasoning: true,
      input: CAPABILITIES[id].vision ? ["text", "image"] : ["text"], cost: COST,
      contextWindow: CAPABILITIES[id].context, maxTokens: MAX_TOKENS,
    })),
    streamSimple(model, context, options) {
      const result = streamNative(model, context, options, (text) => {
        debug(text);
        ui?.setStatus("lmdesk-load", text);
      });
      // Clear load progress as soon as generation starts or fails.
      const wrapped = createAssistantMessageEventStream();
      (async () => {
        try { for await (const event of result) {
          if (["start", "done", "error"].includes(event.type)) ui?.setStatus("lmdesk-load", undefined);
          wrapped.push(event);
        } } finally { ui?.setStatus("lmdesk-load", undefined); wrapped.end(); }
      })();
      return wrapped;
    },
  });
}
