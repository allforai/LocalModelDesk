// 视频参数 → 提交前的耗时提醒。只提醒有实测依据的组合：cross-exam 2026-09-13 q16，
// 1024×576 × 15 秒在 128 GB 机器上 20 分钟只走完 2/16 步。不编造分钟数估算。
const SLOW_SIZE = "1024x576";
const SLOW_FRAMES = 243; // 「约 10 秒」档

export function videoCostNote(size, frames) {
  if (size === SLOW_SIZE && Number(frames) >= SLOW_FRAMES) {
    return "清晰画幅加 10 秒以上会非常慢：实测曾 20 分钟只走完 2/16 步，可能要一小时以上。建议先用草稿画幅试效果。";
  }
  return "";
}
