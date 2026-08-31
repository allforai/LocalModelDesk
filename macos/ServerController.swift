import Foundation

/// The bundled interpreter invocation and its deliberately explicit environment.
struct ServerLaunchCommand {
  var executableURL: URL
  var arguments: [String]
  var environment: [String: String]
  var familyPathPrefix: String?
}

/// All server lifecycle inputs are injectable so the headless harness uses production code.
struct ServerLaunchSpec {
  var launch: ServerLaunchCommand?
  var port: Int
  var llmPort: Int?
  var healthPath: String
  var logFileURL: URL
  var spawnTimeout: TimeInterval = 15
  var termGrace: TimeInterval = 5
}

struct TerminateReport {
  var portFree: Bool
  var llmPortFree: Bool?
  var killedPids: [Int32]
}

/// Starts the embedded Desk server, or safely adopts an already healthy one.
final class ServerController {
  private let spec: ServerLaunchSpec
  private var child: Process?
  private(set) var state: ServerState = .stopped

  init(spec: ServerLaunchSpec) { self.spec = spec }

  var isChildRunning: Bool { child?.isRunning ?? false }

  func spawnEmbeddedServer() -> Result<ServerState, ServerFailure> {
    state = .starting
    if healthCheckOK() {
      state = .runningAttached
      return .success(state)
    }

    let occupants = PortGuard.listeners(onPort: spec.port)
    if !occupants.isEmpty { return fail(.portConflict(pids: occupants)) }
    guard let launch = spec.launch else { return fail(.noEmbeddedRuntime) }

    let process = Process()
    process.executableURL = launch.executableURL
    process.arguments = launch.arguments
    var environment = ProcessInfo.processInfo.environment
    for (key, value) in launch.environment { environment[key] = value }
    process.environment = environment

    do {
      try FileManager.default.createDirectory(
        at: spec.logFileURL.deletingLastPathComponent(), withIntermediateDirectories: true)
      if !FileManager.default.fileExists(atPath: spec.logFileURL.path) {
        FileManager.default.createFile(atPath: spec.logFileURL.path, contents: nil)
      }
      let log = try FileHandle(forWritingTo: spec.logFileURL)
      log.seekToEndOfFile()
      process.standardOutput = log
      process.standardError = log
      try process.run()
    } catch {
      return fail(.spawnFailed(String(describing: error)))
    }

    child = process
    let deadline = Date().addingTimeInterval(spec.spawnTimeout)
    while Date() < deadline {
      if healthCheckOK() {
        state = .runningOwned(pid: process.processIdentifier)
        return .success(state)
      }
      if !process.isRunning {
        child = nil
        return fail(.spawnFailed("service exited while starting; see \(spec.logFileURL.path)"))
      }
      usleep(200_000)
    }

    PortGuard.reap(pids: [process.processIdentifier], grace: 2.0)
    child = nil
    return fail(.healthTimeout(lastError: "\(Int(spec.spawnTimeout))s elapsed without 200 JSON from \(spec.healthPath)"))
  }

  private func fail(_ failure: ServerFailure) -> Result<ServerState, ServerFailure> {
    state = .failed(failure)
    return .failure(failure)
  }

  /// A listener is adoptable only if it serves a successful JSON health response.
  private func healthCheckOK() -> Bool {
    guard let url = URL(string: "http://127.0.0.1:\(spec.port)\(spec.healthPath)") else {
      return false
    }
    var request = URLRequest(url: url)
    request.timeoutInterval = 1.0
    let semaphore = DispatchSemaphore(value: 0)
    var ok = false
    URLSession.shared.dataTask(with: request) { data, response, _ in
      if let response = response as? HTTPURLResponse, response.statusCode == 200,
         let data, (try? JSONSerialization.jsonObject(with: data)) != nil {
        ok = true
      }
      semaphore.signal()
    }.resume()
    semaphore.wait()
    return ok
  }
}
