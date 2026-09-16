# 完成度报告 — LocalModelDesk（macOS 外壳 + 本地 Python 服务 + 零依赖 Web UI）

需求基准：superstorm-registry · 共 13 面，盘问 5 面 · 实测 7 问 · 旅程 4 条，盘问 4 条 · 操作面 97 个，裁决触及 28 个

## 总览

实证完成：2（运行时 2 · 代码 0 · 台账 0） · 缺口：4 · 跑偏：0 · 无法自证：1
旅程裁决：实证完成：0 · 缺口：3 · 跑偏：1 · 无法自证：0

> 盘问官即交付作者（examiner_is_author）：bias-guard 生效——gap 从严，降级为 low 或 done 需额外独立证据。

> 本 run 取证类子 agent（实测官、枚举官）用 sonnet，用户于 2026-09-16 确认：「成本优先：取证类用 Sonnet 5」。裁决与普查仍用会话模型。
> 定靶时盘问官推荐的是选项 A（本轮取证要驱动真窗口改宽、读回、拍图，降档实测官更易残缺重派）。

取证时间：首问 2026-09-16T18:47:01+09:00 · 末问 2026-09-17T00:29:12+09:00 · 跨 342 分钟
相邻 runtime 问间隔不足 60 秒，请核对是否真实取证：聊天页、状态栏、标签条、会话侧栏、作业视图、助手行这六个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？ → 视频页、音乐页、资源页、素材库、设置抽屉这五个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？（0 秒）；这四个端点在「请求体有问题」时，客户端拿到的是参数错误，还是状态错误 / 未捕获异常？POST /api/llm/load（缺 key）、POST /api/first-run（models_root 传非字符串）、PUT /api/config（配置损坏时传一个非法字段）、POST /api/resources/download（key 不在目录表里） → J1 走得通吗？（2 秒）

## 规则一致性（规则 ↔ 规则；候选不计为产品缺陷）
历史台账未做规则对比；不追溯拒收原裁决。

## 需求覆盖（基准 92 条，有裁决 25 条，无裁决 67 条）
- R-foundation-02 配置持久化到 `<data root>/config.json`，字段至少含： — 缺口（这四个端点在「请求体有问题」时，客户端拿到的是参数错误，还是状态错误 / 未捕获异常？POST /api/llm/load（缺 key）、POST /api/first-run（models_root 传非字符串）、PUT /api/config（配置损坏时传一个非法字段）、POST /api/resources/download（key 不在目录表里）） · 缺口（一个全新安装（全新数据根、用户什么都没点过）的 LocalModelDesk，对外接口是开着还是关着？服务起来后它有没有真的在某个地址上监听？监听在哪个地址？）
- R-foundation-03 首运语义：无配置或 `first_run_done` 为假时，`api:readConfig` 必须能表达 needs-setup 状态； — 缺口（这四个端点在「请求体有问题」时，客户端拿到的是参数错误，还是状态错误 / 未捕获异常？POST /api/llm/load（缺 key）、POST /api/first-run（models_root 传非字符串）、PUT /api/config（配置损坏时传一个非法字段）、POST /api/resources/download（key 不在目录表里）） · 缺口（J1 走得通吗？） · 缺口（一个全新安装（全新数据根、用户什么都没点过）的 LocalModelDesk，对外接口是开着还是关着？服务起来后它有没有真的在某个地址上监听？监听在哪个地址？）
- R-foundation-04 收编既有权重：给定一个 legacy 根（如 `~/LocalModelDesk`）， — 缺口（J1 走得通吗？）
- R-resources-01 单一目录定义，供服务端、前端、以及任何 CLI 入口共同消费； — 缺口（J1 走得通吗？）
- R-resources-03 每项报出 `present` | `partial` | `missing`；`partial` 必须带完成百分比 — 缺口（J1 走得通吗？）
- R-resources-05 对某一目录项发起下载；中断后再次发起必须续传，已完整的文件不得重下。 — 缺口（这四个端点在「请求体有问题」时，客户端拿到的是参数错误，还是状态错误 / 未捕获异常？POST /api/llm/load（缺 key）、POST /api/first-run（models_root 传非字符串）、PUT /api/config（配置损坏时传一个非法字段）、POST /api/resources/download（key 不在目录表里））
- R-arbiter-06 暴露单一台面状态对象：内存里是谁、媒体是否在跑、现在能不能开下一件重活， — 无法自证（当加载模型所需的解释器不存在时，POST /api/llm/load 之后会发生什么？状态会走到某个终态吗？GET /api/llm/status 会不会一直停在 loading？台面的重活令牌会不会被永久占住？）
- R-llm-01 按目录 key 加载聊天模型：先向 `arbiter` 申请许可，再启动 mlx-lm 服务， — 缺口（这四个端点在「请求体有问题」时，客户端拿到的是参数错误，还是状态错误 / 未捕获异常？POST /api/llm/load（缺 key）、POST /api/first-run（models_root 传非字符串）、PUT /api/config（配置损坏时传一个非法字段）、POST /api/resources/download（key 不在目录表里）） · 无法自证（当加载模型所需的解释器不存在时，POST /api/llm/load 之后会发生什么？状态会走到某个终态吗？GET /api/llm/status 会不会一直停在 loading？台面的重活令牌会不会被永久占住？）
- R-llm-04 加载失败必须给出原因（mlx-lm 日志尾部），不得只报一个「加载超时」。 — 无法自证（当加载模型所需的解释器不存在时，POST /api/llm/load 之后会发生什么？状态会走到某个终态吗？GET /api/llm/status 会不会一直停在 loading？台面的重活令牌会不会被永久占住？）
- R-llm-06 媒体作业进行中、或当前没有加载模型时，聊天请求被拒绝并带明确原因，不得挂起等待。 — 实证完成（POST /api/llm/chat 还活着吗？同一 payload 分别打 /api/llm/chat 与 /api/llm/chat/stream，两个端点的可达性、HTTP 状态码与错误体形状一致吗？）
- R-gateway-07 绑定 `0.0.0.0` 于配置端口，使同网络其他设备可达；开关关闭时不监听。 — 缺口（一个全新安装（全新数据根、用户什么都没点过）的 LocalModelDesk，对外接口是开着还是关着？服务起来后它有没有真的在某个地址上监听？监听在哪个地址？）
- R-library-01 列出成品（视频/音频），带时间、类别、字节数。列表来源同时覆盖历史记录与磁盘上的孤儿文件 — 缺口（J3 走得通吗？）
- R-ui-01 前端是静态文件（`index.html`、`app.css`、ES 模块），由服务端供给； — 缺口（聊天页、状态栏、标签条、会话侧栏、作业视图、助手行这六个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-ui-02 聊天面板：模型选择、加载/卸载、流式回复、思考过程可展开、左侧会话列表（新建/切换/重命名/删除）。 — 缺口（聊天页、状态栏、标签条、会话侧栏、作业视图、助手行这六个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？） · 缺口（J4 走得通吗？）
- R-ui-03 视频面板：提示词、画幅、帧数、步数、进度、完成后就地播放。 — 缺口（视频页、音乐页、资源页、素材库、设置抽屉这五个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-ui-04 音乐面板：风格描述、歌词、时长、进度、完成后就地播放。 — 缺口（视频页、音乐页、资源页、素材库、设置抽屉这五个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-ui-05 资源面板：每个模型显示 `齐` / `一半 N%` / `没下`、体积、实际占盘， — 缺口（视频页、音乐页、资源页、素材库、设置抽屉这五个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-ui-06 素材库面板：成品与历史，点击播放，点击把当时的参数回填进对应表单。 — 缺口（视频页、音乐页、资源页、素材库、设置抽屉这五个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-ui-07 常驻状态条：真实内存（不是写死的 128）、内存里是谁、媒体是否在跑、现在能不能开下一件重活。 — 缺口（聊天页、状态栏、标签条、会话侧栏、作业视图、助手行这六个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？） · 缺口（J4 走得通吗？）
- R-ui-10 设置界面：对外 API 的开关、主机、端口，并显示可复制的 base URL — 缺口（视频页、音乐页、资源页、素材库、设置抽屉这五个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？）
- R-shell-01 App 从 `Contents/Resources/` 内的内嵌运行时启动服务； — 缺口（J4 走得通吗？）
- R-shell-04 退出时终止内嵌服务；不得留下孤儿进程（退出后台面端口不再有监听）。 — 跑偏（J2 走得通吗？） · 实证完成（台面服务意外退出后，外壳错误页上那个「▶ 详情」折叠展开后给的是什么？里面有没有日志路径？那个路径指向的文件真的存在、里面真的有这次崩溃的日志吗？）
- R-shell-05 Dock 图标存在，App 可被正常激活与切换（不是 LSUIElement）。 — 跑偏（J2 走得通吗？） · 实证完成（台面服务意外退出后，外壳错误页上那个「▶ 详情」折叠展开后给的是什么？里面有没有日志路径？那个路径指向的文件真的存在、里面真的有这次崩溃的日志吗？）
- R-shell-06 App 不注册任何登录项、不写任何 LaunchAgent plist。 — 缺口（J3 走得通吗？）
- R-shell-07 首运弹出 models 目录选择（`NSOpenPanel`），并可选择收编既有目录树。 — 缺口（J3 走得通吗？）
- R-foundation-01 所有路径由本模块单点解析，区分「只读 bundle 资源根」与「可写用户数据根」； — 无裁决（面 F1 已盘问但无裁决引用它；面 F12 未盘问）
- R-foundation-05 服务在 `mlx-h3`、内嵌 venv、模型目录任一缺失时仍能启动并提供状态接口； — 无裁决（面 F1 已盘问但无裁决引用它）
- R-foundation-06 配置写入原子：先写同目录临时文件再 `os.replace`；写到一半崩掉不得留下损坏的 `config.json`。 — 无裁决（面 F1 已盘问但无裁决引用它）
- R-resources-02 完整度以 HF 仓库文件清单为准：取得每个期望文件的路径与字节数， — 无裁决（面 F2 未盘问）
- R-resources-04 报出每项实际占盘字节数，以及 models 所在卷的剩余空间。 — 无裁决（面 F2 未盘问）
- R-resources-06 取消/暂停进行中的下载；已下载的部分必须保持可续传状态，不得清空。 — 无裁决（面 F2 未盘问）
- R-resources-07 下载进行时可查询实时进度：已完成字节/总字节、当前文件、速率、预估剩余。 — 无裁决（面 F2 未盘问）
- R-resources-08 删除某一目录项的权重并回收磁盘，需要显式确认参数（无确认参数一律拒绝执行）。 — 无裁决（面 F2 未盘问；面 F12 未盘问）
- R-resources-09 同时至多一个下载在跑；`arbiter` 报告有重活（媒体生成）在跑时，下载必须拒绝启动并说明原因。 — 无裁决（面 F2 未盘问）
- R-arbiter-01 聊天 LLM、视频生成、音乐生成三者互斥；持有者唯一，任何时刻至多一个重活。 — 无裁决（面 F3 未盘问）
- R-arbiter-02 真实内存快照：总量、已用、可用、内存压力，取自操作系统（macOS 上 `vm_stat` / `sysctl`）， — 无裁决（面 F3 未盘问）
- R-arbiter-03 按端口收割 LLM：找出监听 LLM 端口的**任何**进程并终止（先 TERM 后 KILL）， — 无裁决（面 F3 未盘问）
- R-arbiter-04 媒体作业进行中拒绝加载 LLM；已有媒体作业时拒绝启动第二个媒体作业。拒绝必须带机器可读原因。 — 无裁决（面 F3 未盘问）
- R-arbiter-05 启动媒体作业前自动让出内存（卸掉 LLM）；让出失败必须导致启动失败，不得带着 LLM 硬上。 — 无裁决（面 F3 未盘问）
- R-arbiter-07 加载某模型前比对其体积与当前可用内存，装不下要在加载前给出警告（不是加载失败后才说）。 — 无裁决（面 F3 未盘问）
- R-llm-02 卸载当前模型，并确认 LLM 端口确已释放（走 `api:reapLlmPort`，不只是终止自己的子进程）。 — 无裁决（面 F4 已盘问但无裁决引用它）
- R-llm-03 流式对话：逐 token 输出正文增量，并把思考/推理增量（`reasoning_content` / `reasoning`） — 无裁决（面 F4 已盘问但无裁决引用它）
- R-llm-05 报出当前加载的是哪个模型及其元数据（视觉能力、量化、参数量、体积）。 — 无裁决（面 F4 已盘问但无裁决引用它）
- R-llm-07 对话必须经由本服务转发；前端与外部客户端都不直连 mlx-lm 端口。 — 无裁决（面 F4 已盘问但无裁决引用它）
- R-gateway-01 `GET /v1/models`：OpenAI 格式，列出当前可服务的模型。没有模型驻留时返回空列表而非报错。 — 无裁决（面 F5 已盘问但无裁决引用它）
- R-gateway-02 `POST /v1/chat/completions` 非流式：OpenAI 请求与响应形状，含 `usage`、`finish_reason`。 — 无裁决（面 F5 已盘问但无裁决引用它）
- R-gateway-03 同端点流式：SSE，`data:` 分块与 OpenAI 增量格式一致，以 `data: [DONE]` 结束。 — 无裁决（面 F5 已盘问但无裁决引用它）
- R-gateway-04 `POST /v1/messages` 非流式：Anthropic 请求形状（`model`/`max_tokens`/`messages`/`system`） — 无裁决（面 F5 已盘问但无裁决引用它）
- R-gateway-05 同端点流式：发出 `message_start`、`content_block_start`、`content_block_delta`、 — 无裁决（面 F5 已盘问但无裁决引用它）
- R-gateway-06 Anthropic 的 `system`（字符串或块数组）、多轮 `messages`、`stop_reason` — 无裁决（面 F5 已盘问但无裁决引用它）
- R-gateway-08 无模型驻留或媒体作业进行中：返回 `503`，带 `Retry-After` 头与机器可读原因码。 — 无裁决（面 F5 已盘问但无裁决引用它；面 F13 未盘问）
- R-gateway-09 错误按各自方言的原生错误信封返回（OpenAI 的 `{"error":{...}}`； — 无裁决（面 F5 已盘问但无裁决引用它）
- R-gateway-10 请求里的 `model` 既接受目录 key，也接受当前加载模型的标识符； — 无裁决（面 F5 已盘问但无裁决引用它）
- R-media-01 启动文生视频作业：提示词、画幅（宽高）、帧数、步数。H3 命令行的构造只存在一处。 — 无裁决（面 F6 未盘问）
- R-media-02 启动文生歌曲作业：风格描述、歌词、时长。Music 3 调用的构造只存在一处。 — 无裁决（面 F6 未盘问）
- R-media-03 作业运行中可流式读取进度/日志输出。 — 无裁决（面 F6 未盘问）
- R-media-04 作业产出落在 outputs 根，文件名带时间戳（视频 `h3-<stamp>.mp4`，音频 `music3-<stamp>.wav`）， — 无裁决（面 F6 未盘问）
- R-media-05 任何重活占着 `arbiter` 时拒绝启动新作业，拒绝带机器可读原因。 — 无裁决（面 F6 未盘问）
- R-media-06 作业失败记录失败与原因；**产出文件不存在时绝不报成功**（退出码 0 但无文件也算失败）。 — 无裁决（面 F6 未盘问）
- R-media-07 取消运行中的作业：终止子进程并释放 `arbiter` 许可，状态转为已取消。 — 无裁决（面 F6 未盘问）
- R-library-02 提供成品字节流并支持 HTTP `Range`，返回 `206` 与正确的 `Content-Range`，使播放器可拖动。 — 无裁决（面 F7 未盘问；面 F12 未盘问）
- R-library-03 每个作业追加一条历史：类别、提示词/全部参数、耗时、状态、产出文件名、时间戳。 — 无裁决（面 F7 未盘问）
- R-library-04 能把一条历史的参数原样取回，供前端回填表单（「再做一版」）。 — 无裁决（面 F7 未盘问）
- R-library-05 多会话聊天：新建、列出、切换、重命名、删除。 — 无裁决（面 F7 未盘问）
- R-library-06 每个会话持久化其消息、所用模型、更新时间；重启后仍在。删除会话即删除其持久化文件。 — 无裁决（面 F7 未盘问）
- R-library-07 历史与会话一律存于用户数据根之下，不得写进 bundle 或代码目录。 — 无裁决（面 F7 未盘问）
- R-ui-08 加载装不下的模型前弹出内存警告，确认后才继续。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-ui-09 首运界面：选择 models 目录，或收编一个既有目录树。 — 无裁决（面 F8 已盘问但无裁决引用它）
- R-shell-02 菜单栏项显示实时台面状态（空闲 / 已加载 XX / 出片中），菜单含「打开窗口」与「退出」。 — 无裁决（面 F9 已盘问但无裁决引用它）
- R-shell-03 关闭窗口不退出应用；App 留在菜单栏，服务继续存活；再次「打开窗口」能把窗口调回来。 — 无裁决（面 F9 已盘问但无裁决引用它）
- R-shell-08 服务意外死亡时在界面上说明，而不是显示一个空白 WebView。 — 无裁决（面 F9 已盘问但无裁决引用它）
- R-packaging-01 一个构建脚本从干净 checkout 产出 `LocalModelDesk.app`；步骤可重复，中途失败要报错退出而非产出半成品。 — 无裁决（面 F10 未盘问）
- R-packaging-02 包内自带 Python 运行时与全部依赖；产物不依赖 `/opt/homebrew` 或任何用户级 site-packages。 — 无裁决（面 F10 未盘问）
- R-packaging-03 `Info.plist` 含 bundle id、版本、图标、`LSMinimumSystemVersion`。 — 无裁决（面 F10 未盘问）
- R-packaging-04 用 Developer ID Application 证书签名，启用 hardened runtime 与时间戳； — 无裁决（面 F10 未盘问）
- R-packaging-05 构建自动验证：`codesign --verify --deep --strict` 通过， — 无裁决（面 F10 未盘问；面 F12 未盘问）
- R-packaging-06 安装步骤把 App 放到 `/Applications`。 — 无裁决（面 F10 未盘问）
- R-packaging-07 卸载步骤移除 App 与旧的 `com.aa.localmodeldesk` LaunchAgent； — 无裁决（面 F10 未盘问）
- R-packaging-08 根目录旧脚本（`initModels.sh`、`run-h3.sh`、`run-music3.py`、`unload-llm.sh`）删除， — 无裁决（面 F10 未盘问）
- R-packaging-09 README 改写为安装后的真实行为，含：不自启、菜单栏形态、模型目录位置与收编、 — 无裁决（面 F10 未盘问）
- R-e2e-01 测试态服务可启动：注入假后端、临时数据根与临时模型根，浏览器可访问， — 无裁决（面 F11 未盘问）
- R-e2e-02 首运流程：无配置时呈现首运界面；选定 models 目录后进入主界面；配置确已落盘。 — 无裁决（面 F11 未盘问）
- R-e2e-03 聊天流程：选模型 → 加载 → 发消息 → 看到**逐步增长**的流式正文 → 思考块可展开 → 回复入库。 — 无裁决（面 F11 未盘问）
- R-e2e-04 多会话：新建 / 切换 / 重命名 / 删除；**刷新页面后仍在**。 — 无裁决（面 F11 未盘问）
- R-e2e-05 资源面板：齐 / 一半 N% / 没下 三态正确渲染且百分比正确； — 无裁决（面 F11 未盘问）
- R-e2e-06 视频流程：填参数 → 启动 → 进度可见 → 完成后播放器出现且 `src` 指向新成品。 — 无裁决（面 F11 未盘问）
- R-e2e-07 音乐流程：同上。 — 无裁决（面 F11 未盘问）
- R-e2e-08 互斥在 UI 上可见：媒体运行中，加载按钮与另一媒体按钮均被禁用，状态条给出拒绝原因； — 无裁决（面 F11 未盘问）
- R-e2e-09 素材库：点历史项把当时参数回填进对应表单（逐字段断言）；点成品可播放。 — 无裁决（面 F11 未盘问）
- R-e2e-10 状态条显示**真实内存数值**并随状态变化；断言页面上不存在写死的 `128` 内存字面量。 — 无裁决（面 F11 未盘问）
- R-e2e-11 设置面板显示对外 API 的两条 base URL（OpenAI 与 Anthropic），并明示当前无鉴权。 — 无裁决（面 F11 未盘问）
- R-e2e-12 **零直连断言**：通过浏览器网络拦截，断言整场 e2e 期间前端**没有向 `127.0.0.1:8767` — 无裁决（面 F11 未盘问）

## 逐面完成度

### 首次运行与配置落地（F1）— 1 问中 0 问实证通过 · 操作面 11 个，裁决触及 6 个，未触及：S3 重置损坏配置、S4 路径与能力自检、S60 模型目录选择面板 NSOpenPanel、D5 死契约：GET /api/paths、D8 死契约：POST /api/adopt 的 target_root 入参
- **缺口** [G3] [F1] 这四个端点在「请求体有问题」时，客户端拿到的是参数错误，还是状态错误 / 未捕获异常？POST /api/llm/load（缺 key）、POST /api/first-run（models_root 传非字符串）、PUT /api/config（配置损坏时传一个非法字段）、POST /api/resources/download（key 不在目录表里） — first-run 传非字符串 models_root → 500 {"code":"internal"} 且把 Python 原始异常消息（含类型名）透传给客户端；config 损坏时 PUT /api/config → 500 config_corrupt，对请求体里的非法字段只字不提；llm/load 缺 key → 404「未找到模型: 」（空串）（证据：evidence/q07/）

