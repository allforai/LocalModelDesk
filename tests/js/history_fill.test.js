import test from "node:test";
import assert from "node:assert/strict";
import { fillPlan } from "../../desk/static/js/pure/history_fill.js";

test("video 参数 → video 表单五字段", () => {
  const plan = fillPlan({ kind: "video", params: { prompt: "海边", width: 768, height: 448, frames: 49, steps: 16 } });
  assert.deepEqual(plan, { pane: "video", fields: { prompt: "海边", width: 768, height: 448, frames: 49, steps: 16 } });
});

test("music 参数 → music 表单三字段", () => {
  const plan = fillPlan({ kind: "music", params: { caption: "民谣", lyrics: "词", duration: 90 } });
  assert.deepEqual(plan, { pane: "music", fields: { caption: "民谣", lyrics: "词", duration: 90 } });
});

test("未知 kind → null（不显示按钮）", () => {
  assert.equal(fillPlan({ kind: "unknown", params: { prompt: "x" } }), null);
});

test("image 参数完整回填，保留种子零，并带上会话与尝试（D-93）", () => {
  const params = { prompt: "猫", width: 768, height: 1024, steps: 40, seed: 0 };
  assert.deepEqual(fillPlan({ kind: "image", params, session_id: "s1", attempt_id: "a1" }),
    { pane: "image", session_id: "s1", attempt_id: "a1", fields: params });
});

test("image 条目没有会话或种子时：会话为 null，种子为 null 而不是补 42（D-93）", () => {
  const plan = fillPlan({ kind: "image", params: { prompt: "猫", width: 512, height: 512, steps: 20 } });
  assert.deepEqual(plan, { pane: "image", session_id: null, attempt_id: null,
    fields: { prompt: "猫", width: 512, height: 512, steps: 20, seed: null } });
});

test("无 params / 空条目 → null", () => {
  assert.equal(fillPlan({ kind: "video" }), null);
  assert.equal(fillPlan(null), null);
});
