"""Pure manifest-to-local-tree completeness verification (R-resources-02/03)."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .catalog import ModelEntry
from .disk import dir_bytes
from .manifest import Manifest
from .parts import part_bytes


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
    bytes_in_flight: int = 0
    stale_bytes: int = 0
    resumable_bytes: int = 0

    def to_json(self) -> dict:
        payload = asdict(self)
        payload["gaps"] = [asdict(gap) for gap in self.gaps]
        return payload


def _incomplete_bytes(model_dir: Path, active_since: float | None) -> tuple[int, int]:
    """Split hf's .incomplete blobs into (this attempt's in-flight, previous attempts' stale).

    A blob only belongs to the current attempt when its mtime is no older than
    ``active_since`` (with a 1s buffer for filesystem timestamp coarseness). When
    ``active_since`` is None (no download is currently running for this model),
    every .incomplete blob is dead weight from a past, now-unresumable attempt —
    it must be reported, never counted toward progress (J18).
    """
    cache = model_dir / ".cache" / "huggingface" / "download"
    fresh = stale = 0
    try:
        for path in cache.rglob("*.incomplete"):
            try:
                if not path.is_file():
                    continue
                stat = path.stat()
            except OSError:
                continue
            if active_since is not None and stat.st_mtime + 1 >= active_since:
                fresh += stat.st_size
            else:
                stale += stat.st_size
    except OSError:
        return 0, 0
    return fresh, stale


def verify_tree(entry: ModelEntry, manifest: Manifest, models_root: Path, *,
                 active_since: float | None = None) -> ModelStatus:
    """Stat manifest paths and return their byte-accurate completeness status.

    ``active_since`` should be the wall-clock time the current download attempt
    (if any) started; pass None when no download is running for this model so
    leftover .incomplete blobs from a dead attempt are reported as stale rather
    than counted as in-flight progress (J18).
    """
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

    fresh, stale = _incomplete_bytes(model_dir, active_since)
    resumable = 0 if not gaps else part_bytes(model_dir, manifest.files)
    in_flight = 0 if not gaps else min(fresh, max(expected_total - local_total - resumable, 0))
    counted = local_total + resumable + in_flight
    state = "present" if not gaps else "missing" if counted == 0 else "partial"
    percent = round(min(counted / expected_total, 1.0) * 100.0, 2) if expected_total else 0.0
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
        bytes_in_flight=in_flight,
        stale_bytes=stale,
        resumable_bytes=resumable,
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
        stale_bytes=0,
    )
