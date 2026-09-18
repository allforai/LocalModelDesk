"""R-budget-07 / R-budget-10：共存是集合问题，来源取最弱者。"""
import itertools
import pytest
from desk.budget.budget import Workload, fits, plan

GIB = 1024 ** 3


def w(kind, bytes_gib, source="measured", key=None):
    return Workload(kind=kind, key=key, bytes_needed=int(bytes_gib * GIB), source=source)


def test_one_workload_that_fits_is_ok():
    assert fits([w("chat", 80)], 120 * GIB).ok


def test_one_workload_that_does_not_fit_reports_the_shortfall():
    v = fits([w("chat", 150)], 120 * GIB)
    assert not v.ok
    assert v.shortfall_bytes == 30 * GIB
    assert v.needed_bytes == 150 * GIB and v.available_bytes == 120 * GIB


def test_two_that_fit_together_are_ok():
    assert fits([w("chat", 80), w("video", 30)], 120 * GIB).ok


def test_two_that_each_fit_alone_but_not_together_are_refused():
    """这是两两判断答不了的那一类：各自都装得下，合起来装不下。"""
    assert fits([w("chat", 80)], 120 * GIB).ok
    assert fits([w("video", 80)], 120 * GIB).ok
    assert not fits([w("chat", 80), w("video", 80)], 120 * GIB).ok


def test_three_way_is_not_the_conjunction_of_pairs():
    """三件两两都能共存，三件一起却装不下——合取判断会错放。"""
    trio = [w("chat", 40), w("video", 40), w("music", 40)]
    for a, b in itertools.combinations(trio, 2):
        assert fits([a, b], 100 * GIB).ok
    assert not fits(trio, 100 * GIB).ok


def test_source_is_the_weakest_of_the_group():
    assert fits([w("chat", 10), w("video", 10)], 100 * GIB).source == "measured"
    assert fits([w("chat", 10), w("video", 10, "predicted")], 100 * GIB).source == "predicted"
    assert fits([w("chat", 10, "measured"), w("video", 10, "predicted"),
                 w("music", 10, "unavailable")], 100 * GIB).source == "unavailable"


def test_unavailable_source_refuses_coexistence_even_when_the_numbers_fit():
    """没量过就不放宽：数字上装得下，也不许两件并存。"""
    pair = [w("chat", 10, "unavailable"), w("video", 10)]
    assert not fits(pair, 500 * GIB).ok
    assert fits([w("chat", 10, "unavailable")], 500 * GIB).ok    # 单件照常


def test_empty_group_fits():
    assert fits([], 0).ok


def test_plan_releases_the_cheapest_set_that_makes_room():
    """最小让出：腾出够用的那些，不是全卸。"""
    resident = [w("chat", 80, key="llama"), w("music", 10, key="m3")]
    p = plan([w("video", 30)], resident, 120 * GIB)
    assert p.ok
    assert [r.key for r in p.release] == ["m3"]      # 卸掉 10 就够，不必动 80


def test_plan_releases_nothing_when_it_already_fits():
    p = plan([w("video", 10)], [w("chat", 80, key="llama")], 120 * GIB)
    assert p.ok and p.release == ()


def test_plan_reports_failure_when_even_full_eviction_is_not_enough():
    p = plan([w("video", 200)], [w("chat", 80, key="llama")], 120 * GIB)
    assert not p.ok
    assert p.verdict.shortfall_bytes > 0


def test_resident_bytes_are_not_counted_twice():
    """R-budget-12：available_bytes 已经排除了常驻内存，再整个加一遍就是扣两遍。

    实测（2026-09-18 本机）：子进程真实占用 6 GiB，available_bytes 降 4.7 GiB，
    释放后回升——它确实随常驻占用变化。
    """
    resident = Workload("chat", "m", int(80 * GIB), "measured", bytes_resident=int(80 * GIB))
    # 80 GiB 全部已分配 ⇒ 对剩余额度不再有任何占用
    assert fits([resident, w("video", 30)], 40 * GIB).ok


def test_the_unallocated_half_of_a_resident_still_counts():
    """懒分配是这条的理由：已驻留模型的权重占掉了，被授予的 KV 额度还没占，
    那部分仍是对内存的承诺，必须留着。"""
    resident = Workload("chat", "m", int(80 * GIB), "measured", bytes_resident=int(50 * GIB))
    # 未分配 30 GiB 仍要计 ⇒ 30 + 30 = 60 > 40
    assert not fits([resident, w("video", 30)], 40 * GIB).ok


def test_a_candidate_that_is_not_resident_counts_in_full():
    """还没授予的候选 bytes_resident 恒为 0——它还没占任何东西。"""
    assert w("video", 30).bytes_resident == 0
    assert not fits([w("chat", 80), w("video", 30)], 100 * GIB).ok


def test_noisy_measurement_never_makes_a_workload_contribute_headroom():
    """实测可能因采样噪声略大于 bytes_needed；负数会让一件重活反过来「贡献」额度。"""
    noisy = Workload("chat", "m", int(10 * GIB), "measured", bytes_resident=int(12 * GIB))
    verdict = fits([noisy], 1 * GIB)
    assert verdict.needed_bytes == 0
    assert verdict.ok


def test_plan_frees_only_the_resident_bytes_not_the_whole_need():
    """让出一件已驻留重活，物理上只回收它已经分配的那部分（bytes_resident）。

    未分配的那份从没占过内存，回收不了；plan() 若按 bytes_needed 算 freed，会把
    可用余量虚增到 5+80=85 GiB，而不是实际能回收的 5+50=55 GiB。
    """
    resident = [Workload("chat", "m", int(80 * GIB), "measured", bytes_resident=int(50 * GIB))]
    p = plan([w("video", 20)], resident, 5 * GIB)
    assert p.ok
    assert p.release == tuple(resident)
    assert p.verdict.available_bytes == 55 * GIB     # 5 + 50，不是 5 + 80


def test_bytes_resident_defaults_to_zero_so_existing_call_sites_keep_working():
    """既有几十处四参构造不用改——加字段必须带默认值。"""
    assert Workload("video", None, 1, "measured").bytes_resident == 0
