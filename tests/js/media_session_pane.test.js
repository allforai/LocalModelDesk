// 共用会话控制器 panes/media_session.js 的通用行为（假 DOM、最小假页面，kind 取 music）。
// 图片页经由它的行为由 tests/js/image_pane.test.js 覆盖。
import test from "node:test";
import assert from "node:assert/strict";
import { button, byData, find, findAll, flush, makeGenericPane, withBackend } from "./support/fake_dom.js";

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

test("modelTexts 缺省时用通用兜底文案：模型/运行环境缺失时原因行不为空，生成仍被禁用", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1")]);
    const { parts, pane } = makeGenericPane({ modelTexts: undefined });
    pane.setHeavyAllowed(true);
    await pane.refresh();

    pane.setRuntimeStatus({ present: false });
    assert.equal(pane.availability().reason, "MLX 运行环境不可用，请检查服务或应用安装");
    assert.equal(pane.availability().disabled, true);

    pane.setRuntimeStatus({ present: true });
    pane.setModelStatus({ state: "missing" });
    assert.equal(parts.model.textContent, "尚未安装模型，请到「资源」页下载");
    assert.equal(pane.availability().reason, "尚未安装模型，请到「资源」页下载");
    assert.equal(pane.availability().disabled, true);
  });
});

// ---------- 挑选合成模式（M-05–M-11） ----------
const labeled = (node, label) => find(node, (n) => n.tagName === "button" && n.attrs?.["aria-label"] === label);
const card = (parts, id) => cards(parts).find((c) => c.dataset.attemptId === id);
const composeCalls = (backend) => backend.calls.filter((c) => c.url === "/api/media/compose");

test("canCompose 缺省：不建工具行与合成栏（图片页不受影响）", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2")]);
    const { root, pane, ready } = makeGenericPane();
    ready(); await pane.refresh();
    assert.equal(byData(root, "musicComposeStart"), null);
    assert.equal(byData(root, "musicComposeBar"), null);
    assert.equal(pane.togglePick("a1"), undefined);
  });
});

