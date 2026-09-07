import logging
import sys
from pathlib import Path

import pytest

from desk.foundation import paths as paths_mod


@pytest.fixture()
def fake_repo(tmp_path):
    repo = tmp_path / "repo"
    (repo / "desk" / "static").mkdir(parents=True)
    (repo / "desk" / "media").mkdir(parents=True)
    return repo


@pytest.fixture()
def data_root(tmp_path, monkeypatch):
    root = tmp_path / "data"
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(root))
    return root


def test_dev_mode_without_bundle_marker(fake_repo, data_root):
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.mode == "dev"
    assert roots.resources_root == fake_repo
    assert roots.static_dir == fake_repo / "desk" / "static"
    assert roots.media_cli_dir == fake_repo / "desk" / "media"
    assert roots.venv_python == Path(sys.executable)
    assert roots.music_python == roots.venv_python
    assert roots.mlx_h3_env == {} and roots.music_env == {}


def test_bundle_mode_with_marker(fake_repo, data_root):
    (fake_repo / "bundle.json").write_text("{}", encoding="utf-8")
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    python = fake_repo / "python" / "bin" / "python3.13"
    assert roots.mode == "bundle"
    assert roots.venv_python == python
    assert roots.mlx_h3_cmd == (str(python), "-s", "-c", "from mlx_h3.cli import main; main()")
    assert roots.mlx_h3_env == {"PYTHONPATH": str(fake_repo / "pylibs" / "h3")}
    assert roots.music_env == {"PYTHONPATH": str(fake_repo / "pylibs" / "music")}
    assert roots.hf_cmd == (str(python), "-s", "-c", "from huggingface_hub.cli.hf import main; main()")
    assert roots.hf_env == {"PYTHONPATH": str(fake_repo / "pylibs" / "desk")}


def test_dev_mode_hf_env_is_empty(fake_repo, data_root):
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.hf_env == {}


def test_env_data_root_and_param_precedence(fake_repo, tmp_path, monkeypatch):
    env_root = tmp_path / "from-env"
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(env_root))
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.data_root == env_root.resolve()
    assert roots.config_path == roots.data_root / "config.json"
    explicit = tmp_path / "explicit"
    assert paths_mod.resolve_paths(resources_root=fake_repo, data_root=explicit).data_root == explicit.resolve()


def test_derived_paths_and_config_roots(fake_repo, data_root):
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.logs_dir == roots.data_root / "logs"
    assert roots.sessions_dir == roots.data_root / "sessions"
    assert roots.history_path == roots.data_root / "history.jsonl"
    assert roots.models_root == roots.data_root / "models"
    assert roots.outputs_root == roots.data_root / "outputs"


def test_resolve_creates_data_and_logs_but_not_models(fake_repo, data_root):
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    assert roots.data_root.is_dir()
    assert roots.logs_dir.is_dir()
    assert not roots.models_root.exists()


def test_resolve_sees_config_changes_immediately(fake_repo, data_root):
    from desk.foundation import config as config_mod

    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    config_mod.update_config(roots, models_root=data_root / "ext-disk")
    again = paths_mod.resolve_paths(resources_root=fake_repo)
    assert again.models_root == data_root.resolve() / "ext-disk"


def test_mlx_h3_dev_cmd_resolution_order(fake_repo, data_root, monkeypatch):
    fake_bin = fake_repo / "mlx-h3"
    monkeypatch.setenv("LOCALMODELDESK_MLX_H3", str(fake_bin))
    assert paths_mod.resolve_paths(resources_root=fake_repo).mlx_h3_cmd == (str(fake_bin),)


def test_hf_dev_cmd_empty_when_unresolvable(fake_repo, data_root, monkeypatch):
    monkeypatch.delenv("LOCALMODELDESK_HF", raising=False)
    monkeypatch.setattr(paths_mod.shutil, "which", lambda name: None)
    assert paths_mod.resolve_paths(resources_root=fake_repo).hf_cmd == ()


def test_corrupt_config_propagates_by_default(fake_repo, data_root):
    from desk.foundation.errors import ConfigCorruptError

    data_root.mkdir(parents=True, exist_ok=True)
    (data_root / "config.json").write_text("{broken", encoding="utf-8")
    with pytest.raises(ConfigCorruptError):
        paths_mod.resolve_paths(resources_root=fake_repo)
    roots = paths_mod.resolve_paths(resources_root=fake_repo, default_config_on_corrupt=True)
    assert roots.models_root == data_root.resolve() / "models"


def test_normalize_user_path_expands_tilde(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    assert paths_mod.normalize_user_path("~/x") == (tmp_path / "x").resolve()


def test_setup_logging_writes_under_data_root_only(fake_repo, data_root, monkeypatch):
    roots = paths_mod.resolve_paths(resources_root=fake_repo)
    monkeypatch.setattr(paths_mod, "_LOGGING_CONFIGURED", False)
    root_logger = logging.getLogger()
    saved = root_logger.handlers[:]
    for handler in saved:
        root_logger.removeHandler(handler)
    try:
        paths_mod.setup_logging(roots)
        logging.getLogger("desk.test").info("hello-a16")
        for handler in root_logger.handlers:
            handler.flush()
        log_file = roots.logs_dir / "desk.log"
        assert log_file.exists()
        assert "hello-a16" in log_file.read_text(encoding="utf-8")
        paths_mod.setup_logging(roots)
        file_handlers = [handler for handler in root_logger.handlers
                         if isinstance(handler, logging.FileHandler)]
        assert len(file_handlers) == 1
    finally:
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
            handler.close()
        for handler in saved:
            root_logger.addHandler(handler)
    repo_root = Path(__file__).resolve().parent.parent
    assert list(repo_root.glob("*.log")) == []
    assert list((repo_root / "desk").rglob("*.log")) == []
