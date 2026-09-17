import test from "node:test";
import assert from "node:assert/strict";
import { budgetLabel } from "../../desk/static/js/pure/budget_label.js";

test("每种来源都有中文标签，且估算与实测分得开", () => {
  assert.equal(budgetLabel("measured"), "已实测");
  assert.equal(budgetLabel("predicted"), "估算");
  assert.equal(budgetLabel("unavailable"), "算不出");
  assert.notEqual(budgetLabel("predicted"), budgetLabel("measured"));
});
