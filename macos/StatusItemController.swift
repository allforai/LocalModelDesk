import AppKit

/// ui:menuBarItem — displays current desk status and a compact control menu.
final class StatusItemController: NSObject, NSMenuDelegate {
  private let statusItem: NSStatusItem
  private let api: DeskAPI
  private let detailItem = NSMenuItem(title: "状态：启动中…", action: nil, keyEquivalent: "")
  private let memoryItem = NSMenuItem(title: "内存 —", action: nil, keyEquivalent: "")
  var onOpenWindow: (() -> Void)?
  var onMenuOpened: (() -> Void)?

  init(api: DeskAPI) {
    self.api = api
    statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.variableLength)
    super.init()
    statusItem.button?.title = "启动中…"

    let menu = NSMenu()
    menu.autoenablesItems = false
    menu.delegate = self
    detailItem.isEnabled = false
    memoryItem.isEnabled = false
    menu.addItem(detailItem)
    menu.addItem(memoryItem)
    menu.addItem(.separator())

    let openItem = NSMenuItem(title: "打开窗口", action: #selector(openWindow), keyEquivalent: "")
    openItem.target = self
    menu.addItem(openItem)
    let quitItem = NSMenuItem(title: "退出", action: #selector(quit), keyEquivalent: "")
    quitItem.target = self
    menu.addItem(quitItem)
    statusItem.menu = menu
  }

  /// The status model's pure mapping is the sole source of status copy.
  func render(_ status: ShellStatus) {
    let title = menuTitle(for: status)
    statusItem.button?.title = title
    detailItem.title = "状态：\(title)"
  }

  /// The sole writer of the memory menu row; called on every poll and again when the menu opens.
  func renderMemory(_ result: Result<MemoryLine, DeskAPIError>) {
    switch result {
    case .success(let line):
      memoryItem.title = memoryMenuTitle(used: line.usedBytes, total: line.totalBytes,
                                         available: line.availableBytes)
    case .failure:
      memoryItem.title = "内存 不可读"
    }
  }

  /// Refreshes the data:memorySnapshot row when the menu opens. Menu tracking runs the run loop
  /// in event-tracking mode, where `DispatchQueue.main.async` blocks do not fire until the menu
  /// closes; use common + eventTracking modes so the row updates while the menu is still open.
  func menuWillOpen(_ menu: NSMenu) {
    api.memorySnapshot { [weak self] result in
      RunLoop.main.perform(inModes: [.common, .eventTracking]) { self?.renderMemory(result) }
    }
    onMenuOpened?()
  }

  @objc private func openWindow() { onOpenWindow?() }

  @objc private func quit() { NSApp.terminate(nil) }
}
