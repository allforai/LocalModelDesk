// ui:deskShell —— 所有周期性状态更新都由此唯一的 2 秒 tick 驱动。
import * as api from "./api.js";
import { createStore } from "./store.js";
import { createStatusBar } from "./widgets/statusbar.js";
import { createChatPane } from "./panes/chat.js";
import { createVideoPane } from "./panes/video.js";
import { createMusicPane } from "./panes/music.js";
import { createResourcesPane } from "./panes/resources.js";
import { createLibraryPane } from "./panes/library.js";
import { createFirstRunPane } from "./panes/firstrun.js";
import { createSettingsPane } from "./panes/settings.js";
import { heavyAvailability } from "./pure/desk_state.js";
import { hydrateIcons } from "./icons.js";
import { initialTab } from "./pure/tab_hash.js";
import { isDrawerCloseKey } from "./pure/drawer.js";
import { showFatal } from "./widgets/fatal.js";

const $ = (selector) => document.querySelector(selector);
const store = createStore({ activeTab: "chat" });
let activeTab = "chat";
let panes; let statusbar; let settings; let failures = 0; let modelNames = {};
let jobActive = false; let jobLogFrom = 0; let lastJobId = null; let mediaBusyReason = "";

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
    panes = { chat:createChatPane($("#pane-chat")), video:createVideoPane($("#pane-video"), { onStarted }), music:createMusicPane($("#pane-music"), { onStarted }), resources:createResourcesPane($("#pane-resources")), library:createLibraryPane($("#pane-library"), { applyFill }) };
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
}

function applyFill(plan) { if (plan) { panes[plan.pane].fill(plan.fields); showTab(plan.pane); } }

function applyHeavyAvailability(deskState) {
  const llm = heavyAvailability(deskState, "llm");
  const media = heavyAvailability(deskState, "media");
  const llmAllowed = llm.allowed || llm.code === "llm_already_held";
  panes.chat.setHeavyAllowed(llmAllowed, llmAllowed ? "" : llm.reason);
  panes.video.setHeavyAllowed(media.allowed, media.reason);
  panes.music.setHeavyAllowed(media.allowed, media.reason);
  // Idle panes must say why they can't start, not silently keep the last
  // finished job's caption while their own button is disabled (F14, gap #9).
  mediaBusyReason = media.allowed ? "" : media.reason;
  panes.video.jobView.setBusyReason(mediaBusyReason);
  panes.music.jobView.setBusyReason(mediaBusyReason);
}

async function tickJob() {
  const payload = await api.jobStatus(jobLogFrom, lastJobId);
  const pane = payload.kind === "music" ? panes.music : panes.video;
  const changed = payload.job_id !== lastJobId;
  if (changed) { lastJobId = payload.job_id; jobLogFrom = 0; }
  pane.jobView.apply(payload, { replaceLog: changed, busyReason: mediaBusyReason }); jobLogFrom = payload.next_log_from ?? jobLogFrom;
  if (payload.status !== "running") jobActive = false;
}

async function tick() {
  try {
    const [deskState, memory, llm] = await Promise.all([api.deskState(), api.memorySnapshot(), api.llmStatus()]);
    const download = await panes.resources.refresh();
    failures = 0; statusbar.offline(false); statusbar.update(deskState, memory, download, modelNames); applyHeavyAvailability(deskState); store.set({ deskState, memory });
    panes.chat.applyLlmStatus(llm, deskState);
    await panes.chat.refreshSessionsIfStale();
    if (deskState.media_busy) jobActive = true;
    if (jobActive) await tickJob();
  } catch (error) { failures += 1; if (failures >= 3) statusbar.offline(true); }
}

hydrateIcons(document);
boot();
