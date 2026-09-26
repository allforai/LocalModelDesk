// 共用会话控制器 panes/media_session.js 的通用行为（假 DOM、最小假页面，kind 取 music）。
// 图片页经由它的行为由 tests/js/image_pane.test.js 覆盖。
import test from "node:test";
import assert from "node:assert/strict";
import { findAll, flush, makeGenericPane, withBackend } from "./support/fake_dom.js";

const cards = (parts) => findAll(parts.timeline, (n) => "attemptId" in n.dataset);
const items = (parts) => findAll(parts["session-list"], (n) => "sessionId" in n.dataset);
const current = (parts) => items(parts).find((n) => n.getAttribute("aria-current") === "true")?.dataset.sessionId ?? null;
const done = (id) => ({ id, job_id: 0, ts: "2026-09-24T09:00:00", status: "done", params: { prompt: id }, output: `${id}.wav`, error: null });
const running = (id) => ({ id, job_id: 9, ts: "2026-09-24T09:00:00", status: "running", params: { prompt: id }, output: null, error: null });

test("首次 refresh 列表为空：自动 POST /api/media-sessions/music 新建并选中", async () => {
  await withBackend("music", async (backend) => {
    const { parts, pane } = makeGenericPane();
    await pane.refresh();
    const posts = backend.calls.filter((c) => c.url === "/api/media-sessions/music" && c.method === "POST");
    assert.equal(posts.length, 1);
    assert.equal(backend.sessions.length, 1);
    assert.equal(current(parts), backend.sessions[0].id);
    assert.equal(pane.currentId(), backend.sessions[0].id);
    assert.ok(items(parts)[0].classList.contains("music-session"));
    assert.ok("musicEmpty" in parts.timeline.children[0].dataset);
  });
});

test("有 running 尝试的会话优先被选中", async () => {
  await withBackend("music", async (backend) => {
    const busy = backend.addSession("在生成", [running("r1")]);
    backend.addSession("最新的", [done("d1")]); // updated 更新，排在最上
    const { parts, pane } = makeGenericPane();
    await pane.refresh();
    assert.notEqual(items(parts)[0].dataset.sessionId, busy.id);
    assert.equal(current(parts), busy.id);
    assert.deepEqual(cards(parts).map((c) => c.dataset.attemptId), ["r1"]);
    assert.equal(backend.calls.filter((c) => c.method === "POST").length, 0);
  });
});

test("applyJob 忽略别的媒体作业，本媒体的 running 作业更新对应卡片", async () => {
  await withBackend("music", async (backend) => {
    const s = backend.addSession("歌", [done("d1")]);
    const { parts, pane } = makeGenericPane();
    await pane.refresh();
    const before = backend.calls.length;
    pane.applyJob({ job_id: 5, kind: "image", status: "running", session_id: s.id, attempt_id: "x" });
    await flush();
    assert.equal(backend.calls.length, before);
    assert.deepEqual(cards(parts).map((c) => c.dataset.attemptStatus), ["done"]);

    s.attempts.push(running("a7"));
    pane.applyJob({ job_id: 7, kind: "music", status: "running", session_id: s.id, attempt_id: "a7", log: "" });
    await flush(); await flush();
    assert.ok(backend.calls.slice(before).some((c) => c.url === `/api/media-sessions/music/${s.id}` && c.method === "GET"));
    assert.deepEqual(cards(parts).map((c) => c.dataset.attemptStatus), ["done", "running"]);
    assert.equal(pane.availability().reason, "正在生成这个会话里的第 2 次");
  });
});

test("删除当前会话后按 pickCurrent 重选；列表删空了自动新建", async () => {
  await withBackend("music", async (backend) => {
    const older = backend.addSession("旧的", [done("d1")]);
    const newer = backend.addSession("新的", [done("d2")]);
    const { parts, pane } = makeGenericPane();
    await pane.refresh();
    assert.equal(current(parts), newer.id);

    const trash = (id) => findAll(items(parts).find((n) => n.dataset.sessionId === id),
      (n) => n.tagName === "button" && /删除会话/.test(n.attrs?.["aria-label"] ?? ""))[0];
    await trash(newer.id).click(); await flush();
    assert.ok(backend.calls.some((c) => c.method === "DELETE" && c.url === `/api/media-sessions/music/${newer.id}`));
    assert.equal(current(parts), older.id);

    await trash(older.id).click(); await flush();
    assert.equal(backend.sessions.length, 1);
    assert.notEqual(backend.sessions[0].id, older.id);
    assert.equal(current(parts), backend.sessions[0].id);
    assert.equal(backend.calls.filter((c) => c.method === "POST" && c.url === "/api/media-sessions/music").length, 1);
  });
});

test("别的会话在生成时，忙碌原因用 noun：「<标题>」正在生成歌曲，并给出回到该会话", async () => {
  await withBackend("music", async (backend) => {
    const busy = backend.addSession("夏夜", [running("r1")]);
    const mine = backend.addSession("另一首", [done("d1")]);
    const { parts, pane, seen, ready } = makeGenericPane();
    ready();
    await pane.refresh();
    assert.equal(current(parts), busy.id);
    await items(parts).find((n) => n.dataset.sessionId === mine.id).click(); await flush();
    assert.equal(current(parts), mine.id);
    const state = pane.availability();
    assert.equal(state.reason, "「夏夜」正在生成歌曲");
    assert.equal(state.disabled, true);
    assert.equal(parts["hint-text"].textContent, "「夏夜」正在生成歌曲");
    assert.equal(parts.return.hidden, false);
    assert.equal(seen.availability.at(-1).reason, "「夏夜」正在生成歌曲");
    assert.ok(seen.switches >= 1);
  });
});
