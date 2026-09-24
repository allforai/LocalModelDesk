"""Continuation: frame hand-off, chain joining, and every way a join can end (B §3.3–3.4)."""
import threading
import time
from pathlib import Path

import pytest

from desk.media import compose
from desk.media import service as service_mod
from desk.media.service import MediaError
from media_fakes import FIXED_TIME, FakeExecutor, finished_snapshot, make_service
from test_media_sessions_service import music, music_ready, video


@pytest.fixture(autouse=True)
def fake_ffmpeg(monkeypatch, tmp_path):
    """Frame extraction and size probing run synchronously; fake both, keep argv builders real."""
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: "/fake/ffmpeg")
    monkeypatch.setattr(compose, "ffprobe_path", lambda: "/fake/ffprobe")
    monkeypatch.setattr(compose, "probe_size", lambda _probe, _video: (512, 288))
    def fake_run(cmd, **_kw):
        Path(cmd[-1]).write_bytes(b"png")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(service_mod.subprocess, "run", fake_run)
    monkeypatch.setattr(service_mod, "wav_seconds", lambda _p: 20.0)


def first_segment(service, deps, kind="video"):
    sid = deps.media_sessions[kind].create()["id"]
    run = video if kind == "video" else music
    snap = finished_snapshot(service, lambda: run(service, session_id=sid))
    return sid, snap["attempt_id"]


def attempts(deps, kind, sid):
    return deps.media_sessions[kind].get(sid)["attempts"]


def test_video_continuation_uses_last_frame_and_joins_the_chain(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    snap = finished_snapshot(service, lambda: video(service, session_id=sid, continues=first))
    second = attempts(deps, "video", sid)[1]
    assert second["continues"] == first and second["params"]["mode"] == "image"
    assert (tmp_path / "outputs" / ".inputs" / second["params"]["first_frame"]).is_file()
    assert second["status"] == "done" and second["output"] == snap["output"]
    assert second["joined_output"].startswith("h3-joined-") and second["joined_error"] is None
    join_cmd = deps.executor.spawned[-1]["cmd"]
    graph = join_cmd[join_cmd.index("-filter_complex") + 1]
    assert "[0:v]trim" not in graph and "[1:v]trim=start_frame=1" in graph
    assert deps.history.entries[-1]["joined_output"] == second["joined_output"]


def test_permit_is_released_when_the_model_exits_and_only_once(tmp_path):
    service, deps = make_service(tmp_path, executor=FakeExecutor(join_script="block"))
    sid, first = first_segment(service, deps)
    finished = threading.Event()
    service.on_job_finished(lambda _s: finished.set())
    video(service, session_id=sid, continues=first)
    deadline = time.time() + 5
    while deps.arbiter.released.count("permit-2") == 0 and time.time() < deadline:
        time.sleep(0.01)
    assert service.job_status()["status"] == "running"          # 还在拼接
    assert deps.arbiter.released.count("permit-2") == 1           # 许可已释放
    service.cancel_job()
    assert finished.wait(5)
    assert deps.arbiter.released.count("permit-2") == 1


def test_cancel_during_join_keeps_the_segment_as_done(tmp_path):
    service, deps = make_service(tmp_path, executor=FakeExecutor(join_script="block"))
    sid, first = first_segment(service, deps)
    finished = threading.Event()
    service.on_job_finished(lambda _s: finished.set())
    video(service, session_id=sid, continues=first)
    deadline = time.time() + 5
    while attempts(deps, "video", sid)[1]["output"] is None and time.time() < deadline:
        time.sleep(0.01)
    service.cancel_job()
    assert finished.wait(5)
    second = attempts(deps, "video", sid)[1]
    assert second["status"] == "done" and second["output"]
    assert second["joined_output"] is None and second["joined_error"]["code"] == "join_cancelled"


def test_join_failure_keeps_the_segment_as_done(tmp_path):
    service, deps = make_service(tmp_path, executor=FakeExecutor(join_script="fail"))
    sid, first = first_segment(service, deps)
    finished_snapshot(service, lambda: video(service, session_id=sid, continues=first))
    second = attempts(deps, "video", sid)[1]
    assert second["status"] == "done" and second["joined_error"]["code"] == "join_failed"


def test_broken_chain_still_generates_and_names_the_missing_segment(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    service._clock = lambda: FIXED_TIME + 1          # own file name: outputs are named by the second
    finished_snapshot(service, lambda: video(service, session_id=sid, continues=first))
    second = attempts(deps, "video", sid)[1]
    (tmp_path / "outputs" / attempts(deps, "video", sid)[0]["output"]).unlink()   # 删掉第 1 段
    spawned_before = len(deps.executor.spawned)
    finished_snapshot(service, lambda: video(service, session_id=sid, continues=second["id"]))
    third = attempts(deps, "video", sid)[2]
    assert third["status"] == "done"
    assert third["joined_error"] == {"code": "segment_missing", "message": "第 1 段的文件已不在，无法拼成成片"}
    assert len(deps.executor.spawned) == spawned_before + 1       # 只跑了模型，没跑拼接


def test_music_continuation_crossfades_without_touching_model_inputs(tmp_path):
    service, deps = make_service(tmp_path)
    music_ready(service, tmp_path)
    sid, first = first_segment(service, deps, "music")
    finished_snapshot(service, lambda: music(service, session_id=sid, continues=first, lyrics="[verse]\n晚上"))
    second = attempts(deps, "music", sid)[1]
    assert second["params"]["lyrics"] == "[verse]\n晚上" and second["joined_output"].startswith("music3-joined-")
    join_cmd = deps.executor.spawned[-1]["cmd"]
    assert "acrossfade=d=1.5:c1=tri:c2=tri" in join_cmd[join_cmd.index("-filter_complex") + 1]


@pytest.mark.parametrize("arrange, code, status", [
    (lambda deps, sid, first: "9" * 32, "segment_not_found", 404),
    (lambda deps, sid, first: (Path(deps.outputs) / deps.first_output).unlink() or first, "segment_missing", 404),
])
def test_bad_continues_is_refused_and_writes_nothing(tmp_path, arrange, code, status):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    deps.outputs = tmp_path / "outputs"
    deps.first_output = attempts(deps, "video", sid)[0]["output"]
    target = arrange(deps, sid, first)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=target)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert len(attempts(deps, "video", sid)) == 1


def test_continues_conflicts_with_an_explicit_first_frame(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=first, mode="image", first_frame="a" * 32 + ".png")
    assert exc.value.code == "invalid_params"


def test_continues_without_session_is_session_required(tmp_path):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, continues="a" * 32)
    assert exc.value.code == "session_required"


