# 完成度报告 — LocalModelDesk（macOS 外壳 + 本地 Python 服务 + 零依赖 Web UI）

需求基准：superstorm-registry · 共 2 面，盘问 1 面 · 实测 1 问 · 操作面 97 个，裁决触及 3 个

## 总览

实证完成：0 · 缺口：1 · 跑偏：0 · 无法自证：0

> 盘问官即交付作者（examiner_is_author）：bias-guard 生效——gap 从严，降级为 low 或 done 需额外独立证据。

> 本 run 取证类子 agent（实测官、枚举官）用 sonnet，用户于 2026-09-16 确认：「成本优先：取证类用 Sonnet 5」。裁决与普查仍用会话模型。
> 定靶时盘问官推荐的是选项 A（本轮取证要驱动真窗口改宽、读回、拍图，降档实测官更易残缺重派）。

取证时间：首问 2026-09-17T03:10:51+09:00 · 末问 2026-09-17T03:10:51+09:00 · 跨 0 分钟

## 规则一致性（规则 ↔ 规则；候选不计为产品缺陷）
历史台账未做规则对比；不追溯拒收原裁决。

## 需求覆盖（基准 92 条，有裁决 4 条，无裁决 88 条）
- R-ui-01 前端是静态文件（`index.html`、`app.css`、ES 模块），由服务端供给； — 缺口（修复之后，状态栏、聊天页、会话侧栏、视频页这四个面，在 900/940/1099/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-ui-02 聊天面板：模型选择、加载/卸载、流式回复、思考过程可展开、左侧会话列表（新建/切换/重命名/删除）。 — 缺口（修复之后，状态栏、聊天页、会话侧栏、视频页这四个面，在 900/940/1099/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-ui-03 视频面板：提示词、画幅、帧数、步数、进度、完成后就地播放。 — 缺口（修复之后，状态栏、聊天页、会话侧栏、视频页这四个面，在 900/940/1099/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-ui-07 常驻状态条：真实内存（不是写死的 128）、内存里是谁、媒体是否在跑、现在能不能开下一件重活。 — 缺口（修复之后，状态栏、聊天页、会话侧栏、视频页这四个面，在 900/940/1099/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-foundation-01 所有路径由本模块单点解析，区分「只读 bundle 资源根」与「可写用户数据根」； — 无裁决（未落任何面）
- R-foundation-02 配置持久化到 `<data root>/config.json`，字段至少含： — 无裁决（未落任何面）
- R-foundation-03 首运语义：无配置或 `first_run_done` 为假时，`api:readConfig` 必须能表达 needs-setup 状态； — 无裁决（未落任何面）
- R-foundation-04 收编既有权重：给定一个 legacy 根（如 `~/LocalModelDesk`）， — 无裁决（未落任何面）
- R-foundation-05 服务在 `mlx-h3`、内嵌 venv、模型目录任一缺失时仍能启动并提供状态接口； — 无裁决（未落任何面）
- R-foundation-06 配置写入原子：先写同目录临时文件再 `os.replace`；写到一半崩掉不得留下损坏的 `config.json`。 — 无裁决（未落任何面）
- R-resources-01 单一目录定义，供服务端、前端、以及任何 CLI 入口共同消费； — 无裁决（未落任何面）
- R-resources-02 完整度以 HF 仓库文件清单为准：取得每个期望文件的路径与字节数， — 无裁决（未落任何面）
- R-resources-03 每项报出 `present` | `partial` | `missing`；`partial` 必须带完成百分比 — 无裁决（未落任何面）
- R-resources-04 报出每项实际占盘字节数，以及 models 所在卷的剩余空间。 — 无裁决（未落任何面）
- R-resources-05 对某一目录项发起下载；中断后再次发起必须续传，已完整的文件不得重下。 — 无裁决（未落任何面）
- R-resources-06 取消/暂停进行中的下载；已下载的部分必须保持可续传状态，不得清空。 — 无裁决（未落任何面）
- R-resources-07 下载进行时可查询实时进度：已完成字节/总字节、当前文件、速率、预估剩余。 — 无裁决（未落任何面）
- R-resources-08 删除某一目录项的权重并回收磁盘，需要显式确认参数（无确认参数一律拒绝执行）。 — 无裁决（未落任何面）
- R-resources-09 同时至多一个下载在跑；`arbiter` 报告有重活（媒体生成）在跑时，下载必须拒绝启动并说明原因。 — 无裁决（未落任何面）
- R-arbiter-01 聊天 LLM、视频生成、音乐生成三者互斥；持有者唯一，任何时刻至多一个重活。 — 无裁决（未落任何面）
- R-arbiter-02 真实内存快照：总量、已用、可用、内存压力，取自操作系统（macOS 上 `vm_stat` / `sysctl`）， — 无裁决（未落任何面）
- R-arbiter-03 按端口收割 LLM：找出监听 LLM 端口的**任何**进程并终止（先 TERM 后 KILL）， — 无裁决（未落任何面）
- R-arbiter-04 媒体作业进行中拒绝加载 LLM；已有媒体作业时拒绝启动第二个媒体作业。拒绝必须带机器可读原因。 — 无裁决（未落任何面）
- R-arbiter-05 启动媒体作业前自动让出内存（卸掉 LLM）；让出失败必须导致启动失败，不得带着 LLM 硬上。 — 无裁决（未落任何面）
- R-arbiter-06 暴露单一台面状态对象：内存里是谁、媒体是否在跑、现在能不能开下一件重活， — 无裁决（未落任何面）
- R-arbiter-07 加载某模型前比对其体积与当前可用内存，装不下要在加载前给出警告（不是加载失败后才说）。 — 无裁决（未落任何面）
- R-llm-01 按目录 key 加载聊天模型：先向 `arbiter` 申请许可，再启动 mlx-lm 服务， — 无裁决（未落任何面）
- R-llm-02 卸载当前模型，并确认 LLM 端口确已释放（走 `api:reapLlmPort`，不只是终止自己的子进程）。 — 无裁决（未落任何面）
- R-llm-03 流式对话：逐 token 输出正文增量，并把思考/推理增量（`reasoning_content` / `reasoning`） — 无裁决（未落任何面）
- R-llm-04 加载失败必须给出原因（mlx-lm 日志尾部），不得只报一个「加载超时」。 — 无裁决（未落任何面）
- R-llm-05 报出当前加载的是哪个模型及其元数据（视觉能力、量化、参数量、体积）。 — 无裁决（未落任何面）
- R-llm-06 媒体作业进行中、或当前没有加载模型时，聊天请求被拒绝并带明确原因，不得挂起等待。 — 无裁决（未落任何面）
- R-llm-07 对话必须经由本服务转发；前端与外部客户端都不直连 mlx-lm 端口。 — 无裁决（未落任何面）
- R-gateway-01 `GET /v1/models`：OpenAI 格式，列出当前可服务的模型。没有模型驻留时返回空列表而非报错。 — 无裁决（未落任何面）
- R-gateway-02 `POST /v1/chat/completions` 非流式：OpenAI 请求与响应形状，含 `usage`、`finish_reason`。 — 无裁决（未落任何面）
- R-gateway-03 同端点流式：SSE，`data:` 分块与 OpenAI 增量格式一致，以 `data: [DONE]` 结束。 — 无裁决（未落任何面）
- R-gateway-04 `POST /v1/messages` 非流式：Anthropic 请求形状（`model`/`max_tokens`/`messages`/`system`） — 无裁决（未落任何面）
- R-gateway-05 同端点流式：发出 `message_start`、`content_block_start`、`content_block_delta`、 — 无裁决（未落任何面）
- R-gateway-06 Anthropic 的 `system`（字符串或块数组）、多轮 `messages`、`stop_reason` — 无裁决（未落任何面）
- R-gateway-07 绑定 `0.0.0.0` 于配置端口，使同网络其他设备可达；开关关闭时不监听。 — 无裁决（未落任何面）
- R-gateway-08 无模型驻留或媒体作业进行中：返回 `503`，带 `Retry-After` 头与机器可读原因码。 — 无裁决（未落任何面）
- R-gateway-09 错误按各自方言的原生错误信封返回（OpenAI 的 `{"error":{...}}`； — 无裁决（未落任何面）
- R-gateway-10 请求里的 `model` 既接受目录 key，也接受当前加载模型的标识符； — 无裁决（未落任何面）
- R-media-01 启动文生视频作业：提示词、画幅（宽高）、帧数、步数。H3 命令行的构造只存在一处。 — 无裁决（未落任何面）
- R-media-02 启动文生歌曲作业：风格描述、歌词、时长。Music 3 调用的构造只存在一处。 — 无裁决（未落任何面）
- R-media-03 作业运行中可流式读取进度/日志输出。 — 无裁决（未落任何面）
- R-media-04 作业产出落在 outputs 根，文件名带时间戳（视频 `h3-<stamp>.mp4`，音频 `music3-<stamp>.wav`）， — 无裁决（未落任何面）
- R-media-05 任何重活占着 `arbiter` 时拒绝启动新作业，拒绝带机器可读原因。 — 无裁决（未落任何面）
- R-media-06 作业失败记录失败与原因；**产出文件不存在时绝不报成功**（退出码 0 但无文件也算失败）。 — 无裁决（未落任何面）
- R-media-07 取消运行中的作业：终止子进程并释放 `arbiter` 许可，状态转为已取消。 — 无裁决（未落任何面）
- R-library-01 列出成品（视频/音频），带时间、类别、字节数。列表来源同时覆盖历史记录与磁盘上的孤儿文件 — 无裁决（未落任何面）
- R-library-02 提供成品字节流并支持 HTTP `Range`，返回 `206` 与正确的 `Content-Range`，使播放器可拖动。 — 无裁决（未落任何面）
- R-library-03 每个作业追加一条历史：类别、提示词/全部参数、耗时、状态、产出文件名、时间戳。 — 无裁决（未落任何面）
- R-library-04 能把一条历史的参数原样取回，供前端回填表单（「再做一版」）。 — 无裁决（未落任何面）
- R-library-05 多会话聊天：新建、列出、切换、重命名、删除。 — 无裁决（未落任何面）
- R-library-06 每个会话持久化其消息、所用模型、更新时间；重启后仍在。删除会话即删除其持久化文件。 — 无裁决（未落任何面）
- R-library-07 历史与会话一律存于用户数据根之下，不得写进 bundle 或代码目录。 — 无裁决（未落任何面）
- R-ui-04 音乐面板：风格描述、歌词、时长、进度、完成后就地播放。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-ui-05 资源面板：每个模型显示 `齐` / `一半 N%` / `没下`、体积、实际占盘， — 无裁决（面 F8 已盘问但无裁决引用它）
- R-ui-06 素材库面板：成品与历史，点击播放，点击把当时的参数回填进对应表单。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-ui-08 加载装不下的模型前弹出内存警告，确认后才继续。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-ui-09 首运界面：选择 models 目录，或收编一个既有目录树。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-ui-10 设置界面：对外 API 的开关、主机、端口，并显示可复制的 base URL — 无裁决（面 F8 已盘问但无裁决引用它）
- R-shell-01 App 从 `Contents/Resources/` 内的内嵌运行时启动服务； — 无裁决（面 F9 未盘问）
- R-shell-02 菜单栏项显示实时台面状态（空闲 / 已加载 XX / 出片中），菜单含「打开窗口」与「退出」。 — 无裁决（面 F9 未盘问）
- R-shell-03 关闭窗口不退出应用；App 留在菜单栏，服务继续存活；再次「打开窗口」能把窗口调回来。 — 无裁决（面 F9 未盘问）
- R-shell-04 退出时终止内嵌服务；不得留下孤儿进程（退出后台面端口不再有监听）。 — 无裁决（面 F9 未盘问）
- R-shell-05 Dock 图标存在，App 可被正常激活与切换（不是 LSUIElement）。 — 无裁决（面 F9 未盘问）
- R-shell-06 App 不注册任何登录项、不写任何 LaunchAgent plist。 — 无裁决（面 F9 未盘问）
- R-shell-07 首运弹出 models 目录选择（`NSOpenPanel`），并可选择收编既有目录树。 — 无裁决（面 F9 未盘问）
- R-shell-08 服务意外死亡时在界面上说明，而不是显示一个空白 WebView。 — 无裁决（面 F9 未盘问）
- R-packaging-01 一个构建脚本从干净 checkout 产出 `LocalModelDesk.app`；步骤可重复，中途失败要报错退出而非产出半成品。 — 无裁决（未落任何面）
- R-packaging-02 包内自带 Python 运行时与全部依赖；产物不依赖 `/opt/homebrew` 或任何用户级 site-packages。 — 无裁决（未落任何面）
- R-packaging-03 `Info.plist` 含 bundle id、版本、图标、`LSMinimumSystemVersion`。 — 无裁决（未落任何面）
- R-packaging-04 用 Developer ID Application 证书签名，启用 hardened runtime 与时间戳； — 无裁决（未落任何面）
- R-packaging-05 构建自动验证：`codesign --verify --deep --strict` 通过， — 无裁决（未落任何面）
- R-packaging-06 安装步骤把 App 放到 `/Applications`。 — 无裁决（未落任何面）
- R-packaging-07 卸载步骤移除 App 与旧的 `com.aa.localmodeldesk` LaunchAgent； — 无裁决（未落任何面）
- R-packaging-08 根目录旧脚本（`initModels.sh`、`run-h3.sh`、`run-music3.py`、`unload-llm.sh`）删除， — 无裁决（未落任何面）
- R-packaging-09 README 改写为安装后的真实行为，含：不自启、菜单栏形态、模型目录位置与收编、 — 无裁决（未落任何面）
- R-e2e-01 测试态服务可启动：注入假后端、临时数据根与临时模型根，浏览器可访问， — 无裁决（未落任何面）
- R-e2e-02 首运流程：无配置时呈现首运界面；选定 models 目录后进入主界面；配置确已落盘。 — 无裁决（未落任何面）
- R-e2e-03 聊天流程：选模型 → 加载 → 发消息 → 看到**逐步增长**的流式正文 → 思考块可展开 → 回复入库。 — 无裁决（未落任何面）
- R-e2e-04 多会话：新建 / 切换 / 重命名 / 删除；**刷新页面后仍在**。 — 无裁决（未落任何面）
- R-e2e-05 资源面板：齐 / 一半 N% / 没下 三态正确渲染且百分比正确； — 无裁决（未落任何面）
- R-e2e-06 视频流程：填参数 → 启动 → 进度可见 → 完成后播放器出现且 `src` 指向新成品。 — 无裁决（未落任何面）
- R-e2e-07 音乐流程：同上。 — 无裁决（未落任何面）
- R-e2e-08 互斥在 UI 上可见：媒体运行中，加载按钮与另一媒体按钮均被禁用，状态条给出拒绝原因； — 无裁决（未落任何面）
- R-e2e-09 素材库：点历史项把当时参数回填进对应表单（逐字段断言）；点成品可播放。 — 无裁决（未落任何面）
- R-e2e-10 状态条显示**真实内存数值**并随状态变化；断言页面上不存在写死的 `128` 内存字面量。 — 无裁决（未落任何面）
- R-e2e-11 设置面板显示对外 API 的两条 base URL（OpenAI 与 Anthropic），并明示当前无鉴权。 — 无裁决（未落任何面）
- R-e2e-12 **零直连断言**：通过浏览器网络拦截，断言整场 e2e 期间前端**没有向 `127.0.0.1:8767` — 无裁决（未落任何面）

