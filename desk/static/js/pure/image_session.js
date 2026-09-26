// 图片会话的纯逻辑（设计 docs/superpowers/specs/2026-09-24-image-sessions-design.md）。
// 零 DOM、零 fetch：卡片文案、动作参数、当前会话选择、不可用原因都在这里算好，
// panes/image.js 只负责把结果画出来。attemptView 是图片、音乐等媒体共用的卡片状态函数，
// 已搬到 pure/media_session.js。
import { ParamsError, SEED_MAX, randomSeed } from "./media_session.js";

export const DEFAULT_PARAMS = Object.freeze({ width: 1024, height: 1024, steps: 40 });

export function specLine(params) {
  const p = params ?? {};
  const size = Number.isInteger(p.width) && Number.isInteger(p.height) ? `${p.width}×${p.height}` : "";
  const steps = Number.isInteger(p.steps) ? `${p.steps} 步` : "";
  return [size, steps].filter(Boolean).join(" · ");
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

// 以图生图的两档强度（2026-09-24 可行性测试）：mflux 里强度越高越接近底稿。
// 0.6 保留构图、重画细节；0.35 保留主体与色调、换构图。只允许这两个值，后端同样校验。
export const REFINE_STRENGTH = 0.6;
export const RECOMPOSE_STRENGTH = 0.35;
export const NO_IMAGE_REASON = "这一次没有图片，不能以它为底稿换个构图";

// 这一次能不能当底稿：生成完成、有文件名、文件还在。
export function hasImage(attempt) {
  return attempt?.status === "done" && typeof attempt.output === "string" && !!attempt.output && !attempt.output_missing;
}

// D-46：「换个构图」——提示词、宽高、步数取该尝试，种子换一个与原值不同的新随机数；
// 有图时以这张为底稿重绘（强度 0.35）。
export function recomposeParams(attempt, sessionId, draw = randomSeed) {
  const fields = refineFields(attempt);
  let seed = draw();
  while (seed === fields.seed) seed = draw();
  const params = { session_id: sessionId, prompt: fields.prompt, width: fields.width, height: fields.height, steps: fields.steps, seed };
  if (hasImage(attempt)) params.base = { attempt_id: attempt.id, strength: RECOMPOSE_STRENGTH };
  return params;
}

// 「在这张基础上改」之后按「生成图片」：提示条还在（种子框没被改）且那一次有图，就以它为底稿（强度 0.6）。
export function submitBase(seedInputValue, ref) {
  if (!ref?.attemptId || !ref.image || !refineChipVisible(seedInputValue, ref)) return null;
  return { attempt_id: ref.attemptId, strength: REFINE_STRENGTH };
}

// 卡片上的「基于第 N 次」：底稿还在这个会话的列表里才标。
export function baseLabel(attempt, attempts) {
  const id = attempt?.base?.attempt_id;
  if (!id || !Array.isArray(attempts)) return "";
  const index = attempts.findIndex((a) => a?.id === id);
  return index < 0 ? "" : `基于第 ${index + 1} 次`;
}

// D-41/D-42：提示条只在种子框的值等于被引用尝试的种子时显示。
export function refineChipVisible(seedInputValue, ref) {
  if (!ref || !Number.isInteger(ref.seed)) return false;
  return String(seedInputValue ?? "").trim() === String(ref.seed);
}

export function refineChipText(ref) {
  if (Number.isInteger(ref?.index) && ref.attemptId && ref.image) return `以第 ${ref.index + 1} 次为底稿`;
  return Number.isInteger(ref?.index) ? `沿用第 ${ref.index + 1} 次的构图` : "沿用素材库里这张的构图";
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
