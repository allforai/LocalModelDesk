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


def test_can_start_field_reflects_the_backfill_from_this_same_grant():
    """回填不能只便宜下一次读者：这一次 `_grant` 返回、广播给订阅者的 `state`
    里的 `can_start` 字段，也必须看见刚测出的 `bytes_resident`。

    `_state_for` 内部先读快照、跑 `_backfill_resident`，`can_start` 用的
    `resident` 若是调用方在进 `_state_for` 之前就捕获好的旧值，这次回填只改了
    `self._workloads`（供下一次读者受益），并不会反映到这次返回值——刚授予一件
    重活后，`can_start` 会把它的驻留量误判成 0，偏保守地判一次「暂时不能开」。
    """
    # 授予 llm 时基线可用 100 GiB；_grant → _state_for 里读到的快照已经降到
    # 30 GiB，说明 llm 实占了 70 GiB，未分配只剩 80-70=10 GiB。
    memory = StepMemory([100 * GIB, 100 * GIB, 30 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 15 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)

    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")

    assert granted["ok"] is True
    # 用旧（回填前）的 resident：llm 记满未分配 80 GiB，80+15=95 > 30，误判「装不下」。
    # 用回填后的 resident：llm 未分配只剩 10 GiB，10+15=25 <= 30，正确判「装得下」。
    assert granted["state"]["can_start"]["media"]["ok"] is True


def test_a_rise_in_available_memory_records_zero_not_a_negative():
    """别的进程释放内存导致可用不降反升时，记 0 而不是负数。"""
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 120 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 1, "measured")})
    arbiter = Arbiter(llm_port=43124, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.can_start_heavy("video", params={}, key=None)
    assert list(arbiter._workloads.values())[0].bytes_resident == 0
