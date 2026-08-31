# 模块设计：shell

**日期** 2026-08-31
**对应 spec** `docs/superpowers/specs/2026-08-31-shell-spec.md`
**覆盖需求** R-shell-01 … R-shell-08
**消费（数据形状补充声明，Phase 1.2 对齐）** spec 消费清单之外，本设计还消费 `data:memorySnapshot`
（`api:memorySnapshot` 载荷，菜单内存行）。

## 架构

shell 是一个纯 Swift/AppKit 的 macOS App 外壳，编译产物即 `LocalModelDesk.app/Contents/MacOS/LocalModelDesk`。
它自己**不包含任何业务逻辑**：模型、作业、配置全部住在内嵌 Python 服务里；shell 只负责四件事：

1. **服务生命周期**：从 `Contents/Resources/` 启动内嵌服务、健康检查、退出时确定性收割（R-shell-01/04）。
2. **窗口与激活策略**：一个承载 `ui:deskShell` 的 WKWebView 主窗口；关窗不退（R-shell-03/05）。
3. **菜单栏**：NSStatusItem 实时显示台面状态（R-shell-02），数据只来自 `data:deskState`。
4. **原生首运流程**：`api:readConfig` 报 needs-setup 时，用 NSOpenPanel + NSAlert 驱动目录选择/收编，
   落到 `api:completeFirstRun` / `api:adoptLegacyModels`（R-shell-07）。

### 与内嵌服务的边界（唯一进程间契约）

```
LocalModelDesk (Swift, 前台 App)
   │ spawn: <Resources>/python/bin/python3.13 -s -m desk   ← packaging §1.3 冻结的环境契约（-s：禁用用户 site-packages）
   │        env PYTHONPATH=<Resources>:<Resources>/pylibs/desk
   │ HTTP : http://127.0.0.1:8766          ← 台面接口（唯一数据通道）
   ▼
desk 服务 (Python, 子进程)
   └─ 自己管理 mlx-lm(:8767)、媒体子进程——它们全部跑同一个内嵌解释器（packaging §1.3），
      这正是退出时 shell 按解释器路径收割全家的依据（见 terminate 流程）
```

- shell 启动服务的方式是按 **packaging 设计 §1.3 的运行期环境契约**执行内嵌解释器：
  可执行文件 `<Resources>/python/bin/python3.13`，参数 `-s -m desk`，
  环境 `PYTHONPATH=<Resources>:<Resources>/pylibs/desk`（三个字符串常量全部只住在 `DeskPaths.swift`）。
  「内嵌运行时是否存在」的判据 = `<Resources>/bundle.json`（packaging §1.4 的 bundle 标记，
  foundation 判定运行形态用的同一个文件——不另造第二个标记）。
  Swift 源码里因此**只出现 `Bundle.main.resourceURL` 相对路径**，没有任何 home/checkout 路径（R-shell-01，消 A10）。
- shell 与服务之间只走 HTTP（127.0.0.1:8766）。shell 不 import Python、不读服务的内部文件。
- 退出契约：shell 对子进程 TERM→KILL 后，**按内嵌解释器路径收割整个嵌入进程家族**
  （mlx-lm、H3、Music 子进程都跑 `<Resources>/python/bin/python3.13`，media 还用了
  `start_new_session=True`，它们不会随 desk 进程自动死），随后**验证 8766 与 8767 均无监听**。
  机制细节见 ServerController terminate 流程与 Assumptions A-5。

### 开发模式（无 bundle 时）

沿用 foundation 的原则「靠 bundle 标记判断，不靠 if-dev 分支」：
`<Resources>/bundle.json` 不存在 ⇒ shell 进入 **attach-only** 模式——健康检查 8766，
已有服务就直接挂上；没有就显示错误页提示开发者手动 `python -m desk`（foundation §3.1 的 dev 入口）。
这样开发路径完全不需要在 Swift 里写 checkout 路径（R-shell-01 在开发态也成立）。

### 文件布局

