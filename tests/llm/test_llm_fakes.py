"""The LLM fakes are themselves programmable test subjects."""
import threading

import pytest

from desk.llm.backend import BackendHttpError
from tests.llm.llm_fakes import CallLedger, FakeArbiter, FakeBackend, FakeCatalog, FakePaths, FakeProcess, make_entry


def test_fake_process_poll_script_sticks_set_exit_and_records_shared_ledger():
    ledger = CallLedger()
    process = FakeProcess(poll_script=[None, None, 3], calls=ledger)
    assert [process.poll(), process.poll(), process.poll(), process.poll()] == [None, None, 3, 3]
    process.set_exit(9)
    assert process.poll() == 9
    process.terminate(); process.kill(); process.wait(1.5)
    assert [call["name"] for call in ledger.calls] == ["terminate", "kill", "wait"]
    assert ledger.calls[-1]["args"] == (1.5,)


def test_fake_backend_scripts_calls_and_configured_failures(tmp_path):
    ledger = CallLedger()
    backend = FakeBackend(health_script=[False, True], chat_result={"answer": "ok"}, chat_error=RuntimeError("unavailable"), calls=ledger)
    assert backend.spawn("py", "model", 9999, tmp_path / "log") is backend.process
    assert [backend.health(9999), backend.health(9999), backend.health(9999)] == [False, True, True]
    with pytest.raises(RuntimeError, match="unavailable"):
        backend.chat(9999, {})
    backend.chat_error = None
    assert backend.chat(9999, {}) == {"answer": "ok"}
    assert [call["name"] for call in ledger.calls] == ["spawn", "health", "health", "health", "chat", "chat"]


def test_fake_backend_can_block_health_and_interrupt_stream():
    backend = FakeBackend(chunks=[{"a": 1}, {"a": 2}], stream_error_after=1)
    iterator = backend.chat_stream(9999, {})
    assert next(iterator) == {"a": 1}
    with pytest.raises(BackendHttpError, match="fake"):
        next(iterator)
    backend = FakeBackend(); backend.hold_health = True
    received = []
    thread = threading.Thread(target=lambda: received.append(backend.health(9999)))
    thread.start(); assert not received
    backend.health_release.set(); thread.join(timeout=5)
    assert received == [True]


def test_fake_arbiter_scripts_state_events_and_shared_ledger():
    ledger = CallLedger()
    arbiter = FakeArbiter(calls=ledger, acquire_results=[{"ok": False, "reason": {"code": "media_busy"}}], reap_results=[{"ok": False, "port": 1, "killed_pids": [], "error": "stuck"}])
    received = []
    unsubscribe = arbiter.subscribe(received.append)
    assert arbiter.acquire_heavy("llm", "glm")["ok"] is False
    assert arbiter.reap_llm_port(1234)["ok"] is False
    assert arbiter.release_heavy("tok") == {"ok": True}
    assert arbiter.desk_state()["holder"]["kind"] == "llm"
    changed = {"holder": None, "media_busy": False}
    arbiter.set_desk_state(changed)
    assert arbiter.desk_state() == changed
    arbiter.emit({"holder": {"kind": "video"}}); unsubscribe(); arbiter.emit({"holder": None})
    assert received == [{"holder": {"kind": "video"}}]
    assert [call["name"] for call in ledger.calls] == ["acquire", "reap", "release"]


def test_fake_catalog_paths_and_entry_are_isolated_and_programmable(tmp_path):
    entry = make_entry("tiny", name="Tiny")
    catalog = FakeCatalog([entry])
    paths = FakePaths(tmp_path)
    listed = catalog.list_catalog(); listed.clear()
    assert catalog.list_catalog() == [entry]
    assert paths.resolve_paths().models_root == tmp_path / "models"
    assert paths.logs_dir.is_dir()
    assert paths.venv_python == tmp_path / "venv" / "bin" / "python3"
