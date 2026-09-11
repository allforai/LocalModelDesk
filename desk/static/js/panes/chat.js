// ui:chatPane —— 模型选择/加载/卸载、流式回复（思考可展开）、左侧会话列表（R-ui-02、R-ui-08）。
// 只做「取数 → 调纯函数 → 写 DOM」；一律 createElement/textContent，无 innerHTML。
import * as api from "../api.js";
import { sseDataLines } from "../stream.js";
import { initialStream, reduceChunk } from "../pure/chat_stream.js";
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
    renderLlm(status);
  }

  // Same visual family as the status-bar holder pill (badge/badge-*), instead of
  // bare colored text (F15).
  const BADGE_KIND = { idle: "none", loading: "busy", loaded: "ok", error: "unknown" };

  function renderLlm(payload) {
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
      els.modelState.textContent = "已被媒体任务让出内存，可重新加载";
      // Keep the dropdown pointed at the evicted model, not whatever sat first
      // in the list, so "加载" reloads the model that was actually kicked out.
      if (state.model_key && !els.modelSelect.dataset.userPicked) els.modelSelect.value = state.model_key;
    } else {
      const tail = state.error?.log_tail ? `\n${state.error.log_tail}` : "";
      els.modelState.textContent = `加载失败（${state.error?.code ?? "?"}）：${state.error?.message ?? ""}${tail}`;
    }
    const badgeKind = state.error?.code === "evicted" ? "busy" : (BADGE_KIND[state.status] ?? "unknown");
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
    wrap.append(who, details, contentEl, errorEl);
    details.hidden = !message.reasoning && !live;
    details.open = live;
    els.messages.append(wrap);
    els.messages.scrollTop = els.messages.scrollHeight;
    return { wrap, details, summary, reasoningEl, contentEl, errorEl };
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
      const rename = doc.createElement("button");
      rename.className = "btn-sm";
      rename.textContent = "改名";
      addIcon(rename, "pencil", doc);
      rename.addEventListener("click", (event) => { event.stopPropagation?.(); beginRename(li, session); });
      const remove = doc.createElement("button");
      remove.className = "btn-danger btn-sm";
      remove.textContent = "删";
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
    const live = messageNode({ role: "assistant", content: "", reasoning: "" }, true);
    streaming = true;
    els.sendBtn.disabled = true;
    setButtonLabel(els.sendBtn, "生成中…");
    els.messages.dataset.streaming = "1";
    const thinkStart = Date.now();
    let firstContentSeen = false;
    let thinkingSeconds = 0;
    let state = initialStream();
    try {
      const body = await api.chatStream(session.messages);
      for await (const line of sseDataLines(body)) {
        state = reduceChunk(state, line);
        live.reasoningEl.replaceChildren(renderMarkdown(doc, state.reasoning));
        live.details.hidden = !state.reasoning;
        if (state.content && !firstContentSeen) {
          firstContentSeen = true;
          thinkingSeconds = Math.round((Date.now() - thinkStart) / 1000);
          live.summary.textContent = `已思考 ${thinkingSeconds} 秒`;
          live.details.open = false;
        }
        live.contentEl.replaceChildren(renderMarkdown(doc, state.content));
        if (state.done || state.error) break;
      }
      if (!state.done && !state.error) state = { ...state, error: { code: "stream_interrupted", message: "流在完成前中断" } };
    } catch (error) {
      state = { ...state, error: { code: error.code ?? "stream_error", message: error.message } };
    } finally {
      streaming = false;
      els.sendBtn.disabled = false;
      setButtonLabel(els.sendBtn, "发送");
      delete els.messages.dataset.streaming;
    }
    if (state.error) {
      // A media job that evicted the model (or any other mid-stream failure)
      // must not leave the bubble stuck on "思考中…" with half a thought and
      // no answer (widewin gap #1). Label it plainly instead.
      live.summary.textContent = state.error.code === "evicted" ? "已中断：内存让给了媒体作业" : "已中断";
      live.details.open = false;
      if (!state.content) {
        const note = doc.createElement("p");
        note.className = "empty-answer";
        note.textContent = "这条回答没有生成完，可重新发送。";
        live.contentEl.replaceChildren(note);
      }
      live.errorEl.textContent = `出错（${state.error.code}）：${state.error.message}`;
      session.messages.pop();
      return;
    }
    const assistant = { role: "assistant", content: state.content };
    if (state.reasoning) { assistant.reasoning = state.reasoning; assistant.thinking_s = thinkingSeconds; }
    session.messages.push(assistant);
    try {
      const updated = await api.updateChatSession(session.id, { messages: session.messages, model: els.modelSelect.value || null });
      sessions = sortSessions(sessions.map((item) => item.id === updated.id ? updated : item));
      renderSessionList();
    } catch (error) { setError(`会话保存失败：${error.message}`); }
  }

  els.loadBtn.addEventListener("click", loadSelected);
  els.unloadBtn.addEventListener("click", unload);
  els.modelSelect.addEventListener("change", () => { els.modelSelect.dataset.userPicked = "1"; });
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

  function setHeavyAllowed(allowed, reason = "") {
    els.loadBtn.disabled = !allowed;
    els.loadBtn.title = allowed ? "" : reason;
    if (els.loadHint) els.loadHint.textContent = allowed ? "" : reason;
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
