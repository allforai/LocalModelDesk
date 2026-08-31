"""Adoption tests using tiny fake model files."""
import os

import pytest

from desk.foundation import config as config_mod
from desk.foundation import firstrun
from desk.foundation import paths as paths_mod
from desk.foundation.errors import (
    AdoptConflictError,
    AdoptError,
    InsufficientSpaceError,
    LegacyRootError,
)


GIB = 1 << 30


@pytest.fixture()
def roots(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    repo = tmp_path / "repo"
    (repo / "desk").mkdir(parents=True)
    return paths_mod.resolve_paths(resources_root=repo)


def make_legacy(tmp_path, name="legacy"):
    legacy = tmp_path / name
    files = {
        "llms/org/repo-a/model-00001.safetensors": b"A" * 40,
        "llms/org/repo-a/config.json": b"{}",
        "minimax-h3/dit.safetensors": b"H" * 64,
        "minimax-music3/music.safetensors": b"M" * 32,
    }
    for rel, content in files.items():
        path = legacy / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return legacy, sum(len(content) for content in files.values())


def snapshot(root):
    return sorted(
        (str(path.relative_to(root)), path.read_bytes())
        for path in root.rglob("*")
        if path.is_file()
    )


def force_cross_volume(monkeypatch, free_bytes):
    monkeypatch.setattr(firstrun, "_same_volume", lambda _a, _b: False)

    class FakeUsage:
        def __init__(self, free):
            self.free = free

    monkeypatch.setattr(firstrun.shutil, "disk_usage", lambda _path: FakeUsage(free_bytes))


def test_point_mode_repoints_without_touching_source(roots, tmp_path):
    legacy, _ = make_legacy(tmp_path)
    before = snapshot(legacy)

    result = firstrun.adopt_legacy_models(roots, legacy, mode="point")

    assert result.mode == "point"
    assert result.models_root == legacy.resolve()
    assert sorted(result.adopted) == ["llms", "minimax-h3", "minimax-music3"]
    assert result.moved_bytes == 0
    assert result.source_retained is False
    assert snapshot(legacy) == before
    cfg = config_mod.read_config(roots)
    assert cfg.models_root == legacy.resolve()
    assert cfg.first_run_done is True


def test_partial_legacy_tree_is_accepted(roots, tmp_path):
    legacy = tmp_path / "only-llms"
    (legacy / "llms" / "o" / "r").mkdir(parents=True)
    (legacy / "llms" / "o" / "r" / "w.safetensors").write_bytes(b"x" * 10)

    result = firstrun.adopt_legacy_models(roots, legacy, mode="point")

    assert result.adopted == ["llms"]


def test_no_known_subtree_raises(roots, tmp_path):
    empty = tmp_path / "nothing"
    (empty / "unrelated").mkdir(parents=True)

    with pytest.raises(LegacyRootError) as exc:
        firstrun.adopt_legacy_models(roots, empty, mode="point")

    assert exc.value.code == "legacy_root_invalid"
    assert not roots.config_path.exists()


def test_unknown_mode_raises(roots, tmp_path):
    legacy, _ = make_legacy(tmp_path)

    with pytest.raises(LegacyRootError):
        firstrun.adopt_legacy_models(roots, legacy, mode="copy")


def test_move_same_volume_renames_everything(roots, tmp_path):
    legacy, total = make_legacy(tmp_path)
    target = tmp_path / "new-home"
    before = snapshot(legacy)

    result = firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)

    assert result.mode == "move"
    assert sorted(result.adopted) == ["llms", "minimax-h3", "minimax-music3"]
    assert result.moved_bytes == total
    assert result.source_retained is False
    for name in ("llms", "minimax-h3", "minimax-music3"):
        assert not (legacy / name).exists()
    assert snapshot(target) == before
    assert config_mod.read_config(roots).models_root == target.resolve()


def test_move_default_target_is_data_root_models(roots, tmp_path):
    legacy, _ = make_legacy(tmp_path)

    result = firstrun.adopt_legacy_models(roots, legacy, mode="move")

    assert result.models_root == roots.data_root / "models"
    assert (roots.data_root / "models" / "llms").is_dir()


