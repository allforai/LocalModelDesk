// tests/js/library_pane.test.js —— 素材库页（素材库预览设计 L-10–L-45）
import test from "node:test";
import assert from "node:assert/strict";
import { Element, find, findAll, byData, flush } from "./support/fake_dom.js";
import { createLibraryPane, PREFS_KEY } from "../../desk/static/js/panes/library.js";

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
function memoryStorage(initial = {}) {
  const data = { ...initial };
  return { data, getItem: (k) => data[k] ?? null, setItem: (k, v) => { data[k] = String(v); } };
}
function serve(outputs, history, { reveal } = {}) {
  const calls = [];
  globalThis.fetch = async (url, options = {}) => {
    calls.push([url, options.method ?? "GET"]);
    if (url.endsWith("/reveal")) return reveal ?? { ok: true, status: 200, json: async () => ({}) };
    return { ok: true, status: 200, json: async () => (url === "/api/outputs" ? outputs : history) };
  };
  return calls;
}
async function mount({ outputs = [], history = [], storage = memoryStorage(), applyFill = () => {}, reveal } = {}) {
  const calls = serve(outputs, history, { reveal });
  const doc = makeDoc();
  const parts = { toolbar: new Element("div"), error: new Element("p"), view: new Element("div") };
  const root = new Element("section");
  root.append(parts.toolbar, parts.error, parts.view);
  root.ownerDocument = doc;
  root.querySelector = (selector) => parts[selector.match(/^\[data-lib-([\w-]+)\]$/)?.[1]] ?? null;
  const pane = createLibraryPane(root, { applyFill, storage });
  await pane.refresh();
  return { doc, parts, pane, root, calls, storage };
}
const rows = (parts) => findAll(parts.view, (n) => "libKey" in (n.dataset ?? {}));
const items = (parts) => findAll(parts.view, (n) => "libItem" in (n.dataset ?? {}));
const viewBtn = (parts, key) => find(parts.toolbar, (n) => n.dataset?.libViewBtn === key);
const filterBtn = (parts, label) => find(byData(parts.toolbar, "libFilter"), (n) => n.tagName === "button" && n.textContent === label);
const btn = (node, text) => find(node, (n) => n.tagName === "button" && n.textContent === text);
const dialog = (doc) => find(doc.body, (n) => n.attrs?.role === "dialog");

const OUTPUTS = [
  { name: "cat 1.png", kind: "image", bytes: 2048, ts: "2026-09-25T10:03:00Z" },
  { name: "h3-1.mp4", kind: "video", bytes: 4096, ts: "2026-09-25T10:02:00Z" },
  { name: "music3-1.wav", kind: "music", bytes: 1024, ts: "2026-09-25T10:01:00Z" },
];
const HISTORY = [
  { kind: "image", status: "done", ts: "2026-09-25T10:03:00Z", output: "cat 1.png", session_id: "s1", attempt_id: "a1",
    params: { prompt: "橘猫", width: 1024, height: 768, steps: 40, seed: 0 } },
  { kind: "video", status: "done", ts: "2026-09-25T10:02:00Z", output: "h3-1.mp4", duration_s: 80,
    params: { prompt: "海边", width: 768, height: 448, frames: 48, steps: 16 } },
  { kind: "music", status: "done", ts: "2026-09-25T10:01:00Z", output: "music3-1.wav", audio_seconds: 29.71,
    params: { caption: "民谣", lyrics: "啦", duration: 300 } },
  { kind: "video", status: "failed", ts: "2026-09-24T10:00:00Z", output: null, error: "exit_nonzero: exit 1",
    params: { prompt: "镜头缓慢推近", frames: 48 } },
];

test("默认缩略图视图：新的在前，工具栏有筛选、三个视图按钮、大小滑块、刷新", async () => {
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  assert.equal(parts.view.dataset.libMode, "grid");
  assert.deepEqual(rows(parts).map((r) => r.dataset.libKey),
    ["o:cat 1.png", "o:h3-1.mp4", "o:music3-1.wav", "h:2026-09-24T10:00:00Z:video:"]);
  assert.equal(viewBtn(parts, "grid").attrs["aria-pressed"], "true");
  assert.equal(viewBtn(parts, "list").attrs["aria-pressed"], "false");
  assert.equal(viewBtn(parts, "table").attrs["aria-label"], "明细");
  assert.equal(byData(parts.toolbar, "libThumb").hidden, false);
  assert.ok(byData(parts.toolbar, "libRefresh"));
  assert.deepEqual(findAll(byData(parts.toolbar, "libFilter"), (n) => n.tagName === "button").map((b) => b.textContent),
    ["全部", "图片", "视频", "音乐"]);
});

