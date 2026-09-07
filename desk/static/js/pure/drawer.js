// 纯逻辑：哪些按键应关闭设置抽屉（Esc）。main.js 的 keydown 监听器据此决定是否调用 setDrawerOpen(false)。
export function isDrawerCloseKey(key) {
  return key === "Escape";
}
