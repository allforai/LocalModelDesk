import pytest

from desk.agent_cli.decide import RETRY_CODES, Snapshot, decide
from desk.agent_cli.errors import EXIT_MEMORY

OK = {"ok": True, "reason": None, "release": [], "memory_warning": None}
EVICTS_LLM = {"ok": True, "reason": None, "release": [{"kind": "llm", "key": "glm"}], "memory_warning": None}
WAIT_MEDIA = {"ok": False, "reason": {"code": "insufficient_budget", "message": "不够"},
              "release": [{"kind": "image", "key": "qwen-image"}], "memory_warning": None}
TOO_BIG = {"ok": False, "reason": {"code": "insufficient_budget", "message": "这台机器装不下"},
           "release": [], "memory_warning": None}


def snap(**kw):
    base = dict(llm_status="idle", llm_model=None, active_chats=0, ui_chat_recent=False,
                media_running=False, precheck=OK)
    base.update(kw)
    return Snapshot(**base)


def test_loading_waits_for_both_ops():
    assert decide("chat", "glm", snap(llm_status="loading")).action == "wait"
    assert decide("image", None, snap(llm_status="loading")).action == "wait"


def test_chat_with_the_resident_model_submits_even_when_busy():
    s = snap(llm_status="loaded", llm_model="glm", active_chats=3, media_running=True, ui_chat_recent=True)
    assert decide("chat", "glm", s).action == "submit"


@pytest.mark.parametrize("kw", [dict(media_running=True), dict(active_chats=1),
                                dict(ui_chat_recent=True, llm_status="loaded", llm_model="qwen27")])
def test_chat_needing_a_swap_waits_while_busy(kw):
    assert decide("chat", "glm", snap(**kw)).action == "wait"


def test_chat_swaps_when_idle_and_precheck_ok():
    assert decide("chat", "glm", snap()).action == "swap"
    assert decide("chat", "glm", snap(llm_status="loaded", llm_model="qwen27")).action == "swap"


def test_recent_ui_chat_without_a_loaded_model_does_not_block():
    assert decide("chat", "glm", snap(ui_chat_recent=True, llm_status="error")).action == "swap"


def test_chat_waits_when_memory_can_be_freed():
    assert decide("chat", "glm", snap(precheck=WAIT_MEDIA)).action == "wait"


def test_chat_fails_with_4_when_model_too_big():
    d = decide("chat", "glm", snap(precheck=TOO_BIG))
    assert (d.action, d.exit_code) == ("fail", EXIT_MEMORY)
    assert "这台机器装不下" in d.reason and "不能强制加载" in d.reason


@pytest.mark.parametrize("kw", [dict(media_running=True), dict(active_chats=1)])
def test_image_waits_while_media_or_chat_busy(kw):
    assert decide("image", None, snap(**kw)).action == "wait"


def test_image_submits_when_idle():
    assert decide("image", None, snap()).action == "submit"


def test_image_that_would_evict_llm_waits_if_ui_chatted_recently():
    s = snap(llm_status="loaded", llm_model="glm", ui_chat_recent=True, precheck=EVICTS_LLM)
    assert decide("image", None, s).action == "wait"
    s2 = snap(llm_status="loaded", llm_model="glm", ui_chat_recent=False, precheck=EVICTS_LLM)
    assert decide("image", None, s2).action == "submit"


def test_image_waits_when_memory_can_be_freed_and_submits_otherwise():
    assert decide("image", None, snap(precheck=WAIT_MEDIA)).action == "wait"
    # A non-releasable refusal is left to the server, whose error becomes the exit code.
    assert decide("image", None, snap(precheck=TOO_BIG)).action == "submit"


def test_retry_codes():
    assert {"media_busy", "load_in_progress", "model_mismatch", "evicted", "no_model_loaded"} <= RETRY_CODES
