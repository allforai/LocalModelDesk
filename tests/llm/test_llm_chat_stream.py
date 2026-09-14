"""Streaming chat events preserve separate deltas and terminal semantics."""
import pytest

from desk.llm.state import LlmRejected
from tests.llm.llm_fakes import make_loaded, make_service


CONTENT_CHUNKS = [
    {"choices": [{"delta": {"content": "你"}}]},
    {"choices": [{"delta": {"content": "好"}}]},
    {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"total_tokens": 3}},
]

REASONING_CHUNKS = [
    {"choices": [{"delta": {"reasoning_content": "先想"}}]},
    {"choices": [{"delta": {"reasoning": "再想"}}]},
    {"choices": [{"delta": {"content": "答", "reasoning_content": "同拍"}}]},
    {"choices": [{"delta": {}, "finish_reason": "stop"}], "usage": {"total_tokens": 5}},
]


def test_stream_content_deltas_then_done_with_usage(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chunks": CONTENT_CHUNKS})

    events = list(testbed.service.chat_stream({"messages": []}))

    assert events == [
        {"type": "delta", "text": "你", "reasoning": None},
        {"type": "delta", "text": "好", "reasoning": None},
        {"type": "done", "usage": {"total_tokens": 3}, "finish_reason": "stop"},
    ]
    _, _, payload = next(call for call in testbed.calls if call[0] == "chat_stream")
    assert payload["model"] == "default_model"
    assert payload["stream_options"] == {"include_usage": True}


def test_stream_reasoning_stays_separate_from_content(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chunks": REASONING_CHUNKS})

    events = list(testbed.service.chat_stream({"messages": []}))

    assert events[:3] == [
        {"type": "delta", "text": None, "reasoning": "先想"},
        {"type": "delta", "text": None, "reasoning": "再想"},
        {"type": "delta", "text": "答", "reasoning": "同拍"},
    ]
    assert events[3]["type"] == "done"


def test_stream_upstream_interruption_yields_error_without_done(tmp_path):
    testbed = make_loaded(
        tmp_path, backend_kw={"chunks": CONTENT_CHUNKS[:2], "stream_error_after": 1}
    )

    events = list(testbed.service.chat_stream({"messages": []}))

    assert events[-1] == {
        "type": "error", "code": "upstream_error", "message": "fake upstream stream interrupted",
    }
    assert not any(event["type"] == "done" for event in events)


def test_stream_missing_usage_or_finish_yields_error_not_done(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chunks": CONTENT_CHUNKS[:2]})

    events = list(testbed.service.chat_stream({"messages": []}))

    assert events[-1]["type"] == "error"
    assert events[-1]["code"] == "upstream_error"
    assert not any(event["type"] == "done" for event in events)


def test_stream_prechecks_raise_before_iteration(tmp_path):
    testbed = make_service(tmp_path)

    with pytest.raises(LlmRejected) as exc:
        testbed.service.chat_stream({"messages": []})

    assert exc.value.code == "no_model_loaded"
    assert testbed.calls == []


def test_stream_supplies_default_max_tokens_when_request_omits_it(tmp_path):
    """mlx_lm 默认 512 token，推理模型会把预算全花在思考上（cross-exam 2026-09-13 J1/G15）。"""
    from desk.llm.state import DEFAULT_CHAT_MAX_TOKENS

    testbed = make_loaded(tmp_path, backend_kw={"chunks": CONTENT_CHUNKS})
    list(testbed.service.chat_stream({"messages": []}))
    _, _, payload = next(call for call in testbed.calls if call[0] == "chat_stream")
    assert payload["max_tokens"] == DEFAULT_CHAT_MAX_TOKENS == 8192


def test_stream_keeps_caller_max_tokens(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chunks": CONTENT_CHUNKS})
    list(testbed.service.chat_stream({"messages": [], "max_tokens": 64}))
    _, _, payload = next(call for call in testbed.calls if call[0] == "chat_stream")
    assert payload["max_tokens"] == 64
