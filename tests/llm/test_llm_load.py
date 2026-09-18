"""LlmService successful load lifecycle and loaded-model metadata."""
from desk.llm.state import DEFAULT_LLM_PORT
from tests.llm.llm_fakes import make_entry, make_service


def test_load_happy_path_order_and_state(tmp_path):
    testbed = make_service(tmp_path, backend_kw={"health_script": [False, True]})

    state = testbed.service.load("glm")

    assert state["status"] == "loading"
    assert state["model_key"] == "glm"
    final = testbed.service.wait_settled()
    assert final["status"] == "loaded"
    assert final["loaded_at"] is not None
    assert final["error"] is None
    names = [call[0] for call in testbed.calls]
    assert names[:4] == ["acquire", "reap", "listeners", "spawn"]
    assert names.index("spawn") < names.index("health")
    assert ("acquire", "llm", "glm") in testbed.calls
    assert ("reap", DEFAULT_LLM_PORT) in testbed.calls
    assert "release" not in names


def test_load_uses_resolved_paths(tmp_path):
    entry = make_entry(key="qwen35", relpath="llms/mlx-community/qwen35-4bit")
    testbed = make_service(tmp_path, entries=[entry])

    testbed.service.load("qwen35")
    testbed.service.wait_settled()

    _, python, model_path, port, log_path = next(
        call for call in testbed.calls if call[0] == "spawn"
    )
    assert python == str(testbed.paths.venv_python)
    assert model_path == str(testbed.paths.models_root / entry.relpath)
    assert port == DEFAULT_LLM_PORT
    assert log_path == str(testbed.paths.logs_dir / "mlx-lm.log")


def test_status_reports_loaded_model_metadata_verbatim(tmp_path):
    entry = make_entry(key="superqwen", vision=True, quant="8bit", params="80B", gb=84.0)
    testbed = make_service(tmp_path, entries=[entry])

    testbed.service.load("superqwen")
    testbed.service.wait_settled()

    status = testbed.service.status()
    assert status["state"]["status"] == "loaded"
    assert status["loaded_model"] == {
        "key": "superqwen", "name": entry.name, "hf_repo": entry.hf_repo,
        "served_id": entry.hf_repo, "vision": True, "quant": "8bit",
        "params": "80B", "gb": 84.0,
    }


def test_status_idle_has_no_loaded_model(tmp_path):
    testbed = make_service(tmp_path)

    assert testbed.service.status() == {
        "state": {"status": "idle", "model_key": None, "error": None, "loaded_at": None},
        "loaded_model": None,
    }


def test_a_non_dict_config_json_does_not_kill_the_load_thread(tmp_path):
    """config.json 合法但不是对象时，预算该退回「算不出」，而不是让加载线程死掉。

    keep-code-simple S1/F6：_read_model_config 在 service.py 里定义了两次，
    带类型守卫的那份（43 行）被无守卫的那份（65 行）遮蔽，于是 json.loads("[]")
    得到 list，一路传到 estimate.py 的 config.get(...) 抛 AttributeError；
    它发生在 _load_worker 里、spawn 之前，线程直接死 → 状态永远停在 loading。
    """
    from desk.llm.service import _read_model_config

    model_dir = tmp_path / "m"
    model_dir.mkdir()
    (model_dir / "config.json").write_text("[]", encoding="utf-8")

    assert _read_model_config(model_dir) == {}, "非 dict 的 config 必须被挡成 {}"
