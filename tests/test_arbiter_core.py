"""Facade tests for the heavy-work arbiter."""

import threading
from types import SimpleNamespace

from desk.arbiter.core import Arbiter
from desk.arbiter.reaper import ReapResult


def test_memory_snapshot_is_reader_dict():
    snapshot = SimpleNamespace(
        to_dict=lambda: {
            "total_bytes": 128_000_000_000,
            "used_bytes": 76_000_000_000,
            "available_bytes": 52_000_000_000,
            "pressure": "normal",
            "page_size": 16384,
            "captured_at": 1.0,
        }
    )
    arbiter = Arbiter(llm_port=43123, memory=SimpleNamespace(snapshot=lambda: snapshot))

    assert arbiter.memory_snapshot() == snapshot.to_dict()


def test_reap_llm_port_uses_argument_port_not_llm_port():
    calls = []

    def reaper(port):
        calls.append(port)
        return ReapResult(ok=True, port=port, killed_pids=[])

    arbiter = Arbiter(llm_port=43123, reaper=reaper)

    assert arbiter.reap_llm_port(61234) == {
        "ok": True, "port": 61234, "killed_pids": [], "error": None
    }
    assert calls == [61234]


def test_package_exports():
    import desk.arbiter as package

    for name in (
        "Arbiter", "MemoryReader", "MemorySnapshot", "MemoryProbeError",
        "parse_vm_stat", "ReapResult", "reap_port", "Decision", "Holder",
        "plan_acquire", "KINDS", "MEDIA_KINDS", "PHASE_ACQUIRING", "PHASE_HELD",
    ):
        assert hasattr(package, name), name


def test_can_start_heavy_is_read_only_and_uses_acquire_decision():
    arbiter = Arbiter(llm_port=43123)
    assert arbiter.can_start_heavy("video") == {
        "ok": True,
        "reason": None,
        "memory_warning": None,
    }

    llm = arbiter.acquire_heavy("llm", "model-a")

    assert arbiter.can_start_heavy("llm") == {
        "ok": False,
        "reason": {
            "code": "llm_already_held",
            "message": "llm 'model-a' already holds memory; release it first",
        },
        "memory_warning": None,
    }
    assert arbiter.current_holder()["kind"] == "llm"
    assert arbiter.release_heavy(llm["token"]) == {"ok": True}


def test_can_start_heavy_warns_for_oversized_model_without_refusing():
    memory = SimpleNamespace(
        snapshot=lambda: SimpleNamespace(available_bytes=52_000_000_000))
    arbiter = Arbiter(llm_port=43123, memory=memory)

    result = arbiter.can_start_heavy("llm", estimated_bytes=74_000_000_000)

    assert result == {
        "ok": True,
        "reason": None,
        "memory_warning": {
            "code": "insufficient_memory",
            "required_bytes": 74_000_000_000,
            "available_bytes": 52_000_000_000,
            "message": "model requires about 74.0 GB; 52.0 GB is currently available",
        },
    }


def test_can_start_heavy_does_not_warn_when_model_exactly_fits_available_memory():
    memory = SimpleNamespace(
        snapshot=lambda: SimpleNamespace(available_bytes=52_000_000_000))
    arbiter = Arbiter(llm_port=43123, memory=memory)

    result = arbiter.can_start_heavy("llm", estimated_bytes=52_000_000_000)

    assert result == {"ok": True, "reason": None, "memory_warning": None}


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
