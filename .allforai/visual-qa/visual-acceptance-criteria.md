# 图片会话 · 视觉验收标准

来源设计：`docs/superpowers/specs/2026-09-24-image-sessions-design.md`；需求 `image-sessions` rev 1。机器可读版：`visual-acceptance-criteria.json`（status: passed）；截图清单：`visual-evidence-requirements.json`。

每个状态都在两个视口截图：1280×800（wide）与 900×700（narrow）。

## 全局规则（每张截图都适用）

必须出现：
- 左侧会话列表（「新会话」主按钮在最上）
- 右侧时间线与底部输入区（提示词输入框 + 「生成图片」主按钮 + 折叠的「高级参数」）
- 当前会话在列表中高亮（aria-current=true）

不得出现：
- 主流程可见文字中出现「种子」一词（唯一例外：展开的「高级参数」折叠区内的标签与数值；本规则只适用于图片页，「素材库」页条目元数据中的「种子 N」按用户 2026-09-24 决定豁免，见设计 D-50a）
- 空白图片框：任何 <img> 的 naturalWidth 为 0、破图标，或没有图片的灰色/空占位框
- 页面横向滚动条（document.scrollingElement.scrollWidth > clientWidth）
- 按钮或会话标题文字被裁切（按钮 scrollWidth > clientWidth；省略号只允许出现在会话标题与提示词摘要）
- 元素互相遮挡（会话列表、时间线、输入区、弹层之外的任意两块可见区域重叠）
- 视频页或音乐页的元素出现在图片页

## 各状态

### `first-entry-auto-session` — 首次进入：无任何会话时自动新建的空会话

- 设计落点：D-62、D-80、D-10；需求：BR-4、AC-7
- 前置数据：空数据目录（image-sessions/ 不存在）；图片模型与运行环境可用
- 操作：打开 #tab=image
- 必须出现：
  - 会话列表恰有一项「新会话」且高亮
  - 时间线居中两行：「还没有图片」与「在下面写下想要的画面，点「生成图片」…」
  - 「生成图片」按钮可用
  - 「高级参数」处于折叠状态
- 不得出现：
  - 「请先新建会话」一类提示
  - 进度条
  - 任何图片框或缩略图占位
  - 「种子」一词
- 截图：`evidence/first-entry-auto-session-wide.png`、`evidence/first-entry-auto-session-narrow.png`

### `empty-session` — 会话内无尝试（手动新建后）

- 设计落点：D-60、D-80；需求：BR-4、AC-4、AC-7
- 前置数据：已有一个含 1 次完成尝试的会话；点「新会话」
- 操作：点「新会话」
- 必须出现：
  - 新会话排在列表最上并高亮
  - 空会话提示两行
  - 焦点在提示词输入框
- 不得出现：
  - 上一个会话的尝试卡片
  - 图片框
  - 「种子」一词
- 截图：`evidence/empty-session-wide.png`、`evidence/empty-session-narrow.png`

### `running` — 生成中（当前会话）

- 设计落点：D-81、D-82、D-83、§7.6；需求：AC-7
- 前置数据：测试外壳的脚本化媒体执行器让作业停在运行中并输出步数进度
- 操作：输入提示词，点「生成图片」
- 必须出现：
  - 时间线末尾一张展开的卡片：「第 N 次 · 生成中…（已用 …）」
  - 进度条
  - 「取消」按钮
  - 折叠的「日志」
  - 会话列表该项有「生成中」标记
  - 「生成图片」禁用，状态行「正在生成这个会话里的第 N 次」
- 不得出现：
  - running 卡片里的图片框或空白占位
  - running 卡片上的「在这张基础上改」「换个构图」按钮
  - 「种子」一词
- 截图：`evidence/running-wide.png`、`evidence/running-narrow.png`

### `running-other-session` — 别的会话在生成时查看另一会话

