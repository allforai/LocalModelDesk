"""The single, zero-I/O model catalog for resources."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .errors import UnknownModelError
from ..media.image_model import BASE, BASE_REVISION, ENCODER, ENCODER_REVISION


GROUP_CHAT = "chat"
GROUP_VIDEO = "video"
GROUP_MUSIC = "music"
GROUP_IMAGE = "image"


@dataclass(frozen=True)
class ModelEntry:
    key: str
    name: str
    group: str
    hf_repo: str
    relpath: str
    gb: float
    vision: bool = False
    quant: str | None = None
    params: str | None = None
    sources: tuple[dict, ...] = ()
    backend: str = "mlx-lm"
    abliterated: bool = False
    tools: bool = False
    context_window: int | None = None
    disk_bytes: int | None = None
    runtime_note: str | None = None

    def to_json(self) -> dict:
        return asdict(self)


CATALOG: tuple[ModelEntry, ...] = (
    ModelEntry("qwen38-flash-next", "Qwen3.8 Flash Next 越狱 · oQ5e MTP", GROUP_CHAT,
               "mlx-community/Qwen3.8-Flash-Next-Uncensored-oQ5e-mtp",
               "llms/mlx-community/Qwen3.8-Flash-Next-Uncensored-oQ5e-mtp",
               128.54 * 10**9 / 1024**3, vision=True, quant="oQ5e", params="180B-A6B",
               sources=({"repo": "mlx-community/Qwen3.8-Flash-Next-Uncensored-oQ5e-mtp", "revision": "c7d915c693e37fa11810d600b617adb4c36ff596", "target": "."},),
               backend="omlx", abliterated=True, tools=True, context_window=262144,
               disk_bytes=128540000000,
               runtime_note="独立 oMLX · SSD n-gram offload · M5 Max 128GB 短请求实测约84 GiB，调度预留100 GiB · 完整窗口未实测"),
    ModelEntry("qwen-image", "Qwen-Image 2.1 + Heretic · MLX BF16", GROUP_IMAGE,
               BASE, "image-models/qwen-image-2.1-heretic", 30.9,
               quant="BF16", sources=(
                   {"repo": BASE, "revision": BASE_REVISION, "target": "."},
                   {"repo": ENCODER, "revision": ENCODER_REVISION, "target": "text_encoder"})),
    ModelEntry("h3", "MiniMax H3 视频 8bit", GROUP_VIDEO,
               "appautomaton/minimax-h3-base-8bit-mlx", "minimax-h3", 103.0),
    ModelEntry("music3", "MiniMax Music 3", GROUP_MUSIC,
               "appautomaton/MiniMax-Music3-MLX", "minimax-music3", 27.0),
    # The 8-bit conversion of the Huihui abliterated GLM 4.7 Flash replaces the 4-bit build,
    # which fell into repetition loops on the real app (2026-09-15: 1 loop in 5 runs vs 0 in 5).
    # The key stays "glm" so existing sessions keep their model.
    ModelEntry("glm", "GLM 4.7 Flash 越狱 8bit", GROUP_CHAT,
               "mlx-community/glm-4.7-flash-abliterated-8bit",
               "llms/mlx-community/glm-4.7-flash-abliterated-8bit",
               29.7, quant="8bit", params="30B-A3B"),
    ModelEntry("superqwen", "SuperQwen3.8 27B 越狱 4bit", GROUP_CHAT,
               "Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit",
               "llms/Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit",
               16.1, vision=True, quant="4bit", params="27B"),
    ModelEntry("gemma", "Gemma 4 31B 越狱 8bit 视觉", GROUP_CHAT,
               "thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit",
               "llms/thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit",
               33.8, vision=True, quant="8bit", params="31B"),
    ModelEntry("qwen35", "Qwen3.6 35B-A3B 越狱 8bit", GROUP_CHAT,
               "mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit",
               "llms/mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit",
               36.8, quant="8bit", params="35B-A3B"),
)


def list_catalog() -> list[ModelEntry]:
    return list(CATALOG)


def entry(key: str) -> ModelEntry:
    for model in CATALOG:
        if model.key == key:
            return model
    raise UnknownModelError(f"unknown model key: {key!r}")
