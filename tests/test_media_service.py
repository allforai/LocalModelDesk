"""MediaService video success path."""
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.media.service import MediaError
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


def test_start_music_job_argv_output_and_runtime_capability(tmp_path):
    """Music jobs use the dedicated runtime, argv, and WAV output convention."""
    from desk.media.commands import build_music_command

    service, deps = make_service(tmp_path)
    roots = SimpleNamespace(
        outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
        music_python=Path("/fake/bin/music-python"), media_cli_dir=Path("/fake/media"),
        music_env={"PYTHONPATH": "/fake/pylibs/music"},
    )
    service._resolve_paths = lambda: roots
    service._probe_capabilities = lambda: {
        "music_runtime": SimpleNamespace(present=True, detail=""),
    }
    service._list_catalog = lambda: [
        SimpleNamespace(key="music3", relpath="minimax-music3"),
    ]

    snap = finished_snapshot(service, lambda: service.start_music_job(
        caption="ambient piano", lyrics="instrumental", duration=30.0))

    output = tmp_path / "outputs" / f"music3-{STAMP}.wav"
    assert snap["status"] == "done"
    assert snap["output"] == output.name
    assert deps.executor.spawned == [{"cmd": build_music_command(
        roots.music_python, roots.media_cli_dir / "music3_cli.py",
        tmp_path / "models" / "minimax-music3", caption="ambient piano",
        lyrics="instrumental", duration=30.0, output=output),
        "extra_env": roots.music_env}]

    service, deps = make_service(tmp_path)
    service._probe_capabilities = lambda: {}
    with pytest.raises(MediaError) as err:
        service.start_music_job(caption="ambient piano", lyrics="", duration=30.0)
    assert err.value.code == "capability_missing"
    assert err.value.http_status == 503
    assert deps.executor.spawned == []


class TestStartDiscipline:
    VALID = dict(prompt="p", width=512, height=288, frames=73, steps=10)

    @pytest.mark.parametrize("bad", [
        dict(prompt=""), dict(prompt="   "), dict(prompt=None),
        dict(width=0), dict(width=-1), dict(width="512"), dict(width=True),
        dict(height=0), dict(frames=0), dict(steps=0),
    ])
    def test_invalid_video_params_never_touch_arbiter_or_spawn(self, tmp_path, bad):
        service, deps = make_service(tmp_path)
        with pytest.raises(MediaError) as err:
            service.start_video_job(**{**self.VALID, **bad})
        assert err.value.code == "invalid_params"
        assert err.value.http_status == 400
        assert deps.arbiter.acquired == []
        assert deps.executor.spawned == []
        assert service.job_status()["status"] == "idle"

    @pytest.mark.parametrize("bad", [
        dict(caption=""), dict(caption=None), dict(lyrics=None),
        dict(duration=0), dict(duration=-3.0), dict(duration="30"),
    ])
    def test_invalid_music_params_never_spawns(self, tmp_path, bad):
        service, deps = make_service(tmp_path)
        valid = dict(caption="c", lyrics="l", duration=30.0)
        with pytest.raises(MediaError) as err:
            service.start_music_job(**{**valid, **bad})
        assert err.value.code == "invalid_params"
        assert err.value.http_status == 400
        assert deps.executor.spawned == []

    def test_missing_capability_is_503_and_arbiter_untouched(self, tmp_path):
        service, deps = make_service(tmp_path)
        service._probe_capabilities = lambda: {}
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "capability_missing"
        assert err.value.http_status == 503
        assert deps.arbiter.acquired == []
        assert deps.executor.spawned == []

    def test_can_start_refusal_passes_code_and_holder_through(self, tmp_path):
        service, deps = make_service(tmp_path)
        reason = {"code": "transition_in_progress", "message": "evicting now", "holder": {"kind": "llm"}}
        deps.arbiter.can_start_heavy = lambda _: {"ok": False, "reason": reason}
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "transition_in_progress"
        assert err.value.http_status == 409
        assert err.value.detail == reason
        assert deps.arbiter.acquired == []
        assert deps.executor.spawned == []

    def test_acquire_refusal_never_spawns_and_state_unchanged(self, tmp_path):
        service, deps = make_service(tmp_path)
        reason = {"code": "evict_failed", "message": "still listening", "holder": {"kind": "llm"}}
        deps.arbiter.acquire_heavy = lambda *_: {"ok": False, "reason": reason}
        with pytest.raises(MediaError) as err:
            service.start_video_job(**self.VALID)
        assert err.value.code == "evict_failed"
        assert err.value.detail == reason
        assert deps.executor.spawned == []
        assert deps.arbiter.released == []
        assert service.job_status()["status"] == "idle"
