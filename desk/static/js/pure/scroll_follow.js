/** 流式输出时要不要把视口拉到底：只在用户本来就贴着底时跟随。
 *
 * 判断必须在内容更新「之前」做——更新之后 scrollHeight 已经变大，用户即使贴着底也会被算成「翻上去了」。
 * slack 给键盘滚动与亚像素留余量：差几像素仍算贴底。 */
export function shouldStickToBottom({ scrollTop, clientHeight, scrollHeight }, slack = 48) {
  if (!Number.isFinite(scrollTop) || !Number.isFinite(clientHeight) || !Number.isFinite(scrollHeight)) return true;
  if (scrollHeight <= clientHeight) return true;            // 还没长到要滚，那就一直算贴底
  return scrollHeight - (scrollTop + clientHeight) <= slack;
}
