import test from "node:test";
import assert from "node:assert/strict";
import { buildSummaryRequest } from "../../desk/static/js/pure/summary_prompt.js";

const head = [
  { role: "user", content: "帮我把视频导出成 4K" },
  { role: "assistant", content: "好的，先确认分辨率" },
  { role: "user", content: "用 h3 那个模型" },
];

test("提示词是一张固定的表，不是「总结一下」", () => {
  const [request] = buildSummaryRequest(head).slice(-1);
  assert.doesNotMatch(request.content, /总结一下|简要概括/);
  for (const section of ["用户要做的事", "事实与决定|关键概念", "涉及的文件", "用户说过的每一句", "待办"]) {
    assert.match(request.content, new RegExp(section), `模板缺小节：${section}`);
  }
});

// R-context-02：模板含且至少含六项——用户原始意图、关键概念、涉及文件与代码、
// 错误与修法、用户历次发言逐条列出、待办与当前工作。上一份计划的教训是
// 「测试照着实现写、不照着 spec 写」会漏掉分歧；这里逐项对着 spec 的原始措辞查，
// 不是照抄计划给的五节模板。
test("模板六节逐一对齐 spec 原始措辞，一节都不能少（R-context-02）", () => {
  const [request] = buildSummaryRequest(head).slice(-1);
  for (const section of [
    "用户要做的事",
    "关键概念",
    "涉及的文件与代码",
    "错误与修法",
    "用户说过的每一句",
    "待办与当前进度",
  ]) {
    assert.match(request.content, new RegExp(section), `模板缺 spec 要求的小节：${section}`);
  }
});

test("用户原话原样进提示词，模型只需搬运不需复述", () => {
  // 断言必须落在专门的「用户原话」逐条小节里（"- " 开头逐行），而不是随便在
  // 对话记录（【用户】…）里出现就算数——否则删掉专门的原话小节这条测试也不会
  // 变红，等于没测到「原样抄进提示词、模型只需搬运」这件事本身。
  const text = buildSummaryRequest(head).map((m) => m.content).join("\n");
  assert.match(text, /^- 帮我把视频导出成 4K$/m);
  assert.match(text, /^- 用 h3 那个模型$/m);
});

test("助手的话也在，但和用户的话分得开", () => {
  const text = buildSummaryRequest(head).map((m) => m.content).join("\n");
  assert.match(text, /好的，先确认分辨率/);
});

test("空输入不产出请求——没有可摘的东西就不该调模型", () => {
  assert.deepEqual(buildSummaryRequest([]), []);
});

test("已有的摘要作为前情进入提示词，不被当成用户发言", () => {
  const text = buildSummaryRequest([
    { role: "summary", content: "上一份摘要" },
    { role: "user", content: "接着说" },
  ]).map((m) => m.content).join("\n");
  assert.match(text, /上一份摘要/);
  // 「用户原话」逐条清单只认 role === "user"：摘要不能顶着 "- " 前缀混进去，
  // 被模型误当成用户自己说过的一句话。
  assert.doesNotMatch(text, /^- 上一份摘要$/m);
});

// 原计划这条测试用 text.split("用户说过的每一句") 取后半段来判断摘要有没有
// 混进「用户历次发言」——短接验证时发现它不会变红：那个切分点落在 TEMPLATE
// 自带的小节说明文字里，从来没有真正圈住 quotes/transcript 的实际内容，
// 所以断言恒真。按纪律改成量「摘要文本出现几次」：正确实现里它只应该在
// 「更早的摘要」一处出现；混进对话记录（当成一轮新发言）就会变成两次。
test("摘要内容只在「更早的摘要」出现一次，不会被当成对话记录里的一轮新发言重复贴出", () => {
  const text = buildSummaryRequest([
    { role: "summary", content: "上一份摘要" },
    { role: "user", content: "接着说" },
  ]).map((m) => m.content).join("\n");
  const occurrences = text.split("上一份摘要").length - 1;
  assert.equal(occurrences, 1, "摘要文本被重复贴了不止一次");
});
