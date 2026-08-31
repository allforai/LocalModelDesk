"""api:completeFirstRun / api:adoptLegacyModels (R-foundation-03/04)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from . import config as config_mod
from .errors import LegacyRootError, NotWritableError
from .paths import normalize_user_path


LEGACY_SUBTREES = ("llms", "minimax-h3", "minimax-music3")


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
    """Adopt a recognized legacy root by pointing configuration at it."""
    legacy = normalize_user_path(legacy_root)
    found = [name for name in LEGACY_SUBTREES if (legacy / name).is_dir()]
    if not found:
        raise LegacyRootError(
            f"no known model subtrees ({', '.join(LEGACY_SUBTREES)}) under {legacy}",
            path=str(legacy),
        )
    if mode != "point":
        raise LegacyRootError(f"unknown adopt mode: {mode!r}", mode=str(mode))
    config_mod.update_config(roots, models_root=legacy, first_run_done=True)
    return AdoptResult("point", legacy, found, 0, False)
