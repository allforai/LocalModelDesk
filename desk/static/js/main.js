// ui:deskShell —— 所有周期性状态更新都由此唯一的 2 秒 tick 驱动。
import * as api from "./api.js";
import { createStore } from "./store.js";
import { createStatusBar } from "./widgets/statusbar.js";
import { createChatPane } from "./panes/chat.js";
import { createVideoPane } from "./panes/video.js";
import { createMusicPane } from "./panes/music.js";
import { createImagePane } from "./panes/image.js";
import { createResourcesPane } from "./panes/resources.js";
import { createLibraryPane } from "./panes/library.js";
import { createFirstRunPane } from "./panes/firstrun.js";
import { createSettingsPane } from "./panes/settings.js";
import { assistReason, heavyAvailability } from "./pure/desk_state.js";
import { hydrateIcons } from "./icons.js";
import { initialTab } from "./pure/tab_hash.js";
import { isDrawerCloseKey } from "./pure/drawer.js";
import { showFatal } from "./widgets/fatal.js";

const $ = (selector) => document.querySelector(selector);
const store = createStore({ activeTab: "chat" });
let activeTab = "chat";
let panes; let statusbar; let settings; let failures = 0; let modelNames = {};
let jobActive = false; let jobLogFrom = 0; let lastJobId = null; let mediaBusyReason = "";
// tick() 每 2 秒都会刷新资源面板，配置坏掉可能在开机之后才发生（比如运行中被外部
// 改坏）——一旦发现就只报一次致命屏，不要每个 tick 都重挂一遍「重新设置」监听器。
let configBroken = false;

async function boot() {
  let config;
  try { config = await api.readConfig(); } catch (error) {
    showFatal($("#fatal"), error, { resetConfig: api.resetConfig, reload: () => globalThis.location.reload() });
    return;
  }
  if (config.needs_setup ?? !config.first_run_done) enterFirstRun(config); else enterDesk();
}

function enterFirstRun(config) {
  const root = $("#pane-firstrun");
  setDeskShellHidden(true);
  const pane = createFirstRunPane(root, { onDone: () => { root.hidden = true; boot(); } });
  pane.init(config); root.hidden = false;
}

function enterDesk() {
  setDeskShellHidden(false);
  if (!panes) {
    statusbar = createStatusBar($("#statusbar"));
    api.listCatalog().then((entries) => { modelNames = Object.fromEntries((entries.models ?? entries).map((e) => [e.key, e.name])); }).catch(() => {});
    const onStarted = (job) => { jobActive = job.status === "running"; lastJobId = job.job_id ?? null; jobLogFrom = job.next_log_from ?? 0; };
    panes = {
      chat:createChatPane($("#pane-chat")), video:createVideoPane($("#pane-video"), { onStarted }),
      music:createMusicPane($("#pane-music"), { onStarted }), image:createImagePane($("#pane-image"), { onStarted }),
      resources:createResourcesPane($("#pane-resources"), {
        onModels: (models) => panes.image.setModelStatus(models?.find((m) => m.key === "qwen-image")),
        // 配置读不出来是整台机器级别的问题（不只是资源页），复用开机就有的那个
        // fatal 屏和「重新设置」入口，不为资源页另起一个说法（R-config-corrupt-01）。
        onConfigBroken: (error) => {
          if (configBroken) return;
          configBroken = true;
          setDeskShellHidden(true);
          showFatal($("#fatal"), error, { resetConfig: api.resetConfig, reload: () => globalThis.location.reload() });
        },
      }), library:createLibraryPane($("#pane-library"), { applyFill }),
    };
    settings = createSettingsPane($("#pane-settings"), { onReset: () => globalThis.location.reload() });
    $("[data-open-settings]").addEventListener("click", () => setDrawerOpen(true));
    $("[data-close-settings]").addEventListener("click", () => setDrawerOpen(false));
    document.addEventListener("keydown", (event) => { if (isDrawerCloseKey(event.key)) setDrawerOpen(false); });
    for (const button of document.querySelectorAll("#tabs [data-tab]")) button.addEventListener("click", () => showTab(button.dataset.tab));
    globalThis.addEventListener?.("hashchange", () => {
      const wanted = initialTab(globalThis.location?.hash);
      if (wanted !== activeTab) showTab(wanted);
    });
    globalThis.setInterval(tick, 2000);
  }
  panes.chat.init(); tick();
  showTab(initialTab(globalThis.location?.hash));
}

