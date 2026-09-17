# 上下文压缩 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 长会话不再把全部历史原样发上去——超过预算给的触发点时，较早的消息由一条结构化摘要替代，尾部保持原文，而磁盘与界面上一个字都不少。

**Architecture:** 压缩住在前端，因为会话与消息就住在那里（`session.messages`，经 `api.updateChatSession` 落盘），而服务端的聊天流是无状态的。判断与切分做成 `desk/static/js/pure/compaction.js` 的纯函数；编排在 `panes/chat.js`，发生在两轮之间；触发点取自 `/api/budget` 的 `chat.compact_at`（budget 子系统已就位）。

**Tech Stack:** 零依赖 ES module、`node --test`、pytest + Playwright（e2e）、既有的 `desk/testing` 假模型台面。

**Spec:** `docs/superpowers/specs/2026-09-17-budget-spec.md` 的 R-context-01 … R-context-05 与 R-budget-09；设计见 `docs/superpowers/specs/2026-09-17-budget-design.md` 的「上下文管理」一节

## Global Constraints

- **零第三方依赖**：前端只用原生 ES module，与仓库既有 `pure/` 风格一致。
- **压缩只影响发送内容，不影响存储与展示**（R-context-03）。`session.messages` 永远保留全部原始消息；用户往上翻，每一条都还在。
- **摘要按固定模板填表，不得用开放式「总结一下」**（R-context-02）。本地 27B 做不了「判断什么重要」，但能填表。
- **用户原话逐条保留，不许改写**（R-context-02）。模型复述会走样。
- **压缩在两轮之间进行，用当前驻留模型，对用户可见**（R-context-04）。不加载第二个模型，不静默阻塞。
- **`summary` 角色发送时必须翻译成 `system`**。服务端不校验角色，但 mlx-lm 要套模型的 chat template，模板只认 system/user/assistant——发一个 `summary` 角色上去会炸在模板里。
- **测试必须验证「功能失效时会变红」**：每写完一个测试，短接被测实现跑一次，确认失败，再改回。双向行为要双向验证。**这一条是硬要求**：上一个计划里有两条测试是假的（其中一条是我写的），都是靠这一步抓出来的。
- **计划里的代码必须与本节和 spec 一致**。上一个计划的 `for_chat` 漏减权重，正是因为计划代码与设计文档不符而测试只照着代码写——没有任何一环会发现分歧。写测试时对着 spec 的需求写，不要只对着实现写。
- 中文标识符不进代码；面向用户的文案用中文。
- 测试一律用 `tmp_path` 或假台面，不得写入 `~/LocalModelDesk/llms` 与 `~/Library/Application Support/LocalModelDesk`。

---

## File Structure

| 文件 | 职责 |
|---|---|
| `desk/static/js/pure/compaction.js` | 纯函数：要不要压、按什么比例切、切在哪里 |
| `desk/static/js/pure/summary_prompt.js` | 纯函数：把待压缩消息渲染成填表式提示词 |
| `desk/static/js/pure/chat_stream.js` | 改 `wireMessages`：认 `summary`、翻译成 `system`、跳过被替代的消息 |
| `desk/static/js/panes/chat.js` | 编排：轮次结束后判断、调模型生成摘要、写回会话、渲染分隔与展开 |
| `desk/static/js/api.js` | 无需改动（`api.budget` 已在 Task 9 加好） |
| `desk/static/app.css` | 摘要分隔条样式 |
| `desk/testing/harness.py` | 假台面的 `/api/budget` 改为可配置，让 e2e 能给出很小的 `compact_at` |
| `tests/js/compaction.test.js` 等 | 与既有 `tests/js/*.test.js` 命名一致 |
| `tests/e2e/test_chat_compaction.py` | 真浏览器验证：触发、尾部保留、原文不丢 |

**关于 token 计数**：前端拿不到 tokenizer。唯一诚实的换算来源是**上一轮真实请求的读数**——`usage.prompt_tokens` 配上那次实际发出去的字符数，相除就是这个会话、这个模型的每 token 字符数。和 budget 子系统用「日志字节数 ÷ prompt_tokens」自校准是同一招：不猜常数，用实测比值。没有读数时不猜，不压缩。

---

### Task 1: compaction.js —— 要不要压、切在哪里

**Files:**
- Create: `desk/static/js/pure/compaction.js`
- Test: `tests/js/compaction.test.js`

**Interfaces:**
- Consumes: 无
- Produces:
  - `charsPerToken(sentChars: number, promptTokens: number) -> number | null`
  - `needsCompaction({promptTokens, compactAt, pressure}) -> boolean`
  - `splitForCompaction(messages, {compactAt, charsPerToken}) -> {head: Message[], tail: Message[]}`

**背景（实现者必读）**：

`needsCompaction` 有两个触发源。一是额度：上一轮的 `prompt_tokens` 超过 `/api/budget` 给的 `chat.compact_at`。二是内存压力（R-budget-09 的第一步）：`snapshot.pressure` 不是 `normal` 时立即压缩——那是台面唯一能便宜做到的减压动作，已核实 mlx-lm 没有管理端点、外部触发不了它的 trim。

`compactAt` 为 0 或缺失表示「预算算不出」（例如模型是 MLA、或没有驻留模型）。**算不出时不压缩**，与 budget 子系统「未经实测不放宽」同一条纪律：不知道额度就不要替用户裁剪历史。

`splitForCompaction` 的尾部保留量**不是常数**：按「尾部原文估算 token 数不超过 `compactAt` 的一半」反推，且**至少保留最近一轮完整问答**（最后一条 user 及其后的全部）。写死轮数会在 80 KB/token 与 960 KB/token 的模型之间差一个数量级——这是真机实测的数字，不是假设。

- [ ] **Step 1: 写失败的测试**

