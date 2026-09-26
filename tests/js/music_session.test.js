import test from "node:test";
import assert from "node:assert/strict";
import * as m from "../../desk/static/js/pure/music_session.js";

const A = (id, extra = {}) => ({ id, status: "done", output: `${id}.wav`, ts: "2026-09-27T10:0" + id.length + ":00",
  params: { caption: "民谣", lyrics: "[verse]\n早晨的风\n吹过窗", duration: 30, seed: 11 }, ...extra });

test("readMusicParams validates and omits empty seed", () => {
  assert.deepEqual(m.readMusicParams({ caption: "民谣", lyrics: "la", duration: "30", seed: "" }), { caption: "民谣", lyrics: "la", duration: 30 });
  assert.throws(() => m.readMusicParams({ caption: " ", lyrics: "la", duration: "30" }), /请填写风格描述/);
  assert.throws(() => m.readMusicParams({ caption: "a", lyrics: " ", duration: "30" }), /请填写歌词/);
  assert.throws(() => m.readMusicParams({ caption: "a", lyrics: "l", duration: "5" }), (e) => e.advanced && /高级参数里的数值有误：时长须为 10–300 的整数/.test(e.message));
  assert.throws(() => m.readMusicParams({ caption: "a", lyrics: "l", duration: "30", seed: "-1" }), /种子须为 0–4294967295 的整数/);
});

test("versionParams keeps continues and draws a different seed", () => {
  const seeds = [11, 11, 42];
  const p = m.versionParams(A("b", { continues: "a" }), "s1", () => seeds.shift());
  assert.deepEqual(p, { session_id: "s1", caption: "民谣", lyrics: "[verse]\n早晨的风\n吹过窗", duration: 30, seed: 42, continues: "a" });
  assert.equal("continues" in m.versionParams(A("a"), "s1", () => 5), false);
});

test("next segment: keeps caption/duration; compose attempt keeps inputs", () => {
  assert.deepEqual(m.nextFields(A("a"), { caption: "x", duration: 99 }), { caption: "民谣", duration: 30 });
  assert.deepEqual(m.nextFields({ id: "c", status: "done", output: "c.wav", params: { parts: ["a", "b"] } }, { caption: "x", duration: 99 }),
    { caption: "x", duration: 99 });
  assert.equal(m.canContinue(A("a")), true);
  assert.equal(m.canContinue(A("a", { output_missing: true })), false);
  assert.equal(m.canContinue({ id: "f", status: "failed" }), false);
});

test("chip texts and stale continuation", () => {
  assert.equal(m.chipText({ type: "refine", index: 1 }), "沿用第 2 次");
  assert.equal(m.chipText({ type: "refine", index: null }), "沿用素材库里这首");
  assert.equal(m.chipText({ type: "continue", index: 2 }), "接在第 3 次后面");
  assert.equal(m.chipText({ type: "continue", index: 2, missing: true }), "第 3 次的文件已不在，不能接着写");
  assert.equal(m.submitContinues({ type: "continue", attemptId: "c" }, ""), "c");
  assert.equal(m.submitContinues({ type: "refine", attemptId: "b", continues: "a", seed: 11 }, "11"), "a");
  assert.equal(m.submitContinues({ type: "refine", attemptId: "b", continues: "a", seed: 11 }, "12"), null);   // 改了种子→提示条隐藏→不续写
  assert.equal(m.submitContinues(null, ""), null);
});

test("card title, lyrics preview, chain line with gap", () => {
  const attempts = [A("a"), A("bb", { continues: "a" }), { id: "c", status: "done", output: "c.wav", op: "compose", params: { parts: ["a", "bb"] } }, A("ddd", { continues: "zz" })];
  assert.match(m.cardTitle(attempts[1], 1, attempts), /^第 2 次 · \d\d:\d\d · 接第 1 次$/);
  assert.match(m.cardTitle(attempts[2], 2, attempts), /合成：第 1、2 次$/);
  assert.equal(m.lyricsPreview("[verse]\n\n早晨的风\n"), "早晨的风");
  assert.equal(m.chainLine(attempts[1], attempts), "由：第 1 次 → 第 2 次");
  assert.equal(m.chainLine(attempts[0], attempts), "");
  assert.equal(m.chainLine(attempts[3], attempts), "由：… → 第 4 次");
});

test("join problem offers rejoin only for recoverable codes and complete chains", () => {
  const a = A("a"), b = A("b", { continues: "a", joined_error: { code: "join_failed", message: "拼接成片失败" } });
  assert.deepEqual(m.joinProblem(b, [a, b]), { text: "这一段生成好了，但成片没拼成：拼接成片失败", rejoin: { parts: ["a", "b"] }, reason: "" });
  const gone = { ...a, output_missing: true };
  assert.deepEqual(m.joinProblem(b, [gone, b]).rejoin, null);
  assert.equal(m.joinProblem(b, [gone, b]).reason, "链上有一段已不在");
  const missing = A("b", { continues: "a", joined_error: { code: "segment_missing", message: "第 1 段的文件已不在，无法拼成成片" } });
  assert.deepEqual(m.joinProblem(missing, [a, missing]), { text: "这一段生成好了，但成片没拼成：第 1 段的文件已不在，无法拼成成片", rejoin: null, reason: "" });
  assert.equal(m.joinProblem(a, [a]), null);
});
