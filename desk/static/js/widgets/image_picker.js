// 从图片会话里选一张当视频首帧的选择框（设计 V-23）。跟 confirm.js 共用同一套
// 遮罩 + role=dialog + aria-modal + Esc/点遮罩关闭骨架；两栏内容（会话列表 + 缩略图网格）
// 参照 skill_install.js 的动态换内容做法，用 dataset 标关键元素方便测试，不靠 textContent 匹配。
import { addIcon } from "../icons.js";
import { hasImage } from "../pure/image_session.js";
import { sessionTitle } from "../pure/media_session.js";

// doc: 承载 DOM 的文档对象（测试可传假 DOM）。
// listSessions(): Promise<会话摘要[]>（同 api.listMediaSessions("image")：{id,title,attempt_count,corrupt?,…}）。
// getSession(id): Promise<完整会话>（同 api.getMediaSession("image", id)：{id,title,attempts:[…]}）。
// serveOutput(output): 缩略图 src。
// resolve(null | {ref:{kind:"image",session_id,attempt_id}, title, index})。
export function openImagePicker(doc, { listSessions, getSession, serveOutput }) {
  return new Promise((resolve) => {
    const overlay = doc.createElement("div"); overlay.className = "overlay";
    const box = doc.createElement("div"); box.className = "dialog dialog-wide image-picker";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", "从图片会话选首帧");

    let settled = false;
    const settle = (value) => {
      if (settled) return;
      settled = true;
      doc.removeEventListener?.("keydown", onKey);
      overlay.remove();
      resolve(value);
    };
    const onKey = (event) => { if (event.key === "Escape") settle(null); };
    doc.addEventListener?.("keydown", onKey);
    overlay.addEventListener("click", (event) => { if (event.target === overlay) settle(null); });

    const h = doc.createElement("h3"); h.textContent = "从图片会话选首帧";
    const bodyBox = doc.createElement("div"); bodyBox.className = "image-picker-body";
    const sessionList = doc.createElement("ul"); sessionList.className = "image-picker-sessions";
    (sessionList.dataset ??= {}).imagePickerSessions = "1";
    const grid = doc.createElement("div"); grid.className = "image-picker-grid";
    (grid.dataset ??= {}).imagePickerGrid = "1";
    bodyBox.append(sessionList, grid);
    const row = doc.createElement("div"); row.className = "dialog-actions";
    const cancelBtn = doc.createElement("button"); cancelBtn.textContent = "取消";
    (cancelBtn.dataset ??= {}).imagePickerCancel = "1";
    cancelBtn.addEventListener("click", () => settle(null));
    row.append(cancelBtn);
    box.append(h, bodyBox, row);
    overlay.append(box);

    let sessionButtons = [];
    let currentId = null; // 挡住切换太快时过期的 getSession 结果落到错的会话上

    function renderGrid(session) {
      grid.replaceChildren();
      const attempts = session?.attempts ?? [];
      const pickable = attempts
        .map((attempt, index) => ({ attempt, index }))
        .filter(({ attempt }) => hasImage(attempt));
      if (!pickable.length) {
        const p = doc.createElement("p"); p.className = "hint image-picker-empty";
        (p.dataset ??= {}).imagePickerEmpty = "1";
        p.textContent = "这个会话还没有生成好的图片";
        grid.append(p);
        return;
      }
      for (const { attempt, index } of pickable) {
        const thumb = doc.createElement("button");
        thumb.type = "button";
        thumb.className = "attempt-thumb image-picker-thumb";
        (thumb.dataset ??= {}).imagePickerThumb = "1";
        thumb.setAttribute("aria-label", `第 ${index + 1} 次`);
        const img = doc.createElement("img");
        img.alt = attempt.params?.prompt || "生成的图片";
        img.src = serveOutput(attempt.output);
        thumb.append(img);
        thumb.addEventListener("click", () => settle({
          ref: { kind: "image", session_id: session.id, attempt_id: attempt.id },
          title: sessionTitle(session),
          index,
        }));
        grid.append(thumb);
      }
    }

    async function selectSession(summary) {
      currentId = summary.id;
      for (const btn of sessionButtons) btn.classList.toggle("selected", btn.dataset.sessionId === summary.id);
      let session = null;
      try { session = await getSession(summary.id); } catch { /* 读不出来就当没有可选图片 */ }
      if (currentId !== summary.id) return; // 这期间用户已经切到别的会话
      renderGrid(session);
    }

    function renderSessions(sessions) {
      sessionList.replaceChildren();
      sessionButtons = sessions.map((summary) => {
        const li = doc.createElement("li");
        const btn = doc.createElement("button");
        btn.type = "button";
        btn.className = "image-picker-session";
        (btn.dataset ??= {}).sessionId = summary.id;
        const count = Number.isInteger(summary?.attempt_count) ? summary.attempt_count : (summary?.attempts?.length ?? 0);
        btn.textContent = `${sessionTitle(summary)}（${count} 次生成）`;
        btn.addEventListener("click", () => selectSession(summary));
        addIcon(btn, "image", doc);
        li.append(btn);
        sessionList.append(li);
        return btn;
      });
    }

    (async () => {
      const raw = await listSessions();
      // 坏文件会话读不出尝试，选不出首帧：不进这个选择框（D-90 一类会话在这里没意义）。
      const sessions = raw.filter((s) => !s?.corrupt);
      renderSessions(sessions);
      if (sessions.length) {
        await selectSession(sessions[0]);
        sessionButtons[0]?.focus?.();
      } else {
        renderGrid(null);
      }
    })();

    doc.body.append(overlay);
  });
}
