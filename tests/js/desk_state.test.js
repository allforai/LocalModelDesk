import test from "node:test";
import assert from "node:assert/strict";
import { renderState, heavyAvailability } from "../../desk/static/js/pure/desk_state.js";

const GB = 1024 ** 3;
const idle = { holder: null, media_busy: false, can_start: { ok: true } };
const snapA = { total_bytes: 137438953472, used_bytes: 96 * GB, available_bytes: 32 * GB, pressure: "warn" };
const snapB = { total_bytes: 271437611008, used_bytes: 10 * GB, available_bytes: 240 * GB, pressure: "normal" };

test("内存数字来自快照输入而非写死常量（census A09）：两组快照输出各含各的数字", () => {
  const a = renderState(idle, snapA);
  assert.ok(a.memText.includes("96"));
  assert.ok(a.memText.includes("128"));
  assert.ok(a.memText.includes("32"));
  const b = renderState(idle, snapB);
  assert.ok(b.memText.includes("253"));
  assert.ok(b.memText.includes("240"));
  assert.notEqual(a.memText, b.memText);
});

test("三种持有者文案", () => {
  const busyState = (holder) => ({ holder, media_busy: holder?.kind !== "llm", can_start: { ok: false, reason: "media_busy" } });
  assert.equal(renderState(idle, snapA).holderText, "内存里：无");
  assert.equal(renderState(busyState({ kind: "llm", label: "glm" }), snapA).holderText, "内存里：glm");
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

test("拒绝码翻译成中文原因，llm_already_held 指向卸载动作", () => {
  const state = { can_start: { llm: { ok: false, reason: { code: "llm_already_held" } }, media: { ok: true } } };
  assert.deepEqual(heavyAvailability(state, "llm"), { allowed: false, code: "llm_already_held", reason: "已有聊天模型驻留：先卸载，再加载另一个" });
  const evicted = { can_start: { llm: { ok: false, reason: { code: "evict_failed" } } } };
  assert.equal(heavyAvailability(evicted, "llm").reason, "让出内存失败，请重试或先手动卸载");
});

test("insufficient_budget 有中文兜底文案，不直接把错误码显示给用户（R-budget-13）", () => {
  const state = { can_start: { llm: { ok: false, reason: { code: "insufficient_budget" } } } };
  const result = heavyAvailability(state, "llm");
  assert.equal(result.reason, "内存不够，先卸掉一个再来");
  assert.notEqual(result.reason, "insufficient_budget");
});

test("快照缺失如实说不可用，不编数字", () => {
  assert.equal(renderState(idle, null).memText, "内存读数不可用");
});

test("状态条内存文案标 GiB", () => {
  const view = renderState({ can_start: { llm: { ok: true } } }, { total_bytes: 128 * 1024 ** 3, used_bytes: 64 * 1024 ** 3, available_bytes: 64 * 1024 ** 3 });
  assert.equal(view.memText, "已用 64 / 总 128 GiB（可用 64 GiB）");  // N3：与菜单栏同一取整
});

test("状态条四格带字段名，下载中并入媒体格并转为 busy", () => {
  const idle = renderState({ holder: null, media_busy: false, can_start: { llm: { ok: true } } }, null, { state: "running", key: "gemma" });
  assert.equal(idle.holderText, "内存里：无");
  assert.equal(idle.mediaText, "媒体：空闲 · 下载中 gemma");
  assert.equal(idle.tone, "busy");
  const held = renderState({ holder: { kind: "llm", label: "glm" }, media_busy: false, can_start: { llm: { ok: false, reason: { code: "llm_already_held" } }, media: { ok: true } } }, null);
  assert.equal(held.holderText, "内存里：glm");
  assert.equal(held.nextText, "可开下一件重活");
});

test("下一件重活：图标与 ok 位随可否开工变化，不随 tone 变化（F1/F2）", () => {
  const ok = renderState(idle, snapA);
  assert.equal(ok.nextOk, true);
  assert.equal(ok.nextIcon, "check");
  const busy = renderState(
    { holder: { kind: "video", label: "3" }, media_busy: true, can_start: { ok: false, reason: "media_busy" } }, snapA);
  assert.equal(busy.nextOk, false);
  assert.equal(busy.nextIcon, "x");
  // downloading keeps tone busy but the next-step item stays ok
  const dl = renderState(idle, snapA, { state: "running", key: "superqwen" });
  assert.equal(dl.tone, "busy");
  assert.equal(dl.nextOk, true);
  assert.equal(dl.nextIcon, "check");
});

test("状态条用显示名而不是 key（F11）", () => {
  const names = { glm: "GLM 4.7 Flash 越狱 4bit", superqwen: "SuperQwen3.8 27B 越狱 4bit" };
  const loaded = { holder: { kind: "llm", label: "glm" }, media_busy: false, can_start: { ok: false, reason: "llm_already_held" } };
  assert.equal(renderState(loaded, snapA, null, names).holderText, "内存里：GLM 4.7 Flash 越狱 4bit");
  assert.equal(renderState(idle, snapA, { state: "running", key: "superqwen" }, names).mediaText, "媒体：空闲 · 下载中 SuperQwen3.8 27B 越狱 4bit");
  assert.equal(renderState(loaded, snapA).holderText, "内存里：glm");
});

test("heavyAvailability 透出原因码", () => {
  const held = { holder: { kind: "llm", label: "glm" }, media_busy: false, can_start: { llm: { ok: false, reason: { code: "llm_already_held" } } } };
  assert.equal(heavyAvailability(held, "llm").code, "llm_already_held");
  assert.equal(heavyAvailability(idle, "llm").code, null);
});
