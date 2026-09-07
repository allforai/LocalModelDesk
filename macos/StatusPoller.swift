import Foundation

/// Polls data:deskState every three seconds instead of maintaining an event channel.
final class StatusPoller {
  private let api: DeskAPI
  private var timer: Timer?
  private(set) var consecutiveFailures = 0
  var onUpdate: ((Result<DeskStateSnapshot, DeskAPIError>) -> Void)?
  var onMemory: ((Result<MemoryLine, DeskAPIError>) -> Void)?

  init(api: DeskAPI) { self.api = api }

  func start(interval: TimeInterval = 3.0) {
    stop()
    let timer = Timer(timeInterval: interval, repeats: true) { [weak self] _ in
      self?.pollOnce()
    }
    RunLoop.main.add(timer, forMode: .common)
    self.timer = timer
    pollOnce()
  }

  func stop() {
    timer?.invalidate()
    timer = nil
  }

  private func pollOnce() {
    api.deskState { [weak self] result in
      DispatchQueue.main.async {
        guard let self else { return }
        if case .failure = result {
          self.consecutiveFailures += 1
        } else {
          self.consecutiveFailures = 0
        }
        self.onUpdate?(result)
      }
    }
    api.memorySnapshot { [weak self] result in
      RunLoop.main.perform(inModes: [.common]) { self?.onMemory?(result) }
    }
  }
}