### 聊天与模型加载（F4）— 2 问中 1 问实证通过 · 操作面 8 个，裁决触及 6 个，未触及：S17 卸载/取消加载、S21 提示词助手（看手气/优化）
- **实证完成** [F4] POST /api/llm/chat 还活着吗？同一 payload 分别打 /api/llm/chat 与 /api/llm/chat/stream，两个端点的可达性、HTTP 状态码与错误体形状一致吗？ — 两个端点都可达（无 404）；未加载模型时都返回 503 {"error":{"code":"no_model_loaded","message":"当前没有加载模型"}}，逐字相同（diff 只差 Date 头）（证据：evidence/q01/）
- **无法自证** [F4] 当加载模型所需的解释器不存在时，POST /api/llm/load 之后会发生什么？状态会走到某个终态吗？GET /api/llm/status 会不会一直停在 loading？台面的重活令牌会不会被永久占住？ — 前提造不出来：dev 模式下 venv_python = Path(sys.executable)，即正在跑服务的解释器本身，必然存在。实测到的是相邻分支（解释器在、mlx_lm 模块没装），而那条分支产品处理得对：5 秒内进入 error/backend_exited 并带 log_tail，60 秒内状态稳定，can_start.llm 全程 ok（令牌已归还）（证据：evidence/q09/）

### 对外网关（F5）— 1 问中 0 问实证通过 · 操作面 8 个，裁决触及 4 个，未触及：S42 网关：OpenAI 模型列表、S43 网关：OpenAI 对话（流式/非流式）、S44 网关：Anthropic messages（流式/非流式）、S45 网关准入闸（媒体忙/未加载/模型不符 → 503 + Retry-After）
- **缺口** [G4] [F5] 一个全新安装（全新数据根、用户什么都没点过）的 LocalModelDesk，对外接口是开着还是关着？服务起来后它有没有真的在某个地址上监听？监听在哪个地址？ — 全新安装、磁盘上还没有 config.json 时，enabled 就是 true、host 就是 0.0.0.0、auth 是 none；换成空闲端口复跑，lsof 实测 `TCP *:18812 (LISTEN)`、listening:true——真的听在所有网卡上（证据：evidence/q08/）

### 网页界面的视觉与交互验收（F8）— 2 问中 0 问实证通过 · 操作面 3 个，裁决触及 3 个
- **缺口** [G1] [F8] 聊天页、状态栏、标签条、会话侧栏、作业视图、助手行这六个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？ — 独立评审官逐张看完 42 张：4 条 finding（1 high / 2 medium / 1 low），28 条基线规则实证通过；另把 1400 档四张与参考图逐像素比对，504 万像素只差 0.33%（证据：evidence/q02/）
- **缺口** [G2] [F8] 视频页、音乐页、资源页、素材库、设置抽屉这五个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？ — 独立评审官逐张看完 35 张：4 条 finding（1 medium / 3 low）。它先判「占位文字用 #a9a9a9 不在基线五色内」，核对冻结参考图后自己撤回——参考图里的占位文字同样是 #a9a9a9，那条规则是令牌枚举不是白名单（证据：evidence/q02/）

### 原生外壳：窗口、菜单、状态项、错误页、生命周期（F9）— 1 问中 1 问实证通过 · 操作面 15 个，裁决触及 5 个，未触及：S51 应用主菜单（关于 / 设置…⌘, / 隐藏 ⌘H / 隐藏其他 ⌥⌘H / 全部显示 / 退出 ⌘Q）、S52 文件菜单（关闭窗口 ⌘W）、S53 编辑菜单（撤销/重做/剪切/复制/粘贴/粘贴并匹配样式/删除/全选）、S54 窗口菜单（最小化 ⌘M / 进入全屏幕 ⌃⌘F）、S55 ⌘, 本地键盘监听（WKWebView 吞掉键等价物的补偿）、S57 WKWebView 上下文菜单（重新载入本地化）、S63 退出时按进程组同步收割子进程并核验端口已释放、S66 父进程看门狗（LMD_PARENT_PID 消失即退出）、S67 SIGTERM/SIGINT 优雅退出与自成进程组、D4 死契约：PortGuard.family(matching:)
- **实证完成** [F9] 台面服务意外退出后，外壳错误页上那个「▶ 详情」折叠展开后给的是什么？里面有没有日志路径？那个路径指向的文件真的存在、里面真的有这次崩溃的日志吗？ — 展开后给出 `日志：/tmp/…/logs/server-stdout.log` 并把尾部约 20 行内嵌在 <pre> 里；该文件真实存在（2354 字节），页面里那段与磁盘 tail -n 20 逐字符一致（证据：evidence/q10/）

## 旅程完成度

### J1 第一次打开 LocalModelDesk、机器上已有若干 MLX 模型目录的人 · 全新数据根（没有 config.json），从 app 启动 · 台面可用，且模型目录指向他自己的目录 — 缺口（medium，误导）
走了 5 步，卡在第 2 步：点击「收编」 → 未跳转，下方出现红色英文：no known model subtrees (llms, minimax-h3, minimax-music3) under /Users/aa/LocalModelDesk/llms（证据：evidence/q04/）
- 1 done 在「收编既有目录树」填入 /Users/aa/LocalModelDesk/llms，保持默认「指向」不选「移动」 → 输入框显示新值，「指向」仍选中
- 2 stuck 点击「收编」 → 未跳转，下方出现红色英文：no known model subtrees (llms, minimax-h3, minimax-music3) under /Users/aa/LocalModelDesk/llms
- 3 done 改走另一条路：在「选择 models 目录」填入同一路径 → 输入框显示新值
- 4 done 点击「使用该目录」 → 首运页消失、标签栏出现、会话已建；模型下拉列出 6 个模型，但每一项文案末尾都带「（未下载/不完整）」
- 5 done 打开设置核对模型目录 → 「模型目录 > 当前目录」= /Users/aa/LocalModelDesk/llms

### J2 正在用台面的人 · 台面服务进程突然退出 · 知道出了什么事，并点一下回到可用台面 — 跑偏（low）
走通但绕过 waypoint：日志路径或日志尾可见（证据：evidence/q03/）
- 1 done kill 自己实例上确认过的台面服务进程（pid 30910） → 约 2 秒后截图与起点逐字节相同（237482 bytes），界面无任何变化
- 2 done 不再操作，等约 8 秒再截图 → 台面内容整体消失，中央出现红色左边框卡片「× 服务未响应」，正文「台面服务意外退出（退出码 0）。」，下方有未展开的「▶ 详情」与蓝色「重试」
- 3 done 点击错误卡片上的「重试」 → 错误卡片消失，台面恢复；lsof 确认 18771 上是新进程 pid 36017 顶替了被 kill 的 30910

### J3 想找刚生成的文件的人 · app 在跑但主窗口关着，只剩菜单栏图标 · 不开主窗口就在访达里打开成品目录 — 缺口（medium，无反馈）
走了 3 步，卡在第 2 步：点击菜单项「打开成品目录」 → 菜单收起；desk.log 记 POST /api/outputs/reveal 200；点击后与显式 activate Finder 后各查一次，Finder count windows 都是 0，全屏截图也没有新窗口；config.json 里 outputs_root=/private/tmp/…/outputs，find 遍历确认该目录不存在（证据：evidence/q05/）
- 1 done 点击菜单栏的 LocalModelDesk 状态图标 → 菜单展开：状态：空闲 / 内存 已用 41 / 总 128 GiB（可用 87 GiB）/ 打开窗口 / 打开成品目录 / 设置… / 退出
- 2 stuck 点击菜单项「打开成品目录」 → 菜单收起；desk.log 记 POST /api/outputs/reveal 200；点击后与显式 activate Finder 后各查一次，Finder count windows 都是 0，全屏截图也没有新窗口；config.json 里 outputs_root=/private/tmp/…/outputs，find 遍历确认该目录不存在
- 3 stuck 点击后与显式 activate Finder 后各查一次 Finder 窗口数，并全屏截图 → 两次 count windows 都是 0，全屏截图里没有任何新窗口；config.json 的 outputs_root 目录经 find 确认不存在

### J4 在外接显示器与笔记本屏之间来回的人 · 台面开着，逐档改窗口宽度（900 / 899 两侧 / 1100 两侧 / 1400 之上 / 1920） · 每个宽度下界面都可读可操作 — 缺口（high，系统报错）
走了 6 步，卡在第 4 步：设宽 640（确认范围之内） → readback scroll_width=763 > client_width=640，仍横向溢出；模型行右侧状态文字与下拉箭头被裁在窗口外（证据：evidence/q06/）
- 1 done 逐档设宽 200 / 100 → /window 原样接受、无下限拦截；#pane-chat client_width=0；侧栏把窗口挤满或溢出，顶部大半控件不在画面内
- 2 done 设宽 320 → 「加载/卸载」只剩图标无文字，提示句逐字竖排换行，模型名截成「GL」
- 3 done 设宽 480 → readback scroll_width=763 > client_width=480（元素级横向溢出）；顶部右侧控件被裁出窗口，输入框占位符逐字竖排
- 4 stuck 设宽 640（确认范围之内） → readback scroll_width=763 > client_width=640，仍横向溢出；模型行右侧状态文字与下拉箭头被裁在窗口外
- 5 done 设宽 768 / 900 / 1280 / 1600 / 1920 → 五档 scroll_width 与 client_width 始终相等，不再横向溢出；1920 档布局干净、无裁切
- 6 done 设宽 3840（超出逻辑屏宽两倍） → 原样接受，WKWebView 真按 3840 CSS px 渲染（snapshot 物理 7680×1800）；布局不裂，但侧栏仍固定 248px，右侧大片空白

## 缺口清单（按严重度）
- **high** **缺口** [G1] [F8] 聊天页、状态栏、标签条、会话侧栏、作业视图、助手行这六个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？ — 独立评审官逐张看完 42 张：4 条 finding（1 high / 2 medium / 1 low），28 条基线规则实证通过；另把 1400 档四张与参考图逐像素比对，504 万像素只差 0.33%（证据：evidence/q02/）
- **high** **缺口** [G4] [F5] 一个全新安装（全新数据根、用户什么都没点过）的 LocalModelDesk，对外接口是开着还是关着？服务起来后它有没有真的在某个地址上监听？监听在哪个地址？ — 全新安装、磁盘上还没有 config.json 时，enabled 就是 true、host 就是 0.0.0.0、auth 是 none；换成空闲端口复跑，lsof 实测 `TCP *:18812 (LISTEN)`、listening:true——真的听在所有网卡上（证据：evidence/q08/）
- **high** **缺口** [J4] [F9] J4 走得通吗？ — 确认范围内的 640 档就已经元素级横向溢出（763 > 640）并裁掉模型行右侧；范围外继续恶化；两端都没有任何宽度拦截，100px 与 3840px 都照单全收（证据：evidence/q06/）
- **medium** **缺口** [G2] [F8] 视频页、音乐页、资源页、素材库、设置抽屉这五个面，在 600/640/899/1100/1300/1400/1920 七档窗口宽度下还成立吗？ — 独立评审官逐张看完 35 张：4 条 finding（1 medium / 3 low）。它先判「占位文字用 #a9a9a9 不在基线五色内」，核对冻结参考图后自己撤回——参考图里的占位文字同样是 #a9a9a9，那条规则是令牌枚举不是白名单（证据：evidence/q02/）
- **medium** **缺口** [G3] [F1] 这四个端点在「请求体有问题」时，客户端拿到的是参数错误，还是状态错误 / 未捕获异常？POST /api/llm/load（缺 key）、POST /api/first-run（models_root 传非字符串）、PUT /api/config（配置损坏时传一个非法字段）、POST /api/resources/download（key 不在目录表里） — first-run 传非字符串 models_root → 500 {"code":"internal"} 且把 Python 原始异常消息（含类型名）透传给客户端；config 损坏时 PUT /api/config → 500 config_corrupt，对请求体里的非法字段只字不提；llm/load 缺 key → 404「未找到模型: 」（空串）（证据：evidence/q07/）
- **medium** **缺口** [J1] [F1] J1 走得通吗？ — 收编路径被拒并停在首运页（红色英文错误）；换一条路进得了台面，但 6 个模型全部显示「未下载/不完整」，而那个目录里确实有它们（证据：evidence/q04/）
- **medium** **缺口** [J3] [F9] J3 走得通吗？ — 接口回 200，访达什么都没打开——outputs_root 指向的目录在磁盘上不存在，而 reveal 不核实这一点（证据：evidence/q05/）
- **low** **跑偏** [J2] [F9] J2 走得通吗？ — 错误页写明了原因并给了重试；一次点击回到可用台面且服务被真正重新拉起（新 pid）。但「▶ 详情」始终折着，日志路径这个必经点从未出现（证据：evidence/q03/）

## 无法自证清单（待人工验证，不计为完成也不计为失败）
- **无法自证** [F4] 当加载模型所需的解释器不存在时，POST /api/llm/load 之后会发生什么？状态会走到某个终态吗？GET /api/llm/status 会不会一直停在 loading？台面的重活令牌会不会被永久占住？ — 前提造不出来：dev 模式下 venv_python = Path(sys.executable)，即正在跑服务的解释器本身，必然存在。实测到的是相邻分支（解释器在、mlx_lm 模块没装），而那条分支产品处理得对：5 秒内进入 error/backend_exited 并带 log_tail，60 秒内状态稳定，can_start.llm 全程 ok（令牌已归还）（证据：evidence/q09/）

## 未盘问声明（按风险排序）
- 模型资源：校验、下载续传、删除（F2）— 未盘问，不计入任何完成度 · 未评估风险
- 台面互斥与内存仲裁（F3）— 未盘问，不计入任何完成度 · 未评估风险
- 媒体作业：视频 / 音乐 / 上传 / 取消（F6）— 未盘问，不计入任何完成度 · 未评估风险
- 成品、历史与会话存储（F7）— 未盘问，不计入任何完成度 · 未评估风险
- 打包、安装与环境变量入口（F10）— 未盘问，不计入任何完成度 · 未评估风险
- 取证与测试基础设施（探针、无头 harness、随包发布的 desk.testing）（F11）— 未盘问，不计入任何完成度 · 未评估风险
- 横切：数据生命周期与安全边界（F12）— 未盘问，不计入任何完成度 · 未评估风险
- 横切：失败恢复与重试（F13）— 未盘问，不计入任何完成度 · 未评估风险

## 未拉的线（已发现泄漏点、未实测——续盘从这里接手）
- [F4] 加载模型后 POST /api/llm/chat 真能返回一条完整补全吗（usage/finish_reason 形状与网关契约对得上吗）？ — 泄漏点：本轮禁止加载模型，只证到拒绝路径；成功路径零调用点又无人走
- [F8] 被中断/无内容的回答为什么同时显示「（这条回答没有内容）」和红色错误行？两条说的是同一件事吗？ — 泄漏点：盘问官自测截图里同一条回答下并排出现两行（非取证，仅牌候选）
- [F8] 「已思考 135 秒 + 空内容 + 已达到长度上限」这种回答，用户能看出发生了什么、能重试吗？ — 泄漏点：同上自测截图
- [F5] 服务对每个响应回 HTTP/1.0 且 Server 头暴露 Python 版本（BaseHTTP/0.6 Python/3.14.7），对外网关开着时算不算信息暴露？ — 泄漏点：q01 实测官的 incidental_observations
- [F8] 600×400 下视频页的「生成视频」按钮在视口之外，用户滚得到吗？该面到底能不能滚？ — 泄漏点：评审官：视频/音乐/资源/素材库在 600/640 档内容溢出视口，右侧 8px 空区里一个滑块像素都没有
- [F8] 键盘焦点圈在真 WKWebView 里长什么样（2px 强调色 + 2px 偏移，会话列内侧 4px 够不够）？ — 泄漏点：评审官 could_not 第 1 条：77 张图里没有任何控件处于焦点态
- [F8] 悬停才出现的会话操作键盘能不能拿到（pointer 轴那条规则的另一半）？ — 泄漏点：评审官 could_not：只拍到「平时隐藏」这一半
- [F9] 错误页「▶ 详情」展开后给的是什么？日志路径对不对、点得开吗？ — 泄漏点：J2 实测官未展开该折叠，done_looks_like 的日志路径一条因此未证
- [F9] 服务退出后界面停在旧画面多久才告知？2 秒时逐字节没变，10 秒时已是错误页——中间这段用户在对着一个已死的台面点什么？ — 泄漏点：J2 实测官：kill 后 2 秒截图与起点逐字节相同
- [F9] 外壳错误页的 HTML 没有 lang 属性吗？读回里 locale 从 en-US 变成 zh-CN 正好跨在错误页前后。 — 泄漏点：J2 实测官 incidental：readback 的 locale 与 tab 字段在 kill 前后发生变化
- [F8] 页面级滚动条（资源页/视频页这类 scroll_source=html 的面）在真窗口里到底画成什么样？8px 深色还是系统浅灰？ — 泄漏点：A 组判缺陷、B 组判取证产物；web view 快照不画页面级滚动条，要用整窗 screencapture 重取
- [F8] 视频/音乐页右侧任务列在宽窗下到底吃不吃满余宽？基线那句「右侧空区 ≤ 0px」在 idle 态怎么量？ — 泄漏点：两位评审官对同一条 ends 结论相反，根因是右列没有可见边界
- [F8] 输入框占位文字为什么是 #a9a9a9（UA 默认）而不是令牌色？还有哪些控件漏掉了 ::placeholder？ — 泄漏点：B 组逐像素量出视频/音乐页 placeholder 为 (169,169,169)，不在基线五色内
- [F8] 原生 select 的弹出层在验收里怎么取证？现在它根本不出现在任何截图里。 — 泄漏点：U4 那 7 张与 U3/U5 逐字节相同
- [F8] 状态条右端空区的上限该定多少？基线 ends 写 40%，而用户确认的参考图在 1400 档就是 47.3%。 — 泄漏点：B 组核对参考图后发现 ends 与已确认呈现自相矛盾
- [F8] 状态条左侧那组项与右侧设置按钮之间这么大一块空，本身是不是该重新设计（而不只是调一个上限数字）？ — 泄漏点：A 组量出 1100/1300/1400/1920 四档分别 46.4%/45.2%/49.2%/63.2%，宽窗越拉越空
- [F1] 还有多少条路径会把 Python 原始异常消息透传给客户端？app.py 的兜底 except 是不是该只回一句中性文案？ — 泄漏点：q07 实测：first-run 把 "argument should be a str or an os.PathLike object…" 原样回给了客户端
- [F5] 【安全】全新数据根首次启动时，「开启对外接口」为什么是默认勾上并已尝试监听 0.0.0.0:8770？用户一次都没点过。 — 泄漏点：J1 实测官：进设置面板、未点「保存并应用」就已显示「无法绑定 0.0.0.0:8770——该端口已被占用」，说明它自动试过了
- [F2] 指着一个确实装着模型的目录，为什么 6 个模型全是「未下载/不完整」？是缺 HF 文件清单缓存吗？联网后会自愈吗？ — 泄漏点：J1 实测官：目录里确有 mlx-community/glm-4.7-flash-abliterated-8bit，界面仍标未下载
- [F1] 首运页「收编既有目录树」的占位符写 /path/to/existing/models，而产品要的是它的父目录；失败信息还是英文。 — 泄漏点：J1 实测官：填 llms 目录被拒，错误原文 no known model subtrees (llms, minimax-h3, minimax-music3) under …
- [F2] 资源页在这种「指向了既有目录但清单缺失」的状态下长什么样？badge 是「没下」还是「未知」？ — 泄漏点：J1 实测官没去资源页，oracle 里那一条只能从聊天页下拉间接看到
- [F1] 全新数据根下，原生 NSAlert 首运对话框与网页首运页是两个入口——哪个先出现？会不会互相盖住？ — 泄漏点：J3 实测官看到的是原生「首次设置：模型放在哪？」对话框，J1 实测官看到的是网页首运表单
- [F11] 取证探针在多实例并存时会不会失应答？q08 实测官起的第三个实例，shell 端口正常但探针端口 30 秒无应答。 — 泄漏点：q08 实测官的 could_not：/readback 与 /window 反复超时，只好放弃截图那一步
- [F11] 【取证工具】app 刚起来时不激活到前台，WebContent 子进程就不生成，探针四个端点全超时——取证脚本要不要先激活窗口？ — 泄漏点：J4 与 q08 两个互不相识的实测官都撞上：激活 pid 后探针立刻恢复应答
- [F11] 【取证工具】读回的 orientation 按 width>=height 算，窗口拉窄到 640×768 就报 portrait，而矩阵那一轴只有 landscape——会让窄档截图被校验器判为轴值不符。 — 泄漏点：J4 实测官：宽度≤640 时 readback.orientation 翻成 portrait
- [F9] 窗口该不该有最小宽度？现在 100px 也照单全收，那时连会话侧栏都被裁掉大半。 — 泄漏点：J4 实测官：/window?width=100 无任何拦截
- [F8] 超宽屏（3840 CSS px）下侧栏仍固定 248px、右侧大片空白，宽端是不是也该有布局回应？ — 泄漏点：J4 实测官：3840 档布局不裂但大片未使用空间
- [F4] 打包模式下把 venv_python 指向一个不存在的路径，POST /api/llm/load 会不会永远停在 loading、令牌永不归还？ — 泄漏点：q09 实测官：dev 模式造不出这个前提；代码走向已归档在 q09-09
- [F6] dev 模式下 capabilities.music_runtime.present=false（mlx_minimax_music3 not importable）——打包后的 app 里这一项是什么？能力探测对用户怎么呈现？ — 泄漏点：q09 实测官读 /api/paths 时顺带看到
- [F9] 真正的硬崩溃（段错误/未捕获异常/OOM 被杀）之后，错误页详情里那份日志有没有诊断信息？ — 泄漏点：q10 实测官：本次是 SIGTERM 优雅退出，日志里只有访问日志，这条分支没验到
- [F9] 错误页为什么只指 server-stdout.log，不提同目录更大的 desk.log？出事时该看哪一个？ — 泄漏点：q10 实测官：logs/ 下 desk.log 4216 字节，错误页一次都没提

## 缺陷模式（同类位点清点——未查位点不进任何完成度）

