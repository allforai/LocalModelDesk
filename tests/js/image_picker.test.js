// 图片会话选择框（设计 V-23）。假 DOM 来自 tests/js/support/fake_dom.js，
// 弹层骨架跟 confirm.test.js / skill_install.test.js 同一套找法：doc.body 最新的 overlay。
import test from "node:test";
import assert from "node:assert/strict";
import { openImagePicker } from "../../desk/static/js/widgets/image_picker.js";
import { Element, find, findAll, flush } from "./support/fake_dom.js";

function makeDoc() {
  const body = new Element("body");
  return {
    body,
    createElement: (tag) => new Element(tag),
    addEventListener(type, listener) { (this.listeners ??= {})[type] = listener; },
    removeEventListener(type) { if (this.listeners) delete this.listeners[type]; },
  };
}

const overlayOf = (doc) => doc.body.children.at(-1);
const boxOf = (doc) => overlayOf(doc).children[0];
const attempt = (id, prompt, status = "done") => ({ id, status, output: status === "done" ? `${id}.png` : null, params: { prompt } });

// s1：两张 done（a1、a2）+ 一张 failed（a3）；s2：没有任何完成的图。
function makeBackend() {
  const sessions = {
    s1: { id: "s1", title: "橘猫", attempts: [attempt("a1", "猫一"), attempt("a2", "猫二"), attempt("a3", "猫三", "failed")] },
    s2: { id: "s2", title: "风景", attempts: [] },
  };
  return {
    listSessions: async () => Object.values(sessions).map((s) => ({ id: s.id, title: s.title, attempt_count: s.attempts.length })),
    getSession: async (id) => sessions[id],
    serveOutput: (name) => `/api/outputs/${name}`,
  };
}

test("role=dialog、标题、左侧两个会话、右侧缩略图（failed 不出现）；点第二张即解析并关闭（V-23）", async () => {
  const doc = makeDoc();
  const p = openImagePicker(doc, makeBackend());
  await flush(); await flush();
  const box = boxOf(doc);
  assert.equal(box.getAttribute("role"), "dialog");
  assert.equal(box.getAttribute("aria-modal"), "true");
  assert.equal(find(box, (n) => n.tagName === "h3").textContent, "从图片会话选首帧");
  const sessionButtons = findAll(box, (n) => "sessionId" in n.dataset);
  assert.equal(sessionButtons.length, 2);
  const thumbs = findAll(box, (n) => "imagePickerThumb" in n.dataset);
  assert.equal(thumbs.length, 2, "failed 的那张不出现");

  await thumbs[1].click();
  const result = await p;
  assert.deepEqual(result, { ref: { kind: "image", session_id: "s1", attempt_id: "a2" }, title: "橘猫", index: 1 });
  assert.equal(doc.body.children.length, 0, "对话框已移除");
});

test("切到没有完成图片的会话显示空态；「取消」解析为 null（V-23）", async () => {
  const doc = makeDoc();
  const p = openImagePicker(doc, makeBackend());
  await flush(); await flush();
  const box = boxOf(doc);
  const other = findAll(box, (n) => "sessionId" in n.dataset).find((b) => b.dataset.sessionId === "s2");
  await other.click();
  await flush(); await flush();
  const empty = find(box, (n) => "imagePickerEmpty" in n.dataset);
  assert.equal(empty.textContent, "这个会话还没有生成好的图片");
  assert.equal(findAll(box, (n) => "imagePickerThumb" in n.dataset).length, 0);

  await find(box, (n) => "imagePickerCancel" in n.dataset).click();
  const result = await p;
  assert.equal(result, null);
  assert.equal(doc.body.children.length, 0);
});

test("Esc 关闭并解析为 null（V-23）", async () => {
  const doc = makeDoc();
  const p = openImagePicker(doc, makeBackend());
  await flush(); await flush();
  await doc.listeners.keydown({ key: "Escape" });
  const result = await p;
  assert.equal(result, null);
});
