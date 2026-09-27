import test from "node:test";
import assert from "node:assert/strict";
import * as v from "../../desk/static/js/pure/video_session.js";

const T = (id, extra = {}) => ({ id, status: "done", output: `${id}.mp4`, ts: "2026-09-27T10:00:00",
  params: { prompt: "雨夜街道", width: 512, height: 288, frames: 73, steps: 16, seed: 9 }, refs: {}, ...extra });

test("readVideoParams", () => {
  assert.deepEqual(v.readVideoParams({ prompt: "p", size: "768x448", frames: "124", steps: "16", seed: "" }),
    { prompt: "p", width: 768, height: 448, frames: 124, steps: 16 });
  assert.throws(() => v.readVideoParams({ prompt: " ", size: "512x288", frames: "49", steps: "16" }), /请填写视频提示词/);
  assert.throws(() => v.readVideoParams({ prompt: "p", size: "512x288", frames: "49", steps: "3" }), (e) => e.advanced && /步数须为 4–50 的整数/.test(e.message));
  assert.throws(() => v.readVideoParams({ prompt: "p", size: "512x288", frames: "49", steps: "16", seed: "x" }), /种子须为 0–4294967295 的整数/);
});

test("spec line and duration label", () => {
  assert.equal(v.specLine({ width: 512, height: 288, frames: 73, steps: 16 }), "512×288 · 约 3 秒 · 16 步");
  assert.equal(v.durationLabel(125), "约 5 秒");
});

test("sourceOf distinguishes upload, ref and continuation", () => {
  assert.deepEqual(v.sourceOf(T("a", { params: { ...T("a").params, mode: "image", first_frame: "f.png" } })), { type: "upload", id: "f.png" });
  const ref = { kind: "image", session_id: "s", attempt_id: "i" };
  assert.deepEqual(v.sourceOf(T("b", { params: { ...T("b").params, mode: "image" }, refs: { first_frame: ref } })), { type: "ref", ref });
  assert.deepEqual(v.sourceOf(T("c", { continues: "a", params: { ...T("c").params, mode: "image", first_frame: "x.png" } })), { type: "continue", attemptId: "a" });
  assert.equal(v.sourceOf(T("d")), null);
});

test("versionParams keeps assets, refs and continues with a new seed", () => {
  const ref = { kind: "image", session_id: "s", attempt_id: "i" };
  const a = T("b", { params: { ...T("b").params, mode: "image", use_audio: true, last_frame: "l.png" }, refs: { first_frame: ref } });
  const seeds = [9, 10];
  assert.deepEqual(v.versionParams(a, "s1", () => seeds.shift()), {
    session_id: "s1", prompt: "雨夜街道", width: 512, height: 288, frames: 73, steps: 16, seed: 10,
    mode: "image", use_audio: true, last_frame: "l.png", refs: { first_frame: ref } });
  const c = T("c", { continues: "a", params: { ...T("c").params, mode: "image", first_frame: "x.png", use_audio: true } });
  const p = v.versionParams(c, "s1", () => 1);
  assert.equal(p.continues, "a"); assert.equal("first_frame" in p, false); assert.equal("mode" in p, false);   // 续写由后端决定首帧与方式
});

test("versionParams 续写段换版本保留 use_audio（未勾选不能被后端默认值带回来）", () => {
  const off = T("c", { continues: "a", params: { ...T("c").params, mode: "image", first_frame: "x.png", use_audio: false } });
  assert.equal(v.versionParams(off, "s1", () => 1).use_audio, false);
  const on = T("c", { continues: "a", params: { ...T("c").params, mode: "image", first_frame: "x.png", use_audio: true } });
  assert.equal(v.versionParams(on, "s1", () => 1).use_audio, true);
  const absent = T("c", { continues: "a", params: { ...T("c").params, mode: "image", first_frame: "x.png" } });
  assert.equal("use_audio" in v.versionParams(absent, "s1", () => 1), false);
});

