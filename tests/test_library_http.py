"""library.http — transport-neutral handlers and error mapping tests."""
import json
from pathlib import Path

from desk.library import LibraryService
from desk.library.http import LibRequest, routes


class FakeRoots:
    def __init__(self, base: Path):
        self.data_root = base
        self.history_path = base / "history.jsonl"
        self.sessions_dir = base / "sessions"
        self.outputs_root = base / "outputs"


def make_service(tmp_path):
    roots = FakeRoots(tmp_path)
    roots.outputs_root.mkdir()
    return LibraryService(roots), roots


def route_map(service):
    return {(method, path): handler for method, path, handler in routes(service)}


def body_json(resp):
    return json.loads(resp.body.decode("utf-8"))


def test_list_history_and_outputs_routes(tmp_path):
    svc, roots = make_service(tmp_path)
    svc.append_history({"kind": "video", "status": "done", "output": "h3-a.mp4"})
    svc.append_history({"kind": "music", "status": "done", "output": None})
    (roots.outputs_root / "h3-a.mp4").write_bytes(b"x" * 4)

    route_handlers = route_map(svc)
    history = route_handlers[("GET", "/api/history")](LibRequest(query={"limit": "1"}))
    assert history.status == 200
    assert len(body_json(history)) == 1

    outputs = route_handlers[("GET", "/api/outputs")](LibRequest())
    assert outputs.status == 200
    assert body_json(outputs)[0]["name"] == "h3-a.mp4"


def test_serve_output_route_maps_range_404_416(tmp_path):
    svc, roots = make_service(tmp_path)
    (roots.outputs_root / "h3-a.mp4").write_bytes(b"x" * 10)
    handler = route_map(svc)[("GET", "/api/outputs/{name}")]

    ok = handler(LibRequest(path_params={"name": "h3-a.mp4"}, headers={"range": "bytes=2-3"}))
    assert ok.status == 206
    assert ok.headers["Content-Range"] == "bytes 2-3/10"
    assert ok.body.read() == b"xx"
    assert handler(LibRequest(path_params={"name": "../evil"})).status == 404

    unsatisfiable = handler(LibRequest(path_params={"name": "h3-a.mp4"}, headers={"Range": "bytes=99-"}))
    assert unsatisfiable.status == 416


def test_bad_limit_is_400(tmp_path):
    svc, _ = make_service(tmp_path)

    response = route_map(svc)[("GET", "/api/history")](LibRequest(query={"limit": "abc"}))

    assert response.status == 400
    assert "error" in body_json(response)
