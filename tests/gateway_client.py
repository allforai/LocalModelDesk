"""Gateway HTTP test helpers using a temporary loopback server."""
from __future__ import annotations

import contextlib
import http.client
import json
import threading

from desk.gateway.http_server import GatewayHTTPServer

FIXED_NOW = 1756605000
FIXED_ID = "fixedfixedfixedfixedfixedfixed00"


@contextlib.contextmanager
def serve(backend, *, now=lambda: FIXED_NOW, new_id=lambda: FIXED_ID):
    server = GatewayHTTPServer(("127.0.0.1", 0), backend, now=now, new_id=new_id)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)


def request(port, method, path, body=None, host="127.0.0.1"):
    """Return ``(status, lowercase_headers, raw_bytes)`` for one request."""
    conn = http.client.HTTPConnection(host, port, timeout=10)
    payload = None
    if body is not None:
        payload = body if isinstance(body, (bytes, str)) else json.dumps(body, ensure_ascii=False)
    try:
        conn.request(method, path, body=payload, headers={"Content-Type": "application/json"})
        response = conn.getresponse()
        raw = response.read()
        return response.status, {key.lower(): value for key, value in response.getheaders()}, raw
    finally:
        conn.close()


def json_request(port, method, path, body=None, host="127.0.0.1"):
    status, headers, raw = request(port, method, path, body, host=host)
    return status, headers, json.loads(raw)


def sse_request(port, path, body):
    status, headers, raw = request(port, "POST", path, body)
    frames = [frame + "\n\n" for frame in raw.decode("utf-8").split("\n\n") if frame]
    return status, headers, frames
