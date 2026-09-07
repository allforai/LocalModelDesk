// data:deskState + data:memorySnapshot → 状态条视图（R-ui-07）。不含任何内存常量。
const GB = 1024 ** 3;
const REASON_TEXT = {
  media_busy: "媒体作业进行中",
  llm_loaded: "聊天模型驻留中",
  llm_already_held: "已有聊天模型驻留：先卸载，再加载另一个",
  transition_in_progress: "重活交接进行中",
  evict_failed: "让出内存失败，请重试或先手动卸载",
  memory_low: "可用内存不足",
  insufficient_memory: "可用内存不足",
};

function decisionFor(deskState, kind) {
  const canStart = deskState?.can_start;
  if (!canStart) return { ok: false, reason: null };
  return canStart[kind] ?? canStart;
}

export function heavyAvailability(deskState, kind) {
  const decision = decisionFor(deskState, kind);
  const reason = decision?.reason;
  const code = (typeof reason === "object" ? reason?.code : reason) ?? null;
  return {
    allowed: decision?.ok !== false,
    code,
    reason: REASON_TEXT[code] ?? (code ? `暂不可用（${code}）` : ""),
  };
}

export function renderState(deskState, snapshot, download = null, names = {}) {
  const gb = (n) => (n / GB).toFixed(1);
  const display = (key) => names?.[key] ?? key;
  const memText = snapshot && Number.isFinite(snapshot.total_bytes)
    ? `已用 ${gb(snapshot.used_bytes)} / 总 ${gb(snapshot.total_bytes)} GiB（可用 ${gb(snapshot.available_bytes)} GiB）`
    : "内存读数不可用";

  const holder = deskState?.holder ?? null;
  let holderText = "内存里：无";
  if (holder) {
    if (holder.kind === "llm") holderText = `内存里：${display(holder.label)}`;
    else if (holder.kind === "video") holderText = "视频生成中";
    else if (holder.kind === "music") holderText = "音乐生成中";
    else holderText = `${holder.kind}：${holder.label}`;
  }

  const downloading = download?.state === "running" ? download.key : null;
  const mediaText = `${deskState?.media_busy ? "媒体：生成中" : "媒体：空闲"}${downloading ? ` · 下载中 ${display(downloading)}` : ""}`;

  const nextKind = deskState?.media_busy || holder?.kind === "llm" ? "media" : "llm";
  const can = decisionFor(deskState, nextKind);
  const reason = typeof can?.reason === "object" ? can?.reason?.code : can?.reason;
  const ok = can ? can.ok !== false : false;
  const nextText = ok
    ? "可开下一件重活"
    : `不可：${REASON_TEXT[reason] ?? reason ?? "状态未知"}`;
  const tone = deskState?.media_busy || downloading ? "busy" : holder ? "ok" : ok ? "ok" : "error";
  return { memText, holderText, mediaText, nextText, nextOk: ok, nextIcon: ok ? "check" : "x", tone };
}
