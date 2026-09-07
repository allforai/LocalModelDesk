import Foundation

/// Headless CLI compiled only by shell tests, not shipped in the app product.
@main
struct ShellHarness {
  static func main() {
    let args = Array(CommandLine.arguments.dropFirst())
    guard let command = args.first else {
      FileHandle.standardError.write(Data("usage: shellharness <map-status>\n".utf8))
      exit(64)
    }
    switch command {
    case "map-status": runMapStatus()
    case "glyph-state": print(menuGlyphState(for: parseStatusFixture()).rawValue)
    case "spawn-probe": runSpawn(Array(args.dropFirst()))
    case "run": runServer(Array(args.dropFirst()))
    case "listeners":
      guard args.count >= 2, let port = Int(args[1]) else { exit(64) }
      for pid in PortGuard.listeners(onPort: port) { print(pid) }
    case "ensure-free":
      guard args.count >= 2, let port = Int(args[1]) else { exit(64) }
      exit(PortGuard.ensureFree(port: port) ? 0 : 3)
    case "family":
      guard args.count >= 2 else { exit(64) }
      let pgrepTool = args.count >= 3 ? args[2] : "/usr/bin/pgrep"
      for pid in PortGuard.family(matching: args[1], pgrepTool: pgrepTool) { print(pid) }
    case "reap-family":
      guard args.count >= 2 else { exit(64) }
      let pgrepTool = args.count >= 3 ? args[2] : "/usr/bin/pgrep"
      PortGuard.reap(pids: PortGuard.family(matching: args[1], pgrepTool: pgrepTool), grace: 2.0)
      exit(PortGuard.family(matching: args[1], pgrepTool: pgrepTool).isEmpty ? 0 : 3)
    case "error-page":
      guard args.count >= 3 else { exit(64) }
      print(errorPageHTML(reason: args[1], logPath: args[2]))
    case "poll-failure":
      guard args.count >= 3, let failures = Int(args[1]) else { exit(64) }
      switch pollFailureAction(consecutiveFailures: failures, childRunning: args[2] == "true") {
      case .keepWaiting: print("keepWaiting")
      case .serviceExited: print("serviceExited")
      case .serviceUnresponsive: print("serviceUnresponsive")
      }
    default:
      FileHandle.standardError.write(Data("unknown subcommand \(command)\n".utf8))
      exit(64)
    }
  }

  /// Reads fixture JSON from stdin and builds the `ShellStatus` it describes.
  static func parseStatusFixture() -> ShellStatus {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    guard let object = try? JSONSerialization.jsonObject(with: data),
          let fixture = object as? [String: Any] else {
      FileHandle.standardError.write(Data("bad fixture JSON\n".utf8))
      exit(65)
    }

    let server: ServerState
    switch fixture["server"] as? String {
    case "starting": server = .starting
    case "stopped": server = .stopped
    case "failed": server = .failed(.spawnFailed("fixture"))
    case "attached": server = .runningAttached
    default: server = .runningOwned(pid: 1)
    }

    var desk: DeskStateSnapshot?
    if let deskState = fixture["desk_state"], !(deskState is NSNull) {
      desk = DeskStateSnapshot.parse(deskState)
    }
    return ShellStatus(
      server: server,
      desk: desk,
      needsSetup: fixture["needs_setup"] as? Bool ?? false,
      lastPollError: fixture["poll_error"] as? String
    )
  }

  /// Reads fixture JSON from stdin and writes its menu-title mapping to stdout.
  static func runMapStatus() {
    print(menuTitle(for: parseStatusFixture()))
  }

