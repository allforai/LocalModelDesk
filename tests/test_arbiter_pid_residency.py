"""R-budget-14：驻留量按持有者 pid 读，不再用整机标量作差。

整机差额有两个该口径内解不掉的病，实测都已量到：

1. **只捕捉到一部分。** 2026-09-19 本机实测，只读 mmap 一个真实模型分片并逐页触碰：
   真占 4.82 GiB，`ps rss` 读到 4.84 GiB，而 `available_bytes` 的净降幅只有 2.46 GiB
   ——51%。mlx 的权重正是这种 mmap 的文件页，所以这是最要紧的那一格。
2. **分不清是谁占的。** 多件重活同时加载时，一次全局差额无法归属；旧实现用
   「只有一件待回填时才记」的闸回避它，代价是共存场景下谁都不会被回填——
   而共存正是预算模式的主用例。

按 pid 读同时解掉这两条，并让那道闸与 4 GiB 噪声下限一起消失（进程自己的 rss
不含别人的噪声，也不需要靠量级去区分「是噪声还是加载」）。
"""
from types import SimpleNamespace

import pytest

from desk.arbiter.core import Arbiter
from desk.budget.budget import Workload

GIB = 1024 ** 3


class FixedBudget:
    def __init__(self, costs):
        self._costs = costs

    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None):
        return self._costs[kind]


def _memory(available_gib=100):
    return SimpleNamespace(snapshot=lambda: SimpleNamespace(
        available_bytes=int(available_gib * GIB), total_bytes=128 * GIB, pressure="normal"))


def _arbiter(costs, resident_by_pid, pids_by_token):
    """resident_by_pid: pid -> 该进程此刻的 rss；pids_by_token: token -> 它拥有的 pid 集合。"""
    return Arbiter(
        llm_port=43200, memory=_memory(), budget=FixedBudget(costs),
        read_resident_bytes=lambda pid: resident_by_pid.get(pid, 0),
    ), pids_by_token


def test_residency_comes_from_the_holders_own_process():
    """按 pid 读：量到的是这个进程自己占了多少，与整机噪声无关。"""
    resident = {}
    arbiter = Arbiter(llm_port=43200, memory=_memory(),
                      budget=FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")}),
                      read_resident_bytes=lambda pid: resident.get(pid, 0))
    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.note_pids(granted["token"], {4242})

    resident[4242] = 30 * GIB          # 模型加载完，进程自己占了 30 GiB
    arbiter.desk_state()               # 任何一次读快照都会回填

    held = list(arbiter._workloads.values())
    assert held[0].bytes_resident == 30 * GIB


def test_two_concurrent_holders_are_each_credited_their_own_bytes():
    """旧实现在这里直接放弃记账（单件闸），而共存正是预算模式的主用例。

    按 pid 读之后，两件同时驻留各记各的，互不串味——这是 R-budget-14 最重要的收益。
    """
    resident = {}
    arbiter = Arbiter(llm_port=43200, memory=_memory(),
                      # 两件要真能共存（50+20 ≤ 100），否则会走自动让出把 llm 抹掉，
                      # 测不到「各记各的」这件事。
                      budget=FixedBudget({"llm": Workload("llm", "m", 50 * GIB, "measured"),
                                          "video": Workload("video", None, 20 * GIB, "measured")}),
                      read_resident_bytes=lambda pid: resident.get(pid, 0))
    llm = arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.note_pids(llm["token"], {111})
    video = arbiter.acquire_heavy("video", "job-1", params={}, key=None)
    arbiter.note_pids(video["token"], {222})

    resident[111] = 30 * GIB
    resident[222] = 20 * GIB
    arbiter.desk_state()

    by_kind = {w.kind: w.bytes_resident for w in arbiter._workloads.values()}
    assert by_kind == {"llm": 30 * GIB, "video": 20 * GIB}


def test_a_holder_with_several_pids_sums_them():
    """一件重活可能有多个进程（媒体作业会起子进程），全算它头上。"""
    resident = {111: 10 * GIB, 112: 5 * GIB}
    arbiter = Arbiter(llm_port=43200, memory=_memory(),
                      budget=FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")}),
                      read_resident_bytes=lambda pid: resident.get(pid, 0))
    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.note_pids(granted["token"], {111, 112})
    arbiter.desk_state()

    assert list(arbiter._workloads.values())[0].bytes_resident == 15 * GIB