### ? 颜色写成字面量绕开令牌：改一处令牌，抄过去的那些不跟着变，深色一致性没有单一出处 — 共 8 位点：实证 0，未查 8
- **未查** 按钮前景白（[?] 同类嫌疑，未实证）
- **未查** 遮罩黑（[?] 同类嫌疑，未实证）
- **未查** 徽章底色（[?] 同类嫌疑，未实证）
- **未查** 错误卡底色（[?] 同类嫌疑，未实证）
- **未查** 外壳错误页全套配色（[?] 同类嫌疑，未实证）
- **未查** 菜单栏状态行语义色（[?] 同类嫌疑，未实证）
- **未查** 菜单栏图标（[?] 同类嫌疑，未实证）
- **未查** 应用图标（[?] 同类嫌疑，未实证）

### ? 运行时状态检查排在入参校验之前：请求体缺字段/类型不对时，客户端拿到的是状态错误（no_model_loaded / model_not_found / config_corrupt）甚至未捕获异常穿透出的 500 internal，而不是参数错误。15 个受检端点里 7 个如此，5 个顺序正确——不是全局约定，是一半一半 — 共 12 位点：实证 0，未查 12
- **未查** POST /api/llm/chat（[?] 同类嫌疑，未实证）
- **未查** POST /api/llm/chat/stream（[?] 同类嫌疑，未实证）
- **未查** POST /api/llm/load（[?] 同类嫌疑，未实证）
- **未查** POST /api/first-run（[?] 同类嫌疑，未实证）
- **未查** PUT /api/config（[?] 同类嫌疑，未实证）
- **未查** POST /api/config/reset（[?] 同类嫌疑，未实证）
- **未查** POST /api/resources/download（[?] 同类嫌疑，未实证）
- **未查** （反例）POST /api/adopt（[?] 同类嫌疑，未实证）
- **未查** （反例）POST /api/llm/prompt-assist（[?] 同类嫌疑，未实证）
- **未查** （反例）POST /api/media/video（[?] 同类嫌疑，未实证）
- **未查** （反例）POST /api/media/music（[?] 同类嫌疑，未实证）
- **未查** （反例）POST /api/resources/delete（[?] 同类嫌疑，未实证）

### ? 驱动系统/子进程去做一件事之后不核实它是否真的发生：返回值被丢掉、异常被吞、或状态无条件写成成功。11 个位点里 7 个如此、4 个写法正确——不是全局约定，是一半一半 — 共 11 位点：实证 0，未查 11
- **未查** POST /api/outputs/reveal（[?] 同类嫌疑，未实证）
- **未查** 菜单栏「打开成品目录」（Swift 侧）（[?] 同类嫌疑，未实证）
- **未查** POST /api/llm/load（[?] 同类嫌疑，未实证）
- **未查** POST /api/outputs/{name}/reveal（[?] 同类嫌疑，未实证）
- **未查** POST /api/resources/download/cancel（[?] 同类嫌疑，未实证）
- **未查** POST /api/media/cancel（[?] 同类嫌疑，未实证）
- **未查** ServerController.terminateEmbeddedServer 的失败上报（[?] 同类嫌疑，未实证）
- **未查** （反例）POST /api/llm/unload（[?] 同类嫌疑，未实证）
- **未查** （反例）POST /api/resources/download（[?] 同类嫌疑，未实证）
- **未查** （反例）POST /api/media/video 与 /music（[?] 同类嫌疑，未实证）
- **未查** （反例）ServerController.spawnEmbeddedServer（[?] 同类嫌疑，未实证）

## 视觉基线与矩阵覆盖

基线：confirmed · visual/visual-baseline.json · visual/interaction-baseline.json
审查模式：single；文件校验不代替实际看图。
普查官原件：visual/census.json（摘要绑定）
done: 0 · gap: 77 · drift: 0 · unprovable: 0 · not_examined: 402 · not_applicable: 0 · abstracted: 312
独立性假设存疑（该轴的用例出了缺口，被它抽象掉的用例需重展开）：device ← V-bf440d877b399cb06c241bfea170ec8b2ff03e2d9a34f474d6524dfe821a1410, V-a8ed870e59e2928876fe18f9a8b603b871fa6e86251f43b7eec16e9da5f79538, V-bdc1ff7710fdfe0a7c768c8bf936bf5f2637f4f4cbd321b84315e0c214ef8a91, V-0c4f0259fd77b01b7e3beb1ab1d822007290340fa466c71032106c733703a7b1, V-695eaf0fefa9f15254c07667202090cd2534344ee1634f42a68de9012335d242, V-6103ebbceb17ab57a33e34f3ba7a0300be32597c863904ef4c4f759dff7a8994, V-849163a61787a89c6224e6e2f5534f0a963b0579f85a34f743ed319f935fc6cf, V-62ba8758c693f873b71a62d33dac18ff210fab10a77de771ea0d6b928a0e5d7b, V-63ed87a72c68414c2381bef3b577b722980ab7ab7f7da0aee1782e5fdf6162a3, V-7f6a0263e153e685752152688972b42037a7f3941926a3e3102e9915fae48d50, V-99b5e086f2dedf85d4180dacd00bc427c229910b03b2b86fe65adfbe06273368, V-5c2e75ae4907de09e70470f742d54ec01fd41078f540a1d987d5253d83cc9641, V-6b9a200fbfdc15efc317659e5faa8314c85654b38af37b28f2c46f6320e21269, V-807cdb44d2d1ee976a647958518794c5e088b878bf89d511e9ab315e561b3187, V-e366d5842a639b60602163f5c828c60b8e96a11d96cdee6a2f23dd73be658c35, V-901f8775e8dddbf8d2e41c2b8178d9d038f20cc34b2e7846d8e03e4a5538c9be, V-ba66962e322d96961fa2170aec53442c9063d87cc2e92e572a794765fe122939, V-0e72db93d78a722a00dc3f420c19708960804837b3eb0965829fe9d209d60b29, V-4b00c177c3ec97bc63aa5145fc64bf922ff6123c231331610c677fcc549fdeec, V-a7483c13da2ebeb59382ec8c557ff861133d254b0bc628f381ff41022e1afd35, V-8d328f54063214b41918d4ab4b3e64efd92e527c5dc796249e73e599e826da4d, V-43905a857679e23e03d88a5b5a4e736cc4b684361d42895fbcd89e5619fa640e, V-daeb321a307de1179e1385abc3b8440f9a3e6446842f84f2fc12f7ac9ab3c159, V-3805f8fe9bdbd784f131f9dd518a7de7fd218335908e26e54380e299a1b6f0b9, V-c6f93f48c43cb742120e39a9f97aa0f3664a6cf501c8bfc27ce126be1b98a021, V-6a632785ef810be017fdc1b08a16432a785aae692e5579afbaf53ee7eba7e538, V-c257bff9b0564c96fea90994fd80275da04c3ffcc2f3695fbb95dbbdda7778e0, V-031a7070f7b5973cde0df78fbbc5ec655137f47b78d6d6e692f683b078068332, V-b427eb4b4506ecb473814c2c75d14bc2bd2bcce8f59836ca9450c756d4ad0cca, V-7f678dcc5eba6712ce9090b87ab52355b048793dce3f50592aa1f8e003c78509, V-b74d4cfa282bd4aa0cecec0357d8fb59228345d843c35c528b9952e45df3c6ac, V-dd96993ec2b9374c1d205a26e6f715134f06c6b0e0b3680ca80a50507e3a508c, V-8b0af805a8f36671943e4ace1b17b3a3e7dcd5d8a5cef11b7fe3c50185832b7b, V-9b787f7ed94450f68fde0da9af5c49433ca0a2073d00ccbdd76b86384dbad3dd, V-2b642df190e00d877b220436edf1c282f0478d45357efd602710b3338499bc10, V-76ba35b179a56956c180b7accaeafba86413de34db0e942972f09f5f17f2dc0b

