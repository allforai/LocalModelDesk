import json

import pytest

from desk.resources.catalog import entry
from desk.resources.errors import ManifestUnavailableError
from desk.resources.manifest import ManifestFile, ManifestStore


GLM = entry("glm")


def make_store(tmp_path, fetcher):
    return ManifestStore(cache_dir_provider=lambda: tmp_path / "manifests", fetcher=fetcher)


def test_fresh_fetch_writes_cache_atomically(tmp_path):
    store = make_store(tmp_path, lambda repo: [ManifestFile("a.safetensors", 100),
                                               ManifestFile("sub/b.bin", 60)])
    manifest = store.get(GLM)
    assert manifest.source == "fresh"
    assert manifest.repo == GLM.hf_repo
    assert manifest.total_bytes == 160
    raw = json.loads((tmp_path / "manifests" / "glm.json").read_text())
    assert raw["files"] == [{"path": "a.safetensors", "size": 100},
                            {"path": "sub/b.bin", "size": 60}]
    assert not list((tmp_path / "manifests").glob("*.tmp"))


def test_cache_hit_skips_fetch_and_reports_cached(tmp_path):
    calls = []

    def fetcher(repo):
        calls.append(repo)
        return [ManifestFile("a", 1)]

    store = make_store(tmp_path, fetcher)
    first = store.get(GLM)
    second = store.get(GLM)
    assert calls == [GLM.hf_repo]
    assert second.source == "cached"
    assert second.fetched_at == first.fetched_at
    assert second.files == first.files


def test_fetch_failure_falls_back_to_cache(tmp_path):
    state = {"fail": False}

    def fetcher(repo):
        if state["fail"]:
            raise OSError("network down")
        return [ManifestFile("a", 1)]

    store = make_store(tmp_path, fetcher)
    first = store.get(GLM)
    state["fail"] = True
    fallback = store.get(GLM, refresh=True)
    assert fallback.source == "cached"
    assert fallback.fetched_at == first.fetched_at


def test_fetch_failure_without_cache_raises(tmp_path):
    def fetcher(repo):
        raise OSError("network down")

    with pytest.raises(ManifestUnavailableError) as exc:
        make_store(tmp_path, fetcher).get(GLM)
    assert exc.value.code == "manifest_unavailable"


def test_corrupt_cache_treated_as_missing(tmp_path):
    (tmp_path / "manifests").mkdir()
    (tmp_path / "manifests" / "glm.json").write_text("{ not json")

    def failing(repo):
        raise OSError("down")

    with pytest.raises(ManifestUnavailableError):
        make_store(tmp_path, failing).get(GLM)
    manifest = make_store(tmp_path, lambda repo: [ManifestFile("a", 2)]).get(GLM)
    assert manifest.source == "fresh"
    raw = json.loads((tmp_path / "manifests" / "glm.json").read_text())
    assert raw["files"] == [{"path": "a", "size": 2}]
