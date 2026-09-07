import base64
import subprocess

import pytest

from desk.media.routes import build_routes
from desk.media.service import MediaError
from desk.testing.seed import TINY_MP4
from media_fakes import make_service, finished_snapshot

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9ZkAAAAASUVORK5CYII=")


@pytest.mark.parametrize("mode,name,content,key,flag", [
    ("image", "first.png", PNG, "first_frame", "--first-frame"),
    ("reference", "clip.mp4", TINY_MP4, "ref_video", "--ref-video-silent"),
])
def test_uploaded_asset_reaches_real_command_builder(tmp_path, mode, name, content, key, flag):
    if mode == "reference":
        clip = tmp_path / "sample.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "color=c=blue:s=32x32:d=1",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", str(clip)], check=True)
        content = clip.read_bytes()
    service, deps = make_service(tmp_path)
    routes = {(m, p): h for m, p, h in build_routes(service)}
    code, asset = routes["POST", "/api/media/inputs"]({"name": name, "data": base64.b64encode(content).decode()}, {})
    assert code == 200, asset
    params = dict(prompt="waves", width=512, height=288, frames=49, steps=16,
                  mode=mode, use_audio=False, **{key: asset["id"]})
    snapshot = finished_snapshot(service, lambda: service.start_video_job(**params))
    command = deps.executor.spawned[0]["cmd"]
    assert command[command.index(flag) + 1] == str(tmp_path / "outputs" / ".inputs" / asset["id"])
    assert snapshot["params"][key] == asset["id"]
    assert snapshot["status"] == "done"
    assert (tmp_path / "outputs" / ".inputs" / asset["id"]).read_bytes() == content


@pytest.mark.parametrize("asset_id", [None, "../../secret.png", "a" * 32 + ".png"])
def test_missing_or_unsafe_inputs_rejected_before_acquire(tmp_path, asset_id):
    service, deps = make_service(tmp_path)
    with pytest.raises(MediaError):
        service.start_video_job(prompt="p", width=512, height=288, frames=49, steps=16,
                                mode="image", first_frame=asset_id)
    assert not deps.arbiter.acquired


def test_invalid_upload_removed(tmp_path):
    service, _ = make_service(tmp_path)
    with pytest.raises(MediaError):
        service.upload_input(name="bad.png", data=base64.b64encode(b"not an image").decode())
    assert not list((tmp_path / "outputs" / ".inputs").iterdir())
