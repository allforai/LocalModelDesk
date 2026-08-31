"""Static asset delivery for the desk UI."""
from __future__ import annotations

from pathlib import Path
from urllib.parse import unquote


CONTENT_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
}


class StaticAssets:
    """Resolve allowed UI paths beneath the configured static root."""

    def __init__(self, static_root: Path) -> None:
        self._root = Path(static_root).resolve()

    def resolve(self, url_path: str) -> tuple[Path, str] | None:
        path = unquote(url_path.split("?", 1)[0])
        if path in ("", "/", "/index.html"):
            rel = "index.html"
        elif path.startswith("/static/"):
            rel = path[len("/static/"):]
        else:
            return None

        if not rel or rel.endswith("/"):
            return None
        candidate = (self._root / rel).resolve()
        if not candidate.is_relative_to(self._root):
            return None
        content_type = CONTENT_TYPES.get(candidate.suffix)
        if content_type is None or not candidate.is_file():
            return None
        return candidate, content_type
