from types import SimpleNamespace
from pathlib import Path

import pytest

from desk.media.service import MediaError
from desk.media.routes import build_routes
from desk.resources.catalog import entry
from desk.resources.manifest import ManifestStore
from desk.resources.verify import verify_tree
from media_fakes import FakeExecutor, finished_snapshot, make_service
from test_media_image_cli import pipeline


def image_service(tmp_path, **kwargs):
    service, deps = make_service(tmp_path, **kwargs)
    model = entry("qwen-image")
    pipeline(tmp_path / "models" / model.relpath)
    roots = SimpleNamespace(models_root=tmp_path / "models", outputs_root=tmp_path / "outputs",
        image_python=Path("/fake/image-python"), image_env={"PYTHONPATH": "/fake/image"},
        media_cli_dir=Path("/fake/media"))
    service._resolve_paths = lambda: roots
    service._probe_capabilities = lambda: {"image_runtime": SimpleNamespace(present=True)}
    service._list_catalog = lambda: [model]
    return service, deps


@pytest.mark.parametrize("bad", [dict(width=True), dict(width=255), dict(height=257),
    dict(height=2064), dict(steps=0), dict(steps=True), dict(seed=-1), dict(seed=2**32),
    dict(seed=1.2), dict(force="false"), dict(prompt="")])
def test_invalid_image_params_do_not_spawn(tmp_path, bad):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError):
        service.start_image_job(**{**dict(prompt="cat"), **bad})
    assert deps.executor.spawned == []
    assert deps.arbiter.acquired == []


def test_image_success_records_params_and_unique_png_names(tmp_path):
    service, deps = image_service(tmp_path)
    first = dict(finished_snapshot(service, lambda: service.start_image_job(prompt="cat", seed=123)))
    second = finished_snapshot(service, lambda: service.start_image_job(prompt="cat", seed=123))
    assert first["status"] == second["status"] == "done"
    assert first["output"].endswith(".png") and first["output"] != second["output"]
    assert first["params"] == dict(prompt="cat", width=1024, height=1024, steps=40, seed=123)
    assert deps.executor.spawned[0]["cmd"][:3] == ["/fake/image-python", "-s", "/fake/media/image_cli.py"]
    assert deps.history.entries[0]["kind"] == "image"
    assert deps.arbiter.last_precheck["key"] == "qwen-image"
    assert len(deps.arbiter.released) == 2


def test_image_cancel_releases_and_can_retry(tmp_path):
    service, deps = image_service(tmp_path, executor=FakeExecutor("block"))
    snap = finished_snapshot(service, lambda: (service.start_image_job(prompt="cat"), service.cancel_job()))
    assert snap["status"] == "cancelled" and snap["output"] is None
    assert deps.arbiter.released == ["permit-1"]
    service._executor = FakeExecutor("success")
    assert finished_snapshot(service, lambda: service.start_image_job(prompt="retry"))["status"] == "done"


def test_image_worker_failure_releases(tmp_path):
    service, deps = image_service(tmp_path, executor=FakeExecutor("fail"))
    snap = finished_snapshot(service, lambda: service.start_image_job(prompt="cat"))
    assert snap["status"] == "error"
    assert deps.arbiter.released == ["permit-1"]


def test_missing_model_is_rejected_before_arbiter(tmp_path):
    service, deps = image_service(tmp_path)
    (tmp_path / "models" / entry("qwen-image").relpath / "processor/tokenizer.json").unlink()
    with pytest.raises(MediaError, match="缺失") as exc:
        service.start_image_job(prompt="cat")
    assert exc.value.code == "model_incomplete"
    assert not deps.arbiter.acquired


def test_image_memory_warning_requires_explicit_force(tmp_path):
    service, deps = image_service(tmp_path, memory_warning={"required_bytes": 52*1024**3, "available_bytes": 1})
    with pytest.raises(MediaError) as exc:
        service.start_image_job(prompt="cat")
    assert exc.value.code == "insufficient_memory"
    assert not deps.arbiter.acquired
    assert finished_snapshot(service, lambda: service.start_image_job(prompt="cat", force=True))["status"] == "done"


def test_image_route_defaults_and_rejects_truthy_string_force(tmp_path):
    service, _ = image_service(tmp_path)
    route = next(handler for method, path, handler in build_routes(service) if path == "/api/media/image")
    assert route({"prompt": "cat", "force": "false"}, {})[0] == 400
    assert route({"prompt": "cat"}, {})[0] == 200


def test_image_manifest_is_pinned_offline_and_describes_two_sources(tmp_path):
    model = entry("qwen-image")
    store = ManifestStore(lambda: tmp_path, fetcher=lambda _: pytest.fail("must not fetch main"))
    manifest = store.get(model, refresh=True)
    assert manifest.source == "pinned"
    assert len({f.repo for f in manifest.files}) == 2
    assert all(len(f.revision) == 40 for f in manifest.files)
    pipeline(tmp_path / model.relpath)
    assert verify_tree(model, manifest, tmp_path).state == "present"
    (tmp_path / model.relpath / "localmodeldesk-image.json").unlink()
    assert verify_tree(model, manifest, tmp_path).state == "partial"
