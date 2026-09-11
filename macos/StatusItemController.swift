import AppKit

/// ui:menuBarItem — displays current desk status and a compact control menu.
final class StatusItemController: NSObject, NSMenuDelegate {
  private let statusItem: NSStatusItem
  private let api: DeskAPI
  private let detailItem = NSMenuItem(title: "状态：启动中…", action: nil, keyEquivalent: "")
  private let memoryItem = NSMenuItem(title: "内存 —", action: nil, keyEquivalent: "")
  var onOpenWindow: (() -> Void)?
  var onOpenSettings: (() -> Void)?
  var onRevealOutputs: (() -> Void)?
  var onMenuOpened: (() -> Void)?

  init(api: DeskAPI) {
    self.api = api
    statusItem = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)
    super.init()
    configureStatusButton(label: "启动中…", glyph: .down)

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
    openItem.image = NSImage(systemSymbolName: "macwindow", accessibilityDescription: "打开窗口")
    openItem.indentationLevel = 0
    menu.addItem(openItem)
    let revealItem = NSMenuItem(title: "打开成品目录", action: #selector(revealOutputs), keyEquivalent: "")
    revealItem.target = self
    revealItem.image = NSImage(systemSymbolName: "folder", accessibilityDescription: "打开成品目录")
    revealItem.indentationLevel = 0
    menu.addItem(revealItem)
    let settingsItem = NSMenuItem(title: "设置…", action: #selector(openSettings), keyEquivalent: ",")
    settingsItem.target = self
    settingsItem.image = NSImage(systemSymbolName: "gearshape", accessibilityDescription: "设置")
    settingsItem.indentationLevel = 0
    menu.addItem(settingsItem)
    menu.addItem(.separator())
    let quitItem = NSMenuItem(title: "退出", action: #selector(quit), keyEquivalent: "")
    quitItem.target = self
    quitItem.image = NSImage(systemSymbolName: "power", accessibilityDescription: "退出")
    quitItem.indentationLevel = 0
    menu.addItem(quitItem)
    statusItem.menu = menu
  }

  /// The status model's pure mapping is the sole source of status copy and glyph.
  func render(_ status: ShellStatus) {
    let title = menuTitle(for: status)
    let glyph = menuGlyphState(for: status)
    configureStatusButton(label: title, glyph: glyph)
    let text = "状态：\(title)"
    detailItem.image = NSImage(systemSymbolName: glyphName(for: glyph), accessibilityDescription: nil)
    detailItem.attributedTitle = NSAttributedString(
      string: text, attributes: [.foregroundColor: tintColor(for: glyph)])
  }

  /// SF Symbol for the status row, mirroring the same three-state distinction (idle/loaded/busy,
  /// plus down) the menu-bar glyph draws — so the row is never blank next to the four menu items
  /// below it, which all carry icons (N5).
  private func glyphName(for glyph: MenuGlyphState) -> String {
    switch glyph {
    case .down: return "circle.slash"
    case .idle: return "circle"
    case .loaded: return "circle.fill"
    case .busy: return "waveform"
    }
  }

  /// Semantic color for the status row, matching the web statusbar's `--ok`/`--busy` tokens:
  /// neutral while idle/down, green once something is loaded, orange while busy (N5).
  private func tintColor(for glyph: MenuGlyphState) -> NSColor {
    switch glyph {
    case .down, .idle: return .secondaryLabelColor
    case .loaded: return .systemGreen
    case .busy: return .systemOrange
    }
  }

  /// Draws an 18x18 monochrome template "desk" glyph whose state variant marks
  /// idle/loaded/busy/down at a glance, independent of light/dark menu bars.
  private func configureStatusButton(label: String, glyph: MenuGlyphState) {
    guard let button = statusItem.button else { return }
    let image = NSImage(size: NSSize(width: 18, height: 18), flipped: false) { rect in
      NSColor.black.setStroke(); NSColor.black.setFill()
      let body = NSBezierPath(roundedRect: rect.insetBy(dx: 2, dy: 3), xRadius: 3, yRadius: 3)
      body.lineWidth = 1.5; body.stroke()
      switch glyph {
      case .idle: break
      case .loaded: NSBezierPath(ovalIn: NSRect(x: 11, y: 3, width: 5, height: 5)).fill()
      case .busy:
        let tri = NSBezierPath(); tri.move(to: NSPoint(x: 11, y: 3)); tri.line(to: NSPoint(x: 16, y: 5.5)); tri.line(to: NSPoint(x: 11, y: 8)); tri.close(); tri.fill()
      case .down:
        let slash = NSBezierPath(); slash.move(to: NSPoint(x: 3, y: 3)); slash.line(to: NSPoint(x: 15, y: 15)); slash.lineWidth = 1.5; slash.stroke()
      }
      return true
    }
    image.isTemplate = true
    image.accessibilityDescription = "LocalModelDesk：\(label)"
    button.image = image
    button.imagePosition = .imageOnly
    button.title = ""
    button.toolTip = "LocalModelDesk · \(label)"
    button.setAccessibilityLabel("LocalModelDesk：\(label)")
  }

  /// The sole writer of the memory menu row; called on every poll and again when the menu opens.
  func renderMemory(_ result: Result<MemoryLine, DeskAPIError>) {
    switch result {
    case .success(let line):
      memoryItem.title = memoryMenuTitle(used: line.usedBytes, total: line.totalBytes,
                                         available: line.availableBytes)
      memoryItem.image = NSImage(systemSymbolName: "memorychip", accessibilityDescription: nil)
      memoryItem.attributedTitle = NSAttributedString(
        string: memoryItem.title, attributes: [.foregroundColor: NSColor.secondaryLabelColor])
    case .failure:
      memoryItem.title = "内存 不可读"
      memoryItem.image = NSImage(systemSymbolName: "exclamationmark.triangle",
                                 accessibilityDescription: nil)
      memoryItem.attributedTitle = NSAttributedString(
        string: memoryItem.title, attributes: [.foregroundColor: NSColor.systemRed])
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

  @objc private func openSettings() { onOpenSettings?() }

  @objc private func revealOutputs() { onRevealOutputs?() }

  @objc private func quit() { NSApp.terminate(nil) }
}
