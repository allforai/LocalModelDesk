"""The visual-acceptance probe surface: the routes a capture run drives, without a GUI.

A capture has to set the window width, read back what the app actually rendered, and take the picture
from outside the app. These tests pin the HTTP contract against the harness' canned window; the real
window's answers are the app's job (macos/MainWindowController.swift).
"""
import json
import subprocess
import time
import urllib.error
import urllib.request

import pytest

from shell_helpers import free_port, harness_path, port_listening


@pytest.fixture
def probe():
    """The harness serving the probe on a free port; stopped when the test ends."""
    port = free_port()
    proc = subprocess.Popen([harness_path(), "visual-probe", str(port)],
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    deadline = time.time() + 10
    while time.time() < deadline and not port_listening(port):
        if proc.poll() is not None:
            raise AssertionError("probe exited: " + (proc.stderr.read() if proc.stderr else ""))
        time.sleep(0.05)
    assert port_listening(port), "probe never listened"
    try:
        yield port
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def get(port, path):
    with urllib.request.urlopen(f"http://127.0.0.1:{port}{path}", timeout=10) as response:
        return response.status, response.headers.get("Content-Type"), response.read()


def test_readback_answers_json_the_capture_can_record(probe):
    status, content_type, body = get(probe, "/readback")
    assert status == 200 and content_type == "application/json"
    assert json.loads(body)["appearance"] == "dark"


def test_window_applies_a_width_and_names_the_window(probe):
    """The device axis needs both ends of the width range; the capture sets them through this route."""
    status, _, body = get(probe, "/window?width=1280&height=800")
    assert status == 200
    applied = json.loads(body)
    assert (applied["width"], applied["height"]) == (1280, 800)
    assert applied["window_number"] == 42        # screencapture -l needs it for the whole-window shot


def test_window_without_a_size_is_refused(probe):
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(probe, "/window")
    assert caught.value.code == 400


def test_snapshot_returns_png_bytes(probe):
    status, content_type, body = get(probe, "/snapshot")
    assert status == 200 and content_type == "image/png"
    assert body.startswith(b"\x89PNG\r\n\x1a\n")


def test_eval_runs_an_expression_in_the_page(probe):
    """A capture reaches a state only a click gets to — the drawer, another tab — through this route."""
    status, content_type, body = get(probe, "/eval?js=document.title")
    assert status == 200 and content_type == "application/json"
    assert json.loads(body)["value"] == "stub:document.title"


def test_eval_decodes_the_expression_it_was_given(probe):
    status, _, body = get(probe, "/eval?js=location.hash%20%3D%20%27%23tab%3Dvideo%27")
    assert json.loads(body)["value"] == "stub:location.hash = '#tab=video'"


def test_eval_without_an_expression_is_refused(probe):
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(probe, "/eval")
    assert caught.value.code == 400


def test_unknown_route_is_refused(probe):
    with pytest.raises(urllib.error.HTTPError) as caught:
        get(probe, "/whatever")
    assert caught.value.code == 404


def test_a_launch_without_the_env_var_opens_no_probe():
    """The probe is capture-only infrastructure: a normal launch must not open a port at all."""
    plain = subprocess.run([harness_path(), "probe-port"], capture_output=True, text=True)
    assert plain.stdout.strip() == "none"
    asked = subprocess.run([harness_path(), "probe-port"], capture_output=True, text=True,
                           env={"LMD_PROBE_PORT": "8771", "PATH": "/usr/bin:/bin"})
    assert asked.stdout.strip() == "8771"
