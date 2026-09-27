// 音乐会话的纯逻辑（设计 docs/superpowers/specs/2026-09-27-music-sessions-design.md）。零 DOM、零 fetch。
import { ParamsError, SEED_MAX, chainOf, positionOf, randomSeed } from "./media_session.js";

export const DEFAULT_DURATION = 60;
export const CANNOT_CONTINUE = "这一段没有生成好，不能接着写";
const REJOINABLE = new Set(["join_failed", "join_cancelled", "interrupted"]);

export function readMusicParams(values) {
  const caption = String(values?.caption ?? "");
  const lyrics = String(values?.lyrics ?? "");
  if (!caption.trim()) throw new ParamsError("请填写风格描述");
  if (!lyrics.trim()) throw new ParamsError("请填写歌词：Music 3 需要歌词才能生成");
  const advanced = (reason) => new ParamsError(`高级参数里的数值有误：${reason}`, { advanced: true });
  const duration = Number(String(values?.duration ?? "").trim());
  if (!Number.isInteger(duration) || duration < 10 || duration > 300) throw advanced("时长须为 10–300 的整数");
  const params = { caption, lyrics, duration };
  const seedRaw = String(values?.seed ?? "").trim();
  if (seedRaw) {
    const seed = Number(seedRaw);
    if (!Number.isInteger(seed) || seed < 0 || seed > SEED_MAX) throw advanced("种子须为 0–4294967295 的整数");
    params.seed = seed;
  }
  return params;
}

export function refineFields(attempt) {
  const p = attempt?.params ?? {};
  return { caption: typeof p.caption === "string" ? p.caption : "", lyrics: typeof p.lyrics === "string" ? p.lyrics : "",
    duration: Number.isFinite(p.duration) ? p.duration : DEFAULT_DURATION, seed: Number.isInteger(p.seed) ? p.seed : null };
}

export function nextFields(attempt, current) {
  if (attempt?.op === "compose" || Array.isArray(attempt?.params?.parts)) return { caption: current.caption, duration: current.duration };
  const f = refineFields(attempt);
  return { caption: f.caption, duration: f.duration };
}

export function canContinue(attempt) {
  return attempt?.status === "done" && typeof attempt.output === "string" && !!attempt.output && !attempt.output_missing;
}

export function versionParams(attempt, sessionId, draw = randomSeed) {
  const f = refineFields(attempt);
  let seed = draw();
  while (seed === f.seed) seed = draw();
  const params = { session_id: sessionId, caption: f.caption, lyrics: f.lyrics, duration: f.duration, seed };
  if (attempt?.continues) params.continues = attempt.continues;
  return params;
}

const ordinal = (index) => (Number.isInteger(index) ? `第 ${index + 1} 次` : "");

export function chipText(ref) {
  if (!ref) return "";
  if (ref.type === "continue") return ref.missing ? `${ordinal(ref.index)}的文件已不在，不能接着写` : `接在${ordinal(ref.index)}后面`;
  return Number.isInteger(ref.index) ? `沿用${ordinal(ref.index)}` : "沿用素材库里这首";
}

// 提示条可见时才续写（M-27）：续写提示条总是可见；沿用提示条要求种子框仍等于被引用的种子（IS D-42）。
export function submitContinues(ref, seedInput) {
  if (!ref) return null;
  if (ref.type === "continue") return ref.missing ? null : ref.attemptId;
  if (!Number.isInteger(ref.seed) || String(seedInput ?? "").trim() !== String(ref.seed)) return null;
  return ref.continues ?? null;
}

export function lyricsPreview(lyrics) {
  return String(lyrics ?? "").split("\n").map((line) => line.trim()).find((line) => line && !/^\[[^\]]*\]$/.test(line)) ?? "";
}

export function chainLine(attempt, attempts) {
  const { items, gap } = chainOf(attempt, attempts);
  if (items.length < 2 && !gap) return "";
  return `由：${gap ? "… → " : ""}${items.map((a) => `第 ${positionOf(attempts, a.id) + 1} 次`).join(" → ")}`;
}

// 成片问题行（M-40、M-41）：没拼成（joined_error），或拼好的成片文件已被删（joined_missing）。
// 可重新拼接时 rejoin.parts 是整条链；链上缺段时按钮禁用、原因「链上有一段已不在」。视频卡片共用。
export function joinProblem(attempt, attempts) {
  if (attempt?.status !== "done") return null;
  const error = attempt.joined_error;
  let text;
  if (error) {
    text = `这一段生成好了，但成片没拼成：${error.message ?? ""}`;
    if (!REJOINABLE.has(error.code)) return { text, rejoin: null, reason: "" };
  } else if (attempt.joined_output && attempt.joined_missing) {
    text = "这一段生成好了，但成片文件已不在";
  } else return null;
  const { items, gap } = chainOf(attempt, attempts);
  if (gap || !items.every(canContinue)) return { text, rejoin: null, reason: "链上有一段已不在" };
  return { text, rejoin: { parts: items.map((a) => a.id) }, reason: "" };
}
