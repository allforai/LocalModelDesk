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
  /// D1/N7/N8: single dark theme, danger-accented title, log path folded behind 「详情」.
  func showErrorPage(reason: String, logPath: String) {
    let html = """
    <!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>LocalModelDesk</title>
    <style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#14161a;color:#e7e9ee;font:14px/1.6 -apple-system,"PingFang SC",sans-serif}
    main{max-width:36em;padding:32px;background:#1d2026;border:1px solid #2c313a;border-left:4px solid #e5534b;border-radius:8px}
    h1{font-size:20px;margin:0 0 12px;color:#e5534b}h1::before{content:"✕ "}
    .danger{color:#e5534b}details{margin-top:12px;color:#9aa3b2;font-size:13px}summary{cursor:pointer}
    code{font:13px ui-monospace,Menlo,monospace;color:#9aa3b2;word-break:break-all}
    button{margin-top:16px;padding:8px 12px;border-radius:6px;border:1px solid #4f8cff;background:#4f8cff;color:#fff;font:inherit;cursor:pointer}</style></head>
    <body><main><h1 class="danger">服务未响应</h1><p id="reason">\(Self.escapeHTML(reason))</p>
    <details><summary>详情</summary><p>日志：<code>\(Self.escapeHTML(logPath))</code></p></details>
    <button onclick="window.webkit.messageHandlers.shellRetry.postMessage('retry')">重试</button></main></body></html>
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
