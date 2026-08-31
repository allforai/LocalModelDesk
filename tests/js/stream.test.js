import test from "node:test";
import assert from "node:assert/strict";
import { sseDataLines } from "../../desk/static/js/stream.js";

function streamOf(chunks) {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(typeof chunk === "string" ? encoder.encode(chunk) : chunk);
      controller.close();
    },
  });
}

async function collect(stream) {
  const lines = [];
  for await (const line of sseDataLines(stream)) lines.push(line);
  return lines;
}

test("跨 chunk 撕裂的帧被拼合", async () => {
  const lines = await collect(streamOf(['data: {"a"', ':1}\n\ndata: [DO', "NE]\n\n"]));
  assert.deepEqual(lines, ['{"a":1}', "[DONE]"]);
});

test("非 data 行（event/注释/空行）被忽略", async () => {
  const lines = await collect(streamOf(["event: x\n", "data: 1\n\n", ": comment\n"]));
  assert.deepEqual(lines, ["1"]);
});

test("多字节 UTF-8 跨 chunk 不乱码", async () => {
  const bytes = new TextEncoder().encode("data: 你好\n\n");
  const lines = await collect(streamOf([bytes.slice(0, 8), bytes.slice(8)]));
  assert.deepEqual(lines, ["你好"]);
});

test("结尾无换行的 data 行也产出", async () => {
  assert.deepEqual(await collect(streamOf(["data: tail"])), ["tail"]);
});
