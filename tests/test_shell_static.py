"""Static shell contracts for path, route, and Swift syntax boundaries."""
import os
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parent.parent
MACOS = ROOT / "macos"


def app_sources():
    files = sorted(MACOS.glob("*.swift"))
    assert files, "macos/*.swift does not exist"
    return files


def all_sources():
    return app_sources() + sorted((MACOS / "harness").glob("*.swift"))


def read_all(files):
    return {file: file.read_text(encoding="utf-8") for file in files}


def test_no_checkout_paths():
    for file, text in read_all(all_sources()).items():
        for needle in ("localModelDesk", "media-gui", "homeDirectoryForCurrentUser", "/opt/homebrew"):
            assert needle not in text, f"{file.name} contains forbidden string {needle!r}"


def test_no_launch_agent_writes():
    for file, text in read_all(all_sources()).items():
        for needle in ("LaunchAgents", "SMAppService", "LSSharedFileList", "loginItem"):
            assert needle not in text, f"{file.name} contains forbidden string {needle!r}"


def test_routes_only_in_deskapi():
    for file, text in read_all(app_sources()).items():
        if file.name != "DeskAPI.swift":
            assert '"/api/' not in text, f"{file.name} contains a route string"


def test_path_construction_only_in_deskpaths():
    for file, text in read_all(app_sources()).items():
        if file.name != "DeskPaths.swift":
            assert "applicationSupportDirectory" not in text
            assert "Bundle.main.resourceURL" not in text


def test_deskpaths_declares_frozen_contract():
    text = (MACOS / "DeskPaths.swift").read_text(encoding="utf-8")
    assert 'environment["LOCALMODELDESK_DATA_ROOT"]' in text
    assert '"LOCALMODELDESK_DATA_ROOT": userDataRoot.path' in text
    assert '"PYTHONDONTWRITEBYTECODE": "1"' in text
    assert '"LMD_SHELL_PORT": String(port)' in text
    assert "(1...65535).contains(value)" in text
    assert "workingDirectoryURL: resources" in text
    assert "python/bin/python3.13" in text
    assert '"-s", "-m", "desk"' in text
    assert "pylibs/desk" in text
    assert "bundle.json" in text
    assert "8766" in text and "8767" in text


def test_swiftc_parse():
    result = subprocess.run(
        ["xcrun", "swiftc", "-parse"] + [str(file) for file in all_sources()],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr


# ---- T-06 ui:mainWindow ----
def _read(name):
    return (MACOS / name).read_text(encoding="utf-8")


def test_main_window_close_hides_not_quits():
    text = _read("MainWindowController.swift")
    assert "windowShouldClose" in text
    assert "orderOut" in text
    assert "return false" in text


def test_main_window_error_page_mechanism():
    text = _read("MainWindowController.swift")
    assert "loadHTMLString" in text
    assert "shellRetry" in text
    assert "didFailProvisionalNavigation" in text
    assert "服务未运行" in text


def test_main_window_registers_retry_bridge_before_webview_creation():
    text = _read("MainWindowController.swift")
    bridge = 'config.userContentController.add(self, name: "shellRetry")'
    assert bridge in text
    assert text.index(bridge) < text.index("WKWebView(frame:"), (
        "shellRetry must be registered before WKWebView initializes its configuration"
    )


# ---- T-07 ui:menuBarItem ----
def test_status_item_mechanism():
    text = _read("StatusItemController.swift")
    assert "NSStatusBar.system.statusItem" in text
    assert "menuTitle(for:" in text
    assert "打开窗口" in text
    assert "退出" in text
    assert "menuWillOpen" in text


def test_status_poller_interval():
    text = _read("StatusPoller.swift")
    assert "3.0" in text
    assert "consecutiveFailures" in text


# ---- T-08 api:chooseModelsDirectory + FirstRunFlow ----
def test_chooser_panel_configuration():
    text = _read("ModelsDirectoryChooser.swift")
    assert "NSOpenPanel" in text
    assert "canChooseDirectories = true" in text
    assert "canChooseFiles = false" in text
    assert "canCreateDirectories = true" in text


def test_first_run_three_branches():
    text = _read("FirstRunFlow.swift")
    assert "使用默认目录" in text
    assert "选择其他目录…" in text
    assert "收编既有目录树…" in text
    assert "point" in text and "move" in text
    assert "completeFirstRun" in text and "adoptLegacyModels" in text
    assert "重选" in text


# ---- T-09 AppDelegate + main ----
def test_activation_policy_regular():
    combined = "\n".join(read_all(app_sources()).values())
    assert "setActivationPolicy(.regular)" in combined
    assert "LSUIElement" not in combined
    assert ".accessory" not in combined


def test_last_window_closed_does_not_terminate():
    text = _read("AppDelegate.swift")
    assert "applicationShouldTerminateAfterLastWindowClosed" in text
    import re
    match = re.search(r"applicationShouldTerminateAfterLastWindowClosed[^{]*\{[^}]*\}", text)
    assert match and "false" in match.group(0)


def test_main_menu_exposes_standard_editing_shortcuts():
    text = _read("AppDelegate.swift")
    for title, action, key in (
        ("撤销", "undo:", "z"), ("重做", "redo:", "z"),
        ("剪切", "NSText.cut", "x"), ("复制", "NSText.copy", "c"),
        ("粘贴", "NSText.paste", "v"), ("全选", "NSText.selectAll", "a"),
    ):
        assert f'withTitle: "{title}"' in text
        assert action in text
        assert f'keyEquivalent: "{key}"' in text
    assert "NSTextView.pasteAsPlainText" in text
    assert "[.command, .shift]" in text


def test_signal_paths_reap():
    main_text = _read("main.swift")
    assert "SIGTERM" in main_text and "SIGINT" in main_text
    assert "makeSignalSource" in main_text
    app_text = _read("AppDelegate.swift")
    assert "applicationWillTerminate" in app_text
    assert "terminateEmbeddedServer" in app_text
    assert "applicationShouldHandleReopen" in app_text
    assert "performClose" in app_text


def test_swiftc_typecheck_app():
    environment = os.environ.copy()
    environment["CLANG_MODULE_CACHE_PATH"] = "/private/tmp/lmd-swift-module-cache"
    result = subprocess.run(
        ["xcrun", "swiftc", "-typecheck"] + [str(file) for file in app_sources()],
        capture_output=True,
        text=True,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
