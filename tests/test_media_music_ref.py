"""配乐参考（实验性）: H3 from a reference image plus a clip of a music-session song (design S-10–S-14)."""
import wave
from pathlib import Path

import pytest

from desk.media import service as service_mod
from desk.media.audio import wav_seconds_exact as real_wav_seconds_exact
from desk.media.routes import build_routes
from desk.media.service import MediaError
from media_fakes import FakeExecutor, finished_snapshot, make_service
from test_media_continue import attempts, fake_ffmpeg, first_segment  # noqa: F401  (autouse fixture)
from test_media_sessions_service import done_image, video

SONG = "b" * 32
UPLOAD = "c" * 32 + ".png"
CONFLICT = "配乐参考不能和首帧、尾帧或续写同时使用"


@pytest.fixture
def clips(monkeypatch):
    """Record every synchronous ffmpeg call (the clip cut) while still writing its output."""
    calls = []
    def fake_run(cmd, **_kw):
        calls.append(cmd)
        Path(cmd[-1]).write_bytes(b"wav")
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(service_mod.subprocess, "run", fake_run)
    return calls


def song_ref(deps, tmp_path, *, joined=None):
    songs = deps.media_sessions["music"]
    sid = songs.create()["id"]
    songs.begin_attempt(sid, {"id": SONG, "job_id": 1, "params": {"caption": "独立流行", "lyrics": "l", "duration": 20.0, "seed": 1}})
    (tmp_path / "outputs").mkdir(parents=True, exist_ok=True)
    (tmp_path / "outputs" / "song.wav").write_bytes(b"wav")
    if joined:
        (tmp_path / "outputs" / joined).write_bytes(b"wav")
    songs.settle_attempt(sid, SONG, "done", "song.wav", joined_output=joined)
    return {"kind": "music", "session_id": sid, "attempt_id": SONG}


def upload(tmp_path):
    inputs = tmp_path / "outputs" / ".inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    (inputs / UPLOAD).write_bytes(b"png")
    return UPLOAD


def ready(deps, tmp_path):
    sid = deps.media_sessions["video"].create()["id"]
    return sid, upload(tmp_path), song_ref(deps, tmp_path)


def music_ref(service, sid, ref_audio=None, **kw):
    refs = kw.pop("refs", {"ref_audio": ref_audio})
    return video(service, session_id=sid, mode="music_ref", refs=refs, **kw)


def wavs(tmp_path):
    return sorted((tmp_path / "outputs" / ".inputs").glob("*.wav"))


def test_music_ref_cuts_a_clip_and_passes_ref_image_and_ref_audio(tmp_path, clips):
    service, deps = make_service(tmp_path)
    sid, image, ref = ready(deps, tmp_path)
    finished_snapshot(service, lambda: music_ref(service, sid, ref, ref_image=image, frames=73))
    clip_cmd = clips[-1]
    assert clip_cmd[clip_cmd.index("-i") + 1] == str(tmp_path / "outputs" / "song.wav")
    assert float(clip_cmd[clip_cmd.index("-ss") + 1]) == 0
    assert float(clip_cmd[clip_cmd.index("-t") + 1]) == pytest.approx(73 / 24)
    clip = clip_cmd[-1]   # the clip is deleted once the job finalizes (S-14b); assert its path via the ffmpeg argv, not the filesystem
    cmd = deps.executor.spawned[-1]["cmd"]
    assert cmd[cmd.index("--ref-image") + 1] == str(tmp_path / "outputs" / ".inputs" / image)
    assert cmd[cmd.index("--ref-audio") + 1] == clip
    assert "--first-frame" not in cmd and "--audio-start" not in cmd
    made = attempts(deps, "video", sid)[-1]
    assert made["status"] == "done" and made["refs"] == {"ref_audio": ref}
    assert made["params"]["mode"] == "music_ref" and made["params"]["audio_start"] == 0
    assert made["params"]["ref_image"] == image
    assert wavs(tmp_path) == []   # nothing references the clip after the job (S-14b)


@pytest.mark.parametrize("frames", [24, 362])
def test_clip_length_is_clamped_to_2_to_15_seconds(tmp_path, clips, frames):
    service, deps = make_service(tmp_path)
    sid, image, ref = ready(deps, tmp_path)
    finished_snapshot(service, lambda: music_ref(service, sid, ref, ref_image=image, frames=frames, audio_start=1.5))
    clip_cmd = clips[-1]
    assert float(clip_cmd[clip_cmd.index("-t") + 1]) == max(2, min(15, frames / 24))
    assert float(clip_cmd[clip_cmd.index("-ss") + 1]) == 1.5
    assert attempts(deps, "video", sid)[-1]["params"]["audio_start"] == 1.5


