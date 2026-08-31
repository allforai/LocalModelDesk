"""Anthropic request/response translation without IO or clock access."""
from __future__ import annotations

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
