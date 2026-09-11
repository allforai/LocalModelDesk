// ui:libraryPane —— 成品 + 历史合并时间倒序；点击就地播放；「回填」经 main 切 tab 写表单（R-ui-06）。
import * as api from "../api.js";
import { fillPlan } from "../pure/history_fill.js";
import { formatBytes, formatDuration, formatTimestamp } from "../pure/format.js";
import { addIcon } from "../icons.js";
import { describeJobError } from "../pure/job_error.js";

const KIND_LABEL = { video: "视频", music: "音乐", file: "文件" };
const STATUS_LABEL = { done: "完成", failed: "失败", cancelled: "已取消" };

export function createLibraryPane(root, ctx) { // ctx.applyFill(plan)
  const doc = root.ownerDocument;
  const els = {
    refreshBtn: root.querySelector("[data-lib-refresh]"),
    player: root.querySelector("[data-lib-player]"),
    list: root.querySelector("[data-lib-list]"),
    error: root.querySelector("[data-lib-error]"),
  };

  async function refresh() {
    els.error.textContent = "";
    try {
      const [outputs, history] = await Promise.all([api.listOutputs(), api.listHistory()]);
      render(outputs, history);
    } catch (err) {
      els.error.textContent = err.message;
    }
  }

  function render(outputs, history) {
    els.list.replaceChildren();
    if (!outputs.length && !history.length) {
      const empty = doc.createElement("li");
      empty.className = "empty";
      empty.textContent = "还没有成品。去「视频」或「音乐」面板生成第一件，它会出现在这里。";
      els.list.append(empty);
      return;
    }
    const outByName = new Map(outputs.map((output) => [output.name, output]));
    const matchedOutputNames = new Set();
    const rows = history.map((entry) => {
      const output = entry.output ? outByName.get(entry.output) ?? null : null;
      if (output) matchedOutputNames.add(output.name);
      return { ts: entry.ts ?? "", entry, output };
    });
    for (const output of outputs) {
      if (!matchedOutputNames.has(output.name)) {
        rows.push({ ts: output.ts ?? "", entry: null, output });
      }
    }
    rows.sort((a, b) => String(b.ts).localeCompare(String(a.ts)));
    for (const row of rows) els.list.append(rowNode(row));
  }

  function summarize(entry) {
    const params = entry.params ?? {};
    const text = String(params.prompt ?? params.caption ?? "");
    const spec = entry.kind === "video"
      ? [
        params.width && params.height ? `${params.width}×${params.height}` : null,
        params.frames ? `约 ${Math.round(params.frames / 24)} 秒` : null,
        params.steps ? `${params.steps}步` : null,
      ]
      : [params.duration ? `${params.duration}s` : null];
    return {
      text: text.length > 60 ? `${text.slice(0, 60)}…` : text,
      spec: spec.filter(Boolean).join(" · "),
    };
  }

  function rowNode({ entry, output }) {
    const li = doc.createElement("li");
    li.className = "card lib-row";
    const head = doc.createElement("div");
    if (entry) {
      const summary = summarize(entry);
      const title = doc.createElement("p");
      title.className = "lib-title";
      title.textContent = summary.text || "（无提示词）";
      const meta = doc.createElement("p");
      meta.className = "lib-meta";
      meta.textContent = [
        KIND_LABEL[entry.kind] ?? entry.kind,
        STATUS_LABEL[entry.status] ?? entry.status,
        formatTimestamp(entry.ts),
        entry.duration_s != null ? `耗时 ${formatDuration(entry.duration_s)}` : null,
        summary.spec,
      ].filter(Boolean).join(" · ");
      head.append(title, meta);
      if (entry.error) {
        const [code, ...rest] = entry.error.split(": ");
        const { title: errorTitle, detail } = describeJobError({ code, message: rest.join(": ") });
        const error = doc.createElement("p");
        error.className = "inline-error";
        error.textContent = errorTitle;
        const details = doc.createElement("details");
        details.className = "lib-error-details";
        const summary = doc.createElement("summary");
        summary.textContent = "详情";
        const pre = doc.createElement("pre");
        pre.textContent = detail;
        details.append(summary, pre);
        head.append(error, details);
      }
    } else {
      const title = doc.createElement("p");
      title.className = "lib-title";
      title.textContent = output.name;
      const meta = doc.createElement("p");
      meta.className = "lib-meta";
      meta.textContent = `无历史记录 · ${formatBytes(output.bytes)} · ${formatTimestamp(output.ts)}`;
      head.append(title, meta);
    }

    const actions = doc.createElement("div");
    actions.className = "lib-actions";
    const playable = output ?? (entry?.output ? { name: entry.output, kind: entry.kind } : null);
    li.outputName = playable?.name ?? null;
    if (playable?.name) (li.dataset ??= {}).outputName = playable.name;
    const rowTitle = entry ? summarize(entry).text : output.name;
    if (playable) {
      li.addEventListener("click", () => playOutput(playable, rowTitle));
      const play = doc.createElement("button");
      play.textContent = "播放";
      addIcon(play, "play", doc);
      play.addEventListener("click", (event) => {
        event.stopPropagation();
        playOutput(playable, rowTitle);
      });
      actions.append(play);
      const reveal = doc.createElement("button");
      reveal.textContent = "在访达中显示";
      addIcon(reveal, "folder", doc);
      reveal.addEventListener("click", async (event) => {
        event.stopPropagation();
        try { await api.revealOutput(playable.name); } catch (error) { els.error.textContent = error.message; }
      });
      actions.append(reveal);
    }
    const plan = entry ? fillPlan(entry) : null;
    if (plan) {
      const fill = doc.createElement("button");
      fill.textContent = "回填参数";
      addIcon(fill, "sliders", doc);
      fill.addEventListener("click", (event) => {
        event.stopPropagation();
        ctx.applyFill(plan);
      });
      actions.append(fill);
    }
    li.append(head, actions);
    return li;
  }

  function playOutput(output, title = "") {
    for (const row of els.list.children ?? []) {
      const base = String(row.className ?? "").replace(/\s*\bplaying\b/, "");
      row.className = row.outputName === output.name ? `${base} playing` : base;
    }
    els.player.replaceChildren();
    const isVideo = output.kind === "video" || /\.(mp4|webm)$/i.test(output.name);
    const media = doc.createElement(isVideo ? "video" : "audio");
    media.controls = true;
    media.autoplay = true;
    media.src = api.serveOutput(output.name);
    const caption = doc.createElement("p");
    caption.className = "hint";
    caption.textContent = `正在播放：${title || output.name}`;
    els.player.append(media, caption);
    els.player.scrollIntoView?.({ block: "start", behavior: "smooth" });
  }

  els.refreshBtn.addEventListener("click", refresh);
  return { refresh };
}
