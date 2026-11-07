// Pi model IDs are stable; display names include versions and suggested use cases.
export const modelName = (model) => `${model.version} · ${model.use_case}`;
export const modelCommand = (key) => `pi --model lmdesk/${key}`;
export const RELOAD_HINT = "已有 pi 会话：先 /reload，再用 /model 搜索 lmdesk。列表每行仍显示 key，选中后下方 Model Name 显示完整版本和用途。第一条请求才自动加载模型，台面需保持运行。";
export function integrationView(state = {}, busy = false) {
  busy = busy || state.pi_install?.state === "running";
  const labels = { installing: "正在安装 pi", absent: "未安装", manual: "手动安装（可接管）", installed: "已安装", stale: "需更新", conflict: "文件冲突", error: "不可用" };
  return {
    label: labels[state.state] ?? "未知状态",
    tone: state.state === "installed" ? "ok" : ["conflict", "error", "stale"].includes(state.state) ? "busy" : "none",
    installDisabled: busy || !state.can_install,
    removeDisabled: busy || !state.can_remove,
  };
}
