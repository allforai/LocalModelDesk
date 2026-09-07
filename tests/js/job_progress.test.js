import test from "node:test";
import assert from "node:assert/strict";
import { parseStepProgress } from "../../desk/static/js/pure/job_progress.js";

test("从日志里取最后一个 step N/M", () => {
  assert.deepEqual(parseStepProgress("start\nstep 1/16 12.2s\nstep 5/16 4.1s\n"), { step: 5, total: 16, pct: 31 });
  assert.equal(parseStepProgress("text encoder\n"), null);
});
