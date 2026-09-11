"""Transition-table tests for the pure arbiter state machine (R-arbiter-01/04)."""
import pytest

from desk.arbiter.state import (
    Decision, Holder, PHASE_ACQUIRING, PHASE_HELD, plan_acquire,
)


def holder(kind, phase=PHASE_HELD):
    return Holder(kind=kind, label="x", token="tok", since=0.0, phase=phase)


def test_idle_llm_grants():
    assert plan_acquire(None, "llm") == Decision("grant")


@pytest.mark.parametrize("kind", ["video", "music"])
def test_idle_media_grants(kind):
    assert plan_acquire(None, kind) == Decision("grant")


@pytest.mark.parametrize("kind", ["video", "music"])
def test_llm_held_media_evicts_then_grants(kind):
    assert plan_acquire(holder("llm"), kind).action == "evict_then_grant"


def test_llm_held_llm_refused():
    d = plan_acquire(holder("llm"), "llm")
    assert (d.action, d.reason_code) == ("refuse", "llm_already_held")


@pytest.mark.parametrize("held", ["video", "music"])
@pytest.mark.parametrize("kind", ["llm", "video", "music"])
def test_media_held_refuses_everything(held, kind):
    d = plan_acquire(holder(held), kind)
    assert (d.action, d.reason_code) == ("refuse", "media_busy")


@pytest.mark.parametrize("kind", ["llm", "video", "music"])
def test_acquiring_phase_refuses(kind):
    d = plan_acquire(holder("video", phase=PHASE_ACQUIRING), kind)
    assert (d.action, d.reason_code) == ("refuse", "transition_in_progress")


def test_unknown_kind_refused():
    d = plan_acquire(None, "quantum")
    assert (d.action, d.reason_code) == ("refuse", "unknown_kind")


def test_refusals_carry_messages():
    assert plan_acquire(holder("music"), "llm").reason_message


def test_holder_carries_a_human_readable_name():
    """菜单栏只拿得到 /api/state 的 holder 视图，它必须带显示名（N2）。"""
    h = Holder(kind="llm", label="glm", token="tok", since=0.0, phase=PHASE_HELD,
               display="GLM 4.7 Flash 越狱 4bit")
    assert h.public_view()["display"] == "GLM 4.7 Flash 越狱 4bit"


def test_holder_display_falls_back_to_label_when_absent():
    """没有显式 display 时（旧调用点未传），仍需给出可读值而非 None。"""
    h = Holder(kind="music", label="job-2", token="tok", since=0.0, phase=PHASE_HELD)
    assert h.public_view()["display"] == "job-2"
