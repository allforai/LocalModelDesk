import test from "node:test";
import assert from "node:assert/strict";
import {
  attemptLabel, attemptView, autoTitle, availability, deleteMessage, orderSessions, pickCurrent, randomSeed,
  readImageParams, recomposeParams, refineChipText, refineChipVisible, refineFields, runningLabel,
  runningSessionId, sessionMeta, sessionTitle, specLine, startErrorText,
  hasImage, submitBase, baseLabel, NO_IMAGE_REASON,
} from "../../desk/static/js/pure/image_session.js";

const SEED = "种子"; // 「种子」

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
  assert.equal(specLine({ width: 1024, height: 768, steps: 40 }), "1024×768 · 40 步");
});

test("尝试状态 → 标记与原因（D-84、D-85）：失败、已取消、退出取消、中断、文件不在", () => {
  assert.deepEqual(attemptView({ status: "done", output: "a.png" }).kind, "done");
  const failed = attemptView({ status: "failed", error: { code: "exit_nonzero", message: "exit 1", log_tail: "boom" } });
  assert.equal(failed.kind, "failed"); assert.equal(failed.badge, "失败");
  assert.equal(failed.title, "生成程序异常退出"); assert.equal(failed.icon, "x"); assert.equal(failed.tone, "danger");
  assert.equal(attemptView({ status: "failed", error: { code: "interrupted", message: "x" } }).title, "应用在生成途中关闭，这次没有完成");
  const cancelled = attemptView({ status: "cancelled", error: { code: "cancelled", message: "已取消：这次生成被手动停止" } });
  assert.equal(cancelled.badge, "已取消"); assert.equal(cancelled.title, "已取消"); assert.equal(cancelled.tone, "muted");
  // AC-6「显示原因」：用户取消的说明来自存进文件的原话（D-09），去掉与标记重复的「已取消：」。
  assert.equal(cancelled.sub, "这次生成被手动停止");
  assert.equal(attemptView({ status: "cancelled", error: { code: "cancelled", message: "已取消" } }).sub, "");
  assert.equal(attemptView({ status: "cancelled", error: null }).sub, "");
  assert.equal(attemptView({ status: "cancelled", error: { code: "cancelled_on_quit", message: "应用退出时停止了这次生成" } }).sub, "");
  assert.equal(attemptView({ status: "cancelled", error: { code: "cancelled_on_quit", message: "x" } }).title, "应用退出时停止了这次生成");
  const missing = attemptView({ status: "done", output: "a.png", output_missing: true });
  assert.equal(missing.kind, "missing"); assert.equal(missing.icon, "image");
  assert.equal(missing.title, "图片文件已不在"); assert.equal(missing.sub, "可能已在访达中移动或删除");
  assert.equal(attemptView({ status: "done", output: "a.png" }, { broken: true }).kind, "missing");
  assert.equal(attemptView({ status: "running" }).kind, "running");
});

test("「在这张基础上改」回填五个值并沿用种子（D-40、D-44）", () => {
  const attempt = { params: { prompt: "猫", width: 768, height: 512, steps: 30, seed: 0 } };
  assert.deepEqual(refineFields(attempt), { prompt: "猫", width: 768, height: 512, steps: 30, seed: 0 });
});

test("「换个构图」同参数、新随机种子，恰好相同时重取（D-46）", () => {
  const attempt = { params: { prompt: "猫", width: 768, height: 512, steps: 30, seed: 7 } };
  const draws = [7, 7, 99];
  const params = recomposeParams(attempt, "s1", () => draws.shift());
  assert.deepEqual(params, { session_id: "s1", prompt: "猫", width: 768, height: 512, steps: 30, seed: 99 });
  for (let i = 0; i < 50; i += 1) {
    const seed = randomSeed();
    assert.ok(Number.isInteger(seed) && seed >= 0 && seed <= 4294967295);
  }
  const fixed = { getRandomValues: (buffer) => { buffer[0] = 4294967295; return buffer; } };
  assert.equal(randomSeed(fixed), 4294967295);
});

