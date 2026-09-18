"""R-budget-12：已分配的字节由实测回填，不由估算。"""
from types import SimpleNamespace

from desk.arbiter.core import Arbiter
from desk.budget.budget import Workload

GIB = 1024 ** 3


class StepMemory:
    """按调用次序吐出预设的 available_bytes，模拟「加载后可用内存下降」。"""

    def __init__(self, values):
        self._values = list(values)
        self.calls = 0

    def snapshot(self):
        value = self._values[min(self.calls, len(self._values) - 1)]
        self.calls += 1
        return SimpleNamespace(available_bytes=value, total_bytes=128 * GIB, pressure="normal")


class FixedBudget:
    def __init__(self, costs):
        self._costs = costs

    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None):
        return self._costs[kind]


def test_resident_bytes_are_backfilled_from_the_measured_drop():
    # 授予时可用 100 GiB；加载完成后降到 70 GiB ⇒ 实际占了 30 GiB
    # 前三个值覆盖 acquire 期间的全部快照读取（_decide 两次 + _grant→_state_for 一次），
    # 这样夹具不依赖精确的调用次数；第四个值是加载完成后的可用内存。
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 70 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 27 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43124, memory=memory, budget=budget)
    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")
    assert granted["ok"] is True

    arbiter.can_start_heavy("video", params={}, key=None)   # 这一次读快照，顺带回填

    held = list(arbiter._workloads.values())
    assert held and held[0].bytes_resident == 30 * GIB


def test_backfill_happens_once_and_never_grows():
    """回填后不再更新：KV 慢慢长起来时若跟着涨，未分配会越算越小，
    最终等于把这件重活当成不占内存。"""
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 70 * GIB, 40 * GIB, 40 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 1, "measured")})
    arbiter = Arbiter(llm_port=43124, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.can_start_heavy("video", params={}, key=None)
    first = list(arbiter._workloads.values())[0].bytes_resident
    arbiter.can_start_heavy("video", params={}, key=None)
    assert list(arbiter._workloads.values())[0].bytes_resident == first


def test_a_rise_in_available_memory_records_zero_not_a_negative():
    """别的进程释放内存导致可用不降反升时，记 0 而不是负数。"""
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 120 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 1, "measured")})
    arbiter = Arbiter(llm_port=43124, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.can_start_heavy("video", params={}, key=None)
    assert list(arbiter._workloads.values())[0].bytes_resident == 0
