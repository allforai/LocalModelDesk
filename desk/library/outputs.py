"""Output delivery helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import re
from urllib.parse import unquote

from .history import HistoryStore


@dataclass(frozen=True)
class RangePlan:
    """The selected byte range, independent of any HTTP framework."""

    status: int
    start: int | None
    length: int


_RANGE = re.compile(r"bytes=(?:(\d+)-(\d*)|-(\d+))")
_TS_FMT = "%Y-%m-%dT%H:%M:%S"
_MEDIA_SUFFIXES = frozenset({".mp4", ".wav", ".m4a", ".webm"})


def _infer_kind(name: str) -> str:
    if name.startswith("h3-"):
        return "video"
    if name.startswith("music3-"):
        return "music"
    return "file"


class OutputsStore:
    def __init__(self, outputs_root: Path, history: HistoryStore):
        self._root = outputs_root
        self._history = history

    def resolve(self, name: str) -> Path | None:
        """Return a real regular file within the outputs root, if safe."""
        name = unquote(name or "")
        if not name or "/" in name or "\\" in name or name.startswith("."):
            return None

        root = os.path.realpath(self._root)
        candidate = os.path.realpath(os.path.join(root, name))
        if not candidate.startswith(root + os.sep):
            return None

        path = Path(candidate)
        return path if path.is_file() else None

    def list(self) -> list[dict]:
        """List media files, enriched with their matching history entries."""
        if not self._root.is_dir():
            return []

        by_output = self._history.by_output()
        items = []
        for child in self._root.iterdir():
            if child.name.startswith(".") or child.suffix.lower() not in _MEDIA_SUFFIXES:
                continue
            if not child.is_file():
                continue

            stat = child.stat()
            mtime_ts = datetime.fromtimestamp(stat.st_mtime).strftime(_TS_FMT)
            entry = by_output.get(child.name)
            if entry is None:
                items.append({
                    "name": child.name,
                    "kind": _infer_kind(child.name),
                    "bytes": stat.st_size,
                    "ts": mtime_ts,
                    "orphan": True,
                    "history_id": None,
                })
            else:
                items.append({
                    "name": child.name,
                    "kind": entry.get("kind") or _infer_kind(child.name),
                    "bytes": stat.st_size,
                    "ts": entry.get("ts") or mtime_ts,
                    "orphan": False,
                    "history_id": entry.get("id"),
                })
        items.sort(key=lambda item: item["ts"], reverse=True)
        return items


def parse_range(size: int, header: str | None) -> RangePlan:
    """Plan a single RFC 7233 byte range, ignoring malformed ranges."""
    if size < 0:
        raise ValueError("size must not be negative")

    full = RangePlan(200, 0, size)
    if not isinstance(header, str):
        return full
    match = _RANGE.fullmatch(header)
    if match is None:
        return full

    start_text, end_text, suffix_text = match.groups()
    if suffix_text is not None:
        suffix_length = int(suffix_text)
        if suffix_length == 0 or size == 0:
            return RangePlan(416, None, 0)
        length = min(suffix_length, size)
        return RangePlan(206, size - length, length)

    start = int(start_text)
    if end_text and start > int(end_text):
        return full
    if start >= size:
        return RangePlan(416, None, 0)
    end = min(int(end_text), size - 1) if end_text else size - 1
    return RangePlan(206, start, end - start + 1)
