// 设置页「本机 agent」的纯逻辑（A-62/A-64）。
export const TRY_PHRASE = "用本地模型把这句话翻成英文：今天天气很好";

export function initialChecked(rows) {
  return new Set(rows.filter((r) => r.state === "installed" || r.state === "stale").map((r) => r.key));
}

export function applyEnabled(rows, checked) {
  return rows.some((r) => {
    const want = checked.has(r.key);
    // 勾上被占用的行也算变化：点了应用，这一行才会报出装不上的原因（A-54/A-64）。
    if (want) return r.state !== "installed";
    return r.state === "installed" || r.state === "stale";
  });
}

export function rowText(row) {
  switch (row.state) {
    case "installed": return { status: "已安装", tone: "ok" };
    case "absent": return { status: "未安装", tone: "none" };
    case "stale": return { status: row.message ?? "指向旧位置，点应用更新", tone: "warn" };
    case "occupied": return { status: row.message ?? "位置被占用，台面不会改动", tone: "warn" };
    default: return { status: `无法写入：${row.message ?? "未知原因"}`, tone: "warn" };
  }
}
