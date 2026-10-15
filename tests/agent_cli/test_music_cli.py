import json

from desk.testing import launch_test_harness
from desk.testing.scripts import MediaScript, fast_media_steps
from tests.agent_cli.cli_helpers import run_cli

MUS = {"model_states": {"music3": "present"}}


def _j(h, *args):
    r = run_cli(h, *args, "--json")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


def _raw(h, title):
    sid = next(s["id"] for s in h.library.media_sessions["music"].list() if s.get("title") == title)
    return h.library.media_sessions["music"].get(sid)["attempts"]


def _fake_ffmpeg(tmp_path, monkeypatch):
    ffmpeg = tmp_path / "ffmpeg"
    ffmpeg.write_text("")
    monkeypatch.setenv("LOCALMODELDESK_FFMPEG", str(ffmpeg))


def test_lyrics_required_exactly_one(tmp_path):
    lyrics = tmp_path / "l.txt"
    lyrics.write_text("[verse]\n你好", encoding="utf-8")
    with launch_test_harness(tmp_path, **MUS) as h:
        run_cli(h, "music", "new", "歌")
        assert run_cli(h, "music", "gen", "歌", "民谣").returncode == 2
        both = run_cli(h, "music", "gen", "歌", "民谣", "--lyrics", "x", "--lyrics-file", str(lyrics))
        assert both.returncode == 2
        assert run_cli(h, "music", "gen", "歌", "民谣", "--lyrics-file", str(tmp_path / "none.txt")).returncode == 2


def test_gen_with_lyrics_file_and_show_prompt_is_caption(tmp_path):
    lyrics = tmp_path / "l.txt"
    lyrics.write_text("[verse]\n你好", encoding="utf-8")
    script = MediaScript([fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **MUS) as h:
        created = _j(h, "music", "new", "歌")
        assert any(s["id"] == created["id"] for s in _j(h, "music", "sessions")["sessions"])
        body = _j(h, "music", "gen", "歌", "轻柔的民谣", "--lyrics-file", str(lyrics))
        assert body["path"].startswith("/")
        params = _raw(h, "歌")[0]["params"]
        assert params["lyrics"] == "[verse]\n你好" and params["caption"] == "轻柔的民谣" and params["duration"] == 60
        assert _j(h, "music", "show", "歌")["attempts"][0]["prompt"] == "轻柔的民谣"
        assert _j(h, "music", "wait", "歌", body["attempt_id"])["path"] == body["path"]
        assert _j(h, "music", "rename", "歌", "新歌")["title"] == "新歌"


def test_inline_lyrics_duration_and_continue(tmp_path, monkeypatch):
    _fake_ffmpeg(tmp_path, monkeypatch)
    script = MediaScript([fast_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **MUS) as h:
        run_cli(h, "music", "new", "歌")
        first = _j(h, "music", "gen", "歌", "民谣", "--lyrics", "[instrumental]", "--duration", "30")
        assert _raw(h, "歌")[0]["params"]["duration"] == 30
        second = _j(h, "music", "gen", "歌", "民谣", "--lyrics", "[instrumental]", "--duration", "30",
                    "--continue", first["attempt_id"])
        assert _raw(h, "歌")[1]["continues"] == first["attempt_id"]
        assert second["path"]


def test_join_needs_two_parts_then_composes(tmp_path, monkeypatch):
    _fake_ffmpeg(tmp_path, monkeypatch)
    script = MediaScript([fast_media_steps(), fast_media_steps()])
    with launch_test_harness(tmp_path, media_script=script, **MUS) as h:
        run_cli(h, "music", "new", "歌")
        one = _j(h, "music", "gen", "歌", "a", "--lyrics", "[instrumental]")
        two = _j(h, "music", "gen", "歌", "b", "--lyrics", "[instrumental]")
        assert run_cli(h, "music", "join", "歌", one["attempt_id"]).returncode == 2
        joined = _j(h, "music", "join", "歌", one["attempt_id"], two["attempt_id"])
        assert joined["path"].startswith("/")
        last = _raw(h, "歌")[-1]
        assert last["op"] == "compose" and last["params"]["parts"] == [one["attempt_id"], two["attempt_id"]]