def test_refused_continuation_cleans_its_extracted_frame(tmp_path):
    service, deps = make_service(tmp_path, memory_warning={"code": "insufficient_memory",
                                                            "required_bytes": 10, "available_bytes": 1})
    sid = deps.media_sessions["video"].create()["id"]
    finished_snapshot(service, lambda: video(service, session_id=sid, force=True))
    first = attempts(deps, "video", sid)[0]["id"]
    inputs = tmp_path / "outputs" / ".inputs"
    before = set(inputs.iterdir()) if inputs.is_dir() else set()
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=first)
    assert exc.value.code == "insufficient_memory"
    assert (set(inputs.iterdir()) if inputs.is_dir() else set()) == before
    assert len(attempts(deps, "video", sid)) == 1


def test_missing_ffmpeg_refuses_continuation_but_not_plain_generation(tmp_path, monkeypatch):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    monkeypatch.setattr(compose, "ffmpeg_path", lambda: None)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=first)
    assert (exc.value.code, exc.value.http_status, exc.value.message) == ("capability_missing", 503, compose.FFMPEG_MISSING)
    assert finished_snapshot(service, lambda: video(service, session_id=sid))["status"] == "done"


def test_frame_extraction_failure_is_500_and_writes_nothing(tmp_path, monkeypatch):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    monkeypatch.setattr(service_mod.subprocess, "run",
                        lambda cmd, **kw: type("R", (), {"returncode": 1, "stdout": "", "stderr": "boom"})())
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, continues=first)
    assert (exc.value.code, exc.value.http_status) == ("frame_extract_failed", 500)
    assert len(attempts(deps, "video", sid)) == 1
