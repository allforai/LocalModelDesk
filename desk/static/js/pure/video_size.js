// desk/static/js/pure/video_size.js
// 视频画幅（视频画幅设计 Z-01–Z-41，重做 42f8062）：方向 × 档位或自定义、H3 画布规则、首帧形状跟随、提醒。
// 规则与 desk/media/service.py 的 VIDEO_* 常量、内存公式与 desk/media/memory_estimate.py 一致（tests/test_video_size_mirror.py 钉住）。
export const ORIENTATIONS = [
  { value: "landscape", label: "横屏" },
  { value: "portrait", label: "竖屏" },
  { value: "square", label: "方形" },
];
export const CUSTOM = "custom";
const LABEL = Object.fromEntries(ORIENTATIONS.map((o) => [o.value, o.label]));
const TIERS = ["草稿", "标准", "清晰"];
const LANDSCAPE = [[512, 288], [768, 448], [1024, 576]];
const SQUARE = [[384, 384], [576, 576], [768, 768]];

const MULTIPLE = 32;
const SIDE_MIN = 256;
const SIDE_MAX = 1344;
const MAX_PIXELS = 768 * 1344;

export function presetsFor(orientation) {
  const rows = orientation === "square" ? SQUARE
    : orientation === "portrait" ? LANDSCAPE.map(([w, h]) => [h, w]) : LANDSCAPE;
  return rows.map(([width, height], tier) => ({
    value: `${width}x${height}`, width, height, tier, label: `${TIERS[tier]} ${width}×${height}`,
  }));
}

// 档位值在它那个方向里是第几档（0–2）；不是档位返回 -1。三个方向的档位值互不相同。
export function tierOf(value) {
  for (const { value: orientation } of ORIENTATIONS) {
    const preset = presetsFor(orientation).find((p) => p.value === value);
    if (preset) return preset.tier;
  }
  return -1;
}

export function parseSize(value) {
  const match = /^(\d+)x(\d+)$/.exec(String(value ?? ""));
  return match ? { width: Number(match[1]), height: Number(match[2]) } : null;
}

export function snap32(value) {
  if (value === "" || value == null) return Number.NaN;
  const n = Number(value);
  return Number.isFinite(n) ? Math.round(n / MULTIPLE) * MULTIPLE : Number.NaN;
}

// Z-01/02：合法返回空串，否则返回第一条违规说明。
export function sizeError(width, height) {
  if (![width, height].every(Number.isInteger)) return "宽和高须为整数";
  if (width % MULTIPLE || height % MULTIPLE) return `宽和高须为 ${MULTIPLE} 的倍数`;
  if ([width, height].some((n) => n < SIDE_MIN || n > SIDE_MAX)) return `每边须在 ${SIDE_MIN}–${SIDE_MAX} 之间`;
  if (width * height > MAX_PIXELS) return "面积不能超过 768×1344（约 103 万像素）";
  return "";
}

// Z-20：宽高比 0.9–1.1 算方形。
export function shapeOf(width, height) {
  const ratio = width / height;
  if (ratio >= 0.9 && ratio <= 1.1) return "square";
  return width > height ? "landscape" : "portrait";
}

// Z-31：按尺寸找回方向与档位；不在任何档位里就是自定义（方向按形状）。
export function matchSize(width, height) {
  for (const { value: orientation } of ORIENTATIONS) {
    const preset = presetsFor(orientation).find((p) => p.width === width && p.height === height);
    if (preset) return { orientation, size: preset.value };
  }
  return { orientation: shapeOf(width, height), size: CUSTOM };
}

// Z-21/22/24：current = {orientation, custom}；frame = 首帧尺寸或 null（读不到）。
// 返回要切到的方向（不切为 null）与提示文案。
export function frameFollow(current, frame) {
  if (!frame || !(frame.width > 0) || !(frame.height > 0)) return { orientation: null, note: "" };
  const shape = shapeOf(frame.width, frame.height);
  if (shape === current.orientation) return { orientation: null, note: "" };
  if (current.custom) {
    return { orientation: null, note: `首帧是${LABEL[shape]}，画幅是${LABEL[current.orientation]}，画面会被拉伸变形` };
  }
  return { orientation: shape, note: `已按首帧切到${LABEL[shape]}` };
}

// Z-41：与 desk/media/memory_estimate.py 的视频公式同源——27 GiB 固定开销 + 每多一个草稿体积（512×288×49 帧）1.4 GiB。
// 只有两个实测点，更大的组合是外推。
const DRAFT_VOLUME = 512 * 288 * 49;
const FIXED_GIB = 27.0;
const PER_VOLUME_GIB = 1.4;
export const H3_BUDGET_GIB = 40;

export function estimateGiB(width, height, frames) {
  const volume = (width * height * Number(frames)) / DRAFT_VOLUME;
  return FIXED_GIB + PER_VOLUME_GIB * Math.max(volume - 1, 0);
}

// Z-40：「很慢」只对有实测依据的面积——cross-exam 2026-09-13 q16，1024×576 × 15 秒在 128 GB 机器上 20 分钟只走完 2/16 步。
const SLOW_PIXELS = 1024 * 576;
const SLOW_FRAMES = 243; // 「约 10 秒」档

export function videoCostNote(width, height, frames) {
  const notes = [];
  if (width * height >= SLOW_PIXELS && Number(frames) >= SLOW_FRAMES) {
    notes.push("大画幅加 10 秒以上会非常慢：实测 1024×576 曾 20 分钟只走完 2/16 步，可能要一小时以上。建议先用草稿画幅试效果。");
  }
  const need = estimateGiB(width, height, frames);
  if (need > H3_BUDGET_GIB) notes.push(`按实测外推约需 ${Math.ceil(need)} GiB，超过视频生成的 ${H3_BUDGET_GIB} GiB 上限，可能中途失败。`);
  return notes.join("");
}
