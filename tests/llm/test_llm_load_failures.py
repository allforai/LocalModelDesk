"""LlmService cleanup behavior when loading cannot complete."""
from desk.llm.state import (
    ERR_BACKEND_EXITED,
    ERR_LOAD_TIMEOUT,
    ERR_PORT_NOT_RELEASED,
)
from tests.llm.llm_fakes import make_service


def test_backend_exit_records_log_tail_and_releases_reservation(tmp_path):
    testbed = make_service(
        tmp_path,
        backend_kw={"health_script": [False], "tail_text": "backend trace"},
    )
    testbed.proc.set_exit(17)

    testbed.service.load("glm")
    final = testbed.service.wait_settled()

    assert final["error"] == {
        "code": ERR_BACKEND_EXITED,
        "message": "mlx-lm 进程退出，退出码 17",
        "log_tail": "backend trace",
    }
    names = [call[0] for call in testbed.calls]
    assert names.index("log_tail") < names.index("release")
    assert ("release", "tok-1") in testbed.calls


def test_load_timeout_records_log_tail_and_releases_reservation(tmp_path):
    testbed = make_service(
        tmp_path,
        load_timeout_s=0,
        backend_kw={"health_script": [False], "tail_text": "timeout trace"},
    )

    testbed.service.load("glm")
    final = testbed.service.wait_settled()

    assert final["error"] == {
        "code": ERR_LOAD_TIMEOUT,
        "message": "mlx-lm 超过 0s 未就绪",
        "log_tail": "timeout trace",
    }
    names = [call[0] for call in testbed.calls]
    assert names.index("log_tail") < names.index("release")
    assert ("release", "tok-1") in testbed.calls


def test_failed_port_reap_fails_before_spawn_and_releases_reservation(tmp_path):
    testbed = make_service(
        tmp_path,
        arbiter_kw={"reap_result": {"ok": False, "error": "still occupied"}},
    )

    testbed.service.load("glm")
    final = testbed.service.wait_settled()

    assert final["error"] == {
        "code": ERR_PORT_NOT_RELEASED,
        "message": "still occupied",
        "log_tail": None,
    }
    names = [call[0] for call in testbed.calls]
    assert "spawn" not in names
    assert names.index("reap") < names.index("release")
    assert ("release", "tok-1") in testbed.calls