```
macos/
  main.swift                  # 入口：NSApplication、AppDelegate、SIGTERM/SIGINT 处理
  AppDelegate.swift           # 生命周期编排（启动→健康→首运→加载 UI；退出→收割）
  DeskPaths.swift             # Swift 侧唯一的路径/端口常量点（见 Assumptions）
  DeskAPI.swift               # 唯一的 HTTP 客户端：路由字符串全部集中于此
  ServerController.swift      # api:spawnEmbeddedServer / api:terminateEmbeddedServer（无 AppKit 依赖）
  PortGuard.swift             # 端口监听探测 + TERM→KILL 收割（无 AppKit 依赖）
  ShellStatus.swift           # data:shellStatus 模型 + deskState→菜单文案的纯映射函数
  StatusItemController.swift  # ui:menuBarItem
  MainWindowController.swift  # ui:mainWindow（WKWebView + 错误页）
  FirstRunFlow.swift          # R-shell-07 原生首运编排
  ModelsDirectoryChooser.swift# api:chooseModelsDirectory（NSOpenPanel 封装）
  harness/ShellHarness.swift  # 仅测试脚本编译的 headless CLI（不进 App 产物）
scripts/
  shell-lifecycle-test.sh     # 编译 harness 并跑生命周期场景（被 pytest 调用）
tests/
  test_shell_static.py        # Swift 源码静态断言 + swiftc -parse
  test_shell_lifecycle.py     # 用假服务验证 spawn/health/terminate/收割
```

## 组件

### 1. ServerController —— `api:spawnEmbeddedServer` / `api:terminateEmbeddedServer`

**职责** 内嵌服务的启动、健康等待、终止与端口收割。刻意做成无 AppKit 依赖的类，
以便 harness 在 headless 下驱动同一份代码。

**接口（Swift）**

```swift
struct ServerLaunchCommand {       // packaging §1.3 契约的 Swift 形状
  var executableURL: URL           // App 内 = <Resources>/python/bin/python3.13
  var arguments: [String]          // App 内 = ["-s", "-m", "desk"]（-s 为 packaging §1.3 运行期契约）
  var environment: [String: String]// App 内 = ["PYTHONPATH": "<Resources>:<Resources>/pylibs/desk"]
  var familyPathPrefix: String?    // 退出时按此可执行路径收割全家；App 内 = executableURL.path
}

struct ServerLaunchSpec {          // 全部可注入，测试用假值
  var launch: ServerLaunchCommand? // nil ⇒ attach-only（bundle.json 缺失的开发模式）
  var port: Int                    // App 内固定 8766
  var llmPort: Int?                // App 内固定 8767；退出时一并验证无监听（假服务测试传 nil 或临时端口）
  var healthPath: String           // 默认 "/api/state"
  var logFileURL: URL              // 子进程 stdout/stderr 落盘处
  var spawnTimeout: TimeInterval   // 默认 15s
  var termGrace: TimeInterval      // 默认 5s
}

enum ServerState { case stopped, starting, runningOwned(pid: Int32), runningAttached, failed(ServerFailure) }

final class ServerController {
  init(spec: ServerLaunchSpec)
  func spawnEmbeddedServer(completion: (Result<ServerState, ServerFailure>) -> Void)
  func terminateEmbeddedServer() -> TerminateReport   // 同步，退出路径专用
  var state: ServerState
}
```

**spawn 流程**
1. 健康检查 `GET :8766<healthPath>`：返回 200 且 body 是 JSON ⇒ `runningAttached`，直接完成
   （二次启动 App、或上次 App 被 SIGKILL 留下的服务，都走这条被重新收编）。
2. 端口被占但健康检查不过 ⇒ `failed(.portConflict)`（不是我们的服务，绝不杀，交给错误页说明）。
3. 端口空闲：`launch == nil` ⇒ `failed(.noEmbeddedRuntime)`；否则 `Process` 按 `ServerLaunchCommand`
   执行内嵌解释器（executable + arguments + environment 原样注入），
   stdout/stderr 追加到 `logFileURL`（目录不存在先创建）。
4. 轮询健康（0.2s 间隔）直到 200 或超时；超时 ⇒ TERM 子进程 ⇒ `failed(.healthTimeout(lastError))`。

**terminate 流程（R-shell-04 的核心）**
1. 持有子进程 ⇒ SIGTERM；最多等 `termGrace`（给服务一个体面收尾窗口）；仍活着 ⇒ SIGKILL；`waitpid` 收尸。
2. **全家收割**（仅 owned 模式，`familyPathPrefix != nil`）：`PortGuard.family(matching: familyPathPrefix)`
   （经 `pgrep -f <路径>`）找出仍在跑内嵌解释器的所有进程——mlx-lm、H3、Music 子进程都跑
   `<Resources>/python/bin/python3.13`，且 media 用 `start_new_session=True` 起它们，
   它们**不会**随 desk 进程死——逐个 TERM → 等 2s → KILL → 复查。
   内嵌解释器绝对路径是本 App 安装独有的，杀伤半径天然受限（Phase 1.2 定为规范机制：
   没有任何后端设计安装 desk 侧 SIGTERM 收割器，见 A-5）。
