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

GIB = 1024 ** 3

MEDIA_KIND_NAMES = ("video", "music")


class FakeBudget:
    """Deterministic `.cost(...)` double: fixed Workload per kind, no IO.

    Mirrors the one real-`Budget` detail R-budget-13 tests depend on: for a
    non-media kind (chat needs a model `key` to look up a per-token cost),
    `cost()` called without a `key` cannot produce a real number and falls
    back to a `bytes_needed=0`/`source="unavailable"` stub — see
    `Budget._per_token`/`Budget.for_chat` in desk/budget/budget.py, which
    return exactly that shape when `key` is falsy. A double that ignored this
    and always returned the fixture Workload regardless of `key` would let
    the R-budget-13 regression tests pass by coincidence (small, round byte
    counts happening to still fit) without ever exercising the bug they name.
    """

    def __init__(self, costs: dict):
        self._costs = costs

    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None):
        if kind not in MEDIA_KIND_NAMES and key is None:
            return Workload(kind, None, 0, "unavailable")
        return self._costs[kind]


class StepMemory:
    """按调用次序吐出预设的 available_bytes，模拟「授予后可用内存下降」。

    与 tests/test_arbiter_resident_accounting.py 里的同名夹具同源：_backfill_resident
    的采样点在每次读快照时，不在 acquire_heavy 里，所以要控制的是调用顺序上的值，
    不是时间。"""

    def __init__(self, values):
        self._values = list(values)
        self.calls = 0

    def snapshot(self):
        value = self._values[min(self.calls, len(self._values) - 1)]
        self.calls += 1
        return SimpleNamespace(available_bytes=value)


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
    """预算不够但让出音乐够用时，release 只含音乐那一件而非全部（R-arbiter-05）。

    分母换成机器自报的静态能力之后（R-budget-16），声明的占用与分母是同一种东西，
    plan() 直接按整件额度算「让出能回收多少」——不再需要问谁此刻实际占了多少。
    """
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


def test_acquire_heavy_in_budget_mode_evicts_the_llm_per_the_minimal_plan():
    """R-arbiter-05 改写后是「仅在预算不足时**让出**，且最小让出」，不是「不足就拒绝」。

    这条测试原先断言的是相反的行为（budget 模式从不自动让出，由调用方按 release
    建议自己执行）。那个设计偏离了 spec，而且它承诺的「调用方执行」这一半
    从来没有人实现——release 被算出来又被丢掉，于是「加载着聊天模型时开视频作业」
    在 budget 模式下直接失败，比 legacy 还差。按 spec 翻回来。

    只有「卸聊天模型」这一种让出是自动的；要腾掉正在跑的媒体作业时仍然拒绝
    （见 test_budget_mode_refuses_rather_than_killing_a_running_media_job）。
    """
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=50_000_000_000))
    budget = FakeBudget({
        "llm": Workload("llm", "model-a", 40_000_000_000, "measured"),
        "video": Workload("video", None, 40_000_000_000, "measured"),
    })
    reaped = []
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=budget,
                      reaper=lambda port: (reaped.append(port) or
                                           SimpleNamespace(ok=True, port=port, killed_pids=[], error=None)))
    assert arbiter.acquire_heavy("llm", "model-a", params={}, key="model-a")["ok"] is True

    granted = arbiter.acquire_heavy("video", "job-a", params={}, key=None)

    assert granted["ok"] is True
    assert reaped == [43123]
    assert arbiter.desk_state()["holder"]["kind"] == "video"   # 聊天模型已被让出


def test_budget_mode_evicts_the_llm_to_make_room_for_media(tmp_path):
    """R-arbiter-05 改写后仍要求「预算不足时让出，且最小让出」——不是「预算不足就拒绝」。

    上线时这里是个回归：预算模式下 plan_acquire 从不返回 evict_then_grant，
    算出来的 release 也没有任何调用方消费，于是「加载着聊天模型时开视频作业」
    会直接失败，而 legacy 模式下它会先卸模型再跑。
    """
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=80_000_000_000))
    budget = FakeBudget({
        "llm": Workload("llm", "model-a", 70_000_000_000, "measured"),
        "video": Workload("video", None, 27_000_000_000, "measured"),
    })
    reaped = []
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=budget,
                      reaper=lambda port: (reaped.append(port) or
                                           SimpleNamespace(ok=True, port=port, killed_pids=[], error=None)))
    arbiter.acquire_heavy("llm", "model-a", params={}, key="model-a")

    grant = arbiter.acquire_heavy("video", "job-1", params={}, key=None)

    assert grant["ok"] is True, "预算不足时应让出聊天模型再授予，而不是拒绝"
    assert reaped == [43123], "没有真的去收割 LLM 端口"


