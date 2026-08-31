"""Pure manifest-to-local-tree completeness verification (R-resources-02/03)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .catalog import ModelEntry
from .disk import dir_bytes
from .manifest import Manifest


@dataclass(frozen=True)
class FileGap:
    path: str
    expected_size: int
    local_size: int


@dataclass(frozen=True)
class ModelStatus:
    key: str
    state: str
    percent: float
    bytes_expected: int
    bytes_local: int
    disk_bytes: int
    gaps: tuple[FileGap, ...]
    manifest_source: str
    manifest_fetched_at: str | None
    reason: str | None = None

    def to_json(self) -> dict:
        payload = asdict(self)
        payload["gaps"] = [asdict(gap) for gap in self.gaps]
        return payload


def verify_tree(entry: ModelEntry, manifest: Manifest, models_root: Path) -> ModelStatus:
    """Stat manifest paths and return their byte-accurate completeness status."""
    model_dir = Path(models_root) / entry.relpath
    expected_total = manifest.total_bytes
    local_total = 0
    gaps: list[FileGap] = []

    for file in manifest.files:
        try:
            local_size = (model_dir / file.path).lstat().st_size
        except OSError:
            local_size = 0
        local_total += min(local_size, file.size)
        if local_size != file.size:
            gaps.append(FileGap(file.path, file.size, local_size))

    state = "present" if not gaps else "missing" if local_total == 0 else "partial"
    percent = round(local_total / expected_total * 100.0, 2) if expected_total else 0.0
    return ModelStatus(
        key=entry.key,
        state=state,
        percent=percent,
        bytes_expected=expected_total,
        bytes_local=local_total,
        disk_bytes=dir_bytes(model_dir),
        gaps=tuple(gaps),
        manifest_source=manifest.source,
        manifest_fetched_at=manifest.fetched_at,
    )


def unknown_status(entry: ModelEntry, disk_bytes_: int) -> ModelStatus:
    """Report an honest status when no usable manifest is available."""
    return ModelStatus(
        key=entry.key,
        state="unknown",
        percent=0.0,
        bytes_expected=0,
        bytes_local=0,
        disk_bytes=disk_bytes_,
        gaps=(),
        manifest_source="none",
        manifest_fetched_at=None,
        reason="manifest_unavailable",
    )
