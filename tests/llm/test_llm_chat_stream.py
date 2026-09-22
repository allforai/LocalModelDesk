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


def test_stream_cut_by_eviction_reports_evicted_not_upstream_error(tmp_path):
    testbed = make_loaded(
        tmp_path, backend_kw={"chunks": CONTENT_CHUNKS[:2], "stream_error_after": 1}
    )
    events = testbed.service.chat_stream({"messages": []})
    first = next(events)
    testbed.arbiter.emit({"holder": {"kind": "media", "label": "h3"}, "media_busy": True})

    rest = list(events)

    assert first["type"] == "delta"
    assert rest[-1] == {"type": "error", "code": "evicted", "message": "内存让给了媒体作业，回答被中断"}


def test_stream_cut_while_media_is_taking_the_memory_reports_evicted(tmp_path):
    """真机：仲裁先杀 mlx-lm、后通知订阅者，断流时服务状态还没变成 evicted（2026-09-15 真机复核）。

    这里走的是**轮询**那条路（`set_desk_state`，服务自己去读），不是推送那条；
    断流的原因只能靠台面状态分辨，否则会被标成 upstream_error。
    """
    testbed = make_loaded(
        tmp_path, backend_kw={"chunks": CONTENT_CHUNKS[:2], "stream_error_after": 1}
    )
    events = testbed.service.chat_stream({"messages": []})
    first = next(events)
    testbed.arbiter.set_desk_state({"holder": {"kind": "video", "label": "job-1", "phase": "acquiring"},
                                    "media_busy": False})

    rest = list(events)

    assert first["type"] == "delta"
    assert rest[-1] == {"type": "error", "code": "evicted", "message": "内存让给了媒体作业，回答被中断"}


def test_a_crash_during_a_coexisting_media_job_is_not_called_an_eviction(tmp_path):
    """共存时后端自己崩了，不能报成「已被媒体任务驱逐」。

    判据只看 `holder`（= 最后授予的那件）就会这样：视频一开始它就是 video，
    于是任何断流都被归因成让位，真正的崩溃原因被这句话盖掉。
    """
    testbed = make_loaded(
        tmp_path, backend_kw={"chunks": CONTENT_CHUNKS[:2], "stream_error_after": 1}
    )
    events = testbed.service.chat_stream({"messages": []})
    next(events)
    testbed.arbiter.set_desk_state({
        "holders": [{"kind": "llm", "label": "glm", "phase": "held"},
                    {"kind": "video", "label": "job-1", "phase": "held"}],
        "holder": {"kind": "video", "label": "job-1", "phase": "held"},
        "media_busy": True})

    rest = list(events)

    assert rest[-1]["code"] != "evicted", "共存时的崩溃被误报成驱逐"


def test_chat_stream_is_rejected_once_the_desk_no_longer_holds_the_model(tmp_path):
    """持有权已经没了就别开流——不必先吐半截答案再报错。"""
    testbed = make_loaded(tmp_path, backend_kw={"chunks": CONTENT_CHUNKS})
    testbed.arbiter.set_desk_state({
        "holders": [{"kind": "video", "label": "job-1", "phase": "held"}],
        "holder": {"kind": "video", "label": "job-1", "phase": "held"},
        "media_busy": True})

    with pytest.raises(LlmRejected) as exc:
        list(testbed.service.chat_stream({"messages": []}))

    assert exc.value.code == "evicted"
    assert not any(call[0] == "chat_stream" for call in testbed.calls)


def test_stream_uses_the_models_recommended_sampling_unless_the_request_sets_it(tmp_path):
    """mlx_lm defaults to temperature 0 (greedy); GLM then repeated one sentence for 8192 tokens."""
    import json

    testbed = make_loaded(tmp_path, backend_kw={"chunks": CONTENT_CHUNKS})
    model_dir = testbed.paths.models_root / testbed.entries[0].relpath
    (model_dir / "generation_config.json").write_text(json.dumps({"temperature": 1.0, "top_k": 20}))

    list(testbed.service.chat_stream({"messages": []}))
    list(testbed.service.chat_stream({"messages": [], "temperature": 0.2}))

    first, second = [call[2] for call in testbed.calls if call[0] == "chat_stream"]
    assert (first["temperature"], first["top_k"]) == (1.0, 20)
    assert (second["temperature"], second["top_k"]) == (0.2, 20)
