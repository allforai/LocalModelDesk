// desk/static/js/panes/library.js
// ui:libraryPane —— 素材库（素材库预览设计 L-10–L-45）：类访达的缩略图 / 列表 / 明细三视图 + 类型筛选 + 预览弹层。
// 条目模型在 pure/library_view.js，弹层在 widgets/library_preview.js；「回填」经 main 切 tab 写表单（R-ui-06）。
import * as api from "../api.js";
import { buildItems, clockText, hasMedia, normalizePrefs, THUMB_MAX, THUMB_MIN, visibleItems } from "../pure/library_view.js";
import { formatBytes, formatDuration, formatTimestamp } from "../pure/format.js";
import { addIcon, setIcon } from "../icons.js";
import { renderErrorBlock } from "../widgets/error_block.js";
import { renderSegmentSwitch } from "../widgets/segment_switch.js";
import { openLibraryPreview } from "../widgets/library_preview.js";

export const PREFS_KEY = "lmd.library";
const KIND_LABEL = { video: "视频", music: "音乐", image: "图片", file: "文件" };
const STATUS_LABEL = { done: "完成", failed: "失败", cancelled: "已取消" };
const KIND_ICON = { image: "image", video: "video", music: "music", file: "file" };
const FILTERS = [["all", "全部"], ["image", "图片"], ["video", "视频"], ["music", "音乐"]];
const VIEWS = [["grid", "缩略图", "grid"], ["list", "列表", "list"], ["table", "明细", "table"]];
const COLUMNS = [[null, "缩略"], ["title", "提示词"], ["kind", "类型"], ["ts", "生成时间"], ["duration", "时长"],
  ["dims", "画幅"], ["bytes", "大小"], ["gen", "耗时"]];
const ASCENDING_FIRST = new Set(["title", "kind"]);
const EMPTY_ALL = "还没有成品。去「图片」「视频」或「音乐」面板生成第一件，它会出现在这里。";

