"""Completion criterion 2: new session → generate → continue → joined → compose, real ffmpeg, fake models."""
import shutil
import subprocess
from pathlib import Path

import pytest

from desk.media.executor import SubprocessExecutor
from desk.media.routes import build_routes
from media_fakes import finished_snapshot, make_service
from test_media_sessions_service import music_ready

FF, FP = shutil.which("ffmpeg"), shutil.which("ffprobe")
pytestmark = pytest.mark.skipif(not (FF and FP), reason="ffmpeg/ffprobe not installed")


class LavfiExecutor:
    """Model commands produce a real 1 s clip at --output; ffmpeg commands really run."""
    def __init__(self):
        self.real = SubprocessExecutor()

    def spawn(self, cmd, *, extra_env=None):
        if "--output" not in cmd:
            return self.real.spawn(cmd)
        out = cmd[cmd.index("--output") + 1]
        if out.endswith(".mp4"):
            synth = [FF, "-y", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=512x288:rate=24", "-f", "lavfi",
                     "-i", "sine=frequency=440:sample_rate=32000", "-t", "1", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                     "-c:a", "aac", "-shortest", out]
        else:
            synth = [FF, "-y", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=44100",
                     "-t", "5", "-ac", "2", out]
        return self.real.spawn(synth)


def duration(path: Path) -> float:
    return float(subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                                capture_output=True, text=True, check=True).stdout)


def post(service, path, body):
    handler = next(h for m, p, h in build_routes(service) if (m, p) == ("POST", path))
    status, payload = handler(body, {})
    assert status == 200, payload
    return payload


@pytest.mark.parametrize("kind", ["video", "music"])
def test_generate_continue_join_compose(tmp_path, kind):
    service, deps = make_service(tmp_path, executor=LavfiExecutor())
    music_ready(service, tmp_path)
    store = deps.media_sessions[kind]
    sid = store.create()["id"]
    body = ({"prompt": "p", "width": 512, "height": 288, "frames": 24, "steps": 4} if kind == "video"
            else {"caption": "c", "lyrics": "[verse]\nla", "duration": 5.0})
    path = f"/api/media/{kind}"
    first = finished_snapshot(service, lambda: post(service, path, {**body, "session_id": sid}))["attempt_id"]
    finished_snapshot(service, lambda: post(service, path, {**body, "session_id": sid, "continues": first}))
    second = store.get(sid)["attempts"][1]
    assert second["status"] == "done" and second["joined_error"] is None, second
    joined = tmp_path / "outputs" / second["joined_output"]
    expected = 2 - 1 / 24 if kind == "video" else 10 - 1.5
    assert abs(duration(joined) - expected) < 0.15
    finished_snapshot(service, lambda: post(service, "/api/media/compose",
                                            {"kind": kind, "session_id": sid, "parts": [first, second["id"]]}))
    made = store.get(sid)["attempts"][2]
    assert made["op"] == "compose" and made["status"] == "done" and (tmp_path / "outputs" / made["output"]).is_file()