- V-85e6f904b5b04d47cad5e0d36f08999fc2cc5f4df126d6d9b4a514ba1d9f8a31 U1 — not_examined · needs_setup 进入 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-532a05a6b75cd6d70fb52a5e4da71d518a32db7367c1dd8b9b1a001c9a14db77 U1 — not_examined · needs_setup 进入 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b4ed3487abe9c8ed53c6f574012b8e567838fefc1c94cf8341855b08902b0e90 U1 — not_examined · needs_setup 进入 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-04ea03ecf68418d05a13a0cc9c187455e8f3af35d0f1eff397363f38d4c4ec9b U1 — not_examined · needs_setup 进入 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c5a4c174a264531f1f7a87b0a0abf834757c509d6e60aa025ebad7253ebfd1b4 U1 — not_examined · needs_setup 进入 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-97da322c023b3c2c2612124928667aa3882e73775c0a2504005a0377c8cd724d U1 — not_examined · needs_setup 进入 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-aa13075afd04f054a1fd7d217c83655e5839382079676ba5259e4c537f3e54cc U1 — not_examined · needs_setup 进入 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-769ddc9c9a6a8b909504c9db58ba0f826dff359ef8c0fe4138e76b0f22bc68e7 U1 — abstracted · 继续使用当前目录卡片（已有可识别模型时才显示） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-855d6a52e0db67e4697fb8b564b8a6cb04d62583e4080594ffe15e910e362689 U1 — abstracted · 继续使用当前目录卡片（已有可识别模型时才显示） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-86d7205b3734d31de81447eecda99520f8cdc51b1dc514a3a862006d9f1cbdb8 U1 — abstracted · 继续使用当前目录卡片（已有可识别模型时才显示） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-20b3a7cbe5aa0e6b29eb51f5d3f82a3a4ecab3cd661562f9b5392225e57d8b03 U1 — abstracted · 继续使用当前目录卡片（已有可识别模型时才显示） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-caea4c3ea794e3f71c08d7b58c555fb8a7df1d0ffc14c1998daa615ffd926bb9 U1 — abstracted · 继续使用当前目录卡片（已有可识别模型时才显示） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d8f60e086a887b7c0b11e0c977365ab5766f788391d30642dff62600936e27f7 U1 — not_examined · 继续使用当前目录卡片（已有可识别模型时才显示） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-781f53fd17a91e0e0e010b7e78438dcbdecfa27182638ceea18489aa606566f3 U1 — abstracted · 继续使用当前目录卡片（已有可识别模型时才显示） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e9248d0eba0777770a002481429f274eaaa79b7a80cfe77b6ceda00a582809a9 U1 — abstracted · 选择 models 目录 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-491801f3f607d66aa1ec47a48d71a14fa0d7ec49cdf01adbcb4592dbc308331d U1 — abstracted · 选择 models 目录 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a2f205dc0bf8a032acf3f6462e10fc5d4653c27089384e76a78c4e35a11eade6 U1 — abstracted · 选择 models 目录 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c9f0e5204bba5afa4120484d2b1766b9de9da4450c4d774ff5fbbf9873336546 U1 — abstracted · 选择 models 目录 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bf3a33e9a7794bbcd302e25fc6ad99f0162dc6146ddae342bca669a2abaa40c9 U1 — abstracted · 选择 models 目录 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b639e6dd6d2e7cfa4675ccf249d2221b6ebed9e1a0b57aabf8be30db33e656c2 U1 — not_examined · 选择 models 目录 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a1d211fa73c0168bd4b14a1c55220909299e0dcd52cf46ec39f4008331f6f647 U1 — abstracted · 选择 models 目录 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-72bd2c58e4ae08bc53b0a9b48c0508f4b491e7cccc8cb0d5b071553a3999e89c U1 — abstracted · 扫描到的候选列表 / 空列表 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-622a79bae3beffb8c85ba0220c743c3cf7a7e6824b4db809a838b74006952bc8 U1 — abstracted · 扫描到的候选列表 / 空列表 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a06a507d43781d1e5f9967264642efb31c04e8bd658b3a6123cf742d179d6185 U1 — abstracted · 扫描到的候选列表 / 空列表 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-dbe4784d5597457cebacb987bea2aff286f4481ea1a6eafedcbb1f656db7cbf5 U1 — abstracted · 扫描到的候选列表 / 空列表 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-aec2c945bc154e1332bd355aa7e61662431b6fe792438208dd8ccdc47fa31758 U1 — abstracted · 扫描到的候选列表 / 空列表 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-292cb7162128fe73466452fe8e3f7b2ce0d292d49b784b4e627c43a6fb39365e U1 — not_examined · 扫描到的候选列表 / 空列表 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5af1546039c2e6d45bc229ef67e4712dfb80a2944d7ec56a1928b140b7062ed9 U1 — abstracted · 扫描到的候选列表 / 空列表 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d70a1affe79bef24599edc2003567d20e49732b1af02d77720033b58164836a7 U1 — abstracted · 收编：指向 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1373651595835f6af2994eb8ab6cf7ed22343d179f9a7664bb53eec541a67f20 U1 — abstracted · 收编：指向 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c5cd371aa81b4a81617f47a2f22ad4c59cdc86f0ee04f34a69228b7f8676ae9e U1 — abstracted · 收编：指向 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a3358a7228479e0096a0ac60661e9c8de1e10f6c98a02d4a98a93dd1b1bf4daf U1 — abstracted · 收编：指向 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5a35b0c2a82f4cc8bf2c8b4882eb8c7b025e4d2a0e40da02c5506ab98fe684b0 U1 — abstracted · 收编：指向 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6441dafd9e33f18fea0e4fbce3965576ee7582e3099fb8cde9ef383738ab2122 U1 — not_examined · 收编：指向 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b72449f4f287ebfdb40386474b81a00a5d865432481eead146f476da9ea62179 U1 — abstracted · 收编：指向 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3348d77f778ea5e4f2e3744a23608b1a86ffa272e08e818dc91983a04e2b9605 U1 — abstracted · 收编：移动 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5362676da6e87bb1685abedaaada47b0ca5230acc2c7f5a42d399fc0bd8c3ba4 U1 — abstracted · 收编：移动 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d65a38c57a9ac0991fdfcef16385934c13ad783cd7b5d83a50c0e352fcb3eb64 U1 — abstracted · 收编：移动 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-096c59ce28601abea81d805b200d5d885a3fbab8e190bf90b3505bde7ff4f4d0 U1 — abstracted · 收编：移动 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-312c231bee9fefcc751185b45f2f889e14275bfb93a548f2dedfbeeeb5807cfa U1 — abstracted · 收编：移动 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-57b008c32270af352d5a67f462d5268bdd8940735854beef8fa06140f4d0953d U1 — not_examined · 收编：移动 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a5025276fefbb32e9417a62e665c83ee8932c74bf53b484b05c7d2f9a0416e70 U1 — abstracted · 收编：移动 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a34e874eec77bb40c8f327ed82fd4ca34367c0087607cfc4bee66353c1d41535 U1 — abstracted · 提交失败内联错误 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5de3e592f9dfcc0cd719716f89e272e0b6990c14f4a77de64b98b4a9c0c60038 U1 — abstracted · 提交失败内联错误 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bd86cec9a49f538423b8c6dc17abb0979e653e105f940421f3d93abf5c101385 U1 — abstracted · 提交失败内联错误 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3f2cc850c277e6540269277be7bf3a2e3cbab6bb2381c30252794d3007ec9e71 U1 — abstracted · 提交失败内联错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6d1914a17484110671eebd4e9580e80e49247c1075678161f3c31a5771f7e8fc U1 — abstracted · 提交失败内联错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-40c5a20a95f4d051096e8ee2f47279c7f76e05c3d96c6ed76a911c5f87f7846f U1 — not_examined · 提交失败内联错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1d13d3f21a5949533936285335e60f53ec69301dece367c693d656ae83e423d1 U1 — abstracted · 提交失败内联错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ece5f115cbbe99f4aeb0c6ef5ded51e42b2b613db936bcf6857501cdda6e8701 U1 — abstracted · scroll-bottom / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-adaa67738cd89c734d2944f39bb19819045888013d3e450f786dca1c21b2ed2a U1 — abstracted · scroll-bottom / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5ebaaaf76c784f40798e997ce3cec859d70ee67ff324337a29e71ca4ddae23e7 U1 — abstracted · scroll-bottom / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0df3e5016f7043410a96a9ee4436917d1c08b848290bffac3c637508eaea7a48 U1 — abstracted · scroll-bottom / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5b610621d59ada8dd8a05a5e8155ae9a1a2f49e59b66d4cf8621dee71fffe7e8 U1 — abstracted · scroll-bottom / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-089fdbed127a5af1c94f4505f0e30f89c1521b0c8582a26c0d9cfd7ba60497f5 U1 — not_examined · scroll-bottom / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-06f6e0ec663afcf25971d4f19d0eb0e3e071cb42b8920bdbdd23a855c788f59f U1 — abstracted · scroll-bottom / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-efd5301f2ae70429b71e0c882ef39102a66c6c848b2a5573dd260fb738cd1f65 U1 — abstracted · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2e6742bbd3f116612a98afce79373a1c588de7f1ff884a9676b750a49fe48dfc U1 — abstracted · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-64d327e80750395b1b2c251ac3866110478e674e6a2c8f81c0bddf257458e821 U1 — abstracted · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c2fc2c2ad0d4ac636eefadfa9f4af7366e1ac4ac9f6ec11d690f1d35aebf5442 U1 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-137e804dd1bf62249878d31b2a5ea79223461702ccdbb70c7bff7af35858375a U1 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2477b97c24c7b6b9b4a98ace6585e038a4ab2beeee489c24e0c05836a75f468b U1 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e7b2aab01ae6447cee8c15a98b771bca7815d653819bda7675c906a0328b4be2 U1 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bf440d877b399cb06c241bfea170ec8b2ff03e2d9a34f474d6524dfe821a1410 U2 — gap · tone=ok / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-a8ed870e59e2928876fe18f9a8b603b871fa6e86251f43b7eec16e9da5f79538 U2 — gap · tone=ok / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-bdc1ff7710fdfe0a7c768c8bf936bf5f2637f4f4cbd321b84315e0c214ef8a91 U2 — gap · tone=ok / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-0c4f0259fd77b01b7e3beb1ab1d822007290340fa466c71032106c733703a7b1 U2 — gap · tone=ok / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-695eaf0fefa9f15254c07667202090cd2534344ee1634f42a68de9012335d242 U2 — gap · tone=ok / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-48276b92ffedaf204847db6ce0acd215a914db6ad7f628afd404e40f9dc249fc U2 — gap · tone=ok / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-6103ebbceb17ab57a33e34f3ba7a0300be32597c863904ef4c4f759dff7a8994 U2 — gap · tone=ok / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-84bcda86f392f78c7da7a792487766f3d36f1ce8facf8f384003916ff43c7216 U2 — abstracted · tone=busy / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d72497564e61d63abcc32449c350fd64320b4e5613b4bd69dd3db9487defcdce U2 — abstracted · tone=busy / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-573cf92f934a01ef5ab3dfb6474ca50491830ad5cb13eb0503e7b759e706e56d U2 — abstracted · tone=busy / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-20d139b3969b6f32129f369b73dd8c28b70af2fc0f033b03fa8de8967e26b07f U2 — abstracted · tone=busy / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2cde029c325e060a09300de70b3ad2481e251892c7b09bfa0d13c9bfcba5b495 U2 — abstracted · tone=busy / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-98c7151e31ec2d332dddef05d628312848e53c298b52d5e3be352a12c2d85fd3 U2 — not_examined · tone=busy / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-945bc509abc342afcdcaa0ffde29555ac63d63d5990ae496da60c8ff62a2c01c U2 — abstracted · tone=busy / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-468e9ba739ca747fdc59a561021a14f8ca8bd798e1e397af118310a10e157b25 U2 — abstracted · tone=error / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-05d357f0ade575d77a8f11a7a399b44731c882917ee2b6db6251653c936e31ae U2 — abstracted · tone=error / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-93d12ddac3a9262f8f2aada69065fd366987b148e0c73f89fd6b460d412a37fc U2 — abstracted · tone=error / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4b3efd0789236788b27e10bdb9de2e4364e5a331bfe998a213fba5995da01410 U2 — abstracted · tone=error / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f1c498ef18a5c472bd6291522e1ed82cdb2cc525f7af76820c1b76b863acc105 U2 — abstracted · tone=error / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-103c967901a9f0e5958a2a82bbb8dd1431937f6bf6d882d52c2f44ad24ad4740 U2 — not_examined · tone=error / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ac37816b8a6c3b36b71905d800288a9d6b77c92eb11eb60c546288e72f540e87 U2 — abstracted · tone=error / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-45ee9f825e784690ce01a3a3596499879936137950a06f765f56082ad5749ff3 U2 — abstracted · offline=1 服务失联 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-10f416e074f5696a3b4f49b3e69d8affddbac6878d2b408596930a5796bcad5b U2 — abstracted · offline=1 服务失联 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f3721870e3674ade56e687edf344a7b9d94a23dc46e0f0cdf26eda5b5fcee051 U2 — abstracted · offline=1 服务失联 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c8a7f204ab42f0dfee11501b46dcc456a2bddd5d3e32f7d5c4ece4671a532286 U2 — abstracted · offline=1 服务失联 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5bedf6902332eecf0bee9cfe578244a0d54bef4ac8571c9f56ccad72cf194003 U2 — abstracted · offline=1 服务失联 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b647f803a40d7acbc63ca5c202fd66e78fdd2e1132a2da5ac90e4a739441ebeb U2 — not_examined · offline=1 服务失联 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-544ee3db4b6fe36a6dbf1a82e52070644c878b4564e4d471579dd6356d74e630 U2 — abstracted · offline=1 服务失联 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-494f9cd24af70d741bd1369fc770220c900325d66eb00430d79f81d621538ad5 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2e1318e6a02dc752315d667213ec1ef3f95952d64d8464694f2edbfd67d83ba6 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-af62ecd57958425ad3b7d6346a87499a20eb9c62a894650303a86318d159139d U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9c28e44dccb2432218e8f5f20e9d96ffc61be87b5e9a265d99abf612540265f5 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ff0b3d974fda28ceee4515fe4b2aaa268e6912633a17fe4eb739631058e4aa38 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-509d998123864f153b8a3dcf3285d2060e4ebdb8f990d928dc7998e574eed0ee U2 — not_examined · holder badge: ok(llm)/busy(媒体)/none(无) / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bbfdd1c38509af7d39279915b397e93714c2a280900a3b0b59279a75a5996f69 U2 — abstracted · holder badge: ok(llm)/busy(媒体)/none(无) / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7e73d6c3b7ee4f38471f8f2ed7b131326c1195c479c25998d3bd8f91fcce9c1b U2 — abstracted · 宽版文案 >1100px / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d765bdcfab89409ac9f261483c441374c65408bc354aaeac522ef4853d0e23eb U2 — abstracted · 宽版文案 >1100px / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-50f8ad0503bf63cab74adb3d85dd65c7faaacda5b95c43c68a5b65290aaa918f U2 — abstracted · 宽版文案 >1100px / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5ae1b675a8c31ba5096f87655e652261fb22d9355badba2815ecc51f2a867f89 U2 — abstracted · 宽版文案 >1100px / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ec737a18b96bc555a3c6d9006cec8d867a51a37aed45a54d1f2c557e49b18ba4 U2 — abstracted · 宽版文案 >1100px / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a2f834d3df3d3245e2b231f133e5bfd3eb06d34949343389cd06b9c18e4af15a U2 — not_examined · 宽版文案 >1100px / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d7968ca6891e8f37d001759d4a8cb13a79d872b7944589d1e9e648b86267fc29 U2 — abstracted · 宽版文案 >1100px / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9bc3892c44cadf8bebc1d34565407078e0fd4280730c6f5f64ad5c04d184869c U2 — abstracted · 窄版文案 ≤1100px / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-98a319589bed5fcec54de7a23b4c6e275add7821392b8b10fc288ebe2050a75e U2 — abstracted · 窄版文案 ≤1100px / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-93b9dfc78656dce83d442588d3f7a3d550a6d036c15da92a6f50cb910da9f66c U2 — abstracted · 窄版文案 ≤1100px / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bf64514ff5c12a5abfe94f1cd410ab11fead540cf5c855d22dc9f9a1c2d8d6ab U2 — abstracted · 窄版文案 ≤1100px / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7e6a54ac94491c65076250936f567c7aa3398ddca7025c15e2e63b0c46c95246 U2 — abstracted · 窄版文案 ≤1100px / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ac9bf4dd6eb74693289e6b4bb67a4bb94c14b8f0dca3f3e86e09a57854fe2af8 U2 — not_examined · 窄版文案 ≤1100px / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a8698c98481166580fe4161d98ac0eb04e317c536560e62475700c7a8e27a527 U2 — abstracted · 窄版文案 ≤1100px / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b9361f0d979f09b9714d3703b97c74fe5927c5cd31c87bcc344f9f85959925a4 U2 — abstracted · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f1ad274876940f3762f7de14ca5ae0e85106c648d333c6468791d85148b5de08 U2 — abstracted · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ec694981b91b2a8f36de4ebc076f9ce4c9499d5383e6dd28cebbc19b58960eb7 U2 — abstracted · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d8c461565f426e9fc4d20df22e2806f671ac0384e3aa565b7f1c2e8d7d770402 U2 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9b376555aaece6be1ecf8d552255efda229fa0e9f96e4992881e156d1cd5262a U2 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-402187151e671fffe193ab3f014286ca53dcf10274b77f8dfe2c55ca38b225ae U2 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4fb9cdef1b313a72e38f04891ec7cf0852feaed1782e40387b17565ba6020b55 U2 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-849163a61787a89c6224e6e2f5534f0a963b0579f85a34f743ed319f935fc6cf U3 — gap · chat/video/music/resources/library 五选一 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-62ba8758c693f873b71a62d33dac18ff210fab10a77de771ea0d6b928a0e5d7b U3 — gap · chat/video/music/resources/library 五选一 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-63ed87a72c68414c2381bef3b577b722980ab7ab7f7da0aee1782e5fdf6162a3 U3 — gap · chat/video/music/resources/library 五选一 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-7f6a0263e153e685752152688972b42037a7f3941926a3e3102e9915fae48d50 U3 — gap · chat/video/music/resources/library 五选一 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-99b5e086f2dedf85d4180dacd00bc427c229910b03b2b86fe65adfbe06273368 U3 — gap · chat/video/music/resources/library 五选一 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-bbeedcc506c53a1cf842f4ace2a07aba6b2104b57d022af750e8539c936a398b U3 — gap · chat/video/music/resources/library 五选一 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-5c2e75ae4907de09e70470f742d54ec01fd41078f540a1d987d5253d83cc9641 U3 — gap · chat/video/music/resources/library 五选一 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-7c56ee28bea89ccf25af2eddfc06b475ccf2faf7f1f60a43fb0ba9291a9c0468 U3 — abstracted · active 下划线 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0a020fd066935e59058df477ac7e4de82ccd036c9cc348fa538a51a9815559ca U3 — abstracted · active 下划线 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cc3c4d967516fc2df54aecd5372f5f53ad625032131a174541a809330941de02 U3 — abstracted · active 下划线 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-09ebd9054c1ca3f04d9615cd228b344aae4d1330070681401fa68bd16fc77d4d U3 — abstracted · active 下划线 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-569d3ff5548fd3c6c07f9832fa446c0ee22a2dc0582e12968ec45ff965edd248 U3 — abstracted · active 下划线 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3fb0f317c196a897031af8d43a74aa82dcd0a86235b870f2be91614c4e4c6a76 U3 — not_examined · active 下划线 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0a1de8acd893f18eaab1f3cc59e710555957dea616607780b74eb344df2e9df3 U3 — abstracted · active 下划线 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a0fb653e271aa0be5944c9cc1b9d491f1a35452b0afa03d99646ea7ad17795f6 U3 — abstracted · hash #tab=… 同步 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8c04b977b606bfdc81cc26cfc889497cd2619963e95f3ad9c96c031ac0b80ad8 U3 — abstracted · hash #tab=… 同步 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7f81be032975178f041432f15120be2fe597998530087e2274b63e36b8ede2c8 U3 — abstracted · hash #tab=… 同步 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0931e2f2a67e734387426fa8887f46a5f3a033b6dd085496dd374ae1b77bc58d U3 — abstracted · hash #tab=… 同步 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f52b383d9a642fac0d39def2b6903e2d3f8f9e4f5be22db23cc2c517e2f51745 U3 — abstracted · hash #tab=… 同步 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-80a9ef52b2410b58059ddb3fc47125dd4cbde33101f99df3ac30432787b94037 U3 — not_examined · hash #tab=… 同步 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-74284f20ba8756a07ff7568b6a49809459f5ea7302c17cd861bdd2db952de260 U3 — abstracted · hash #tab=… 同步 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c4d55d50443158e536f63ad32beeb9d735c28eef594ee83aabbd813c3ca7e076 U3 — abstracted · 白名单外 hash 回落 chat / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4cfd764f0ee090dfe1ae4cfbf1f8d9127a4bcfdb75bca84221bb8beb1ca9a512 U3 — abstracted · 白名单外 hash 回落 chat / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f2a9ad8b45ff79d19576bb3b9e71551780dfd8486d275a981841f14522bad843 U3 — abstracted · 白名单外 hash 回落 chat / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e1810fef907faaa97c211853cc5e476e38714714d4587cde774f81c5c07b9b84 U3 — abstracted · 白名单外 hash 回落 chat / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a7d6d7d60e11fbc02b1ac490b5ba90dfb0b2e1b21a2e32d785cea60c11342931 U3 — abstracted · 白名单外 hash 回落 chat / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e3b57b15788dcc6a0c594d066e770b15d83d84c9042697fa24d7f2861d90d907 U3 — not_examined · 白名单外 hash 回落 chat / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8d9fad42374ada9259941931c73933ab6249a2b4bf67cb78525f54a5b987349d U3 — abstracted · 白名单外 hash 回落 chat / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-fa9c3525fe540d45557aeb24c990a6dd5c9a392d3c7d73ab127ec441c62ce17e U3 — abstracted · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-63b0f33756c8e5cb5c6fd75eee8af9e1c3dc349cba9f2693485b9ab3a9e439a4 U3 — abstracted · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8d2439553c2df381f7e902b6cb73f19684553d9b408cce939e8769ef90f0418f U3 — abstracted · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0526feb1a9e073f856f4886fcaf7562f2bd354ff766e77804b2e380fc8c0b39a U3 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-15b5b8415c75f29d015cd77bae7529f0c0f0f87d44a6d5ac25ca59c9f6a51249 U3 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3b96ce65c5251da3a916e86f20d474f1150807d8ed7260750f7b8923f8f16325 U3 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-dddd327e4b61077091bfc4b0cba0b4a3a01e4f1118ec2068aad5ef5b9a367300 U3 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d81165c39503c245ac4fa278c07dc5deb184a283eb77e5ed27db7a7f251a58ef U4 — gap · 模型下拉：未下载/不完整项 disabled / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-6a820624191768c6c54bb207f98f207e2a17ebce947124dc655dd46c63b21215 U4 — gap · 模型下拉：未下载/不完整项 disabled / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-182ac2a81ce1bd44291392083b2931f85c7a7d8c6196c108142c0512905d2163 U4 — gap · 模型下拉：未下载/不完整项 disabled / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-a8358d5573dba07ad2acf3b915ed7aa73734db4961599286b1df046f64b9bf1a U4 — gap · 模型下拉：未下载/不完整项 disabled / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-d633e9a380b9c3da3a7b2694d0d9421d61144d2f171b2995bd1f067936afddd9 U4 — gap · 模型下拉：未下载/不完整项 disabled / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-13bf2a211e8a7965c9771334d2aad78e7a0a1b15b1548bd131ceb6997266ae7d U4 — gap · 模型下拉：未下载/不完整项 disabled / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-97e5b1a42d26b88b5eb0c3f6f158337212ff1a380e0cb8f72667dcdd5bb75fa9 U4 — gap · 模型下拉：未下载/不完整项 disabled / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-91f87115e83aac53bab56fbc1b3e7e9792dc2e2310971da78a037d4dbeca9664 U4 — not_examined · 未加载 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3cf81a04c20053a05dac34657ce85c80909e8c8abcdef09651b9f0c47b285292 U4 — not_examined · 未加载 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3d2ea67818d330da103e7297274fde62fdf215c7be5ae91128c7f5b51d5676a7 U4 — not_examined · 未加载 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-48a7e9269a7cbc2c03294e0b498b03074a230641a44f31183c400f29ba8820ed U4 — not_examined · 未加载 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9d4194ebd9ef50b383c7b4ba1cd152bc09e6fd2939f7de888e13e7bbd9ca7860 U4 — not_examined · 未加载 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3a2a8618d0f35d24d1b908886209841a55b62e11a3aa5f1c99904fc4a3221747 U4 — not_examined · 未加载 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-caede91cc4429300598c28fc1db9e5dfad604741e65df102f18b2e58ac7632c5 U4 — not_examined · 未加载 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-715230ea9e114ff1c3b6d790e1126ad522a42b9279d17e070818f1a36e3654bc U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-92b668a593b03839aa018bf722bc29d52dc8d1805e7277d5e6eb45049bf8f814 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d2371c76e26d2079bffe0643b0debadb019bdf0e973b78de70a8c562e201010f U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-87d4ae3d6f52df2261bd5cfe7342e0988c45990f5ad70ab226ac5cc085fc2359 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d7e01aa87267981ffc558d3b6b0b0615101d7cb18618ced8e6a159887db19ea6 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-845b01cf7b160623c232cda4fbe7b8d3e0a2369bc5197dbe08ecd901148c6fba U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-988e395ecb240f85a2e4e96f1a412dd7b63885eb68f60fd3fac588738fdacd13 U4 — not_examined · 加载中（卸载按钮变「取消加载」） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bf3a64dbccc98ac810728e5019bb6beaa71fa0b572954f8a10c27713447528d1 U4 — not_examined · 已加载 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-84c86bd3c8070373dd935f3c26929f622aaf0ee9b5e84591b59d8fa178ee8e9a U4 — not_examined · 已加载 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c58889509cdf6b9f8296afc0d1e93447ffb676ed50a7b79a471fcc07d96d11ef U4 — not_examined · 已加载 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-913b21c6eb68d70ff1c3e9f129324b8a95785cb2a999b45e05cc8d379f845212 U4 — not_examined · 已加载 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2a532350987adfe2092db23a15597b5a39bd42b441ccc67d54faa5b05c1697d1 U4 — not_examined · 已加载 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7ec84bfadb43808a9f84fa7a783755386dd89d1515406f29b3815d855d488c37 U4 — not_examined · 已加载 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0d4fca2c799916351cded2304c50ce462de08815e98e68489779d7426b7c5dd5 U4 — not_examined · 已加载 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8f3c86f34982cb61b98703c3b86fa3dad6d4f03e80df8f79826f5d86b229960f U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d057b6721b3cd30ca9feed5b800d527ad83016d9c492b4871f2163bc1b22bce4 U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a48ce6d42bfb196b7b5f2020900bc0fbc38215340e18fb4f232e68bc210ac84e U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-52ec9ad23890d9cdc5c9d8569ce13ccbf48ec0797b64c9e395c53d033a23382f U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1f4c4d8f8a576cb9353fea7fb5a757be0804fbf7948e53ca7cb7538d732da54a U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3e339cbf17c8336ef878f7d1e1a5819e688856bf2e51087922b91e0436be752e U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7fdda6013de1cef4443bfc0753533a08b0442069a5d643c44a5052d05d9d34de U4 — not_examined · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-40259e188eb85b5b3d5109ba5cc376637c28571a6a2c879f987859e631c4e978 U4 — not_examined · 加载失败（log_tail 挂 title） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-46422718c7a5b7bc7f125ede264b2895b0264979f9a42af387d7398e780cadb6 U4 — not_examined · 加载失败（log_tail 挂 title） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-66a3b42f65d645be9be86fed50239cf4ff4c9fa93d9b99f2e6cbf66a7f7eb6d5 U4 — not_examined · 加载失败（log_tail 挂 title） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7be20e89b19264c21f06b25bb3aacec99b6ef8f85bee9a1b62550db7c36928d8 U4 — not_examined · 加载失败（log_tail 挂 title） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1581716aaecebc56f173a4d9611c5353f15f284d7b9f7c18c95f49f6e081a051 U4 — not_examined · 加载失败（log_tail 挂 title） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-95de555ccda2c2de095e25c7e228c6f51cd8d77daaa4d5cdd925d2a53ac28d7c U4 — not_examined · 加载失败（log_tail 挂 title） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9c15bd5edc64308f17c058d9b65d4e1a9150babdebe937a791efb1093bf18a3c U4 — not_examined · 加载失败（log_tail 挂 title） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-93dee5ad253856013bf2753a6ccecfd5b33f0e7926e042f6b340a9f268526f17 U4 — not_examined · 空会话空态 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5b50d10a98e64f5b2869b9d505e87b9773c767b114d22e0c392be747f2861586 U4 — not_examined · 空会话空态 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-edc244b020e0d99f5fb4a3a2a6a5a90fc1386a90d29772af6d097a3e6f097c8e U4 — not_examined · 空会话空态 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5d89e7a85dac86101edf320306a1642635ba1811688011957f601685808e3e2f U4 — not_examined · 空会话空态 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9be335657435247b2fccee0000ba3b568f2f13700e9766d49b83ae3cc5848e8a U4 — not_examined · 空会话空态 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-fa2c44c4d07cdfa8cb435127ff365ec8d523bd894f05bd6026967319a4a43a43 U4 — not_examined · 空会话空态 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b062196529ea0edc794f3443a9685d301d674ca3198e38bcfbee4c0227711dca U4 — not_examined · 空会话空态 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9b593eef0dbac20180fa4f7b71b76d36b8a578b7975eca1096d48e6aa7a6d28c U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-023216a926c6d7e05789fb85e16f3f010b56197b84e0b1a79d090f73b94995a3 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-78a046ca161001b60809afaa7333f4420311c20cd7d218e43cbcd022af267693 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-39dc9c378c80c1170515f0a494c64f28742b67f146384e1311fc0829e65905a8 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3e1cb0b2431aecc946e9683fab13215797454cb9326d07a61b0af0be53fd446e U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-627bf0d86b2c35f478cc61b63c6793b9c2cc5c9838d557a54395784414af5cd0 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-550694f00ff7aa987abb07ae29074e5ecd5b236fa0b425fdff901ad668bd4008 U4 — not_examined · 流式回答中（发送键变「停止」、composer 半透明） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f05ea6b957726ee854f003b76cf7f04b973e78ac789155685782ef5179d16d04 U4 — not_examined · 思考折叠块 已思考 N 秒 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-87f8dec8c35083a535e59c2d89c297dfbdb172aa8e9e684f8f29d4485e8d2b52 U4 — not_examined · 思考折叠块 已思考 N 秒 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8846517688f3ece06b0f929c567d26b96179dc96810f7f178f01cc0a2c341269 U4 — not_examined · 思考折叠块 已思考 N 秒 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ace587ffbdfec68cca89ce9a21f6f2262f2b31b8f32be78f0cfa1a79e07db94f U4 — not_examined · 思考折叠块 已思考 N 秒 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-39b44fe165d9fd85e96eb0d3b6beb82c13585a93a4159943d61f903f61ade513 U4 — not_examined · 思考折叠块 已思考 N 秒 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-be87f700a374ff702d46db92e4063f5883014cd65401a53189dc7d20e0519873 U4 — not_examined · 思考折叠块 已思考 N 秒 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-244f41361928c6a05611c74ba1fe8b41c2af739970c0dc62047572ef529cc7a6 U4 — not_examined · 思考折叠块 已思考 N 秒 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-fcbc5b461ddfb40669f2929ccc42ee27e34cfb1262431b7013a9597549b51c92 U4 — not_examined · 流被中断/被停止/上游错误 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6ec261bd3f590e50eca09c50caf3c1cd85eb0dfe7d230306557b3b5114bd2bff U4 — not_examined · 流被中断/被停止/上游错误 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9f77ac2b46a47b4bdaadef5de8501faad622f227dc2495d34c6933647f7384a8 U4 — not_examined · 流被中断/被停止/上游错误 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a231e3f0e3dc55f7f0f84931b6df7117ec415c54129dc49d38ef2905daffeb93 U4 — not_examined · 流被中断/被停止/上游错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-86cfa04059e7d796f7a8b1d5ff8fbac57258bf20d6595fbf7ceedec34223117b U4 — not_examined · 流被中断/被停止/上游错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3ab81374ee51a4c9ae12baf1c26b509e266f81efe1e0b917d1b32195b88df367 U4 — not_examined · 流被中断/被停止/上游错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e2ed0ee5925dd6007349ab2bd03ac6995bd65590109210688d00107135164b1a U4 — not_examined · 流被中断/被停止/上游错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-30b0a8b1e0399e103bcf9879af0a871a11e89f2026d791918cbffe4ab262ed4f U4 — not_examined · 重试行 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-df2aa35eb3c398fd5515ca5e2a2baa7b231f3cf2b4073b6d946c71d3d00b76b4 U4 — not_examined · 重试行 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ea9c3eaafc6398773a22992376c188485bd119e840d318679145c416afdf0772 U4 — not_examined · 重试行 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e5151eb154ba7adbe77b6d5bd3ff9f93fb6dfd40af3211f1d89a50aa6f7c77f9 U4 — not_examined · 重试行 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4243e11d6a812778641cf4d8b044e3dc7b51f5676c96aae0612fb71144a4879f U4 — not_examined · 重试行 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3fe71851636a9a74ccdfab5805eb6d3e90720869abb3d5945c2b9bca24904985 U4 — not_examined · 重试行 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-361afb2dfeb37e0e1eadc9b51378c1e20ab34a6c9bc8b0b67d605f4f02c46330 U4 — not_examined · 重试行 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8095dbcd819f4bdc67bd098378e353764635bd29831a24ae031b43e049fc6ae1 U4 — not_examined · 内联错误 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c37a86bfd10da28ada34b3906a84e879c0e282a17864678348a2816e318f146f U4 — not_examined · 内联错误 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-58b3bda6519e345a96ca5397bcad22fc8b22f17ad99542cc9ce8c47bc4d83dde U4 — not_examined · 内联错误 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1295dd167d0993ea19f42694f64ae084fc3217b2a666f4cd26ffe40af3e181b3 U4 — not_examined · 内联错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d4aa55fff0525ce74ddc997e1405f278bd18cc1bf6d203de9a9d23e8d3ea03fe U4 — not_examined · 内联错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1837ecb89e9a6faa18dc56fd40853ea6aa049b40d11b21a5439ff2c0dd9f51e9 U4 — not_examined · 内联错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9c31fd40c095964abb540c53096a398b6f876ea66f6c1474de0a3d97cd9b99e3 U4 — not_examined · 内联错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e2f7ba0457c4ffcc1544d3d6853b0d2da8ae90d056e4f359c6203ed2cb3444ed U4 — not_examined · scroll-bottom / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-33fc762b0d82f5e547696a5a26d68a4fa71934a7315c64e9f8445c0207f67f2f U4 — not_examined · scroll-bottom / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-dfcf74848e996d3bf880530983ba7f8c10d08bb4c0d4151f834ace8bb35b4c30 U4 — not_examined · scroll-bottom / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-30da8ea39ab2a326015ee0f731830e2f8ccd249483487bedbbfe85a58a78680b U4 — not_examined · scroll-bottom / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-21656d16762809a28da1f1694ab7f4bb30155bbe76cf77c29d0f315f1e6bda31 U4 — not_examined · scroll-bottom / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9e065867911c6c1f10dad7d5931e1ee5acd9397dad9ea41f92943b1531ee7e61 U4 — not_examined · scroll-bottom / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b47377f08cd932adb2da5f6e3fa7cc7e5de9d7bf8a2df4d7f1fda5df052bb157 U4 — not_examined · scroll-bottom / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-74ba276059cb34b900e5ca5e051146405e5738cc600bf6825452d66a576220a3 U4 — not_examined · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-629d631724dbbbfc54987a683410f7028e5d5abd6fa21ebf690e89c28dd1a5b0 U4 — not_examined · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a84f50de8eb901525d117209c5cfcce727a5b7c69155130c3f24d55bb882e316 U4 — not_examined · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5d3407ad0d70bd4bd7866f6b6355b1d754906857d1f43e0535adca30eabba84d U4 — not_examined · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0b7ef45e84a0a26cd28d1f9ea0d7c2e2e8312f67f43ac2159509b6c811cfa538 U4 — not_examined · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b2da832612102213c2942f933b8de83f32625749d533e80a33ac38d449b3c33f U4 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2e4aeb58f7f1932da19665dc21af42ac33fc95b32a247308abe9c246b5c0044c U4 — not_examined · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6b9a200fbfdc15efc317659e5faa8314c85654b38af37b28f2c46f6320e21269 U5 — gap · 当前会话高亮 aria-current / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-807cdb44d2d1ee976a647958518794c5e088b878bf89d511e9ab315e561b3187 U5 — gap · 当前会话高亮 aria-current / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-e366d5842a639b60602163f5c828c60b8e96a11d96cdee6a2f23dd73be658c35 U5 — gap · 当前会话高亮 aria-current / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-901f8775e8dddbf8d2e41c2b8178d9d038f20cc34b2e7846d8e03e4a5538c9be U5 — gap · 当前会话高亮 aria-current / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-ba66962e322d96961fa2170aec53442c9063d87cc2e92e572a794765fe122939 U5 — gap · 当前会话高亮 aria-current / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-26e6dec31295e2d044bff629ab429a1e7bbc7428cf692a23ce26d4a86a22f2dc U5 — gap · 当前会话高亮 aria-current / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-0e72db93d78a722a00dc3f420c19708960804837b3eb0965829fe9d209d60b29 U5 — gap · 当前会话高亮 aria-current / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-782b63b95fa8469c45e59d4f9ddf2bea7cdb0d66c976554371e4fb97706efac1 U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-81255b65a6c47506b9b4015f9655e223daaba3449634e7d6fe2d15a54d715e5e U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d39dcd1c703c3f18c8344f5dca18daef775b99e42190611af58c532630016f20 U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-270ae9a3a925803856b43b5ec7688cc20ff33f0673ddb3aa00646947dfe11458 U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3e90895c7343a625bec54e9b26b3387720270bf054d863fc470d4ee9a87c410e U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6489b1ad50841f5812356b70f7e2b907b582f627f02b3bdf22e59bf711d22797 U5 — not_examined · hover/focus-within 才露出改名与删除按钮 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5486179092ea0c4bbcf40a59c77a92f3f48a0b429e82ce77adffefbc1013aecf U5 — abstracted · hover/focus-within 才露出改名与删除按钮 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-957da8d5e051fdddad2a6a2ec131c561e409f2ea33d8b9512b748a461bbf4817 U5 — abstracted · 就地改名输入框 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c03e33c4c1345e1c241a82ba9ea22c7e0187375746fb52711f9cfc249b9af059 U5 — abstracted · 就地改名输入框 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d73d30803835ff0333088640f64177424bf85bdbd8e2699ab1696fd8cd5ba78e U5 — abstracted · 就地改名输入框 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9f10b244693f241141cbdfb08204f2a25cddb0bb3371d4734da65a661e3871ae U5 — abstracted · 就地改名输入框 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c7b37ccf15d880bfea74cffb6c9378bb224247884d8bcd22f1aef9fd5df40b32 U5 — abstracted · 就地改名输入框 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-da447aa43bfab3f4afe5c04408c948a954985f4d561a9cb2e7e911e51ae655ec U5 — not_examined · 就地改名输入框 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-44233a0f0490a3c8adcce42e8f809a29166cc67972611f57c893fc64a1541e72 U5 — abstracted · 就地改名输入框 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-96db24aa42cf0264a2c7e2c6d100b454ec93a122d527035ab1bf2bb620f77ecf U5 — abstracted · 删除确认对话框 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3e2936e9ad79102988a2300a3075a08cde38100e90229d0408adcd34b3421263 U5 — abstracted · 删除确认对话框 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e209762b7370e4d787be203dac52d59842bc30cee9bbe0f9837293c1af837b5e U5 — abstracted · 删除确认对话框 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-33f4c6e3d69ce20299f009014991efa3d14b407cb61f83111a62652656a22d14 U5 — abstracted · 删除确认对话框 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a5043c540f25c1700af4f9be51fb2dc3578483540375171fabd85f484db1691a U5 — abstracted · 删除确认对话框 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-02c1ac9f5d75db3c24dd0fe8785b0afe2bcffb89d66c0b5674b8b810fa03042e U5 — not_examined · 删除确认对话框 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6ac8732934b6fe09c803190fdd16eac62833288bbe51480984fa80a0ba342110 U5 — abstracted · 删除确认对话框 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-60122bd3fb536776eb8319d2a7e8bedd943abcc30bc4328e2b9aa8b410c3065e U5 — abstracted · 列表为空时自动建一个会话 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e979a5fc0b9138e1d50cf7de972430d8eb2bae654d436729b02c37a8769356ee U5 — abstracted · 列表为空时自动建一个会话 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ad57413a951e68dc9f51d10300343ce988028c845e931de48a2d5c800f2a37e3 U5 — abstracted · 列表为空时自动建一个会话 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a26482cbb41a293f877572013a3985a47f184873893ac1916965387838f363b9 U5 — abstracted · 列表为空时自动建一个会话 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d2232f0cb96539dcbe7aca49470a4d66ac2d3243a46db3d0517514b80743caeb U5 — abstracted · 列表为空时自动建一个会话 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4761ab8b62b01524ccce265b32fe6f2d3da4a80d8205394429556ea2ba473e0a U5 — not_examined · 列表为空时自动建一个会话 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-476691b36ff740817c5a59166ebf73e0d5a39ada180f4aa08a054038901f0a71 U5 — abstracted · 列表为空时自动建一个会话 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6c5266f52317d5ecd022afa9b701eac8a9df7ba9fd446d98c25b86127aeec928 U5 — abstracted · scroll-bottom / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7ff983ac9a85a8b1a6083a29dbcac78d9ee5a688d5bfa50e49df1fe8aebed20c U5 — abstracted · scroll-bottom / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1b3a8f6694e370b655cf24833a3a3897554bd8f8fd4d6acf3096ffbcfdfdf376 U5 — abstracted · scroll-bottom / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d748006c25f43ea1b3104d279dfb223937a289d4b148f188bef618914a28845d U5 — abstracted · scroll-bottom / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-91d69e1f9b48ccb92e0ab3336203bcbae101cdbb84342ade4fb1f99afec70f07 U5 — abstracted · scroll-bottom / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-eb1fdd1ac938917e2fa66d1e59e5a6566606f19060747bd330d9f036a8ebc40e U5 — not_examined · scroll-bottom / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-957c90ef3a54a3509794229590dc7989056c95e4a31e3e90a858722ad844cc01 U5 — abstracted · scroll-bottom / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1f103280b635e478cf33b7964486d7b519e56c618765ebd78fba0f98379d5f42 U5 — abstracted · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2888ea3a2624e354915f643baf159ccb4e349fe06465bd3ddceed313befd38b4 U5 — abstracted · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-261224115bae189e08e2faf7fc361b27056523711b4a62edd28e29d537f8f87c U5 — abstracted · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8548b243adf17060909ab7eedcfccceaa365600844a15ce363ca62f767a19aae U5 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-dd7da7fd2655d7135fbb86407c46a072d2ea9133cd05ff62d1b51068e6e4fb52 U5 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4a3f207ed68ccc88747f95e03784f5bdf5aa77047abe004cfdc5b188e7edafb6 U5 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-15c38a51697b9c99209ad82f89504dd0a40d06cc379450a32373fad836392794 U5 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6f30160cd65a3cc811cd4efa206d573a8cc261afb0eb5d5f48845fb688fdb994 U6 — gap · 文生视频 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-879a7f78240cbb9b97767c4d75e9146bd847246a99520abeb1cd5810367c2413 U6 — gap · 文生视频 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-ce3cd5c353d2437fee288180e00df8dbbaa1904fba116db04da5c93ded542f46 U6 — gap · 文生视频 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-095564bd113af44e77401d6e22509538430442093876f9ab35addc258f9a18ad U6 — gap · 文生视频 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-e327e755ba80c921a3c1e4e529c19869458e9ef9603ac697f6d21a065b7a3751 U6 — gap · 文生视频 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-6f7e8d164f5642d59a7a0373a3fe1e8abd0ace696a974cd3831e8fe1c5d33de6 U6 — gap · 文生视频 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-f6c47c72c7aa42e3d8672558eeb37fb885b4aeab2a2f16f90c1bede47f9ff49e U6 — gap · 文生视频 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-2d40ece097739cb958c268374cbadc2d4ff9b110e603ef1b992f19731699d28f U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1e73934636be4e1134459f6ae8a0f02c1787ef1a0bd872be23ad2fbdcd3a224c U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4d4320568e2fcc3a8f26ae1fabfb6251079c52d11ff3cd37f87489c93d1f01bf U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6648af972bca0a35beb17cad78706472bf63c4c346abc01b699144a57ad36306 U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b96ba6965e2d66274f656fff8b2aa758f364a72febea54cd8a22f3f65ee940c1 U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-003d5d65ad52a811598332476566de41633b402e58bbaf053abdd36d70f8d63a U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6430c57615c2ba438f5239689dfef839b0c357e302cc3a32508ca37a80957ca9 U6 — not_examined · 图生视频（首帧/尾帧、预览、清除尾帧） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6d58b728665d06662125b97c4cb42442836b5c1dd51e7fef81b69efa86713270 U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-42b11638bcf69ef1092818b3b23f54f59b4ba477dbe1ac8bbe098c67fa353688 U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8851bb2de21b2d58964c5c2e3f77a5b8260712dbade500bec55ed6a17ff1bbf0 U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-10974e86afd5d00370003629d5fea59a7340104106c05b850cf3342ca103ab96 U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b517bf5e2b3442e8edc6ef882f9a72beba35734c708bb9a4d138130f3a890655 U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-03265c26cc00fbe78d94bb558b65ba503c365df88b2430dfd196ca201f9784ad U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-eac76c558ca0866927b5cbe3a61279e06ebc6825503b96479c7931b3c094708e U6 — not_examined · 视频参考生成（参考视频、音轨复选） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-64d01e3ad406752e2b3d21a6237aa6df3ba5a9d8055c2a5cf401b3daad0fac27 U6 — not_examined · 上传中/上传失败 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-513396f4028e22db45412b35a0d1079744ac54d97cb9aee8e02a2fe7fb257e94 U6 — not_examined · 上传中/上传失败 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2de6e36fb3d99b2138c9a595c6c2505e0e50b19299d3ced9b0d373b2bef338d5 U6 — not_examined · 上传中/上传失败 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a8d83210aa99572ecf32a72f34387b611292805908d32c6726ccf80d6ef44add U6 — not_examined · 上传中/上传失败 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ee4bcc08702ba3c710702d188e161de25fbf50abffa2eb29e06f6d4556266f12 U6 — not_examined · 上传中/上传失败 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-26aebb04c885a4e299c33779530abe2dc0ee9bc523db2f53257832b5abfa8404 U6 — not_examined · 上传中/上传失败 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-627dcee23dd27296784812c5fc2b88110aaa1c7b9348b7d6f2a8091d5e203d6b U6 — not_examined · 上传中/上传失败 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8e1a0a107ac3c512049f0765bef7d60b799d9c94bb1910af20eca38c14777358 U6 — not_examined · 画幅与时长下拉、步数 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-39cca1774b478189aa5725f3073f3019354f4ab2dd422ff05363656635b7f645 U6 — not_examined · 画幅与时长下拉、步数 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6802a6e488ca2dd746227c687100bf4dadb51cc13801cf010083dc300c6fd70f U6 — not_examined · 画幅与时长下拉、步数 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d94efb8d47be42fa9caa5707c06354b9e1f7aa25e3d9e862581ffa19da0e0e55 U6 — not_examined · 画幅与时长下拉、步数 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9b778e8b43aef195157a4d884a6a14e7abc887f53caecd054570aebfce9459df U6 — not_examined · 画幅与时长下拉、步数 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6cdce35fedd0290b43a3ad7152adda4b27618665aba36119b2480da4f845c89d U6 — not_examined · 画幅与时长下拉、步数 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b7e82688074890617a97b81f2178d959d86ae8bb64f7220421a69416049f9599 U6 — not_examined · 画幅与时长下拉、步数 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-62b3572c5c791849a4a1f96b74a641398d13b5e5a2c45605e05da81d63ac7665 U6 — not_examined · 成本提示 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3cdd91e4a4c7362d912fb296263947d4fc59395eb2eaf651dcf73c4a6cfa3c9a U6 — not_examined · 成本提示 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-43f755d852a1892d9687482618a42a2dcbda20d1c043c336225471ff06be9e83 U6 — not_examined · 成本提示 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c87d111842040084acd66183a681f135574e82654e352593aee2e4c5c926abac U6 — not_examined · 成本提示 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-563246c7a58332d496135227ee5442ac81d20ad287f9e155955951213619f7ed U6 — not_examined · 成本提示 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-554ab4762c064064615d3954f156fab1eb19c98a24b0c48fafb246d43c0f73b5 U6 — not_examined · 成本提示 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-29e9420d6fab4d8e03fbba43bcb53055a6aec1271d9afba5aeb771a5c0cb65a0 U6 — not_examined · 成本提示 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-edee29228a9b43947bfa0bb993923b1e6455d45e843921d54c0ca7408f3de2e5 U6 — not_examined · 互斥不可开工提示 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-512c629c965bd01c0ddae6b07d4c6b7797c45860bcca9ecc0c757fc17f767ae5 U6 — not_examined · 互斥不可开工提示 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c93d35a1d1049964d83731e89ba7ab47b7ab8f0d76031a21f45a7a22a83abada U6 — not_examined · 互斥不可开工提示 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8bde7dabfb848ed2f7b94a090577de38bbde9571223130739321a371df040532 U6 — not_examined · 互斥不可开工提示 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1cca975b634c9eccb750c2235a65174861576600ddf782b4299ece4ed0b019f9 U6 — not_examined · 互斥不可开工提示 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2bf7866ce75b15e3b618083f1218a96282324b4331e3b816c746d3beda2a4dc4 U6 — not_examined · 互斥不可开工提示 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-04c15bde4c68c7c3c48b83437d5315c0bc9060f43eddb5c27fc7eb4f0cee56a7 U6 — not_examined · 互斥不可开工提示 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d2904f2eeaaccb509f6e5e9726fbbaf59abe85168b77f92b43d9bd38b5efc650 U6 — not_examined · 内联错误 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-18cf276b1496fe192e778cf110ee8f6094fe9ae18575167ae02166898a2767a0 U6 — not_examined · 内联错误 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1582c950c8ed9247f02fcd8689033887cc6378b80c9f1a5fabf2839aa7b2936c U6 — not_examined · 内联错误 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-255a5d9b9ee570b98e1fc1e5c46d7457dbc193ce380ca6afc2139f5060d38061 U6 — not_examined · 内联错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3d3602d22762ac16386ed47ff373e78844574f81eb28a42aba03589843d2e773 U6 — not_examined · 内联错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-88fbd7d415a3f54355d755c90befcbc0a14db3595f3ec85d0d5488c3143a83f5 U6 — not_examined · 内联错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2fab26f8b296e07e5fa5a4ca7ba68b61952d9dbd171241c4546381d31098b361 U6 — not_examined · 内联错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-28e1128854884555c8f3e4f48deabebc67293ae7064d0a103d6922d5b4de893b U6 — not_examined · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-49e3a7134a642f334bcb8c47d221618d236cd7102d3e0fc95b7e78e334b4ea53 U6 — not_examined · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5b40eb64071ba988ecdc4b7bfeae5e40a88bb58a6db464c39f05f94229494dfc U6 — not_examined · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a3784d35b9ad226054460d87d405ac76c3102f79c7659f614df86e754c2db08c U6 — not_examined · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2335e4a3f8b9fb37f49db8dabfb7d5e67adde578619696bf0f8e93cb58487a4d U6 — not_examined · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-92df62277ed32b20efd8c47bdc30084024e970bbd33848ef6d3da29826e70ed2 U6 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-58a9bc09b06c4dd2a692f5d23e7e873737c046496c205885ee4816fc4098f1c5 U6 — not_examined · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-877ecaa7c48666dfa9b3f5c55341e50bb177058fe8c2291354aea70b16c1c55c U7 — gap · 风格描述必填 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-4462dce70218103c9883ecf88a82ea03b0ff5072452d3949402489c00d5051dd U7 — gap · 风格描述必填 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-94e01de60fc7ee41a3736fd90538ee8a83eaa15fcf888d9149798bce9d4014b3 U7 — gap · 风格描述必填 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-9f5733aa3cc5792a5fbec9f78a454f087cbfa71730bb734c37f7a6c8c1682fc7 U7 — gap · 风格描述必填 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-0bfcd763ae7387f0ff78797b830d758e9825d295e9a41e1d7288cd4e16d6f8d3 U7 — gap · 风格描述必填 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-88e214cd1a4ba95f822496d30e38d27f9d568292fa487561ea1b9d01c7a44809 U7 — gap · 风格描述必填 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-cee41dd5163ce1c0a7588453503b7f130a92f8a9ae66dfa863321c258f373622 U7 — gap · 风格描述必填 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-be2dcf4a22ea029f2f27d2b11fdeb090e8372a87cc922f54930ef45002a34035 U7 — not_examined · 歌词必填 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-916cbf6564f2a6bea8aba7a74d332537020f291da58462be9f34c92d5c65bdf7 U7 — not_examined · 歌词必填 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-fdcd081d55e6b371735bf9306877c85572c40e2c7536d06a37fd653ce82ec68e U7 — not_examined · 歌词必填 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9ca9f85b9992bd0e44df3c952df40e42a699cb28f9a368d28f157d4ca52fceb2 U7 — not_examined · 歌词必填 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-11afa4a3a576dff910c2fac2a851edae8b5fd08284953e3f956984324526075d U7 — not_examined · 歌词必填 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-89669fd479ccfced00768e894fc688055336249c463be6104440a64512575f76 U7 — not_examined · 歌词必填 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-147f8f8d4801ae99b47770c79ca4e99fb3fd5f5ba5dea5868d9e9fca21f23046 U7 — not_examined · 歌词必填 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-fb7082b62e1afc1966077017f21054d1cd5693460c620527bd2ac1644fcede2e U7 — not_examined · 时长与实际时长说明 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ee90ae18d67ab09f4f00f089249c355243deb3556c747ee8a87230d3f27237e9 U7 — not_examined · 时长与实际时长说明 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4af79168886fa201c1e6e6f58db50fd58729b07838be3c76955ae9ef60993e5c U7 — not_examined · 时长与实际时长说明 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4703675adbb02335e9615babce8386da11dd381bdb3efe90752fca7df7becc6d U7 — not_examined · 时长与实际时长说明 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c144ff6853b46b098d736ffd0068c2dbc02e3a1854d435ed708fe0b841574d16 U7 — not_examined · 时长与实际时长说明 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b7eeef3b8ac5cd02854c136ee51748df6a1d2a8dd20314c0c6e62bdee59433d5 U7 — not_examined · 时长与实际时长说明 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-aeaa94aeff25b266c2758869d2a8f2298778e7689853f48227d93e63509746c8 U7 — not_examined · 时长与实际时长说明 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-497e4e6e887436776f03b84532108e1318f7cd7cbfce03d2993c1e666515d180 U7 — not_examined · 互斥不可开工提示 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-98ae56390c9dff90bfafcb6b16b27623ab6820a764c2c57ea49440335bb0b9e7 U7 — not_examined · 互斥不可开工提示 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b6a85b850b1d3b0a5ade9691873885b9ffa2807584bdba8a2993dc7c0b299d91 U7 — not_examined · 互斥不可开工提示 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2604f8723a143afefa26b46987ff1c12f18d7a0bfe7f0dd32ec5b84b200d1612 U7 — not_examined · 互斥不可开工提示 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b3c39c5867ef1d6a09637ed033811e143535736cdefedbec62b4cfec96fecd9b U7 — not_examined · 互斥不可开工提示 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4151276e54b2b9ea0af333d9f37f6b318263d2a39a3b68869fab2c362b1c0291 U7 — not_examined · 互斥不可开工提示 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9712d9121c9d3ed67ece576a908e477364d83076e8ca9ce50276170fb48ae681 U7 — not_examined · 互斥不可开工提示 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f944a479305d8c6b8a2e8c54df047557d686bb297c6c8e9d8c39aefaa908448a U7 — not_examined · 内联错误 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1a4cb40a8d547411fb40e66a41a3a3e8b11906c5029ebeb05070120131c4c4ba U7 — not_examined · 内联错误 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-27349120d649b45c8e73aca61010051d46104f71ed1de8aab7a04cf3b3778edf U7 — not_examined · 内联错误 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1cb57447b425ad6a2640f200fe17c7ba74991e780389bbdb70b1905920eb2ac4 U7 — not_examined · 内联错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-13322b343b52f25f137c3704de6bd480b199fc9b98abfdb6cc86104d1b49d785 U7 — not_examined · 内联错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a0d65afed0ead9945ad9b5e6bfa1c919e19f3c5820c64ad428dbfa8786d39d95 U7 — not_examined · 内联错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e5af32272937205d5a8f1d6801942d3576458253cf7ed7a4f5fbadabe5598148 U7 — not_examined · 内联错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ad3e79e20f9af1209600d21f06aa3ba8976d227380af533371564b588c2d8166 U7 — not_examined · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d24229ce08c31dec460453d4bd1795751a4c147d280f61c91137e96dcdc76348 U7 — not_examined · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ff42aadf2da04ec3899f01b79a49b24ca70ee98b7ec57af97092bd9bb7b4fba4 U7 — not_examined · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-40cc450d4f768870bcd0f92b3203416cf550372a848cc71636d6465564a8ea5c U7 — not_examined · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9a9e61dddebef90d7951a01154bf554900fe943b9ca8db344be4a090a8db0d00 U7 — not_examined · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-505e5fc59c1f2a94269a196321a62bf39ca814b07c6731ca6c1c3361a35c6b14 U7 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-fcd2c1c3ed41b9c2a55a0f6e0867c2171dc16d428e0529d1d657f5378ce9a594 U7 — not_examined · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4b00c177c3ec97bc63aa5145fc64bf922ff6123c231331610c677fcc549fdeec U8 — gap · idle（空闲提示或互斥忙原因替换） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-a7483c13da2ebeb59382ec8c557ff861133d254b0bc628f381ff41022e1afd35 U8 — gap · idle（空闲提示或互斥忙原因替换） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-8d328f54063214b41918d4ab4b3e64efd92e527c5dc796249e73e599e826da4d U8 — gap · idle（空闲提示或互斥忙原因替换） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-43905a857679e23e03d88a5b5a4e736cc4b684361d42895fbcd89e5619fa640e U8 — gap · idle（空闲提示或互斥忙原因替换） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-daeb321a307de1179e1385abc3b8440f9a3e6446842f84f2fc12f7ac9ab3c159 U8 — gap · idle（空闲提示或互斥忙原因替换） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-b6c14823b2c4ed2627d354e30f1d9a12b9bf2be9710e0ca1277753a9727a02af U8 — gap · idle（空闲提示或互斥忙原因替换） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-3805f8fe9bdbd784f131f9dd518a7de7fd218335908e26e54380e299a1b6f0b9 U8 — gap · idle（空闲提示或互斥忙原因替换） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-5a746aabca0f61489a15d0aa7462b0d0ce2bde7ff0936a827e3e52ba656fc23c U8 — abstracted · running（已用时长、进度条确定/不确定） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-59e4568bf7c6ab9fb6be1dd1f8928e7c920e8de2ed75568cccf310648f6613df U8 — abstracted · running（已用时长、进度条确定/不确定） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-95e4e1d39142208e2d6478d38c394a7f670fd2f525e7241618643720d8ad8938 U8 — abstracted · running（已用时长、进度条确定/不确定） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c6a0c95c4be63344bf6075463929a9c75795463b10c7e6b3bfa8939d55469918 U8 — abstracted · running（已用时长、进度条确定/不确定） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-90f50e5f0793942abeefc7a4a6706e7f141747555e2c7d581c74c63ef500f500 U8 — abstracted · running（已用时长、进度条确定/不确定） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-fed78845bf7d351dccedef04255c53d5c95ac35f997213e41c4349e0c3fc4aba U8 — not_examined · running（已用时长、进度条确定/不确定） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6ae76918497386b5e3e7fbf46534dc17170cc951513cd043e0e9799c47a7633e U8 — abstracted · running（已用时长、进度条确定/不确定） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e627be6203abb5b12c101610b30c18fe62d82d301d1701ff09d764ad602a11c4 U8 — abstracted · done（耗时 + 就地播放器） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2cf1d5694f7394df2ea9727ebc4d766994ea7875d43cfba41d32d72d25c1a4aa U8 — abstracted · done（耗时 + 就地播放器） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f9c4a237075fded2e19dff238f6600b64c8a6afb64c98bc34b91ac48fa6702e7 U8 — abstracted · done（耗时 + 就地播放器） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cd0783098c7d9cc5d15ed12a612102aa813ac56dc37cb4c181c0e5bb794ea598 U8 — abstracted · done（耗时 + 就地播放器） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-11e8e71a08721fc002af6ac44376f9cffe87454e374468c3da763af3b40f803b U8 — abstracted · done（耗时 + 就地播放器） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1c6e7ce6601f62eceb5910d2a26322d7e9a62f63aee367e9720516a0239a4920 U8 — not_examined · done（耗时 + 就地播放器） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-469de788e323657c5f51d0f4b1d49cde2ce180d6053228e3c97f1462ed1fa385 U8 — abstracted · done（耗时 + 就地播放器） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4b1a14fd527913c0b665b32042c9f0f4ae9ae7f2cb7eb226183046d7181b70ab U8 — abstracted · error（错误卡 + 详情折叠） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-137a4a0e3346a334a96c6911806d34d93433afd0d6204c8244cd68428785c2ab U8 — abstracted · error（错误卡 + 详情折叠） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-062f6a5e9b98061f40b1002b8b58547197f19abee666dbe87b0e9b777e879f75 U8 — abstracted · error（错误卡 + 详情折叠） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ae938a4683fc8f6969112e7d4a59b54ffe61644c219ede11cf9e4ee899210563 U8 — abstracted · error（错误卡 + 详情折叠） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4709da8f6aa33189250d415315192a0375757782a8a8c7dd3ade83b69e5945b6 U8 — abstracted · error（错误卡 + 详情折叠） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-0aa4788792dfa8a9c33dc4bd03854204fa9277afa292e39a718b47135ba0e07a U8 — not_examined · error（错误卡 + 详情折叠） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7d3e43093db35cb06009b2dd755c9bf071bac4f16d1005c44ac8787563eb5f9c U8 — abstracted · error（错误卡 + 详情折叠） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-de579939f36b61bcddb04191e0c9f65036d20e14cb1527421845c55c2a2de5d0 U8 — abstracted · cancelled / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-733a977c612eb56e02324350cf448bbc601cb4d3138c1a94b10ea3ac250d235f U8 — abstracted · cancelled / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5f78d2871b1977c53ef66f6a3ad45f16a2ace55c7b441a55dce60fbd52cc972a U8 — abstracted · cancelled / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-55ea36b9f4badd044dacad970943c3c747cdec15286b3cf65f723cb983aee29b U8 — abstracted · cancelled / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-fec2c6edf8207992ce411df6f70979a3a1faa70474e099fb8626feaadd050bb1 U8 — abstracted · cancelled / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f598d375fef14e75bc5f29a3b509704b591df23be8ec65eb908bfe5bf306cc56 U8 — not_examined · cancelled / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5bb453a3e979429b7abb4c1262c7bd027e58b1c01833d6cf6086e181de16ae05 U8 — abstracted · cancelled / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3a3e41254f9713a9b96f0aacd1ec107052617011a955843d6829dd2bc1869201 U8 — abstracted · 日志折叠区（增量追加/截断） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f6886168e7c90f2b86415cc12d341168ee4f8774ce863f01d1c403f7eb2298e1 U8 — abstracted · 日志折叠区（增量追加/截断） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-577ec6231d193087f6abee73c3075a2246cc79fba0dc9a210f69d218a1266616 U8 — abstracted · 日志折叠区（增量追加/截断） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1d87645222c66ec6aea8a23929d6f8c47eda39890f3177e768e6e1b2514c407e U8 — abstracted · 日志折叠区（增量追加/截断） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3ca4e2b610a52f1190a4fec8bf334457b086f35cd7b0365f6a1014b2760790a8 U8 — abstracted · 日志折叠区（增量追加/截断） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-479454f0562d9a2374c267216709e53fc0fba246250852edc0b5e2f2f3918b6f U8 — not_examined · 日志折叠区（增量追加/截断） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-592532aa7c70be9e25cd8de5cf8d1044785c1e732c6a91f836fd0e78ef74f8cc U8 — abstracted · 日志折叠区（增量追加/截断） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d9b88983c41820410498040380f97ea02fe7a1a558e5d69f02e3ed53464b3e44 U8 — abstracted · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e4163cd0678f8a27463c338726e20781de38a7d591c4dca95420377d5e00fae0 U8 — abstracted · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-314284fb897f9869c1014955dfb432b39df766087ea8769f1a03adc4a0728322 U8 — abstracted · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a6584bced3395f18f165e275f0405c40752a23ca0990e8360a4fc551ca2fbcec U8 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-641a05c5deb5c9c17dd54a3dfe5286847767b5f257dd9de85b55de5e28fe3666 U8 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a1fe3fd5b261b8ea19b77d120e346f2d3fd603a063c48874656e0bb916504922 U8 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5d06590929e3b69d7d9d361a2f7bf8c8449bc16f9dd3dbb59b6a2dec6b38d56e U8 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c6f93f48c43cb742120e39a9f97aa0f3664a6cf501c8bfc27ce126be1b98a021 U9 — gap · 不可用：先加载模型 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-6a632785ef810be017fdc1b08a16432a785aae692e5579afbaf53ee7eba7e538 U9 — gap · 不可用：先加载模型 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-c257bff9b0564c96fea90994fd80275da04c3ffcc2f3695fbb95dbbdda7778e0 U9 — gap · 不可用：先加载模型 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-031a7070f7b5973cde0df78fbbc5ec655137f47b78d6d6e692f683b078068332 U9 — gap · 不可用：先加载模型 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-b427eb4b4506ecb473814c2c75d14bc2bd2bcce8f59836ca9450c756d4ad0cca U9 — gap · 不可用：先加载模型 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-9fa7817509ae316c9228c0b20a0b3158a008e49a912c8a9ee772dddaa7eabfbb U9 — gap · 不可用：先加载模型 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-7f678dcc5eba6712ce9090b87ab52355b048793dce3f50592aa1f8e003c78509 U9 — gap · 不可用：先加载模型 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-1.json'] · 模式：single · 分歧：无 · 降级：无
- V-bc89eb2df4a89ef5090a8c0eafae74bff629aa5ba8231f1002ae2c2018253292 U9 — abstracted · 不可用：媒体作业进行中 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d20559e2e12fc054929204bb1471c9f10dda14ba8b9583c9ad0acf58fb863fb9 U9 — abstracted · 不可用：媒体作业进行中 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-467c2989df627be41141c7c51c5f4fb8c70b3b65c09654ad5b45d4c3967fbe7d U9 — abstracted · 不可用：媒体作业进行中 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-10b916d15b035eba73c2394ec4d08b205305ebb4902463fed138ee78cd8d89ed U9 — abstracted · 不可用：媒体作业进行中 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-58f88ab7f19d1fee23209976bb0900ed578861b65d626d17e24cecd7a541ae1f U9 — abstracted · 不可用：媒体作业进行中 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-18718d0a4e2377c5b7f6d898441d1dde2c0c4d1415bbdcdaecb7c50834c31ee7 U9 — not_examined · 不可用：媒体作业进行中 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-de84c9c485261307f35334daab52b21e5981392123da4ddf303ded2b758b7045 U9 — abstracted · 不可用：媒体作业进行中 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-19102401e0c1430296084777a3cb5ee48a5f1dd2bf2165477e711a9647c1b2f2 U9 — abstracted · 可用 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cc4c5eadc3dcd9163d5fce64565f028bc815f5ca73491a21e320702d078ca516 U9 — abstracted · 可用 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b30e49bb347dbc4d4a50a9fe82226eca3900ebc8b149fb8d35d56bd21e25a631 U9 — abstracted · 可用 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-871a955c21e27ff06130a9a4ad09d0e888d5045a21ea1064800504f5b210ffd0 U9 — abstracted · 可用 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6f1d669e7be329665b4e2d396ff6dcb36dda0cca24d2cca2afaab39df1eb458a U9 — abstracted · 可用 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4e09b35f4a9de1b5c95f3c2fc069f435aa890c1b53a977cc4d7bf5f792238f3d U9 — not_examined · 可用 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9f27401ca865ebbf134e2a16524b83b2376a7e156c2199098c2109813d87ab97 U9 — abstracted · 可用 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9a2c15a9a90171aef0d08f6c64cd036fa2d15a317242ae808da53bb0a8cf8df1 U9 — abstracted · 模型正在写提示词… / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-047cea31626ac9d63a208069e00c0a1d5c4491a87e95d715550f2daae9f14908 U9 — abstracted · 模型正在写提示词… / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1df4b434ee20dde13ff093a3d166db8fe3a6e361b76fae1b1809835b9f0f060d U9 — abstracted · 模型正在写提示词… / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ecd07992378f3d74d95d0e975065fead5ad09a031cafb4b9b50d2e41b20ce569 U9 — abstracted · 模型正在写提示词… / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8a49eaf979344e52905e86dd3ea184f9feaabda0447441165ca04dc0e34ca492 U9 — abstracted · 模型正在写提示词… / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4eba9e244b1a5981077b2b1a3d741f3a311773f7c4e32e5e532cdea7331b94f9 U9 — not_examined · 模型正在写提示词… / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-03bcc69b7a7bbaa547b0408b8dbd35967ac9096e9aa224c7bb5c2cf55fc38fd2 U9 — abstracted · 模型正在写提示词… / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-238997a4bfac44d5e5c157af02e063984a49b148519790bd06387f67d6b55c19 U9 — abstracted · 覆盖前确认对话框 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a80eced37e46bde7b5850e97a4d8a4edbbff7d70726695a740affe22c5c1fa67 U9 — abstracted · 覆盖前确认对话框 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-09e786914d8594cac540b1cbaef713bd76018bb85d69410a4fd32000d8f2130d U9 — abstracted · 覆盖前确认对话框 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-464f0ee8ac5e8323ddfeea76684b4af0f557fe7c92405e64b0497aa866c9a7c2 U9 — abstracted · 覆盖前确认对话框 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-82b9a4bdbd72c57e3c0a801a596c7065e94b2276297c9d84c5150aa651611c94 U9 — abstracted · 覆盖前确认对话框 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8345b2c304306d848cb768709953eda0a9dfe65d78254bff7b62dad0a19be837 U9 — not_examined · 覆盖前确认对话框 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8a40f2c82c1b2f288d5501fb778b4d3a7de57799f3e4ffda8a1af32729ad917c U9 — abstracted · 覆盖前确认对话框 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-25f8a7ebc599d9c53699647b8f8f4f7ec1194bc0f3736020c817d3969b195299 U9 — abstracted · 已优化 + 恢复原文可见 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-25c69e4dc99756124e01ef1f89e9435ed7cb54229fdaacc569d65c5f91044647 U9 — abstracted · 已优化 + 恢复原文可见 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e2c0a1ff74ebb920bb1a6c42fd19f6d2626b267e0abedc3a618e51ae0cf304d1 U9 — abstracted · 已优化 + 恢复原文可见 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c55514a57fc020fc8e5175536515820040ba6ea2ba4ed885c18c07d68075e8e3 U9 — abstracted · 已优化 + 恢复原文可见 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-10d81577b7160dccc8804c7844d97f13fd62b8172960ab493d4c1a823851f557 U9 — abstracted · 已优化 + 恢复原文可见 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4e6055a26a93fadbd3fd048a0e326ac9d357d78aa520dea2e7e14fe4cbd89f65 U9 — not_examined · 已优化 + 恢复原文可见 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-be40878ef4d8502ebfe95c0172ffc847b53c6108b9cbc3bce72a27e61698c0e8 U9 — abstracted · 已优化 + 恢复原文可见 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1aa417629acae799b2db47ecc65258d924dbf11bb8c85e6c01b410c3b2df5965 U9 — abstracted · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-001c9e7a7fc4146a52683b769ef36feda229609150bc0f35451b54c7ddd4807a U9 — abstracted · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-446e2d17c6847b9265e93cc32f0f50229ebde04205eff60af9b6bef1073ef8e4 U9 — abstracted · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5841d29887b06e24795d90f23697d2f24ea12da9afd68f68e8f30c5db92f8d0a U9 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-34e7b1c737e77b7768f448b18b38769f814dad518308d4c0433bf92e503b3d1f U9 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-941e6a5dcb82496e183687cbc831c2c4c1ba92533c4b5cf968e11d16ffdca116 U9 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-61fbab0082d44466eb11ee0b80cd6f1aea0beb83cc2501729c4085e660860a2b U9 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5160df5bb538843f840b521adad44ed9f9b71e4edf58caf0121e667bc86c844b U10 — gap · badge 齐/一半 N%/没下/未知（含拿不到文件清单） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-a309470d8f657874b471f460d79587aa1efa0c5883c095fd704bcc6b846b62d8 U10 — gap · badge 齐/一半 N%/没下/未知（含拿不到文件清单） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-cd53853684bce2c657f919404a80223300050bbc10c6a89c4b3e7bc4741b3e3f U10 — gap · badge 齐/一半 N%/没下/未知（含拿不到文件清单） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-ce522943e3ddda1a26efa0e3d8163ebdbd93ff9f04b457613aec2373d9aabae7 U10 — gap · badge 齐/一半 N%/没下/未知（含拿不到文件清单） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-c061a43fcb4c8a649a2166c0db5fc2a721835340e2e0a3d09893032c0e8ec28e U10 — gap · badge 齐/一半 N%/没下/未知（含拿不到文件清单） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-e991e3ec1eb4e359fc8f0cdc36a52dd61086bdb612efab7036c470c22e7b5058 U10 — gap · badge 齐/一半 N%/没下/未知（含拿不到文件清单） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-61d23f07ac2d2c7b226c5481123db821dc80c219a6e925fc7b0324362f3a6438 U10 — gap · badge 齐/一半 N%/没下/未知（含拿不到文件清单） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-c52ec053a03a7a3c7b7f7022896cbc0b2549e6136a1ef6382afb08ef726e33ce U10 — not_examined · 动作：下载/续传/取消/删除 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9ab9a93f96f099c24361727e1eda8b9dadec342e83f1cc558720db0f5e6b9f10 U10 — not_examined · 动作：下载/续传/取消/删除 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ec6bc1d200896a15455b2962962d483a3a2c65a1e04e74db7c67df984e35b04d U10 — not_examined · 动作：下载/续传/取消/删除 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0bf0564e6c283db424bda477164461a35b320d3eb4bb570775dc2dc089ec037d U10 — not_examined · 动作：下载/续传/取消/删除 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2504f373b0000393d6c853724a2e15d23b595297f410cd0463eae0f0c5a65a12 U10 — not_examined · 动作：下载/续传/取消/删除 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6fd8f0869f7ba46e680677bbf683506deaa20f20061970eebc64bab5a05b6b64 U10 — not_examined · 动作：下载/续传/取消/删除 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-44ec41fd8245d68c1c626e1d8975740f6ba97d9805eb450cbcad8659c68c1ef3 U10 — not_examined · 动作：下载/续传/取消/删除 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-40735beced754c58922429ec71d986605e13ab2b89df95b1e39658798b69fbbd U10 — not_examined · 已有下载在进行时其它行按钮 disabled + 原因 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-08976f7a0c509472fbb054cc6e7e840a4bac8d1375f642477af7ffcd47aa020f U10 — not_examined · 已有下载在进行时其它行按钮 disabled + 原因 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ce09e6ad76c2022f8ad2ec0a1243cc876f0025d81f53a23ea71ebd4cb32c862d U10 — not_examined · 已有下载在进行时其它行按钮 disabled + 原因 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f4a1f2368b001e12845844cfc204037cedf92cce00113089e972bbed75ce8b03 U10 — not_examined · 已有下载在进行时其它行按钮 disabled + 原因 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bb5c5753ff534cc8fc14fc1f25e47693a637c107fab6add171bb1fc576622688 U10 — not_examined · 已有下载在进行时其它行按钮 disabled + 原因 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-df7601639a604c68f98484b3c4609e29eb8eaa249f493c20e9b51b8cef8cec2f U10 — not_examined · 已有下载在进行时其它行按钮 disabled + 原因 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-153d594c0d5d7b5a1c320b90e8978394db7b0a35c88ee09a5dca4580f0ad4f62 U10 — not_examined · 已有下载在进行时其它行按钮 disabled + 原因 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d21a464f824df3ad64f67e0db98d6eb0a8db09861e3535dd5df9135445b8d687 U10 — not_examined · 下载中：已下/总量、速率、剩余、当前文件 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4dde6778c1c165b71e59a36785188867728c60fd8efca2b80692b646b43e32a9 U10 — not_examined · 下载中：已下/总量、速率、剩余、当前文件 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-af869312c02b6d78f2dc59ac237e33346bbc853c26150dbfa161aab31a4df93a U10 — not_examined · 下载中：已下/总量、速率、剩余、当前文件 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d6391b6f57af03aaa4f1b29d78ca4830fded7348aef0dc75d938a615f01ce4fd U10 — not_examined · 下载中：已下/总量、速率、剩余、当前文件 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f7ced3814494222b3a1790e9f324bcb7118fade2a3176d2e7eddaac45beac1b3 U10 — not_examined · 下载中：已下/总量、速率、剩余、当前文件 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ec241e0cbf8d378747c4b65dacc923b83bf81c28fc9b987ef35ce72097a131f9 U10 — not_examined · 下载中：已下/总量、速率、剩余、当前文件 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0478cec3d3009478d058a13389c25643962689b427b5f0904e1b81a8b0d4f05e U10 — not_examined · 下载中：已下/总量、速率、剩余、当前文件 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5b47e5b46399195a2a376de7ff02f6585e3864b00db3e55fefbf8ff484286a26 U10 — not_examined · 残片可续传与旧版残片提示 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ed7bd213348a422e15daf106f1d087635065f34578ba5f79b405e2709834a281 U10 — not_examined · 残片可续传与旧版残片提示 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b457543713dac3e2ccada8f4cd7788acdefd09c88d4458db008939842d6b80cb U10 — not_examined · 残片可续传与旧版残片提示 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-38dbedcc08228810166093b0acbceff81cfd5759b71bb6640945aeb7951b1f51 U10 — not_examined · 残片可续传与旧版残片提示 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f537699b4aa1f35d2212839e83df9e83ba89086a87aed144e0fab5e6dc92faeb U10 — not_examined · 残片可续传与旧版残片提示 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4ebe6604319a64963ca1926756a7446e861fc2c5fd4f853430c84348e48565ed U10 — not_examined · 残片可续传与旧版残片提示 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5552834813c6628b44002ebd14ecd6909044db85637b46e48b46be99d19b2bea U10 — not_examined · 残片可续传与旧版残片提示 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5ee9a920ecf5d87aa152464f790324cd3db55914b1109304cc9ff23ed88fce7c U10 — not_examined · 缺失文件折叠清单 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c709f78242a6ddcd2c523bdcd0a6130c216c8ba00670edfeba04a9682609141b U10 — not_examined · 缺失文件折叠清单 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-455842d4ff89af6440cb59141ee1242ea4142ead50de3c030c19fad9518e7ffb U10 — not_examined · 缺失文件折叠清单 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-976368aabe2dc94f1de1b4384e39b887e25bfe5c8c0bde9b9532b3f038222d54 U10 — not_examined · 缺失文件折叠清单 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-21d85db77ec033b0a75fdf282c3aeb4efc0b613e3bde283fb5accab75105d3f4 U10 — not_examined · 缺失文件折叠清单 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4ab3091ea2ac28b29ebdb8273d9d1607f1190167f342ac1009bb7e4a06b4a5f1 U10 — not_examined · 缺失文件折叠清单 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5bc0b74d1673629e2effad8c41bc567fb427a1ec8080392c03e7418a67867c4a U10 — not_examined · 缺失文件折叠清单 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d6c8e7e9835fc17f03058f5386b0b7c085860c45b13cd3d455de9fbfe90e2708 U10 — not_examined · 磁盘剩余与模型目录行 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-256f971219a89dc9a98792870e16dc0222018ae55d03fdd28f0e1a2992f9bd39 U10 — not_examined · 磁盘剩余与模型目录行 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f88a5569f20b03bb400ef35e4591c6ae194664f0c2ba2a12ebca0a6b5f37e453 U10 — not_examined · 磁盘剩余与模型目录行 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4c51535cba811dbddaad8f5664b9db0521deab95f2000ec36a120e2f6cd26b88 U10 — not_examined · 磁盘剩余与模型目录行 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-171df41a260518b7ecde860b9634c0195d22b7f4d92a68a9b610df9db33bec7e U10 — not_examined · 磁盘剩余与模型目录行 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-264efc881390ce166d103a11bf7cb309e44896c77943cf304227177fe93af471 U10 — not_examined · 磁盘剩余与模型目录行 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5b430e9b320e1d6237224198cdca60c2827b39c888bed1936d039e9c02042af5 U10 — not_examined · 磁盘剩余与模型目录行 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5d2efb2dff7c5d3760be0e34aba11862dbe73f28b948a031a5415de19ec66140 U10 — not_examined · 删除确认对话框 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e3b62e32629da2dc46e0dd90817be75adc477ca56ac54960a4908ae47e650011 U10 — not_examined · 删除确认对话框 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4f35137e8c0670d7540a2a375886d7a0a122782237ca9adfa2e4fb846931aded U10 — not_examined · 删除确认对话框 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5876044446f0f3f309d104bef6418533bb2c2600a28e7ad8dc195e0c2a554df6 U10 — not_examined · 删除确认对话框 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-47ed524dd5a8e9602287aba1c0d0bac5a9b597234ca7f0846b5c11b6c867ecf2 U10 — not_examined · 删除确认对话框 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-db3ead6c3d4613140cc10f4093b2a4933539805c254fa7cc57f61f00f521ac87 U10 — not_examined · 删除确认对话框 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d591d7368047a42acdbd9db7cce574d8a21d041d24909387d5e1eee889156970 U10 — not_examined · 删除确认对话框 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d9e9e6a76ef0a8a43f5d0412088d63789f2011e79953c60b6bb85d02b2ce6005 U10 — not_examined · 内联错误 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e9c7361a8fd999222da8d8b0fb0facc2d297b8c82f66be6684fb99388c4cb5c8 U10 — not_examined · 内联错误 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5565dc35c3e806dfe9e7914d524bf3a392da252cda91e3a648e198df2b4a6fab U10 — not_examined · 内联错误 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3f149f4869606eb038202e84abacc40678c3b933ee2027590938817ad003f6ed U10 — not_examined · 内联错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bc8d7690743511a9ea1c3224e95180c5c5570f7c2a5214e5642d53d99cc2b82d U10 — not_examined · 内联错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9e6c2d76db3ca3199d7e9fe37f4d9ea94f88e32cfa249359ec14df146015a2f2 U10 — not_examined · 内联错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a6959ff47721a79ba1820a9a6cdd2ec35f97731c686fa7da33c516ebf7dbcf60 U10 — not_examined · 内联错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-969d5c9185f1bf6b23101eeb59c0dfb06d59c593957f95afff400886b7ab8633 U10 — not_examined · scroll-bottom / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-23aed32d340aca55010b2c66235d883b088851ec7987e6fb94cfddb6a172cad3 U10 — not_examined · scroll-bottom / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d0a4fdc647a4f969f378db05fa8cd6da1313cb0227de48396519c63c4db576a8 U10 — not_examined · scroll-bottom / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0d54bda19302f78735e388212b825116f514b077ad4f979d4e05288c4ace534d U10 — not_examined · scroll-bottom / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-96df1a6dfbde68f02633bf358bc8de29312bce3e39c4b9a18f2c889cae7774cb U10 — not_examined · scroll-bottom / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e209b6a733b9b4d3d32c9c186834d2cd1d222554a2c6438a0c75eb523e118394 U10 — not_examined · scroll-bottom / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3c707e7feb0868db4b14e71db6838cc80954d48a26fd38ffa894d71ee0611491 U10 — not_examined · scroll-bottom / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-772d42e890f59780bd0d17782d9c5530786493054b0796e12f8c90d27e097959 U10 — not_examined · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-fdcbf9b02bf99c74cc0d4bd0ff9f6c70991201e5cf1dbc4eed5794e821dc46cf U10 — not_examined · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-92d0805d11332f9c4aeed692874bc26c636cd7a3e0170b10317d715c70aa5c31 U10 — not_examined · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ecce48322ad841bb255126a1ee65f03953bcdea89dd005c670e2409770ee56cc U10 — not_examined · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3a9cfb5c99d9f8855d3832d0817947e32b1f802697cc83b2d73ed17c0dd45eec U10 — not_examined · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2aa1c26b616dc69b5460e45f17ca8461368032af82ac8651237da7fec45586e6 U10 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-db14741ed4ae99449dac73c3074b01d1a50dae0b1d667ab372f4c64d056e52c3 U10 — not_examined · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b74d4cfa282bd4aa0cecec0357d8fb59228345d843c35c528b9952e45df3c6ac U11 — gap · 空态 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-dd96993ec2b9374c1d205a26e6f715134f06c6b0e0b3680ca80a50507e3a508c U11 — gap · 空态 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-8b0af805a8f36671943e4ace1b17b3a3e7dcd5d8a5cef11b7fe3c50185832b7b U11 — gap · 空态 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-9b787f7ed94450f68fde0da9af5c49433ca0a2073d00ccbdd76b86384dbad3dd U11 — gap · 空态 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-2b642df190e00d877b220436edf1c282f0478d45357efd602710b3338499bc10 U11 — gap · 空态 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-b48600db8f49f068cb324e350bbe6a85ad696a9ad19d0f7d793731d30142e2bb U11 — gap · 空态 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-76ba35b179a56956c180b7accaeafba86413de34db0e942972f09f5f17f2dc0b U11 — gap · 空态 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-e8f604204e6461a27e0c45fb0ce9a3d0dc6c476644c81152dc999cedba78f34e U11 — abstracted · 成品+历史按时间倒序合并 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7b1201af2fd4f8d440a7fd74b439859f0560ed065de480052c30f8bcd03b71f9 U11 — abstracted · 成品+历史按时间倒序合并 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c8e3e9395cbaec52fc21597d49507c72debb188796e564662037b6cdf36f0412 U11 — abstracted · 成品+历史按时间倒序合并 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6bf69a79d8db6684a192c392cf9c10951cfb1f533554c9a04a0655568eff36cb U11 — abstracted · 成品+历史按时间倒序合并 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1e578308738675f356c908f56f03cdbe176550bd694f5f6cca96ee001421b486 U11 — abstracted · 成品+历史按时间倒序合并 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c91d9282f3d4f305fafd1387983c2dc4551f6d28c33b33b6a45bd4bb7a432c7d U11 — not_examined · 成品+历史按时间倒序合并 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4274d6806c0a222090b903621c2c978855b9bf0fc6430b0054105ffe7efc4c13 U11 — abstracted · 成品+历史按时间倒序合并 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-db67530552ab037ea2ade904db9f799d890ba4c476865174ca71afeb31ae4358 U11 — abstracted · 完成/失败/已取消 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c3859d62ea6834146a02560e603dcf74936191952f5c1d63825e41c34c560a14 U11 — abstracted · 完成/失败/已取消 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cf40fa9f325711b9e2a59badf48f4d638e4df55aed9fe0a7307d3a9cce653e4a U11 — abstracted · 完成/失败/已取消 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ee4347868ac84140fe59bfcf1610bc68049478f31ae6e09c8684ec8db03c2e0d U11 — abstracted · 完成/失败/已取消 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-51d54eaef207d20ffec07303f6370dd283b4423db30dca1a307918e89af02877 U11 — abstracted · 完成/失败/已取消 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8994db61202a8a3cbf925f086d0ede00a1539c8b5a9f4ae9a61766dc78345c01 U11 — not_examined · 完成/失败/已取消 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-570e1d2826d70b0f7b6610524180f2fa78245e093de58f34dc0726f99c62ee23 U11 — abstracted · 完成/失败/已取消 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-09a0c1175037d4b680ff332090c63d1080ff1ac46e90893289ee3b4aa4c23a11 U11 — abstracted · 就地播放（video/audio） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-5cc52d4d7d9279e2bdb61ea851eb7be4074c81326bf93e60c273f952ccb03f1c U11 — abstracted · 就地播放（video/audio） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2611f44f802cb5ba8674ec05fed78c1b3727dc77150dca11e45d842a5f076bb8 U11 — abstracted · 就地播放（video/audio） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3f2f4dce495be077caf7d6c02b54ee356e4c2c4d9c4455fa68bc99144497af8d U11 — abstracted · 就地播放（video/audio） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3250e1112678705a21c9e6849860060b3d28ecf1c6ae47fdcc754d31b62cbe96 U11 — abstracted · 就地播放（video/audio） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3c78fc53fdcd4a424d44cb52e3c2692a115e72cbb0ddace661a01ec52c12c9e2 U11 — not_examined · 就地播放（video/audio） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2faeb567af17838cbbe9e909de2673e95d80f00833aa18f833dce708c3cbdca7 U11 — abstracted · 就地播放（video/audio） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4c2322b69139622b09fcdb681f7397e1a0366afd25a7108bc306652961642512 U11 — abstracted · 在访达显示 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-45b4f815ccf530cbae0a27def3eccb15c9c2294574aa4c694611b33fa2d9ab6b U11 — abstracted · 在访达显示 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-32923beda3d2803f4172339d8b93bb8539fa1f09cd134b1053c298108d1bdae3 U11 — abstracted · 在访达显示 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a847ac1f4a5509cf49bd6138023f7fa5207ba4b9bb3010e87e08ef687e2052fb U11 — abstracted · 在访达显示 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-779ff5e182d29a996900be9ca04931cdb8fdf222daeca4004d2d9006aa2e1b68 U11 — abstracted · 在访达显示 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d178a8e6f8329f8250980391ebe91fb14b482baf7bf798b774bb3f91e01d0e8f U11 — not_examined · 在访达显示 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bb518931a533b310155f2c6ad8c09f93dca2da4494ba4a52bbe414bb783ccce4 U11 — abstracted · 在访达显示 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-13b8b9b4566ffb43d5d1c246faea8b3133119ec1c2b86424316c78484df8192a U11 — abstracted · 回填到视频/音乐表单 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-28286d4cdd4854cabaaaca9f6aac9c2ea35fbe465a57e520d1dbfeb0e7b85545 U11 — abstracted · 回填到视频/音乐表单 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-fc3792e55254bcbe5c8edd077d14843a15941c201531710078307f0bab4b1045 U11 — abstracted · 回填到视频/音乐表单 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f0b80473094303a5a4e50cf3e26400d40bb21f812299681b4738ed0ba3106324 U11 — abstracted · 回填到视频/音乐表单 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a0a75e101d91ac9527302eb2dae4e3bfbd652456f7f222f3011fc5896fc2932c U11 — abstracted · 回填到视频/音乐表单 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-fb63cec9e13b5406eafecf2eeced9438f12ca445e05daf8ad2186f81d1a5ac04 U11 — not_examined · 回填到视频/音乐表单 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7f69c077c6041f734ee0da566fa8406ac474f7eef355a11926bef7b4a469cbd1 U11 — abstracted · 回填到视频/音乐表单 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7639f2bf68076b563ba1813479fd74e8551fd2ba8957289e8b90d774d2632ff9 U11 — abstracted · 错误卡 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-af3d4e3cc5aec9f6ed7be5d808e55a17775a56f3bbd9aea02453bcd488a2351a U11 — abstracted · 错误卡 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b3d59ea09596000ce7698d1d931029559f09467326be5508d921a517b60e45ff U11 — abstracted · 错误卡 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e14e90784c36f516b01a6c89ec519a42322728971956670c4b4553a8301b1a6f U11 — abstracted · 错误卡 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b961a9d05d0243cd672322d8fab13a582336eeb947b873a0e5a873eeeeb1c20b U11 — abstracted · 错误卡 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-af2cfa41552f610e8b37151e8d5b33c328f7ae7ff19d6bf06cf30a5a5ab18554 U11 — not_examined · 错误卡 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-eb0b96c9702c0f864628c3520af3fe7b7844440fa3335a55f830139926cc8e14 U11 — abstracted · 错误卡 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cbce3abdb9519c5c537fefffe7bb97542fef892d3e2f33592130bc5ecf5d3627 U11 — abstracted · scroll-bottom / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-eaf1a3849a730521c1bebe3b9030a3daba46510eb561dc273383a603915c1bf7 U11 — abstracted · scroll-bottom / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-860740f0b87f5ee4fb626504623c404d7973d64b38cefe3f7a0a5976fe495851 U11 — abstracted · scroll-bottom / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-313024d9cf12130b6fe162f8da92c0348ed1be127a4b65905c757de8b18baf09 U11 — abstracted · scroll-bottom / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-627d4014d4c8cce02dddc4f274d1d7b0d73484f2b8eef45ed0b65266c87f41db U11 — abstracted · scroll-bottom / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-56561a74c6c425db1060005d20b74913869a68b476ed45aea9bec2c7641164ad U11 — not_examined · scroll-bottom / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4e5c430f69a8f177a5f4005c8a8694815c44546350e7236fcb37f0d2f0baebeb U11 — abstracted · scroll-bottom / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b80fe59b0177b42a34cdc7cf29c9b436b543a2036904b849683b19e2b35f049a U11 — abstracted · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f526cb6a0d90af56a6be79ca675a09326b52690ea4d7b704e866d3ff79a54378 U11 — abstracted · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4c3ff12c3384d3c4ca3cf03d6dd0dcd7972085a372f1d504935eff80a6fa519c U11 — abstracted · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-44ef066b50fa861c0faedaae5a0c78bf5bfa54c3ce116bdbda47dff4fb513225 U11 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-abe67dd1dab337b1f86715f218fb30b88d812611f415d5565ef47b15ea053d25 U11 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a788defb765f47a1368a1ef4110ce5ff0ee1103704d2179d583c455690b36965 U11 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a7780e312af1a217ca41257b5b2f20ce8530bb63153d632a6d77ba1462629de4 U11 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9dc1c6518d6e6c952fc6ad4cb150e133921d5594624e81d31f674e6fb282127d U12 — gap · 打开（body.drawer-open + 背景遮罩） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-a30c48b52abb66eaa9224a944a0123ae09d42ea0810b654c32db0c55ab41fea9 U12 — gap · 打开（body.drawer-open + 背景遮罩） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-7b7cde0f1d1a3cc763454de501edbda4fa10ab2bf6848009b75347b2927b234a U12 — gap · 打开（body.drawer-open + 背景遮罩） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-05c8cda5be6a1ea0d3c397f12f58811a51696602a35ab95114372c0c5b0a657e U12 — gap · 打开（body.drawer-open + 背景遮罩） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-995b2830213ad19589cffc2314510c363dfecfe318c058eb47344941414594f5 U12 — gap · 打开（body.drawer-open + 背景遮罩） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-e5bbb093723c0811885082ad2a87d9966612bf18755917b9d1301879e23b9757 U12 — gap · 打开（body.drawer-open + 背景遮罩） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-15ea9f86a68bf700e2c10ce1f7371e390d684933513a347ee47f38cce5b41e52 U12 — gap · 打开（body.drawer-open + 背景遮罩） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
  证据：q02/screenshot-manifest.json · reviewers：['q02/visual-review-2.json'] · 模式：single · 分歧：无 · 降级：无
