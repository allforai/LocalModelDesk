import Foundation

/// Swift's only location for path and port constants and path construction.
enum DeskPaths {
  static let port: Int =
    ProcessInfo.processInfo.environment["LMD_SHELL_PORT"].flatMap(Int.init) ?? 8766
  static let llmPort: Int = 8767

  static var baseURL: URL { URL(string: "http://127.0.0.1:\(port)")! }

  static var resourcesURL: URL? { Bundle.main.resourceURL }
  static var bundleMarkerURL: URL? { resourcesURL?.appendingPathComponent("bundle.json") }
  static var embeddedPythonURL: URL? {
    resourcesURL?.appendingPathComponent("python/bin/python3.13")
  }

  static let embeddedServerArguments = ["-s", "-m", "desk"]
  static func embeddedEnvironment(resources: URL) -> [String: String] {
    ["PYTHONPATH": "\(resources.path):\(resources.path)/pylibs/desk"]
  }

  static var userDataRoot: URL {
    FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
      .appendingPathComponent("LocalModelDesk")
  }
  static var serverStdoutLogURL: URL {
    userDataRoot.appendingPathComponent("logs/server-stdout.log")
  }

  /// Starts an embedded runtime only when the packaged bundle marker exists.
  static func makeLaunchSpec() -> ServerLaunchSpec {
    var launch: ServerLaunchCommand?
    if let marker = bundleMarkerURL,
       FileManager.default.fileExists(atPath: marker.path),
       let python = embeddedPythonURL,
       let resources = resourcesURL {
      launch = ServerLaunchCommand(
        executableURL: python,
        arguments: embeddedServerArguments,
        environment: embeddedEnvironment(resources: resources),
        familyPathPrefix: python.path)
    }
    return ServerLaunchSpec(
      launch: launch,
      port: port,
      llmPort: llmPort,
      healthPath: DeskAPI.statePath,
      logFileURL: serverStdoutLogURL)
  }
}
