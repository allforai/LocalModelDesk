"""MediaService video success path."""
import threading

from media_fakes import FIXED_TIME, STAMP, FakeExecutor, finished_snapshot, make_service


def start_video(service):
    return service.start_video_job(prompt="rain on a quiet street", width=512,
        height=288, frames=73, steps=10)


def test_initial_job_state_shape(tmp_path):
    state = make_service(tmp_path)[0].job_status()
    assert state == {"job_id": 0, "status": "idle", "kind": None, "params": None,
        "output": None, "error": None, "started_at": None, "finished_at": None,
        "log": "", "next_log_from": 0, "log_len": 0, "log_truncated": False}


def test_start_video_job_success_path(tmp_path):
    service, deps = make_service(tmp_path)
    snap = finished_snapshot(service, lambda: start_video(service))
    assert snap["status"] == "done"
    assert snap["output"] == f"h3-{STAMP}.mp4"
    assert snap["params"] == {"prompt": "rain on a quiet street", "width": 512,
        "height": 288, "frames": 73, "steps": 10}
    assert snap["started_at"] == snap["finished_at"] == FIXED_TIME
    assert "line-1" in snap["log"]
    assert deps.arbiter.acquired == [("video", "job-1", "permit-1")]
    assert deps.arbiter.released == ["permit-1"]
    assert deps.history.entries == [{"kind": "video", "status": "done", "params": snap["params"],
        "output": f"h3-{STAMP}.mp4", "duration_s": 0.0, "error": None}]


def test_video_argv_and_running_state(tmp_path):
    from desk.media.commands import build_h3_command

    service, deps = make_service(tmp_path, executor=FakeExecutor("block"))
    completed = threading.Event()
    service.on_job_finished(lambda _: completed.set())
    state = start_video(service)
    assert state["status"] == "running"
    assert deps.executor.spawned == [{"cmd": build_h3_command(
        ("/fake/bin/mlx-h3",), tmp_path / "models" / "minimax-h3",
        prompt="rain on a quiet street", width=512, height=288, frames=73,
        steps=10, output=tmp_path / "outputs" / f"h3-{STAMP}.mp4"),
        "extra_env": {"PYTHONPATH": "/fake/pylibs/h3"}}]
    service.cancel_job()
    assert completed.wait(5)
