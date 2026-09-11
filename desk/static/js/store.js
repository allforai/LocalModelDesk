// 极轻量状态容器：tick 最新快照 + 当前会话 id（设计 §3）。无持久化。
// get/subscribe 已删（零调用点，F13 census 2026-09-08）：目前只有 main.js 写入。
export function createStore(initial = {}) {
  let state = { ...initial };

  return {
    set(patch) {
      state = { ...state, ...patch };
    },
  };
}
