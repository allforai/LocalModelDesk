import test from "node:test";
import assert from "node:assert/strict";
import { createStore } from "../../desk/static/js/store.js";

test("set 合并补丁而不抛出（get/subscribe 已删：零调用点，F13）", () => {
  const store = createStore({ a: 1 });
  assert.doesNotThrow(() => store.set({ b: 2 }));
  assert.doesNotThrow(() => store.set({ c: 3 }));
});
