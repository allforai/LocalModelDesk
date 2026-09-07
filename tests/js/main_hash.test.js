import test from "node:test";
import assert from "node:assert/strict";
import { tabFromHash } from "../../desk/static/js/pure/tab_hash.js";

test("hash 解析成合法 tab，否则回到聊天", () => {
  assert.equal(tabFromHash("#tab=music"), "music");
  assert.equal(tabFromHash("#tab=bogus"), "chat");
  assert.equal(tabFromHash(""), "chat");
});
