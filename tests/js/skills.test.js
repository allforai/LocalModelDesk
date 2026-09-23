import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  resolveSelection, skillSystemMessage, skillChars, skillTokens,
} from "../../desk/static/js/pure/skills.js";

const entry = (name, body, attachments = []) => ({
  name, description: "d", source: "user", overrides_bundled: false,
  body, chars: body.length, attachments, ok: true, error: null,
});

test("拼进上下文的是原文，不是转述", () => {
  const { resolved } = resolveSelection(
    [{ name: "a", attachments: [] }], [entry("a", "原文正文")]);
  assert.equal(skillSystemMessage(resolved).content.includes("原文正文"), true);
  assert.equal(skillSystemMessage(resolved).role, "system");
});

test("没选中任何 skill 时不产生 system 消息", () => {
  assert.equal(skillSystemMessage([]), null);
});

test("多个 skill 按选中顺序拼接", () => {
  // R-skill-04：顺序由用户的点击顺序决定，不重新排序——他先点的就该先生效。
  const { resolved } = resolveSelection(
    [{ name: "b", attachments: [] }, { name: "a", attachments: [] }],
    [entry("a", "AAA"), entry("b", "BBB")]);
  const content = skillSystemMessage(resolved).content;
  assert.ok(content.indexOf("BBB") < content.indexOf("AAA"), "没按选中顺序拼");
});

test("勾中的附件原文拼进去，没勾的不进去", () => {
  const available = [entry("a", "正文", [{ file: "X.md", chars: 3, text: "附件原文" }])];
  const on = resolveSelection([{ name: "a", attachments: ["X.md"] }], available);
  const off = resolveSelection([{ name: "a", attachments: [] }], available);
  assert.ok(skillSystemMessage(on.resolved).content.includes("附件原文"));
  assert.ok(!skillSystemMessage(off.resolved).content.includes("附件原文"));
});

test("消失的 skill 不静默丢弃，也不继续注入", () => {
  // R-skill-14：用户可能在文件夹里删掉一个正被选中的 skill。
  const { resolved, dropped } = resolveSelection(
    [{ name: "gone", attachments: [] }, { name: "a", attachments: [] }], [entry("a", "AAA")]);
  assert.deepEqual(resolved.map((s) => s.name), ["a"]);
  assert.equal(dropped.length, 1);
  assert.equal(dropped[0].name, "gone");
  assert.match(dropped[0].reason, /不存在/);
});

test("变坏的 skill 也要被摘出来并说明", () => {
  const broken = { ...entry("bad", ""), ok: false, error: "frontmatter 缺 description" };
  const { resolved, dropped } = resolveSelection([{ name: "bad", attachments: [] }], [broken]);
  assert.deepEqual(resolved, []);
  assert.equal(dropped[0].reason, "frontmatter 缺 description");
});

test("勾中的附件已经不在了，只丢这一份附件，不丢整个 skill", () => {
  const { resolved, dropped } = resolveSelection(
    [{ name: "a", attachments: ["GONE.md"] }], [entry("a", "正文")]);
  assert.equal(resolved.length, 1);
  assert.deepEqual(resolved[0].attachments, []);
  assert.equal(dropped.length, 1);
  assert.match(dropped[0].name, /GONE\.md/);
});

test("占用按拼出来的字符数算，含附件", () => {
  const available = [entry("a", "12345", [{ file: "X.md", chars: 3, text: "678" }])];
  const bare = resolveSelection([{ name: "a", attachments: [] }], available).resolved;
  const withFile = resolveSelection([{ name: "a", attachments: ["X.md"] }], available).resolved;
  assert.ok(skillChars(withFile) > skillChars(bare), "勾了附件占用没涨");
  assert.equal(skillChars([]), 0);
});

test("这个模块里不许出现任何摘要机制", () => {
  // R-skill-02 是条否定需求，只有守卫测试能钉住它：进模型的每个字都是原文。
  // 别处出错都看得见（文件坏了界面会说、token 超了界面会显示），唯独转述错了没人知道。
  const source = readFileSync(
    new URL("../../desk/static/js/pure/skills.js", import.meta.url), "utf-8");
  for (const banned of ["summar", "摘要", "截断", "slice(0,", "substring("]) {
    assert.ok(!source.includes(banned), `${banned} 出现了——原文被转述或截断了`);
  }
});

test("量不到每 token 字符数时不猜，返回 null", () => {
  // compaction.js 的房规：量不到就返回 null，而不是套一个默认值。
  assert.equal(skillTokens(1000, null), null);
  assert.equal(skillTokens(1000, 0), null);
  assert.equal(skillTokens(1000, 4), 250);
});
