import test from "node:test";
import assert from "node:assert/strict";
import { charsPerToken, needsCompaction, splitForCompaction } from "../../desk/static/js/pure/compaction.js";

const msg = (role, content) => ({ role, content });

test("每 token 字符数由上一轮真实读数相除得出，不猜常数", () => {
  assert.equal(charsPerToken(4000, 1000), 4);
});

test("缺任一读数就返回 null，调用方据此不压缩", () => {
  assert.equal(charsPerToken(4000, 0), null);
  assert.equal(charsPerToken(0, 1000), null);
  assert.equal(charsPerToken(4000, undefined), null);
});

test("超过触发点就该压", () => {
  assert.equal(needsCompaction({ promptTokens: 30_000, compactAt: 29_971 }), true);
});

test("没到触发点不压", () => {
  assert.equal(needsCompaction({ promptTokens: 1_000, compactAt: 29_971 }), false);
});

test("内存压力起来时立即压，不等额度用满", () => {
  // R-budget-09 第一步：这是台面唯一能便宜做到的减压动作。
  assert.equal(needsCompaction({ promptTokens: 10, compactAt: 29_971, pressure: "warn" }), true);
});

test("算不出额度时一律不压", () => {
  // 预算说「算不出」就别替用户裁剪历史——与 budget 的「未经实测不放宽」同一条纪律。
  assert.equal(needsCompaction({ promptTokens: 999_999, compactAt: 0 }), false);
  assert.equal(needsCompaction({ promptTokens: 999_999, compactAt: undefined }), false);
});

test("压力起来但额度算不出时，仍然不压", () => {
  assert.equal(needsCompaction({ promptTokens: 10, compactAt: 0, pressure: "critical" }), false);
});

test("尾部按预算反推，不是写死的轮数", () => {
  // compactAt=100，一半=50 token，每 token 4 字符 ⇒ 尾部最多约 200 字符
  const messages = [
    msg("user", "a".repeat(400)), msg("assistant", "b".repeat(400)),
    msg("user", "c".repeat(80)), msg("assistant", "d".repeat(80)),
  ];
  const { head, tail } = splitForCompaction(messages, { compactAt: 100, charsPerToken: 4 });
  assert.equal(head.length, 2);
  assert.deepEqual(tail.map((m) => m.role), ["user", "assistant"]);
});

test("至少保留最近一轮完整问答，哪怕它超预算", () => {
  // 尾部预算再小也不能把用户刚问的那句连同回答一起摘掉——那是他眼前正在看的。
  const messages = [
    msg("user", "旧"), msg("assistant", "旧答"),
    msg("user", "x".repeat(10_000)), msg("assistant", "y".repeat(10_000)),
  ];
  const { head, tail } = splitForCompaction(messages, { compactAt: 10, charsPerToken: 4 });
  assert.equal(tail.length, 2);
  assert.equal(head.length, 2);
});

test("整段对话还没超出尾部预算时，没有可压的头部", () => {
  const messages = [msg("user", "短"), msg("assistant", "也短")];
  const { head, tail } = splitForCompaction(messages, { compactAt: 10_000, charsPerToken: 4 });
  assert.deepEqual(head, []);
  assert.equal(tail.length, 2);
});

test("已有的 summary 永远留在头部，不进尾部也不被丢弃", () => {
  // 第二次压缩要把「上一份摘要 + 其后的老消息」一起重新摘成一份。
  // 摘要之后的内容必须足够短，让预算判断不会先于摘要边界触发——
  // 否则「遇到 summary 就停」这条逻辑根本没被跑到，测试测不出它被删掉。
  const messages = [
    { role: "summary", content: "上一份摘要" },
    msg("user", "e".repeat(20)), msg("assistant", "f".repeat(20)),
    msg("user", "近"), msg("assistant", "近答"),
  ];
  const { head, tail } = splitForCompaction(messages, { compactAt: 1_000, charsPerToken: 4 });
  assert.equal(head.length, 1);
  assert.equal(head[0].role, "summary");
  assert.equal(tail.some((m) => m.role === "summary"), false);
});
