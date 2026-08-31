"""data:deskConfig — defaults merge, needs_setup, atomic persistence."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigCorruptError


CONFIG_VERSION = 1
_KNOWN_KEYS = {"config_version", "first_run_done", "models_root", "outputs_root", "gateway"}
_GATEWAY_KEYS = {"enabled", "host", "port"}
_LOCK = threading.Lock()


@dataclass(frozen=True)
class GatewayConfig:
    enabled: bool
    host: str
    port: int


@dataclass(frozen=True)
class DeskConfig:
    config_version: int
    first_run_done: bool
    models_root: Path
    outputs_root: Path
    gateway: GatewayConfig
    needs_setup: bool
    extra: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        out = dict(self.extra)
        out.update({
            "config_version": self.config_version,
            "first_run_done": self.first_run_done,
            "models_root": str(self.models_root),
            "outputs_root": str(self.outputs_root),
            "gateway": {
                "enabled": self.gateway.enabled,
                "host": self.gateway.host,
                "port": self.gateway.port,
            },
        })
        return out


def _defaults(data_root: Path) -> dict:
    return {
        "config_version": CONFIG_VERSION,
        "first_run_done": False,
        "models_root": str(data_root / "models"),
        "outputs_root": str(data_root / "outputs"),
        "gateway": {"enabled": True, "host": "0.0.0.0", "port": 8770},
    }


def _load_raw(config_path: Path) -> dict | None:
    """Return None when absent; reject malformed persisted configuration."""
    if not config_path.exists():
        return None
    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ConfigCorruptError(
            f"config.json is corrupt: {config_path}: {exc}",
            path=str(config_path), parse_error=str(exc),
        ) from exc
    if not isinstance(raw, dict):
        raise ConfigCorruptError(
            f"config.json is corrupt: {config_path}: top level is not an object",
            path=str(config_path), parse_error="top level is not an object",
        )
    return raw


def _from_raw(raw: dict | None, data_root: Path) -> DeskConfig:
    defaults = _defaults(data_root)
    merged = dict(defaults)
    file_gateway: dict = {}
    if raw:
        for key, value in raw.items():
            if key == "gateway" and isinstance(value, dict):
                file_gateway = value
            elif key in _KNOWN_KEYS:
                merged[key] = value
    gateway = dict(defaults["gateway"])
    gateway.update({key: value for key, value in file_gateway.items() if key in _GATEWAY_KEYS})
    extra = {key: value for key, value in (raw or {}).items() if key not in _KNOWN_KEYS}
    return DeskConfig(
        config_version=int(merged["config_version"]),
        first_run_done=bool(merged["first_run_done"]),
        models_root=Path(merged["models_root"]),
        outputs_root=Path(merged["outputs_root"]),
        gateway=GatewayConfig(
            enabled=bool(gateway["enabled"]),
            host=str(gateway["host"]),
            port=int(gateway["port"]),
        ),
        needs_setup=(raw is None) or not bool(merged["first_run_done"]),
        extra=extra,
    )


def default_config(data_root: Path) -> DeskConfig:
    """Return pure defaults, as if config.json were absent."""
    return _from_raw(None, data_root)


def read_config(roots) -> DeskConfig:
    """Read configuration from duck-typed roots with data_root and config_path."""
    with _LOCK:
        raw = _load_raw(roots.config_path)
    return _from_raw(raw, roots.data_root)


def _atomic_write(config_path: Path, payload: dict) -> None:
    """Write via a same-directory temporary file so readers never see torn JSON."""
    config_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = config_path.with_name(
        f"{config_path.name}.tmp-{os.getpid()}-{os.urandom(4).hex()}"
    )
    try:
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, config_path)
    except BaseException:
        try:
            tmp.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def write_config(roots, config: DeskConfig) -> None:
    """api:writeConfig — atomically write a complete configuration document."""
    with _LOCK:
        _atomic_write(roots.config_path, config.to_json())


def update_config(roots, **fields) -> DeskConfig:
    """Locked read-modify-write so concurrent updates cannot drop fields."""
    with _LOCK:
        raw = _load_raw(roots.config_path)
        current = _from_raw(raw, roots.data_root)
        merged = current.to_json()
        for key, value in fields.items():
            if key == "gateway" and isinstance(value, dict):
                gateway = dict(merged["gateway"])
                gateway.update({key: val for key, val in value.items() if key in _GATEWAY_KEYS})
                merged["gateway"] = gateway
            elif isinstance(value, Path):
                merged[key] = str(value)
            else:
                merged[key] = value
        _atomic_write(roots.config_path, merged)
        return _from_raw(merged, roots.data_root)
