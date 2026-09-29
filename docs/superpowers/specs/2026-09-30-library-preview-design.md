# 模块设计：素材库预览（library-preview）

**日期** 2026-09-30
**来源** 用户 2026-09-29「素材库应该要使用预览的方式」「参考文件夹的样式，可以缩图，可以明细，可以列表等等」；三种视图与两段设计「按推荐来」「可以，继续」。
**上游** 现有素材库 `desk/static/js/panes/library.js`（R-ui-06、B-43、issue #12、F3）；遮罩对话框骨架 `widgets/confirm.js`、`widgets/media_picker.js`；本机记忆状态的做法 `widgets/sessions_collapse.js`。

每条 **[L-xx]** 可写成测试断言。

---

## 0. 范围与非目标

- 范围：素材库页面改为类访达的三种视图（缩略图 / 列表 / 明细）+ 类型筛选 + 预览弹层 + 键盘操作。纯前端。
- [L-00a] 不改后端接口：仍用 `GET /api/outputs`、`GET /api/history?limit=200`、`/api/outputs/<name>`（支持 Range）、reveal 接口。
- [L-00b] 不做访达的「分栏」「画廊」视图。
- [L-00c] 不做服务端缩略图/海报帧生成；视频首帧由浏览器 `<video preload="metadata">` 取。
- [L-00d] 不做删除、重命名、多选、拖拽导出。
- [L-00e] 页面顶部的播放区（`[data-lib-player]`）取消；播放、预览都进预览弹层（缩略图视图音乐卡片的就地试听除外，见 L-24）。
- 台面未发布，不谈兼容。

---

## 1. 条目模型（pure/library_view.js）

- [L-01] 合并规则沿用现状：历史与成品按文件名匹配；一条历史的 `output` 与 `joined_output` 各占一条（B-43）；没匹配到历史的成品单独一条（「无历史记录」）；有历史但文件都不在的也占一条。
- [L-02] 每条条目归一为：`{ key, kind: "image"|"video"|"music"|"file", status, ts, title, prompt, spec, duration_s?, width?, height?, bytes?, gen_s?, output?: name, missing: bool, entry?: 历史记录, error? }`。`key` 在一次渲染内唯一且稳定（文件名优先，否则历史 ts+kind）。
- [L-03] `missing`：有历史、状态为完成、`output` 名在成品列表里找不到。
- [L-04] 时长：音乐取 `audio_seconds`，否则 `params.duration`；视频取 `params.frames / 24`；图片无。画幅取 `params.width×height`。
- [L-05] 筛选：`all | image | video | music`；`file` 类只在 `all` 下出现。
- [L-06] 排序：键为 `ts`（生成时间）| `title`（提示词）| `kind`（类型）| `duration`（时长）| `dims`（画幅，按宽×高面积）| `bytes`（文件大小）| `gen`（耗时），方向 `asc | desc`；缩略列不可排序；缺值一律排在最后（不论方向）；同值按 `ts` 倒序稳定。默认 `ts desc`。

## 2. 工具栏与状态记忆

- [L-10] 工具栏一行：左侧类型筛选分段控件（全部 / 图片 / 视频 / 音乐，复用 `widgets/segment_switch.js` 的样式与语义）；右侧视图切换三个图标按钮（缩略图 / 列表 / 明细，`aria-pressed`、`aria-label`），缩略图视图时出现大小滑块，最右「刷新」。
- [L-11] 视图、筛选、缩略图大小、明细排序记在 `localStorage` 键 `lmd.library`（JSON）；读写都包 try/catch，读不到用默认值（缩略图、全部、200px、`ts desc`）；值非法时回落默认。
- [L-12] 筛选后为空：显示「没有这类成品」并写明当前筛选（例：「当前筛选：视频」）；整体为空沿用现有引导语。

## 3. 三种视图

