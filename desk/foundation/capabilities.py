"""R-foundation-05: missing pieces become queryable state, never a dead service."""
from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from pathlib import Path

from . import config as config_mod
from .errors import ConfigCorruptError


@dataclass(frozen=True)
class Capability:
    present: bool
    path: str
    detail: str = ""


def _executable(path: Path) -> bool:
    return path.exists() and os.access(path, os.X_OK)


def probe_capabilities(roots) -> dict[str, Capability]:
    """Return five read-only capability states without blocking startup."""
    caps: dict[str, Capability] = {}

    if roots.mode == "bundle":
        package = roots.resources_root / "pylibs" / "h3" / "mlx_h3"
        present = package.is_dir()
        caps["mlx_h3"] = Capability(
            present, str(package), "" if present else "mlx_h3 package dir missing from bundle"
        )
    else:
        executable = Path(roots.mlx_h3_cmd[0]) if roots.mlx_h3_cmd else None
        present = executable is not None and _executable(executable)
        caps["mlx_h3"] = Capability(
            present,
            str(executable) if executable else "",
            "" if present else "mlx-h3 executable not found",
        )

    present = _executable(roots.venv_python)
    caps["venv"] = Capability(
        present,
        str(roots.venv_python),
        "" if present else "python interpreter missing or not executable",
    )

    present = roots.models_root.is_dir()
    caps["models_root"] = Capability(
        present,
        str(roots.models_root),
        "" if present else "models root directory does not exist",
    )

    if roots.mode == "bundle":
        package = roots.resources_root / "pylibs" / "music" / "mlx_minimax_music3"
        present = package.is_dir()
        caps["music_runtime"] = Capability(
            present,
            str(package),
            "" if present else "mlx_minimax_music3 package dir missing from bundle",
        )
    else:
        present = importlib.util.find_spec("mlx_minimax_music3") is not None
        caps["music_runtime"] = Capability(
            present,
            "mlx_minimax_music3",
            "" if present else "mlx_minimax_music3 not importable",
        )

    try:
        config_mod.read_config(roots)
        caps["config"] = Capability(True, str(roots.config_path))
    except ConfigCorruptError as exc:
        caps["config"] = Capability(False, str(roots.config_path), str(exc))

    return caps
