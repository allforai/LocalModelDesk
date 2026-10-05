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
- [L-00f] 历史接口仍只取最近 200 条；更早的成品照旧以「无历史记录」条目出现（标题为文件名），不在本次扩展。
- 台面未发布，不谈兼容。

---

## 1. 条目模型（pure/library_view.js）

- [L-01] 合并规则沿用现状：历史与成品按文件名匹配；一条历史的 `output` 与 `joined_output` 各占一条（B-43）；没匹配到历史的成品单独一条（「无历史记录」）；有历史但文件都不在的也占一条。
- [L-02] 每条条目归一为：`{ key, kind: "image"|"video"|"music"|"file", status, ts, title, prompt, spec, duration_s?, width?, height?, bytes?, gen_s?, output?: name, missing: bool, entry?: 历史记录, error? }`。`key` 跨刷新稳定（L-32 靠它保持选中）：有文件用 `o:<文件名>`，否则 `h:<ts>:<kind>:<attempt_id 或空>`，同一次渲染内重复时追加 `#2`、`#3`。
- [L-03] `missing`：有历史、状态为完成、`output` 名在成品列表里找不到。
- [L-04] 时长：音乐取 `audio_seconds`，否则 `params.duration`；视频取 `params.frames / 24`；图片无。画幅取 `params.width×height`。
- [L-05] 筛选：`all | image | video | music`；`file` 类只在 `all` 下出现。
- [L-06] 排序：键为 `ts`（生成时间）| `title`（提示词）| `kind`（类型）| `duration`（时长）| `dims`（画幅，按宽×高面积）| `bytes`（文件大小）| `gen`（耗时），方向 `asc | desc`；缩略列不可排序；缺值一律排在最后（不论方向）；`title` 用 `localeCompare(…, "zh")`；同值按 `ts` 倒序稳定。默认 `ts desc`。

## 2. 工具栏与状态记忆

- [L-10] 工具栏一行：左侧类型筛选分段控件（全部 / 图片 / 视频 / 音乐，复用 `widgets/segment_switch.js`，它按 `labels` 数组生成任意项数，只需改掉文件头「两项」的注释）；右侧视图切换三个图标按钮（缩略图 / 列表 / 明细，`aria-pressed`、`aria-label`），缩略图视图时出现大小滑块，最右「刷新」。
- [L-11] 视图、筛选、缩略图大小、明细排序记在 `localStorage` 键 `lmd.library`（JSON）；读写都包 try/catch，读不到用默认值（缩略图、全部、200px、`ts desc`）；值非法时回落默认。缩略图大小滑块是普通 `input[type=range]`，方向键只调大小，不移动选中（L-31 只在条目区内生效）。
- [L-12] 筛选后为空：显示「没有这类成品」并写明当前筛选（例：「当前筛选：视频」）；整体为空沿用现有引导语。

## 3. 三种视图

- [L-20] 缩略图：自适应网格 `repeat(auto-fill, minmax(var(--lib-thumb), 1fr))`，滑块调 `--lib-thumb` 140–320px。卡片：方形媒体区 + 提示词两行截断 + 时间一行。
- [L-21] 图片卡片：`<img loading="lazy">`，`object-fit: cover`。
- [L-22] 视频卡片：进入视口（IntersectionObserver；环境没有时直接加载）才设 `src=<url>#t=0.1`、`preload="metadata"`、`muted`、`playsinline`；角标显示时长。鼠标悬停静音播放，移开暂停并回到 0.1 秒；同一时刻最多一个卡片在悬停播放。
- [L-23] 音乐卡片：渐变底 + 音乐图标 + 时长。`file` 类（不认识的文件）：文件图标 + 文件名。
- [L-24] 音乐卡片右上角小播放按钮就地试听（右下角是时长角标）：页面只有一个隐藏的 `<audio>`；按钮 `aria-pressed` 与图标（播放/暂停）反映状态，再点暂停；开别的试听、打开预览、点「刷新」重画、离开素材库页时都停掉并复位按钮；点按钮不触发选中/打开。
- [L-25] 失败/取消（无成品）：灰卡 + 警示图标 + 状态字；`missing`：灰卡 + 「文件已不在」。
- [L-26] 媒体加载失败（img/video `error`）：该卡片退回类型图标占位，不影响其他卡片。
- [L-27] 列表：每行 48px 缩略图（规则同 L-21/L-22，但视频不悬停播放）+ 提示词 + 元信息行（类型 · 状态 · 时间 · 耗时 · 规格）+ 右侧动作（预览、在访达中显示、回填参数）；失败记录照旧显示错误块（F3）。
- [L-28] 明细：`<table>`，列：缩略（32px）、提示词、类型、生成时间、时长、画幅、大小、耗时。除缩略列外表头是按钮，点击按该列排序，再点反向，`aria-sort` 标当前列；缺值显示「—」。

