"""Window-level shell behaviour acceptance (D-0002) via Orca computer."""
import functools
import json
import os
import signal
import subprocess
import tempfile
import time
from types import SimpleNamespace

import pytest

from shell_helpers import ROOT, free_port, harness_path, port_listening, start_fake_desk


ORCA = "orca"


@functools.lru_cache(maxsize=1)
def app_binary() -> str:
    scratch = tempfile.mkdtemp(prefix="shellapp-")
    proc = subprocess.run(
        [str(ROOT / "scripts" / "build-shell-app.sh"), scratch],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"App compilation failed:\n{proc.stderr}"
    return proc.stdout.strip().splitlines()[-1]


def orca_json(*args, timeout=60):
    result = subprocess.run(
        [ORCA, "computer", *args, "--json"],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    try:
        return result.returncode, json.loads(result.stdout)
    except (json.JSONDecodeError, ValueError):
        return result.returncode, {"raw": result.stdout, "stderr": result.stderr}


def tree_text(pid: int) -> str:
    code, obj = orca_json(
        "get-app-state", "--app", f"pid:{pid}", "--restore-window", "--no-screenshot"
    )
    if code != 0:
        return ""
    result = obj.get("result", obj)
    snapshot = result.get("snapshot", {}) if isinstance(result, dict) else {}
    return snapshot.get("treeText", "") or ""


def wait_for_window(pid: int, timeout=45) -> str:
    deadline = time.time() + timeout
    tree = ""
    while time.time() < deadline:
        tree = tree_text(pid)
        if tree.strip():
            return tree
        time.sleep(1.5)
    pytest.fail(f"no accessibility tree for App window within {timeout}s (pid {pid})")


def hotkey(pid: int, chord: str):
    code, obj = orca_json("hotkey", "--app", f"pid:{pid}", "--key", chord, "--no-screenshot")
    assert code == 0, f"orca hotkey failed: {obj}"


@pytest.fixture()
def shell_app():
    port = free_port()
    fake = start_fake_desk(port)
    env = dict(os.environ, LMD_SHELL_PORT=str(port))
    proc = subprocess.Popen(
        [app_binary()], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    ctx = SimpleNamespace(proc=proc, fake=fake, port=port)
    yield ctx
    for child in (proc, fake):
        if child.poll() is None:
            child.kill()
            child.wait()


def test_cmd_w_keeps_app_and_server_alive(shell_app):
    """R-shell-03: closing a window leaves App and attached service alive."""
    wait_for_window(shell_app.proc.pid)
    hotkey(shell_app.proc.pid, "CmdOrCtrl+W")
    time.sleep(3)
    assert shell_app.proc.poll() is None, "App must survive Cmd+W"
    assert port_listening(shell_app.port), "service must survive Cmd+W"
    assert shell_app.fake.poll() is None


def test_cmd_q_exits_app_and_spares_the_attached_service(shell_app):
    """R-shell-04 + G20: Quit exits App; a service it did not start survives.

    R-shell-04 only obliges the shell to terminate the *embedded* service — that
    path is covered by test_shell_lifecycle.test_owned_sigterm_reaps_child_family_and_ports.
    Here the listener belongs to a foreign process (the fake service the fixture
    starts), so quitting must observe it, never signal it.
    """
    wait_for_window(shell_app.proc.pid)
    hotkey(shell_app.proc.pid, "CmdOrCtrl+Q")
    deadline = time.time() + 30
    while time.time() < deadline and shell_app.proc.poll() is None:
        time.sleep(0.5)
    assert shell_app.proc.poll() is not None, "App must exit after Cmd+Q"
    assert shell_app.fake.poll() is None, "attached foreign service must survive quit"
    assert port_listening(shell_app.port), "foreign listener must still be serving"


def test_server_death_shows_error_text(shell_app):
    """R-shell-08: a killed service yields accessible error text, not a blank web view."""
    wait_for_window(shell_app.proc.pid)
    shell_app.fake.send_signal(signal.SIGKILL)
    shell_app.fake.wait(timeout=10)
    tree = ""
    deadline = time.time() + 40
    while time.time() < deadline:
        tree = tree_text(shell_app.proc.pid)
        if "服务未响应" in tree or "意外退出" in tree:
            break
        time.sleep(2)
    else:
        pytest.fail(f"no service-death explanation within 40s; last tree:\n{tree[-2000:]}")
    assert shell_app.proc.poll() is None


def test_main_window_disallows_tab_bar():
    """未拉的线 #8: 应用不支持多标签窗口，别让系统在窗口菜单里塞「显示标签页」。"""
    source = (ROOT / "macos" / "MainWindowController.swift").read_text()
    assert "tabbingMode = .disallowed" in source


def test_main_window_sets_a_900x600_content_floor():
    """issue #13: 899×600 已知会裂（模型下拉越出窗口、状态条「设置」折成两行），900×600 是干净的下限。

    不需要 GUI：走无 AppKit 的 headless harness，断言它打印的是 MainWindowController 实际引用的那个
    常量（macos/VisualProbe.swift 里的 MainWindowMinSize），而不是测试自己重新声明一份数字。
    """
    proc = subprocess.run([harness_path(), "window-min-size"], capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "900x600"

    source = (ROOT / "macos" / "MainWindowController.swift").read_text()
    assert "window.contentMinSize = NSSize(width: CGFloat(MainWindowMinSize.width)," in source


def test_error_page_is_dark_themed_and_names_the_reason():
    proc = subprocess.run([harness_path(), "error-page", "服务无响应", "/tmp/x.log"],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    html = proc.stdout
    assert "background:#14161a" in html and "color:#e7e9ee" in html
    assert "<h1 class=\"danger\">服务未响应</h1>" in html and "服务无响应" in html
    assert 'class="danger"' in html and "<details>" in html and "/tmp/x.log" in html
    assert 'onclick="window.webkit.messageHandlers.shellRetry.postMessage' in html
