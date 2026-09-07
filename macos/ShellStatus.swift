import Foundation

/// Failure reasons used by the shell's server state.
enum ServerFailure: Error, Equatable {
  case noEmbeddedRuntime
  case portConflict(pids: [Int32])
  case healthTimeout(lastError: String)
  case spawnFailed(String)
}

/// State of the embedded desk service.
enum ServerState: Equatable {
  case stopped
  case starting
  case runningOwned(pid: Int32)
  case runningAttached
  case failed(ServerFailure)
}

/// Consumer projection of the arbiter's `data:deskState` contract.
struct DeskStateSnapshot: Equatable {
  var holderKind: String?
  var holderLabel: String?

  /// Ignores unknown fields, but rejects an absent or malformed `holder`.
  static func parse(_ object: Any) -> DeskStateSnapshot? {
    guard let dict = object as? [String: Any], let holderValue = dict["holder"] else {
      return nil
    }
    if holderValue is NSNull {
      return DeskStateSnapshot(holderKind: nil, holderLabel: nil)
    }
    guard let holder = holderValue as? [String: Any], let kind = holder["kind"] as? String else {
      return nil
    }
    return DeskStateSnapshot(holderKind: kind, holderLabel: holder["label"] as? String)
  }
}

/// Shell-owned status derived from service state, desk state, and configuration.
struct ShellStatus {
  var server: ServerState
  var desk: DeskStateSnapshot?
  var needsSetup: Bool
  var lastPollError: String?
}

/// The sole mapping from shell status to the menu-bar title.
func menuTitle(for status: ShellStatus) -> String {
  switch status.server {
  case .starting:
    return "启动中…"
  case .stopped, .failed:
    return "服务未运行"
  case .runningOwned, .runningAttached:
    break
  }

  if status.needsSetup { return "待设置" }
  guard let desk = status.desk else { return "状态不可读" }
  guard let kind = desk.holderKind else { return "空闲" }

  switch kind {
  case "llm": return "已加载 \(desk.holderLabel ?? "?")"
  case "video": return "出片中"
  case "music": return "出歌中"
  default: return "状态不可读"
  }
}

enum PollFailureAction: Equatable { case keepWaiting, serviceExited, serviceUnresponsive }

/// After `threshold` consecutive poll failures the shell must surface a problem whether or not
/// the child is alive: a hung service is as unusable as an exited one (cross-exam G19/G31).
func pollFailureAction(consecutiveFailures: Int, childRunning: Bool, threshold: Int = 3) -> PollFailureAction {
  if consecutiveFailures < threshold { return .keepWaiting }
  return childRunning ? .serviceUnresponsive : .serviceExited
}