function setDeskShellHidden(hidden) {
  for (const selector of ["#statusbar", "#tabs", "main"]) $(selector).hidden = hidden;
}

function setDrawerOpen(open) {
  $("#pane-settings").hidden = !open;
  document.body.classList.toggle("drawer-open", open);
  if (open) settings.init();
}

function showTab(name) {
  activeTab = name;
  setDrawerOpen(false);
  for (const button of document.querySelectorAll("#tabs [data-tab]")) button.classList.toggle("active", button.dataset.tab === name);
  for (const section of document.querySelectorAll("main > [data-pane]")) section.hidden = section.dataset.pane !== name;
  store.set({ activeTab:name });
  if (globalThis.location) globalThis.history?.replaceState(null, "", `#tab=${name}`);
  if (name === "resources") panes.resources.refresh();
  if (name === "library") panes.library.refresh();
  if (name === "video") panes.video.jobView.sync({ busyReason: mediaBusyReason });
  if (name === "music") panes.music.jobView.sync({ busyReason: mediaBusyReason });
  if (name === "image") panes.image.refresh();
}

// 图片条目的回填要先找回它所在的会话（设计 D-94/D-95），由图片页自己处理。
function applyFill(plan) {
  if (!plan) return;
  if (plan.pane === "image") { showTab("image"); panes.image.applyFill(plan); return; }
  panes[plan.pane].fill(plan.fields); showTab(plan.pane);
}

function applyHeavyAvailability(deskState) {
  const llm = heavyAvailability(deskState, "llm");
  const media = heavyAvailability(deskState, "media");
  const llmAllowed = llm.allowed || llm.code === "llm_already_held";
  panes.chat.setHeavyAllowed(llmAllowed, llmAllowed ? "" : llm.reason);
  panes.video.setHeavyAllowed(media.allowed, media.reason);
  panes.music.setHeavyAllowed(media.allowed, media.reason);
  panes.image.setHeavyAllowed(media.allowed, media.reason);
  // Idle panes must say why they can't start, not silently keep the last
  // finished job's caption while their own button is disabled (F14, gap #9).
  mediaBusyReason = media.allowed ? "" : media.reason;
  panes.video.jobView.setBusyReason(mediaBusyReason);
  panes.music.jobView.setBusyReason(mediaBusyReason);
}

async function tickJob() {
  const payload = await api.jobStatus(jobLogFrom, lastJobId);
  const changed = payload.job_id !== lastJobId;
  if (changed) { lastJobId = payload.job_id; jobLogFrom = 0; }
  // 图片作业不再有固定的作业区：交给图片页按 attempt_id 找到对应卡片（设计 D-82/D-92）。
  if (payload.kind === "image") panes.image.applyJob(payload, { replaceLog: changed });
  else (panes[payload.kind] ?? panes.video).jobView.apply(payload, { replaceLog: changed, busyReason: mediaBusyReason });
  jobLogFrom = payload.next_log_from ?? jobLogFrom;
  if (payload.status !== "running") jobActive = false;
}

async function tick() {
  try {
    const [deskState, memory, llm, budget, capabilities] = await Promise.all([
      api.deskState(), api.memorySnapshot(), api.llmStatus(),
      // 预算读不到不该让整个 tick 失败：状态栏少一行后缀，比整条状态栏掉线好。
      api.budget().catch(() => null),
      api.capabilities().catch(() => null),
    ]);
    panes.image.setRuntimeStatus(capabilities?.image_runtime);
    const download = await panes.resources.refresh();
    failures = 0; statusbar.offline(false); statusbar.update(deskState, memory, download, modelNames, budget); applyHeavyAvailability(deskState); store.set({ deskState, memory });
    panes.chat.applyLlmStatus(llm, deskState);
    const reason = assistReason(llm, deskState);
    panes.video.setAssistAvailable(!reason, reason);
    panes.music.setAssistAvailable(!reason, reason);
    await panes.chat.refreshSessionsIfStale();
    if (deskState.media_busy) jobActive = true;
    if (jobActive) await tickJob();
    await panes.image.poll(deskState);
  } catch (error) {
    panes.image.setHeavyAllowed(false, "服务状态暂不可用，请稍后重试");
    failures += 1; if (failures >= 3) statusbar.offline(true);
  }
}

hydrateIcons(document);
boot();
