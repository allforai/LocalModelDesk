// 图片会话的纯逻辑（设计 docs/superpowers/specs/2026-09-24-image-sessions-design.md）。
// 零 DOM、零 fetch：卡片文案、动作参数、当前会话选择、不可用原因都在这里算好，
// panes/image.js 只负责把结果画出来。
import { describeJobError } from "./job_error.js";
import { formatDuration } from "./format.js";

export const SEED_MAX = 4294967295;
export const DEFAULT_PARAMS = Object.freeze({ width: 1024, height: 1024, steps: 40 });

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

// D-81：running 卡片的标题行，沿用 jobview 的 formatDuration 文案。
export function runningLabel(index, elapsedSeconds) {
  const elapsed = Number.isFinite(elapsedSeconds) ? `（已用 ${formatDuration(elapsedSeconds)}）` : "";
  return `第 ${index + 1} 次 · 生成中…${elapsed}`;
}

export function specLine(params) {
  const p = params ?? {};
  const size = Number.isInteger(p.width) && Number.isInteger(p.height) ? `${p.width}×${p.height}` : "";
  const steps = Number.isInteger(p.steps) ? `${p.steps} 步` : "";
  return [size, steps].filter(Boolean).join(" · ");
}

// 卡片状态 → {kind, badge, title, sub, icon, tone}（D-73、D-84、D-85）。
// kind ∈ running | done | failed | cancelled | missing；missing 是 done 但图片文件不在
// （后端 output_missing，或前端 <img> 触发 error 后由调用方传 broken=true）。
export function attemptView(attempt, { broken = false } = {}) {
  const status = attempt?.status;
  if (status === "running") return { kind: "running", badge: "生成中", title: "", sub: "", icon: null, tone: "busy" };
  if (status === "done" && !attempt.output_missing && !broken && attempt.output)
    return { kind: "done", badge: "", title: "", sub: "", icon: null, tone: "" };
  if (status === "done")
    return { kind: "missing", badge: "图片文件已不在", title: "图片文件已不在", sub: "可能已在访达中移动或删除", icon: "image", tone: "muted" };
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

// D-40：「在这张基础上改」回填到输入区的五个值。
export function refineFields(attempt) {
  const p = attempt?.params ?? {};
  return {
    prompt: typeof p.prompt === "string" ? p.prompt : "",
    width: Number.isInteger(p.width) ? p.width : DEFAULT_PARAMS.width,
    height: Number.isInteger(p.height) ? p.height : DEFAULT_PARAMS.height,
    steps: Number.isInteger(p.steps) ? p.steps : DEFAULT_PARAMS.steps,
    seed: Number.isInteger(p.seed) ? p.seed : null,
  };
}

// 32 位无符号随机整数（0–4294967295），来自 crypto.getRandomValues。
export function randomSeed(cryptoImpl = globalThis.crypto) {
  const buffer = new Uint32Array(1);
  cryptoImpl.getRandomValues(buffer);
  return buffer[0];
}

// D-46：「换个构图」——提示词、宽高、步数取该尝试，种子换一个与原值不同的新随机数。
export function recomposeParams(attempt, sessionId, draw = randomSeed) {
  const fields = refineFields(attempt);
  let seed = draw();
  while (seed === fields.seed) seed = draw();
  return { session_id: sessionId, prompt: fields.prompt, width: fields.width, height: fields.height, steps: fields.steps, seed };
}

// D-41/D-42：提示条只在种子框的值等于被引用尝试的种子时显示。
export function refineChipVisible(seedInputValue, ref) {
  if (!ref || !Number.isInteger(ref.seed)) return false;
  return String(seedInputValue ?? "").trim() === String(ref.seed);
}

export function refineChipText(ref) {
  return Number.isInteger(ref?.index) ? `沿用第 ${ref.index + 1} 次的构图` : "沿用素材库里这张的构图";
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

export function readImageParams(values) {
  const prompt = String(values?.prompt ?? "");
  if (!prompt.trim()) throw new ParamsError("请填写图片提示词");
  const advanced = (reason) => new ParamsError(`高级参数里的数值有误：${reason}`, { advanced: true });
  const params = { prompt };
  for (const name of ["width", "height", "steps"]) {
    const raw = String(values?.[name] ?? "").trim();
    if (!raw || !Number.isInteger(Number(raw))) throw advanced("宽度、高度和步数须为整数");
    params[name] = Number(raw);
  }
  if ([params.width, params.height].some((n) => n < 256 || n > 2048 || n % 16))
    throw advanced("宽高须为 256–2048 范围内的 16 的倍数");
  if (params.steps < 1 || params.steps > 100) throw advanced("步数须为 1–100 的整数");
  const seedRaw = String(values?.seed ?? "").trim();
  if (seedRaw) {
    const seed = Number(seedRaw);
    if (!Number.isInteger(seed) || seed < 0 || seed > SEED_MAX) throw advanced("种子须为 0–4294967295 的整数");
    params.seed = seed;
  }
  return params;
}

// 找当前正在生成的图片作业属于哪个会话（D-82、D-87）：作业快照优先，其次列表摘要的 running。
export function runningSessionId(job, sessions) {
  if (job && job.kind === "image" && job.status === "running" && job.session_id) return job.session_id;
  if (job && job.kind === "image" && job.status === "running") return null;
  return (sessions ?? []).find((s) => !s.corrupt && s.running)?.id ?? null;
}

// §7.6：输入区状态提示与「生成图片」「换个构图」的不可用原因，只取第一条。
// 返回 {reason, disabled, returnTo}；returnTo 是「回到该会话」要切去的会话 id。
export function availability(state) {
  const s = state ?? {};
  const out = (reason, returnTo = null) => ({ reason, disabled: true, returnTo });
  if (s.pending) return out("正在提交…");
  if (s.listState !== "ready" || !s.currentId) return out("会话还没加载好");
  if (s.currentCorrupt) return out("请选择其他会话或新建一个");
  if (!s.current) return out("会话还没加载好");
  const runningId = runningSessionId(s.job, s.sessions);
  if (runningId && runningId === s.currentId) {
    const attempts = s.current.attempts ?? [];
    let index = attempts.findIndex((a) => s.job?.attempt_id && a.id === s.job.attempt_id);
    if (index < 0) index = attempts.findIndex((a) => a.status === "running");
    if (index < 0) index = attempts.length;
    return out(`正在生成这个会话里的第 ${index + 1} 次`);
  }
  if (runningId) {
    const other = (s.sessions ?? []).find((item) => item.id === runningId);
    return out(`「${sessionTitle(other)}」正在生成图片`, runningId);
  }
  if (!s.allowed) return out(s.busyReason || "服务状态暂不可用，请稍后重试");
  if (s.runtimeReason) return out(s.runtimeReason);
  if (s.modelReason) return out(s.modelReason);
  return { reason: "", disabled: false, returnTo: null };
}

// D-90：删除确认正文。
export function deleteMessage(summary) {
  const base = `确定删除「${sessionTitle(summary)}」？只删除这个会话分组，其中的图片仍保留在素材库。`;
  return summary?.running ? `${base}这个会话正在生成图片，生成会继续完成，图片会进入素材库，但不会再出现在任何会话里。` : base;
}

// D-88：启动失败的错误行文案（session_not_found 由调用方另行处理）。
export function startErrorText(error) {
  return describeJobError({ code: error?.code, message: error?.message }).title || error?.message || "生成失败";
}
