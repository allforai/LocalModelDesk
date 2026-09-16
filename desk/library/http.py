"""Transport-neutral carriers for library responses."""
from dataclasses import dataclass, field
import json
from pathlib import Path

from .errors import LibraryError, NotFoundError, ValidationError


class OutputsRootMissingError(LibraryError):
    """The outputs root does not exist yet — nothing has been generated (issue #12).

    Defined here, not in errors.py: outputs.py already imports from this module, so this direction
    keeps the dependency one-way (errors.py -> http.py -> outputs.py) with no import cycle.
    """

    code = "outputs_root_missing"


class RevealFailedError(LibraryError):
    """The OS opener (`open` / `open -R`) exited non-zero; the reveal did not actually happen."""

    code = "reveal_failed"


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


def _json_body(request: LibRequest) -> dict:
    try:
        payload = json.loads(request.body)
    except (TypeError, ValueError) as exc:
        raise ValidationError("request body must be valid JSON") from exc
    if not isinstance(payload, dict):
        raise ValidationError("request body must be an object")
    return payload


def _header(request: LibRequest, name: str) -> str | None:
    for key, value in request.headers.items():
        if key.lower() == name.lower():
            return value
    return None


def handle_list_outputs(service, request: LibRequest) -> Response:
    return _json_response(200, service.list_outputs())


def handle_serve_output(service, request: LibRequest) -> Response:
    return service.serve_output(request.path_params["name"], _header(request, "Range"))


def handle_reveal_output(service, request: LibRequest) -> Response:
    path = service.outputs.reveal(request.path_params.get("name"))
    return _json_response(200, {"revealed": str(path)})


def handle_reveal_folder(service, request: LibRequest) -> Response:
    return _json_response(200, {"revealed": str(service.outputs.reveal(None))})


def handle_list_history(service, request: LibRequest) -> Response:
    raw = request.query.get("limit")
    limit = None
    if raw is not None:
        if not str(raw).isdigit():
            raise ValidationError("limit must be a non-negative integer")
        limit = int(raw)
    return _json_response(200, service.list_history(limit))


def handle_list_sessions(service, request: LibRequest) -> Response:
    return _json_response(200, service.list_chat_sessions())


def handle_create_session(service, request: LibRequest) -> Response:
    payload = _json_body(request) if request.body else {}
    unknown = set(payload) - {"title", "model"}
    if unknown:
        raise ValidationError(f"unknown keys: {sorted(unknown)}")
    return _json_response(
        200, service.create_chat_session(payload.get("title"), payload.get("model"))
    )


def handle_update_session(service, request: LibRequest) -> Response:
    return _json_response(
        200,
        service.update_chat_session(request.path_params["id"], _json_body(request)),
    )


def handle_delete_session(service, request: LibRequest) -> Response:
    session_id = request.path_params["id"]
    service.delete_chat_session(session_id)
    return _json_response(200, {"deleted": session_id})


def dispatch(service, handler, request: LibRequest) -> Response:
    """Map expected library errors; let unexpected failures reach the host."""
    try:
        return handler(service, request)
    except OutputsRootMissingError as exc:
        return _json_response(404, {"error": {"code": exc.code, "message": str(exc)}})
    except RevealFailedError as exc:
        return _json_response(500, {"error": {"code": exc.code, "message": str(exc)}})
    except NotFoundError as exc:
        return _json_response(404, {"error": str(exc)})
    except ValidationError as exc:
        return _json_response(400, {"error": str(exc)})


def routes(service) -> list[tuple[str, str, object]]:
    """Return module routes for mounting by the application host."""
    def bind(handler):
        return lambda request: dispatch(service, handler, request)

    return [
        ("POST", "/api/outputs/reveal", bind(handle_reveal_folder)),
        ("POST", "/api/outputs/{name}/reveal", bind(handle_reveal_output)),
        ("GET", "/api/outputs/{name}", bind(handle_serve_output)),
        ("GET", "/api/outputs", bind(handle_list_outputs)),
        ("GET", "/api/history", bind(handle_list_history)),
        ("GET", "/api/sessions", bind(handle_list_sessions)),
        ("POST", "/api/sessions", bind(handle_create_session)),
        ("PATCH", "/api/sessions/{id}", bind(handle_update_session)),
        ("DELETE", "/api/sessions/{id}", bind(handle_delete_session)),
    ]
