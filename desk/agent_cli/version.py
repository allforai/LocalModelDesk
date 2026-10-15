"""Resources root and version, shared by the CLI and the desk's /api/state (A-32)."""
from __future__ import annotations

import json
from pathlib import Path


def resources_root() -> Path:
    """Contents/Resources inside the app bundle, or the repo root in development."""
    return Path(__file__).resolve().parents[2]


def read_version(root: Path) -> str:
    try:
        data = json.loads((root / "bundle.json").read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("bundle_version"), str):
            return data["bundle_version"]
    except (OSError, ValueError):
        pass
    try:
        text = (root / "packaging" / "VERSION").read_text(encoding="utf-8").strip()
        if text:
            return text
    except OSError:
        pass
    return "unknown"
