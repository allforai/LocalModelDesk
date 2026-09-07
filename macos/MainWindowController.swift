import AppKit
import WebKit

/// ui:mainWindow — hosts ui:deskShell in a WKWebView and provides a local error page.
final class MainWindowController: NSObject, NSWindowDelegate, WKNavigationDelegate,
                                  WKScriptMessageHandler {
  private let window: NSWindow
  private var webView: WKWebView!
  private let baseURL: URL
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
    webView = WKWebView(frame: .zero, configuration: config)
    window.title = "LocalModelDesk"
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

  var isWindowVisible: Bool { window.isVisible }

  /// Loads ui:deskShell.
  func loadDeskShell() {
    webView.load(URLRequest(url: baseURL))
  }

  /// Closing the window hides it; the application and embedded server remain alive.
  func windowShouldClose(_ sender: NSWindow) -> Bool {
    window.orderOut(nil)
    return false
  }

  /// Displays an error page that stays available even when the service is down.
  func showErrorPage(reason: String, logPath: String) {
    let html = """
    <!doctype html><html><head><meta charset="utf-8"><title>LocalModelDesk</title></head>
    <body style="font-family: -apple-system, sans-serif; padding: 2em; max-width: 40em; margin: auto;">
      <h1>服务未运行</h1>
      <p id="reason">\(Self.escapeHTML(reason))</p>
      <p>日志：<code>\(Self.escapeHTML(logPath))</code></p>
      <button onclick="window.webkit.messageHandlers.shellRetry.postMessage('retry')">重试</button>
    </body></html>
    """
    webView.loadHTMLString(html, baseURL: nil)
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

  private static func escapeHTML(_ string: String) -> String {
    string.replacingOccurrences(of: "&", with: "&amp;")
      .replacingOccurrences(of: "<", with: "&lt;")
      .replacingOccurrences(of: ">", with: "&gt;")
  }
}
