"""R-foundation-05: missing pieces become queryable state, never a dead service."""
from __future__ import annotations

import importlib.util
import os
import subprocess
import time
from functools import lru_cache
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


@lru_cache(maxsize=8)
def _image_importable(python: str, pythonpath: str, interpreter_mtime: float, freshness: int) -> bool:
    env = dict(os.environ)
    if pythonpath:
        env["PYTHONPATH"] = pythonpath
    try:
        result = subprocess.run([python, "-s", "-c",
            "import importlib.util; print(all(importlib.util.find_spec(n) is not None for n in ('mflux','mlx')))"],
            env=env, capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and result.stdout.strip() == "True"
    except (OSError, subprocess.TimeoutExpired):
        return False


def probe_capabilities(roots) -> dict[str, Capability]:
    """Return five read-only capability states without blocking startup."""
    caps: dict[str, Capability] = {}
    image_python = getattr(roots, "image_python", None)
    image_path = (getattr(roots, "image_env", {}) or {}).get("PYTHONPATH", "")
    present = bool(image_python and _executable(image_python) and
                   _image_importable(str(image_python), image_path, image_python.stat().st_mtime, int(time.monotonic() // 10)))
    caps["image_runtime"] = Capability(present, str(image_python or ""),
        "" if present else "图片 MLX 运行环境缺失，请安装 .venv-image 或使用包含图片运行时的应用")

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
