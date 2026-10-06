import test from "node:test";
import assert from "node:assert/strict";
import { Element } from "./support/fake_dom.js";
import { renderSegmentSwitch } from "../../desk/static/js/widgets/segment_switch.js";

const doc = { createElement: (tag) => new Element(tag) };

test("setChecked 改选中但不触发 onChange；之后点任意一项按新选中判断（视频画幅方向）", async () => {
  const changes = [];
  const group = renderSegmentSwitch(doc, { labels: ["横屏", "竖屏", "方形"], ariaLabel: "画幅方向", onChange: (i) => changes.push(i) });
  group.setChecked(2);
  assert.deepEqual(group.children.map((b) => b.attrs["aria-checked"]), ["false", "false", "true"]);
  assert.deepEqual(group.children.map((b) => b.tabIndex), [-1, -1, 0]);
  assert.deepEqual(changes, []);
  await group.children[2].click();
  assert.deepEqual(changes, [], "点已选中的项不算变化");
  await group.children[0].click();
  assert.deepEqual(changes, [0]);
});

test("setDisabled 同时设每个按钮的 disabled 与 title；解除后清空 title", () => {
  const group = renderSegmentSwitch(doc, { labels: ["横屏", "竖屏"], ariaLabel: "画幅方向" });
  group.setDisabled(true, "接着往下生沿用上一段的画幅");
  assert.deepEqual(group.children.map((b) => [b.disabled, b.title]),
    [[true, "接着往下生沿用上一段的画幅"], [true, "接着往下生沿用上一段的画幅"]]);
  group.setDisabled(false);
  assert.deepEqual(group.children.map((b) => [b.disabled, b.title]), [[false, ""], [false, ""]]);
});
