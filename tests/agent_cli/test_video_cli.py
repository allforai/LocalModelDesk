import base64
import json
import signal
import time

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, default_media_steps, fast_media_steps
from tests.agent_cli.cli_helpers import popen_cli, run_cli

VID = {"model_states": {"h3": "present", "qwen-image": "present"}, "image_runtime": True}
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def _j(h, *args):
    r = run_cli(h, *args, "--json")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _attempts(h, session):
    return _j(h, "video", "show", session)["attempts"]


def _raw_attempts(h, title):
    sid = next(s["id"] for s in h.library.media_sessions["video"].list() if s.get("title") == title)
    return h.library.media_sessions["video"].get(sid)["attempts"]


def test_new_sessions_rename_show_gen_wait(tmp_path):
    script = MediaScript([fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **VID) as h:
        created = _j(h, "video", "new", "日落")
        assert created["title"] == "日落"
        assert any(s["id"] == created["id"] for s in _j(h, "video", "sessions")["sessions"])
        assert _j(h, "video", "rename", "日落", "日出")["title"] == "日出"
        body = _j(h, "video", "gen", "日出", "湖面上的落日")
        assert body["path"].startswith("/") and body["path"].endswith(".mp4")
        shown = _attempts(h, "日出")
        assert shown[0]["id"] == body["attempt_id"] and shown[0]["prompt"] == "湖面上的落日"
        raw = _raw_attempts(h, "日出")[0]["params"]
        # defaults: UI frames 124 and steps 16; size is the spec's standard landscape tier
        assert (raw["width"], raw["height"], raw["frames"], raw["steps"]) == (768, 448, 124, 16)
        assert _j(h, "video", "wait", "日出", body["attempt_id"])["path"] == body["path"]


def test_gen_resume_hint_names_video_wait(tmp_path):
    script = MediaScript([fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **VID) as h:
        run_cli(h, "video", "new", "a")
        r = run_cli(h, "video", "gen", "a", "x", "--size", "512x288", "--steps", "4")
        assert r.returncode == 0, r.stderr
        assert "已提交：会话" in r.stderr and "lmdesk video wait" in r.stderr


def test_frames_not_in_durations_is_exit_2_and_lists_choices(tmp_path):
    with launch_test_harness(tmp_path, **VID) as h:
        run_cli(h, "video", "new", "a")
        r = run_cli(h, "video", "gen", "a", "x", "--frames", "50")
        assert r.returncode == 2
        for frames in ("49", "73", "124", "192", "243", "362"):
            assert frames in r.stderr
        assert "秒" in r.stderr


def test_continue_with_first_frame_is_exit_2(tmp_path):
    png = tmp_path / "f.png"
    png.write_bytes(PNG)
    with launch_test_harness(tmp_path, **VID) as h:
        run_cli(h, "video", "new", "a")
        r = run_cli(h, "video", "gen", "a", "x", "--continue", "abc", "--first-frame", str(png))
        assert r.returncode == 2


def test_first_frame_local_file_rules(tmp_path):
    with launch_test_harness(tmp_path, **VID) as h:
        run_cli(h, "video", "new", "a")
        assert run_cli(h, "video", "gen", "a", "x", "--first-frame", str(tmp_path / "none.png")).returncode == 2
        gif = tmp_path / "f.gif"
        gif.write_bytes(PNG)
        assert run_cli(h, "video", "gen", "a", "x", "--first-frame", str(gif)).returncode == 2
        big = tmp_path / "big.png"
        big.write_bytes(b"0" * (32 * 1024 * 1024 + 1))
        assert run_cli(h, "video", "gen", "a", "x", "--first-frame", str(big)).returncode == 2


def test_first_frame_local_file_is_uploaded_and_sent_as_image_mode(tmp_path):
    png = tmp_path / "f.png"
    png.write_bytes(PNG)
    script = MediaScript([fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **VID) as h:
        run_cli(h, "video", "new", "a")
        r = run_cli(h, "video", "gen", "a", "x", "--size", "512x288", "--steps", "4", "--first-frame", str(png), "--json")
        assert r.returncode == 0, r.stderr
        params = _raw_attempts(h, "a")[0]["params"]
        assert params["mode"] == "image" and params["first_frame"].endswith(".png")


def test_first_frame_from_image_session_attempt_is_sent_as_ref(tmp_path):
    script = MediaScript([fast_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **VID) as h:
        image = _j(h, "image", "new", "白鹭")
        shot = _j(h, "image", "gen", "白鹭", "一只白鹭", "--size", "512x512", "--steps", "4")
        run_cli(h, "video", "new", "a")
        ref = f"image:白鹭:{shot['attempt_id']}"
        r = run_cli(h, "video", "gen", "a", "展翅", "--size", "512x288", "--steps", "4", "--first-frame", ref, "--json")
        assert r.returncode == 0, r.stderr
        attempt = _raw_attempts(h, "a")[0]
        assert attempt["refs"]["first_frame"] == {"kind": "image", "session_id": image["id"], "attempt_id": shot["attempt_id"]}
        assert attempt["params"]["mode"] == "image"


def test_continue_then_wait_prints_joined_output(tmp_path):
    script = MediaScript([fast_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **VID) as h:
        run_cli(h, "video", "new", "a")
        first = _j(h, "video", "gen", "a", "一", "--size", "512x288", "--steps", "4")
        second = _j(h, "video", "gen", "a", "二", "--size", "512x288", "--steps", "4", "--continue", first["attempt_id"])
        raw = _raw_attempts(h, "a")[1]
        assert raw["continues"] == first["attempt_id"] and raw["joined_output"]
        assert second["path"].endswith(raw["joined_output"])
        assert _j(h, "video", "wait", "a", second["attempt_id"])["path"] == second["path"]


def test_join_needs_two_parts_then_produces_a_composition(tmp_path):
    script = MediaScript([fast_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **VID) as h:
        run_cli(h, "video", "new", "a")
        one = _j(h, "video", "gen", "a", "一", "--size", "512x288", "--steps", "4")
        two = _j(h, "video", "gen", "a", "二", "--size", "512x288", "--steps", "4")
        assert run_cli(h, "video", "join", "a", one["attempt_id"]).returncode == 2
        joined = _j(h, "video", "join", "a", one["attempt_id"], two["attempt_id"])
        assert joined["path"].startswith("/") and joined["path"].endswith(".mp4")
        last = _raw_attempts(h, "a")[-1]
        assert last["op"] == "compose" and last["params"]["parts"] == [one["attempt_id"], two["attempt_id"]]
        assert _attempts(h, "a")[-1]["prompt"] == f"合成：{one['attempt_id']} {two['attempt_id']}"


def test_sigterm_after_submit_keeps_job_and_wait_recovers(tmp_path):
    script = MediaScript([default_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **VID) as h:
        run_cli(h, "video", "new", "a")
        p = popen_cli(h, "video", "gen", "a", "x", "--size", "512x288", "--steps", "4")
        deadline = time.time() + 10
        while h.media.job_status()["status"] != "running":
            assert time.time() < deadline
            time.sleep(0.05)
        time.sleep(0.5)
        p.send_signal(signal.SIGTERM)
        _, stderr = p.communicate(timeout=20)
        assert p.returncode == 3 and "lmdesk video wait" in stderr
        assert h.media.job_status()["status"] == "running"
        script.step(); script.step()
        attempt = _attempts(h, "a")[0]["id"]
        assert run_cli(h, "video", "wait", "a", attempt).returncode == 0


def test_attempt_view_falls_back_to_output_when_joined_file_is_missing(tmp_path):
    from desk.agent_cli.media import _attempt_view
    attempt = {"id": "a", "status": "done", "output": "v/one.mp4", "joined_output": "v/joined.mp4",
               "joined_missing": True, "params": {}}
    assert _attempt_view("video", attempt, tmp_path)["path"] == str(tmp_path / "v/one.mp4")
    attempt["joined_missing"] = False
    assert _attempt_view("video", attempt, tmp_path)["path"] == str(tmp_path / "v/joined.mp4")


def test_failed_submit_discards_uploaded_first_frame(tmp_path, monkeypatch):
    import io
    import types
    import pytest
    from desk.agent_cli import media
    from desk.agent_cli.client import HttpError
    from desk.agent_cli.errors import CliError

    png = tmp_path / "f.png"
    png.write_bytes(PNG)
    posts = []

    class Client:
        def post(self, path, body=None, **_):
            posts.append(path)
            if path == "/api/media/inputs":
                return {"id": "a" * 32 + ".png"}
            if path == "/api/media/video":
                raise HttpError(400, "bad_request", "no", {})
            return {}

    monkeypatch.setattr(media, "snapshot", lambda *a, **k: None)
    monkeypatch.setattr(media, "decide", lambda *a, **k: types.SimpleNamespace(action="go"))
    args = types.SimpleNamespace(no_wait=True, out=None)
    with pytest.raises(CliError):
        media._run_job(Client(), "video", args, None, io.StringIO(), "s", "video", {}, "/api/media/video",
                       {}, upload=png)
    assert posts == ["/api/media/inputs", "/api/media/video", "/api/media/inputs/discard"]


def _interrupt_desk(cancel, attempts):
    class Desk:
        posts = []

        def post(self, path, body=None, **_):
            Desk.posts.append(path)
            if isinstance(cancel, Exception):
                raise cancel
            return cancel

        def get(self, path, query=None):
            if isinstance(attempts, Exception):
                raise attempts
            return {"attempts": attempts}

    Desk.posts = []
    return Desk()


def _interrupt(desk, signum):
    from desk.agent_cli.media import _interrupted
    return _interrupted(desk, "video", "s1", "a1", 7, signum, "已提交：…（中断后可用 lmdesk video wait s1 a1 继续等待）")


def test_sigint_cancel_succeeds():
    error = _interrupt(_interrupt_desk({"status": "cancelled"}, []), signal.SIGINT)
    assert error.exit_code == 3 and error.message == "已中断并取消这次生成" and error.hint is None


def test_sigint_after_the_job_already_finished_says_so_and_keeps_the_wait_hint():
    from desk.agent_cli.client import HttpError
    desk = _interrupt_desk(HttpError(409, "job_not_running", "作业 7 不在运行", {}), [{"id": "a1", "status": "done"}])
    error = _interrupt(desk, signal.SIGINT)
    assert error.exit_code == 3 and "中断前已经完成" in error.message and "取消这次" not in error.message
    assert "lmdesk video wait s1 a1" in error.hint


def test_sigint_after_the_job_already_failed_has_no_result():
    from desk.agent_cli.client import HttpError
    desk = _interrupt_desk(HttpError(409, "job_not_running", "x", {}), [{"id": "a1", "status": "failed"}])
    error = _interrupt(desk, signal.SIGINT)
    assert "已经结束" in error.message and error.hint is None


def test_sigint_with_the_desk_gone_never_claims_cancelled():
    from desk.agent_cli.client import Unreachable
    error = _interrupt(_interrupt_desk(Unreachable("refused", "x"), Unreachable("refused", "x")), signal.SIGINT)
    assert "取消" not in error.message and "仍在台面继续" in error.message and error.hint


def test_sigterm_never_cancels():
    desk = _interrupt_desk({"status": "cancelled"}, [])
    error = _interrupt(desk, signal.SIGTERM)
    assert error.message == "已中断，生成仍在台面继续" and error.hint and desk.posts == []
