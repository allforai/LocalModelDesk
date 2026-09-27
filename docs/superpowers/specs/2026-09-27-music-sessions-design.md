# 模块设计：音乐会话（music-sessions）

**日期** 2026-09-27
**来源** 用户 2026-09-25/27 对话确认（全部按推荐）：音乐页改成会话式；「接着写下一段」预填由用户写；时间线平铺（同图片页）；输入区在底部、歌词框可伸缩；续写段的「改 / 换版本」仍接在原位置；手动合成用「挑选合成」模式；前端抽共用会话控制器（方案 1）。
**上游** `2026-09-25-media-sessions-base-design.md`（下称 B-xx，后端已合并 6d1f79c）、`2026-09-24-image-sessions-design.md`（下称 IS D-xx）。
**下游** 第 3 块视频会话复用本文的共用控制器。

每条 **[M-xx]** 可写成测试断言。本文未写到的用户可见行为不归实现者发明。

---

## 0. 范围与非目标

**范围**
- 前端共用会话控制器 `panes/media_session.js`（承接 B-70–B-72），图片页改用它，行为不变。
- 音乐页改成会话式：会话列表、时间线、底部输入区、三个动作、成片播放、重新拼接、挑选合成。
- 后端：音乐生成 `session_id` 必填（B §3.2 约定的「第 2 块改为必填」）。
- 素材库回填音乐条目回到原会话。

**非目标**
- [M-00a] 视频页不改（第 3 块）。
- [M-00b] 不做真正的音频续写（运行库不支持，见 B §0.3）。
- [M-00c] 不改 `AI 帮写`（prompt_assist）的行为，只把它挂在新输入区里。
- [M-00d] 单次尝试不能删除（沿用 IS D-00c）。
- 台面未发布，不谈兼容或迁移。

---

## 1. 共用会话控制器

### 1.1 文件

```
desk/static/js/panes/media_session.js   createSessionPane —— 会话页的全部通用流程
desk/static/js/pure/media_session.js    通用纯逻辑（由 pure/image_session.js 移出并参数化）
desk/static/js/widgets/session_list.js  会话列表项（由 widgets/image_session_list.js 改名）
desk/static/js/panes/image.js           只剩图片专属：输入区、提示条、底稿、卡片、大图自适应
desk/static/js/pure/image_session.js    只剩图片专属纯逻辑（底稿强度、提示条、readImageParams、recomposeParams…）
desk/static/js/panes/music.js           音乐页：输入区、提示条、卡片、动作
desk/static/js/pure/music_session.js    音乐纯逻辑
desk/static/js/widgets/music_session_card.js  音乐卡片
```

### 1.2 接口

```js
createSessionPane(root, {
  kind,                 // "image" | "music"
  noun,                 // "图片" | "歌曲"（忙碌原因、删除确认等文案）
  emptyLines,           // [标题, 说明]，空会话时显示
  dataPrefix,           // "image" | "music"：DOM 查询前缀 data-<prefix>-timeline 等
  renderCard(doc, {attempt, index, attempts, selected, running, job, broken, picking, pickOrder}) → {node, running?, image?},
  composer: {
    read() → params,            // 抛 ParamsError（advanced 标志决定错误显示位置）
    prefill(fields, chip),      // 回填输入区并显示提示条；不提交
    afterStart(),               // 生成成功启动后的输入区收尾（图片：清种子隐藏提示条；音乐：见 M-24）
    onSessionSwitch(),          // 切换会话时清除提示条等（IS D-64）
    focus(),
  },
  startJob(params) → Promise<job>,   // api.startImageJob / api.startMusicJob
  canCompose: bool,                  // 音乐 true，图片 false
  confirm, randomSeed,               // 测试注入
}) → { refresh, applyJob, poll, applyFill, setHeavyAllowed, setModelStatus, setRuntimeStatus,
       startGeneration(params, {fromInputs}), currentId(), currentSession(), selectAttempt(id), settleView }
```

