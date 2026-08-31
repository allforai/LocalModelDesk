import errno

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
