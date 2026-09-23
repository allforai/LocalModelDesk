"""Output delivery helpers."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
import os
from pathlib import Path
import re
import subprocess
from urllib.parse import unquote

from .errors import NotFoundError
from .history import HistoryStore
from .http import FileSlice, OutputsRootMissingError, RevealFailedError, Response


@dataclass(frozen=True)
class RangePlan:
    """The selected byte range, independent of any HTTP framework."""

    status: int
    start: int | None
    length: int


_RANGE = re.compile(r"bytes=(?:(\d+)-(\d*)|-(\d+))")
_TS_FMT = "%Y-%m-%dT%H:%M:%S"
_CONTENT_TYPES = {
    ".mp4": "video/mp4",
    ".wav": "audio/wav",
    ".m4a": "audio/mp4",
    ".webm": "video/webm",
    ".png": "image/png",
}
_MEDIA_SUFFIXES = frozenset(_CONTENT_TYPES)


def _infer_kind(name: str) -> str:
    if name.lower().endswith(".png"):
        return "image"
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

    def set_opener(self, opener) -> None:
        """Override the subprocess launcher used by :meth:`reveal` (tests).
        Test seam: production code never calls this (census 2026-09-08, F13)."""
        self._opener = opener

    def reveal(self, name: str | None = None) -> Path:
        """Reveal a single output in Finder, or open the outputs folder.

        Never a false success (issue #12): the root must exist before Finder is even asked to open
        it — mirroring the existence check `resolve()` already does for a named file — and the
        opener's exit code is checked, not discarded, in both the folder and the named-file case.
        """
        opener = getattr(self, "_opener", None) or (
            lambda argv, **kw: subprocess.run(argv, check=False, timeout=10)
        )
        if name is None:
            if not self._root.is_dir():
                raise OutputsRootMissingError("成品目录还不存在，生成第一个作品后会自动创建")
            self._run_opener(opener, ["open", str(self._root)])
            return self._root
        path = self.resolve(name)
        if path is None:
            raise NotFoundError("output not found")
        self._run_opener(opener, ["open", "-R", str(path)])
        return path

    @staticmethod
    def _run_opener(opener, argv: list[str]) -> None:
        """Run the opener and check its exit code. A test double that returns nothing (no
        `.returncode`) is treated as success, so existing call-site fakes keep working."""
        result = opener(argv)
        returncode = getattr(result, "returncode", None)
        if returncode not in (None, 0):
            raise RevealFailedError(f"打开访达失败（{argv[0]} 退出码 {returncode}）")

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

    def serve(self, name: str, range_header: str | None = None) -> Response:
        """Describe a safe complete or ranged output-file response."""
        path = self.resolve(name)
        if path is None or path.suffix.lower() not in _CONTENT_TYPES:
            return Response(
                404,
                {"Content-Type": "application/json"},
                json.dumps({"error": "output not found"}).encode("utf-8"),
            )

        size = path.stat().st_size
        plan = parse_range(size, range_header)
        headers = {
            "Accept-Ranges": "bytes",
            "Content-Type": _CONTENT_TYPES[path.suffix.lower()],
        }
        if plan.status == 416:
            headers["Content-Range"] = f"bytes */{size}"
            return Response(416, headers, b"")

        headers["Content-Length"] = str(plan.length)
        if plan.status == 206:
            end = plan.start + plan.length - 1
            headers["Content-Range"] = f"bytes {plan.start}-{end}/{size}"
        return Response(plan.status, headers, FileSlice(path, plan.start, plan.length))


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
