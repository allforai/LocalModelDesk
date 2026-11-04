"""Pure OpenAI dialect parsing, response construction, and SSE framing."""
from __future__ import annotations

import json
from typing import Iterable, Iterator

from .errors import REASON_INVALID_REQUEST, GatewayReject

DEFAULT_MAX_TOKENS = 2048
# `functions`/`function_call` are the retired pre-tools API. `tools`/`tool_choice` are
# forwarded to mlx-lm, which applies the resident model's own tool template and parses
# the calls it produces; the gateway only normalizes the envelope.
_REJECTED_TOOL_FIELDS = ("functions", "function_call")


def _bad(message: str) -> GatewayReject:
    return GatewayReject(REASON_INVALID_REQUEST, 400, message)


def _parse_tool_calls(index: int, value: object) -> list[dict]:
    if not isinstance(value, list) or not value:
        raise _bad(f"messages[{index}].tool_calls must be a non-empty array")
    parsed = []
    for position, call in enumerate(value):
        where = f"messages[{index}].tool_calls[{position}]"
        function = call.get("function") if isinstance(call, dict) else None
        if (
            not isinstance(function, dict)
            or not isinstance(function.get("name"), str)
            or not function["name"]
        ):
            raise _bad(f"{where}.function needs a string 'name'")
        if call.get("type") != "function":
            raise _bad(f"{where}.type must be 'function'")
        if not isinstance(call.get("id"), str) or not call["id"]:
            raise _bad(f"{where}.id must be a non-empty string")
        arguments = function.get("arguments")
        if not isinstance(arguments, str):
            raise _bad(f"{where}.function.arguments must be a JSON string")
        entry = {"type": "function", "function": {"name": function["name"], "arguments": arguments}}
        entry["id"] = call["id"]
        parsed.append(entry)
    return parsed


def _parse_message(index: int, message: object) -> dict:
    if not isinstance(message, dict) or not isinstance(message.get("role"), str):
        raise _bad(f"messages[{index}] must be an object with a string 'role'")
    role, content, tool_calls = message["role"], message.get("content"), message.get("tool_calls")
    # OpenAI clients (including Pi) can wrap plain text in content blocks.
    # The desk's current chat transport is text-only; never silently drop images.
    if isinstance(content, list):
        if not all(isinstance(block, dict) and block.get("type") == "text"
                   and isinstance(block.get("text"), str) for block in content):
            raise _bad(f"messages[{index}].content supports only text blocks")
        content = "".join(block["text"] for block in content)
    if role == "tool":
        if not isinstance(content, str):
            raise _bad(f"messages[{index}] ('tool') needs a string 'content'")
        call_id = message.get("tool_call_id")
        if not isinstance(call_id, str) or not call_id:
            raise _bad(f"messages[{index}] ('tool') needs a string 'tool_call_id'")
        parsed = {"role": "tool", "content": content, "tool_call_id": call_id}
        if isinstance(message.get("name"), str):
            parsed["name"] = message["name"]
        return parsed
    if tool_calls is not None:
        if role != "assistant":
            raise _bad(f"messages[{index}]: only 'assistant' messages may carry 'tool_calls'")
        if content is not None and not isinstance(content, str):
            raise _bad(f"messages[{index}].content must be a string or null")
        return {
            "role": role,
            "content": content if content is not None else "",
            "tool_calls": _parse_tool_calls(index, tool_calls),
        }
    if not isinstance(content, str):
        raise _bad(f"messages[{index}] must be an object with string 'role' and string 'content'")
    return {"role": role, "content": content}


def _parse_tools(value: object) -> list[dict] | None:
    """Validate the OpenAI tool envelope; descriptors travel to the model unchanged."""
    if value is None:
        return None
    if not isinstance(value, list):
        raise _bad("'tools' must be an array")
    parsed = []
    for position, tool in enumerate(value):
        function = tool.get("function") if isinstance(tool, dict) else None
        if (
            not isinstance(function, dict)
            or not isinstance(function.get("name"), str)
            or not function["name"]
        ):
            raise _bad(
                f"tools[{position}] must be {{'type': 'function', 'function': {{'name': ...}}}}"
            )
        if tool.get("type") != "function":
            raise _bad(f"tools[{position}].type must be 'function'")
        if "description" in function and not isinstance(function["description"], str):
            raise _bad(f"tools[{position}].function.description must be a string")
        if "parameters" in function and not isinstance(function["parameters"], dict):
            raise _bad(f"tools[{position}].function.parameters must be an object")
        if function.get("strict"):
            raise _bad("strict tool schemas are not enforced by this backend")
        parsed.append({"type": "function", "function": dict(function)})
    return parsed


def _parse_tool_choice(value: object) -> object:
    if value is None:
        return None
    # This mlx-lm version only selects tools automatically. Do not silently claim
    # to enforce 'none', 'required', or a forced function when upstream ignores it.
    if value == "auto":
        return value
    raise _bad("only tool_choice='auto' is supported by this backend")


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
    parsed_messages = [_parse_message(index, message) for index, message in enumerate(messages)]
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
            "tools": _parse_tools(body.get("tools")),
            "tool_choice": _parse_tool_choice(body.get("tool_choice")),
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
    if result.get("tool_calls"):
        message["tool_calls"] = result["tool_calls"]
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


def _chunk(completion_id: str, created: int, model: str, delta: dict,
           finish_reason: str | None = None, usage: dict | None = None) -> bytes:
    chunk = {
        "id": completion_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [{"index": 0, "delta": delta, "finish_reason": finish_reason}],
    }
    if usage is not None:
        chunk["usage"] = {
            "prompt_tokens": usage["prompt_tokens"],
            "completion_tokens": usage["completion_tokens"],
            "total_tokens": usage["prompt_tokens"] + usage["completion_tokens"],
        }
    return _frame(chunk)


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
            elif kind == "tool_calls":
                yield _chunk(completion_id, created, model, {"tool_calls": payload})
            elif kind == "finish":
                yield _chunk(completion_id, created, model, {},
                             finish_reason=payload["finish_reason"], usage=payload.get("usage"))
                yield b"data: [DONE]\n\n"
                return
    except Exception as exc:  # noqa: BLE001
        yield _error_frame(str(exc))
        return
    yield _error_frame("upstream stream ended without a finish event")