## 4. 选中与键盘

- [L-30] 每个条目的主体是一个 `<button data-lib-item>`（缩略图视图是整张卡片的媒体+文字区，列表是缩略图+文字区，明细是提示词单元格），`aria-label` 为标题；动作按钮（试听、预览、在访达中显示、回填）是它的兄弟节点，不嵌套在里面（避免交互元素嵌套）。单击主体 = 选中（`aria-current="true"` + 选中样式）；双击主体，或焦点在主体上按 Enter/空格 = 打开预览（`preventDefault`，不再额外触发选中之外的点击）。
- [L-31] roving tabindex：所有主体里只有选中项（没有选中时是第一项）`tabIndex=0`，其余 `-1`；方向键只在焦点位于某个主体上时处理，移动时同时移动选中与焦点并滚入视野（`block: "nearest"`）。缩略图视图 ←/→ 前后一个，↑/↓ 跳一行：列数 = 与第一项 `offsetTop` 相同的前导项个数，量不到（0）时 ↑/↓ 退化为 ←/→；列表/明细 ↑/↓ 前后一个。到头停住，不循环。
- [L-32] 切换筛选、排序、刷新后：原选中项仍在就保持，否则清空选中。
- [L-33] 动作按钮（预览、在访达中显示、回填、试听）点击与按键都不冒泡为选中/打开；各自行为同现状（reveal 失败把服务端文案写进错误行，issue #12）。

## 5. 预览弹层（widgets/library_preview.js）

- [L-40] 复用遮罩 + `role=dialog` + `aria-modal` + Esc/点遮罩关闭的骨架；打开时焦点进弹层，关闭后焦点与选中回到最后预览的条目。
- [L-41] 主区：图片按窗口适配；视频 `controls autoplay`（有声）；音乐大卡片 + `<audio controls autoplay>`；失败显示错误块；`missing` 显示「文件已不在」；`file` 类显示「无法预览这种文件」，信息区照常。
- [L-42] 信息区（宽屏在右，窄于 900px 在下）：完整提示词、全部参数、生成时间、耗时、文件名与大小；按钮「回填参数」（有 fillPlan 时；调用 `ctx.applyFill(plan)` 并关闭弹层）、「在访达中显示」（有文件时）、「关闭」。
- [L-43] ←/→ 在当前筛选+排序顺序里切上一件/下一件（到头不循环，按钮置灰）；Esc 关闭；空格仅在焦点不在媒体控件、按钮或输入框上时关闭（否则交给该控件，如视频暂停）。切换或关闭时停止并释放上一件媒体（`pause()` + 移除 `src`）。弹层打开期间遮罩挡住页面，素材库不会被刷新，弹层按打开时的条目快照翻页。
- [L-44] 动效：遮罩淡入、面板淡入+轻微缩放（180ms 左右）；全局 `prefers-reduced-motion` 规则生效。
- [L-45] 离开素材库页（`main.js` 的 `showTab` 切到别的页）时调用 `panes.library.onHide()`：停掉试听（L-24）与悬停播放（L-22）。现状顶部播放区切页后仍在后台出声，本条一并修掉。

