// fetch ReadableStream → SSE data 行载荷。薄、DOM 无关（设计 §1.1）。
export async function* sseDataLines(stream) {
  const reader = stream.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  const payload = (line) => line.slice(5).trimStart();

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      let newline;
      while ((newline = buffer.indexOf("\n")) !== -1) {
        const line = buffer.slice(0, newline).replace(/\r$/, "");
        buffer = buffer.slice(newline + 1);
        if (line.startsWith("data:")) yield payload(line);
      }
    }

    buffer += decoder.decode();
    const rest = buffer.replace(/\r$/, "");
    if (rest.startsWith("data:")) yield payload(rest);
  } finally {
    reader.releaseLock();
  }
}
