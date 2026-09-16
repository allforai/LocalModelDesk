import Foundation

/// The values a visual-acceptance capture has to read back from inside the running app: setting an axis
/// is not the same as the app rendering it, and a screenshot that cannot say what it is a screenshot of
/// is not evidence. Kept as one expression so the caller gets a single JSON object back.
let visualReadbackJS = """
(() => {
  const css = getComputedStyle(document.documentElement);
  // Only the visible pane counts: a hidden pane is still in the DOM and measures 0 everywhere, which
  // would report "no scrollbar" for every tab that is not the one the chat lives in.
  const pane = document.querySelector('main > section:not([hidden])') || document.body;
  const named = (el) => el ? (el.id ? '#' + el.id : el.className ? '.' + String(el.className).split(' ')[0] : el.tagName.toLowerCase()) : null;
  const candidates = [pane.querySelector('.messages'), pane.querySelector('.sessions'), pane,
                      document.scrollingElement].filter(Boolean);
  const scroller = candidates.find((el) => el.clientHeight > 0 && el.scrollHeight > el.clientHeight) || pane;
  const list = pane.querySelector('.sessions');
  const profile = (el) => el ? {
    scroll_width: el.scrollWidth, client_width: el.clientWidth,
    scroll_height: el.scrollHeight, client_height: el.clientHeight,
    gutter_px: el.offsetWidth - el.clientWidth
  } : null;
  return JSON.stringify({
    appearance: window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light',
    theme_attr: document.documentElement.getAttribute('data-theme'),
    locale: document.documentElement.lang || navigator.language,
    direction: css.direction,
    width: window.innerWidth,
    height: window.innerHeight,
    device_pixel_ratio: window.devicePixelRatio,
    root_font_px: parseFloat(css.fontSize),
    pointer: window.matchMedia('(pointer: coarse)').matches ? 'touch' : 'mouse',
    // Every axis the code declares support on owes the capture a value read back inside the app;
    // without these two a capture cannot prove it is the zoom level and orientation it claims.
    dynamic_type: '浏览器缩放 ' + Math.round((window.visualViewport ? window.visualViewport.scale : 1) * 100) + '%',
    orientation: window.innerWidth >= window.innerHeight ? 'landscape' : 'portrait',
    hover: window.matchMedia('(hover: hover)').matches,
    any_pointer_coarse: window.matchMedia('(any-pointer: coarse)').matches,
    scroll_profile: profile(scroller),
    scroll_source: named(scroller),
    pane: named(pane),
    session_list_profile: profile(list),
    tab: (location.hash || '#chat').slice(1)
  });
})()
"""

/// Why a probe request could not be answered (Result needs a real Error, and the text is the reply body).
struct ProbeFailure: Error {
  let message: String
  init(_ message: String) { self.message = message }
}

/// What the probe can ask of the window. The app fulfils it with the real WKWebView; the headless
/// harness fulfils it with canned values, so the HTTP surface is testable without a GUI.
protocol VisualProbeTarget: AnyObject {
  /// The app's own readback as a JSON object string.
  func probeReadback(_ done: @escaping (Result<String, ProbeFailure>) -> Void)
  /// Resizes the window's content to the requested logical size; answers with what was applied.
  func probeResize(width: Int, height: Int, _ done: @escaping (Result<String, ProbeFailure>) -> Void)
  /// A PNG of the web view as WebKit painted it — scrollbars included.
  func probeSnapshot(_ done: @escaping (Result<Data, ProbeFailure>) -> Void)
  /// Runs one expression in the page and answers with its value, so a capture can reach a state that
  /// only a click gets to (open the drawer, switch tabs, focus a control).
  func probeEval(_ javaScript: String, _ done: @escaping (Result<String, ProbeFailure>) -> Void)
}

/// A loopback-only HTTP surface for visual acceptance, started only when LMD_PROBE_PORT is set: a
/// capture run needs to set the window width, read back what the app actually rendered, and take the
/// picture, all from outside the app. It is never started by a normal launch.
final class VisualProbe {
  static let portEnvKey = "LMD_PROBE_PORT"

  private let port: UInt16
  private unowned let target: VisualProbeTarget
  private var listenFD: Int32 = -1

  init(port: UInt16, target: VisualProbeTarget) {
    self.port = port
    self.target = target
  }

  /// Reads the port from the environment; nil means "not a probe run", which is the normal case.
  static func configuredPort(_ environment: [String: String] = ProcessInfo.processInfo.environment) -> UInt16? {
    guard let raw = environment[portEnvKey], let value = UInt16(raw), value > 0 else { return nil }
    return value
  }

