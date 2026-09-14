from pathlib import Path

from desk import __main__ as main_mod

REPO = Path(__file__).resolve().parent.parent


def test_runtime_port_reads_shell_contract(monkeypatch):
    monkeypatch.setenv("LMD_SHELL_PORT", "18766")
    assert main_mod.runtime_port() == 18766


def test_runtime_port_rejects_values_swift_host_cannot_bind(monkeypatch):
    for value in ("0", "-1", "65536", "not-a-port"):
        monkeypatch.setenv("LMD_SHELL_PORT", value)
        assert main_mod.runtime_port() == 8766


def test_service_becomes_its_own_process_group_leader(tmp_path):
    """壳靠 pgid 收割；服务必须是自己进程组的组长（R-shell-04）。"""
    import subprocess
    import sys
    import textwrap

    script = textwrap.dedent(
        """
        import os, sys
        sys.path.insert(0, %r)
        from desk.__main__ import ensure_own_process_group
        ensure_own_process_group()
        print(os.getpid(), os.getpgid(0))
        """
    ) % str(REPO)
    out = subprocess.run([sys.executable, "-c", script], capture_output=True, text=True, check=True)
    pid, pgid = (int(x) for x in out.stdout.split())
    assert pid == pgid


def test_parent_watchdog_stops_when_parent_disappears():
    """壳消失后服务不许继续占端口（R-shell-04 非正常退出路径）。"""
    import subprocess
    import threading

    from desk.__main__ import watch_parent

    # A pid known to be gone: spawn, wait for exit, reap — os.kill(pid, 0) then raises OSError,
    # exactly as it would once the real shell process has exited (-1 is a broadcast target on
    # this platform's os.kill, not a reliable "no such process" probe).
    gone = subprocess.Popen(["true"])
    gone.wait()

    stopped = threading.Event()
    watch_parent(parent_pid=gone.pid, interval=0.01, on_gone=stopped.set)
    assert stopped.wait(2.0)


def test_graceful_exit_shuts_down_once_then_exits():
    from desk.__main__ import graceful_exit

    calls = []
    runtime = type("R", (), {"shutdown": lambda self: calls.append("shutdown")})()
    graceful_exit(runtime, exit=lambda code: calls.append(("exit", code)))
    assert calls == ["shutdown", ("exit", 0)]


def test_graceful_exit_still_exits_when_shutdown_raises():
    from desk.__main__ import graceful_exit

    calls = []

    class Broken:
        def shutdown(self):
            raise RuntimeError("boom")

    graceful_exit(Broken(), exit=lambda code: calls.append(code))
    assert calls == [0]


def test_install_termination_runs_graceful_exit_off_the_signal_thread():
    import signal
    import threading

    from desk.__main__ import install_termination

    finished = threading.Event()
    seen = {}

    class Runtime:
        def shutdown(self):
            seen["thread"] = threading.current_thread().name

    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        install_termination(Runtime(), exit=lambda code: finished.set())
        handler = signal.getsignal(signal.SIGTERM)
        handler(signal.SIGTERM, None)
        assert finished.wait(2.0)
        assert seen["thread"] != threading.main_thread().name
    finally:
        for sig, old in previous.items():
            signal.signal(sig, old)
