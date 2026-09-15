import json
from types import SimpleNamespace

from desk.resources.catalog import CATALOG
from desk.resources.http import build_routes
from desk.resources.manifest import ManifestFile
from desk.resources.service import ResourcesService


class NoThread:
    def __init__(self, *args, **kwargs):
        pass

    def start(self):
        pass


class FakeExecutor:
    def __init__(self):
        self.calls = []

    def spawn(self, cmd, cwd=None, extra_env=None):
        self.calls.append(list(cmd))
        return SimpleNamespace(poll=lambda: None, terminate=lambda: None,
                               kill=lambda: None, stderr_tail=lambda: "")


def make_routes(tmp_path):
    hf = tmp_path / "hf"
    hf.write_text("#!/bin/sh\n")
    hf.chmod(0o755)
    roots = SimpleNamespace(models_root=tmp_path / "models", data_root=tmp_path / "data",
                            hf_cmd=(str(hf),))
    svc = ResourcesService(resolve_paths=lambda: roots,
                           can_start_heavy=lambda: {"ok": True},
                           fetcher=lambda repo: [ManifestFile("a.bin", 10)],
                           executor=FakeExecutor(), thread_factory=NoThread)
    return build_routes(svc), svc, roots


def _match_route(routes, method: str, path: str):
    """Return the first matching handler and its path parameters, if any.

    Production route dispatch lives in DeskApp._find; this is a test-only
    helper reconstructing just enough matching to drive build_routes()
    handlers directly (G6, P1).
    """
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


def call(routes, method, path, query=None, body=None):
    matched = _match_route(routes, method, path)
    assert matched is not None, f"no route for {method} {path}"
    handler, params = matched
    return handler(query or {}, body or {}, **params)


def test_get_catalog_returns_all_eight(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/catalog")
    assert status == 200
    assert [m["key"] for m in payload["models"]] == [e.key for e in CATALOG]
    json.dumps(payload)


def test_get_status_bundles_models_and_disk(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/status")
    assert status == 200
    assert len(payload["models"]) == 8
    assert payload["disk"]["free_bytes"] > 0
    json.dumps(payload)


def test_get_status_single_key_and_unknown_key_404(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/status/glm")
    assert status == 200 and payload["key"] == "glm"
    status, payload = call(routes, "GET", "/api/resources/status/nope")
    assert status == 404
    assert payload["error"]["code"] == "unknown_model"


def test_download_roundtrip_and_conflict(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/download")
    assert status == 200 and payload["state"] == "idle"
    status, payload = call(routes, "POST", "/api/resources/download", body={"key": "glm"})
    assert status == 200 and payload["state"] == "running"
    status, payload = call(routes, "POST", "/api/resources/download", body={"key": "h3"})
    assert status == 409
    assert payload["error"]["code"] == "download_in_progress"
    status, payload = call(routes, "POST", "/api/resources/download/cancel")
    assert status == 200 and payload["state"] == "cancelled"


def test_cancel_without_download_is_409(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "POST", "/api/resources/download/cancel")
    assert status == 409
    assert payload["error"]["code"] == "not_downloading"


def test_delete_requires_confirm(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "POST", "/api/resources/delete", body={"key": "glm"})
    assert status == 400
    assert payload["error"]["code"] == "confirm_required"
    status, payload = call(routes, "POST", "/api/resources/delete",
                           body={"key": "glm", "confirm": "glm"})
    assert status == 200
    assert payload == {"key": "glm", "freed_bytes": 0}


def test_get_disk(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/disk")
    assert status == 200
    assert set(payload["per_model"]) == {e.key for e in CATALOG}


def test_match_route_none_for_unknown_path(tmp_path):
    routes, *_ = make_routes(tmp_path)
    assert _match_route(routes, "GET", "/api/resources/nope") is None
