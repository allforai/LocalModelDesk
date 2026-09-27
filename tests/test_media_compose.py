"""ffmpeg primitives: argv shape (always) and real runs on lavfi clips (when ffmpeg exists)."""
import shutil
import subprocess
from pathlib import Path

import pytest

from desk.media import compose

FF = shutil.which("ffmpeg")
FP = shutil.which("ffprobe")
needs_ffmpeg = pytest.mark.skipif(not (FF and FP), reason="ffmpeg/ffprobe not installed")


def test_every_command_ends_with_its_output(tmp_path):
    out = tmp_path / "o"
    for cmd in (compose.last_frame_command("ff", Path("v.mp4"), out),
                compose.concat_video_command("ff", [(Path("a.mp4"), False), (Path("b.mp4"), True)], (512, 288), out),
                compose.crossfade_audio_command("ff", [(Path("a.wav"), 20.0), (Path("b.wav"), 20.0)], out),
                compose.soundtrack_command("ff", Path("v.mp4"), Path("a.wav"), out)):
        assert cmd[0] == "ff" and cmd[1] == "-y" and cmd[-1] == str(out)


def test_concat_drops_first_frame_only_where_asked(tmp_path):
    cmd = compose.concat_video_command("ff", [(Path("a.mp4"), False), (Path("b.mp4"), True)], (512, 288), tmp_path / "o.mp4")
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "[0:v]trim" not in graph and "[1:v]trim=start_frame=1" in graph
    assert "[1:a]atrim=start=0.041667" in graph and "[0:a]atrim" not in graph
    assert "scale=512:288:force_original_aspect_ratio=decrease,pad=512:288" in graph
    assert "concat=n=2:v=1:a=1" in graph


def test_crossfade_skips_fade_next_to_a_short_segment(tmp_path):
    cmd = compose.crossfade_audio_command("ff", [(Path("a.wav"), 20.0), (Path("b.wav"), 2.0), (Path("c.wav"), 20.0)],
                                          tmp_path / "o.wav")
    graph = cmd[cmd.index("-filter_complex") + 1]
    assert "acrossfade" not in graph and graph.count("concat=n=2:v=0:a=1") == 2
    cmd = compose.crossfade_audio_command("ff", [(Path("a.wav"), 20.0), (Path("b.wav"), 20.0)], tmp_path / "o.wav")
    assert "acrossfade=d=1.5:c1=tri:c2=tri" in cmd[cmd.index("-filter_complex") + 1]


def test_ffmpeg_path_honours_override_and_reports_absence(tmp_path, monkeypatch):
    fake = tmp_path / "ffmpeg"
    fake.write_text("#!/bin/sh\n")
    monkeypatch.setenv("LOCALMODELDESK_FFMPEG", str(fake))
    assert compose.ffmpeg_path() == str(fake)
    monkeypatch.setenv("LOCALMODELDESK_FFMPEG", str(tmp_path / "nope"))   # invalid override falls back to PATH
    monkeypatch.setenv("PATH", str(tmp_path / "empty"))
    assert compose.ffmpeg_path() is None
    monkeypatch.delenv("LOCALMODELDESK_FFMPEG")
    assert compose.ffmpeg_path() is None


def test_find_tool_falls_back_to_path_when_override_is_invalid(tmp_path, monkeypatch):
    bin_dir = tmp_path / "bin"; bin_dir.mkdir()
    on_path = bin_dir / "ffmpeg"
    on_path.write_text("#!/bin/sh\n"); on_path.chmod(0o755)
    monkeypatch.setenv("PATH", str(bin_dir))
    monkeypatch.setenv("LOCALMODELDESK_FFMPEG", str(tmp_path / "nope"))
    assert compose.find_tool("ffmpeg") == str(on_path)


def test_probe_size_timeout_is_a_value_error(monkeypatch):
    def slow(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, kw.get("timeout"))
    monkeypatch.setattr(compose.subprocess, "run", slow)
    with pytest.raises(ValueError):
        compose.probe_size("ffprobe", Path("v.mp4"))


def lavfi_video(path: Path, size="512x288", seconds=1):
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"testsrc=size={size}:rate=24",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=32000", "-t", str(seconds),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path)], check=True)