  static func parseSpec(_ args: [String]) -> ServerLaunchSpec {
    var port: Int?
    var launcher: String?
    var launcherArgs: [String] = []
    var logPath = NSTemporaryDirectory() + "shellharness-server.log"
    var spawnTimeout: TimeInterval = 15
    var termGrace: TimeInterval = 5
    var llmPort: Int?
    var familyPath: String?
    var index = 0

    while index < args.count {
      guard index + 1 < args.count else { exit(64) }
      let value = args[index + 1]
      switch args[index] {
      case "--port": port = Int(value)
      case "--launcher": launcher = value
      case "--launcher-arg": launcherArgs.append(value)
      case "--log": logPath = value
      case "--spawn-timeout": spawnTimeout = TimeInterval(value) ?? 15
      case "--term-grace": termGrace = TimeInterval(value) ?? 5
      case "--llm-port": llmPort = Int(value)
      case "--family-path": familyPath = value
      default:
        FileHandle.standardError.write(Data("unknown flag \(args[index])\n".utf8))
        exit(64)
      }
      index += 2
    }

    guard let port else {
      FileHandle.standardError.write(Data("--port is required\n".utf8))
      exit(64)
    }
    let launch = launcher.map {
      ServerLaunchCommand(executableURL: URL(fileURLWithPath: $0), arguments: launcherArgs,
                          environment: [:], familyPathPrefix: familyPath)
    }
    return ServerLaunchSpec(launch: launch, port: port, llmPort: llmPort,
                            healthPath: "/api/state",
                            logFileURL: URL(fileURLWithPath: logPath),
                            spawnTimeout: spawnTimeout, termGrace: termGrace)
  }

  static func runSpawn(_ args: [String]) {
    let controller = ServerController(spec: parseSpec(args))
    switch controller.spawnEmbeddedServer() {
    case .success(.runningAttached): print("ATTACHED")
    case .success(.runningOwned(let pid)): print("RUNNING \(pid)")
    case .success(let state):
      print("UNEXPECTED \(String(describing: state))")
      exit(70)
    case .failure(.noEmbeddedRuntime): print("NO_RUNTIME")
    case .failure(.portConflict(let pids)):
      print("PORT_CONFLICT \(pids.map(String.init).joined(separator: ","))")
    case .failure(.healthTimeout): print("HEALTH_TIMEOUT")
    case .failure(.spawnFailed(let reason)): print("SPAWN_FAILED \(reason)")
    }
    fflush(stdout)
    if case .failed = controller.state { exit(1) }
  }

  static func runServer(_ args: [String]) {
    let controller = ServerController(spec: parseSpec(args))
    switch controller.spawnEmbeddedServer() {
    case .success(.runningAttached): print("ATTACHED")
    case .success(.runningOwned(let pid)): print("RUNNING \(pid)")
    case .success:
      print("UNEXPECTED")
      exit(70)
    case .failure(.noEmbeddedRuntime): print("NO_RUNTIME")
    case .failure(.portConflict(let pids)):
      print("PORT_CONFLICT \(pids.map(String.init).joined(separator: ","))")
    case .failure(.healthTimeout): print("HEALTH_TIMEOUT")
    case .failure(.spawnFailed(let reason)): print("SPAWN_FAILED \(reason)")
    }
    fflush(stdout)
    if case .failed = controller.state { exit(1) }
    waitForSignalThenTerminate(controller)
  }

  static func waitForSignalThenTerminate(_ controller: ServerController) -> Never {
    signal(SIGTERM, SIG_IGN)
    signal(SIGINT, SIG_IGN)
    let finish: () -> Void = {
      let report = controller.terminateEmbeddedServer()
      let object: [String: Any] = [
        "port_free": report.portFree,
        "llm_port_free": report.llmPortFree as Any? ?? NSNull(),
        "killed_pids": report.killedPids.map(Int.init),
      ]
      if let data = try? JSONSerialization.data(withJSONObject: object) {
        FileHandle.standardOutput.write(data)
        FileHandle.standardOutput.write(Data("\n".utf8))
      }
      exit(report.portFree && report.llmPortFree != false ? 0 : 3)
    }
    let term = DispatchSource.makeSignalSource(signal: SIGTERM)
    let interrupt = DispatchSource.makeSignalSource(signal: SIGINT)
    term.setEventHandler(handler: finish)
    interrupt.setEventHandler(handler: finish)
    term.resume()
    interrupt.resume()
    dispatchMain()
  }
}