- [M-01] 控制器承担 IS §6–§7 与 §3.7 中与媒体种类无关的全部行为：会话列表四种状态（IS §7.2）、自动新建首个会话（IS D-62）、当前会话恢复（IS D-63）、切换（IS D-64，经 `composer.onSessionSwitch`）、时间线骨架与选中展开（IS D-71、D-72）、running 卡片进度与日志（IS D-81、D-82）、落定后重取（IS D-27）、改名删除（IS D-89、D-90）、忙碌原因（IS §7.6，名词取 `noun`）、「回到该会话」、内存确认重发（IS D-49）、`session_not_found` 自动切换（IS D-88）、滚动意图（贴底 / 对齐选中 / 用户滚动后不拽）与 ResizeObserver。
- [M-02] 图片页专属的「展开卡片大图自适应」（IS D-74 的 `fitExpandedImage`）经 `renderCard` 返回的 `image` 节点接入：控制器只在 `image` 存在时调用页面提供的适配（由 `image.js` 以回调形式传入 `fitExpanded(node, image)`），音乐页不传。
- [M-03] 纯逻辑参数化：`availability(state, {noun})`、`deleteMessage(summary, {noun})`、`runningSessionId(job, sessions, kind)`；其余（`sessionTitle`、`sessionMeta`、`attemptLabel`、`orderSessions`、`pickCurrent`、`randomSeed`、`ParamsError`、`autoTitle`）原样迁移。图片页调用时 `noun="图片"`，产出的文案与迁移前逐字相同。
- [M-04] **图片页零回归**：`tests/js/image_pane.test.js` 与 `tests/e2e/test_image_sessions.py`、`tests/e2e/test_image_flow.py` 的断言不改（只允许改 import 路径与挂载方式），全部通过。

### 1.3 挑选合成模式（`canCompose: true` 时）

- [M-05] 时间线上方工具行出现次级按钮「挑几段合成…」（`data-<prefix>-compose-start`）。会话没有 ≥2 个 `done` 且文件在的尝试时按钮 `disabled`，`title`「至少要有两段完成的才能合成」。
- [M-06] 进入模式：每张 `done` 且文件在的卡片左侧出现勾选框（`aria-label="选中第 N 次"`）；其余卡片不可选、不变灰。卡片点击在此模式下切换勾选而非展开。
- [M-07] 勾选顺序即拼接顺序，已选卡片显示序号徽标 ①②③…；取消勾选后其后序号前移。
- [M-08] 底部输入区替换为合成栏：按顺序列出已选段（「第 N 次 · 时长」），每项「上移」「下移」「移除」（图标按钮，`aria-label` 同名）；右侧主按钮「合成（K 段）」，次级按钮「取消」。K<2 时主按钮 `disabled`，原因行「至少选两段」。有作业在跑或服务不可用时 `disabled`，原因同 IS §7.6 第一条可用原因。
- [M-09] 点「合成」：`POST /api/media/compose {kind, session_id, parts}`；成功启动 → 退出挑选模式、恢复输入区、新 compose 尝试追加并选中（running 卡片）；失败 → 留在模式内，错误显示在合成栏错误行（`describeJobError` 标题，`capability_missing` 显示后端原话「需要 ffmpeg 才能拼接成片」）。
- [M-10] 「取消」、切换会话、新建会话都退出挑选模式并清空已选。
- [M-11] 界面不允许同一段选两次（勾选框语义）。B-44 后端允许重复，界面不提供。

---

## 2. 音乐页

### 2.1 布局（`#pane-music`，与 `#pane-image` 同构）

```
┌──────────────┬──────────────────────────────────────────────────────┐
│ [+ 新会话]    │ 生成歌曲 · <模型状态> · [模型说明 ▸]      [挑几段合成…] │
│ 会话列表      │ 时间线（卡片，旧在上新在下）                            │
│              │ ┌ 接在第 2 次后面 × ┐                                   │
│              │ [风格描述________________________________]              │
│              │ [歌词（4 行，聚焦/内容多时长高，最多 50vh）] [生成歌曲]   │
│              │ AI 帮写 · ▸ 高级参数（时长、种子）                       │
│              │ 状态提示 · 错误                                         │
└──────────────┴──────────────────────────────────────────────────────┘
```

- [M-20] 左栏、主区宽度、外边距、窄窗 900×700 规则同 IS D-70、D-78。原 `.form | .job` 两栏与 jobview 删除。
- [M-21] 输入区：提示条（M-26）；风格描述 `<input>`（`placeholder` 沿用「例如：温柔的民谣，木吉他伴奏，女声轻唱，慢速」，`aria-label="风格描述"`）；歌词 `<textarea>`（`placeholder="歌词（必填）"`，默认 4 行，聚焦或内容超出时增高，最高 `50vh`，失焦且内容不超 4 行时回落）；「AI 帮写」行（原 `data-music-assist`）；主按钮「生成歌曲」（sparkles 图标，⌘Enter 等同点击）；「高级参数」`<details>` 默认折叠，内含「时长（秒）」（10–300，默认 60，下方保留提示「成品时长由模型按歌词决定，常短于所填时长；素材库会标注实际时长。」）与「种子（留空则每次随机）」；状态行 `role=status`；错误行 `role=alert`。
- [M-22] 头部：「生成歌曲」、模型状态（沿用现有音乐模型状态文案来源）、「模型说明」折叠（MiniMax Music 3 · MLX 本机推理；需要歌词；成品为 WAV）。
- [M-23] 空会话：「还没有歌曲」／「在下面写风格描述和歌词，点「生成歌曲」。之后可以在任意一段上「在这段基础上改」「换个版本」或「接着写下一段」。」
- [M-24] 生成成功启动后：风格描述、歌词、时长保留；种子框清空；提示条若为「沿用第 N 次」则隐藏，若为「接在第 N 次后面」也隐藏（下一次生成回到普通生成，除非再点「接着写下一段」）。
- [M-25] 「种子」二字只出现在「高级参数」内（同 IS D-50）。