## 6. 文件与测试

- 新增 `desk/static/js/pure/library_view.js`（L-01–L-06）、`desk/static/js/widgets/library_preview.js`（L-40–L-44）；重写 `desk/static/js/panes/library.js`（工具栏、三视图、选中、键盘）；`index.html` 素材库 section 改结构；`app.css` 新增素材库一节；`icons.js` 按需补图标（grid、list、table、music）。
- [L-50] `node --test`：纯函数（合并含 B-43、missing、筛选、排序缺值在后）；假 DOM：视图切换与记忆（含存储抛错）、单击选中/双击打开、键盘移动、预览 ←/→ 与到头置灰、回填调用 applyFill 并关闭、reveal 失败文案、试听按钮不冒泡。现有 `library_pane.test.js` 中依赖顶部播放区的断言改为断言预览弹层。
- [L-51] e2e（Playwright）：三视图渲染、预览打开/切换/关闭、键盘导航、回填回到对应页面（沿用 `test_library_panel.py` 的回填用例）、切页停声（L-45）；在 1280 与 900 宽截图目检，截图目录由 `$LMD_LIBRARY_SHOTS` 指定。
- [L-52] 迁移依赖 `[data-lib-player]` 的现有 e2e：`test_image_sessions.py`（约 329–355 行，含「预览与刷新按钮的间距」断言，改为断言弹层里图片的尺寸）、`test_image_flow.py`（约 466 行）；（`test_library_panel.py::test_audio_player_matches_the_dark_palette` 只查音乐会话卡片的播放器，不受影响）；`test_outputs_range.py` 只等 `[data-lib-list] li`，改为等 `[data-lib-item]`。
- [L-53] WebKit 核对：应用外壳是 WKWebView，而 e2e 默认跑 Chromium。视频首帧缩略图（`#t=0.1` + `preload="metadata"`）与悬停播放须另用 Playwright WebKit（本机已装 webkit-2272）跑一条用例确认能出首帧；不行则退回「视频图标 + 时长」占位并在本文件记下。
- 完成标准：JS、Python、e2e 全绿；L-53 通过；截图目检三视图与弹层（台面只有深色一套配色）。

## 7. 闭环自审（2026-09-30）

逐条追「用户动作 → 规则 → 代码现状 → 结果」，改了以下问题：

1. 条目主体若做成 `role=option` 再内嵌动作按钮，是交互元素嵌套（读屏与键盘都乱）→ 改为主体按钮 + 兄弟动作按钮（L-30）。
2. 键盘范围未限定：滑块的方向键会被抢 → 只在焦点位于条目主体时处理（L-11、L-31）；↑/↓ 的「列数」在假 DOM/窄窗下量不到 → 规定量法与退化（L-31）。
3. 预览里空格关闭与视频控件的空格暂停冲突 → 焦点在控件上时空格交给控件（L-43）。
4. `key` 用「ts+kind」可能重复且没说跨刷新稳定，L-32 保持选中依赖它 → 重定 key（L-02）。
5. 试听与切页：`showTab` 没有离开钩子，现状顶部播放器切页后仍出声 → 新增 L-45；试听遇刷新重画会被销毁 → 明确「刷新即停」（L-24）。
6. 漏了 `file` 类的卡片与预览表现 → L-23 补上（预览同 L-41 的「无法预览」路径：只显示信息与「在访达中显示」）。
7. 现有 e2e 有 3 个文件依赖 `[data-lib-player]`，原文只提了 JS 测试 → L-52。
8. e2e 只跑 Chromium，而视频首帧取法在 WebKit 上有已知差异，外壳恰是 WKWebView → L-53。
9. 完成标准写了「亮/暗两种主题」，但 `app.css` 没有浅色主题 → 改为只核对深色。

