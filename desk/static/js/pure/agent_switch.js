// 聊天页：驻留模型被 agent 换掉时给一条可关闭的提示（A-66）。
export function agentSwitchNotice(prevKey, payload) {
  const state = payload?.state ?? {};
  if (state.status !== "loaded" || !state.model_key || payload.loaded_by !== "agent") return null;
  if (prevKey === null || prevKey === state.model_key) return null;
  return `模型已被 agent 切换为 ${payload.loaded_model?.name ?? state.model_key}`;
}