- 设计落点：D-77、D-87、§7.6；需求：AC-4、AC-7
- 前置数据：会话 A 有运行中作业；会话 B 至少 1 次完成尝试
- 操作：点会话 B
- 必须出现：
  - 会话 A 在列表中带「生成中」标记
  - 会话 B 高亮，时间线是 B 的尝试
  - 状态行「「<A 的标题>」正在生成图片」与行内按钮「回到该会话」
  - 「生成图片」与「换个构图」禁用，「在这张基础上改」可用
- 不得出现：
  - A 的 running 卡片出现在 B 的时间线
  - 只写「媒体作业进行中」而不说明是哪个会话
  - 「种子」一词
- 截图：`evidence/running-other-session-wide.png`、`evidence/running-other-session-narrow.png`

### `timeline-three-rounds` — 三轮「生成 → 在这张基础上改 → 再生成」后的时间线

- 设计落点：D-40、D-44、D-71、D-72、D-73、D-74；需求：AC-1、AC-2、BR-3、BR-8、AC-7
- 前置数据：同一会话里按验收步骤连续完成三次生成（脚本化执行器每次产出一张真实 PNG）
- 操作：生成 → 在第 1 次上点「在这张基础上改」，改提示词，生成 → 在第 2 次上点「在这张基础上改」，改提示词，生成
- 必须出现：
  - 时间线从上到下「第 1 次」「第 2 次」「第 3 次」
  - 折叠的第 1、2 次卡片显示真实缩略图；展开的第 3 次以大图代替缩略图（设计 §7.1 草图，2026-09-24 修复 B-01），大图渲染高度 ≥ min(192px, 60vh)
  - 折叠卡片有提示词摘要与「宽×高 · N 步」；展开卡片以完整提示词代替摘要
  - 最后一次（第 3 次）展开：大图、完整提示词、折叠的「高级参数」、「在这张基础上改」「换个构图」两个按钮
  - 会话标题是第 1 次的提示词（≤24 字 + …）
- 不得出现：
  - 任何一张空白或破图
  - 尝试顺序颠倒或缺失
  - 折叠卡片上出现「种子」
  - 按钮文字被裁切
- 截图：`evidence/timeline-three-rounds-wide.png`、`evidence/timeline-three-rounds-narrow.png`

### `attempt-selected-actions` — 选中一张较早的尝试（展开 + 两个动作）

- 设计落点：D-72、D-74、D-86；需求：BR-6、AC-7
- 前置数据：会话里有 ≥2 次完成尝试
- 操作：点第 1 次的卡片
- 必须出现：
  - 第 1 次展开（aria-expanded=true），其他卡片折叠
  - 大图完整显示（不超过 60vh、不被裁切）
  - 「在这张基础上改」「换个构图」两个次级按钮并排或换行完整可见
- 不得出现：
  - 两个动作按钮被遮挡或裁切
  - 同时展开两张卡片
  - 展开区外出现「种子」
- 截图：`evidence/attempt-selected-actions-wide.png`、`evidence/attempt-selected-actions-narrow.png`

### `refine-prefill` — 点「在这张基础上改」之后的输入区

- 设计落点：D-40、D-41、D-42、D-43；需求：BR-6、BR-7、AC-7
- 前置数据：会话里有 ≥2 次完成尝试；「高级参数」折叠
- 操作：在第 2 次上点「在这张基础上改」
- 必须出现：
  - 提示词输入框内容等于第 2 次的提示词且获得焦点
  - 输入框上方提示条「沿用第 2 次的构图」及 × 按钮
  - 「高级参数」仍折叠
  - 尚未产生新的尝试卡片
- 不得出现：
  - 自动提交产生的 running 卡片
  - 提示条或按钮里出现「种子」
  - 「高级参数」被自动展开
- 截图：`evidence/refine-prefill-wide.png`、`evidence/refine-prefill-narrow.png`

### `attempt-failed` — 失败的尝试

