// 素材库条目模型（素材库预览设计 L-01–L-06）：合并成品与历史、筛选、排序、偏好归一。纯函数，无 DOM。
import { fillPlan } from "./history_fill.js";

export const FILTERS = ["all", "image", "video", "music"];
export const VIEWS = ["grid", "list", "table"];
export const SORT_KEYS = ["ts", "title", "kind", "duration", "dims", "bytes", "gen"];
export const THUMB_MIN = 140;
export const THUMB_MAX = 320;
export const DEFAULT_PREFS = Object.freeze({
  view: "grid", filter: "all", thumb: 200, sort: Object.freeze({ key: "ts", dir: "desc" }),
});

// L-11：读到什么都归一成合法偏好；大小夹在 140–320。
export function normalizePrefs(raw) {
  const p = raw && typeof raw === "object" ? raw : {};
  const sort = p.sort && typeof p.sort === "object" ? p.sort : {};
  const thumb = typeof p.thumb === "number" ? p.thumb : Number.NaN;
  return {
    view: VIEWS.includes(p.view) ? p.view : DEFAULT_PREFS.view,
    filter: FILTERS.includes(p.filter) ? p.filter : DEFAULT_PREFS.filter,
    thumb: Number.isFinite(thumb) ? Math.min(THUMB_MAX, Math.max(THUMB_MIN, Math.round(thumb))) : DEFAULT_PREFS.thumb,
    sort: {
      key: SORT_KEYS.includes(sort.key) ? sort.key : DEFAULT_PREFS.sort.key,
      dir: sort.dir === "asc" || sort.dir === "desc" ? sort.dir : DEFAULT_PREFS.sort.dir,
    },
  };
}

// 一行规格（沿用原素材库的写法）：图片「宽×高 · 步数 · 种子」，视频「宽×高 · 约 N 秒 · 步数」，歌曲按成品实际时长并注明请求值。
export function specText(entry) {
  const params = entry.params ?? {};
  const parts = entry.kind === "image"
    ? [params.width && params.height ? `${params.width}×${params.height}` : null,
      params.steps ? `${params.steps}步` : null, params.seed != null ? `种子 ${params.seed}` : null]
    : entry.kind === "video"
    ? [params.width && params.height ? `${params.width}×${params.height}` : null,
      params.frames ? `约 ${Math.round(params.frames / 24)} 秒` : null, params.steps ? `${params.steps}步` : null]
    : [Number.isFinite(entry.audio_seconds)
      ? `成品 ${Math.round(entry.audio_seconds)} 秒${params.duration ? `（请求 ${params.duration} 秒）` : ""}`
      : params.duration ? `${params.duration}s` : null];
  return parts.filter(Boolean).join(" · ");
}

export function clockText(seconds) {
  const total = Math.max(0, Math.round(Number(seconds) || 0));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

// 有能播/能看的文件：有文件名且不是 missing（失败、取消、文件已不在的条目都没有）。
export const hasMedia = (item) => !!item.output && !item.missing;

// L-04：音乐取成品实际时长，否则请求时长；视频按 24 帧/秒；图片没有。
function mediaSeconds(entry) {
  const params = entry.params ?? {};
  if (entry.kind === "music") {
    if (Number.isFinite(entry.audio_seconds)) return entry.audio_seconds;
    const requested = Number(params.duration);
    return params.duration != null && params.duration !== "" && Number.isFinite(requested) ? requested : null;
  }
  if (entry.kind === "video" && Number(params.frames) > 0) return Number(params.frames) / 24;
  return null;
}

function fromEntry(entry, output) {
  const params = entry.params ?? {};
  const prompt = String(params.prompt ?? params.caption ?? "");
  const sized = entry.kind === "image" || entry.kind === "video";
  const missing = !output && entry.status === "done" && !!entry.output;
  return {
    key: output ? `o:${output.name}` : `h:${entry.ts ?? ""}:${entry.kind}:${entry.attempt_id ?? ""}`,
    kind: entry.kind,
    status: entry.status,
    ts: entry.ts ?? output?.ts ?? "",
    title: prompt || "（无提示词）",
    prompt,
    spec: specText(entry),
    duration_s: mediaSeconds(entry),
    width: sized ? Number(params.width) || null : null,
    height: sized ? Number(params.height) || null : null,
    bytes: output?.bytes ?? null,
    gen_s: Number.isFinite(entry.duration_s) ? entry.duration_s : null,
    output: output?.name ?? (missing ? entry.output : null),
    missing,
    entry,
    error: entry.error ?? null,
    plan: fillPlan(entry),
  };
}

function fromOutput(output) {
  return {
    key: `o:${output.name}`, kind: output.kind ?? "file", status: "done", ts: output.ts ?? "",
    title: output.name, prompt: "", spec: "", duration_s: null, width: null, height: null,
    bytes: output.bytes ?? null, gen_s: null, output: output.name, missing: false, entry: null, error: null, plan: null,
  };
}

// L-01：历史按文件名配成品；一条历史的 output 与 joined_output 各占一条（B-43）；没配上的历史、没配上的成品各占一条。
export function buildItems(outputs = [], history = []) {
  const byName = new Map(outputs.map((output) => [output.name, output]));
  const matched = new Set();
  const items = [];
  for (const entry of history) {
    let hit = false;
    for (const name of [entry.output, entry.joined_output].filter(Boolean)) {
      const output = byName.get(name);
      if (!output) continue;
      matched.add(name);
      hit = true;
      items.push(fromEntry(entry, output));
    }
    if (!hit) items.push(fromEntry(entry, null));
  }
  for (const output of outputs) if (!matched.has(output.name)) items.push(fromOutput(output));
  const seen = new Map();
  for (const item of items) {
    const count = (seen.get(item.key) ?? 0) + 1;
    seen.set(item.key, count);
    if (count > 1) item.key = `${item.key}#${count}`;
  }
  return sortItems(items, DEFAULT_PREFS.sort);
}

export function filterItems(items, filter) {
  return filter === "all" ? [...items] : items.filter((item) => item.kind === filter);
}

const SORT_VALUE = {
  ts: (item) => item.ts || null,
  title: (item) => item.title || null,
  kind: (item) => item.kind || null,
  duration: (item) => item.duration_s ?? null,
  dims: (item) => (item.width && item.height ? item.width * item.height : null),
  bytes: (item) => item.bytes ?? null,
  gen: (item) => item.gen_s ?? null,
};
const plain = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

// L-06：缺值不论方向都排最后；提示词按中文排；同值按时间倒序。
export function sortItems(items, { key = "ts", dir = "desc" } = {}) {
  const value = SORT_VALUE[key] ?? SORT_VALUE.ts;
  const sign = dir === "asc" ? 1 : -1;
  const compare = key === "title" ? (a, b) => a.localeCompare(b, "zh") : plain;
  return [...items].sort((x, y) => {
    const a = value(x);
    const b = value(y);
    if (a == null && b != null) return 1;
    if (b == null && a != null) return -1;
    if (a != null && b != null) {
      const diff = compare(a, b);
      if (diff) return sign * diff;
    }
    return plain(String(y.ts ?? ""), String(x.ts ?? ""));
  });
}

export function visibleItems(items, prefs) {
  return sortItems(filterItems(items, prefs.filter), prefs.sort);
}
