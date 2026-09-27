// data:historyEntry → {pane, fields} 回填计划；未知 kind / 无参数 → null（R-ui-06）。
export function fillPlan(entry) {
  if (!entry || typeof entry !== "object") return null;
  const params = entry.params;
  if (!params || typeof params !== "object") return null;
  if (params.op === "compose" || params.op === "soundtrack") return null; // 合成、配乐成品没有可回填的参数（B-74、S-06）
  const session = { session_id: entry.session_id ?? null, attempt_id: entry.attempt_id ?? null };
  if (entry.kind === "video") {
    return {
      pane: "video",
      ...session,
      fields: {
        prompt: params.prompt ?? "",
        width: params.width ?? null,
        height: params.height ?? null,
        frames: params.frames ?? null,
        steps: params.steps ?? null,
        // V-61：带种子才能显示「沿用素材库里这段」；V-05：首帧来自图片会话时历史条目在顶层记 refs。
        seed: Number.isInteger(params.seed) ? params.seed : null,
        ...(entry.refs && Object.keys(entry.refs).length ? { refs: entry.refs } : {}),
        ...(params.mode ? { mode: params.mode, first_frame: params.first_frame,
          last_frame: params.last_frame, ref_video: params.ref_video, use_audio: params.use_audio } : {}),
      },
    };
  }
  if (entry.kind === "music") {
    return {
      pane: "music",
      ...session,
      fields: {
        caption: params.caption ?? "",
        lyrics: params.lyrics ?? "",
        duration: params.duration ?? null,
        seed: Number.isInteger(params.seed) ? params.seed : null,
      },
    };
  }
  if (entry.kind === "image") {
    // 设计 D-93：带上会话与尝试，素材库回填据此回到原会话（D-94）；种子缺失为 null，不再补默认值。
    return {
      pane: "image", session_id: entry.session_id ?? null, attempt_id: entry.attempt_id ?? null,
      fields: {
        prompt: params.prompt ?? "", width: params.width ?? 1024, height: params.height ?? 1024,
        steps: params.steps ?? 40, seed: Number.isInteger(params.seed) ? params.seed : null,
      },
    };
  }
  return null;
}
