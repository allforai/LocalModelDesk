"""data:deskConfig — defaults merge, needs_setup, atomic persistence."""
from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from .errors import ConfigCorruptError, ConfigInvalidError, ConfigNotCorruptError


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
            "配置文件无法读取（内容不是合法 JSON）；可以点「重新设置」重建一份，坏文件会自动备份。",
            path=str(config_path), parse_error=str(exc), recoverable=True,
        ) from exc
    if not isinstance(raw, dict):
        raise ConfigCorruptError(
            "配置文件无法读取（顶层结构不是对象）；可以点「重新设置」重建一份，坏文件会自动备份。",
            path=str(config_path), parse_error="top level is not an object", recoverable=True,
        )
    return raw


def _validate(merged: dict, gateway: dict) -> None:
    """Raise ConfigInvalidError naming the first offending field."""
    def bad(field: str, reason: str) -> None:
        raise ConfigInvalidError(f"invalid {field}: {reason}", field=field, reason=reason)
    if not isinstance(merged["config_version"], int) or isinstance(merged["config_version"], bool):
        bad("config_version", "must be an integer")
    if not isinstance(merged["first_run_done"], bool):
        bad("first_run_done", "must be true or false")
    for key in ("models_root", "outputs_root"):
        if not isinstance(merged[key], str) or not merged[key]:
            bad(key, "must be a non-empty path string")
    if not isinstance(gateway["enabled"], bool):
        bad("gateway.enabled", "must be true or false")
    if not isinstance(gateway["host"], str) or not gateway["host"].strip():
        bad("gateway.host", "must be a non-empty host string")
    port = gateway["port"]
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        bad("gateway.port", "must be an integer between 1 and 65535")


def _from_raw(raw: dict | None, data_root: Path, *, source: str = "file") -> DeskConfig:
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
    try:
        _validate(merged, gateway)
    except ConfigInvalidError as exc:
        if source == "file":
            raise ConfigCorruptError(
                f"config.json is corrupt: {exc.message}",
                path="config.json", parse_error=f"{exc.payload['field']}: {exc.payload['reason']}",
            ) from exc
        raise
    extra = {key: value for key, value in (raw or {}).items() if key not in _KNOWN_KEYS}
    return DeskConfig(
        config_version=merged["config_version"],
        first_run_done=merged["first_run_done"],
        models_root=Path(merged["models_root"]),
        outputs_root=Path(merged["outputs_root"]),
        gateway=GatewayConfig(enabled=gateway["enabled"], host=gateway["host"], port=gateway["port"]),
        needs_setup=(raw is None) or not merged["first_run_done"],
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


def reset_config(roots, *, force: bool = False) -> dict:
    """Move a broken config aside and start the first-run flow instead of dead-ending.

    A config that still parses is left alone unless ``force`` is set: a stray call must
    not rename a good file and fall back to default gateway settings (G2).
    """
    path = Path(roots.config_path)
    backup = None
    with _LOCK:
        if path.exists() and not force:
            try:
                _load_raw(path)
            except ConfigCorruptError:
                pass
            else:
                raise ConfigNotCorruptError("配置文件是好的，不需要重新设置")
        if path.exists():
            backup = path.with_name(f"config.broken-{time.strftime('%Y%m%d-%H%M%S')}.json")
            path.replace(backup)
    return {"backup": str(backup) if backup else None, "needs_setup": True}


def update_config(roots, **fields) -> DeskConfig:
    """Locked read-validate-write: nothing reaches disk unless it parses back."""
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
        validated = _from_raw(merged, roots.data_root, source="update")
        _atomic_write(roots.config_path, merged)
        return validated
