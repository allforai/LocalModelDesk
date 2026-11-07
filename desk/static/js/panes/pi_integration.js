import * as api from "../api.js";
import { integrationView, modelCommand, modelName, RELOAD_HINT } from "../pure/pi_integration.js";
import { confirmDialog } from "../widgets/confirm.js";

export function createPiIntegrationSection(root, ctx = {}) {
  const el = (name) => root.querySelector(`[data-pi-${name}]`);
  let state = {};
  let busy = false;
  let pollTimer;

  function render(payload = state) {
    const wasInstalling = state.pi_install?.state === "running";
    state = payload;
    if (wasInstalling && state.pi_install?.state !== "running") el("result").textContent = state.pi_install?.message ?? "";
    const installing = state.pi_install?.state === "running";
    const view = integrationView(state, busy);
    el("status").textContent = view.label;
    el("status").className = `badge badge-${view.tone}`;
    el("message").textContent = state.message ?? "";
    el("path").textContent = state.path ?? "";
    el("detected").textContent = state.pi_detected ? "已检测到 pi" : "未检测到 pi；点击安装将先运行 brew install --formula pi-coding-agent";
    el("log").textContent = state.pi_install?.output ?? "";
    el("log").hidden = !state.pi_install?.output;
    el("brew-message").textContent = state.pi_install?.message ?? "";
    el("install").disabled = view.installDisabled;
    el("remove").disabled = view.removeDisabled;
    el("check").disabled = busy || installing;
    el("refresh").disabled = busy;
    el("endpoints").textContent = `控制面：${state.desk_url ?? "—"} · 网关：${state.gateway_url ?? "—"}`;
    const doc = root.ownerDocument;
    el("models").replaceChildren(...(state.models ?? []).map((model) => {
      const li = doc.createElement("li");
      li.dataset.piModel = model.key;
      const key = doc.createElement("code"); key.textContent = `lmdesk/${model.key}`;
      const name = doc.createElement("strong"); name.textContent = modelName(model);
      const note = doc.createElement("span"); note.className = "hint"; note.textContent = model.note;
      const copy = doc.createElement("button"); copy.className = "btn-sm"; copy.textContent = "复制启动命令";
      copy.setAttribute("aria-label", `复制 ${model.key} 启动命令`);
      copy.addEventListener("click", async () => {
        try { await globalThis.navigator.clipboard.writeText(modelCommand(model.key)); el("result").textContent = `已复制 ${modelCommand(model.key)}`; }
        catch (error) { el("error").textContent = error.message; }
      });
      li.append(key, name, note, copy);
      return li;
    }));
    clearTimeout(pollTimer);
    if (installing) pollTimer = setTimeout(async () => {
      try { render(await api.piIntegrationStatus()); }
      catch (error) { el("error").textContent = `安装状态读取失败，请刷新状态：${error.message}`; }
    }, 1500);
  }

  async function perform(operation, success) {
    if (busy) return;
    busy = true;
    el("error").textContent = "";
    el("result").textContent = "处理中…";
    render();
    try {
      const result = await operation();
      render(await api.piIntegrationStatus());
      el("result").textContent = success(result);
    } catch (error) {
      el("error").textContent = error.message;
      el("result").textContent = "";
      try { render(await api.piIntegrationStatus()); } catch { /* keep the error visible */ }
    } finally { busy = false; render(); }
  }

  el("install").addEventListener("click", () => perform(() => api.piIntegrationApply("install"), (result) => result.pi_install?.state === "running" ? "正在安装 pi，完成后会自动安装接入扩展。请保持台面运行。" : result.pi_install?.state === "error" ? result.pi_install.message : "已安装或更新。请在 pi 执行 /reload，再用 /model 选择 lmdesk。不会改变 pi 默认模型。"));
  el("check").addEventListener("click", () => perform(api.piIntegrationCheck, (result) => `${result.ok ? "✓ " : "检查未通过："}${result.message}`));
  el("refresh").addEventListener("click", () => perform(api.piIntegrationStatus, () => "状态已刷新"));
  el("remove").addEventListener("click", async () => {
    const confirm = ctx.confirm ?? ((options) => confirmDialog(root.ownerDocument, options));
    if (busy || !await confirm({ title: "移除 pi 接入", message: "只移除台面管理的扩展与连接配置，不卸载 pi、不改默认模型。已有 pi 会话需 /reload 后生效。", confirmLabel: "移除接入" })) return;
    return perform(() => api.piIntegrationApply("remove"), () => "已移除。请在 pi 执行 /reload；台面模型和会话未改动。");
  });
  el("hint").textContent = RELOAD_HINT;
  return { init: () => perform(api.piIntegrationStatus, () => "") };
}
