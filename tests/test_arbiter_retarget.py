"""换聊天模型时，同一张 llm 令牌改记成新模型（cross-exam G6/G7）。"""
from types import SimpleNamespace

from desk.arbiter.core import Arbiter
from desk.arbiter.reaper import ReapResult
from desk.arbiter.state import still_holds
from desk.budget.budget import Workload

GB = 1_000_000_000


class KeyedBudget:
    """按 (kind, key) 给开销：换模型要两个大小不同的聊天模型，按 kind 给定值的 FakeBudget 分不出来。"""

    def __init__(self, costs):
        self._costs = costs

    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None):
        return self._costs[(kind, key)]


def _arbiter(budget=None, available=100 * GB):
    memory = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=available))
    return Arbiter(llm_port=43123, memory=memory, budget=budget,
                   reaper=lambda port: ReapResult(ok=True, port=port, killed_pids=[]))


def _costs():
    table = {("llm", "small"): 20, ("llm", "big"): 60, ("video", None): 50}
    return KeyedBudget({k: Workload(k[0], k[1], v * GB, "measured") for k, v in table.items()})


def test_retarget_relabels_the_llm_holder_and_notifies_subscribers():
    arbiter = _arbiter()
    token = arbiter.acquire_heavy("llm", "glm", "GLM")["token"]
    seen = []
    arbiter.subscribe(seen.append)

    result = arbiter.retarget_heavy(token, "qwen", "Qwen", params={}, key="qwen")

    assert result["ok"] is True and result["token"] == token
    state = arbiter.desk_state()
    assert still_holds(state, "llm", "qwen") and not still_holds(state, "llm", "glm")
    assert state["holder"]["display"] == "Qwen"
    assert len(seen) == 1 and still_holds(seen[0], "llm", "qwen")
    assert arbiter.release_heavy(token) == {"ok": True}


def test_retarget_counts_the_new_model_and_drops_the_old_one():
    arbiter = _arbiter(_costs())
    token = arbiter.acquire_heavy("llm", "small", params={}, key="small")["token"]

    assert arbiter.retarget_heavy(token, "big", params={}, key="big")["ok"] is True

    # big 60 + video 50 > 100：开视频要先让出聊天模型，让出的应是 big。
    # 台账若还按 small 20 记，20 + 50 装得下，release 会是空的。
    answer = arbiter.can_start_heavy("video", params={}, key=None)
    assert [w["key"] for w in answer["release"]] == ["big"]


def test_retarget_refuses_when_the_new_model_does_not_fit_beside_running_media():
    arbiter = _arbiter(_costs())
    token = arbiter.acquire_heavy("llm", "small", params={}, key="small")["token"]
    assert arbiter.acquire_heavy("video", "job-1", params={}, key=None)["ok"] is True

    result = arbiter.retarget_heavy(token, "big", params={}, key="big")

    assert result["ok"] is False and result["reason"]["code"] == "insufficient_budget"
    assert still_holds(arbiter.desk_state(), "llm", "small")


def test_retarget_only_accepts_a_live_llm_token():
    arbiter = _arbiter()
    media = arbiter.acquire_heavy("video", "job-1")["token"]
    assert arbiter.retarget_heavy("nope", "qwen")["reason"]["code"] == "not_holder"
    assert arbiter.retarget_heavy(media, "qwen")["reason"]["code"] == "not_holder"


def test_budget_mode_retarget_needs_capacity_inputs():
    arbiter = _arbiter(_costs())
    token = arbiter.acquire_heavy("llm", "small", params={}, key="small")["token"]
    assert arbiter.retarget_heavy(token, "big")["reason"]["code"] == "capacity_unknown"
    assert still_holds(arbiter.desk_state(), "llm", "small")
