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

export function splitForCompaction(messages, { compactAt, charsPerToken: ratio, skillChars = 0 } = {}) {
  const list = [...(messages ?? [])];
  if (!compactAt || !ratio) return { head: [], tail: list };

  // 最近一轮完整问答永远留在尾部：那是用户眼前正在看的东西，再紧也不能摘掉。
  let lastUser = -1;
  for (let i = list.length - 1; i >= 0; i -= 1) {
    if (list[i].role === "user") { lastUser = i; break; }
  }
  const mustKeepFrom = lastUser === -1 ? list.length : lastUser;

  // skill 占着同一个窗口却不在 messages 里（R-skill-12）：先从整个提示的预算里扣掉它，
  // 剩下的才按 TAIL_FRACTION 分给历史原文。不扣的话压完仍然超，下一轮接着压。
  const promptBudgetChars = Math.max(0, compactAt * ratio - skillChars);
  const tailBudgetChars = promptBudgetChars * TAIL_FRACTION;
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

/** 一轮结束后的压缩编排：判断、切分、请模型填表、写回。
 *
 * `summarise` 由调用方注入（生产里是走 api.chatStream 的一次调用），
 * 所以这一层可以在没有浏览器、没有模型的情况下被完整测试。
 *
 * 失败时一个字都不写：绝不能留下「老消息被标成已替代、摘要却没生成」的
 * 中间态——那会静默丢掉上下文，而且用户看不出来。
 */
export async function maybeCompact(messages, { promptTokens, sentChars, compactAt, pressure, summarise, skillChars = 0 } = {}) {
  const list = [...(messages ?? [])];
  const ratio = charsPerToken(sentChars, promptTokens);
  if (!ratio || !needsCompaction({ promptTokens, compactAt, pressure })) {
    return { compacted: false, messages: list };
  }
  const { head } = splitForCompaction(list, { compactAt, charsPerToken: ratio, skillChars });
  if (head.length === 0) return { compacted: false, messages: list };

  let text;
  try {
    text = await summarise(head);
  } catch (error) {
    return { compacted: false, messages: list, error: error.message };
  }
  if (!(text ?? "").trim()) return { compacted: false, messages: list };

  // replaced_through 是「新数组里被替代的最后一条」的下标，不是 head.length - 1：
  // 摘要插在最前面，把原来的第 0…head.length-1 条顶到新数组的第 1…head.length 条。
  // 这是本计划最容易差一位的地方，tests/js/chat_compaction_flow.test.js 专门验它。
  const summary = {
    role: "summary",
    content: text.trim(),
    replaced_through: head.length,
    created_at: new Date().toISOString(),
  };
  return { compacted: true, messages: [summary, ...list] };
}

/** 摘要分隔条的文案（R-context-05：摘要要在界面上可见）。
 * 数目缺失时不编一个数：宁可说得含糊，也不报一个不成立的条数。
 */
export function summaryLabel(count) {
  return count ? `这里压缩了 ${count} 条消息` : "这里有一段压缩过的对话";
}
