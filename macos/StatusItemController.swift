import AppKit

/// ui:menuBarItem — displays current desk status and a compact control menu.
final class StatusItemController: NSObject, NSMenuDelegate {
  private let statusItem: NSStatusItem
  private let api: DeskAPI
  private let detailItem = NSMenuItem(title: "状态：启动中…", action: nil, keyEquivalent: "")
  private let memoryItem = NSMenuItem(title: "内存 —", action: nil, keyEquivalent: "")
  var onOpenWindow: (() -> Void)?
  var onOpenSettings: (() -> Void)?
  var onMenuOpened: (() -> Void)?

  init(api: DeskAPI) {
    self.api = api
    statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
    super.init()
    configureStatusButton(label: "启动中…")

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
    let settingsItem = NSMenuItem(title: "设置…", action: #selector(openSettings), keyEquivalent: ",")
    settingsItem.target = self
    menu.addItem(settingsItem)
    menu.addItem(.separator())
    let quitItem = NSMenuItem(title: "退出", action: #selector(quit), keyEquivalent: "")
    quitItem.target = self
    menu.addItem(quitItem)
    statusItem.menu = menu
  }

  /// The status model's pure mapping is the sole source of status copy.
  func render(_ status: ShellStatus) {
    let title = menuTitle(for: status)
    configureStatusButton(label: title)
    detailItem.title = "状态：\(title)"
  }

  /// Use the product mark consistently; live state remains available in the menu and tooltip.
  private func configureStatusButton(label: String) {
    guard let button = statusItem.button else { return }
    let image = NSApp.applicationIconImage.copy() as? NSImage
    image?.size = NSSize(width: 18, height: 18)
    image?.isTemplate = false
    image?.accessibilityDescription = "LocalModelDesk：\(label)"
    button.image = image
    button.imagePosition = .imageOnly
    button.title = ""
    button.toolTip = "LocalModelDesk · \(label)"
    button.setAccessibilityLabel("LocalModelDesk：\(label)")
  }

  /// Refreshes the data:memorySnapshot row only when the menu opens.
  func menuWillOpen(_ menu: NSMenu) {
    api.memorySnapshot { [weak self] result in
      DispatchQueue.main.async {
        switch result {
        case .success(let line):
          let gib = 1_073_741_824.0
          self?.memoryItem.title = String(
            format: "内存 已用 %.1f / 共 %.0f GiB",
            Double(line.usedBytes) / gib,
            Double(line.totalBytes) / gib
          )
        case .failure:
          self?.memoryItem.title = "内存 不可读"
        }
      }
    }
    onMenuOpened?()
  }

  @objc private func openWindow() { onOpenWindow?() }

  @objc private func openSettings() { onOpenSettings?() }

  @objc private func quit() { NSApp.terminate(nil) }
}
