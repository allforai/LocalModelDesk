"""data:llmState / data:loadedModel / ChatEvent shapes and error codes."""
from types import SimpleNamespace

from desk.llm import DEFAULT_LLM_PORT, LlmState, LoadedModel
from desk.llm import state as S


def test_default_port_is_frozen_constant():
    assert DEFAULT_LLM_PORT == 8767
    assert S.DEFAULT_LLM_PORT == 8767


def test_package_exports_llm_data_shapes():
    assert LlmState is S.LlmState
    assert LoadedModel is S.LoadedModel


def test_llm_state_idle_to_dict():
    assert S.LlmState().to_dict() == {
        "status": "idle", "model_key": None, "error": None, "loaded_at": None,
    }


def test_llm_state_error_carries_log_tail():
    st = S.LlmState(
        status=S.STATUS_ERROR,
        model_key="glm",
        error=S.LlmError(code=S.ERR_BACKEND_EXITED, message="failed", log_tail="tail"),
    )
    assert st.to_dict()["error"] == {
        "code": "backend_exited", "message": "failed", "log_tail": "tail",
    }


def test_loaded_model_from_entry_is_zero_copy_and_served_id_is_hf_repo():
    entry = SimpleNamespace(
        key="glm", name="GLM-4.5-Air", hf_repo="mlx-community/GLM-4.5-Air-4bit",
        vision=False, quant="4bit", params="106B", gb=60.2,
    )
    assert S.LoadedModel.from_entry(entry).to_dict() == {
        "key": "glm", "name": "GLM-4.5-Air", "hf_repo": "mlx-community/GLM-4.5-Air-4bit",
        "served_id": "mlx-community/GLM-4.5-Air-4bit", "vision": False,
        "quant": "4bit", "params": "106B", "gb": 60.2,
    }


def test_chat_event_shapes():
    assert S.delta_event("text", None) == {"type": "delta", "text": "text", "reasoning": None}
    assert S.delta_event(None, "thought") == {"type": "delta", "text": None, "reasoning": "thought"}
    assert S.done_event({"total_tokens": 3}, "stop") == {
        "type": "done", "usage": {"total_tokens": 3}, "finish_reason": "stop",
    }
    assert S.error_event(S.ERR_UPSTREAM_ERROR, "broken") == {
        "type": "error", "code": "upstream_error", "message": "broken",
    }


def test_exceptions():
    exc = S.LlmRejected(S.ERR_MEDIA_BUSY, "media job running")
    assert exc.to_dict() == {"code": "media_busy", "message": "media job running"}
    up = S.UpstreamError("upstream broken")
    assert up.code == "upstream_error" and up.message == "upstream broken"


def test_error_code_vocabulary_complete():
    assert {
        S.ERR_MODEL_NOT_FOUND, S.ERR_MODEL_DIR_MISSING, S.ERR_MEDIA_BUSY,
        S.ERR_LOAD_IN_PROGRESS, S.ERR_BACKEND_EXITED, S.ERR_LOAD_TIMEOUT,
        S.ERR_PORT_NOT_RELEASED, S.ERR_EVICTED, S.ERR_NO_MODEL_LOADED,
        S.ERR_MODEL_MISMATCH, S.ERR_UPSTREAM_ERROR,
    } == {
        "model_not_found", "model_dir_missing", "media_busy", "load_in_progress",
        "backend_exited", "load_timeout", "port_not_released", "evicted",
        "no_model_loaded", "model_mismatch", "upstream_error",
    }
