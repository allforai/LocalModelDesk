import test from "node:test";
import assert from "node:assert/strict";
import { agentSwitchNotice } from "../../desk/static/js/pure/agent_switch.js";

const p = (key, by, name = key) => ({ state: { status: "loaded", model_key: key }, loaded_model: { name }, loaded_by: by });

test("agent 换了模型才提示", () => {
  assert.equal(agentSwitchNotice("glm", p("qwen27", "agent", "Qwen 27B")), "模型已被 agent 切换为 Qwen 27B");
  assert.equal(agentSwitchNotice("glm", p("qwen27", "ui")), null);
  assert.equal(agentSwitchNotice("glm", p("glm", "agent")), null);
  assert.equal(agentSwitchNotice(null, p("glm", "agent")), null);
  assert.equal(agentSwitchNotice("glm", { state: { status: "loading", model_key: "x" }, loaded_by: null }), null);
});
