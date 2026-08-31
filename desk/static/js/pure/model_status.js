// data:modelStatus + data:modelEntry (+ data:downloadProgress) → 资源面板行视图（R-ui-05）。
import { formatBytes, formatPercent } from "./format.js";

export function rowView(entry, status, download = null) {
  const dl = download && download.state === "running" ? download : null;
  const isDownloading = dl !== null && dl.key === entry.key;
  const otherDownloading = dl !== null && dl.key !== entry.key;

  let badge;
  let pct = 0;
  if (status.state === "present") { badge = "齐"; pct = 100; }
  else if (status.state === "partial") { pct = status.percent; badge = `一半 ${formatPercent(status.percent)}`; }
  else if (status.state === "missing") { badge = "没下"; }
  else badge = `未知（${status.reason ?? "manifest_unavailable"}）`;

  let actions;
  if (isDownloading) actions = ["cancel"];
  else if (status.state === "present") actions = ["delete"];
  else if (status.state === "partial") actions = ["resume", "delete"];
  else if (status.state === "missing") actions = ["download"];
  else actions = [];

  const wantsDownload = actions.includes("download") || actions.includes("resume");
  const downloadDisabled = otherDownloading && wantsDownload;
  return {
    key: entry.key,
    badge,
    pct,
    sizeText: `${entry.gb} GB`,
    diskText: formatBytes(status.disk_bytes),
    actions,
    downloadDisabled,
    downloadDisabledReason: downloadDisabled ? "已有一个下载在进行（同时只允许一个）" : null,
    missing: status.gaps ?? [],
  };
}
