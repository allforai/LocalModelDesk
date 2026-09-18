"""Replaceable subprocess execution interface and implementation."""
from __future__ import annotations

import os
import signal
import subprocess
from typing import Iterator, Protocol


class ProcessHandle(Protocol):
    """A running process, including its process group."""

    def iter_output(self) -> Iterator[str]: ...

    def wait(self) -> int: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def poll(self) -> int | None: ...


class Executor(Protocol):
    @property
    def pid(self) -> int: ...

    def spawn(
        self, cmd: list[str], *, extra_env: dict[str, str] | None = None
    ) -> ProcessHandle: ...


class SubprocessHandle:
    def __init__(self, proc: subprocess.Popen[str]) -> None:
        self._proc = proc

    @property
    def pid(self) -> int:
        """作业进程的 pid——仲裁器按它读这件重活实际驻留多少（R-budget-14）。"""
        return self._proc.pid

    def iter_output(self) -> Iterator[str]:
        assert self._proc.stdout is not None
        for line in self._proc.stdout:
            yield line.rstrip("\n")

    def wait(self) -> int:
        return self._proc.wait()

    def poll(self) -> int | None:
        return self._proc.poll()

    def _signal_group(self, sig: int) -> None:
        try:
            os.killpg(os.getpgid(self._proc.pid), sig)
        except ProcessLookupError:
            pass

    def terminate(self) -> None:
        self._signal_group(signal.SIGTERM)

    def kill(self) -> None:
        self._signal_group(signal.SIGKILL)


class SubprocessExecutor:
    """Spawn processes in independent sessions for group-wide cancellation."""

    def spawn(
        self, cmd: list[str], *, extra_env: dict[str, str] | None = None
    ) -> SubprocessHandle:
        env = {**os.environ, **extra_env} if extra_env else None
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            start_new_session=True,
            env=env,
        )
        return SubprocessHandle(proc)
