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