def test_residency_tracks_growth_instead_of_being_pinned_once():
    """按 pid 读是幂等查询，不是一次性采样——KV 长起来时它跟着涨，这是对的。

    旧实现必须「只填一次」，因为整机差额一旦被噪声污染就永远错；进程自己的 rss
    没有这个问题，跟涨反而让未分配量随时准确。
    """
    resident = {}
    arbiter = Arbiter(llm_port=43200, memory=_memory(),
                      budget=FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")}),
                      read_resident_bytes=lambda pid: resident.get(pid, 0))
    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.note_pids(granted["token"], {4242})

    resident[4242] = 30 * GIB
    arbiter.desk_state()
    resident[4242] = 45 * GIB          # KV 长起来了
    arbiter.desk_state()

    assert list(arbiter._workloads.values())[0].bytes_resident == 45 * GIB


def test_residency_is_clamped_to_what_the_workload_asked_for():
    """一件重活不可能占得比它要的还多；超出的部分一定是别的东西被算进来了。

    上界要在这里夹住：`plan()` 的 freed 直接吃这个值，不夹会让「让出能回收多少」偏乐观。
    """
    resident = {4242: 200 * GIB}
    arbiter = Arbiter(llm_port=43200, memory=_memory(),
                      budget=FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")}),
                      read_resident_bytes=lambda pid: resident.get(pid, 0))
    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.note_pids(granted["token"], {4242})
    arbiter.desk_state()

    assert list(arbiter._workloads.values())[0].bytes_resident == 80 * GIB


def test_a_holder_with_no_pid_yet_stays_at_zero():
    """进程还没起来（acquire 在 spawn 之前）就记 0，退回保守——spec 的兜底。"""
    arbiter = Arbiter(llm_port=43200, memory=_memory(),
                      budget=FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")}),
                      read_resident_bytes=lambda pid: 99 * GIB)
    arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.desk_state()

    assert list(arbiter._workloads.values())[0].bytes_resident == 0


def test_an_unreadable_pid_records_zero_not_a_guess():
    """进程已经没了、ps 读不到——记 0，不猜。"""
    def boom(pid):
        raise OSError("no such process")

    arbiter = Arbiter(llm_port=43200, memory=_memory(),
                      budget=FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")}),
                      read_resident_bytes=boom)
    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.note_pids(granted["token"], {4242})
    arbiter.desk_state()

    assert list(arbiter._workloads.values())[0].bytes_resident == 0


def test_note_pids_for_an_unknown_token_is_ignored():
    """迟到的 note_pids（持有者已经释放）不该凭空造出一条记录。"""
    arbiter = Arbiter(llm_port=43200, memory=_memory(),
                      budget=FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")}),
                      read_resident_bytes=lambda pid: 1)
    arbiter.note_pids("no-such-token", {4242})
    # 断言要落在 note_pids 真正写的那本账上。原来写的是 `_workloads == {}`——
    # 那个字典 note_pids 压根不碰，改不改实现都成立，是条假测试。
    assert arbiter._holder_pids == {}


def test_released_holder_stops_being_counted():
    """释放之后 pid 记录要跟着清掉，否则 token 复用会拿到上一任的进程。"""
    resident = {4242: 30 * GIB}
    arbiter = Arbiter(llm_port=43200, memory=_memory(),
                      budget=FixedBudget({"llm": Workload("llm", "m", 80 * GIB, "measured")}),
                      read_resident_bytes=lambda pid: resident.get(pid, 0))
    granted = arbiter.acquire_heavy("llm", "m", params={}, key="m")
    arbiter.note_pids(granted["token"], {4242})
    arbiter.desk_state()
    arbiter.release_heavy(granted["token"])

    assert arbiter._workloads == {}
    assert arbiter._holder_pids == {}


def test_reading_residency_is_real_on_this_machine():
    """口径探针：真起一个占内存的子进程，确认 read_resident_bytes 读得到。

    这条钉住的是「实现真的能从操作系统拿到数」，不是某个具体数值——
    数值本身随机器与时刻变。只起 512 MiB，跑得快且对机器无压力。
    """
    import subprocess
    import sys
    import textwrap
    from desk.arbiter.core import read_resident_bytes

    script = textwrap.dedent("""
        import os, sys
        n = 512 * 1024 ** 2
        b = bytearray(n)
        b[::4096] = os.urandom(n // 4096)
        sys.stdout.write("ready\\n"); sys.stdout.flush()
        sys.stdin.readline()
    """)
    child = subprocess.Popen([sys.executable, "-c", script],
                             stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert child.stdout.readline().strip() == "ready"
        measured = read_resident_bytes(child.pid)
    finally:
        child.stdin.write("\n")
        child.stdin.flush()
        child.wait()

    assert measured > 400 * 1024 ** 2, f"读到的驻留量不合理：{measured}"


def test_reading_a_dead_pid_returns_zero():
    from desk.arbiter.core import read_resident_bytes

    assert read_resident_bytes(999_999) == 0
