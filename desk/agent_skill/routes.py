"""HTTP routes for the agent capability (A-41, A-45). Returns DeskApp-style (method, path, handler(req))."""
from __future__ import annotations

from desk.app import Response
from desk.llm.state import ERR_MODEL_NOT_FOUND, LlmRejected


def _error(status: int, code: str, message: str) -> Response:
    return Response(status, {"error": {"code": code, "message": message}})


def _int(query: dict, name: str):
    try:
        return int(query.get(name, ""))
    except (TypeError, ValueError):
        return None


def build_precheck_routes(llm, media) -> list:
    def precheck(req):
        op = req.query.get("op")
        if op == "chat":
            try:
                return Response(200, llm.precheck_load(req.query.get("model") or ""))
            except LlmRejected as exc:
                return _error(404 if exc.code == ERR_MODEL_NOT_FOUND else 409, exc.code, exc.message)
        if op == "image":
            width, height, steps = _int(req.query, "width"), _int(req.query, "height"), _int(req.query, "steps")
            if None in (width, height, steps):
                return _error(400, "invalid_params", "width/height/steps 须为整数")
            return Response(200, media.precheck_image(width, height, steps))
        return _error(400, "invalid_params", "op 只能是 chat 或 image")

    return [("GET", "/api/agent/precheck", precheck)]
