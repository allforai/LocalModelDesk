// 聊天页：驻留模型被 agent 换掉时给一条可关闭的提示（A-66）。
// prevKey：上次看到的驻留模型；null 表示上次看到的是「没加载」，undefined 表示页面还没拿到过状态。
export function agentSwitchNotice(prevKey, payload) {
  const state = payload?.state ?? {};
  if (state.status !== "loaded" || !state.model_key || payload.loaded_by !== "agent") return null;
  if (prevKey === undefined || prevKey === state.model_key) return null;
  return `模型已被 agent 切换为 ${payload.loaded_model?.name ?? state.model_key}`;
}
