import test from "node:test";
import assert from "node:assert/strict";
import { fitBadge, fitDetail, fitReportView } from "../../desk/static/js/pure/fit.js";

const GIB = 1024 ** 3;

test("fitBadge：四态各自的短文案与徽标种类", () => {
  assert.deepEqual(fitBadge({ level: "fits" }), { label: "能跑", badgeKind: "ok" });
  assert.deepEqual(fitBadge({ level: "tight" }), { label: "偏紧", badgeKind: "busy" });
  assert.deepEqual(fitBadge({ level: "too_big" }), { label: "装不下", badgeKind: "unknown" });
  assert.deepEqual(fitBadge({ level: "unknown" }), { label: "算不出", badgeKind: "none" });
  assert.deepEqual(fitBadge(null), { label: "算不出", badgeKind: "none" });
});

test("fitDetail：算不出时不报数字，只说算不出", () => {
  assert.equal(fitDetail({ level: "unknown" }), "这台机器的重活能力还没能测出来");
  assert.equal(fitDetail(null), "这台机器的重活能力还没能测出来");
});

test("fitDetail：装不下时说需要多少、能给多少、差多少", () => {
  const fit = { level: "too_big", needed_bytes: 120 * GIB, available_bytes: 100 * GIB, shortfall_bytes: 20 * GIB, headroom_bytes: -20 * GIB };
  const text = fitDetail(fit);
  assert.match(text, /120\.0 GiB/);
  assert.match(text, /100\.0 GiB/);
  assert.match(text, /差 20\.0 GiB/);
});

test("fitDetail：能跑/偏紧时说需要多少、能给多少、剩多少", () => {
  const fit = { level: "fits", needed_bytes: 16 * GIB, available_bytes: 100 * GIB, shortfall_bytes: 0, headroom_bytes: 84 * GIB };
  const text = fitDetail(fit);
  assert.match(text, /16\.0 GiB/);
  assert.match(text, /剩 84\.0 GiB/);
});

test("fitReportView：算不出机器能力时不推荐任何模型", () => {
  const catalog = [
    { key: "a", fit: { level: "unknown" } },
    { key: "b", fit: { level: "unknown" } },
  ];
  const view = fitReportView(catalog);
  assert.equal(view.capacityKnown, false);
  assert.deepEqual(view.fits, []);
  assert.deepEqual(view.tight, []);
  assert.deepEqual(view.tooBig, []);
});

test("fitReportView：能力已知时按三态分组", () => {
  const catalog = [
    { key: "a", fit: { level: "fits" } },
    { key: "b", fit: { level: "tight" } },
    { key: "c", fit: { level: "too_big" } },
    { key: "d", fit: { level: "fits" } },
  ];
  const view = fitReportView(catalog);
  assert.equal(view.capacityKnown, true);
  assert.deepEqual(view.fits.map((e) => e.key), ["a", "d"]);
  assert.deepEqual(view.tight.map((e) => e.key), ["b"]);
  assert.deepEqual(view.tooBig.map((e) => e.key), ["c"]);
});

test("fitReportView：空目录也算不出（没有条目可判断）", () => {
  const view = fitReportView([]);
  assert.equal(view.capacityKnown, false);
});

test("fitReportView：混有一个 unknown 条目也整体算不出——能力是整机一个数，不是有的模型能判有的不能", () => {
  const catalog = [
    { key: "a", fit: { level: "fits" } },
    { key: "b", fit: { level: "unknown" } },
  ];
  const view = fitReportView(catalog);
  assert.equal(view.capacityKnown, false);
});
