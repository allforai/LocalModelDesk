"""Assembly contract for the deterministic end-to-end harness."""

import json
from urllib.request import Request, urlopen

from desk.testing import TestHarness, launch_test_harness


def _get(url: str):
    with urlopen(url, timeout=5) as response:
        return response.status, json.loads(response.read())


def _post(url: str, body: dict):
    request = Request(
        url, data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urlopen(request, timeout=5) as response:
        return response.status, json.loads(response.read())


def test_launch_test_harness_serves_real_routes_on_ephemeral_ports(tmp_path):
    with launch_test_harness(tmp_path) as harness:
        assert isinstance(harness, TestHarness)
        assert harness.base_url.startswith("http://127.0.0.1:")
        assert not harness.base_url.endswith(":8766")

        status, config = _get(harness.base_url + "/api/config")
        assert status == 200
        assert config["needs_setup"] is False
        assert config["models_root"] == str(harness.models_root)

        status, catalog = _get(harness.base_url + "/api/resources/catalog")
        assert status == 200
        assert len(catalog) == 9
        image = next(entry for entry in catalog if entry["key"] == "qwen-image")
        assert image["group"] == "image"
        assert len(image["sources"]) == 2

        status, state = _get(harness.base_url + "/api/state")
        assert status == 200
        assert state["holder"] is None

        status, memory = _get(harness.base_url + "/api/memory")
        assert status == 200
        assert memory["total_bytes"] == 200_000_000_000

        status, gateway = _get(harness.base_url + "/api/gateway/config")
        assert status == 200
        assert gateway["status"]["port"] == harness.gateway_port

        status, disk = _get(harness.base_url + "/api/resources/disk")
        assert status == 200
        assert disk["free_bytes"] > 0

        legacy = tmp_path / "legacy"
        (legacy / "llms").mkdir(parents=True)
        status, adopted = _post(harness.base_url + "/api/adopt", {
            "legacy_root": str(legacy), "mode": "point",
        })
        assert status == 200
        assert adopted["models_root"] == str(legacy)

        prefixes = [path for _method, path in harness.routes]
        for required in ("/api/config", "/api/llm/", "/api/media/", "/api/resources/",
                         "/api/state", "/api/memory", "/api/outputs", "/api/history",
                         "/api/sessions", "/api/gateway/config", "/api/adopt",
                         "/api/resources/disk"):
            assert any(path.startswith(required) or required.startswith(path) for path in prefixes)


def production_route_table():
    """Collect (method, pattern) from every production route module.

    None of these ``build_routes``/``routes`` calls invoke the service they
    are given -- they only build closures over it -- so a bare ``object()``
    stand-in is safe here and never touches real paths or state.
    """
    from desk.foundation import routes as foundation_routes
    from desk.library import http as library_http
    from desk.llm import routes as llm_routes
    from desk.media import routes as media_routes
    from desk.resources import http as resources_http

    fake_service = object()
    table = set()
    table.update((method, path) for method, path, _handler in foundation_routes.build_routes())
    table.update((method, path) for method, path, _handler in resources_http.build_routes(fake_service))
    table.update((route.method, route.path) for route in llm_routes.build_routes(fake_service))
    table.update((method, path) for method, path, _handler in media_routes.build_routes(fake_service))
    table.update((method, path) for method, path, _handler in library_http.routes(fake_service))
    table.update({
        ("GET", "/api/state"),
        ("GET", "/api/memory"),
        ("GET", "/api/gateway/config"),
        ("POST", "/api/gateway/config"),
    })
    return table


def test_harness_mirrors_every_production_route(tmp_path):
    """harness 少一条路由，e2e 就有一整块测不到（R-e2e-01）."""
    from desk.testing.harness import launch_test_harness

    with launch_test_harness(tmp_path) as harness:
        harness_routes = {(m, p) for m, p, _handler in harness.app._routes}
    production_routes = production_route_table()

    missing = production_routes - harness_routes
    assert missing == set(), f"harness 缺少生产路由：{sorted(missing)}"


def test_launch_test_harness_can_start_unconfigured(tmp_path):
    with launch_test_harness(tmp_path, configured=False) as harness:
        status, config = _get(harness.base_url + "/api/config")
        assert status == 200
        assert config["needs_setup"] is True
        assert not (harness.data_root / "config.json").exists()
