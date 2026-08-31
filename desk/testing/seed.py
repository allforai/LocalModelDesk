"""Bundle fake resources, three-state model trees, and tiny media bytes for E2E tests."""
from __future__ import annotations

import json
import shutil
import struct
import sys
from pathlib import Path


TINY_MP4 = (
    b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom"
    b"\x00\x00\x00\x08free"
)
_WAV_SAMPLES = b"\x00\x00" * 8
TINY_WAV = (
    b"RIFF" + struct.pack("<I", 36 + len(_WAV_SAMPLES)) + b"WAVE"
    + b"fmt " + struct.pack("<IHHIIHH", 16, 1, 1, 8000, 16000, 2, 16)
    + b"data" + struct.pack("<I", len(_WAV_SAMPLES)) + _WAV_SAMPLES
)

MANIFEST_FILES: tuple[tuple[str, int], ...] = (
    ("weights/a.safetensors", 600),
    ("weights/b.safetensors", 400),
)
PARTIAL_PERCENT = 60.0


def _repo_static_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "static"


def build_bundle_resources(tmp_path: Path) -> Path:
    """Build a bundle-mode resource tree with all capability directories present."""
    res = tmp_path / "res"
    (res / "desk").mkdir(parents=True)
    static_dir = _repo_static_dir()
    if static_dir.is_dir():
        shutil.copytree(static_dir, res / "desk" / "static")
    else:
        (res / "desk" / "static").mkdir()
        (res / "desk" / "static" / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (res / "python" / "bin").mkdir(parents=True)
    (res / "python" / "bin" / "python3.13").symlink_to(Path(sys.executable))
    for package in ("pylibs/desk", "pylibs/h3/mlx_h3", "pylibs/music/mlx_minimax_music3"):
        (res / package).mkdir(parents=True)
    (res / "bundle.json").write_text(json.dumps({
        "app": "LocalModelDesk", "bundle_version": "e2e",
        "python": "python/bin/python3.13",
    }), encoding="utf-8")
    return res


def default_states(entries) -> dict[str, str]:
    """Return present, partial, and missing chat states plus installed media."""
    states: dict[str, str] = {}
    chat = [entry for entry in entries if entry.group == "chat"]
    for entry, state in zip(chat[:3], ("present", "partial", "missing")):
        states[entry.key] = state
    for entry in entries:
        if entry.group in ("video", "music"):
            states[entry.key] = "present"
    return states


def seed_models(
    models_root: Path, entries, model_states: dict[str, str] | None = None,
) -> dict[str, str]:
    """Lay down the manifest pattern for present and partial model states."""
    by_key = {entry.key: entry for entry in entries}
    states = dict(model_states if model_states is not None else default_states(entries))
    for key, state in states.items():
        if state == "missing":
            continue
        root = models_root / by_key[key].relpath / "weights"
        root.mkdir(parents=True, exist_ok=True)
        (root / "a.safetensors").write_bytes(b"x" * 600)
        if state == "present":
            (root / "b.safetensors").write_bytes(b"x" * 400)
    return states
