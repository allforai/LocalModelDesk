"""Programmable LLM collaborators with a shared ordered call ledger."""
from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Iterable

from desk.llm.backend import BackendHttpError


class CallLedger:
    """Append-only call recorder shareable by every fake in a test."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def record(self, name: str, *args: Any, **kwargs: Any) -> None:
        self.calls.append({"name": name, "args": args, "kwargs": kwargs})

    def clear(self) -> None:
        self.calls.clear()


def _record(calls: CallLedger | list, name: str, *args: Any) -> None:
    if isinstance(calls, CallLedger):
        calls.record(name, *args)
    else:
        calls.append((name, *args))


def _pop(script: list[Any]) -> Any:
    if not script:
        raise ValueError("fake scripts must contain at least one result")
    if len(script) > 1:
        return script.pop(0)
    return script[0]


@dataclass(frozen=True)
class FakeEntry:
    key: str
    name: str
    group: str
    hf_repo: str
    relpath: str
    gb: float
    vision: bool = False
    quant: str | None = None
    params: str | None = None


def make_entry(key: str = "glm", **overrides: Any) -> FakeEntry:
    defaults = {
        "name": "GLM-4.5-Air", "group": "chat", "hf_repo": f"mlx-community/{key}-4bit",
        "relpath": f"llms/mlx-community/{key}-4bit", "gb": 60.2, "vision": False,
        "quant": "4bit", "params": "106B",
    }
    defaults.update(overrides)
    return FakeEntry(key=key, **defaults)


class FakeCatalog:
    def __init__(self, entries: Iterable[Any] = (), *, ledger: CallLedger | None = None) -> None:
        self._entries = list(entries)
        self.ledger = ledger

    def list_catalog(self) -> list[Any]:
        if self.ledger is not None:
            self.ledger.record("catalog.list_catalog")
        return list(self._entries)

    list_models = list_catalog

    def find(self, key: str) -> Any | None:
        if self.ledger is not None:
            self.ledger.record("catalog.find", key)
        return next((entry for entry in self._entries if getattr(entry, "key", None) == key), None)

    get = find


class FakePaths:
    def __init__(self, root: Path | None = None, *, venv_python: Path | None = None,
                 logs_dir: Path | None = None, models_root: Path | None = None) -> None:
        root = Path(root) if root is not None else Path("/fake")
        self.models_root = Path(models_root) if models_root is not None else root / "models"
        self.logs_dir = Path(logs_dir) if logs_dir is not None else root / "logs"
        self.venv_python = Path(venv_python) if venv_python is not None else root / "venv" / "bin" / "python3"
        self.models_root.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

    def resolve_paths(self) -> SimpleNamespace:
        return SimpleNamespace(models_root=self.models_root, logs_dir=self.logs_dir, venv_python=self.venv_python)


class FakeProcess:
    def __init__(self, poll_script: Iterable[int | None] = (None,), *, calls: CallLedger | list | None = None) -> None:
        self._script = list(poll_script)
        self.calls = calls if calls is not None else []
        self.terminated = False
        self.killed = False
        self.wait_timeouts: list[float] = []

    def set_exit(self, code: int) -> None:
        self._script = [code]

    def poll(self) -> int | None:
        return _pop(self._script)

    def terminate(self) -> None:
        self.terminated = True
        _record(self.calls, "terminate")

    def kill(self) -> None:
        self.killed = True
        _record(self.calls, "kill")

    def wait(self, timeout: float) -> None:
        self.wait_timeouts.append(timeout)
        _record(self.calls, "wait", timeout)


class FakeBackend:
    Process = FakeProcess

    def __init__(self, *, process: FakeProcess | None = None, health_script: Iterable[bool] = (True,),
                 health_results: Iterable[bool] | None = None, chunks: Iterable[dict] = (),
                 stream: Iterable[dict] | None = None, stream_error_after: int | None = None,
                 chat_result: dict | None = None, chat_error: Exception | None = None,
                 stream_error: Exception | None = None, tail_text: str = "fake mlx-lm log tail",
                 log_text: str | None = None, spawn_error: Exception | None = None,
                 calls: CallLedger | list | None = None, ledger: CallLedger | None = None) -> None:
        self.calls = calls if calls is not None else (ledger if ledger is not None else CallLedger())
        self.ledger = self.calls if isinstance(self.calls, CallLedger) else None
        self.process = process if process is not None else FakeProcess(calls=self.calls)
        self._health_script = list(health_results if health_results is not None else health_script)
        self.chunks = list(stream if stream is not None else chunks)
        self.stream_error_after = stream_error_after
        self.chat_result = {} if chat_result is None else chat_result
        self.chat_error = chat_error
        self.stream_error = stream_error
        self.tail_text = tail_text if log_text is None else log_text
        self.spawn_exc = spawn_error
        self.hold_health = False
        self.health_release = threading.Event()

    def spawn(self, python: Path | str, model_path: Path | str, port: int, log_path: Path | str) -> FakeProcess:
        _record(self.calls, "spawn", str(python), str(model_path), port, str(log_path))
        if self.spawn_exc is not None:
            raise self.spawn_exc
        return self.process

    def health(self, port: int) -> bool:
        _record(self.calls, "health", port)
        if self.hold_health:
            return bool(self.health_release.wait(timeout=5.0))
        return _pop(self._health_script)

    def chat(self, port: int, payload: dict) -> dict:
        _record(self.calls, "chat", port, payload)
        if self.chat_error is not None:
            raise self.chat_error
        return self.chat_result

    def chat_stream(self, port: int, payload: dict):
        _record(self.calls, "chat_stream", port, payload)
        if self.stream_error is not None:
            raise self.stream_error

        def generate():
            for index, chunk in enumerate(self.chunks):
                if self.stream_error_after is not None and index == self.stream_error_after:
                    raise BackendHttpError("fake upstream stream interrupted")
                yield chunk
            if self.stream_error_after is not None and self.stream_error_after >= len(self.chunks):
                raise BackendHttpError("fake upstream stream interrupted")

        return generate()

    def log_tail(self, log_path: Path | str, max_lines: int = 40) -> str:
        _record(self.calls, "log_tail", str(log_path), max_lines)
        return self.tail_text


class FakeArbiter:
    def __init__(self, *, calls: CallLedger | list | None = None, ledger: CallLedger | None = None,
                 acquire_results: Iterable[dict] | None = None, acquire_result: dict | None = None,
                 reap_results: Iterable[dict] | None = None, reap_result: dict | None = None,
                 release_result: dict | None = None, desk_states: Iterable[dict] | None = None,
                 listeners: Iterable[dict] = ()) -> None:
        self.calls = calls if calls is not None else (ledger if ledger is not None else CallLedger())
        self.ledger = self.calls if isinstance(self.calls, CallLedger) else None
        self._acquire = list(acquire_results if acquire_results is not None else [acquire_result or {"ok": True, "token": "tok-1"}])
        self._reap = list(reap_results if reap_results is not None else [reap_result or {"ok": True, "port": 0, "killed_pids": [], "error": None}])
        self.release_result = release_result or {"ok": True}
        self._desk_states = list(desk_states or [{"holder": {"kind": "llm", "label": "glm", "phase": "held"}, "media_busy": False}])
        self._subscribers: list[Any] = []
        self._listeners = list(listeners)

    def acquire_heavy(self, kind: str, label: str, display: str | None = None) -> dict:
        _record(self.calls, "acquire", kind, label)
        return _pop(self._acquire)

    def release_heavy(self, token: str) -> dict:
        _record(self.calls, "release", token)
        return self.release_result

    def reap_llm_port(self, port: int) -> dict:
        _record(self.calls, "reap", port)
        return _pop(self._reap)

    def llm_port_listeners(self, port: int) -> list[dict]:
        _record(self.calls, "listeners", port)
        return list(self._listeners)

    def desk_state(self) -> dict:
        return _pop(self._desk_states)

    def set_desk_state(self, state: dict) -> None:
        self._desk_states = [state]

    def subscribe(self, callback: Any):
        self._subscribers.append(callback)
        def unsubscribe() -> None:
            if callback in self._subscribers:
                self._subscribers.remove(callback)
        return unsubscribe

    def emit(self, state: dict) -> None:
        for callback in tuple(self._subscribers):
            callback(state)


def make_service(tmp_path: Path, *, entries: Iterable[Any] | None = None,
                 backend_kw: dict[str, Any] | None = None,
                 arbiter_kw: dict[str, Any] | None = None, **service_kw: Any) -> SimpleNamespace:
    """Build an LLM service with local fake collaborators."""
    from desk.llm.service import LlmService

    calls: list = []
    proc = FakeProcess(calls=calls)
    backend = FakeBackend(process=proc, calls=calls, **(backend_kw or {}))
    arbiter = FakeArbiter(calls=calls, **(arbiter_kw or {}))
    paths = FakePaths(tmp_path)
    entries = list(entries) if entries is not None else [make_entry()]
    for entry in entries:
        (paths.models_root / entry.relpath).mkdir(parents=True, exist_ok=True)
    service = LlmService(
        backend=backend, arbiter=arbiter, catalog=FakeCatalog(entries), paths=paths,
        load_timeout_s=service_kw.pop("load_timeout_s", 2.0),
        poll_interval_s=service_kw.pop("poll_interval_s", 0.001),
        term_grace_s=service_kw.pop("term_grace_s", 0.05), **service_kw,
    )
    return SimpleNamespace(service=service, backend=backend, arbiter=arbiter, paths=paths,
                           calls=calls, proc=proc, entries=entries)


def make_loaded(tmp_path: Path, **kwargs: Any) -> SimpleNamespace:
    """Build a service and wait for its default model to load."""
    testbed = make_service(tmp_path, **kwargs)
    testbed.service.load(testbed.entries[0].key)
    final = testbed.service.wait_settled()
    assert final["status"] == "loaded", final
    return testbed
