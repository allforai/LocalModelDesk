"""OpenAI dialect parsing, response construction, and SSE chunks."""
import json

import pytest

from desk.gateway import openai_dialect
from desk.gateway.errors import REASON_HEADER, REASON_INVALID_REQUEST, GatewayReject
from gateway_client import json_request, serve, sse_request
from gateway_fakes import IDLE_STATUS, FakeBackend

LOADED = {
    "state": "loaded",
    "loaded": {
        "key": "qwen3-30b",
        "served_id": "mlx-community/Qwen3-30B-A3B-8bit",
        "loaded_at": 1756600000.0,
        "meta": {},
    },
}
RESULT = {
    "content": "你好！",
    "reasoning": "用户在打招呼。",
    "finish_reason": "stop",
    "usage": {"prompt_tokens": 12, "completion_tokens": 7},
}
EVENTS = [
    ("reasoning", "用户在"),
    ("reasoning", "打招呼。"),
    ("content", "你"),
    ("content", "好！"),
    ("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}}),
]


def _reject(body) -> GatewayReject:
    with pytest.raises(GatewayReject) as exc_info:
        openai_dialect.parse_request(body)
    return exc_info.value


def test_parse_minimal_defaults():
    parsed = openai_dialect.parse_request({"messages": [{"role": "user", "content": "hi"}]})
    assert parsed == {
        "model": None,
        "stream": False,
        "chat_request": {
            "messages": [{"role": "user", "content": "hi"}],
            "max_tokens": 2048,
            "temperature": None,
            "top_p": None,
        },
    }


def test_parse_full_fields_passthrough():
    parsed = openai_dialect.parse_request({
        "model": "qwen3-30b", "stream": True, "max_tokens": 64,
        "temperature": 0.2, "top_p": 0.9,
        "messages": [{"role": "system", "content": "s"}, {"role": "user", "content": "u"}],
        "metadata": {"ignored": True},
    })
    assert parsed["model"] == "qwen3-30b"
    assert parsed["stream"] is True
    assert parsed["chat_request"]["max_tokens"] == 64
    assert parsed["chat_request"]["temperature"] == 0.2
    assert parsed["chat_request"]["top_p"] == 0.9
    assert [message["role"] for message in parsed["chat_request"]["messages"]] == ["system", "user"]


def test_parse_rejects_invalid_requests_and_tools():
    body = {"messages": [{"role": "user", "content": "hi"}]}
    assert (_reject({"stream": "yes", **body}).code, _reject({"stream": "yes", **body}).http) == (
        REASON_INVALID_REQUEST, 400
    )
    for invalid in ({}, {"messages": "not a list"}, {"messages": []}, {"messages": [{"role": "user"}]}):
        assert _reject(invalid).http == 400
    for field, value in (("tools", [{"type": "function"}]), ("tool_choice", "auto"), ("functions", [{}])):
        assert _reject({**body, field: value}).http == 400
    assert openai_dialect.parse_request({**body, "tools": []})["stream"] is False


def test_models_list_handles_unloaded_two_ids_and_duplicates():
    assert openai_dialect.models_list({"state": "idle", "loaded": None}) == {"object": "list", "data": []}
    assert openai_dialect.models_list(LOADED)["data"] == [
        {"id": "qwen3-30b", "object": "model", "created": 1756600000, "owned_by": "localmodeldesk"},
        {"id": "mlx-community/Qwen3-30B-A3B-8bit", "object": "model", "created": 1756600000, "owned_by": "localmodeldesk"},
    ]
    same = {"state": "loaded", "loaded": {"key": "same", "served_id": "same", "loaded_at": 5.0}}
    assert [item["id"] for item in openai_dialect.models_list(same)["data"]] == ["same"]


def test_completion_response_shape_reasoning_and_length():
    response = openai_dialect.completion_response(RESULT, "qwen3-30b", "chatcmpl-fixed", 1756605000)
    assert response == {
        "id": "chatcmpl-fixed", "object": "chat.completion", "created": 1756605000, "model": "qwen3-30b",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "你好！", "reasoning_content": "用户在打招呼。"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19},
    }
    no_reasoning = openai_dialect.completion_response({**RESULT, "reasoning": ""}, "m", "id", 1)
    assert "reasoning_content" not in no_reasoning["choices"][0]["message"]
    assert openai_dialect.completion_response({**RESULT, "finish_reason": "length"}, "m", "id", 1)["choices"][0]["finish_reason"] == "length"


