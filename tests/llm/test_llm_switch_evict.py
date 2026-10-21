"""LLM model switches retain their lease and eviction interrupts loading."""
from __future__ import annotations

import threading
import time

import pytest
from tests.deadlines import HANG_TIMEOUT_S
from desk.arbiter.core import Arbiter
from desk.arbiter.reaper import ReapResult
from desk.llm.service import LlmService
from desk.llm.state import LlmRejected
from tests.llm.llm_fakes import (
    FakeBackend,
    FakeCatalog,
    FakePaths,
    make_entry,
    make_loaded,
    make_service,
)


def _free_port() -> int:
    import socket

    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def test_initial_load_does_not_deadlock_real_arbiter_subscription(tmp_path):
    entry = make_entry()
    paths = FakePaths(tmp_path)
    (paths.models_root / entry.relpath).mkdir(parents=True)
    port = _free_port()  # never the real 8767: a running app's mlx-lm there reads as a stranger
    service = LlmService(
        backend=FakeBackend(),
        arbiter=Arbiter(
            llm_port=port,
            reaper=lambda port: ReapResult(ok=True, port=port, killed_pids=[]),
        ),
        catalog=FakeCatalog([entry]),
        paths=paths,
        port=port,
        poll_interval_s=0.001,
    )
    result = []
    loader = threading.Thread(target=lambda: result.append(service.load("glm")), daemon=True)

    loader.start()
    loader.join(timeout=HANG_TIMEOUT_S)

    assert not loader.is_alive()
    assert result == [{"status": "loading", "model_key": "glm", "loaded_at": None, "error": None}]
    assert service.wait_settled()["status"] == "loaded"


def test_switch_model_retargets_the_same_permit(tmp_path):
    glm = make_entry(key="glm")
    qwen = make_entry(key="qwen")
    testbed = make_loaded(tmp_path, entries=[glm, qwen])
    testbed.calls.clear()

    state = testbed.service.load("qwen")

    assert state["status"] == "loading"
    assert testbed.service.wait_settled()["status"] == "loaded"
    names = [call[0] for call in testbed.calls]
    assert "acquire" not in names and "release" not in names
    assert names[:4] == ["retarget", "terminate", "wait", "reap"]   # 先问 arbiter，再停旧进程
    assert testbed.calls[0] == ("retarget", "tok-1", "qwen")
    assert testbed.arbiter.last_retarget["key"] == "qwen"
    assert ("spawn", str(testbed.paths.venv_python),
            str(testbed.paths.models_root / qwen.relpath), 8767,
            str(testbed.paths.logs_dir / "mlx-lm.log")) in testbed.calls


def test_switch_refused_keeps_the_old_model_loaded(tmp_path):
    glm = make_entry(key="glm")
    qwen = make_entry(key="qwen")
    refusal = {"ok": False, "reason": {"code": "insufficient_budget", "message": "装不下"}}
    testbed = make_loaded(tmp_path, entries=[glm, qwen], arbiter_kw={"retarget_result": refusal})
    testbed.calls.clear()

    with pytest.raises(LlmRejected) as exc:
        testbed.service.load("qwen")

    assert exc.value.code == "insufficient_budget"
    status = testbed.service.status()
    assert status["state"]["status"] == "loaded" and status["state"]["model_key"] == "glm"
    assert "terminate" not in [call[0] for call in testbed.calls]


def test_state_with_the_old_label_during_a_switch_is_not_an_eviction(tmp_path):
    glm = make_entry(key="glm")
    qwen = make_entry(key="qwen")
    testbed = make_loaded(tmp_path, entries=[glm, qwen])
    old = {"kind": "llm", "label": "glm", "phase": "held"}
    testbed.arbiter.on_retarget = lambda: testbed.arbiter.emit(
        {"holder": old, "holders": [old], "media_busy": False})

    testbed.service.load("qwen")

    assert testbed.service.wait_settled()["status"] == "loaded"


def test_eviction_while_loading_immediately_converges_to_evicted_error(tmp_path):
    testbed = make_service(tmp_path)
    testbed.backend.hold_health = True
    testbed.service.load("glm")
    deadline = time.monotonic() + HANG_TIMEOUT_S
    while "health" not in [call[0] for call in testbed.calls] and time.monotonic() < deadline:
        time.sleep(0.001)
    assert "health" in [call[0] for call in testbed.calls]

    testbed.arbiter.emit({
        "holder": {"kind": "video", "label": "job-1", "phase": "held"},
        "media_busy": True,
    })

    state = testbed.service.wait_settled(timeout_s=HANG_TIMEOUT_S)
    assert state["status"] == "error"
    assert state["model_key"] == "glm"
    assert state["error"]["code"] == "evicted"
    assert testbed.proc.terminated is True
    testbed.backend.health_release.set()
    assert testbed.service.wait_settled()["error"]["code"] == "evicted"


def test_unload_does_not_deadlock_when_releasing_llm_notifies_subscribers(tmp_path):
    entry = make_entry()
    paths = FakePaths(tmp_path)
    (paths.models_root / entry.relpath).mkdir(parents=True)
    port = _free_port()  # never the real 8767: a running app's mlx-lm there reads as a stranger
    service = LlmService(
        backend=FakeBackend(),
        arbiter=Arbiter(
            llm_port=port,
            reaper=lambda port: ReapResult(ok=True, port=port, killed_pids=[]),
        ),
        catalog=FakeCatalog([entry]),
        paths=paths,
        port=port,
        poll_interval_s=0.001,
    )
    assert service.load("glm")["status"] == "loading"
    assert service.wait_settled()["status"] == "loaded"

    result = []
    unloader = threading.Thread(target=lambda: result.append(service.unload()), daemon=True)
    unloader.start()
    unloader.join(timeout=HANG_TIMEOUT_S)

    assert not unloader.is_alive()
    assert result == [{"status": "idle", "model_key": None, "loaded_at": None, "error": None}]


def test_chat_after_a_switch_is_answered_not_refused_as_evicted(tmp_path):
    glm, qwen = make_entry(key="glm"), make_entry(key="qwen")
    paths = FakePaths(tmp_path)
    for entry in (glm, qwen):
        (paths.models_root / entry.relpath).mkdir(parents=True)
    port = _free_port()
    backend = FakeBackend(chat_result={"choices": [{"message": {"content": "好"}, "finish_reason": "stop"}],
                                       "usage": {"total_tokens": 1}})
    service = LlmService(
        backend=backend,
        arbiter=Arbiter(llm_port=port, reaper=lambda port: ReapResult(ok=True, port=port, killed_pids=[])),
        catalog=FakeCatalog([glm, qwen]), paths=paths, port=port, poll_interval_s=0.001,
    )
    service.load("glm")
    assert service.wait_settled()["status"] == "loaded"
    service.load("qwen")
    assert service.wait_settled()["status"] == "loaded"

    answer = service.chat_completion({"messages": [{"role": "user", "content": "hi"}], "model": "qwen"})

    assert answer["content"] == "好" and answer["model"] == "qwen"
    assert service.status()["state"]["status"] == "loaded"
