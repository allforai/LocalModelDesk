"""Soundtrack jobs: replace a video's audio with a music-session song (design S-01–S-07)."""
import threading

import pytest

from desk.media import compose
from desk.media.routes import build_routes
from desk.media.service import MediaError
from media_fakes import finished_snapshot, make_service
from test_media_compose_job import PartialOutputExecutor
from test_media_continue import attempts, fake_ffmpeg, first_segment  # noqa: F401  (autouse fixture)
from test_media_sessions_service import video

SONG = "b" * 32


def done_song(deps, tmp_path, name="song.wav"):
    songs = deps.media_sessions["music"]
    sid = songs.create()["id"]
    songs.begin_attempt(sid, {"id": SONG, "job_id": 1, "params": {"caption": "独立流行", "lyrics": "l", "duration": 20.0, "seed": 1}})
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outputs" / name).write_bytes(b"wav")
    songs.settle_attempt(sid, SONG, "done", name)
    return {"kind": "music", "session_id": sid, "attempt_id": SONG}


def ready(service, deps, tmp_path):
    sid, source = first_segment(service, deps)
    return sid, source, done_song(deps, tmp_path)


def soundtrack(service, sid, source, ref, **kw):
    return service.start_soundtrack_job(**{"session_id": sid, "source": source, "refs": {"soundtrack": ref}, **kw})


def test_soundtrack_appends_a_soundtrack_attempt_without_arbiter(tmp_path):
    service, deps = make_service(tmp_path)
    sid, source, ref = ready(service, deps, tmp_path)
    acquired, prechecks = len(deps.arbiter.acquired), len(deps.arbiter.precheck_calls)
    snap = finished_snapshot(service, lambda: soundtrack(service, sid, source, ref))
    assert len(deps.arbiter.acquired) == acquired and len(deps.arbiter.precheck_calls) == prechecks
    made = attempts(deps, "video", sid)[-1]
    assert made["op"] == "soundtrack" and made["params"] == {"source": source}
    assert made["refs"] == {"soundtrack": ref} and made["continues"] is None
    assert made["status"] == "done" and made["output"].startswith("h3-soundtrack-") and made["output"].endswith(".mp4")
    assert snap["output"] == made["output"]
    cmd = deps.executor.spawned[-1]["cmd"]
    source_output = attempts(deps, "video", sid)[0]["output"]
    assert cmd[cmd.index("-i") + 1] == str(tmp_path / "outputs" / source_output)
    assert str(tmp_path / "outputs" / "song.wav") in cmd and "apad" in cmd
    entry = deps.history.entries[-1]
    assert entry["params"]["op"] == "soundtrack" and entry["refs"] == {"soundtrack": ref}


def test_soundtrack_uses_the_joined_output_when_the_source_has_one(tmp_path):
    service, deps = make_service(tmp_path)
    sid, first = first_segment(service, deps)
    second = finished_snapshot(service, lambda: video(service, session_id=sid, continues=first))["attempt_id"]
    joined = attempts(deps, "video", sid)[-1]["joined_output"]
    assert joined
    ref = done_song(deps, tmp_path)
    finished_snapshot(service, lambda: soundtrack(service, sid, second, ref))
    cmd = deps.executor.spawned[-1]["cmd"]
    assert cmd[cmd.index("-i") + 1] == str(tmp_path / "outputs" / joined)


def test_missing_session_is_session_required(tmp_path):
    service, deps = make_service(tmp_path)
    sid, source, ref = ready(service, deps, tmp_path)
    with pytest.raises(MediaError) as exc:
        soundtrack(service, None, source, ref)
    assert (exc.value.code, exc.value.http_status) == ("session_required", 400)
    assert len(attempts(deps, "video", sid)) == 1


