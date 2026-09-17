import test from "node:test";
import assert from "node:assert/strict";
import { budgetLabel } from "../../desk/static/js/pure/budget_label.js";

test("每种来源都有中文标签，且估算与实测分得开", () => {
  assert.equal(budgetLabel("measured"), "已实测");
  assert.equal(budgetLabel("predicted"), "估算");
  assert.equal(budgetLabel("unavailable"), "算不出");
  assert.notEqual(budgetLabel("predicted"), budgetLabel("measured"));
});

test("tick 把预算交给状态栏：没接线时状态栏永远拿不到额度", async () => {
  // 这条盯的是接线本身。Task 8 把 statusbar 的可选第 5 参做好了，但 main.js
  // 从没去取 /api/budget，于是「对话额度」这行文案永远不会出现。
  const { default: source } = await import("node:fs").then((fs) => ({
    default: fs.readFileSync(new URL("../../desk/static/js/main.js", import.meta.url), "utf8"),
  }));
  assert.match(source, /api\.budget\(\)/, "main.js 没有调用 api.budget()");
  assert.match(source, /statusbar\.update\([^)]*budget/, "取到的预算没传给 statusbar.update");
});