def _decode(frames):
    decoded = []
    for frame in frames:
        line = frame.decode("utf-8")
        assert line.startswith("data: ") and line.endswith("\n\n")
        payload = line[len("data: "):-2]
        decoded.append(payload if payload == "[DONE]" else json.loads(payload))
    return decoded


def test_stream_chunks_full_replay():
    decoded = _decode(openai_dialect.stream_chunks(iter(EVENTS), "chatcmpl-fixed", 1756605000, "qwen3-30b"))
    assert decoded[-1] == "[DONE]"
    chunks = decoded[:-1]
    assert all((chunk["id"], chunk["object"], chunk["created"], chunk["model"]) == (
        "chatcmpl-fixed", "chat.completion.chunk", 1756605000, "qwen3-30b") for chunk in chunks)
    assert [chunk["choices"][0]["delta"] for chunk in chunks] == [
        {"role": "assistant"}, {"reasoning_content": "用户在"}, {"reasoning_content": "打招呼。"},
        {"content": "你"}, {"content": "好！"}, {},
    ]
    assert [chunk["choices"][0]["finish_reason"] for chunk in chunks] == [None, None, None, None, None, "stop"]


def test_stream_chunks_errors_are_not_done():
    def failing_events():
        yield ("content", "部分")
        raise RuntimeError("mlx-lm died")

    midway = _decode(openai_dialect.stream_chunks(failing_events(), "id", 1, "m"))
    missing_finish = _decode(openai_dialect.stream_chunks(iter([("content", "x")]), "id", 1, "m"))
    assert "[DONE]" not in midway
    assert midway[-1] == {"error": {"message": "mlx-lm died", "type": "api_error"}}
    assert "[DONE]" not in missing_finish
    assert missing_finish[-1]["error"]["type"] == "api_error"


def test_http_models_empty_when_idle():
    with serve(FakeBackend(llm=IDLE_STATUS)) as port:
        status, _, payload = json_request(port, "GET", "/v1/models")
    assert status == 200
    assert payload == {"object": "list", "data": []}


def test_http_models_lists_loaded_identifiers():
    with serve(FakeBackend()) as port:
        status, _, payload = json_request(port, "GET", "/v1/models")
    assert status == 200
    assert [model["id"] for model in payload["data"]] == ["qwen3-30b", "mlx-community/Qwen3-30B-A3B-8bit"]
    for model in payload["data"]:
        assert model["object"] == "model"
        assert model["created"] == 1756600000
        assert model["owned_by"] == "localmodeldesk"


def test_http_unknown_path_404_openai_envelope():
    with serve(FakeBackend()) as port:
        status, headers, payload = json_request(port, "GET", "/no/such/path")
    assert status == 404
    assert payload["error"]["type"] == "invalid_request_error"
    assert headers[REASON_HEADER.lower()] == "not_found"


def test_http_unknown_path_under_messages_gets_anthropic_envelope():
    with serve(FakeBackend()) as port:
        status, _, payload = json_request(port, "GET", "/v1/messages/count_tokens")
    assert status == 404
    assert payload == {"type": "error", "error": {"type": "not_found_error", "message": "unknown path: /v1/messages/count_tokens"}}


def test_http_method_not_allowed():
    with serve(FakeBackend()) as port:
        first, _, first_payload = json_request(port, "POST", "/v1/models", body={})
        second, _, _ = json_request(port, "GET", "/v1/chat/completions")
    assert (first, second) == (405, 405)
    assert first_payload["error"]["code"] == "method_not_allowed"