  func start() -> Bool {
    let fd = socket(AF_INET, SOCK_STREAM, 0)
    guard fd >= 0 else { return false }
    var yes: Int32 = 1
    setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &yes, socklen_t(MemoryLayout<Int32>.size))
    var addr = sockaddr_in()
    addr.sin_family = sa_family_t(AF_INET)
    addr.sin_port = port.bigEndian
    addr.sin_addr.s_addr = inet_addr("127.0.0.1")   // loopback only: never reachable from the network
    let bound = withUnsafePointer(to: &addr) {
      $0.withMemoryRebound(to: sockaddr.self, capacity: 1) { bind(fd, $0, socklen_t(MemoryLayout<sockaddr_in>.size)) }
    }
    guard bound == 0, listen(fd, 4) == 0 else { close(fd); return false }
    listenFD = fd
    Thread.detachNewThread { [weak self] in self?.acceptLoop(fd) }
    return true
  }

  func stop() {
    if listenFD >= 0 { close(listenFD); listenFD = -1 }
  }

  private func acceptLoop(_ fd: Int32) {
    while true {
      let client = accept(fd, nil, nil)
      if client < 0 { return }                     // the listener was closed
      handle(client)
      close(client)
    }
  }

  private func handle(_ client: Int32) {
    guard let request = readRequestLine(client) else { return }
    let (path, query) = VisualProbe.parseTarget(request)
    switch path {
    case "/readback":
      respond(client, awaitText { self.target.probeReadback($0) })
    case "/window":
      let width = Int(query["width"] ?? "") ?? 0
      let height = Int(query["height"] ?? "") ?? 0
      guard width > 0, height > 0 else {
        write(client, status: "400 Bad Request", type: "application/json",
              body: Data(#"{"error":"window needs width and height"}"#.utf8))
        return
      }
      respond(client, awaitText { self.target.probeResize(width: width, height: height, $0) })
    case "/eval":
      guard let raw = query["js"], let js = VisualProbe.percentDecoded(raw), !js.isEmpty else {
        write(client, status: "400 Bad Request", type: "application/json",
              body: Data(#"{"error":"eval needs a js= expression"}"#.utf8))
        return
      }
      respond(client, awaitText { self.target.probeEval(js, $0) })
    case "/snapshot":
      switch awaitValue({ self.target.probeSnapshot($0) }) {
      case .success(let png): write(client, status: "200 OK", type: "image/png", body: png)
      case .failure(let why): writeError(client, why.message)
      }
    default:
      write(client, status: "404 Not Found", type: "application/json",
            body: Data(#"{"error":"unknown probe route"}"#.utf8))
    }
  }

  private func respond(_ client: Int32, _ result: Result<String, ProbeFailure>) {
    switch result {
    case .success(let json): write(client, status: "200 OK", type: "application/json", body: Data(json.utf8))
    case .failure(let why): writeError(client, why.message)
    }
  }

  private func writeError(_ client: Int32, _ why: String) {
    let payload = ["error": why]
    let body = (try? JSONSerialization.data(withJSONObject: payload)) ?? Data(#"{"error":"probe failed"}"#.utf8)
    write(client, status: "500 Internal Server Error", type: "application/json", body: body)
  }

  /// The window work happens on the main thread; this accept thread waits for it.
  private func awaitValue<T>(_ work: @escaping (@escaping (Result<T, ProbeFailure>) -> Void) -> Void) -> Result<T, ProbeFailure> {
    var answer: Result<T, ProbeFailure> = .failure(ProbeFailure("probe timed out"))
    let done = DispatchSemaphore(value: 0)
    DispatchQueue.main.async { work { result in answer = result; done.signal() } }
    _ = done.wait(timeout: .now() + 10)
    return answer
  }

  private func awaitText(_ work: @escaping (@escaping (Result<String, ProbeFailure>) -> Void) -> Void) -> Result<String, ProbeFailure> {
    awaitValue(work)
  }

  /// Reads the request line and then drains the headers. Closing a socket that still has unread bytes
  /// in its receive buffer sends RST instead of FIN, and the client sees "connection reset" instead of
  /// the answer we just wrote — which showed up as a third of a capture run failing at random.
  private func readRequestLine(_ client: Int32) -> String? {
    var first: String?
    var line = Data()
    var byte: UInt8 = 0
    var total = 0
    while total < 16384 {
      let got = read(client, &byte, 1)
      if got <= 0 { break }
      total += 1
      if byte == 0x0A {
        let text = String(data: line, encoding: .utf8) ?? ""
        if first == nil { first = text }
        else if text.isEmpty { break }              // blank line: end of headers
        line.removeAll(keepingCapacity: true)
        continue
      }
      if byte != 0x0D { line.append(byte) }
    }
    guard let requestLine = first, !requestLine.isEmpty else { return nil }
    return requestLine
  }

  /// "GET /window?width=1280&height=800 HTTP/1.1" -> ("/window", ["width": "1280", "height": "800"])
  static func parseTarget(_ requestLine: String) -> (String, [String: String]) {
    let parts = requestLine.split(separator: " ")
    guard parts.count >= 2 else { return ("", [:]) }
    let target = String(parts[1])
    guard let mark = target.firstIndex(of: "?") else { return (target, [:]) }
    var query: [String: String] = [:]
    for pair in target[target.index(after: mark)...].split(separator: "&") {
      let kv = pair.split(separator: "=", maxSplits: 1)
      if kv.count == 2 { query[String(kv[0])] = String(kv[1]) }
    }
    return (String(target[target.startIndex..<mark]), query)
  }

  /// Query values arrive percent-encoded ("+" is a space, as in a form-encoded query).
  static func percentDecoded(_ raw: String) -> String? {
    raw.replacingOccurrences(of: "+", with: " ").removingPercentEncoding
  }

  private func write(_ client: Int32, status: String, type: String, body: Data) {
    let header = "HTTP/1.1 \(status)\r\nContent-Type: \(type)\r\nContent-Length: \(body.count)\r\nConnection: close\r\n\r\n"
    var payload = Data(header.utf8)
    payload.append(body)
    payload.withUnsafeBytes { raw in
      var sent = 0
      while sent < raw.count {
        let wrote = Foundation.write(client, raw.baseAddress!.advanced(by: sent), raw.count - sent)
        if wrote <= 0 { return }
        sent += wrote
      }
    }
  }
}
