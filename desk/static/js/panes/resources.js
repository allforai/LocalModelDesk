// ui:resourcesPane —— 模型完整性、磁盘占用与单飞下载操作。
import * as api from "../api.js";
import { formatBytes } from "../pure/format.js";
import { rowView } from "../pure/model_status.js";
import { confirmDialog } from "../widgets/confirm.js";
import { addIcon } from "../icons.js";

const ACTION_LABEL = { download: "下载", resume: "续传", cancel: "取消", delete: "删除" };
const ACTION_ICON = { download: "download", resume: "refresh", cancel: "x", delete: "trash" };

export function createResourcesPane(root) {
  const doc = root.ownerDocument;
  let downloadProgress = null;
  const els = {
    refreshBtn: root.querySelector("[data-res-refresh]"),
    list: root.querySelector("[data-res-list]"),
    error: root.querySelector("[data-res-error]"),
    disk: root.querySelector("[data-res-disk]"),
  };

  function refreshLabel() {
    return els.refreshBtn?.querySelector?.("[data-label]") ?? els.refreshBtn;
  }

  async function refresh({ revalidate = false } = {}) {
    if (els.error) els.error.textContent = "";
    if (revalidate && els.refreshBtn) {
      els.refreshBtn.disabled = true;
      const label = refreshLabel();
      if (label) label.textContent = "校验中…";
    }
    try {
      const [catalogPayload, statusPayload, disk] = await Promise.all([
        api.listCatalog(), api.verifyAllModels(revalidate), api.diskUsage(),
      ]);
      const catalog = catalogPayload.models ?? catalogPayload;
      const statuses = statusPayload.models ?? [];
      downloadProgress = statusPayload.download ?? statusPayload.download_progress ?? downloadProgress;
      render(catalog, statuses, downloadProgress, disk ?? statusPayload.disk);
    } catch (err) {
      if (els.error) els.error.textContent = err.message;
    } finally {
      if (revalidate && els.refreshBtn) {
        els.refreshBtn.disabled = false;
        const label = refreshLabel();
        if (label) label.textContent = "重新校验";
      }
    }
    return downloadProgress;
  }

  function render(catalog, statuses, download, disk) {
    if (els.list) els.list.replaceChildren();
    const statusByKey = new Map(statuses.map((status) => [status.key, status]));
    for (const entry of catalog) {
      const status = statusByKey.get(entry.key) ?? { key: entry.key, state: "unknown" };
      els.list?.append(rowNode(entry, rowView(entry, status, download)));
    }
    if (els.disk && disk) {
      els.disk.textContent = `可用 ${formatBytes(disk.free_bytes)} / ${formatBytes(disk.total_bytes)}（剩余空间）`;
    }
  }

  function rowNode(entry, view) {
    const li = doc.createElement("li");
    li.className = "res-row";
    // The browser tests and future automation address a row by the catalog key,
    // not a localized display name.
    (li.dataset ??= {}).model = entry.key;

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
      button.className = action === "delete" ? "btn-danger" : action === "download" || action === "resume" ? "btn-primary" : "";
      button.textContent = ACTION_LABEL[action];
      addIcon(button, ACTION_ICON[action], doc);
      button.disabled = view.downloadDisabled && (action === "download" || action === "resume");
      if (button.disabled) button.title = view.downloadDisabledReason;
      button.addEventListener("click", async () => {
        if (button.disabled) return;
        try {
          if (action === "cancel") downloadProgress = await api.cancelDownload();
          else if (action === "delete") {
            // The small DOM doubles used by unit tests have no document body;
            // production deletes always require an explicit confirmation.
            if (doc.body && !await confirmDialog(doc, {
              title: "删除模型",
              message: `确定删除「${entry.name}」？将回收约 ${view.diskText} 磁盘空间。`,
              confirmLabel: "确认",
            })) return;
            await api.deleteModel(entry.key);
          }
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

  els.refreshBtn?.addEventListener("click", () => refresh({ revalidate: true }));
  return { refresh: () => refresh() };
}
