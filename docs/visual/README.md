# 视觉基线（tracked）

`visual-baseline.candidate.json` / `interaction-baseline.candidate.json` 是**候选规则**，不是已确认基线。

## 为什么放在这里

上一次冻结的基线随 `docs/cross-exam/` 一起从公开树里删掉了，git 历史与磁盘上都找不回（2026-09-16 查证）。
没有基线，视觉 reviewer 判"这里不对"时无句可引，渲染器拒收裁决，整轮视觉验收作废；重新逐类确认一次
基线是一整场对话。所以规则从此跟代码一起进 git：`.gitignore` 只挡运行产物（`docs/cross-exam/**/evidence/`
与录屏），基线与报告都跟踪。

## 候选 → 基线

候选里的每条规则都从当前代码读出来并注明出处（`basis`），供 `/superstorm:cross-exam` 的视觉验收
逐类摆给用户确认。用户确认后：

1. 该类的 `confirmation` 写用户原话、`confirmed_at` 写时间；
2. 整份复制进本轮 run 的 `visual/visual-baseline.json`，按原始字节算 SHA-256 绑定；
3. 确认后的版本回写到这里，作为下一轮的起点。

`status` 仍是 `candidate` 的文件不能当基线用：渲染器要的是带 confirmation 的那一份。

## 候选里已知的待决项

- `layout` 里钉死（pinned）规则的 `ends` 两端按 `width_range` 的 min / max 写。候选用的是
  **提案值 900 与 2560**（900 = 媒体面单列断点 899px 之上的第一个可用宽；2560 = 常见外接显示器）。
  用户确认 `width_range` 后，两端的键要改成确认值，`empty` 的量也跟着重算。
- `environment` 的 pointer 轴：候选按"接鼠标（macOS 常显滚动条并占位）"写。若本轮也要覆盖
  仅触控板（悬浮滚动条），该类要多一个值，滚动条那条规则要分别给出两种指针下的样子。
- 上一轮基线里 K2 / K4 附注 / K5 附注 / L2 / L6 的原文只从计划文档里抢救回残句（见各条 `basis`
  的 `recovered_from`），其余规则是从现在的代码重新读出来的，不是旧基线的原文。