## 逐面完成度

### 网页界面的视觉与交互验收（F8）— 1 问中 0 问实证通过 · 操作面 3 个，裁决触及 3 个
- **缺口** [G1] [F8] 修复之后，状态栏、聊天页、会话侧栏、视频页这四个面，在 900/940/1099/1100/1300/1400/1920 七档窗口宽度下还成立吗？ — 21 条基线规则实证通过；两条 finding 指向同一个事实：会话卡片内边距实测 12px 而基线写 16px。上一轮那两条（模型下拉越界 high、设置按钮折行 medium）在七档里都不再出现（证据：evidence/q02/）

## 旅程完成度
（无旅程声明）

## 缺口清单（按严重度）
- **low** **缺口** [G1] [F8] 修复之后，状态栏、聊天页、会话侧栏、视频页这四个面，在 900/940/1099/1100/1300/1400/1920 七档窗口宽度下还成立吗？ — 21 条基线规则实证通过；两条 finding 指向同一个事实：会话卡片内边距实测 12px 而基线写 16px。上一轮那两条（模型下拉越界 high、设置按钮折行 medium）在七档里都不再出现（证据：evidence/q02/）

## 无法自证清单（待人工验证，不计为完成也不计为失败）
（无）

## 未盘问声明（按风险排序）
- 原生外壳：窗口、菜单、状态项、错误页、生命周期（F9）— 未盘问，不计入任何完成度 · 未评估风险

