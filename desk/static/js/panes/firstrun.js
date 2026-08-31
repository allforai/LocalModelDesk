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
  };
  const setError = (text) => { els.error.textContent = text ?? ""; };

  function init(config) {
    els.modelsRoot.value = config?.models_root ?? "";
  }

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
