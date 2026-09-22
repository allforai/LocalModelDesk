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


# ---- still_holds：台面还认不认这件重活 ---------------------------------

def test_still_holds_finds_a_coexisting_holder_not_just_the_last_one():
    """媒体作业与聊天共存时，聊天必须仍算「被持有」。

    这是共存的判据：媒体在不在跑与「我还能不能用这个模型」无关——预算在授予那一刻
    就按「聊天用满窗口」把 KV 预留进去了（budget.cost("llm") 报的 bytes_needed
    就是权重加满窗 KV），媒体能开正说明两者一起装得下。
    """
    from desk.arbiter.state import still_holds
    desk = {"holders": [{"kind": "llm", "label": "superqwen"},
                        {"kind": "video", "label": "job-2"}],
            "holder": {"kind": "video", "label": "job-2"},
            "media_busy": True}
    assert still_holds(desk, "llm", "superqwen"), "共存时聊天被判成没被持有"


def test_still_holds_is_false_once_the_holder_is_gone():
    from desk.arbiter.state import still_holds
    desk = {"holders": [{"kind": "video", "label": "job-2"}], "media_busy": True}
    assert not still_holds(desk, "llm", "superqwen")


def test_still_holds_distinguishes_labels_within_a_kind():
    """换了模型也是「不再持有」——不能只看 kind。"""
    from desk.arbiter.state import still_holds
    desk = {"holders": [{"kind": "llm", "label": "gemma"}]}
    assert not still_holds(desk, "llm", "superqwen")


def test_still_holds_falls_back_to_the_single_holder_field():
    """台面状态没有 holders 时退回读 holder——旧形状不能让判据静默变成 False。"""
    from desk.arbiter.state import still_holds
    assert still_holds({"holder": {"kind": "llm", "label": "superqwen"}}, "llm", "superqwen")
    assert not still_holds({"holder": None}, "llm", "superqwen")


def test_still_holds_survives_junk_entries():
    from desk.arbiter.state import still_holds
    desk = {"holders": [None, "nonsense", {"kind": "llm", "label": "superqwen"}]}
    assert still_holds(desk, "llm", "superqwen")
    assert not still_holds({}, "llm", "superqwen")
