// ui:settingsPane —— 保存 gateway 配置后显式 apply，并展示实际监听状态。
import * as api from "../api.js";
import { baseUrls } from "../pure/base_url.js";

export function createSettingsPane(root) {
  const els = {
    enabled: root.querySelector("[data-settings-enabled]"),
    host: root.querySelector("[data-settings-host]"),
    port: root.querySelector("[data-settings-port]"),
    save: root.querySelector("[data-settings-save]"),
    listening: root.querySelector("[data-settings-listening]"),
    error: root.querySelector("[data-settings-error]"),
    openaiUrl: root.querySelector("[data-settings-openai-url]"),
    anthropicUrl: root.querySelector("[data-settings-anthropic-url]"),
    lanNote: root.querySelector("[data-settings-lan-note]"),
    authWarning: root.querySelector("[data-settings-auth-warning]"),
    copyOpenai: root.querySelector("[data-settings-copy-openai]"),
    copyAnthropic: root.querySelector("[data-settings-copy-anthropic]"),
  };
  let urls = { openai: "", anthropic: "" };

  const setError = (text) => { els.error.textContent = text ?? ""; };

  function render(payload) {
    const config = payload.config ?? {};
    const status = payload.status ?? {};
    els.enabled.checked = config.enabled ?? status.enabled ?? false;
    els.host.value = config.host ?? status.host ?? "";
    els.port.value = config.port ?? status.port ?? "";
    els.listening.textContent = status.listening ? "监听中" : "未监听";
    els.listening.dataset.listening = String(Boolean(status.listening));
    setError(status.last_error);

    urls = baseUrls({
      host: status.host ?? config.host,
      port: status.port ?? config.port,
      lanHost: status.lan_host,
    });
    els.openaiUrl.textContent = urls.openai;
    els.anthropicUrl.textContent = urls.anthropic;
    els.lanNote.textContent = urls.note ?? "";
    els.lanNote.hidden = !urls.note;
    els.authWarning.textContent = "当前为无鉴权监听：同一网络任何设备都能调用本机模型";
  }

  async function save() {
    setError("");
    const port = Number(els.port.value);
    if (!Number.isInteger(port) || port < 1 || port > 65535) {
      setError("端口须在 1 到 65535 之间");
      return;
    }
    const host = els.host.value.trim();
    if (!host) {
      setError("主机不能为空");
      return;
    }
    const gateway = {
      enabled: els.enabled.checked,
      host,
      port,
    };
    try {
      await api.writeConfig({ gateway });
      render(await api.gatewayConfig(true));
    } catch (error) { setError(error.message); }
  }

  async function copy(url) {
    try { await globalThis.navigator.clipboard.writeText(url); }
    catch (error) { setError(error.message); }
  }

  els.save.addEventListener("click", save);
  els.copyOpenai.addEventListener("click", () => copy(urls.openai));
  els.copyAnthropic.addEventListener("click", () => copy(urls.anthropic));

  async function init() {
    try { render(await api.gatewayConfig()); }
    catch (error) { setError(error.message); }
  }

  return { init };
}
