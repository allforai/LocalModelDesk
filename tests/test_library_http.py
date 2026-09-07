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


def test_route_table_covers_module_contract(tmp_path):
    svc, _ = make_service(tmp_path)

    assert set(route_map(svc)) == {
        ("GET", "/api/outputs"),
        ("GET", "/api/outputs/{name}"),
        ("POST", "/api/outputs/{name}/reveal"),
        ("POST", "/api/outputs/reveal"),
        ("GET", "/api/history"),
        ("GET", "/api/sessions"),
        ("POST", "/api/sessions"),
        ("PATCH", "/api/sessions/{id}"),
        ("DELETE", "/api/sessions/{id}"),
    }


def test_reveal_output_runs_open_minus_R_and_refuses_escape(tmp_path):
    svc, roots = make_service(tmp_path)
    calls = []
    svc.outputs.set_opener(lambda argv, **kw: calls.append(argv))
    target = roots.outputs_root / "h3-1.mp4"
    target.write_bytes(b"x")

    route_handlers = route_map(svc)
    reveal_file = route_handlers[("POST", "/api/outputs/{name}/reveal")]
    result = reveal_file(LibRequest(path_params={"name": "h3-1.mp4"}))
    assert result.status == 200
    assert body_json(result)["revealed"].endswith("h3-1.mp4")
    assert calls == [["open", "-R", str(target.resolve())]]

    result = reveal_file(LibRequest(path_params={"name": "../config.json"}))
    assert result.status == 404

    reveal_folder = route_handlers[("POST", "/api/outputs/reveal")]
    result = reveal_folder(LibRequest())
    assert result.status == 200
    assert calls[-1] == ["open", str(roots.outputs_root.resolve())]


def test_session_crud_over_http(tmp_path):
    svc, _ = make_service(tmp_path)
    route_handlers = route_map(svc)
    created = route_handlers[("POST", "/api/sessions")](
        LibRequest(body=json.dumps({"title": "t"}).encode())
    )
    assert created.status == 200
    session_id = body_json(created)["id"]
    patched = route_handlers[("PATCH", "/api/sessions/{id}")](
        LibRequest(
            path_params={"id": session_id},
            body=json.dumps({"messages": [{"role": "user", "content": "hi"}]}).encode(),
        )
    )
    assert patched.status == 200
    assert len(body_json(patched)["messages"]) == 1
    listed = route_handlers[("GET", "/api/sessions")](LibRequest())
    assert body_json(listed)[0]["id"] == session_id
    deleted = route_handlers[("DELETE", "/api/sessions/{id}")](
        LibRequest(path_params={"id": session_id})
    )
    assert deleted.status == 200
    assert body_json(deleted) == {"deleted": session_id}


def test_create_with_empty_body_uses_defaults(tmp_path):
    svc, _ = make_service(tmp_path)

    response = route_map(svc)[("POST", "/api/sessions")](LibRequest())

    assert response.status == 200
    assert body_json(response)["title"] == "新会话"


def test_session_http_error_mapping(tmp_path):
    svc, _ = make_service(tmp_path)
    route_handlers = route_map(svc)
    assert route_handlers[("DELETE", "/api/sessions/{id}")](
        LibRequest(path_params={"id": "0" * 32})
    ).status == 404
    assert route_handlers[("PATCH", "/api/sessions/{id}")](
        LibRequest(path_params={"id": "0" * 32}, body=b"{oops")
    ).status == 400
    session_id = body_json(route_handlers[("POST", "/api/sessions")](LibRequest()))["id"]
    assert route_handlers[("PATCH", "/api/sessions/{id}")](
        LibRequest(path_params={"id": session_id}, body=json.dumps({"nope": 1}).encode())
    ).status == 400
    assert route_handlers[("POST", "/api/sessions")](
        LibRequest(body=json.dumps({"weird": 1}).encode())
    ).status == 400