@pytest.mark.parametrize("case, code, status", [
    ("bad_source_type", "invalid_params", 400),
    ("bad_refs", "invalid_params", 400),
    ("extra_ref", "invalid_params", 400),
    ("unknown_source", "segment_not_found", 404),
    ("source_missing", "segment_missing", 404),
    ("song_gone", "ref_missing", 404),
    ("no_ffmpeg", "capability_missing", 503),
])
def test_refusals_write_nothing(tmp_path, monkeypatch, case, code, status):
    service, deps = make_service(tmp_path)
    sid, source, ref = ready(service, deps, tmp_path)
    request = {"session_id": sid, "source": source, "refs": {"soundtrack": ref}}
    if case == "bad_source_type":
        request["source"] = 7
    elif case == "bad_refs":
        request["refs"] = {"soundtrack": "nope"}
    elif case == "extra_ref":
        request["refs"] = {"soundtrack": ref, "first_frame": ref}
    elif case == "unknown_source":
        request["source"] = "9" * 32
    elif case == "source_missing":
        (tmp_path / "outputs" / attempts(deps, "video", sid)[0]["output"]).unlink()
    elif case == "song_gone":
        (tmp_path / "outputs" / "song.wav").unlink()
    else:
        monkeypatch.setattr(compose, "ffmpeg_path", lambda: None)
    spawned = len(deps.executor.spawned)
    with pytest.raises(MediaError) as exc:
        service.start_soundtrack_job(**request)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    if case == "song_gone":
        assert exc.value.message == "引用的音乐已不在"
    if case == "no_ffmpeg":
        assert exc.value.message == "需要 ffmpeg 才能拼接成片"
    assert len(attempts(deps, "video", sid)) == 1 and len(deps.executor.spawned) == spawned


def test_soundtrack_is_mutually_exclusive_with_a_running_job(tmp_path):
    service, deps = make_service(tmp_path)
    sid, source, ref = ready(service, deps, tmp_path)
    deps.executor.script = "block"
    video(service, session_id=sid)
    with pytest.raises(MediaError) as exc:
        soundtrack(service, sid, source, ref)
    assert (exc.value.code, exc.value.http_status) == ("media_busy", 409)
    assert len(attempts(deps, "video", sid)) == 2
    service.cancel_job()


def test_failed_soundtrack_settles_join_failed_and_removes_its_partial_output(tmp_path):
    service, deps = make_service(tmp_path, executor=PartialOutputExecutor(join_script="fail"))
    sid, source, ref = ready(service, deps, tmp_path)
    finished_snapshot(service, lambda: soundtrack(service, sid, source, ref))
    made = attempts(deps, "video", sid)[-1]
    assert made["status"] == "failed" and made["error"]["code"] == "join_failed"
    assert not list((tmp_path / "outputs").glob("h3-soundtrack-*"))


def test_cancelled_soundtrack_removes_its_partial_output(tmp_path):
    service, deps = make_service(tmp_path, executor=PartialOutputExecutor(join_script="block"))
    sid, source, ref = ready(service, deps, tmp_path)
    finished = threading.Event()
    service.on_job_finished(lambda _s: finished.set())
    soundtrack(service, sid, source, ref)
    assert list((tmp_path / "outputs").glob("h3-soundtrack-*")), "fixture must write the partial file before blocking"
    service.cancel_job()
    assert finished.wait(5)
    assert attempts(deps, "video", sid)[-1]["status"] == "cancelled"
    assert not list((tmp_path / "outputs").glob("h3-soundtrack-*"))


def test_a_soundtrack_attempt_can_be_continued(tmp_path):
    service, deps = make_service(tmp_path)
    sid, source, ref = ready(service, deps, tmp_path)
    scored = finished_snapshot(service, lambda: soundtrack(service, sid, source, ref))["attempt_id"]
    finished_snapshot(service, lambda: video(service, session_id=sid, continues=scored))
    last = attempts(deps, "video", sid)[-1]
    assert last["status"] == "done" and last["continues"] == scored and last["joined_output"]


def test_video_generation_does_not_take_a_soundtrack_ref(tmp_path):
    service, deps = make_service(tmp_path)
    sid, _source, ref = ready(service, deps, tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, refs={"soundtrack": ref})
    assert exc.value.code == "invalid_params"
    assert len(attempts(deps, "video", sid)) == 1


def test_soundtrack_route(tmp_path, monkeypatch):
    service, _deps = make_service(tmp_path)
    seen = {}
    monkeypatch.setattr(service, "start_soundtrack_job", lambda **kw: seen.update(kw) or {"ok": True})
    handler = next(h for m, p, h in build_routes(service) if (m, p) == ("POST", "/api/media/soundtrack"))
    assert handler({"session_id": "s", "source": "a", "refs": {"soundtrack": {}}}, {}) == (200, {"ok": True})
    assert seen == {"session_id": "s", "source": "a", "refs": {"soundtrack": {}}, "force": False}