test("next segment keeps size/frames/steps; compose keeps current", () => {
  assert.deepEqual(v.nextFields(T("a"), { size: "1024x576", frames: 49, steps: 20 }), { size: "512x288", frames: 73, steps: 16 });
  assert.deepEqual(v.nextFields({ id: "c", status: "done", output: "c.mp4", op: "compose", params: { parts: ["a", "b"] } }, { size: "1024x576", frames: 49, steps: 20 }),
    { size: "1024x576", frames: 49, steps: 20 });
});

test("chip and first-frame labels", () => {
  assert.equal(v.chipText({ type: "continue", index: 0 }), "接在第 1 次后面");
  assert.equal(v.chipText({ type: "continue", index: 0, missing: true }), "第 1 次的文件已不在，不能接着往下生");
  assert.equal(v.chipText({ type: "library" }), "沿用素材库里这段");
  assert.equal(v.chipText({ type: "refine", index: 1 }), "沿用第 2 次");
  assert.equal(v.firstFrameLabel({ type: "upload" }, { fileName: "cat.png" }), "已选择：cat.png");
  assert.equal(v.firstFrameLabel({ type: "ref" }, { imageTitle: "橘猫", imageIndex: 2 }), "首帧：图片会话「橘猫」第 3 次");
  assert.equal(v.firstFrameLabel({ type: "ref" }, {}), "首帧：来自图片会话");
  assert.equal(v.firstFrameLabel({ type: "continue" }, { continueIndex: 1 }), "接在第 2 次后面（用它的最后一帧）");
});

test("refineFields extracts this attempt's own params for text/image-upload/image-ref/reference/continued attempts", () => {
  assert.deepEqual(v.refineFields(T("a")), { mode: "text", prompt: "雨夜街道", size: "512x288", frames: 73, steps: 16, seed: 9,
    first: null, last: null, refVideo: null, useAudio: true, audioStart: 0 });
  const upload = T("b", { params: { ...T("b").params, mode: "image", first_frame: "f.png", use_audio: false } });
  assert.deepEqual(v.refineFields(upload), { mode: "image", prompt: "雨夜街道", size: "512x288", frames: 73, steps: 16, seed: 9,
    first: "f.png", last: null, refVideo: null, useAudio: false, audioStart: 0 });
  // 图片会话引用：后端记 params.first_frame 为 null（V-04），来源由 refs 另行表达（sourceOf 负责），refineFields 只读自己的字段。
  const ref = T("c", { params: { ...T("c").params, mode: "image", first_frame: null }, refs: { first_frame: { kind: "image", session_id: "s", attempt_id: "i" } } });
  assert.deepEqual(v.refineFields(ref), { mode: "image", prompt: "雨夜街道", size: "512x288", frames: 73, steps: 16, seed: 9,
    first: null, last: null, refVideo: null, useAudio: true, audioStart: 0 });
  const reference = T("d", { params: { ...T("d").params, mode: "reference", ref_video: "v.mp4" } });
  assert.deepEqual(v.refineFields(reference), { mode: "reference", prompt: "雨夜街道", size: "512x288", frames: 73, steps: 16, seed: 9,
    first: null, last: null, refVideo: "v.mp4", useAudio: true, audioStart: 0 });
  // 续写段自己的 first_frame 也是 null（由上一段最后一帧推导），continues 不影响 refineFields 的读取。
  const continued = T("e", { continues: "a", params: { ...T("e").params, mode: "image", first_frame: null } });
  assert.deepEqual(v.refineFields(continued), { mode: "image", prompt: "雨夜街道", size: "512x288", frames: 73, steps: 16, seed: 9,
    first: null, last: null, refVideo: null, useAudio: true, audioStart: 0 });
});

test("canContinue requires a done attempt with a present file", () => {
  assert.equal(v.canContinue(T("a")), true);
  assert.equal(v.canContinue(T("a", { output_missing: true })), false);
  assert.equal(v.canContinue({ id: "f", status: "failed" }), false);
});

