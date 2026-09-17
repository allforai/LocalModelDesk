import test from "node:test";
import assert from "node:assert/strict";
import { initialStream, reduceChunk, wireMessages } from "../../desk/static/js/pure/chat_stream.js";

test("delta 正文与思考分流累加，不混流（R-ui-02）", () => {
  let s = initialStream();
  s = reduceChunk(s, '{"type":"delta","text":null,"reasoning":"想"}');
  s = reduceChunk(s, '{"type":"delta","text":"你","reasoning":null}');
  s = reduceChunk(s, '{"type":"delta","text":"好","reasoning":"想2"}');
  assert.equal(s.content, "你好");
  assert.equal(s.reasoning, "想想2");
  assert.equal(s.done, false);
  assert.equal(s.error, null);
});

test("done 事件置 done 并携带 usage/finish_reason", () => {
  const s = reduceChunk(initialStream(),
    '{"type":"done","usage":{"total_tokens":9},"finish_reason":"stop"}');
  assert.equal(s.done, true);
  assert.deepEqual(s.usage, { total_tokens: 9 });
  assert.equal(s.finishReason, "stop");
});

test("[DONE] 哨兵同样置 done", () => {
  assert.equal(reduceChunk(initialStream(), "[DONE]").done, true);
});

test("error 事件置 error，其后的行不再累加", () => {
  let s = reduceChunk(initialStream(),
    '{"type":"error","code":"no_model_loaded","message":"没有已加载的模型"}');
  assert.equal(s.error.code, "no_model_loaded");
  assert.equal(s.error.message, "没有已加载的模型");
  s = reduceChunk(s, '{"type":"delta","text":"x","reasoning":null}');
  assert.equal(s.content, "");
});

test("裸 {error:…} 信封也识别", () => {
  const s = reduceChunk(initialStream(), '{"error":{"code":"boom","message":"炸"}}');
  assert.equal(s.error.code, "boom");
});

test("坏 JSON 行跳过且不中断", () => {
  let s = reduceChunk(initialStream(), "{not json");
  assert.equal(s.error, null);
  s = reduceChunk(s, '{"type":"delta","text":"好","reasoning":null}');
  assert.equal(s.content, "好");
});

test("wireMessages 只发 role/content，并跳过没有正文的中断回答", async () => {
  const { wireMessages } = await import("../../desk/static/js/pure/chat_stream.js");
  const history = [
    { role: "user", content: "问一" },
    { role: "assistant", content: "答一", reasoning: "想", thinking_s: 3 },
    { role: "user", content: "问二" },
    { role: "assistant", content: "", reasoning: "想了一半", interrupted: { code: "evicted", message: "让出内存" } },
    { role: "user", content: "问三" },
    { role: "assistant", content: "半句", interrupted: { code: "upstream_error", message: "断流" } },
  ];
  assert.deepEqual(wireMessages(history), [
    { role: "user", content: "问一" },
    { role: "assistant", content: "答一" },
    { role: "user", content: "问二" },
    { role: "user", content: "问三" },
    { role: "assistant", content: "半句" },
  ]);
});

test("摘要以 system 角色发送——模型的 chat template 只认三种角色", () => {
  const wired = wireMessages([
    { role: "summary", content: "前情", replaced_through: 1 },
    { role: "user", content: "问" },
    { role: "assistant", content: "答" },
    { role: "user", content: "再问" },
  ]);
  assert.equal(wired[0].role, "system");
  assert.match(wired[0].content, /前情/);
});

test("被摘要替代的消息不发送，但摘要之后的照发", () => {
  // replaced_through 是「新数组里被替代的最后一条」的下标：summary 自己在下标 0，
  // 两条被替代的消息（被替代的问/答）分别在下标 1、2，所以是 2，不是 1——
  // 计划 Task 2 Step 1 给的样例数据在这里写成了 1，与 Task 4 明文约定的语义
  // （replaced_through = head.length，off-by-one 是全计划最容易写错的地方）
  // 自相矛盾，已按 Task 4 的语义改正，见 deviations。
  const wired = wireMessages([
    { role: "summary", content: "前情", replaced_through: 2 },
    { role: "user", content: "被替代的问" },
    { role: "assistant", content: "被替代的答" },
    { role: "user", content: "还在的问" },
  ]);
  assert.deepEqual(wired.map((m) => m.content).slice(1), ["还在的问"]);
});

test("摘要内容带前缀，模型才不会把它当成用户说过的话", () => {
  const [first] = wireMessages([{ role: "summary", content: "前情", replaced_through: 0 }]);
  assert.notEqual(first.content, "前情");
  assert.match(first.content, /前情/);
});

test("没有摘要时行为一字不变", () => {
  const before = [
    { role: "user", content: "问" },
    { role: "assistant", content: "答" },
  ];
  assert.deepEqual(wireMessages(before), [
    { role: "user", content: "问" },
    { role: "assistant", content: "答" },
  ]);
});

test("中断且无内容的助手消息仍然被丢掉", () => {
  // 既有行为，不能在这次改动里丢失。
  const wired = wireMessages([
    { role: "user", content: "问" },
    { role: "assistant", content: "", interrupted: { code: "stopped", message: "x" } },
  ]);
  assert.equal(wired.length, 1);
});
