// ui:firstRunPane —— 全屏引导：选 models 目录 或 收编既有目录树（R-ui-09）。
// 目录选择用文本输入即完整可用（A5）；NSOpenPanel 注入是 shell 模块的事。
import * as api from "../api.js";

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

  els.keepBtn?.addEventListener("click", async () => {
    setError("");
    try {
      await api.completeFirstRun(currentRoot);
      ctx.onDone();
    } catch (error) { setError(error.message); }
  });

  els.completeBtn.addEventListener("click", async () => {
    setError("");
    try {
      await api.completeFirstRun(els.modelsRoot.value.trim() || undefined);
      ctx.onDone();
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
      ctx.onDone();
    } catch (error) { setError(error.message); }
  });

  return { init };
}