## 未拉的线（已发现泄漏点、未实测——续盘从这里接手）
- [F9] contentMinSize 能不能挡住用户真的拖拽？（程序化 setContentSize 已实测挡不住，探针现在自己夹） — 泄漏点：2026-09-17：修复后请求 400px 仍被原样应用，改成探针显式夹取；用户拖拽这条路径要真拖窗口才验得了

## 缺陷模式（同类位点清点——未查位点不进任何完成度）
（无）

## 视觉基线与矩阵覆盖

基线：confirmed · visual/visual-baseline.json · visual/interaction-baseline.json
审查模式：single；文件校验不代替实际看图。
普查官原件：visual/census.json（摘要绑定）
done: 0 · gap: 28 · drift: 0 · unprovable: 0 · not_examined: 160 · not_applicable: 0 · abstracted: 78
独立性假设存疑（该轴的用例出了缺口，被它抽象掉的用例需重展开）：device ← V-bdb4cbb641eda5d896c1a5e43fc96f23c5c69b9ab38900eed47b133ff2374d7a, V-0d87f9a8be860e92c22fc451946970847cd52ed493b36922bedda4717a6a91d8, V-b6901ffabd4c1bc9bfed02ca2301fbcb29e8d335a69bb03fe1f03d00400c4e67, V-0c4f0259fd77b01b7e3beb1ab1d822007290340fa466c71032106c733703a7b1, V-695eaf0fefa9f15254c07667202090cd2534344ee1634f42a68de9012335d242, V-6103ebbceb17ab57a33e34f3ba7a0300be32597c863904ef4c4f759dff7a8994, V-687fc5064dc8775617a1b41562a1aff4b86864f0fcc7eee4fdf59797e6a6bff9, V-71c49f2c50d9dd97330e593d5f409fe4da64b362b683f07a660da66b94a74a66, V-1348d37254b3e9ea26169ecaeb3b4f90a9d0d65c23adbf9842e9370e1b9650c8, V-901f8775e8dddbf8d2e41c2b8178d9d038f20cc34b2e7846d8e03e4a5538c9be, V-ba66962e322d96961fa2170aec53442c9063d87cc2e92e572a794765fe122939, V-0e72db93d78a722a00dc3f420c19708960804837b3eb0965829fe9d209d60b29

