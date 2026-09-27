// 通用媒体选择框（设计 S-20/S-21，泛化自图片首帧选择框 V-23）。跟 confirm.js 共用同一套
// 遮罩 + role=dialog + aria-modal + Esc/点遮罩关闭骨架；两栏内容（会话列表 + 右侧内容）。
// 参照 skill_install.js 的动态换内容做法，用 dataset 标关键元素方便测试，不靠 textContent 匹配。
import { addIcon } from "../icons.js";
import { hasImage } from "../pure/image_session.js";
import { autoTitle, sessionTitle } from "../pure/media_session.js";

// 音乐尝试的可选文件：优先未缺失的 joined_output，否则 output；都不在则不可选（S-20）。
export function musicOutput(attempt) {
  if (typeof attempt?.joined_output === "string" && attempt.joined_output && !attempt.joined_missing) return attempt.joined_output;
  if (typeof attempt?.output === "string" && attempt.output && !attempt.output_missing) return attempt.output;
  return null;
}

// doc: 承载 DOM 的文档对象（测试可传假 DOM）。
// kind: "image" | "music"；title/emptyText 由调用方给（S-21）。
// listSessions(): Promise<会话摘要[]>（同 api.listMediaSessions(kind)：{id,title,attempt_count,corrupt?,…}）。
// getSession(id): Promise<完整会话>（同 api.getMediaSession(kind, id)：{id,title,attempts:[…]}）。
// serveOutput(output): 缩略图/试听 src。
// resolve(null | {ref:{kind, session_id, attempt_id}, title, index, label?})；
// label 只在音乐分支给（风格描述摘要，S-20），图片分支保持原行为不带 label。
export function openMediaPicker(doc, { kind, title, emptyText, listSessions, getSession, serveOutput }) {
  return new Promise((resolve) => {
    const overlay = doc.createElement("div"); overlay.className = "overlay";
    const box = doc.createElement("div"); box.className = "dialog dialog-wide media-picker";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-label", title);

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

    const h = doc.createElement("h3"); h.textContent = title;
    const bodyBox = doc.createElement("div"); bodyBox.className = "media-picker-body";
    const sessionList = doc.createElement("ul"); sessionList.className = "media-picker-sessions";
    (sessionList.dataset ??= {}).mediaPickerSessions = "1";
    const content = doc.createElement("div");
    content.className = kind === "music" ? "media-picker-list" : "media-picker-grid";
    (content.dataset ??= {}).mediaPickerContent = "1";
    bodyBox.append(sessionList, content);
    const row = doc.createElement("div"); row.className = "dialog-actions";
    const cancelBtn = doc.createElement("button"); cancelBtn.textContent = "取消";
    (cancelBtn.dataset ??= {}).mediaPickerCancel = "1";
    cancelBtn.addEventListener("click", () => settle(null));
    row.append(cancelBtn);
    box.append(h, bodyBox, row);
    overlay.append(box);

    let sessionButtons = [];
    let currentId = null; // 挡住切换太快时过期的 getSession 结果落到错的会话上

    function renderEmpty() {
      const p = doc.createElement("p"); p.className = "hint media-picker-empty";
      (p.dataset ??= {}).mediaPickerEmpty = "1";
      p.textContent = emptyText;
      content.append(p);
    }

    function renderImages(session) {
      const attempts = session?.attempts ?? [];
      const pickable = attempts
        .map((attempt, index) => ({ attempt, index }))
        .filter(({ attempt }) => hasImage(attempt));
      if (!pickable.length) { renderEmpty(); return; }
      for (const { attempt, index } of pickable) {
        const thumb = doc.createElement("button");
        thumb.type = "button";
        thumb.className = "attempt-thumb media-picker-thumb";
        (thumb.dataset ??= {}).mediaPickerThumb = "1";
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
        content.append(thumb);
      }
    }

    function renderMusic(session) {
      const attempts = session?.attempts ?? [];
      const pickable = attempts
        .map((attempt, index) => ({ attempt, index, file: musicOutput(attempt) }))
        .filter(({ attempt, file }) => attempt?.status === "done" && !!file);
      if (!pickable.length) { renderEmpty(); return; }
      for (const { attempt, index, file } of pickable) {
        const item = doc.createElement("div");
        item.className = "media-picker-music-item";
        (item.dataset ??= {}).mediaPickerMusicItem = "1";
        const label = autoTitle(attempt.params?.caption);
        const head = doc.createElement("p");
        head.className = "media-picker-music-label";
        head.textContent = `第 ${index + 1} 次 · ${label}`;
        const audio = doc.createElement("audio");
        audio.setAttribute("controls", "");
        audio.setAttribute("preload", "none");
        (audio.dataset ??= {}).mediaPickerAudio = "1";
        audio.src = serveOutput(file);
        const pickBtn = doc.createElement("button");
        pickBtn.type = "button";
        pickBtn.className = "media-picker-pick";
        (pickBtn.dataset ??= {}).mediaPickerPick = "1";
        pickBtn.textContent = "选这首";
        pickBtn.addEventListener("click", () => settle({
          ref: { kind: "music", session_id: session.id, attempt_id: attempt.id },
          title: sessionTitle(session),
          index,
          label,
        }));
        item.append(head, audio, pickBtn);
        content.append(item);
      }
    }

    function renderContent(session) {
      content.replaceChildren();
      if (kind === "music") renderMusic(session);
      else renderImages(session);
    }

    async function selectSession(summary) {
      currentId = summary.id;
      for (const btn of sessionButtons) btn.classList.toggle("selected", btn.dataset.sessionId === summary.id);
      let session = null;
      try { session = await getSession(summary.id); } catch { /* 读不出来就当没有可选内容 */ }
      if (currentId !== summary.id) return; // 这期间用户已经切到别的会话
      renderContent(session);
    }

    function renderSessions(sessions) {
      sessionList.replaceChildren();
      sessionButtons = sessions.map((summary) => {
        const li = doc.createElement("li");
        const btn = doc.createElement("button");
        btn.type = "button";
        btn.className = "media-picker-session";
        (btn.dataset ??= {}).sessionId = summary.id;
        const count = Number.isInteger(summary?.attempt_count) ? summary.attempt_count : (summary?.attempts?.length ?? 0);
        btn.textContent = `${sessionTitle(summary)}（${count} 次生成）`;
        btn.addEventListener("click", () => selectSession(summary));
        addIcon(btn, kind, doc);
        li.append(btn);
        sessionList.append(li);
        return btn;
      });
    }

    (async () => {
      const raw = await listSessions();
      // 坏文件会话读不出尝试，选不出内容：不进这个选择框（D-90 一类会话在这里没意义）。
      const sessions = raw.filter((s) => !s?.corrupt);
      renderSessions(sessions);
      if (sessions.length) {
        await selectSession(sessions[0]);
        sessionButtons[0]?.focus?.();
      } else {
        renderContent(null);
      }
    })();

    doc.body.append(overlay);
  });
}
