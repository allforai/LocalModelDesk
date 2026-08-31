"""Pure OpenAI dialect parsing, response construction, and SSE framing."""
from __future__ import annotations

import json
from typing import Iterable, Iterator

from .errors import REASON_INVALID_REQUEST, GatewayReject

DEFAULT_MAX_TOKENS = 2048
_REJECTED_TOOL_FIELDS = ("tools", "tool_choice", "functions")


def _bad(message: str) -> GatewayReject:
    return GatewayReject(REASON_INVALID_REQUEST, 400, message)


def parse_request(body: object) -> dict:
    """Validate an OpenAI request and return its internal representation."""
    if not isinstance(body, dict):
        raise _bad("request body must be a JSON object")
    stream = body.get("stream", False)
    if not isinstance(stream, bool):
        raise _bad("'stream' must be a boolean")
    for field in _REJECTED_TOOL_FIELDS:
        if body.get(field):
            raise _bad(f"'{field}' is not supported by this gateway")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise _bad("'messages' must be a non-empty array")
    parsed_messages = []
    for index, message in enumerate(messages):
        if (
            not isinstance(message, dict)
            or not isinstance(message.get("role"), str)
            or not isinstance(message.get("content"), str)
        ):
            raise _bad(f"messages[{index}] must be an object with string 'role' and string 'content'")
        parsed_messages.append({"role": message["role"], "content": message["content"]})
    max_tokens = body.get("max_tokens", DEFAULT_MAX_TOKENS)
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
        raise _bad("'max_tokens' must be a positive integer")
    model = body.get("model")
    if model is not None and not isinstance(model, str):
        raise _bad("'model' must be a string")
    return {
        "model": model or None,
        "stream": stream,
        "chat_request": {
            "messages": parsed_messages,
            "max_tokens": max_tokens,
            "temperature": body.get("temperature"),
            "top_p": body.get("top_p"),
        },
    }


def models_list(llm_status: dict) -> dict:
    """Construct a /v1/models payload from the injected LLM status."""
    loaded = llm_status.get("loaded")
    if llm_status.get("state") != "loaded" or not loaded:
        return {"object": "list", "data": []}
    created = int(loaded["loaded_at"])
    identifiers = [loaded["key"]]
    if loaded["served_id"] != loaded["key"]:
        identifiers.append(loaded["served_id"])
    return {
        "object": "list",
        "data": [
            {"id": identifier, "object": "model", "created": created, "owned_by": "localmodeldesk"}
            for identifier in identifiers
        ],
    }


def completion_response(result: dict, model: str, completion_id: str, created: int) -> dict:
    """Construct a non-streaming OpenAI chat completion response."""
    message = {"role": "assistant", "content": result["content"]}
    if result.get("reasoning"):
        message["reasoning_content"] = result["reasoning"]
    usage = result["usage"]
    return {
        "id": completion_id,
        "object": "chat.completion",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "message": message, "finish_reason": result["finish_reason"]}],
        "usage": {
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "total_tokens": usage["prompt_tokens"] + usage["completion_tokens"],
        },
    }


def _frame(payload: dict) -> bytes:
    return b"data: " + json.dumps(payload, ensure_ascii=False).encode("utf-8") + b"\n\n"


def _chunk(completion_id: str, created: int, model: str, delta: dict, finish_reason: str | None = None) -> bytes:
    return _frame({
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    })


def _error_frame(message: str) -> bytes:
    return _frame({"error": {"message": message, "type": "api_error"}})


def stream_chunks(events: Iterable[tuple], completion_id: str, created: int, model: str) -> Iterator[bytes]:
    """Translate backend events into OpenAI SSE frames.

    A backend exception or a missing finish event emits an error frame without the
    terminal ``[DONE]`` marker, so an incomplete stream cannot look successful.
    """
    yield _chunk(completion_id, created, model, {"role": "assistant"})
    try:
        for kind, payload in events:
            if kind == "content":
                yield _chunk(completion_id, created, model, {"content": payload})
            elif kind == "reasoning":
                yield _chunk(completion_id, created, model, {"reasoning_content": payload})
            elif kind == "finish":
                yield _chunk(completion_id, created, model, {}, finish_reason=payload["finish_reason"])
                yield b"data: [DONE]\n\n"
                return
    except Exception as exc:  # noqa: BLE001
        yield _error_frame(str(exc))
        return
    yield _error_frame("upstream stream ended without a finish event")
