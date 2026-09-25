"""ffmpeg argv builders for joining, composing and frame extraction (design B-50/B-51/§6).

Pure functions: no session knowledge, no business rules. Every command puts `-y`
right after the executable and the output path last, so the job runner and the
test executors can find what a command writes without parsing ffmpeg syntax.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

FPS = 24                 # H3 output frame rate
CROSSFADE_S = 1.5
SHORT_SEGMENT_S = 3.0    # a seam next to a shorter segment is a plain cut
FFMPEG_MISSING = "需要 ffmpeg 才能拼接成片"


def _find(name: str) -> str | None:
    override = os.environ.get("LOCALMODELDESK_" + name.upper())
    if override:
        return override if Path(override).is_file() else None
    return shutil.which(name)


def ffmpeg_path() -> str | None:
    return _find("ffmpeg")


def ffprobe_path() -> str | None:
    return _find("ffprobe")


def probe_size(ffprobe: str, video: Path) -> tuple[int, int]:
    result = subprocess.run([ffprobe, "-v", "error", "-select_streams", "v:0", "-show_entries",
                             "stream=width,height", "-of", "csv=p=0:s=x", str(video)],
                            capture_output=True, text=True, timeout=30)
    try:
        width, height = (int(n) for n in result.stdout.strip().split("x"))
    except ValueError as exc:
        raise ValueError(f"cannot read video size of {video.name}") from exc
    return width, height


def last_frame_command(ffmpeg: str, video: Path, png: Path) -> list[str]:
    return [ffmpeg, "-y", "-v", "error", "-sseof", "-0.1", "-i", str(video),
            "-frames:v", "1", "-update", "1", str(png)]


def concat_video_command(ffmpeg: str, parts: list[tuple[Path, bool]], size: tuple[int, int],
                         output: Path) -> list[str]:
    width, height = size
    inputs, chains, labels = [], [], []
    for i, (path, drop_first) in enumerate(parts):
        inputs += ["-i", str(path)]
        v = f"[{i}:v]" + ("trim=start_frame=1,setpts=PTS-STARTPTS," if drop_first else "")
        v += (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
              f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={FPS}[v{i}]")
        a = f"[{i}:a]" + (f"atrim=start={1 / FPS:.6f},asetpts=PTS-STARTPTS," if drop_first else "")
        a += f"aresample=48000[a{i}]"
        chains += [v, a]
        labels.append(f"[v{i}][a{i}]")
    graph = ";".join(chains) + ";" + "".join(labels) + f"concat=n={len(parts)}:v=1:a=1[v][a]"
    return [ffmpeg, "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", str(output)]


def crossfade_audio_command(ffmpeg: str, parts: list[tuple[Path, float]], output: Path) -> list[str]:
    inputs, steps = [], []
    for path, _seconds in parts:
        inputs += ["-i", str(path)]
    current = "[0:a]"
    for i in range(1, len(parts)):
        short = min(parts[i - 1][1], parts[i][1]) < SHORT_SEGMENT_S
        seam = ("concat=n=2:v=0:a=1" if short else f"acrossfade=d={CROSSFADE_S}:c1=tri:c2=tri")
        label = f"[x{i}]"
        steps.append(f"{current}[{i}:a]{seam}{label}")
        current = label
    graph = ";".join(steps)
    return [ffmpeg, "-y", "-v", "error", *inputs, "-filter_complex", graph, "-map", current,
            "-c:a", "pcm_s16le", str(output)]


def replace_audio_command(ffmpeg: str, video: Path, audio: Path, output: Path) -> list[str]:
    return [ffmpeg, "-y", "-v", "error", "-i", str(video), "-i", str(audio), "-map", "0:v", "-map", "1:a",
            "-c:v", "copy", "-c:a", "aac", "-shortest", str(output)]
