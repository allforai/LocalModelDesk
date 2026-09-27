import base64
import struct
import subprocess
import zlib

import pytest

from desk.media import compose, inputs
from desk.media.inputs import save_input
from desk.media.routes import build_routes
from desk.media.service import MediaError
from desk.testing.seed import TINY_MP4
from media_fakes import make_service, finished_snapshot

PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+a9ZkAAAAASUVORK5CYII=")


def make_valid_png(width: int, height: int) -> bytes:
    """A larger real PNG so a mid-file truncation still leaves valid header/IHDR chunks."""
    def chunk(tag: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + tag + payload + struct.pack(">I", zlib.crc32(tag + payload))

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    raw = b"".join(b"\x00" + bytes([(x + y) % 256 for x in range(width * 3)]) for y in range(height))
    idat = chunk(b"IDAT", zlib.compress(raw))
    iend = chunk(b"IEND", b"")
    return signature + ihdr + idat + iend


def test_truncated_png_is_rejected(tmp_path):
    png = make_valid_png(64, 64)
    data = base64.b64encode(png[: len(png) // 3]).decode()
    with pytest.raises(ValueError) as exc:
        save_input(tmp_path, "a.png", data)
    assert str(exc.value) == "图片文件已损坏，无法解码"
    assert not list((tmp_path / ".inputs").glob("*")) if (tmp_path / ".inputs").exists() else True


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
    sid = deps.media_sessions["video"].create()["id"]
    params = dict(prompt="waves", width=512, height=288, frames=49, steps=16,
                  mode=mode, use_audio=False, session_id=sid, **{key: asset["id"]})
    snapshot = finished_snapshot(service, lambda: service.start_video_job(**params))
    command = deps.executor.spawned[0]["cmd"]
    assert command[command.index(flag) + 1] == str(tmp_path / "outputs" / ".inputs" / asset["id"])
    assert snapshot["params"][key] == asset["id"]
    assert snapshot["status"] == "done"
    assert (tmp_path / "outputs" / ".inputs" / asset["id"]).read_bytes() == content


@pytest.mark.parametrize("asset_id, message", [
    (None, "素材编号无效，请重新选择文件"),
    ("../../secret.png", "素材编号无效，请重新选择文件"),
    ("a" * 32 + ".png", "素材不存在或类型不匹配，请重新选择文件"),
])
def test_missing_or_unsafe_inputs_rejected_before_acquire(tmp_path, asset_id, message):
    service, deps = make_service(tmp_path)
    sid = deps.media_sessions["video"].create()["id"]
    with pytest.raises(MediaError) as exc:
        service.start_video_job(prompt="p", width=512, height=288, frames=49, steps=16,
                                mode="image", first_frame=asset_id, session_id=sid)
    assert (exc.value.code, exc.value.message) == ("invalid_input", message)
    assert not deps.arbiter.acquired


def test_invalid_upload_removed(tmp_path):
    service, _ = make_service(tmp_path)
    with pytest.raises(MediaError):
        service.upload_input(name="bad.png", data=base64.b64encode(b"not an image").decode())
    assert not list((tmp_path / "outputs" / ".inputs").iterdir())


@pytest.mark.parametrize("valid", [True, False])
def test_tool_lookup_matches_compose(tmp_path, monkeypatch, valid):
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    on_path = bin_dir / "ffprobe"
    on_path.write_text("#!/bin/sh\n"); on_path.chmod(0o755)
    override = tmp_path / "override-ffprobe"
    if valid:
        override.write_text("#!/bin/sh\n")
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("LOCALMODELDESK_FFPROBE", str(override))
    assert inputs._tool("ffprobe") == compose.find_tool("ffprobe") == str(override if valid else on_path)
