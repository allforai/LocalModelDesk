// data:modelStatus + data:modelEntry (+ data:downloadProgress) → 资源面板行视图（R-ui-05）。
import { formatBytes, formatPercent } from "./format.js";
import { fitBadge, fitDetail } from "./fit.js";

// data:modelStatus → {badge, badgeKind} 短文案，present/partial/missing/unknown 四态。
// 资源页（rowView）和聊天页下拉都用它，避免各自拼一套状态说法。
export function statusBadge(status) {
  if (status.state === "present") return { badge: "齐", badgeKind: "ok" };
  if (status.state === "partial") return { badge: `一半 ${formatPercent(status.percent)}`, badgeKind: "busy" };
  if (status.state === "missing") return { badge: "没下", badgeKind: "none" };
  const reason = status.reason === "manifest_unavailable" || !status.reason ? "拿不到文件清单" : status.reason;
  return { badge: `未知：${reason}`, badgeKind: "unknown" };
}

export function rowView(entry, status, download = null) {
  const dl = download && download.state === "running" ? download : null;
  const isDownloading = dl !== null && dl.key === entry.key;
  const otherDownloading = dl !== null && dl.key !== entry.key;

  const { badge, badgeKind } = statusBadge(status);
  const pct = status.state === "present" ? 100 : status.state === "partial" ? status.percent : 0;

  let actions;
  if (isDownloading) actions = ["cancel"];
  else if (status.state === "present") actions = ["delete"];
  else if (status.state === "partial") actions = ["resume", "delete"];
  else if (status.state === "missing") actions = ["download"];
  else actions = [];

  const wantsDownload = actions.includes("download") || actions.includes("resume");
  const downloadDisabled = otherDownloading && wantsDownload;
  const notes = [];
  if (!isDownloading && status.state === "partial" && status.resumable_bytes > 0) notes.push(`已下 ${formatBytes(status.resumable_bytes)} 可续传`);
  if (status.stale_bytes > 0) notes.push(`另有 ${formatBytes(status.stale_bytes)} 旧版残片无法续传，开始下载时会清理`);
  return {
    key: entry.key,
    badge,
    badgeKind,
    pct,
    sizeText: Number.isFinite(status.bytes_expected) ? formatBytes(status.bytes_expected) : `${entry.gb} GiB（目录）`,
    diskText: formatBytes(status.disk_bytes),
    actions,
    downloadDisabled,
    downloadDisabledReason: downloadDisabled ? "已有一个下载在进行（同时只允许一个）" : null,
    missing: status.gaps ?? [],
    note: notes.length ? notes.join("；") : null,
    // 这台机器装不装得下——资源页的常驻标记，读的是目录端点自己带的判定
    // （desk.budget.budget.assess_fit），不是本文件另拼一套。
    fit: fitBadge(entry.fit),
    fitDetail: fitDetail(entry.fit),
  };
}