```js
// tests/js/compaction.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { charsPerToken, needsCompaction, splitForCompaction } from "../../desk/static/js/pure/compaction.js";

const msg = (role, content) => ({ role, content });

test("每 token 字符数由上一轮真实读数相除得出，不猜常数", () => {
  assert.equal(charsPerToken(4000, 1000), 4);
});

test("缺任一读数就返回 null，调用方据此不压缩", () => {
  assert.equal(charsPerToken(4000, 0), null);
  assert.equal(charsPerToken(0, 1000), null);
  assert.equal(charsPerToken(4000, undefined), null);
});

test("超过触发点就该压", () => {
  assert.equal(needsCompaction({ promptTokens: 30_000, compactAt: 29_971 }), true);
});

test("没到触发点不压", () => {
  assert.equal(needsCompaction({ promptTokens: 1_000, compactAt: 29_971 }), false);
});

test("内存压力起来时立即压，不等额度用满", () => {
  // R-budget-09 第一步：这是台面唯一能便宜做到的减压动作。
  assert.equal(needsCompaction({ promptTokens: 10, compactAt: 29_971, pressure: "warn" }), true);
});

test("算不出额度时一律不压", () => {
  // 预算说「算不出」就别替用户裁剪历史——与 budget 的「未经实测不放宽」同一条纪律。
  assert.equal(needsCompaction({ promptTokens: 999_999, compactAt: 0 }), false);
  assert.equal(needsCompaction({ promptTokens: 999_999, compactAt: undefined }), false);
});

test("压力起来但额度算不出时，仍然不压", () => {
  assert.equal(needsCompaction({ promptTokens: 10, compactAt: 0, pressure: "critical" }), false);
});

test("尾部按预算反推，不是写死的轮数", () => {
  // compactAt=100，一半=50 token，每 token 4 字符 ⇒ 尾部最多约 200 字符
  const messages = [
    msg("user", "a".repeat(400)), msg("assistant", "b".repeat(400)),
    msg("user", "c".repeat(80)), msg("assistant", "d".repeat(80)),
  ];
  const { head, tail } = splitForCompaction(messages, { compactAt: 100, charsPerToken: 4 });
  assert.equal(head.length, 2);
  assert.deepEqual(tail.map((m) => m.role), ["user", "assistant"]);
});

test("至少保留最近一轮完整问答，哪怕它超预算", () => {
  // 尾部预算再小也不能把用户刚问的那句连同回答一起摘掉——那是他眼前正在看的。
  const messages = [
    msg("user", "旧"), msg("assistant", "旧答"),
    msg("user", "x".repeat(10_000)), msg("assistant", "y".repeat(10_000)),
  ];
  const { head, tail } = splitForCompaction(messages, { compactAt: 10, charsPerToken: 4 });
  assert.equal(tail.length, 2);
  assert.equal(head.length, 2);
});

test("整段对话还没超出尾部预算时，没有可压的头部", () => {
  const messages = [msg("user", "短"), msg("assistant", "也短")];
  const { head, tail } = splitForCompaction(messages, { compactAt: 10_000, charsPerToken: 4 });
  assert.deepEqual(head, []);
  assert.equal(tail.length, 2);
});

test("已有的 summary 永远留在头部，不进尾部也不被丢弃", () => {
  // 第二次压缩要把「上一份摘要 + 其后的老消息」一起重新摘成一份。
  // 摘要之后的内容必须足够短，让预算判断不会先于摘要边界触发——
  // 否则「遇到 summary 就停」这条逻辑根本没被跑到，测试测不出它被删掉。
  const messages = [
    { role: "summary", content: "上一份摘要" },
    msg("user", "e".repeat(20)), msg("assistant", "f".repeat(20)),
    msg("user", "近"), msg("assistant", "近答"),
  ];
  const { head, tail } = splitForCompaction(messages, { compactAt: 1_000, charsPerToken: 4 });
  assert.equal(head.length, 1);
  assert.equal(head[0].role, "summary");
  assert.equal(tail.some((m) => m.role === "summary"), false);
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/compaction.test.js`
Expected: FAIL — `Cannot find module '.../pure/compaction.js'`

- [ ] **Step 3: 写最小实现**

```js
// desk/static/js/pure/compaction.js
/** 压缩的三个纯判断：要不要压、按什么换算、切在哪里。
 *
 * 前端没有 tokenizer，所以每 token 字符数只能从上一轮真实请求里量：
 * usage.prompt_tokens 配那次实际发出去的字符数，相除即得。这和 budget 用
 * 「日志字节数 ÷ prompt_tokens」自校准是同一招——不猜常数，用实测比值。
 * 量不到就返回 null，调用方据此不压缩，而不是套一个默认值。
 */

const TAIL_FRACTION = 0.5;   // 尾部原文最多占触发点的一半，剩下留给摘要与新一轮

export function charsPerToken(sentChars, promptTokens) {
  if (!sentChars || !promptTokens) return null;
  return sentChars / promptTokens;
}

export function needsCompaction({ promptTokens, compactAt, pressure } = {}) {
  // 算不出额度就不压：不知道上限却去裁剪用户的历史，比不裁更糟。
  if (!compactAt) return false;
  // R-budget-09 第一步：压力起来时立即压。已核实 mlx-lm 没有管理端点，
  // 外部触发不了它的 trim，收紧对话是台面唯一能便宜做到的减压动作。
  if (pressure && pressure !== "normal") return true;
  return (promptTokens ?? 0) >= compactAt;
}

const lengthOf = (message) => (message.content ?? "").length;

export function splitForCompaction(messages, { compactAt, charsPerToken: ratio } = {}) {
  const list = [...(messages ?? [])];
  if (!compactAt || !ratio) return { head: [], tail: list };

  // 最近一轮完整问答永远留在尾部：那是用户眼前正在看的东西，再紧也不能摘掉。
  let lastUser = -1;
  for (let i = list.length - 1; i >= 0; i -= 1) {
    if (list[i].role === "user") { lastUser = i; break; }
  }
  const mustKeepFrom = lastUser === -1 ? list.length : lastUser;

  const tailBudgetChars = compactAt * TAIL_FRACTION * ratio;
  // 强制保留区间（最近一轮问答）自身的字符数先算进预算里：它已经不可摘除，
  // 若它本身就已经超出预算，就不该再把更早的短消息也顺手拉进尾部
  // （测试「至少保留最近一轮完整问答，哪怕它超预算」验的正是这一点）。
  let used = 0;
  for (let i = mustKeepFrom; i < list.length; i += 1) {
    used += lengthOf(list[i]);
  }
  let cut = mustKeepFrom;
  for (let i = mustKeepFrom - 1; i >= 0; i -= 1) {
    // 已有的摘要永远归头部：第二次压缩要把它和其后的老消息一起重新摘成一份。
    if (list[i].role === "summary") break;
    used += lengthOf(list[i]);
    if (used > tailBudgetChars) break;
    cut = i;
  }
  return { head: list.slice(0, cut), tail: list.slice(cut) };
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/js/compaction.test.js`
Expected: PASS（11 passed）

