// tests/js/video_size.test.js —— 视频画幅规则（视频画幅设计 Z-01–Z-41）
import test from "node:test";
import assert from "node:assert/strict";
import {
  CUSTOM, ORIENTATIONS, estimateGiB, frameFollow, matchSize, parseSize, presetsFor, shapeOf, sizeError, snap32, tierOf,
  videoCostNote,
} from "../../desk/static/js/pure/video_size.js";

test("方向与档位：横屏三档、竖屏对调、方形三档，全部合法（Z-10/11）", () => {
  assert.deepEqual(ORIENTATIONS.map((o) => [o.value, o.label]), [["landscape", "横屏"], ["portrait", "竖屏"], ["square", "方形"]]);
  assert.deepEqual(presetsFor("landscape").map((p) => p.label), ["草稿 512×288", "标准 768×448", "清晰 1024×576"]);
  assert.deepEqual(presetsFor("portrait").map((p) => p.value), ["288x512", "448x768", "576x1024"]);
  assert.deepEqual(presetsFor("square").map((p) => p.value), ["384x384", "576x576", "768x768"]);
  for (const { value } of ORIENTATIONS) for (const p of presetsFor(value)) assert.equal(sizeError(p.width, p.height), "", p.value);
  assert.equal(tierOf("448x768"), 1);
  assert.equal(tierOf("768x768"), 2);
  assert.equal(tierOf("448x800"), -1);
  assert.equal(CUSTOM, "custom");
});

test("画布规则边界与文案顺序（Z-01/02）", () => {
  assert.equal(sizeError(Number.NaN, 288), "宽和高须为整数");
  assert.equal(sizeError(512.5, 288), "宽和高须为整数");
  assert.equal(sizeError(500, 288), "宽和高须为 32 的倍数");
  assert.equal(sizeError(224, 288), "每边须在 256–1344 之间");
  assert.equal(sizeError(256, 256), "");
  assert.equal(sizeError(1344, 768), "");
  assert.equal(sizeError(1376, 512), "每边须在 256–1344 之间");
  assert.equal(sizeError(1344, 800), "面积不能超过 768×1344（约 103 万像素）");
  assert.equal(sizeError(1344, 1024), "面积不能超过 768×1344（约 103 万像素）");
});

test("parseSize 与 snap32", () => {
  assert.deepEqual(parseSize("448x768"), { width: 448, height: 768 });
  assert.equal(parseSize("custom"), null);
  assert.equal(parseSize(""), null);
  assert.equal(snap32("450"), 448);
  assert.equal(snap32(500), 512);
  assert.ok(Number.isNaN(snap32("")));
  assert.ok(Number.isNaN(snap32("abc")));
});

test("形状判定：0.9–1.1 为方形（Z-20）", () => {
  assert.equal(shapeOf(1024, 1024), "square");
  assert.equal(shapeOf(990, 1100), "square"); // 0.9
  assert.equal(shapeOf(1100, 1000), "square"); // 1.1
  assert.equal(shapeOf(890, 1000), "portrait");
  assert.equal(shapeOf(1120, 1000), "landscape");
});

test("matchSize：档位找回方向与档位，不在档位里是自定义（Z-31）", () => {
  assert.deepEqual(matchSize(448, 768), { orientation: "portrait", size: "448x768" });
  assert.deepEqual(matchSize(576, 576), { orientation: "square", size: "576x576" });
  assert.deepEqual(matchSize(448, 800), { orientation: "portrait", size: CUSTOM });
  assert.deepEqual(matchSize(1024, 1000), { orientation: "square", size: CUSTOM });
});

test("frameFollow：方向不同就切并提示；自定义只提示拉伸；读不到尺寸不动（Z-21/22/24）", () => {
  assert.deepEqual(frameFollow({ orientation: "landscape", custom: false }, { width: 1024, height: 1024 }),
    { orientation: "square", note: "已按首帧切到方形" });
  assert.deepEqual(frameFollow({ orientation: "square", custom: false }, { width: 1000, height: 1050 }), { orientation: null, note: "" });
  assert.deepEqual(frameFollow({ orientation: "landscape", custom: true }, { width: 720, height: 1280 }),
    { orientation: null, note: "首帧是竖屏，画幅是横屏，画面会被拉伸变形" });
  assert.deepEqual(frameFollow({ orientation: "landscape", custom: false }, null), { orientation: null, note: "" });
  assert.deepEqual(frameFollow({ orientation: "landscape", custom: false }, { width: undefined, height: 5 }), { orientation: null, note: "" });
});

test("提醒：按面积判断很慢，按公式外推超 40 GiB 提醒（Z-40/41）", () => {
  assert.equal(estimateGiB(512, 288, 49), 27);
  assert.equal(videoCostNote(512, 288, 49), "");
  const slow = videoCostNote(1024, 576, 243);
  assert.match(slow, /^大画幅加 10 秒以上会非常慢：实测 1024×576 曾 20 分钟只走完 2\/16 步/);
  assert.match(slow, /超过视频生成的 40 GiB 上限，可能中途失败。$/);
  assert.equal(videoCostNote(1024, 576, 192), "按实测外推约需 48 GiB，超过视频生成的 40 GiB 上限，可能中途失败。");
  assert.equal(videoCostNote(576, 1024, 192), videoCostNote(1024, 576, 192), "按面积，不分横竖");
  assert.equal(videoCostNote(768, 1344, 49), "");
  assert.equal(videoCostNote(768, 448, 362), "按实测外推约需 50 GiB，超过视频生成的 40 GiB 上限，可能中途失败。");
});
