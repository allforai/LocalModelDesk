import test from "node:test";
import assert from "node:assert/strict";
import { describeJobError } from "../../desk/static/js/pure/job_error.js";

test("常见失败原因翻成人话，原始码放进详情", () => {
  assert.deepEqual(describeJobError({ code: "exit_nonzero", message: "exit 1", log_tail: "mlx_h3.memory.BudgetExceeded: SWAPPING" }),
    { title: "内存不足，生成被中止", detail: "exit_nonzero: exit 1\nmlx_h3.memory.BudgetExceeded: SWAPPING" });
  assert.equal(describeJobError({ code: "exit_nonzero", message: "exit 1", log_tail: "ffmpeg ... load_rgb_image" }).title, "素材无法解码，请换一张图片或视频");
  assert.equal(describeJobError({ code: "lyrics_required", message: "请填写歌词" }).title, "请填写歌词");
  assert.equal(describeJobError({ code: "no_output", message: "exit 0 but output file missing" }).title, "生成结束但没有产出文件");
  assert.equal(describeJobError({ code: "weird", message: "?" }).title, "生成失败（weird）");
});
