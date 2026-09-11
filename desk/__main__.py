"""Run the Desk HTTP service."""
from __future__ import annotations
import os
import threading
import time

from .runtime import build_runtime


def ensure_own_process_group() -> None:
    """Become our own process group leader so the shell can reap us by pgid, never by path."""
    try:
        if os.getpgid(0) != os.getpid():
            os.setpgrp()
    except OSError:
        pass  # already a leader, or a platform without process groups


def watch_parent(parent_pid: int, *, interval: float = 3.0, on_gone=None) -> threading.Thread:
    """Exit with the shell: a force-killed parent must not leave the service holding ports."""

    def loop() -> None:
        while True:
            try:
                os.kill(parent_pid, 0)
            except OSError:
                (on_gone or (lambda: os._exit(0)))()
                return
            time.sleep(interval)

    thread = threading.Thread(target=loop, name="parent-watchdog", daemon=True)
    thread.start()
    return thread


def runtime_port() -> int:
    """Use the same overridable shell port contract as the native host."""
    try:
        port = int(os.environ.get("LMD_SHELL_PORT", "8766"))
    except ValueError:
        return 8766
    return port if 1 <= port <= 65535 else 8766


def main() -> None:
    ensure_own_process_group()
    parent = os.environ.get("LMD_PARENT_PID")
    if parent and parent.isdigit():
        watch_parent(int(parent))
    runtime = build_runtime(port=runtime_port())
    try:
        runtime.serve_forever()
    finally:
        runtime.shutdown()


if __name__ == "__main__":
    main()
