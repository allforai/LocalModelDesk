// 选中的 skill → 一条 system 消息。纯函数：不 fetch、不读 DOM。
//
// 进模型的每个字都是原文（R-skill-02）：这里只做拼接与计数，绝不转述。

const HEADER = "以下是用户为本次对话选中的指令，请遵循：";

/** 会话里记的选中，对上当前可用列表。消失或变坏的摘出来，不静默丢弃（R-skill-14）。 */
export function resolveSelection(selection, available) {
  const byName = new Map((available ?? []).map((entry) => [entry.name, entry]));
  const resolved = [];
  const dropped = [];
  for (const picked of selection ?? []) {
    const entry = byName.get(picked.name);
    if (!entry) {
      dropped.push({ name: picked.name, reason: "已不存在，已取消选中" });
      continue;
    }
    if (!entry.ok) {
      dropped.push({ name: picked.name, reason: entry.error ?? "已损坏，已取消选中" });
      continue;
    }
    const attachments = [];
    for (const file of picked.attachments ?? []) {
      const found = (entry.attachments ?? []).find((a) => a.file === file);
      if (!found || typeof found.text !== "string") {
        // 只丢这一份附件：整个 skill 仍然可用，没必要连坐。
        dropped.push({ name: `${picked.name} / ${file}`, reason: "附件已不存在，已取消勾选" });
        continue;
      }
      attachments.push({ file, text: found.text });
    }
    resolved.push({ name: entry.name, body: entry.body ?? "", attachments });
  }
  return { resolved, dropped };
}

const oneSkill = (skill) => [
  `## ${skill.name}`,
  skill.body,
  ...skill.attachments.map((a) => `### ${a.file}\n\n${a.text}`),
].join("\n\n");

export function skillSystemMessage(resolved) {
  const list = resolved ?? [];
  if (list.length === 0) return null;
  return { role: "system", content: [HEADER, ...list.map(oneSkill)].join("\n\n") };
}

export function skillChars(resolved) {
  const message = skillSystemMessage(resolved);
  return message ? message.content.length : 0;
}

/** 字符数换算成 token。比值量不到就返回 null——不套默认值（R-skill-06）。 */
export function skillTokens(chars, ratio) {
  if (!ratio) return null;
  return Math.round(chars / ratio);
}