test("缩略图：图片地址编码；无 IntersectionObserver 时视频直接设首帧地址；时长角标；失败与文件已不在是灰卡", async () => {
  const history = [...HISTORY, { kind: "video", status: "done", ts: "2026-09-20T00:00:00Z", output: "gone.mp4", params: { prompt: "删了" } }];
  const { parts } = await mount({ outputs: OUTPUTS, history });
  const [image, video, music, failed, gone] = rows(parts);
  assert.equal(find(image, (n) => n.tagName === "img").src, "/api/outputs/cat%201.png");
  assert.equal(find(image, (n) => n.tagName === "img").loading, "lazy");
  const v = find(video, (n) => n.tagName === "video");
  assert.equal(v.src, "/api/outputs/h3-1.mp4#t=0.1");
  assert.equal(v.muted, true);
  assert.equal(v.preload, "metadata");
  assert.equal(find(video, (n) => n.className === "lib-badge").textContent, "0:02");
  assert.equal(find(music, (n) => n.className === "lib-badge").textContent, "0:30");
  assert.match(find(failed, (n) => /lib-thumb/.test(n.className)).className, /is-empty/);
  assert.equal(find(gone, (n) => n.className === "lib-thumb-note").textContent, "文件已不在");
});

test("懒加载：有 IntersectionObserver 时视频进视口才设地址（Review Focus 1）", async (t) => {
  class FakeObserver {
    constructor(callback) { this.callback = callback; this.targets = []; FakeObserver.last = this; }
    observe(target) { this.targets.push(target); }
    unobserve(target) { this.targets = this.targets.filter((x) => x !== target); }
    fire() { this.callback(this.targets.map((target) => ({ target, isIntersecting: true }))); }
  }
  globalThis.IntersectionObserver = FakeObserver;
  t.after(() => { delete globalThis.IntersectionObserver; });
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const v = find(parts.view, (n) => n.tagName === "video");
  assert.equal(v.src, undefined);
  FakeObserver.last.fire();
  assert.equal(v.src, "/api/outputs/h3-1.mp4#t=0.1");
  assert.deepEqual(FakeObserver.last.targets, []);
});

test("图片加载失败退回类型图标，不影响其他卡片", async () => {
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const [image, video] = rows(parts);
  const img = find(image, (n) => n.tagName === "img");
  await img.dispatch("error");
  assert.equal(find(image, (n) => n.tagName === "img"), null);
  assert.match(find(image, (n) => /lib-thumb/.test(n.className)).className, /is-broken/);
  assert.ok(find(video, (n) => n.tagName === "video"));
});

test("视图切换写进本机存储，下次打开沿用；存储坏了或抛错照常显示默认视图", async () => {
  const { parts, storage } = await mount({ outputs: OUTPUTS, history: HISTORY });
  await viewBtn(parts, "table").click();
  assert.equal(parts.view.dataset.libMode, "table");
  assert.equal(JSON.parse(storage.data[PREFS_KEY]).view, "table");
  assert.equal(byData(parts.toolbar, "libThumb").hidden, true);
  const again = await mount({ outputs: OUTPUTS, history: HISTORY, storage });
  assert.equal(again.parts.view.dataset.libMode, "table");
  const broken = await mount({ outputs: OUTPUTS, history: HISTORY, storage: memoryStorage({ [PREFS_KEY]: "{oops" }) });
  assert.equal(broken.parts.view.dataset.libMode, "grid");
  const throwing = { getItem() { throw new Error("denied"); }, setItem() { throw new Error("denied"); } };
  const locked = await mount({ outputs: OUTPUTS, history: HISTORY, storage: throwing });
  assert.equal(locked.parts.view.dataset.libMode, "grid");
  await viewBtn(locked.parts, "list").click();
  assert.equal(locked.parts.view.dataset.libMode, "list");
});

test("筛选：只看视频；某类没有时写明当前筛选；整个库为空时是引导语", async () => {
  const { parts } = await mount({ outputs: OUTPUTS.slice(0, 2), history: HISTORY.slice(0, 2) });
  await filterBtn(parts, "视频").click();
  assert.deepEqual(rows(parts).map((r) => r.dataset.libKey), ["o:h3-1.mp4"]);
  await filterBtn(parts, "音乐").click();
  assert.equal(byData(parts.view, "libEmpty").textContent, "没有这类成品。当前筛选：音乐");
  const empty = await mount();
  assert.equal(byData(empty.parts.view, "libEmpty").textContent,
    "还没有成品。去「图片」「视频」或「音乐」面板生成第一件，它会出现在这里。");
});

