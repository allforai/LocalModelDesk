"""Thin HTTP adapter from the LLM UI routes to ``LlmService``."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable, Iterator

from .state import (
    ERR_LOAD_IN_PROGRESS,
    ERR_MEDIA_BUSY,
    ERR_MODEL_DIR_MISSING,
    ERR_MODEL_MISMATCH,
    ERR_MODEL_NOT_FOUND,
    ERR_NO_MODEL_LOADED,
    ERR_UPSTREAM_ERROR,
    LlmRejected,
    UpstreamError,
)


_REJECTION_STATUS = {
    ERR_MODEL_NOT_FOUND: 404,
    ERR_MODEL_DIR_MISSING: 404,
    ERR_MEDIA_BUSY: 409,
    ERR_LOAD_IN_PROGRESS: 409,
    ERR_MODEL_MISMATCH: 409,
    ERR_NO_MODEL_LOADED: 503,
}


@dataclass(frozen=True)
class RouteResult:
    status: int
    body: dict[str, Any] | None = None
    sse: Iterator[dict] | None = None


@dataclass(frozen=True)
class Route:
    method: str
    path: str
    handler: Callable[[dict], RouteResult]


def encode_sse(event: dict) -> bytes:
    """Encode one chat event as a complete SSE data frame."""
    return b"data: " + json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n\n"


def build_routes(service) -> list[Route]:
    return [
        Route("POST", "/api/llm/load", lambda body: _load(service, body)),
        Route("POST", "/api/llm/unload", lambda body: _unload(service)),
        Route("GET", "/api/llm/status", lambda _body: RouteResult(200, service.status())),
        Route("POST", "/api/llm/chat", lambda body: _chat(service, body)),
        Route("POST", "/api/llm/chat/stream", lambda body: _chat_stream(service, body)),
    ]


def _rejected(exc: LlmRejected) -> RouteResult:
    return RouteResult(_REJECTION_STATUS.get(exc.code, 409), {"error": exc.to_dict()})


def _load(service, body: dict) -> RouteResult:
    try:
        state = service.load(str(body.get("key") or ""))
    except LlmRejected as exc:
        return _rejected(exc)
    if state["status"] == "error":
        return RouteResult(500, {"state": state, "error": state["error"]})
    return RouteResult(202, {"state": state})


def _unload(service) -> RouteResult:
    try:
        state = service.unload()
    except LlmRejected as exc:
        return _rejected(exc)
    if state["status"] == "error":
        return RouteResult(500, {"state": state, "error": state["error"]})
    return RouteResult(200, {"state": state})


def _chat(service, body: dict) -> RouteResult:
    try:
        return RouteResult(200, service.chat_completion(body))
    except LlmRejected as exc:
        return _rejected(exc)
    except UpstreamError as exc:
        return RouteResult(502, {"error": {"code": ERR_UPSTREAM_ERROR, "message": exc.message}})


def _chat_stream(service, body: dict) -> RouteResult:
    try:
        events = service.chat_stream(body)
    except LlmRejected as exc:
        return _rejected(exc)
    return RouteResult(200, sse=events)
