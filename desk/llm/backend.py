"""Subprocess boundary for the local mlx-lm server."""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Iterator, Protocol


class BackendProcess(Protocol):
    """The lifecycle operations used by :class:`LlmService`."""

    def poll(self) -> int | None: ...

    def terminate(self) -> None: ...

    def kill(self) -> None: ...

    def wait(self, timeout: float) -> None: ...


class LlmBackend(Protocol):
    """Injectable interface to a local OpenAI-compatible LLM backend."""

    def spawn(
        self, python: Path, model_path: Path, port: int, log_path: Path
    ) -> BackendProcess: ...

    def health(self, port: int) -> bool: ...

    def chat(self, port: int, payload: dict) -> dict: ...

    def chat_stream(self, port: int, payload: dict) -> Iterator[dict]: ...

    def log_tail(self, log_path: Path, max_lines: int = 40) -> str: ...


class MlxLmBackend:
    """Launches ``mlx_lm server`` and reads its diagnostic log."""

    def spawn(
        self, python: Path, model_path: Path, port: int, log_path: Path
    ) -> BackendProcess:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        argv = [
            str(python), "-s", "-m", "mlx_lm", "server",
            "--model", str(model_path), "--host", "127.0.0.1",
            "--port", str(port),
        ]
        with log_path.open("ab") as log_file:
            return subprocess.Popen(argv, stdout=log_file, stderr=log_file)

    def log_tail(self, log_path: Path, max_lines: int = 40) -> str:
        """Return the final log lines without masking a missing-log failure."""
        if max_lines <= 0:
            raise ValueError("max_lines must be positive")
        if not log_path.exists():
            return f"日志文件不存在: {log_path}"
        return "\n".join(log_path.read_text(encoding="utf-8", errors="replace").splitlines()[-max_lines:])