### 2.2 提示条

- [M-26] 两种，互斥：
  - 沿用：「沿用第 N 次」（由「在这段基础上改」产生）；显示条件同 IS D-42（种子框值 == 被引用尝试的 seed）；× 清空种子框并隐藏。
  - 续写：「接在第 N 次后面」（由「接着写下一段」产生）；不依赖种子框；× 隐藏并取消续写。
- [M-27] 提示条可见时点「生成歌曲」的请求：沿用 → 带被引用尝试的 `continues`（若它有，M-31）；续写 → `continues = 被续写尝试 id`。提示条不可见 → 不带 `continues`。
- [M-28] 若被引用 / 被续写的尝试已不再是 `done` 且文件在（`output_missing` 或会话刷新后找不到），提示条改为「第 N 次的文件已不在，不能接着写」并带 ×，「生成歌曲」`disabled`、原因同文案；点 × 回到普通生成。后端返回 `segment_missing` / `segment_not_found` 时同样处理。

### 2.3 卡片

- [M-30] 折叠：标题行「第 N 次 · HH:MM」＋（续写）「接第 M 次」／（合成）「合成：第 a、b、c 次」（引用的尝试不在列表中时显示「合成」）；风格描述摘要（一行省略，`title` 全文）；歌词首个非空、非 `[段落标记]` 行（一行省略）；状态标记（生成中 / 失败 / 已取消 / 文件已不在；完成不标）。
- [M-31] 展开：
  - 播放器 `<audio controls>`：有 `joined_output` 且 `joined_missing` 为假时默认播放成片，旁边分段切换「成片 | 只听这一段」（`role=radiogroup`）；否则只播 `output`，不显示切换。`<audio>` 报错时替换为「文件已不在」状态（同 IS D-85）。
  - 续写链说明：「由：第 1 次 → 第 3 次 → 第 5 次」（`chain` 由前端沿 `continues` 在当前会话 attempts 中回溯得到；遇到不在列表的前段则只显示可找到的部分并以「…」开头）。
  - 成片问题行（M-40）。
  - 完整风格描述、歌词（`<details>` 默认折叠，summary「歌词」）、「高级参数」折叠（时长、种子）。
  - 动作按钮（次级样式，从左到右）：「在这段基础上改」「换个版本」「接着写下一段」。compose 尝试只有「接着写下一段」（它没有可回填的参数）。
- [M-32] 失败 / 已取消 / 文件不在：不渲染 `<audio>`，图标块与原因同 IS D-84、D-85；动作按钮按 M-33–M-35 的可用性显示。

### 2.4 三个动作

- [M-33] **在这段基础上改**：回填风格描述、歌词、时长、种子；提示条「沿用第 N 次」；焦点到歌词框末尾；不提交；生成中可用（同 IS D-45）。失败 / 取消的尝试也可用（参数完整）。
- [M-34] **换个版本**：立即提交 `{session_id, caption, lyrics, duration, seed: 新随机数≠原值, continues: 原尝试的 continues}`；不改输入区。不可用条件同 IS D-48（生成中、提交中、模型缺失、运行环境不可用、其他作业占用）。
- [M-35] **接着写下一段**：风格描述、时长 ← 该尝试（compose 尝试：保留输入区当前值）；歌词清空；种子框清空；提示条「接在第 N 次后面」；焦点到歌词框；不提交。仅 `done` 且文件在的尝试显示为可用；否则 `disabled`，下方原因「这一段没有生成好，不能接着写」。
- [M-36] 回填不改变「高级参数」的折叠状态（同 IS D-43）。

### 2.5 成片问题与重新拼接

- [M-40] 尝试 `done` 且 `joined_error` 非空时，展开卡片在播放器下显示一行：「这一段生成好了，但成片没拼成：<原因>」，原因取 `joined_error.message`。
- [M-41] `joined_error.code ∈ {join_failed, join_cancelled, interrupted}` 时该行带次级按钮「重新拼接」：提交 `compose`，`parts` = 前端回溯出的链（M-31）各项 id，全部可找到且 `done`、文件在时才可用，否则按钮 `disabled`、原因「链上有一段已不在」。成功后新合成卡片追加并选中（B-75）。成片文件被删（`joined_missing`）同样显示问题行并按 M-41 提供重新拼接；问题行文案为「这一段生成好了，但成片文件已不在」。
- [M-42] `segment_missing` 不提供按钮，只显示原因。

### 2.6 后端与接通

