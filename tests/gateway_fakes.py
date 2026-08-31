"""gateway shared fake backend with programmable state and call recording."""
from __future__ import annotations

import copy

LOADED_STATUS = {
    "state": "loaded",
    "loaded": {"key": "qwen3-30b", "served_id": "mlx-community/Qwen3-30B-A3B-8bit",
               "loaded_at": 1756600000.0, "meta": {}},
}
IDLE_STATUS = {"state": "idle", "loaded": None}
IDLE_DESK = {
    "holder": None, "media_busy": False,
    "can_start": {"llm": {"ok": True, "reason": None}, "media": {"ok": True, "reason": None}},
}
MEDIA_DESK = {
    "holder": {"kind": "video", "label": "H3 视频", "phase": "running"}, "media_busy": True,
    "can_start": {"llm": {"ok": False, "reason": {"code": "media_busy", "message": "视频作业进行中"}}},
}
MEDIA_REFUSAL = {"ok": False, "reason": {"code": "media_busy", "message": "视频作业进行中"}}
RESULT = {"content": "你好！", "reasoning": "用户在打招呼。", "finish_reason": "stop",
          "usage": {"prompt_tokens": 12, "completion_tokens": 7}}
EVENTS = [("reasoning", "用户在"), ("content", "好！"),
          ("finish", {"finish_reason": "stop", "usage": {"prompt_tokens": 12, "completion_tokens": 7}})]

QUERY_METHODS = {"llm_status", "desk_state", "can_start_heavy"}


class FakeBackend:
    """Programmable GatewayBackend fake that records all calls."""

    def __init__(self, *, llm=None, desk=None, can_start=None, result=None,
                 events=None, stream_error=None, completion_error=None):
        self.calls = []
        self._llm = llm if llm is not None else LOADED_STATUS
        self._desk = desk if desk is not None else IDLE_DESK
        self._can_start = can_start if can_start is not None else {"ok": True, "reason": None}
        self._result = result if result is not None else RESULT
        self._events = list(events) if events is not None else list(EVENTS)
        self._stream_error = stream_error
        self._completion_error = completion_error

    def llm_status(self):
        self.calls.append(("llm_status",))
        return copy.deepcopy(self._llm)

    def desk_state(self):
        self.calls.append(("desk_state",))
        return copy.deepcopy(self._desk)

    def can_start_heavy(self, kind):
        self.calls.append(("can_start_heavy", kind))
        return copy.deepcopy(self._can_start)

    def chat_completion(self, req):
        self.calls.append(("chat_completion", copy.deepcopy(req)))
        if self._completion_error is not None:
            raise self._completion_error
        return copy.deepcopy(self._result)

    def chat_stream(self, req):
        self.calls.append(("chat_stream", copy.deepcopy(req)))

        def gen():
            yield from self._events
            if self._stream_error is not None:
                raise self._stream_error

        return gen()

    def called_methods(self):
        return [call[0] for call in self.calls]

    def assert_no_inference_calls(self):
        assert set(self.called_methods()) <= QUERY_METHODS, self.calls
