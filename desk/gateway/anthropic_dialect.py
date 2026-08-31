"""Anthropic request/response translation without IO or clock access."""
from __future__ import annotations

import json
from typing import Iterable, Iterator

from .errors import REASON_INVALID_REQUEST, GatewayReject

_REJECTED_TOOL_FIELDS = ("tools", "tool_choice")
_STOP_REASON = {"stop": "end_turn", "length": "max_tokens"}


def _bad(message: str) -> GatewayReject:
    return GatewayReject(REASON_INVALID_REQUEST, 400, message)


def _text_from_blocks(blocks, where: str) -> str:
    parts = []
    for index, block in enumerate(blocks):
        if (not isinstance(block, dict) or block.get("type") != "text"
                or not isinstance(block.get("text"), str)):
            raise _bad(f"{where}[{index}]: only 'text' content blocks are supported")
        parts.append(block["text"])
    return "".join(parts)


def parse_request(body) -> dict:
    """Convert an Anthropic request to the backend chat request shape."""
    if not isinstance(body, dict):
        raise _bad("request body must be a JSON object")
    stream = body.get("stream", False)
    if not isinstance(stream, bool):
        raise _bad("'stream' must be a boolean")
    for field in _REJECTED_TOOL_FIELDS:
        if body.get(field):
            raise _bad(f"'{field}' is not supported by this gateway")
    max_tokens = body.get("max_tokens")
    if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or max_tokens < 1:
        raise _bad("'max_tokens' is required and must be a positive integer")
    messages = body.get("messages")
    if not isinstance(messages, list) or not messages:
        raise _bad("'messages' must be a non-empty array")

    parsed = []
    system = body.get("system")
    if system is not None:
        if isinstance(system, str):
            system_text = system
        elif isinstance(system, list):
            system_text = _text_from_blocks(system, "system")
        else:
            raise _bad("'system' must be a string or an array of text blocks")
        parsed.append({"role": "system", "content": system_text})

    for index, message in enumerate(messages):
        if not isinstance(message, dict) or not isinstance(message.get("role"), str):
            raise _bad(f"messages[{index}] must be an object with a string 'role'")
        content = message.get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = _text_from_blocks(content, f"messages[{index}].content")
        else:
            raise _bad(f"messages[{index}].content must be a string or an array of content blocks")
        parsed.append({"role": message["role"], "content": text})

    model = body.get("model")
    if model is not None and not isinstance(model, str):
        raise _bad("'model' must be a string")
    return {
        "model": model or None,
        "stream": stream,
        "chat_request": {
            "messages": parsed,
            "max_tokens": max_tokens,
            "temperature": body.get("temperature"),
            "top_p": body.get("top_p"),
        },
    }


def message_response(result: dict, model: str, message_id: str) -> dict:
    """Convert a completed backend result to an Anthropic message response."""
    content = []
    if result.get("reasoning"):
        content.append({"type": "thinking", "thinking": result["reasoning"]})
    content.append({"type": "text", "text": result["content"]})
    usage = result["usage"]
    return {
        "id": message_id,
        "type": "message",
        "role": "assistant",
        "model": model,
        "content": content,
        "stop_reason": _STOP_REASON[result["finish_reason"]],
        "stop_sequence": None,
        "usage": {"input_tokens": usage["prompt_tokens"], "output_tokens": usage["completion_tokens"]},
    }


def _frame(name: str, data: dict) -> bytes:
    """Return an Anthropic SSE event with exactly event and data lines."""
    return f"event: {name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


_DELTA_BY_TYPE = {"thinking": ("thinking_delta", "thinking"), "text": ("text_delta", "text")}


def stream_events(events: Iterable[tuple], message_id: str, model: str) -> Iterator[bytes]:
    """Translate backend events into Anthropic SSE events.

    Switching content-block types closes the existing block before opening the
    next.  An upstream error or stream without a finish event emits ``error``
    and never ``message_stop``.
    """
    yield _frame("message_start", {
        "type": "message_start",
        "message": {"id": message_id, "type": "message", "role": "assistant", "model": model,
                    "content": [], "stop_reason": None,
                    "usage": {"input_tokens": 0, "output_tokens": 0}},
    })
    index = -1
    open_type = None
    text_emitted = False

    def start(block_type: str) -> bytes:
        block = {"type": "thinking", "thinking": ""} if block_type == "thinking" else {"type": "text", "text": ""}
        return _frame("content_block_start", {
            "type": "content_block_start", "index": index, "content_block": block,
        })

    def stop() -> bytes:
        return _frame("content_block_stop", {"type": "content_block_stop", "index": index})

    try:
        for kind, payload in events:
            if kind == "finish":
                if open_type is not None:
                    yield stop()
                    open_type = None
                if not text_emitted:
                    index += 1
                    yield start("text")
                    yield stop()
                usage = payload["usage"]
                yield _frame("message_delta", {
                    "type": "message_delta",
                    "delta": {"stop_reason": _STOP_REASON[payload["finish_reason"]], "stop_sequence": None},
                    "usage": {"input_tokens": usage["prompt_tokens"], "output_tokens": usage["completion_tokens"]},
                })
                yield _frame("message_stop", {"type": "message_stop"})
                return

            block_type = "thinking" if kind == "reasoning" else "text"
            if open_type != block_type:
                if open_type is not None:
                    yield stop()
                index += 1
                yield start(block_type)
                open_type = block_type
                text_emitted = text_emitted or block_type == "text"
            delta_type, key = _DELTA_BY_TYPE[block_type]
            yield _frame("content_block_delta", {
                "type": "content_block_delta", "index": index,
                "delta": {"type": delta_type, key: payload},
            })
    except Exception as exc:  # noqa: BLE001
        yield _frame("error", {"type": "error", "error": {"type": "api_error", "message": str(exc)}})
        return
    yield _frame("error", {
        "type": "error",
        "error": {"type": "api_error", "message": "upstream stream ended without a finish event"},
    })