test("列表视图：元信息、失败错误块（F3）、在访达中显示（含 issue #12 失败文案）、回填参数", async () => {
  const fills = [];
  const reveal = { ok: false, status: 404,
    json: async () => ({ error: { code: "outputs_root_missing", message: "成品目录还不存在，生成第一个作品后会自动创建" } }) };
  const storage = memoryStorage({ [PREFS_KEY]: JSON.stringify({ view: "list" }) });
  const { parts, calls } = await mount({ outputs: OUTPUTS, history: HISTORY, storage, applyFill: (p) => fills.push(p), reveal });
  const [image, , music, failed] = rows(parts);
  assert.match(find(image, (n) => n.className === "lib-meta").textContent, /图片 · 完成 · 2026-09-25 10:03 · 1024×768 · 40步 · 种子 0/);
  assert.ok(find(music, (n) => n.className === "lib-meta").textContent.includes("成品 30 秒（请求 300 秒）"));
  const block = find(failed, (n) => n.className === "inline-error job-error");
  assert.equal(find(block, (n) => n.tagName === "strong").textContent, "生成程序异常退出");
  assert.equal(find(find(block, (n) => n.tagName === "details"), (n) => n.tagName === "pre").textContent, "exit_nonzero: exit 1");
  await btn(image, "在访达中显示").click();
  await flush();
  assert.ok(calls.some(([url, method]) => url === "/api/outputs/cat%201.png/reveal" && method === "POST"));
  assert.equal(parts.error.textContent, "成品目录还不存在，生成第一个作品后会自动创建");
  await btn(image, "回填参数").click();
  assert.deepEqual(fills, [{ pane: "image", session_id: "s1", attempt_id: "a1",
    fields: { prompt: "橘猫", width: 1024, height: 768, steps: 40, seed: 0 } }]);
  assert.equal(btn(failed, "在访达中显示"), null);
});

test("明细视图：表头点一下按该列排序、再点反向，aria-sort 标当前列，缺值显示「—」", async () => {
  const storage = memoryStorage({ [PREFS_KEY]: JSON.stringify({ view: "table" }) });
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY, storage });
  const header = (key) => find(parts.view, (n) => n.dataset?.libSort === key);
  assert.equal(header("ts").parentNode.attrs["aria-sort"], "descending");
  await header("bytes").click();
  assert.deepEqual(rows(parts).map((r) => r.dataset.libKey),
    ["o:h3-1.mp4", "o:cat 1.png", "o:music3-1.wav", "h:2026-09-24T10:00:00Z:video:"]);
  assert.equal(header("bytes").parentNode.attrs["aria-sort"], "descending");
  await header("bytes").click();
  assert.equal(header("bytes").parentNode.attrs["aria-sort"], "ascending");
  assert.deepEqual(rows(parts).map((r) => r.dataset.libKey).slice(0, 3), ["o:music3-1.wav", "o:cat 1.png", "o:h3-1.mp4"]);
  assert.equal(JSON.parse(storage.data[PREFS_KEY]).sort.dir, "asc");
  const imageRow = rows(parts).find((r) => r.dataset.libKey === "o:cat 1.png");
  assert.deepEqual(imageRow.children.slice(2).map((td) => td.textContent),
    ["图片", "2026-09-25 10:03", "—", "1024×768", "2 KiB", "—"]);
});

test("选中与键盘：单击选中（aria-current、roving tabIndex）；方向键移动；到头停住", async () => {
  const storage = memoryStorage({ [PREFS_KEY]: JSON.stringify({ view: "list" }) });
  const { parts } = await mount({ outputs: OUTPUTS, history: HISTORY, storage });
  const mains = items(parts);
  assert.deepEqual(mains.map((m) => m.tabIndex), [0, -1, -1, -1], "没有选中时第一项可 Tab 到");
  await mains[1].click();
  assert.equal(mains[1].attrs["aria-current"], "true");
  assert.match(rows(parts)[1].className, /is-selected/);
  assert.deepEqual(mains.map((m) => m.tabIndex), [-1, 0, -1, -1]);
  await mains[1].dispatch("keydown", { key: "ArrowDown" });
  assert.equal(mains[2].attrs["aria-current"], "true");
  assert.equal(mains[1].attrs["aria-current"], undefined);
  assert.ok(mains[2].focused > 0);
  await mains[2].dispatch("keydown", { key: "ArrowDown" });
  await mains[3].dispatch("keydown", { key: "ArrowDown" });
  assert.equal(mains[3].attrs["aria-current"], "true", "最后一项再往下停住");
  await viewBtn(parts, "grid").click();
  const grid = items(parts);
  assert.equal(grid[3].attrs["aria-current"], "true", "切视图保留选中");
  await grid[3].dispatch("keydown", { key: "ArrowLeft" });
  assert.equal(grid[2].attrs["aria-current"], "true");
  await grid[2].dispatch("keydown", { key: "ArrowUp" });
  assert.equal(grid[1].attrs["aria-current"], "true", "量不到列数时 ↑ 退化为前一个");
});