3. `PortGuard.ensureFree(port)`：对**仍在监听 8766 的任何进程**（含 attached 模式下不是我们 spawn 的）
   TERM → 等 2s → KILL → 复查；随后（owned 模式）复查 `llmPort`(8767) 亦无监听。
   两个端口都确认无监听才算成功。
4. 返回 `TerminateReport{ portFree: Bool, llmPortFree: Bool?, killedPids: [Int32] }`；
   任一为 false 时写日志并 stderr 如实上报（不假装成功——错误不吞）。

### 2. PortGuard

`listeners(onPort:) -> [pid]`（经 `lsof -tiTCP:<port> -sTCP:LISTEN` 解析，等价于 `unload-llm.sh` 的按端口语义）；
`ensureFree(port:grace:) -> Bool` 实现 TERM→KILL→复查；
`family(matching: String) -> [pid]`（经 `pgrep -f <可执行路径>`）配合 `reap(pids:grace:)` 实现退出时的全家收割。
服务**活着**时 8767 的收割权威仍是 arbiter 的 `api:reapLlmPort`（shell 运行中绝不碰 8767）；
shell 只在**退出路径、desk 进程已死之后**做端口/家族收割——那时进程内已无人可执行收割。
无 AppKit 依赖，harness 直接复用。

### 3. AppDelegate + main.swift

- `setActivationPolicy(.regular)`：Dock 图标存在、可正常激活切换（R-shell-05；静态断言检查此调用存在，
  且源码中不得出现 `LSUIElement` / `.accessory`）。
- `applicationShouldTerminateAfterLastWindowClosed → false`（R-shell-03）。
- `applicationShouldHandleReopen`：点 Dock 图标 ⇒ 唤回主窗口。
- `applicationWillTerminate`：同步调用 `terminateEmbeddedServer()`。
- `main.swift` 用 `DispatchSourceSignal` 接管 SIGTERM/SIGINT：先 `terminateEmbeddedServer()` 再 `exit(0)`
  ——异常终止路径也清理（R-shell-04 后半句）。
- **不出现** `SMAppService`、`LSSharedFileList`、任何 `LaunchAgents` 字样或写入（R-shell-06；静态断言）。

启动编排（`applicationDidFinishLaunching`）：

```
建菜单栏(初始"启动中…") → spawnEmbeddedServer
  ├─ 失败 ⇒ 主窗口显示错误页；菜单栏"服务未运行"
  └─ 成功 ⇒ DeskAPI.readConfig
       ├─ needs_setup ⇒ FirstRunFlow.run()（完成或用户放弃后继续）
       └─ 加载 http://127.0.0.1:8766/ 进 WKWebView；启动 StatusPoller
```

### 4. MainWindowController —— `ui:mainWindow`

- 一个 NSWindow（尺寸/居中逻辑沿用现 `App.swift`），contentView 为 WKWebView，加载 `ui:deskShell`。
- `windowShouldClose` ⇒ `orderOut` 并返回 false 的等价实现（窗口隐藏，App 与服务继续活，R-shell-03）。
- `showWindow()`：把既有窗口 `makeKeyAndOrderFront` + 激活 App（菜单栏「打开窗口」与 Dock reopen 共用）。
- **错误页**（R-shell-08）：以下任一情形，用 `loadHTMLString` 换上本地错误页（内容是 Swift 内嵌字符串，
  不依赖服务活着）：
  - `spawnEmbeddedServer` 失败（区分文案：端口冲突 / 无内嵌运行时 / 健康超时）；
  - WKNavigationDelegate `didFailProvisionalNavigation`；
  - StatusPoller 连续 3 次拉不到 deskState 且子进程已退出（捕获 `Process.terminationHandler`）。
  错误页含：死亡原因一句话、日志路径（`logs/`）、「重试」按钮。重试经
  `WKScriptMessageHandler`（`window.webkit.messageHandlers.shellRetry`）回调 Swift，
  重新走 spawn→health→reload。这是错误页唯一的 JS 桥，不对 `ui:deskShell` 注入任何东西。

