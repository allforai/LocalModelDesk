// 会话式媒体页（图片、音乐）共用的会话控制器（设计 docs/superpowers/specs/2026-09-27-music-sessions-design.md §1，
// 图片页行为见 docs/superpowers/specs/2026-09-24-image-sessions-design.md §5–§8）。
// 左栏会话列表、右侧尝试时间线、忙碌原因、发起生成与作业轮询都在这里；卡片长什么样（renderCard）
// 与输入区（composer）由各页提供。尝试记录只由后端写（D-14）：这里只读会话、发起生成，
// 作业结束后重新 GET 会话，从不自己把尝试标成完成或失败（D-27）。
// 页面里的元素都按 data-<dataPrefix>-* 找：timeline、session-list、session-new、model、hint、hint-text、return、error；
// canCompose 时另找 composer（挑选合成模式里隐藏它），工具行与合成栏由这里创建（§1.3 M-05–M-11）。
import * as api from "../api.js";
import { addIcon } from "../icons.js";
import { describeJobError } from "../pure/job_error.js";
import { confirmDialog } from "../widgets/confirm.js";
import { beginRenameItem, renderSessionItem } from "../widgets/session_list.js";
import { parseStepProgress } from "../pure/job_progress.js";
import {
  availability, deleteMessage, orderSessions, pickCurrent, runningLabel, sessionTitle, startErrorText,
} from "../pure/media_session.js";

const camel = (name) => name.replace(/-([a-z])/g, (_, c) => c.toUpperCase());

// 页面没传 modelTexts（或漏了某一项）时的通用兜底文案，保证「模型缺失/运行环境不可用」时原因行不为空
// （空原因会让 availability 把这一条当没发生，生成仍然可点，见最终评审 Minor 1）。
const DEFAULT_MODEL_TEXTS = {
  missing: "尚未安装模型，请到「资源」页下载",
  runtime: "MLX 运行环境不可用，请检查服务或应用安装",
};

