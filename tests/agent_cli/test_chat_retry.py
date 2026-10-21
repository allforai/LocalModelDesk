"""模型已加载、要的就是它，对话却一直被拒：重试改变不了什么，不能等到超时（P2）。"""
import io

import pytest

from desk.agent_cli.chat import run_ask
from desk.agent_cli.client import HttpError
from desk.agent_cli.errors import CliError, EXIT_ERROR
from desk.agent_cli.waiter import Waiter


class Desk:
    def __init__(self, refusals):
        self.refusals = refusals
        self.chats = 0

    def get(self, path, query=None):
        if path == "/api/llm/status":
            return {"state": {"status": "loaded", "model_key": "glm"}, "active_chats": 0, "ui_chat_recent": False}
        if path == "/api/media/job":
            return {"status": "idle"}
        if path == "/api/agent/precheck":
            return {"ok": True, "release": []}
        if path == "/api/resources/catalog":
            return [{"key": "glm", "group": "chat"}]
        raise AssertionError(path)

    def post(self, path, body=None, timeout=None):
        assert path == "/api/llm/chat"
        self.chats += 1
        if self.chats <= self.refusals:
            raise HttpError(409, "evicted", "模型已被台面收回", {})
        return {"content": "好", "model": "glm"}


def _waiter():
    now = [0.0]
    return Waiter(600, clock=lambda: now[0], sleep=lambda s: now.__setitem__(0, now[0] + s), err=io.StringIO())


def _ask(desk):
    return run_ask(desk, question="hi", model="glm", system=None, files=[], stdin_text="",
                   max_tokens=None, waiter=_waiter())


def test_three_refusals_of_a_loaded_model_end_with_the_desks_reason():
    desk = Desk(refusals=99)
    with pytest.raises(CliError) as exc:
        _ask(desk)
    assert exc.value.exit_code == EXIT_ERROR
    assert "模型已被台面收回" in exc.value.message
    assert desk.chats == 3


def test_a_single_refusal_is_still_retried():
    desk = Desk(refusals=1)
    assert _ask(desk)["content"] == "好"
    assert desk.chats == 2
