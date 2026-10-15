import errno
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from desk.agent_cli.client import DeskClient, HttpError, Unreachable, classify_os_error


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, status, payload):
        data = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self.path.startswith("/ok"):
            self._send(200, {"path": self.path})
        elif self.path == "/obj-error":
            self._send(409, {"error": {"code": "media_busy", "message": "忙", "detail": {"x": 1}}})
        else:
            self._send(404, {"error": "会话不存在"})

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        if self.path == "/slow":
            import time
            time.sleep(1.5)
        self._send(200, {"echo": json.loads(self.rfile.read(n) or b"{}")})


@pytest.fixture
def server():
    srv = HTTPServer(("127.0.0.1", 0), _Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_get_with_query_and_post_body(server):
    c = DeskClient(server)
    assert c.get("/ok", {"a": "中 文"})["path"] == "/ok?a=%E4%B8%AD+%E6%96%87"
    assert c.post("/x", {"k": 1}) == {"echo": {"k": 1}}


def test_object_error_envelope(server):
    with pytest.raises(HttpError) as exc:
        DeskClient(server).get("/obj-error")
    assert (exc.value.status, exc.value.code, exc.value.message, exc.value.detail) == (409, "media_busy", "忙", {"x": 1})


def test_string_error_envelope(server):
    with pytest.raises(HttpError) as exc:
        DeskClient(server).get("/missing")
    assert (exc.value.status, exc.value.code, exc.value.message) == (404, "http_404", "会话不存在")


def test_refused_connection_is_classified_refused():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    with pytest.raises(Unreachable) as exc:
        DeskClient(f"http://127.0.0.1:{port}").get("/ok")
    assert exc.value.kind == "refused"


@pytest.mark.parametrize("err,kind", [
    (errno.ECONNREFUSED, "refused"), (errno.EPERM, "sandbox"), (errno.EACCES, "sandbox"),
    (errno.ETIMEDOUT, "other"),
])
def test_classify_os_error(err, kind):
    assert classify_os_error(OSError(err, "x")) == kind


def test_post_timeout_override_outlasts_the_default(server):
    """A long non-streaming chat must not die on the client's default socket timeout."""
    with pytest.raises(Unreachable):
        DeskClient(server, timeout=0.5).post("/slow", {})
    assert DeskClient(server, timeout=0.5).post("/slow", {"k": 1}, timeout=5) == {"echo": {"k": 1}}
