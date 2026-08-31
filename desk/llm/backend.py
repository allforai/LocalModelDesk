"""Subprocess boundary for the local mlx-lm server."""
from __future__ import annotations

import http.client
import json
import subprocess
from pathlib import Path
from typing import Iterator, Protocol


class BackendHttpError(Exception):
    """An mlx-lm HTTP request failed."""


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

    def health(self, port: int) -> bool:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=1.0)
        try:
            conn.request("GET", "/v1/models")
            return conn.getresponse().status == 200
        except OSError:
            return False
        finally:
            conn.close()

    def chat(self, port: int, payload: dict) -> dict:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=300.0)
        try:
            try:
                conn.request(
                    "POST", "/v1/chat/completions", body=json.dumps(payload),
                    headers={"Content-Type": "application/json"},
                )
                response = conn.getresponse()
                body = response.read()
            except OSError as exc:
                raise BackendHttpError(f"连接 mlx-lm 失败: {exc}") from exc
            if response.status != 200:
                raise BackendHttpError(f"上游状态码 {response.status}: {body[:200]!r}")
            try:
                return json.loads(body)
            except ValueError as exc:
                raise BackendHttpError(f"上游返回非 JSON: {exc}") from exc
        finally:
            conn.close()

    def chat_stream(self, port: int, payload: dict) -> Iterator[dict]:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=300.0)
        try:
            conn.request(
                "POST", "/v1/chat/completions", body=json.dumps(payload),
                headers={"Content-Type": "application/json"},
            )
            response = conn.getresponse()
        except OSError as exc:
            conn.close()
            raise BackendHttpError(f"连接 mlx-lm 失败: {exc}") from exc
        if response.status != 200:
            head = response.read(2048)
            conn.close()
            raise BackendHttpError(f"上游状态码 {response.status}: {head[:200]!r}")
        return self._iter_sse(conn, response)

    @staticmethod
    def _iter_sse(conn: http.client.HTTPConnection, response: http.client.HTTPResponse) -> Iterator[dict]:
        try:
            while True:
                try:
                    raw = response.readline()
                except OSError as exc:
                    raise BackendHttpError(f"上游流中断: {exc}") from exc
                if not raw:
                    return
                line = raw.decode("utf-8", "replace").strip()
                if not line.startswith("data:"):
                    continue
                data = line[len("data:"):].strip()
                if data == "[DONE]":
                    return
                try:
                    yield json.loads(data)
                except ValueError:
                    continue
        finally:
            conn.close()
