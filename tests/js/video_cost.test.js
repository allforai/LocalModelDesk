import test from "node:test";
import assert from "node:assert/strict";
import { videoCostNote } from "../../desk/static/js/pure/video_cost.js";

test("只有清晰画幅加 10 秒以上才提醒（有实测依据的组合）", () => {
  const slow = videoCostNote("1024x576", 243);
  assert.match(slow, /20 分钟只走完 2\/16 步/);
  assert.equal(videoCostNote("1024x576", "362"), slow);
  assert.equal(videoCostNote("1024x576", 192), "");
  assert.equal(videoCostNote("768x448", 362), "");
  assert.equal(videoCostNote("512x288", 49), "");
});
