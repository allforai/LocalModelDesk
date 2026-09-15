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


def test_default_fetcher_follows_pagination_and_uses_lfs_size():
    from desk.resources.manifest import HF_TREE_URL, default_fetcher

    base = HF_TREE_URL.format(repo="org/repo")
    page2 = base + "&cursor=abc"
    pages = {
        base: (json.dumps([
            {"type": "file", "path": "config.json", "size": 123},
            {"type": "file", "path": "model.safetensors", "size": 134,
             "lfs": {"size": 5000000, "oid": "x"}},
            {"type": "directory", "path": "sub"},
        ]).encode(), page2),
        page2: (json.dumps([{"type": "file", "path": "sub/x.bin", "size": 7}]).encode(), None),
    }

    files = default_fetcher("org/repo", http_get=lambda url: pages[url])

    assert files == [ManifestFile("config.json", 123),
                     ManifestFile("model.safetensors", 5000000),
                     ManifestFile("sub/x.bin", 7)]


def test_default_fetcher_is_manifest_store_default():
    import inspect

    from desk.resources.manifest import ManifestStore, default_fetcher

    sig = inspect.signature(ManifestStore.__init__)
    assert sig.parameters["fetcher"].default is default_fetcher


def test_cache_for_a_different_repo_is_ignored_and_refetched(tmp_path):
    """The glm catalog key moved from the 4-bit to the 8-bit repo (2026-09-16); the cached
    4-bit file list made the downloaded 8-bit model show as partial."""
    import dataclasses

    calls = []

    def fetcher(repo):
        calls.append(repo)
        return [ManifestFile("model-new.safetensors", 7)]

    old_entry = dataclasses.replace(GLM, hf_repo="someone/old-4bit-repo")
    make_store(tmp_path, lambda repo: [ManifestFile("model-old.safetensors", 3)]).get(old_entry)

    manifest = make_store(tmp_path, fetcher).get(GLM)

    assert calls == [GLM.hf_repo]
    assert manifest.repo == GLM.hf_repo
    assert [f.path for f in manifest.files] == ["model-new.safetensors"]


def test_fetch_failure_does_not_fall_back_to_another_repos_cache(tmp_path):
    import dataclasses

    old_entry = dataclasses.replace(GLM, hf_repo="someone/old-4bit-repo")
    make_store(tmp_path, lambda repo: [ManifestFile("model-old.safetensors", 3)]).get(old_entry)

    def offline(repo):
        raise OSError("offline")

    with pytest.raises(ManifestUnavailableError):
        make_store(tmp_path, offline).get(GLM)
