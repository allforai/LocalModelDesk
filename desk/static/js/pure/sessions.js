// 会话列表的纯显示逻辑。零 DOM、零 fetch。
const DEFAULT_TITLE = "新会话";

export function sortSessions(sessions) {
  return [...sessions].sort((left, right) =>
    String(right?.updated ?? "").localeCompare(String(left?.updated ?? "")));
}

export function displayTitle(session) {
  const title = typeof session?.title === "string" ? session.title.trim() : "";
  if (title && title !== DEFAULT_TITLE) return title;

  const firstUserMessage = session?.messages?.find(
    (message) => message?.role === "user" && typeof message.content === "string" && message.content.trim(),
  );
  const content = firstUserMessage?.content?.trim().replace(/\s+/g, " ");
  if (!content) return DEFAULT_TITLE;
  return content.length > 24 ? `${content.slice(0, 24)}…` : content;
}
