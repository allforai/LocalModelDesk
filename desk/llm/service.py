"""Load local LLMs through the arbiter and an injectable backend."""
from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from .backend import BackendHttpError
from .state import (
    DEFAULT_CHAT_MAX_TOKENS,
    DEFAULT_LLM_PORT,
    ERR_BACKEND_EXITED,
    ERR_EVICTED,
    ERR_LOAD_IN_PROGRESS,
    ERR_LOAD_TIMEOUT,
    ERR_MEDIA_BUSY,
    ERR_MODEL_MISMATCH,
    ERR_MODEL_DIR_MISSING,
    ERR_MODEL_NOT_FOUND,
    ERR_NO_MODEL_LOADED,
    ERR_PORT_BUSY,
    ERR_PORT_NOT_RELEASED,
    ERR_UPSTREAM_ERROR,
    STATUS_ERROR,
    STATUS_IDLE,
    STATUS_LOADED,
    STATUS_LOADING,
    LlmError,
    LlmRejected,
    LlmState,
    LoadedModel,
    UpstreamError,
    delta_event,
    done_event,
    error_event,
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
        self._load_generation = 0
        self._unsubscribe = self._arbiter.subscribe(self._on_desk_state)
        self._closed = False

    def owned_pids(self) -> set[int]:
        """Pids this service spawned — the only ones the arbiter may reap (P1)."""
        proc = self._proc
        pid = getattr(proc, "pid", None)
        return {pid} if isinstance(pid, int) else set()

    def close(self) -> None:
        """Release subscriptions and any child process owned by this service."""
        with self._lock:
            if self._closed:
                return
            self._closed = True
            self._load_generation += 1
            proc, token = self._proc, self._token
            self._proc = None
            self._token = None
            self._entry = None
            self._state = LlmState(status=STATUS_IDLE)
        self._unsubscribe()
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(self._term_grace_s)
            except Exception:
                proc.kill()
        if token is not None:
            self._arbiter.release_heavy(token)

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
            reusing_existing_token = self._state.status == STATUS_LOADED
            if reusing_existing_token:
                if not self._teardown_proc_locked():
                    self._state = LlmState(
                        status=STATUS_ERROR,
                        model_key=self._state.model_key,
                        error=LlmError(ERR_PORT_NOT_RELEASED, f"切换后端口 {self._port} 仍被占用"),
                    )
                    return self._state.to_dict()
            else:
                previous_state = self._state
            self._entry = None
            self._state = LlmState(status=STATUS_LOADING, model_key=entry.key)
            self._load_generation += 1
            generation = self._load_generation
            if reusing_existing_token:
                self._load_thread = threading.Thread(
                    target=self._load_worker,
                    args=(entry, model_dir, Path(roots.venv_python), self._log_path(roots), generation),
                    daemon=True,
                    name="llm-load",
                )
                self._load_thread.start()
                return self._state.to_dict()

        acquired = self._arbiter.acquire_heavy("llm", entry.key, getattr(entry, "name", None))
        if not acquired.get("ok"):
            reason = acquired.get("reason") or {}
            code = reason.get("code") if isinstance(reason, dict) else None
            message = reason.get("message") if isinstance(reason, dict) else None
            with self._lock:
                if generation == self._load_generation:
                    self._state = previous_state
            raise LlmRejected(code or ERR_MEDIA_BUSY, message or "媒体任务正在运行")

        with self._lock:
            self._token = acquired.get("token")
            self._load_thread = threading.Thread(
                target=self._load_worker,
                args=(entry, model_dir, Path(roots.venv_python), self._log_path(roots), generation),
                daemon=True,
                name="llm-load",
            )
            self._load_thread.start()
            return self._state.to_dict()

    def _load_worker(self, entry: Any, model_dir: Path, python: Path, log_path: Path,
                     generation: int) -> None:
        with self._lock:
            if generation != self._load_generation:
                return
        reap = self._arbiter.reap_llm_port(self._port)
        if not reap.get("ok"):
            with self._lock:
                if generation != self._load_generation:
                    return
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
        strangers = self._arbiter.llm_port_listeners(self._port)
        if strangers:
            first = strangers[0]
            message = (f"端口 {self._port} 被其他程序占用（pid {first['pid']}："
                       f"{first['command'][:80]}），请先结束它再加载")
            with self._lock:
                if generation != self._load_generation:
                    return
                token = self._token
                self._token = None
                self._state = LlmState(status=STATUS_ERROR, model_key=entry.key,
                                       error=LlmError(ERR_PORT_BUSY, message))
            if token is not None:
                self._arbiter.release_heavy(token)
            return
        proc = self._backend.spawn(python, model_dir, self._port, log_path)
        with self._lock:
            if generation != self._load_generation:
                proc.terminate()
                return
            self._proc = proc
        deadline = time.monotonic() + self._load_timeout_s
        while True:
            return_code = proc.poll()
            if return_code is not None:
                log_tail = self._backend.log_tail(log_path)
                with self._lock:
                    if generation != self._load_generation:
                        return
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
                    if generation != self._load_generation:
                        return
                    self._state = LlmState(
                        status=STATUS_LOADED, model_key=entry.key, loaded_at=time.time()
                    )
                    self._entry = entry
                return
            if time.monotonic() >= deadline:
                log_tail = self._backend.log_tail(log_path)
                with self._lock:
                    if generation != self._load_generation:
                        return
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

    def _on_desk_state(self, desk_state: dict[str, Any]) -> None:
        """Make an arbiter eviction visible without waiting for the load poll loop."""
        with self._lock:
            if self._state.status not in {STATUS_LOADING, STATUS_LOADED}:
                return
            holder = desk_state.get("holder")
            still_held = (
                isinstance(holder, dict)
                and holder.get("kind") == "llm"
                and holder.get("label") == self._state.model_key
            )
            if still_held:
                return
            proc = self._proc
            self._proc = None
            self._token = None
            self._entry = None
            self._load_generation += 1
            self._state = LlmState(
                status=STATUS_ERROR,
                model_key=self._state.model_key,
                error=LlmError(ERR_EVICTED, "LLM 已被媒体任务驱逐"),
            )
        if proc is not None:
            proc.terminate()

    def status(self) -> dict[str, Any]:
        """Return the current public state and loaded model, when one is resident."""
        token = None
        with self._lock:
            if self._state.status == STATUS_LOADED and self._proc is not None:
                return_code = self._proc.poll()
                if return_code is not None:
                    log_path = self._log_path(self._paths.resolve_paths())
                    token = self._token
                    self._proc = None
                    self._token = None
                    self._entry = None
                    self._state = LlmState(
                        status=STATUS_ERROR,
                        model_key=self._state.model_key,
                        error=LlmError(
                            ERR_BACKEND_EXITED,
                            f"mlx-lm 进程已退出，退出码 {return_code}",
                            self._backend.log_tail(log_path),
                        ),
                    )
            loaded = None
            if self._state.status == STATUS_LOADED and self._entry is not None:
                loaded = LoadedModel.from_entry(self._entry).to_dict()
            result = {"state": self._state.to_dict(), "loaded_model": loaded}
        if token is not None:
            self._arbiter.release_heavy(token)
        return result

    def on_heavy_state_changed(self, desk_state: dict[str, Any]) -> None:
        """Converge a resident model after heavy-work ownership moves away from LLM."""
        holder = (desk_state or {}).get("holder")
        if holder and holder.get("kind") == "llm":
            return
        token = None
        with self._lock:
            if self._state.status != STATUS_LOADED:
                return
            log_path = self._log_path(self._paths.resolve_paths())
            token = self._token
            self._proc = None
            self._token = None
            self._entry = None
            self._state = LlmState(
                status=STATUS_ERROR,
                model_key=self._state.model_key,
                error=LlmError(
                    ERR_BACKEND_EXITED,
                    "重活持有权已易主，mlx-lm 已被收割",
                    self._backend.log_tail(log_path),
                ),
            )
        if token is not None:
            self._arbiter.release_heavy(token)

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
        """Unload a settled model, or cancel a load that is still in progress."""
        token = None
        proc = None
        with self._lock:
            if self._state.status == STATUS_LOADING:
                self._load_generation += 1
                proc, token = self._proc, self._token
                self._proc = None
                self._token = None
                self._entry = None
                self._state = LlmState(status=STATUS_IDLE)
                result = self._state.to_dict()
            elif self._state.status == STATUS_IDLE:
                return self._state.to_dict()
            elif self._teardown_proc_locked():
                token = self._token
                self._token = None
                self._entry = None
                self._state = LlmState(status=STATUS_IDLE)
                result = self._state.to_dict()
            else:
                self._state = LlmState(
                    status=STATUS_ERROR,
                    model_key=self._state.model_key,
                    error=LlmError(
                        ERR_PORT_NOT_RELEASED,
                        f"卸载后端口 {self._port} 仍被占用",
                    ),
                )
                result = self._state.to_dict()
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(self._term_grace_s)
            except Exception:
                proc.kill()
        if token is not None:
            self._arbiter.release_heavy(token)
        return result

    def _chat_precheck(self, request: dict[str, Any]) -> Any:
        """Reject chat requests that cannot use the currently resident model."""
        desk_state = self._arbiter.desk_state() or {}
        if desk_state.get("media_busy"):
            raise LlmRejected(ERR_MEDIA_BUSY, "媒体作业进行中，聊天请求被拒绝")
        with self._lock:
            if self._state.status != STATUS_LOADED or self._entry is None:
                raise LlmRejected(ERR_NO_MODEL_LOADED, "当前没有加载模型")
            entry = self._entry
        requested_model = request.get("model")
        if requested_model and requested_model not in (entry.key, entry.hf_repo):
            raise LlmRejected(
                ERR_MODEL_MISMATCH,
                f"请求模型 {requested_model!r} 与驻留模型 {entry.key!r} 不符",
            )
        return entry

    @staticmethod
    def _upstream_payload(request: dict[str, Any], entry: Any) -> dict[str, Any]:
        # mlx_lm.server maps this stable alias to the model supplied on its
        # command line. Sending the public HF repository id makes it resolve
        # and download a second model from the Hub instead of using the
        # already resident local path.
        payload: dict[str, Any] = {"model": "default_model", "messages": request["messages"]}
        for key in ("temperature", "top_p", "max_tokens"):
            if request.get(key) is not None:
                payload[key] = request[key]
        payload.setdefault("max_tokens", DEFAULT_CHAT_MAX_TOKENS)
        return payload

    def chat_completion(self, request: dict[str, Any]) -> dict[str, Any]:
        """Forward a non-streaming chat request without fabricating response data."""
        entry = self._chat_precheck(request)
        payload = self._upstream_payload(request, entry)
        payload["stream"] = False
        try:
            raw = self._backend.chat(self._port, payload)
        except BackendHttpError as exc:
            raise UpstreamError(str(exc)) from exc
        try:
            choice = raw["choices"][0]
            message = choice["message"]
        except (KeyError, IndexError, TypeError) as exc:
            raise UpstreamError(f"上游响应缺 choices/message: {exc}") from exc
        usage = raw.get("usage")
        finish_reason = choice.get("finish_reason")
        if usage is None or finish_reason is None:
            raise UpstreamError("上游响应缺 usage/finish_reason")
        reasoning = message.get("reasoning_content")
        if reasoning is None:
            reasoning = message.get("reasoning")
        return {
            "content": message.get("content") if message.get("content") is not None else "",
            "reasoning": reasoning,
            "usage": usage,
            "finish_reason": finish_reason,
            "model": entry.key,
        }

    def chat_stream(self, request: dict[str, Any]):
        """Yield separated chat deltas and one terminal event from the resident model."""
        entry = self._chat_precheck(request)
        payload = self._upstream_payload(request, entry)
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
        return self._stream_events(payload)

    def _interruption_event(self, fallback_message: str) -> dict[str, Any]:
        """Name the real cause when the resident model was taken away mid-stream."""
        with self._lock:
            error = self._state.error
        if error is not None and error.code == ERR_EVICTED:
            return error_event(ERR_EVICTED, "内存让给了媒体作业，回答被中断")
        return error_event(ERR_UPSTREAM_ERROR, fallback_message)

    def _stream_events(self, payload: dict[str, Any]):
        usage = None
        finish_reason = None
        try:
            for chunk in self._backend.chat_stream(self._port, payload):
                choices = chunk.get("choices") or []
                choice = choices[0] if choices else {}
                delta = choice.get("delta") or {}
                text = delta.get("content") or None
                reasoning = delta.get("reasoning_content")
                if reasoning is None:
                    reasoning = delta.get("reasoning")
                reasoning = reasoning or None
                if text is not None or reasoning is not None:
                    yield delta_event(text, reasoning)
                if choice.get("finish_reason") is not None:
                    finish_reason = choice["finish_reason"]
                if chunk.get("usage") is not None:
                    usage = chunk["usage"]
        except BackendHttpError as exc:
            yield self._interruption_event(str(exc))
            return
        if usage is None or finish_reason is None:
            yield self._interruption_event("上游流终止但缺 usage/finish_reason")
            return
        yield done_event(usage, finish_reason)

    def wait_settled(self, timeout_s: float = 5.0) -> dict[str, Any]:
        """Wait for an in-flight load; intended for polling callers and tests.
        Test seam: production code never calls this (census 2026-09-08, F13)."""
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            with self._lock:
                if self._state.status != STATUS_LOADING:
                    return self._state.to_dict()
            time.sleep(0.001)
        with self._lock:
            return self._state.to_dict()
