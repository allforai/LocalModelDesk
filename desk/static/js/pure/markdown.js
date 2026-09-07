// 极小 Markdown → DOM 节点（不经 innerHTML）。只覆盖模型回复常见语法；其余按纯文本。
function inline(doc, text) {
  const out = [];
  const re = /(\*\*[^*]+\*\*|`[^`]+`)/g;
  let last = 0, m;
  while ((m = re.exec(text))) {
    if (m.index > last) out.push(doc.createTextNode(text.slice(last, m.index)));
    const tok = m[0];
    if (tok.startsWith("**")) { const b = doc.createElement("strong"); b.textContent = tok.slice(2, -2); out.push(b); }
    else { const c = doc.createElement("code"); c.textContent = tok.slice(1, -1); out.push(c); }
    last = m.index + tok.length;
  }
  if (last < text.length) out.push(doc.createTextNode(text.slice(last)));
  return out;
}

export function renderMarkdown(doc, text) {
  const frag = doc.createDocumentFragment();
  const lines = String(text ?? "").replace(/\r\n?/g, "\n").split("\n");
  let i = 0;
  const para = [];
  const flushPara = () => { if (!para.length) return; const p = doc.createElement("p"); para.forEach((l, idx) => { if (idx) p.append(doc.createElement("br")); p.append(...inline(doc, l)); }); frag.append(p); para.length = 0; };
  while (i < lines.length) {
    const line = lines[i];
    if (/^```/.test(line)) {
      flushPara();
      const buf = [];
      i += 1;
      while (i < lines.length && !/^```/.test(lines[i])) buf.push(lines[i++]);
      i += 1;
      const pre = doc.createElement("pre");
      const code = doc.createElement("code");
      code.textContent = `${buf.join("\n")}\n`;
      pre.append(code);
      frag.append(pre);
      continue;
    }
    const h = /^(#{1,3})\s+(.*)$/.exec(line);
    if (h) { flushPara(); const el = doc.createElement(h[1].length === 1 ? "h3" : "h4"); el.append(...inline(doc, h[2])); frag.append(el); i += 1; continue; }
    const li = /^\s*(?:[-*]|\d+\.)\s+(.*)$/.exec(line);
    if (li) {
      flushPara();
      const ordered = /^\s*\d+\./.test(line);
      const list = doc.createElement(ordered ? "ol" : "ul");
      while (i < lines.length && /^\s*(?:[-*]|\d+\.)\s+/.test(lines[i])) {
        const item = doc.createElement("li");
        item.append(...inline(doc, lines[i].replace(/^\s*(?:[-*]|\d+\.)\s+/, "")));
        list.append(item);
        i += 1;
      }
      frag.append(list);
      continue;
    }
    if (line.trim() === "") { flushPara(); i += 1; continue; }
    para.push(line);
    i += 1;
  }
  flushPara();
  return frag;
}
