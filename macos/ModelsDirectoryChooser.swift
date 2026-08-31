import AppKit

/// api:chooseModelsDirectory — NSOpenPanel wrapper for the native first-run flow.
enum ModelsDirectoryChooser {
  static func choose(prompt: String) -> URL? {
    let panel = NSOpenPanel()
    panel.message = prompt
    panel.canChooseDirectories = true
    panel.canChooseFiles = false
    panel.canCreateDirectories = true
    panel.allowsMultipleSelection = false
    panel.prompt = "选择"
    return panel.runModal() == .OK ? panel.url : nil
  }
}