- [L-20] 缩略图：自适应网格 `repeat(auto-fill, minmax(var(--lib-thumb), 1fr))`，滑块调 `--lib-thumb` 140–320px。卡片：方形媒体区 + 提示词两行截断 + 时间一行。
- [L-21] 图片卡片：`<img loading="lazy">`，`object-fit: cover`。
- [L-22] 视频卡片：进入视口（IntersectionObserver；环境没有时直接加载）才设 `src=<url>#t=0.1`、`preload="metadata"`、`muted`、`playsinline`；角标显示时长。鼠标悬停静音播放，移开暂停并回到 0.1 秒；同一时刻最多一个卡片在悬停播放。
- [L-23] 音乐卡片：渐变底 + 音乐图标 + 时长。
- [L-24] 音乐卡片右下角小播放按钮就地试听（单个 `<audio>`，再点暂停；开别的试听或打开预览时停掉）；点按钮不触发选中/打开。
- [L-25] 失败/取消（无成品）：灰卡 + 警示图标 + 状态字；`missing`：灰卡 + 「文件已不在」。
- [L-26] 媒体加载失败（img/video `error`）：该卡片退回类型图标占位，不影响其他卡片。
- [L-27] 列表：每行 48px 缩略图（规则同 L-21/L-22，但视频不悬停播放）+ 提示词 + 元信息行（类型 · 状态 · 时间 · 耗时 · 规格）+ 右侧动作（预览、在访达中显示、回填参数）；失败记录照旧显示错误块（F3）。
- [L-28] 明细：`<table>`，列：缩略（32px）、提示词、类型、生成时间、时长、画幅、大小、耗时。除缩略列外表头是按钮，点击按该列排序，再点反向，`aria-sort` 标当前列；缺值显示「—」。

## 4. 选中与键盘

- [L-30] 单击条目 = 选中（`aria-selected`、选中样式）；双击、Enter、空格 = 打开预览。
- [L-31] 列表/缩略图容器可聚焦（`tabindex=0`，roving 选中）；缩略图视图 ←/→ 前后一个，↑/↓ 按当前列数跳一行；列表/明细 ↑/↓ 前后一个。选中项滚入视野（`block: "nearest"`）。
- [L-32] 切换筛选、排序、刷新后：原选中项仍在就保持，否则清空选中。
- [L-33] 条目内按钮（预览、在访达中显示、回填、试听）点击不冒泡为选中/打开；各自行为同现状（reveal 失败把服务端文案写进错误行，issue #12）。

## 5. 预览弹层（widgets/library_preview.js）

- [L-40] 复用遮罩 + `role=dialog` + `aria-modal` + Esc/点遮罩关闭的骨架；打开时焦点进弹层，关闭后焦点与选中回到最后预览的条目。
- [L-41] 主区：图片按窗口适配；视频 `controls autoplay`（有声）；音乐大卡片 + `<audio controls autoplay>`；失败显示错误块；`missing` 显示「文件已不在」。
- [L-42] 信息区（宽屏在右，窄于 900px 在下）：完整提示词、全部参数、生成时间、耗时、文件名与大小；按钮「回填参数」（有 fillPlan 时；调用 `ctx.applyFill(plan)` 并关闭弹层）、「在访达中显示」（有文件时）、「关闭」。
- [L-43] ←/→ 在当前筛选+排序顺序里切上一件/下一件（到头不循环，按钮置灰）；空格、Esc 关闭。切换或关闭时停止并释放上一件媒体（`pause()` + 移除 `src`）。
- [L-44] 动效：遮罩淡入、面板淡入+轻微缩放（180ms 左右）；全局 `prefers-reduced-motion` 规则生效。

## 6. 文件与测试

- 新增 `desk/static/js/pure/library_view.js`（L-01–L-06）、`desk/static/js/widgets/library_preview.js`（L-40–L-44）；重写 `desk/static/js/panes/library.js`（工具栏、三视图、选中、键盘）；`index.html` 素材库 section 改结构；`app.css` 新增素材库一节；`icons.js` 按需补图标（grid、list、table、music）。
- [L-50] `node --test`：纯函数（合并含 B-43、missing、筛选、排序缺值在后）；假 DOM：视图切换与记忆（含存储抛错）、单击选中/双击打开、键盘移动、预览 ←/→ 与到头置灰、回填调用 applyFill 并关闭、reveal 失败文案、试听按钮不冒泡。现有 `library_pane.test.js` 中依赖顶部播放区的断言改为断言预览弹层。
- [L-51] e2e（Playwright）：三视图渲染、预览打开/切换/关闭、键盘导航、回填回到对应页面（沿用 `test_library_panel.py` 的回填用例）；在 1280 与 900 宽截图目检，截图目录由 `$LMD_LIBRARY_SHOTS` 指定。
- 完成标准：JS、Python、e2e 全绿；截图目检三视图与弹层在亮/暗两种主题下正常。
