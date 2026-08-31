import pytest

from desk.resources import catalog
from desk.resources.catalog import ModelEntry
from desk.resources.errors import ConfirmRequiredError, DownloadBusyError, PathEscapeError
from tests.test_resources_service import GLM, fill_model, make_service


def test_delete_model_requires_confirmation_matching_the_model_key(tmp_path):
    service, holder = make_service(tmp_path)
    model_dir = holder["roots"].models_root / GLM.relpath
    fill_model(holder["roots"].models_root, GLM, {"model.safetensors": 1})

    with pytest.raises(ConfirmRequiredError):
        service.delete_model("glm", confirm="different")

    assert model_dir.is_dir()


def test_delete_model_removes_confirmed_model_directory(tmp_path):
    service, holder = make_service(tmp_path)
    model_dir = holder["roots"].models_root / GLM.relpath
    fill_model(holder["roots"].models_root, GLM, {"model.safetensors": 1})

    service.delete_model("glm", confirm="glm")

    assert not model_dir.exists()


def test_delete_model_rejects_a_resolved_path_outside_models_root(tmp_path, monkeypatch):
    service, holder = make_service(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel = outside / "keep"
    sentinel.write_text("do not delete")
    models_root = holder["roots"].models_root
    models_root.mkdir()
    (models_root / "escaped").symlink_to(outside, target_is_directory=True)
    escaped = ModelEntry("escaped", "Escaped", "chat", "repo/escaped", "escaped", 1)
    monkeypatch.setattr(catalog, "CATALOG", (escaped,))

    with pytest.raises(PathEscapeError):
        service.delete_model("escaped", confirm="escaped")

    assert sentinel.read_text() == "do not delete"


def test_delete_model_rejects_while_a_download_is_running(tmp_path):
    service, holder = make_service(tmp_path)
    model_dir = holder["roots"].models_root / GLM.relpath
    fill_model(holder["roots"].models_root, GLM, {"model.safetensors": 1})
    service.start_download("glm")

    with pytest.raises(DownloadBusyError):
        service.delete_model("glm", confirm="glm")

    assert model_dir.is_dir()


def test_delete_model_rejects_after_cancellation_until_download_exits(tmp_path):
    service, holder = make_service(tmp_path)
    model_dir = holder["roots"].models_root / GLM.relpath
    fill_model(holder["roots"].models_root, GLM, {"model.safetensors": 1})
    service.start_download("glm")
    service.cancel_download()

    with pytest.raises(DownloadBusyError):
        service.delete_model("glm", confirm="glm")

    assert model_dir.is_dir()