export function createSessionPane(root, {
  kind, noun, dataPrefix, emptyLines, modelTexts = {},
  renderCard, fitExpanded = null, composer, startJob,
  confirm: askConfirm, onStarted, canCompose = false,
}) {
  const confirm = askConfirm ?? confirmDialog;
  const doc = root.ownerDocument;
  const q = (name) => root.querySelector(`[data-${dataPrefix}-${name}]`);
  const els = {
    error: q("error"), hint: q("hint"), hintText: q("hint-text"), returnBtn: q("return"), model: q("model"),
    timeline: q("timeline"), list: q("session-list"), sessionNew: q("session-new"),
  };

  let sessions = []; let listState = "loading"; let listError = ""; let loadedOnce = false;
  let currentId = null; let current = null; let currentCorrupt = false;
  let selectedId = null; let renaming = false;
  let job = null; let jobLog = "";
  let pending = false; let allowed = false; let busyReason = "正在检查服务状态…";
  let modelReason = "正在检查模型…"; let runtimeReason = "正在检查 MLX 运行环境…";
  let inflight = null; let polling = false; let viewToken = 0; let returnTo = null; let freshId = null;
  let runningRefs = null; let secondaryRefs = null; let expandedRefs = null;
  // 时间线该停在哪（D-71/D-72）："bottom" 贴底（打开会话、追加、落定），"selected" 让选中的展开卡片
  // 整张可见（点卡片、在这张基础上改、素材库回填），null 是用户自己滚过——之后只重算大图上限，不再拽动。
  let scrollIntent = null;
  const broken = new Set();
  // 挑选合成模式（M-05–M-11）：picks 是已勾选尝试的 id，顺序即拼接顺序。
  let picking = false; let picks = []; let composeError = "";
  // 上次画时间线时交给卡片的 actionsBlocked（「重新拼接」的不可用原因）与是否有卡片用到它：
  // 原因变了且有卡片用到时重画，作业结束后按钮自己恢复（issue #18）。
  let lastBlocked = null; let blockedShown = false;
  const actionsBlockedOf = (state) => (state.disabled ? state.reason : "");

  const setError = (text) => { els.error.textContent = text ?? ""; };

  // ---------- availability (§7.6) ----------
  function currentAvailability() {
    return availability({
      pending, listState, currentId, currentCorrupt, current, job, sessions, kind,
      allowed, busyReason, runtimeReason, modelReason,
    }, { noun });
  }
  // 提示行、「回到该会话」与模型状态行由这里更新；生成按钮与卡片上的动作交给输入区（composer）。
  function updateAvailability() {
    const state = currentAvailability();
    els.hintText.textContent = state.reason;
    returnTo = state.returnTo;
    els.returnBtn.hidden = !returnTo;
    els.hint.hidden = !state.reason;
    els.model.textContent = modelReason || "模型文件完整 · 可离线生成";
    composer.updateAvailability?.(state, { secondary: secondaryRefs });
    updateCompose(state);
    if (blockedShown && actionsBlockedOf(state) !== lastBlocked) renderTimeline();
  }
  function setModelStatus(status) {
    modelReason = status?.state === "present" ? "" : status?.reason || (
      status?.state === "partial" ? "模型不完整，请到「资源」页继续下载或校验" :
      status?.state === "missing" ? (modelTexts.missing || DEFAULT_MODEL_TEXTS.missing) : "暂时无法确认模型状态，请稍后重试");
    updateAvailability();
  }
  function setRuntimeStatus(capability) {
    runtimeReason = capability?.present ? "" : capability?.detail || modelTexts.runtime || DEFAULT_MODEL_TEXTS.runtime;
    updateAvailability();
  }
  function setHeavyAllowed(value, reason = "") {
    allowed = value; busyReason = reason; updateAvailability();
  }

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
      retry.dataset[camel(`${dataPrefix}-sessions-retry`)] = "";
      retry.addEventListener("click", () => { refresh(); });
      li.append(text, retry);
      items.push(li);
    } else {
      for (const summary of sessions) {
        items.push(renderSessionItem(doc, summary, {
          current: summary.id === currentId, onSelect: (s) => selectSession(s.id), onRename: beginRename, onDelete: removeSession,
          kindClass: `${dataPrefix}-session`,
        }));
      }
    }
    els.list.replaceChildren(...items);
  }

  function beginRename(li, summary) {
    renaming = true;
    beginRenameItem(doc, li, summary, async (title) => {
      if (title && title !== summary.title) {
        try { await api.renameMediaSession(kind, summary.id, title); }
        catch (error) { setError(error.message); }
      }
      renaming = false;
      await reloadList();
      if (summary.id === currentId) await loadSession(currentId);
    });
  }

  async function removeSession(summary) {
    const go = await confirm(doc, { title: "删除会话", message: deleteMessage(summary, { noun }), confirmLabel: "删除" });
    if (!go) return;
    try {
      await api.deleteMediaSession(kind, summary.id);
    } catch (error) { setError(error.message); return; }
    if (summary.id === currentId) { currentId = null; current = null; currentCorrupt = false; }
    await refresh();
  }

  async function reloadList() {
    try { sessions = orderSessions(await api.listMediaSessions(kind), freshId); }
    catch { return; } // 后台刷新失败时保留已显示的列表，下次轮询再取
    renderList(); updateAvailability();
  }

  // ---------- 时间线 ----------
  // 空态说明里用「」括起来的按钮名整体换行，不在名字中间断开。
  function emptyBlock(lines) {
    const box = doc.createElement("div");
    box.className = `session-empty ${dataPrefix}-empty`;
    box.dataset[camel(`${dataPrefix}-empty`)] = "";
    lines.forEach((line, i) => {
      const p = doc.createElement("p");
      p.className = i === 0 ? `session-empty-title ${dataPrefix}-empty-title` : "hint";
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
    runningRefs = null; secondaryRefs = null; expandedRefs = null; blockedShown = false;
    lastBlocked = actionsBlockedOf(currentAvailability());
    if (scroll) scrollIntent = "bottom";
    const keep = els.timeline.scrollTop;
    if (currentCorrupt) {
      els.timeline.replaceChildren(emptyBlock([`这个会话文件已损坏，无法显示。可以删除它，素材库里的${noun}不受影响。`]));
      updateAvailability();
      return;
    }
    if (!current) { els.timeline.replaceChildren(); updateAvailability(); return; }
    const attempts = current.attempts ?? [];
    if (!attempts.length) {
      els.timeline.replaceChildren(emptyBlock(emptyLines));
      updateAvailability();
      return;
    }
    if (!attempts.some((a) => a.id === selectedId)) selectedId = attempts.at(-1).id;
    const pickedBefore = picks.length;
    prunePicks();
    if (picks.length !== pickedBefore) renderPicks(); // 已选的一段刷新后不可挑了：合成栏列表同步减少
    const list = doc.createElement("ol");
    list.className = `session-attempts ${dataPrefix}-attempts`;
    attempts.forEach((attempt, index) => {
      const card = renderCard(doc, {
        attempt, index, attempts, selected: attempt.id === selectedId, job, broken: broken.has(attempt.id),
        onBroken: (a) => { if (!broken.has(a.id)) { broken.add(a.id); renderTimeline(); } },
        onImageLoad: settleView,
        picking, pickIndex: picks.indexOf(attempt.id), onTogglePick: (a) => togglePick(a.id),
        actionsBlocked: lastBlocked,
      });
      if (card.usesActionsBlocked) blockedShown = true;
      // 挑选模式里点卡片切换勾选而不是展开（M-06）；勾选框自己的 click 冒泡上来时不再切一次（它走 change）。
      card.node.addEventListener("click", (event) => {
        if (!picking) selectAttempt(attempt);
        else if (event?.target?.type !== "checkbox") togglePick(attempt.id);
      });
      card.node.addEventListener("keydown", (event) => {
        if (event.target && event.target !== card.node) return;
        if (event.key !== "Enter" && event.key !== " ") return;
        event.preventDefault?.();
        if (picking) { togglePick(attempt.id); focusCard(attempt.id); }
        else selectAttempt(attempt, { focus: true });
      });
      if (card.running) runningRefs = { ...card.running, attemptId: attempt.id };
      if (card.secondary) secondaryRefs = card.secondary;
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
  // 展开卡片里有大图且页面给了 fitExpanded 时，先按「时间线可视高度 − 卡片里除大图以外的高度」算出
  // 大图可用的高度交给页面去定上限（图片页 IS D-74）；然后按 scrollIntent 贴底或把展开卡片滚入可见区。
  // 图片加载完、窗口或输入区变高变矮、卡片里折叠块开合时都会重来一次（ResizeObserver + load）。
  const rect = (node) => (typeof node?.getBoundingClientRect === "function" ? node.getBoundingClientRect() : null);
  function timelineInner() {
    const style = doc.defaultView?.getComputedStyle?.(els.timeline);
    return els.timeline.clientHeight - (parseFloat(style?.paddingTop) || 0) - (parseFloat(style?.paddingBottom) || 0);
  }
  function fitExpandedImage() {
    const image = expandedRefs?.image;
    if (!image || !fitExpanded) return;
    const card = rect(expandedRefs?.node); const shown = rect(image); const box = rect(els.timeline);
    if (!card || !shown || !box || !els.timeline.clientHeight) return;
    fitExpanded(image, timelineInner() - (card.height - shown.height) - 4);
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
    if (focus) focusCard(attempt.id);
  }
  // 时间线重画后卡片是新节点：键盘操作后把焦点还给同一张卡片。
  function focusCard(attemptId) {
    [...(els.timeline.querySelectorAll?.("[data-attempt-id]") ?? [])]
      .find((node) => node.dataset.attemptId === attemptId)?.focus?.();
  }

  // 页面用：按 id 选中当前会话里的一次尝试（同点卡片）。
  function selectAttemptById(id, { focus = false } = {}) {
    const attempt = (current?.attempts ?? []).find((a) => a.id === id);
    if (attempt) selectAttempt(attempt, { focus });
  }

  // 这一次正是选中展开的那张时，之后的落定让它整张可见（输入区变高后仍对齐它，D-72）。
  function keepInView(attemptId) {
    if (attemptId === selectedId) scrollIntent = "selected";
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
      const session = await api.getMediaSession(kind, id);
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
    if (id !== currentId) {
      composer.onSessionSwitch?.(); selectedId = null; current = null; currentCorrupt = false;
      broken.clear(); // 播放出错的标记只在本会话内有效；切回来时文件可能已恢复
      exitPicking({ render: false }); // M-10：切换、新建会话都退出挑选模式
    }
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
          let list = await api.listMediaSessions(kind);
          if (!list.length) { await api.createMediaSession(kind); list = await api.listMediaSessions(kind); }
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
      const created = await api.createMediaSession(kind);
      freshId = created.id;
      sessions = orderSessions(await api.listMediaSessions(kind), freshId);
      listState = "ready"; loadedOnce = true;
      switchTo(created.id);
      await loadSession(created.id, { scroll: true });
      composer.focus?.();
    } catch (error) { setError(error.message); }
  }

  // ---------- 生成 ----------
  async function submitWithMemoryConfirm(params, submit) {
    try { return await submit(params); }
    catch (error) {
      if (error.code !== "insufficient_memory") throw error;
      const ok = await confirm(doc, { title: "内存可能不足", message: error.message, confirmLabel: "仍要生成" });
      return ok ? submit({ ...params, force: true }) : null;
    }
  }

  // via：页面自己的另一种作业接口（如视频的配乐），走同样的提交 → onStarted → 选中新尝试 → 重载会话流程。
  async function startGeneration(params, { fromInputs, via = startJob }) {
    pending = true; setError(""); updateAvailability();
    try {
      const started = await submitWithMemoryConfirm(params, via);
      if (!started) return;
      job = started; jobLog = started.log ?? "";
      onStarted?.(started);
      composer.afterStart?.({ fromInputs }); // D-65
      if (started.attempt_id) selectedId = started.attempt_id;
      if (started.session_id === currentId) await loadSession(currentId, { scroll: true });
      await reloadList();
    } catch (error) {
      if (error.code === "session_not_found") {
        currentId = null; current = null;
        pending = false;
        await refresh();
        const now = sessions.find((s) => s.id === currentId);
        setError(`这个会话已被删除，已切到「${sessionTitle(now)}」，请重新点「${composer.startLabel}」`);
      } else setError(startErrorText(error));
    } finally { pending = false; updateAvailability(); }
  }

  async function cancelJob() {
    try { applyJob(await api.cancelJob()); } catch (error) { setError(error.message); }
  }

  // ---------- 挑选合成（§1.3 M-05–M-11） ----------
  const PICK_AT_LEAST_TWO = "至少要有两段完成的才能合成";
  const pickable = (attempt) => attempt?.status === "done" && typeof attempt.output === "string" && !!attempt.output
    && !attempt.output_missing && !broken.has(attempt.id);
  const attemptsNow = () => current?.attempts ?? [];
  const pickName = (id) => `第 ${attemptsNow().findIndex((a) => a.id === id) + 1} 次`;
  function prunePicks() { picks = picks.filter((id) => pickable(attemptsNow().find((a) => a.id === id))); }

  const compose = canCompose ? buildCompose() : null;
  function buildCompose() {
    const make = (tag, className, text) => {
      const node = doc.createElement(tag);
      if (className) node.className = className;
      if (text) node.textContent = text;
      return node;
    };
    const toolbar = make("div", "session-toolbar");
    const startBtn = make("button", "btn-secondary btn-sm", "挑几段合成…");
    startBtn.dataset[camel(`${dataPrefix}-compose-start`)] = "";
    startBtn.addEventListener("click", enterPicking);
    toolbar.append(startBtn);
    els.timeline.parentNode.insertBefore(toolbar, els.timeline);

    const bar = make("div", "compose-bar");
    bar.dataset[camel(`${dataPrefix}-compose-bar`)] = "";
    bar.setAttribute("role", "form");
    bar.setAttribute("aria-label", "挑几段合成");
    bar.hidden = true;
    const lead = make("p", "hint compose-lead", "勾选顺序就是拼接顺序：");
    const list = make("ol", "compose-picks");
    const submit = make("button", "btn-primary");
    submit.addEventListener("click", () => {
      if (!submit.disabled) startCompose([...picks]);
    });
    const cancel = make("button", "btn-secondary", "取消");
    cancel.addEventListener("click", () => exitPicking({ focus: true }));
    const actions = make("div", "compose-actions");
    actions.append(submit, cancel);
    const reason = make("p", "hint compose-reason");
    reason.setAttribute("role", "status");
    const error = make("p", "inline-error");
    error.dataset[camel(`${dataPrefix}-compose-error`)] = "";
    error.setAttribute("role", "alert");
    bar.append(lead, list, actions, reason, error);
    const composerNode = q("composer");
    composerNode.parentNode.insertBefore(bar, composerNode);
    return { startBtn, bar, list, submit, reason, error, composerNode };
  }

  function iconButton(made, label, icon, disabled, onClick) {
    const btn = doc.createElement("button");
    made.set(label, btn);
    btn.className = "btn-sm";
    btn.setAttribute("aria-label", label);
    btn.title = label;
    btn.disabled = disabled;
    addIcon(btn, icon, doc);
    btn.addEventListener("click", onClick);
    return btn;
  }

  // 已选列表：每项「第 N 次」＋上移、下移、移除；refocus 是刚点过的按钮名，重画后把焦点还给同名按钮。
  function renderPicks(refocus = null) {
    if (!compose) return;
    const move = (from, to) => {
      const next = [...picks];
      [next[from], next[to]] = [next[to], next[from]];
      picks = next;
    };
    const made = new Map();
    const rows = picks.map((id, i) => {
      const name = pickName(id);
      const li = doc.createElement("li");
      const label = doc.createElement("span");
      label.textContent = name;
      li.append(label,
        iconButton(made, `上移${name}`, "chevron-up", i === 0, () => { move(i, i - 1); afterPicksChange(`上移${name}`); }),
        iconButton(made, `下移${name}`, "chevron-down", i === picks.length - 1, () => { move(i, i + 1); afterPicksChange(`下移${name}`); }),
        iconButton(made, `移除${name}`, "x", false, () => { picks = picks.filter((p) => p !== id); afterPicksChange(); }));
      return li;
    });
    if (!rows.length) {
      const li = doc.createElement("li");
      li.className = "hint";
      li.textContent = "在上面的卡片里勾选要拼接的段落";
      rows.push(li);
    }
    compose.list.replaceChildren(...rows);
    if (refocus) {
      const target = made.get(refocus);
      if (target && !target.disabled) target.focus?.();
      else compose.submit.focus?.();
    }
  }
  function afterPicksChange(refocus = null) {
    renderPicks(refocus);
    renderTimeline();
  }

  // 合成栏主按钮、原因行、错误行与工具行按钮随可用性更新（M-05、M-08）。
  function updateCompose(state = currentAvailability()) {
    if (!compose) return;
    const count = attemptsNow().filter(pickable).length;
    compose.startBtn.disabled = count < 2 || picking;
    compose.startBtn.title = count < 2 ? PICK_AT_LEAST_TWO : "";
    compose.bar.hidden = !picking;
    compose.composerNode.hidden = picking;
    compose.submit.textContent = `合成（${picks.length} 段）`;
    compose.submit.disabled = picks.length < 2 || state.disabled;
    compose.reason.textContent = picks.length < 2 ? "至少选两段" : state.reason;
    compose.error.textContent = composeError;
  }

  function enterPicking() {
    if (!compose || picking || compose.startBtn.disabled) return;
    picking = true; picks = []; composeError = "";
    renderPicks();
    renderTimeline();
  }

  // focus：只有合成栏「取消」把焦点还给「挑几段合成…」；切换、新建会话与合成成功的退出不抢焦点。
  function exitPicking({ render = true, focus = false } = {}) {
    if (!picking) return;
    picking = false; picks = []; composeError = "";
    renderPicks();
    if (render) renderTimeline();
    else updateCompose();
    if (focus) compose.startBtn.focus?.();
  }

  // 只在挑选模式里、只对完成且文件在的尝试生效；再点一次取消勾选（同一段不会选两次，M-11）。
  function togglePick(id) {
    if (!picking) return;
    if (picks.includes(id)) picks = picks.filter((p) => p !== id);
    else if (pickable(attemptsNow().find((a) => a.id === id))) picks = [...picks, id];
    else return;
    afterPicksChange();
  }

  // 提交合成（M-09）；也给页面的「重新拼接」用（M-41）。合成不查内存，没有「仍要生成」确认。
  // 失败时挑选模式里写到合成栏错误行并留在模式内，否则写到页面错误行。
  // 已在提交或生成不可用（有作业在跑等）时不再发：快速双击只发一次（issue #18）。
  async function startCompose(parts) {
    if (pending || currentAvailability().disabled) return;
    const toBar = picking;
    pending = true; composeError = ""; setError(""); updateAvailability();
    try {
      const started = await api.startComposeJob({ kind, session_id: currentId, parts });
      job = started; jobLog = started.log ?? "";
      exitPicking({ render: false });
      onStarted?.(started);
      if (started.attempt_id) selectedId = started.attempt_id;
      if (started.session_id === currentId) await loadSession(currentId, { scroll: true });
      await reloadList();
    } catch (error) {
      const text = composeErrorText(error);
      if (toBar && picking) composeError = text;
      else setError(text);
    } finally { pending = false; updateAvailability(); }
  }

  // capability_missing 显示后端原话（「需要 ffmpeg 才能拼接成片」）；describeJobError 认得的码用它的标题，
  // 其余（段已不在、会话已删等）用后端原话，不笼统写成「生成失败」。
  function composeErrorText(error) {
    if (error?.code === "capability_missing") return error.message;
    const { title } = describeJobError({ code: error?.code, message: error?.message });
    return title && title !== "生成失败" ? title : error?.message || "合成没有开始";
  }

  // ---------- 作业轮询（D-82、D-27） ----------
  // main.js 的 2 秒 tick 取到本页这种媒体的作业时交给这里。
  function applyJob(payload, { replaceLog = false } = {}) {
    if (!payload || (payload.kind && payload.kind !== kind)) return;
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
  // 找到那一次就切过去、选中并交给 refine(attempt, index)；否则只用 prefillOnly(fields) 回填输入区。
  async function applyFill(plan, { refine, prefillOnly }) {
    await refresh();
    if (plan?.session_id && plan.attempt_id) {
      try {
        const session = await api.getMediaSession(kind, plan.session_id);
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
    prefillOnly(plan?.fields ?? {});
  }

  // ---------- 事件 ----------
  els.sessionNew.addEventListener("click", createSession);
  els.returnBtn.addEventListener("click", () => { if (returnTo) selectSession(returnTo); });

  renderList();
  updateAvailability();
  return {
    refresh, applyJob, poll, applyFill, cancelJob, setHeavyAllowed, setModelStatus, setRuntimeStatus,
    startGeneration, startCompose, togglePick, currentId: () => currentId, currentSession: () => current,
    selectAttempt: selectAttemptById, keepInView,
    availability: currentAvailability, setError, settleView, rerender: () => renderTimeline(),
  };
}
