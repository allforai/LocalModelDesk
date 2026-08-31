import Foundation

/// Port listener detection, TERM-to-KILL reaping, and executable-path family cleanup.
/// This remains AppKit-free so the lifecycle harness can exercise it headlessly.
enum PortGuard {
  /// Uses the same port-listener semantics as the legacy unload script.
  static func listeners(onPort port: Int) -> [Int32] {
    parsePids(runCapture("/usr/sbin/lsof", ["-tiTCP:\(port)", "-sTCP:LISTEN"]))
  }

  /// Finds processes launched through a given executable path, including detached children.
  static func family(matching pathPrefix: String, pgrepTool: String = "/usr/bin/pgrep") -> [Int32] {
    parsePids(runCapture(pgrepTool, ["-f", pathPrefix]))
      .filter { $0 != ProcessInfo.processInfo.processIdentifier }
  }

  /// Sends TERM, waits through the grace period, then KILLs remaining processes.
  @discardableResult
  static func reap(pids: [Int32], grace: TimeInterval) -> [Int32] {
    guard !pids.isEmpty else { return [] }
    for pid in pids { kill(pid, SIGTERM) }
    let deadline = Date().addingTimeInterval(grace)
    while Date() < deadline && pids.contains(where: { kill($0, 0) == 0 }) {
      usleep(100_000)
    }
    for pid in pids where kill(pid, 0) == 0 { kill(pid, SIGKILL) }
    usleep(200_000)
    return pids
  }

  /// Confirms that no listener remains after reaping all listeners on the port.
  static func ensureFree(port: Int, grace: TimeInterval = 2.0) -> Bool {
    let pids = listeners(onPort: port)
    if pids.isEmpty { return true }
    reap(pids: pids, grace: grace)
    return listeners(onPort: port).isEmpty
  }

  private static func parsePids(_ text: String) -> [Int32] {
    text.split(whereSeparator: \.isNewline)
      .compactMap { Int32($0.trimmingCharacters(in: .whitespaces)) }
  }

  private static func runCapture(_ tool: String, _ args: [String]) -> String {
    let process = Process()
    process.executableURL = URL(fileURLWithPath: tool)
    process.arguments = args
    let pipe = Pipe()
    process.standardOutput = pipe
    process.standardError = FileHandle.nullDevice
    do { try process.run() } catch { return "" }
    let data = pipe.fileHandleForReading.readDataToEndOfFile()
    process.waitUntilExit()
    return String(data: data, encoding: .utf8) ?? ""
  }
}
