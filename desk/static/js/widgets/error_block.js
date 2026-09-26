// ui:errorBlock —— 作业失败的统一呈现：标题 + 可选「详情」折叠；会话卡片（取其「详情」折叠）
// 与 library.js 的素材库失败行共用同一套说法（F8）。
import { describeJobError } from "../pure/job_error.js";

export function renderErrorBlock(doc, error) {
  const { title, detail } = describeJobError(error);
  const box = doc.createElement("div");
  box.className = "inline-error job-error";
  const strong = doc.createElement("strong");
  strong.textContent = title;
  box.append(strong);
  if (detail) {
    const details = doc.createElement("details");
    const summary = doc.createElement("summary");
    summary.textContent = "详情";
    const pre = doc.createElement("pre");
    pre.textContent = detail;
    details.append(summary, pre);
    box.append(details);
  }
  return box;
}