- V-bdb4cbb641eda5d896c1a5e43fc96f23c5c69b9ab38900eed47b133ff2374d7a U2 — gap · tone=ok / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-0d87f9a8be860e92c22fc451946970847cd52ed493b36922bedda4717a6a91d8 U2 — gap · tone=ok / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-b6901ffabd4c1bc9bfed02ca2301fbcb29e8d335a69bb03fe1f03d00400c4e67 U2 — gap · tone=ok / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-0c4f0259fd77b01b7e3beb1ab1d822007290340fa466c71032106c733703a7b1 U2 — gap · tone=ok / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-695eaf0fefa9f15254c07667202090cd2534344ee1634f42a68de9012335d242 U2 — gap · tone=ok / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-48276b92ffedaf204847db6ce0acd215a914db6ad7f628afd404e40f9dc249fc U2 — gap · tone=ok / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-6103ebbceb17ab57a33e34f3ba7a0300be32597c863904ef4c4f759dff7a8994 U2 — gap · tone=ok / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-fb370e08052cf1c62f32f361c39a9989f525d6ca73ef5770518d99dea3514b94 U2 — abstracted · tone=busy / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e2fee767ec9d92896d041a075094d1ee9900d03e049fa94fe8a5f99b1eb67b03 U2 — abstracted · tone=busy / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-18111a4ca235098ca3dacb6ada66a083515daab5d4e5ccec23b50695edbf70f4 U2 — abstracted · tone=busy / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-20d139b3969b6f32129f369b73dd8c28b70af2fc0f033b03fa8de8967e26b07f U2 — abstracted · tone=busy / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2cde029c325e060a09300de70b3ad2481e251892c7b09bfa0d13c9bfcba5b495 U2 — abstracted · tone=busy / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-98c7151e31ec2d332dddef05d628312848e53c298b52d5e3be352a12c2d85fd3 U2 — not_examined · tone=busy / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-945bc509abc342afcdcaa0ffde29555ac63d63d5990ae496da60c8ff62a2c01c U2 — abstracted · tone=busy / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a9b0554a30e9faa486156a4e79b77de5d7df5aed054c05e2839061ee1bb8968b U2 — abstracted · tone=error / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-baef193cc45ccbcbc616e666ccbe9a9f51f939201a28d5b07ceea1893a8e4be5 U2 — abstracted · tone=error / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-258235e2ee9b16fdc57d6429afa22b44046f44fb7015b3f0fda56f58c5ff48c0 U2 — abstracted · tone=error / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4b3efd0789236788b27e10bdb9de2e4364e5a331bfe998a213fba5995da01410 U2 — abstracted · tone=error / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f1c498ef18a5c472bd6291522e1ed82cdb2cc525f7af76820c1b76b863acc105 U2 — abstracted · tone=error / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-103c967901a9f0e5958a2a82bbb8dd1431937f6bf6d882d52c2f44ad24ad4740 U2 — not_examined · tone=error / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ac37816b8a6c3b36b71905d800288a9d6b77c92eb11eb60c546288e72f540e87 U2 — abstracted · tone=error / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ba2728e45f4fe87b9095ce95920cdfa1555ee7ecd4fdc3483a3f7b73d9675d73 U2 — abstracted · offline=1 服务失联 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e0124188b155c8fab955cdd8088dc4a962c6d3578d892d53091a81eb2152b216 U2 — abstracted · offline=1 服务失联 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b0f00f1228911b7c624f2491a2944572634d4696a50a96d88c3878e12faf584f U2 — abstracted · offline=1 服务失联 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c8a7f204ab42f0dfee11501b46dcc456a2bddd5d3e32f7d5c4ece4671a532286 U2 — abstracted · offline=1 服务失联 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5bedf6902332eecf0bee9cfe578244a0d54bef4ac8571c9f56ccad72cf194003 U2 — abstracted · offline=1 服务失联 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b647f803a40d7acbc63ca5c202fd66e78fdd2e1132a2da5ac90e4a739441ebeb U2 — not_examined · offline=1 服务失联 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-544ee3db4b6fe36a6dbf1a82e52070644c878b4564e4d471579dd6356d74e630 U2 — abstracted · offline=1 服务失联 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2c10184189ee9aa4a08793dfc3cd0b98b949c9af5432c13b82b6deebe4263b97 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-86bde33b29b2ada76250055b8e0ce725e924dcbba07a6f7f92b468c1b607559e U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-255e39e3ee074646755e4efe898723554b8544a8bfa111f082b847d90b47e866 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9c28e44dccb2432218e8f5f20e9d96ffc61be87b5e9a265d99abf612540265f5 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ff0b3d974fda28ceee4515fe4b2aaa268e6912633a17fe4eb739631058e4aa38 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-509d998123864f153b8a3dcf3285d2060e4ebdb8f990d928dc7998e574eed0ee U2 — not_examined · holder badge: ok(llm)/busy(媒体)/none(无) / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bbfdd1c38509af7d39279915b397e93714c2a280900a3b0b59279a75a5996f69 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3adc8ab6c89e45a7772bd76d1b0834e6b5e159e77ac83a1d2ff30299145a4001 U2 — abstracted · 宽版文案 >1100px / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8a724c280802ede2cde2d3ac53cdfbd704c3a20317225496d07eeb02589266c5 U2 — abstracted · 宽版文案 >1100px / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-afef06debaa5bc2be7b2cc5256ae1fbfa8be9a596f9cb47c1d0db99e1e00ad60 U2 — abstracted · 宽版文案 >1100px / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5ae1b675a8c31ba5096f87655e652261fb22d9355badba2815ecc51f2a867f89 U2 — abstracted · 宽版文案 >1100px / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ec737a18b96bc555a3c6d9006cec8d867a51a37aed45a54d1f2c557e49b18ba4 U2 — abstracted · 宽版文案 >1100px / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a2f834d3df3d3245e2b231f133e5bfd3eb06d34949343389cd06b9c18e4af15a U2 — not_examined · 宽版文案 >1100px / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d7968ca6891e8f37d001759d4a8cb13a79d872b7944589d1e9e648b86267fc29 U2 — abstracted · 宽版文案 >1100px / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0b86b9d9c4f26e6b33b61ea9f3a1d401f2f19caf072eefff9ac163d1839c9318 U2 — abstracted · 窄版文案 ≤1100px / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5aa2d8ed91f615a25419b587e3ea357dcb658b2d7613a9fb74b6bf98f6a287bc U2 — abstracted · 窄版文案 ≤1100px / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4eca079c9c51ef8b43db227b511daa19507646f83f1464280b39630cdde3c7d6 U2 — abstracted · 窄版文案 ≤1100px / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bf64514ff5c12a5abfe94f1cd410ab11fead540cf5c855d22dc9f9a1c2d8d6ab U2 — abstracted · 窄版文案 ≤1100px / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7e6a54ac94491c65076250936f567c7aa3398ddca7025c15e2e63b0c46c95246 U2 — abstracted · 窄版文案 ≤1100px / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ac9bf4dd6eb74693289e6b4bb67a4bb94c14b8f0dca3f3e86e09a57854fe2af8 U2 — not_examined · 窄版文案 ≤1100px / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a8698c98481166580fe4161d98ac0eb04e317c536560e62475700c7a8e27a527 U2 — abstracted · 窄版文案 ≤1100px / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-92da992a3bd6b94b4c52d3de7a5534f76b7b35d6fb12eda4f3c9d643a66fefb9 U2 — abstracted · resize-drag / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6052747d10ef6c1092451a55f5ad529e199d0a6aa4986301549f19be4c540859 U2 — abstracted · resize-drag / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-707737b094e9e93e171de1619b2bc54a2d9d421cccb459d7a4582a601d8081e0 U2 — abstracted · resize-drag / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d8c461565f426e9fc4d20df22e2806f671ac0384e3aa565b7f1c2e8d7d770402 U2 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9b376555aaece6be1ecf8d552255efda229fa0e9f96e4992881e156d1cd5262a U2 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-402187151e671fffe193ab3f014286ca53dcf10274b77f8dfe2c55ca38b225ae U2 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4fb9cdef1b313a72e38f04891ec7cf0852feaed1782e40387b17565ba6020b55 U2 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c301a384cc8159b904684118dee0d2878a325243b5b7c6c41405260ff1f6c66a U4 — gap · 模型下拉：未下载/不完整项 disabled / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-bfdceb3c5180958a8c301652ab985d5a882d8062a3d4066dc87fe6db76c12c2e U4 — gap · 模型下拉：未下载/不完整项 disabled / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-a653b091acdc707170f60cdf96542c39b46ed3e2a9f6a11116ffd932913cbcf6 U4 — gap · 模型下拉：未下载/不完整项 disabled / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-a8358d5573dba07ad2acf3b915ed7aa73734db4961599286b1df046f64b9bf1a U4 — gap · 模型下拉：未下载/不完整项 disabled / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-d633e9a380b9c3da3a7b2694d0d9421d61144d2f171b2995bd1f067936afddd9 U4 — gap · 模型下拉：未下载/不完整项 disabled / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-13bf2a211e8a7965c9771334d2aad78e7a0a1b15b1548bd131ceb6997266ae7d U4 — gap · 模型下拉：未下载/不完整项 disabled / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-97e5b1a42d26b88b5eb0c3f6f158337212ff1a380e0cb8f72667dcdd5bb75fa9 U4 — gap · 模型下拉：未下载/不完整项 disabled / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-7b1c9085f5c2b8a621bb7bf0b159066909093f797a6cefed7e10e6346489d0dc U4 — not_examined · 未加载 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9db62739edab87e3ccce0a9acabd5d5b4c1af4d7d5b9c3e12877d92264d7c244 U4 — not_examined · 未加载 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-99262ee5211fa30914991d223b57bbbb4dd8492960fbefe382c678926abfcad6 U4 — not_examined · 未加载 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-48a7e9269a7cbc2c03294e0b498b03074a230641a44f31183c400f29ba8820ed U4 — not_examined · 未加载 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9d4194ebd9ef50b383c7b4ba1cd152bc09e6fd2939f7de888e13e7bbd9ca7860 U4 — not_examined · 未加载 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3a2a8618d0f35d24d1b908886209841a55b62e11a3aa5f1c99904fc4a3221747 U4 — not_examined · 未加载 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-caede91cc4429300598c28fc1db9e5dfad604741e65df102f18b2e58ac7632c5 U4 — not_examined · 未加载 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f46c73f06102f39353dfd821d9bdf802035043abdab2c2a133e7efe59f828ad8 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-31a70e1d5bb871633c64109bd8b893b4e5e3c3abf5fea03ff3ac1c04745a0a21 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-68907599a1abd06989e05c6c577599730665a5440daf0064e85ef37fe756b817 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-87d4ae3d6f52df2261bd5cfe7342e0988c45990f5ad70ab226ac5cc085fc2359 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d7e01aa87267981ffc558d3b6b0b0615101d7cb18618ced8e6a159887db19ea6 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-845b01cf7b160623c232cda4fbe7b8d3e0a2369bc5197dbe08ecd901148c6fba U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-988e395ecb240f85a2e4e96f1a412dd7b63885eb68f60fd3fac588738fdacd13 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-439373504c3a07ac4a0df27b6ed3664ef929f8bcc61c4749944f02f5ee840b16 U4 — not_examined · 已加载 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e37d0907e762c4f92647454a0dce76d33df3e4594c96a491bb44b67c34c08fce U4 — not_examined · 已加载 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-90a141fb6169a30e3c5428cf99736cb2bd585a33d801848ee16413797d8ff5cb U4 — not_examined · 已加载 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-913b21c6eb68d70ff1c3e9f129324b8a95785cb2a999b45e05cc8d379f845212 U4 — not_examined · 已加载 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2a532350987adfe2092db23a15597b5a39bd42b441ccc67d54faa5b05c1697d1 U4 — not_examined · 已加载 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7ec84bfadb43808a9f84fa7a783755386dd89d1515406f29b3815d855d488c37 U4 — not_examined · 已加载 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0d4fca2c799916351cded2304c50ce462de08815e98e68489779d7426b7c5dd5 U4 — not_examined · 已加载 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7c67ac9b40c81db9e4855520bcb7f1710bacfcfa9b76a8d10ba2acc18a5d9868 U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5094542f631a1b46abf4003626ce3632225ee5493e3a2b3f19822f16c70b04bc U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-89b52f3fc9f832cc44e7ab755c814020fa33124f9d458e088009ed22d5201539 U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-52ec9ad23890d9cdc5c9d8569ce13ccbf48ec0797b64c9e395c53d033a23382f U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1f4c4d8f8a576cb9353fea7fb5a757be0804fbf7948e53ca7cb7538d732da54a U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3e339cbf17c8336ef878f7d1e1a5819e688856bf2e51087922b91e0436be752e U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7fdda6013de1cef4443bfc0753533a08b0442069a5d643c44a5052d05d9d34de U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b95220d967cb2b1a6a7e601ea2d86d2e54bb09b10ac5e65564f27241d4465503 U4 — not_examined · 加载失败（log_tail 挂 title） / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-291f8d514df470126b64c28388cda4e0604b555e1fa30c31e6e3dc8833d22f26 U4 — not_examined · 加载失败（log_tail 挂 title） / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-89b5cdc19f16c8ac579fef2e7815c964541cc6aacb46a024100830bfbf62c914 U4 — not_examined · 加载失败（log_tail 挂 title） / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7be20e89b19264c21f06b25bb3aacec99b6ef8f85bee9a1b62550db7c36928d8 U4 — not_examined · 加载失败（log_tail 挂 title） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1581716aaecebc56f173a4d9611c5353f15f284d7b9f7c18c95f49f6e081a051 U4 — not_examined · 加载失败（log_tail 挂 title） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-95de555ccda2c2de095e25c7e228c6f51cd8d77daaa4d5cdd925d2a53ac28d7c U4 — not_examined · 加载失败（log_tail 挂 title） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9c15bd5edc64308f17c058d9b65d4e1a9150babdebe937a791efb1093bf18a3c U4 — not_examined · 加载失败（log_tail 挂 title） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7517bd66c94b1f0ab3d058eb85709f14a30ba052fe9336f4071a91d80d23ceea U4 — not_examined · 空会话空态 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-fe756f4e838408c5cfbf03891e5f602eb107755e8de3c11ac6a5f168d97788eb U4 — not_examined · 空会话空态 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-26351feefadd4666fe337a8012f621356b8f099dd746cda36f95e9f95733c7a7 U4 — not_examined · 空会话空态 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5d89e7a85dac86101edf320306a1642635ba1811688011957f601685808e3e2f U4 — not_examined · 空会话空态 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9be335657435247b2fccee0000ba3b568f2f13700e9766d49b83ae3cc5848e8a U4 — not_examined · 空会话空态 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-fa2c44c4d07cdfa8cb435127ff365ec8d523bd894f05bd6026967319a4a43a43 U4 — not_examined · 空会话空态 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b062196529ea0edc794f3443a9685d301d674ca3198e38bcfbee4c0227711dca U4 — not_examined · 空会话空态 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c6a8016b8ce5842f4ae5165fc7a73c5a618f27345e3999e4dd08f825a7657d7e U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-32ad6243ffb966c221484d665187afe9ed57e7d10abdfb947e68b78f1b22d0f8 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1ce1bb1b7c9dd2ec85b00de6cd59f3222be2bd263d5289053032122bbe02a0f2 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-39dc9c378c80c1170515f0a494c64f28742b67f146384e1311fc0829e65905a8 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3e1cb0b2431aecc946e9683fab13215797454cb9326d07a61b0af0be53fd446e U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-627bf0d86b2c35f478cc61b63c6793b9c2cc5c9838d557a54395784414af5cd0 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-550694f00ff7aa987abb07ae29074e5ecd5b236fa0b425fdff901ad668bd4008 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ce704e58b2de378a0bfa51827d299262ac0de19e0cb92016b12531571910cd56 U4 — not_examined · 思考折叠块 已思考 N 秒 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-72517eff771fa62ceab6e68df720c64c8eec04e867ed22afd7c851fa51d47ab2 U4 — not_examined · 思考折叠块 已思考 N 秒 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-eba1eab4b61342fa5d0d811dd8b49038c54fdf88758c83c35024c6cd987b396c U4 — not_examined · 思考折叠块 已思考 N 秒 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ace587ffbdfec68cca89ce9a21f6f2262f2b31b8f32be78f0cfa1a79e07db94f U4 — not_examined · 思考折叠块 已思考 N 秒 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-39b44fe165d9fd85e96eb0d3b6beb82c13585a93a4159943d61f903f61ade513 U4 — not_examined · 思考折叠块 已思考 N 秒 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-be87f700a374ff702d46db92e4063f5883014cd65401a53189dc7d20e0519873 U4 — not_examined · 思考折叠块 已思考 N 秒 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-244f41361928c6a05611c74ba1fe8b41c2af739970c0dc62047572ef529cc7a6 U4 — not_examined · 思考折叠块 已思考 N 秒 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a533776ee58a8719c59785d5f6f971f6e25f7afe3b2941f88b7659bc5872255f U4 — not_examined · 流被中断/被停止/上游错误 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f43a6a7ca2ead9f5390c3c1898ba999aae3fb76b64651e40f0b1210793fd75e4 U4 — not_examined · 流被中断/被停止/上游错误 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b9715e688f3113675d0a52dbb15c1b1b1df78524a54ce376402911f8cce24104 U4 — not_examined · 流被中断/被停止/上游错误 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a231e3f0e3dc55f7f0f84931b6df7117ec415c54129dc49d38ef2905daffeb93 U4 — not_examined · 流被中断/被停止/上游错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-86cfa04059e7d796f7a8b1d5ff8fbac57258bf20d6595fbf7ceedec34223117b U4 — not_examined · 流被中断/被停止/上游错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3ab81374ee51a4c9ae12baf1c26b509e266f81efe1e0b917d1b32195b88df367 U4 — not_examined · 流被中断/被停止/上游错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e2ed0ee5925dd6007349ab2bd03ac6995bd65590109210688d00107135164b1a U4 — not_examined · 流被中断/被停止/上游错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-175d380cf0786b7dd50283365cfb1c568c803308dd5041e11fd1c2609eaf47e3 U4 — not_examined · 重试行 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-221ffd2aedc4e092b519051d11feb585364e50079d280d37093794a082362e47 U4 — not_examined · 重试行 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2c98be9ed7cf45f973e094c08cb6227a5ce4867f30620af153231ee304ff17d3 U4 — not_examined · 重试行 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e5151eb154ba7adbe77b6d5bd3ff9f93fb6dfd40af3211f1d89a50aa6f7c77f9 U4 — not_examined · 重试行 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4243e11d6a812778641cf4d8b044e3dc7b51f5676c96aae0612fb71144a4879f U4 — not_examined · 重试行 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3fe71851636a9a74ccdfab5805eb6d3e90720869abb3d5945c2b9bca24904985 U4 — not_examined · 重试行 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-361afb2dfeb37e0e1eadc9b51378c1e20ab34a6c9bc8b0b67d605f4f02c46330 U4 — not_examined · 重试行 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-48a90729e92216b7fa3f2ed53811624726c714e2c3524054e2fc3c236d57e187 U4 — not_examined · 内联错误 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ee07e8f7a20148effe308aafa7b569370c388e802f2cec8e9c872bebb1f1bbf6 U4 — not_examined · 内联错误 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-953441ade6ff43d654e7caa962732ea036130d8ac422e343d46d7df2d56c35a2 U4 — not_examined · 内联错误 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1295dd167d0993ea19f42694f64ae084fc3217b2a666f4cd26ffe40af3e181b3 U4 — not_examined · 内联错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d4aa55fff0525ce74ddc997e1405f278bd18cc1bf6d203de9a9d23e8d3ea03fe U4 — not_examined · 内联错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1837ecb89e9a6faa18dc56fd40853ea6aa049b40d11b21a5439ff2c0dd9f51e9 U4 — not_examined · 内联错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9c31fd40c095964abb540c53096a398b6f876ea66f6c1474de0a3d97cd9b99e3 U4 — not_examined · 内联错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8848d64971aed09f59b23cc2f88e4c4c623ee8e734897d514551d99754af9892 U4 — not_examined · scroll-bottom / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f37384291dcc0b9484fccb644923929405a3e70e1b186613d6eeff2cd6413cfe U4 — not_examined · scroll-bottom / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bb52b35303883d807a7581f3d48bde624bf6bb12522e960ae94d49e68d31547d U4 — not_examined · scroll-bottom / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-30da8ea39ab2a326015ee0f731830e2f8ccd249483487bedbbfe85a58a78680b U4 — not_examined · scroll-bottom / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-21656d16762809a28da1f1694ab7f4bb30155bbe76cf77c29d0f315f1e6bda31 U4 — not_examined · scroll-bottom / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9e065867911c6c1f10dad7d5931e1ee5acd9397dad9ea41f92943b1531ee7e61 U4 — not_examined · scroll-bottom / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b47377f08cd932adb2da5f6e3fa7cc7e5de9d7bf8a2df4d7f1fda5df052bb157 U4 — not_examined · scroll-bottom / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2e7f8d0b1706dad1ab4c9ec81d2a1c1dde735c2e492a80fae70ea45a0f82eab1 U4 — not_examined · resize-drag / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-43e68100e36e3924890121d1b23364ab17b0a720bec78ea70844ff8d0018e09a U4 — not_examined · resize-drag / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-fc218ef30ee77dac91ca5b2151920de03e348c43e318f12b3b1ea600401df6be U4 — not_examined · resize-drag / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5d3407ad0d70bd4bd7866f6b6355b1d754906857d1f43e0535adca30eabba84d U4 — not_examined · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0b7ef45e84a0a26cd28d1f9ea0d7c2e2e8312f67f43ac2159509b6c811cfa538 U4 — not_examined · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b2da832612102213c2942f933b8de83f32625749d533e80a33ac38d449b3c33f U4 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2e4aeb58f7f1932da19665dc21af42ac33fc95b32a247308abe9c246b5c0044c U4 — not_examined · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-687fc5064dc8775617a1b41562a1aff4b86864f0fcc7eee4fdf59797e6a6bff9 U5 — gap · 当前会话高亮 aria-current / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-71c49f2c50d9dd97330e593d5f409fe4da64b362b683f07a660da66b94a74a66 U5 — gap · 当前会话高亮 aria-current / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-1348d37254b3e9ea26169ecaeb3b4f90a9d0d65c23adbf9842e9370e1b9650c8 U5 — gap · 当前会话高亮 aria-current / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-901f8775e8dddbf8d2e41c2b8178d9d038f20cc34b2e7846d8e03e4a5538c9be U5 — gap · 当前会话高亮 aria-current / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-ba66962e322d96961fa2170aec53442c9063d87cc2e92e572a794765fe122939 U5 — gap · 当前会话高亮 aria-current / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-26e6dec31295e2d044bff629ab429a1e7bbc7428cf692a23ce26d4a86a22f2dc U5 — gap · 当前会话高亮 aria-current / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-0e72db93d78a722a00dc3f420c19708960804837b3eb0965829fe9d209d60b29 U5 — gap · 当前会话高亮 aria-current / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-fd6a09b0ee791279d7b86b3daed67b4eacaab4790d7a27fb7cdf8d7bfae2a9e3 U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bb720b70743f73f8a7f60ab541ab68f0732c27014892f91671883226d83754dc U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b6f24b4a38a1fd9df9b9a6b747b45b1494acf3fa1efad1e0be91eb7fed79af8a U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-270ae9a3a925803856b43b5ec7688cc20ff33f0673ddb3aa00646947dfe11458 U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3e90895c7343a625bec54e9b26b3387720270bf054d863fc470d4ee9a87c410e U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6489b1ad50841f5812356b70f7e2b907b582f627f02b3bdf22e59bf711d22797 U5 — not_examined · hover/focus-within 才露出改名与删除按钮 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5486179092ea0c4bbcf40a59c77a92f3f48a0b429e82ce77adffefbc1013aecf U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-66cb459e9868196068b9d1f38e97aa74329eaa80bf837e2aa263113b203793fc U5 — abstracted · 就地改名输入框 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-22d68b180d21d8a06cacf7394171dc64d5966a636f808d97f396abc5d756db63 U5 — abstracted · 就地改名输入框 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ed859cf5f36584d12c9b19751a6e3ce2a6ad5e10973e10641f03796dab0b5774 U5 — abstracted · 就地改名输入框 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9f10b244693f241141cbdfb08204f2a25cddb0bb3371d4734da65a661e3871ae U5 — abstracted · 就地改名输入框 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c7b37ccf15d880bfea74cffb6c9378bb224247884d8bcd22f1aef9fd5df40b32 U5 — abstracted · 就地改名输入框 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-da447aa43bfab3f4afe5c04408c948a954985f4d561a9cb2e7e911e51ae655ec U5 — not_examined · 就地改名输入框 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-44233a0f0490a3c8adcce42e8f809a29166cc67972611f57c893fc64a1541e72 U5 — abstracted · 就地改名输入框 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6299ce7cfa0f26fb850909c67b5a285ea1f5b534ed475e14137ed7c7560732de U5 — abstracted · 删除确认对话框 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2ac7c6cafcc69c9b856c13e87e53d41796ead7086a8b475d60eae8fb5bc1101a U5 — abstracted · 删除确认对话框 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b4a75cec6f6431f937d8cfdc316461c41420c91d25307ebdc0119d1fdad174e2 U5 — abstracted · 删除确认对话框 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-33f4c6e3d69ce20299f009014991efa3d14b407cb61f83111a62652656a22d14 U5 — abstracted · 删除确认对话框 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a5043c540f25c1700af4f9be51fb2dc3578483540375171fabd85f484db1691a U5 — abstracted · 删除确认对话框 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-02c1ac9f5d75db3c24dd0fe8785b0afe2bcffb89d66c0b5674b8b810fa03042e U5 — not_examined · 删除确认对话框 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6ac8732934b6fe09c803190fdd16eac62833288bbe51480984fa80a0ba342110 U5 — abstracted · 删除确认对话框 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d2e70dfedb8a84bcd96b19966f5d18a01ff71ab60a1a4f5ffd2cd82dbb15b167 U5 — abstracted · 列表为空时自动建一个会话 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-345dd2f3675c6fa2d8dcf9be3be35b0591fdc1272e8bc69b8189f1f8cb1c1174 U5 — abstracted · 列表为空时自动建一个会话 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6a2063f8a62bf187e2b82a59a71e6a9a4a1e6d7c31a6476ff01a69276597704c U5 — abstracted · 列表为空时自动建一个会话 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a26482cbb41a293f877572013a3985a47f184873893ac1916965387838f363b9 U5 — abstracted · 列表为空时自动建一个会话 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d2232f0cb96539dcbe7aca49470a4d66ac2d3243a46db3d0517514b80743caeb U5 — abstracted · 列表为空时自动建一个会话 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4761ab8b62b01524ccce265b32fe6f2d3da4a80d8205394429556ea2ba473e0a U5 — not_examined · 列表为空时自动建一个会话 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-476691b36ff740817c5a59166ebf73e0d5a39ada180f4aa08a054038901f0a71 U5 — abstracted · 列表为空时自动建一个会话 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1aec384cc4b9ca5cbcaf016794508063392f3dab77bbe8a49da69e45541b914b U5 — abstracted · scroll-bottom / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-72520c8101290249348d65660e73db2b340ebb86a0049450438273048dc2c769 U5 — abstracted · scroll-bottom / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-52247e2c36b14f885d5c48ecf0c85568310293331e430217363a7e83f4d94300 U5 — abstracted · scroll-bottom / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d748006c25f43ea1b3104d279dfb223937a289d4b148f188bef618914a28845d U5 — abstracted · scroll-bottom / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-91d69e1f9b48ccb92e0ab3336203bcbae101cdbb84342ade4fb1f99afec70f07 U5 — abstracted · scroll-bottom / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-eb1fdd1ac938917e2fa66d1e59e5a6566606f19060747bd330d9f036a8ebc40e U5 — not_examined · scroll-bottom / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-957c90ef3a54a3509794229590dc7989056c95e4a31e3e90a858722ad844cc01 U5 — abstracted · scroll-bottom / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8a3ff27bba93a96dbaf6174db6ffd23cb56dbbcdde9da9d672916202a924953f U5 — abstracted · resize-drag / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7e052648c859bfb091778330afbc17f86ba16fef4a60e99de94f9f1dba2d0afd U5 — abstracted · resize-drag / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8d4f4521f8806a3f1cf25492ab934c53da30538f7797066ca10a631d6da45d48 U5 — abstracted · resize-drag / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8548b243adf17060909ab7eedcfccceaa365600844a15ce363ca62f767a19aae U5 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-dd7da7fd2655d7135fbb86407c46a072d2ea9133cd05ff62d1b51068e6e4fb52 U5 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4a3f207ed68ccc88747f95e03784f5bdf5aa77047abe004cfdc5b188e7edafb6 U5 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-15c38a51697b9c99209ad82f89504dd0a40d06cc379450a32373fad836392794 U5 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-85005d00afd8479b2b11013bbb2b21dd2f0b59fb2f39bb254f9a534474d24f8b U6 — gap · 文生视频 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-2569df3c3c909cb21fadfcf7816f2fc3c59264752875f05d2e04ff632d1b9f79 U6 — gap · 文生视频 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-85f4bccd70fb3d22c6595a51ba2912eda29a7adafbbf38cc4d2573a583a71a6e U6 — gap · 文生视频 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-095564bd113af44e77401d6e22509538430442093876f9ab35addc258f9a18ad U6 — gap · 文生视频 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-e327e755ba80c921a3c1e4e529c19869458e9ef9603ac697f6d21a065b7a3751 U6 — gap · 文生视频 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-6f7e8d164f5642d59a7a0373a3fe1e8abd0ace696a974cd3831e8fe1c5d33de6 U6 — gap · 文生视频 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-f6c47c72c7aa42e3d8672558eeb37fb885b4aeab2a2f16f90c1bede47f9ff49e U6 — gap · 文生视频 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-d872bb669791d07f0df2b5b336d7d5aebef0e13d84c7fbc350d1bcf27bf15fe1 U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-dbcdd7bf31e6279dcb3c150de51d7c0583882210741a4d83f0c6da1aee3be1f8 U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-683da411d144595484039eadd686fb356542b4d634df55fb48bab40f22486bc4 U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6648af972bca0a35beb17cad78706472bf63c4c346abc01b699144a57ad36306 U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b96ba6965e2d66274f656fff8b2aa758f364a72febea54cd8a22f3f65ee940c1 U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-003d5d65ad52a811598332476566de41633b402e58bbaf053abdd36d70f8d63a U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6430c57615c2ba438f5239689dfef839b0c357e302cc3a32508ca37a80957ca9 U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5fbad99314fe389d01658299edee8f9e17f202c9ba2f12acad544cb6885fdddb U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-549b9bb2a6ba7d6f7d8f0003e794c2ca7a21296b6768311785f56498c050dea0 U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-dc0c725f1772178512f9d323776ded337bdd55e24c681a7d38f639282f5097ce U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-10974e86afd5d00370003629d5fea59a7340104106c05b850cf3342ca103ab96 U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b517bf5e2b3442e8edc6ef882f9a72beba35734c708bb9a4d138130f3a890655 U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-03265c26cc00fbe78d94bb558b65ba503c365df88b2430dfd196ca201f9784ad U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-eac76c558ca0866927b5cbe3a61279e06ebc6825503b96479c7931b3c094708e U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b31561a5a19e1bfaa1bd038bf385c65ee55ce44c7463758de3e4a65e60087bd4 U6 — not_examined · 上传中/上传失败 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f471328c24b893b5bb374689be3abec125e1aa095a7b0b684b7f041932481fbb U6 — not_examined · 上传中/上传失败 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-45d08ce9bb49cb9dd7466a91d38b99076ae8456d3a35aaa6d189ac54f9fc2a85 U6 — not_examined · 上传中/上传失败 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a8d83210aa99572ecf32a72f34387b611292805908d32c6726ccf80d6ef44add U6 — not_examined · 上传中/上传失败 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ee4bcc08702ba3c710702d188e161de25fbf50abffa2eb29e06f6d4556266f12 U6 — not_examined · 上传中/上传失败 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-26aebb04c885a4e299c33779530abe2dc0ee9bc523db2f53257832b5abfa8404 U6 — not_examined · 上传中/上传失败 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-627dcee23dd27296784812c5fc2b88110aaa1c7b9348b7d6f2a8091d5e203d6b U6 — not_examined · 上传中/上传失败 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-54d66e8fa4c58cc8ddaef7792ac0a05e4fcff5958a8f4d6afd415048eccc1d37 U6 — not_examined · 画幅与时长下拉、步数 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-05adbac430393552fa36db89ada7c85d32828bae699cd8d14e70e51bdb724fae U6 — not_examined · 画幅与时长下拉、步数 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-161104beabafd314c646ce128a0fdb43c1acf18ee7dcc4c60f1fed018defaf29 U6 — not_examined · 画幅与时长下拉、步数 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d94efb8d47be42fa9caa5707c06354b9e1f7aa25e3d9e862581ffa19da0e0e55 U6 — not_examined · 画幅与时长下拉、步数 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9b778e8b43aef195157a4d884a6a14e7abc887f53caecd054570aebfce9459df U6 — not_examined · 画幅与时长下拉、步数 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6cdce35fedd0290b43a3ad7152adda4b27618665aba36119b2480da4f845c89d U6 — not_examined · 画幅与时长下拉、步数 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b7e82688074890617a97b81f2178d959d86ae8bb64f7220421a69416049f9599 U6 — not_examined · 画幅与时长下拉、步数 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5874f1bc4768074132bc33edfddf649cdc22c874ad6e55ee6d4d123de74827ea U6 — not_examined · 成本提示 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7bf8026159742f37e46c8ad85ee1e1498ee2fb964ec9a8f2214f94ce801734ad U6 — not_examined · 成本提示 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-febf325f8fe04866438cc063562ebf38ecf4089c7cf62c05bdedae9bb88edd61 U6 — not_examined · 成本提示 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c87d111842040084acd66183a681f135574e82654e352593aee2e4c5c926abac U6 — not_examined · 成本提示 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-563246c7a58332d496135227ee5442ac81d20ad287f9e155955951213619f7ed U6 — not_examined · 成本提示 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-554ab4762c064064615d3954f156fab1eb19c98a24b0c48fafb246d43c0f73b5 U6 — not_examined · 成本提示 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-29e9420d6fab4d8e03fbba43bcb53055a6aec1271d9afba5aeb771a5c0cb65a0 U6 — not_examined · 成本提示 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6cd1b19082d65a37914c6f03322b6f9a33e579086fa92d162005d47a3e8ab750 U6 — not_examined · 互斥不可开工提示 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c4bebf7b035949c54e21b40838b9384673ebd7a8e90f74291278266f8820ee4a U6 — not_examined · 互斥不可开工提示 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7cc92ba71a3786b0551d201ba210477a0def888e962a22e397eaf9974d3cad7b U6 — not_examined · 互斥不可开工提示 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8bde7dabfb848ed2f7b94a090577de38bbde9571223130739321a371df040532 U6 — not_examined · 互斥不可开工提示 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1cca975b634c9eccb750c2235a65174861576600ddf782b4299ece4ed0b019f9 U6 — not_examined · 互斥不可开工提示 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2bf7866ce75b15e3b618083f1218a96282324b4331e3b816c746d3beda2a4dc4 U6 — not_examined · 互斥不可开工提示 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-04c15bde4c68c7c3c48b83437d5315c0bc9060f43eddb5c27fc7eb4f0cee56a7 U6 — not_examined · 互斥不可开工提示 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e172742ea3516b45c4faaf3ec24b357ae72dbf1028063c2a40aa80c56bcb9de3 U6 — not_examined · 内联错误 / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6fb8656f83d001a5cbb33088ad230c52e52dafe9f80bbed7c9e805c1c5a74387 U6 — not_examined · 内联错误 / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-12604fe20120a17cd4aac91ccd6e3bf0ea0254c21d48b1ef1276ad197a9450ae U6 — not_examined · 内联错误 / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-255a5d9b9ee570b98e1fc1e5c46d7457dbc193ce380ca6afc2139f5060d38061 U6 — not_examined · 内联错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3d3602d22762ac16386ed47ff373e78844574f81eb28a42aba03589843d2e773 U6 — not_examined · 内联错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-88fbd7d415a3f54355d755c90befcbc0a14db3595f3ec85d0d5488c3143a83f5 U6 — not_examined · 内联错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2fab26f8b296e07e5fa5a4ca7ba68b61952d9dbd171241c4546381d31098b361 U6 — not_examined · 内联错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e915339d16b3a6df6fad5958fc292f2796b3f942e8fb15f5c6f94ec470431cb3 U6 — not_examined · resize-drag / 900x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5482b246f927a83031f24e6e71748523369465a178dac5155cbdb4154ebcb520 U6 — not_examined · resize-drag / 940x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a030960041127ac5ad3dd906c5aa1ffa81fc592c4c05881acf1fab7b1b60929e U6 — not_examined · resize-drag / 1099x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a3784d35b9ad226054460d87d405ac76c3102f79c7659f614df86e754c2db08c U6 — not_examined · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2335e4a3f8b9fb37f49db8dabfb7d5e67adde578619696bf0f8e93cb58487a4d U6 — not_examined · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-92df62277ed32b20efd8c47bdc30084024e970bbd33848ef6d3da29826e70ed2 U6 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-58a9bc09b06c4dd2a692f5d23e7e873737c046496c205885ee4816fc4098f1c5 U6 — not_examined · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse

