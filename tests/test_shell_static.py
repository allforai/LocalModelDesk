"""Static shell contracts for path, route, and Swift syntax boundaries."""
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
