"""Anthropic dialect parsing and non-streaming responses."""
import pytest

from desk.gateway import anthropic_dialect
from desk.gateway.errors import REASON_INVALID_REQUEST, GatewayReject

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
