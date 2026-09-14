import test from "node:test";
import assert from "node:assert/strict";
import { showFatal } from "../../desk/static/js/widgets/fatal.js";

class El {
  constructor() { this.hidden = true; this.textContent = ""; this.listeners = {}; this.disabled = false; }
  addEventListener(type, fn) { this.listeners[type] = fn; }
}

function makeRoot() {
  const parts = { "[data-fatal-text]": new El(), "[data-fatal-reset]": new El() };
  const root = new El();
  root.querySelector = (selector) => parts[selector];
  return { root, text: parts["[data-fatal-text]"], reset: parts["[data-fatal-reset]"] };
}

test("坏配置：显示说明与「重新设置」，点击后备份并重新载入（J25）", async () => {
  const { root, text, reset } = makeRoot();
  let reloaded = false;
  showFatal(root, { code: "config_corrupt", message: "配置文件无法读取" }, {
    resetConfig: async () => ({ backup: "/d/config.broken-1.json", needs_setup: true }),
    reload: () => { reloaded = true; },
  });
  assert.equal(root.hidden, false);
  assert.equal(text.textContent, "无法读取配置：配置文件无法读取");
  assert.equal(reset.hidden, false);
  await reset.listeners.click();
  assert.equal(text.textContent, "已备份到 /d/config.broken-1.json，正在重新进入首次设置…");
  assert.equal(reloaded, true);
});

test("其它致命错误不给重设按钮；重设失败时说明原因", async () => {
  const other = makeRoot();
  showFatal(other.root, { code: "timeout", message: "请求超时" }, { resetConfig: async () => ({}), reload() {} });
  assert.equal(other.reset.hidden, true);

  const broken = makeRoot();
  showFatal(broken.root, { code: "config_corrupt", message: "坏了" }, {
    resetConfig: async () => { throw new Error("磁盘只读"); },
    reload() { throw new Error("不应重新载入"); },
  });
  await broken.reset.listeners.click();
  assert.equal(broken.text.textContent, "重新设置失败：磁盘只读");
  assert.equal(broken.reset.disabled, false);
});