- V-e5363d087a1c753aebe6f2956d2d8b2924217bee4d5731d4381bf9a83c31c576 U12 — not_examined · Esc 关闭 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d77350f3693ce3f76239d766a37c42c9100b8f473364625a4d62649df6aa89b2 U12 — not_examined · Esc 关闭 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-397d394000bf0f5551a3fe1730f0fea696760610ad44b27927d589cfcbfbeff0 U12 — not_examined · Esc 关闭 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-22bebe058cce553504807e5a163fddcecef935b639363a5f155633ef5ec3cb80 U12 — not_examined · Esc 关闭 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5d7a5e91bf3a641a2f213636631236a4a11bb7c51da16866d891cf429d1ce043 U12 — not_examined · Esc 关闭 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-15887366100933f6a02293aca4bc88f649fe59454849dc9c5d848e6a3a9e04a9 U12 — not_examined · Esc 关闭 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5b4ec8c1ffffb56cff209ea07bb88214830a54cfa36e771fefb52fe1c12f3759 U12 — not_examined · Esc 关闭 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-48abb063839a22903a3a247faa49980dedaed161d08a5970f28d254d5699c271 U12 — not_examined · 模型目录：使用此目录 / 自动扫描本机 / 重新设置模型目录… / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c54223d5a754ed3c839415f5fd56630390c84383afb531549ff273480fc728cb U12 — not_examined · 模型目录：使用此目录 / 自动扫描本机 / 重新设置模型目录… / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-28b6f9c41381b093467ebaf08659546347141622704dc647b7c39c52131d5076 U12 — not_examined · 模型目录：使用此目录 / 自动扫描本机 / 重新设置模型目录… / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1e81b297b39975536c49662945815e2db1e561d16e13676f7de14849ddc0dee5 U12 — not_examined · 模型目录：使用此目录 / 自动扫描本机 / 重新设置模型目录… / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bab19dd0877937b5272d4a4d53e59e8ff4e05afc30652d6352772aaa8b282117 U12 — not_examined · 模型目录：使用此目录 / 自动扫描本机 / 重新设置模型目录… / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ea49dc3487c3e8edde4b6e28b881f472c956a4b9df3bbd63a27439453b034e2c U12 — not_examined · 模型目录：使用此目录 / 自动扫描本机 / 重新设置模型目录… / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-174b3ec774683904994cb6c7864c9157076783cd5d0db4b32c88da864b3d15dc U12 — not_examined · 模型目录：使用此目录 / 自动扫描本机 / 重新设置模型目录… / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-40fc33d41951c3798d19cac1de34afd02dbc80e9fd4806ee8366462b5314371a U12 — not_examined · 对外 API 开关、主机、端口 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b5599aa0862cd30b8ba641f7b1f8badb23c2d1f90fb24a17d0f4569390bb9571 U12 — not_examined · 对外 API 开关、主机、端口 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-725265a9e267cdd09f8a167abf3985067e51504ab8e9f40d3be75d9b31e6e7e3 U12 — not_examined · 对外 API 开关、主机、端口 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-72d7934a67ac7fe5eff1a604bfa1bfd376104bc3d81a1b029d7c6795451ce8ce U12 — not_examined · 对外 API 开关、主机、端口 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4aee050f7650d3f23670959f36360814940a0a5ad6ad59fd1e80fa06527ad4ea U12 — not_examined · 对外 API 开关、主机、端口 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4bac1f5a9fa448d7188fa09080deba12987ed9508eb57bd06e32fd0f46ff0ae5 U12 — not_examined · 对外 API 开关、主机、端口 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3c86cab1d3ad8ff79e5ff4afe23d7d829d6c062935907796b275028bf8334f7e U12 — not_examined · 对外 API 开关、主机、端口 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f8fbede694e64efd2aee42c159ee476568e4418387bb3f0545f5f994c9888b3c U12 — not_examined · listening 徽章 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-7a2bb9d748d1da0b41a08d7ea4946b645bd06da4cbde184a6d67de374a565aa6 U12 — not_examined · listening 徽章 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-82b9c7e7bf6b20d68630618bac8a1a8b56682f8f5cd419cd05a2e542607c10bf U12 — not_examined · listening 徽章 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bde14e0546178b782064e58dc98b78d3339e5e575b5020977749bd04071ece68 U12 — not_examined · listening 徽章 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5c5046d696435328068b9204e409b0922d430b51ac79c8194b17bcf1cf9fa3f7 U12 — not_examined · listening 徽章 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e82d8c7c951a1de6e82b467574f46f082f97b5e59a044146a336bb332631f429 U12 — not_examined · listening 徽章 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d11a6de023f34f16586e3cf0c9e562732416afc07fa944a25dc3ace69d0a9ad0 U12 — not_examined · listening 徽章 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2d86528c4f9265e3f0c72d777364d0535e38f3f37c5ae3b3932954b2de6ceb66 U12 — not_examined · 无鉴权告警 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-429ace9a781b7caebd06225bc1418416e846278023fec5a94fc30e1a876683f9 U12 — not_examined · 无鉴权告警 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-57c670c8019803c75954dcbe60f0440cb9b2c35ca2f3d2c6882e84b9bc324361 U12 — not_examined · 无鉴权告警 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3d1d3ddd627faf48655021d00782674e729613eed39772ece51625e22552fd00 U12 — not_examined · 无鉴权告警 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-c07b3d1f131e87129f5ae7128b3d99ee7e26de3e36003bf36e2b5e46adf0de27 U12 — not_examined · 无鉴权告警 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-21a7d52a9cacd687239d9e0e38a4535bad85f8fdebdc52680f735bad75220fa0 U12 — not_examined · 无鉴权告警 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1b3ffd94d1264169bc68a00ea2ca39d9118fac4a048484d74f8e8049223a887b U12 — not_examined · 无鉴权告警 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a353704b9efc6a83566a4cc7cbe6fd52ab601c996ba8c6e53e283959b0cfd414 U12 — not_examined · OpenAI / Anthropic base URL 与复制按钮（仅 listening 时显示） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8a5e2bbcbe03c885f59593b2bfa05b35979952fb3c419fb16bff3bfe1752fa4e U12 — not_examined · OpenAI / Anthropic base URL 与复制按钮（仅 listening 时显示） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a24c80d2e9f25ef8f0393de7d88162ccbd58f864bbf029db9bc0acf6389cc159 U12 — not_examined · OpenAI / Anthropic base URL 与复制按钮（仅 listening 时显示） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-511a85cfe2e88a15e755ca8b9da3e7604656092bede40bfba6ff2561849c15c6 U12 — not_examined · OpenAI / Anthropic base URL 与复制按钮（仅 listening 时显示） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-618eccd1d15a0cea6a3517bc0c9bc85b1c914fdcdfe592ec8c5f57659daf9c8c U12 — not_examined · OpenAI / Anthropic base URL 与复制按钮（仅 listening 时显示） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-50e700fe7693ffc243972000744aa01384f9d75205d41f635ebadc978fbdb2be U12 — not_examined · OpenAI / Anthropic base URL 与复制按钮（仅 listening 时显示） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0c2c9585632bb9c4340ed38a791ebb05437ef798d6e60cffae4c930ceb93f689 U12 — not_examined · OpenAI / Anthropic base URL 与复制按钮（仅 listening 时显示） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e0c5bbdb0ec3cc73ba907d6301726ea548fee4224440a7b8773ddd5d5ae48ac8 U12 — not_examined · LAN 候选地址说明 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-66b3b6d4073990cd6c631c23f464506a3ff4412192b82e6f385bae291e12ce78 U12 — not_examined · LAN 候选地址说明 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4b7f52c88243fe843fee40beb454bc7b8d640ef9c38c467c395bf99a5c217186 U12 — not_examined · LAN 候选地址说明 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-4580ff067f79cbf529d38cdd2ab467fa1b31a89018882bb6bb0c419c4d4cacb0 U12 — not_examined · LAN 候选地址说明 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e1ee538b37bf9bbd20e9235a3114ae1f9a119968e22d841dc4ed378c4b7decfd U12 — not_examined · LAN 候选地址说明 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1418363b62f7e6c6985afddb725d15158ee3480a897a82b4b9d82bb4b4723053 U12 — not_examined · LAN 候选地址说明 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0a7ccab2ebb292b065581efd96a548105b9e19ff89719b484e2825a59ac23689 U12 — not_examined · LAN 候选地址说明 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-31f3c5fa4df2133fa0ccd86dab7fde59037a17a4cf8ef4533dfe2bf18ea9601d U12 — not_examined · 绑定失败 apply_error 与回滚 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0db5804a6730eae671ed000bd218b702a1dbcc784bf36ea8fb48c4fe33a39229 U12 — not_examined · 绑定失败 apply_error 与回滚 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d1486fc1181eb81e4f2fcb7b23a1be09ec4f493115f731d82866deafecc5a89c U12 — not_examined · 绑定失败 apply_error 与回滚 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-b02dbe9bcab81c46ea606c059e7f02fcc8ddc9b0db1504400565a2240be944b7 U12 — not_examined · 绑定失败 apply_error 与回滚 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-04085ed5a2249cf64056220c8b5b64895111862d04a0d10388ab8a190f631de9 U12 — not_examined · 绑定失败 apply_error 与回滚 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-0c67c712e26c612a1b267686444ec054bd9135728b6eab53bf4a23aa02c00abd U12 — not_examined · 绑定失败 apply_error 与回滚 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-14841cb8f368cc0d75e4280da6c5946d49cd2896da342b17e913fe49d34fc61d U12 — not_examined · 绑定失败 apply_error 与回滚 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-909be0399c6f16709b3383dd35274c534850473f479359a351888805af321711 U12 — not_examined · 内联错误 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d287ae53ea7749b841e51aead7a4e9cbb4f2af4b8c447c44d006518d10d992f1 U12 — not_examined · 内联错误 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ef7ebf87c8b3c6cc25b903dfd2fcd65825105991a77e69698058977e4f12dcd9 U12 — not_examined · 内联错误 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e41030a9e73ca4f6daf5b8345222f2a7ee3fc7bb568462c3dde030c215a9ea6c U12 — not_examined · 内联错误 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d2969e878145dc979f42c2f7e04b1f8b9b34031f4048708c04f65c9e55981601 U12 — not_examined · 内联错误 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-a6071dde403eeb9b6ebda77afe915e63e631e903fc1f006ea7204387e03a7c73 U12 — not_examined · 内联错误 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5bd7ec1e6bf9041fe8fd8655882eb87f513ff2fddf4bb06d0c8c4845ac19580a U12 — not_examined · 内联错误 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e4a541ae2e35ac34946a4b0f18ea3ce09ec32f9c7609b0daa5a6862dd7f170c8 U12 — not_examined · scroll-bottom / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9f0e0dd9ab54238746153c9d690f5b394f6b1437afbfafd34963549a48b4b8d7 U12 — not_examined · scroll-bottom / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2a53a3b996938476237066e2e07442b8a1229d9fe03d2d7c762d604a7696d95a U12 — not_examined · scroll-bottom / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3ffcd19c8e3d88d8aa7842755d795cb6e80e790810b82a93be7ff8c1dc157179 U12 — not_examined · scroll-bottom / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-866606642b65cd34fc6baa34c5bba1aca20a0967b4aa312f202401497285eb8c U12 — not_examined · scroll-bottom / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6793826954ca0f0e93505dc2904ae99152562e098a26c121fd437bfbcbcdb533 U12 — not_examined · scroll-bottom / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9ca8fafeeaa6334528119dd38baac7a85e567e8a0f7c2413f292972f9daf0cd5 U12 — not_examined · scroll-bottom / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3f27e784c39daa5d4e146432f39bf751f7b1e87cda1780750ce0a20b051d8257 U12 — not_examined · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-db1206bbbeebaaf88897223c6f0775d8dce7f5bece06b278e84b89e59b2e00f8 U12 — not_examined · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-61d9aef74efea6dcf0fa88bb84180e0b870ca5dedb68b7e0f943ed819ebc71ba U12 — not_examined · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8df6c6feac709acfcfdc3dcb87d0d49d48ae9996424e4582e245ed6223aa2f7a U12 — not_examined · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9e5c89972e6d00dbd70e83214ba0346bb5d4cc09abfba9be61b435216501921a U12 — not_examined · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-66b6059ad98b0f6c0330a7754711262b0a853eaa0fbb3bf634a4c83a0f023997 U12 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-595e5197bf80610c71e6f47bc3f170d78919feec8ab94c5ec7edfb6f726f4d87 U12 — not_examined · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-5f72d4978e53bb05e69e129e9838d3990371de75b3d250999310c53264875835 U13 — not_examined · danger（删除模型/删除会话） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-9ed8bcad3e6e69bc1abd57fd4b7e281ff4ddccf43ea216485e560cd486c0db96 U13 — not_examined · danger（删除模型/删除会话） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6a14bf0ed0f78332d2e24867816762b0eff11765b450281abaaa7289dc3cd674 U13 — not_examined · danger（删除模型/删除会话） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-861cc08fea95c87e418334ad9b2df0f89c408c3873e3ebec0ca02f85ff478e91 U13 — not_examined · danger（删除模型/删除会话） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-d604d7a596cfafe22ebe29981cebe236faf7221ee8ac60f9f9c0d57be0de532c U13 — not_examined · danger（删除模型/删除会话） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-2ce47d6325b2ac18f03e484f8b00be0ae8523bc9d9ca7950cd377102c1f559a8 U13 — not_examined · danger（删除模型/删除会话） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e725d7c72058d637faa15a7dabf6a2146e8a41cc41abc89d1b2442902c6c0c8b U13 — not_examined · danger（删除模型/删除会话） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-ead14e8844f4cb81a72285a75d71efe538038ab63d53f35ba6951ee054b50385 U13 — abstracted · 非 danger（换模型/内存警告/看手气替换） / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-28b97fa1f04cb53d8e2999c91b133977b5043ea20eefe750a26fd5c1a9542821 U13 — abstracted · 非 danger（换模型/内存警告/看手气替换） / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e745d00b7ea797e057af16286a782c360f923a7e07b136874f4c8b14aaa17243 U13 — abstracted · 非 danger（换模型/内存警告/看手气替换） / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4c7bd1dc681a343ee5ecd2f2583d2c71e975430ba5f1c84e33d74254e8b767ad U13 — abstracted · 非 danger（换模型/内存警告/看手气替换） / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-2d34de8e65e211654b71e61a1abcc89b4eed4689152c8cc349b7b4cd613738f7 U13 — abstracted · 非 danger（换模型/内存警告/看手气替换） / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e4bbdfa0bbb9c713f1f5fbc1f0b5a5e43ab6cd5a6559e48e9fd994b2638396ad U13 — not_examined · 非 danger（换模型/内存警告/看手气替换） / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-1adbe777b1fc84547e3267b64a58d081ddd332c7b9924ed9572d167e0e8e7b45 U13 — abstracted · 非 danger（换模型/内存警告/看手气替换） / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-e9e6d953b8910e838c573d52c6c62e5618d0af233bfcb39954a66495988f6249 U13 — abstracted · 点遮罩取消 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c33c8a1004fa82ff8c249e0bac33b0a1ac9fcd57696981486da9fe90595b679a U13 — abstracted · 点遮罩取消 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9d9e3eb27f62dfe2856f719d0cd1b955e7ba24b82ac2ff201ccd85da4a0b8b5e U13 — abstracted · 点遮罩取消 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c46fbccc0df994074e55acc0a5601e8fc3c5b1118c8fe9e7cc629e510b1211ff U13 — abstracted · 点遮罩取消 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-15f1832507a8ebf720be7c1a50880fb87e9d7e6caf0cdd6b1f72406c531c3732 U13 — abstracted · 点遮罩取消 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-21b256130f8c5e3c7a5eb737cb5814f9c40ee109142e71911750423ac2669d37 U13 — not_examined · 点遮罩取消 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-97134ba09be788c1fa24fb8d1fc4e5b88e7f73e2ed4eb1d6c4c09ac877422223 U13 — abstracted · 点遮罩取消 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-df67197894516745a76b49f77746a1f155ad8b3ba2cb7cf21ee97c759b1fd749 U13 — abstracted · Esc 取消 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b99532ba68998119f3cf798784e936d2654e2fb2c5dabd3ce4a81d2d9f1cf553 U13 — abstracted · Esc 取消 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-544a2be08c9e638e54ad0bd63bd797fba384b1c43f6cef81fd7706beb59dc3b6 U13 — abstracted · Esc 取消 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6a46c52d5121d4c8ad8e91a9c0cd9a9db6e518573ead89a167f32050087b6311 U13 — abstracted · Esc 取消 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-41a29c31a098a487dc1eb32146273486a4b06fdc5cb1dd5e2bb96ce9a3201ccb U13 — abstracted · Esc 取消 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-dbff8d25abb25cdd5bcbf1072eacb93b4ad345b60158bebc7027f41f38f79df6 U13 — not_examined · Esc 取消 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-3e2ec34418aa41d2a93619498e054d50d74288fb4f47555e851819b25d9fbbd7 U13 — abstracted · Esc 取消 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-bdca50f625f622623de92ce85661ac32f9c740970c04e2c6c8bd617d525c7286 U13 — abstracted · 破坏性对话框不响应回车默认确认 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-4044ed3325ba41b23080e0fc1a2796103bc9d8be73b2d0fafce5269a94ccaa67 U13 — abstracted · 破坏性对话框不响应回车默认确认 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3ca3b37638e3ec8b80720731109ac89867982cfa920fe7f567f7e05da7c66c98 U13 — abstracted · 破坏性对话框不响应回车默认确认 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cbb8ca9c4c6d42b93f8d4c3c02a284098df49d66a613ae96401a8757c3e3d889 U13 — abstracted · 破坏性对话框不响应回车默认确认 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1bf8764e135fe9d9e747fcec281f404ca3bfa5c97b314f91fe564eada565220b U13 — abstracted · 破坏性对话框不响应回车默认确认 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ec08330403aeae6dac80eaaea0c48c88232d2825a813d36a0fe95aaf9c19018b U13 — not_examined · 破坏性对话框不响应回车默认确认 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-13972f5a1e27c306d6e98c1e6359ac083767a5d51446652a485e3cb2cb8519b6 U13 — abstracted · 破坏性对话框不响应回车默认确认 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-f40c283dceb2ff5ebff12b76c53f355e98ba86a45490017db1e5e21bd44052b7 U13 — abstracted · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-3b3805891f5b571523a9b2340e22f62e02592475d93a03c05f4f6ad02c95a2b8 U13 — abstracted · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-a847893edd4fc306544905c718882b2b934e99ed9174c74c26653d0bc4b09dba U13 — abstracted · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-674790a2814a16e50009befe212b58ba0a7a0056d8d3024c1a69cf0dfb29477a U13 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-d9cd9bca5f1a14824b1a46a156abb108dff840296ed21541a61524caa8266173 U13 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c454b0c66ef1333863a32bfb8ee9e5f6db024b773d24bdf972f7cc4b4d443d11 U13 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-bf3f23f7d718e35042ead31c91334444068ac9cd634ab003b9d54f11e6918287 U13 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-6096cf9edf012027acf16de326afbe4ad7e4af3bd976b7fe27b34a210a7bb04f U14 — not_examined · 读配置失败 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-412ab35671733262b5afcc8273edef3fe60914cbf4be13674e9f6d16ed66f8c0 U14 — not_examined · 读配置失败 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e5aa19461b7f77d0ada9091337386a058948f82cc6a9aa2688e92701ca8653ed U14 — not_examined · 读配置失败 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-50edc3b0021098ce2d85d6efe3cc7b1a3f627e2359834bcf70048ba98fd03b45 U14 — not_examined · 读配置失败 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-f443b47468133e04adfecd8c838b2c1786dc678c94848b2dbb55964025902435 U14 — not_examined · 读配置失败 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-8d24a9c424f40fdc0049409b0ce931c7f329cd2b9856496f647f793197494ea3 U14 — not_examined · 读配置失败 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-57e5a56a8470c1beb4c6ce8e7efe3373fcd42aa7444cc2967a3bd2cdee227ee3 U14 — not_examined · 读配置失败 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-e1816fbfb04d1e581c0e05054730617be6f4689012dc3427c8e749086a196e7f U14 — abstracted · config_corrupt 时显示「重新设置」按钮 / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-9ffc487799ef06d3b16b8cbfe9ac0691ab9233959a2ed13616795ce9843eccbb U14 — abstracted · config_corrupt 时显示「重新设置」按钮 / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-cbf66acd80f94822b9487e0d23a03c80ad1e06b269070a6bd5b469a14156fd0b U14 — abstracted · config_corrupt 时显示「重新设置」按钮 / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-739a3ccf506f54d211201dae93fe53023f396def918f6ffc5a8cf544cd4450c1 U14 — abstracted · config_corrupt 时显示「重新设置」按钮 / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-44c688795da2580e15a08968f027a0ae03a239fa726fd22d49a8c42ec7dbb357 U14 — abstracted · config_corrupt 时显示「重新设置」按钮 / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-8b6edfe419b7550afdb6122c627005c0f960be9f3e14f1c98db2818d1400c8fe U14 — not_examined · config_corrupt 时显示「重新设置」按钮 / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-46be73fd9643cb89baecfdb1526940d3a0ca45a4e6ddfbe3136b500380bc6235 U14 — abstracted · config_corrupt 时显示「重新设置」按钮 / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7accef48fdfdfd724b0ad59a2c15c5bda2f408cdfc5dac6f7040b420a6af8785 U14 — abstracted · resize-drag / 600x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-c5071d21f1b0c397a1183bed387eaab24f6c81eb09a9bf25dff688704e0734a7 U14 — abstracted · resize-drag / 640x400@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-ab033c23fcae37223d6e2efa1b3bf642bdb96e8c5cdb0c7f45070a41f1e4282f U14 — abstracted · resize-drag / 899x600@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-b4ecb18946a696f4824f94633a098e18bc55f77ee482b6ba4c1d08182ad23f48 U14 — abstracted · resize-drag / 1100x700@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-7b72211f90846072ef315e93a8ef58c7417b8ef2b6024d29d275d772ad3a9751 U14 — abstracted · resize-drag / 1300x800@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开
- V-1df99c18b97912ebf90d81ce85506b87fa50e39cc84c1b803b2817f60699468d U14 — not_examined · resize-drag / 1400x900@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse
- V-6b48aea8e190fd5fdda8e772c18bbb91651049f6450ebc436edc00f1412715b8 U14 — abstracted · resize-drag / 1920x1080@2 / macOS 26.0 WKWebView / dark / 浏览器缩放 100% / zh-CN / landscape / mouse · 已抽象（device），独立性存疑，需重展开

