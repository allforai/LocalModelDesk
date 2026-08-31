"""H3 video and Music 3 job runner."""
from __future__ import annotations

import logging
import threading
import time
from pathlib import Path
from typing import Any, Callable

from .commands import build_h3_command, build_music_command

log = logging.getLogger(__name__)
DEFAULT_LOG_LIMIT = 1024 * 1024


class MediaError(Exception):
    def __init__(self, code: str, message: str, http_status: int, detail: dict | None = None):
        super().__init__(message)
        self.code, self.message, self.http_status, self.detail = code, message, http_status, detail or {}


def _nonempty(name: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise MediaError("invalid_params", f"{name} must be a non-empty string", 400)


def _positive_int(name: str, value: Any) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise MediaError("invalid_params", f"{name} must be a positive integer", 400)


class MediaService:
    def __init__(self, *, resolve_paths, probe_capabilities, arbiter, list_catalog,
                 append_history, executor, clock: Callable[[], float] = time.time,
                 term_grace_s: float = 5.0, log_limit: int = DEFAULT_LOG_LIMIT):
        self._resolve_paths, self._probe_capabilities, self._arbiter = resolve_paths, probe_capabilities, arbiter
        self._list_catalog, self._append_history, self._executor = list_catalog, append_history, executor
        self._clock, self._term_grace_s, self._log_limit = clock, term_grace_s, log_limit
        self._lock = threading.RLock()
        self._state: dict[str, Any] = {"job_id": 0, "status": "idle", "kind": None, "params": None,
            "output": None, "error": None, "started_at": None, "finished_at": None}
        self._log = ""; self._log_dropped = 0; self._log_truncated = False
        self._cancel_requested = False; self._handle = None; self._callbacks: list[Callable[[dict], None]] = []

    def start_video_job(self, *, prompt, width, height, frames, steps) -> dict:
        _nonempty("prompt", prompt)
        for name, value in (("width", width), ("height", height), ("frames", frames), ("steps", steps)):
            _positive_int(name, value)
        return self._start("video", {"prompt": prompt, "width": width, "height": height, "frames": frames, "steps": steps})

    def start_music_job(self, *, caption, lyrics, duration) -> dict:
        _nonempty("caption", caption)
        if not isinstance(lyrics, str) or isinstance(duration, bool) or not isinstance(duration, (int, float)) or duration <= 0:
            raise MediaError("invalid_params", "lyrics must be a string and duration must be positive", 400)
        return self._start("music", {"caption": caption, "lyrics": lyrics, "duration": duration})

    def _start(self, kind: str, params: dict) -> dict:
        with self._lock:
            if self._state["status"] == "running":
                raise MediaError("media_busy", "a media job is already running", 409)
            cap_key = "mlx_h3" if kind == "video" else "music_runtime"
            cap = self._probe_capabilities().get(cap_key)
            if cap is None or not cap.present:
                raise MediaError("capability_missing", f"{cap_key} is unavailable: {getattr(cap, 'detail', '')}", 503)
            roots = self._resolve_paths()
            catalog_key = "h3" if kind == "video" else "music3"
            model_root = Path(roots.models_root) / {e.key: e.relpath for e in self._list_catalog()}[catalog_key]
            pre = self._arbiter.can_start_heavy(kind)
            if not pre.get("ok"):
                reason = pre.get("reason") or {}
                raise MediaError(reason.get("code", "refused"), reason.get("message", "arbiter refused"), 409)
            job_id = self._state["job_id"] + 1
            grant = self._arbiter.acquire_heavy(kind, f"job-{job_id}")
            if not grant.get("ok"):
                reason = grant.get("reason") or {}
                raise MediaError(reason.get("code", "acquire_refused"), reason.get("message", "arbiter refused"), 409)
            permit, now = grant["token"], self._clock()
            try:
                stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(now))
                root = Path(roots.outputs_root); root.mkdir(parents=True, exist_ok=True)
                if kind == "video":
                    output = root / f"h3-{stamp}.mp4"
                    command = build_h3_command(tuple(roots.mlx_h3_cmd), model_root, output=output, **params)
                    extra_env = dict(roots.mlx_h3_env)
                else:
                    output = root / f"music3-{stamp}.wav"
                    command = build_music_command(Path(roots.music_python), Path(roots.media_cli_dir) / "music3_cli.py", model_root, output=output, **params)
                    extra_env = dict(roots.music_env)
                handle = self._executor.spawn(command, extra_env=extra_env)
            except Exception as exc:
                self._state = {"job_id": job_id, "status": "error", "kind": kind, "params": dict(params), "output": None,
                    "error": {"code": "spawn_failed", "message": str(exc)}, "started_at": now, "finished_at": self._clock()}
                self._reset_log(); self._finalize(permit)
                raise MediaError("spawn_failed", str(exc), 500) from exc
            self._state = {"job_id": job_id, "status": "running", "kind": kind, "params": dict(params), "output": None,
                "error": None, "started_at": now, "finished_at": None}
            self._reset_log(); self._cancel_requested = False; self._handle = handle
            threading.Thread(target=self._worker, args=(handle, permit, output), daemon=True).start()
            return self.job_status()

    def _worker(self, handle, permit: str, output: Path) -> None:
        try:
            try:
                for line in handle.iter_output(): self._append_log(line)
                code, failure = handle.wait(), None
            except Exception as exc:
                code, failure = None, str(exc)
            with self._lock:
                if self._cancel_requested: status, error = "cancelled", None
                elif failure is not None: status, error = "error", {"code": "worker_failed", "message": failure}
                elif code == 0 and output.is_file(): status, error = "done", None
                elif code == 0: status, error = "error", {"code": "no_output", "message": "exit 0 but output file missing"}
                else: status, error = "error", {"code": "exit_nonzero", "message": f"exit {code}"}
                self._state.update(status=status, output=output.name if status == "done" else None, error=error, finished_at=self._clock())
                self._handle = None
        finally:
            self._finalize(permit)

    def _finalize(self, permit: str) -> None:
        with self._lock: snap, callbacks = self.job_status(), list(self._callbacks)
        try: self._arbiter.release_heavy(permit)
        except Exception: log.exception("release_heavy failed")
        try: self._append_history(self._history_entry(snap))
        except Exception as exc: self._append_log(f"[media] append_history failed: {exc}")
        for callback in callbacks:
            try: callback(snap)
            except Exception: log.exception("jobFinished subscriber failed")

    def _history_entry(self, snap: dict) -> dict:
        error = snap["error"]
        return {"kind": snap["kind"], "status": {"done": "done", "error": "failed", "cancelled": "cancelled"}[snap["status"]],
            "params": snap["params"], "output": snap["output"], "duration_s": snap["finished_at"] - snap["started_at"],
            "error": f"{error['code']}: {error['message']}" if error else None}

    def cancel_job(self) -> dict:
        with self._lock:
            if self._state["status"] != "running": raise MediaError("no_running_job", "no media job is running", 409)
            self._cancel_requested = True; handle = self._handle
        handle.terminate()
        deadline = time.monotonic() + self._term_grace_s
        while handle.poll() is None and time.monotonic() < deadline: time.sleep(.02)
        if handle.poll() is None: handle.kill()
        return self.job_status()

    def job_status(self, *, log_from: int = 0, job_id: int | None = None) -> dict:
        with self._lock:
            state = dict(self._state); state["params"] = dict(self._state["params"]) if self._state["params"] else None
            state["error"] = dict(self._state["error"]) if self._state["error"] else None
            if job_id is not None and job_id != state["job_id"]: log_from = 0
            state.update(log=self._log[max(log_from - self._log_dropped, 0):], next_log_from=self._log_dropped + len(self._log), log_len=self._log_dropped + len(self._log), log_truncated=self._log_truncated)
            return state

    def on_job_finished(self, callback: Callable[[dict], None]) -> Callable[[], None]:
        with self._lock: self._callbacks.append(callback)
        def unsubscribe() -> None:
            with self._lock:
                if callback in self._callbacks: self._callbacks.remove(callback)
        return unsubscribe

    def _reset_log(self) -> None: self._log = ""; self._log_dropped = 0; self._log_truncated = False
    def _append_log(self, line: str) -> None:
        with self._lock:
            self._log += line if line.endswith("\n") else line + "\n"
            overflow = len(self._log) - self._log_limit
            if overflow > 0: self._log = self._log[overflow:]; self._log_dropped += overflow; self._log_truncated = True
