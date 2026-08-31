from pathlib import Path

import pytest

from desk.llm import LlmBackend, MlxLmBackend
from desk.llm import backend as backend_module


class _Popen:
    def __init__(self, argv, **kwargs):
        self.argv = argv
        self.kwargs = kwargs


def test_package_exports_backend_protocol_and_implementation():
    assert LlmBackend is backend_module.LlmBackend
    assert MlxLmBackend is backend_module.MlxLmBackend


def test_spawn_launches_loopback_server_without_cors_override(tmp_path, monkeypatch):
    calls = []

    def popen(argv, **kwargs):
        calls.append(_Popen(argv, **kwargs))
        return calls[-1]

    monkeypatch.setattr(backend_module.subprocess, "Popen", popen)
    log_path = tmp_path / "logs" / "mlx-lm.log"
    proc = MlxLmBackend().spawn(
        Path("/app/venv/bin/python"), Path("/models/qwen"), 9123, log_path
    )

    assert proc is calls[0]
    assert calls[0].argv == [
        "/app/venv/bin/python", "-s", "-m", "mlx_lm", "server",
        "--model", "/models/qwen", "--host", "127.0.0.1", "--port", "9123",
    ]
    assert "--allowed-origins" not in calls[0].argv
    assert calls[0].kwargs["stdout"] is calls[0].kwargs["stderr"]
    assert calls[0].kwargs["stdout"].mode == "ab"
    assert log_path.exists()


def test_log_tail_returns_last_lines_and_missing_file_explanation(tmp_path):
    backend = MlxLmBackend()
    log_path = tmp_path / "mlx-lm.log"

    assert backend.log_tail(log_path) == f"日志文件不存在: {log_path}"

    log_path.write_text("".join(f"line {index}\n" for index in range(45)))
    assert backend.log_tail(log_path, max_lines=3) == "line 42\nline 43\nline 44"


def test_log_tail_rejects_non_positive_line_counts(tmp_path):
    with pytest.raises(ValueError):
        MlxLmBackend().log_tail(tmp_path / "mlx-lm.log", max_lines=0)
