// Pure helper: extract step-progress from a job's accumulated log text.
export function parseStepProgress(logText) {
  let result = null;
  const matches = String(logText ?? "").matchAll(/step\s+(\d+)\s*\/\s*(\d+)|(\{[^\n]*\})/g);
  for (const match of matches) {
    let step, total;
    if (match[3]) {
      try {
        const event = JSON.parse(match[3]);
        if (event.event !== "progress") continue;
        step = event.step; total = event.steps;
      } catch { continue; }
    } else { step = Number(match[1]); total = Number(match[2]); }
    if (Number.isInteger(step) && Number.isInteger(total) && total > 0 && step >= 0 && step <= total)
      result = { step, total, pct: Math.round(step / total * 100) };
  }
  return result;
}