export function createLibraryPane(root, ctx) { // ctx.applyFill(plan)；ctx.storage 可注入（测试）
  const doc = root.ownerDocument;
  const storage = "storage" in ctx ? ctx.storage : globalThis.localStorage;
  const q = (name) => root.querySelector(`[data-lib-${name}]`);
  const els = { toolbar: q("toolbar"), error: q("error"), view: q("view") };
  const el = (tag, className = "") => {
    const node = doc.createElement(tag);
    if (className) node.className = className;
    return node;
  };
  const text = (tag, className, value) => {
    const node = el(tag, className);
    node.textContent = value;
    return node;
  };

  let prefs = readPrefs();
  let items = [];
  let shown = [];
  let rows = []; // 当前视图里的 [{item, main, row}]，顺序同 shown
  let selectedKey = null;
  let preview = null;
  let hovering = null;
  let audition = { key: null, button: null };
  const sortButtons = new Map(); // 明细视图当前表头的排序按钮

  // L-24：整页只有一个试听播放器。
  const player = el("audio");
  player.hidden = true;
  player.dataset.libAudition = "";
  player.addEventListener("ended", () => stopAudition());
  root.append(player);

  // L-22：视频缩略图进视口才设地址；环境没有 IntersectionObserver 时直接设。
  const observer = typeof globalThis.IntersectionObserver === "function"
    ? new globalThis.IntersectionObserver((entries) => {
      for (const entry of entries) {
        if (!entry.isIntersecting) continue;
        loadVideo(entry.target);
        observer.unobserve(entry.target);
      }
    }, { rootMargin: "200px" })
    : null;

  function readPrefs() {
    try { return normalizePrefs(JSON.parse(storage?.getItem(PREFS_KEY) ?? "null")); } catch { return normalizePrefs(null); }
  }
  function writePrefs() {
    try { storage?.setItem(PREFS_KEY, JSON.stringify(prefs)); } catch { /* 本机存储不可用：只是记不住，不影响使用 */ }
  }

  const toolbar = buildToolbar();
  syncToolbar();
  applyThumb();

  function buildToolbar() {
    const filter = renderSegmentSwitch(doc, {
      labels: FILTERS.map(([, label]) => label),
      checked: FILTERS.findIndex(([key]) => key === prefs.filter),
      ariaLabel: "类型",
      onChange: (index) => setPrefs({ filter: FILTERS[index][0] }),
    });
    filter.dataset.libFilter = "";
    const views = el("div", "lib-views");
    views.setAttribute("role", "group");
    views.setAttribute("aria-label", "视图");
    const viewButtons = VIEWS.map(([key, label, icon]) => {
      const b = el("button", "btn-quiet lib-view-btn");
      b.dataset.libViewBtn = key;
      b.setAttribute("aria-label", label);
      b.title = label;
      addIcon(b, icon, doc);
      b.addEventListener("click", () => setPrefs({ view: key }));
      return b;
    });
    views.append(...viewButtons);
    const size = el("input", "lib-thumb-size");
    size.type = "range";
    size.min = String(THUMB_MIN);
    size.max = String(THUMB_MAX);
    size.step = "20";
    size.value = String(prefs.thumb);
    size.dataset.libThumb = "";
    size.setAttribute("aria-label", "缩略图大小");
    size.addEventListener("input", () => setPrefs({ thumb: Number(size.value) }, { rerender: false }));
    const refresh = el("button");
    refresh.dataset.libRefresh = "";
    refresh.textContent = "刷新";
    addIcon(refresh, "refresh", doc);
    refresh.addEventListener("click", () => refreshPane());
    els.toolbar.replaceChildren(filter, el("span", "lib-toolbar-spacer"), size, views, refresh);
    return { viewButtons, size };
  }

  function syncToolbar() {
    for (const b of toolbar.viewButtons) b.setAttribute("aria-pressed", b.dataset.libViewBtn === prefs.view ? "true" : "false");
    toolbar.size.hidden = prefs.view !== "grid";
  }
  function applyThumb() {
    els.view.style?.setProperty?.("--lib-thumb", `${prefs.thumb}px`);
  }
  function setPrefs(patch, { rerender = true, focusSort = null } = {}) {
    prefs = normalizePrefs({ ...prefs, ...patch });
    writePrefs();
    syncToolbar();
    applyThumb();
    if (rerender) render({ focusSort });
  }

  async function refreshPane() {
    els.error.textContent = "";
    stopAudition();
    try {
      const [outputs, history] = await Promise.all([api.listOutputs(), api.listHistory()]);
      items = buildItems(outputs, history);
      render();
    } catch (err) {
      els.error.textContent = err.message;
    }
  }

  function render({ focusSort = null } = {}) {
    stopAudition();
    stopHover();
    shown = visibleItems(items, prefs);
    if (selectedKey && !shown.some((item) => item.key === selectedKey)) selectedKey = null;
    els.view.dataset.libMode = prefs.view;
    observer?.disconnect();
    rows = [];
    if (!shown.length) {
      els.view.replaceChildren(emptyNode());
      return;
    }
    els.view.replaceChildren(prefs.view === "table" ? renderTable() : prefs.view === "list" ? renderList() : renderGrid());
    syncSelection();
    if (focusSort) sortButtons.get(focusSort)?.focus?.(); // 表头重绘了，键盘焦点回到刚按的那一列
  }

  function emptyNode() {
    const label = FILTERS.find(([key]) => key === prefs.filter)?.[1] ?? "全部";
    const node = text("p", "empty", items.length ? `没有这类成品。当前筛选：${label}` : EMPTY_ALL);
    node.dataset.libEmpty = "";
    return node;
  }

  function tagRow(row, item) {
    row.dataset.libKey = item.key;
    if (hasMedia(item)) row.dataset.outputName = item.output;
  }

  // L-30：条目主体是一个按钮；动作按钮是它的兄弟节点。
  function mainButton(item) {
    const b = el("button", "lib-item");
    b.dataset.libItem = "";
    b.setAttribute("aria-label", item.title);
    b.tabIndex = -1;
    b.addEventListener("click", () => select(item.key));
    b.addEventListener("dblclick", () => open(item.key));
    b.addEventListener("keydown", (event) => onItemKey(event, item.key));
    return b;
  }

  function renderGrid() {
    const list = el("ul", "lib-grid");
    list.dataset.libList = "";
    for (const item of shown) {
      const li = el("li", "lib-card");
      tagRow(li, item);
      const main = mainButton(item);
      // <button> 里只能放短语内容：标题、时间、缩略图都用 span（CSS 里设成块）。
      main.append(thumbNode(item, { hover: true }), text("span", "lib-title", item.title), text("span", "lib-meta", formatTimestamp(item.ts)));
      li.append(main);
      if (item.kind === "music" && hasMedia(item)) li.append(auditionButton(item));
      list.append(li);
      rows.push({ item, main, row: li });
    }
    return list;
  }

  function metaLine(item) {
    if (!item.entry) return `无历史记录 · ${formatBytes(item.bytes)} · ${formatTimestamp(item.ts)}`;
    return [
      KIND_LABEL[item.kind] ?? item.kind,
      STATUS_LABEL[item.status] ?? item.status,
      formatTimestamp(item.ts),
      item.gen_s != null ? `耗时 ${formatDuration(item.gen_s)}` : null,
      item.spec,
    ].filter(Boolean).join(" · ");
  }

  function renderList() {
    const list = el("ul", "lib-rows");
    list.dataset.libList = "";
    for (const item of shown) {
      const li = el("li", "lib-row");
      tagRow(li, item);
      const main = mainButton(item);
      const body = el("span", "lib-row-text");
      body.append(text("span", "lib-title", item.title), text("span", "lib-meta", metaLine(item)));
      main.append(thumbNode(item, { hover: false }), body);
      li.append(main, actionsNode(item));
      if (item.error) {
        const [code, ...rest] = item.error.split(": ");
        li.append(renderErrorBlock(doc, { code, message: rest.join(": ") }));
      }
      list.append(li);
      rows.push({ item, main, row: li });
    }
    return list;
  }

  function actionsNode(item) {
    const actions = el("div", "lib-actions");
    const action = (label, icon, run) => {
      const b = el("button");
      b.textContent = label;
      addIcon(b, icon, doc);
      b.addEventListener("click", (event) => { event.stopPropagation?.(); run(); });
      actions.append(b);
    };
    action("预览", item.kind === "image" ? "image" : "play", () => open(item.key));
    if (hasMedia(item)) {
      action("在访达中显示", "folder", async () => {
        try { await api.revealOutput(item.output); } catch (error) { els.error.textContent = error.message; }
      });
    }
    if (item.plan) action("回填参数", "sliders", () => ctx.applyFill(item.plan));
    return actions;
  }

  function renderTable() {
    const table = el("table", "lib-table");
    const head = el("thead");
    const headRow = el("tr");
    sortButtons.clear();
    for (const [key, label] of COLUMNS) {
      const th = el("th");
      th.setAttribute("scope", "col");
      if (!key) {
        th.className = "lib-col-thumb";
        th.textContent = label;
      } else {
        const b = text("button", "lib-sort", label);
        b.dataset.libSort = key;
        sortButtons.set(key, b);
        if (prefs.sort.key === key) {
          th.setAttribute("aria-sort", prefs.sort.dir === "asc" ? "ascending" : "descending");
          addIcon(b, prefs.sort.dir === "asc" ? "chevron-up" : "chevron-down", doc);
        }
        b.addEventListener("click", () => {
          const dir = prefs.sort.key === key
            ? (prefs.sort.dir === "desc" ? "asc" : "desc")
            : (ASCENDING_FIRST.has(key) ? "asc" : "desc");
          setPrefs({ sort: { key, dir } }, { focusSort: key });
        });
        th.append(b);
      }
      headRow.append(th);
    }
    head.append(headRow);
    const body = el("tbody");
    body.dataset.libList = "";
    for (const item of shown) {
      const tr = el("tr");
      tagRow(tr, item);
      const main = mainButton(item);
      main.append(text("span", "lib-title", item.title));
      const cells = [
        thumbNode(item, { hover: false }), main, KIND_LABEL[item.kind] ?? item.kind, formatTimestamp(item.ts),
        item.duration_s != null ? clockText(item.duration_s) : "—",
        item.width && item.height ? `${item.width}×${item.height}` : "—",
        item.bytes != null ? formatBytes(item.bytes) : "—",
        item.gen_s != null ? formatDuration(item.gen_s) : "—",
      ];
      for (const cell of cells) {
        const td = el("td");
        if (typeof cell === "string") td.textContent = cell; else td.append(cell);
        tr.append(td);
      }
      body.append(tr);
      rows.push({ item, main, row: tr });
    }
    table.append(head, body);
    return table;
  }

  // L-21–L-26：缩略图。
  function thumbNode(item, { hover }) {
    const box = el("span", "lib-thumb");
    box.dataset.kind = item.kind;
    if (!hasMedia(item)) {
      box.classList.add("is-empty");
      addIcon(box, item.status === "done" && !item.missing ? KIND_ICON[item.kind] ?? "file" : "alert", doc);
      const note = item.missing ? "文件已不在" : STATUS_LABEL[item.status] ?? item.status;
      box.title = note; // 列表 / 明细视图藏掉文字，悬停仍能看到
      box.append(text("span", "lib-thumb-note", note));
      return box;
    }
    const src = api.serveOutput(item.output);
    const fallback = (node) => () => {
      node.remove();
      box.classList.add("is-broken");
      addIcon(box, KIND_ICON[item.kind] ?? "file", doc);
    };
    if (item.kind === "image") {
      const img = el("img");
      img.loading = "lazy";
      img.alt = "";
      img.src = src;
      img.addEventListener("error", fallback(img));
      box.append(img);
    } else if (item.kind === "video") {
      const video = el("video");
      video.muted = true;
      video.playsInline = true;
      video.setAttribute("playsinline", "");
      video.preload = "metadata";
      video.dataset.src = `${src}#t=0.1`;
      video.addEventListener("error", fallback(video));
      box.append(video);
      if (observer) observer.observe(video); else loadVideo(video);
      if (hover) {
        box.addEventListener("mouseenter", () => startHover(video));
        box.addEventListener("mouseleave", () => stopHover());
      }
    } else {
      addIcon(box, KIND_ICON[item.kind] ?? "file", doc);
    }
    if (item.duration_s != null) box.append(text("span", "lib-badge", clockText(item.duration_s)));
    return box;
  }
  function loadVideo(video) {
    if (!video.dataset.src) return;
    video.src = video.dataset.src;
    delete video.dataset.src;
  }
  function startHover(video) {
    stopHover();
    loadVideo(video);
    hovering = video;
    video.play?.()?.catch?.(() => {});
  }
  function stopHover() {
    if (!hovering) return;
    const video = hovering;
    hovering = null;
    video.pause?.();
    try { video.currentTime = 0.1; } catch { /* 元数据还没到 */ }
  }

  // L-24：试听。
  function auditionButton(item) {
    const b = el("button", "btn-quiet lib-audition");
    b.dataset.libAuditionBtn = "";
    b.setAttribute("aria-pressed", "false");
    b.setAttribute("aria-label", "试听");
    b.title = "试听";
    addIcon(b, "play", doc);
    b.addEventListener("click", (event) => { event.stopPropagation?.(); toggleAudition(item, b); });
    return b;
  }
  function toggleAudition(item, button) {
    if (audition.key === item.key) { stopAudition(); return; }
    stopAudition();
    player.src = api.serveOutput(item.output);
    player.play?.()?.catch?.(() => {});
    audition = { key: item.key, button };
    button.setAttribute("aria-pressed", "true");
    button.setAttribute("aria-label", "暂停试听");
    button.title = "暂停试听";
    setIcon(button, "pause", doc);
  }
  function stopAudition() {
    const { key, button } = audition;
    audition = { key: null, button: null };
    if (!key) return;
    player.pause?.();
    player.removeAttribute?.("src");
    player.load?.();
    button.setAttribute("aria-pressed", "false");
    button.setAttribute("aria-label", "试听");
    button.title = "试听";
    setIcon(button, "play", doc);
  }

  // L-30–L-32：选中、roving tabindex、键盘。
  function select(key, { focus = false } = {}) {
    selectedKey = key;
    syncSelection();
    const row = rows.find((r) => r.item.key === key);
    if (!row) return;
    row.row.scrollIntoView?.({ block: "nearest" });
    if (focus) row.main.focus?.();
  }
  function syncSelection() {
    const anchor = rows.find((r) => r.item.key === selectedKey) ?? rows[0];
    for (const r of rows) {
      const on = r.item.key === selectedKey;
      r.row.classList.toggle("is-selected", on);
      if (on) r.main.setAttribute("aria-current", "true"); else r.main.removeAttribute("aria-current");
      r.main.tabIndex = r === anchor ? 0 : -1;
    }
  }
  function columns() {
    const top = (r) => r.row.getBoundingClientRect?.().top;
    const first = rows.length ? top(rows[0]) : undefined;
    if (!Number.isFinite(first)) return 1;
    let count = 0;
    for (const r of rows) {
      if (Math.abs(top(r) - first) < 1) count += 1; else break;
    }
    return Math.max(1, count);
  }
  function stepFor(key) {
    const grid = prefs.view === "grid";
    if (key === "ArrowDown") return grid ? columns() : 1;
    if (key === "ArrowUp") return grid ? -columns() : -1;
    if (grid && key === "ArrowRight") return 1;
    if (grid && key === "ArrowLeft") return -1;
    return 0;
  }
  function onItemKey(event, key) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault?.();
      event.stopPropagation?.(); // 打开预览的这次按键不能再传到弹层的 keydown 上把它关掉
      open(key);
      return;
    }
    const step = stepFor(event.key);
    if (!step) return;
    event.preventDefault?.();
    const from = rows.findIndex((r) => r.item.key === key);
    const to = from + step;
    if (from < 0 || to < 0 || to >= rows.length) return;
    select(rows[to].item.key, { focus: true });
  }

  // L-40–L-43：预览弹层，按打开时的筛选 + 排序快照翻页。
  function open(key) {
    const snapshot = shown;
    const index = snapshot.findIndex((item) => item.key === key);
    if (index < 0 || preview) return;
    stopAudition();
    stopHover();
    select(key);
    preview = openLibraryPreview(doc, {
      items: snapshot,
      index,
      serveOutput: api.serveOutput,
      onFill: (plan) => ctx.applyFill(plan),
      onReveal: (name) => api.revealOutput(name),
      onClose: (at) => {
        preview = null;
        const item = snapshot[at];
        if (item) select(item.key, { focus: true });
      },
    });
  }

  // L-45：离开素材库页。
  function onHide() {
    stopAudition();
    stopHover();
  }

  return { refresh: refreshPane, onHide };
}
