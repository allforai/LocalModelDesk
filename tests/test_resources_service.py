from pathlib import Path
from types import SimpleNamespace

from desk.resources.catalog import CATALOG, entry
from desk.resources.manifest import ManifestFile
from desk.resources.service import ResourcesService


GLM = entry("glm")


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def spawn(self, cmd, cwd=None):
        self.calls.append(list(cmd))
        return SimpleNamespace(poll=lambda: None, terminate=lambda: None,
                               kill=lambda: None, stderr_tail=lambda: "")


def make_service(tmp_path, *, fetcher=None):
    hf = tmp_path / "hf"
    hf.write_text("#!/bin/sh\n")
    hf.chmod(0o755)
    holder = {"roots": SimpleNamespace(models_root=tmp_path / "models",
                                       data_root=tmp_path / "data",
                                       hf_cmd=(str(hf),))}
    service = ResourcesService(
        resolve_paths=lambda: holder["roots"],
        can_start_heavy=lambda: {"ok": True},
        fetcher=fetcher or (lambda _repo: [ManifestFile("model.safetensors", 100),
                                            ManifestFile("tokenizer.json", 60)]),
        executor=FakeExecutor(), sample_interval=.01)
    return service, holder


def fill_model(root, model, sizes):
    directory = Path(root) / model.relpath
    directory.mkdir(parents=True, exist_ok=True)
    for name, size in sizes.items():
        path = directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"x" * size)


def test_resources_service_facade_wires_catalog_verify_disk_and_paths(tmp_path):
    service, holder = make_service(tmp_path)
    fill_model(holder["roots"].models_root, GLM,
               {"model.safetensors": 100, "tokenizer.json": 60})

    assert [model.key for model in service.list_catalog()] == [model.key for model in CATALOG]
    assert service.verify_model("glm").state == "present"
    assert set(service.disk_usage().per_model) == {model.key for model in CATALOG}
    assert (tmp_path / "data" / "manifests" / "glm.json").is_file()

    holder["roots"] = SimpleNamespace(models_root=tmp_path / "elsewhere",
                                       data_root=holder["roots"].data_root,
                                       hf_cmd=holder["roots"].hf_cmd)
    assert service.verify_model("glm").state == "missing"


def test_verify_all_isolates_an_unavailable_manifest(tmp_path):
    def fetcher(repo):
        if repo == GLM.hf_repo:
            raise OSError("offline")
        return [ManifestFile("a", 10)]

    service, _ = make_service(tmp_path, fetcher=fetcher)
    statuses = service.verify_all_models()

    assert [status.key for status in statuses] == [model.key for model in CATALOG]
    assert next(status for status in statuses if status.key == "glm").state == "unknown"


def test_download_facade_exposes_events_and_progress(tmp_path):
    service, _ = make_service(tmp_path)
    received = []
    service.events.subscribe_progress(received.append)

    service.events.emit_progress("event")
    assert received == ["event"]
    assert service.download_progress().state == "idle"
    assert service.start_download("glm").state == "running"
    assert service.cancel_download().state == "cancelled"


def test_download_facade_injects_sampling_sleep_and_thread_factory(tmp_path):
    created = []
    sleeps = []

    class StopSampling(Exception):
        pass

    class FakeThread:
        def __init__(self, *, target, daemon):
            self.target = target
            self.daemon = daemon

        def start(self):
            created.append(self)
            try:
                self.target()
            except StopSampling:
                pass

    service, holder = make_service(tmp_path)
    service = ResourcesService(
        resolve_paths=lambda: holder["roots"],
        can_start_heavy=lambda: {"ok": True},
        fetcher=lambda _repo: [ManifestFile("a", 1)],
        executor=FakeExecutor(),
        sleep=lambda seconds: (sleeps.append(seconds), (_ for _ in ()).throw(StopSampling()))[1],
        thread_factory=FakeThread,
    )

    service.start_download("glm")

    assert len(created) == 1
    assert created[0].daemon is True
    assert sleeps == [1.0]
