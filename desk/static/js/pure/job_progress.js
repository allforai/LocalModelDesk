// Pure helper: extract step-progress from a job's accumulated log text.
export function parseStepProgress(logText) {
  const all = [...String(logText ?? "").matchAll(/step\s+(\d+)\s*\/\s*(\d+)/g)];
  if (!all.length) return null;
  const [, s, t] = all.at(-1);
  const step = Number(s), total = Number(t);
  return total > 0 ? { step, total, pct: Math.round((step / total) * 100) } : null;
}
