import test from "node:test";
import assert from "node:assert/strict";
import { createStore } from "../../desk/static/js/store.js";

test("set 合并补丁并通知订阅者；退订后不再通知", () => {
  const store = createStore({ a: 1 });
  const seen = [];
  const unsubscribe = store.subscribe((state) => seen.push(state));
  store.set({ b: 2 });
  assert.deepEqual(store.get(), { a: 1, b: 2 });
  assert.deepEqual(seen, [{ a: 1, b: 2 }]);
  unsubscribe();
  store.set({ c: 3 });
  assert.equal(seen.length, 1);
  assert.deepEqual(store.get(), { a: 1, b: 2, c: 3 });
});
