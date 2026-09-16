"""HTTP status mapping and parseable SSE frames for the LLM UI surface."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest

from desk.llm.routes import build_routes
from tests.llm.llm_fakes import make_loaded, make_service


STREAM_CHUNKS = [
    {"choices": [{"delta": {"content": "你"}}]},
    {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"total_tokens": 2}},
]
OK_CHAT = {
    "choices": [{"message": {"content": "答", "reasoning_content": "想"}, "finish_reason": "stop"}],
    "usage": {"total_tokens": 2},
}


def serve(routes):
    table = {(route.method, route.path): route.handler for route in routes}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass

        def _dispatch(self):
            handler = table[(self.command, self.path)]
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length) or b"{}") if length else {}
            result = handler(body)
            if result.sse is not None:
                self.send_response(result.status)
                self.send_header("Content-Type", "text/event-stream")
                self.end_headers()
                for event in result.sse:
                    self.wfile.write(b"data: " + json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n\n")
                return
            payload = json.dumps(result.body).encode()
            self.send_response(result.status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        do_GET = _dispatch
        do_POST = _dispatch

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


@pytest.fixture()
def loaded_server(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": OK_CHAT, "chunks": STREAM_CHUNKS})
    server = serve(build_routes(testbed.service))
    yield testbed, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


@pytest.fixture()
def idle_server(tmp_path):
    testbed = make_service(tmp_path)
    server = serve(build_routes(testbed.service))
    yield testbed, f"http://127.0.0.1:{server.server_address[1]}"
    server.shutdown()
    server.server_close()


def _post(base, path, payload):
    return urlopen(Request(base + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}))


def test_load_202_and_status_200(idle_server):
    testbed, base = idle_server
    response = _post(base, "/api/llm/load", {"key": "glm"})
    assert response.status == 202
    assert json.load(response)["state"]["status"] == "loading"
    testbed.service.wait_settled()
    response = urlopen(base + "/api/llm/status")
    assert response.status == 200
    got = json.load(response)
    assert got["state"]["status"] == "loaded"
    assert got["loaded_model"]["key"] == "glm"


def test_load_unknown_key_404(idle_server):
    _, base = idle_server
    with pytest.raises(HTTPError) as exc:
        _post(base, "/api/llm/load", {"key": "nope"})
    assert exc.value.code == 404
    assert json.load(exc.value)["error"]["code"] == "model_not_found"


def test_load_missing_key_400(idle_server):
    """issue #5: 缺 key 必须是 400 key_required，不该被「目录里查不到」吸收成 404。"""
    _, base = idle_server
    with pytest.raises(HTTPError) as exc:
        _post(base, "/api/llm/load", {})
    assert exc.value.code == 400
    assert json.load(exc.value)["error"]["code"] == "key_required"


def test_load_non_string_key_400(idle_server):
    _, base = idle_server
    with pytest.raises(HTTPError) as exc:
        _post(base, "/api/llm/load", {"key": 123})
    assert exc.value.code == 400
    assert json.load(exc.value)["error"]["code"] == "key_required"


def test_unload_200_then_chat_503(loaded_server):
    _, base = loaded_server
    response = _post(base, "/api/llm/unload", {})
    assert response.status == 200
    assert json.load(response)["state"]["status"] == "idle"
    with pytest.raises(HTTPError) as exc:
        _post(base, "/api/llm/chat", {"messages": []})
    assert exc.value.code == 503
    assert json.load(exc.value)["error"]["code"] == "no_model_loaded"


def test_chat_200_with_separated_fields(loaded_server):
    _, base = loaded_server
    response = _post(base, "/api/llm/chat", {"messages": [{"role": "user", "content": "hi"}]})
    assert response.status == 200
    got = json.load(response)
    assert got["content"] == "答"
    assert got["reasoning"] == "想"
    assert got["finish_reason"] == "stop"
    assert got["model"] == "glm"


def test_chat_model_mismatch_409(loaded_server):
    _, base = loaded_server
    with pytest.raises(HTTPError) as exc:
        _post(base, "/api/llm/chat", {"messages": [], "model": "gpt-4o"})
    assert exc.value.code == 409
    assert json.load(exc.value)["error"]["code"] == "model_mismatch"


def test_stream_sse_frames_parse_and_end_with_done(loaded_server):
    _, base = loaded_server
    response = _post(base, "/api/llm/chat/stream", {"messages": []})
    assert response.status == 200
    assert response.headers["Content-Type"].startswith("text/event-stream")
    frames = [frame for frame in response.read().decode().split("\n\n") if frame]
    events = []
    for frame in frames:
        assert frame.startswith("data: ")
        events.append(json.loads(frame[len("data: "):]))
    assert events[0] == {"type": "delta", "text": "你", "reasoning": None}
    assert events[-1]["type"] == "done"


def test_stream_precheck_rejection_is_plain_json_503(idle_server):
    _, base = idle_server
    with pytest.raises(HTTPError) as exc:
        _post(base, "/api/llm/chat/stream", {"messages": []})
    assert exc.value.code == 503
    assert json.load(exc.value)["error"]["code"] == "no_model_loaded"


def test_unload_while_loading_cancels_the_load(idle_server):
    testbed, base = idle_server
    testbed.backend.hold_health = True
    _post(base, "/api/llm/load", {"key": "glm"})
    response = _post(base, "/api/llm/unload", {})
    assert response.status == 200
    assert json.load(response)["state"]["status"] == "idle"
    testbed.backend.health_release.set()
    testbed.service.wait_settled()


def _route(service, path):
    return next(route for route in build_routes(service) if route.path == path)


def test_prompt_assist_route_returns_fields(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": {
        "choices": [{"message": {"content": '{"caption": "温柔民谣", "lyrics": "第一行"}'}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 9},
    }})
    result = _route(testbed.service, "/api/llm/prompt-assist").handler({"task": "music", "action": "lucky"})
    assert result.status == 200
    assert result.body == {"task": "music", "action": "lucky", "text": "温柔民谣", "lyrics": "第一行"}


def test_prompt_assist_route_maps_errors(tmp_path):
    idle = make_service(tmp_path)
    handler = _route(idle.service, "/api/llm/prompt-assist").handler
    no_model = handler({"task": "video", "action": "lucky"})
    assert no_model.status == 503
    assert no_model.body["error"]["code"] == "no_model_loaded"
    bad = handler({"task": "video", "action": "refine", "text": ""})
    assert bad.status == 400
    assert bad.body["error"] == {"code": "text_required", "message": "先在输入框里写点东西，再点「优化提示词」"}
