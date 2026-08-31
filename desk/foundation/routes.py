"""HTTP adapter for foundation: parse requests, call APIs, serialize results."""
from __future__ import annotations

from . import capabilities as caps_mod
from . import config as config_mod
from . import firstrun
from . import paths as paths_mod
from .errors import LegacyRootError
from .paths import normalize_user_path


def _roots():
    return paths_mod.resolve_paths()


def _config_json(cfg: config_mod.DeskConfig) -> dict:
    result = cfg.to_json()
    result["needs_setup"] = cfg.needs_setup
    return result


def get_config(_req) -> dict:
    roots = _roots()
    return _config_json(config_mod.read_config(roots))


def put_config(req) -> dict:
    return _config_json(config_mod.update_config(_roots(), **req.body))


def get_paths(_req) -> dict:
    roots = paths_mod.resolve_paths(default_config_on_corrupt=True)
    caps = caps_mod.probe_capabilities(roots)
    return {
        "mode": roots.mode,
        "resources_root": str(roots.resources_root),
        "static_dir": str(roots.static_dir),
        "venv_python": str(roots.venv_python),
        "mlx_h3_cmd": list(roots.mlx_h3_cmd),
        "mlx_h3_env": dict(roots.mlx_h3_env),
        "music_python": str(roots.music_python),
        "music_env": dict(roots.music_env),
        "media_cli_dir": str(roots.media_cli_dir),
        "hf_cmd": list(roots.hf_cmd),
        "data_root": str(roots.data_root),
        "config_path": str(roots.config_path),
        "logs_dir": str(roots.logs_dir),
        "sessions_dir": str(roots.sessions_dir),
        "history_path": str(roots.history_path),
        "models_root": str(roots.models_root),
        "outputs_root": str(roots.outputs_root),
        "capabilities": {name: {"present": cap.present, "path": cap.path, "detail": cap.detail} for name, cap in caps.items()},
    }


def post_first_run(req) -> dict:
    raw = req.body.get("models_root")
    cfg = firstrun.complete_first_run(_roots(), normalize_user_path(raw) if raw else None)
    return _config_json(cfg)


def post_adopt(req) -> dict:
    legacy_root, mode = req.body.get("legacy_root"), req.body.get("mode")
    if not legacy_root or mode not in ("point", "move"):
        raise LegacyRootError("body must include legacy_root and mode 'point'|'move'")
    raw_target = req.body.get("target_root")
    result = firstrun.adopt_legacy_models(
        _roots(), normalize_user_path(legacy_root), mode,
        target_root=normalize_user_path(raw_target) if raw_target else None,
    )
    return {"mode": result.mode, "models_root": str(result.models_root), "adopted": list(result.adopted), "moved_bytes": result.moved_bytes, "source_retained": result.source_retained}


def build_routes() -> list:
    return [
        ("GET", "/api/config", get_config),
        ("PUT", "/api/config", put_config),
        ("GET", "/api/paths", get_paths),
        ("POST", "/api/first-run", post_first_run),
        ("POST", "/api/adopt", post_adopt),
    ]