test("compose picking: order, reorder, min two, submit, exit", async () => {
  await withBackend("music", async (backend) => {
    const s = backend.addSession("歌", [done("a1"), done("a2"), done("a3")]);
    backend.nextJob = 50; // 新尝试 id 是 a50，不与已有的 a1–a3 重名
    const { root, parts, pane, ready } = makeGenericPane({ canCompose: true });
    ready(); await pane.refresh();
    const startBtn = byData(root, "musicComposeStart");
    const toolbar = startBtn.parentNode;
    assert.equal(toolbar.className, "session-toolbar");
    assert.equal(root.children.indexOf(toolbar), root.children.indexOf(parts.timeline) - 1);
    assert.equal(startBtn.textContent, "挑几段合成…");
    assert.equal(startBtn.disabled, false);
    assert.equal(startBtn.title, "");
    const bar = byData(root, "musicComposeBar");
    assert.equal(bar.className, "compose-bar");
    assert.equal(root.children.indexOf(bar), root.children.indexOf(parts.composer) - 1);
    assert.equal(bar.hidden, true);
    assert.equal(parts.composer.hidden, false);

    await startBtn.click();
    assert.equal(bar.hidden, false);
    assert.equal(parts.composer.hidden, true);
    assert.ok(cards(parts).every((c) => "picking" in c.dataset));
    assert.equal(button(bar, "合成（0 段）").disabled, true);
    assert.match(bar.textContent, /至少选两段/);

    pane.togglePick("a3"); pane.togglePick("a1");
    assert.match(bar.textContent, /第 3 次.*第 1 次/s);
    assert.deepEqual(cards(parts).map((c) => c.dataset.pickIndex), ["1", "-1", "0"]);
    assert.equal(button(bar, "合成（2 段）").disabled, false);
    assert.doesNotMatch(bar.textContent, /至少选两段/);
    assert.equal(labeled(bar, "上移第 3 次").disabled, true);
    assert.equal(labeled(bar, "下移第 1 次").disabled, true);

    await labeled(bar, "上移第 1 次").click();           // a1 升到第一
    assert.match(bar.textContent, /第 1 次.*第 3 次/s);
    assert.deepEqual(cards(parts).map((c) => c.dataset.pickIndex), ["0", "-1", "1"]);

    // 卡片点击切换勾选（不展开）；取消勾选后序号前移；同一段不会选两次（M-06/M-07/M-11）
    await card(parts, "a2").click();
    assert.deepEqual(cards(parts).map((c) => c.dataset.pickIndex), ["0", "2", "1"]);
    await card(parts, "a1").click();
    assert.deepEqual(cards(parts).map((c) => c.dataset.pickIndex), ["-1", "1", "0"]);
    await card(parts, "a2").dispatch("keydown", { key: "Enter" });     // 键盘同样切换，焦点留在这张卡片
    assert.deepEqual(cards(parts).map((c) => c.dataset.pickIndex), ["-1", "-1", "0"]);
    assert.equal(card(parts, "a2").focused, 1);
    await card(parts, "a2").dispatch("keydown", { key: " " });
    assert.deepEqual(cards(parts).map((c) => c.dataset.pickIndex), ["-1", "1", "0"]);
    await labeled(bar, "移除第 2 次").click();
    pane.togglePick("a1");
    assert.deepEqual(cards(parts).map((c) => c.dataset.pickIndex), ["1", "-1", "0"]);
    await labeled(bar, "下移第 3 次").click();
    assert.match(bar.textContent, /第 1 次.*第 3 次/s);

    await button(bar, "合成（2 段）").click(); await flush();
    assert.deepEqual(composeCalls(backend), [{ url: "/api/media/compose", method: "POST", body: { kind: "music", session_id: s.id, parts: ["a1", "a3"] } }]);
    assert.equal(bar.hidden, true);                        // 退出模式、恢复输入区
    assert.equal(parts.composer.hidden, false);
    assert.ok(cards(parts).every((c) => !("picking" in c.dataset) && c.dataset.pickIndex === "-1"));
    const added = s.attempts.at(-1);
    assert.equal(added.op, "compose");
    assert.deepEqual(card(parts, added.id).dataset.attemptStatus, "running");
    assert.equal(card(parts, added.id).getAttribute("aria-expanded"), "true");

    // 再进入时已选是空的
    await startBtn.click();
    assert.ok(button(bar, "合成（0 段）"));
  });
});

