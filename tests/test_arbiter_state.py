"""Transition-table tests for the pure arbiter state machine (R-arbiter-01/04).

R-arbiter-01 改写：能否并存由预算判定，不由持有者种类硬编码——`plan_acquire` 的
入参从单个持有者变成一组，判定结果由 `budget` 的 `Verdict` 给出（Task 7）。
"""
from desk.arbiter.state import (
    Decision, Holder, PHASE_ACQUIRING, PHASE_HELD, plan_acquire,
)
from desk.budget.budget import Verdict

OK = Verdict(True, 0, 0, "measured", 0)
NO = Verdict(False, 100, 80, "measured", 20)
UNKNOWN = Verdict(False, 100, 80, "unavailable", 20)


def holder(kind, token="t"):
    return Holder(kind=kind, label=kind, token=token, since=0.0, phase="held")


def test_empty_holders_grants():
    assert plan_acquire((), "llm", OK).action == "grant"


def test_budget_ok_grants_even_while_media_runs():
    """这正是被改掉的那条铁律：媒体在跑，预算够，聊天照样装得下。"""
    assert plan_acquire((holder("video"),), "llm", OK).action == "grant"


def test_budget_short_refuses_with_the_numbers():
    d = plan_acquire((holder("video"),), "llm", NO)
    assert d.action == "refuse"
    assert d.reason_code == "insufficient_budget"
    assert "80" in d.reason_message and "100" in d.reason_message


def test_reason_message_names_the_source():
    assert "unavailable" in plan_acquire((holder("video"),), "llm", UNKNOWN).reason_message


def test_transition_in_progress_still_refuses():
    """既有分支不能在重构里丢掉。"""
    acquiring = Holder(kind="video", label="v", token="t", since=0.0, phase="acquiring")
    assert plan_acquire((acquiring,), "llm", OK).reason_code == "transition_in_progress"


def test_unknown_kind_still_refuses():
    assert plan_acquire((), "banana", OK).reason_code == "unknown_kind"


def test_holder_carries_a_human_readable_name():
    """菜单栏只拿得到 /api/state 的 holder 视图，它必须带显示名（N2）。"""
    h = Holder(kind="llm", label="glm", token="tok", since=0.0, phase=PHASE_HELD,
               display="GLM 4.7 Flash 越狱 4bit")
    assert h.public_view()["display"] == "GLM 4.7 Flash 越狱 4bit"


def test_holder_display_falls_back_to_label_when_absent():
    """没有显式 display 时（旧调用点未传），仍需给出可读值而非 None。"""
    h = Holder(kind="music", label="job-2", token="tok", since=0.0, phase=PHASE_HELD)
    assert h.public_view()["display"] == "job-2"
