"""Transport-neutral carriers for library responses."""
from dataclasses import dataclass, field
import json
from pathlib import Path

from .errors import NotFoundError, ValidationError


@dataclass(frozen=True)
class FileSlice:
    """A byte range to stream from a file."""

    path: Path
    start: int
    length: int

    def read(self) -> bytes:
        with open(self.path, "rb") as file:
            file.seek(self.start)
            return file.read(self.length)


@dataclass(frozen=True)
class LibRequest:
    path_params: dict = field(default_factory=dict)
    query: dict = field(default_factory=dict)
    headers: dict = field(default_factory=dict)
    body: bytes = b""


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict
    body: object


def _json_response(status: int, payload) -> Response:
    return Response(
        status,
        {"Content-Type": "application/json"},
        json.dumps(payload, ensure_ascii=False).encode("utf-8"),
    )


def _header(request: LibRequest, name: str) -> str | None:
    for key, value in request.headers.items():
        if key.lower() == name.lower():
            return value
    return None


def handle_list_outputs(service, request: LibRequest) -> Response:
    return _json_response(200, service.list_outputs())


def handle_serve_output(service, request: LibRequest) -> Response:
    return service.serve_output(request.path_params["name"], _header(request, "Range"))


def handle_list_history(service, request: LibRequest) -> Response:
    raw = request.query.get("limit")
    limit = None
    if raw is not None:
        if not str(raw).isdigit():
            raise ValidationError("limit must be a non-negative integer")
        limit = int(raw)
    return _json_response(200, service.list_history(limit))


def dispatch(service, handler, request: LibRequest) -> Response:
    """Map expected library errors; let unexpected failures reach the host."""
    try:
        return handler(service, request)
    except NotFoundError as exc:
        return _json_response(404, {"error": str(exc)})
    except ValidationError as exc:
        return _json_response(400, {"error": str(exc)})


def routes(service) -> list[tuple[str, str, object]]:
    """Return module routes for mounting by the application host."""
    def bind(handler):
        return lambda request: dispatch(service, handler, request)

    return [
        ("GET", "/api/outputs/{name}", bind(handle_serve_output)),
        ("GET", "/api/outputs", bind(handle_list_outputs)),
        ("GET", "/api/history", bind(handle_list_history)),
    ]
