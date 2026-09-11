import test from "node:test";
import assert from "node:assert/strict";
import { tabFromHash, initialTab } from "../../desk/static/js/pure/tab_hash.js";

test("hash 解析成合法 tab，否则回到聊天", () => {
  assert.equal(tabFromHash("#tab=music"), "music");
  assert.equal(tabFromHash("#tab=bogus"), "chat");
  assert.equal(tabFromHash(""), "chat");
});

test("a fresh load with no hash always lands on chat", () => {
  assert.equal(initialTab(""), "chat");
  assert.equal(initialTab("#"), "chat");
  assert.equal(initialTab("#tab=music"), "music");
  assert.equal(initialTab("#tab=nonsense"), "chat");
});
