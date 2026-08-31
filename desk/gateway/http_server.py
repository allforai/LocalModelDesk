"""Gateway HTTP adapter: routing, bounded body reads, JSON/SSE writes."""
from __future__ import annotations

import json
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import anthropic_dialect, guard, openai_dialect
from .errors import (
    REASON_HEADER,
    REASON_INVALID_REQUEST,
    REASON_METHOD_NOT_ALLOWED,
    REASON_NOT_FOUND,
    REASON_UPSTREAM_ERROR,
    RETRY_AFTER_SECONDS,
    GatewayReject,
    dialect_for_path,
    error_envelope,
)

MAX_BODY_BYTES = 10 * 1024 * 1024


def _new_id() -> str:
    return uuid.uuid4().hex


class GatewayHTTPServer(ThreadingHTTPServer):
    """One handler thread per request with injectable time and ID sources."""

    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, backend, *, now=time.time, new_id=_new_id):
        super().__init__(address, _Handler)
        self.backend = backend
        self.now = now
        self.new_id = new_id


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server: GatewayHTTPServer

    def log_message(self, fmt, *args):
        pass

    def _send_json(self, code: int, payload: dict, extra_headers=()):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for name, value in extra_headers:
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(body)

    def _send_reject(self, reject: GatewayReject):
        headers = [(REASON_HEADER, reject.code)]
        if reject.http == 503:
            headers.append(("Retry-After", str(RETRY_AFTER_SECONDS)))
        self._send_json(reject.http, error_envelope(dialect_for_path(self.path), reject), headers)

    def _stream(self, frames):
        """Write SSE frames and close the producer if the client disconnects."""
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.send_header("Connection", "close")
        self.end_headers()
        try:
            for frame in frames:
                self.wfile.write(frame)
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            close = getattr(frames, "close", None)
            if close is not None:
                close()
            self.close_connection = True

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > MAX_BODY_BYTES:
            # Drain without buffering so the response can be delivered cleanly
            # to clients that have already begun their upload.
            remaining = length
            while remaining:
                chunk = self.rfile.read(min(64 * 1024, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
            raise GatewayReject(
                REASON_INVALID_REQUEST, 400, f"request body exceeds {MAX_BODY_BYTES} bytes"
            )
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            return json.loads(raw)
        except ValueError:
            raise GatewayReject(
                REASON_INVALID_REQUEST, 400, "request body is not valid JSON"
            ) from None

    def do_GET(self):
        try:
            if self.path == "/v1/models":
                self._send_json(200, openai_dialect.models_list(self.server.backend.llm_status()))
            elif self.path in ("/v1/chat/completions", "/v1/messages"):
                raise GatewayReject(REASON_METHOD_NOT_ALLOWED, 405, f"{self.path} requires POST")
            else:
                raise GatewayReject(REASON_NOT_FOUND, 404, f"unknown path: {self.path}")
        except GatewayReject as reject:
            self._send_reject(reject)

    def do_POST(self):
        try:
            if self.path == "/v1/chat/completions":
                self._chat(openai_dialect)
            elif self.path == "/v1/messages":
                self._chat(anthropic_dialect)
            elif self.path == "/v1/models":
                raise GatewayReject(REASON_METHOD_NOT_ALLOWED, 405, "/v1/models requires GET")
            else:
                raise GatewayReject(REASON_NOT_FOUND, 404, f"unknown path: {self.path}")
        except GatewayReject as reject:
            self._send_reject(reject)

    def _chat(self, dialect_mod):
        parsed = dialect_mod.parse_request(self._read_json_body())
        loaded = guard.admit(self.server.backend, parsed["model"])
        model_out = parsed["model"] or loaded["served_id"]

        if parsed["stream"]:
            try:
                events = self.server.backend.chat_stream(parsed["chat_request"])
            except Exception as exc:
                raise GatewayReject(
                    REASON_UPSTREAM_ERROR, 500, f"chat backend failed: {exc}"
                ) from exc
            if dialect_mod is openai_dialect:
                frames = openai_dialect.stream_chunks(
                    events, "chatcmpl-" + self.server.new_id(), int(self.server.now()), model_out
                )
            else:
                frames = anthropic_dialect.stream_events(
                    events, "msg_" + self.server.new_id(), model_out
                )
            self._stream(frames)
            return

        try:
            result = self.server.backend.chat_completion(parsed["chat_request"])
        except Exception as exc:
            raise GatewayReject(REASON_UPSTREAM_ERROR, 500, f"chat backend failed: {exc}") from exc
        if dialect_mod is openai_dialect:
            payload = openai_dialect.completion_response(
                result, model_out, "chatcmpl-" + self.server.new_id(), int(self.server.now())
            )
        else:
            payload = anthropic_dialect.message_response(
                result, model_out, "msg_" + self.server.new_id()
            )
        self._send_json(200, payload)
