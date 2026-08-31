"""Facade tests for the heavy-work arbiter."""

import threading

from desk.arbiter.core import Arbiter
from desk.arbiter.reaper import ReapResult


def test_evict_llm_grants_media_invalidates_old_token_and_emits_states():
    reaped_ports = []

    def reaper(port):
        reaped_ports.append(port)
        return ReapResult(ok=True, port=port, killed_pids=[])

    arbiter = Arbiter(llm_port=43123, reaper=reaper, clock=lambda: 42.0)
    states = []
    arbiter.subscribe(states.append)
    llm = arbiter.acquire_heavy("llm", "model-a")

    media = arbiter.acquire_heavy("video", "job-a")

    assert media["ok"] is True
    assert reaped_ports == [43123]
    assert arbiter.current_holder() == {
        "kind": "video", "label": "job-a", "since": 42.0, "phase": "held"
    }
    assert arbiter.release_heavy(llm["token"])["reason"]["code"] == "not_holder"
    assert [state["holder"]["phase"] for state in states] == [
        "held", "acquiring", "held"
    ]
    assert all("token" not in state["holder"] for state in states)


def test_evict_failure_restores_llm_holder_and_keeps_its_token_valid():
    def reaper(port):
        return ReapResult(ok=False, port=port, killed_pids=[], error="still listening")

    arbiter = Arbiter(llm_port=43123, reaper=reaper, clock=lambda: 42.0)
    llm = arbiter.acquire_heavy("llm", "model-a")

    result = arbiter.acquire_heavy("music", "job-a")

    assert result == {
        "ok": False,
        "reason": {"code": "evict_failed", "message": "still listening"},
    }
    assert arbiter.current_holder()["kind"] == "llm"
    assert arbiter.release_heavy(llm["token"]) == {"ok": True}


def test_fast_rejects_during_eviction_without_waiting_for_transition_lock():
    eviction_started = threading.Event()
    finish_eviction = threading.Event()

    def reaper(port):
        eviction_started.set()
        assert finish_eviction.wait(timeout=1)
        return ReapResult(ok=True, port=port, killed_pids=[])

    arbiter = Arbiter(llm_port=43123, reaper=reaper)
    arbiter.acquire_heavy("llm", "model-a")
    eviction = threading.Thread(
        target=arbiter.acquire_heavy, args=("video", "job-a"), daemon=True
    )
    eviction.start()
    assert eviction_started.wait(timeout=1)

    rejected = []
    completed = threading.Event()

    def retry():
        rejected.append(arbiter.acquire_heavy("music", "job-b"))
        completed.set()

    retry_thread = threading.Thread(target=retry, daemon=True)
    retry_thread.start()
    assert completed.wait(timeout=0.1)
    assert rejected == [{
        "ok": False,
        "reason": {
            "code": "transition_in_progress",
            "message": "a heavy-work transition is in progress; retry shortly",
        },
    }]

    finish_eviction.set()
    eviction.join(timeout=1)
    retry_thread.join(timeout=1)
    assert not eviction.is_alive()
    assert not retry_thread.is_alive()


def test_sixteen_simultaneous_acquires_grant_exactly_one():
    arbiter = Arbiter(llm_port=43123)
    barrier = threading.Barrier(16)
    results = []
    results_lock = threading.Lock()

    def acquire(index):
        barrier.wait(timeout=1)
        result = arbiter.acquire_heavy("llm", f"model-{index}")
        with results_lock:
            results.append(result)

    threads = [threading.Thread(target=acquire, args=(index,)) for index in range(16)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=1)

    assert all(not thread.is_alive() for thread in threads)
    assert sum(result["ok"] for result in results) == 1
    assert len(results) == 16
    assert {
        result["reason"]["code"] for result in results if not result["ok"]
    } == {"llm_already_held"}


def test_mixed_media_race_grants_exactly_one_request():
    reaper_started = threading.Event()
    finish_reaper = threading.Event()

    def reaper(port):
        reaper_started.set()
        assert finish_reaper.wait(timeout=1)
        return ReapResult(ok=True, port=port, killed_pids=[])

    arbiter = Arbiter(llm_port=43123, reaper=reaper)
    arbiter.acquire_heavy("llm", "model-a")
    barrier = threading.Barrier(16)
    results = []
    results_lock = threading.Lock()

    def acquire(index):
        barrier.wait(timeout=1)
        kind = "video" if index % 2 else "music"
        result = arbiter.acquire_heavy(kind, f"job-{index}")
        with results_lock:
            results.append(result)

    threads = [threading.Thread(target=acquire, args=(index,)) for index in range(16)]
    for thread in threads:
        thread.start()
    assert reaper_started.wait(timeout=1)
    finish_reaper.set()
    for thread in threads:
        thread.join(timeout=1)

    assert all(not thread.is_alive() for thread in threads)
    assert sum(result["ok"] for result in results) == 1
    assert len(results) == 16
    assert arbiter.current_holder()["kind"] in {"video", "music"}
    assert all(
        result["reason"]["code"] in {"transition_in_progress", "media_busy"}
        for result in results
        if not result["ok"]
    )


def test_late_release_of_stale_token_is_harmless_after_replay():
    arbiter = Arbiter(
        llm_port=43123,
        reaper=lambda port: ReapResult(ok=True, port=port, killed_pids=[]),
    )
    llm = arbiter.acquire_heavy("llm", "model-a")
    media = arbiter.acquire_heavy("video", "job-a")

    first_late_release = arbiter.release_heavy(llm["token"])
    second_late_release = arbiter.release_heavy(llm["token"])

    assert first_late_release["reason"]["code"] == "not_holder"
    assert second_late_release["reason"]["code"] == "not_holder"
    assert arbiter.current_holder()["kind"] == "video"
    assert arbiter.release_heavy(media["token"]) == {"ok": True}
