"""H3 / Music 3 命令行构造的唯一定义点。"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence


H3_BUDGET_GB = 70


def build_h3_command(
    mlx_h3_cmd: Sequence[str],
    h3_root: Path,
    *,
    prompt: str,
    width: int,
    height: int,
    frames: int,
    steps: int,
    output: Path,
) -> list[str]:
    """Build the complete argv for an H3 video-generation invocation."""
    return [
        *mlx_h3_cmd,
        prompt,
        "--tokenizer", str(h3_root / "tokenizer" / "tokenizer.json"),
        "--text-encoder", str(h3_root / "mlx-8bit" / "te_qwen3vl_a8g32.safetensors"),
        "--dit", str(h3_root / "mlx-8bit" / "dit_fl2va_a8g32.safetensors"),
        "--ref-dit", str(h3_root / "mlx-8bit" / "dit_ref2va_a8g32.safetensors"),
        "--video-vae", str(h3_root / "bf16" / "vae" / "minimax_h3_video_vae_fp16.safetensors"),
        "--audio-vae", str(h3_root / "bf16" / "vae" / "minimax_h3_audio_vae_fp32.safetensors"),
        "--width", str(width),
        "--height", str(height),
        "--frames", str(frames),
        "--steps", str(steps),
        "--budget", str(H3_BUDGET_GB),
        "--output", str(output),
    ]
