import test from "node:test";
import assert from "node:assert/strict";
import { integrationView, modelCommand, modelName, RELOAD_HINT } from "../../desk/static/js/pure/pi_integration.js";

test("状态和按钮跟后端能力走，忙时禁止重复提交", () => {
  assert.equal(integrationView({ state: "installed" }).label, "已安装");
  assert.equal(integrationView({ state: "manual", can_install: true }).installDisabled, false);
  assert.equal(integrationView({ state: "stale", can_install: true, can_remove: true }).removeDisabled, false);
  const conflict = integrationView({ state: "conflict", can_install: false, can_remove: false });
  assert.equal(conflict.label, "文件冲突");
  assert.equal(conflict.installDisabled, true);
  assert.equal(conflict.removeDisabled, true);
  assert.equal(integrationView({ can_install: true, can_remove: true }, true).installDisabled, true);
});

test("名称含版本和用途，命令保留稳定 key", () => {
  assert.equal(modelName({ version: "Gemma 4 31B 8bit", use_case: "擅长看图（台面）·pi仅文本" }), "Gemma 4 31B 8bit · 擅长看图（台面）·pi仅文本");
  assert.equal(modelCommand("glm"), "pi --model lmdesk/glm");
  assert.match(RELOAD_HINT, /\/reload/);
  assert.match(RELOAD_HINT, /Model Name/);
  assert.match(RELOAD_HINT, /第一条请求/);
});