- [ ] **Step 5: 验证测试会咬**

逐个短接，每次确认变红后改回：
1. `needsCompaction` 的 `if (!compactAt) return false;` 删掉 → 「算不出额度时一律不压」与「压力起来但额度算不出」两条变红。
2. 压力那一行删掉 → 「内存压力起来时立即压」变红。
3. `splitForCompaction` 的 `mustKeepFrom` 改成 `list.length`（即尾部只保留空）→ 「至少保留最近一轮完整问答」变红。
4. `if (list[i].role === "summary") break;` 删掉 → 「已有的 summary 永远留在头部」变红。

四次都确认变红后改回，重跑 11 passed。

- [ ] **Step 6: 提交**

```bash
git add desk/static/js/pure/compaction.js tests/js/compaction.test.js
git commit -m "feat(chat): 压缩的三个纯判断——要不要压、怎么换算、切在哪

前端没有 tokenizer，每 token 字符数只能从上一轮真实请求里量：prompt_tokens
配那次实际发出去的字符数，相除即得。和 budget 用日志字节数除 prompt_tokens
自校准是同一招——不猜常数，用实测比值；量不到就不压，不套默认值。

尾部保留量按预算反推而不是写死轮数：真机实测每 token 开销在 80KB 与 960KB
之间差一个数量级，写死一个轮数在两端都是错的。"
```

---

### Task 2: wireMessages 认摘要

**Files:**
- Modify: `desk/static/js/pure/chat_stream.js`
- Test: `tests/js/chat_stream.test.js`（既有文件，追加）

**Interfaces:**
- Consumes: 无
- Produces: `wireMessages(messages) -> {role, content}[]`，行为扩展如下

**背景（实现者必读）**：`wireMessages` 现在的实现是

```js
export function wireMessages(messages) {
  return messages
    .filter((message) => !(message.role === "assistant" && message.interrupted && !(message.content ?? "").trim()))
    .map((message) => ({ role: message.role, content: message.content ?? "" }));
}
```

要改三件事，缺一不可：

1. **`summary` 翻译成 `system`**。服务端不校验角色（已核实），但 mlx-lm 要套模型的 chat template，模板只认 system/user/assistant——原样发 `summary` 会炸在模板里。
2. **被摘要替代的消息不发送**。`summary` 消息带 `replaced_through`（被它替代的最后一条消息在 `messages` 里的下标）；下标小于等于它的消息全部跳过。**它们不被删除**，只是不发（R-context-03）。
3. **摘要内容加前缀说明它是什么**，否则模型会把它当成用户说过的话。

- [ ] **Step 1: 写失败的测试**

```js
// 追加到 tests/js/chat_stream.test.js
test("摘要以 system 角色发送——模型的 chat template 只认三种角色", () => {
  const wired = wireMessages([
    { role: "summary", content: "前情", replaced_through: 2 },
    { role: "user", content: "问" },
    { role: "assistant", content: "答" },
    { role: "user", content: "再问" },
  ]);
  assert.equal(wired[0].role, "system");
  assert.match(wired[0].content, /前情/);
});

test("被摘要替代的消息不发送，但摘要之后的照发", () => {
  const wired = wireMessages([
    { role: "summary", content: "前情", replaced_through: 2 },
    { role: "user", content: "被替代的问" },
    { role: "assistant", content: "被替代的答" },
    { role: "user", content: "还在的问" },
  ]);
  assert.deepEqual(wired.map((m) => m.content).slice(1), ["还在的问"]);
});

test("摘要内容带前缀，模型才不会把它当成用户说过的话", () => {
  const [first] = wireMessages([{ role: "summary", content: "前情", replaced_through: 0 }]);
  assert.notEqual(first.content, "前情");
  assert.match(first.content, /前情/);
});

test("没有摘要时行为一字不变", () => {
  const before = [
    { role: "user", content: "问" },
    { role: "assistant", content: "答" },
  ];
  assert.deepEqual(wireMessages(before), [
    { role: "user", content: "问" },
    { role: "assistant", content: "答" },
  ]);
});

test("中断且无内容的助手消息仍然被丢掉", () => {
  // 既有行为，不能在这次改动里丢失。
  const wired = wireMessages([
    { role: "user", content: "问" },
    { role: "assistant", content: "", interrupted: { code: "stopped", message: "x" } },
  ]);
  assert.equal(wired.length, 1);
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/chat_stream.test.js`
Expected: FAIL — 摘要那几条（`wired[0].role` 是 `"summary"` 而非 `"system"`）

- [ ] **Step 3: 写最小实现**

```js
const SUMMARY_PREFIX = "以下是本次对话更早部分的摘要，供你理解上下文；它不是用户的原话：\n\n";

export function wireMessages(messages) {
  const list = messages ?? [];
  // 摘要替代的那一段不发送——但它们仍然留在会话文件与界面上（R-context-03）。
  let skipThrough = -1;
  for (let i = 0; i < list.length; i += 1) {
    if (list[i].role === "summary" && Number.isInteger(list[i].replaced_through)) {
      skipThrough = Math.max(skipThrough, list[i].replaced_through);
    }
  }
  return list
    .filter((message, index) => !(index <= skipThrough && message.role !== "summary"))
    .filter((message) => !(message.role === "assistant" && message.interrupted && !(message.content ?? "").trim()))
    .map((message) => message.role === "summary"
      // chat template 只认 system/user/assistant，原样发 summary 会炸在模板里。
      ? { role: "system", content: SUMMARY_PREFIX + (message.content ?? "") }
      : { role: message.role, content: message.content ?? "" });
}
```

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/js/chat_stream.test.js`
Expected: PASS

- [ ] **Step 5: 验证测试会咬**

1. 把 `{ role: "system", ... }` 改回 `{ role: message.role, ... }` → 「摘要以 system 角色发送」变红。
2. 把 `SUMMARY_PREFIX +` 去掉 → 「摘要内容带前缀」变红。
3. 把 `skipThrough` 那段过滤删掉 → 「被摘要替代的消息不发送」变红。
4. 把 `interrupted` 那条过滤删掉 → 「中断且无内容的助手消息仍然被丢掉」变红（**这条是既有行为的回归网**，必须确认它还咬得住）。

四次都确认后改回。

- [ ] **Step 6: 跑全部 JS 测试**

Run: `node --test "tests/js/**/*.test.js"`
Expected: PASS

- [ ] **Step 7: 提交**

```bash
git add desk/static/js/pure/chat_stream.js tests/js/chat_stream.test.js
git commit -m "feat(chat): wireMessages 认摘要——翻译成 system，跳过被替代的消息

