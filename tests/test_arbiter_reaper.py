"""reap_port against real child processes on OS-assigned ephemeral ports."""
import contextlib
import socket
import subprocess
import sys

from desk.arbiter.reaper import ReapResult, _listening_pids, reap_port


CHILD = r"""
import signal, socket, sys, time
if "ignore-term" in sys.argv:
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
s = socket.socket()
s.bind(("127.0.0.1", 0))
s.listen(1)
print(s.getsockname()[1], flush=True)
time.sleep(120)
"""


def spawn_listener(*extra):
    proc = subprocess.Popen(
        [sys.executable, "-c", CHILD, *extra], stdout=subprocess.PIPE, text=True
    )
    port = int(proc.stdout.readline())
    return proc, port


@contextlib.contextmanager
def listener(*extra):
    proc, port = spawn_listener(*extra)
    try:
        yield proc, port
    finally:
        with contextlib.suppress(ProcessLookupError):
            proc.kill()
        proc.wait(timeout=10)


def test_reap_kills_foreign_listener():
    with listener() as (proc, port):
        result = reap_port(port, term_timeout=3.0, kill_timeout=3.0)
        assert result.ok is True
        assert proc.pid in result.killed_pids
        assert result.error is None
        assert _listening_pids(port) == []
        assert proc.wait(timeout=5) is not None


def test_empty_port_is_success_with_no_kills():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    assert reap_port(port) == ReapResult(ok=True, port=port, killed_pids=[])


def test_sigterm_immune_listener_falls_through_to_sigkill():
    with listener("ignore-term") as (proc, port):
        result = reap_port(port, term_timeout=0.5, kill_timeout=3.0)
        assert result.ok is True
        assert proc.pid in result.killed_pids
        assert _listening_pids(port) == []


def test_result_to_dict_shape():
    result = ReapResult(ok=True, port=1, killed_pids=[2]).to_dict()
    assert set(result) == {"ok", "port", "killed_pids", "error"}
