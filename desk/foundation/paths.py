"""Single source of truth for paths and execution environment selection."""
from __future__ import annotations

import os
import logging
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from . import config as config_mod
from .errors import ConfigCorruptError


_MLX_H3_ENTRY = "from mlx_h3.cli import main; main()"
_HF_ENTRY = "from huggingface_hub.cli.hf import main; main()"
_LOGGING_CONFIGURED = False


def normalize_user_path(value) -> Path:
    """Expand a user path and return its absolute, normalized form."""
    return Path(value).expanduser().resolve()


@dataclass(frozen=True)
class PathRoots:
    mode: str
    resources_root: Path
    static_dir: Path
    venv_python: Path
    mlx_h3_cmd: tuple
    mlx_h3_env: dict
    music_python: Path
    music_env: dict
    media_cli_dir: Path
    hf_cmd: tuple
    data_root: Path
    config_path: Path
    logs_dir: Path
    sessions_dir: Path
    history_path: Path
    models_root: Path
    outputs_root: Path


@dataclass(frozen=True)
class _StaticRoots:
    mode: str
    resources_root: Path
    data_root: Path
    config_path: Path


def _static_roots(data_root=None, resources_root=None) -> _StaticRoots:
    if resources_root is None:
        import desk

        resources_root = Path(desk.__file__).resolve().parent.parent
    resources_root = normalize_user_path(resources_root)
    if data_root is None:
        env_root = os.environ.get("LOCALMODELDESK_DATA_ROOT")
        data_root = Path(env_root) if env_root else Path.home() / "Library" / "Application Support" / "LocalModelDesk"
    data_root = normalize_user_path(data_root)
    return _StaticRoots(
        mode="bundle" if (resources_root / "bundle.json").exists() else "dev",
        resources_root=resources_root,
        data_root=data_root,
        config_path=data_root / "config.json",
    )


def _mlx_h3_dev_cmd() -> tuple:
    override = os.environ.get("LOCALMODELDESK_MLX_H3")
    if override:
        return (override,)
    found = shutil.which("mlx-h3")
    return (found,) if found else (str(Path.home() / ".local" / "bin" / "mlx-h3"),)


def _hf_dev_cmd() -> tuple:
    override = os.environ.get("LOCALMODELDESK_HF")
    if override:
        return (override,)
    found = shutil.which("hf")
    return (found,) if found else ()


def resolve_paths(*, data_root=None, resources_root=None, default_config_on_corrupt: bool = False) -> PathRoots:
    """Return fresh roots, including current configuration-derived locations."""
    static = _static_roots(data_root=data_root, resources_root=resources_root)
    try:
        config = config_mod.read_config(static)
    except ConfigCorruptError:
        if not default_config_on_corrupt:
            raise
        config = config_mod.default_config(static.data_root)

    if static.mode == "bundle":
        python = static.resources_root / "python" / "bin" / "python3.13"
        mlx_h3_cmd = (str(python), "-s", "-c", _MLX_H3_ENTRY)
        mlx_h3_env = {"PYTHONPATH": str(static.resources_root / "pylibs" / "h3")}
        music_env = {"PYTHONPATH": str(static.resources_root / "pylibs" / "music")}
        hf_cmd = (str(python), "-s", "-c", _HF_ENTRY)
    else:
        python = Path(sys.executable)
        mlx_h3_cmd = _mlx_h3_dev_cmd()
        mlx_h3_env = {}
        music_env = {}
        hf_cmd = _hf_dev_cmd()

    roots = PathRoots(
        mode=static.mode,
        resources_root=static.resources_root,
        static_dir=static.resources_root / "desk" / "static",
        venv_python=python,
        mlx_h3_cmd=mlx_h3_cmd,
        mlx_h3_env=mlx_h3_env,
        music_python=python,
        music_env=music_env,
        media_cli_dir=static.resources_root / "desk" / "media",
        hf_cmd=hf_cmd,
        data_root=static.data_root,
        config_path=static.config_path,
        logs_dir=static.data_root / "logs",
        sessions_dir=static.data_root / "sessions",
        history_path=static.data_root / "history.jsonl",
        models_root=config.models_root,
        outputs_root=config.outputs_root,
    )
    roots.data_root.mkdir(parents=True, exist_ok=True)
    roots.logs_dir.mkdir(parents=True, exist_ok=True)
    return roots


def setup_logging(roots: PathRoots) -> None:
    """Configure the codebase's sole file logger under the data root."""
    global _LOGGING_CONFIGURED
    if _LOGGING_CONFIGURED:
        return
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    file_handler = logging.FileHandler(roots.logs_dir / "desk.log", encoding="utf-8")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s")
    )
    root.addHandler(file_handler)
    root.addHandler(logging.StreamHandler(sys.stderr))
    _LOGGING_CONFIGURED = True
