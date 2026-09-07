import test from "node:test";
import assert from "node:assert/strict";
import { renderMarkdown } from "../../desk/static/js/pure/markdown.js";

class Node {
  constructor(tag) { this.tagName = tag; this.children = []; this.textContent = ""; this.className = ""; }
  append(...n) { for (const c of n) this.children.push(typeof c === "string" ? { tagName: "#text", textContent: c } : c); }
}
const doc = {
  createElement: (t) => new Node(t),
  createDocumentFragment: () => new Node("#fragment"),
  createTextNode: (t) => ({ tagName: "#text", textContent: t }),
};
const flat = (n) => {
  if (n.tagName === "#text") return n.textContent;
  const inner = n.children.length ? n.children.map(flat).join("") : n.textContent;
  return `<${n.tagName}>${inner}</${n.tagName}>`;
};

test("标题、粗体、行内代码、围栏代码、列表都变成节点，HTML 原样当文本", () => {
  const frag = renderMarkdown(doc, "# 标题\n\n我是**通义千问**，用 `x`。\n\n```py\nprint(1)\n```\n\n- a\n- b\n\n<b>no</b>");
  assert.equal(
    frag.children.map(flat).join(""),
    "<h3>标题</h3><p>我是<strong>通义千问</strong>，用 <code>x</code>。</p><pre><code>print(1)\n</code></pre><ul><li>a</li><li>b</li></ul><p><b>no</b></p>",
  );
});

test("空文本返回空片段，纯文本折行成 <br>", () => {
  assert.equal(renderMarkdown(doc, "").children.length, 0);
  const frag = renderMarkdown(doc, "第一行\n第二行");
  assert.equal(flat(frag.children[0]), "<p>第一行<br></br>第二行</p>");
});
