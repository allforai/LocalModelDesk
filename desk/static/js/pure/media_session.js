// 会话式媒体页（图片、音乐…）通用的纯逻辑（设计 docs/superpowers/specs/2026-09-24-image-sessions-design.md，
// 音乐会话见 docs/superpowers/specs/2026-09-27-music-sessions-design.md）。
// 零 DOM、零 fetch：卡片文案、当前会话选择、不可用原因、删除确认都在这里算好，各媒体页的
// panes/*.js 只负责把结果画出来；各媒体特有的参数与卡片文案（如图片的 specLine、attemptView）
// 留在各自的 pure/*_session.js 里。
import { describeJobError } from "./job_error.js";
import { formatDuration } from "./format.js";

export const SEED_MAX = 4294967295;

// 卡片状态 → {kind, badge, title, sub, icon, tone}（D-73、D-84、D-85；V-10）。
// kind ∈ running | done | failed | cancelled | missing；missing 是 done 但文件不在
// （后端 output_missing，或前端加载触发 error 后由调用方传 broken=true）。noun 决定缺文件文案，
// 各媒体页传自己的名词（图片、音频、视频…），默认「图片」；icon 同理决定缺文件图标，默认「image」。
export function attemptView(attempt, { broken = false, noun = "图片", icon = "image" } = {}) {
  const status = attempt?.status;
  if (status === "running") return { kind: "running", badge: "生成中", title: "", sub: "", icon: null, tone: "busy" };
  if (status === "done" && !attempt.output_missing && !broken && attempt.output)
    return { kind: "done", badge: "", title: "", sub: "", icon: null, tone: "" };
  if (status === "done") {
    const text = `${noun}文件已不在`;
    return { kind: "missing", badge: text, title: text, sub: "可能已在访达中移动或删除", icon, tone: "muted" };
  }
  if (status === "cancelled") {
    const onQuit = attempt?.error?.code === "cancelled_on_quit";
    // 用户取消：标记「已取消」之外，说明取存进文件的原话（D-09「已取消：这次生成被手动停止」），
    // 去掉与标记重复的前缀；退出取消的标题本身就是原因，不再重复。
    const said = onQuit ? "" : String(attempt?.error?.message ?? "").replace(/^\s*已取消\s*[：:]?\s*/, "").trim();
    return { kind: "cancelled", badge: "已取消", title: onQuit ? "应用退出时停止了这次生成" : "已取消", sub: said, icon: "x", tone: "muted" };
  }
  const error = attempt?.error ?? null;
  const title = error?.code === "interrupted" ? "应用在生成途中关闭，这次没有完成" : (describeJobError(error).title || "生成失败");
  return { kind: "failed", badge: "失败", title, sub: "", icon: "x", tone: "danger" };
}

// D-11：连续空白折叠、去首尾空白、超过 24 字取前 24 字加「…」（与聊天 displayTitle 同规则）。
export function autoTitle(prompt) {
  const text = String(prompt ?? "").replace(/\s+/g, " ").trim();
  return text.length > 24 ? `${text.slice(0, 24)}…` : text;
}

export function sessionTitle(summary) {
  if (summary?.corrupt) return "无法读取的会话";
  const title = typeof summary?.title === "string" ? summary.title.trim() : "";
  return title || "新会话";
}

const clock = (iso) => (typeof iso === "string" && iso.length >= 16 ? iso.slice(11, 16) : "");

// D-77：「N 次生成 · HH:MM」；坏文件「文件已损坏」（§7.2）。
export function sessionMeta(summary) {
  if (summary?.corrupt) return "文件已损坏";
  const count = Number.isInteger(summary?.attempt_count) ? summary.attempt_count : (summary?.attempts?.length ?? 0);
  return [`${count} 次生成`, clock(summary?.updated)].filter(Boolean).join(" · ");
}

export function attemptLabel(index, attempt) {
  return [`第 ${index + 1} 次`, clock(attempt?.ts)].filter(Boolean).join(" · ");
}

// D-81：running 卡片的标题行，已用时长用 formatDuration 的文案。
export function runningLabel(index, elapsedSeconds) {
  const elapsed = Number.isFinite(elapsedSeconds) ? `（已用 ${formatDuration(elapsedSeconds)}）` : "";
  return `第 ${index + 1} 次 · 生成中…${elapsed}`;
}

// 32 位无符号随机整数（0–4294967295），来自 crypto.getRandomValues。
export function randomSeed(cryptoImpl = globalThis.crypto) {
  const buffer = new Uint32Array(1);
  cryptoImpl.getRandomValues(buffer);
  return buffer[0];
}

// 列表顺序：按 updated 降序（后端已排），坏文件最后；同一秒内的并列项让刚新建的那个排最上（D-60）。
export function orderSessions(list, freshId = null) {
  const items = Array.isArray(list) ? [...list] : [];
  const key = (s) => (s?.corrupt ? "" : String(s?.updated ?? ""));
  return items.map((s, i) => [s, i]).sort(([a, i], [b, j]) => {
    if (!!a.corrupt !== !!b.corrupt) return a.corrupt ? 1 : -1;
    const byTime = key(b).localeCompare(key(a));
    if (byTime) return byTime;
    if (a.id === freshId) return -1;
    if (b.id === freshId) return 1;
    return i - j;
  }).map(([s]) => s);
}

