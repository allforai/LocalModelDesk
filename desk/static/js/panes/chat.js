// ui:chatPane —— 模型选择/加载/卸载、流式回复（思考可展开）、左侧会话列表（R-ui-02、R-ui-08）。
// 只做「取数 → 调纯函数 → 写 DOM」；一律 createElement/textContent，无 innerHTML。
import * as api from "../api.js";
import { sseDataLines } from "../stream.js";
import { initialStream, reduceChunk, wireMessages } from "../pure/chat_stream.js";
import { needsWarning } from "../pure/mem_warn.js";
import { formatBytes } from "../pure/format.js";
import { sortSessions, displayTitle } from "../pure/sessions.js";
import { confirmDialog } from "../widgets/confirm.js";
import { addIcon } from "../icons.js";
import { renderMarkdown } from "../pure/markdown.js";
import { formatTimestamp } from "../pure/format.js";

export function createChatPane(root, ctx = {}) {
  const doc = root.ownerDocument;
  const els = {
    sessionList: root.querySelector("[data-session-list]"),
    sessionNew: root.querySelector("[data-session-new]"),
    modelSelect: root.querySelector("[data-model-select]"),
    loadBtn: root.querySelector("[data-load]"),
    unloadBtn: root.querySelector("[data-unload]"),
    modelState: root.querySelector("[data-model-state]"),
    messages: root.querySelector("[data-messages]"),
    input: root.querySelector("[data-chat-input]"),
    sendBtn: root.querySelector("[data-send]"),
    error: root.querySelector("[data-chat-error]"),
    loadHint: root.querySelector("[data-load-hint]"),
  };
  let catalog = [];
  let sessions = [];
  let currentId = null;
  let streaming = false;
  let sessionsTick = 0;
  let modelName = "";
  let lastLoadedKey = null;
  let llmStatus = "idle";
  let liveTurn = null; // { session, state } while a reply is streaming — read by the pagehide saver
  let readyModels = null; // null until the catalog has been read once
  let heavyAllowed = true;
  let heavyReason = "";

  const setError = (text) => { els.error.textContent = text ?? ""; };
  const current = () => sessions.find((s) => s.id === currentId) ?? null;

  // Writing button.textContent replaces every child, icon SVG included (F3).
  // Route label changes through a dedicated <span data-label> instead so the
  // icon addIcon()/hydrateIcons() attached earlier survives every state change.
  function setButtonLabel(button, text) {
    const label = button.querySelector?.("[data-label]");
    if (label) { label.textContent = text; return; }
    const span = doc.createElement("span");
    (span.dataset ??= {}).label = "1";
    span.textContent = text;
    button.append(span);
  }

  async function refreshModels() {
    const [entries, verified, status] = await Promise.all([
      api.listCatalog(), api.verifyAllModels(), api.llmStatus(),
    ]);
    catalog = entries.filter((entry) => entry.group === "chat");
    const byKey = new Map((verified.models ?? verified).map((model) => [model.key, model]));
    const selected = els.modelSelect.value;
    els.modelSelect.replaceChildren();
    for (const entry of catalog) {
      const modelStatus = byKey.get(entry.key);
      const ready = modelStatus?.state === "present";
      const sizeText = Number.isFinite(modelStatus?.bytes_expected)
        ? formatBytes(modelStatus.bytes_expected)
        : `${entry.gb} GiB（目录）`;
      const option = doc.createElement("option");
      option.value = entry.key;
      const marks = [entry.params, entry.name?.includes(entry.quant ?? " ") ? null : entry.quant, entry.vision ? "视觉" : null].filter(Boolean).join(" · ");
      option.textContent = `${entry.name} · ${sizeText}${marks ? ` · ${marks}` : ""}${ready ? "" : "（未下载/不完整）"}`;
      option.disabled = !ready;
      els.modelSelect.append(option);
    }
    if (selected) els.modelSelect.value = selected;
    readyModels = catalog.filter((entry) => byKey.get(entry.key)?.state === "present").length;
    syncLoadButton();
    renderLlm(status);
  }

  // Same visual family as the status-bar holder pill (badge/badge-*), instead of
  // bare colored text (F15).
  const BADGE_KIND = { idle: "none", loading: "busy", loaded: "ok", error: "unknown" };

  // Without a desk snapshot (older callers) assume the media job still holds memory.
  const mediaStillHolds = (deskState) => !deskState || Boolean(deskState.media_busy || (deskState.holder && deskState.holder.kind !== "llm"));

  function renderLlm(payload, deskState) {
    const state = payload.state;
    llmStatus = state.status;
    els.modelState.dataset.status = state.status;
    if (state.status === "idle") els.modelState.textContent = "未加载";
    else if (state.status === "loading") els.modelState.textContent = `加载中：${state.model_key ?? ""}`;
    else if (state.status === "loaded") {
      els.modelState.textContent = `已加载：${payload.loaded_model?.name ?? state.model_key}`;
      if (state.model_key && state.model_key !== lastLoadedKey) { els.modelSelect.value = state.model_key; lastLoadedKey = state.model_key; }
      delete els.modelSelect.dataset.userPicked;
    } else if (state.error?.code === "evicted") {
      els.modelState.textContent = mediaStillHolds(deskState) ? "已被媒体任务让出内存，可重新加载" : "媒体任务已结束，可重新加载";
      // Keep the dropdown pointed at the evicted model, not whatever sat first
      // in the list, so "加载" reloads the model that was actually kicked out.
      if (state.model_key && !els.modelSelect.dataset.userPicked) els.modelSelect.value = state.model_key;
    } else {
      const tail = state.error?.log_tail ? `\n${state.error.log_tail}` : "";
      els.modelState.textContent = `加载失败（${state.error?.code ?? "?"}）：${state.error?.message ?? ""}${tail}`;
    }
    const badgeKind = state.error?.code === "evicted"
      ? (mediaStillHolds(deskState) ? "busy" : "none")
      : (BADGE_KIND[state.status] ?? "unknown");
    els.modelState.className = `badge badge-${badgeKind}`;
    if (state.status !== "loaded") lastLoadedKey = state.status === "loading" ? lastLoadedKey : null;
    els.unloadBtn.disabled = state.status === "idle" || state.status === "loading";
    modelName = payload.loaded_model?.name ?? state.model_key ?? modelName;
  }

  async function pollUntilSettled() {
    for (;;) {
      const payload = await api.llmStatus();
      renderLlm(payload);
      if (payload.state.status !== "loading") return;
      await new Promise((resolve) => setTimeout(resolve, 1000));
    }
  }

  async function loadSelected() {
    setError("");
    const entry = catalog.find((item) => item.key === els.modelSelect.value);
    if (!entry) return;
    const confirm = ctx.confirm ?? ((options) => confirmDialog(doc, options));
    try {
      if (llmStatus === "loaded" && lastLoadedKey && lastLoadedKey !== entry.key) {
        const from = catalog.find((item) => item.key === lastLoadedKey)?.name ?? lastLoadedKey;
        const go = await confirm({ title: "换模型", message: `将先卸载「${from}」，再加载「${entry.name}」。`, confirmLabel: "换模型", danger: false });
        if (!go) return;
        await api.unloadLlm();
        renderLlm(await api.llmStatus());
      } else if (llmStatus === "loaded" && lastLoadedKey === entry.key) {
        return;
      }
      const snapshot = await api.memorySnapshot();
      const { warn, message } = needsWarning(Math.round(entry.gb * 1024 ** 3), snapshot);
      if (warn && !await confirm({ title: "内存警告", message, confirmLabel: "仍要加载", danger: false })) return;
      await api.loadLlm(entry.key);
      await pollUntilSettled();
    } catch (error) { setError(error.message); }
  }

  async function unload() {
    setError("");
    try {
      await api.unloadLlm();
      renderLlm(await api.llmStatus());
    } catch (error) { setError(error.message); }
  }

  function messageNode(message, live = false, fallbackName = "") {
    const wrap = doc.createElement("div");
    wrap.className = `msg msg-${message.role}`;
    if (message.role === "user") {
      const bubble = doc.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = message.content ?? "";
      wrap.append(bubble);
      els.messages.append(wrap);
      els.messages.scrollTop = els.messages.scrollHeight;
      return { wrap };
    }
    const who = doc.createElement("div");
    who.className = "who";
    const dot = doc.createElement("span");
    dot.className = "dot";
    const name = doc.createElement("span");
    name.textContent = message.model || fallbackName || modelName || "模型";
    who.append(dot, name);
    const details = doc.createElement("details");
    details.className = "thinking";
    const summary = doc.createElement("summary");
    summary.textContent = live
      ? "思考中…"
      : Number.isFinite(message.thinking_s)
        ? `已思考 ${Math.max(1, Math.round(message.thinking_s))} 秒`
        : "思考过程（未记录时长）";
    const reasoningEl = doc.createElement("div");
    reasoningEl.className = "md";
    reasoningEl.append(renderMarkdown(doc, message.reasoning ?? ""));
    details.append(summary, reasoningEl);
    const contentEl = doc.createElement("div");
    contentEl.className = "md";
    if (!live && !(message.content ?? "").trim()) {
      const empty = doc.createElement("p");
      empty.className = "empty-answer";
      empty.textContent = "（这条回答没有内容）";
      contentEl.append(empty);
    } else {
      contentEl.append(renderMarkdown(doc, message.content ?? ""));
    }
    const errorEl = doc.createElement("p");
    errorEl.className = "inline-error";
    if (!live && message.interrupted) errorEl.textContent = `回答没有生成完：${message.interrupted.message}`;
    else if (!live && message.truncated) errorEl.textContent = "已达到长度上限，回答被截断。";
    wrap.append(who, details, contentEl, errorEl);
    details.hidden = !message.reasoning && !live;
    details.open = live;
    els.messages.append(wrap);
    els.messages.scrollTop = els.messages.scrollHeight;
    return { wrap, details, summary, reasoningEl, contentEl, errorEl };
  }

  function appendRetry() {
    const row = doc.createElement("div");
    row.className = "retry-row";
    const button = doc.createElement("button");
    (button.dataset ??= {}).retry = "1";
    button.textContent = "重试";
    button.addEventListener("click", () => retry());
    row.append(button);
    els.messages.append(row);
  }

  async function retry() {
    const session = current();
    if (streaming || !session?.messages?.at(-1)?.interrupted) return;
    session.messages.pop();
    renderMessages();
    await streamReply(session);
  }

  function showMessages(list, fallbackModelName = "") {
    els.messages.replaceChildren();
    if (!list.length) {
      const empty = doc.createElement("p");
      empty.className = "empty";
      empty.textContent = "这是一个新会话。选好模型、点「加载」，然后在下面输入第一句。";
      els.messages.append(empty);
      return;
    }
    for (const message of list) messageNode(message, false, fallbackModelName);
    if (list.at(-1)?.interrupted) appendRetry();
  }

  const sessionModelName = (session) => catalog.find((item) => item.key === session?.model)?.name ?? session?.model ?? "";

  function renderMessages() {
    showMessages(current()?.messages ?? [], sessionModelName(current()));
  }

  async function refreshSessions(selectId) {
    sessions = sortSessions(await api.listChatSessions());
    if (sessions.length === 0) sessions = [await api.createChatSession()];
    const wanted = selectId ?? currentId;
    currentId = sessions.some((session) => session.id === wanted) ? wanted : sessions[0].id;
    renderSessionList();
    renderMessages();
  }

  function beginRename(li, session) {
    const input = doc.createElement("input");
    input.value = session.title ?? "";
    let done = false;
    const finish = async () => {
      if (done) return;
      done = true;
      const title = input.value.trim();
      if (title && title !== session.title) {
        try { await api.updateChatSession(session.id, { title }); }
        catch (error) { setError(error.message); }
      }
      await refreshSessions(session.id);
    };
    input.addEventListener("keydown", (event) => { if (event.key === "Enter") finish(); });
    input.addEventListener("blur", finish);
    li.replaceChildren(input);
    input.focus();
  }

  function renderSessionList() {
    els.sessionList.replaceChildren();
    for (const session of sessions) {
      const li = doc.createElement("li");
      li.className = "card session";
      li.classList.toggle("active", session.id === currentId);
      const title = doc.createElement("div");
      title.className = "session-title";
      title.textContent = displayTitle(session);
      const meta = doc.createElement("div");
      meta.className = "session-meta";
      meta.textContent = [session.model, formatTimestamp(session.updated).slice(11)].filter(Boolean).join(" · ");
      const actions = doc.createElement("div");
      actions.className = "session-actions";
      // Icon-only (F7): text labels ("改名"/"删") widened this hover-revealed
      // column past the card's horizontal center, so a plain click meant to
      // switch sessions could land on a button instead. The accessible name
      // still comes through via aria-label.
      const rename = doc.createElement("button");
      rename.className = "btn-sm";
      rename.setAttribute?.("aria-label", "改名");
      addIcon(rename, "pencil", doc);
      rename.addEventListener("click", (event) => { event.stopPropagation?.(); beginRename(li, session); });
      const remove = doc.createElement("button");
      remove.className = "btn-danger btn-sm";
      remove.setAttribute?.("aria-label", `删除会话：${displayTitle(session)}`);
      addIcon(remove, "trash", doc);
      remove.addEventListener("click", async (event) => {
        event.stopPropagation?.();
        const go = await confirmDialog(doc, { title: "删除会话", message: `确定删除「${displayTitle(session)}」？该会话的全部消息将被删除。`, confirmLabel: "删除" });
        if (!go) return;
        try {
          await api.deleteChatSession(session.id);
          await refreshSessions();
        } catch (error) { setError(error.message); }
      });
      actions.append(rename, remove);
      li.addEventListener("click", () => {
        currentId = session.id;
        renderSessionList();
        renderMessages();
      });
      li.append(title, meta, actions);
      els.sessionList.append(li);
    }
  }

  async function send() {
    if (streaming) return;
    const text = els.input.value.trim();
    const session = current();
    if (!text || !session) return;
    setError("");
    session.messages = session.messages ?? [];
    if (session.messages.length === 0) els.messages.replaceChildren();
    session.messages.push({ role: "user", content: text });
    els.input.value = "";
    messageNode({ role: "user", content: text });
    await streamReply(session);
  }

  // One reply, from first frame to saved turn. Every ending — done, truncated,
  // interrupted — is pushed into the session and saved (P3).
  async function streamReply(session) {
    setError("");
    const live = messageNode({ role: "assistant", content: "", reasoning: "" }, true);
    streaming = true;
    els.sendBtn.disabled = true;
    setButtonLabel(els.sendBtn, "生成中…");
    els.messages.dataset.streaming = "1";
    const thinkStart = Date.now();
    const elapsed = () => Math.round((Date.now() - thinkStart) / 1000);
    let firstContentSeen = false;
    let thinkingSeconds = 0;
    let state = initialStream();
    liveTurn = { session, state };
    try {
      const body = await api.chatStream(wireMessages(session.messages));
      for await (const line of sseDataLines(body)) {
        state = reduceChunk(state, line);
        liveTurn.state = state;
        live.reasoningEl.replaceChildren(renderMarkdown(doc, state.reasoning));
        live.details.hidden = !state.reasoning;
        if (state.content && !firstContentSeen) {
          firstContentSeen = true;
          thinkingSeconds = elapsed();
          live.summary.textContent = `已思考 ${thinkingSeconds} 秒`;
          live.details.open = false;
        }
        live.contentEl.replaceChildren(renderMarkdown(doc, state.content));
        if (state.done || state.error) break;
      }
      if (!state.done && !state.error) state = { ...state, error: { code: "stream_interrupted", message: "连接在回答完成前断开" } };
    } catch (error) {
      state = { ...state, error: { code: error.code ?? "stream_error", message: error.message } };
    } finally {
      liveTurn = null;
      streaming = false;
      els.sendBtn.disabled = false;
      setButtonLabel(els.sendBtn, "发送");
      delete els.messages.dataset.streaming;
    }
    if (!firstContentSeen && state.reasoning) thinkingSeconds = elapsed();
    const assistant = { role: "assistant", content: state.content };
    if (state.reasoning) { assistant.reasoning = state.reasoning; assistant.thinking_s = thinkingSeconds; }
    if (state.error) {
      // Widewin gap #1 / P3: label it plainly, keep what was said, offer a retry.
      assistant.interrupted = { code: state.error.code, message: state.error.message };
      live.summary.textContent = state.error.code === "evicted" ? "已中断：内存让给了媒体作业" : "已中断";
      live.details.open = false;
      if (!state.content) {
        const note = doc.createElement("p");
        note.className = "empty-answer";
        note.textContent = "这条回答没有生成完，可点「重试」重新生成。";
        live.contentEl.replaceChildren(note);
      }
      live.errorEl.textContent = `回答没有生成完：${state.error.message}`;
    } else {
      if (state.reasoning && !firstContentSeen) live.summary.textContent = `已思考 ${Math.max(1, thinkingSeconds)} 秒`;
      if (!state.content) {
        const note = doc.createElement("p");
        note.className = "empty-answer";
        note.textContent = state.reasoning ? "模型只输出了思考，没有给出回答。" : "（这条回答没有内容）";
        live.contentEl.replaceChildren(note);
      }
      if (state.finishReason === "length") {
        assistant.truncated = true;
        live.errorEl.textContent = "已达到长度上限，回答被截断。";
      }
    }
    session.messages.push(assistant);
    if (state.error && currentId === session.id) appendRetry();
    try {
      const updated = await api.updateChatSession(session.id, { messages: session.messages, model: els.modelSelect.value || null });
      sessions = sortSessions(sessions.map((item) => item.id === updated.id ? updated : item));
      renderSessionList();
    } catch (error) { setError(`会话保存失败：${error.message}`); }
  }

  els.loadBtn.addEventListener("click", loadSelected);
  els.unloadBtn.addEventListener("click", unload);
  els.modelSelect.addEventListener("change", () => { els.modelSelect.dataset.userPicked = "1"; });
  // Closing or reloading the page mid-reply must not lose the question (P3 path 6).
  function saveLiveTurnOnPageHide() {
    if (!liveTurn) return;
    const { session, state } = liveTurn;
    const partial = { role: "assistant", content: state.content };
    if (state.reasoning) partial.reasoning = state.reasoning;
    partial.interrupted = { code: "page_closed", message: "页面关闭时回答还没生成完" };
    api.updateChatSession(session.id, { messages: [...session.messages, partial], model: els.modelSelect.value || null }, { keepalive: true })
      .catch(() => {});
  }
  (ctx.window ?? globalThis).addEventListener?.("pagehide", saveLiveTurnOnPageHide);

  els.sendBtn.addEventListener("click", send);
  els.input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) send();
  });
  els.sessionNew.addEventListener("click", async () => {
    try {
      const created = await api.createChatSession();
      await refreshSessions(created.id);
    } catch (error) { setError(error.message); }
  });

  async function init() {
    try { await refreshModels(); } catch (error) { setError(error.message); }
    try { await refreshSessions(); } catch (error) { setError(error.message); }
  }

  function syncLoadButton() {
    const noModels = readyModels === 0;
    els.loadBtn.disabled = !heavyAllowed || noModels;
    const hint = !heavyAllowed ? heavyReason : noModels ? "还没有下载好的聊天模型，去「资源」页下载" : "";
    els.loadBtn.title = hint;
    if (els.loadHint) els.loadHint.textContent = hint;
  }

  function setHeavyAllowed(allowed, reason = "") {
    heavyAllowed = allowed;
    heavyReason = reason;
    syncLoadButton();
  }

  async function refreshSessionsIfStale() {
    sessionsTick += 1;
    if (sessionsTick % 5 !== 0 || streaming) return;
    const latest = sortSessions(await api.listChatSessions());
    if (latest.length !== sessions.length || latest.some((s, i) => s.id !== sessions[i].id || s.updated !== sessions[i].updated)) {
      sessions = latest; renderSessionList();
    }
  }

  return { init, refreshModels, setHeavyAllowed, showMessages, applyLlmStatus: renderLlm, refreshSessionsIfStale };
}
