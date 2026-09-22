"""Anthropic dialect parsing, responses, and streaming events."""
import json

import pytest

from desk.gateway import anthropic_dialect
from desk.gateway.errors import REASON_HEADER, REASON_INVALID_REQUEST, GatewayReject
from gateway_client import json_request, serve, sse_request
from gateway_fakes import EVENTS as BACKEND_EVENTS, IDLE_STATUS, FakeBackend

RESULT = {"content": "你好！", "reasoning": "用户在打招呼。",
          "finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}}
BASE = {"max_tokens": 100, "messages": [{"role": "user", "content": "hi"}]}


def _reject(body) -> GatewayReject:
    with pytest.raises(GatewayReject) as exc_info:
        anthropic_dialect.parse_request(body)
    return exc_info.value


def test_parse_minimal():
    parsed = anthropic_dialect.parse_request(dict(BASE))
    assert parsed == {
        "model": None,
        "stream": False,
        "chat_request": {"messages": [{"role": "user", "content": "hi"}],
                         "max_tokens": 100, "temperature": None, "top_p": None},
    }


def test_parse_max_tokens_required():
    rejected = _reject({"messages": [{"role": "user", "content": "hi"}]})
    assert (rejected.code, rejected.http) == (REASON_INVALID_REQUEST, 400)
    assert _reject({**BASE, "max_tokens": "100"}).http == 400
    assert _reject({**BASE, "max_tokens": 0}).http == 400


def test_parse_system_string_prepended():
    parsed = anthropic_dialect.parse_request({**BASE, "system": "你是台面助手"})
    assert parsed["chat_request"]["messages"][:2] == [
        {"role": "system", "content": "你是台面助手"}, {"role": "user", "content": "hi"}]


def test_parse_system_block_array_concatenated():
    parsed = anthropic_dialect.parse_request({
        **BASE, "system": [{"type": "text", "text": "你是"}, {"type": "text", "text": "台面助手"}]})
    assert parsed["chat_request"]["messages"][0] == {"role": "system", "content": "你是台面助手"}


def test_parse_multiturn_order_preserved_with_block_content():
    parsed = anthropic_dialect.parse_request({
        "max_tokens": 50, "system": "s",
        "messages": [
            {"role": "user", "content": "第一轮"},
            {"role": "assistant", "content": [{"type": "text", "text": "回"}, {"type": "text", "text": "答"}]},
            {"role": "user", "content": "第二轮"},
        ],
    })
    assert [(message["role"], message["content"]) for message in parsed["chat_request"]["messages"]] == [
        ("system", "s"), ("user", "第一轮"), ("assistant", "回答"), ("user", "第二轮")]


def test_parse_non_text_block_rejected():
    rejected = _reject({**BASE, "messages": [{"role": "user", "content": [{"type": "image", "source": {}}]}]})
    assert rejected.http == 400


def test_parse_stream_must_be_boolean_and_tools_rejected():
    assert _reject({**BASE, "stream": "yes"}).http == 400
    assert _reject({**BASE, "tools": [{"name": "t"}]}).http == 400
    assert _reject({**BASE, "tool_choice": {"type": "auto"}}).http == 400
    assert anthropic_dialect.parse_request({**BASE, "metadata": {"user_id": "x"}, "top_k": 5})["stream"] is False


def test_message_response_shape():
    assert anthropic_dialect.message_response(RESULT, "qwen3-30b", "msg_fixed") == {
        "id": "msg_fixed", "type": "message", "role": "assistant", "model": "qwen3-30b",
        "content": [{"type": "thinking", "thinking": "用户在打招呼。"}, {"type": "text", "text": "你好！"}],
        "stop_reason": "end_turn", "stop_sequence": None,
        "usage": {"input_tokens": 12, "output_tokens": 7},
    }


def test_message_response_length_maps_to_max_tokens():
    assert anthropic_dialect.message_response({**RESULT, "finish_reason": "length"}, "m", "msg_1")["stop_reason"] == "max_tokens"


def test_message_response_no_thinking_block_when_reasoning_empty():
    assert anthropic_dialect.message_response({**RESULT, "reasoning": ""}, "m", "msg_1")["content"] == [{"type": "text", "text": "你好！"}]


EVENTS = [("reasoning", "用户在"), ("reasoning", "打招呼。"), ("content", "你"), ("content", "好！"),
          ("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}})]


def _decode_frames(frames):
    """Assert each SSE frame has exactly an event and data line."""
    out = []
    for frame in frames:
        text = frame.decode("utf-8")
        assert text.endswith("\n\n")
        lines = text[:-2].split("\n")
        assert len(lines) == 2, f"each event must have exactly two lines: {lines!r}"
        assert lines[0].startswith("event: ") and lines[1].startswith("data: ")
        out.append((lines[0][len("event: "):], json.loads(lines[1][len("data: "):])))
    return out


def test_stream_events_full_sequence():
    decoded = _decode_frames(anthropic_dialect.stream_events(iter(EVENTS), "msg_fixed", "qwen3-30b"))
    assert [name for name, _ in decoded] == [
        "message_start",
        "content_block_start", "content_block_delta", "content_block_delta", "content_block_stop",
        "content_block_start", "content_block_delta", "content_block_delta", "content_block_stop",
        "message_delta", "message_stop",
    ]
    start = decoded[0][1]
    assert start["type"] == "message_start"
    assert start["message"]["id"] == "msg_fixed"
    assert start["message"]["model"] == "qwen3-30b"
    assert start["message"]["content"] == []
    assert start["message"]["usage"] == {"input_tokens": 0, "output_tokens": 0}
    assert decoded[1][1] == {"type": "content_block_start", "index": 0,
                             "content_block": {"type": "thinking", "thinking": ""}}
    assert decoded[2][1] == {"type": "content_block_delta", "index": 0,
                             "delta": {"type": "thinking_delta", "thinking": "用户在"}}
    assert decoded[4][1] == {"type": "content_block_stop", "index": 0}
    assert decoded[5][1] == {"type": "content_block_start", "index": 1,
                             "content_block": {"type": "text", "text": ""}}
    assert decoded[6][1] == {"type": "content_block_delta", "index": 1,
                             "delta": {"type": "text_delta", "text": "你"}}
    assert decoded[8][1] == {"type": "content_block_stop", "index": 1}
    assert decoded[9][1] == {"type": "message_delta",
                             "delta": {"stop_reason": "end_turn", "stop_sequence": None},
                             "usage": {"input_tokens": 12, "output_tokens": 7}}
    assert decoded[10][1] == {"type": "message_stop"}


def test_stream_events_edge_cases_and_errors():
    content_only = _decode_frames(anthropic_dialect.stream_events(iter([
        ("content", "hi"), ("finish", {"finish_reason": "length", "usage": {"prompt_tokens": 1, "completion_tokens": 2}}),
    ]), "msg_1", "m"))
    assert [name for name, _ in content_only] == ["message_start", "content_block_start", "content_block_delta", "content_block_stop", "message_delta", "message_stop"]
    assert content_only[1][1]["index"] == 0
    assert content_only[4][1]["delta"]["stop_reason"] == "max_tokens"

    interleaved = _decode_frames(anthropic_dialect.stream_events(iter([
        ("content", "a"), ("reasoning", "r"), ("content", "b"),
        ("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 1, "completion_tokens": 1}}),
    ]), "msg_1", "m"))
    assert [(data["index"], data["content_block"]["type"]) for name, data in interleaved if name == "content_block_start"] == [(0, "text"), (1, "thinking"), (2, "text")]

    empty = _decode_frames(anthropic_dialect.stream_events(iter([
        ("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 1, "completion_tokens": 0}}),
    ]), "msg_1", "m"))
    assert [name for name, _ in empty] == ["message_start", "content_block_start", "content_block_stop", "message_delta", "message_stop"]
    assert empty[1][1]["content_block"] == {"type": "text", "text": ""}

    def failing_events():
        yield ("content", "部分")
        raise RuntimeError("mlx-lm died")

    midway = _decode_frames(anthropic_dialect.stream_events(failing_events(), "msg_1", "m"))
    missing_finish = _decode_frames(anthropic_dialect.stream_events(iter([("content", "x")]), "msg_1", "m"))
    assert "message_stop" not in [name for name, _ in midway]
    assert midway[-1] == ("error", {"type": "error", "error": {"type": "api_error", "message": "mlx-lm died"}})
    assert missing_finish[-1][0] == "error"
    assert "message_stop" not in [name for name, _ in missing_finish]


def test_http_messages_full_paths_503_envelope_and_stream_errors():
    body = {**BASE, "model": "qwen3-30b"}
    backend = FakeBackend()
    with serve(backend) as port:
        status, _, payload = json_request(port, "POST", "/v1/messages", body=body)
    assert status == 200
    assert payload == anthropic_dialect.message_response(
        RESULT, "qwen3-30b", "msg_fixedfixedfixedfixedfixedfixed00"
    )
    assert backend.calls[-1] == ("chat_completion", {
        "messages": [{"role": "user", "content": "hi"}],
        "max_tokens": 100, "temperature": None, "top_p": None,
    })

    streaming = FakeBackend(events=BACKEND_EVENTS)
    with serve(streaming) as port:
        status, headers, frames = sse_request(port, "/v1/messages", {**body, "stream": True})
    assert status == 200
    assert headers["content-type"] == "text/event-stream; charset=utf-8"
    decoded = _decode_frames(iter(frame.encode("utf-8") for frame in frames))
    assert [name for name, _ in decoded][-2:] == ["message_delta", "message_stop"]
    assert decoded[0][1]["message"]["id"] == "msg_fixedfixedfixedfixedfixedfixed00"
    assert streaming.called_methods() == ["llm_status", "desk_state", "chat_stream"]

    rejected = FakeBackend(llm=IDLE_STATUS)
    with serve(rejected) as port:
        status, headers, payload = json_request(port, "POST", "/v1/messages", body=body)
    assert status == 503
    assert headers[REASON_HEADER.lower()] == "no_model_loaded"
    assert headers["retry-after"] == "30"
    assert payload == {
        "type": "error",
        "error": {
            "type": "overloaded_error",
            "message": "no chat model is loaded; the gateway never auto-loads",
        },
    }
    rejected.assert_no_inference_calls()

    broken = FakeBackend(events=[("content", "partial")], stream_error=RuntimeError("mlx-lm died"))
    with serve(broken) as port:
        status, _, frames = sse_request(port, "/v1/messages", {**body, "stream": True})
    assert status == 200
    decoded = _decode_frames(iter(frame.encode("utf-8") for frame in frames))
    assert decoded[-1] == ("error", {
        "type": "error", "error": {"type": "api_error", "message": "mlx-lm died"},
    })
    assert "message_stop" not in [name for name, _ in decoded]
