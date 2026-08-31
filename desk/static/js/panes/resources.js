// ui:resourcesPane —— 模型完整性、磁盘占用与单飞下载操作。
import * as api from "../api.js";
import { formatBytes } from "../pure/format.js";
import { rowView } from "../pure/model_status.js";

const ACTION_LABEL = { download: "下载", resume: "续传", cancel: "取消", delete: "删除" };

export function createResourcesPane(root) {
  const doc = root.ownerDocument;
  let downloadProgress = null;
  const els = {
    refreshBtn: root.querySelector("[data-res-refresh]"),
    list: root.querySelector("[data-res-list]"),
    error: root.querySelector("[data-res-error]"),
    disk: root.querySelector("[data-res-disk]"),
  };

  async function refresh() {
    if (els.error) els.error.textContent = "";
    try {
      const [catalogPayload, statusPayload, disk] = await Promise.all([
        api.listCatalog(), api.verifyAllModels(), api.diskUsage(),
      ]);
      const catalog = catalogPayload.models ?? catalogPayload;
      const statuses = statusPayload.models ?? [];
      downloadProgress = statusPayload.download ?? statusPayload.download_progress ?? downloadProgress;
      render(catalog, statuses, downloadProgress, disk ?? statusPayload.disk);
    } catch (err) {
      if (els.error) els.error.textContent = err.message;
    }
  }

  function render(catalog, statuses, download, disk) {
    if (els.list) els.list.replaceChildren();
    const statusByKey = new Map(statuses.map((status) => [status.key, status]));
    for (const entry of catalog) {
      const status = statusByKey.get(entry.key) ?? { key: entry.key, state: "unknown" };
      els.list?.append(rowNode(entry, rowView(entry, status, download)));
    }
    if (els.disk && disk) {
      els.disk.textContent = `可用 ${formatBytes(disk.free_bytes)} / ${formatBytes(disk.total_bytes)}`;
    }
  }

  function rowNode(entry, view) {
    const li = doc.createElement("li");
    li.className = "res-row";
    li.textContent = `${entry.name} · ${view.badge} · 预计 ${view.sizeText} · 占用 ${view.diskText}`;

    const title = doc.createElement("p");
    title.textContent = entry.name;
    const meta = doc.createElement("p");
    meta.className = "res-meta";
    meta.textContent = `${view.badge} · 预计 ${view.sizeText} · 占用 ${view.diskText}`;
    li.append(title, meta);
    if (view.pct > 0 && view.pct < 100) {
      const progress = doc.createElement("progress");
      progress.value = view.pct;
      progress.max = 100;
      progress.textContent = `${view.pct}%`;
      li.append(progress);
    }
    if (view.missing.length) li.append(missingNode(view.missing));

    const actions = doc.createElement("div");
    actions.className = "res-actions";
    for (const action of view.actions) {
      const button = doc.createElement("button");
      button.type = "button";
      button.textContent = ACTION_LABEL[action];
      button.disabled = view.downloadDisabled && (action === "download" || action === "resume");
      if (button.disabled) button.title = view.downloadDisabledReason;
      button.addEventListener("click", async () => {
        if (button.disabled) return;
        try {
          if (action === "cancel") downloadProgress = await api.cancelDownload();
          else if (action === "delete") await api.deleteModel(entry.key);
          else downloadProgress = await api.startDownload(entry.key);
          await refresh();
        } catch (err) {
          if (els.error) els.error.textContent = err.message;
        }
      });
      actions.append(button);
    }
    li.append(actions);
    return li;
  }

  function missingNode(gaps) {
    const details = doc.createElement("details");
    const summary = doc.createElement("summary");
    summary.textContent = `缺失文件（${gaps.length}）`;
    const list = doc.createElement("ul");
    for (const gap of gaps) {
      const item = doc.createElement("li");
      item.textContent = gap.path;
      list.append(item);
    }
    details.append(summary, list);
    return details;
  }

  els.refreshBtn?.addEventListener("click", refresh);
  return { refresh };
}
