// 两项的分段切换（「成片 | 只听这一段」等，M-31、V-32）：role=radiogroup，选中项可 Tab 到（其余 tabIndex=-1），
// 方向键左右（上下同）、Home、End 切换并把焦点移过去，与原生单选组一致。onChange(index) 在选中项变化时调用。
export function renderSegmentSwitch(doc, { labels, checked = 0, onChange, ariaLabel = "播放哪一版" }) {
  const group = doc.createElement("div");
  group.className = "segment-switch";
  group.setAttribute("role", "radiogroup");
  group.setAttribute("aria-label", ariaLabel);
  let current = checked;
  const mark = (index) => buttons.forEach((btn, i) => {
    btn.setAttribute("aria-checked", i === index ? "true" : "false");
    btn.tabIndex = i === index ? 0 : -1;
  });
  const choose = (index, { focus = false } = {}) => {
    mark(index);
    if (focus) buttons[index].focus?.();
    if (index !== current) { current = index; onChange?.(index); }
  };
  const buttons = labels.map((label, i) => {
    const btn = doc.createElement("button");
    btn.className = "btn-secondary btn-sm";
    btn.textContent = label;
    btn.setAttribute("role", "radio");
    btn.addEventListener("click", (event) => { event.stopPropagation?.(); choose(i); });
    btn.addEventListener("keydown", (event) => {
      const last = buttons.length - 1;
      const to = { ArrowRight: i + 1, ArrowDown: i + 1, ArrowLeft: i - 1, ArrowUp: i - 1, Home: 0, End: last }[event.key];
      if (to === undefined) return;
      event.preventDefault?.();
      event.stopPropagation?.();
      choose((to + buttons.length) % buttons.length, { focus: true });
    });
    return btn;
  });
  mark(checked);
  group.append(...buttons);
  return group;
}
