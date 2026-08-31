"""api:completeFirstRun / api:adoptLegacyModels (R-foundation-03/04)."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

from . import config as config_mod
from .errors import (
    AdoptConflictError,
    AdoptError,
    InsufficientSpaceError,
    LegacyRootError,
    NotWritableError,
)
from .paths import normalize_user_path


LEGACY_SUBTREES = ("llms", "minimax-h3", "minimax-music3")
_SAFETY_MARGIN_BYTES = 1 << 30
_copy2 = shutil.copy2


@dataclass(frozen=True)
class AdoptResult:
    mode: str
    models_root: Path
    adopted: list[str]
    moved_bytes: int
    source_retained: bool


def complete_first_run(roots, models_root: Path | None = None) -> config_mod.DeskConfig:
    """Probe the models root, then atomically record first-run completion."""
    target = normalize_user_path(models_root) if models_root else roots.data_root / "models"
    try:
        target.mkdir(parents=True, exist_ok=True)
        probe = target / ".lmd-write-probe"
        probe.write_bytes(b"lmd")
        probe.unlink()
    except OSError as exc:
        raise NotWritableError(
            f"models root not writable: {target}: {exc}",
            path=str(target),
            os_error=str(exc),
        ) from exc
    return config_mod.update_config(roots, models_root=target, first_run_done=True)


def adopt_legacy_models(roots, legacy_root, mode: str, target_root=None) -> AdoptResult:
    """Adopt a recognized legacy root by pointing to or moving its subtrees."""
    legacy = normalize_user_path(legacy_root)
    found = [name for name in LEGACY_SUBTREES if (legacy / name).is_dir()]
    if not found:
        raise LegacyRootError(
            f"no known model subtrees ({', '.join(LEGACY_SUBTREES)}) under {legacy}",
            path=str(legacy),
        )
    if mode == "point":
        config_mod.update_config(roots, models_root=legacy, first_run_done=True)
        return AdoptResult("point", legacy, found, 0, False)
    if mode == "move":
        return _adopt_move(roots, legacy, found, target_root)
    raise LegacyRootError(f"unknown adopt mode: {mode!r}", mode=str(mode))


def _tree_bytes(root: Path) -> int:
    total = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            path = Path(dirpath) / name
            if not path.is_symlink():
                total += path.stat().st_size
    return total


def _same_volume(left: Path, right: Path) -> bool:
    return left.stat().st_dev == right.stat().st_dev


def _adopt_move(roots, legacy: Path, found: list[str], target_root) -> AdoptResult:
    target = normalize_user_path(target_root) if target_root else roots.data_root / "models"
    if target == legacy or target.is_relative_to(legacy):
        raise LegacyRootError(
            f"target root {target} lies inside legacy root {legacy}", path=str(target)
        )
    target.mkdir(parents=True, exist_ok=True)
    # Include subtrees already moved by an interrupted same-volume attempt so a
    # retry reports the complete adopted set.
    found = [
        name
        for name in LEGACY_SUBTREES
        if (legacy / name).is_dir() or (target / name).is_dir()
    ]
    if not _same_volume(legacy, target):
        return _move_cross_volume(roots, legacy, found, target)
    return _move_same_volume(roots, legacy, found, target)


def _move_same_volume(roots, legacy: Path, found: list[str], target: Path) -> AdoptResult:
    adopted: list[str] = []
    moved_bytes = 0
    for name in found:
        src, dst = legacy / name, target / name
        if not src.exists():
            adopted.append(name)
            continue
        if dst.exists() and dst.is_dir() and any(dst.iterdir()):
            raise AdoptConflictError(
                f"target already has a non-empty {name!r}: {dst}",
                subtree=name,
                path=str(dst),
            )
        size = _tree_bytes(src)
        try:
            os.rename(src, dst)
        except OSError as exc:
            raise AdoptError(
                f"move failed on subtree {name!r}: {exc}",
                adopted=list(adopted),
                remaining=[item for item in found if item not in adopted],
            ) from exc
        adopted.append(name)
        moved_bytes += size
    config_mod.update_config(roots, models_root=target, first_run_done=True)
    return AdoptResult("move", target, adopted, moved_bytes, False)


def _copy_tree_resumable(src: Path, dst: Path) -> int:
    """Copy files while retaining matching files from an interrupted attempt."""
    copied = 0
    for dirpath, _dirnames, filenames in os.walk(src):
        relative = Path(dirpath).relative_to(src)
        destination_dir = dst / relative
        destination_dir.mkdir(parents=True, exist_ok=True)
        for name in sorted(filenames):
            source = Path(dirpath) / name
            destination = destination_dir / name
            if destination.exists() and destination.stat().st_size == source.stat().st_size:
                continue
            _copy2(source, destination)
            copied += source.stat().st_size
    return copied


def _move_cross_volume(roots, legacy: Path, found: list[str], target: Path) -> AdoptResult:
    total = sum(_tree_bytes(legacy / name) for name in found)
    needed = total + _SAFETY_MARGIN_BYTES
    free = shutil.disk_usage(target).free
    if free < needed:
        raise InsufficientSpaceError(
            f"not enough space on target volume: need {needed} bytes, free {free} bytes, "
            f"short {needed - free} bytes",
            needed_bytes=needed,
            free_bytes=free,
            shortfall_bytes=needed - free,
        )

    adopted: list[str] = []
    moved_bytes = 0
    for name in found:
        try:
            moved_bytes += _copy_tree_resumable(legacy / name, target / name)
        except OSError as exc:
            raise AdoptError(
                f"copy failed on subtree {name!r}: {exc}",
                adopted=list(adopted),
                remaining=[item for item in found if item not in adopted],
            ) from exc
        adopted.append(name)
    config_mod.update_config(roots, models_root=target, first_run_done=True)
    return AdoptResult("move", target, adopted, moved_bytes, True)
