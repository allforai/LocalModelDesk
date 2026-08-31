"""guard.admit: 503 ordering, model matching, and never auto-loading."""
import pytest

from desk.gateway.errors import (
    REASON_MEDIA_JOB_RUNNING,
    REASON_MODEL_NOT_LOADED,
    REASON_NO_MODEL_LOADED,
    GatewayReject,
)
from desk.gateway.guard import admit
from gateway_fakes import IDLE_STATUS, MEDIA_DESK, MEDIA_REFUSAL, FakeBackend


def _rejected(backend, model=None):
    with pytest.raises(GatewayReject) as error:
        admit(backend, model)
    backend.assert_no_inference_calls()
    return error.value


def test_admit_ok_returns_loaded():
    backend = FakeBackend()
    loaded = admit(backend, None)
    assert loaded["key"] == "qwen3-30b"
    assert loaded["served_id"] == "mlx-community/Qwen3-30B-A3B-8bit"
    backend.assert_no_inference_calls()


def test_admit_accepts_key_and_served_id_and_empty():
    for model in ("qwen3-30b", "mlx-community/Qwen3-30B-A3B-8bit", None, ""):
        assert admit(FakeBackend(), model)["key"] == "qwen3-30b"


def test_media_busy_uses_arbiter_reason_code():
    backend = FakeBackend(desk=MEDIA_DESK, can_start=MEDIA_REFUSAL)
    rejected = _rejected(backend)
    assert (rejected.http, rejected.code) == (503, "media_busy")
    assert "视频作业进行中" in rejected.message
    assert ("can_start_heavy", "llm") in backend.calls


def test_media_busy_falls_back_to_local_code():
    rejected = _rejected(FakeBackend(desk=MEDIA_DESK, can_start={"ok": True, "reason": None}))
    assert (rejected.http, rejected.code) == (503, REASON_MEDIA_JOB_RUNNING)


def test_media_busy_checked_before_model_state():
    backend = FakeBackend(llm=IDLE_STATUS, desk=MEDIA_DESK, can_start=MEDIA_REFUSAL)
    assert _rejected(backend).code == "media_busy"


def test_no_model_loaded():
    for status in (IDLE_STATUS, {"state": "loading", "loaded": None}, {"state": "error", "loaded": None}):
        rejected = _rejected(FakeBackend(llm=status))
        assert (rejected.http, rejected.code) == (503, REASON_NO_MODEL_LOADED)


def test_model_mismatch_names_resident_model():
    rejected = _rejected(FakeBackend(), "gpt-4o")
    assert (rejected.http, rejected.code) == (503, REASON_MODEL_NOT_LOADED)
    assert "gpt-4o" in rejected.message
    assert "qwen3-30b" in rejected.message


def test_backend_protocol_has_no_load_paths():
    backend = FakeBackend()
    for forbidden in ("load_llm", "unload_llm", "acquire_heavy", "release_heavy"):
        assert not hasattr(backend, forbidden)
