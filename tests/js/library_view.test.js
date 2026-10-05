import test from "node:test";
import assert from "node:assert/strict";
import {
  buildItems, clockText, DEFAULT_PREFS, filterItems, hasMedia, normalizePrefs, sortItems, specText, visibleItems,
} from "../../desk/static/js/pure/library_view.js";

const video = (extra = {}) => ({ kind: "video", status: "done", ts: "2026-09-25T10:00:00Z", output: "h3-1.mp4",
  params: { prompt: "海边", width: 768, height: 448, frames: 48, steps: 16 }, duration_s: 80, ...extra });

test("合并：历史按文件名配成品；output 与 joined_output 各占一条（B-43）；孤儿成品单独一条；新的在前", () => {
  const outputs = [
    { name: "h3-1.mp4", kind: "video", bytes: 10, ts: "2026-09-25T10:00:00Z" },
    { name: "h3-joined-1.mp4", kind: "video", bytes: 20, ts: "2026-09-25T10:05:00Z" },
    { name: "orphan.wav", kind: "music", bytes: 5, ts: "2026-09-26T09:00:00Z" },
  ];
  const items = buildItems(outputs, [video({ joined_output: "h3-joined-1.mp4", ts: "2026-09-25T10:05:00Z" })]);
  assert.deepEqual(items.map((i) => i.key), ["o:orphan.wav", "o:h3-1.mp4", "o:h3-joined-1.mp4"]);
  assert.equal(items[0].title, "orphan.wav");
  assert.equal(items[0].entry, null);
  assert.equal(items[0].plan, null);
  for (const item of items.slice(1)) {
    assert.equal(item.title, "海边");
    assert.ok(item.plan, "有历史的条目带回填计划");
  }
  assert.equal(items[1].bytes, 10);
  assert.equal(items[2].bytes, 20);
});

test("条目字段：时长、画幅、耗时、规格", () => {
  const [v] = buildItems([{ name: "h3-1.mp4", kind: "video", bytes: 10 }], [video()]);
  assert.equal(v.duration_s, 2);
  assert.equal(v.width, 768);
  assert.equal(v.height, 448);
  assert.equal(v.gen_s, 80);
  assert.equal(v.spec, "768×448 · 约 2 秒 · 16步");
  const music = { kind: "music", status: "done", ts: "t", output: "music3-1.wav",
    params: { caption: "民谣", lyrics: "啦", duration: 300 }, audio_seconds: 29.71 };
  const [m] = buildItems([{ name: "music3-1.wav", kind: "music" }], [music]);
  assert.equal(m.title, "民谣");
  assert.equal(m.duration_s, 29.71);
  assert.equal(m.width, null);
  assert.equal(m.spec, "成品 30 秒（请求 300 秒）");
  const [m2] = buildItems([], [{ ...music, audio_seconds: undefined, output: null, status: "failed" }]);
  assert.equal(m2.duration_s, 300);
  assert.equal(specText({ kind: "image", params: { width: 1024, height: 768, steps: 40, seed: 0 } }), "1024×768 · 40步 · 种子 0");
});

test("missing：完成但文件不在；失败记录不算 missing；hasMedia 只认有文件的条目", () => {
  const items = buildItems([], [
    video({ ts: "2026-09-25T10:00:00Z" }),
    video({ ts: "2026-09-24T10:00:00Z", status: "failed", output: null, error: "exit_nonzero: exit 1" }),
  ]);
  assert.equal(items[0].missing, true);
  assert.equal(items[0].output, "h3-1.mp4");
  assert.equal(hasMedia(items[0]), false);
  assert.equal(items[1].missing, false);
  assert.equal(items[1].error, "exit_nonzero: exit 1");
  assert.equal(hasMedia(items[1]), false);
  const [orphan] = buildItems([{ name: "x.bin", kind: "file", bytes: 1 }], []);
  assert.equal(hasMedia(orphan), true);
});

