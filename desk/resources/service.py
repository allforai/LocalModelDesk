"""Facade assembling catalog, manifests, verification, disk usage, and downloads."""
from __future__ import annotations

import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

from . import catalog
from .catalog import CATALOG, ModelEntry
from .disk import DiskUsage, dir_bytes, disk_usage
from .downloader import DownloadProgress, Downloader
from .errors import (ConfirmRequiredError, DownloadBusyError, HfCliMissingError,
                     ManifestUnavailableError, MediaBusyError, PathEscapeError)
from .events import ResourceEvents
from .manifest import ManifestStore, default_fetcher
from .verify import ModelStatus, unknown_status, verify_tree


class _SubprocessExecutor:
    def spawn(self, cmd, cwd=None):
        return subprocess.Popen(cmd, cwd=cwd)


class _InjectableDownloader(Downloader):
    """Downloader variant whose sampler side effects are supplied by the facade."""

    def __init__(self, *args, sleep: Callable, thread_factory: Callable, **kwargs):
        super().__init__(*args, **kwargs)
        self._sleep = sleep
        self._thread_factory = thread_factory

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
            model = catalog.entry(key)
            roots = self._resolve_paths()
            hf_cmd = tuple(roots.hf_cmd)
            if not hf_cmd or not Path(hf_cmd[0]).exists():
                raise HfCliMissingError("hf command is unavailable")
            try:
                manifest = self._manifest_store.get(model, refresh=True)
            except Exception:
                manifest = None
            try:
                handle = self._executor.spawn(
                    [*hf_cmd, "download", model.hf_repo, "--local-dir",
                     str(Path(roots.models_root) / model.relpath)], cwd=None)
            except FileNotFoundError as exc:
                raise HfCliMissingError("hf command is unavailable") from exc
            now = self._clock()
            self._progress = DownloadProgress(key=model.key, state="running",
                                              bytes_total=manifest.total_bytes if manifest else 0,
                                              started_at=str(now))
            self._handle, self._model, self._manifest = handle, model, manifest
            self._cancel_at = None
            self._previous_done, self._previous_sample = 0, now
            self._thread_factory(target=self._sample_loop, daemon=True).start()
            return self._progress.copy()

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
            self._sleep(self._sample_interval)


def _resolve_delete_target(models_root: Path, entry: ModelEntry) -> Path:
    """Return a catalog target only when it resolves inside the models root."""
    root = Path(models_root).resolve()
    target = (Path(models_root) / entry.relpath).resolve()
    if target == root or not target.is_relative_to(root):
        raise PathEscapeError(
            f"refusing to delete: {entry.relpath!r} resolves outside the models root",
            detail={"target": str(target), "models_root": str(root)},
        )
    return target


class ResourcesService:
    """Resources API facade whose path roots are resolved for every operation."""

    def __init__(self, resolve_paths: Callable, can_start_heavy: Callable,
                 fetcher: Callable = default_fetcher, executor=None,
                 clock=time.monotonic, sleep=time.sleep,
                 sample_interval: float = 1.0, thread_factory=threading.Thread):
        self._resolve_paths = resolve_paths
        self.events = ResourceEvents()
        self._manifests = ManifestStore(
            cache_dir_provider=lambda: Path(self._resolve_paths().data_root) / "manifests",
            fetcher=fetcher,
        )
        self._downloader = _InjectableDownloader(
            executor=executor if executor is not None else _SubprocessExecutor(),
            manifest_store=self._manifests,
            resolve_paths=resolve_paths,
            can_start_heavy=can_start_heavy,
            events=self.events,
            clock=clock,
            sample_interval=sample_interval,
            sleep=sleep,
            thread_factory=thread_factory,
        )

    def list_catalog(self) -> list[ModelEntry]:
        return catalog.list_catalog()

    def verify_model(self, key: str, refresh: bool = False) -> ModelStatus:
        model = catalog.entry(key)
        roots = self._resolve_paths()
        model_dir = Path(roots.models_root) / model.relpath
        try:
            manifest = self._manifests.get(model, refresh=refresh)
        except ManifestUnavailableError:
            return unknown_status(model, dir_bytes(model_dir))
        return verify_tree(model, manifest, Path(roots.models_root))

    def verify_all_models(self, refresh: bool = False) -> list[ModelStatus]:
        return [self.verify_model(model.key, refresh=refresh) for model in CATALOG]

    def disk_usage(self) -> DiskUsage:
        return disk_usage(Path(self._resolve_paths().models_root), CATALOG)

    def start_download(self, key: str) -> DownloadProgress:
        return self._downloader.start(key)

    def cancel_download(self) -> DownloadProgress:
        return self._downloader.cancel()

    def download_progress(self) -> DownloadProgress:
        return self._downloader.progress()

    def delete_model(self, key: str, confirm: str | None = None) -> dict:
        model = catalog.entry(key)
        if confirm != model.key:
            raise ConfirmRequiredError(
                f"deleteModel refused: pass confirm={model.key!r} to delete this model")
        target = _resolve_delete_target(Path(self._resolve_paths().models_root), model)
        with self._downloader._lock:
            active = self._downloader._handle is not None
            downloading = self._downloader._model
            if active and downloading is not None and downloading.key == model.key:
                raise DownloadBusyError(
                    f"{model.key!r} is currently downloading; wait for it to exit first")
            freed = dir_bytes(target)
            if target.is_dir():
                shutil.rmtree(target)
            elif target.exists():
                target.unlink()
        return {"key": model.key, "freed_bytes": freed}