def test_move_conflict_on_nonempty_target_subtree(roots, tmp_path):
    legacy, _ = make_legacy(tmp_path)
    target = tmp_path / "occupied"
    (target / "llms" / "already").mkdir(parents=True)
    (target / "llms" / "already" / "x.bin").write_bytes(b"1")

    with pytest.raises(AdoptConflictError) as exc:
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)

    assert exc.value.code == "adopt_conflict"
    assert exc.value.payload["subtree"] == "llms"
    assert (legacy / "llms").is_dir()
    assert not roots.config_path.exists()


def test_move_target_inside_legacy_rejected(roots, tmp_path):
    legacy, _ = make_legacy(tmp_path)

    with pytest.raises(LegacyRootError):
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=legacy / "sub")
    with pytest.raises(LegacyRootError):
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=legacy)


def test_move_midway_failure_reports_ledger_and_retry_completes(roots, tmp_path, monkeypatch):
    legacy, _ = make_legacy(tmp_path)
    target = tmp_path / "halfway"
    real_rename = os.rename
    calls = {"n": 0}

    def flaky_rename(src, dst):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("injected rename failure")
        return real_rename(src, dst)

    monkeypatch.setattr(firstrun.os, "rename", flaky_rename)
    with pytest.raises(AdoptError) as exc:
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)

    assert exc.value.code == "adopt_failed"
    assert len(exc.value.payload["adopted"]) == 1
    assert len(exc.value.payload["remaining"]) == 2
    assert not roots.config_path.exists()
    monkeypatch.setattr(firstrun.os, "rename", real_rename)
    result = firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)
    assert sorted(result.adopted) == ["llms", "minimax-h3", "minimax-music3"]
    assert config_mod.read_config(roots).first_run_done is True


def test_cross_volume_copy_retains_source(roots, tmp_path, monkeypatch):
    legacy, total = make_legacy(tmp_path)
    target = tmp_path / "other-volume"
    before = snapshot(legacy)
    force_cross_volume(monkeypatch, free_bytes=10 * GIB)

    result = firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)

    assert result.source_retained is True
    assert result.moved_bytes == total
    assert snapshot(legacy) == before
    assert snapshot(target) == before
    assert config_mod.read_config(roots).models_root == target.resolve()


def test_cross_volume_insufficient_space_exact_shortfall(roots, tmp_path, monkeypatch):
    legacy, total = make_legacy(tmp_path)
    target = tmp_path / "small-volume"
    force_cross_volume(monkeypatch, free_bytes=GIB)

    with pytest.raises(InsufficientSpaceError) as exc:
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)

    payload = exc.value.payload
    assert payload["needed_bytes"] == total + GIB
    assert payload["free_bytes"] == GIB
    assert payload["shortfall_bytes"] == total
    assert not roots.config_path.exists()


def test_cross_volume_failure_then_resumed_retry_skips_copied(roots, tmp_path, monkeypatch):
    legacy, _total = make_legacy(tmp_path)
    target = tmp_path / "flaky-volume"
    force_cross_volume(monkeypatch, free_bytes=10 * GIB)
    real_copy2 = firstrun._copy2
    state = {"copies": 0}

    def flaky_copy2(src, dst):
        state["copies"] += 1
        if state["copies"] == 3:
            raise OSError("injected copy failure")
        return real_copy2(src, dst)

    monkeypatch.setattr(firstrun, "_copy2", flaky_copy2)
    with pytest.raises(AdoptError) as exc:
        firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)

    assert exc.value.payload["remaining"]
    assert not roots.config_path.exists()

    counted = {"copies": 0}

    def counting_copy2(src, dst):
        counted["copies"] += 1
        return real_copy2(src, dst)

    monkeypatch.setattr(firstrun, "_copy2", counting_copy2)
    result = firstrun.adopt_legacy_models(roots, legacy, mode="move", target_root=target)

    assert sorted(result.adopted) == ["llms", "minimax-h3", "minimax-music3"]
    assert counted["copies"] == 2
    assert snapshot(legacy)