test("compose picking needs two done segments and exits on session switch", async () => {
  await withBackend("music", async (backend) => {
    const failed = { ...done("f1"), status: "failed", output: null };
    const gone = { ...done("g1"), output_missing: true };
    const other = backend.addSession("另一首", [done("b1"), done("b2"), failed, gone]);
    const thin = backend.addSession("只一段", [done("a1"), { ...failed, id: "f2" }, { ...gone, id: "g2" }]);
    const { root, parts, pane, ready } = makeGenericPane({ canCompose: true });
    ready(); await pane.refresh();
    assert.equal(pane.currentId(), thin.id);
    const startBtn = byData(root, "musicComposeStart");
    assert.equal(startBtn.disabled, true);
    assert.equal(startBtn.title, "至少要有两段完成的才能合成");

    await items(parts).find((n) => n.dataset.sessionId === other.id).click(); await flush();
    assert.equal(startBtn.disabled, false);
    assert.equal(startBtn.title, "");
    await startBtn.click();
    pane.togglePick("b2"); pane.togglePick("b1");
    const bar = byData(root, "musicComposeBar");
    assert.ok(button(bar, "合成（2 段）"));

    // 切回只有一段的会话：退出模式、已选清空；不可选的尝试不被勾选
    await items(parts).find((n) => n.dataset.sessionId === thin.id).click(); await flush();
    assert.equal(bar.hidden, true);
    assert.equal(parts.composer.hidden, false);
    assert.equal(startBtn.disabled, true);
    pane.togglePick("a1");                                   // 不在挑选模式：无效
    assert.ok(cards(parts).every((c) => c.dataset.pickIndex === "-1"));

    await items(parts).find((n) => n.dataset.sessionId === other.id).click(); await flush();
    await startBtn.click();
    assert.ok(button(bar, "合成（0 段）"));
    await items(parts).find((n) => n.dataset.sessionId === thin.id).click(); await flush();
    await startBtn.click();                                  // disabled 时无效
    assert.equal(bar.hidden, true);
    // 在可进入的会话里：失败、文件已不在的尝试不能选
    await items(parts).find((n) => n.dataset.sessionId === other.id).click(); await flush();
    await startBtn.click();
    pane.togglePick("f1"); pane.togglePick("g1");
    assert.ok(button(bar, "合成（0 段）"));

    // 新建会话也退出模式
    pane.togglePick("b1");
    await parts["session-new"].click(); await flush();
    assert.equal(bar.hidden, true);
    assert.equal(parts.composer.hidden, false);

    // 「取消」退出并清空
    await items(parts).find((n) => n.dataset.sessionId === other.id).click(); await flush();
    await startBtn.click();
    pane.togglePick("b1");
    await button(bar, "取消").click();
    assert.equal(bar.hidden, true);
    await startBtn.click();
    assert.ok(button(bar, "合成（0 段）"));
  });
});

test("compose picking disabled while a job runs", async () => {
  await withBackend("music", async (backend) => {
    const s = backend.addSession("歌", [done("a1"), done("a2")]);
    const { root, pane, ready } = makeGenericPane({ canCompose: true });
    ready(); await pane.refresh();
    await byData(root, "musicComposeStart").click();
    pane.togglePick("a1"); pane.togglePick("a2");
    const bar = byData(root, "musicComposeBar");
    assert.equal(button(bar, "合成（2 段）").disabled, false);

    s.attempts.push(running("r3"));
    pane.applyJob({ job_id: 9, kind: "music", status: "running", session_id: s.id, attempt_id: "r3", log: "" });
    await flush(); await flush();
    assert.equal(bar.hidden, false);
    assert.equal(button(bar, "合成（2 段）").disabled, true);
    assert.equal(pane.availability().reason, "正在生成这个会话里的第 3 次");
    assert.match(bar.textContent, /正在生成这个会话里的第 3 次/);
    await button(bar, "合成（2 段）").click(); await flush();
    assert.equal(composeCalls(backend).length, 0);

    // 服务不可用时同样按 §7.6 第一条原因
    s.attempts.at(-1).status = "done"; s.attempts.at(-1).output = "r3.wav";
    pane.applyJob({ job_id: 9, kind: "music", status: "done", session_id: s.id, attempt_id: "r3" });
    await flush(); await flush();
    assert.equal(button(bar, "合成（2 段）").disabled, false);
    pane.setHeavyAllowed(false, "对话模型正在占用内存");
    assert.equal(button(bar, "合成（2 段）").disabled, true);
    assert.match(bar.textContent, /对话模型正在占用内存/);
  });
});

