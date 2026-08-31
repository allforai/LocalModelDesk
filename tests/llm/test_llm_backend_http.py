"""MlxLmBackend 的 http.client 通路：健康、非流式、SSE 解析、故障抛出。"""
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from desk.llm.backend import BackendHttpError, MlxLmBackend


OK_CHAT = {"choices": [{"message": {"content": "你好", "reasoning_content": "想想"},
                        "finish_reason": "stop"}],
           "usage": {"prompt_tokens": 1, "completion_tokens": 2, "total_tokens": 3}}

SSE_LINES = [
    b'data: {"choices":[{"delta":{"content":"a"}}]}\n\n',
    b"noise-not-a-data-line\n\n",
    b"data: not-json\n\n",
    b'data: {"choices":[{"delta":{},"finish_reason":"stop"}],"usage":{"total_tokens":3}}\n\n',
    b"data: [DONE]\n\n",
]


class Upstream(BaseHTTPRequestHandler):
    mode = "ok"

    def log_message(self, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'{"data": []}')

    def do_POST(self):
        self.rfile.read(int(self.headers.get("Content-Length") or 0))
        if type(self).mode == "error500":
            self.send_response(500)
            self.end_headers()
            self.wfile.write(b"boom")
            return
        if type(self).mode == "sse":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            for line in SSE_LINES:
                self.wfile.write(line)
            return
        if type(self).mode == "sse_truncated":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.end_headers()
            self.wfile.write(SSE_LINES[0])
            return
        body = json.dumps(OK_CHAT).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


@pytest.fixture()
def upstream():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Upstream)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield server
    server.shutdown()
    server.server_close()


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def test_health_true_then_false_on_dead_port(upstream):
    backend = MlxLmBackend()
    assert backend.health(upstream.server_address[1]) is True
    assert backend.health(_free_port()) is False


def test_chat_returns_upstream_json(upstream):
    Upstream.mode = "ok"
    assert MlxLmBackend().chat(upstream.server_address[1], {"messages": []}) == OK_CHAT


def test_chat_non_200_raises(upstream):
    Upstream.mode = "error500"
    with pytest.raises(BackendHttpError):
        MlxLmBackend().chat(upstream.server_address[1], {"messages": []})
    Upstream.mode = "ok"


def test_chat_connection_refused_raises():
    with pytest.raises(BackendHttpError):
        MlxLmBackend().chat(_free_port(), {"messages": []})


def test_chat_stream_parses_data_lines_skips_noise_stops_at_done(upstream):
    Upstream.mode = "sse"
    chunks = list(MlxLmBackend().chat_stream(upstream.server_address[1], {"messages": []}))
    assert chunks == [
        {"choices": [{"delta": {"content": "a"}}]},
        {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"total_tokens": 3}},
    ]
    Upstream.mode = "ok"


def test_chat_stream_truncated_ends_without_done_chunk(upstream):
    Upstream.mode = "sse_truncated"
    chunks = list(MlxLmBackend().chat_stream(upstream.server_address[1], {"messages": []}))
    assert chunks == [{"choices": [{"delta": {"content": "a"}}]}]
    Upstream.mode = "ok"


def test_chat_stream_non_200_raises(upstream):
    Upstream.mode = "error500"
    with pytest.raises(BackendHttpError):
        MlxLmBackend().chat_stream(upstream.server_address[1], {"messages": []})
    Upstream.mode = "ok"