### 5. StatusItemController + StatusPoller —— `ui:menuBarItem` / `data:shellStatus`

- NSStatusItem（variableLength 文本）。每 3s `GET /api/state`（`data:deskState`）；
  菜单打开时（`menuWillOpen`）额外拉一次 `api:memorySnapshot` 刷新内存行，
  并（仅当 `needsSetup == true` 时）重拉一次 `GET /api/config` 以便首运完成后文案自动退出「待设置」。
  `needs_setup` **不在** deskState 里——它属于 `data:deskConfig`（arbiter 的 deskState 合同只有
  `holder / media_busy / can_start` 三键），来源是启动时与 FirstRunFlow 结束后的 `api:readConfig`。
- `ShellStatus`（`data:shellStatus`，shell 对外暴露的自身状态模型）：

```swift
struct ShellStatus {
  var server: ServerState                 // stopped/starting/runningOwned/runningAttached/failed
  var desk: DeskStateSnapshot?            // 最近一次成功拉到的 data:deskState，服务死了为 nil
  var needsSetup: Bool                    // 来自最近一次 api:readConfig（data:deskConfig.needs_setup）
  var lastPollError: String?
}

struct DeskStateSnapshot {                // data:deskState 的消费投影（arbiter 合同，见 A-4）
  var holderKind: String?                 // holder == null ⇒ nil；否则 holder.kind ∈ llm|video|music
  var holderLabel: String?                // holder.label（llm 时为 llm acquire 传入的模型目录 key）
}
```

- 纯映射函数 `menuTitle(for: ShellStatus) -> String`（R-shell-02 的文案唯一来源）：

| 条件 | 菜单栏标题 |
|---|---|
| server = starting | `启动中…` |
| server = failed/stopped | `服务未运行` |
| needsSetup（来自 readConfig） | `待设置` |
| holder == null | `空闲` |
| holder.kind == llm | `已加载 <holder.label>` |
| holder.kind == video / music | `出片中` / `出歌中` |
| deskState 拉取失败但进程还在 | `状态不可读` |

- 菜单项：状态详情（禁用行：上表全文 + `内存 已用 x.x / 共 y GiB`，来自 `api:memorySnapshot`）、
  分隔线、「打开窗口」（`showWindow`）、「退出」（`NSApp.terminate` ⇒ 走 `applicationWillTerminate` 收割）。
  仅此四类，无更多菜单项（YAGNI）。

### 6. FirstRunFlow + ModelsDirectoryChooser —— R-shell-07 / `api:chooseModelsDirectory`

`api:chooseModelsDirectory` 实现为 `ModelsDirectoryChooser.choose(prompt:) -> URL?`：
NSOpenPanel，`canChooseDirectories = true`、`canChooseFiles = false`、`canCreateDirectories = true`。

`FirstRunFlow.run(api: DeskAPI)`（仅当 `readConfig` 表明 needs-setup 时进入）：

```
NSAlert「首次设置：模型放在哪？」三个按钮
  ├─ 使用默认目录            ⇒ POST completeFirstRun{}   # 不带 models_root，服务端用默认值（foundation 路由合同）
  ├─ 选择其他目录…           ⇒ chooseModelsDirectory ⇒ POST completeFirstRun{ models_root }
  └─ 收编既有目录树…         ⇒ chooseModelsDirectory(选 legacy 根)
        ⇒ NSAlert「指向该目录 / 移动到默认目录」⇒ POST adoptLegacyModels{ legacy_root, mode: point|move }
```

- 任一 POST 返回错误（目录不可写、移动空间不足等）⇒ NSAlert 原样展示服务端错误文案，
  提供「重选」回到起点；**绝不静默回退**（对齐 R-foundation-03/04 的错误语义）。
- 用户取消（关掉面板/按 Esc）⇒ 不落任何配置，直接加载 UI；服务端仍是 needs-setup，
  网页里 ui 模块的 `ui:firstRunPane` 会兜底（浏览器直访 8766 的用户也走那条路）。
  两条首运路径调的是同一组 foundation API，不存在第二份逻辑。
- 首运成功后重新 `readConfig` 确认 `first_run_done`，再加载 UI。

### 7. DeskAPI

唯一的 HTTP 客户端封装（URLSession，同主机短超时）。集中全部路由字符串：

