"""Media HTTP route table: handler adapters and error envelopes."""
import threading
from pathlib import Path
from types import SimpleNamespace

from desk.media.routes import build_routes
from media_fakes import make_service


def route_map(service):
    return {(method, path): handler for method, path, handler in build_routes(service)}


def test_music_without_lyrics_is_a_400_with_chinese_message(tmp_path):
    service, _ = make_service(tmp_path)
    service._probe_capabilities = lambda: {"music_runtime": SimpleNamespace(present=True, detail="")}
    service._resolve_paths = lambda: SimpleNamespace(
        outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
        music_python=Path("/fake/bin/music-python"), media_cli_dir=Path("/fake/media"), music_env={})
    service._list_catalog = lambda: [SimpleNamespace(key="music3", relpath="minimax-music3", gb=27.0)]
    handler = route_map(service)[("POST", "/api/media/music")]
    status, payload = handler({"caption": "民谣", "lyrics": "   ", "duration": 10}, {})
    assert status == 400
    assert payload["error"]["code"] == "lyrics_required"
    assert payload["error"]["message"] == "请填写歌词：Music 3 需要歌词才能生成"


def test_media_routes_adapter_and_error_envelopes(tmp_path):
    service, _ = make_service(tmp_path)
    routes = route_map(service)
    assert list(routes) == [
        ("POST", "/api/media/inputs"),
        ("POST", "/api/media/video"),
        ("POST", "/api/media/music"),
        ("POST", "/api/media/image"),
        ("POST", "/api/media/cancel"),
        ("GET", "/api/media/job"),
    ]

    status, payload = routes[("POST", "/api/media/video")]({"prompt": ""}, {})
    assert (status, payload["error"]["code"]) == (400, "prompt_required")
    assert set(payload["error"]) == {"code", "message", "detail"}

    service._probe_capabilities = lambda: {}
    status, payload = routes[("POST", "/api/media/video")]({
        "prompt": "p", "width": 512, "height": 288, "frames": 73, "steps": 10,
    }, {})
    assert (status, payload["error"]["code"]) == (503, "capability_missing")

    status, payload = routes[("POST", "/api/media/cancel")](None, {})
    assert (status, payload["error"]["code"]) == (409, "no_running_job")


def test_media_routes_start_jobs_and_parse_status_cursor(tmp_path):
    service, _ = make_service(tmp_path)
    routes = route_map(service)
    done = threading.Event()
    service.on_job_finished(lambda _: done.set())
    status, payload = routes[("POST", "/api/media/video")]({
        "prompt": "p", "width": 512, "height": 288, "frames": 73, "steps": 10,
    }, {})
    assert status == 200
    assert payload["status"] == "running"
    assert done.wait(5.0)

    status, payload = routes[("GET", "/api/media/job")](None, {"log_from": "0", "job_id": "1"})
    assert status == 200
    assert payload["job_id"] == 1
    status, payload = routes[("GET", "/api/media/job")](None, {"log_from": "nope"})
    assert (status, payload["error"]["code"]) == (400, "invalid_params")

    service, _ = make_service(tmp_path / "music")
    service._probe_capabilities = lambda: {
        "music_runtime": SimpleNamespace(present=True, detail=""),
    }
    service._resolve_paths = lambda: SimpleNamespace(
        outputs_root=tmp_path / "music" / "outputs", models_root=tmp_path / "music" / "models",
        music_python=Path("/fake/bin/music-python"), media_cli_dir=Path("/fake/media"),
        music_env={},
    )
    service._list_catalog = lambda: [SimpleNamespace(key="music3", relpath="minimax-music3", gb=27.0)]
    done = threading.Event()
    service.on_job_finished(lambda _: done.set())
    status, payload = route_map(service)[("POST", "/api/media/music")]({
        "caption": "c", "lyrics": "l", "duration": 30.0,
    }, {})
    assert status == 200
    assert payload["kind"] == "music"
    assert done.wait(5.0)
