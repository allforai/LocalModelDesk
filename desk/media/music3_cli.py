"""Music 3 pipeline subprocess entry point.

Run by the dedicated music interpreter with model and output paths supplied by
the caller.  Keeping the MLX import inside ``main`` allows ``--help`` to work
where the runtime package is unavailable.
"""
import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="music3_cli",
        description="Generate a song with MiniMax Music 3 (MLX)",
    )
    parser.add_argument("--root", required=True, help="music3 model root directory")
    parser.add_argument("--caption", required=True, help="style description")
    parser.add_argument("--lyrics", required=True, help="lyrics text (may be empty)")
    parser.add_argument("--duration", required=True, type=float, help="target seconds")
    parser.add_argument("--output", required=True, help="output .wav path")
    return parser


def main(argv=None) -> None:
    args = build_parser().parse_args(argv)
    from mlx_minimax_music3 import GenerationRequest, Music3Pipeline

    pipeline = Music3Pipeline(args.root)
    pipeline.generate(
        GenerationRequest(
            caption=args.caption,
            lyrics=args.lyrics,
            audio_duration=args.duration,
            seed=0,
        ),
        output=args.output,
        overwrite=True,
    )
    print(args.output, flush=True)


if __name__ == "__main__":
    main()