test("合成启动失败：挑选模式里错误写在合成栏并留在模式内；capability_missing 显示后端原话", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1"), done("a2")]);
    const { root, parts, pane, ready } = makeGenericPane({ canCompose: true });
    ready(); await pane.refresh();
    backend.composeResult = () => ({ ok: false, status: 503, statusText: "", json: async () => ({ error: { code: "capability_missing", message: "需要 ffmpeg 才能拼接成片" } }) });
    await byData(root, "musicComposeStart").click();
    pane.togglePick("a1"); pane.togglePick("a2");
    const bar = byData(root, "musicComposeBar");
    await button(bar, "合成（2 段）").click(); await flush();
    assert.equal(bar.hidden, false);
    assert.equal(byData(bar, "musicComposeError").textContent, "需要 ffmpeg 才能拼接成片");
    assert.equal(parts.error.textContent, "");
    assert.ok(button(bar, "合成（2 段）"));

    backend.composeResult = () => ({ ok: false, status: 409, statusText: "", json: async () => ({ error: { code: "media_busy", message: "busy" } }) });
    await button(bar, "合成（2 段）").click(); await flush();
    assert.equal(byData(bar, "musicComposeError").textContent, "已有作业在进行");
    backend.composeResult = () => ({ ok: false, status: 404, statusText: "", json: async () => ({ error: { code: "segment_missing", message: "第 1 次的文件已不在" } }) });
    await button(bar, "合成（2 段）").click(); await flush();
    assert.equal(byData(bar, "musicComposeError").textContent, "第 1 次的文件已不在");

    // 取消后错误清掉；不在挑选模式时 startCompose 的错误写到页面错误行
    await button(bar, "取消").click();
    await pane.startCompose(["a1", "a2"]);
    assert.equal(parts.error.textContent, "第 1 次的文件已不在");
    await byData(root, "musicComposeStart").click();
    assert.equal(byData(bar, "musicComposeError").textContent, "");
  });
});

test("startCompose 在挑选模式外也能用（重新拼接）：成功后新尝试被选中", async () => {
  await withBackend("music", async (backend) => {
    const s = backend.addSession("歌", [done("a1"), done("a2")]);
    backend.nextJob = 50;
    const started = [];
    const { parts, pane, ready } = makeGenericPane({ canCompose: true, onStarted: (job) => started.push(job) });
    ready(); await pane.refresh();
    await pane.startCompose(["a1", "a2"]);
    assert.deepEqual(composeCalls(backend).map((c) => c.body), [{ kind: "music", session_id: s.id, parts: ["a1", "a2"] }]);
    const added = s.attempts.at(-1);
    assert.equal(started.length, 1);
    assert.equal(started[0].attempt_id, added.id);
    assert.equal(card(parts, added.id).dataset.attemptStatus, "running");
    assert.equal(pane.availability().reason, "正在生成这个会话里的第 3 次");
    assert.equal(parts.error.textContent, "");
  });
});

// ---------- issue #18 ----------
test("挑选模式中已选的一段在刷新后文件不在：合成栏列表与「合成（K 段）」随之减少", async () => {
  await withBackend("music", async (backend) => {
    const s = backend.addSession("歌", [done("a1"), done("a2"), done("a3")]);
    const { root, pane, ready } = makeGenericPane({ canCompose: true });
    ready(); await pane.refresh();
    await byData(root, "musicComposeStart").click();
    pane.togglePick("a1"); pane.togglePick("a2"); pane.togglePick("a3");
    const bar = byData(root, "musicComposeBar");
    assert.ok(button(bar, "合成（3 段）"));
    assert.ok(labeled(bar, "移除第 2 次"));
    s.attempts[1].output_missing = true;
    await pane.refresh();
    assert.ok(button(bar, "合成（2 段）"));
    assert.equal(labeled(bar, "移除第 2 次"), null);
    assert.match(bar.textContent, /第 1 次.*第 3 次/s);
  });
});

test("「取消」退出挑选后焦点回到「挑几段合成…」；切换会话、新建会话、合成成功退出时不抢焦点", async () => {
  await withBackend("music", async (backend) => {
    const a = backend.addSession("甲", [done("a1"), done("a2")]);
    backend.addSession("乙", [done("b1"), done("b2")]);
    backend.nextJob = 50;
    const { root, parts, pane, ready } = makeGenericPane({ canCompose: true });
    ready(); await pane.refresh();
    const startBtn = byData(root, "musicComposeStart");
    const bar = byData(root, "musicComposeBar");
    await startBtn.click();
    await button(bar, "取消").click();
    assert.equal(bar.hidden, true);
    assert.equal(startBtn.focused, 1);

    await startBtn.click();
    await items(parts).find((n) => n.dataset.sessionId === a.id).click(); await flush();
    assert.equal(bar.hidden, true);
    await startBtn.click();
    await parts["session-new"].click(); await flush();
    assert.equal(bar.hidden, true);
    await items(parts).find((n) => n.dataset.sessionId === a.id).click(); await flush();
    await startBtn.click();
    pane.togglePick("a1"); pane.togglePick("a2");
    await button(bar, "合成（2 段）").click(); await flush();
    assert.equal(bar.hidden, true);
    assert.equal(startBtn.focused, 1);
  });
});

