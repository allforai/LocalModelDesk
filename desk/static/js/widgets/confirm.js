// 通用确认弹层：内存警告 / 删除确认共用（设计 §1.1）。resolve(true|false)，取消即 false。
export function confirmDialog(doc, { title, message, confirmLabel = "确定", cancelLabel = "取消" }) {
  return new Promise((resolve) => {
    const overlay = doc.createElement("div");
    overlay.className = "overlay";
    const box = doc.createElement("div");
    box.className = "dialog";
    const h = doc.createElement("h3");
    h.textContent = title;
    const p = doc.createElement("p");
    p.textContent = message;
    const row = doc.createElement("div");
    row.className = "dialog-actions";
    const cancelBtn = doc.createElement("button");
    cancelBtn.textContent = cancelLabel;
    const okBtn = doc.createElement("button");
    okBtn.className = "btn-danger";
    okBtn.textContent = confirmLabel;
    const finish = (val) => { overlay.remove(); resolve(val); };
    cancelBtn.addEventListener("click", () => finish(false));
    okBtn.addEventListener("click", () => finish(true));
    row.append(cancelBtn, okBtn);
    box.append(h, p, row);
    overlay.append(box);
    doc.body.append(overlay);
  });
}
