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
    bytes_in_flight: int = 0

    def to_json(self) -> dict:
        payload = asdict(self)
        payload["gaps"] = [asdict(gap) for gap in self.gaps]
        return payload


def _in_flight_bytes(model_dir: Path) -> int:
    """Bytes sitting in hf's .incomplete files: downloaded but not yet moved into place."""
    cache = model_dir / ".cache" / "huggingface" / "download"
    total = 0
    try:
        for path in cache.rglob("*.incomplete"):
            try:
                if path.is_file():
                    total += path.stat().st_size
            except OSError:
                continue
    except OSError:
        return 0
    return total


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

    in_flight = 0 if not gaps else min(_in_flight_bytes(model_dir), max(expected_total - local_total, 0))
    counted = local_total + in_flight
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
