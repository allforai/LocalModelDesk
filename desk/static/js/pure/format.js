// 字节 / 百分比 / 时长 / 速率 / 时间戳 格式化。零 DOM、零 fetch。
const GB = 1024 ** 3;
const MB = 1024 ** 2;
const KB = 1024;

export function formatBytes(bytes) {
  if (!Number.isFinite(bytes) || bytes < 0) return "—";
  if (bytes >= GB) return `${(bytes / GB).toFixed(1)} GiB`;
  if (bytes >= MB) return `${Math.round(bytes / MB)} MiB`;
  if (bytes >= KB) return `${Math.round(bytes / KB)} KiB`;
  return `${bytes} B`;
}

export function formatPercent(pct) {
  if (!Number.isFinite(pct)) return "0%";
  return `${Math.max(0, Math.min(100, Math.round(pct)))}%`;
}

export function formatDuration(seconds) {
  if (!Number.isFinite(seconds) || seconds < 0) return "—";
  const s = Math.round(seconds);
  if (s < 60) return `${s}秒`;
  const m = Math.floor(s / 60);
  if (m < 60) return `${m}分${String(s % 60).padStart(2, "0")}秒`;
  return `${Math.floor(m / 60)}时${String(m % 60).padStart(2, "0")}分`;
}

// 状态条 / 菜单栏共用的内存读数格式：取整到 GiB（N3 —— 同屏三处读数曾因 0.4 GiB 的
// 轮询抖动各自四舍五入到 79.0/79.4/79.2，互不相同；取整后三处必须一致，macOS 菜单栏
// 的 memoryMenuTitle 用同一进制、同一取整方式）。
export function formatMemoryLine(usedBytes, totalBytes, availableBytes) {
  const gib = (n) => Math.round(n / GB);
  return `已用 ${gib(usedBytes)} / 总 ${gib(totalBytes)} GiB（可用 ${gib(availableBytes)} GiB）`;
}

export function formatRate(bps) {
  if (!Number.isFinite(bps) || bps <= 0) return "—";
  return `${formatBytes(bps)}/s`;
}

export function formatTimestamp(iso) {
  if (typeof iso !== "string" || iso.length < 16) return "—";
  return `${iso.slice(0, 10)} ${iso.slice(11, 16)}`;
}
