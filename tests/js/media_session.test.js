import test from "node:test";
import assert from "node:assert/strict";
import {
  attemptView, autoTitle, availability, deleteMessage, orderSessions, pickCurrent, randomSeed,
  runningLabel, runningSessionId, sessionMeta, sessionTitle, startErrorText, attemptLabel, chainOf,
} from "../../desk/static/js/pure/media_session.js";

const ready = { listState: "ready", currentId: "s1", current: { attempts: [] }, sessions: [{ id: "s1" }, { id: "s2", title: "旧歌", running: true }],
  allowed: true, busyReason: "", runtimeReason: "", modelReason: "" };

test("availability keeps the image wording with noun 图片 and says 歌曲 for music", () => {
  const job = { kind: "image", status: "running", session_id: "s2" };
  assert.equal(availability({ ...ready, job }, { noun: "图片" }).reason, "「旧歌」正在生成图片");
  const music = { kind: "music", status: "running", session_id: "s2" };
  assert.equal(availability({ ...ready, job: music, kind: "music" }, { noun: "歌曲" }).reason, "「旧歌」正在生成歌曲");
});

test("runningSessionId only follows jobs of its own kind", () => {
  const sessions = [{ id: "s1" }];
  assert.equal(runningSessionId({ kind: "music", status: "running", session_id: "s1" }, sessions, "image"), null);
  assert.equal(runningSessionId({ kind: "music", status: "running", session_id: "s1" }, sessions, "music"), "s1");
});

test("deleteMessage names the noun", () => {
  assert.equal(deleteMessage({ title: "晚风" }, { noun: "歌曲" }),
    "确定删除「晚风」？只删除这个会话分组，其中的歌曲仍保留在素材库。");
  assert.match(deleteMessage({ title: "猫", running: true }, { noun: "图片" }), /这个会话正在生成图片，生成会继续完成，图片会进入素材库/);
});

test("chainOf walks continues back and reports a gap", () => {
  const attempts = [{ id: "a" }, { id: "b", continues: "a" }, { id: "c", continues: "b" }, { id: "d", continues: "zz" }];
  assert.deepEqual(chainOf(attempts[2], attempts).items.map((x) => x.id), ["a", "b", "c"]);
  assert.equal(chainOf(attempts[2], attempts).gap, false);
  const broken = chainOf(attempts[3], attempts);
  assert.deepEqual(broken.items.map((x) => x.id), ["d"]); assert.equal(broken.gap, true);
});

// ---- 以下用例从 tests/js/image_session.test.js 移入（断言不变，只调整 import 与新增的
// {noun}/kind 参数），覆盖搬到 pure/media_session.js 的函数。----

test("D-11 标题截断：空白折叠、去首尾空白、超过 24 字加省略号（与聊天同规则）", () => {
  assert.equal(autoTitle("  一只橘猫\n\n坐在  窗边 "), "一只橘猫 坐在 窗边");
  const long = "一只橘猫坐在窗边，午后阳光，细腻的水彩插画，暖色调，柔和光线";
  assert.equal(autoTitle(long), `${long.slice(0, 24)}…`);
  assert.equal(autoTitle("a".repeat(24)), "a".repeat(24));
});

test("会话列表文案：标题、N 次生成 · HH:MM、坏文件（D-77、§7.2）", () => {
  assert.equal(sessionTitle({ title: "橘猫" }), "橘猫");
  assert.equal(sessionTitle({ title: "" }), "新会话");
  assert.equal(sessionTitle({ id: "x", corrupt: true }), "无法读取的会话");
  assert.equal(sessionMeta({ attempt_count: 3, updated: "2026-09-24T14:05:40" }), "3 次生成 · 14:05");
  assert.equal(sessionMeta({ attempt_count: 0, updated: "2026-09-24T09:01:00" }), "0 次生成 · 09:01");
  assert.equal(sessionMeta({ id: "x", corrupt: true }), "文件已损坏");
});

test("卡片标题行：第 N 次 · HH:MM；生成中沿用 jobview 时长文案（D-73、D-81）", () => {
  assert.equal(attemptLabel(0, { ts: "2026-09-24T14:02:11" }), "第 1 次 · 14:02");
  assert.equal(runningLabel(1, 80), "第 2 次 · 生成中…（已用 1分20秒）");
  assert.equal(runningLabel(2, undefined), "第 3 次 · 生成中…");
});

test("randomSeed 返回 0–4294967295 的整数，可注入 crypto 实现（D-46）", () => {
  for (let i = 0; i < 50; i += 1) {
    const seed = randomSeed();
    assert.ok(Number.isInteger(seed) && seed >= 0 && seed <= 4294967295);
  }
  const fixed = { getRandomValues: (buffer) => { buffer[0] = 4294967295; return buffer; } };
  assert.equal(randomSeed(fixed), 4294967295);
});

test("当前会话恢复：优先生成中的，否则最新；坏文件不优先（D-63）", () => {
  const list = [{ id: "a" }, { id: "b", running: true }, { id: "c", corrupt: true }];
  assert.equal(pickCurrent(list), "b");
  assert.equal(pickCurrent(list, "a"), "a");
  assert.equal(pickCurrent(list, "gone"), "b");
  assert.equal(pickCurrent([{ id: "c", corrupt: true }, { id: "d" }]), "d");
  assert.equal(pickCurrent([{ id: "c", corrupt: true }]), "c");
  assert.equal(pickCurrent([]), null);
});

