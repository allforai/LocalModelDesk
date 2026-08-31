# 模块 spec：shell

**单一职责** macOS App 外壳：菜单栏、窗口、以及内嵌服务的生命周期。

## 背景约束

现状 `App.swift` 硬编码 `~/localModelDesk/media-gui/server.py`——装完的 App 不能依赖任何 checkout 目录。
服务必须从 `.app/Contents/Resources/` 里起。

人类明示：**不自启**（现有的 `com.aa.localmodeldesk` LaunchAgent 要卸掉）；
菜单栏 + Dock 都在；关窗口不退；菜单栏 Quit 才终止服务。

## 需求

- **R-shell-01** App 从 `Contents/Resources/` 内的内嵌运行时启动服务；
  Swift 源码中不得出现任何指向 home 下 checkout 目录的路径。
- **R-shell-02** 菜单栏项显示实时台面状态（空闲 / 已加载 XX / 出片中），菜单含「打开窗口」与「退出」。
- **R-shell-03** 关闭窗口不退出应用；App 留在菜单栏，服务继续存活；再次「打开窗口」能把窗口调回来。
- **R-shell-04** 退出时终止内嵌服务；不得留下孤儿进程（退出后台面端口不再有监听）。
  异常终止路径（如 SIGTERM）也要清理。
- **R-shell-05** Dock 图标存在，App 可被正常激活与切换（不是 LSUIElement）。
- **R-shell-06** App 不注册任何登录项、不写任何 LaunchAgent plist。
- **R-shell-07** 首运弹出 models 目录选择（`NSOpenPanel`），并可选择收编既有目录树。
- **R-shell-08** 服务意外死亡时在界面上说明，而不是显示一个空白 WebView。

## 暴露

`ui:menuBarItem`、`ui:mainWindow`、`api:spawnEmbeddedServer`、`api:terminateEmbeddedServer`、
`api:chooseModelsDirectory`、`data:shellStatus`

## 消费

`data:deskState`、`api:memorySnapshot`、`api:readConfig`、`api:completeFirstRun`、
`api:adoptLegacyModels`、`ui:deskShell`

## 验收取向

- 可自动验证：Swift 源码静态断言（不含 home checkout 路径、不含 LaunchAgents 写入、
  `setActivationPolicy(.regular)`）；`swiftc` 编译通过；
  进程生命周期用一个 headless 的服务启停脚本验证「终止后端口无监听」。
- 「关窗口不退、菜单栏状态显示正确、首运面板弹出」这类需要真实点击的：标 `reality_gate`，附人工 runbook。
