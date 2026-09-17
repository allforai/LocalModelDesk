/** 填表式摘要提示词。
 *
 * 本地 27B 做不了「判断什么重要」这种开放任务，但能填表。给它一张固定的表，
 * 输出质量的方差会显著变小——这是对冲本地模型能力弱的主要手段。
 *
 * 模板小节对应 spec R-context-02「模板含且至少含」的六项：用户原始意图、
 * 关键概念、涉及文件与代码、错误与修法、用户历次发言逐条列出、待办与当前工作。
 *
 * 「用户说过的每一句」那一节不让模型复述：复述必然走样。用户原话原样抄进
 * 提示词，模型只需搬运。
 */

const TEMPLATE = `请按下面的表格逐节填写，不要增加小节，不要发表评论。

## 用户要做的事
（用户的目标，尽量用他自己的措辞）

## 关键概念
（对话中出现过的重要概念、术语，一条一行）

## 涉及的文件与代码
（出现过的文件名、函数名、代码片段、参数值，一条一行）

## 错误与修法
（遇到过的报错、失败，以及后来怎么解决的，一条一行；没有就写「无」）

## 用户说过的每一句
（把下面「用户原话」里的每一条原样抄下来，一条一行，一个字都不要改）

## 待办与当前进度
（还没做完的事，以及现在进行到哪一步）`;

export function buildSummaryRequest(head) {
  const list = head ?? [];
  if (list.length === 0) return []; // 没有可摘的就不调模型

  const transcript = list
    .filter((m) => m.role !== "summary")
    .map((m) => `【${m.role === "user" ? "用户" : "助手"}】${m.content ?? ""}`)
    .join("\n");
  const earlier = list
    .filter((m) => m.role === "summary")
    .map((m) => m.content ?? "")
    .join("\n");
  const quotes = list
    .filter((m) => m.role === "user")
    .map((m) => `- ${m.content ?? ""}`)
    .join("\n");

  const parts = [];
  if (earlier) parts.push(`# 更早的摘要\n${earlier}`);
  parts.push(`# 对话记录\n${transcript}`);
  parts.push(`# 用户原话（这一节必须原样抄进表里）\n${quotes}`);
  parts.push(TEMPLATE);
  return [{ role: "user", content: parts.join("\n\n") }];
}