test("cardTitle marks continued and compose attempts", () => {
  const attempts = [T("a"), T("bb", { continues: "a" }), { id: "c", status: "done", output: "c.mp4", op: "compose", params: { parts: ["a", "bb"] } }];
  assert.match(v.cardTitle(attempts[1], 1, attempts), /^第 2 次 · \d\d:\d\d · 接第 1 次$/);
  assert.match(v.cardTitle(attempts[2], 2, attempts), /合成：第 1、2 次$/);
  assert.match(v.cardTitle(attempts[0], 0, attempts), /^第 1 次 · \d\d:\d\d$/);
});

const song = { kind: "music", session_id: "m1", attempt_id: "t2" };
const img = { kind: "image", session_id: "s", attempt_id: "i" };
const musicRef = (extra = {}, refs = { ref_audio: song }) => T("m", { params: { ...T("m").params, mode: "music_ref", use_audio: true,
  audio_start: 12.5, ref_image: "r.png", ...extra }, refs });

test("MODES 有配乐参考", () => {
  assert.equal(v.MODES.music_ref, "配乐参考");
});

test("refineFields 读出 music_ref 的起始秒；refImageOf 区分上传与图片会话引用", () => {
  const fields = v.refineFields(musicRef());
  assert.equal(fields.mode, "music_ref");
  assert.equal(fields.audioStart, 12.5);
  assert.deepEqual(v.refImageOf(musicRef()), { type: "upload", id: "r.png" });
  assert.deepEqual(v.refImageOf(musicRef({ ref_image: null }, { ref_audio: song, ref_image: img })), { type: "ref", ref: img });
  assert.equal(v.refImageOf(T("a")), null);
  assert.equal(v.refImageOf(T("b", { params: { ...T("b").params, mode: "image", first_frame: "f.png" } })), null);
});

test("versionParams 原样重发 music_ref：新种子、audio_start、ref_image 与 refs，不带 use_audio", () => {
  assert.deepEqual(v.versionParams(musicRef(), "s1", () => 5), {
    session_id: "s1", prompt: "雨夜街道", width: 512, height: 288, frames: 73, steps: 16, seed: 5,
    mode: "music_ref", ref_image: "r.png", audio_start: 12.5, refs: { ref_audio: song } });
  const fromRef = v.versionParams(musicRef({ ref_image: null, audio_start: 0 }, { ref_audio: song, ref_image: img }), "s1", () => 5);
  assert.equal("ref_image" in fromRef, false);
  assert.equal(fromRef.audio_start, 0);
  assert.deepEqual(fromRef.refs, { ref_audio: song, ref_image: img });
});

test("soundtrackTitle：配乐摘要与基于第几次；取不到时省略", () => {
  const attempts = [T("a"), { id: "s", status: "done", output: "s.mp4", ts: "2026-09-27T10:05:00", op: "soundtrack",
    params: { source: "a" }, refs: { soundtrack: song } }];
  assert.equal(v.soundtrackTitle(attempts[1], 1, attempts, "轻快钢琴"), "第 2 次 · 10:05 · 配乐：轻快钢琴 · 基于第 1 次");
  assert.equal(v.soundtrackTitle(attempts[1], 1, attempts, ""), "第 2 次 · 10:05 · 配乐 · 基于第 1 次");
  assert.equal(v.soundtrackTitle({ ...attempts[1], params: { source: "gone" } }, 1, attempts, "轻快钢琴"), "第 2 次 · 10:05 · 配乐：轻快钢琴");
  assert.equal(v.cardTitle(attempts[1], 1, attempts), "第 2 次 · 10:05 · 配乐 · 基于第 1 次");
});

test("接着往下生：配乐尝试没有画幅参数，保留输入区当前值", () => {
  const st = { id: "s", status: "done", output: "s.mp4", op: "soundtrack", params: { source: "a" } };
  assert.deepEqual(v.nextFields(st, { size: "1024x576", frames: 49, steps: 20 }), { size: "1024x576", frames: 49, steps: 20 });
});
