import AppKit

/// R-shell-07: native first-run orchestration when api:readConfig needs setup.
final class FirstRunFlow {
  private let api: DeskAPI

  init(api: DeskAPI) { self.api = api }

  /// Returns true after configuration is persisted, false when the user cancels.
  func run() -> Bool {
    while true {
      let alert = NSAlert()
      alert.messageText = "首次设置：模型放在哪？"
      alert.informativeText = "默认位置是「资源库/Application Support/LocalModelDesk/models」。"
      alert.addButton(withTitle: "使用默认目录")
      alert.addButton(withTitle: "选择其他目录…")
      alert.addButton(withTitle: "收编既有目录树…")
      switch alert.runModal() {
      case .alertFirstButtonReturn:
        if post({ self.api.completeFirstRun(modelsRoot: nil, completion: $0) }) { return true }
      case .alertSecondButtonReturn:
        guard let directory = ModelsDirectoryChooser.choose(prompt: "选择模型存放目录") else {
          return false
        }
        if post({ self.api.completeFirstRun(modelsRoot: directory.path, completion: $0) }) {
          return true
        }
      case .alertThirdButtonReturn:
        guard let legacyRoot = ModelsDirectoryChooser.choose(prompt: "选择既有模型目录树的根") else {
          return false
        }
        let modeAlert = NSAlert()
        modeAlert.messageText = "收编方式"
        modeAlert.informativeText = "指向：模型留在原地；移动：搬到默认目录。"
        modeAlert.addButton(withTitle: "指向该目录")
        modeAlert.addButton(withTitle: "移动到默认目录")
        let mode = modeAlert.runModal() == .alertFirstButtonReturn ? "point" : "move"
        if post({ self.api.adoptLegacyModels(legacyRoot: legacyRoot.path, mode: mode, completion: $0) }) {
          return true
        }
      default:
        return false
      }
    }
  }

  /// Waits for a foundation POST and exposes its original error before retrying.
  private func post(_ operation: (@escaping (Result<Void, DeskAPIError>) -> Void) -> Void) -> Bool {
    let semaphore = DispatchSemaphore(value: 0)
    var outcome: Result<Void, DeskAPIError> =
      .failure(DeskAPIError(code: "no_response", message: "服务无响应"))
    operation { result in
      outcome = result
      semaphore.signal()
    }
    semaphore.wait()
    switch outcome {
    case .success:
      return true
    case .failure(let error):
      let alert = NSAlert()
      alert.messageText = "设置失败"
      alert.informativeText = "\(error.code)：\(error.message)"
      alert.addButton(withTitle: "重选")
      alert.runModal()
      return false
    }
  }
}
