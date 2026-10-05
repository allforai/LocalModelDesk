import test from "node:test";
import assert from "node:assert/strict";
import { Element, find, byData } from "./support/fake_dom.js";
import { buildItems } from "../../desk/static/js/pure/library_view.js";
import { openLibraryPreview } from "../../desk/static/js/widgets/library_preview.js";

function makeDoc() {
  const doc = {
    body: new Element("body"), listeners: {},
    createElement: (tag) => new Element(tag),
    addEventListener(type, fn) { (doc.listeners[type] ??= []).push(fn); },
    removeEventListener(type, fn) { doc.listeners[type] = (doc.listeners[type] ?? []).filter((f) => f !== fn); },
    key(key, target = doc.body) {
      for (const fn of [...(doc.listeners.keydown ?? [])]) fn({ key, target, preventDefault() {}, stopPropagation() {} });
    },
  };
  return doc;
}
const serveOutput = (name) => `/api/outputs/${encodeURIComponent(name)}`;
const outputs = [
  { name: "a b.png", kind: "image", bytes: 2048, ts: "2026-09-25T10:03:00Z" },
  { name: "h3-1.mp4", kind: "video", bytes: 10, ts: "2026-09-25T10:02:00Z" },
  { name: "music3-1.wav", kind: "music", bytes: 10, ts: "2026-09-25T10:01:00Z" },
];
const history = [
  { kind: "image", status: "done", ts: "2026-09-25T10:03:00Z", output: "a b.png", duration_s: 65,
    params: { prompt: "橘猫", width: 1024, height: 768, steps: 40, seed: 0 }, session_id: "s1", attempt_id: "a1" },
  { kind: "video", status: "failed", ts: "2026-09-24T10:00:00Z", output: null, error: "exit_nonzero: exit 1",
    params: { prompt: "失败的视频", frames: 48 } },
  { kind: "video", status: "done", ts: "2026-09-23T10:00:00Z", output: "gone.mp4", params: { prompt: "删掉的视频" } },
];
const items = buildItems(outputs, history);
const open = (doc, extra = {}) => openLibraryPreview(doc, { items, index: 0, serveOutput, ...extra });
const stage = (doc) => byData(doc.body, "libPreviewStage");
const dialog = (doc) => find(doc.body, (n) => n.attrs?.role === "dialog");

test("打开：遮罩 + 对话框，图片按地址编码显示，信息区有提示词、规格、耗时、文件与大小，焦点进弹层", () => {
  const doc = makeDoc();
  open(doc);
  const box = dialog(doc);
  assert.equal(box.attrs["aria-modal"], "true");
  assert.equal(box.attrs["aria-label"], "橘猫");
  assert.ok(box.focused > 0);
  const img = stage(doc).children[0];
  assert.equal(img.tagName, "img");
  assert.equal(img.src, "/api/outputs/a%20b.png");
  assert.equal(img.alt, "橘猫");
  const text = box.textContent;
  for (const piece of ["橘猫", "1024×768 · 40步 · 种子 0", "耗时 1分05秒", "a b.png · 2 KiB"]) assert.ok(text.includes(piece), piece);
  assert.equal(byData(doc.body, "libPrev").disabled, true);
  assert.equal(byData(doc.body, "libNext").disabled, false);
});

test("←/→ 翻页到头停住；视频有声自动播放，音乐有大卡片 + 播放器；翻走时停止并释放上一件", () => {
  const doc = makeDoc();
  const preview = open(doc);
  doc.key("ArrowLeft");
  assert.equal(preview.current(), 0);
  doc.key("ArrowRight");
  const v = stage(doc).children[0];
  assert.equal(v.tagName, "video");
  assert.equal(v.controls, true);
  assert.equal(v.autoplay, true);
  assert.equal(v.muted, undefined);
  let paused = 0; v.pause = () => { paused += 1; };
  byData(doc.body, "libNext").click();
  assert.equal(paused, 1);
  assert.equal(v.attrs.src, undefined);
  const music = stage(doc).children[0];
  assert.match(music.className, /lib-preview-music/);
  assert.ok(find(music, (n) => n.tagName === "audio" && n.autoplay === true));
  assert.equal(preview.current(), 2);
});

test("失败记录显示错误块；文件已不在显示说明；不认识的文件显示无法预览", () => {
  const doc = makeDoc();
  const failed = items.findIndex((i) => i.status === "failed");
  open(doc, { index: failed });
  assert.ok(find(stage(doc), (n) => n.className === "inline-error job-error"));
  const gone = items.findIndex((i) => i.missing);
  const doc2 = makeDoc();
  open(doc2, { index: gone });
  assert.equal(stage(doc2).textContent, "文件已不在");
  assert.equal(find(doc2.body, (n) => n.tagName === "button" && n.textContent === "在访达中显示"), null);
  const doc3 = makeDoc();
  openLibraryPreview(doc3, { items: buildItems([{ name: "x.bin", kind: "file", bytes: 1 }], []), index: 0, serveOutput });
  assert.equal(stage(doc3).textContent, "无法预览这种文件");
});

test("Esc 关闭并回报最后看的下标；空格只在焦点不在控件上时关闭", () => {
  const doc = makeDoc();
  const closed = [];
  open(doc, { onClose: (i) => closed.push(i) });
  doc.key("ArrowRight");
  doc.key(" ", new Element("button"));
  doc.key(" ", new Element("video"));
  assert.ok(dialog(doc), "焦点在按钮或视频上时空格交给控件");
  doc.key("ArrowRight", new Element("video"));
  assert.equal(closed.length, 0);
  doc.key(" ", new Element("div"));
  assert.deepEqual(closed, [1], "视频上按 → 不翻页，仍停在第 2 件");
  assert.equal(dialog(doc), null);
  assert.deepEqual(doc.listeners.keydown, []);
  doc.key("Escape");
  assert.deepEqual(closed, [1], "关闭只回报一次");
});

test("回填参数：关闭弹层再调 onFill；在访达中显示失败写进弹层错误行；点遮罩关闭", async () => {
  const doc = makeDoc();
  const fills = []; const closed = [];
  open(doc, {
    onFill: (plan) => fills.push(plan), onClose: (i) => closed.push(i),
    onReveal: async () => { throw new Error("成品目录还不存在，生成第一个作品后会自动创建"); },
  });
  find(doc.body, (n) => n.tagName === "button" && n.textContent === "在访达中显示").click();
  await new Promise((resolve) => setImmediate(resolve));
  assert.equal(byData(doc.body, "libPreviewError").textContent, "成品目录还不存在，生成第一个作品后会自动创建");
  find(doc.body, (n) => n.tagName === "button" && n.textContent === "回填参数").click();
  assert.deepEqual(closed, [0]);
  assert.equal(fills.length, 1);
  assert.equal(fills[0].pane, "image");
  const doc2 = makeDoc();
  const closed2 = [];
  open(doc2, { onClose: (i) => closed2.push(i) });
  const overlay = doc2.body.children[0];
  await overlay.dispatch("click", { target: overlay });
  assert.deepEqual(closed2, [0]);
});