- 设计落点：D-08、D-09、D-84、D-85、D-86；需求：AC-6、BR-3、AC-7
- 前置数据：脚本化执行器让作业非零退出（exit_nonzero，带日志尾部）
- 操作：生成并等待作业结束
- 必须出现：
  - 卡片带「失败」标记与原因标题（describeJobError 的人话，如「生成程序异常退出」）
  - 缩略图位置是危险色图标块
  - 展开后「详情」折叠里有 code: message 与日志尾部
  - 两个动作按钮
- 不得出现：
  - 空白图片框或破图
  - 只写「失败」而没有原因
  - 「种子」一词（高级参数折叠时）
- 截图：`evidence/attempt-failed-wide.png`、`evidence/attempt-failed-narrow.png`

### `attempt-cancelled` — 已取消的尝试

- 设计落点：D-09、D-24、D-84、D-85；需求：AC-6、AC-7
- 前置数据：脚本化执行器保持运行，用户点 running 卡片上的「取消」
- 操作：生成 → 点「取消」 → 等待落定
- 必须出现：
  - 卡片带「已取消」标记与说明
  - 缩略图位置是灰色图标块
  - 两个动作按钮
- 不得出现：
  - 空白图片框
  - 卡片停留在「生成中」
  - 「种子」一词
- 截图：`evidence/attempt-cancelled-wide.png`、`evidence/attempt-cancelled-narrow.png`

### `attempt-interrupted` — 应用中途关闭后重启看到的尝试

- 设计落点：D-25、D-85；需求：AC-3、AC-6、AC-7
- 前置数据：会话文件里预置一个 status=running 的尝试，然后启动外壳（触发 recover_running）
- 操作：打开 #tab=image
- 必须出现：
  - 该尝试显示「应用在生成途中关闭，这次没有完成」
  - 失败样式图标块
- 不得出现：
  - 卡片显示为「生成中」
  - 进度条
  - 空白图片框
- 截图：`evidence/attempt-interrupted-wide.png`、`evidence/attempt-interrupted-narrow.png`

### `attempt-file-missing` — 图片文件已不在

- 设计落点：D-85、§2 get.output_missing；需求：AC-6、AC-7
- 前置数据：一次完成尝试后，从 outputs_root 删除其 PNG 文件
- 操作：刷新图片页
- 必须出现：
  - 卡片显示「图片文件已不在」与「可能已在访达中移动或删除」
  - 灰色图片图标块
  - 两个动作按钮仍可用
- 不得出现：
  - 浏览器破图标
  - 空白图片框
- 截图：`evidence/attempt-file-missing-wide.png`、`evidence/attempt-file-missing-narrow.png`

### `model-missing` — 图片模型缺失

- 设计落点：§7.6；需求：AC-7
- 前置数据：资源目录里没有 qwen-image 模型
- 操作：打开 #tab=image
- 必须出现：
  - 头部模型状态与状态行「尚未安装图片模型，请到「资源」页下载」
  - 「生成图片」禁用
- 不得出现：
  - 「生成图片」可点
  - 「种子」一词
- 截图：`evidence/model-missing-wide.png`、`evidence/model-missing-narrow.png`

### `runtime-unavailable` — 图片运行环境不可用

- 设计落点：§7.6；需求：AC-7
- 前置数据：capabilities.image_runtime.present=false
- 操作：打开 #tab=image
- 必须出现：
  - 状态行为运行环境原因（capability.detail 或「图片 MLX 运行环境不可用，请检查服务或应用安装」）
  - 「生成图片」禁用
- 不得出现：
  - 「生成图片」可点
- 截图：`evidence/runtime-unavailable-wide.png`、`evidence/runtime-unavailable-narrow.png`

### `busy-other-media` — 视频或音乐作业占用

- 设计落点：§7.6；需求：AC-7
- 前置数据：图片页当前会话有 ≥1 次完成尝试（已展开）；脚本化执行器让一个视频作业运行中
- 操作：切到图片页
- 必须出现：
  - 状态行为现有媒体忙碌原因（如「媒体作业进行中」）
  - 「生成图片」与「换个构图」禁用
