import Foundation

/// Port listener detection, TERM-to-KILL reaping, and executable-path family cleanup.
/// This remains AppKit-free so the lifecycle harness can exercise it headlessly.
enum PortGuard {
  /// Uses the same port-listener semantics as the legacy unload script.
  static func listeners(onPort port: Int) -> [Int32] {
    parsePids(runCapture("/usr/sbin/lsof", ["-tiTCP:\(port)", "-sTCP:LISTEN"]))
  }

  /// Path-prefix match. Test/diagnostic only: it cannot tell our own children from a
  /// second instance of the same bundle, so it must never drive a reap (P1, 2026-09-08).
  static func family(matching pathPrefix: String, pgrepTool: String = "/usr/bin/pgrep") -> [Int32] {
    parsePids(runCapture(pgrepTool, ["-f", pathPrefix]))
      .filter { $0 != ProcessInfo.processInfo.processIdentifier }
  }

  /// Lists every live process in one process group — the only ownership-safe reap set.
  static func familyByGroup(pgid: Int32, psTool: String = "/bin/ps") -> [Int32] {
    parsePids(runCapture(psTool, ["-o", "pid=", "-g", String(pgid)]))
      .filter { $0 != ProcessInfo.processInfo.processIdentifier }
  }

  /// Reads one process's group id; nil when the process is gone.
  static func processGroup(of pid: Int32, psTool: String = "/bin/ps") -> Int32? {
    parsePids(runCapture(psTool, ["-o", "pgid=", "-p", String(pid)])).first
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
  /// Test seam: used only by macos/harness/ShellHarness.swift (ensure-free).
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
