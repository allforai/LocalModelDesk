"""R-budget-03/04：起 mlx-lm 时传限额，每轮答完记实测。"""
from desk.llm.backend import MlxLmBackend
from tests.llm.llm_fakes import make_loaded, make_service


class RecordingPopen:
    calls = []
    def __init__(self, argv, **kwargs):
        RecordingPopen.calls.append(argv)


def test_spawn_appends_extra_args(monkeypatch, tmp_path):
    import subprocess
    RecordingPopen.calls.clear()
    monkeypatch.setattr(subprocess, "Popen", RecordingPopen)
    MlxLmBackend().spawn(tmp_path / "py", tmp_path / "model", 8767, tmp_path / "log",
                         extra_args=["--prompt-cache-bytes", "123", "--prompt-cache-size", "1"])
    argv = RecordingPopen.calls[-1]
    assert argv[-4:] == ["--prompt-cache-bytes", "123", "--prompt-cache-size", "1"]
    assert "--model" in argv and "--port" in argv     # 原有参数没被挤掉


def test_spawn_without_extra_args_is_unchanged(monkeypatch, tmp_path):
    import subprocess
    RecordingPopen.calls.clear()
    monkeypatch.setattr(subprocess, "Popen", RecordingPopen)
    MlxLmBackend().spawn(tmp_path / "py", tmp_path / "model", 8767, tmp_path / "log")
    assert "--prompt-cache-bytes" not in RecordingPopen.calls[-1]


class FakeBudget:
    """A minimal stand-in for desk.budget.budget.Budget's llm-facing surface."""

    def __init__(self, launch_args_result=None):
        self._launch_args_result = list(launch_args_result or [])
        self.launch_args_calls = []
        self.record_turn_calls = []

    def launch_args(self, key, config, weights_gb):
        self.launch_args_calls.append((key, config, weights_gb))
        return list(self._launch_args_result)

    def record_turn(self, key, log_text, prompt_tokens, weights_gb):
        self.record_turn_calls.append((key, log_text, prompt_tokens, weights_gb))


def test_load_passes_budget_launch_args_to_spawn(tmp_path):
    """加载时 spawn 收到的 extra_args 与 Budget.launch_args 的返回一致。"""
    budget = FakeBudget(launch_args_result=["--prompt-cache-bytes", "999", "--prompt-cache-size", "1"])
    testbed = make_service(tmp_path, budget=budget)

    testbed.service.load("glm")
    final = testbed.service.wait_settled()

    assert final["status"] == "loaded", final
    assert testbed.backend.spawn_extra_args == [
        "--prompt-cache-bytes", "999", "--prompt-cache-size", "1",
    ]
    # Budget was asked using this model's own key and weight size.
    (key, config, weights_gb), = budget.launch_args_calls
    assert key == "glm"
    assert weights_gb == testbed.entries[0].gb
    assert isinstance(config, dict)


def test_load_without_budget_spawns_with_no_extra_args(tmp_path):
    """budget 未注入时行为不变：不传 extra_args。"""
    testbed = make_service(tmp_path)

    testbed.service.load("glm")
    final = testbed.service.wait_settled()

    assert final["status"] == "loaded", final
    assert testbed.backend.spawn_extra_args is None


DONE_CHUNKS = [
    {"choices": [{"delta": {"content": "你"}}]},
    {"choices": [{"delta": {}, "finish_reason": "stop"}],
     "usage": {"prompt_tokens": 40_000, "total_tokens": 40_003}},
]


def test_completed_turn_records_prompt_tokens_from_the_done_event(tmp_path):
    """一轮流式结束后 record_turn 被调用一次，prompt_tokens 取自 done 事件。"""
    budget = FakeBudget()
    testbed = make_loaded(
        tmp_path, budget=budget,
        backend_kw={"chunks": DONE_CHUNKS, "tail_text": "Prompt Cache: 1 sequences, 12.40 GB"},
    )

    events = list(testbed.service.chat_stream({"messages": []}))

    assert events[-1]["type"] == "done"
    (key, log_text, prompt_tokens, weights_gb), = budget.record_turn_calls
    assert key == "glm"
    assert prompt_tokens == 40_000
    assert log_text == "Prompt Cache: 1 sequences, 12.40 GB"
    assert weights_gb == testbed.entries[0].gb


def test_interrupted_turn_does_not_record(tmp_path):
    """没跑完的一轮（缺 usage/finish_reason）不该被当成实测记下去。"""
    budget = FakeBudget()
    testbed = make_loaded(tmp_path, budget=budget, backend_kw={"chunks": DONE_CHUNKS[:1]})

    events = list(testbed.service.chat_stream({"messages": []}))

    assert events[-1]["type"] == "error"
    assert budget.record_turn_calls == []


def test_stream_without_budget_still_works(tmp_path):
    """budget 未注入时聊天流程不受影响（向后兼容既有测试夹具）。"""
    testbed = make_loaded(tmp_path, backend_kw={"chunks": DONE_CHUNKS})

    events = list(testbed.service.chat_stream({"messages": []}))

    assert events[-1]["type"] == "done"
