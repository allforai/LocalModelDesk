import errno
import os

import pytest

from desk.foundation import config as config_mod
from desk.foundation import firstrun
from desk.foundation import paths as paths_mod
from desk.foundation.errors import NotWritableError


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
    for relpath in ("minimax-h3", "minimax-music3",
                    "llms/huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit"):
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
