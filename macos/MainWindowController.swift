import AppKit
import WebKit

/// ui:mainWindow — hosts ui:deskShell in a WKWebView and provides a local error page.
final class MainWindowController: NSObject, NSWindowDelegate, WKNavigationDelegate,
                                  WKScriptMessageHandler {
  private let window: NSWindow
  private var webView: WKWebView!
  private let baseURL: URL
  private var lastFragment: String?
  var onRetry: (() -> Void)?

  init(baseURL: URL) {
    self.baseURL = baseURL
    window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1200, height: 800),
                      styleMask: [.titled, .closable, .miniaturizable, .resizable],
                      backing: .buffered, defer: false)
    super.init()
    let config = WKWebViewConfiguration()
    // Register before creating the web view: WKWebView retains its configuration at init.
    config.userContentController.add(self, name: "shellRetry")
    // With macOS keyboard navigation off (the default) WebKit's Tab skips buttons. Tab-to-links
    // makes Tab visit every control, like Safari's "Press Tab to highlight each item", without
    // touching the user's system setting.
    config.preferences.tabFocusesLinks = true
    webView = DeskWebView(frame: .zero, configuration: config)
    window.title = "LocalModelDesk"
    window.tabbingMode = .disallowed
    window.center()
    window.contentView = webView
    window.isReleasedWhenClosed = false
    window.delegate = self
    webView.navigationDelegate = self
  }

  func showWindow() {
    window.makeKeyAndOrderFront(nil)
    NSApp.activate(ignoringOtherApps: true)
  }

  /// Opens the window and forwards to the web shell's settings control.
  func showSettings() {
    showWindow()
    webView.evaluateJavaScript("document.querySelector('[data-open-settings]')?.click()")
  }

  /// Loads ui:deskShell, restoring the tab that was active before an error page replaced it.
  func loadDeskShell() {
    var url = baseURL
    if let fragment = lastFragment, var components = URLComponents(url: baseURL, resolvingAgainstBaseURL: false) {
      components.fragment = fragment
      url = components.url ?? baseURL
    }
    webView.load(URLRequest(url: url))
  }

  /// Closing the window hides it; the application and embedded server remain alive.
  func windowShouldClose(_ sender: NSWindow) -> Bool {
    window.orderOut(nil)
    return false
  }

  /// Displays an error page that stays available even when the service is down.
  /// D1/N7/N8: single dark theme, danger-accented title, log path folded behind 「详情」.
  func showErrorPage(reason: String, logPath: String, logTail: String = "") {
    lastFragment = webView.url?.fragment
    webView.loadHTMLString(errorPageHTML(reason: reason, logPath: logPath, logTail: logTail), baseURL: nil)
    showWindow()
  }

  func userContentController(_ userContentController: WKUserContentController,
                             didReceive message: WKScriptMessage) {
    if message.name == "shellRetry" { onRetry?() }
  }

  func webView(_ webView: WKWebView, didFailProvisionalNavigation navigation: WKNavigation!,
               withError error: Error) {
    showErrorPage(reason: "页面加载失败：\(error.localizedDescription)",
                  logPath: DeskPaths.serverStdoutLogURL.path)
  }
}

/// The default WKWebView context menu is not localized ("Reload"); name it in Chinese.
final class DeskWebView: WKWebView {
  override func willOpenMenu(_ menu: NSMenu, with event: NSEvent) {
    super.willOpenMenu(menu, with: event)
    for item in menu.items where item.identifier?.rawValue == "WKMenuItemIdentifierReload" {
      item.title = "重新载入"
    }
  }
}
