import test from "node:test";
import assert from "node:assert/strict";
import { needsWarning } from "../../desk/static/js/pure/mem_warn.js";

const GB = 1024 ** 3;
const snap = { total_bytes: 128 * GB, used_bytes: 60 * GB, available_bytes: 68 * GB };

test("装得下：不警", () => {
  assert.deepEqual(needsWarning(40 * GB, snap), { warn: false, message: null });
});

test("装不下：警且 message 含双方数字", () => {
  const { warn, message } = needsWarning(103 * GB, snap);
  assert.equal(warn, true);
  assert.ok(message.includes("103.0 GB"));
  assert.ok(message.includes("68.0 GB"));
});

test("边界恰好相等也警（A2：宁可略敏感）", () => {
  assert.equal(needsWarning(68 * GB, snap).warn, true);
});

test("快照缺失：不弹窗（权威判断在 arbiter R-arbiter-07，这层只是触发条件）", () => {
  assert.equal(needsWarning(103 * GB, null).warn, false);
});