def lavfi_wav(path: Path, seconds):
    subprocess.run([FF, "-y", "-v", "error", "-f", "lavfi", "-i", f"sine=frequency=440:sample_rate=44100",
                    "-t", str(seconds), "-ac", "2", str(path)], check=True)


def duration(path: Path) -> float:
    out = subprocess.run([FP, "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return float(out)


@needs_ffmpeg
def test_real_concat_with_mixed_sizes_and_dropped_frame(tmp_path):
    lavfi_video(tmp_path / "a.mp4", "512x288")
    lavfi_video(tmp_path / "b.mp4", "768x448")
    out = tmp_path / "joined.mp4"
    subprocess.run(compose.concat_video_command(FF, [(tmp_path / "a.mp4", False), (tmp_path / "b.mp4", True)],
                                                compose.probe_size(FP, tmp_path / "a.mp4"), out), check=True)
    assert compose.probe_size(FP, out) == (512, 288)
    assert abs(duration(out) - (2 - 1 / 24)) < 0.1


@needs_ffmpeg
def test_real_crossfade_and_last_frame_and_soundtrack(tmp_path):
    lavfi_wav(tmp_path / "a.wav", 5); lavfi_wav(tmp_path / "b.wav", 5)
    song = tmp_path / "song.wav"
    subprocess.run(compose.crossfade_audio_command(FF, [(tmp_path / "a.wav", 5.0), (tmp_path / "b.wav", 5.0)], song), check=True)
    assert abs(duration(song) - 8.5) < 0.1
    lavfi_video(tmp_path / "v.mp4")
    png = tmp_path / "last.png"
    subprocess.run(compose.last_frame_command(FF, tmp_path / "v.mp4", png), check=True)
    assert png.stat().st_size > 0
    swapped = tmp_path / "swapped.mp4"
    subprocess.run(compose.soundtrack_command(FF, tmp_path / "v.mp4", song, swapped), check=True)
    assert abs(duration(swapped) - 1.0) < 0.1


def test_soundtrack_command_copies_video_and_pads_audio_to_the_video_length(tmp_path):
    out = tmp_path / "o.mp4"
    cmd = compose.soundtrack_command("ff", Path("v.mp4"), Path("song.wav"), out)
    assert cmd[:2] == ["ff", "-y"] and cmd[-1] == str(out)
    assert cmd[cmd.index("-c:v") + 1] == "copy" and cmd[cmd.index("-af") + 1] == "apad"
    assert "-shortest" in cmd and cmd.index("-af") < cmd.index("-shortest")
    assert cmd[cmd.index("-i") + 1] == "v.mp4" and "song.wav" in cmd


@needs_ffmpeg
@pytest.mark.parametrize("video_s, song_s", [(1, 5), (3, 1)])
def test_real_soundtrack_output_is_as_long_as_the_video(tmp_path, video_s, song_s):
    lavfi_video(tmp_path / "v.mp4", seconds=video_s)
    lavfi_wav(tmp_path / "song.wav", song_s)
    out = tmp_path / "scored.mp4"
    subprocess.run(compose.soundtrack_command(FF, tmp_path / "v.mp4", tmp_path / "song.wav", out), check=True)
    assert abs(duration(out) - video_s) < 0.15


def test_audio_clip_command_seeks_then_cuts_and_writes_wav_last(tmp_path):
    out = tmp_path / "clip.wav"
    cmd = compose.audio_clip_command("ff", Path("song.wav"), 1.5, 3.0416, out)
    assert cmd[:2] == ["ff", "-y"] and cmd[-1] == str(out)
    assert float(cmd[cmd.index("-ss") + 1]) == 1.5 and float(cmd[cmd.index("-t") + 1]) == 3.0416
    assert cmd[cmd.index("-i") + 1] == "song.wav"


@needs_ffmpeg
def test_real_audio_clip_is_as_long_as_asked(tmp_path):
    lavfi_wav(tmp_path / "song.wav", 5)
    out = tmp_path / "clip.wav"
    subprocess.run(compose.audio_clip_command(FF, tmp_path / "song.wav", 1, 2, out), check=True)
    assert abs(duration(out) - 2) < 0.05
