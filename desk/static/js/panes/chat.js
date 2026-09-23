// ui:chatPane —— 模型选择/加载/卸载、流式回复（思考可展开）、左侧会话列表（R-ui-02、R-ui-08）。
// 只做「取数 → 调纯函数 → 写 DOM」；一律 createElement/textContent，无 innerHTML。
import * as api from "../api.js";
import { sseDataLines } from "../stream.js";
import { initialStream, reduceChunk, wireMessages } from "../pure/chat_stream.js";
import { maybeCompact, summaryLabel, charsPerToken } from "../pure/compaction.js";
import { resolveSelection, skillSystemMessage, skillChars, skillTokens } from "../pure/skills.js";
import { buildSummaryRequest } from "../pure/summary_prompt.js";
import { needsWarning } from "../pure/mem_warn.js";
import { formatBytes } from "../pure/format.js";
import { statusBadge } from "../pure/model_status.js";
import { sortSessions, displayTitle } from "../pure/sessions.js";
import { confirmDialog } from "../widgets/confirm.js";
import { addIcon } from "../icons.js";
import { renderMarkdown } from "../pure/markdown.js";
import { formatTimestamp } from "../pure/format.js";
import { shouldStickToBottom } from "../pure/scroll_follow.js";

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
    skillBar: root.querySelector("[data-skill-bar]"),
    skillNotice: root.querySelector("[data-skill-notice]"),
    skillCost: root.querySelector("[data-skill-cost]"),
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
  let streamAbort = null; // aborts the streaming fetch when the user presses 停止
  let readyModels = null; // null until the catalog has been read once
  let heavyAllowed = true;
  let heavyReason = "";
  let compactingBanner = null; // 「正在压缩较早的对话…」提示条，压缩期间显示（R-context-04）
  // 可用列表与选中状态分开存：列表来自扫描（唯一一份已解析列表，R-skill-16），
  // 选中来自会话（R-skill-15）。两者每次扫描后对账一次（refreshSkills）。
  let availableSkills = [];
  // 每 token 字符数前端量不出来，只能从上一轮真实请求里量：sentChars 配那次
  // 真实返回的 usage.prompt_tokens，相除即得（compaction.js 同一招）。没发生过
  // 请求之前就是 null——绝不套一个默认值（R-skill-06）。
  let lastCharsPerToken = null;
  let lastCompactAt = null;

  const setError = (text) => { els.error.textContent = text ?? ""; };
  const current = () => sessions.find((s) => s.id === currentId) ?? null;

  // 会话可能是这个功能上线之前存的，没有 skills 这个键——`session?.skills ?? []`
  // 是有意的，不是多余的防御：裸读 session.skills 会在这种旧会话上炸掉整个聊天面板。
  function currentResolution() {
    const session = current();
    return resolveSelection(session?.skills ?? [], availableSkills);
  }

  // 占用显示：量不到每 token 字符数就只报字符数，绝不套一个默认比值（R-skill-06）。
  // compaction.js 的房规是「量不到就返回 null，而不是套一个默认值」，这里沿用。
  function renderSkillCost(ratio, compactAt) {
    const { resolved } = currentResolution();
    const chars = skillChars(resolved);
    if (chars === 0) { els.skillCost.textContent = ""; els.skillCost.dataset.warn = ""; return; }
    const tokens = skillTokens(chars, ratio);
    if (tokens === null) {
      els.skillCost.textContent = `skill 占用 ${chars} 字符（还没量过 token）`;
      els.skillCost.dataset.warn = "";
      return;
    }
    els.skillCost.textContent = compactAt
      ? `skill 占用 ${tokens} / 额度 ${compactAt}`
      : `skill 占用 ${tokens}`;
    // 超过三成时警告而不禁止——是用户的机器，由他决定（R-skill-06）。
    els.skillCost.dataset.warn = compactAt && tokens > compactAt * 0.3 ? "1" : "";
  }

  async function toggleSkill(entry) {
    if (!entry.ok) return; // 坏的点不动（R-skill-08）
    const session = current();
    if (!session) return;
    const picked = session.skills ?? [];
    session.skills = picked.some((s) => s.name === entry.name)
      ? picked.filter((s) => s.name !== entry.name)
      : [...picked, { name: entry.name, attachments: [] }];
    renderSkillChips();
    try { await saveSession(session); } catch (error) { setError(`会话保存失败：${error.message}`); }
  }

  async function toggleAttachment(name, file, checked) {
    const session = current();
    if (!session) return;
    session.skills = (session.skills ?? []).map((s) => {
      if (s.name !== name) return s;
      const attachments = checked
        ? [...new Set([...(s.attachments ?? []), file])]
        : (s.attachments ?? []).filter((f) => f !== file);
      return { ...s, attachments };
    });
    renderSkillChips();
    try { await saveSession(session); } catch (error) { setError(`会话保存失败：${error.message}`); }
  }

  // 芯片渲染：好条目 title 写 description（今天的消费者是用户，他靠这句话决定点不点，
  // 不是模型），坏条目 disabled 且 title 写 error（R-skill-08 后半）。
  // overrides_bundled 为真时标出「已覆盖自带」——覆盖必须看得见（R-skill-07）。
  // 附件在芯片展开后以勾选框列出，每个标明 file 与 chars（R-skill-10）。
  function renderSkillChips() {
    for (const child of [...(els.skillBar.children ?? [])]) {
      if (child === els.skillNotice || child === els.skillCost) continue;
      child.remove();
    }
    const { resolved } = currentResolution();
    const selectedNames = new Set(resolved.map((s) => s.name));
    const session = current();
    for (const entry of availableSkills) {
      const chip = doc.createElement("button");
      chip.className = "skill-chip";
      (chip.dataset ??= {}).skillChip = entry.name;
      chip.disabled = !entry.ok;
      chip.title = entry.ok ? (entry.description ?? "") : (entry.error ?? "");
      const isSelected = selectedNames.has(entry.name);
      chip.textContent = entry.overrides_bundled ? `${entry.name} · 已覆盖自带` : entry.name;
      chip.classList.toggle("active", isSelected);
      chip.addEventListener("click", () => toggleSkill(entry));
      els.skillBar.append(chip);
      if (entry.ok && (entry.attachments ?? []).length) {
        const picked = (session?.skills ?? []).find((s) => s.name === entry.name);
        const pickedAttachments = new Set(picked?.attachments ?? []);
        for (const att of entry.attachments) {
          const label = doc.createElement("label");
          label.className = "skill-attachment";
          const checkbox = doc.createElement("input");
          checkbox.type = "checkbox";
          checkbox.disabled = !isSelected;
          checkbox.checked = isSelected && pickedAttachments.has(att.file);
          (checkbox.dataset ??= {}).skillAttachment = `${entry.name}/${att.file}`;
          checkbox.addEventListener("change", () => toggleAttachment(entry.name, att.file, checkbox.checked));
          const span = doc.createElement("span");
          span.textContent = `${att.file}（${att.chars} 字符）`;
          label.append(checkbox, span);
          els.skillBar.append(label);
        }
      }
    }
    renderSkillCost(lastCharsPerToken, lastCompactAt);
  }

  // 扫描完成后的对账：会话里记的选中，对上刚扫描出来的可用列表。消失或变坏的
  // 摘出来在界面上说明，并把会话里的选中写回成对账后的结果——不静默丢弃
  // （R-skill-14）。
  async function refreshSkills(rescan = false) {
    const payload = rescan ? await api.rescanSkills() : await api.listSkills();
    availableSkills = payload.skills ?? [];
    const session = current();
    if (!session) { renderSkillChips(); return; }
    const { resolved, dropped } = resolveSelection(session.skills ?? [], availableSkills);
    if (dropped.length) {
      els.skillNotice.textContent = dropped.map((d) => `${d.name}：${d.reason}`).join("；");
      session.skills = resolved.map((s) => ({
        name: s.name, attachments: s.attachments.map((a) => a.file),
      }));
      try { await saveSession(session); } catch (error) { setError(`会话保存失败：${error.message}`); }
    } else {
      els.skillNotice.textContent = "";
    }
    renderSkillChips();
  }

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
      // Reuse the resources pane's own vocabulary (statusBadge) instead of collapsing
      // missing/partial/unknown into one made-up "未下载/不完整" suffix — an unknown
      // status (manifest unreachable) is not the same claim as "definitely not downloaded".
      const suffix = ready ? "" : ` （${statusBadge(modelStatus ?? { state: "unknown" }).badge}）`;
      option.textContent = `${entry.name} · ${sizeText}${marks ? ` · ${marks}` : ""}${suffix}`;
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
      els.modelState.textContent = `加载失败（${state.error?.code ?? "?"}）：${state.error?.message ?? ""}`;
    }
    // A full mlx-lm log inside the badge floods the page; keep it one hover away.
    els.modelState.title = state.status === "error" ? (state.error?.log_tail ?? "") : "";
    const badgeKind = state.error?.code === "evicted"
      ? (mediaStillHolds(deskState) ? "busy" : "none")
      : (BADGE_KIND[state.status] ?? "unknown");
    els.modelState.className = `badge badge-${badgeKind}`;
    if (state.status !== "loaded") lastLoadedKey = state.status === "loading" ? lastLoadedKey : null;
    els.unloadBtn.disabled = state.status === "idle";
    setButtonLabel(els.unloadBtn, state.status === "loading" ? "取消加载" : "卸载");
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
    if (message.role === "summary") {
      // R-context-03：被替代的消息没有被删除，只是不发送——它们照常在下面各自渲染成自己的节点。
      // R-context-05：摘要本身可展开、可编辑、可重新生成。
      const details = doc.createElement("details");
      const summaryEl = doc.createElement("summary");
      summaryEl.textContent = summaryLabel(message.replaced_through);
      const body = doc.createElement("div");
      body.className = "md";
      body.append(renderMarkdown(doc, message.content ?? ""));
      const actions = doc.createElement("div");
      actions.className = "summary-actions";
      const edit = doc.createElement("button");
      edit.className = "btn-sm";
      edit.textContent = "改";
      (edit.dataset ??= {}).editSummary = "1";
      edit.addEventListener("click", () => beginEditSummary(message, body));
      const redo = doc.createElement("button");
      redo.className = "btn-sm";
      redo.textContent = "重压";
      (redo.dataset ??= {}).redoSummary = "1";
      redo.addEventListener("click", () => regenerateSummary(message));
      actions.append(edit, redo);
      details.append(summaryEl, body, actions);
      wrap.append(details);
      els.messages.append(wrap);
      return { wrap, details, body };
    }
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
    renderSkillChips(); // 切到别的会话，芯片的选中态、占用显示都得跟着换
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
      li.tabIndex = 0;
      if (session.id === currentId) li.setAttribute?.("aria-current", "true");
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
      const select = () => {
        currentId = session.id;
        renderSessionList();
        renderMessages();
        renderSkillChips();
        [...(els.sessionList.children ?? [])].find((node) => node.dataset?.sessionId === session.id)?.focus?.();
      };
      (li.dataset ??= {}).sessionId = session.id;
      li.addEventListener("click", select);
      li.addEventListener("keydown", (event) => {
        if (event.target && event.target !== li) return; // buttons and the rename input handle their own keys
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault();
        select();
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
    streamAbort = new AbortController();
    // A model can repeat itself until the token limit; the user must be able to stop it.
    els.sendBtn.disabled = false;
    setButtonLabel(els.sendBtn, "停止");
    els.messages.dataset.streaming = "1";
    const thinkStart = Date.now();
    const elapsed = () => Math.round((Date.now() - thinkStart) / 1000);
    let firstContentSeen = false;
    let thinkingSeconds = 0;
    let state = initialStream();
    liveTurn = { session, state };
    // 记下这一轮实际发出去的字符数：压缩要靠它反推每 token 字符数（R-context-01 背景）。
    let sentChars = 0;
    try {
      // skill 必须在这里、在测量 sentChars 之前拼进去（R-skill-13）：每 token
      // 字符数由 sentChars / promptTokens 反推，而 skill 必然计入上游返回的
      // promptTokens——它若没计入 sentChars，比值会被悄悄带偏，且没有任何迹象。
      const { resolved } = currentResolution();
      const wired = wireMessages(session.messages, skillSystemMessage(resolved));
      sentChars = JSON.stringify(wired).length;
      const body = await api.chatStream(wired, { signal: streamAbort.signal });
      for await (const line of sseDataLines(body)) {
        state = reduceChunk(state, line);
        liveTurn.state = state;
        const stickThinking = shouldStickToBottom(els.messages);
        live.reasoningEl.replaceChildren(renderMarkdown(doc, state.reasoning));
        live.details.hidden = !state.reasoning;
        if (stickThinking) els.messages.scrollTop = els.messages.scrollHeight;
        if (state.content && !firstContentSeen) {
          firstContentSeen = true;
          thinkingSeconds = elapsed();
          live.summary.textContent = `已思考 ${thinkingSeconds} 秒`;
          live.details.open = false;
        }
        // 每块之前先看用户是不是贴着底：更新之后 scrollHeight 已经变大，那时再判就永远是「翻上去了」。
        const stick = shouldStickToBottom(els.messages);
        live.contentEl.replaceChildren(renderMarkdown(doc, state.content));
        if (stick) els.messages.scrollTop = els.messages.scrollHeight;
        if (state.done || state.error) break;
      }
      if (!state.done && !state.error) state = { ...state, error: { code: "stream_interrupted", message: "连接在回答完成前断开" } };
    } catch (error) {
      state = {
        ...state,
        error: error?.name === "AbortError"
          ? { code: "stopped", message: "已停止生成" }
          : { code: error.code ?? "stream_error", message: error.message },
      };
    } finally {
      liveTurn = null;
      streamAbort = null;
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
      const stopped = state.error.code === "stopped";
      live.summary.textContent = stopped ? "已停止" : state.error.code === "evicted" ? "已中断：内存让给了媒体作业" : "已中断";
      live.details.open = false;
      if (!state.content) {
        const note = doc.createElement("p");
        note.className = "empty-answer";
        note.textContent = "这条回答没有生成完，可点「重试」重新生成。";
        live.contentEl.replaceChildren(note);
      }
      live.errorEl.textContent = stopped ? state.error.message : `回答没有生成完：${state.error.message}`;
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
    // 压缩发生在两轮之间，不打断正在生成的回答（R-context-04）。
    await compactIfNeeded(session, state.usage?.prompt_tokens, sentChars);
  }

  // 「把 head 拼成填表提示词、调同一个驻留模型、拼出完整文本」——两轮之间的
  // 自动压缩（compactIfNeeded）与用户手动点「重压」（regenerateSummary）共用
  // 这一段：都不加载第二个模型（R-context-04），过程都要有可见提示。
  async function runSummarise(session, head, bannerText) {
    const showBanner = () => {
      if (currentId !== session.id) return;
      els.sendBtn.disabled = true; // 摘要占用同一个模型：发送按钮得置灰，否则像是卡住了
      if (!compactingBanner) {
        compactingBanner = doc.createElement("p");
        compactingBanner.className = "compacting-banner";
        compactingBanner.textContent = bannerText;
        els.messages.prepend(compactingBanner);
      }
    };
    const hideBanner = () => {
      if (compactingBanner) { compactingBanner.remove(); compactingBanner = null; }
      if (currentId === session.id) els.sendBtn.disabled = false;
    };
    showBanner();
    try {
      const body = await api.chatStream(buildSummaryRequest(head));
      let s = initialStream();
      for await (const line of sseDataLines(body)) {
        s = reduceChunk(s, line);
        if (s.done || s.error) break;
      }
      if (s.error) throw new Error(s.error.message);
      return s.content;
    } finally {
      hideBanner();
    }
  }

  async function saveSession(session) {
    const updated = await api.updateChatSession(session.id, {
      messages: session.messages, model: els.modelSelect.value || null, skills: session.skills ?? [],
    });
    sessions = sortSessions(sessions.map((item) => item.id === updated.id ? updated : item));
    renderSessionList();
  }

  // 一轮结束后判断是否要压缩较早的历史。summarise 走同一个驻留模型的一次
  // chatStream 调用（R-context-04：不加载第二个模型）；纯判断/切分/写回逻辑
  // 都在 maybeCompact 里，这里只负责取数、渲染进行中提示、落盘。
  async function compactIfNeeded(session, promptTokens, sentChars) {
    const budget = await api.budget().catch(() => null);
    if (!budget) return; // 预算读不到就不压缩，不能替用户裁剪历史（同 R-budget-11 的保守纪律）
    lastCompactAt = budget.chat?.compact_at ?? null;
    const ratio = charsPerToken(sentChars, promptTokens);
    if (ratio) lastCharsPerToken = ratio; // 量不到就保留上一次量到的值，不回退成猜的
    if (currentId === session.id) renderSkillCost(lastCharsPerToken, lastCompactAt);
    const result = await maybeCompact(session.messages, {
      promptTokens, sentChars,
      compactAt: budget.chat?.compact_at,
      pressure: budget.pressure,
      // skill 占着同一个窗口却不在 messages 里（R-skill-12）：不把它的占用告诉
      // maybeCompact，压缩会按只剩历史来算预算，压完仍然超，下一轮接着压。
      skillChars: skillChars(currentResolution().resolved),
      summarise: (head) => runSummarise(session, head, "正在压缩较早的对话…"),
    });
    // 失败或没到触发点：maybeCompact 已经原样返回，什么都不用做，下一轮再判断。
    if (!result.compacted) return;
    session.messages = result.messages;
    try { await saveSession(session); }
    catch (error) { setError(`会话保存失败：${error.message}`); }
    if (currentId === session.id) renderMessages();
  }

  // R-context-05：摘要本身是会话里的一条普通消息，本地模型摘歪了，用户自己
  // 改一句就行，不必重开会话——就地编辑的写法照抄 beginRename。
  function beginEditSummary(message, body) {
    const session = current();
    if (!session) return;
    const textarea = doc.createElement("textarea");
    textarea.className = "summary-edit";
    textarea.value = message.content ?? "";
    let done = false;
    const finish = async () => {
      if (done) return;
      done = true;
      const text = textarea.value.trim();
      if (text && text !== message.content) {
        message.content = text;
        try { await saveSession(session); }
        catch (error) { setError(`会话保存失败：${error.message}`); }
      }
      if (currentId === session.id) renderMessages();
    };
    textarea.addEventListener("keydown", (event) => { if (event.key === "Enter") finish(); });
    textarea.addEventListener("blur", finish);
    body.replaceChildren(textarea);
    textarea.focus();
  }

  // R-context-05：在原文基础上重新生成——原文就是这条摘要替代掉的那一段，
  // 它从未被删除（R-context-03），仍然原样躺在 session.messages 里，取回来
  // 再喂一遍填表提示词即可。生成失败时保留旧摘要，不写半截。
  async function regenerateSummary(message) {
    const session = current();
    if (!session) return;
    const at = session.messages.indexOf(message);
    if (at === -1) return;
    const head = session.messages.slice(at + 1, (message.replaced_through ?? at) + 1);
    if (head.length === 0) return;
    setError("");
    let text;
    try {
      text = await runSummarise(session, head, "正在重新生成摘要…");
    } catch (error) { setError(`重新生成摘要失败：${error.message}`); return; }
    if (!(text ?? "").trim()) { setError("重新生成摘要失败：模型没有返回内容"); return; }
    message.content = text.trim();
    try { await saveSession(session); }
    catch (error) { setError(`会话保存失败：${error.message}`); }
    if (currentId === session.id) renderMessages();
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

  els.sendBtn.addEventListener("click", () => (streaming ? streamAbort?.abort() : send()));
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
    try { await refreshSkills(); } catch (error) { setError(error.message); }
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

  return {
    init, refreshModels, setHeavyAllowed, showMessages, applyLlmStatus: renderLlm, refreshSessionsIfStale,
    rescanSkills: () => refreshSkills(true),
  };
}
