"""Subprocess boundary for the local mlx-lm server."""
from __future__ import annotations

import http.client
import json
import os
import subprocess
from pathlib import Path
from typing import Iterator, Protocol
from .content import uses_vision


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
        self, python: Path, model_path: Path, port: int, log_path: Path,
        extra_args: list[str] | None = None,
    ) -> BackendProcess: ...

    def health(self, port: int) -> bool: ...

    def chat(self, port: int, payload: dict) -> dict: ...

    def chat_stream(self, port: int, payload: dict) -> Iterator[dict]: ...

    def log_tail(self, log_path: Path, max_lines: int = 40) -> str: ...


class MlxLmBackend:
    """Launches ``mlx_lm server`` and reads its diagnostic log."""

    request_timeout = 300.0

    def __init__(self, *, vision_python=None, vision_env=None):
        self.vision_python = vision_python
        self.vision_env = vision_env
        self._vision_ports = set()

    def spawn(
        self, python: Path, model_path: Path, port: int, log_path: Path,
        extra_args: list[str] | None = None,
    ) -> BackendProcess:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        vision = uses_vision(model_path)
        if vision:
            self._vision_ports.add(port)
        else:
            self._vision_ports.discard(port)
        if vision and self.vision_python is not None:
            python = self.vision_python
        argv = [
            str(python), "-s", "-m", *(["mlx_vlm.server"] if vision else ["mlx_lm", "server"]),
            "--model", str(model_path), "--host", "127.0.0.1",
            "--port", str(port),
            *(["--max-num-seqs", "1", "--vision-cache-size", "1"] if vision else (extra_args or [])),
        ]
        with log_path.open("ab") as log_file:
            env = {**os.environ, **self.vision_env} if vision and self.vision_env is not None else None
            return subprocess.Popen(argv, stdout=log_file, stderr=log_file, env=env)

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
            response = conn.getresponse()
            if response.status != 200:
                return False
            if port in self._vision_ports:
                return any(m.get("loaded") for m in json.loads(response.read()).get("data", []))
            return True
        except (OSError, ValueError):
            return False
        finally:
            conn.close()

    def chat(self, port: int, payload: dict) -> dict:
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=self.request_timeout)
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
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=self.request_timeout)
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