| 方法 | 路由（见 Assumptions A-3） | 对应注册表接口 |
|---|---|---|
| GET | `/api/state` | `data:deskState` |
| GET | `/api/memory` | `api:memorySnapshot` |
| GET | `/api/config` | `api:readConfig` |
| POST | `/api/first-run` | `api:completeFirstRun` |
| POST | `/api/adopt` | `api:adoptLegacyModels` |

响应解析全部防御式：未知字段忽略、缺字段降级（拉不出 holder 就显示「状态不可读」），
不因服务端 shape 演进而崩。

## 数据流

**启动**
```
用户双击 App → spawnEmbeddedServer(<Resources>/python/bin/python3.13 -s -m desk)
  → 健康轮询 :8766 → readConfig
  → [needs_setup] FirstRunFlow(NSOpenPanel → completeFirstRun/adoptLegacyModels)
  → WKWebView 载入 ui:deskShell → StatusPoller 开始 3s 轮询 deskState
```

**运行中**
```
deskState(HTTP) ─→ StatusPoller ─→ ShellStatus ─→ menuTitle() ─→ NSStatusItem
memorySnapshot(HTTP, 菜单展开时) ────────────────→ 菜单内存行
```

**关窗 / 唤回**
```
关窗 ⇒ 窗口 orderOut（App、服务、轮询全部照旧）
菜单「打开窗口」/ Dock 点击 ⇒ showWindow()
```

**退出（唯一会停服务的路径）**
```
菜单「退出」/ SIGTERM/SIGINT
  → terminateEmbeddedServer(): 子进程 TERM→KILL（termGrace 内给服务体面收尾的机会）
      → 按内嵌解释器路径收割全家（mlx-lm、H3、Music 残余进程）
      → PortGuard.ensureFree(8766) → 复查 8767 无监听
  → exit
（Phase 1.2 实查：没有任何后端设计安装 desk 侧 SIGTERM 收割器，llm 只在下次 spawn 前收孤儿、
 media 子进程用 start_new_session 起——因此 shell 的按路径全家收割是 R-shell-04 的规范保证，见 A-5）
```

## 错误处理

| 情形 | 行为 |
|---|---|
| `<Resources>/bundle.json` 缺失（开发态） | attach-only；无现役服务 ⇒ 错误页「未找到内嵌运行时，开发模式请先启动 `python -m desk`」 |
| 8766 被非台面进程占用 | 不杀、不重试端口；错误页「端口 8766 被其他进程占用（pid …）」；菜单栏「服务未运行」 |
| 健康检查超时 | TERM 子进程；错误页附日志路径；「重试」可再来 |
| 运行中服务崩溃 | `terminationHandler` + 连续轮询失败共同触发错误页与菜单栏降级（R-shell-08，不留空白 WebView） |
| 首运 API 报错 | NSAlert 原样透出服务端 error 文案，可重选；不回退默认、不伪造成功 |
| 退出时端口/进程收不干净 | `TerminateReport.portFree/llmPortFree=false` 写入日志并 stderr 输出；不谎报成功 |
| deskState 拉取失败但进程活着 | 菜单栏「状态不可读」，不显示旧数据冒充实时 |

原则重申：**错误就是错误**。shell 不为任何失败编造可用状态。

## 测试

验收全部是快速确定性命令；需要真点击的项列 reality-gate runbook。

### tests/test_shell_static.py（纯 pytest，秒级）

对 `macos/*.swift`（排除 `harness/`）做静态断言：
1. 不含 `localModelDesk`（**大小写敏感**——`DeskPaths.swift` 里 `Application Support/LocalModelDesk`
   的大写拼写是合法的，测试不得为此放宽成大小写不敏感）、`media-gui`、
   `homeDirectoryForCurrentUser` 与 `/opt/homebrew`（R-shell-01，消 A10）；
2. 不含 `LaunchAgents`、`SMAppService`、`LSSharedFileList`、`loginItem`（R-shell-06）；
3. 含 `setActivationPolicy(.regular)`，不含 `LSUIElement`、`.accessory`（R-shell-05）；
4. `applicationShouldTerminateAfterLastWindowClosed` 返回 `false`（R-shell-03 的可静态半面）；
5. 路由字符串 `"/api/"` 只出现在 `DeskAPI.swift`（单点契约不散落）；
6. `swiftc -parse macos/*.swift macos/harness/*.swift` 退出码 0（语法级编译门，几秒内）。

