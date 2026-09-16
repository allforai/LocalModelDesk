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
    // Content size, not frame size (issue #13): below 900×600 known controls break (model dropdown
    // overflows, the status bar's 「设置」 button wraps). setContentSize (probeResize's /window route
    // included) clamps to this floor, which is exactly the point.
    window.contentMinSize = NSSize(width: CGFloat(MainWindowMinSize.width),
                                   height: CGFloat(MainWindowMinSize.height))
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

/// Visual acceptance captures the real window: WebKit draws scrollbars, focus rings and font
/// smoothing differently from the headless browser the e2e suite drives, and those differences are
/// exactly what a visual reviewer is asked about. Only reachable when LMD_PROBE_PORT is set.
extension MainWindowController: VisualProbeTarget {
  func probeReadback(_ done: @escaping (Result<String, ProbeFailure>) -> Void) {
    webView.evaluateJavaScript(visualReadbackJS) { value, error in
      if let error { return done(.failure(ProbeFailure("readback failed: \(error.localizedDescription)"))) }
      guard let json = value as? String else { return done(.failure(ProbeFailure("readback returned no JSON"))) }
      done(.success(json))
    }
  }

  func probeResize(width: Int, height: Int, _ done: @escaping (Result<String, ProbeFailure>) -> Void) {
    // contentMinSize constrains live (user) resizing only; setContentSize walks past it, so the probe
    // clamps explicitly — it must not park the window at a size no user could drag it to (issue #13,
    // measured 2026-09-17: a /window?width=400 request was applied verbatim before this).
    let floored = MainWindowMinSize.clamped(width: width, height: height)
    window.setContentSize(NSSize(width: floored.width, height: floored.height))
    showWindow()
    // The web view learns its new size on the next layout pass; answering earlier would hand the
    // capture a width the page has not applied yet.
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.3) {
      // webView.bounds, not the requested width/height: this reports what actually got applied
      // (post-clamp), never the raw request — that is the readback a capture needs to be evidence.
      let size = self.webView.bounds.size
      let payload: [String: Any] = ["width": Int(size.width), "height": Int(size.height),
                                    "window_number": self.window.windowNumber,
                                    "backing_scale": self.window.backingScaleFactor]
      guard let data = try? JSONSerialization.data(withJSONObject: payload),
            let json = String(data: data, encoding: .utf8) else {
        return done(.failure(ProbeFailure("could not describe the window")))
      }
      done(.success(json))
    }
  }

  func probeEval(_ javaScript: String, _ done: @escaping (Result<String, ProbeFailure>) -> Void) {
    webView.evaluateJavaScript(javaScript) { value, error in
      if let error { return done(.failure(ProbeFailure("eval failed: \(error.localizedDescription)"))) }
      // Answer as one JSON object whatever the expression produced, including nothing at all.
      let payload: Any = value ?? NSNull()
      let wrapped: [String: Any] = JSONSerialization.isValidJSONObject(["value": payload])
        ? ["value": payload] : ["value": String(describing: payload)]
      guard let data = try? JSONSerialization.data(withJSONObject: wrapped),
            let json = String(data: data, encoding: .utf8) else {
        return done(.failure(ProbeFailure("eval result could not be described")))
      }
      done(.success(json))
    }
  }

  func probeSnapshot(_ done: @escaping (Result<Data, ProbeFailure>) -> Void) {
    let config = WKSnapshotConfiguration()
    // Waiting for a screen update deadlocks whenever the window is occluded — which it is for most of a
    // capture run, since the driver is a terminal in front of it. The caller already waits for the page
    // to settle after the resize, so snapshot what is rendered now.
    config.afterScreenUpdates = false
    webView.takeSnapshot(with: config) { image, error in
      if let error { return done(.failure(ProbeFailure("snapshot failed: \(error.localizedDescription)"))) }
      guard let image, let tiff = image.tiffRepresentation,
            let bitmap = NSBitmapImageRep(data: tiff),
            let png = bitmap.representation(using: .png, properties: [:]) else {
        return done(.failure(ProbeFailure("snapshot produced no PNG")))
      }
      done(.success(png))
    }
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
