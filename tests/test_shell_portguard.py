"""PortGuard：listeners/ensure-free/family/reap-family。全部随机端口 + tmp_path。"""
import subprocess

from shell_helpers import (FAKE_DESK_SERVER, free_port, harness_path,
                           port_listening, start_script)


def test_listeners_sees_fake_server():
    port = free_port()
    proc = start_script(FAKE_DESK_SERVER, port)
    try:
        out = subprocess.run([harness_path(), "listeners", str(port)],
                             capture_output=True, text=True, timeout=30)
        assert proc.pid in [int(x) for x in out.stdout.split()]
    finally:
        proc.kill()
        proc.wait()


def test_listeners_empty_on_idle_port():
    out = subprocess.run([harness_path(), "listeners", str(free_port())],
                         capture_output=True, text=True, timeout=30)
    assert out.stdout.strip() == ""


def test_ensure_free_kills_listener():
    port = free_port()
    proc = start_script(FAKE_DESK_SERVER, port)
    try:
        result = subprocess.run([harness_path(), "ensure-free", str(port)], timeout=60)
        assert result.returncode == 0
        proc.wait(timeout=10)
        assert not port_listening(port)
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def test_ensure_free_on_idle_port():
    assert subprocess.run([harness_path(), "ensure-free", str(free_port())],
                          timeout=60).returncode == 0


def test_family_and_reap(tmp_path):
    """Exercise the executable-path family query even where host pgrep is sandboxed."""
    fake = tmp_path / "python3.13-fake"
    fake.write_text("#!/usr/bin/env python3\nimport time\ntime.sleep(300)\n")
    fake.chmod(0o755)
    procs = [subprocess.Popen([str(fake)]) for _ in range(2)]
    pgrep = tmp_path / "pgrep-fixture"
    state = tmp_path / "pgrep-state"
    state.write_text("0")
    pgrep.write_text(
        "#!/bin/sh\n"
        "test \"$1\" = -f && test \"$2\" = \"$PORTGUARD_FAMILY_PATH\" || exit 64\n"
        "count=$(cat \"$PORTGUARD_PGREP_STATE\")\n"
        "echo $((count + 1)) > \"$PORTGUARD_PGREP_STATE\"\n"
        "test \"$count\" -ge 2 && exit 0\n"
        "for pid in $PORTGUARD_FAMILY_PIDS; do\n"
        "  kill -0 \"$pid\" 2>/dev/null && echo \"$pid\"\n"
        "done\n"
    )
    pgrep.chmod(0o755)
    env = {
        "PORTGUARD_FAMILY_PATH": str(fake),
        "PORTGUARD_FAMILY_PIDS": " ".join(str(proc.pid) for proc in procs),
        "PORTGUARD_PGREP_STATE": str(state),
    }
    try:
        out = subprocess.run([harness_path(), "family", str(fake), str(pgrep)],
                             capture_output=True, text=True, timeout=30, env=env)
        assert {p.pid for p in procs} <= {int(x) for x in out.stdout.split()}
        result = subprocess.run([harness_path(), "reap-family", str(fake), str(pgrep)],
                                timeout=60, env=env)
        assert result.returncode == 0
        for proc in procs:
            proc.wait(timeout=10)
    finally:
        for proc in procs:
            if proc.poll() is None:
                proc.kill()
                proc.wait()