### tests/test_shell_lifecycle.py（pytest 驱动 harness，headless）

`scripts/shell-lifecycle-test.sh` 先用 `swiftc` 把
`ServerController.swift + PortGuard.swift + ShellStatus.swift + harness/ShellHarness.swift`
编成 `<scratch>/shellharness`（无 AppKit 主循环）。harness 子命令与场景：

1. **spawn→healthy→SIGTERM→clean**：假服务是 tmp 目录里一个 `python3 -c` 小 HTTP 脚本
   （在**随机空闲端口**上应答 `/api/state` 200 JSON）；harness `run --launcher <假服务> --port N`；
   pytest 断言端口进入监听、给 harness 发 SIGTERM、断言 harness 退出码 0 且**端口无监听、子进程消失**
   （R-shell-04 的机器可证明面）。
2. **孤儿收编**：先手动起假服务再跑 harness ⇒ 输出 `ATTACHED`；SIGTERM 后同样断言端口释放
   （attached 模式也不留孤儿）。
3. **端口冲突**：起一个**不答健康检查**的假监听 ⇒ harness 输出 `PORT_CONFLICT` 且**不杀**该进程（断言其仍活着，杀伤半径受控）。
4. **健康超时**：launcher 指向 `sleep 999` ⇒ harness 在超时后输出 `HEALTH_TIMEOUT`，子进程已被终止。
5. **无 launcher 且无现役服务** ⇒ `NO_RUNTIME`。
6. **菜单文案映射**：harness `map-status < fixture.json` 打印 `menuTitle` 结果，
   pytest 用表驱动断言全部七行文案；fixture 用 arbiter 的**真实 deskState 形状**
   （`holder: null` 与 `holder: {kind, label}` 两种，`needs_setup` 单独来自 config fixture），
   把 R-shell-02 的纯逻辑面拉进自动验收。
7. **全家收割**：launcher 是一个假解释器脚本（拷进 tmp_path、路径唯一），它先
   `setsid` 起一个**同路径**的分离孙进程（模拟 media 的 `start_new_session=True` 子进程）再应答健康检查；
   对 harness 发 SIGTERM 后，pytest 断言**孙进程也已消失**且端口无监听
   （R-shell-04「不得留下孤儿进程」的机器可证明面；`--family-path` 注入假解释器路径）。

全部使用随机空闲端口与 tmp_path，不触碰真实 8766/8767、不触碰任何权重目录。

### reality-gate runbook（人工，Phase 2 附证据）

1. 双击 App：Dock 图标出现，⌘Tab 可切换（R-shell-05）。
2. 首运：NSOpenPanel 弹出，三条路径各走一遍（默认/自选/收编-指向），错误路径用只读目录验证报错文案（R-shell-07）。
3. 关窗：窗口消失，菜单栏项仍在，`lsof -iTCP:8766` 仍有监听；菜单「打开窗口」唤回原状态（R-shell-03）。
4. 加载一个 LLM / 起一个视频作业，看菜单栏在 10s 内变为「已加载 …」/「出片中」（R-shell-02）。
5. 菜单「退出」：App 消失且 `lsof -iTCP:8766 -iTCP:8767` 双双为空（R-shell-04 全景）。
6. `kill -TERM <App pid>` 重复第 5 步的断言（异常终止路径）。
7. 运行中 `kill -9` 掉 desk 服务进程：窗口 10s 内出现错误说明页而非空白（R-shell-08），「重试」能复活。

## Assumptions（本模块自决，或待 Phase 1.2 对齐的跨模块契约）

- **A-1 启动入口契约（Phase 1.2 已对齐）**：packaging 设计 §1.3/§3.2 的冻结契约是
  **不设 launcher 文件**，由 shell 直接执行
  `<Resources>/python/bin/python3.13 -s -m desk`（`-s` 按 packaging 运行期契约），`PYTHONPATH=<Resources>:<Resources>/pylibs/desk`；
  内嵌运行时存在性判据 = `<Resources>/bundle.json`（packaging §1.4，与 foundation 判定运行形态共用）。
  这三个常量只住在 `DeskPaths.swift`，packaging 布局若再演进，改动仍是常量级。
