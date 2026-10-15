"""A-40/A-43: chat counting, recent UI chat, and who loaded the model."""
from desk.llm.backend import BackendHttpError
from tests.llm.llm_fakes import make_loaded, make_service

OK = {
    "choices": [{"message": {"content": "答"}, "finish_reason": "stop"}],
    "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
}
STREAM = [
    {"choices": [{"delta": {"content": "答"}}]},
    {"choices": [{"delta": {}, "finish_reason": "stop"}],
     "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2}},
]


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def test_status_reports_zero_chats_and_no_recent_ui_chat_initially(tmp_path):
    testbed = make_service(tmp_path)
    status = testbed.service.status()
    assert status["active_chats"] == 0
    assert status["ui_chat_recent"] is False
    assert status["loaded_by"] is None


def test_loaded_by_follows_the_load_origin(tmp_path):
    testbed = make_service(tmp_path)
    testbed.service.load("glm", origin="agent")
    testbed.service.wait_settled()
    assert testbed.service.status()["loaded_by"] == "agent"
    testbed.service.load("glm")
    testbed.service.wait_settled()
    assert testbed.service.status()["loaded_by"] == "ui"


def test_unload_clears_loaded_by(tmp_path):
    testbed = make_loaded(tmp_path)
    testbed.service.unload()
    assert testbed.service.status()["loaded_by"] is None


def test_ui_chat_marks_recent_for_300_seconds_and_agent_chat_does_not(tmp_path):
    clock = Clock()
    testbed = make_loaded(tmp_path, backend_kw={"chat_result": OK}, clock=clock)
    testbed.service.chat_completion({"messages": [], "origin": "agent"})
    assert testbed.service.status()["ui_chat_recent"] is False
    testbed.service.chat_completion({"messages": []})
    assert testbed.service.status()["ui_chat_recent"] is True
    clock.now += 299
    assert testbed.service.status()["ui_chat_recent"] is True
    clock.now += 2
    assert testbed.service.status()["ui_chat_recent"] is False


def test_stream_counts_while_open_and_decrements_once_on_finish(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"stream": STREAM})
    events = testbed.service.chat_stream({"messages": []})
    first = next(events)
    assert first is not None
    assert testbed.service.status()["active_chats"] == 1
    list(events)
    assert testbed.service.status()["active_chats"] == 0


def test_stream_closed_midway_decrements_exactly_once(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"stream": STREAM})
    events = testbed.service.chat_stream({"messages": []})
    next(events)
    events.close()
    events.close()
    assert testbed.service.status()["active_chats"] == 0


def test_stream_never_iterated_does_not_leak_a_count(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"stream": STREAM})
    events = testbed.service.chat_stream({"messages": []})
    del events
    assert testbed.service.status()["active_chats"] == 0


def test_completion_error_decrements(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"chat_error": BackendHttpError("boom")})
    try:
        testbed.service.chat_completion({"messages": []})
    except Exception:
        pass
    assert testbed.service.status()["active_chats"] == 0


def test_load_route_passes_origin(tmp_path):
    from desk.llm.routes import build_routes

    testbed = make_service(tmp_path)
    load = next(r for r in build_routes(testbed.service) if r.path == "/api/llm/load")
    result = load.handler({"key": "glm", "origin": "agent"})
    assert result.status == 202
    testbed.service.wait_settled()
    assert testbed.service.status()["loaded_by"] == "agent"
