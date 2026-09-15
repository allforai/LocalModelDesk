import pytest

from desk.resources.catalog import CATALOG, entry, list_catalog
from desk.resources.errors import UnknownModelError


GOLDEN = [
    ("h3", "video", "appautomaton/minimax-h3-base-8bit-mlx", "minimax-h3", 103.0),
    ("music3", "music", "appautomaton/MiniMax-Music3-MLX", "minimax-music3", 27.0),
    ("glm", "chat", "huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit", "llms/huihui-ai/Huihui-GLM-4.7-Flash-abliterated-mlx-4bit", 16.9),
    ("glm8", "chat", "mlx-community/glm-4.7-flash-abliterated-8bit", "llms/mlx-community/glm-4.7-flash-abliterated-8bit", 29.7),
    ("superqwen", "chat", "Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit", "llms/Jiunsong/SuperQwen3.8-27b-abliterated-MLX-4bit", 16.1),
    ("qwen27", "chat", "ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit", "llms/ailexleon/Huihui-Qwen3.8-27B-abliterated-mlx-8Bit", 29.5),
    ("gemma", "chat", "thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit", "llms/thdekerk/Huihui-gemma-4-31B-it-v2-MLX-8bit", 33.8),
    ("qwen35", "chat", "mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit", "llms/mlx-community/Huihui-Qwen3.6-35B-A3B-Claude-4.7-Opus-abliterated-mlx-8bit", 36.8),
    ("llama70", "chat", "divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx", "llms/divinetribe/Llama-3.3-70B-Instruct-abliterated-8bit-mlx", 75.0),
]


def test_exactly_nine_entries_matching_golden_list():
    assert [(e.key, e.group, e.hf_repo, e.relpath, e.gb) for e in CATALOG] == GOLDEN


def test_keys_unique_and_group_distribution():
    keys = [e.key for e in CATALOG]
    assert len(set(keys)) == 9
    groups = [e.group for e in CATALOG]
    assert groups.count("video") == 1
    assert groups.count("music") == 1
    assert groups.count("chat") == 7


def test_chat_entries_carry_quant_params_gb():
    for model in CATALOG:
        if model.group == "chat":
            assert model.quant in ("4bit", "8bit")
            assert model.params
            assert model.gb > 0
            assert isinstance(model.vision, bool)


def test_relpaths_are_relative_and_contained():
    for model in CATALOG:
        assert not model.relpath.startswith("/")
        assert ".." not in model.relpath.split("/")


def test_list_catalog_returns_fresh_list():
    listed = list_catalog()
    assert listed == list(CATALOG)
    listed.append("junk")
    assert len(CATALOG) == 9


def test_entry_lookup_and_unknown_key():
    assert entry("glm").hf_repo == GOLDEN[2][2]
    assert entry("glm").name == "GLM 4.7 Flash 越狱 4bit"
    with pytest.raises(UnknownModelError):
        entry("does-not-exist")


def test_entry_is_frozen():
    with pytest.raises(Exception):
        entry("h3").gb = 1.0


def test_to_json_is_plain_dict():
    model = entry("superqwen").to_json()
    assert model["key"] == "superqwen"
    assert model["vision"] is True
    assert model["quant"] == "4bit"