test("key 跨刷新稳定且同一次渲染内不重复", () => {
  const entry = { kind: "music", status: "failed", ts: "2026-09-25T10:00:00Z", output: null, params: {} };
  const once = buildItems([], [entry, { ...entry }]);
  assert.deepEqual(once.map((i) => i.key), ["h:2026-09-25T10:00:00Z:music:", "h:2026-09-25T10:00:00Z:music:#2"]);
  const again = buildItems([], [entry, { ...entry }]);
  assert.deepEqual(again.map((i) => i.key), once.map((i) => i.key));
  const [withAttempt] = buildItems([], [{ ...entry, attempt_id: "a7" }]);
  assert.equal(withAttempt.key, "h:2026-09-25T10:00:00Z:music:a7");
});

test("筛选：file 只在 all 下出现", () => {
  const items = buildItems(
    [{ name: "a.png", kind: "image" }, { name: "b.wav", kind: "music" }, { name: "c.bin", kind: "file" }], []);
  assert.deepEqual(filterItems(items, "all").length, 3);
  assert.deepEqual(filterItems(items, "image").map((i) => i.key), ["o:a.png"]);
  assert.deepEqual(filterItems(items, "music").map((i) => i.key), ["o:b.wav"]);
  assert.deepEqual(filterItems(items, "video"), []);
});

test("排序：缺值不论方向都在最后；提示词按中文排；同值按时间倒序", () => {
  const items = [
    { key: "a", ts: "2026-01-01", title: "乙", bytes: 5, kind: "image", duration_s: null, width: 2, height: 2, gen_s: 1 },
    { key: "b", ts: "2026-01-03", title: "甲", bytes: null, kind: "video", duration_s: 3, width: null, height: null, gen_s: null },
    { key: "c", ts: "2026-01-02", title: "丙", bytes: 9, kind: "image", duration_s: 1, width: 4, height: 4, gen_s: 1 },
  ];
  const keys = (sort) => sortItems(items, sort).map((i) => i.key);
  assert.deepEqual(keys({ key: "bytes", dir: "desc" }), ["c", "a", "b"]);
  assert.deepEqual(keys({ key: "bytes", dir: "asc" }), ["a", "c", "b"]);
  assert.deepEqual(keys({ key: "duration", dir: "asc" }), ["c", "b", "a"]);
  assert.deepEqual(keys({ key: "dims", dir: "desc" }), ["c", "a", "b"]);
  assert.deepEqual(keys({ key: "gen", dir: "asc" }), ["c", "a", "b"], "同值（1）按时间倒序");
  assert.deepEqual(keys({ key: "ts", dir: "desc" }), ["b", "c", "a"]);
  assert.deepEqual(keys({ key: "title", dir: "asc" }), ["c", "b", "a"], "中文排序：丙 甲 乙");
  assert.deepEqual(keys({ key: "nonsense", dir: "desc" }), ["b", "c", "a"], "未知键按时间倒序");
});

test("visibleItems 先筛后排", () => {
  const items = buildItems([{ name: "a.png", kind: "image", bytes: 1, ts: "2026-01-01" },
    { name: "b.png", kind: "image", bytes: 9, ts: "2026-01-02" }, { name: "c.wav", kind: "music", bytes: 5 }], []);
  assert.deepEqual(visibleItems(items, { filter: "image", sort: { key: "bytes", dir: "asc" } }).map((i) => i.key),
    ["o:a.png", "o:b.png"]);
});

test("偏好归一：非法值回落默认，大小夹在 140–320", () => {
  assert.deepEqual(normalizePrefs(null), { view: "grid", filter: "all", thumb: 200, sort: { key: "ts", dir: "desc" } });
  assert.deepEqual(normalizePrefs("garbage"), normalizePrefs(null));
  assert.deepEqual(normalizePrefs({ view: "table", filter: "music", thumb: 999, sort: { key: "bytes", dir: "asc" } }),
    { view: "table", filter: "music", thumb: 320, sort: { key: "bytes", dir: "asc" } });
  assert.deepEqual(normalizePrefs({ view: "column", filter: "file", thumb: "x", sort: { key: "x", dir: "up" } }), normalizePrefs(null));
  assert.equal(normalizePrefs({ thumb: 10 }).thumb, 140);
  assert.equal(DEFAULT_PREFS.view, "grid");
});

test("clockText", () => {
  assert.equal(clockText(0), "0:00");
  assert.equal(clockText(29.71), "0:30");
  assert.equal(clockText(125), "2:05");
});