// D-63：优先有 running 尝试的会话，否则 updated 最新的（列表已按 updated 降序）；坏文件排最后。
export function pickCurrent(sessions, preferredId = null) {
  const list = Array.isArray(sessions) ? sessions : [];
  if (preferredId && list.some((s) => s.id === preferredId)) return preferredId;
  const running = list.find((s) => !s.corrupt && s.running);
  if (running) return running.id;
  const healthy = list.find((s) => !s.corrupt);
  return (healthy ?? list[0])?.id ?? null;
}

// D-51/D-66：输入区读数。种子框为空则不传 seed，由后端取随机值。错误分两类：
// 提示词问题（主流程错误行）与高级参数问题（高级参数区内，文案带前缀）。
export class ParamsError extends Error {
  constructor(message, { advanced = false } = {}) { super(message); this.advanced = advanced; }
}

// 找当前正在生成的某一种媒体作业属于哪个会话（D-82、D-87）：作业快照优先，其次列表摘要的 running。
export function runningSessionId(job, sessions, kind) {
  if (job && job.kind === kind && job.status === "running" && job.session_id) return job.session_id;
  if (job && job.kind === kind && job.status === "running") return null;
  return (sessions ?? []).find((s) => !s.corrupt && s.running)?.id ?? null;
}

// §7.6：输入区状态提示与「生成图片」「换个构图」等动作的不可用原因，只取第一条。
// 返回 {reason, disabled, returnTo}；returnTo 是「回到该会话」要切去的会话 id。
export function availability(state, { noun }) {
  const s = state ?? {};
  const out = (reason, returnTo = null) => ({ reason, disabled: true, returnTo });
  if (s.pending) return out("正在提交…");
  if (s.listState !== "ready" || !s.currentId) return out("会话还没加载好");
  if (s.currentCorrupt) return out("请选择其他会话或新建一个");
  if (!s.current) return out("会话还没加载好");
  const runningId = runningSessionId(s.job, s.sessions, s.kind ?? "image");
  if (runningId && runningId === s.currentId) {
    const attempts = s.current.attempts ?? [];
    let index = attempts.findIndex((a) => s.job?.attempt_id && a.id === s.job.attempt_id);
    if (index < 0) index = attempts.findIndex((a) => a.status === "running");
    if (index < 0) index = attempts.length;
    return out(`正在生成这个会话里的第 ${index + 1} 次`);
  }
  if (runningId) {
    const other = (s.sessions ?? []).find((item) => item.id === runningId);
    return out(`「${sessionTitle(other)}」正在生成${noun}`, runningId);
  }
  if (!s.allowed) return out(s.busyReason || "服务状态暂不可用，请稍后重试");
  if (s.runtimeReason) return out(s.runtimeReason);
  if (s.modelReason) return out(s.modelReason);
  return { reason: "", disabled: false, returnTo: null };
}

// D-90：删除确认正文。
export function deleteMessage(summary, { noun }) {
  const base = `确定删除「${sessionTitle(summary)}」？只删除这个会话分组，其中的${noun}仍保留在素材库。`;
  return summary?.running ? `${base}这个会话正在生成${noun}，生成会继续完成，${noun}会进入素材库，但不会再出现在任何会话里。` : base;
}

// D-88：启动失败的错误行文案（session_not_found 由调用方另行处理）。
export function startErrorText(error) {
  return describeJobError({ code: error?.code, message: error?.message }).title || error?.message || "生成失败";
}

// 沿 continues 在同一会话的尝试里回溯到链首（M-31、M-41）；前段不在列表里时 gap=true。
export function chainOf(attempt, attempts) {
  const byId = new Map((attempts ?? []).map((a) => [a?.id, a]));
  const items = []; const seen = new Set(); let cursor = attempt; let gap = false;
  while (cursor) {
    if (seen.has(cursor.id)) { gap = true; break; }
    seen.add(cursor.id); items.push(cursor);
    if (!cursor.continues) break;
    cursor = byId.get(cursor.continues);
    if (!cursor) gap = true;
  }
  return { items: items.reverse(), gap };
}

// 尝试在本会话列表里的下标，不在时 -1（卡片标题、链说明里的「第 N 次」都由它算）。
export function positionOf(attempts, id) {
  return (attempts ?? []).findIndex((a) => a?.id === id);
}

// 挑选合成的序号徽标（M-06）：前 20 个用圈码 ①–⑳，之后写成「(21)」，不越界到别的字符。
export function pickBadge(index) {
  return index < 20 ? String.fromCharCode(0x2460 + index) : `(${index + 1})`;
}

// 音乐、视频卡片标题（M-30、V-31）：合成尝试标出各段序号（有一段找不到就只写「合成」），续写段标出前段序号。
export function sessionCardTitle(attempt, index, attempts, { composeWord = "合成" } = {}) {
  const base = attemptLabel(index, attempt);
  if (attempt?.op === "compose" || Array.isArray(attempt?.params?.parts)) {
    const nums = (attempt.params?.parts ?? []).map((id) => positionOf(attempts, id));
    return nums.length && nums.every((n) => n >= 0) ? `${base} · ${composeWord}：第 ${nums.map((n) => n + 1).join("、")} 次` : `${base} · ${composeWord}`;
  }
  if (attempt?.continues) {
    const n = positionOf(attempts, attempt.continues);
    if (n >= 0) return `${base} · 接第 ${n + 1} 次`;
  }
  return base;
}
