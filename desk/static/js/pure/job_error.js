// 作业失败对象 → {title, detail}。title 是人话；detail 保留原始码与日志尾部供「详情」展开。
const RULES = [
  [/BudgetExceeded|out of memory|SWAPPING/i, "内存不足，生成被中止"],
  [/load_rgb_image|ffmpeg|decode|Invalid data/i, "素材无法解码，请换一张图片或视频"],
  [/lyrics must be a non-empty/i, "请填写歌词"],
];
const CODE_TITLE = { lyrics_required: null, no_output: "生成结束但没有产出文件", spawn_failed: "无法启动生成程序", worker_failed: "生成程序意外退出", insufficient_memory: "可用内存不足" };

export function describeJobError(error) {
  if (!error) return { title: "", detail: "" };
  const tail = typeof error.log_tail === "string" ? error.log_tail : "";
  const detail = [`${error.code}: ${error.message}`, tail].filter(Boolean).join("\n");
  const hit = RULES.find(([re]) => re.test(tail) || re.test(error.message ?? ""));
  if (hit) return { title: hit[1], detail };
  if (error.code in CODE_TITLE) return { title: CODE_TITLE[error.code] ?? error.message, detail };
  return { title: `生成失败（${error.code}）`, detail };
}
