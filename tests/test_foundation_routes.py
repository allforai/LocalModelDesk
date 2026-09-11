import json
import os

import pytest

from desk.app import DeskApp
from desk.foundation import routes as routes_mod
from http_helpers import http_call


@pytest.fixture()
def server(tmp_path, monkeypatch):
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(tmp_path / "data"))
    app = DeskApp("127.0.0.1", 0)
    app.add_routes(routes_mod.build_routes())
    app.start_background()
    yield app
    app.shutdown()


def test_get_config_reports_needs_setup(server):
    status, payload = http_call(server, "GET", "/api/config")
    assert status == 200
    assert payload["needs_setup"] is True
    assert payload["gateway"]["port"] == 8770


def test_put_config_merges_subset(server):
    status, payload = http_call(server, "PUT", "/api/config", {"gateway": {"port": 9100}})
    assert status == 200
    assert payload["gateway"]["port"] == 9100
    assert payload["gateway"]["host"] == "0.0.0.0"


def test_config_reset_endpoint_backs_up_broken_file(server, tmp_path):
    config_path = tmp_path / "data" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{not json", encoding="utf-8")

    status, payload = http_call(server, "POST", "/api/config/reset", {})
    assert status == 200
    assert payload["needs_setup"] is True
    assert payload["backup"]


def test_get_paths_includes_capabilities(server):
    status, payload = http_call(server, "GET", "/api/paths")
    assert status == 200
    assert payload["mode"] == "dev"
    assert set(payload["capabilities"]) == {"mlx_h3", "venv", "models_root", "music_runtime", "config"}
    assert payload["models_root"]


def test_first_run_endpoint_happy_and_unwritable(server, tmp_path):
    status, payload = http_call(server, "POST", "/api/first-run", {})
    assert status == 200
    assert payload["first_run_done"] is True
    fenced = tmp_path / "fenced"
    fenced.mkdir()
    os.chmod(fenced, 0o500)
    try:
        status, payload = http_call(server, "POST", "/api/first-run", {"models_root": str(fenced / "m")})
        assert status == 400
        assert payload["error"]["code"] == "not_writable"
    finally:
        os.chmod(fenced, 0o700)


def test_adopt_endpoint_point_and_bad_body(server, tmp_path):
    legacy = tmp_path / "legacy"
    (legacy / "llms" / "o" / "r").mkdir(parents=True)
    (legacy / "llms" / "o" / "r" / "w.safetensors").write_bytes(b"x" * 8)
    status, payload = http_call(server, "POST", "/api/adopt", {"legacy_root": str(legacy), "mode": "point"})
    assert status == 200
    assert payload["adopted"] == ["llms"]
    assert payload["moved_bytes"] == 0
    status, payload = http_call(server, "POST", "/api/adopt", {"mode": "sideways"})
    assert status == 400
    assert payload["error"]["code"] == "legacy_root_invalid"


def test_discover_endpoint_selects_best_local_tree(server, tmp_path, monkeypatch):
    local = tmp_path / "existing"
    model = local / "minimax-music3"
    model.mkdir(parents=True)
    (model / "weight.safetensors").write_bytes(b"x")
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", str(local))
    status, payload = http_call(server, "POST", "/api/models/discover", {})
    assert status == 200
    assert payload["found"] is True
    assert payload["models_root"] == str(local)
    assert payload["candidates"][0]["model_keys"] == ["music3"]


def test_get_config_lists_discovered_roots_only_while_setup_is_needed(server, tmp_path, monkeypatch):
    tree = tmp_path / "legacy"
    (tree / "minimax-h3").mkdir(parents=True)
    (tree / "minimax-h3" / "w.bin").write_bytes(b"x")
    monkeypatch.setenv("LOCALMODELDESK_MODEL_SCAN_ROOTS", str(tree))
    status, payload = http_call(server, "GET", "/api/config")
    assert status == 200
    assert payload["needs_setup"] is True
    # Membership rather than equality: this test's own execution environment
    # (a worktree nested under a real checkout that itself contains model
    # directories) can add unrelated candidates to the scan roots — see
    # test_discover_endpoint_selects_best_local_tree for the same pre-existing
    # environmental hazard, unrelated to this task's discovered/apply split.
    assert str(tree) in payload["discovered"]
    status, _ = http_call(server, "POST", "/api/first-run", {"models_root": str(tmp_path / "chosen")})
    assert status == 200
    status, payload = http_call(server, "GET", "/api/config")
    assert status == 200
    assert payload["needs_setup"] is False
    assert "discovered" not in payload


def test_unknown_route_404_and_invalid_json_400(server):
    status, payload = http_call(server, "GET", "/api/nope")
    assert status == 404
    assert payload["error"]["code"] == "not_found"
    import urllib.request
    req = urllib.request.Request(f"http://127.0.0.1:{server.port}/api/adopt", data=b"not-json", method="POST")
    try:
        urllib.request.urlopen(req, timeout=5)
        raised = None
    except urllib.error.HTTPError as exc:
        raised = exc.code, json.loads(exc.read())
    assert raised[0] == 400
    assert raised[1]["error"]["code"] == "bad_request"