逐轴覆盖（已抽象与不适用不计）：
- state：holder badge: ok(llm)/busy(媒体)/none(无) 0/1 · hover/focus-within 才露出改名与删除按钮 0/1 · offline=1 服务失联 0/1 · resize-drag 0/16 · scroll-bottom 0/8 · tone=busy 0/1 · tone=error 0/1 · tone=ok 7/7 · 上传中/上传失败 0/7 · 互斥不可开工提示 0/7 · 内联错误 0/14 · 列表为空时自动建一个会话 0/1 · 删除确认对话框 0/1 · 加载中（卸载按钮变「取消加载」） 0/7 · 加载失败（log_tail 挂 title） 0/7 · 图生视频（首帧/尾帧、预览、清除尾帧） 0/7 · 宽版文案 >1100px 0/1 · 就地改名输入框 0/1 · 已加载 0/7 · 当前会话高亮 aria-current 7/7 · 思考折叠块 已思考 N 秒 0/7 · 成本提示 0/7 · 文生视频 7/7 · 未加载 0/7 · 模型下拉：未下载/不完整项 disabled 7/7 · 流式回答中（发送键变「停止」、composer 半透明） 0/7 · 流被中断/被停止/上游错误 0/7 · 画幅与时长下拉、步数 0/7 · 空会话空态 0/7 · 窄版文案 ≤1100px 0/1 · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） 0/7 · 视频参考生成（参考视频、音轨复选） 0/7 · 重试行 0/7
- device：1099x700@2 4/25 · 1100x700@2 4/25 · 1300x800@2 4/25 · 1400x900@2 4/38 · 1920x1080@2 4/25 · 900x600@2 4/25 · 940x600@2 4/25
- os：macOS 26.0 WKWebView 28/188
- appearance：dark 28/188
- dynamic_type：浏览器缩放 100% 28/188
- locale：zh-CN 28/188
- orientation：landscape 28/188
- pointer：mouse 28/188
