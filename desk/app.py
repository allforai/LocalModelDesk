"""Ultra-thin HTTP skeleton: route table, JSON codec, and error envelope."""
from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .foundation.errors import FoundationError


log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    body: dict


class DeskApp:
    def __init__(self, host: str = "127.0.0.1", port: int = 8766):
        self._routes: list = []
        app = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt, *args):
                log.info("http %s", fmt % args)

            def _dispatch(self, method: str) -> None:
                path = self.path.split("?", 1)[0]
                handler = app._find(method, path)
                if handler is None:
                    self._send(404, {"error": {"code": "not_found", "message": f"no route for {method} {path}"}})
                    return
                body: dict = {}
                length = int(self.headers.get("Content-Length") or 0)
                if length:
                    try:
                        body = json.loads(self.rfile.read(length).decode("utf-8"))
                    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                        self._send(400, {"error": {"code": "bad_request", "message": f"invalid JSON body: {exc}"}})
                        return
                try:
                    result = handler(Request(method, path, body))
                except FoundationError as exc:
                    self._send(exc.http_status, {"error": {"code": exc.code, "message": exc.message, **exc.payload}})
                except Exception as exc:
                    log.exception("unhandled error on %s %s", method, path)
                    self._send(500, {"error": {"code": "internal", "message": str(exc)}})
                else:
                    self._send(200, result)

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

        self._server = ThreadingHTTPServer((host, port), Handler)

    @property
    def port(self) -> int:
        return self._server.server_address[1]

    def add_routes(self, routes) -> None:
        self._routes.extend(routes)

    def _find(self, method: str, path: str):
        best, best_len = None, -1
        for route_method, prefix, handler in self._routes:
            if route_method == method and (path == prefix or path.startswith(prefix.rstrip("/") + "/")) and len(prefix) > best_len:
                best, best_len = handler, len(prefix)
        return best

    def start_background(self) -> None:
        threading.Thread(target=self._server.serve_forever, daemon=True).start()

    def serve_forever(self) -> None:
        self._server.serve_forever()

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()
