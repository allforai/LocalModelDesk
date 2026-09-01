"""Black-box proof that the production composition root is actually usable."""
import json
from urllib.parse import quote
import urllib.request

from desk.runtime import build_runtime

from http_helpers import http_call


def _configured_data_root(tmp_path, monkeypatch):
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "config.json").write_text(json.dumps({
        "config_version": 1,
        "first_run_done": False,
        "models_root": str(data_root / "models"),
        "outputs_root": str(data_root / "outputs"),
        "gateway": {"enabled": False, "host": "127.0.0.1", "port": 0},
    }), encoding="utf-8")
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(data_root))
    return data_root


def _raw_get(runtime, path):
    with urllib.request.urlopen(
        f"http://127.0.0.1:{runtime.port}{path}", timeout=5
    ) as response:
        return response.status, response.headers, response.read()


def test_production_runtime_mounts_shell_and_core_services(tmp_path, monkeypatch):
    data_root = _configured_data_root(tmp_path, monkeypatch)
    runtime = build_runtime(port=0)
    runtime.start_background()
    try:
        status, headers, body = _raw_get(runtime, "/")
        assert status == 200
        assert headers.get_content_type() == "text/html"
        assert b"LocalModelDesk" in body

        status, headers, body = _raw_get(runtime, "/static/js/main.js")
        assert status == 200
        assert "javascript" in headers.get("Content-Type")
        assert body

        status, state = http_call(runtime, "GET", "/api/state")
        assert status == 200
        assert state["holder"] is None
        assert state["media_busy"] is False
        assert set(state["can_start"]) == {"llm", "media"}

        status, catalog = http_call(runtime, "GET", "/api/resources/catalog")
        assert status == 200
        assert isinstance(catalog, list) and catalog

        status, llm = http_call(runtime, "GET", "/api/llm/status")
        assert status == 200
        assert llm["state"]["status"] == "idle"

        status, paths = http_call(runtime, "GET", "/api/paths")
        assert status == 200
        assert paths["data_root"] == str(data_root.resolve())
    finally:
        runtime.shutdown()


def test_production_runtime_supports_dynamic_patch_routes(tmp_path, monkeypatch):
    data_root = _configured_data_root(tmp_path, monkeypatch)
    outputs = data_root / "outputs"
    outputs.mkdir()
    media = outputs / "space name.wav"
    media.write_bytes(b"RIFF-test")
    runtime = build_runtime(port=0)
    runtime.start_background()
    try:
        status, session = http_call(runtime, "POST", "/api/sessions", {})
        assert status == 200
        status, updated = http_call(
            runtime, "PATCH", f"/api/sessions/{session['id']}", {"title": "renamed"}
        )
        assert status == 200
        assert updated["title"] == "renamed"

        status, headers, body = _raw_get(
            runtime, f"/api/outputs/{quote(media.name)}"
        )
        assert status == 200
        assert headers.get_content_type().startswith("audio/")
        assert body == b"RIFF-test"
    finally:
        runtime.shutdown()


def test_production_modules_never_import_test_fakes():
    from pathlib import Path

    for relative in ("desk/runtime.py", "desk/__main__.py", "desk/gateway/desk_backend.py"):
        assert "desk.testing" not in Path(relative).read_text(encoding="utf-8")
