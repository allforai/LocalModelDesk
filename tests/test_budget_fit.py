"""单个模型适不适合这台机器：纯函数，四态，无 IO（R-budget-fit）。

resources 目录页的常驻标记和首运报告都读这同一个函数的结果，不各自拼一套判断。
"""
from desk.budget.budget import FIT_TIGHT_FRACTION, assess_fit

GIB = 1024 ** 3


def test_comfortable_headroom_is_fits():
    v = assess_fit(16 * GIB, 100 * GIB)
    assert v.level == "fits"
    assert v.needed_bytes == 16 * GIB
    assert v.available_bytes == 100 * GIB
    assert v.headroom_bytes == 84 * GIB
    assert v.shortfall_bytes == 0


def test_right_at_the_tight_boundary_is_still_fits():
    """边界本身不算紧：卡线的那一口气算够，比较用严格大于。"""
    needed = int(100 * GIB * FIT_TIGHT_FRACTION)
    assert assess_fit(needed, 100 * GIB).level == "fits"


def test_one_byte_past_the_boundary_is_tight():
    needed = int(100 * GIB * FIT_TIGHT_FRACTION) + 1
    v = assess_fit(needed, 100 * GIB)
    assert v.level == "tight"
    assert v.shortfall_bytes == 0
    assert v.headroom_bytes >= 0


def test_needing_more_than_available_is_too_big_and_says_by_how_much():
    v = assess_fit(120 * GIB, 100 * GIB)
    assert v.level == "too_big"
    assert v.shortfall_bytes == 20 * GIB
    assert v.available_bytes == 100 * GIB
    assert v.needed_bytes == 120 * GIB


def test_needing_exactly_available_still_runs_not_too_big():
    """刚好吃满不算超——「超」的边界也用严格大于。"""
    assert assess_fit(100 * GIB, 100 * GIB).level != "too_big"


def test_unknown_capacity_recommends_nothing_not_a_guess():
    """算不出机器能力时不许拿别的数顶替——这是本功能存在的意义。"""
    v = assess_fit(16 * GIB, None)
    assert v.level == "unknown"
    assert v.available_bytes is None
    assert v.needed_bytes == 16 * GIB
    assert v.headroom_bytes is None
    assert v.shortfall_bytes == 0
