import test from "node:test";
import assert from "node:assert/strict";
import { rowView, statusBadge } from "../../desk/static/js/pure/model_status.js";

const entry = { key: "glm", name: "GLM", gb: 68.4, vision: false };
const base = {
  key: "glm", state: "present", percent: 100,
  bytes_expected: 73446916096, bytes_local: 73446916096, disk_bytes: 73446916096, gaps: [],
};

test("present：徽标「齐」、pct 100、只有删除（R-ui-05）", () => {
  const v = rowView(entry, base);
  assert.equal(v.badge, "齐");
  assert.equal(v.pct, 100);
  assert.deepEqual(v.actions, ["delete"]);
  assert.equal(v.sizeText, "68.4 GiB");
  assert.equal(v.diskText, "68.4 GiB");
});

test("size text 在 bytes_expected 缺失时回退到目录估计", () => {
  const v = rowView(entry, { ...base, bytes_expected: undefined });
  assert.equal(v.sizeText, "68.4 GiB（目录）");
});

test("partial：「一半 N%」按字节 + 续传/删除 + 缺失清单透传", () => {
  const gaps = [{ path: "a.safetensors", expected_size: 100, local_size: 40 }];
  const v = rowView(entry, { ...base, state: "partial", percent: 41.7, gaps });
  assert.equal(v.badge, "一半 42%");
  assert.deepEqual(v.actions, ["resume", "delete"]);
  assert.deepEqual(v.missing, gaps);
});

test("missing：「没下」+ 下载", () => {
  const v = rowView(entry, { ...base, state: "missing", percent: 0, disk_bytes: 0 });
  assert.equal(v.badge, "没下");
  assert.equal(v.pct, 0);
  assert.deepEqual(v.actions, ["download"]);
});

test("unknown：中文说明原因，无控件", () => {
  const v = rowView(entry, { ...base, state: "unknown", percent: 0, reason: "manifest_unavailable" });
  assert.equal(v.badge, "未知：拿不到文件清单");
  assert.deepEqual(v.actions, []);
});

test("本项下载中：只有取消", () => {
  const v = rowView(entry, { ...base, state: "partial", percent: 40 },
    { state: "running", key: "glm" });
  assert.deepEqual(v.actions, ["cancel"]);
});

test("别项下载中：下载/续传禁用并注明原因（R-resources-09 前端侧）", () => {
  const v = rowView(entry, { ...base, state: "missing", percent: 0 },
    { state: "running", key: "llama70" });
  assert.deepEqual(v.actions, ["download"]);
  assert.equal(v.downloadDisabled, true);
  assert.ok(v.downloadDisabledReason.includes("一个下载"));
});

test("statusBadge：present/partial/missing/unknown 四态文案与种类，供聊天页下拉复用（不重新拼一套）", () => {
  assert.deepEqual(statusBadge(base), { badge: "齐", badgeKind: "ok" });
  assert.deepEqual(statusBadge({ ...base, state: "partial", percent: 41.7 }), { badge: "一半 42%", badgeKind: "busy" });
  assert.deepEqual(statusBadge({ ...base, state: "missing", percent: 0 }), { badge: "没下", badgeKind: "none" });
  assert.deepEqual(
    statusBadge({ ...base, state: "unknown", percent: 0, reason: "manifest_unavailable" }),
    { badge: "未知：拿不到文件清单", badgeKind: "unknown" },
  );
  assert.deepEqual(
    statusBadge({ ...base, state: "unknown", percent: 0 }),
    { badge: "未知：拿不到文件清单", badgeKind: "unknown" },
  );
  assert.deepEqual(
    statusBadge({ ...base, state: "unknown", percent: 0, reason: "boom" }),
    { badge: "未知：boom", badgeKind: "unknown" },
  );
});

test("取消后的一半：说明已下多少可续传；旧残片单独说明", () => {
  const v = rowView(entry, { ...base, state: "partial", percent: 21.2, resumable_bytes: 3 * 1024 ** 3, stale_bytes: 0 });
  assert.equal(v.badge, "一半 21%");
  assert.equal(v.note, "已下 3.0 GiB 可续传");
  const w = rowView(entry, { ...base, state: "partial", percent: 5, resumable_bytes: 0, stale_bytes: 2 * 1024 ** 3 });
  assert.equal(w.note, "另有 2.0 GiB 旧版残片无法续传，开始下载时会清理");
  const idle = rowView(entry, { ...base, state: "present", percent: 100 });
  assert.equal(idle.note, null);
});
