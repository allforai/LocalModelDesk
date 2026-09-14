"""Where resumable download bytes live, and how many of them count as progress."""
from __future__ import annotations

from pathlib import Path

PARTS_DIR = (".cache", "localmodeldesk", "parts")


def part_path(model_dir: Path, rel_path: str) -> Path:
    return Path(model_dir).joinpath(*PARTS_DIR, rel_path + ".part")


def attempt_manifest_path(model_dir: Path) -> Path:
    return Path(model_dir) / ".cache" / "localmodeldesk" / "manifest.json"


def part_bytes(model_dir: Path, files) -> int:
    """Bytes already on disk for files whose final copy is not complete yet."""
    total = 0
    for file in files:
        try:
            if (Path(model_dir) / file.path).stat().st_size == file.size:
                continue
        except OSError:
            pass
        try:
            total += min(part_path(model_dir, file.path).stat().st_size, file.size)
        except OSError:
            continue
    return total
