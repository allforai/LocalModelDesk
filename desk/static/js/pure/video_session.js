// 视频会话的纯逻辑（设计 docs/superpowers/specs/2026-09-27-video-sessions-design.md，第 3a 块）。零 DOM、零 fetch。
import { ParamsError, SEED_MAX, attemptLabel, positionOf, randomSeed, sessionCardTitle } from "./media_session.js";

export const SIZES = [["512x288", "草稿 512×288"], ["768x448", "标准 768×448"], ["1024x576", "清晰 1024×576"]];
export const DURATIONS = [[49, "约 2 秒（快速）"], [73, "约 3 秒"], [124, "约 5 秒（常用）"], [192, "约 8 秒"], [243, "约 10 秒"], [362, "约 15 秒（最长）"]];
export const MODES = { text: "文生", image: "图生", reference: "参考", music_ref: "配乐参考" };
export const CANNOT_CONTINUE = "这一段没有生成好，不能接着往下生";

const DEFAULT_SIZE = SIZES[0][0];
const DEFAULT_FRAMES = 124;
const DEFAULT_STEPS = 16;

export function readVideoParams(values) {
  const prompt = String(values?.prompt ?? "");
  if (!prompt.trim()) throw new ParamsError("请填写视频提示词");
  const advanced = (reason) => new ParamsError(`高级参数里的数值有误：${reason}`, { advanced: true });
  const size = String(values?.size ?? "");
  if (!SIZES.some(([v]) => v === size)) throw advanced("画幅无效");
  const [width, height] = size.split("x").map(Number);
  const frames = Number(String(values?.frames ?? "").trim());
  if (!DURATIONS.some(([v]) => v === frames)) throw advanced("视频时长无效");
  const steps = Number(String(values?.steps ?? "").trim());
  if (!Number.isInteger(steps) || steps < 4 || steps > 50) throw advanced("步数须为 4–50 的整数");
  const params = { prompt, width, height, frames, steps };
  const seedRaw = String(values?.seed ?? "").trim();
  if (seedRaw) {
    const seed = Number(seedRaw);
    if (!Number.isInteger(seed) || seed < 0 || seed > SEED_MAX) throw advanced("种子须为 0–4294967295 的整数");
    params.seed = seed;
  }
  return params;
}

// 去掉标签括号说明（如「（常用）」），取 DURATIONS 中与 frames 最接近的一档。
export function durationLabel(frames) {
  const target = Number(frames);
  const [, label] = DURATIONS.reduce((best, item) => (Math.abs(item[0] - target) < Math.abs(best[0] - target) ? item : best));
  return label.replace(/（[^）]*）$/, "");
}

export function specLine(params) {
  return `${params.width}×${params.height} · ${durationLabel(params.frames)} · ${params.steps} 步`;
}

// 图生首帧来源（V-22）：续写关系优先于图片会话引用，引用优先于本地上传素材；文生/参考模式无首帧来源。
export function sourceOf(attempt) {
  const p = attempt?.params ?? {};
  if (p.mode !== "image") return null;
  if (attempt?.continues) return { type: "continue", attemptId: attempt.continues };
  const ref = attempt?.refs?.first_frame;
  if (ref) return { type: "ref", ref };
  if (typeof p.first_frame === "string" && p.first_frame) return { type: "upload", id: p.first_frame };
  return null;
}

// 配乐参考的参考图来源（S-34）：图片会话引用优先于本地上传素材；其他方式没有参考图。
export function refImageOf(attempt) {
  const p = attempt?.params ?? {};
  if (p.mode !== "music_ref") return null;
  const ref = attempt?.refs?.ref_image;
  if (ref) return { type: "ref", ref };
  if (typeof p.ref_image === "string" && p.ref_image) return { type: "upload", id: p.ref_image };
  return null;
}

// 「在这段基础上改」回填用（V-40）：只读这段自己记录的参数，不涉及 continues/refs 的解读（由 sourceOf 负责）。
export function refineFields(attempt) {
  const p = attempt?.params ?? {};
  const [defaultWidth, defaultHeight] = DEFAULT_SIZE.split("x").map(Number);
  const width = Number.isFinite(p.width) ? p.width : defaultWidth;
  const height = Number.isFinite(p.height) ? p.height : defaultHeight;
  return {
    mode: typeof p.mode === "string" ? p.mode : "text",
    prompt: typeof p.prompt === "string" ? p.prompt : "",
    size: `${width}x${height}`,
    frames: Number.isFinite(p.frames) ? p.frames : DEFAULT_FRAMES,
    steps: Number.isFinite(p.steps) ? p.steps : DEFAULT_STEPS,
    seed: Number.isInteger(p.seed) ? p.seed : null,
    first: typeof p.first_frame === "string" && p.first_frame ? p.first_frame : null,
    last: typeof p.last_frame === "string" && p.last_frame ? p.last_frame : null,
    refVideo: typeof p.ref_video === "string" && p.ref_video ? p.ref_video : null,
    useAudio: typeof p.use_audio === "boolean" ? p.use_audio : true,
    audioStart: Number.isFinite(p.audio_start) && p.audio_start >= 0 ? p.audio_start : 0,
  };
}

