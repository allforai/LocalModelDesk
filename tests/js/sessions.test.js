import test from "node:test";
import assert from "node:assert/strict";
import { displayTitle, sortSessions }
  from "../../desk/static/js/pure/sessions.js";

test("sortSessions：按 updated 降序且不修改原数组", () => {
  const sessions = [
    { id: "old", updated: "2026-08-31T09:00:00Z" },
    { id: "new", updated: "2026-08-31T11:00:00Z" },
    { id: "middle", updated: "2026-08-31T10:00:00Z" },
  ];

  const sorted = sortSessions(sessions);

  assert.deepEqual(sorted.map(({ id }) => id), ["new", "middle", "old"]);
  assert.deepEqual(sessions.map(({ id }) => id), ["old", "new", "middle"]);
});

test("displayTitle：默认标题会由首条用户消息派生，超出 24 字加省略号", () => {
  const content = "一二三四五六七八九十一二三四五六七八九十一二三四五";
  assert.equal(displayTitle({
    title: "新会话",
    messages: [{ role: "assistant", content: "忽略" }, { role: "user", content }],
  }), `${content.slice(0, 24)}…`);
  assert.equal(displayTitle({ title: "已重命名", messages: [] }), "已重命名");
  assert.equal(displayTitle({ title: "", messages: [] }), "新会话");
});
