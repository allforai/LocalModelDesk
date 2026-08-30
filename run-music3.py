#!/usr/bin/env python3
import argparse
import subprocess
from pathlib import Path

from mlx_minimax_music3 import GenerationRequest, Music3Pipeline

HERE = Path(__file__).resolve().parent
ROOT = HERE / "minimax-music3"
OUT_DIR = HERE / "outputs"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a song with MiniMax Music 3 (MLX)")
    parser.add_argument("--caption", required=True)
    parser.add_argument("--lyrics", required=True)
    parser.add_argument("--duration", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    output = Path(args.output) if args.output else OUT_DIR / "music3.wav"
    subprocess.run([str(HERE / "unload-llm.sh")], check=False)
    pipeline = Music3Pipeline(str(ROOT))
    result = pipeline.generate(
        GenerationRequest(
            caption=args.caption,
            lyrics=args.lyrics,
            audio_duration=args.duration,
            seed=args.seed,
        ),
        output=str(output),
        overwrite=True,
    )
    print(result.metadata.checkpoint_profile)
    print(output)


if __name__ == "__main__":
    main()
