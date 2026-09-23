import json
import logging
import os
import traceback

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
    assert set(payload["capabilities"]) == {"mlx_h3", "venv", "models_root", "music_runtime", "image_runtime", "config"}


def test_public_capabilities_does_not_expose_paths(server):
    status, payload = http_call(server, "GET", "/api/capabilities")
    assert status == 200
    assert isinstance(payload["image_runtime"]["present"], bool)
    assert all(set(value) == {"present", "detail"} for value in payload.values())
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


@pytest.mark.parametrize("bad_root", [12345, {"a": 1}, ["x"], ""])
def test_first_run_rejects_non_string_models_root_with_400(server, bad_root):
    """issue #8: 类型错误的 models_root 曾经 TypeError 穿透成 500 internal。"""
    status, payload = http_call(server, "POST", "/api/first-run", {"models_root": bad_root})
    assert status == 400
    assert payload["error"]["code"] == "models_root_invalid"
    assert "int" not in payload["error"]["message"]
    assert "dict" not in payload["error"]["message"]


def test_first_run_endpoint_rejects_pointing_at_a_subtree_itself(server, tmp_path):
    """issue #10: the 'select models directory' entry must warn instead of silently
    succeeding when it's handed the llms/ subtree itself rather than its parent."""
    parent = tmp_path / "external"
    llms = parent / "llms"
    (llms / "mlx-community" / "glm").mkdir(parents=True)
    (llms / "mlx-community" / "glm" / "weight.safetensors").write_bytes(b"x")

    status, payload = http_call(server, "POST", "/api/first-run", {"models_root": str(llms)})

    assert status == 400
    assert payload["error"]["code"] == "models_root_unrecognized"
    assert str(llms) in payload["error"]["message"]
    assert str(parent) in payload["error"]["message"]

    status, payload = http_call(server, "GET", "/api/config")
    assert payload["needs_setup"] is True


def test_first_run_missing_models_root_still_uses_default(server):
    status, payload = http_call(server, "POST", "/api/first-run", {})
    assert status == 200
    assert payload["first_run_done"] is True


def test_put_config_rejects_bad_field_before_500ing_on_a_corrupt_file(server, tmp_path):
    """issue #5: 字段校验必须先于「配置文件损坏」的状态检查。"""
    config_path = tmp_path / "data" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{ this is not valid json", encoding="utf-8")

    status, payload = http_call(server, "PUT", "/api/config", {"gateway": {"port": "not-a-number"}})
    assert status == 400
    assert payload["error"]["code"] == "config_invalid"


def test_put_config_still_500s_on_corrupt_file_when_fields_are_valid(server, tmp_path):
    config_path = tmp_path / "data" / "config.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("{ this is not valid json", encoding="utf-8")

    status, payload = http_call(server, "PUT", "/api/config", {"gateway": {"port": 9100}})
    assert status == 500
    assert payload["error"]["code"] == "config_corrupt"


def test_unhandled_exception_is_sanitized_and_the_original_is_logged(caplog):
    """issue #8: 兜底不该外泄 Python 异常原文，但服务端日志要留住完整 traceback。"""
    app = DeskApp("127.0.0.1", 0)

    def boom(_req):
        raise TypeError("argument should be a str or an os.PathLike object, not 'int'")

    app.add_routes([("POST", "/boom", boom)])
    app.start_background()
    try:
        with caplog.at_level(logging.ERROR):
            status, payload = http_call(app, "POST", "/boom", {})
        assert status == 500
        assert payload["error"]["code"] == "internal"
        assert "os.PathLike" not in payload["error"]["message"]
        assert "int" not in payload["error"]["message"]

        logged = [record for record in caplog.records if record.exc_info]
        assert logged, "the exception must be logged with exc_info for a traceback"
        formatted = "".join(traceback.format_exception(*logged[0].exc_info))
        assert "TypeError" in formatted
        assert "argument should be a str or an os.PathLike object" in formatted
    finally:
        app.shutdown()


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
