import test from "node:test";
import assert from "node:assert/strict";
import { applyEnabled, initialChecked, rowText, TRY_PHRASE } from "../../desk/static/js/pure/agent_skill.js";

const row = (key, state, extra = {}) => ({ key, name: key, state, detected: true, ...extra });

test("installed 与 stale 的行初始勾选，其余不勾", () => {
  const rows = [row("claude", "installed"), row("codex", "stale"), row("pi", "absent"), row("dsh", "occupied")];
  assert.deepEqual([...initialChecked(rows)].sort(), ["claude", "codex"]);
});

test("应用按钮：只有会产生变化时才可点（A-64）", () => {
  const rows = [row("claude", "installed"), row("codex", "stale"), row("pi", "absent")];
  assert.equal(applyEnabled(rows, new Set(["claude"])), true, "取消勾选 stale 行会卸掉它");
  assert.equal(applyEnabled(rows, new Set(["claude", "codex"])), true, "stale 勾着也要能点，点了才会更新");
  const clean = [row("claude", "installed"), row("pi", "absent")];
  assert.equal(applyEnabled(clean, new Set(["claude"])), false);
  assert.equal(applyEnabled(clean, new Set(["claude", "pi"])), true);
  assert.equal(applyEnabled(clean, new Set()), true);
});

test("勾选 occupied 的行不算变化：它装不上", () => {
  const rows = [row("claude", "occupied")];
  assert.equal(applyEnabled(rows, new Set(["claude"])), false);
});

test("状态文字", () => {
  assert.deepEqual(rowText(row("a", "installed")), { status: "已安装", tone: "ok" });
  assert.deepEqual(rowText(row("a", "absent")), { status: "未安装", tone: "none" });
  assert.equal(rowText(row("a", "stale")).status, "指向旧位置，点应用更新");
  assert.equal(rowText(row("a", "stale", { target: "/gone/x" , message: null })).tone, "warn");
  assert.equal(rowText(row("a", "occupied", { message: "这里已有同名文件或目录，台面不会改动" })).status,
    "这里已有同名文件或目录，台面不会改动");
  assert.equal(rowText(row("a", "error", { message: "Permission denied" })).status, "无法写入：Permission denied");
});

test("试用语", () => {
  assert.equal(TRY_PHRASE, "用本地模型把这句话翻成英文：今天天气很好");
});
