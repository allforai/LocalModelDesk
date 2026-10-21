// 设置页「本机 agent」的纯逻辑（A-62/A-64）。
export const TRY_PHRASE = "用本地模型把这句话翻成英文：今天天气很好";

export function initialChecked(rows) {
  return new Set(rows.filter((r) => r.state === "installed" || r.state === "stale").map((r) => r.key));
}

// cli 是命令行链接那一行（payload.cli）。它跟着 agent 行走：应用后只要有一行装上，它就该在；
// 一行都不装，它就该被卸掉（installer.apply）。它失效或缺失时也要能点应用，点了才会修好（A-64，G9）。
export function applyEnabled(rows, checked, cli = null) {
  const rowsChange = rows.some((r) => {
    const want = checked.has(r.key);
    // 勾上被占用的行也算变化：点了应用，这一行才会报出装不上的原因（A-54/A-64）。
    if (want) return r.state !== "installed";
    return r.state === "installed" || r.state === "stale";
  });
  if (rowsChange || !cli) return rowsChange;
  if (rows.some((r) => checked.has(r.key))) return cli.state === "stale" || cli.state === "absent";
  return cli.state === "installed" || cli.state === "stale";
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
