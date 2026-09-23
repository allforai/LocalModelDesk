import test from "node:test";
import assert from "node:assert/strict";
import { charsPerToken, needsCompaction, splitForCompaction, maybeCompact } from "../../desk/static/js/pure/compaction.js";

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

test("skill 占掉的窗口要从尾部预算里扣掉", () => {
  // R-skill-12：splitForCompaction 算的是「历史原文最多留多少」，而 skill 占着同一个
  // 窗口又不在 messages 里。不扣掉它，压完仍然超，下一轮再压——大 skill 下收敛不了。
  const messages = Array.from({ length: 20 }, (_, i) => ({ role: "user", content: "x".repeat(100) }));
  const options = { compactAt: 1000, charsPerToken: 4 };
  const without = splitForCompaction(messages, options);
  const withSkill = splitForCompaction(messages, { ...options, skillChars: 1500 });
  assert.ok(withSkill.tail.length < without.tail.length,
    "带着 skill 时尾部没有变短——预算没扣掉 skill");
});

test("skill 大到吃光预算时，仍然保留最近一轮完整问答", () => {
  // 预算被扣成负数不能变成「一条都不留」：用户眼前正在看的那一轮再紧也不能摘掉。
  const messages = [
    { role: "user", content: "老的" },
    { role: "assistant", content: "老答" },
    { role: "user", content: "最近的问" },
    { role: "assistant", content: "最近的答" },
  ];
  const { tail } = splitForCompaction(messages, {
    compactAt: 100, charsPerToken: 4, skillChars: 100000,
  });
  assert.deepEqual(tail.map((m) => m.content), ["最近的问", "最近的答"]);
});

test("没有 skill 时切分结果和以前一模一样", () => {
  const messages = Array.from({ length: 10 }, () => ({ role: "user", content: "y".repeat(50) }));
  const options = { compactAt: 800, charsPerToken: 4 };
  assert.deepEqual(splitForCompaction(messages, options),
                   splitForCompaction(messages, { ...options, skillChars: 0 }));
});

test("Math.max 防止负预算把所有历史扫进头部", () => {
  // 空消息（如中断的助手回答）加超大 skill 时，预算是负数。
  // 没有 Math.max 的话，used=0 时 0 > -999 成立，loop 立即 break，
  // 所有历史都进头部交给摘要器——真实的不收敛问题。
  // 用户看不到这些空消息（wireMessages 过滤掉了），但 session.messages 里有它们。
  const messages = [
    { role: "assistant", content: "" },
    { role: "assistant", content: "" },
  ];
  const { head, tail } = splitForCompaction(messages, {
    compactAt: 10, charsPerToken: 1, skillChars: 999,
  });
  assert.equal(tail.length, 2, "尾部应该有两条空消息");
  assert.equal(head.length, 0, "头部应该为空，没有历史需要摘要");
});

test("maybeCompact 透传 skillChars 给 splitForCompaction", async () => {
  // maybeCompact 若没有透传 skillChars，所有的 skill 防护都失效：
  // 单测对 splitForCompaction 的验证在生产里无效。
  const messages = Array.from({ length: 20 }, () => ({ role: "user", content: "x".repeat(100) }));

  // 有 skill 时头部应该更多（更多历史需要压缩）
  const withoutSkill = await maybeCompact(messages, {
    promptTokens: 2000, sentChars: 4000, compactAt: 1000, pressure: "normal",
    summarise: async (head) => head.length.toString(),
  });

  const withSkill = await maybeCompact(messages, {
    promptTokens: 2000, sentChars: 4000, compactAt: 1000, pressure: "normal",
    summarise: async (head) => head.length.toString(),
    skillChars: 1500,
  });

  // 若没有透传 skillChars，两个结果中 head 大小相同（都没有扣掉 skill）。
  // 若正确透传了，withSkill 的 head 更大（skill 吃掉了预算）。
  if (withoutSkill.compacted && withSkill.compacted) {
    // 都压缩了的情况
    assert.ok(withSkill.messages[0].replaced_through > withoutSkill.messages[0].replaced_through,
      "有 skill 时应该压缩更多消息（head 更大），说明 skillChars 被透传了");
  }
});
