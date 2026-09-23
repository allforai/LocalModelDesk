"""HTTP adapter from SkillsService to the skills route table."""
from __future__ import annotations


def build_routes(service) -> list[tuple[str, str, object]]:
    return [
        ("GET", "/api/skills", lambda _body, _query: (200, service.list_skills())),
        ("POST", "/api/skills/rescan", lambda _body, _query: (200, service.rescan())),
    ]
