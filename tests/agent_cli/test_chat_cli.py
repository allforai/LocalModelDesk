import json

from desk.testing import launch_test_harness
from desk.testing.scripts import ChatScript, Delta, Done
from tests.agent_cli.cli_helpers import run_cli

CHAT = "glm"      # 与 Task 4 确认过的对话模型 key 一致
OTHER = "qwen27"  # 另一个对话模型；若目录里没有，换成目录中第二个 group=chat 的 key


def test_status_json_reports_desk_and_versions(tmp_path):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "status", "--json")
        assert r.returncode == 0, r.stderr
        body = json.loads(r.stdout)
        assert body["desk"]["reachable"] is True
        assert body["llm"]["status"] == "idle"
        assert body["media"]["running"] is False
        assert body["version"]["cli"] == body["version"]["desk"]


def test_models_lists_only_chat_models(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        r = run_cli(h, "models", "--json")
        assert r.returncode == 0, r.stderr
        models = json.loads(r.stdout)["models"]
        assert models and all(m["group"] == "chat" for m in models)
        assert {"key", "name", "gb", "loaded", "fit"} <= set(models[0])


def test_ask_without_model_and_nothing_loaded_is_exit_5_listing_models(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        r = run_cli(h, "ask", "你好")
        assert r.returncode == 5
        assert CHAT in r.stderr


def test_ask_unknown_model_is_exit_5(tmp_path):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "ask", "你好", "--model", "nope")
        assert r.returncode == 5


def test_ask_loads_on_demand_then_answers_and_marks_agent(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        r = run_cli(h, "ask", "你好", "--model", CHAT)
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "你好，世界"
        status = h.llm.status()
        assert status["state"]["model_key"] == CHAT and status["loaded_by"] == "agent"
        assert status["ui_chat_recent"] is False
        assert h.chat_script.requests[-1].get("origin") is None  # origin never reaches the backend


def test_ask_uses_resident_model_when_none_given(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        h.llm.load(CHAT); h.llm.wait_settled()
        r = run_cli(h, "ask", "你好")
        assert r.returncode == 0, r.stderr
        assert h.llm.status()["loaded_by"] == "ui"


def test_ask_waits_instead_of_swapping_while_ui_chatted_recently(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present", OTHER: "present"}) as h:
        h.llm.load(CHAT); h.llm.wait_settled()
        h.llm.chat_completion({"messages": [{"role": "user", "content": "hi"}]})
        r = run_cli(h, "ask", "你好", "--model", OTHER, "--timeout", "3")
        assert r.returncode == 3
        assert h.llm.status()["state"]["model_key"] == CHAT


def test_ask_reads_stdin_and_files_and_ignores_empty_stdin(tmp_path):
    note = tmp_path / "note.md"
    note.write_text("文件内容")
    turn = [Delta(content="你好，世界"), Done(usage={"total_tokens": 1})]
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}, chat_script=ChatScript(turn + turn)) as h:
        r = run_cli(h, "ask", "总结", "--model", CHAT, "--file", str(note), stdin="管道内容")
        assert r.returncode == 0, r.stderr
        sent = h.chat_script.requests[-1]["messages"][-1]["content"]
        assert "总结" in sent and "管道内容" in sent and "note.md" in sent and "文件内容" in sent
        r2 = run_cli(h, "ask", "只有问题", "--model", CHAT, stdin="")
        assert r2.returncode == 0
        assert h.chat_script.requests[-1]["messages"][-1]["content"] == "只有问题"


def test_ask_json_output(tmp_path):
    with launch_test_harness(tmp_path, model_states={CHAT: "present"}) as h:
        r = run_cli(h, "ask", "你好", "--model", CHAT, "--json")
        body = json.loads(r.stdout)
        assert body["content"] == "你好，世界" and body["model"] == CHAT


def test_missing_file_is_exit_2(tmp_path):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "ask", "x", "--file", str(tmp_path / "nope.md"))
        assert r.returncode == 2


def test_error_json_shape(tmp_path):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "ask", "x", "--model", "nope", "--json")
        assert json.loads(r.stdout)["error"]["code"] == "model_not_found"


def test_version_mismatch_only_warns(tmp_path, monkeypatch):
    with launch_test_harness(tmp_path) as h:
        r = run_cli(h, "status", extra_env={"LMDESK_FAKE_VERSION": "0.0.0-test"})
        assert r.returncode == 0
        assert "版本不一致" in r.stderr


def test_ask_switches_from_a_ui_loaded_model_and_both_can_chat(tmp_path):
    turn = [Delta(content="你好，世界"), Done(usage={"total_tokens": 1})]
    with launch_test_harness(tmp_path, model_states={CHAT: "present", OTHER: "present"},
                             chat_script=ChatScript(turn + turn)) as h:
        h.llm.load(CHAT); h.llm.wait_settled()

        r = run_cli(h, "ask", "你好", "--model", OTHER, "--timeout", "30")

        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == "你好，世界"
        assert h.llm.status()["state"]["model_key"] == OTHER
        ui = h.llm.chat_completion({"messages": [{"role": "user", "content": "hi"}], "model": OTHER})
        assert ui["model"] == OTHER   # 界面身份的对话也不再被当成「已收回」

