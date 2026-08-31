import test from "node:test";
import assert from "node:assert/strict";
import { initialStream, reduceChunk } from "../../desk/static/js/pure/chat_stream.js";

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
