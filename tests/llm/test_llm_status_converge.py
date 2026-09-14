"""LLM status liveness checks and heavy-ownership convergence."""
from tests.llm.llm_fakes import make_loaded, make_service


def test_status_self_check_detects_dead_process(tmp_path):
    testbed = make_loaded(tmp_path, backend_kw={"tail_text": "Killed: 9"})
    testbed.backend.process.set_exit(9)

    got = testbed.service.status()

    assert got["state"]["status"] == "error"
    assert got["state"]["error"] == {
        "code": "backend_exited",
        "message": "mlx-lm 进程已退出，退出码 9",
        "log_tail": "Killed: 9",
    }
    assert got["loaded_model"] is None
    assert ("release", "tok-1") in testbed.calls


def test_holder_moving_to_media_marks_the_model_evicted(tmp_path):
    testbed = make_loaded(tmp_path)

    testbed.arbiter.emit({"holder": {"kind": "video", "label": "job-1", "phase": "held"}, "media_busy": True})

    got = testbed.service.status()
    assert got["state"]["status"] == "error"
    assert got["state"]["error"]["code"] == "evicted"


def test_holder_still_this_model_is_noop(tmp_path):
    testbed = make_loaded(tmp_path)

    testbed.arbiter.emit({"holder": {"kind": "llm", "label": "glm", "phase": "held"}, "media_busy": False})

    assert testbed.service.status()["state"]["status"] == "loaded"


def test_holder_change_when_not_loaded_is_noop(tmp_path):
    testbed = make_service(tmp_path)

    testbed.arbiter.emit({"holder": None, "media_busy": False})

    assert testbed.service.status()["state"]["status"] == "idle"
    assert testbed.calls == []


def test_backend_killed_by_media_eviction_is_evicted_not_backend_exited(tmp_path):
    """仲裁收割端口时 mlx-lm 先退出；状态自检不能把驱逐误报成 backend_exited 并附整段日志。"""
    testbed = make_loaded(tmp_path)
    testbed.arbiter.set_desk_state({"holder": {"kind": "video", "label": "job-1", "phase": "acquiring"},
                                    "media_busy": False})
    testbed.backend.process.set_exit(-15)

    got = testbed.service.status()

    assert got["state"]["status"] == "error"
    assert got["state"]["error"]["code"] == "evicted"
    assert got["state"]["error"]["log_tail"] is None
    assert ("release", "tok-1") in testbed.calls
