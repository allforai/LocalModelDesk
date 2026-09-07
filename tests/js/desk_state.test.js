import test from "node:test";
import assert from "node:assert/strict";
import { renderState } from "../../desk/static/js/pure/desk_state.js";

const GB = 1024 ** 3;
const idle = { holder: null, media_busy: false, can_start: { ok: true } };
const snapA = { total_bytes: 137438953472, used_bytes: 96 * GB, available_bytes: 32 * GB, pressure: "warn" };
const snapB = { total_bytes: 271437611008, used_bytes: 10 * GB, available_bytes: 240 * GB, pressure: "normal" };

test("内存数字来自快照输入而非写死常量（census A09）：两组快照输出各含各的数字", () => {
  const a = renderState(idle, snapA);
  assert.ok(a.memText.includes("96.0"));
  assert.ok(a.memText.includes("128.0"));
  assert.ok(a.memText.includes("32.0"));
  const b = renderState(idle, snapB);
  assert.ok(b.memText.includes("252.8"));
  assert.ok(b.memText.includes("240.0"));
  assert.notEqual(a.memText, b.memText);
});

test("三种持有者文案", () => {
  const busyState = (holder) => ({ holder, media_busy: holder?.kind !== "llm", can_start: { ok: false, reason: "media_busy" } });
  assert.equal(renderState(idle, snapA).holderText, "空闲");
  assert.equal(renderState(busyState({ kind: "llm", label: "glm" }), snapA).holderText, "LLM：glm");
  assert.equal(renderState(busyState({ kind: "video", label: "3" }), snapA).holderText, "视频生成中");
  assert.equal(renderState(busyState({ kind: "music", label: "4" }), snapA).holderText, "音乐生成中");
});

test("可/不可开下一件 + tone", () => {
  const ok = renderState(idle, snapA);
  assert.equal(ok.nextText, "可开下一件重活");
  assert.equal(ok.tone, "ok");
  const busy = renderState(
    { holder: { kind: "video", label: "3" }, media_busy: true, can_start: { ok: false, reason: "media_busy" } },
    snapA);
  assert.equal(busy.nextText, "不可：媒体作业进行中");
  assert.equal(busy.mediaText, "媒体：生成中");
  assert.equal(busy.tone, "busy");
});

test("仲裁器的按种类拒绝会在状态条显示拒绝原因", () => {
  const view = renderState({
    holder: { kind: "video", label: "3" },
    media_busy: true,
    can_start: { media: { ok: false, reason: { code: "media_busy", message: "视频作业进行中" } } },
  }, snapA);
  assert.equal(view.nextText, "不可：媒体作业进行中");
});

test("未知拒绝码原样透出，不吞", () => {
  const v = renderState({ holder: null, media_busy: false, can_start: { ok: false, reason: "weird_code" } }, snapA);
  assert.ok(v.nextText.includes("weird_code"));
});

test("快照缺失如实说不可用，不编数字", () => {
  assert.equal(renderState(idle, null).memText, "内存读数不可用");
});

test("状态条内存文案标 GiB", () => {
  const view = renderState({ can_start: { llm: { ok: true } } }, { total_bytes: 128 * 1024 ** 3, used_bytes: 64 * 1024 ** 3, available_bytes: 64 * 1024 ** 3 });
  assert.equal(view.memText, "已用 64.0 / 总 128.0 GiB（可用 64.0 GiB）");
});
