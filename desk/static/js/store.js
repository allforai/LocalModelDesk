// 极轻量状态容器：tick 最新快照 + 当前会话 id（设计 §3）。无持久化。
export function createStore(initial = {}) {
  let state = { ...initial };
  const subscribers = new Set();

  return {
    get: () => state,
    set(patch) {
      state = { ...state, ...patch };
      for (const subscriber of [...subscribers]) subscriber(state);
    },
    subscribe(subscriber) {
      subscribers.add(subscriber);
      return () => subscribers.delete(subscriber);
    },
  };
}
