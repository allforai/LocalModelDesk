// ui:imagePane —— 会话式图片页（设计 docs/superpowers/specs/2026-09-24-image-sessions-design.md §5–§8）。
// 左栏会话列表、右侧尝试时间线 + 底部输入区。尝试记录只由后端写（D-14）：这里只读会话、
// 发起生成，作业结束后重新 GET 会话，从不自己把尝试标成完成或失败（D-27）。
import * as api from "../api.js";
import { confirmDialog } from "../widgets/confirm.js";
import { renderAttemptCard } from "../widgets/image_session_card.js";
import { beginRenameItem, renderSessionItem } from "../widgets/image_session_list.js";
import { parseStepProgress } from "../pure/job_progress.js";
import {
  availability, deleteMessage, orderSessions, pickCurrent, randomSeed, readImageParams, recomposeParams,
  refineChipText, refineChipVisible, refineFields, runningLabel, sessionTitle, startErrorText,
} from "../pure/image_session.js";

export function createImagePane(root, ctx = {}) {
  const doc = root.ownerDocument;
  const q = (name) => root.querySelector(`[data-image-${name}]`);
  const els = {
    prompt: q("prompt"), width: q("width"), height: q("height"), steps: q("steps"), seed: q("seed"),
    start: q("start"), error: q("error"), hint: q("hint"), hintText: q("hint-text"), returnBtn: q("return"),
    model: q("model"), advanced: q("advanced"), advancedError: q("advanced-error"),
    refine: q("refine"), refineText: q("refine-text"), refineClear: q("refine-clear"),
    timeline: q("timeline"), list: q("session-list"), sessionNew: q("session-new"), composer: q("composer"),
  };
  const confirm = ctx.confirm ?? confirmDialog;
  const drawSeed = ctx.randomSeed ?? randomSeed;

  let sessions = []; let listState = "loading"; let listError = ""; let loadedOnce = false;
  let currentId = null; let current = null; let currentCorrupt = false;
  let selectedId = null; let refineRef = null; let renaming = false;
  let job = null; let jobLog = "";
  let pending = false; let allowed = false; let busyReason = "正在检查服务状态…";
  let modelReason = "正在检查模型…"; let runtimeReason = "正在检查 MLX 运行环境…";
  let inflight = null; let polling = false; let viewToken = 0; let returnTo = null; let freshId = null;
  let runningRefs = null; let recomposeRefs = null; let expandedRefs = null;
  // 时间线该停在哪（D-71/D-72）："bottom" 贴底（打开会话、追加、落定），"selected" 让选中的展开卡片
  // 整张可见（点卡片、在这张基础上改、素材库回填），null 是用户自己滚过——之后只重算大图上限，不再拽动。
  let scrollIntent = null;
  const broken = new Set();

  const setError = (text) => { els.error.textContent = text ?? ""; };

  // ---------- availability (§7.6) ----------
  function currentAvailability() {
    return availability({
      pending, listState, currentId, currentCorrupt, current, job, sessions,
      allowed, busyReason, runtimeReason, modelReason,
    });
  }
  function updateAvailability() {
    const state = currentAvailability();
    els.start.disabled = state.disabled;
    els.start.title = state.reason;
    els.hintText.textContent = state.reason;
    returnTo = state.returnTo;
    els.returnBtn.hidden = !returnTo;
    els.hint.hidden = !state.reason;
    els.model.textContent = modelReason || "模型文件完整 · 可离线生成";
    if (recomposeRefs) {
      recomposeRefs.button.disabled = state.disabled;
      recomposeRefs.button.title = state.reason;
      recomposeRefs.hint.textContent = state.disabled ? state.reason : "";
    }
  }
  function setModelStatus(status) {
    modelReason = status?.state === "present" ? "" : status?.reason || (
      status?.state === "partial" ? "模型不完整，请到「资源」页继续下载或校验" :
      status?.state === "missing" ? "尚未安装图片模型，请到「资源」页下载" : "暂时无法确认模型状态，请稍后重试");
    updateAvailability();
  }
  function setRuntimeStatus(capability) {
    runtimeReason = capability?.present ? "" : capability?.detail || "图片 MLX 运行环境不可用，请检查服务或应用安装";
    updateAvailability();
  }
  function setHeavyAllowed(value, reason = "") {
    allowed = value; busyReason = reason; updateAvailability();
  }

  // ---------- 提示条（D-41/D-42） ----------
  function syncChip() {
    const visible = refineChipVisible(els.seed.value, refineRef);
    els.refine.hidden = !visible;
    els.refineText.textContent = visible ? refineChipText(refineRef) : "";
  }
  function clearSeedAndChip() { els.seed.value = ""; refineRef = null; syncChip(); }

  // ---------- 会话列表 ----------
  function renderList() {
    if (renaming) return;
    const items = [];
    if (listState === "loading") {
      const li = doc.createElement("li");
      li.className = "hint sessions-state";
      li.textContent = "正在加载会话…";
      items.push(li);
    } else if (listState === "error") {
      const li = doc.createElement("li");
      li.className = "sessions-state sessions-failed";
      const text = doc.createElement("p");
      text.className = "inline-error";
      text.textContent = `会话列表读不出来：${listError}`;
      const retry = doc.createElement("button");
      retry.className = "btn-secondary btn-sm";
      retry.textContent = "重试";
      retry.dataset.imageSessionsRetry = "";
      retry.addEventListener("click", () => { refresh(); });
      li.append(text, retry);
      items.push(li);
    } else {
      for (const summary of sessions) {
        items.push(renderSessionItem(doc, summary, {
          current: summary.id === currentId, onSelect: (s) => selectSession(s.id), onRename: beginRename, onDelete: removeSession,
        }));
      }
    }
    els.list.replaceChildren(...items);
  }

  function beginRename(li, summary) {
    renaming = true;
    beginRenameItem(doc, li, summary, async (title) => {
      if (title && title !== summary.title) {
        try { await api.renameImageSession(summary.id, title); }
        catch (error) { setError(error.message); }
      }
      renaming = false;
      await reloadList();
      if (summary.id === currentId) await loadSession(currentId);
    });
  }

  async function removeSession(summary) {
    const go = await confirm(doc, { title: "删除会话", message: deleteMessage(summary), confirmLabel: "删除" });
    if (!go) return;
    try {
      await api.deleteImageSession(summary.id);
    } catch (error) { setError(error.message); return; }
    if (summary.id === currentId) { currentId = null; current = null; currentCorrupt = false; }
    await refresh();
  }

  async function reloadList() {
    try { sessions = orderSessions(await api.listImageSessions(), freshId); }
    catch { return; } // 后台刷新失败时保留已显示的列表，下次轮询再取
    renderList(); updateAvailability();
  }

  // ---------- 时间线 ----------
  // 空态说明里用「」括起来的按钮名整体换行，不在名字中间断开。
  function emptyBlock(lines) {
    const box = doc.createElement("div");
    box.className = "image-empty";
    box.dataset.imageEmpty = "";
    lines.forEach((line, i) => {
      const p = doc.createElement("p");
      p.className = i === 0 ? "image-empty-title" : "hint";
      for (const part of line.split(/(「[^」]*」)/).filter(Boolean)) {
        const span = doc.createElement("span");
        if (part.startsWith("「")) span.className = "keep-together";
        span.textContent = part;
        p.append(span);
      }
      box.append(p);
    });
    return box;
  }

  function renderTimeline({ scroll = false } = {}) {
    runningRefs = null; recomposeRefs = null; expandedRefs = null;
    if (scroll) scrollIntent = "bottom";
    const keep = els.timeline.scrollTop;
    if (currentCorrupt) {
      els.timeline.replaceChildren(emptyBlock(["这个会话文件已损坏，无法显示。可以删除它，素材库里的图片不受影响。"]));
      updateAvailability();
      return;
    }
    if (!current) { els.timeline.replaceChildren(); updateAvailability(); return; }
    const attempts = current.attempts ?? [];
    if (!attempts.length) {
      els.timeline.replaceChildren(emptyBlock([
        "还没有图片", "在下面写下想要的画面，点「生成图片」。之后可以在任意一张上「在这张基础上改」或「换个构图」。",
      ]));
      updateAvailability();
      return;
    }
    if (!attempts.some((a) => a.id === selectedId)) selectedId = attempts.at(-1).id;
    const list = doc.createElement("ol");
    list.className = "image-attempts";
    attempts.forEach((attempt, index) => {
      const ours = job && job.attempt_id === attempt.id && job.status === "running";
      const card = renderAttemptCard(doc, {
        attempt, index, selected: attempt.id === selectedId, broken: broken.has(attempt.id),
        elapsed: ours ? job.elapsed_s : undefined, serveOutput: api.serveOutput,
        onBroken: (a) => { if (!broken.has(a.id)) { broken.add(a.id); renderTimeline(); } },
        onImageLoad: settleView, onRefine: refine, onRecompose: recompose, onCancel: cancelJob,
      });
      card.node.addEventListener("click", () => selectAttempt(attempt));
      card.node.addEventListener("keydown", (event) => {
        if (event.target && event.target !== card.node) return;
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault?.();
        selectAttempt(attempt, { focus: true });
      });
      if (card.running) runningRefs = { ...card.running, attemptId: attempt.id };
      if (card.recompose) recomposeRefs = card.recompose;
      if (card.node.getAttribute("aria-expanded") === "true") expandedRefs = { node: card.node, image: card.image };
      list.append(card.node);
    });
    els.timeline.replaceChildren(list);
    applyRunningDetails();
    els.timeline.scrollTop = scroll ? els.timeline.scrollHeight : keep;
    updateAvailability();
    watchExpanded();
    settleView();
  }

  // ---------- 展开卡片可见（D-71、D-72、D-74、D-78） ----------
  // 大图高度上限取「时间线可视高度 − 卡片里除大图以外的高度」（且不超过 60vh），这样标题、整张图、
  // 高级参数与两个动作能一起放进时间线；但大图不会为此缩到 IMAGE_FLOOR（缩略图的两倍）以下——放不下
  // 时让标题行滚出上沿，整张大图和两个动作仍在可见区（B-01）。然后按 scrollIntent 贴底或把展开卡片滚入可见区。
  // 图片加载完、窗口或输入区变高变矮、卡片里折叠块开合时都会重来一次（ResizeObserver + load）。
  const IMAGE_FLOOR = 192;
  const rect = (node) => (typeof node?.getBoundingClientRect === "function" ? node.getBoundingClientRect() : null);
  function timelineInner() {
    const style = doc.defaultView?.getComputedStyle?.(els.timeline);
    return els.timeline.clientHeight - (parseFloat(style?.paddingTop) || 0) - (parseFloat(style?.paddingBottom) || 0);
  }
  function fitExpandedImage() {
    const image = expandedRefs?.image;
    const card = rect(expandedRefs?.node); const shown = rect(image); const box = rect(els.timeline);
    if (!image || !card || !shown || !box || !els.timeline.clientHeight) return;
    const room = timelineInner() - (card.height - shown.height) - 4;
    image.style.maxHeight = `min(60vh, ${Math.max(IMAGE_FLOOR, Math.floor(room))}px)`;
  }
  function revealExpanded() {
    const card = rect(expandedRefs?.node); const box = rect(els.timeline);
    if (!card || !box) return;
    const inner = box.top + (els.timeline.clientTop || 0);
    const visibleBottom = inner + els.timeline.clientHeight;
    // 整张放得下就对齐卡片上沿；放不下（大图到了下限）就只保证从大图上沿到两个动作都可见。
    const image = rect(expandedRefs?.image);
    const anchor = card.height <= timelineInner() || !image ? card.top : image.top;
    if (anchor < inner) els.timeline.scrollTop -= inner - anchor + 4;
    else if (card.bottom > visibleBottom) els.timeline.scrollTop += Math.min(card.bottom - visibleBottom + 4, anchor - inner);
  }
  function settleView() {
    fitExpandedImage();
    if (scrollIntent === "bottom") els.timeline.scrollTop = els.timeline.scrollHeight;
    else if (scrollIntent === "selected") revealExpanded();
  }
  // 在下一帧再调整：直接在回调里改大图尺寸会让观察目标在同一帧里再变一次（ResizeObserver 循环告警）。
  let settleFrame = 0;
  const settleSoon = () => {
    const view = doc.defaultView;
    if (settleFrame || typeof view?.requestAnimationFrame !== "function") return settleFrame || settleView();
    settleFrame = view.requestAnimationFrame(() => { settleFrame = 0; settleView(); });
  };
  const resizeWatch = typeof doc.defaultView?.ResizeObserver === "function"
    ? new doc.defaultView.ResizeObserver(settleSoon) : null;
  resizeWatch?.observe(els.timeline);
  function watchExpanded() {
    if (!resizeWatch) return;
    resizeWatch.disconnect();
    resizeWatch.observe(els.timeline);
    if (expandedRefs?.node) resizeWatch.observe(expandedRefs.node);
  }
  // 用户自己滚动（滚轮、触控板、拖滚动条）后不再替他贴底或对齐，直到下一次打开、追加或选中。
  for (const type of ["wheel", "touchmove", "mousedown"]) {
    els.timeline.addEventListener(type, (event) => {
      if (type !== "mousedown" || event.target === els.timeline) scrollIntent = null;
    }, { passive: true });
  }
  // 用户自己滚回到底，就当作又贴底了：之后落定、窗口变化仍然停在最底下。
  els.timeline.addEventListener("scroll", () => {
    const t = els.timeline;
    if (scrollIntent === null && t.scrollHeight - t.scrollTop - t.clientHeight <= 2) scrollIntent = "bottom";
  }, { passive: true });

  function selectAttempt(attempt, { focus = false } = {}) {
    if (attempt.id === selectedId || attempt.status === "running") return;
    selectedId = attempt.id;
    scrollIntent = "selected";
    renderTimeline();
    if (focus) [...(els.timeline.querySelectorAll?.("[data-attempt-id]") ?? [])]
      .find((node) => node.dataset.attemptId === attempt.id)?.focus?.();
  }

  function applyRunningDetails() {
    if (!runningRefs) return;
    const ours = job && job.attempt_id === runningRefs.attemptId && job.status === "running";
    const progress = runningRefs.progress;
    const step = ours ? parseStepProgress(jobLog) : null;
    if (step) { progress.value = step.pct; }
    else { progress.removeAttribute?.("value"); }
    if (ours) {
      runningRefs.label.textContent = runningLabel(runningRefs.index, job.elapsed_s);
      runningRefs.log.textContent = jobLog;
      runningRefs.log.scrollTop = runningRefs.log.scrollHeight;
    }
  }

  // ---------- 会话加载与切换 ----------
  // 返回 "gone" 表示会话已不存在（被别处删掉），调用方负责重新选择。
  async function loadSession(id, { scroll = false } = {}) {
    const token = ++viewToken;
    try {
      const session = await api.getImageSession(id);
      if (token !== viewToken || id !== currentId) return "stale";
      const before = current?.id === id ? (current.attempts ?? []).map((a) => a.status).join() : null;
      const after = (session.attempts ?? []).map((a) => a.status).join();
      current = session; currentCorrupt = false;
      // 后端已经把这次作业的尝试落定，而 2 秒轮询还没取到作业结束：以会话文件为准，
      // 不再把它当成「正在生成」（尝试状态只由后端决定，D-14/D-27）。
      const settled = job?.status === "running" && (session.attempts ?? [])
        .find((a) => a.id === job.attempt_id && a.status !== "running");
      if (settled) job = { ...job, status: settled.status };
      renderTimeline({ scroll: scroll || before !== after });
      return "ok";
    } catch (error) {
      if (token !== viewToken || id !== currentId) return "stale";
      if (error.status === 404) { current = null; currentCorrupt = false; return "gone"; }
      if (error.status === 400) { current = null; currentCorrupt = true; renderTimeline(); return "corrupt"; }
      setError(error.message);
      return "error";
    } finally { updateAvailability(); }
  }

  function switchTo(id) {
    if (id !== currentId) { clearSeedAndChip(); selectedId = null; current = null; currentCorrupt = false; }
    currentId = id;
    renderList();
    renderTimeline();
  }

  async function selectSession(id) {
    if (id === currentId && (current || currentCorrupt)) return;
    setError("");
    switchTo(id);
    const outcome = await loadSession(id, { scroll: true });
    if (outcome === "gone") { currentId = null; await refresh(); }
    focusSession(id);
  }

  function focusSession(id) {
    [...(els.list.children ?? [])].find((node) => node.dataset?.sessionId === id)?.focus?.();
  }

  // D-62/D-63：拉列表；空则自动新建一个；按规则选当前会话并加载。并发调用共用同一次。
  function refresh() {
    if (inflight) return inflight;
    inflight = (async () => {
      if (!loadedOnce) { listState = "loading"; renderList(); updateAvailability(); }
      try {
        for (let round = 0; round < 3; round += 1) {
          let list = await api.listImageSessions();
          if (!list.length) { await api.createImageSession(); list = await api.listImageSessions(); }
          sessions = orderSessions(list, freshId); listState = "ready"; loadedOnce = true;
          switchTo(pickCurrent(sessions, currentId));
          if (!currentId) return;
          const outcome = await loadSession(currentId, { scroll: true });
          if (outcome !== "gone") return;
          currentId = null;
        }
      } catch (error) {
        if (!loadedOnce) { listState = "error"; listError = error.message; current = null; }
        else setError(error.message);
      } finally {
        inflight = null;
        renderList(); updateAvailability();
      }
    })();
    return inflight;
  }

  async function createSession() {
    setError("");
    try {
      const created = await api.createImageSession();
      freshId = created.id;
      sessions = orderSessions(await api.listImageSessions(), freshId);
      listState = "ready"; loadedOnce = true;
      switchTo(created.id);
      await loadSession(created.id, { scroll: true });
      els.prompt.focus?.();
    } catch (error) { setError(error.message); }
  }

  // ---------- 生成 ----------
  async function submitWithMemoryConfirm(params) {
    try { return await api.startImageJob(params); }
    catch (error) {
      if (error.code !== "insufficient_memory") throw error;
      const ok = await confirm(doc, { title: "内存可能不足", message: error.message, confirmLabel: "仍要生成" });
      return ok ? api.startImageJob({ ...params, force: true }) : null;
    }
  }

  async function startGeneration(params, { fromInputs }) {
    pending = true; setError(""); updateAvailability();
    try {
      const started = await submitWithMemoryConfirm(params);
      if (!started) return;
      job = started; jobLog = started.log ?? "";
      ctx.onStarted?.(started);
      if (fromInputs) clearSeedAndChip(); // D-65
      if (started.attempt_id) selectedId = started.attempt_id;
      if (started.session_id === currentId) await loadSession(currentId, { scroll: true });
      await reloadList();
    } catch (error) {
      if (error.code === "session_not_found") {
        currentId = null; current = null;
        pending = false;
        await refresh();
        const now = sessions.find((s) => s.id === currentId);
        setError(`这个会话已被删除，已切到「${sessionTitle(now)}」，请重新点「生成图片」`);
      } else setError(startErrorText(error));
    } finally { pending = false; updateAvailability(); }
  }

  function readInputs() {
    return { prompt: els.prompt.value, width: els.width.value, height: els.height.value, steps: els.steps.value, seed: els.seed.value };
  }

  async function startFromInputs() {
    if (els.start.disabled) return;
    els.advancedError.textContent = ""; setError("");
    let params;
    try { params = readImageParams(readInputs()); }
    catch (error) {
      if (error.advanced) { els.advanced.open = true; els.advancedError.textContent = error.message; }
      else setError(error.message);
      return;
    }
    await startGeneration({ session_id: currentId, ...params }, { fromInputs: true });
  }

  // D-40–D-43：回填、沿用种子、不提交；高级参数保持原折叠状态。
  function prefill(fields, ref) {
    els.prompt.value = fields.prompt ?? "";
    for (const name of ["width", "height", "steps"]) if (fields[name] != null) els[name].value = String(fields[name]);
    els.seed.value = fields.seed == null ? "" : String(fields.seed);
    refineRef = fields.seed == null ? null : ref;
    syncChip();
    els.composer?.scrollIntoView?.({ block: "nearest" });
    els.prompt.focus?.();
    const end = els.prompt.value.length;
    els.prompt.setSelectionRange?.(end, end);
  }

  function refine(attempt, index) {
    const fields = refineFields(attempt);
    if (attempt.id === selectedId) scrollIntent = "selected";
    prefill(fields, { seed: fields.seed, index });
    settleView(); // 提示条出现、输入区变高后，被点的这张仍整张可见（ResizeObserver 之外的同步一次）
  }

  function recompose(attempt) {
    if (currentAvailability().disabled || !currentId) return;
    startGeneration(recomposeParams(attempt, currentId, drawSeed), { fromInputs: false });
  }

  async function cancelJob() {
    try { applyJob(await api.cancelJob()); } catch (error) { setError(error.message); }
  }

  // ---------- 作业轮询（D-82、D-27） ----------
  // main.js 的 2 秒 tick 取到 kind == "image" 的作业时交给这里。
  function applyJob(payload, { replaceLog = false } = {}) {
    if (!payload || (payload.kind && payload.kind !== "image")) return;
    const previous = job;
    const sameJob = previous && previous.job_id === payload.job_id;
    if (!sameJob || replaceLog) jobLog = typeof payload.log === "string" ? payload.log : "";
    else if (typeof payload.log === "string") jobLog += payload.log;
    job = payload;
    const transition = !sameJob || previous.status !== payload.status;
    const attempts = current?.attempts ?? [];
    const shown = attempts.find((a) => a.id === payload.attempt_id);
    if (payload.status === "running") {
      if (runningRefs && runningRefs.attemptId === payload.attempt_id) applyRunningDetails();
      else if (payload.session_id && payload.session_id === currentId && (!shown || shown.status !== "running")) loadSession(currentId, { scroll: true });
    } else if (shown && shown.status === "running") {
      loadSession(currentId, { scroll: true });
    }
    if (transition) reloadList();
    updateAvailability();
  }

  // 每个 tick 调一次：作业已不在 running 而文件里仍是 running 时重取，直到后端落定（D-27）。
  async function poll(deskState) {
    if (!loadedOnce || polling || inflight) return;
    polling = true;
    try {
      const mediaBusy = !!deskState?.media_busy;
      const jobRunning = job?.status === "running";
      const stale = (current?.attempts ?? []).find((a) => a.status === "running"
        && !(jobRunning && job.attempt_id === a.id) && (!mediaBusy || (job && !jobRunning)));
      if (stale) await loadSession(currentId, { scroll: true });
      if (sessions.some((s) => s.running) && (!mediaBusy || (job && !jobRunning))) await reloadList();
    } finally { polling = false; }
  }

  // ---------- 素材库回填（D-94/D-95） ----------
  async function applyFill(plan) {
    await refresh();
    if (plan?.session_id && plan.attempt_id) {
      try {
        const session = await api.getImageSession(plan.session_id);
        const index = (session.attempts ?? []).findIndex((a) => a.id === plan.attempt_id);
        if (index >= 0) {
          setError("");
          switchTo(session.id);
          current = session;
          selectedId = plan.attempt_id;
          scrollIntent = "selected";
          renderTimeline();
          refine(session.attempts[index], index);
          return;
        }
      } catch { /* 会话已删或读不出来：按 D-95 停在当前会话 */ }
    }
    const fields = plan?.fields ?? {};
    prefill(fields, { seed: fields.seed ?? null, index: null });
  }

  // ---------- 事件 ----------
  els.start.addEventListener("click", startFromInputs);
  els.prompt.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && (event.metaKey || event.ctrlKey)) { event.preventDefault?.(); startFromInputs(); }
  });
  els.seed.addEventListener("input", syncChip);
  els.refineClear.addEventListener("click", clearSeedAndChip);
  els.sessionNew.addEventListener("click", createSession);
  els.returnBtn.addEventListener("click", () => { if (returnTo) selectSession(returnTo); });

  renderList();
  syncChip();
  updateAvailability();
  return { refresh, applyJob, poll, applyFill, setHeavyAllowed, setModelStatus, setRuntimeStatus };
}