- 不得出现：
  - 「回到该会话」按钮（占用者不是图片会话）
  - 「种子」一词
- 截图：`evidence/busy-other-media-wide.png`、`evidence/busy-other-media-narrow.png`

### `rename` — 重命名会话

- 设计落点：D-89、D-12；需求：BR-5、AC-7
- 前置数据：至少 1 个会话
- 操作：点会话项的铅笔图标
- 必须出现：
  - 该会话项变为输入框，内容为当前标题并获得焦点
  - 其他会话项不变
- 不得出现：
  - 输入框溢出左栏或被裁切
- 截图：`evidence/rename-wide.png`、`evidence/rename-narrow.png`

### `delete-confirm` — 删除会话确认框

- 设计落点：D-90、D-30；需求：BR-5、AC-5、AC-7
- 前置数据：一个含完成尝试的会话
- 操作：点会话项的垃圾桶图标
- 必须出现：
  - 弹层标题「删除会话」
  - 正文「确定删除「<标题>」？只删除这个会话分组，其中的图片仍保留在素材库。」
  - 「取消」获得焦点，「删除」为危险样式
- 不得出现：
  - 「该会话的全部消息将被删除」一类聊天页文案
  - 暗示图片会被删除的文案
- 截图：`evidence/delete-confirm-wide.png`、`evidence/delete-confirm-narrow.png`

### `delete-confirm-running` — 删除正在生成的会话的确认框

- 设计落点：D-90、D-31；需求：BR-5、AC-5、AC-7
- 前置数据：会话有运行中作业
- 操作：点该会话的垃圾桶图标
- 必须出现：
  - 基础正文 + 追加句「这个会话正在生成图片，生成会继续完成，图片会进入素材库，但不会再出现在任何会话里。」
- 不得出现：
  - 缺少追加句
- 截图：`evidence/delete-confirm-running-wide.png`、`evidence/delete-confirm-running-narrow.png`

### `library-after-delete` — 删除会话后素材库仍可打开其图片

- 设计落点：D-30；需求：AC-5
- 前置数据：删除一个含完成尝试的会话
- 操作：确认删除 → 切到素材库 → 预览该图片
- 必须出现：
  - 图片页会话列表里已无该会话
  - 素材库列出该图片并能预览出真实图片
- 不得出现：
  - 素材库里该图片缺失或破图
- 截图：`evidence/library-after-delete-wide.png`、`evidence/library-after-delete-narrow.png`

### `session-list-load-failed` — 会话列表读取失败

- 设计落点：§7.2；需求：AC-7
- 前置数据：Playwright page.route 让 GET /api/image-sessions 返回 500（需在证据里声明为 mock layer）
- 操作：打开 #tab=image
- 必须出现：
  - 列表位置「会话列表读不出来：<原因>」与「重试」按钮
  - 「生成图片」禁用，状态行「会话还没加载好」
- 不得出现：
  - 空白的会话列表而无任何说明
  - 「种子」一词
- 截图：`evidence/session-list-load-failed-wide.png`、`evidence/session-list-load-failed-narrow.png`

### `corrupt-session` — 会话文件损坏

- 设计落点：§7.2；需求：AC-7
- 前置数据：image-sessions/ 下预置一个内容不是 JSON 的 <32hex>.json，另有一个正常会话
- 操作：点「无法读取的会话」项
- 必须出现：
  - 列表项标题「无法读取的会话」、元信息「文件已损坏」、只有删除按钮
  - 时间线说明「这个会话文件已损坏，无法显示。可以删除它，素材库里的图片不受影响。」
  - 「生成图片」禁用，原因「请选择其他会话或新建一个」
- 不得出现：
  - 未捕获异常导致的空白页
  - 改名按钮
- 截图：`evidence/corrupt-session-wide.png`、`evidence/corrupt-session-narrow.png`