test("切换会话后控制器的 broken 集合清空：切回来时卡片不再标坏、可以勾选", async () => {
  await withBackend("music", async (backend) => {
    const a = backend.addSession("甲", [done("a1"), done("a2")]);
    const b = backend.addSession("乙", [done("b1")]);
    const seenBroken = new Map();
    let breakIt = null;
    const { parts, pane, ready } = makeGenericPane({
      canCompose: true,
      renderCard: (d, o) => {
        const li = d.createElement("li");
        li.dataset.attemptId = o.attempt.id;
        li.dataset.pickIndex = String(o.pickIndex ?? -1);
        seenBroken.set(o.attempt.id, o.broken);
        if (o.attempt.id === "a1") breakIt = () => o.onBroken(o.attempt);
        return { node: li };
      },
    });
    ready(); await pane.refresh();
    await items(parts).find((n) => n.dataset.sessionId === a.id).click(); await flush();
    breakIt();
    assert.equal(seenBroken.get("a1"), true);
    await items(parts).find((n) => n.dataset.sessionId === b.id).click(); await flush();
    await items(parts).find((n) => n.dataset.sessionId === a.id).click(); await flush();
    await pane.refresh();
    assert.equal(seenBroken.get("a1"), false);
  });
});

test("被门控的按钮就地更新：忙碌原因变化时不重画卡片，按钮的禁用与提示跟着变（#21）", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1")]);
    let renders = 0; let rejoin = null;
    const { pane, ready } = makeGenericPane({
      renderCard: (d, o) => {
        renders += 1;
        const li = d.createElement("li");
        li.dataset.attemptId = o.attempt.id;
        rejoin = d.createElement("button");
        li.append(rejoin);
        return { node: li, gated: [{ button: rejoin, ownDisabled: false, ownReason: "" }] };
      },
    });
    ready(); await pane.refresh();
    const before = renders;
    assert.equal(rejoin.disabled, false);
    pane.setHeavyAllowed(false, "对话模型正在占用内存");
    assert.equal(renders, before);
    assert.equal(rejoin.disabled, true);
    assert.equal(rejoin.title, "对话模型正在占用内存");
    pane.setHeavyAllowed(true);
    assert.equal(renders, before);
    assert.equal(rejoin.disabled, false);
    assert.equal(rejoin.title, "");
  });
});

test("按钮自己的不可用原因优先于忙碌原因（链上缺段时忙碌结束也不恢复）", async () => {
  await withBackend("music", async (backend) => {
    backend.addSession("歌", [done("a1")]);
    let rejoin = null;
    const { pane, ready } = makeGenericPane({
      renderCard: (d, o) => {
        const li = d.createElement("li");
        li.dataset.attemptId = o.attempt.id;
        rejoin = d.createElement("button");
        li.append(rejoin);
        return { node: li, gated: [{ button: rejoin, ownDisabled: true, ownReason: "链上有一段已不在" }] };
      },
    });
    ready(); await pane.refresh();
    pane.setHeavyAllowed(false, "对话模型正在占用内存");
    assert.equal(rejoin.disabled, true);
    assert.equal(rejoin.title, "链上有一段已不在");
    pane.setHeavyAllowed(true);
    assert.equal(rejoin.disabled, true);
    assert.equal(rejoin.title, "链上有一段已不在");
  });
});
