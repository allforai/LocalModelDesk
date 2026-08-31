"""LLM unload confirms the port is actually released before reporting success."""
import pytest

from desk.llm.state import DEFAULT_LLM_PORT, LlmRejected
from tests.llm.llm_fakes import make_loaded, make_service


def test_unload_success_terminate_then_reap_then_release(tmp_path):
    testbed = make_loaded(tmp_path)

    state = testbed.service.unload()

    assert state == {"status": "idle", "model_key": None, "error": None, "loaded_at": None}
    names = [call[0] for call in testbed.calls]
    terminate = names.index("terminate")
    release = names.index("release")
    final_reap = len(names) - 1 - names[::-1].index("reap")
    assert terminate < final_reap < release
    assert ("reap", DEFAULT_LLM_PORT) in testbed.calls
    assert testbed.service.status()["loaded_model"] is None


def test_unload_idle_is_idempotent(tmp_path):
    testbed = make_service(tmp_path)

    assert testbed.service.unload()["status"] == "idle"
    assert testbed.calls == []


def test_unload_port_still_held_is_error_not_fake_success(tmp_path):
    available = {"ok": True, "port": DEFAULT_LLM_PORT, "killed_pids": [], "error": None}
    occupied = {"ok": False, "port": DEFAULT_LLM_PORT, "killed_pids": [], "error": "pid 7 stubborn"}
    testbed = make_loaded(tmp_path, arbiter_kw={"reap_results": [available, occupied]})

    state = testbed.service.unload()

    assert state["status"] == "error"
    assert state["error"]["code"] == "port_not_released"
    assert "release" not in [call[0] for call in testbed.calls]


def test_unload_during_loading_rejected_worker_unaffected(tmp_path):
    testbed = make_service(tmp_path)
    testbed.backend.hold_health = True
    testbed.service.load("glm")

    with pytest.raises(LlmRejected) as exc:
        testbed.service.unload()

    assert exc.value.code == "load_in_progress"
    testbed.backend.health_release.set()
    assert testbed.service.wait_settled()["status"] == "loaded"