def test_http_oversized_body_400():
    with serve(FakeBackend()) as port:
        big = b'{"messages": "' + b"x" * (10 * 1024 * 1024) + b'"}'
        status, _, payload = json_request(port, "POST", "/v1/chat/completions", body=big)
    assert status == 400
    assert payload["error"]["code"] == "invalid_request"


def test_http_chat_completions_full_paths_and_never_loads():
    body = {"messages": [{"role": "user", "content": "hi"}]}
    backend = FakeBackend()
    with serve(backend) as port:
        status, _, payload = json_request(port, "POST", "/v1/chat/completions", body=body)
    assert status == 200
    assert payload == {
        "id": "chatcmpl-fixedfixedfixedfixedfixedfixed00",
        "object": "chat.completion",
        "created": 1756605000,
        "model": "mlx-community/Qwen3-30B-A3B-8bit",
        "choices": [{"index": 0, "message": {
            "role": "assistant", "content": "你好！", "reasoning_content": "用户在打招呼。"
        }, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 12, "completion_tokens": 7, "total_tokens": 19},
    }
    assert backend.called_methods() == ["llm_status", "desk_state", "chat_completion"]

    backend = FakeBackend(events=EVENTS)
    with serve(backend) as port:
        status, headers, frames = sse_request(port, "/v1/chat/completions", {**body, "stream": True})
    assert status == 200
    assert headers["content-type"] == "text/event-stream; charset=utf-8"
    assert frames[-1] == "data: [DONE]\n\n"
    chunks = [json.loads(frame[6:-2]) for frame in frames[:-1]]
    assert [chunk["choices"][0]["delta"] for chunk in chunks] == [
        {"role": "assistant"}, {"reasoning_content": "用户在"},
        {"reasoning_content": "打招呼。"}, {"content": "你"},
        {"content": "好！"}, {},
    ]
    assert backend.called_methods() == ["llm_status", "desk_state", "chat_stream"]

    rejected = FakeBackend(llm=IDLE_STATUS)
    with serve(rejected) as port:
        status, headers, payload = json_request(port, "POST", "/v1/chat/completions", body=body)
    assert status == 503
    assert headers[REASON_HEADER.lower()] == "no_model_loaded"
    assert headers["retry-after"] == "30"
    assert payload["error"] == {
        "type": "service_unavailable_error",
        "code": "no_model_loaded",
        "message": "no chat model is loaded; the gateway never auto-loads",
    }
    rejected.assert_no_inference_calls()

    invalid = FakeBackend()
    with serve(invalid) as port:
        status, headers, payload = json_request(port, "POST", "/v1/chat/completions", body={})
    assert status == 400
    assert headers[REASON_HEADER.lower()] == "invalid_request"
    assert payload["error"]["type"] == "invalid_request_error"
    assert invalid.calls == []

    failed = FakeBackend(completion_error=RuntimeError("mlx-lm died"))
    with serve(failed) as port:
        status, headers, payload = json_request(port, "POST", "/v1/chat/completions", body=body)
    assert status == 500
    assert headers[REASON_HEADER.lower()] == "upstream_error"
    assert payload["error"] == {
        "type": "api_error", "code": "upstream_error", "message": "chat backend failed: mlx-lm died"
    }


def test_http_chat_stream_setup_error_uses_openai_envelope():
    class BrokenStreamBackend(FakeBackend):
        def chat_stream(self, req):
            self.calls.append(("chat_stream", req))
            raise RuntimeError("stream could not start")

    with serve(BrokenStreamBackend()) as port:
        status, headers, payload = json_request(
            port, "POST", "/v1/chat/completions",
            body={"stream": True, "messages": [{"role": "user", "content": "hi"}]},
        )
    assert status == 500
    assert headers[REASON_HEADER.lower()] == "upstream_error"
    assert payload["error"] == {
        "type": "api_error", "code": "upstream_error", "message": "chat backend failed: stream could not start"
    }
