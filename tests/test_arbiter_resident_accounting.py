"""R-budget-12：已分配的字节由实测回填，不由估算。"""
from types import SimpleNamespace

from desk.arbiter.core import RESIDENT_MIN_BYTES, Arbiter
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


def test_the_grant_itself_backfills_so_the_next_reader_is_not_the_first():
    """回填不能只便宜下一次读者：`_grant` 一返回，这次授予的 `bytes_resident`
    就必须已经量好。

    这条原先断言 `granted["state"]["can_start"]["media"]["ok"] is True`。那个断言
    在 R-budget-13（budget 模式的 `can_start` 改走 `_ownership_answer`，完全不看
    内存）之后恒为真，与回填、与这里的 30 GiB 快照都没有关系——一条从此不可能变红
    的测试不构成证据，所以改断在真正吃回填的两个地方：`_workloads` 里的值本身，
    以及紧接着一次**带参数**的容量问答。删掉 `_state_for` 里的 `_backfill_resident`
    这一行，第一条断言立刻变红。
    """
    # 授予 llm 时基线可用 100 GiB；_grant → _state_for 里读到的快照已经降到
    # 30 GiB，说明 llm 实占了 70 GiB，未分配只剩 80-70=10 GiB。
    memory = StepMemory([100 * GIB, 100 * GIB, 30 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 15 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43125, memory=memory, budget=budget)

    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")

    assert granted["ok"] is True
    # 授予这一步自己就量到了：不必等 2 秒后的 desk_state 轮询。
    assert list(arbiter._workloads.values())[0].bytes_resident == 70 * GIB
    # 不回填：llm 整件 80 GiB 计入，80+15=95 > 30 ⇒ 判「装不下」。
    # 回填后：llm 未分配只剩 10 GiB，10+15=25 <= 30 ⇒ 判「装得下」。
    assert arbiter.can_start_heavy("video", params={}, key=None)["ok"] is True


def test_two_pending_workloads_do_not_each_book_the_whole_drop():
    """两件同时待回填时一个字节都不记——分不清是谁占的就不记。

    available_bytes 是整机口径的一个标量，两件重活一起加载时它的降幅是两件之和。
    对每件各算一次「基线 − 当前」会把同一批字节记两遍：这里 A 需 80、B 需 27，
    基线都是 120，一起加载后可用降到 63，各记 57 时 A 的未分配从 50 被算成 23，
    `fits` 整组少扣 27 GiB，足以放行一件本该拒绝的作业。
    """
    memory = StepMemory([
        120 * GIB, 120 * GIB, 120 * GIB,     # llm 授予期间（两次 _decide + _state_for）
        120 * GIB, 120 * GIB, 120 * GIB,     # video 授予期间：两件都还没开始加载
        63 * GIB,                             # 两件一起加载完：整机降了 57 GiB
    ])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 27 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43126, memory=memory, budget=budget)
    assert arbiter.acquire_heavy("llm", "m", params={}, key="m")["ok"] is True
    assert arbiter.acquire_heavy("video", "job-1", params={}, key="h3")["ok"] is True

    arbiter.desk_state()          # 读快照 63 GiB，顺带尝试回填

    resident = [w.bytes_resident for w in arbiter._workloads.values()]
    assert resident == [0, 0], f"两件待回填时不许各记一遍全局降幅，实得 {resident}"


def test_the_measured_drop_is_clamped_to_what_the_workload_asked_for():
    """回填值的上界是 bytes_needed：一件重活不可能占得比它要的还多。

    超出的部分一定是别人的分配被算到了它头上。`_unallocated` 的 max(...,0) 只保护
    `fits`；`plan()` 的 freed 吃的是原值，虚高的 bytes_resident 会让它以为让出这件
    就腾得出地方。
    """
    # 基线 120 GiB，加载后降到 20 GiB（别的进程也在吃内存）⇒ 降幅 100 GiB，
    # 但这件重活总共只要 27 GiB。
    memory = StepMemory([120 * GIB, 120 * GIB, 120 * GIB, 20 * GIB])
    budget = FixedBudget({"video": Workload("video", None, 27 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43127, memory=memory, budget=budget)
    arbiter.acquire_heavy("video", "job-1", params={}, key="h3")

    arbiter.desk_state()

    assert list(arbiter._workloads.values())[0].bytes_resident == 27 * GIB


def test_a_drop_too_small_to_tell_from_noise_is_not_recorded():
    """低于 RESIDENT_MIN_BYTES 的降幅当作没测到，记 0。

    第一个采样点就在 `_grant` 紧接着的 `_state_for` 里，那一刻模型一行权重都还没读
    进来；而 free+inactive+purgeable+speculative 是整机口径，本机实测负载下相邻两次
    读数就能差 1.49 GiB。没有下限时，「只填一次」会把 bytes_resident 永久钉在噪声上。
    """
    drop = RESIDENT_MIN_BYTES - 1
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 100 * GIB - drop])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43128, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "m", params={}, key="m")

    arbiter.desk_state()

    assert list(arbiter._workloads.values())[0].bytes_resident == 0


def test_a_drop_at_the_floor_is_recorded():
    """下限是「低于就不记」，不是「小于等于就不记」——恰好到线的降幅要记下来，
    否则这条下限就没有一个可说明的边界。"""
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 100 * GIB - RESIDENT_MIN_BYTES])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")})
    arbiter = Arbiter(llm_port=43129, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "m", params={}, key="m")

    arbiter.desk_state()

    assert list(arbiter._workloads.values())[0].bytes_resident == RESIDENT_MIN_BYTES


def test_a_rise_in_available_memory_records_zero_not_a_negative():
    """别的进程释放内存导致可用不降反升时，记 0 而不是负数。"""
    memory = StepMemory([100 * GIB, 100 * GIB, 100 * GIB, 120 * GIB])
    budget = FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured"),
                          "video": Workload("video", None, 1, "measured")})
    arbiter = Arbiter(llm_port=43124, memory=memory, budget=budget)
    arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.can_start_heavy("video", params={}, key=None)
    assert list(arbiter._workloads.values())[0].bytes_resident == 0
