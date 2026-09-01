import Foundation

/// Swift's only location for path and port constants and path construction.
enum DeskPaths {
  static func validatedPort(_ raw: String?) -> Int {
    guard let raw, let value = Int(raw), (1...65535).contains(value) else { return 8766 }
    return value
  }
  static let port: Int = validatedPort(
    ProcessInfo.processInfo.environment["LMD_SHELL_PORT"])
  static let llmPort: Int = 8767

  static var baseURL: URL { URL(string: "http://127.0.0.1:\(port)")! }

  static var resourcesURL: URL? { Bundle.main.resourceURL }
  static var bundleMarkerURL: URL? { resourcesURL?.appendingPathComponent("bundle.json") }
  static var embeddedPythonURL: URL? {
    resourcesURL?.appendingPathComponent("python/bin/python3.13")
  }

  static let embeddedServerArguments = ["-s", "-m", "desk"]
  static func embeddedEnvironment(resources: URL) -> [String: String] {
    [
      "PYTHONPATH": "\(resources.path):\(resources.path)/pylibs/desk",
      "PYTHONDONTWRITEBYTECODE": "1",
      "LMD_SHELL_PORT": String(port),
      "LOCALMODELDESK_DATA_ROOT": userDataRoot.path,
    ]
  }

  static var userDataRoot: URL {
    if let override = ProcessInfo.processInfo.environment["LOCALMODELDESK_DATA_ROOT"],
       !override.isEmpty {
      let expanded = (override as NSString).expandingTildeInPath
      return URL(fileURLWithPath: expanded, isDirectory: true).standardizedFileURL
    }
    return FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
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
        familyPathPrefix: python.path,
        workingDirectoryURL: resources)
    }
    return ServerLaunchSpec(
      launch: launch,
      port: port,
      llmPort: llmPort,
      healthPath: DeskAPI.statePath,
      logFileURL: serverStdoutLogURL)
  }
}