逐轴覆盖（已抽象与不适用不计）：
- state：Esc 关闭 0/7 · Esc 取消 0/1 · LAN 候选地址说明 0/7 · OpenAI / Anthropic base URL 与复制按钮（仅 listening 时显示） 0/7 · active 下划线 0/1 · badge 齐/一半 N%/没下/未知（含拿不到文件清单） 7/7 · cancelled 0/1 · chat/video/music/resources/library 五选一 7/7 · config_corrupt 时显示「重新设置」按钮 0/1 · danger（删除模型/删除会话） 0/7 · done（耗时 + 就地播放器） 0/1 · error（错误卡 + 详情折叠） 0/1 · hash #tab=… 同步 0/1 · holder badge: ok(llm)/busy(媒体)/none(无) 0/1 · hover/focus-within 才露出改名与删除按钮 0/1 · idle（空闲提示或互斥忙原因替换） 7/7 · listening 徽章 0/7 · needs_setup 进入 0/7 · offline=1 服务失联 0/1 · resize-drag 0/44 · running（已用时长、进度条确定/不确定） 0/1 · scroll-bottom 0/24 · tone=busy 0/1 · tone=error 0/1 · tone=ok 7/7 · 上传中/上传失败 0/7 · 下载中：已下/总量、速率、剩余、当前文件 0/7 · 不可用：先加载模型 7/7 · 不可用：媒体作业进行中 0/1 · 互斥不可开工提示 0/14 · 内联错误 0/35 · 列表为空时自动建一个会话 0/1 · 删除确认对话框 0/8 · 加载中（卸载按钮变「取消加载」） 0/7 · 加载失败（log_tail 挂 title） 0/7 · 动作：下载/续传/取消/删除 0/7 · 可用 0/1 · 回填到视频/音乐表单 0/1 · 图生视频（首帧/尾帧、预览、清除尾帧） 0/7 · 在访达显示 0/1 · 完成/失败/已取消 0/1 · 宽版文案 >1100px 0/1 · 对外 API 开关、主机、端口 0/7 · 就地播放（video/audio） 0/1 · 就地改名输入框 0/1 · 已优化 + 恢复原文可见 0/1 · 已加载 0/7 · 已有下载在进行时其它行按钮 disabled + 原因 0/7 · 当前会话高亮 aria-current 7/7 · 思考折叠块 已思考 N 秒 0/7 · 成品+历史按时间倒序合并 0/1 · 成本提示 0/7 · 打开（body.drawer-open + 背景遮罩） 7/7 · 扫描到的候选列表 / 空列表 0/1 · 提交失败内联错误 0/1 · 收编：指向 0/1 · 收编：移动 0/1 · 文生视频 7/7 · 无鉴权告警 0/7 · 日志折叠区（增量追加/截断） 0/1 · 时长与实际时长说明 0/7 · 未加载 0/7 · 模型下拉：未下载/不完整项 disabled 7/7 · 模型正在写提示词… 0/1 · 模型目录：使用此目录 / 自动扫描本机 / 重新设置模型目录… 0/7 · 歌词必填 0/7 · 残片可续传与旧版残片提示 0/7 · 流式回答中（发送键变「停止」、composer 半透明） 0/7 · 流被中断/被停止/上游错误 0/7 · 点遮罩取消 0/1 · 画幅与时长下拉、步数 0/7 · 白名单外 hash 回落 chat 0/1 · 破坏性对话框不响应回车默认确认 0/1 · 磁盘剩余与模型目录行 0/7 · 空会话空态 0/7 · 空态 7/7 · 窄版文案 ≤1100px 0/1 · 绑定失败 apply_error 与回滚 0/7 · 继续使用当前目录卡片（已有可识别模型时才显示） 0/1 · 缺失文件折叠清单 0/7 · 被媒体让出内存（evicted，媒体在忙/已结束两种文案） 0/7 · 覆盖前确认对话框 0/1 · 视频参考生成（参考视频、音轨复选） 0/7 · 读配置失败 0/7 · 选择 models 目录 0/1 · 重试行 0/7 · 错误卡 0/1 · 非 danger（换模型/内存警告/看手气替换） 0/1 · 风格描述必填 7/7
- device：1100x700@2 11/61 · 1300x800@2 11/61 · 1400x900@2 11/113 · 1920x1080@2 11/61 · 600x400@2 11/61 · 640x400@2 11/61 · 899x600@2 11/61
- os：macOS 26.0 WKWebView 77/479
- appearance：dark 77/479
- dynamic_type：浏览器缩放 100% 77/479
- locale：zh-CN 77/479
- orientation：landscape 77/479
- pointer：mouse 77/479
