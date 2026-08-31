"""SubprocessExecutor real-process behavior."""
import os
import signal
import sys
import time

from desk.media.executor import SubprocessExecutor


def _wait_dead(pid: int, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.05)
    raise AssertionError(f"pid {pid} still alive")


def test_iter_output_merges_stdout_stderr_line_by_line():
    h = SubprocessExecutor().spawn([
        sys.executable, "-u", "-c",
        "import sys; print('out-1'); print('err-1', file=sys.stderr); print('out-2')"])
    lines = list(h.iter_output())
    assert h.wait() == 0
    assert sorted(lines) == ["err-1", "out-1", "out-2"]


def test_nonzero_exit_code_is_reported():
    h = SubprocessExecutor().spawn([sys.executable, "-c", "import os; os._exit(3)"])
    list(h.iter_output())
    assert h.wait() == 3
    assert h.poll() == 3


def test_extra_env_overlays_inherited_environment():
    h = SubprocessExecutor().spawn(
        [sys.executable, "-u", "-c",
         "import os; print(os.environ['LMD_PROBE']); print('PATH' in os.environ)"],
        extra_env={"LMD_PROBE": "42"})
    assert list(h.iter_output()) == ["42", "True"]
    assert h.wait() == 0


def test_terminate_signals_the_whole_process_group():
    prog = (
        "import os, subprocess, sys, time\n"
        "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])\n"
        "print('pids', os.getpid(), child.pid, flush=True)\n"
        "time.sleep(60)\n")
    h = SubprocessExecutor().spawn([sys.executable, "-u", "-c", prog])
    line = next(h.iter_output())
    _, parent_pid, child_pid = line.split()
    h.terminate()
    assert h.wait() == -signal.SIGTERM
    _wait_dead(int(parent_pid))
    _wait_dead(int(child_pid))


def test_kill_after_ignored_terminate():
    prog = ("import signal, time\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\n"
            "print('ready', flush=True)\n"
            "time.sleep(60)\n")
    h = SubprocessExecutor().spawn([sys.executable, "-u", "-c", prog])
    assert next(h.iter_output()) == "ready"
    h.terminate()
    time.sleep(0.3)
    assert h.poll() is None
    h.kill()
    assert h.wait() == -signal.SIGKILL