def test_budget_mode_refuses_rather_than_killing_a_running_media_job():
    """让出只对聊天模型自动进行。杀掉用户正在跑的生成作业不是能静默做的事。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=50_000_000_000))
    budget = FakeBudget({
        "video": Workload("video", None, 40_000_000_000, "measured"),
        "music": Workload("music", None, 40_000_000_000, "measured"),
        "llm": Workload("llm", None, 1, "measured"),
    })
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=budget)
    arbiter.acquire_heavy("video", "job-1", params={}, key=None)

    grant = arbiter.acquire_heavy("music", "job-2", params={}, key=None)

    assert grant["ok"] is False
    assert grant["reason"]["code"] == "insufficient_budget"


# ---- Task 3: parameterless queries answer ownership, not budget arithmetic --
# (R-budget-13)

def test_a_parameterless_query_never_answers_insufficient_budget():
    """R-budget-13：无参问的是归属，不是容量。拿不到参数就产出空壳 workload，
    再撞上「一件 unavailable 整组保守」，会与机器多大无关地恒为拒绝。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=60 * GIB))
    budget = FakeBudget({
        "llm": Workload("llm", "model-a", 30 * GIB, "measured"),
        "video": Workload("video", None, 27 * GIB, "measured"),
    })
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "model-a", params={}, key="model-a")

    answer = arbiter.can_start_heavy("llm")          # 无参

    assert answer["reason"] is None or answer["reason"]["code"] != "insufficient_budget"


def test_the_model_switch_path_stays_reachable_with_a_model_resident():
    """已复现的回归：驻留模型后 desk_state 的 can_start.llm 恒为 insufficient_budget，
    前端只对 llm_already_held 放行，于是「换模型」按钮灰掉。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=60 * GIB))
    budget = FakeBudget({
        "llm": Workload("llm", "model-a", 30 * GIB, "measured"),
        "video": Workload("video", None, 27 * GIB, "measured"),
    })
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "model-a", params={}, key="model-a")

    llm_button = arbiter.desk_state()["can_start"]["llm"]

    assert llm_button["ok"] is True or llm_button["reason"]["code"] == "llm_already_held"


def test_a_parameterless_media_query_still_reports_media_busy():
    """归属分支保留唯一与容量无关的那条拒绝：媒体在跑时不能开第二个媒体。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=200 * GIB))
    budget = FakeBudget({"video": Workload("video", None, 1, "measured"),
                         "music": Workload("music", None, 1, "measured"),
                         "llm": Workload("llm", None, 1, "measured")})
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)
    arbiter.acquire_heavy("video", "job-1", params={}, key=None)

    answer = arbiter.can_start_heavy("music")

    assert answer["ok"] is False
    assert answer["reason"]["code"] == "media_busy"


def test_a_query_with_params_still_does_the_budget_arithmetic():
    """反向：带参数的容量判定不受本任务影响，仍按预算判。"""
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=10 * GIB))
    budget = FakeBudget({"llm": Workload("llm", "m", 5 * GIB, "measured"),
                         "video": Workload("video", None, 40 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)

    answer = arbiter.can_start_heavy("video", params={"width": 1024}, key="h3")

    assert answer["ok"] is False
    assert answer["reason"]["code"] == "insufficient_budget"


def test_can_start_heavy_and_desk_state_agree_on_ownership_in_legacy_mode():
    """回归（复审 Important）：legacy 模式（不传 budget，如 e2e 测试台面）下，
    `can_start_heavy` 和 `desk_state()["can_start"]` 问的是同一个「无参归属」问题，
    必须给出同一个答案。`_state_for` 的 `can_start` 闭包若不按 `self._budget` 分流、
    无条件换成 `_ownership_answer`，会把 legacy 模式自己的排他表（任何一件重活在跑，
    其余全部拒绝——模块顶部 docstring 承诺的「byte-for-byte pre-Task-7 rule table」）
    悄悄收窄成「只有媒体挡媒体」，而 `can_start_heavy` 的 legacy 分支毫不知情，仍按
    旧表判。两个入口、同一个 arbiter 状态、同一个无参问题，答案却不一致——这条只被
    Playwright e2e（tests/e2e/test_mutex_ui.py）间接撞到，没有单测钉住。
    """
    arbiter = Arbiter(llm_port=43125)   # 不传 budget：legacy 模式
    arbiter.acquire_heavy("video", "job-1")

    direct = arbiter.can_start_heavy("llm")
    via_state = arbiter.desk_state()["can_start"]["llm"]

    assert direct["ok"] is False
    assert direct["reason"]["code"] == "media_busy"
    assert (via_state["ok"], via_state["reason"]) == (direct["ok"], direct["reason"])


def test_acquire_heavy_without_capacity_input_is_refused_in_budget_mode():
    """R-budget-13 的判据同样管授予：拿不到容量输入时拒绝，不是照常授予。

    无参进 `_cost` 只能拿到 bytes_needed=0 / source=unavailable 的空壳。空壳若是
    当下唯一一件，`fits` 判它装得下并授予，`_workloads` 里从此留下一个 0 字节的
    幽灵持有者，往后每一次 `fits` 都把它整件漏算——一件 100 GiB 的作业会被当成
    不占内存，第二件重活于是被放行。
    """
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=60 * GIB))
    budget = FakeBudget({"llm": Workload("llm", "model-a", 30 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)

    grant = arbiter.acquire_heavy("llm", "model-a")        # 无 params、无 key

    assert grant["ok"] is False
    assert grant["reason"]["code"] == "capacity_unknown"
    assert arbiter._workloads == {}, "被拒绝的调用不许在账上留下持有者"
    assert arbiter.desk_state()["holder"] is None


def test_legacy_mode_still_accepts_a_parameterless_acquire():
    """判据是「这次调用有没有容量输入」，不是「有没有接预算」——没接预算的
    legacy 模式压根没有预算算术可做，它的无参授予必须原样可用（e2e 台面就这么调）。"""
    arbiter = Arbiter(llm_port=43125)

    grant = arbiter.acquire_heavy("llm", "model-a")

    assert grant["ok"] is True


def test_evicting_the_llm_leaves_a_concurrent_media_holder_intact():
    """预算模式下的自动让出只该动让出集合里的那些（R-arbiter-05「最小让出」）。

    `_replace_all` 是 legacy 的单槽语义：把 _holders / _workloads 整个清空。
    预算模式下真的可能有两件重活共存，这时让出聊天模型会把并发的媒体作业一起
    从台账上抹掉——**而那个作业的进程还在跑**。后果：它的 token 再也释放不掉
    （release_heavy 返回 not_holder）、media_busy 变 false、它占的内存不再计入预算，
    于是后续判定会放行过量的重活。
    """
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=100_000_000_000))
    budget = FakeBudget({
        "llm": Workload("llm", "model-a", 60_000_000_000, "measured"),
        # 视频要得少，让出它不够用（100 - 10 + 50 + 60 = 刚好塞满，plan 要求严格富余），
        # 于是最小让出只剩「卸聊天模型」这一种——正是本条要测的那条路径。
        "video": Workload("video", None, 10_000_000_000, "measured"),
        "music": Workload("music", None, 50_000_000_000, "measured"),
    })
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=budget,
                      reaper=lambda port, **kw: SimpleNamespace(
                          ok=True, port=port, killed_pids=[], error=None))
    llm = arbiter.acquire_heavy("llm", "model-a", params={}, key="model-a")
    video = arbiter.acquire_heavy("video", "job-a", params={}, key=None)
    assert llm["ok"] and video["ok"], "前置：两件要先共存得起来"

    # music 要 50G，当前 60+10=70 已占，可用 100 ⇒ 装不下；只有让出 llm（60）才够。
    music = arbiter.acquire_heavy("music", "job-b", params={}, key=None)
    assert music["ok"] is True

    kinds = {h["kind"] for h in [arbiter.desk_state()["holder"]] if h}
    all_kinds = {w.kind for w in arbiter._workloads.values()}
    assert "video" in all_kinds, f"并发的视频作业被一起抹掉了，它的进程还在跑：{all_kinds}"
    assert "llm" not in all_kinds, f"聊天模型本该被让出：{all_kinds}"
    assert arbiter.release_heavy(video["token"])["ok"] is True, "视频作业的 token 释放不掉了"


def test_budget_mode_judges_against_the_machine_capacity_not_what_is_free_now():
    """整个系统只许有一个分母（R-budget-16）。

    真机上撞到的：for_chat 按静态能力算额度（107.5 GiB），而仲裁器的 fits 仍拿
    此刻可用内存（61 GiB）去判——于是模型拿到一个按 107.5 GiB 尺寸算出的 KV 额度，
    再被 61 GiB 的现实拒掉，**任何模型都加载不了**。单测当时全绿，因为夹具喂的
    两个数恰好一致；真机上它们差了 46 GiB。
    """
    class Cap:
        def capacity_bytes(self): return 100_000_000_000
        def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None):
            return Workload(kind, key, 80_000_000_000, "predicted")

    # 此刻可用只有 40G，但这台机器的能力是 100G —— 该按 100G 判。
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=40_000_000_000))
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=Cap())

    answer = arbiter.can_start_heavy("llm", params={}, key="model-a")

    assert answer["ok"] is True, f"拿此刻可用内存当分母了：{answer}"


def test_budget_mode_without_a_capacity_falls_back_to_available_memory():
    """问不出机器能力时退回可用内存——保守，且不会让台面整个不可用。"""
    class NoCap:
        def capacity_bytes(self): return None
        def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None):
            return Workload(kind, key, 80_000_000_000, "predicted")

    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=40_000_000_000))
    arbiter = Arbiter(llm_port=43123, memory=memory, budget=NoCap())

    assert arbiter.can_start_heavy("llm", params={}, key="model-a")["ok"] is False
