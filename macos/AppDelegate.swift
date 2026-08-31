import AppKit

/// Coordinates shell startup, UI presentation, polling, and synchronous teardown.
final class AppDelegate: NSObject, NSApplicationDelegate {
  private var server: ServerController!
  private var api: DeskAPI!
  private var windowController: MainWindowController!
  private var statusController: StatusItemController!
  private var poller: StatusPoller!
  private var status = ShellStatus(server: .stopped, desk: nil, needsSetup: false,
                                   lastPollError: nil)

  func applicationDidFinishLaunching(_ notification: Notification) {
    NSApp.setActivationPolicy(.regular)
    buildMainMenu()
    api = DeskAPI(baseURL: DeskPaths.baseURL)
    server = ServerController(spec: DeskPaths.makeLaunchSpec())
    windowController = MainWindowController(baseURL: DeskPaths.baseURL)
    statusController = StatusItemController(api: api)
    poller = StatusPoller(api: api)
    statusController.onOpenWindow = { [weak self] in self?.windowController.showWindow() }
    statusController.onMenuOpened = { [weak self] in
      guard let self, self.status.needsSetup else { return }
      self.refreshConfig()
    }
    windowController.onRetry = { [weak self] in self?.startServer() }
    poller.onUpdate = { [weak self] result in self?.handlePoll(result) }
    status.server = .starting
    statusController.render(status)
    windowController.showWindow()
    startServer()
  }

  private func startServer() {
    status.server = .starting
    statusController.render(status)
    DispatchQueue.global().async { [weak self] in
      guard let self else { return }
      let result = self.server.spawnEmbeddedServer()
      DispatchQueue.main.async { self.handleSpawn(result) }
    }
  }

  private func handleSpawn(_ result: Result<ServerState, ServerFailure>) {
    switch result {
    case .failure(let failure):
      status.server = .failed(failure)
      statusController.render(status)
      windowController.showErrorPage(reason: Self.describe(failure),
                                     logPath: DeskPaths.serverStdoutLogURL.path)
    case .success(let state):
      status.server = state
      statusController.render(status)
      refreshConfigThenLoad()
    }
  }

  private func refreshConfigThenLoad() {
    api.readConfig { [weak self] result in
      DispatchQueue.main.async {
        guard let self else { return }
        if case .success(let config) = result, config.needsSetup {
          self.status.needsSetup = true
          self.statusController.render(self.status)
          if FirstRunFlow(api: self.api).run() { self.refreshConfig() }
        }
        self.windowController.loadDeskShell()
        self.poller.start()
      }
    }
  }

  private func refreshConfig() {
    api.readConfig { [weak self] result in
      DispatchQueue.main.async {
        guard let self else { return }
        if case .success(let config) = result { self.status.needsSetup = config.needsSetup }
        self.statusController.render(self.status)
      }
    }
  }

  private func handlePoll(_ result: Result<DeskStateSnapshot, DeskAPIError>) {
    switch result {
    case .success(let snapshot):
      status.desk = snapshot
      status.lastPollError = nil
    case .failure(let error):
      status.desk = nil
      status.lastPollError = error.message
      if poller.consecutiveFailures >= 3 && !server.isChildRunning {
        status.server = .failed(.spawnFailed("服务已退出"))
        windowController.showErrorPage(
          reason: "台面服务意外退出（连续 \(poller.consecutiveFailures) 次状态拉取失败）。",
          logPath: DeskPaths.serverStdoutLogURL.path)
        poller.stop()
      }
    }
    statusController.render(status)
  }

  func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
    return false
  }

  func applicationShouldHandleReopen(_ sender: NSApplication, hasVisibleWindows flag: Bool) -> Bool {
    if !flag { windowController.showWindow() }
    return true
  }

  func applicationWillTerminate(_ notification: Notification) {
    reportTerminate(server?.terminateEmbeddedServer())
  }

  func shutdownNow() {
    reportTerminate(server?.terminateEmbeddedServer())
    exit(0)
  }

  private func reportTerminate(_ report: TerminateReport?) {
    guard let report else { return }
    if !report.portFree || report.llmPortFree == false {
      FileHandle.standardError.write(Data(
        "shell: terminate incomplete portFree=\(report.portFree) llmPortFree=\(String(describing: report.llmPortFree))\n".utf8))
    }
  }

  private func buildMainMenu() {
    let mainMenu = NSMenu()
    let appMenuItem = NSMenuItem()
    let appMenu = NSMenu()
    appMenu.addItem(withTitle: "退出 LocalModelDesk",
                    action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q")
    appMenuItem.submenu = appMenu
    mainMenu.addItem(appMenuItem)
    let fileMenuItem = NSMenuItem()
    let fileMenu = NSMenu(title: "文件")
    fileMenu.addItem(withTitle: "关闭窗口",
                     action: #selector(NSWindow.performClose(_:)), keyEquivalent: "w")
    fileMenuItem.submenu = fileMenu
    mainMenu.addItem(fileMenuItem)
    NSApp.mainMenu = mainMenu
  }

  private static func describe(_ failure: ServerFailure) -> String {
    switch failure {
    case .noEmbeddedRuntime:
      return "未找到内嵌运行时（Resources/bundle.json 缺失）。开发模式请先手动启动 python -m desk。"
    case .portConflict(let pids):
      return "端口 \(DeskPaths.port) 被其他进程占用（pid \(pids.map(String.init).joined(separator: ", "))），不属于台面服务，不会代为终止。"
    case .healthTimeout(let lastError):
      return "服务启动超时：\(lastError)"
    case .spawnFailed(let reason):
      return "服务启动失败：\(reason)"
    }
  }
}
