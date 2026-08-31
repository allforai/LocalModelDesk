import test from "node:test";
import assert from "node:assert/strict";
import { formatBytes, formatPercent, formatDuration, formatRate, formatTimestamp }
  from "../../desk/static/js/pure/format.js";

test("formatBytes：GB 一位小数、MB/KB 取整、非法值如实给占位", () => {
  assert.equal(formatBytes(0), "0 B");
  assert.equal(formatBytes(512), "512 B");
  assert.equal(formatBytes(2048), "2 KB");
  assert.equal(formatBytes(820 * 1024 ** 2), "820 MB");
  assert.equal(formatBytes(103 * 1024 ** 3), "103.0 GB");
  assert.equal(formatBytes(-1), "—");
  assert.equal(formatBytes(NaN), "—");
});

test("formatPercent 取整并夹在 0–100", () => {
  assert.equal(formatPercent(37.4), "37%");
  assert.equal(formatPercent(99.6), "100%");
  assert.equal(formatPercent(-3), "0%");
  assert.equal(formatPercent(NaN), "0%");
});

test("formatDuration：秒/分秒/时分", () => {
  assert.equal(formatDuration(45), "45秒");
  assert.equal(formatDuration(125), "2分05秒");
  assert.equal(formatDuration(3720), "1时02分");
  assert.equal(formatDuration(-1), "—");
});

test("formatRate：字节速率", () => {
  assert.equal(formatRate(2 * 1024 ** 2), "2 MB/s");
  assert.equal(formatRate(0), "—");
});

test("formatTimestamp 截到分钟", () => {
  assert.equal(formatTimestamp("2026-08-31T10:11:12"), "2026-08-31 10:11");
  assert.equal(formatTimestamp(null), "—");
});
