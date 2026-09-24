"""Bundle fake resources, three-state model trees, and tiny media bytes for E2E tests."""
from __future__ import annotations

import functools
import json
import shutil
import struct
import sys
import zlib
from pathlib import Path

from desk.media import image_model


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



@functools.lru_cache(maxsize=16)
def gradient_png(width: int = 96, height: int = 64) -> bytes:
    """An RGB gradient PNG, so a finished fake image job renders as a real picture.

    The scripted image executor writes it at the size the job asked for, so the harness lays out
    a 1024×1024 result the way the real model's output is laid out, not as a 96×64 thumbnail."""
    row = bytearray(width * 3)
    row[0::3] = bytes(x * 255 // max(width - 1, 1) for x in range(width))
    row[2::3] = b"\xa0" * width
    rows = bytearray()
    for y in range(height):
        row[1::3] = bytes((y * 255 // max(height - 1, 1),)) * width
        rows += b"\x00" + row
    rows = bytes(rows)

    def chunk(kind: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + kind + data
                + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))

    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header)
            + chunk(b"IDAT", zlib.compress(rows)) + chunk(b"IEND", b""))


TINY_PNG = gradient_png()

MANIFEST_FILES: tuple[tuple[str, int], ...] = (
    ("weights/a.safetensors", 600),
    ("weights/b.safetensors", 400),
)
PARTIAL_PERCENT = 60.0


def _repo_static_dir() -> Path:
    return Path(__file__).resolve().parent.parent / "static"


def build_bundle_resources(tmp_path: Path, *, image_runtime: bool = False) -> Path:
    """Build a bundle-mode resource tree with all capability directories present.

    Rebuilt from scratch on every call, so a harness relaunched on the same
    ``tmp_path`` (a simulated app restart) keeps its data root but gets a fresh
    resource tree. ``image_runtime`` adds importable stand-ins for ``mflux`` and
    ``mlx`` under ``pylibs/image`` so the real capability probe reports the image
    runtime present; the fake media executor never runs them."""
    res = tmp_path / "res"
    if res.exists():
        shutil.rmtree(res)
    (res / "desk").mkdir(parents=True)
    static_dir = _repo_static_dir()
    if static_dir.is_dir():
        shutil.copytree(static_dir, res / "desk" / "static")
    else:
        (res / "desk" / "static").mkdir()
        (res / "desk" / "static" / "index.html").write_text("<!doctype html>", encoding="utf-8")
    (res / "python" / "bin").mkdir(parents=True)
    (res / "python" / "bin" / "python3.13").symlink_to(Path(sys.executable))
    for package in ("pylibs/desk", "pylibs/h3/mlx_h3", "pylibs/music/mlx_minimax_music3", "pylibs/image"):
        (res / package).mkdir(parents=True)
    if image_runtime:
        for package in ("mflux", "mlx"):
            (res / "pylibs" / "image" / package).mkdir()
            (res / "pylibs" / "image" / package / "__init__.py").write_text(
                '"""e2e stand-in: lets the image runtime probe succeed; never imported by a job."""\n',
                encoding="utf-8")
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
        model_dir = models_root / by_key[key].relpath
        if key == "qwen-image" and state == "present":
            _seed_image_pipeline(model_dir)
            continue
        root = model_dir / "weights"
        root.mkdir(parents=True, exist_ok=True)
        (root / "a.safetensors").write_bytes(b"x" * 600)
        if state == "present":
            (root / "b.safetensors").write_bytes(b"x" * 400)
            # 真实模型目录都有 config.json，预算靠它算每 token 的 KV 开销。
            # 台面不铺这个文件，budget 模式下 cost() 就只能产出 source=unavailable
            # 的空壳，于是「一组取最弱来源」会让任何共存判定恒为拒绝——
            # e2e 测的就不是生产语义了。
            model_dir.joinpath("config.json").write_text(json.dumps({
                "model_type": "llama",
                "max_position_embeddings": 8192,
                "num_hidden_layers": 32,
                "num_key_value_heads": 8,
                "head_dim": 128,
            }), encoding="utf-8")
    return states


def _seed_image_pipeline(model_dir: Path) -> None:
    """Lay the pinned image pipeline as sparse files of the exact sizes validate_model checks."""
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / image_model.MARKER).write_text(
        json.dumps({**image_model.PROVENANCE, "complete": True}), encoding="utf-8")
    for item in image_model.files():
        path = model_dir / item["path"]
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("wb") as handle:
            handle.truncate(item["size"])
