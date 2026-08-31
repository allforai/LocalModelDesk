"""ServerController lifecycle: spawn, attach, and classified failures."""
import subprocess

from shell_helpers import (FAKE_BAD_LISTENER, free_port, harness_path,
                           port_listening, start_fake_desk, start_script)


def probe(*extra, timeout=60):
    return subprocess.run([harness_path(), "spawn-probe", *extra],
                          capture_output=True, text=True, timeout=timeout)


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
