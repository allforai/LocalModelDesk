"""HF file manifests: fetch, cache, and honestly degrade on failures."""
from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .catalog import ModelEntry
from .errors import ManifestUnavailableError


log = logging.getLogger(__name__)


HF_TREE_URL = "https://huggingface.co/api/models/{repo}/tree/main?recursive=true"
_NEXT_LINK = re.compile(r'<([^>]+)>\s*;\s*rel="next"')


def _urllib_get(url: str) -> tuple[bytes, str | None]:
    req = urllib.request.Request(url, headers={"User-Agent": "LocalModelDesk"})
    with urllib.request.urlopen(req, timeout=30) as response:
        match = _NEXT_LINK.search(response.headers.get("Link") or "")
        return response.read(), (match.group(1) if match else None)


@dataclass(frozen=True)
class ManifestFile:
    path: str
    size: int


@dataclass(frozen=True)
class Manifest:
    repo: str
    files: tuple[ManifestFile, ...]
    fetched_at: str
    source: str

    @property
    def total_bytes(self) -> int:
        return sum(file.size for file in self.files)


def default_fetcher(
    repo: str,
    http_get: Callable[[str], tuple[bytes, str | None]] = _urllib_get,
) -> list[ManifestFile]:
    """Fetch paths and byte sizes from every page of an HF repository tree."""
    url: str | None = HF_TREE_URL.format(repo=repo)
    files: list[ManifestFile] = []
    while url:
        body, url = http_get(url)
        for item in json.loads(body):
            if item.get("type") != "file":
                continue
            lfs = item.get("lfs") or {}
            files.append(ManifestFile(
                path=item["path"],
                size=int(lfs.get("size") or item.get("size") or 0),
            ))
    return files


class ManifestStore:
    """Cache manifests in ``<data root>/manifests/<key>.json`` atomically."""

    def __init__(self, cache_dir_provider: Callable[[], Path],
                 fetcher: Callable[[str], list[ManifestFile]] = default_fetcher):
        self._cache_dir_provider = cache_dir_provider
        self._fetcher = fetcher

    def get(self, entry: ModelEntry, refresh: bool = False) -> Manifest:
        cache_path = Path(self._cache_dir_provider()) / f"{entry.key}.json"
        cached = self._load_cache(cache_path)
        if cached is not None and not refresh:
            return cached
        try:
            files = tuple(self._fetcher(entry.hf_repo))
        except Exception as exc:
            if cached is not None:
                log.warning("manifest fetch failed for %s; serving cache: %s", entry.hf_repo, exc)
                return cached
            raise ManifestUnavailableError(
                f"no manifest for {entry.hf_repo}: fetch failed and no cache exists ({exc})"
            ) from exc
        manifest = Manifest(
            repo=entry.hf_repo,
            files=files,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            source="fresh",
        )
        self._write_cache(cache_path, manifest)
        return manifest

    def _load_cache(self, cache_path: Path) -> Manifest | None:
        try:
            raw = json.loads(cache_path.read_text(encoding="utf-8"))
            files = tuple(
                ManifestFile(path=file["path"], size=int(file["size"]))
                for file in raw["files"]
            )
            return Manifest(
                repo=raw["repo"], files=files,
                fetched_at=raw["fetched_at"], source="cached",
            )
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _write_cache(self, cache_path: Path, manifest: Manifest) -> None:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "repo": manifest.repo,
            "fetched_at": manifest.fetched_at,
            "files": [{"path": file.path, "size": file.size} for file in manifest.files],
        }
        fd, temp_path = tempfile.mkstemp(
            dir=str(cache_path.parent), prefix=cache_path.name, suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, ensure_ascii=False)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, cache_path)
        except BaseException:
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise
