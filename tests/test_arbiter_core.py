"""Facade tests for the heavy-work arbiter."""

import threading
from types import SimpleNamespace

from desk.arbiter.core import Arbiter
from desk.arbiter.reaper import ReapResult
from desk.budget.budget import Workload


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
    assert arbiter.desk_state()["holder"]["kind"] == "llm"
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
    assert arbiter.desk_state()["holder"] == {
        "kind": "video", "label": "job-a", "display": "job-a", "since": 42.0, "phase": "held"
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
    assert arbiter.desk_state()["holder"]["kind"] == "llm"
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
    assert arbiter.desk_state()["holder"]["kind"] in {"video", "music"}
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
    assert arbiter.desk_state()["holder"]["kind"] == "video"
    assert arbiter.release_heavy(media["token"]) == {"ok": True}


def test_reaper_receives_only_the_pids_we_own():
    """P1：仲裁者收端口前必须把"哪些进程是我们的"告诉 reaper。"""
    seen = {}

    def fake_reaper(port, owned_pids=None):
        seen["port"], seen["owned"] = port, owned_pids
        return ReapResult(ok=True, port=port, killed_pids=[])

    arbiter = Arbiter(8767, reaper=fake_reaper)
    arbiter.set_owned_pid_provider(lambda: {4242})
    arbiter.reap_llm_port(8767)

    assert seen["owned"] == {4242}


def test_reaper_without_a_provider_is_called_the_old_way():
    """未注册归属来源时保持旧签名，注入的假 reaper 不必接受关键字参数。"""
    calls = []
    arbiter = Arbiter(8767, reaper=lambda port: calls.append(port) or ReapResult(
        ok=True, port=port, killed_pids=[]))
    arbiter.reap_llm_port(8767)
    assert calls == [8767]


def test_public_holder_carries_the_display_name_for_the_menu_bar():
    """菜单栏曾显示目录 key『glm』而非模型名（cross-exam 2026-09-13 G16）。"""
    arbiter = Arbiter(llm_port=43124, reaper=lambda port, **_: ReapResult(ok=True, port=port, killed_pids=[]),
                      clock=lambda: 1.0)
    arbiter.acquire_heavy("llm", "glm", "GLM 4.7 Flash 越狱 4bit")
    assert arbiter.desk_state()["holder"]["display"] == "GLM 4.7 Flash 越狱 4bit"
    arbiter2 = Arbiter(llm_port=43125, reaper=lambda port, **_: ReapResult(ok=True, port=port, killed_pids=[]),
                       clock=lambda: 1.0)
    arbiter2.acquire_heavy("video", "job-1")
    assert arbiter2.desk_state()["holder"]["display"] == "job-1"


# ---- Task 7: budget-aware coexistence (R-arbiter-01/04/05) ------------------
#
# Everything above this line runs an `Arbiter(...)` built with no `budget`
# argument, and exercises the legacy single-slot exclusion table byte-for-byte
# unchanged (see the module docstring in desk/arbiter/core.py for why that
# fallback exists). These tests instead wire a `budget` double so the real
# R-arbiter-01 rewrite — coexistence gated by Verdict.ok, not by kind — is
# under test.

class FakeBudget:
    """Deterministic `.cost(...)` double: fixed Workload per kind, no IO."""

    def __init__(self, costs: dict):
        self._costs = costs

    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None):
        return self._costs[kind]


def test_can_start_heavy_grants_llm_while_media_runs_when_budget_allows():
    """这正是被改掉的那条铁律：媒体在跑，预算够，聊天照样装得下（R-arbiter-01）。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=200_000_000_000))
    budget = FakeBudget({
        "video": Workload("video", None, 100_000_000_000, "measured"),
        "llm": Workload("llm", "model-a", 50_000_000_000, "measured"),
    })
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=budget,
                       reaper=lambda port: ReapResult(ok=True, port=port, killed_pids=[]))

    granted = arbiter.acquire_heavy("video", "job-a", params={}, key=None)
    assert granted["ok"] is True

    result = arbiter.can_start_heavy("llm", params={}, key="model-a")
    assert result == {"ok": True, "reason": None, "memory_warning": None, "release": []}

    # And it is not merely advisory: acquiring actually coexists — the video
    # holder is not evicted, both are held at once.
    llm_grant = arbiter.acquire_heavy("llm", "model-a", params={}, key="model-a")
    assert llm_grant["ok"] is True
    assert arbiter.desk_state()["media_busy"] is True
    assert arbiter.release_heavy(granted["token"]) == {"ok": True}
    assert arbiter.release_heavy(llm_grant["token"]) == {"ok": True}


def test_can_start_heavy_reports_the_minimal_release_when_budget_is_short():
    """预算不够但让出音乐够用时，release 只含音乐那一件而非全部（R-arbiter-05）。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=120_000_000_000))
    budget = FakeBudget({
        "video": Workload("video", None, 80_000_000_000, "measured"),
        "music": Workload("music", None, 30_000_000_000, "measured"),
        "llm": Workload("llm", "model-a", 60_000_000_000, "measured"),
    })
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=budget)
    arbiter.acquire_heavy("video", "job-a", params={}, key=None)
    arbiter.acquire_heavy("music", "job-b", params={}, key=None)

    result = arbiter.can_start_heavy("llm", params={}, key="model-a")

    assert result["ok"] is False
    assert result["reason"]["code"] == "insufficient_budget"
    assert [w["kind"] for w in result["release"]] == ["music"]


def test_can_start_heavy_names_the_source_when_it_cannot_tell():
    """依据来源必须出现在拒绝原因里（R-budget-01）。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=10_000_000_000))
    budget = FakeBudget({"llm": Workload("llm", "model-a", 100_000_000_000, "unavailable")})
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=budget)

    result = arbiter.can_start_heavy("llm", params={}, key="model-a")

    assert result["ok"] is False
    assert "unavailable" in result["reason"]["message"]


def test_acquire_heavy_in_budget_mode_never_evicts_it_only_refuses():
    """budget 模式下 acquire_heavy 不再自动让出——那是调用方按 release 建议做的事。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=50_000_000_000))
    budget = FakeBudget({
        "llm": Workload("llm", "model-a", 40_000_000_000, "measured"),
        "video": Workload("video", None, 40_000_000_000, "measured"),
    })
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=budget)
    llm = arbiter.acquire_heavy("llm", "model-a", params={}, key="model-a")
    assert llm["ok"] is True

    refused = arbiter.acquire_heavy("video", "job-a", params={}, key=None)

    assert refused == {"ok": False, "reason": {
        "code": "insufficient_budget",
        "message": "需要 80000000000 字节，可用 50000000000 字节（依据：measured）",
    }}
    assert arbiter.desk_state()["holder"]["kind"] == "llm"   # 没有被让出
