import test from "node:test";
import assert from "node:assert/strict";
import { formatBytes, formatPercent, formatDuration, formatRate, formatTimestamp, formatMemoryLine }
  from "../../desk/static/js/pure/format.js";

test("formatBytes：GiB 一位小数、MiB/KiB 取整、非法值如实给占位", () => {
  assert.equal(formatBytes(0), "0 B");
  assert.equal(formatBytes(512), "512 B");
  assert.equal(formatBytes(2048), "2 KiB");
  assert.equal(formatBytes(820 * 1024 ** 2), "820 MiB");
  assert.equal(formatBytes(103 * 1024 ** 3), "103.0 GiB");
  assert.equal(formatBytes(-1), "—");
  assert.equal(formatBytes(NaN), "—");
});

test("formatBytes 用 GiB/MiB 标签，与 1024 进制一致", () => {
  assert.equal(formatBytes(16878224220), "15.7 GiB");
  assert.equal(formatBytes(5 * 1024 ** 2), "5 MiB");
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
  assert.equal(formatRate(2 * 1024 ** 2), "2 MiB/s");
  assert.equal(formatRate(0), "—");
});

test("formatMemoryLine 取整到 GiB，与菜单栏 memoryMenuTitle 同一进制/同一取整（N3）", () => {
  const GB = 1024 ** 3;
  assert.equal(formatMemoryLine(58.2 * GB, 128 * GB, 69.8 * GB), "已用 58 / 总 128 GiB（可用 70 GiB）");
  assert.equal(formatMemoryLine(0, 128 * GB, 128 * GB), "已用 0 / 总 128 GiB（可用 128 GiB）");
  // 同屏抖动过的三处读数（79.0/79.4/79.2）取整后必须一致
  assert.equal(formatMemoryLine(79.0 * GB, 128 * GB, 49 * GB), "已用 79 / 总 128 GiB（可用 49 GiB）");
  assert.equal(formatMemoryLine(79.4 * GB, 128 * GB, 49 * GB), "已用 79 / 总 128 GiB（可用 49 GiB）");
  assert.equal(formatMemoryLine(79.2 * GB, 128 * GB, 49 * GB), "已用 79 / 总 128 GiB（可用 49 GiB）");
});

test("formatTimestamp 截到分钟", () => {
  assert.equal(formatTimestamp("2026-08-31T10:11:12"), "2026-08-31 10:11");
  assert.equal(formatTimestamp(null), "—");
});
