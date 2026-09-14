// ui:fatal —— 台面无法进入时的整屏说明；配置损坏时给出唯一的恢复入口（J25）。
export function showFatal(root, error, { resetConfig, reload }) {
  const text = root.querySelector("[data-fatal-text]");
  const reset = root.querySelector("[data-fatal-reset]");
  root.hidden = false;
  text.textContent = `无法读取配置：${error.message}`;
  reset.hidden = error.code !== "config_corrupt";
  reset.addEventListener("click", async () => {
    reset.disabled = true;
    try {
      const result = await resetConfig();
      text.textContent = result.backup
        ? `已备份到 ${result.backup}，正在重新进入首次设置…`
        : "正在重新进入首次设置…";
      reload();
    } catch (failure) {
      text.textContent = `重新设置失败：${failure.message}`;
      reset.disabled = false;
    }
  });
}