- **A-2 Swift 侧路径镜像**：Swift 进程无法调用 Python 的 `api:resolvePaths`，故 `DeskPaths.swift`
  是 Swift 侧唯一允许出现路径构造的文件，只镜像 foundation 已冻结的两个根：
  bundle 资源根 = `Bundle.main.resourceURL`；用户数据根 = `~/Library/Application Support/LocalModelDesk/`
  （用于子进程 stdout 落盘 `logs/server-stdout.log`，与服务自己的 `desk.log` 分开，避免双写同一文件）。
  静态断言 5/1 保证它不扩散。
- **A-3 HTTP 路由名（Phase 1.2 已对齐）**：`/api/config`、`/api/first-run`、`/api/adopt`
  以 foundation 设计 §2.6 路由表为准（原提案 `/api/config/first-run`、`/api/config/adopt` 已废弃）；
  `/api/state`、`/api/memory` 与 ui 设计使用的拼写一致（由台面服务组装层挂载）。
  全部集中在 `DeskAPI.swift`，若组装层再改拼写，对齐成本为常量级。
- **A-4 deskState 消费 shape（Phase 1.2 已按 arbiter 合同修正）**：deskState 只有
  `holder / media_busy / can_start` 三键；shell 只读 `holder`——`null` ⇒ 空闲，否则取
  `holder.kind`（`llm|video|music`）与 `holder.label`（llm 时为模型目录 key——llm 以 key 作 acquire label）。
  `needs_setup` 不在 deskState 里，来自 `api:readConfig`（`data:deskConfig`）。
  多余字段忽略，缺字段降级为「状态不可读」——arbiter 侧增删字段不需要 shell 同步发版。
- **A-5 退出收割归属（Phase 1.2 裁定）**：原假设「内嵌服务收到 SIGTERM 后自行收割 :8767 与媒体子进程」
  在对方设计中**无人认领**——foundation/llm/media 设计均未安装 desk 侧 SIGTERM 处理器；
  llm 只在下次 spawn 前 `reap_llm_port`，media 子进程以 `start_new_session=True` 起（不随父进程死）。
  故裁定：退出时的孤儿保证由 **shell 的按内嵌解释器路径全家收割 + 8766/8767 端口复查**规范承担
  （terminate 流程第 2–4 步；生命周期测试场景 7 机检）。`termGrace` 窗口仍给服务体面收尾的机会，
  服务侧将来若增加 SIGTERM 处理器，只会让 KILL 路径更少触发，契约不变。
  attach-only 开发态无内嵌解释器路径可循，只做 8766 端口收割——残余风险与 A-6 同级，判定可接受。
- **A-6 App 被 SIGKILL 的残留**：SIGKILL 无法拦截，服务可能短暂成为孤儿；缓解 = 下次启动 attach 收编
  + 退出时按端口收割。判定为可接受残留风险，不为此加看门狗进程（YAGNI）。
- **A-7 首运双入口**：App 内首运由 shell 原生驱动（R-shell-07 要求 NSOpenPanel，且 WKWebView 中网页拿不到
  绝对路径）；浏览器直访 8766 的首运由 ui 的 `ui:firstRunPane` 承担。两者调同一组 foundation API，
  无第二份逻辑。`api:chooseModelsDirectory` 因此是 Swift 内 API（NSOpenPanel 封装），不注入网页。
- **A-8 错误页「重试」**：R-shell-08 只要求「说明」，重试按钮是本模块内部裁量（避免死胡同 UI），
  实现仅一个 message handler，不扩大对外表面。
- **A-9 轮询而非事件**：`event:heavyStateChanged` 未列入本模块消费；菜单栏用 3s 轮询 deskState 达到
  「实时」观感（状态变化本身以分钟计），不为 shell 新增 SSE 通道（YAGNI）。

## Census 义务清账（shell 归属项）

- **A10 Swift 硬编码 checkout 路径**：由「只执行 bundle 内解释器 + `DeskPaths.swift` 单点 +
  静态断言 1（大小写敏感 grep）」消除；attach-only 开发模式保证开发态也无 checkout 路径。
- **A13 游离启动脚本 `media-gui/start.sh`**：其全部职责（起服务、定端口、日志落盘）被
  `ServerController`（`api:spawnEmbeddedServer`）取代；文件本体的 `git rm` 按 packaging 设计 §2.7
  在 shell 合入**之后**执行（packaging verify V7 + census 重跑 `ls media-gui/start.sh` 机检其不存在）。
  shell 的生命周期测试（场景 1–5、7）即行为取代的证明方——census A13 表中的证明责任由此落实。
