import test from "node:test";
import assert from "node:assert/strict";
import { parseStepProgress } from "../../desk/static/js/pure/job_progress.js";

test("从日志里取最后一个 step N/M", () => {
  assert.deepEqual(parseStepProgress("start\nstep 1/16 12.2s\nstep 5/16 4.1s\n"), { step: 5, total: 16, pct: 31 });
  assert.equal(parseStepProgress("text encoder\n"), null);
});

test("图片进度接受真实 tqdm 前缀后的 JSON，不把 loading/done 当进度", () => {
  const log = ' 25%|██▌| 1/4 [00:02<00:06, 2.26s/it]{"event":"progress","step":2,"steps":4}\n';
  assert.deepEqual(parseStepProgress(log), { step: 2, total: 4, pct: 50 });
  assert.deepEqual(parseStepProgress(log + '{"event":"done","steps":4}\n'), { step: 2, total: 4, pct: 50 });
  assert.equal(parseStepProgress('{"event":"loading"}\n'), null);
});

test("畸形、截断和越界进度不覆盖最后有效值", () => {
  const valid = '{"event":"progress","step":1,"steps":4}\n';
  for (const bad of ['{"event":"progress","step":', '{bad}\n', '{"event":"progress","step":5,"steps":4}\n', '{"event":"progress","step":1,"steps":0}\n'])
    assert.deepEqual(parseStepProgress(valid + bad), { step: 1, total: 4, pct: 25 });
});
