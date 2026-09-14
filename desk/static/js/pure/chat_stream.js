// api:chatStream 的 SSE data 行 → {content, reasoning, done, error} 增量归并。
// 帧合同：llm 设计 routes.py 的 ChatEvent；容忍 [DONE] 哨兵与裸 {error} 信封。
export function initialStream() {
  return { content: "", reasoning: "", done: false, error: null, usage: null, finishReason: null };
}

export function reduceChunk(state, line) {
  if (state.done || state.error) return state;
  const raw = String(line).trim();
  if (raw === "") return state;
  if (raw === "[DONE]") return { ...state, done: true };
  let ev;
  try { ev = JSON.parse(raw); } catch { return state; }
  if (ev === null || typeof ev !== "object") return state;
  if (ev.type === "done") {
    return { ...state, done: true, usage: ev.usage ?? null, finishReason: ev.finish_reason ?? null };
  }
  if (ev.type === "error") {
    return { ...state, error: { code: ev.code ?? "stream_error", message: ev.message ?? "流式对话出错" } };
  }
  if (ev.error !== undefined && ev.error !== null) {
    const error = typeof ev.error === "object" ? ev.error : { message: String(ev.error) };
    return { ...state, error: { code: error.code ?? "stream_error", message: error.message ?? String(ev.error) } };
  }
  if (ev.type !== "delta") return state;
  const text = typeof ev.text === "string" ? ev.text : "";
  const reasoning = typeof ev.reasoning === "string" ? ev.reasoning : "";
  if (!text && !reasoning) return state;
  return { ...state, content: state.content + text, reasoning: state.reasoning + reasoning };
}

// 发给模型的历史：只要 role/content；中断且一个字都没出的回答不算一轮（P3）。
export function wireMessages(messages) {
  return messages
    .filter((message) => !(message.role === "assistant" && message.interrupted && !(message.content ?? "").trim()))
    .map((message) => ({ role: message.role, content: message.content ?? "" }));
}
