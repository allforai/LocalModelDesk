"""Disk accounting and volume free-space reporting (R-resources-04)."""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

from .catalog import ModelEntry


def dir_bytes(path: Path) -> int:
    """Return the sum of lstat sizes below path without following symlinks."""
    path = Path(path)
    if not path.exists():
        return 0
    if path.is_file():
        return path.lstat().st_size

    total = 0
    for root, _directories, files in os.walk(path):
        for name in files:
            try:
                total += (Path(root) / name).lstat().st_size
            except OSError:
                continue
    return total


def volume_free(path: Path) -> tuple[int, int]:
    """Return user-available and total bytes for path's volume."""
    probe = Path(path)
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            break
        probe = parent
    stat = os.statvfs(probe)
    return stat.f_bavail * stat.f_frsize, stat.f_blocks * stat.f_frsize


@dataclass(frozen=True)
class DiskUsage:
    models_root: str
    free_bytes: int
    total_bytes: int
    per_model: dict[str, int]

    def to_json(self) -> dict:
        return asdict(self)


def disk_usage(models_root: Path, entries: Iterable[ModelEntry]) -> DiskUsage:
    """Return volume and per-catalog-model disk usage for a models root."""
    free, total = volume_free(models_root)
    per_model = {
        entry.key: dir_bytes(Path(models_root) / entry.relpath)
        for entry in entries
    }
    return DiskUsage(
        models_root=str(models_root),
        free_bytes=free,
        total_bytes=total,
        per_model=per_model,
    )