def test_reference_image_from_an_image_session(tmp_path, clips):
    service, deps = make_service(tmp_path)
    sid, _image, ref = ready(deps, tmp_path)
    image_ref = {"kind": "image", "session_id": done_image(deps, tmp_path), "attempt_id": "a" * 32}
    finished_snapshot(service, lambda: music_ref(service, sid, refs={"ref_image": image_ref, "ref_audio": ref}))
    cmd = deps.executor.spawned[-1]["cmd"]
    assert cmd[cmd.index("--ref-image") + 1] == str(tmp_path / "outputs" / "cat.png")
    made = attempts(deps, "video", sid)[-1]
    assert made["params"]["ref_image"] is None
    assert made["refs"] == {"ref_image": image_ref, "ref_audio": ref}


def test_the_songs_joined_output_is_preferred(tmp_path, clips):
    service, deps = make_service(tmp_path)
    sid, image = deps.media_sessions["video"].create()["id"], upload(tmp_path)
    ref = song_ref(deps, tmp_path, joined="song-joined.wav")
    finished_snapshot(service, lambda: music_ref(service, sid, ref, ref_image=image))
    assert clips[-1][clips[-1].index("-i") + 1] == str(tmp_path / "outputs" / "song-joined.wav")
    (tmp_path / "outputs" / "song-joined.wav").unlink()
    finished_snapshot(service, lambda: music_ref(service, sid, ref, ref_image=image))
    assert clips[-1][clips[-1].index("-i") + 1] == str(tmp_path / "outputs" / "song.wav")


def _refused(service, sid, **kw):
    with pytest.raises(MediaError) as exc:
        music_ref(service, sid, **kw)
    return exc.value


@pytest.mark.parametrize("case, message", [
    ("both_images", "参考图只能从上传或图片会话二选一"),
    ("no_image", "请先选择参考图"),
    ("no_song", "请先选择一首歌"),
    ("first_frame", CONFLICT),
    ("last_frame", CONFLICT),
    ("ref_video", CONFLICT),
    ("ref_first_frame", CONFLICT),
    ("continues", CONFLICT),
    ("bad_start", None),
    ("negative_start", None),
    ("bool_start", None),
    ("soundtrack_ref", None),
])
def test_invalid_requests_are_400_and_write_nothing(tmp_path, clips, case, message):
    service, deps = make_service(tmp_path)
    sid, image, ref = ready(deps, tmp_path)
    image_ref = {"kind": "image", "session_id": done_image(deps, tmp_path), "attempt_id": "a" * 32}
    request = {"ref_audio": ref, "ref_image": image}
    if case == "both_images":
        request["refs"] = {"ref_image": image_ref, "ref_audio": ref}
    elif case == "no_image":
        del request["ref_image"]
    elif case == "no_song":
        request["refs"] = {}
    elif case in ("first_frame", "last_frame"):
        request[case] = UPLOAD
    elif case == "ref_video":
        request[case] = "d" * 32 + ".mp4"
    elif case == "ref_first_frame":
        request["refs"] = {"first_frame": image_ref, "ref_audio": ref}
    elif case == "continues":
        sid, request["continues"] = first_segment(service, deps)
    elif case == "bad_start":
        request["audio_start"] = "1"
    elif case == "negative_start":
        request["audio_start"] = -1
    elif case == "bool_start":
        request["audio_start"] = True
    else:
        request["refs"] = {"ref_audio": ref, "soundtrack": ref}
    before = len(attempts(deps, "video", sid))
    error = _refused(service, sid, **request)
    assert (error.code, error.http_status) == ("invalid_params", 400)
    if message:
        assert error.message == message
    assert len(attempts(deps, "video", sid)) == before and clips == [] and wavs(tmp_path) == []


def test_song_too_short_from_the_start_second_is_400(tmp_path, clips, monkeypatch):
    service, deps = make_service(tmp_path)
    sid, image, ref = ready(deps, tmp_path)
    monkeypatch.setattr(service_mod, "wav_seconds_exact", lambda _p: 3.0)
    error = _refused(service, sid, ref_audio=ref, ref_image=image, audio_start=2)
    assert (error.code, error.http_status, error.message) == ("invalid_params", 400, "这首歌从第 2 秒起不足 2 秒")
    assert attempts(deps, "video", sid) == [] and clips == [] and wavs(tmp_path) == []


