"""Pinned composite image model, shared by installation and offline inference.

File sizes are from the HF tree APIs at the two immutable revisions below
(2026-09-23). No stock encoder or redundant ComfyUI repack is required.
"""
from __future__ import annotations

import json
from pathlib import Path

BASE = "Qwen/Qwen-Image-2.1"
BASE_REVISION = "790c92633540aa0cb11d9abf19eb46d861714758"
ENCODER = "pottokao/Qwen-Image-2.1-Text-Encoder-Heretic"
ENCODER_REVISION = "047e54342fc4bfcd2addd54049db9c90bb74731e"
MARKER = "localmodeldesk-image.json"
PROVENANCE = dict(base=BASE, base_revision=BASE_REVISION, text_encoder=ENCODER,
                  text_encoder_revision=ENCODER_REVISION, runtime="mflux", format="bf16")
BASE_FILES = (
    ("model_index.json", 447),
    ("processor/added_tokens.json", 707),
    ("processor/chat_template.jinja", 5292),
    ("processor/merges.txt", 1671853),
    ("processor/preprocessor_config.json", 782),
    ("processor/special_tokens_map.json", 613),
    ("processor/tokenizer.json", 11422654),
    ("processor/tokenizer_config.json", 5445),
    ("processor/video_preprocessor_config.json", 817),
    ("processor/vocab.json", 2776833),
    ("scheduler/scheduler_config.json", 485),
    ("transformer/config.json", 370),
    ("transformer/diffusion_pytorch_model-00001-of-00002.safetensors", 9968332504),
    ("transformer/diffusion_pytorch_model-00002-of-00002.safetensors", 4261951904),
    ("transformer/diffusion_pytorch_model.safetensors.index.json", 30283),
    ("vae/config.json", 2079),
    ("vae/diffusion_pytorch_model.safetensors", 1350989512),
)
ENCODER_FILES = (
    ("config.json", 1643), ("generation_config.json", 213),
    ("model-00001-of-00004.safetensors", 4905357176),
    ("model-00002-of-00004.safetensors", 4915962456),
    ("model-00003-of-00004.safetensors", 4974674312),
    ("model-00004-of-00004.safetensors", 2738345504),
    ("model.safetensors.index.json", 67795),
)


def files() -> list[dict]:
    return [dict(path=prefix + path, size=size, repo=repo, revision=revision, source_path=path)
            for prefix, repo, revision, entries in (
                ("", BASE, BASE_REVISION, BASE_FILES),
                ("text_encoder/", ENCODER, ENCODER_REVISION, ENCODER_FILES))
            for path, size in entries]


def read_provenance(root: Path, *, complete: bool = True) -> dict:
    try:
        provenance = json.loads((root / MARKER).read_text())
    except (OSError, ValueError) as exc:
        raise ValueError("图片模型未安装或来源标记无效，请前往资源下载") from exc
    if not isinstance(provenance, dict) or any(provenance.get(k) != v for k, v in PROVENANCE.items()):
        raise ValueError("模型来源不匹配或版本不匹配；不会覆盖未知模型目录")
    if complete and provenance.get("complete") is not True:
        raise ValueError("模型未下载完成，请前往资源继续下载")
    return provenance


def validate_model(root: Path) -> dict:
    provenance = read_provenance(root)
    for item in files():
        path = root / item["path"]
        if not path.resolve().is_relative_to(root.resolve()) or not path.is_file():
            raise ValueError(f"模型文件或分片缺失：{item['path']}")
        if path.stat().st_size != item["size"]:
            raise ValueError(f"模型文件不完整：{item['path']}")
    return provenance


def prepare_destination(root: Path) -> None:
    """Only resume an exact known model; never adopt an unknown nonempty tree."""
    if root.is_symlink() or (root / MARKER).is_symlink() or (root / ".cache").is_symlink():
        raise ValueError("模型目录标记或缓存不允许符号链接")
    if root.exists() and any(root.iterdir()):
        read_provenance(root, complete=False)
    root.mkdir(parents=True, exist_ok=True)
    cache = root / ".cache/localmodeldesk"
    paths = [root / MARKER, root / "localmodeldesk-image.tmp", cache / "manifest.json"]
    paths += [cache / "parts" / (item["path"] + ".part") for item in files()]
    if any(not path.resolve().is_relative_to(root.resolve()) for path in paths):
        raise ValueError("模型下载缓存或标记路径超出目标目录")
    for item in files():
        if not (root / item["path"]).resolve().is_relative_to(root.resolve()):
            raise ValueError("模型目录包含指向外部的链接")
    (root / MARKER).write_text(json.dumps({**PROVENANCE, "complete": False}, indent=2) + "\n")
