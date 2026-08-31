// (模型字节数, data:memorySnapshot) → 是否需要加载前警告（R-ui-08，阈值规则 A2）。
import { formatBytes } from "./format.js";

export function needsWarning(modelBytes, snapshot) {
  if (!Number.isFinite(modelBytes) || modelBytes <= 0) return { warn: false, message: null };
  const available = snapshot?.available_bytes;
  if (!Number.isFinite(available)) return { warn: false, message: null };
  if (modelBytes >= available) {
    return {
      warn: true,
      message: `该模型约需 ${formatBytes(modelBytes)}，当前可用内存仅 ${formatBytes(available)}，` +
        "加载可能打满内存。确定继续？",
    };
  }
  return { warn: false, message: null };
}
