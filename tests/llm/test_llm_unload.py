"""LLM unload confirms the port is actually released before reporting success."""
import time

from desk.llm.state import DEFAULT_LLM_PORT
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


def test_unload_while_loading_cancels_the_load_and_releases(tmp_path):
    testbed = make_service(tmp_path, load_timeout_s=30)
    testbed.backend.hold_health = True

    testbed.service.load("glm")
    assert testbed.service.status()["state"]["status"] == "loading"
    # The load worker runs on a daemon thread; without a real yield point the main thread
    # can reach unload() before the worker ever executes, so wait for it to actually spawn
    # (and register self._proc) before exercising the cancel path deterministically.
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and "spawn" not in [c[0] for c in testbed.calls]:
        time.sleep(0.005)
    assert "spawn" in [c[0] for c in testbed.calls]

    result = testbed.service.unload()
    testbed.backend.health_release.set()

    assert result["status"] == "idle"
    assert ("release", "tok-1") in testbed.calls
    assert testbed.service.wait_settled()["status"] == "idle"
    # unload() may win the race and terminate the already-spawned process itself, or the
    # background worker may notice the generation bump first and terminate it instead —
    # either way "terminate" must show up, possibly slightly after unload() returns.
    deadline = time.monotonic() + 2.0
    while time.monotonic() < deadline and "terminate" not in [c[0] for c in testbed.calls]:
        time.sleep(0.01)
    assert "terminate" in [call[0] for call in testbed.calls]
