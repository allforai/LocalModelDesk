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
    assert payload["discovered"] == [str(tree)]
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


def test_sse_client_disconnect_closes_the_event_generator():
    import socket
    import threading

    from desk.app import DeskApp, Response

    closed = threading.Event()

    def events():
        try:
            for index in range(10_000):
                yield {"type": "delta", "text": "x" * 512, "index": index}
        finally:
            closed.set()

    app = DeskApp(port=0)
    app.add_routes([("GET", "/sse", lambda _req: Response(sse=events()))])
    app.start_background()
    try:
        with socket.create_connection(("127.0.0.1", app.port), timeout=5) as sock:
            sock.sendall(b"GET /sse HTTP/1.1\r\nHost: x\r\n\r\n")
            sock.recv(1024)
        assert closed.wait(5.0)
    finally:
        app.shutdown()


def test_config_reset_endpoint_refuses_healthy_config(server, tmp_path):
    http_call(server, "PUT", "/api/config", {"first_run_done": True})
    status, payload = http_call(server, "POST", "/api/config/reset", {})
    assert status == 409
    assert payload["error"]["code"] == "config_not_corrupt"


def test_get_config_says_which_models_the_current_root_already_has(server, tmp_path):
    kept = tmp_path / "kept"
    (kept / "minimax-music3").mkdir(parents=True)
    (kept / "minimax-music3" / "w.bin").write_bytes(b"x")
    http_call(server, "PUT", "/api/config", {"models_root": str(kept), "first_run_done": False})

    status, payload = http_call(server, "GET", "/api/config")

    assert status == 200
    assert payload["needs_setup"] is True
    assert payload["models_root_models"] == ["music3"]

    http_call(server, "PUT", "/api/config", {"first_run_done": True})
    status, payload = http_call(server, "GET", "/api/config")
    assert "models_root_models" not in payload
