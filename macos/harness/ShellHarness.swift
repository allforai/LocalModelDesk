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
    default:
      FileHandle.standardError.write(Data("unknown subcommand \(command)\n".utf8))
      exit(64)
    }
  }

  /// Reads fixture JSON from stdin and writes its menu-title mapping to stdout.
  static func runMapStatus() {
    let data = FileHandle.standardInput.readDataToEndOfFile()
    guard let object = try? JSONSerialization.jsonObject(with: data),
          let fixture = object as? [String: Any] else {
      FileHandle.standardError.write(Data("map-status: bad fixture JSON\n".utf8))
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
    let status = ShellStatus(
      server: server,
      desk: desk,
      needsSetup: fixture["needs_setup"] as? Bool ?? false,
      lastPollError: fixture["poll_error"] as? String
    )
    print(menuTitle(for: status))
  }
}
