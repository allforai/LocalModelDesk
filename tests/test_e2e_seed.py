"""Unit tests for E2E bundle resources and three-state model seeding."""
import json
import os
import sys

from desk.foundation import resolve_paths
from desk.resources.catalog import list_catalog
from desk.testing.seed import (
    MANIFEST_FILES, PARTIAL_PERCENT, TINY_MP4, TINY_WAV,
    build_bundle_resources, default_states, seed_models,
)


def test_tiny_bytes_have_real_headers():
    assert TINY_MP4[4:8] == b"ftyp"
    assert TINY_WAV[:4] == b"RIFF" and TINY_WAV[8:12] == b"WAVE"
    assert len(TINY_MP4) < 4096 and len(TINY_WAV) < 4096


def test_manifest_pattern_is_600_plus_400():
    assert MANIFEST_FILES == (("weights/a.safetensors", 600), ("weights/b.safetensors", 400))
    assert PARTIAL_PERCENT == 60.0


def test_bundle_tree_probes_as_bundle_with_all_capabilities(tmp_path):
    res = build_bundle_resources(tmp_path)
    assert json.loads((res / "bundle.json").read_text())["app"] == "LocalModelDesk"
    assert (res / "desk" / "static" / "index.html").is_file()
    py = res / "python" / "bin" / "python3.13"
    assert py.is_symlink() and os.access(py, os.X_OK)
    assert os.path.realpath(py) == os.path.realpath(sys.executable)
    for pkg in ("pylibs/desk", "pylibs/h3/mlx_h3", "pylibs/music/mlx_minimax_music3"):
        assert (res / pkg).is_dir()
    roots = resolve_paths(data_root=tmp_path / "data", resources_root=res)
    assert roots.mode == "bundle"
    assert roots.static_dir == res / "desk" / "static"


def test_default_states_cover_three_chat_states_and_media_present():
    entries = list_catalog()
    states = default_states(entries)
    chat_states = [states[e.key] for e in entries if e.group == "chat" and e.key in states]
    assert chat_states[:3] == ["present", "partial", "missing"]
    for entry in entries:
        if entry.group in ("video", "music"):
            assert states[entry.key] == "present"


def test_seed_models_lays_exact_bytes(tmp_path):
    entries = list_catalog()
    chat = [entry for entry in entries if entry.group == "chat"]
    states = {chat[0].key: "present", chat[1].key: "partial", chat[2].key: "missing"}
    seeded = seed_models(tmp_path / "models", entries, states)
    assert seeded == states
    present = tmp_path / "models" / chat[0].relpath
    assert (present / "weights" / "a.safetensors").stat().st_size == 600
    assert (present / "weights" / "b.safetensors").stat().st_size == 400
    partial = tmp_path / "models" / chat[1].relpath
    assert (partial / "weights" / "a.safetensors").stat().st_size == 600
    assert not (partial / "weights" / "b.safetensors").exists()
    assert not (tmp_path / "models" / chat[2].relpath).exists()
