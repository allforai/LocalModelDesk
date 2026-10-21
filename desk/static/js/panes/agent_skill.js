// ui:agentSkillSection —— 设置页「本机 agent」：多选安装、检查、试用语（A-60..A-67）。
import * as api from "../api.js";
import { applyEnabled, initialChecked, rowText, TRY_PHRASE } from "../pure/agent_skill.js";

export function createAgentSkillSection(root) {
  const els = {
    list: root.querySelector("[data-agent-skill-list]"),
    apply: root.querySelector("[data-agent-skill-apply]"),
    check: root.querySelector("[data-agent-skill-check]"),
    checkResult: root.querySelector("[data-agent-skill-check-result]"),
    cli: root.querySelector("[data-agent-skill-cli]"),
    tryText: root.querySelector("[data-agent-skill-try]"),
    copy: root.querySelector("[data-agent-skill-copy]"),
    error: root.querySelector("[data-agent-skill-error]"),
  };
  let rows = [];
  let cli = {};
  let checked = new Set();

  const refreshApply = () => { els.apply.disabled = !applyEnabled(rows, checked, cli); };

  function render(payload) {
    rows = payload.targets ?? [];
    const doc = root.ownerDocument;
    els.list.replaceChildren(...rows.map((row) => {
      const li = doc.createElement("li");
      li.className = "agent-skill-row";
      li.dataset.key = row.key;
      li.dataset.state = row.state;
      const label = doc.createElement("label");
      label.className = "check-row";
      const box = doc.createElement("input");
      box.type = "checkbox";
      box.checked = checked.has(row.key);
      box.addEventListener("change", () => { if (box.checked) checked.add(row.key); else checked.delete(row.key); refreshApply(); });
      const name = doc.createElement("span");
      name.textContent = row.name;
      label.append(box, name);
      const detected = doc.createElement("span");
      detected.className = "hint";
      detected.textContent = row.detected ? "已检测到" : "未检测到";
      const { status, tone } = rowText(row);
      const badge = doc.createElement("span");
      badge.className = `badge badge-${tone === "ok" ? "ok" : tone === "warn" ? "busy" : "none"}`;
      badge.dataset.agentSkillStatus = "";
      badge.textContent = status;
      li.append(label, detected, badge);
      if (row.shared_note) {
        const note = doc.createElement("span");
        note.className = "hint";
        note.textContent = row.shared_note;
        li.append(note);
      }
      return li;
    }));
    cli = payload.cli ?? {};
    els.cli.textContent = `命令行 lmdesk：${cli.path ?? "~/.local/bin/lmdesk"} · ${rowText(cli).status}（至少勾选一个 agent 时自动安装）`;
    refreshApply();
  }

  async function load() {
    const payload = await api.agentSkillStatus();
    checked = initialChecked(payload.targets ?? []);
    render(payload);
  }

  els.apply.addEventListener("click", async () => {
    els.error.textContent = "";
    try {
      const payload = await api.agentSkillApply([...checked]);
      checked = initialChecked(payload.targets ?? []);
      render(payload);
      const failed = (payload.targets ?? []).filter((r) => r.result === "error");
      if (failed.length) els.error.textContent = failed.map((r) => `${r.name}：${rowText(r).status}`).join("；");
    } catch (error) { els.error.textContent = error.message; }
  });

  els.check.addEventListener("click", async () => {
    els.checkResult.textContent = "检查中…";
    try {
      const result = await api.agentSkillCheck();
      els.checkResult.textContent = result.ok ? "lmdesk 能连上台面 ✓" : result.message;
      render(await api.agentSkillStatus());   // 链接可能在台面外被改过：检查时顺手刷新各行，保留当前勾选（G9）
    } catch (error) { els.checkResult.textContent = error.message; }
  });

  els.tryText.textContent = TRY_PHRASE;
  els.copy.addEventListener("click", async () => {
    try { await globalThis.navigator.clipboard.writeText(TRY_PHRASE); }
    catch (error) { els.error.textContent = error.message; }
  });

  return { init: () => load().catch((error) => { els.error.textContent = error.message; }) };
}
