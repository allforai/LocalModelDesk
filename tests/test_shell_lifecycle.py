"""ServerController lifecycle: spawn, attach, terminate, and classified failures."""
import json
import os
import signal
import subprocess

import pytest

from shell_helpers import (FAKE_BAD_LISTENER, free_port, harness_path,
                           port_listening, start_fake_desk, start_script)


FAMILY_LAUNCHER = """\
#!/usr/bin/env python3
import http.server, json, subprocess, sys, time
if "--worker" in sys.argv:
    time.sleep(300)
    sys.exit(0)
port = int(sys.argv[1])
subprocess.Popen([sys.executable, sys.argv[0], "--worker"], start_new_session=True)
class H(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"holder": None, "media_busy": False, "can_start": {}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *a):
        pass
http.server.HTTPServer(("127.0.0.1", port), H).serve_forever()
"""


def probe(*extra, timeout=60):
    return subprocess.run([harness_path(), "spawn-probe", *extra],
                          capture_output=True, text=True, timeout=timeout)


def run_harness(*extra):
    return subprocess.Popen([harness_path(), "run", *extra],
                            stdout=subprocess.PIPE, text=True)


def read_line(proc):
    line = proc.stdout.readline().strip()
    assert line, "harness did not output a status line"
    return line


def write_launcher(tmp_path):
    launcher = tmp_path / "python3.13-embedded"
    launcher.write_text(FAMILY_LAUNCHER)
    launcher.chmod(0o755)
    return launcher


def test_attach_to_existing_service():
    port = free_port()
    fake = start_fake_desk(port)
    try:
        result = probe("--port", str(port))
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "ATTACHED"
        assert fake.poll() is None
    finally:
        fake.kill()
        fake.wait()


def test_port_conflict_never_kills_stranger():
    port = free_port()
    stranger = start_script(FAKE_BAD_LISTENER, port)
    try:
        result = probe("--port", str(port))
        assert result.returncode == 1
        assert result.stdout.startswith("PORT_CONFLICT")
        assert stranger.poll() is None
        assert port_listening(port)
    finally:
        stranger.kill()
        stranger.wait()


def test_no_runtime_without_launcher():
    result = probe("--port", str(free_port()))
    assert result.returncode == 1
    assert result.stdout.strip() == "NO_RUNTIME"


def test_health_timeout_terminates_child(tmp_path):
    marker = "987654321"
    result = probe("--port", str(free_port()), "--launcher", "/bin/sleep",
                   "--launcher-arg", marker, "--log", str(tmp_path / "server.log"),
                   "--spawn-timeout", "2")
    assert result.returncode == 1
    assert result.stdout.startswith("HEALTH_TIMEOUT")
    left = subprocess.run(["pgrep", "-f", f"sleep {marker}"], capture_output=True, text=True)
    assert left.stdout.strip() == ""


def test_spawn_writes_log(tmp_path):
    log = tmp_path / "logs" / "server.log"
    result = probe("--port", str(free_port()), "--launcher", "/bin/sleep",
                   "--launcher-arg", "123456789", "--log", str(log),
                   "--spawn-timeout", "1")
    assert result.returncode == 1
    assert log.exists()


def test_owned_sigterm_reaps_child_family_and_ports(tmp_path):
    port, llm_port = free_port(), free_port()
    launcher = write_launcher(tmp_path)
    harness = run_harness("--port", str(port), "--llm-port", str(llm_port),
                          "--launcher", str(launcher), "--launcher-arg", str(port),
                          "--family-path", str(launcher), "--term-grace", "0.2",
                          "--log", str(tmp_path / "server.log"))
    try:
        line = read_line(harness)
        assert line.startswith("RUNNING "), line
        child_pid = int(line.split()[1])
        assert port_listening(port)
        harness.send_signal(signal.SIGTERM)
        assert harness.wait(timeout=60) == 0
        report = json.loads(read_line(harness))
        assert report["port_free"] is True
        assert report["llm_port_free"] is True
        assert child_pid in report["killed_pids"]
        assert not port_listening(port)
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
        left = subprocess.run(["pgrep", "-f", str(launcher)], capture_output=True, text=True)
        assert left.stdout.strip() == ""
    finally:
        if harness.poll() is None:
            harness.kill()
        subprocess.run(["pkill", "-f", str(launcher)], capture_output=True)


def test_attached_sigterm_reaps_listener(tmp_path):
    port = free_port()
    fake = start_fake_desk(port)
    harness = run_harness("--port", str(port), "--log", str(tmp_path / "server.log"))
    try:
        assert read_line(harness) == "ATTACHED"
        harness.send_signal(signal.SIGTERM)
        assert harness.wait(timeout=60) == 0
        report = json.loads(read_line(harness))
        assert report["port_free"] is True
        assert report["llm_port_free"] is None
        assert not port_listening(port)
        fake.wait(timeout=10)
    finally:
        for proc in (harness, fake):
            if proc.poll() is None:
                proc.kill()
