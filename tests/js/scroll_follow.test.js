import test from "node:test";
import assert from "node:assert/strict";
import { shouldStickToBottom } from "../../desk/static/js/pure/scroll_follow.js";

test("贴着底时跟随", () => {
  assert.equal(shouldStickToBottom({ scrollTop: 900, clientHeight: 400, scrollHeight: 1300 }), true);
});

test("差几像素仍算贴底（键盘滚动与亚像素）", () => {
  assert.equal(shouldStickToBottom({ scrollTop: 880, clientHeight: 400, scrollHeight: 1300 }), true);
});

test("用户翻上去了就不许拽回来", () => {
  assert.equal(shouldStickToBottom({ scrollTop: 200, clientHeight: 400, scrollHeight: 1300 }), false);
});

test("内容还没长到要滚，一直算贴底", () => {
  assert.equal(shouldStickToBottom({ scrollTop: 0, clientHeight: 400, scrollHeight: 400 }), true);
});

test("读不到尺寸时宁可跟随，不要把人卡在半空", () => {
  assert.equal(shouldStickToBottom({}), true);
});
