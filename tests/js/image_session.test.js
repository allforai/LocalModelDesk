import test from "node:test";
import assert from "node:assert/strict";
import {
  readImageParams, recomposeParams, refineChipText, refineChipVisible, refineFields, specLine,
  hasImage, submitBase, baseLabel, NO_IMAGE_REASON,
} from "../../desk/static/js/pure/image_session.js";
import { attemptView } from "../../desk/static/js/pure/media_session.js";

const SEED = "种子"; // 「种子」

test("卡片标题行：规格文案（D-73）", () => {
  assert.equal(specLine({ width: 1024, height: 768, steps: 40 }), "1024×768 · 40 步");
});

test("尝试状态 → 标记与原因（D-84、D-85）：失败、已取消、退出取消、中断、文件不在", () => {
  assert.deepEqual(attemptView({ status: "done", output: "a.png" }).kind, "done");
  const failed = attemptView({ status: "failed", error: { code: "exit_nonzero", message: "exit 1", log_tail: "boom" } });
  assert.equal(failed.kind, "failed"); assert.equal(failed.badge, "失败");
  assert.equal(failed.title, "生成程序异常退出"); assert.equal(failed.icon, "x"); assert.equal(failed.tone, "danger");
  assert.equal(attemptView({ status: "failed", error: { code: "interrupted", message: "x" } }).title, "应用在生成途中关闭，这次没有完成");
  const cancelled = attemptView({ status: "cancelled", error: { code: "cancelled", message: "已取消：这次生成被手动停止" } });
  assert.equal(cancelled.badge, "已取消"); assert.equal(cancelled.title, "已取消"); assert.equal(cancelled.tone, "muted");
  // AC-6「显示原因」：用户取消的说明来自存进文件的原话（D-09），去掉与标记重复的「已取消：」。
  assert.equal(cancelled.sub, "这次生成被手动停止");
  assert.equal(attemptView({ status: "cancelled", error: { code: "cancelled", message: "已取消" } }).sub, "");
  assert.equal(attemptView({ status: "cancelled", error: null }).sub, "");
  assert.equal(attemptView({ status: "cancelled", error: { code: "cancelled_on_quit", message: "应用退出时停止了这次生成" } }).sub, "");
  assert.equal(attemptView({ status: "cancelled", error: { code: "cancelled_on_quit", message: "x" } }).title, "应用退出时停止了这次生成");
  const missing = attemptView({ status: "done", output: "a.png", output_missing: true });
  assert.equal(missing.kind, "missing"); assert.equal(missing.icon, "image");
  assert.equal(missing.title, "图片文件已不在"); assert.equal(missing.sub, "可能已在访达中移动或删除");
  assert.equal(attemptView({ status: "done", output: "a.png" }, { broken: true }).kind, "missing");
  assert.equal(attemptView({ status: "running" }).kind, "running");
});

test("「在这张基础上改」回填五个值并沿用种子（D-40、D-44）", () => {
  const attempt = { params: { prompt: "猫", width: 768, height: 512, steps: 30, seed: 0 } };
  assert.deepEqual(refineFields(attempt), { prompt: "猫", width: 768, height: 512, steps: 30, seed: 0 });
});

test("「换个构图」同参数、新随机种子，恰好相同时重取（D-46）", () => {
  const attempt = { params: { prompt: "猫", width: 768, height: 512, steps: 30, seed: 7 } };
  const draws = [7, 7, 99];
  const params = recomposeParams(attempt, "s1", () => draws.shift());
  assert.deepEqual(params, { session_id: "s1", prompt: "猫", width: 768, height: 512, steps: 30, seed: 99 });
});

test("提示条只在种子框等于被引用尝试的种子时显示（D-41、D-42、D-95）", () => {
  const ref = { seed: 12, index: 1 };
  assert.equal(refineChipVisible("12", ref), true);
  assert.equal(refineChipVisible(" 12 ", ref), true);
  assert.equal(refineChipVisible("13", ref), false);
  assert.equal(refineChipVisible("", ref), false);
  assert.equal(refineChipVisible("0", { seed: 0, index: 0 }), true);
  assert.equal(refineChipVisible("12", null), false);
  assert.equal(refineChipText(ref), "沿用第 2 次的构图");
  assert.equal(refineChipText({ seed: 3, index: null }), "沿用素材库里这张的构图");
});

