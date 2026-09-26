"""Video sessions: required session, first frame from an image session (spec V-01–V-05)."""
import pytest

from desk.media.service import MediaError
from media_fakes import finished_snapshot, make_service
from test_media_sessions_service import done_image, video


def video_session(deps):
    return deps.media_sessions["video"].create()["id"]


@pytest.mark.parametrize("session_id, code, status", [(None, "session_required", 400), ("f" * 32, "session_not_found", 404)])
def test_video_requires_a_session(tmp_path, session_id, code, status):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=session_id)
    assert (exc.value.code, exc.value.http_status) == (code, status)
    assert deps.executor.spawned == []


def image_ref(deps, tmp_path):
    return {"kind": "image", "session_id": done_image(deps, tmp_path), "attempt_id": "a" * 32}


def test_first_frame_ref_becomes_the_first_frame_argument(tmp_path):
    service, deps = make_service(tmp_path)
    sid, ref = video_session(deps), image_ref(deps, tmp_path)
    snap = finished_snapshot(service, lambda: video(service, session_id=sid, mode="image", refs={"first_frame": ref}))
    cmd = deps.executor.spawned[-1]["cmd"]
    assert cmd[cmd.index("--first-frame") + 1] == str(tmp_path / "outputs" / "cat.png")
    attempt = deps.media_sessions["video"].get(sid)["attempts"][0]
    assert attempt["refs"] == {"first_frame": ref} and attempt["params"].get("first_frame") is None
    assert deps.history.entries[-1]["refs"] == {"first_frame": ref}
    assert snap["status"] == "done"


def test_history_has_no_refs_key_without_refs(tmp_path):
    service, deps = make_service(tmp_path)
    finished_snapshot(service, lambda: video(service, session_id=video_session(deps)))
    assert "refs" not in deps.history.entries[-1]


@pytest.mark.parametrize("extra", [{"mode": "text"}, {"mode": "image", "first_frame": "a" * 32 + ".png"}])
def test_first_frame_ref_conflicts_are_400(tmp_path, extra):
    service, deps = make_service(tmp_path)
    sid, ref = video_session(deps), image_ref(deps, tmp_path)
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, refs={"first_frame": ref}, **extra)
    assert (exc.value.code, exc.value.message) == ("invalid_params", "首帧只能从上传或图片会话二选一")
    assert deps.media_sessions["video"].get(sid)["attempts"] == []


def test_first_frame_ref_with_continues_is_400(tmp_path):
    service, deps = make_service(tmp_path)
    sid, ref = video_session(deps), image_ref(deps, tmp_path)
    first = finished_snapshot(service, lambda: video(service, session_id=sid))["attempt_id"]
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, mode="image", refs={"first_frame": ref}, continues=first)
    assert exc.value.code == "invalid_params"


def test_gone_first_frame_ref_is_404(tmp_path):
    service, deps = make_service(tmp_path)
    sid, ref = video_session(deps), image_ref(deps, tmp_path)
    (tmp_path / "outputs" / "cat.png").unlink()
    with pytest.raises(MediaError) as exc:
        video(service, session_id=sid, mode="image", refs={"first_frame": ref})
    assert (exc.value.code, exc.value.http_status, exc.value.message) == ("ref_missing", 404, "引用的图片已不在")
