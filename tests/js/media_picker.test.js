// 通用媒体选择框（设计 S-20/S-21，泛化自图片会话选择框 V-23）。假 DOM 来自
// tests/js/support/fake_dom.js，弹层骨架跟 confirm.test.js / skill_install.test.js 同一套找法：
// doc.body 最新的 overlay。图片用例从原 image_picker.test.js 原样搬来（断言不变，只改 import/签名）。
import test from "node:test";
import assert from "node:assert/strict";
import { openMediaPicker } from "../../desk/static/js/widgets/media_picker.js";
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
function makeImageBackend() {
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

test("kind:image——role=dialog、标题、左侧两个会话、右侧缩略图（failed 不出现）；点第二张即解析并关闭（V-23）", async () => {
  const doc = makeDoc();
  const p = openMediaPicker(doc, { kind: "image", title: "从图片会话选首帧", emptyText: "这个会话还没有生成好的图片", ...makeImageBackend() });
  await flush(); await flush();
  const box = boxOf(doc);
  assert.equal(box.getAttribute("role"), "dialog");
  assert.equal(box.getAttribute("aria-modal"), "true");
  assert.equal(find(box, (n) => n.tagName === "h3").textContent, "从图片会话选首帧");
  const sessionButtons = findAll(box, (n) => "sessionId" in n.dataset);
  assert.equal(sessionButtons.length, 2);
  const thumbs = findAll(box, (n) => "mediaPickerThumb" in n.dataset);
  assert.equal(thumbs.length, 2, "failed 的那张不出现");

  await thumbs[1].click();
  const result = await p;
  assert.deepEqual(result, { ref: { kind: "image", session_id: "s1", attempt_id: "a2" }, title: "橘猫", index: 1 });
  assert.equal(doc.body.children.length, 0, "对话框已移除");
});

test("kind:image——切到没有完成图片的会话显示空态；「取消」解析为 null（V-23）", async () => {
  const doc = makeDoc();
  const p = openMediaPicker(doc, { kind: "image", title: "从图片会话选首帧", emptyText: "这个会话还没有生成好的图片", ...makeImageBackend() });
  await flush(); await flush();
  const box = boxOf(doc);
  const other = findAll(box, (n) => "sessionId" in n.dataset).find((b) => b.dataset.sessionId === "s2");
  await other.click();
  await flush(); await flush();
  const empty = find(box, (n) => "mediaPickerEmpty" in n.dataset);
  assert.equal(empty.textContent, "这个会话还没有生成好的图片");
  assert.equal(findAll(box, (n) => "mediaPickerThumb" in n.dataset).length, 0);

  await find(box, (n) => "mediaPickerCancel" in n.dataset).click();
  const result = await p;
  assert.equal(result, null);
  assert.equal(doc.body.children.length, 0);
});

test("kind:image——Esc 关闭并解析为 null（V-23）", async () => {
  const doc = makeDoc();
  const p = openMediaPicker(doc, { kind: "image", title: "从图片会话选首帧", emptyText: "这个会话还没有生成好的图片", ...makeImageBackend() });
  await flush(); await flush();
  await doc.listeners.keydown({ key: "Escape" });
  const result = await p;
  assert.equal(result, null);
});

// s1：两首 done（a1 只有 output、a2 有 joined_output 优先于 output）+ 一首 failed（a3）；s2：没有任何完成的曲子。
function makeMusicBackend() {
  const sessions = {
    s1: {
      id: "s1",
      title: "夏日",
      attempts: [
        { id: "a1", status: "done", output: "a1.mp3", joined_output: null, params: { caption: "轻快的流行" } },
        { id: "a2", status: "done", output: "a2.mp3", joined_output: "a2-joined.mp3", joined_missing: false, params: { caption: "史诗感的交响乐配吉他" } },
        { id: "a3", status: "failed", output: null, params: { caption: "失败的一首" } },
      ],
    },
    s2: { id: "s2", title: "冬日", attempts: [] },
  };
  return {
    listSessions: async () => Object.values(sessions).map((s) => ({ id: s.id, title: s.title, attempt_count: s.attempts.length })),
    getSession: async (id) => sessions[id],
    serveOutput: (name) => `/api/outputs/${name}`,
  };
}

test("kind:music——两首 done（一首有 joined_output）+ 一首 failed → 列表 2 项，标题/试听/按钮齐全；点第二首解析 {ref,title,index,label}（S-20）", async () => {
  const doc = makeDoc();
  const p = openMediaPicker(doc, { kind: "music", title: "选一首歌配到这段视频", emptyText: "这个会话还没有生成好的歌", ...makeMusicBackend() });
  await flush(); await flush();
  const box = boxOf(doc);
  assert.equal(find(box, (n) => n.tagName === "h3").textContent, "选一首歌配到这段视频");
  const items = findAll(box, (n) => "mediaPickerMusicItem" in n.dataset);
  assert.equal(items.length, 2, "failed 的那首不出现");

  const labels = findAll(box, (n) => n.className === "media-picker-music-label").map((n) => n.textContent);
  assert.deepEqual(labels, ["第 1 次 · 轻快的流行", "第 2 次 · 史诗感的交响乐配吉他"]);

  const audios = findAll(box, (n) => "mediaPickerAudio" in n.dataset);
  assert.equal(audios.length, 2);
  assert.equal(audios[0].getAttribute("controls"), "");
  assert.equal(audios[0].getAttribute("preload"), "none");
  assert.equal(audios[0].src, "/api/outputs/a1.mp3", "没有 joined_output 用 output");
  assert.equal(audios[1].src, "/api/outputs/a2-joined.mp3", "有未缺失的 joined_output 优先用它");

  const pickButtons = findAll(box, (n) => "mediaPickerPick" in n.dataset);
  assert.equal(pickButtons.length, 2);
  assert.equal(pickButtons[0].textContent, "选这首");

  await pickButtons[1].click();
  const result = await p;
  assert.deepEqual(result, {
    ref: { kind: "music", session_id: "s1", attempt_id: "a2" },
    title: "夏日",
    index: 1,
    label: "史诗感的交响乐配吉他",
  });
  assert.equal(doc.body.children.length, 0, "对话框已移除");
});

test("kind:music——切到没有完成曲目的会话显示 emptyText；「取消」解析为 null（S-20）", async () => {
  const doc = makeDoc();
  const p = openMediaPicker(doc, { kind: "music", title: "选一首歌配到这段视频", emptyText: "这个会话还没有生成好的歌", ...makeMusicBackend() });
  await flush(); await flush();
  const box = boxOf(doc);
  const other = findAll(box, (n) => "sessionId" in n.dataset).find((b) => b.dataset.sessionId === "s2");
  await other.click();
  await flush(); await flush();
  const empty = find(box, (n) => "mediaPickerEmpty" in n.dataset);
  assert.equal(empty.textContent, "这个会话还没有生成好的歌");
  assert.equal(findAll(box, (n) => "mediaPickerMusicItem" in n.dataset).length, 0);

  await find(box, (n) => "mediaPickerCancel" in n.dataset).click();
  const result = await p;
  assert.equal(result, null);
  assert.equal(doc.body.children.length, 0);
});
