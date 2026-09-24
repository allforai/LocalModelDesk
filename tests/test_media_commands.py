"""H3 / Music 3 命令构造的逐参数断言。"""
from pathlib import Path

from desk.media.commands import H3_BUDGET_GB, build_h3_command, build_music_command


def test_h3_budget_constant():
    # mlx_h3 pins the whole budget as wired memory and refuses to start when it exceeds the
    # system's GPU working-set limit. 70 GiB held that much for jobs measured at 27–34 GiB and
    # could not start on 64 GiB machines (#15's reporter edited it to 48); 40 runs fine.
    assert H3_BUDGET_GB == 40


def test_build_h3_command_full_argv_equality():
    argv = build_h3_command(
        ("/opt/py/bin/python3.13", "-s", "-c", "from mlx_h3.cli import main; main()"),
        Path("/m/minimax-h3"),
        prompt="rain on a quiet street",
        width=512,
        height=288,
        frames=73,
        steps=10,
        output=Path("/out/h3-20260831-101500.mp4"),
    )
    assert argv == [
        "/opt/py/bin/python3.13", "-s", "-c", "from mlx_h3.cli import main; main()",
        "rain on a quiet street",
        "--tokenizer", "/m/minimax-h3/tokenizer/tokenizer.json",
        "--text-encoder", "/m/minimax-h3/mlx-8bit/te_qwen3vl_a8g32.safetensors",
        "--dit", "/m/minimax-h3/mlx-8bit/dit_fl2va_a8g32.safetensors",
        "--ref-dit", "/m/minimax-h3/mlx-8bit/dit_ref2va_a8g32.safetensors",
        "--video-vae", "/m/minimax-h3/bf16/vae/minimax_h3_video_vae_fp16.safetensors",
        "--audio-vae", "/m/minimax-h3/bf16/vae/minimax_h3_audio_vae_fp32.safetensors",
        "--width", "512",
        "--height", "288",
        "--frames", "73",
        "--steps", "10",
        "--budget", "40",
        "--output", "/out/h3-20260831-101500.mp4",
    ]


def test_build_h3_command_single_element_dev_prefix():
    argv = build_h3_command(
        ("/Users/x/.local/bin/mlx-h3",),
        Path("/m/minimax-h3"),
        prompt="p",
        width=1024,
        height=576,
        frames=124,
        steps=20,
        output=Path("/out/v.mp4"),
    )
    assert argv[0] == "/Users/x/.local/bin/mlx-h3"
    assert argv[1] == "p"
    assert argv[argv.index("--frames") + 1] == "124"


def test_build_music_command_full_argv_equality():
    argv = build_music_command(
        Path("/opt/py/bin/python3.13"),
        Path("/app/desk/media/music3_cli.py"),
        Path("/m/minimax-music3"),
        caption="warm acoustic folk",
        lyrics="A small light in the rain",
        duration=30.5,
        output=Path("/out/music3-20260831-101500.wav"),
    )
    assert argv == [
        "/opt/py/bin/python3.13", "/app/desk/media/music3_cli.py",
        "--root", "/m/minimax-music3",
        "--caption", "warm acoustic folk",
        "--lyrics", "A small light in the rain",
        "--duration", "30.5",
        "--output", "/out/music3-20260831-101500.wav",
    ]


def test_h3_fixed_flags_have_one_definition_within_desk():
    desk_root = Path(__file__).parents[1] / "desk"
    sources = list(desk_root.rglob("*.py"))
    for flag in ("--tokenizer", "--text-encoder", "--dit", "--ref-dit", "--video-vae", "--audio-vae"):
        occurrences = [
            path.relative_to(desk_root)
            for path in sources
            if flag in path.read_text()
        ]
        assert occurrences == [Path("media/commands.py")]
