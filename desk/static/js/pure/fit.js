// data:fitVerdict（后端 desk.budget.budget.assess_fit 的四态）→ 台面文案（R-ui-fit）。
// resources 页的常驻标记、首运报告读的是同一份判定，不各自拼一套说法。
import { formatBytes } from "./format.js";

const LEVEL_LABEL = { fits: "能跑", tight: "偏紧", too_big: "装不下", unknown: "算不出" };
// 复用 resources 面板已有的四种徽标底色：绿/黄是好坏，红留给「装不下」这种要
// 拦住用户的情况，灰留给「不知道」——不知道不该看起来像出了错。
const LEVEL_BADGE_KIND = { fits: "ok", tight: "busy", too_big: "unknown", unknown: "none" };

export function fitBadge(fit) {
  const level = fit?.level ?? "unknown";
  return { label: LEVEL_LABEL[level] ?? LEVEL_LABEL.unknown, badgeKind: LEVEL_BADGE_KIND[level] ?? LEVEL_BADGE_KIND.unknown };
}

// 算不出机器能力时只说「不知道」，绝不拼一个数字出来（哪怕是「需要多少」这半句
// 是知道的）——半真半猜比干脆说不知道更危险。
export function fitDetail(fit) {
  if (!fit || fit.level === "unknown") return "这台机器的重活能力还没能测出来";
  const needed = formatBytes(fit.needed_bytes);
  const available = formatBytes(fit.available_bytes);
  if (fit.level === "too_big") return `需要 ${needed}，这台机器能给 ${available}，差 ${formatBytes(fit.shortfall_bytes)}`;
  return `需要 ${needed}，这台机器能给 ${available}，剩 ${formatBytes(fit.headroom_bytes)}`;
}

// 首运报告：机器能力算不出来时，整份报告不推荐任何模型——一个模型都不点名，
// 因为「能力」是整机一个数，算不出就是全体都算不出，不是有的能判有的不能。
export function fitReportView(catalog) {
  const entries = catalog ?? [];
  const capacityKnown = entries.length > 0 && entries.every((e) => (e.fit?.level ?? "unknown") !== "unknown");
  if (!capacityKnown) return { capacityKnown: false, fits: [], tight: [], tooBig: [] };
  const by = (level) => entries.filter((e) => e.fit.level === level);
  return { capacityKnown: true, fits: by("fits"), tight: by("tight"), tooBig: by("too_big") };
}