def test_song_that_rounds_up_to_2s_but_is_actually_shorter_is_still_400(tmp_path, clips, monkeypatch):
    """1.996 s rounds to 2.00 under `wav_seconds`; the check must use the unrounded duration (S-14 fix)."""
    service, deps = make_service(tmp_path)
    sid, image, ref = ready(deps, tmp_path)
    monkeypatch.setattr(service_mod, "wav_seconds_exact", real_wav_seconds_exact)   # undo test_media_continue's autouse fake for this one test
    with wave.open(str(tmp_path / "outputs" / "song.wav"), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(1000)
        w.writeframes(b"\x00\x00" * 1996)   # exactly 1.996 s; round(1.996, 2) == 2.0
    error = _refused(service, sid, ref_audio=ref, ref_image=image, audio_start=0)
    assert (error.code, error.http_status, error.message) == ("invalid_params", 400, "这首歌从第 0 秒起不足 2 秒")
    assert attempts(deps, "video", sid) == [] and clips == [] and wavs(tmp_path) == []


def test_failed_clip_is_500_and_leaves_nothing(tmp_path, monkeypatch):
    service, deps = make_service(tmp_path)
    sid, image, ref = ready(deps, tmp_path)
    def failing_run(cmd, **_kw):
        Path(cmd[-1]).write_bytes(b"partial")
        return type("R", (), {"returncode": 1, "stdout": "", "stderr": "boom"})()
    monkeypatch.setattr(service_mod.subprocess, "run", failing_run)
    error = _refused(service, sid, ref_audio=ref, ref_image=image)
    assert (error.code, error.http_status, error.message) == ("audio_clip_failed", 500, "没能截取这段音乐")
    assert attempts(deps, "video", sid) == [] and wavs(tmp_path) == []


def test_busy_is_refused_before_cutting_the_clip(tmp_path, clips):
    service, deps = make_service(tmp_path)
    sid, image, ref = ready(deps, tmp_path)
    deps.executor.script = "block"
    video(service, session_id=sid)
    error = _refused(service, sid, ref_audio=ref, ref_image=image)
    assert (error.code, error.http_status) == ("media_busy", 409)
    assert clips == [] and wavs(tmp_path) == []
    assert len(attempts(deps, "video", sid)) == 1
    service.cancel_job()


def test_refusal_after_the_cut_removes_the_clip(tmp_path, clips):
    service, deps = make_service(tmp_path, memory_warning={"code": "insufficient_memory",
                                                            "required_bytes": 10, "available_bytes": 1})
    sid, image, ref = ready(deps, tmp_path)
    error = _refused(service, sid, ref_audio=ref, ref_image=image)
    assert (error.code, error.http_status) == ("insufficient_memory", 409)
    assert len(clips) == 1 and wavs(tmp_path) == []
    assert attempts(deps, "video", sid) == []


def test_gone_song_is_404_ref_missing(tmp_path, clips):
    service, deps = make_service(tmp_path)
    sid, image, ref = ready(deps, tmp_path)
    (tmp_path / "outputs" / "song.wav").unlink()
    error = _refused(service, sid, ref_audio=ref, ref_image=image)
    assert (error.code, error.http_status, error.message) == ("ref_missing", 404, "引用的音乐已不在")
    assert clips == []


def test_clip_wav_is_removed_once_a_successful_job_finalizes(tmp_path, clips):
    service, deps = make_service(tmp_path)
    sid, image, ref = ready(deps, tmp_path)
    finished_snapshot(service, lambda: music_ref(service, sid, ref, ref_image=image))
    assert wavs(tmp_path) == []


def test_clip_wav_is_removed_once_a_failed_job_finalizes(tmp_path, clips):
    service, deps = make_service(tmp_path, executor=FakeExecutor(script="fail"))
    sid, image, ref = ready(deps, tmp_path)
    finished_snapshot(service, lambda: music_ref(service, sid, ref, ref_image=image))
    assert wavs(tmp_path) == []


def test_route_passes_ref_image_and_audio_start_through(tmp_path):
    service, _deps = make_service(tmp_path)
    seen = {}
    service.start_video_job = lambda **kw: seen.update(kw) or {"ok": True}
    handler = {(m, p): h for m, p, h in build_routes(service)}[("POST", "/api/media/video")]
    status, _ = handler({"prompt": "p", "mode": "music_ref", "ref_image": UPLOAD, "audio_start": 4}, {})
    assert status == 200 and seen["ref_image"] == UPLOAD and seen["audio_start"] == 4
    handler({"prompt": "p"}, {})
    assert seen["ref_image"] is None and seen["audio_start"] == 0