test("Enter/双击打开预览；同一次按键不会把刚开的预览关掉；关闭后选中与焦点回到最后看的那件", async () => {
  const { doc, parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const mains = items(parts);
  let stopped = 0;
  await mains[0].dispatch("keydown", { key: " ", stopPropagation() { stopped += 1; } });
  assert.ok(dialog(doc), "空格打开");
  assert.equal(stopped, 1, "打开预览的这次按键不再往外冒泡");
  doc.key("ArrowRight");
  doc.key("Escape");
  assert.equal(dialog(doc), null);
  const after = items(parts);
  assert.equal(after[1].attrs["aria-current"], "true");
  assert.ok(after[1].focused > 0);
  await after[2].dispatch("dblclick");
  assert.equal(dialog(doc).attrs["aria-label"], "民谣");
});

test("在筛选后的视图里预览只在该筛选与排序里翻页（Review Focus 3）", async () => {
  const { doc, parts } = await mount({ outputs: OUTPUTS, history: HISTORY });
  await filterBtn(parts, "视频").click();
  await items(parts)[0].dispatch("keydown", { key: "Enter" });
  assert.equal(dialog(doc).attrs["aria-label"], "海边");
  doc.key("ArrowRight");
  assert.equal(dialog(doc).attrs["aria-label"], "镜头缓慢推近");
  assert.equal(byData(doc.body, "libNext").disabled, true);
});

test("试听：点按钮播放并显示暂停，再点停；不触发选中；动作按钮上按 Enter 不开预览（Review Focus 5）", async () => {
  const { doc, parts, root } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const player = byData(root, "libAudition");
  let paused = 0; player.pause = () => { paused += 1; };
  const button = byData(parts.view, "libAuditionBtn");
  await button.click();
  assert.equal(player.src, "/api/outputs/music3-1.wav");
  assert.equal(button.attrs["aria-pressed"], "true");
  assert.equal(button.attrs["aria-label"], "暂停试听");
  assert.equal(items(parts).some((m) => m.attrs["aria-current"] === "true"), false);
  await button.dispatch("keydown", { key: "Enter" });
  assert.equal(dialog(doc), null);
  await button.click();
  assert.equal(paused, 1);
  assert.equal(button.attrs["aria-pressed"], "false");
  assert.equal(button.attrs["aria-label"], "试听");
});

test("试听中刷新、切筛选、离开页面、打开预览都会停声（Review Focus 4）", async () => {
  const { doc, parts, pane, root } = await mount({ outputs: OUTPUTS, history: HISTORY });
  const player = byData(root, "libAudition");
  let paused = 0; player.pause = () => { paused += 1; };
  const start = async () => byData(parts.view, "libAuditionBtn").click();
  await start(); await pane.refresh(); assert.equal(paused, 1);
  await start(); await filterBtn(parts, "音乐").click(); assert.equal(paused, 2);
  await start(); pane.onHide(); assert.equal(paused, 3);
  assert.equal(byData(parts.view, "libAuditionBtn").attrs["aria-pressed"], "false");
  await start(); await items(parts)[0].dispatch("dblclick"); assert.equal(paused, 4);
  assert.ok(dialog(doc));
});

test("刷新后原选中项还在就保持，不在了就清空", async () => {
  const { parts, pane } = await mount({ outputs: OUTPUTS, history: HISTORY });
  await items(parts)[1].click();
  await pane.refresh();
  assert.equal(items(parts)[1].attrs["aria-current"], "true");
  serve(OUTPUTS.slice(0, 1), HISTORY.slice(0, 1));
  await pane.refresh();
  assert.equal(items(parts).some((m) => m.attrs["aria-current"] === "true"), false);
});
