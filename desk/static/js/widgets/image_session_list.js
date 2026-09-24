// 图片页左栏的会话列表项（设计 D-77、§7.2、D-89、D-90），与聊天页 renderSessionList 同构：
// card session 卡片、右侧图标按钮列、当前项 aria-current。只画 DOM，动作交回面板。
import { addIcon } from "../icons.js";
import { sessionMeta, sessionTitle } from "../pure/image_session.js";

export function renderSessionItem(doc, summary, { current, onSelect, onRename, onDelete }) {
  const title = sessionTitle(summary);
  const li = doc.createElement("li");
  li.className = "card session image-session";
  li.classList.toggle("active", current);
  li.tabIndex = 0;
  li.dataset.sessionId = summary.id;
  if (summary.corrupt) li.dataset.corrupt = "1";
  if (current) li.setAttribute("aria-current", "true");

  const titleRow = doc.createElement("div");
  titleRow.className = "session-title-row";
  const titleNode = doc.createElement("span");
  titleNode.className = "session-title";
  titleNode.textContent = title;
  titleNode.title = title;
  titleRow.append(titleNode);
  if (summary.running && !summary.corrupt) {
    const mark = doc.createElement("span");
    mark.className = "session-running";
    mark.dataset.sessionRunning = "";
    mark.textContent = "生成中";
    titleRow.append(mark);
  }
  const meta = doc.createElement("div");
  meta.className = "session-meta";
  meta.textContent = sessionMeta(summary);

  const actions = doc.createElement("div");
  actions.className = "session-actions";
  if (!summary.corrupt) {
    const rename = doc.createElement("button");
    rename.className = "btn-sm";
    rename.setAttribute("aria-label", "改名");
    addIcon(rename, "pencil", doc);
    rename.addEventListener("click", (event) => { event.stopPropagation?.(); onRename(li, summary); });
    actions.append(rename);
  }
  const remove = doc.createElement("button");
  remove.className = "btn-danger btn-sm";
  remove.setAttribute("aria-label", `删除会话：${title}`);
  addIcon(remove, "trash", doc);
  remove.addEventListener("click", (event) => { event.stopPropagation?.(); onDelete(summary); });
  actions.append(remove);

  li.addEventListener("click", () => onSelect(summary));
  li.addEventListener("keydown", (event) => {
    if (event.target && event.target !== li) return; // 按钮与改名输入框自己处理按键
    if (event.key !== "Enter" && event.key !== " ") return;
    event.preventDefault?.();
    onSelect(summary);
  });
  li.append(titleRow, meta, actions);
  return li;
}

// D-89：列表项就地变成输入框；Enter 或失焦保存，空或未变不请求（由 onCommit 判断）。
export function beginRenameItem(doc, li, summary, onCommit) {
  const input = doc.createElement("input");
  input.className = "session-rename";
  input.value = summary.title ?? "";
  input.setAttribute("aria-label", "会话名称");
  let done = false;
  const finish = () => {
    if (done) return;
    done = true;
    onCommit(input.value.trim());
  };
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") finish(); });
  input.addEventListener("blur", finish);
  input.addEventListener("click", (event) => event.stopPropagation?.());
  li.replaceChildren(input);
  input.focus();
  return input;
}
