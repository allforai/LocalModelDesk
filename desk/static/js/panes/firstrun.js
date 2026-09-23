// ui:firstRunPane —— 全屏引导：选 models 目录 或 收编既有目录树（R-ui-09）。
// 目录选择用文本输入即完整可用（A5）；NSOpenPanel 注入是 shell 模块的事。
import * as api from "../api.js";
import { fitReportView } from "../pure/fit.js";

export function createFirstRunPane(root, ctx) {
  const els = {
    modelsRoot: root.querySelector("[data-fr-models-root]"),
    completeBtn: root.querySelector("[data-fr-complete]"),
    legacyRoot: root.querySelector("[data-fr-legacy]"),
    adoptBtn: root.querySelector("[data-fr-adopt]"),
    error: root.querySelector("[data-fr-error]"),
    keepCard: root.querySelector("[data-fr-keep-card]"),
    keepNote: root.querySelector("[data-fr-keep-note]"),
    keepBtn: root.querySelector("[data-fr-keep]"),
    found: root.querySelector("[data-fr-found]"),
    setup: root.querySelector("[data-fr-setup]"),
    report: root.querySelector("[data-fr-report]"),
    reportSummary: root.querySelector("[data-fr-report-summary]"),
    reportList: root.querySelector("[data-fr-report-list]"),
    reportError: root.querySelector("[data-fr-report-error]"),
    reportContinue: root.querySelector("[data-fr-report-continue]"),
  };
  const setError = (text) => { els.error.textContent = text ?? ""; };

  let currentRoot = null;

  // Found trees are suggestions the user picks, never a silent prefill: a stray 收编
  // must not move the models root onto whatever the scan happened to find.
  function renderFound(paths) {
    if (!els.found) return;
    const doc = root.ownerDocument;
    els.found.replaceChildren(...paths.map((path) => {
      const li = doc.createElement("li");
      const text = doc.createElement("code");
      text.textContent = path;
      const use = doc.createElement("button");
      use.type = "button";
      use.className = "btn-sm";
      use.textContent = "填入";
      use.setAttribute("aria-label", `填入 ${path}`);
      use.addEventListener("click", () => { els.legacyRoot.value = path; });
      li.append(text, use);
      return li;
    }));
  }

  function init(config) {
    currentRoot = config?.models_root ?? null;
    els.modelsRoot.value = currentRoot ?? "";
    const kept = config?.models_root_models ?? [];
    if (els.keepCard) {
      els.keepCard.hidden = kept.length === 0;
      els.keepNote.textContent = kept.length ? `${currentRoot} 里已有 ${kept.length} 个模型，可以不改目录直接回去。` : "";
    }
    renderFound((config?.discovered ?? []).filter((path) => path !== currentRoot));
  }

  function reportItem(doc, entry, tight) {
    const li = doc.createElement("li");
    li.textContent = tight ? `${entry.name}（偏紧）` : entry.name;
    return li;
  }

  function renderReport(catalog) {
    const view = fitReportView(catalog ?? []);
    const doc = root.ownerDocument;
    els.reportList?.replaceChildren();
    if (!view.capacityKnown) {
      // 算不出机器能力就不推荐任何模型——这条和 resources 页、desk.budget.budget
      // 里的同一条纪律：宁可老实说不知道，也不给一个可能坑用户下错模型的猜测。
      if (els.reportSummary) {
        els.reportSummary.textContent = "这台机器的重活能力还没能测出来，具体能跑多大的模型现在说不准——都下载后打开就知道了。";
      }
      return;
    }
    if (els.reportSummary) {
      els.reportSummary.textContent = view.fits.length || view.tight.length
        ? "这台机器能跑得动这些："
        : "这台机器上暂时没有能稳当跑的模型，勉强能跑的也标了出来：";
    }
    for (const entry of view.fits) els.reportList?.append(reportItem(doc, entry, false));
    for (const entry of view.tight) els.reportList?.append(reportItem(doc, entry, true));
  }

  // 目录定下来之后，先给用户一个「这台机器能跑什么」的起点，而不是直接扔回
  // 九个模型名字的台面。报告本身读不出来也不拦住首运——首运的主线是定目录，
  // 这一步失败只报错，进台面的按钮照常能用。
  async function showFitReport() {
    if (els.setup) els.setup.hidden = true;
    if (els.report) els.report.hidden = false;
    if (els.reportError) els.reportError.textContent = "";
    try {
      const payload = await api.listCatalog();
      renderReport(payload.models ?? payload);
    } catch (error) {
      if (els.reportError) els.reportError.textContent = `没能读出适配情况：${error.message}`;
    }
  }

  els.reportContinue?.addEventListener("click", () => ctx.onDone());

  els.keepBtn?.addEventListener("click", async () => {
    setError("");
    try {
      await api.completeFirstRun(currentRoot);
      await showFitReport();
    } catch (error) { setError(error.message); }
  });

  els.completeBtn.addEventListener("click", async () => {
    setError("");
    try {
      await api.completeFirstRun(els.modelsRoot.value.trim() || undefined);
      await showFitReport();
    } catch (error) { setError(error.message); }
  });

  els.adoptBtn.addEventListener("click", async () => {
    setError("");
    const legacy = els.legacyRoot.value.trim();
    if (!legacy) {
      setError("请填写既有目录树的根路径");
      return;
    }
    const mode = root.querySelector('input[name="fr-mode"]:checked')?.value ?? "point";
    try {
      await api.adoptLegacyModels(legacy, mode);
      await showFitReport();
    } catch (error) { setError(error.message); }
  });

  return { init };
}
