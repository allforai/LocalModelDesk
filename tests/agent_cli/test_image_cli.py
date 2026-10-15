import json
import signal
import time

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, cancellable_media_steps, default_media_steps, fast_media_steps
from tests.agent_cli.cli_helpers import popen_cli, run_cli

IMG = {"model_states": {"qwen-image": "present"}, "image_runtime": True}


def _new(h, name):
    r = run_cli(h, "image", "new", name, "--json")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def test_new_sessions_rename_show(tmp_path):
    with launch_test_harness(tmp_path, **IMG) as h:
        created = _new(h, "首页 banner")
        assert created["title"] == "首页 banner"
        listed = json.loads(run_cli(h, "image", "sessions", "--json").stdout)["sessions"]
        assert any(s["id"] == created["id"] and s["title"] == "首页 banner" for s in listed)
        r = run_cli(h, "image", "rename", "首页 banner", "首页大图", "--json")
        assert json.loads(r.stdout)["title"] == "首页大图"
        shown = json.loads(run_cli(h, "image", "show", created["id"], "--json").stdout)
        assert shown["attempts"] == []


def test_session_name_ambiguous_is_exit_2_and_prefix_never_matches(tmp_path):
    with launch_test_harness(tmp_path, **IMG) as h:
        a = _new(h, "图标")
        _new(h, "图标")
        assert run_cli(h, "image", "show", "图标").returncode == 2
        assert run_cli(h, "image", "show", a["id"][:8]).returncode == 5
        assert run_cli(h, "image", "show", " 不存在 ").returncode == 5


