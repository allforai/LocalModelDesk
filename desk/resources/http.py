"""/api/resources/* route table with JSON-ready service responses."""
from __future__ import annotations

from dataclasses import asdict
from functools import wraps
from typing import Callable

from .errors import ResourceError


Handler = Callable[..., tuple[int, dict]]
Route = tuple[str, str, Handler]


def _guarded(fn: Handler) -> Handler:
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except ResourceError as exc:
            return exc.http_status, exc.to_json()
    return wrapper


def match_route(routes: list[Route], method: str, path: str):
    """Return the first matching handler and its path parameters, if any."""
    parts = [part for part in path.split("?", 1)[0].split("/") if part]
    for route_method, pattern, handler in routes:
        if route_method != method:
            continue
        pattern_parts = [part for part in pattern.split("/") if part]
        if len(pattern_parts) != len(parts):
            continue
        params: dict[str, str] = {}
        for pattern_part, actual in zip(pattern_parts, parts):
            if pattern_part.startswith("{") and pattern_part.endswith("}"):
                params[pattern_part[1:-1]] = actual
            elif pattern_part != actual:
                break
        else:
            return handler, params
    return None


def _truthy(value) -> bool:
    return str(value).lower() in ("1", "true", "yes")


def build_routes(service) -> list[Route]:
    @_guarded
    def get_catalog(query, body):
        return 200, {"models": [entry.to_json() for entry in service.list_catalog()]}

    @_guarded
    def get_status(query, body):
        refresh = _truthy(query.get("refresh", "0"))
        return 200, {
            "models": [status.to_json() for status in service.verify_all_models(refresh=refresh)],
            "disk": service.disk_usage().to_json(),
        }

    @_guarded
    def get_status_one(query, body, key):
        refresh = _truthy(query.get("refresh", "0"))
        return 200, service.verify_model(key, refresh=refresh).to_json()

    @_guarded
    def get_download(query, body):
        return 200, asdict(service.download_progress())

    @_guarded
    def post_download(query, body):
        return 200, asdict(service.start_download(str((body or {}).get("key", ""))))

    @_guarded
    def post_cancel(query, body):
        return 200, asdict(service.cancel_download())

    @_guarded
    def post_delete(query, body):
        body = body or {}
        return 200, service.delete_model(str(body.get("key", "")), body.get("confirm"))

    @_guarded
    def get_disk(query, body):
        return 200, service.disk_usage().to_json()

    return [
        ("GET", "/api/resources/catalog", get_catalog),
        ("GET", "/api/resources/status", get_status),
        ("GET", "/api/resources/status/{key}", get_status_one),
        ("GET", "/api/resources/download", get_download),
        ("POST", "/api/resources/download", post_download),
        ("POST", "/api/resources/download/cancel", post_cancel),
        ("POST", "/api/resources/delete", post_delete),
        ("GET", "/api/resources/disk", get_disk),
    ]
