// ui:promptAssist —— 看手气 / 优化提示词：让已加载的聊天模型写或改媒体生成提示词。
import * as api from "../api.js";
import { confirmDialog } from "./confirm.js";

const NEED_MODEL = "先在「聊天」页加载一个模型";
const REASON_BY_CODE = { no_model_loaded: NEED_MODEL, media_busy: "媒体作业进行中，暂时不能调用模型" };
const isBlank = (fields) => Object.values(fields).every((value) => !String(value ?? "").trim());

export function createPromptAssist(doc, container, { task, read, write, mode = () => "text", confirm }) {
  const button = (label, key) => {
    const node = doc.createElement("button");
    node.type = "button";
    node.textContent = label;
    (node.dataset ??= {})[key] = "1";
    return node;
  };
  const lucky = button("看手气", "assistLucky");
  const refine = button("优化提示词", "assistRefine");
  const undo = button("恢复原文", "assistUndo");
  const hint = doc.createElement("span");
  hint.className = "hint";
  (hint.dataset ??= {}).assistHint = "1";
  undo.hidden = true;
  container.append(lucky, refine, undo, hint);

  let available = false;
  let reason = NEED_MODEL;
  let busy = false;
  let original = null;
  let lastMessage = "";
  const ask = confirm ?? ((options) => confirmDialog(doc, options));

  // The 2 s tick calls setAvailable() constantly; keep the last action message
  // ("已优化") on screen instead of wiping it on every tick.
  function render(message = lastMessage) {
    lastMessage = message;
    lucky.disabled = refine.disabled = !available || busy;
    hint.textContent = busy ? "模型正在写提示词…" : !available ? reason : message;
  }

  async function run(action) {
    if (!available || busy) return;
    const before = read();
    if (action === "refine" && !String(before.text ?? "").trim()) { render("先在输入框里写点东西，再点「优化提示词」"); return; }
    if (action === "lucky" && !isBlank(before)) {
      const go = await ask({
        title: "看手气",
        message: "看手气会让模型随机写一份新的提示词，替换输入框里现有的内容。替换后可以点「恢复原文」找回。",
        confirmLabel: "替换",
        danger: false,
      });
      if (!go) return;
    }
    busy = true;
    render();
    let message = "";
    try {
      const result = await api.promptAssist({ task, action, mode: mode(), ...before });
      original = before;
      const next = { text: result.text };
      if (result.lyrics !== undefined) next.lyrics = result.lyrics;
      write(next);
      undo.hidden = false;
      message = action === "lucky" ? "已换上新的提示词" : "已优化";
    } catch (error) {
      message = REASON_BY_CODE[error.code] ?? error.message;
    } finally {
      busy = false;
      render(message);
    }
  }

  lucky.addEventListener("click", () => run("lucky"));
  refine.addEventListener("click", () => run("refine"));
  undo.addEventListener("click", () => {
    if (!original) return;
    write(original);
    original = null;
    undo.hidden = true;
    render("已恢复原文");
  });
  render();

  return {
    setAvailable(allowed, why = "") {
      available = allowed;
      reason = why || NEED_MODEL;
      if (!busy) render();
    },
  };
}
