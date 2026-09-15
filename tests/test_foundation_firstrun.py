import errno
import os
from types import SimpleNamespace

import pytest

from desk.foundation import config as config_mod
from desk.foundation import firstrun
from desk.foundation import paths as paths_mod
from desk.foundation.errors import NotWritableError
from desk.resources.catalog import entry


@pytest.fixture()
def roots(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    repo = tmp_path / "repo"
    (repo / "desk").mkdir(parents=True)
    return paths_mod.resolve_paths(resources_root=repo)


def test_complete_first_run_default_models_root_created_and_persisted(roots):
    cfg = firstrun.complete_first_run(roots)
    assert cfg.models_root == roots.data_root / "models"
    assert cfg.models_root.is_dir()
    assert cfg.first_run_done is True
    assert cfg.needs_setup is False
    assert config_mod.read_config(roots).first_run_done is True


def test_complete_first_run_explicit_models_root_wins(roots, tmp_path):
    target = tmp_path / "external" / "models"
    cfg = firstrun.complete_first_run(roots, models_root=target)
    assert cfg.models_root == target.resolve()
    assert target.is_dir()


def test_complete_first_run_removes_writability_probe(roots):
    firstrun.complete_first_run(roots)
    assert list((roots.data_root / "models").iterdir()) == []


def test_complete_first_run_unwritable_target_does_not_persist(roots, tmp_path, monkeypatch):
    target = tmp_path / "fenced" / "models"

    def fail_probe(self, data):
        if self == target / ".lmd-write-probe":
            raise OSError(errno.EACCES, "Permission denied")
        return original_write_bytes(self, data)

    original_write_bytes = type(target).write_bytes
    monkeypatch.setattr(type(target), "write_bytes", fail_probe)

    with pytest.raises(NotWritableError) as exc:
        firstrun.complete_first_run(roots, models_root=target)

    assert exc.value.code == "not_writable"
    assert exc.value.payload == {
        "path": str(target.resolve()),
        "os_error": "[Errno 13] Permission denied",
    }
    assert not roots.config_path.exists()


def _seed_trees(tmp_path):
    partial = tmp_path / "partial"
    complete = tmp_path / "complete"
    (partial / "minimax-h3").mkdir(parents=True)
    (partial / "minimax-h3" / "weight.safetensors").write_bytes(b"x")
    for relpath in ("minimax-h3", "minimax-music3", entry("glm").relpath):
        directory = complete / relpath
        directory.mkdir(parents=True)
        (directory / "weight.safetensors").write_bytes(b"x")
    return partial, complete


def test_discovery_is_read_only_and_ranks_complete_tree_first(roots, tmp_path, monkeypatch):
    partial, complete = _seed_trees(tmp_path)
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", os.pathsep.join((str(partial), str(complete))))
    candidates = firstrun.discover_model_roots(roots)
    assert candidates[0]["path"] == str(complete)
    assert set(candidates[0]["model_keys"]) == {"h3", "music3", "glm"}
    assert not roots.config_path.exists()


def test_apply_discovered_writes_only_when_called_explicitly(roots, tmp_path, monkeypatch):
    partial, complete = _seed_trees(tmp_path)
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", os.pathsep.join((str(partial), str(complete))))
    config, candidates = firstrun.apply_discovered(roots)
    assert config.models_root == complete
    assert config.first_run_done is True
    assert candidates[0]["path"] == str(complete)


def test_explicit_empty_models_root_survives_discovery(roots, tmp_path, monkeypatch):
    _partial, complete = _seed_trees(tmp_path)
    chosen = tmp_path / "fresh-empty"
    chosen.mkdir()
    firstrun.complete_first_run(roots, chosen)
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", str(complete))
    assert firstrun.discover_model_roots(roots)[0]["path"] == str(complete)
    assert config_mod.read_config(roots).models_root == chosen.resolve()


def _tree(path, subtree="minimax-h3"):
    (path / subtree).mkdir(parents=True)
    (path / subtree / "w.bin").write_bytes(b"x")
    return path


def test_scan_roots_env_replaces_every_guess(tmp_path, monkeypatch):
    """显式扫描目录时不许再把检出目录的上级带进来（嵌套 worktree 里发现了真实检出）。"""
    outer = _tree(tmp_path / "outer")
    repo = outer / "repo"
    repo.mkdir()
    chosen = _tree(tmp_path / "chosen", "minimax-music3")
    home = tmp_path / "home"
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", str(chosen))
    data_root = home / "Library" / "Application Support" / "LocalModelDesk"
    roots = SimpleNamespace(data_root=data_root, models_root=data_root / "models", resources_root=repo)

    assert [item["path"] for item in firstrun.discover_model_roots(roots)] == [str(chosen)]


def test_isolated_data_root_never_offers_the_real_home_or_checkout_tree(tmp_path, monkeypatch):
    """测试副本与 harness 不许把用户真实的模型树列成候选（2026-09-13 未拉的线）。"""
    home = tmp_path / "home"
    real_tree = _tree(home / "LocalModelDesk")
    checkout = _tree(tmp_path / "checkout", "llms")
    bundle = checkout / "LocalModelDesk.app" / "Contents" / "Resources"
    bundle.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", raising=False)

    isolated_data = tmp_path / "isolated-data"
    isolated = SimpleNamespace(data_root=isolated_data, models_root=isolated_data / "models", resources_root=bundle)
    assert firstrun.discover_model_roots(isolated) == []

    default_data = home / "Library" / "Application Support" / "LocalModelDesk"
    real = SimpleNamespace(data_root=default_data, models_root=default_data / "models", resources_root=bundle)
    found = {item["path"] for item in firstrun.discover_model_roots(real)}
    assert str(real_tree) in found
    assert str(checkout) in found


def test_recognized_model_keys_lists_catalog_models_with_files(tmp_path):
    root = _tree(tmp_path / "models", "minimax-music3")
    (root / "minimax-h3").mkdir()  # empty directory does not count
    assert firstrun.recognized_model_keys(root) == ["music3"]
    assert firstrun.recognized_model_keys(tmp_path / "missing") == []
