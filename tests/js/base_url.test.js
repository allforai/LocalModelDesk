import test from "node:test";
import assert from "node:assert/strict";
import { baseUrls } from "../../desk/static/js/pure/base_url.js";

test("普通 host：OpenAI 带 /v1，Anthropic 不带", () => {
  const u = baseUrls({ host: "192.168.31.68", port: 8770 });
  assert.equal(u.openai, "http://192.168.31.68:8770/v1");
  assert.equal(u.anthropic, "http://192.168.31.68:8770");
  assert.equal(u.displayHost, "192.168.31.68");
  assert.equal(u.note, null);
});

test("0.0.0.0：占位符 + 附注", () => {
  const u = baseUrls({ host: "0.0.0.0", port: 8770 });
  assert.equal(u.displayHost, "<本机局域网地址>");
  assert.equal(u.openai, "http://<本机局域网地址>:8770/v1");
  assert.equal(u.anthropic, "http://<本机局域网地址>:8770");
  assert.ok(u.note.includes("局域网 IP"));
});

test("0.0.0.0 用后端给的局域网地址，而不是占位符", () => {
  const urls = baseUrls({ host: "0.0.0.0", port: 8770, lanHost: "192.168.31.68" });
  assert.equal(urls.openai, "http://192.168.31.68:8770/v1");
  assert.equal(urls.note, "监听所有网卡；其他设备用 192.168.31.68 访问，本机也可用 127.0.0.1");
});
