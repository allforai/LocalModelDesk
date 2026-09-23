"""HTTP adapter from SkillsService to the skills route table."""
from __future__ import annotations

from typing import Callable

from .install import InstallError

Handler = Callable[[dict | None, dict], tuple[int, dict]]


def _run(fn: Callable[[], dict]) -> tuple[int, dict]:
    try:
        return 200, fn()
    except InstallError as exc:
        return 409, {"error": {"code": "install_failed", "message": str(exc)}}


def build_routes(service) -> list[tuple[str, str, object]]:
    return [
        ("GET", "/api/skills", lambda _body, _query: (200, service.list_skills())),
        ("POST", "/api/skills/rescan", lambda _body, _query: (200, service.rescan())),
        ("POST", "/api/skills/preview", lambda body, _q: _run(lambda: service.preview_install((body or {}).get("url")))),
        ("POST", "/api/skills/install", lambda body, _q: _run(lambda: service.confirm_install((body or {}).get("staging_id")))),
        ("POST", "/api/skills/discard", lambda body, _q: _run(lambda: service.discard_install((body or {}).get("staging_id")))),
    ]
