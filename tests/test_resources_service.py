from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.budget.budget import Budget
from desk.budget.device import GpuCapacity
from desk.budget.store import Measurements
from desk.media.memory_estimate import estimate_bytes
from desk.resources.catalog import CATALOG, entry
from desk.resources.manifest import ManifestFile
from desk.resources.service import ResourcesService


GLM = entry("glm")
GIB = 1024 ** 3


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def spawn(self, cmd, cwd=None, extra_env=None):
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


def make_budget(working_set_gib):
    m = Measurements()
    m.record_gpu_capacity(GpuCapacity("测试设备", 128 * GIB, working_set_gib * GIB, 80 * GIB), 0.0)
    return Budget(measurements=m, memory_reader=None, media_estimate=estimate_bytes, now=lambda: 0.0)


def test_list_catalog_with_fit_extends_every_entry_with_its_verdict(tmp_path):
    """接线点：目录端点自己就该带上适配判定，不必另起一个问同一件事的接口。"""
    service, holder = make_service(tmp_path)
    service._budget = make_budget(200)

    entries = service.list_catalog_with_fit()

    assert len(entries) == len(CATALOG)
    by_key = {e["key"]: e for e in entries}
    assert by_key["glm"]["fit"]["level"] == "fits"
    assert by_key["glm"]["fit"]["needed_bytes"] == int(GLM.gb * GIB)
    # 媒体模型问的是作业峰值，不是下载体积——两条目录端点不能给出同一个数字。
    assert by_key["h3"]["fit"]["needed_bytes"] == estimate_bytes("video", {})
    assert by_key["h3"]["fit"]["needed_bytes"] != int(entry("h3").gb * GIB)


def test_list_catalog_with_fit_is_unknown_without_a_budget(tmp_path):
    """没接预算就老实说不知道，不拿别的数顶替（构造函数默认 budget=None）。"""
    service, _ = make_service(tmp_path)
    entries = service.list_catalog_with_fit()
    assert all(e["fit"]["level"] == "unknown" for e in entries)


def test_list_catalog_with_fit_survives_a_corrupt_config(tmp_path):
    """config.json 读不出来不该把目录端点也拖下水——降级，不是 500。"""
    from desk.foundation.errors import ConfigCorruptError

    def broken_resolve_paths():
        raise ConfigCorruptError("坏了", path="x", parse_error="boom", recoverable=True)

    service = ResourcesService(
        resolve_paths=broken_resolve_paths, can_start_heavy=lambda: {"ok": True},
        fetcher=lambda _repo: [ManifestFile("a", 1)], executor=FakeExecutor(),
        budget=make_budget(200),
    )

    entries = service.list_catalog_with_fit()

    assert len(entries) == len(CATALOG)
    glm_fit = next(e for e in entries if e["key"] == "glm")["fit"]
    assert glm_fit["level"] == "fits"
    # "不知道下没下载"必须和"知道目录、看了一眼、确实没下载"长得不一样——否则一个
    # 真的躺在磁盘上的模型会被当成没下载（R-config-corrupt-01，报告 2026-09-24 的根因）。
    assert glm_fit["context"] is not None
    assert glm_fit["context"]["unknown"] is True
    assert glm_fit["context"]["reason"]


def test_verify_model_reports_config_corrupt_not_a_raw_crash(tmp_path):
    """config.json 读不出来时 verify_model 得回一个能认出来的 code，不能让异常裸奔。"""
    from desk.foundation.errors import ConfigCorruptError
    from desk.resources.errors import ConfigUnavailableError

    def broken_resolve_paths():
        raise ConfigCorruptError("坏了", path="x", parse_error="boom", recoverable=True)

    service = ResourcesService(
        resolve_paths=broken_resolve_paths, can_start_heavy=lambda: {"ok": True},
        fetcher=lambda _repo: [ManifestFile("a", 1)], executor=FakeExecutor(),
    )

    with pytest.raises(ConfigUnavailableError) as excinfo:
        service.verify_model("glm")
    assert excinfo.value.code == "config_corrupt"


def test_disk_usage_reports_config_corrupt_not_a_raw_crash(tmp_path):
    from desk.foundation.errors import ConfigCorruptError
    from desk.resources.errors import ConfigUnavailableError

    def broken_resolve_paths():
        raise ConfigCorruptError("坏了", path="x", parse_error="boom", recoverable=True)

    service = ResourcesService(
        resolve_paths=broken_resolve_paths, can_start_heavy=lambda: {"ok": True},
        fetcher=lambda _repo: [ManifestFile("a", 1)], executor=FakeExecutor(),
    )

    with pytest.raises(ConfigUnavailableError) as excinfo:
        service.disk_usage()
    assert excinfo.value.code == "config_corrupt"


def test_start_download_reports_config_corrupt_not_a_raw_crash(tmp_path):
    from desk.foundation.errors import ConfigCorruptError
    from desk.resources.errors import ConfigUnavailableError

    def broken_resolve_paths():
        raise ConfigCorruptError("坏了", path="x", parse_error="boom", recoverable=True)

    service = ResourcesService(
        resolve_paths=broken_resolve_paths, can_start_heavy=lambda: {"ok": True},
        fetcher=lambda _repo: [ManifestFile("a", 1)], executor=FakeExecutor(),
    )

    with pytest.raises(ConfigUnavailableError) as excinfo:
        service.start_download("glm")
    assert excinfo.value.code == "config_corrupt"
