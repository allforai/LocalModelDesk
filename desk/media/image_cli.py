"""Offline MLX image worker for the pinned Qwen Image 2.1 / Heretic pipeline."""
from __future__ import annotations

import argparse
from importlib.metadata import version
import json
import os
from pathlib import Path
import time


if __package__:
    from .image_model import validate_model
else:
    from image_model import validate_model


class Progress:
    def call_in_loop(self, t, seed, prompt, latents, config, time_steps):
        import mlx.core as mx
        mx.eval(latents)
        print(json.dumps({"event": "progress", "step": t + 1,
                          "steps": config.num_inference_steps}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--prompt", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1024)
    parser.add_argument("--height", type=int, default=1024)
    parser.add_argument("--steps", type=int, default=40)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--init-image", type=Path, help="img2img: redraw from this image")
    parser.add_argument("--image-strength", type=float,
                        help="img2img: 0–1, higher stays closer to the init image (mflux convention)")
    args = parser.parse_args()
    if not args.prompt.strip():
        parser.error("提示词不能为空")
    if any(size < 256 or size > 2048 or size % 16 for size in (args.width, args.height)):
        parser.error("宽高须为 256–2048 范围内的 16 的倍数")
    if not 1 <= args.steps <= 100 or not 0 <= args.seed < 2**32:
        parser.error("步数须为 1–100，seed 须为 32 位无符号整数")
    if (args.init_image is None) != (args.image_strength is None):
        parser.error("--init-image 与 --image-strength 须同时给出")
    if args.init_image is not None:
        if not args.init_image.is_file():
            parser.error("底稿图片不存在")
        if not 0 < args.image_strength < 1:
            parser.error("--image-strength 须在 0 与 1 之间")
    if args.output.suffix.lower() != ".png" or args.output.exists():
        parser.error("输出须为尚不存在的 PNG 文件")
    provenance = validate_model(args.root)
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    import mlx.core as mx
    from mflux.models.qwen21.variants.txt2img.qwen_image_21 import QwenImage21

    if not mx.metal.is_available():
        raise RuntimeError("需要 Apple Silicon Metal GPU")
    started = time.monotonic()
    print(json.dumps({"event": "loading", "model": provenance}), flush=True)
    model = QwenImage21(model_path=str(args.root.resolve()))
    model.callbacks.register(Progress())
    loaded = time.monotonic()
    img2img = ({"image_path": str(args.init_image), "image_strength": args.image_strength}
               if args.init_image is not None else {})
    result = model.generate_image(seed=args.seed, prompt=args.prompt,
                                  num_inference_steps=args.steps,
                                  width=args.width, height=args.height, **img2img)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    result.save(str(args.output))
    metadata = {
        "model": provenance, "runtime": "MLX", "precision": "bf16",
        "mflux_version": version("mflux"), "mlx_version": version("mlx"),
        "prompt": args.prompt, "seed": args.seed, "steps": args.steps,
        "width": args.width, "height": args.height,
        "init_image": str(args.init_image) if args.init_image is not None else None,
        "image_strength": args.image_strength,
        "load_seconds": round(loaded - started, 2),
        "total_seconds": round(time.monotonic() - started, 2),
        "peak_mlx_bytes": mx.get_peak_memory(), "output": str(args.output),
    }
    args.output.with_suffix(".json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"event": "done", **metadata}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
