"""Load local LLMs through the arbiter and an injectable backend."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from .state import (
    DEFAULT_LLM_PORT,
    ERR_BACKEND_EXITED,
    ERR_LOAD_IN_PROGRESS,
    ERR_LOAD_TIMEOUT,
    ERR_MEDIA_BUSY,
    ERR_MODEL_DIR_MISSING,
    ERR_MODEL_NOT_FOUND,
    ERR_PORT_NOT_RELEASED,
    STATUS_ERROR,
    STATUS_IDLE,
    STATUS_LOADED,
    STATUS_LOADING,
    LlmError,
    LlmRejected,
    LlmState,
    LoadedModel,
)


class LlmService:
    """Coordinate asynchronous model loading without owning process details."""

    def __init__(self, backend: Any, arbiter: Any, catalog: Any, paths: Any, *,
                 port: int = DEFAULT_LLM_PORT, load_timeout_s: float = 180.0,
                 poll_interval_s: float = 0.4, term_grace_s: float = 8.0) -> None:
        self._backend = backend
        self._arbiter = arbiter
        self._catalog = catalog
        self._paths = paths
        self._port = port
        self._load_timeout_s = load_timeout_s
        self._poll_interval_s = poll_interval_s
        self._term_grace_s = term_grace_s
        self._lock = threading.Lock()
        self._state = LlmState(status=STATUS_IDLE)
        self._proc = None
        self._token: str | None = None
        self._entry = None
        self._load_thread: threading.Thread | None = None

    def _find_entry(self, key: str) -> Any | None:
        return next((entry for entry in self._catalog.list_catalog() if entry.key == key), None)

    @staticmethod
    def _log_path(roots: Any) -> Path:
        return Path(roots.logs_dir) / "mlx-lm.log"

    def load(self, key: str) -> dict[str, Any]:
        """Start loading *key* and immediately return its loading state."""
        with self._lock:
            if self._state.status == STATUS_LOADING:
                raise LlmRejected(ERR_LOAD_IN_PROGRESS, "已有模型正在加载")
            entry = self._find_entry(key)
            if entry is None:
                raise LlmRejected(ERR_MODEL_NOT_FOUND, f"未找到模型: {key}")
            roots = self._paths.resolve_paths()
            model_dir = Path(roots.models_root) / entry.relpath
            if not model_dir.is_dir():
                raise LlmRejected(ERR_MODEL_DIR_MISSING, f"模型目录不存在: {model_dir}")
            acquired = self._arbiter.acquire_heavy("llm", entry.key)
            if not acquired.get("ok"):
                reason = acquired.get("reason") or {}
                message = reason.get("message") if isinstance(reason, dict) else None
                raise LlmRejected(ERR_MEDIA_BUSY, message or "媒体任务正在运行")
            self._token = acquired.get("token")
            self._entry = None
            self._state = LlmState(status=STATUS_LOADING, model_key=entry.key)
            self._load_thread = threading.Thread(
                target=self._load_worker,
                args=(entry, model_dir, Path(roots.venv_python), self._log_path(roots)),
                daemon=True,
                name="llm-load",
            )
            self._load_thread.start()
            return self._state.to_dict()

    def _load_worker(self, entry: Any, model_dir: Path, python: Path, log_path: Path) -> None:
        reap = self._arbiter.reap_llm_port(self._port)
        if not reap.get("ok"):
            with self._lock:
                token = self._token
                self._token = None
                self._state = LlmState(
                    status=STATUS_ERROR,
                    model_key=entry.key,
                    error=LlmError(ERR_PORT_NOT_RELEASED, reap.get("error") or "无法释放 LLM 端口"),
                )
            if token is not None:
                self._arbiter.release_heavy(token)
            return
        proc = self._backend.spawn(python, model_dir, self._port, log_path)
        with self._lock:
            self._proc = proc
        deadline = time.monotonic() + self._load_timeout_s
        while True:
            return_code = proc.poll()
            if return_code is not None:
                log_tail = self._backend.log_tail(log_path)
                with self._lock:
                    token = self._token
                    self._token = None
                    self._proc = None
                    self._state = LlmState(
                        status=STATUS_ERROR,
                        model_key=entry.key,
                        error=LlmError(
                            ERR_BACKEND_EXITED,
                            f"mlx-lm 进程退出，退出码 {return_code}",
                            log_tail,
                        ),
                    )
                if token is not None:
                    self._arbiter.release_heavy(token)
                return
            if self._backend.health(self._port):
                with self._lock:
                    self._state = LlmState(
                        status=STATUS_LOADED, model_key=entry.key, loaded_at=time.time()
                    )
                    self._entry = entry
                return
            if time.monotonic() >= deadline:
                log_tail = self._backend.log_tail(log_path)
                with self._lock:
                    token = self._token
                    self._token = None
                    self._proc = None
                    self._state = LlmState(
                        status=STATUS_ERROR,
                        model_key=entry.key,
                        error=LlmError(
                            ERR_LOAD_TIMEOUT,
                            f"mlx-lm 超过 {self._load_timeout_s:.0f}s 未就绪",
                            log_tail,
                        ),
                    )
                if token is not None:
                    self._arbiter.release_heavy(token)
                return
            time.sleep(self._poll_interval_s)

    def status(self) -> dict[str, Any]:
        """Return the current public state and loaded model, when one is resident."""
        with self._lock:
            loaded = None
            if self._state.status == STATUS_LOADED and self._entry is not None:
                loaded = LoadedModel.from_entry(self._entry).to_dict()
            return {"state": self._state.to_dict(), "loaded_model": loaded}

    def _teardown_proc_locked(self) -> bool:
        """Stop the owned child and confirm the LLM port has been released."""
        proc = self._proc
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(self._term_grace_s)
            except Exception:
                proc.kill()
        self._proc = None
        return bool(self._arbiter.reap_llm_port(self._port).get("ok"))

    def unload(self) -> dict[str, Any]:
        """Unload a settled model only after the LLM port is confirmed free."""
        with self._lock:
            if self._state.status == STATUS_LOADING:
                raise LlmRejected(ERR_LOAD_IN_PROGRESS, "加载进行中，等状态落定后再卸载")
            if self._state.status == STATUS_IDLE:
                return self._state.to_dict()
            if self._teardown_proc_locked():
                if self._token is not None:
                    self._arbiter.release_heavy(self._token)
                self._token = None
                self._entry = None
                self._state = LlmState(status=STATUS_IDLE)
            else:
                self._state = LlmState(
                    status=STATUS_ERROR,
                    model_key=self._state.model_key,
                    error=LlmError(
                        ERR_PORT_NOT_RELEASED,
                        f"卸载后端口 {self._port} 仍被占用",
                    ),
                )
            return self._state.to_dict()

    def wait_settled(self, timeout_s: float = 5.0) -> dict[str, Any]:
        """Wait for an in-flight load; intended for polling callers and tests."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                if self._state.status != STATUS_LOADING:
                    return self._state.to_dict()
            time.sleep(0.001)
        with self._lock:
            return self._state.to_dict()
