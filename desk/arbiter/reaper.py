"""Kill listeners on a TCP port and verify that the port is free."""
from __future__ import annotations

import os
import signal
import subprocess
import time
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class ReapResult:
    ok: bool
    port: int
    killed_pids: list[int]
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _listening_pids(port: int) -> list[int]:
    """Return every other process listening on ``port``."""
    proc = subprocess.run(
        ["lsof", f"-tiTCP:{port}", "-sTCP:LISTEN"],
        capture_output=True,
        text=True,
    )
    pids = []
    for token in proc.stdout.split():
        try:
            pid = int(token)
        except ValueError:
            continue
        if pid != os.getpid():
            pids.append(pid)
    return pids


def _signal_and_wait(pids, sig, timeout, port, errors):
    """Signal PIDs and return the listeners remaining after ``timeout``."""
    for pid in pids:
        try:
            os.kill(pid, sig)
        except ProcessLookupError:
            pass
        except PermissionError:
            errors.append(f"EPERM sending signal {int(sig)} to pid {pid}")

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _listening_pids(port):
            return []
        time.sleep(0.1)
    return _listening_pids(port)


def reap_port(
    port: int,
    *,
    term_timeout: float = 5.0,
    kill_timeout: float = 3.0,
    owned_pids: set[int] | None = None,
) -> ReapResult:
    """TERM then KILL listeners we own; succeed only if the final check is empty.

    ``owned_pids`` scopes the kill to processes this arbiter actually spawned.
    A stranger listening on the port is never signaled, even if it never
    frees the port (P1: port reaping must verify ownership, same as the
    shell's path-prefix reaping).
    """
    errors: list[str] = []
    initial = _listening_pids(port)
    if not initial:
        return ReapResult(ok=True, port=port, killed_pids=[])
    if owned_pids is not None:
        initial = [pid for pid in initial if pid in owned_pids]
    if not initial:
        return ReapResult(ok=True, port=port, killed_pids=[])

    remaining = _signal_and_wait(initial, signal.SIGTERM, term_timeout, port, errors)
    if remaining:
        _signal_and_wait(remaining, signal.SIGKILL, kill_timeout, port, errors)

    still = _listening_pids(port)
    if still:
        message = f"pids {still} still listening after SIGKILL"
        if errors:
            message += "; " + "; ".join(errors)
        return ReapResult(
            ok=False,
            port=port,
            killed_pids=[pid for pid in initial if pid not in still],
            error=message,
        )
    return ReapResult(
        ok=True,
        port=port,
        killed_pids=initial,
        error="; ".join(errors) or None,
    )
