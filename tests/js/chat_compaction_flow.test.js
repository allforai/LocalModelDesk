import test from "node:test";
import assert from "node:assert/strict";
import { maybeCompact } from "../../desk/static/js/pure/compaction.js";

const longTurn = (n) => [
  { role: "user", content: "问".repeat(n) },
  { role: "assistant", content: "答".repeat(n) },
];

function fakeSummarise(text) {
  return async () => text;
}

// 计划 Task 4 Step 1 原样给的例子用 compactAt: 30_000（配 ratio 4）——
// tailBudgetChars = compactAt * 0.5 * ratio = 60_000 字符，而这几条用例的
// 全部消息内容加起来才 1600 多字符，永远进不了尾部预算的裁剪线，splitForCompaction
// 按 Task 1 已提交、已测试过的算法（尾部预算=触发点的一半再折算成字符）算出来
// head 恒为空——不是实现写错，是计划这批数字本身凑不出「超过预算」的场景。
// 改用 compactAt: 200（tailBudgetChars=400）让两个 400 字符的旧回合真正超出
// 尾部预算，测的才是「压缩真的发生」而不是「没触发也通过」。见 deviations。
test("超过触发点时产出一条摘要，并标出它替代到哪一条", async () => {
  const messages = [...longTurn(400), ...longTurn(400), ...longTurn(5)];
  const result = await maybeCompact(messages, {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 200,
    summarise: fakeSummarise("填好的表"),
  });
  assert.equal(result.messages.at(0).role, "summary");
  assert.equal(result.messages.at(0).content, "填好的表");
  assert.equal(Number.isInteger(result.messages.at(0).replaced_through), true);
});

test("原始消息一条都不少——压缩只影响发送，不影响存储", async () => {
  const messages = [...longTurn(400), ...longTurn(400), ...longTurn(5)];
  const result = await maybeCompact(messages, {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 200,
    summarise: fakeSummarise("填好的表"),
  });
  const kept = result.messages.filter((m) => m.role !== "summary");
  assert.deepEqual(kept, messages);
});

test("没到触发点时原样返回，且不调模型", async () => {
  let called = false;
  const messages = longTurn(5);
  const result = await maybeCompact(messages, {
    promptTokens: 10, sentChars: 40, compactAt: 30_000,
    summarise: async () => { called = true; return "不该被调用"; },
  });
  assert.equal(called, false);
  assert.equal(result.compacted, false);
  assert.deepEqual(result.messages, messages);
});

test("摘要生成失败时什么都不写——绝不留下「标了替代却没有摘要」的中间态", async () => {
  const messages = [...longTurn(400), ...longTurn(400), ...longTurn(5)];
  const result = await maybeCompact(messages, {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 200,
    summarise: async () => { throw new Error("模型炸了"); },
  });
  assert.equal(result.compacted, false);
  assert.deepEqual(result.messages, messages);
  assert.match(result.error ?? "", /模型炸了/);
});

test("摘要是空字符串时同样视为失败", async () => {
  const messages = [...longTurn(400), ...longTurn(400), ...longTurn(5)];
  const result = await maybeCompact(messages, {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 200,
    summarise: fakeSummarise("   "),
  });
  assert.equal(result.compacted, false);
  assert.deepEqual(result.messages, messages);
});

test("量不到每 token 字符数时不压缩", async () => {
  const messages = [...longTurn(400), ...longTurn(400)];
  const result = await maybeCompact(messages, {
    promptTokens: 0, sentChars: 0, compactAt: 30_000,
    summarise: fakeSummarise("不该被调用"),
  });
  assert.equal(result.compacted, false);
});

test("replaced_through 精确指向被替代的最后一条，不差一位", async () => {
  const head = longTurn(400);                     // 2 条要被替代
  const tail = longTurn(5);                       // 2 条保留
  const result = await maybeCompact([...head, ...tail], {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 200,
    summarise: fakeSummarise("表"),
  });
  const summary = result.messages[0];
  // 新数组：[summary, head0, head1, tail0, tail1]
  assert.equal(summary.replaced_through, 2);
  // 被替代的正好是 head 两条，tail 两条必须还在发送范围内
  assert.deepEqual(result.messages.slice(3), tail);
});
