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
  assert.equal(fillPlan({ kind: "image", params: { prompt: "x" } }), null);
});

test("无 params / 空条目 → null", () => {
  assert.equal(fillPlan({ kind: "video" }), null);
  assert.equal(fillPlan(null), null);
});