// 「换个版本」请求体（V-41）：续写段只带续写关系本身（首帧由后端从原链推导，B-56），
// 否则带原方式（非 text 时）、声音开关与素材 id / 图片会话引用。
export function versionParams(attempt, sessionId, draw = randomSeed) {
  const p = attempt?.params ?? {};
  let seed = draw();
  while (seed === p.seed) seed = draw();
  const base = { session_id: sessionId, prompt: p.prompt, width: p.width, height: p.height, frames: p.frames, steps: p.steps, seed };
  if (attempt?.continues) {
    const continued = { ...base, continues: attempt.continues };
    if (typeof p.use_audio === "boolean") continued.use_audio = p.use_audio;
    return continued;
  }
  const params = { ...base };
  if (typeof p.mode === "string" && p.mode !== "text") params.mode = p.mode;
  if (typeof p.use_audio === "boolean" && p.mode !== "music_ref") params.use_audio = p.use_audio; // 配乐参考没有素材声音
  for (const key of ["first_frame", "last_frame", "ref_video", "ref_image"]) {
    if (typeof p[key] === "string" && p[key]) params[key] = p[key];
  }
  if (p.mode === "music_ref" && Number.isFinite(p.audio_start)) params.audio_start = p.audio_start;
  if (attempt?.refs && Object.keys(attempt.refs).length) params.refs = attempt.refs;
  return params;
}

// 「接着往下生」沿用画幅/时长/步数（V-42）；合成、配乐尝试没有这些参数，保留输入区当前值。
export function nextFields(attempt, current) {
  if (attempt?.op === "compose" || attempt?.op === "soundtrack" || Array.isArray(attempt?.params?.parts)) return current;
  const p = attempt?.params ?? {};
  const size = Number.isFinite(p.width) && Number.isFinite(p.height) ? `${p.width}x${p.height}` : current.size;
  return {
    size,
    frames: Number.isFinite(p.frames) ? p.frames : current.frames,
    steps: Number.isFinite(p.steps) ? p.steps : current.steps,
  };
}

// 仅 done 且文件在场可以接着往下生（V-42）。
export function canContinue(attempt) {
  return attempt?.status === "done" && typeof attempt.output === "string" && !!attempt.output && !attempt.output_missing;
}

const ordinal = (index) => (Number.isInteger(index) ? `第 ${index + 1} 次` : "");

export function chipText(ref) {
  if (!ref) return "";
  if (ref.type === "continue") return ref.missing ? `${ordinal(ref.index)}的文件已不在，不能接着往下生` : `接在${ordinal(ref.index)}后面`;
  if (ref.type === "library") return "沿用素材库里这段";
  return `沿用${ordinal(ref.index)}`;
}

export function firstFrameLabel(source, { fileName, imageTitle, imageIndex, continueIndex } = {}) {
  const type = source?.type;
  if (type === "upload") return `已选择：${fileName ?? ""}`;
  if (type === "ref") {
    const title = typeof imageTitle === "string" ? imageTitle.trim() : "";
    return title && Number.isInteger(imageIndex) ? `首帧：图片会话「${title}」第 ${imageIndex + 1} 次` : "首帧：来自图片会话";
  }
  if (type === "continue") return `接在第 ${continueIndex + 1} 次后面（用它的最后一帧）`;
  return "未选择";
}

// 卡片标题：配乐尝试走 soundtrackTitle（songLabel 是歌的风格描述摘要，可为空），其余同音乐规则（sessionCardTitle）。
export function cardTitle(attempt, index, attempts, songLabel = "") {
  if (attempt?.op === "soundtrack") return soundtrackTitle(attempt, index, attempts, songLabel);
  return sessionCardTitle(attempt, index, attempts);
}

// 配乐卡片标题（S-31）：「第 N 次 · HH:MM · 配乐：<风格描述摘要> · 基于第 M 次」；
// label（风格描述摘要）取不到只写「配乐」，原视频不在本会话里就省略「基于」一段。
export function soundtrackTitle(attempt, index, attempts, label) {
  const source = positionOf(attempts, attempt?.params?.source);
  const parts = [attemptLabel(index, attempt), label ? `配乐：${label}` : "配乐"];
  if (source >= 0) parts.push(`基于第 ${source + 1} 次`);
  return parts.join(" · ");
}
