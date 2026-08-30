import Cocoa
import WebKit

final class AppDelegate: NSObject, NSApplicationDelegate, WKNavigationDelegate {
  var window: NSWindow!
  var web: WKWebView!

  func applicationDidFinishLaunching(_ notification: Notification) {
    ensureServer()
    let screen = NSScreen.main?.visibleFrame ?? NSRect(x: 0, y: 0, width: 1280, height: 800)
    let size = NSSize(width: min(1280, screen.width), height: min(860, screen.height))
    let origin = NSPoint(
      x: screen.midX - size.width / 2,
      y: screen.midY - size.height / 2
    )
    window = NSWindow(
      contentRect: NSRect(origin: origin, size: size),
      styleMask: [.titled, .closable, .miniaturizable, .resizable],
      backing: .buffered,
      defer: false
    )
    window.title = "本地模型台"
    window.minSize = NSSize(width: 900, height: 600)
    web = WKWebView(frame: window.contentView!.bounds)
    web.autoresizingMask = [.width, .height]
    web.navigationDelegate = self
    window.contentView = web
    window.makeKeyAndOrderFront(nil)
    NSApp.activate(ignoringOtherApps: true)
    if let url = URL(string: "http://127.0.0.1:8766/") {
      web.load(URLRequest(url: url))
    }
  }

  func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool {
    true
  }

  private func ensureServer() {
    if urlOK("http://127.0.0.1:8766/") { return }
    let proc = Process()
    proc.executableURL = URL(fileURLWithPath: "/opt/homebrew/bin/python3")
    let gui = FileManager.default.homeDirectoryForCurrentUser
      .appendingPathComponent("localModelDesk/media-gui")
    proc.arguments = ["-u", gui.appendingPathComponent("server.py").path]
    proc.standardOutput = FileHandle(forWritingAtPath: gui.appendingPathComponent("desk.log").path)
    proc.standardError = proc.standardOutput
    do { try proc.run() } catch { return }
    for _ in 0..<30 {
      if urlOK("http://127.0.0.1:8766/") { return }
      Thread.sleep(forTimeInterval: 0.2)
    }
  }

  private func urlOK(_ raw: String) -> Bool {
    guard let url = URL(string: raw) else { return false }
    var req = URLRequest(url: url, timeoutInterval: 1)
    req.httpMethod = "GET"
    let sem = DispatchSemaphore(value: 0)
    var ok = false
    URLSession.shared.dataTask(with: req) { _, resp, _ in
      if let http = resp as? HTTPURLResponse, http.statusCode == 200 { ok = true }
      sem.signal()
    }.resume()
    _ = sem.wait(timeout: .now() + 1.2)
    return ok
  }
}

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
