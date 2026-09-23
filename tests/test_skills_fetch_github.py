"""`_fetch_github` 的成员过滤：tarball 成员剥掉 "<repo>-<branch>/" 前缀之后，
只认「没有路径分隔符、以 .md 结尾」的顶层文件；子目录、`../` 逃逸、大小写变体、
脚本一律跳过——绝不把成员名传进路径拼接（R-skill-01/11）。

不联网：直接 monkeypatch `urllib.request.urlopen`，喂一个内存里造的 tar.gz。
"""
from __future__ import annotations

import io
import tarfile

import pytest

from desk.skills import service as service_module


def _make_tarball(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name=name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, blob: bytes):
        self._blob = blob

    def read(self) -> bytes:
        return self._blob

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_only_top_level_md_members_survive_the_prefix_strip(monkeypatch):
    blob = _make_tarball({
        "repo-main/SKILL.md": b"top level md",
        "repo-main/A.md": b"top level attachment",
        "repo-main/notes/sub.md": b"subdirectory - must be skipped",
        "repo-main/../escape.md": b"path traversal attempt - must be skipped",
        "repo-main/run.sh": b"echo hi - script must be skipped",
        "repo-main/logo.png": b"\x00binary must be skipped",
    })

    def fake_urlopen(url, timeout=30):
        assert "owner/repo" in url
        return _FakeResponse(blob)

    monkeypatch.setattr(service_module.urllib.request, "urlopen", fake_urlopen)

    files = service_module._fetch_github("https://github.com/owner/repo")

    assert files == {"SKILL.md": "top level md", "A.md": "top level attachment"}


def test_a_url_without_owner_and_repo_is_rejected():
    with pytest.raises(ValueError):
        service_module._fetch_github("https://github.com/just-owner")


def test_both_branches_failing_raises(monkeypatch):
    def fake_urlopen(url, timeout=30):
        raise OSError("404")

    monkeypatch.setattr(service_module.urllib.request, "urlopen", fake_urlopen)

    with pytest.raises(ValueError):
        service_module._fetch_github("https://github.com/owner/repo")
