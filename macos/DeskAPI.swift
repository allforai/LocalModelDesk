import Foundation

struct DeskAPIError: Error {
  let code: String
  let message: String
}

struct ConfigSnapshot {
  var needsSetup: Bool
}

struct MemoryLine {
  var usedBytes: Int64
  var totalBytes: Int64
  var availableBytes: Int64
}

/// The sole HTTP client; all service route strings belong here.
final class DeskAPI {
  static let statePath = "/api/state"
  static let memoryPath = "/api/memory"
  static let configPath = "/api/config"
  static let firstRunPath = "/api/first-run"
  static let adoptPath = "/api/adopt"

  let baseURL: URL
  private let session: URLSession

  init(baseURL: URL) {
    self.baseURL = baseURL
    let config = URLSessionConfiguration.ephemeral
    config.timeoutIntervalForRequest = 5
    self.session = URLSession(configuration: config)
  }

  func deskState(completion: @escaping (Result<DeskStateSnapshot, DeskAPIError>) -> Void) {
    request("GET", Self.statePath, body: nil) { result in
      completion(result.flatMap { object in
        guard let snapshot = DeskStateSnapshot.parse(object) else {
          return .failure(DeskAPIError(code: "bad_shape", message: "deskState shape is unreadable"))
        }
        return .success(snapshot)
      })
    }
  }

  func memorySnapshot(completion: @escaping (Result<MemoryLine, DeskAPIError>) -> Void) {
    request("GET", Self.memoryPath, body: nil) { result in
      completion(result.flatMap { object in
        guard let dictionary = object as? [String: Any],
              let total = (dictionary["total_bytes"] as? NSNumber)?.int64Value,
              let used = (dictionary["used_bytes"] as? NSNumber)?.int64Value,
              let available = (dictionary["available_bytes"] as? NSNumber)?.int64Value else {
          return .failure(DeskAPIError(code: "bad_shape", message: "memory snapshot is incomplete"))
        }
        return .success(MemoryLine(usedBytes: used, totalBytes: total, availableBytes: available))
      })
    }
  }

  func readConfig(completion: @escaping (Result<ConfigSnapshot, DeskAPIError>) -> Void) {
    request("GET", Self.configPath, body: nil) { result in
      completion(result.map { object in
        ConfigSnapshot(needsSetup: ((object as? [String: Any])?["needs_setup"] as? Bool) ?? false)
      })
    }
  }

  func completeFirstRun(modelsRoot: String?, completion: @escaping (Result<Void, DeskAPIError>) -> Void) {
    var body: [String: Any] = [:]
    if let modelsRoot { body["models_root"] = modelsRoot }
    request("POST", Self.firstRunPath, body: body) { completion($0.map { _ in () }) }
  }

  func adoptLegacyModels(legacyRoot: String, mode: String,
                         completion: @escaping (Result<Void, DeskAPIError>) -> Void) {
    request("POST", Self.adoptPath, body: ["legacy_root": legacyRoot, "mode": mode]) {
      completion($0.map { _ in () })
    }
  }

  private func request(_ method: String, _ path: String, body: [String: Any]?,
                       completion: @escaping (Result<Any, DeskAPIError>) -> Void) {
    guard let url = URL(string: baseURL.absoluteString + path) else {
      completion(.failure(DeskAPIError(code: "bad_url", message: path)))
      return
    }
    var request = URLRequest(url: url)
    request.httpMethod = method
    if let body {
      request.setValue("application/json", forHTTPHeaderField: "Content-Type")
      request.httpBody = try? JSONSerialization.data(withJSONObject: body)
    }
    session.dataTask(with: request) { data, response, error in
      if let error {
        completion(.failure(DeskAPIError(code: "transport", message: error.localizedDescription)))
        return
      }
      guard let response = response as? HTTPURLResponse else {
        completion(.failure(DeskAPIError(code: "transport", message: "no HTTP response")))
        return
      }
      let object = data.flatMap { try? JSONSerialization.jsonObject(with: $0) }
      guard (200..<300).contains(response.statusCode) else {
        if let envelope = (object as? [String: Any])?["error"] as? [String: Any],
           let code = envelope["code"] as? String {
          completion(.failure(DeskAPIError(code: code, message: envelope["message"] as? String ?? code)))
        } else {
          completion(.failure(DeskAPIError(code: "http_\(response.statusCode)",
                                           message: "HTTP \(response.statusCode)")))
        }
        return
      }
      guard let object else {
        completion(.failure(DeskAPIError(code: "bad_json", message: "response is not JSON")))
        return
      }
      completion(.success(object))
    }.resume()
  }
}
