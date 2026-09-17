// data:budgetSnapshot 的 source 字段 → 中文标签。
/** 来源标签：估算和实测必须一眼分得开，否则预测错了没人看得出来。 */
const LABELS = { measured: "已实测", predicted: "估算", unavailable: "算不出" };

export function budgetLabel(source) {
  return LABELS[source] ?? "未知";
}
