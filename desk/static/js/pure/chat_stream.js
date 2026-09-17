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

const SUMMARY_PREFIX = "以下是本次对话更早部分的摘要，供你理解上下文；它不是用户的原话：\n\n";

// 发给模型的历史：只要 role/content；中断且一个字都没出的回答不算一轮（P3）。
// summary 消息（R-context-05）翻译成 system——服务端不校验角色，但 mlx-lm 要套
// 模型的 chat template，模板只认 system/user/assistant，原样发 summary 会炸在
// 模板里。它 replaced_through 的那一段只是不发送（R-context-03），并未被删除：
// 会话文件与界面上一个字都不少。
export function wireMessages(messages) {
  const list = messages ?? [];
  let skipThrough = -1;
  for (let i = 0; i < list.length; i += 1) {
    if (list[i].role === "summary" && Number.isInteger(list[i].replaced_through)) {
      skipThrough = Math.max(skipThrough, list[i].replaced_through);
    }
  }
  return list
    .filter((message, index) => !(index <= skipThrough && message.role !== "summary"))
    .filter((message) => !(message.role === "assistant" && message.interrupted && !(message.content ?? "").trim()))
    .map((message) => message.role === "summary"
      ? { role: "system", content: SUMMARY_PREFIX + (message.content ?? "") }
      : { role: message.role, content: message.content ?? "" });
}
