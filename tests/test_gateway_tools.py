"""Native tool round trips through the real gateway/service, with only mlx faked.

The gateway transports calls; it never executes them. IDs, argument fragments,
usage, failure semantics and desk accounting must survive both directions.
"""
import json

import pytest

from desk.gateway.desk_backend import DeskGatewayBackend
from gateway_client import json_request, serve, sse_request
from gateway_fakes import FakeBackend, IDLE_STATUS
from tests.llm.llm_fakes import make_loaded

TOOLS = [{"type": "function", "function": {
    "name": "read", "description": "Read a file",
    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}, "required": ["path"]},
}}]
CALL = {"id": "call_read", "type": "function", "function": {
    "name": "read", "arguments": '{"path":"a.txt"}',
}}
USAGE = {"prompt_tokens": 13, "completion_tokens": 9, "total_tokens": 22}
RAW = {"choices": [{"message": {"content": None, "tool_calls": [CALL]},
                    "finish_reason": "tool_calls"}], "usage": USAGE}


def decode(frames):
    return [json.loads(frame.removeprefix("data: ").strip())
            for frame in frames if "[DONE]" not in frame]


def test_nonstream_tool_round_trip_keeps_tools_ids_and_results(tmp_path):
    bed = make_loaded(tmp_path, backend_kw={"chat_result": RAW})
    backend = DeskGatewayBackend(bed.service, bed.arbiter)
    with serve(backend) as port:
        status, _, reply = json_request(port, "POST", "/v1/chat/completions", {
            "model": "glm", "messages": [{"role": "user", "content": "Read a.txt"}],
            "tools": TOOLS, "tool_choice": "auto",
        })
        assert status == 200
        choice = reply["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        assert choice["message"]["tool_calls"] == [CALL]
        assert reply["usage"] == USAGE
        payload = next(c[2] for c in bed.calls if c[0] == "chat")
        assert payload["tools"] == TOOLS
        assert payload["model"] == "default_model"  # never resolve/download a second model
        assert bed.service.status()["active_chats"] == 0

        bed.backend.chat_result = {"choices": [{"message": {"content": "Read successfully"},
                                               "finish_reason": "stop"}], "usage": USAGE}
        history = [
            {"role": "user", "content": "Read a.txt"},
            choice["message"],
            {"role": "tool", "tool_call_id": CALL["id"], "name": "read", "content": "第一行"},
        ]
        status, _, final = json_request(port, "POST", "/v1/chat/completions", json.dumps({
            "model": "glm", "tools": TOOLS, "messages": history,
        }, ensure_ascii=False).encode("utf-8"))
        assert status == 200
        assert final["choices"][0]["message"]["content"] == "Read successfully"
        last_payload = [c[2] for c in bed.calls if c[0] == "chat"][-1]
        assert last_payload["messages"][1]["tool_calls"] == [CALL]
        assert last_payload["messages"][2] == history[2]


def test_stream_preserves_parallel_tool_indexes_fragments_and_accounting(tmp_path):
    fragments = [
        [{"index": 0, "id": "a", "type": "function", "function": {"name": "read", "arguments": '{"path":'}}],
        [{"index": 1, "id": "b", "type": "function", "function": {"name": "read", "arguments": '{"path":"b.txt"}'}}],
        [{"index": 0, "function": {"arguments": '"a.txt"}'}}],
    ]
    chunks = [{"choices": [{"delta": {"tool_calls": fragment}}]} for fragment in fragments]
    chunks.append({"choices": [{"delta": {}, "finish_reason": "tool_calls"}], "usage": USAGE})
    bed = make_loaded(tmp_path, backend_kw={"chunks": chunks})
    original = bed.backend.chat_stream

    def counted(port, payload):
        assert bed.service.status()["active_chats"] == 1
        yield from original(port, payload)

    bed.backend.chat_stream = counted
    with serve(DeskGatewayBackend(bed.service, bed.arbiter)) as port:
        status, _, frames = sse_request(port, "/v1/chat/completions", {
            "model": "glm", "stream": True, "tools": TOOLS,
            "messages": [{"role": "user", "content": "Read two files"}],
        })
    assert status == 200
    chunks = decode(frames)
    assert [c["choices"][0]["delta"]["tool_calls"] for c in chunks
            if "tool_calls" in c["choices"][0]["delta"]] == fragments
    assert chunks[-1]["choices"][0]["finish_reason"] == "tool_calls"
    assert chunks[-1]["usage"] == USAGE
    assert frames[-1].strip() == "data: [DONE]"
    assert bed.service.status()["active_chats"] == 0
    assert next(c[2] for c in bed.calls if c[0] == "chat_stream")["tools"] == TOOLS


def test_partial_tool_stream_failure_is_not_success(tmp_path):
    bed = make_loaded(tmp_path, backend_kw={"chunks": [
        {"choices": [{"delta": {"tool_calls": [{"index": 0, **CALL}]}}]},
    ]})  # missing terminal usage/finish => error, not [DONE]
    with serve(DeskGatewayBackend(bed.service, bed.arbiter)) as port:
        status, _, frames = sse_request(port, "/v1/chat/completions", {
            "stream": True, "tools": TOOLS, "messages": [{"role": "user", "content": "Read"}],
        })
    assert status == 200
    assert "[DONE]" not in "".join(frames)
    assert "error" in decode(frames)[-1]
    assert bed.service.status()["active_chats"] == 0


def test_tools_request_never_loads_a_model():
    backend = FakeBackend(llm=IDLE_STATUS)
    with serve(backend) as port:
        status, _, reply = json_request(port, "POST", "/v1/chat/completions", {
            "tools": TOOLS, "messages": [{"role": "user", "content": "Read"}],
        })
    assert status == 503
    assert reply["error"]["code"] == "no_model_loaded"
    backend.assert_no_inference_calls()


@pytest.mark.parametrize("stream", [False, True])
def test_anthropic_unsolicited_tools_fail_explicitly_not_silently(stream):
    backend = FakeBackend(result={"content": "", "tool_calls": [CALL],
                                  "finish_reason": "tool_calls", "usage": USAGE},
                          events=[("tool_calls", [{"index": 0, **CALL}]),
                                  ("finish", {"finish_reason": "tool_calls", "usage": USAGE})])
    body = {"max_tokens": 50, "stream": stream, "messages": [{"role": "user", "content": "Hi"}]}
    with serve(backend) as port:
        if stream:
            status, _, frames = sse_request(port, "/v1/messages", body)
            assert status == 200
            assert '"type": "error"' in "".join(frames)
            assert "message_stop" not in "".join(frames)
        else:
            status, _, reply = json_request(port, "POST", "/v1/messages", body)
            assert status == 502
            assert reply["error"]["type"] == "api_error"
