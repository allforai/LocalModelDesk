"""The capture driver records what the app rendered, in the shape a screenshot manifest wants.

Driven against the harness' canned window (tests/test_shell_visual_probe.py serves the same surface),
so the record's shape is pinned without a GUI.
"""
import importlib.util
import json
import subprocess
import time

import pytest

from shell_helpers import ROOT, free_port, harness_path, port_listening

spec = importlib.util.spec_from_file_location("visual_capture", ROOT / "scripts" / "visual-capture.py")
visual_capture = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visual_capture)


@pytest.fixture
def probe_port():
    port = free_port()
    proc = subprocess.Popen([harness_path(), "visual-probe", str(port)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 10
    while time.time() < deadline and not port_listening(port):
        time.sleep(0.05)
    assert port_listening(port), "probe never listened"
    try:
        yield port
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_capture_writes_the_image_its_record_names(tmp_path, probe_port):
    record = visual_capture.capture(probe_port, tmp_path, "V-abc123", 1280, 800, label="chat 默认")

    shot = tmp_path / "V-abc123.png"
    assert shot.read_bytes().startswith(b"\x89PNG\r\n\x1a\n")
    assert record["images"] == ["V-abc123.png"]
    assert record["image_digests"]["V-abc123.png"]
    written = json.loads((tmp_path / "V-abc123.json").read_text(encoding="utf-8"))
    assert written == record


def test_capture_records_the_readback_and_the_width_it_applied(tmp_path, probe_port):
    record = visual_capture.capture(probe_port, tmp_path, "V-abc123", 1280, 800)

    assert record["readback"]["appearance"] == "dark"
    assert record["readback"]["pointer"] == "mouse"
    assert record["window"]["width"] == 1280
    assert record["capture_mode"] == "viewport" and record["headless"] is False


def test_capture_records_the_state_it_set_up(tmp_path, probe_port):
    """A case named 'settings drawer open' is only that case if the drawer was actually opened."""
    record = visual_capture.capture(probe_port, tmp_path, "V-drawer", 1280, 800,
                                    before="document.querySelector('[data-open-settings]').click()")
    assert record["setup"]["js"] == "document.querySelector('[data-open-settings]').click()"
    assert "stub:" in record["setup"]["result"]["value"]


def test_capture_copies_the_frozen_case_axes_and_bindings(tmp_path, probe_port):
    """The manifest check compares capture against case on every axis; the row is the only source."""
    case = {"id": "V-x", "surface": "U4", "state": "默认", "device": "1400x900@2", "os": "macOS 26.0 WKWebView",
            "appearance": "dark", "dynamic_type": "浏览器缩放 100%", "locale": "zh-CN",
            "orientation": "landscape", "pointer": "mouse"}
    record = visual_capture.capture(probe_port, tmp_path, "V-x", 1400, 900, case=case,
                                    bindings={"baseline_digest": "abc", "matrix_digest": "def"})
    assert all(record[a] == case[a] for a in visual_capture.AXES)
    assert record["baseline_digest"] == "abc" and record["matrix_digest"] == "def"


def test_the_build_id_changes_with_the_working_tree(tmp_path, probe_port, monkeypatch):
    """A capture taken on a dirty tree must not claim the commit's build: two edits, two builds."""
    first = visual_capture.build_id()
    scratch = ROOT / "scripts" / ".visual-capture-build-probe.tmp"
    scratch.write_text("one", encoding="utf-8")
    try:
        assert visual_capture.build_id() != first
        scratch.write_text("two", encoding="utf-8")
        second = visual_capture.build_id()
        scratch.write_text("one", encoding="utf-8")
        assert visual_capture.build_id() != second
    finally:
        scratch.unlink(missing_ok=True)
    assert visual_capture.build_id() == first


def test_overlay_scrollbars_are_recorded_as_overlay_not_native(tmp_path, probe_port, monkeypatch):
    """`scrollbars` says what WebKit drew: no reserved gutter means the bar floated over the content."""
    original = visual_capture.probe

    def without_gutter(port, path, timeout=20):
        if path == "/readback":
            value = json.loads(original(port, path, timeout))
            value["scroll_profile"] = {"scroll_width": 800, "client_width": 800,
                                       "scroll_height": 2000, "client_height": 800, "gutter_px": 0}
            return json.dumps(value).encode("utf-8")
        return original(port, path, timeout)

    monkeypatch.setattr(visual_capture, "probe", without_gutter)
    record = visual_capture.capture(probe_port, tmp_path, "V-overlay", 1280, 800)
    assert record["scrollbars"] == "overlay"
