"""Facade assembling catalog, manifests, verification, disk usage, and downloads."""
from __future__ import annotations

import os
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
from ..foundation.errors import ConfigCorruptError
from .errors import ConfirmRequiredError, DownloadBusyError, ManifestUnavailableError, PathEscapeError
from .events import ResourceEvents
from .fit import model_fit
from .manifest import ManifestStore, default_fetcher
from .verify import ModelStatus, unknown_status, verify_tree


class _SubprocessExecutor:
    def spawn(self, cmd, cwd=None, extra_env=None):
        env = dict(os.environ)
        env.update(extra_env or {})
        return subprocess.Popen(cmd, cwd=cwd, env=env)


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
                 sample_interval: float = 1.0, thread_factory=threading.Thread,
                 budget=None):
        self._resolve_paths = resolve_paths
        # 没有 budget 就是没有能力问机器——list_catalog_with_fit() 对每个模型都
        # 老实报 unknown，不是没接线就悄悄不带这个字段（G8 同一条纪律：半接线比
        # 不接线更危险，因为它看起来像接好了）。
        self._budget = budget
        self.events = ResourceEvents()
        self._manifests = ManifestStore(
            cache_dir_provider=lambda: Path(self._resolve_paths().data_root) / "manifests",
            fetcher=fetcher,
        )
        self._downloader = Downloader(
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

    def list_catalog_with_fit(self) -> list[dict]:
        """目录 + 每个模型的机型适配判定——resources 端点唯一回答"这个模型行不行"的地方。

        不新增一个平行接口去问同一个问题（这个代码库已经被"两个入口两套答案"咬过）：
        直接扩展 list_catalog() 本来就要给前端的那份数据。
        """
        try:
            models_root = self._resolve_paths().models_root
        except ConfigCorruptError:
            # config.json 读不出来不该把目录端点也拖下水——降级成「模型都当没下载」，
            # 而不是让本来零 IO 的目录列表也跟着 500（和网关配置读取同一条纪律：
            # runtime.py 的 _gateway_config_reader 遇到同样的坏文件也是退默认值）。
            models_root = None
        return [
            {**entry.to_json(), "fit": model_fit(entry, self._budget, models_root)}
            for entry in catalog.list_catalog()
        ]

    def verify_model(self, key: str, refresh: bool = False) -> ModelStatus:
        model = catalog.entry(key)
        roots = self._resolve_paths()
        model_dir = Path(roots.models_root) / model.relpath
        try:
            manifest = self._manifests.get(model, refresh=refresh)
        except ManifestUnavailableError:
            return unknown_status(model, dir_bytes(model_dir))
        progress = self._downloader.progress()
        active_since = self._downloader.attempt_wall if (
            progress.state == "running" and progress.key == model.key
        ) else None
        return verify_tree(model, manifest, Path(roots.models_root), active_since=active_since)

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

    def close(self) -> None:
        self._downloader.close()

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
