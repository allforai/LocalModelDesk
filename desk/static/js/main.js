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

const $ = (selector) => document.querySelector(selector);
const store = createStore({ activeTab: "chat" });
let panes; let statusbar; let settings; let failures = 0;
let jobActive = false; let jobLogFrom = 0; let lastJobId = null;

function fatal(message) { const el = $("#fatal"); el.hidden = false; el.textContent = message; }

async function boot() {
  let config;
  try { config = await api.readConfig(); } catch (error) { fatal(`无法读取配置：${error.message}`); return; }
  if (config.needs_setup ?? !config.first_run_done) enterFirstRun(config); else enterDesk();
}

function enterFirstRun(config) {
  const root = $("#pane-firstrun");
  const pane = createFirstRunPane(root, { onDone: () => { root.hidden = true; boot(); } });
  pane.init(config); root.hidden = false;
}

function enterDesk() {
  if (!panes) {
    statusbar = createStatusBar($("#statusbar"));
    const onStarted = (job) => { jobActive = job.status === "running"; lastJobId = job.job_id ?? null; jobLogFrom = job.next_log_from ?? 0; };
    panes = { chat:createChatPane($("#pane-chat")), video:createVideoPane($("#pane-video"), { onStarted }), music:createMusicPane($("#pane-music"), { onStarted }), resources:createResourcesPane($("#pane-resources")), library:createLibraryPane($("#pane-library"), { applyFill }) };
    settings = createSettingsPane($("#pane-settings"));
    $("[data-open-settings]").addEventListener("click", () => { $("#pane-settings").hidden = false; settings.init(); });
    $("[data-close-settings]").addEventListener("click", () => { $("#pane-settings").hidden = true; });
    for (const button of document.querySelectorAll("#tabs [data-tab]")) button.addEventListener("click", () => showTab(button.dataset.tab));
    globalThis.setInterval(tick, 2000);
  }
  panes.chat.init(); tick();
}

function showTab(name) {
  for (const button of document.querySelectorAll("#tabs [data-tab]")) button.classList.toggle("active", button.dataset.tab === name);
  for (const section of document.querySelectorAll("main > [data-pane]")) section.hidden = section.dataset.pane !== name;
  store.set({ activeTab:name });
  if (name === "resources") panes.resources.refresh();
  if (name === "library") panes.library.refresh();
}

function applyFill(plan) { if (plan) { panes[plan.pane].fill(plan.fields); showTab(plan.pane); } }

function applyHeavyAvailability(deskState) {
  const llm = heavyAvailability(deskState, "llm");
  const media = heavyAvailability(deskState, "media");
  panes.chat.setHeavyAllowed(llm.allowed, llm.reason);
  panes.video.setHeavyAllowed(media.allowed, media.reason);
  panes.music.setHeavyAllowed(media.allowed, media.reason);
}

async function tickJob() {
  const payload = await api.jobStatus(jobLogFrom, lastJobId);
  const pane = payload.kind === "music" ? panes.music : panes.video;
  if (payload.job_id !== lastJobId) { pane.jobView.reset(); lastJobId = payload.job_id; jobLogFrom = 0; }
  pane.jobView.apply(payload); jobLogFrom = payload.next_log_from ?? jobLogFrom;
  if (payload.status !== "running") jobActive = false;
}

async function tick() {
  try {
    const [deskState, memory] = await Promise.all([api.deskState(), api.memorySnapshot()]);
    failures = 0; statusbar.offline(false); statusbar.update(deskState, memory); applyHeavyAvailability(deskState); store.set({ deskState, memory });
    await panes.resources.refresh();
    if (deskState.media_busy) jobActive = true;
    if (jobActive) await tickJob();
  } catch (error) { failures += 1; if (failures >= 3) statusbar.offline(true); }
}

boot();
