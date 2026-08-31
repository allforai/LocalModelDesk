import AppKit

let app = NSApplication.shared
let delegate = AppDelegate()
app.delegate = delegate

signal(SIGTERM, SIG_IGN)
signal(SIGINT, SIG_IGN)
let sigTerm = DispatchSource.makeSignalSource(signal: SIGTERM, queue: .main)
let sigInt = DispatchSource.makeSignalSource(signal: SIGINT, queue: .main)
for source in [sigTerm, sigInt] {
  source.setEventHandler { delegate.shutdownNow() }
  source.resume()
}

app.run()