test("输入区读数：种子留空不传；高级参数错误带前缀（D-51、D-66）", () => {
  assert.deepEqual(readImageParams({ prompt: "猫", width: "1024", height: "768", steps: "40", seed: "" }),
    { prompt: "猫", width: 1024, height: 768, steps: 40 });
  assert.deepEqual(readImageParams({ prompt: "猫", width: "1024", height: "768", steps: "40", seed: "0" }).seed, 0);
  assert.throws(() => readImageParams({ prompt: " ", width: "1024", height: "1024", steps: "40" }),
    (error) => error.message === "请填写图片提示词" && !error.advanced);
  for (const bad of [{ width: "257" }, { steps: "0" }, { seed: "-1" }, { seed: "4294967296" }, { seed: "1.5" }, { height: "" }]) {
    assert.throws(() => readImageParams({ prompt: "猫", width: "1024", height: "1024", steps: "40", seed: "", ...bad }),
      (error) => error.advanced && error.message.startsWith("高级参数里的数值有误："), JSON.stringify(bad));
  }
});

test("规格、提示条、尝试状态文案都不出现「种子」（D-50）", () => {
  const texts = [
    specLine({ width: 1, height: 1, steps: 1 }), refineChipText({ index: 0 }), refineChipText({ index: null }),
    ...["failed", "cancelled", "done"].flatMap((status) => {
      const v = attemptView({ status, output: "a.png", output_missing: true, error: { code: "exit_nonzero", message: "m" } });
      return [v.badge, v.title, v.sub];
    }),
  ];
  for (const text of texts) assert.ok(!String(text).includes(SEED), text);
});


// ---- 以图生图（2026-09-24）：两个按钮以这张为底稿重绘 ----

const DONE = { id: "a1", status: "done", output: "x.png", params: { prompt: "猫", width: 512, height: 768, steps: 16, seed: 7 } };

test("有图才能当底稿：done、有文件名、文件还在", () => {
  assert.equal(hasImage(DONE), true);
  assert.equal(hasImage({ ...DONE, output_missing: true }), false);
  assert.equal(hasImage({ ...DONE, status: "failed" }), false);
  assert.equal(hasImage({ ...DONE, output: null }), false);
  assert.equal(hasImage(null), false);
});

test("「换个构图」以这张为底稿、强度 0.35（保留主体与色调，换构图）", () => {
  const params = recomposeParams(DONE, "s1", () => 99);
  assert.deepEqual(params.base, { attempt_id: "a1", strength: 0.35 });
  assert.equal(params.prompt, "猫");
  assert.equal(params.seed, 99);
});

test("「在这张基础上改」后提示条还在时，「生成图片」以那张为底稿、强度 0.6", () => {
  const ref = { seed: 7, index: 0, attemptId: "a1", image: true };
  assert.deepEqual(submitBase("7", ref), { attempt_id: "a1", strength: 0.6 });
  assert.equal(submitBase("8", ref), null);              // 改了种子：提示条消失，退回文生图
  assert.equal(submitBase("7", { ...ref, image: false }), null); // 没图的尝试只回填
  assert.equal(submitBase("7", { seed: 7, index: null }), null);  // 素材库回填（无会话尝试）
  assert.equal(refineChipText(ref), "以第 1 次为底稿");
  assert.equal(refineChipText({ ...ref, image: false }), "沿用第 1 次的构图");
});

test("卡片标「基于第 N 次」；底稿不在列表里或没有底稿时不标", () => {
  const attempts = [DONE, { id: "a2", base: { attempt_id: "a1", strength: 0.6 } }, { id: "a3", base: { attempt_id: "gone", strength: 0.35 } }];
  assert.equal(baseLabel(attempts[1], attempts), "基于第 1 次");
  assert.equal(baseLabel(attempts[2], attempts), "");
  assert.equal(baseLabel(DONE, attempts), "");
  assert.ok(NO_IMAGE_REASON.length > 0 && !NO_IMAGE_REASON.includes(SEED));
});