服务端不校验角色，但 mlx-lm 要套模型的 chat template，模板只认
system/user/assistant——原样发一个 summary 角色会炸在模板里。

被替代的消息只是不发送，没有被删除：会话文件与界面上一个字都不少。"
```

---

### Task 3: 填表式摘要提示词

**Files:**
- Create: `desk/static/js/pure/summary_prompt.js`
- Test: `tests/js/summary_prompt.test.js`

**Interfaces:**
- Consumes: 无
- Produces: `buildSummaryRequest(head) -> {role, content}[]`

**背景（实现者必读）**：这是对冲本地模型能力弱的**主要手段**。27B 的模型做不了「判断什么重要」这种开放任务，但能填表。所以提示词是一张固定的表，不是「总结一下」。

模板小节——**逐条照抄 spec R-context-02 的六项，不要自己归并**（初稿把「关键概念」并进了「事实与决定」
又整个漏掉了「错误与修法」，只剩五节）：

1. 用户要做的事（**原话**）
2. 关键概念
3. 涉及的文件与代码
4. **错误与修法**
5. **用户说过的每一句，逐条列出**
6. 待办与当前进度

第 4 节最关键：模型复述用户的话必然走样，所以这一节不是让它复述，而是**把用户原话原样抄进提示词**，要求它照抄进摘要。实现上直接把 `head` 里的 user 消息逐条拼进提示词，模型只需搬运。

- [ ] **Step 1: 写失败的测试**

```js
// tests/js/summary_prompt.test.js
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
  for (const section of ["用户要做的事", "事实与决定", "涉及的文件", "用户说过的每一句", "待办"]) {
    assert.match(request.content, new RegExp(section), `模板缺小节：${section}`);
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
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/summary_prompt.test.js`
Expected: FAIL — 模块不存在

- [ ] **Step 3: 写最小实现**

```js
// desk/static/js/pure/summary_prompt.js
/** 填表式摘要提示词。
 *
 * 本地 27B 做不了「判断什么重要」这种开放任务，但能填表。给它一张固定的表，
 * 输出质量的方差会显著变小——这是对冲本地模型能力弱的主要手段。
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
  if (list.length === 0) return [];      // 没有可摘的就不调模型

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
```

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/js/summary_prompt.test.js`
Expected: PASS（5 passed）

- [ ] **Step 5: 验证测试会咬**

1. 把 `TEMPLATE` 换成 `"请总结一下上面的对话。"` → 「提示词是一张固定的表」变红。
2. 把 `quotes` 那段删掉（不再把原话拼进去）→ 「用户原话原样进提示词」变红。
3. 把 `if (list.length === 0) return []` 删掉 → 「空输入不产出请求」变红。
4. 把 `filter((m) => m.role !== "summary")` 去掉（让上一份摘要混进 transcript）→ 检查「已有的摘要不被当成用户发言」是否变红；**若不变红，说明这条测试没咬住，按纪律修测试而不是跳过**。

四次都确认后改回。

- [ ] **Step 6: 提交**

```bash
git add desk/static/js/pure/summary_prompt.js tests/js/summary_prompt.test.js
git commit -m "feat(chat): 填表式摘要提示词，不是「总结一下」

本地 27B 做不了「判断什么重要」这种开放任务，但能填表。固定小节让输出质量
的方差显著变小——这是对冲本地模型能力弱的主要手段。

用户原话原样抄进提示词，模型只需搬运：让它复述必然走样，而用户说过的话
一个字都不该被改写。"
```

---

### Task 4: chat.js 编排 —— 在两轮之间压缩

**Files:**
- Modify: `desk/static/js/panes/chat.js`
- Test: `tests/js/chat_compaction_flow.test.js`

**Interfaces:**
- Consumes: Task 1 的 `charsPerToken` / `needsCompaction` / `splitForCompaction`、Task 3 的 `buildSummaryRequest`、`api.budget()`（Task 9 已加）
- Produces: 会话中出现 `{role: "summary", content, replaced_through, created_at}` 消息

**背景（实现者必读）**：编排的位置是**一轮完全结束之后**（`streamReply` 的收尾已经把助手消息 push 进 `session.messages`、`updateChatSession` 已经落盘），不是流式过程中。R-context-04 要求「两轮之间」且「对用户可见，不得静默阻塞」。

数据从哪来：

- `promptTokens`：上一轮 `done` 事件的 `state.usage.prompt_tokens`
- `sentChars`：那一轮实际发出去的 `wireMessages(...)` 结果的字符总数（发送时顺手记下）
- `compactAt` / `pressure`：`api.budget()` 的 `chat.compact_at` 与顶层 `pressure`

摘要用**当前驻留模型**生成，走同一个 `api.chatStream`，不加载第二个模型（R-context-04）。生成期间界面要显示「正在压缩较早的对话…」。

失败处理：摘要生成失败（模型报错、被中断）**不写入任何东西**，下一轮再试。绝不能出现「老消息被标记成已替代、摘要却没生成」的中间态——那会静默丢掉上下文。

- [ ] **Step 1: 写失败的测试**

```js
// tests/js/chat_compaction_flow.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { maybeCompact } from "../../desk/static/js/pure/compaction.js";

const longTurn = (n) => [
  { role: "user", content: "问".repeat(n) },
  { role: "assistant", content: "答".repeat(n) },
];

function fakeSummarise(text) {
  return async () => text;
}

test("超过触发点时产出一条摘要，并标出它替代到哪一条", async () => {
  const messages = [...longTurn(400), ...longTurn(400), ...longTurn(5)];
  const result = await maybeCompact(messages, {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 30_000,
    summarise: fakeSummarise("填好的表"),
  });
  assert.equal(result.messages.at(0).role, "summary");
  assert.equal(result.messages.at(0).content, "填好的表");
  assert.equal(Number.isInteger(result.messages.at(0).replaced_through), true);
});

test("原始消息一条都不少——压缩只影响发送，不影响存储", async () => {
  const messages = [...longTurn(400), ...longTurn(400), ...longTurn(5)];
  const result = await maybeCompact(messages, {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 30_000,
    summarise: fakeSummarise("填好的表"),
  });
  const kept = result.messages.filter((m) => m.role !== "summary");
  assert.deepEqual(kept, messages);
});

test("没到触发点时原样返回，且不调模型", async () => {
  let called = false;
  const messages = longTurn(5);
  const result = await maybeCompact(messages, {
    promptTokens: 10, sentChars: 40, compactAt: 30_000,
    summarise: async () => { called = true; return "不该被调用"; },
  });
  assert.equal(called, false);
  assert.equal(result.compacted, false);
  assert.deepEqual(result.messages, messages);
});

test("摘要生成失败时什么都不写——绝不留下「标了替代却没有摘要」的中间态", async () => {
  const messages = [...longTurn(400), ...longTurn(400), ...longTurn(5)];
  const result = await maybeCompact(messages, {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 30_000,
    summarise: async () => { throw new Error("模型炸了"); },
  });
  assert.equal(result.compacted, false);
  assert.deepEqual(result.messages, messages);
  assert.match(result.error ?? "", /模型炸了/);
});

test("摘要是空字符串时同样视为失败", async () => {
  const messages = [...longTurn(400), ...longTurn(400), ...longTurn(5)];
  const result = await maybeCompact(messages, {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 30_000,
    summarise: fakeSummarise("   "),
  });
  assert.equal(result.compacted, false);
  assert.deepEqual(result.messages, messages);
});

test("量不到每 token 字符数时不压缩", async () => {
  const messages = [...longTurn(400), ...longTurn(400)];
  const result = await maybeCompact(messages, {
    promptTokens: 0, sentChars: 0, compactAt: 30_000,
    summarise: fakeSummarise("不该被调用"),
  });
  assert.equal(result.compacted, false);
});
```

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/chat_compaction_flow.test.js`
Expected: FAIL — `maybeCompact` 未导出

- [ ] **Step 3: 在 compaction.js 里实现 maybeCompact**

```js
/** 一轮结束后的压缩编排：判断、切分、请模型填表、写回。
 *
 * `summarise` 由调用方注入（生产里是走 api.chatStream 的一次调用），
 * 所以这一层可以在没有浏览器、没有模型的情况下被完整测试。
 *
 * 失败时一个字都不写：绝不能留下「老消息被标成已替代、摘要却没生成」的
 * 中间态——那会静默丢掉上下文，而且用户看不出来。
 */
export async function maybeCompact(messages, { promptTokens, sentChars, compactAt, pressure, summarise } = {}) {
  const list = [...(messages ?? [])];
  const ratio = charsPerToken(sentChars, promptTokens);
  if (!ratio || !needsCompaction({ promptTokens, compactAt, pressure })) {
    return { compacted: false, messages: list };
  }
  const { head } = splitForCompaction(list, { compactAt, charsPerToken: ratio });
  if (head.length === 0) return { compacted: false, messages: list };

  let text;
  try {
    text = await summarise(head);
  } catch (error) {
    return { compacted: false, messages: list, error: error.message };
  }
  if (!(text ?? "").trim()) return { compacted: false, messages: list };

  const summary = {
    role: "summary",
    content: text.trim(),
    replaced_through: head.length - 1,
  };
  return { compacted: true, messages: [summary, ...list] };
}
```

**注意 `replaced_through` 的语义**：它是**在新数组里**被替代的最后一条的下标。摘要插在最前面，所以原来的第 0…head.length-1 条在新数组里是第 1…head.length 条。Task 2 的 `wireMessages` 跳过的是 `index <= replaced_through` 且非 summary 的消息——摘要自己在下标 0，被替代的从下标 1 开始，因此 `replaced_through` 应为 `head.length`，不是 `head.length - 1`。**Step 1 的测试只断言它是整数，所以这个差错测不出来——补一条**：

```js
test("replaced_through 精确指向被替代的最后一条，不差一位", async () => {
  const head = longTurn(400);                     // 2 条要被替代
  const tail = longTurn(5);                       // 2 条保留
  const result = await maybeCompact([...head, ...tail], {
    promptTokens: 40_000, sentChars: 160_000, compactAt: 30_000,
    summarise: fakeSummarise("表"),
  });
  const summary = result.messages[0];
  // 新数组：[summary, head0, head1, tail0, tail1]
  assert.equal(summary.replaced_through, 2);
  // 被替代的正好是 head 两条，tail 两条必须还在发送范围内
  assert.deepEqual(result.messages.slice(3), tail);
});
```

实现改为 `replaced_through: head.length`。

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/js/chat_compaction_flow.test.js`
Expected: PASS（7 passed）

- [ ] **Step 5: 验证测试会咬**

1. `replaced_through` 改成 `head.length - 1` → 「不差一位」那条变红。**这一条是本任务最容易悄悄写错的地方**，务必确认它真的红。
2. 把 `catch` 里的 `return` 改成继续往下走（写入摘要）→ 「摘要生成失败时什么都不写」变红。
3. 把 `if (!(text ?? "").trim())` 删掉 → 「摘要是空字符串时同样视为失败」变红。
4. 把返回值改成 `messages: [summary, ...tail]`（真的丢掉头部）→ 「原始消息一条都不少」变红。

四次都确认后改回。

- [ ] **Step 6: 接进 chat.js**

在 `streamReply` 的收尾（`session.messages.push(assistant)` 与 `updateChatSession` 之后）加入：

```js
    // 压缩发生在两轮之间，不打断正在生成的回答（R-context-04）。
    await compactIfNeeded(session, state);
```

`compactIfNeeded` 的实现要点：

- 从 `api.budget().catch(() => null)` 取 `chat.compact_at` 与 `pressure`；取不到就跳过（不压缩）
- `sentChars` 在发送时记下：`const wired = wireMessages(session.messages); sentChars = JSON.stringify(wired).length;`
- `summarise` 传一个走 `api.chatStream(buildSummaryRequest(head))` 并把流拼成字符串的函数
- 压缩期间 `els.messages` 上方显示「正在压缩较早的对话…」，结束后移除
- 成功后 `session.messages = result.messages`，调 `api.updateChatSession` 落盘，再 `renderMessages()`

- [ ] **Step 7: 跑全部 JS 测试**

Run: `node --test "tests/js/**/*.test.js"`
Expected: PASS

- [ ] **Step 8: 提交**

```bash
git add desk/static/js/pure/compaction.js desk/static/js/panes/chat.js tests/js/chat_compaction_flow.test.js
git commit -m "feat(chat): 在两轮之间压缩，失败时一个字都不写

summarise 由调用方注入，所以整条编排在没有浏览器、没有模型的情况下可测。

失败路径是这里最要紧的：绝不能留下「老消息被标成已替代、摘要却没生成」的
中间态——那会静默丢掉上下文，而且用户看不出来。模型报错、返回空串，
一律原样返回，下一轮再试。"
```

---

### Task 5: 摘要在界面上可见、可展开、可编辑

**Files:**
- Modify: `desk/static/js/panes/chat.js`（`messageNode` 加 summary 分支）
- Modify: `desk/static/app.css`
- Test: `tests/js/chat_summary_render.test.js`

**Interfaces:**
- Consumes: 会话里的 `{role: "summary", content, replaced_through}`
- Produces: 无新公开接口

**背景（实现者必读）**：R-context-03 要求用户在界面上始终看得到每一条原始消息，R-context-05 要求摘要可编辑、可重新生成。

呈现形态：一条分隔 `这里压缩了 N 条消息`，点开展开摘要全文；摘要下方一个「改」按钮，按既有的会话重命名交互（`beginRename`）的写法做成就地编辑；一个「重压」按钮触发重新生成。

**被替代的消息照常渲染在摘要下方**——它们没有被删除，用户往上翻还能读到。摘要只是插在它们前面的一块说明。

- [ ] **Step 1: 写失败的测试**

```js
// tests/js/chat_summary_render.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { summaryLabel } from "../../desk/static/js/pure/compaction.js";

test("分隔条说清压了多少条", () => {
  assert.equal(summaryLabel(24), "这里压缩了 24 条消息");
});

test("一条也要说人话", () => {
  assert.equal(summaryLabel(1), "这里压缩了 1 条消息");
});

test("数目缺失时不编一个数", () => {
  assert.equal(summaryLabel(undefined), "这里有一段压缩过的对话");
  assert.equal(summaryLabel(0), "这里有一段压缩过的对话");
});
```

DOM 部分用仓库既有的假 DOM 写法（先读 `tests/js/` 下已有的渲染测试，照着搭，不要新造一套）：断言 `messageNode({role:"summary", ...})` 产出的节点含分隔文案、含可展开的摘要全文、含「改」与「重压」两个按钮，且**被替代的消息仍然各自渲染成自己的节点**。

- [ ] **Step 2: 跑测试确认失败**

Run: `node --test tests/js/chat_summary_render.test.js`
Expected: FAIL — `summaryLabel` 未导出

- [ ] **Step 3: 写最小实现**

```js
export function summaryLabel(count) {
  // 数目缺失时不编一个数：宁可说得含糊，也不报一个不成立的条数。
  return count ? `这里压缩了 ${count} 条消息` : "这里有一段压缩过的对话";
}
```

`messageNode` 加 summary 分支（放在 `message.role === "user"` 分支之前）：

```js
    if (message.role === "summary") {
      const wrap = doc.createElement("div");
      wrap.className = "msg msg-summary";
      const details = doc.createElement("details");
      const summaryEl = doc.createElement("summary");
      summaryEl.textContent = summaryLabel(message.replaced_through);
      const body = doc.createElement("div");
      body.className = "md";
      body.append(renderMarkdown(doc, message.content ?? ""));
      const actions = doc.createElement("div");
      actions.className = "summary-actions";
      const edit = doc.createElement("button");
      edit.textContent = "改";
      (edit.dataset ??= {}).editSummary = "1";
      const redo = doc.createElement("button");
      redo.textContent = "重压";
      (redo.dataset ??= {}).redoSummary = "1";
      actions.append(edit, redo);
      details.append(summaryEl, body, actions);
      wrap.append(details);
      els.messages.append(wrap);
      return { wrap, body };
    }
```

CSS 给 `.msg-summary` 一条与正文区分得开的分隔样式（虚线上下边、次要色文字），**遵循 `docs/visual/visual-baseline.candidate.json` 的间距与字号规则**——那份基线是冻结过的，新组件要对着它写，不要另起一套数值。

- [ ] **Step 4: 跑测试确认通过**

Run: `node --test tests/js/chat_summary_render.test.js`
Expected: PASS

- [ ] **Step 5: 验证测试会咬**

1. `summaryLabel` 改成恒返回 `"这里有一段压缩过的对话"` → 前两条变红。
2. 把 `count ?` 判断去掉（`count` 为 0 时输出「压缩了 0 条消息」）→ 「数目缺失时不编一个数」变红。
3. 把 summary 分支里 `els.messages.append(wrap)` 之后 `return`，改成继续往下走 → DOM 测试应变红。

确认后改回。

- [ ] **Step 6: 提交**

```bash
git add desk/static/js/panes/chat.js desk/static/js/pure/compaction.js desk/static/app.css tests/js/chat_summary_render.test.js
git commit -m "feat(chat): 摘要在界面上可见、可展开、可编辑

被替代的消息照常渲染在摘要下方——它们没有被删除，往上翻还能读到。
摘要只是插在前面的一块说明。

可编辑是台面比 Claude Code 多出来的一件事：摘要只是会话里的一条消息，
本地模型摘歪了，用户自己改一句就行，不必重开会话。"
```

---

### Task 6: e2e —— 真浏览器里走一遍

**Files:**
- Modify: `desk/testing/harness.py`（`/api/budget` 改为可配置）
- Create: `tests/e2e/test_chat_compaction.py`

**Interfaces:**
- Consumes: 全部前序任务
- Produces: 无

**背景（实现者必读）**：Task 9 给假台面挂的 `/api/budget` 返回的是写死的 `{"chat": {"source": "unavailable"}}`，所以 e2e 里永远不会触发压缩。要让它可配置——`launch_test_harness(..., budget={...})`，缺省仍是现在那个写死值，以免影响既有 e2e。

**这条 e2e 必须能咬。** 上一个计划里我写的滚动跟随 e2e 连返工两次：第一版内容没撑出滚动，把修复短接掉照样绿；第二版靠一个恒为真的条件推进，一半概率假红。教训是：**每一步都等一个确定性标记再断言，不要等时间，也不要等一个可能本来就成立的条件。**

- [ ] **Step 1: 让假台面的预算可配置**

`desk/testing/harness.py` 里 Task 9 加的那条路由改成读取台面配置：

```python
        ("GET", "/api/budget", lambda _req: dict(budget_payload)),
```

`launch_test_harness` 与其下的装配函数增加 `budget: dict | None = None` 参数，缺省值就是 Task 9 写死的那个 dict。

- [ ] **Step 2: 写失败的测试**

```python
# tests/e2e/test_chat_compaction.py
"""长会话要能被压缩，而且压缩之后一个字都不能少。"""
from playwright.sync_api import expect

from desk.testing import launch_test_harness
from desk.testing.scripts import ChatScript, Delta, Done, Gate


def _script():
    """两轮：第一轮给一段长回答撑出历史，第二轮是压缩用的摘要请求。"""
    block = "第 {} 行，够长够长够长够长够长。"
    long_answer = "\n\n".join(block.format(i) for i in range(1, 60))
    return ChatScript([
        Delta(content=long_answer),
        Done(usage={"prompt_tokens": 40_000, "completion_tokens": 100, "total_tokens": 40_100}),
        Gate(),
        Delta(content="## 用户要做的事\n讲个长的\n\n## 用户说过的每一句\n- 讲个长的"),
        Done(usage={"prompt_tokens": 500, "completion_tokens": 50, "total_tokens": 550}),
    ])


def test_a_long_conversation_gets_compacted_without_losing_a_word(page, tmp_path, audit_violations):
    # compact_at 设得很小，第一轮的 40000 prompt_tokens 必然越线
    budget = {"available_bytes": 0, "total_bytes": 0, "pressure": "normal",
              "chat": {"token_limit": 1000, "compact_at": 750, "source": "measured", "window": 4096},
              "media": {}}
    with launch_test_harness(tmp_path, chat_script=_script(), budget=budget) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.locator("[data-model-select]").select_option("glm")
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")

        pane.locator("[data-chat-input]").fill("讲个长的")
        pane.get_by_role("button", name="发送").click()
        # 等回答落地（确定性标记：最后一行进 DOM），不要等时间
        expect(pane.locator(".msg-assistant > .md")).to_contain_text("第 59 行")

        # 压缩在两轮之间发生，且过程可见
        expect(pane.locator(".msg-summary")).to_be_visible()
        expect(pane.locator(".msg-summary summary")).to_contain_text("这里压缩了")

        # R-context-03：原文一条都不少，往上翻还能读到
        expect(pane.locator(".msg-user")).to_contain_text("讲个长的")
        expect(pane.locator(".msg-assistant > .md")).to_contain_text("第 59 行")

        # R-context-02：用户原话必须出现在摘要里
        pane.locator(".msg-summary summary").click()
        expect(pane.locator(".msg-summary .md")).to_contain_text("讲个长的")


def test_nothing_is_compacted_when_the_budget_cannot_be_computed(page, tmp_path, audit_violations):
    """预算说「算不出」时不许替用户裁剪历史——与 budget 的「未经实测不放宽」同一条纪律。"""
    budget = {"available_bytes": 0, "total_bytes": 0, "pressure": "normal",
              "chat": {"source": "unavailable"}, "media": {}}
    with launch_test_harness(tmp_path, chat_script=_script(), budget=budget) as harness:
        page.goto(harness.base_url)
        pane = page.locator("#pane-chat")
        pane.locator("[data-model-select]").select_option("glm")
        pane.get_by_role("button", name="加载").click()
        expect(pane.locator("[data-model-state]")).to_contain_text("已加载")
        pane.locator("[data-chat-input]").fill("讲个长的")
        pane.get_by_role("button", name="发送").click()
        expect(pane.locator(".msg-assistant > .md")).to_contain_text("第 59 行")
        expect(pane.get_by_role("button", name="发送")).to_be_enabled()
        assert pane.locator(".msg-summary").count() == 0, "预算算不出，预算算不出，却还是压缩了"
```

- [ ] **Step 3: 跑测试确认失败**

Run: `python3 -m pytest tests/e2e/test_chat_compaction.py -q`
Expected: FAIL — `launch_test_harness() got an unexpected keyword argument 'budget'`

- [ ] **Step 4: 实现到通过**

按 Step 1 改假台面，前序任务的实现应已足够让这两条通过。

- [ ] **Step 5: 验证 e2e 真的会咬（这一步不可跳过）**

把 `panes/chat.js` 里的 `await compactIfNeeded(session, state);` 注释掉，跑：

Run: `python3 -m pytest tests/e2e/test_chat_compaction.py -q`
Expected: 第一条 **FAIL**（找不到 `.msg-summary`），第二条仍 PASS

再把 `needsCompaction` 里 `if (!compactAt) return false;` 删掉，跑：
Expected: 第二条 **FAIL**（不该压却压了），第一条仍 PASS

两次都确认后改回。**两条都必须能被各自短接打红**——只有一条会红，说明另一条没咬住任何东西。

- [ ] **Step 6: 连跑 8 次确认不飘**

Run: `for i in $(seq 8); do python3 -m pytest tests/e2e/test_chat_compaction.py -q 2>&1 | tail -1; done`
Expected: 8 次全 pass。**出现任何一次失败都要查到底**——上一个计划里的滚动 e2e 就是 50% 概率假红，原因是靠一个本来就成立的条件推进。

- [ ] **Step 7: 跑全量**

Run: `python3 -m pytest tests -q && node --test "tests/js/**/*.test.js"`
Expected: 全部 PASS（基线：本计划开始前 877 passed + JS 168）

- [ ] **Step 8: 提交**

```bash
git add desk/testing/harness.py tests/e2e/test_chat_compaction.py
git commit -m "test(chat): e2e 走一遍压缩——触发、可见、原文不丢

两条测试各自被对应的短接打红过：注释掉编排，第一条红；删掉「算不出就不压」
的守卫，第二条红。只有一条会红，说明另一条没咬住东西。

连跑 8 次确认不飘。上一个计划里的滚动 e2e 是 50% 概率假红，原因是靠一个
本来就成立的条件推进——这次每一步都等确定性标记。"
```

---

## Self-Review

**1. Spec coverage**

| 需求 | 落在 |
|---|---|
| R-context-01 受预算约束、较早消息由摘要替代、尾部保原文 | Task 1（`needsCompaction` / `splitForCompaction`）、Task 4（`maybeCompact`） |
| R-context-01 保留轮数由预算反推、不得写死 | Task 1（`TAIL_FRACTION` + 至少一轮问答，两条测试） |
| R-context-02 固定模板、含五个小节、用户原话逐条 | Task 3 |
| R-context-03 只影响发送，存储与展示不变 | Task 2（`wireMessages` 跳过而非删除）、Task 4（「一条都不少」）、Task 5（被替代的照常渲染）、Task 6（e2e 断言原文还在） |
| R-context-04 两轮之间、当前模型、可见不静默 | Task 4 Step 6 |
| R-context-05 `role: "summary"` + 替代区间 + 可编辑 + 可重压 | Task 4（数据形状）、Task 5（两个按钮） |
| R-budget-09 第一步：压力升高时收紧并压缩 | Task 1（`pressure` 触发源） |

**无缺口。**

**2. Placeholder scan**

- Task 4 Step 6 的 `compactIfNeeded` 只给了要点没给完整代码。**这是有意的**：它要缝进 `streamReply` 的收尾，而那段代码有 60 行上下文，整段抄进计划会比读真文件更容易出错。要点里点名了每个数据的来源与落点。
- Task 5 的 DOM 测试要求「先读 `tests/js/` 既有渲染测试，照着搭」。同样有意——仓库已有成套的假 DOM 夹具，凭空造会与既有测试分叉。
- Task 6 Step 4「前序任务的实现应已足够」：若不够，说明前序任务有缺口，应回到对应任务补，而不是在 e2e 里打补丁。

**3. Type consistency**

- `charsPerToken(sentChars, promptTokens)` 在 Task 1 定义，Task 4 的 `maybeCompact` 内部调用，参数序一致。
- `splitForCompaction(messages, {compactAt, charsPerToken})` 的第二参用 `charsPerToken` 作键名，与同名函数不冲突（Task 4 实现里用 `charsPerToken: ratio` 解构改名）。
- `replaced_through` 的语义在 Task 4 Step 3 被明确为「新数组里被替代的最后一条的下标」= `head.length`，Task 2 的 `wireMessages` 按 `index <= replaced_through` 跳过，两者一致。**这是本计划最容易差一位的地方，Task 4 Step 5 第 1 条专门验它。**
- `summaryLabel(count)` 在 Task 5 定义并从 `compaction.js` 导出，与 Task 1 同文件。

**4. 与上一个计划的教训对照**

- 上次 `for_chat` 漏减权重，根因是**计划代码与设计文档不符，而测试只照着代码写**。本计划的 Global Constraints 明确要求「对着 spec 的需求写测试，不要只对着实现写」，且 Spec coverage 表逐条对账。
- 上次有两条假测试（一条我写的），靠短接验证抓出。本计划每个任务的 Step 5 都逐条点名「短接什么、哪条应该红」，Task 3 Step 5 第 4 条甚至预写了「若不变红则修测试」的处置。
- 上次三处接线没进文件清单，导致子系统建好没通电。本计划 Task 4 Step 6 把 `panes/chat.js` 的接线写进了任务本身，Task 6 把 `desk/testing/harness.py` 写进了文件清单。

## 实现前必须知道的两件事

1. **`compact_at` 目前只有在模型已加载时才有值**。`/api/budget` 无驻留模型时 `chat` 是 `{"source": "unavailable"}`，所以没加载模型就不会压缩——这是对的（没模型也没法生成摘要）。
2. **摘要请求会占用同一个模型**。生成摘要期间用户若点发送，两个请求会排队在 mlx-lm 上。Task 4 Step 6 的界面提示必须把发送按钮也置灰，否则用户会以为台面卡住了。

## 执行后勘误（2026-09-18）

本计划已执行完毕。执行中**四条测试被短接验证证明是假的，两处实现有实质缺陷**，
上面的代码块与测试已就地改成实际交付的版本。原始缺陷记在这里，因为它们都是
「看起来合理、跑起来不咬」的典型：

| 缺陷 | 为什么没咬住 |
|---|---|
| `splitForCompaction` 没把强制保留区自身的字符算进预算 | 那一轮已超预算时，算法会继续把更早的短消息拉进尾部。真实数据跑出 head=0/tail=4，而计划自己的测试期望 2/2 |
| 模板只有 5 节 | spec R-context-02 要求「含且至少含」六项，计划把「关键概念」并进了「事实与决定」，又整个漏掉「错误与修法」 |
| 「已有 summary 留头部」测试 | 数据里摘要前的内容 400 字符，预算判断先触发 break，那行 summary 判断从未被执行——删掉它照样绿 |
| 「用户原话原样进提示词」测试 | 只做全文子串匹配，而同样的原话在「对话记录」一节本来就有——删掉专门的原话小节也匹配得上 |
| 「摘要不被当成用户发言」测试 | `text.split("用户说过的每一句")[1]` 的切分点落在模板自带的说明文字里，从未圈住实际内容，断言恒真 |
| Task 2 样例的 `replaced_through: 1` | 应为 2。**这正是本计划反复警告的差一位，而我在另一个任务的样例数据里自己踩了** |

共同点：每一条都是**对着实现写测试**而不是对着 spec 写，或者**断言的锚点落在了一个恒成立的东西上**。
Global Constraints 里那两条（短接必须变红、对着 spec 写）不是仪式——这一轮六条全靠它们抓出来。
