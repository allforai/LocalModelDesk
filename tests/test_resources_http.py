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


def test_get_catalog_carries_a_fit_verdict_per_model(tmp_path):
    """目录端点本身就带适配判定——不新开一个接口回答同一个问题。"""
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/catalog")
    assert status == 200
    for model in payload["models"]:
        assert model["fit"]["level"] in ("fits", "tight", "too_big", "unknown")
    json.dumps(payload)


def test_get_status_bundles_models_and_disk(tmp_path):
    routes, *_ = make_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/status")
    assert status == 200
    assert len(payload["models"]) == 9
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


def make_broken_config_routes(tmp_path):
    """跟 make_routes 一样，但 resolve_paths 老实报「配置读不出来」——三个受影响的
    端点（status/disk/download）都该经过 build_routes() 的 _guarded 统一变成
    config_corrupt，而不是让 ConfigCorruptError 原样穿到调用方（R-config-corrupt-01）。
    """
    from desk.foundation.errors import ConfigCorruptError

    def broken_resolve_paths():
        raise ConfigCorruptError("坏了", path="x", parse_error="boom", recoverable=True)

    svc = ResourcesService(resolve_paths=broken_resolve_paths,
                           can_start_heavy=lambda: {"ok": True},
                           fetcher=lambda repo: [ManifestFile("a.bin", 10)],
                           executor=FakeExecutor(), thread_factory=NoThread)
    return build_routes(svc), svc


def test_get_status_reports_config_corrupt_when_config_unreadable(tmp_path):
    routes, _ = make_broken_config_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/status")
    assert status == 500
    assert payload["error"]["code"] == "config_corrupt"


def test_get_disk_reports_config_corrupt_when_config_unreadable(tmp_path):
    routes, _ = make_broken_config_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/disk")
    assert status == 500
    assert payload["error"]["code"] == "config_corrupt"


def test_post_download_reports_config_corrupt_when_config_unreadable(tmp_path):
    routes, _ = make_broken_config_routes(tmp_path)
    status, payload = call(routes, "POST", "/api/resources/download", body={"key": "glm"})
    assert status == 500
    assert payload["error"]["code"] == "config_corrupt"


def test_get_catalog_survives_config_corrupt_with_distinguishable_unknown(tmp_path):
    """目录端点本来就该在配置坏时降级，不是这次改动的重点——但降级出来的
    context 不能和"没下载"撞形状（R-config-corrupt-01）。"""
    routes, _ = make_broken_config_routes(tmp_path)
    status, payload = call(routes, "GET", "/api/resources/catalog")
    assert status == 200
    glm = next(m for m in payload["models"] if m["key"] == "glm")
    assert glm["fit"]["context"] == {"unknown": True, "reason": glm["fit"]["context"]["reason"]}
    assert glm["fit"]["context"]["reason"]
