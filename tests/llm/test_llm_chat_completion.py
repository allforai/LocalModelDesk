"""Non-streaming chat rejections, field separation, and upstream passthrough."""
import pytest

from desk.llm.backend import BackendHttpError
from desk.llm.state import LlmRejected, UpstreamError
from tests.llm.llm_fakes import make_loaded, make_service


OK = {
    "choices": [{"message": {"content": "答案", "reasoning_content": "推理"},
                 "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 5, "completion_tokens": 7, "total_tokens": 12},
}


def test_completion_separates_content_and_reasoning(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": OK})

    got = testbed.service.chat_completion({"messages": [{"role": "user", "content": "hi"}]})

    assert got == {"content": "答案", "reasoning": "推理", "usage": OK["usage"],
                   "finish_reason": "stop", "model": "glm"}


def test_completion_empty_content_stays_empty_no_backfill(tmp_path):
    raw = {"choices": [{"message": {"content": "", "reasoning_content": "只想不说"},
                        "finish_reason": "stop"}], "usage": {"total_tokens": 2}}
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": raw})

    got = testbed.service.chat_completion({"messages": []})

    assert got["content"] == ""
    assert got["reasoning"] == "只想不说"


def test_completion_passes_sampling_params_to_resident_local_model(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": OK})

    testbed.service.chat_completion({"messages": [], "temperature": 0.2, "top_p": 0.9,
                                     "max_tokens": 64, "model": testbed.entries[0].hf_repo})

    _, _, payload = next(call for call in testbed.calls if call[0] == "chat")
    assert payload["model"] == "default_model"
    assert (payload["temperature"], payload["top_p"], payload["max_tokens"]) == (0.2, 0.9, 64)
    assert payload["stream"] is False


def test_no_model_loaded_rejected_immediately(tmp_path):
    testbed = make_service(tmp_path)

    with pytest.raises(LlmRejected) as exc:
        testbed.service.chat_completion({"messages": []})

    assert exc.value.code == "no_model_loaded"
    assert not any(call[0] in ("chat", "chat_stream") for call in testbed.calls)


def test_media_busy_rejected_immediately(tmp_path):
    testbed = make_loaded(tmp_path)
    testbed.arbiter.set_desk_state({"holder": {"kind": "video", "label": "j", "phase": "held"},
                                    "media_busy": True})

    with pytest.raises(LlmRejected) as exc:
        testbed.service.chat_completion({"messages": []})

    assert exc.value.code == "media_busy"
    assert not any(call[0] == "chat" for call in testbed.calls)


def test_model_mismatch_rejected_key_and_served_id_accepted(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": OK})

    with pytest.raises(LlmRejected) as exc:
        testbed.service.chat_completion({"messages": [], "model": "gpt-4o"})

    assert exc.value.code == "model_mismatch"
    assert testbed.service.chat_completion({"messages": [], "model": "glm"})["model"] == "glm"
    assert testbed.service.chat_completion(
        {"messages": [], "model": testbed.entries[0].hf_repo})["model"] == "glm"


def test_missing_usage_or_finish_reason_is_upstream_error(tmp_path):
    raw = {"choices": [{"message": {"content": "x"}, "finish_reason": "stop"}]}
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": raw})

    with pytest.raises(UpstreamError):
        testbed.service.chat_completion({"messages": []})


def test_backend_http_error_is_upstream_error(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chat_error": BackendHttpError("连接拒绝")})

    with pytest.raises(UpstreamError):
        testbed.service.chat_completion({"messages": []})


def test_completion_supplies_default_max_tokens(tmp_path):
    from desk.llm.state import DEFAULT_CHAT_MAX_TOKENS

    testbed = make_loaded(tmp_path, backend_kw={"chat_result": {
        "choices": [{"message": {"content": "答"}, "finish_reason": "stop"}],
        "usage": {"total_tokens": 1},
    }})
    testbed.service.chat_completion({"messages": []})
    _, _, payload = next(call for call in testbed.calls if call[0] == "chat")
    assert payload["max_tokens"] == DEFAULT_CHAT_MAX_TOKENS