def test_gen_writes_an_attempt_and_prints_absolute_path(tmp_path):
    script = MediaScript([fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        s = _new(h, "猫")
        r = run_cli(h, "image", "gen", "猫", "一只橘猫", "--size", "512x512", "--steps", "4", "--json")
        assert r.returncode == 0, r.stderr
        body = json.loads(r.stdout)
        assert body["session_id"] == s["id"] and body["path"].startswith("/") and body["path"].endswith(".png")
        assert "已提交：会话" in r.stderr and "lmdesk image wait" in r.stderr
        shown = json.loads(run_cli(h, "image", "show", "猫", "--json").stdout)
        assert shown["attempts"][0]["id"] == body["attempt_id"]
        assert shown["attempts"][0]["path"] == body["path"]


def test_gen_out_copies_creates_dirs_and_handles_existing(tmp_path):
    script = MediaScript([fast_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        target = tmp_path / "proj" / "assets" / "hero.png"
        r = run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--out", str(target))
        assert r.returncode == 0, r.stderr
        assert r.stdout.strip() == str(target) and target.is_file()
        r2 = run_cli(h, "image", "gen", "猫", "y", "--size", "512x512", "--steps", "4", "--out", str(target))
        assert "已覆盖" in r2.stderr
        folder = tmp_path / "proj" / "assets"
        r3 = run_cli(h, "image", "wait", "猫", json.loads(run_cli(h, "image", "show", "猫", "--json").stdout)["attempts"][0]["id"],
                     "--out", str(folder))
        assert r3.returncode == 0 and r3.stdout.strip().startswith(str(folder) + "/")


def test_gen_from_passes_base(tmp_path):
    script = MediaScript([fast_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        first = json.loads(run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--json").stdout)
        r = run_cli(h, "image", "gen", "猫", "改成蓝色", "--from", first["attempt_id"], "--strength", "0.6", "--json")
        assert r.returncode == 0, r.stderr
        shown = json.loads(run_cli(h, "image", "show", "猫", "--json").stdout)
        assert shown["attempts"][-1]["base"]["attempt_id"] == first["attempt_id"]


def test_no_wait_then_wait(tmp_path):
    script = MediaScript([default_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        r = run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--no-wait", "--json")
        assert r.returncode == 0, r.stderr
        sub = json.loads(r.stdout)
        script.step(); script.step()
        r2 = run_cli(h, "image", "wait", "猫", sub["attempt_id"], "--json")
        assert r2.returncode == 0, r2.stderr
        assert json.loads(r2.stdout)["attempt_id"] == sub["attempt_id"]


def test_wait_unknown_attempt_is_5(tmp_path):
    with launch_test_harness(tmp_path, **IMG) as h:
        _new(h, "猫")
        assert run_cli(h, "image", "wait", "猫", "f" * 32).returncode == 5


def test_sigterm_after_submit_keeps_job_and_wait_recovers(tmp_path):
    script = MediaScript([default_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4")
        _wait_running(h)
        time.sleep(0.5)
        p.send_signal(signal.SIGTERM)
        _, stderr = p.communicate(timeout=20)
        assert p.returncode == 3
        assert "lmdesk image wait" in stderr
        assert h.media.job_status()["status"] == "running"
        script.step(); script.step()
        attempt = json.loads(run_cli(h, "image", "show", "猫", "--json").stdout)["attempts"][0]["id"]
        assert run_cli(h, "image", "wait", "猫", attempt).returncode == 0


def test_sigint_after_submit_cancels_only_own_job(tmp_path):
    script = MediaScript([cancellable_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫")
        p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4")
        _wait_running(h)
        time.sleep(0.5)
        p.send_signal(signal.SIGINT)
        p.communicate(timeout=20)
        assert p.returncode == 3
        assert h.media.job_status()["status"] == "cancelled"


def test_slot_reused_by_another_job_still_reads_result_from_session(tmp_path):
    script = MediaScript([default_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫"); _new(h, "狗")
        p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--json")
        _wait_running(h)
        script.step(); script.step()
        _wait_idle(h)
        h.media.start_image_job(session_id=_id(h, "狗"), prompt="y", width=512, height=512, steps=4)
        out, err = p.communicate(timeout=30)
        assert p.returncode == 0, err
        assert json.loads(out)["session_id"] == _id(h, "猫")


def test_memory_warning_is_4_then_force_succeeds(tmp_path):
    # 测试台面的预算容量是固定的 100 GiB，调 MemoryScript 触发不了警告；
    # 改让仲裁器对图片作业回报 memory_warning（与生产里 workload > 容量时的形状一致）。
    script = MediaScript([fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        real = h.arbiter.can_start_heavy
        gib = 1024 ** 3

        def with_warning(kind, params=None, key=None, **kw):
            answer = dict(real(kind, params=params, key=key, **kw))
            if kind == "image" and params is not None:
                answer["memory_warning"] = {"code": "insufficient_memory", "required_bytes": 30 * gib,
                                            "available_bytes": 1 * gib, "source": "predicted", "message": "x"}
            return answer

        h.arbiter.can_start_heavy = with_warning
        _new(h, "猫")
        r = run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4")
        assert r.returncode == 4 and "GiB" in r.stderr
        r2 = run_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--force")
        assert r2.returncode == 0, r2.stderr


def test_busy_desk_then_free_retries_without_failing(tmp_path):
    script = MediaScript([default_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **IMG) as h:
        _new(h, "猫"); _new(h, "狗")
        h.media.start_image_job(session_id=_id(h, "狗"), prompt="先占着", width=512, height=512, steps=4)
        p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4", "--json")
        time.sleep(1.0)
        script.step(); script.step()
        out, err = p.communicate(timeout=40)
        assert p.returncode == 0, err


def test_desk_quitting_midwait_is_exit_1_with_resume_hint(tmp_path):
    script = MediaScript([default_media_steps()])
    h = launch_test_harness(tmp_path, media_script=script, **IMG)
    _new(h, "猫")
    p = popen_cli(h, "image", "gen", "猫", "x", "--size", "512x512", "--steps", "4")
    _wait_running(h)
    h.close()
    _, err = p.communicate(timeout=30)
    assert p.returncode == 1
    assert "lmdesk image wait" in err


def _id(h, title):
    return next(s["id"] for s in h.library.media_sessions["image"].list() if s.get("title") == title)


def _wait_running(h, timeout=10):
    deadline = time.time() + timeout
    while h.media.job_status()["status"] != "running":
        assert time.time() < deadline
        time.sleep(0.05)


def _wait_idle(h, timeout=10):
    deadline = time.time() + timeout
    while h.media.job_status()["status"] == "running":
        assert time.time() < deadline
        time.sleep(0.05)


def test_out_with_trailing_slash_is_a_directory_even_if_missing(tmp_path):
    import io
    from desk.agent_cli.media import _copy_out
    src = tmp_path / "a.png"
    src.write_bytes(b"png")
    final = _copy_out(src, str(tmp_path / "assets") + "/", io.StringIO())
    assert final == (tmp_path / "assets" / "a.png").resolve() and final.read_bytes() == b"png"


def test_usage_error_with_json_prints_error_object(capsys):
    from desk.agent_cli.cli import main
    out = __import__("io").StringIO()
    assert main(["image", "gen", "--json"], out=out) == 2
    assert json.loads(out.getvalue())["error"]["code"] == "usage"