const base = {
  pending: false, listState: "ready", currentId: "a", currentCorrupt: false,
  current: { id: "a", attempts: [{ id: "x1", status: "done" }] }, job: null,
  sessions: [{ id: "a", title: "橘猫" }, { id: "b", title: "海边的灯塔" }],
  allowed: true, busyReason: "", runtimeReason: "", modelReason: "",
};

test("不可用原因按 §7.6 优先级只取第一条", () => {
  assert.deepEqual(availability(base, { noun: "图片" }), { reason: "", disabled: false, returnTo: null });
  assert.equal(availability({ ...base, pending: true, modelReason: "m" }, { noun: "图片" }).reason, "正在提交…");
  assert.equal(availability({ ...base, listState: "loading" }, { noun: "图片" }).reason, "会话还没加载好");
  assert.equal(availability({ ...base, listState: "error" }, { noun: "图片" }).reason, "会话还没加载好");
  assert.equal(availability({ ...base, currentCorrupt: true, current: null }, { noun: "图片" }).reason, "请选择其他会话或新建一个");
  const runningHere = { kind: "image", status: "running", session_id: "a", attempt_id: "x2" };
  const hereState = { ...base, job: runningHere, allowed: false, busyReason: "媒体作业进行中",
    current: { id: "a", attempts: [{ id: "x1", status: "done" }, { id: "x2", status: "running" }] } };
  assert.equal(availability(hereState, { noun: "图片" }).reason, "正在生成这个会话里的第 2 次");
  const other = availability({ ...base, job: { ...runningHere, session_id: "b" }, allowed: false, busyReason: "媒体作业进行中" }, { noun: "图片" });
  assert.deepEqual(other, { reason: "「海边的灯塔」正在生成图片", disabled: true, returnTo: "b" });
  const fromList = availability({ ...base, sessions: [{ id: "a" }, { id: "b", title: "灯塔", running: true }] }, { noun: "图片" });
  assert.equal(fromList.returnTo, "b");
  assert.equal(availability({ ...base, allowed: false, busyReason: "媒体作业进行中" }, { noun: "图片" }).reason, "媒体作业进行中");
  assert.equal(availability({ ...base, allowed: false, busyReason: "媒体作业进行中" }, { noun: "图片" }).returnTo, null);
  assert.equal(availability({ ...base, runtimeReason: "r", modelReason: "m" }, { noun: "图片" }).reason, "r");
  assert.equal(availability({ ...base, modelReason: "尚未安装图片模型，请到「资源」页下载" }, { noun: "图片" }).disabled, true);
  assert.equal(runningSessionId({ kind: "image", status: "done", session_id: "a" }, [{ id: "b", running: true }], "image"), "b");
});

test("删除确认正文：只删分组；生成中追加一句（D-90）", () => {
  assert.equal(deleteMessage({ title: "橘猫" }, { noun: "图片" }), "确定删除「橘猫」？只删除这个会话分组，其中的图片仍保留在素材库。");
  assert.match(deleteMessage({ title: "橘猫", running: true }, { noun: "图片" }), /生成会继续完成，图片会进入素材库，但不会再出现在任何会话里。$/);
});

const NOT_SEED = "种子"; // 「种子」

test("启动失败文案（D-88）与主流程文案都不出现「种子」（D-50）", () => {
  assert.equal(startErrorText({ code: "media_busy", message: "x" }), "已有作业在进行");
  assert.equal(startErrorText({ code: "spawn_failed", message: "x" }), "无法启动生成程序");
  const texts = [
    autoTitle("猫"), sessionMeta({ attempt_count: 1, updated: "2026-09-24T10:00:00" }), attemptLabel(0, {}), runningLabel(0, 1),
    deleteMessage({ title: "t", running: true }, { noun: "图片" }), availability(base, { noun: "图片" }).reason,
    availability({ ...base, pending: true }, { noun: "图片" }).reason, availability({ ...base, currentCorrupt: true }, { noun: "图片" }).reason,
  ];
  for (const text of texts) assert.ok(!String(text).includes(NOT_SEED), text);
});

test("列表顺序：updated 降序、坏文件最后；同一秒并列时刚新建的排最上（D-60）", () => {
  const list = [
    { id: "old", updated: "2026-09-24T10:00:00" }, { id: "x", corrupt: true },
    { id: "a", updated: "2026-09-24T10:05:00" }, { id: "fresh", updated: "2026-09-24T10:05:00" },
  ];
  assert.deepEqual(orderSessions(list, "fresh").map((s) => s.id), ["fresh", "a", "old", "x"]);
  assert.deepEqual(orderSessions(list).map((s) => s.id), ["a", "fresh", "old", "x"]);
});

test("attemptView names the missing file by noun", () => {
  const gone = { status: "done", output: "x", output_missing: true };
  assert.equal(attemptView(gone).title, "图片文件已不在");
  assert.equal(attemptView(gone, { noun: "音频" }).badge, "音频文件已不在");
  assert.equal(attemptView(gone, { noun: "视频" }).title, "视频文件已不在");
});
