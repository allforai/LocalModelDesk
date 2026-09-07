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

export function createChatPane(root) {
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

  const setError = (text) => { els.error.textContent = text ?? ""; };
  const current = () => sessions.find((s) => s.id === currentId) ?? null;

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
      const marks = [entry.params, entry.quant, entry.vision ? "视觉" : null].filter(Boolean).join(" · ");
      option.textContent = `${entry.name} · ${sizeText}${marks ? ` · ${marks}` : ""}${ready ? "" : "（未下载/不完整）"}`;
      option.disabled = !ready;
      els.modelSelect.append(option);
    }
    if (selected) els.modelSelect.value = selected;
    renderLlm(status);
  }

  function renderLlm(payload) {
    const state = payload.state;
    els.modelState.dataset.status = state.status;
    if (state.status === "idle") els.modelState.textContent = "未加载";
    else if (state.status === "loading") els.modelState.textContent = `加载中：${state.model_key ?? ""}`;
    else if (state.status === "loaded") {
      els.modelState.textContent = `已加载：${payload.loaded_model?.name ?? state.model_key}`;
      if (state.model_key) els.modelSelect.value = state.model_key;
    } else {
      const tail = state.error?.log_tail ? `\n${state.error.log_tail}` : "";
      els.modelState.textContent = `加载失败（${state.error?.code ?? "?"}）：${state.error?.message ?? ""}${tail}`;
    }
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
    try {
      const snapshot = await api.memorySnapshot();
      const { warn, message } = needsWarning(Math.round(entry.gb * 1024 ** 3), snapshot);
      if (warn && !await confirmDialog(doc, { title: "内存警告", message, confirmLabel: "仍要加载" })) return;
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

  function messageNode(message, live = false) {
    const wrap = doc.createElement("div");
    wrap.className = `msg msg-${message.role}`;
    const details = doc.createElement("details");
    details.className = "reasoning";
    const summary = doc.createElement("summary");
    summary.textContent = "思考过程";
    const reasoningEl = doc.createElement("pre");
    details.append(summary, reasoningEl);
    const contentEl = doc.createElement("div");
    contentEl.className = "msg-content";
    const errorEl = doc.createElement("p");
    errorEl.className = "inline-error";
    if (message.role === "assistant") wrap.append(details);
    wrap.append(contentEl, errorEl);
    reasoningEl.textContent = message.reasoning ?? "";
    contentEl.textContent = message.content ?? "";
    details.hidden = !message.reasoning && !live;
    details.open = live;
    els.messages.append(wrap);
    els.messages.scrollTop = els.messages.scrollHeight;
    return { details, reasoningEl, contentEl, errorEl };
  }

  function renderMessages() {
    els.messages.replaceChildren();
    const list = current()?.messages ?? [];
    if (!list.length) {
      const empty = doc.createElement("p");
      empty.className = "empty";
      empty.textContent = "这是一个新会话。选好模型、点「加载」，然后在下面输入第一句。";
      els.messages.append(empty);
      return;
    }
    for (const message of list) messageNode(message);
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
      li.classList.toggle("active", session.id === currentId);
      const title = doc.createElement("span");
      title.className = "session-title";
      title.textContent = displayTitle(session);
      title.addEventListener("click", () => {
        currentId = session.id;
        renderSessionList();
        renderMessages();
      });
      const rename = doc.createElement("button");
      rename.textContent = "改名";
      addIcon(rename, "pencil", doc);
      rename.addEventListener("click", () => beginRename(li, session));
      const remove = doc.createElement("button");
      remove.className = "btn-danger btn-sm";
      remove.textContent = "删";
      remove.setAttribute?.("aria-label", `删除会话：${displayTitle(session)}`);
      addIcon(remove, "trash", doc);
      remove.addEventListener("click", async () => {
        const go = await confirmDialog(doc, { title: "删除会话", message: `确定删除「${displayTitle(session)}」？该会话的全部消息将被删除。`, confirmLabel: "删除" });
        if (!go) return;
        try {
          await api.deleteChatSession(session.id);
          await refreshSessions();
        } catch (error) { setError(error.message); }
      });
      li.append(title, rename, remove);
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
    let state = initialStream();
    try {
      const body = await api.chatStream(session.messages);
      for await (const line of sseDataLines(body)) {
        state = reduceChunk(state, line);
        live.reasoningEl.textContent = state.reasoning;
        live.details.hidden = !state.reasoning;
        if (state.content && live.details.open) live.details.open = false;
        live.contentEl.textContent = state.content;
        if (state.done || state.error) break;
      }
      if (!state.done && !state.error) state = { ...state, error: { code: "stream_interrupted", message: "流在完成前中断" } };
    } catch (error) {
      state = { ...state, error: { code: error.code ?? "stream_error", message: error.message } };
    } finally {
      streaming = false;
      els.sendBtn.disabled = false;
    }
    if (state.error) {
      live.errorEl.textContent = `出错（${state.error.code}）：${state.error.message}`;
      session.messages.pop();
      return;
    }
    const assistant = { role: "assistant", content: state.content };
    if (state.reasoning) assistant.reasoning = state.reasoning;
    session.messages.push(assistant);
    try {
      const updated = await api.updateChatSession(session.id, { messages: session.messages, model: els.modelSelect.value || null });
      sessions = sortSessions(sessions.map((item) => item.id === updated.id ? updated : item));
      renderSessionList();
    } catch (error) { setError(`会话保存失败：${error.message}`); }
  }

  els.loadBtn.addEventListener("click", loadSelected);
  els.unloadBtn.addEventListener("click", unload);
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

  return { init, refreshModels, setHeavyAllowed, applyLlmStatus: renderLlm, refreshSessionsIfStale };
}
