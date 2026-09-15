"""The single, zero-I/O model catalog for resources."""
from __future__ import annotations

from dataclasses import asdict, dataclass

from .errors import UnknownModelError


GROUP_CHAT = "chat"
GROUP_VIDEO = "video"
GROUP_MUSIC = "music"


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

    def to_json(self) -> dict:
        return asdict(self)


CATALOG: tuple[ModelEntry, ...] = (
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
    ModelEntry("qwen27", "Qwen3.8 27B 越狱 8bit", GROUP_CHAT,
               "ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit",
               "llms/ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit",
               29.5, vision=True, quant="8bit", params="27B"),
    ModelEntry("gemma", "Gemma 4 31B 越狱 8bit 视觉", GROUP_CHAT,
               "thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit",
               "llms/thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit",
               33.8, vision=True, quant="8bit", params="31B"),
    ModelEntry("qwen35", "Qwen3.6 35B-A3B 越狱 8bit", GROUP_CHAT,
               "mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit",
               "llms/mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit",
               36.8, quant="8bit", params="35B-A3B"),
    ModelEntry("llama70", "Llama 3.3 70B 越狱 8bit", GROUP_CHAT,
               "divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx",
               "llms/divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx",
               75.0, quant="8bit", params="70B"),
)


def list_catalog() -> list[ModelEntry]:
    return list(CATALOG)


def entry(key: str) -> ModelEntry:
    for model in CATALOG:
        if model.key == key:
            return model
    raise UnknownModelError(f"unknown model key: {key!r}")
