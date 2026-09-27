import test from "node:test";
import assert from "node:assert/strict";
import { fillPlan } from "../../desk/static/js/pure/history_fill.js";

test("video 参数 → video 表单五字段", () => {
  const plan = fillPlan({ kind: "video", params: { prompt: "海边", width: 768, height: 448, frames: 49, steps: 16 } });
  assert.deepEqual(plan, { pane: "video", session_id: null, attempt_id: null, fields: { prompt: "海边", width: 768, height: 448, frames: 49, steps: 16, seed: null } });
});

test("video 条目带种子与顶层 refs（V-05、V-61）", () => {
  const ref = { kind: "image", session_id: "s", attempt_id: "a" };
  const plan = fillPlan({ kind: "video", refs: { first_frame: ref },
    params: { prompt: "p", width: 512, height: 288, frames: 49, steps: 16, seed: 7, mode: "image", first_frame: null, use_audio: true } });
  assert.equal(plan.fields.seed, 7);
  assert.deepEqual(plan.fields.refs, { first_frame: ref });
  assert.equal("refs" in fillPlan({ kind: "video", refs: {}, params: { prompt: "p" } }).fields, false);
});

test("video 条目 mode music_ref 带 ref_image 与 audio_start（素材库回填要恢复参考图与起始秒）", () => {
  const plan = fillPlan({ kind: "video", params: { prompt: "p", width: 512, height: 288, frames: 49, steps: 16,
    mode: "music_ref", ref_image: "abc.png", audio_start: 12 } });
  assert.equal(plan.fields.ref_image, "abc.png");
  assert.equal(plan.fields.audio_start, 12);
});

test("music 参数 → music 表单四字段，带种子（M-52：回填后能沿用素材库里这首）", () => {
  const plan = fillPlan({ kind: "music", params: { caption: "民谣", lyrics: "词", duration: 90, seed: 11 } });
  assert.deepEqual(plan, { pane: "music", session_id: null, attempt_id: null, fields: { caption: "民谣", lyrics: "词", duration: 90, seed: 11 } });
});

test("music 参数没有种子 → seed 为 null，不补默认值", () => {
  const plan = fillPlan({ kind: "music", params: { caption: "民谣", lyrics: "词", duration: 90 } });
  assert.deepEqual(plan, { pane: "music", session_id: null, attempt_id: null, fields: { caption: "民谣", lyrics: "词", duration: 90, seed: null } });
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

test("fillPlan carries session fields for video and music, and skips compose entries", () => {
  const video = fillPlan({ kind: "video", session_id: "s", attempt_id: "a", params: { prompt: "p", width: 512, height: 288, frames: 49, steps: 12 } });
  assert.equal(video.session_id, "s"); assert.equal(video.attempt_id, "a");
  const music = fillPlan({ kind: "music", session_id: "m", attempt_id: "b", params: { caption: "c", lyrics: "l", duration: 20 } });
  assert.equal(music.session_id, "m"); assert.equal(music.attempt_id, "b");
  assert.equal(fillPlan({ kind: "video", params: { op: "compose", parts: ["a", "b"] } }), null);
  assert.equal(fillPlan({ kind: "video", params: { op: "soundtrack", source: "a" } }), null);
  assert.equal(fillPlan({ kind: "video", params: { prompt: "p" } }).session_id, null);
});
