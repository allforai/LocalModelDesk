import test from "node:test";
import assert from "node:assert/strict";
import { isDrawerCloseKey } from "../../desk/static/js/pure/drawer.js";

test("Esc 关闭设置抽屉，其他按键不影响", () => {
  assert.equal(isDrawerCloseKey("Escape"), true);
  assert.equal(isDrawerCloseKey("Enter"), false);
  assert.equal(isDrawerCloseKey("a"), false);
});
