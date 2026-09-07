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

/// The menubar glyph's coarse state, mapped from the same status the title text uses.
enum MenuGlyphState: String { case down, idle, loaded, busy }

/// The sole mapping from shell status to the menu-bar glyph variant.
func menuGlyphState(for status: ShellStatus) -> MenuGlyphState {
  switch status.server {
  case .starting, .stopped, .failed: return .down
  case .runningOwned, .runningAttached: break
  }
  guard let desk = status.desk else { return .down }
  guard let kind = desk.holderKind else { return .idle }
  return kind == "llm" ? .loaded : .busy
}

/// Dark, themed error page shown in place of ui:deskShell when the service is down or unresponsive.
func errorPageHTML(reason: String, logPath: String) -> String {
  func esc(_ s: String) -> String {
    s.replacingOccurrences(of: "&", with: "&amp;").replacingOccurrences(of: "<", with: "&lt;")
     .replacingOccurrences(of: ">", with: "&gt;").replacingOccurrences(of: "\"", with: "&quot;")
  }
  return """
  <!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>LocalModelDesk</title>
  <style>body{margin:0;min-height:100vh;display:grid;place-items:center;background:#14161a;color:#e7e9ee;font:14px/1.6 -apple-system,"PingFang SC",sans-serif}
  main{max-width:36em;padding:32px;background:#1d2026;border:1px solid #2c313a;border-radius:8px}h1{font-size:20px;margin:0 0 12px}
  code{font:13px ui-monospace,Menlo,monospace;color:#9aa3b2;word-break:break-all}
  button{margin-top:16px;padding:8px 12px;border-radius:6px;border:1px solid #4f8cff;background:#4f8cff;color:#fff;font:inherit;cursor:pointer}</style></head>
  <body><main><h1>服务未运行</h1><p id="reason">\(esc(reason))</p><p>日志：<code>\(esc(logPath))</code></p>
  <button onclick="window.webkit.messageHandlers.shellRetry.postMessage('retry')">重试</button></main></body></html>
  """
}

enum PollFailureAction: Equatable { case keepWaiting, serviceExited, serviceUnresponsive }

/// After `threshold` consecutive poll failures the shell must surface a problem whether or not
/// the child is alive: a hung service is as unusable as an exited one (cross-exam G19/G31).
func pollFailureAction(consecutiveFailures: Int, childRunning: Bool, threshold: Int = 3) -> PollFailureAction {
  if consecutiveFailures < threshold { return .keepWaiting }
  return childRunning ? .serviceUnresponsive : .serviceExited
}
