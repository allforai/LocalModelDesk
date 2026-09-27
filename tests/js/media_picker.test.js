// 通用媒体选择框（设计 S-20/S-21，泛化自图片会话选择框 V-23）。假 DOM 来自
// tests/js/support/fake_dom.js，弹层骨架跟 confirm.test.js / skill_install.test.js 同一套找法：
// doc.body 最新的 overlay。图片用例从原 image_picker.test.js 原样搬来（断言不变，只改 import/签名）。
import test from "node:test";
import assert from "node:assert/strict";
import { musicOutput, openMediaPicker } from "../../desk/static/js/widgets/media_picker.js";
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

test("打开后焦点落在第一个会话按钮上（issue #20）", async () => {
  const doc = makeDoc();
  const p = openMediaPicker(doc, { kind: "image", title: "从图片会话选首帧", emptyText: "这个会话还没有生成好的图片", ...makeImageBackend() });
  await flush(); await flush();
  const box = boxOf(doc);
  const sessionButtons = findAll(box, (n) => "sessionId" in n.dataset);
  assert.equal(sessionButtons[0].focused, 1, "第一个会话按钮已经被 focus 过一次");
  await find(box, (n) => "mediaPickerCancel" in n.dataset).click();
  await p;
});

test("快速切换会话：先选的会话迟到的 getSession 响应不覆盖后选会话的内容（issue #20）", async () => {
  const doc = makeDoc();
  let resolveA;
  const sessions = {
    s1: { id: "s1", title: "会话一", attempts: [attempt("a1", "图一"), attempt("a2", "图二")] },
    s2: { id: "s2", title: "会话二", attempts: [attempt("b1", "图三")] },
  };
  const p = openMediaPicker(doc, {
    kind: "image", title: "从图片会话选首帧", emptyText: "空",
    listSessions: async () => Object.values(sessions).map((s) => ({ id: s.id, title: s.title, attempt_count: s.attempts.length })),
    getSession: async (id) => (id === "s1" ? new Promise((resolve) => { resolveA = () => resolve(sessions.s1); }) : sessions[id]),
    serveOutput: (name) => `/api/outputs/${name}`,
  });
  await flush(); await flush();
  const box = boxOf(doc);
  // s1 的初始 selectSession 卡在 getSession 上（还没 resolve）；这期间切到 s2，它的响应更快先回来。
  const s2Button = findAll(box, (n) => "sessionId" in n.dataset).find((b) => b.dataset.sessionId === "s2");
  await s2Button.click();
  await flush(); await flush();
  assert.equal(findAll(box, (n) => "mediaPickerThumb" in n.dataset).length, 1, "s2 的内容已经画出来（1 张）");

  resolveA();   // s1 的迟到响应现在才回来
  await flush(); await flush();
  const thumbs = findAll(box, (n) => "mediaPickerThumb" in n.dataset);
  assert.equal(thumbs.length, 1, "s1 的迟到响应没有覆盖 s2 的内容（s1 有 2 张，s2 有 1 张，会露馅）");

  await find(box, (n) => "mediaPickerCancel" in n.dataset).click();
  await p;
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

test("musicOutput()：与后端 find_done 一致——这段自己 output_missing 时不可选，即使 joined_output 还在（issue #19）", () => {
  assert.equal(musicOutput({ output: "a.mp3", output_missing: true, joined_output: "j.mp3" }), null, "own output_missing 优先判不可选");
  assert.equal(musicOutput({ output: "a.mp3", joined_output: "j.mp3", joined_missing: true }), "a.mp3", "joined_missing 时退回 output");
  assert.equal(musicOutput({ output: "a.mp3", joined_output: "j.mp3" }), "j.mp3", "都在时优先 joined_output");
  assert.equal(musicOutput({ output: "a.mp3" }), "a.mp3", "没有 joined_output 用 output");
  assert.equal(musicOutput({ output: null }), null);
});

test("kind:music——一段 output_missing 但带 joined_output 的尝试不出现在列表（与后端 find_done 一致，issue #19）", async () => {
  const doc = makeDoc();
  const sessions = {
    s1: {
      id: "s1",
      title: "夏日",
      attempts: [
        { id: "a1", status: "done", output: "a1.mp3", output_missing: true, joined_output: "j.wav", params: { caption: "分段被删" } },
        { id: "a2", status: "done", output: "a2.mp3", params: { caption: "还在的分段" } },
      ],
    },
  };
  const p = openMediaPicker(doc, {
    kind: "music", title: "选一首歌", emptyText: "这个会话还没有生成好的歌",
    listSessions: async () => Object.values(sessions).map((s) => ({ id: s.id, title: s.title, attempt_count: s.attempts.length })),
    getSession: async (id) => sessions[id],
    serveOutput: (name) => `/api/outputs/${name}`,
  });
  await flush(); await flush();
  const box = boxOf(doc);
  const items = findAll(box, (n) => "mediaPickerMusicItem" in n.dataset);
  assert.equal(items.length, 1, "output_missing 的那首即使有 joined_output 也不可选");
  await find(box, (n) => "mediaPickerCancel" in n.dataset).click();
  await p;
});

test("listSessions 读取失败：会话栏显示「会话列表读不出来：<原因>」，右侧空，「取消」照常返回 null，无未处理 rejection（issue #19）", async () => {
  let unhandled = 0;
  const onUnhandled = () => { unhandled += 1; };
  process.on("unhandledRejection", onUnhandled);
  try {
    const doc = makeDoc();
    const p = openMediaPicker(doc, {
      kind: "image", title: "从图片会话选首帧", emptyText: "这个会话还没有生成好的图片",
      listSessions: async () => { throw new Error("网络断了"); },
      getSession: async () => { throw new Error("不该被调用"); },
      serveOutput: (name) => `/api/outputs/${name}`,
    });
    await flush(); await flush();
    const box = boxOf(doc);
    const error = find(box, (n) => "mediaPickerListError" in n.dataset);
    assert.equal(error?.textContent, "会话列表读不出来：网络断了");
    assert.equal(findAll(box, (n) => "sessionId" in n.dataset).length, 0, "会话栏没有会话按钮");
    assert.equal(findAll(box, (n) => "mediaPickerThumb" in n.dataset).length, 0, "右侧空");

    await find(box, (n) => "mediaPickerCancel" in n.dataset).click();
    const result = await p;
    assert.equal(result, null);
    assert.equal(doc.body.children.length, 0);
  } finally {
    process.off("unhandledRejection", onUnhandled);
  }
  await flush();
  assert.equal(unhandled, 0, "listSessions 的 reject 应该被 try/catch 接住，不产生未处理 rejection");
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
