// data:deskState + data:memorySnapshot → 状态条视图（R-ui-07）。不含任何内存常量。
const GB = 1024 ** 3;
const REASON_TEXT = {
  media_busy: "媒体作业进行中",
  llm_loaded: "聊天模型驻留中",
  transition_in_progress: "重活交接进行中",
  memory_low: "可用内存不足",
};

export function renderState(deskState, snapshot) {
  const gb = (n) => (n / GB).toFixed(1);
  const memText = snapshot && Number.isFinite(snapshot.total_bytes)
    ? `已用 ${gb(snapshot.used_bytes)} / 总 ${gb(snapshot.total_bytes)} GB（可用 ${gb(snapshot.available_bytes)} GB）`
    : "内存读数不可用";

  const holder = deskState?.holder ?? null;
  let holderText = "空闲";
  if (holder) {
    if (holder.kind === "llm") holderText = `LLM：${holder.label}`;
    else if (holder.kind === "video") holderText = "视频生成中";
    else if (holder.kind === "music") holderText = "音乐生成中";
    else holderText = `${holder.kind}：${holder.label}`;
  }

  const mediaText = deskState?.media_busy ? "媒体：生成中" : "媒体：空闲";
  const can = deskState?.can_start ?? null;
  const ok = can ? can.ok !== false : false;
  const nextText = ok
    ? "可开下一件重活"
    : `不可：${REASON_TEXT[can?.reason] ?? can?.reason ?? "状态未知"}`;
  const tone = holder || deskState?.media_busy ? "busy" : ok ? "ok" : "error";
  return { memText, holderText, mediaText, nextText, tone };
}