- [M-50] `start_music_job` 的 `session_id` 改为必填：缺失 / 非字符串 → 400 `session_required`，不存在 → 404 `session_not_found`（同 IS D-18 文案）。`continues`、`refs` 规则不变。
- [M-51] `main.js`：`tickJob` 对 `kind == "music"`（含 compose 作业，`params.op == "compose"` 且 kind 为 music）调用 `panes.music.applyJob`；`showTab("music")` 调 `panes.music.refresh()`；`applyHeavyAvailability` 调 `panes.music.setHeavyAllowed`；删除对 `panes.music.jobView` 的所有调用。`kind == "video"` 仍走视频页 jobview。
- [M-52] 素材库回填：`applyFill` 对 `plan.pane == "music"` 调 `panes.music.applyFill(plan)`：有 `session_id`、`attempt_id` 且能找到 → 切到音乐页、打开会话、选中该尝试并执行「在这段基础上改」；否则停在当前会话按 M-33 回填字段，提示条文案「沿用素材库里这首」（同 IS D-94/95）。
- [M-53] 音乐模型状态与运行环境：`main.js` 以与图片页相同的方式接通（不新增后端）——资源页 `onModels` 回调里 `panes.music.setModelStatus(models?.find((m) => m.key === "music3"))`；能力探测处 `panes.music.setRuntimeStatus(capabilities?.music_runtime)`。文案：模型缺失「尚未安装音乐模型，请到「资源」页下载」，不完整「模型不完整，请到「资源」页继续下载或校验」，未知「暂时无法确认模型状态，请稍后重试」；运行环境不可用「音乐 MLX 运行环境不可用，请检查服务或应用安装」（`capability.detail` 优先）；就绪时头部显示「模型文件完整 · 可离线生成」。

---

## 3. 测试与完成标准

- 纯逻辑单测：`pure/media_session.js`（迁移后的通用函数，含 `noun` 参数化文案）；`pure/music_session.js`：`readMusicParams`（风格描述、歌词必填，时长 10–300 整数，种子范围与错误前缀「高级参数里的数值有误：」）、三个动作生成的请求（M-33–M-35，含续写段保留 `continues`、compose 尝试的「接着写下一段」）、卡片文案（M-30、M-31 链路回溯含缺段）、提示条显隐（M-26–M-28）。
- 控制器单测：用最小假页面跑与种类无关的流程（列表四态、自动新建、切换、轮询落定、删除当前会话后重选）；挑选合成模式（M-05–M-11）。
- 音乐页单测：仿 `image_pane.test.js` 的假 DOM/假 fetch 写法，覆盖 M-21–M-42 的关键路径。
- 图片页零回归：M-04。
- 后端：`tests/test_media_sessions_service.py` 增加音乐缺 `session_id` → 400；现有不带会话的音乐测试改为带会话。
- e2e：`tests/e2e/test_music_sessions.py`（测试外壳的假执行器：模型命令写 `TINY_WAV`，ffmpeg 命令按输出后缀写假文件——拼接在 e2e 中是假的，真拼接由 `tests/test_media_sessions_flow.py` 覆盖）：新会话 → 生成 → 接着写下一段 → 展开续写卡片出现「成片 | 只听这一段」→ 换个版本（新卡片「接第 1 次」）→ 挑几段合成（选两段、调换顺序、合成）→ 合成卡片出现；900×700 截图无横向滚动、按钮文字不截断；页面主流程 DOM 文本不含「种子」（高级参数折叠区除外）。
- 全量：`python3 -m pytest -q --ignore=tests/e2e`、`node --test tests/js/`、`python3 -m pytest tests/e2e -q`。

**完成标准**：M-04 图片零回归；音乐 e2e 走通；`grep -n "jobView" desk/static/js/main.js` 不再出现 `music`；音乐生成不带会话被拒。

---

## 4. 自审闭环

| 环 | 落点 |
|---|---|
| 续写的前段消失 → 用户有出路 | M-28（× 回到普通生成） |
| 成片没拼成 → 有出路 | M-41 重新拼接；M-42 说明原因 |
| 挑选合成模式的退出 | M-09 成功、M-10 取消/切换/新建 |
| 生成中切会话、删会话、退出应用 | M-01 继承 IS §3.8 |
| 音乐作业进度不再有展示方 | M-51 改走 `panes.music.applyJob` |
| 素材库回填音乐 | M-52 |
| 图片页不退化 | M-04 |

## 5. 待决问题

无。由本文决定并写明理由的细节：M-11 界面不允许重复选段（勾选语义清楚，重复需求罕见）；M-24 续写提示条生成后隐藏（避免下一次误接）；M-31 compose 尝试只提供「接着写下一段」（没有参数可回填）；M-53 音乐模型/运行环境状态复用前端已有数据源（`music3` 目录项、`music_runtime` 能力），不新增后端。
