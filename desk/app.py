"""Ultra-thin HTTP skeleton: route table, JSON codec, and error envelope."""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Iterable
from urllib.parse import parse_qs, unquote, urlsplit

from .foundation.errors import FoundationError


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    body: dict
    query: dict[str, str]
    headers: dict[str, str]
    raw_body: bytes
    path_params: dict[str, str]


@dataclass(frozen=True)
class Response:
    """Transport response understood by the production HTTP host."""

    status: int = 200
    body: Any = None
    headers: dict[str, str] | None = None
    sse: Iterable[dict] | None = None


class DeskApp:
    def __init__(self, host: str = "127.0.0.1", port: int = 8766):
        self._routes: list = []
        self.static_assets = None
        app = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                log.info("http %s", fmt % args)

            def _dispatch(self, method: str) -> None:
                parsed = urlsplit(self.path)
                path = parsed.path
                if method == "GET" and app.static_assets is not None:
                    resolved = app.static_assets.resolve(self.path)
                    if resolved is not None:
                        asset, content_type = resolved
                        self._send_response(Response(
                            body=asset.read_bytes(),
                            headers={"Content-Type": content_type},
                        ))
                        return
                matched = app._find(method, path)
                handler, path_params = matched if matched is not None else (None, {})
                if handler is None:
                    self._send(404, {"error": {"code": "not_found", "message": f"no route for {method} {path}"}})
                    return
                body: dict = {}
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                    if length < 0:
                        raise ValueError()
                except ValueError:
                    self._send(400, {"error": {"code": "bad_request", "message": "invalid Content-Length"}})
                    return
                if path == "/api/media/inputs" and length > 45 * 1024 * 1024:
                    self.close_connection = True
                    self._send(413, {"error": {"code": "input_too_large", "message": "素材不能超过 32 MB"}})
                    return
                raw_body = self.rfile.read(length) if length else b""
                if length:
                    try:
                        body = json.loads(raw_body.decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                        self._send(400, {"error": {"code": "bad_request", "message": f"invalid JSON body: {exc}"}})
                        return
                    if not isinstance(body, dict):
                        self._send(400, {"error": {
                            "code": "bad_request", "message": "JSON body must be an object"
                        }})
                        return
                try:
                    query = {
                        key: values[-1]
                        for key, values in parse_qs(parsed.query, keep_blank_values=True).items()
                    }
                    result = handler(Request(
                        method, path, body, query, dict(self.headers.items()), raw_body,
                        path_params,
                    ))
                except FoundationError as exc:
                    self._send(exc.http_status, {"error": {"code": exc.code, "message": exc.message, **exc.payload}})
                except Exception as exc:
                    log.exception("unhandled error on %s %s", method, path)
                    self._send(500, {"error": {"code": "internal", "message": str(exc)}})
                else:
                    if isinstance(result, Response):
                        self._send_response(result)
                    elif isinstance(result, tuple) and len(result) == 2:
                        self._send(result[0], result[1])
                    else:
                        self._send(200, result)

            def _send_response(self, response: Response) -> None:
                headers = dict(response.headers or {})
                if response.sse is not None:
                    self.send_response(response.status)
                    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache")
                    for name, value in headers.items():
                        self.send_header(name, value)
                    self.end_headers()
                    events = response.sse
                    try:
                        for event in events:
                            frame = b"data: " + json.dumps(
                                event, ensure_ascii=False
                            ).encode("utf-8") + b"\n\n"
                            self.wfile.write(frame)
                            self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        log.info("sse client went away on %s", self.path)
                    finally:
                        close = getattr(events, "close", None)
                        if callable(close):
                            close()
                    return
                body = response.body
                if hasattr(body, "read") and callable(body.read):
                    data = body.read()
                elif isinstance(body, bytes):
                    data = body
                elif isinstance(body, str):
                    data = body.encode("utf-8")
                elif body is None:
                    data = b""
                else:
                    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
                    headers.setdefault("Content-Type", "application/json; charset=utf-8")
                self.send_response(response.status)
                headers.setdefault("Content-Length", str(len(data)))
                for name, value in headers.items():
                    self.send_header(name, str(value))
                self.end_headers()
                self.wfile.write(data)

            def _send(self, status: int, payload: dict) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                self._dispatch("GET")

            def do_POST(self):
                self._dispatch("POST")

            def do_PUT(self):
                self._dispatch("PUT")

            def do_DELETE(self):
                self._dispatch("DELETE")

            def do_PATCH(self):
                self._dispatch("PATCH")

        self._server = ThreadingHTTPServer((host, port), Handler)

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    def add_routes(self, routes) -> None:
        self._routes.extend(routes)

    def _find(self, method: str, path: str):
        best, best_score = None, (-1, -1)
        actual = [part for part in path.split("/") if part]
        for route_method, pattern, handler in self._routes:
            if route_method != method:
                continue
            expected = [part for part in pattern.split("/") if part]
            params: dict[str, str] = {}
            dynamic = any(part.startswith("{") and part.endswith("}") for part in expected)
            if dynamic and len(expected) != len(actual):
                continue
            if not dynamic and len(actual) < len(expected):
                continue
            for wanted, found in zip(expected, actual):
                if wanted.startswith("{") and wanted.endswith("}"):
                    params[wanted[1:-1]] = unquote(found)
                elif wanted != found:
                    break
            else:
                if dynamic or len(actual) == len(expected) or path.startswith(pattern.rstrip("/") + "/"):
                    score = (len(expected), sum(not p.startswith("{") for p in expected))
                    if score > best_score:
                        best, best_score = (handler, params), score
        return best

    def start_background(self) -> None:
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()
