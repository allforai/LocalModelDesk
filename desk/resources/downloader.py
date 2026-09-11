"""Single-flight, resumable Hugging Face model downloads."""
from __future__ import annotations

import os
import threading
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .catalog import entry
from .errors import DownloadBusyError, HfCliMissingError, MediaBusyError, NotDownloadingError
from .verify import verify_tree


@dataclass
class DownloadProgress:
    key: str | None = None
    state: str = "idle"
    bytes_done: int = 0
    bytes_total: int = 0
    percent: float = 0.0
    current_file: str | None = None
    rate_bps: float = 0.0
    eta_seconds: float | None = None
    started_at: str | None = None
    error: dict | None = None
    stale_bytes: int = 0

    def copy(self) -> "DownloadProgress":
        return DownloadProgress(**asdict(self))


class Downloader:
    def __init__(self, executor, manifest_store, resolve_paths, can_start_heavy, events,
                 clock=time.monotonic, sample_interval: float = 1.0):
        self._executor = executor
        self._manifest_store = manifest_store
        self._resolve_paths = resolve_paths
        self._can_start_heavy = can_start_heavy
        self._events = events
        self._clock = clock
        self._sample_interval = sample_interval
        self._lock = threading.RLock()
        self._progress = DownloadProgress()
        self._handle = None
        self._model = self._manifest = None
        self._cancel_at: float | None = None
        self._previous_done = 0
        self._previous_sample = 0.0
        self._attempt_wall = 0.0

    def start(self, key: str) -> DownloadProgress:
        with self._lock:
            if self._handle is not None:
                raise DownloadBusyError("a download is already running")
            allowed = self._can_start_heavy()
            if not allowed.get("ok"):
                reason = allowed.get("reason") or {}
                if reason.get("code") == "media_busy":
                    raise MediaBusyError(reason.get("message", "media job running"), reason)
                raise MediaBusyError(reason.get("message", "heavy work is running"), reason)
            model = entry(key)
            roots = self._resolve_paths()
            hf_cmd = tuple(roots.hf_cmd)
            if not hf_cmd or not Path(hf_cmd[0]).exists():
                raise HfCliMissingError("hf command is unavailable")
            try:
                manifest = self._manifest_store.get(model, refresh=True)
            except Exception:
                manifest = None
            destination = Path(roots.models_root) / model.relpath
            self._model = model
            self._purge_incomplete()
            command = [*hf_cmd, "download", model.hf_repo, "--local-dir", str(destination)]
            revision = getattr(manifest, "revision", None) if manifest is not None else None
            if revision:
                command += ["--revision", revision]
            try:
                handle = self._executor.spawn(
                    command, cwd=None, extra_env=dict(getattr(roots, "hf_env", {}) or {}))
            except FileNotFoundError as exc:
                raise HfCliMissingError("hf command is unavailable") from exc
            result = self._begin(model, manifest, handle)
            threading.Thread(target=self._sample_loop, daemon=True).start()
            return result

    def _begin(self, model, manifest, handle) -> DownloadProgress:
        """Record a fresh attempt's state; shared by every start() implementation."""
        now = self._clock()
        total = manifest.total_bytes if manifest is not None else 0
        self._progress = DownloadProgress(key=model.key, state="running", bytes_total=total,
                                          started_at=str(now))
        self._handle, self._model, self._manifest = handle, model, manifest
        self._cancel_at = None
        self._previous_done, self._previous_sample = 0, now
        self._attempt_wall = time.time()
        return self._progress.copy()

    def progress(self) -> DownloadProgress:
        with self._lock:
            return self._progress.copy()

    @property
    def attempt_wall(self) -> float:
        """Wall-clock time the current (or most recent) attempt started."""
        with self._lock:
            return self._attempt_wall

    def cancel(self) -> DownloadProgress:
        with self._lock:
            if self._handle is None or self._progress.state != "running":
                raise NotDownloadingError("no download is running")
            self._handle.terminate()
            self._cancel_at = self._clock()
            self._progress.state = "cancelled"
            snapshot = self._progress.copy()
        self._events.emit_progress(snapshot)
        return snapshot

    def _sample_loop(self) -> None:
        while True:
            with self._lock:
                handle = self._handle
            if handle is None:
                return
            self._sample()
            code = handle.poll()
            with self._lock:
                cancelled = self._progress.state == "cancelled"
                if code is None and self._cancel_at is not None and self._clock() - self._cancel_at >= 8:
                    handle.kill()
                    code = handle.poll()
            if code is not None:
                self._finish(code, cancelled)
                return
            time.sleep(self._sample_interval)

    def _sample(self) -> None:
        with self._lock:
            model, manifest = self._model, self._manifest
            if model is None or manifest is None:
                return
            root = Path(self._resolve_paths().models_root) / model.relpath
            done, current = 0, None
            newest = -1.0
            for file in manifest.files:
                path = root / file.path
                try:
                    size, mtime = path.stat().st_size, path.stat().st_mtime
                except OSError:
                    size, mtime = 0, -1.0
                done += min(size, file.size)
                if size < file.size and mtime >= newest:
                    current, newest = file.path, mtime
            total = manifest.total_bytes
            incomplete_root = root / ".cache" / "huggingface" / "download"
            incomplete_bytes, stale_bytes = 0, 0
            try:
                for path in incomplete_root.rglob("*.incomplete"):
                    if not path.is_file():
                        continue
                    stat = path.stat()
                    if stat.st_mtime + 1 >= self._attempt_wall:
                        incomplete_bytes += stat.st_size
                    else:
                        stale_bytes += stat.st_size
            except OSError:
                pass
            done = min(done + incomplete_bytes, total)
            now = self._clock()
            elapsed = now - self._previous_sample
            instantaneous = (done - self._previous_done) / elapsed if elapsed > 0 else 0.0
            rate = instantaneous if self._progress.rate_bps == 0 else .3 * instantaneous + .7 * self._progress.rate_bps
            self._progress.bytes_done = min(done, total)
            self._progress.percent = round(done / total * 100, 2) if total else 0.0
            self._progress.current_file = current
            self._progress.rate_bps = rate
            self._progress.eta_seconds = (total - done) / rate if rate > 0 else None
            self._progress.stale_bytes = stale_bytes
            self._previous_done, self._previous_sample = done, now
            snapshot = self._progress.copy()
        self._events.emit_progress(snapshot)

    def _finish(self, code: int, cancelled: bool) -> None:
        with self._lock:
            self._sample()
            if not cancelled:
                if code == 0:
                    self._progress.state = "finished"
                    self._purge_incomplete()
                else:
                    self._progress.state = "failed"
                    self._progress.error = {"code": "download_failed", "message": f"hf exited {code}", "returncode": code}
            final_status: Any = None
            if self._manifest is not None:
                final_status = verify_tree(self._model, self._manifest, Path(self._resolve_paths().models_root))
            self._handle = None
            snapshot = self._progress.copy()
        self._events.emit_finished(snapshot, final_status)

    def _purge_incomplete(self) -> None:
        model = self._model
        if model is None:
            return
        cache = Path(self._resolve_paths().models_root) / model.relpath / ".cache" / "huggingface" / "download"
        try:
            for path in cache.rglob("*.incomplete"):
                path.unlink(missing_ok=True)
        except OSError:
            pass