test("提示条只在种子框等于被引用尝试的种子时显示（D-41、D-42、D-95）", () => {
  const ref = { seed: 12, index: 1 };
  assert.equal(refineChipVisible("12", ref), true);
  assert.equal(refineChipVisible(" 12 ", ref), true);
  assert.equal(refineChipVisible("13", ref), false);
  assert.equal(refineChipVisible("", ref), false);
  assert.equal(refineChipVisible("0", { seed: 0, index: 0 }), true);
  assert.equal(refineChipVisible("12", null), false);
  assert.equal(refineChipText(ref), "沿用第 2 次的构图");
  assert.equal(refineChipText({ seed: 3, index: null }), "沿用素材库里这张的构图");
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

test("输入区读数：种子留空不传；高级参数错误带前缀（D-51、D-66）", () => {
  assert.deepEqual(readImageParams({ prompt: "猫", width: "1024", height: "768", steps: "40", seed: "" }),
    { prompt: "猫", width: 1024, height: 768, steps: 40 });
  assert.deepEqual(readImageParams({ prompt: "猫", width: "1024", height: "768", steps: "40", seed: "0" }).seed, 0);
  assert.throws(() => readImageParams({ prompt: " ", width: "1024", height: "1024", steps: "40" }),
    (error) => error.message === "请填写图片提示词" && !error.advanced);
  for (const bad of [{ width: "257" }, { steps: "0" }, { seed: "-1" }, { seed: "4294967296" }, { seed: "1.5" }, { height: "" }]) {
    assert.throws(() => readImageParams({ prompt: "猫", width: "1024", height: "1024", steps: "40", seed: "", ...bad }),
      (error) => error.advanced && error.message.startsWith("高级参数里的数值有误："), JSON.stringify(bad));
  }
});

const base = {
  pending: false, listState: "ready", currentId: "a", currentCorrupt: false,
  current: { id: "a", attempts: [{ id: "x1", status: "done" }] }, job: null,
  sessions: [{ id: "a", title: "橘猫" }, { id: "b", title: "海边的灯塔" }],
  allowed: true, busyReason: "", runtimeReason: "", modelReason: "",
};

test("不可用原因按 §7.6 优先级只取第一条", () => {
  assert.deepEqual(availability(base), { reason: "", disabled: false, returnTo: null });
  assert.equal(availability({ ...base, pending: true, modelReason: "m" }).reason, "正在提交…");
  assert.equal(availability({ ...base, listState: "loading" }).reason, "会话还没加载好");
  assert.equal(availability({ ...base, listState: "error" }).reason, "会话还没加载好");
  assert.equal(availability({ ...base, currentCorrupt: true, current: null }).reason, "请选择其他会话或新建一个");
  const runningHere = { kind: "image", status: "running", session_id: "a", attempt_id: "x2" };
  const hereState = { ...base, job: runningHere, allowed: false, busyReason: "媒体作业进行中",
    current: { id: "a", attempts: [{ id: "x1", status: "done" }, { id: "x2", status: "running" }] } };
  assert.equal(availability(hereState).reason, "正在生成这个会话里的第 2 次");
  const other = availability({ ...base, job: { ...runningHere, session_id: "b" }, allowed: false, busyReason: "媒体作业进行中" });
  assert.deepEqual(other, { reason: "「海边的灯塔」正在生成图片", disabled: true, returnTo: "b" });
  const fromList = availability({ ...base, sessions: [{ id: "a" }, { id: "b", title: "灯塔", running: true }] });
  assert.equal(fromList.returnTo, "b");
  assert.equal(availability({ ...base, allowed: false, busyReason: "媒体作业进行中" }).reason, "媒体作业进行中");
  assert.equal(availability({ ...base, allowed: false, busyReason: "媒体作业进行中" }).returnTo, null);
  assert.equal(availability({ ...base, runtimeReason: "r", modelReason: "m" }).reason, "r");
  assert.equal(availability({ ...base, modelReason: "尚未安装图片模型，请到「资源」页下载" }).disabled, true);
  assert.equal(runningSessionId({ kind: "image", status: "done", session_id: "a" }, [{ id: "b", running: true }]), "b");
});

test("删除确认正文：只删分组；生成中追加一句（D-90）", () => {
  assert.equal(deleteMessage({ title: "橘猫" }), "确定删除「橘猫」？只删除这个会话分组，其中的图片仍保留在素材库。");
  assert.match(deleteMessage({ title: "橘猫", running: true }), /生成会继续完成，图片会进入素材库，但不会再出现在任何会话里。$/);
});

test("启动失败文案（D-88）与主流程文案都不出现「种子」（D-50）", () => {
  assert.equal(startErrorText({ code: "media_busy", message: "x" }), "已有作业在进行");
  assert.equal(startErrorText({ code: "spawn_failed", message: "x" }), "无法启动生成程序");
  const texts = [
    autoTitle("猫"), sessionMeta({ attempt_count: 1, updated: "2026-09-24T10:00:00" }), attemptLabel(0, {}), runningLabel(0, 1),
    specLine({ width: 1, height: 1, steps: 1 }), refineChipText({ index: 0 }), refineChipText({ index: null }),
    deleteMessage({ title: "t", running: true }), availability(base).reason,
    availability({ ...base, pending: true }).reason, availability({ ...base, currentCorrupt: true }).reason,
    ...["failed", "cancelled", "done"].flatMap((status) => {
      const v = attemptView({ status, output: "a.png", output_missing: true, error: { code: "exit_nonzero", message: "m" } });
      return [v.badge, v.title, v.sub];
    }),
  ];
  for (const text of texts) assert.ok(!String(text).includes(SEED), text);
});

test("列表顺序：updated 降序、坏文件最后；同一秒并列时刚新建的排最上（D-60）", () => {
  const list = [
    { id: "old", updated: "2026-09-24T10:00:00" }, { id: "x", corrupt: true },
    { id: "a", updated: "2026-09-24T10:05:00" }, { id: "fresh", updated: "2026-09-24T10:05:00" },
  ];
  assert.deepEqual(orderSessions(list, "fresh").map((s) => s.id), ["fresh", "a", "old", "x"]);
  assert.deepEqual(orderSessions(list).map((s) => s.id), ["a", "fresh", "old", "x"]);
});


// ---- 以图生图（2026-09-24）：两个按钮以这张为底稿重绘 ----

const DONE = { id: "a1", status: "done", output: "x.png", params: { prompt: "猫", width: 512, height: 768, steps: 16, seed: 7 } };

test("有图才能当底稿：done、有文件名、文件还在", () => {
  assert.equal(hasImage(DONE), true);
  assert.equal(hasImage({ ...DONE, output_missing: true }), false);
  assert.equal(hasImage({ ...DONE, status: "failed" }), false);
  assert.equal(hasImage({ ...DONE, output: null }), false);
  assert.equal(hasImage(null), false);
});

test("「换个构图」以这张为底稿、强度 0.35（保留主体与色调，换构图）", () => {
  const params = recomposeParams(DONE, "s1", () => 99);
  assert.deepEqual(params.base, { attempt_id: "a1", strength: 0.35 });
  assert.equal(params.prompt, "猫");
  assert.equal(params.seed, 99);
});

test("「在这张基础上改」后提示条还在时，「生成图片」以那张为底稿、强度 0.6", () => {
  const ref = { seed: 7, index: 0, attemptId: "a1", image: true };
  assert.deepEqual(submitBase("7", ref), { attempt_id: "a1", strength: 0.6 });
  assert.equal(submitBase("8", ref), null);              // 改了种子：提示条消失，退回文生图
  assert.equal(submitBase("7", { ...ref, image: false }), null); // 没图的尝试只回填
  assert.equal(submitBase("7", { seed: 7, index: null }), null);  // 素材库回填（无会话尝试）
  assert.equal(refineChipText(ref), "以第 1 次为底稿");
  assert.equal(refineChipText({ ...ref, image: false }), "沿用第 1 次的构图");
});

test("卡片标「基于第 N 次」；底稿不在列表里或没有底稿时不标", () => {
  const attempts = [DONE, { id: "a2", base: { attempt_id: "a1", strength: 0.6 } }, { id: "a3", base: { attempt_id: "gone", strength: 0.35 } }];
  assert.equal(baseLabel(attempts[1], attempts), "基于第 1 次");
  assert.equal(baseLabel(attempts[2], attempts), "");
  assert.equal(baseLabel(DONE, attempts), "");
  assert.ok(NO_IMAGE_REASON.length > 0 && !NO_IMAGE_REASON.includes(SEED));
});
