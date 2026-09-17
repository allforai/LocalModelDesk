"""R-budget-02：窗口读取顺序写死，且永不读 vision_config。"""
import json
from pathlib import Path

import pytest

from desk.budget.estimate import declared_window, per_token_bytes

LLAMA = {"model_type": "llama", "max_position_embeddings": 131072,
         "num_hidden_layers": 80, "num_key_value_heads": 8, "head_dim": 128}
QWEN = {"model_type": "qwen3_5",
        "text_config": {"max_position_embeddings": 262144, "num_hidden_layers": 64,
                        "num_key_value_heads": 4, "head_dim": 256}}
GEMMA = {"model_type": "gemma4",
         "text_config": {"max_position_embeddings": 262144, "num_hidden_layers": 60,
                         "num_key_value_heads": 16, "head_dim": 256},
         "vision_config": {"max_position_embeddings": 131072}}


def test_top_level_window_is_read():
    assert declared_window(LLAMA) == 131072


def test_text_config_wins_over_top_level():
    nested = dict(QWEN, max_position_embeddings=8192)   # 顶层是个陷阱值
    assert declared_window(nested) == 262144


def test_vision_config_is_never_read():
    """gemma-4 的视觉塔是 131072，文本塔是 262144；取错砍掉一半窗口。"""
    assert declared_window(GEMMA) == 262144


def test_vision_only_config_reports_nothing():
    """只有 vision_config 时必须报「读不到」，不许拿视觉塔的数顶替。"""
    assert declared_window({"vision_config": {"max_position_embeddings": 131072}}) is None


def test_missing_window_is_none_not_a_default():
    assert declared_window({"model_type": "mystery"}) is None


def test_per_token_bytes_matches_the_hand_computed_value():
    # 80 层 × 8 KV 头 × 128 head_dim × 2 (K和V) × 2 (fp16) = 327680
    assert per_token_bytes(LLAMA) == 327_680


def test_per_token_bytes_reads_nested_config():
    # 64 × 4 × 256 × 2 × 2 = 262144
    assert per_token_bytes(QWEN) == 262_144


MLA = {"model_type": "glm4_moe_lite", "max_position_embeddings": 202752,
       "num_hidden_layers": 47, "num_key_value_heads": 20, "hidden_size": 2048,
       "num_attention_heads": 20, "kv_lora_rank": 512,
       "qk_nope_head_dim": 192, "qk_rope_head_dim": 64, "v_head_dim": 256}


def test_mla_architecture_reports_nothing_rather_than_a_wrong_number():
    """glm-4.7-flash 是 MLA：每层每 token 只存一个压缩潜向量，标准公式不适用。

    套标准公式并用 hidden_size // num_attention_heads 凑 head_dim（2048/20 = 102.4，
    连整数都不是）会得出约 375 KB/token，实际约 53 KB——高估 7 倍，而且看起来很合理。
    这种数比没有数更危险，所以宁可报 None 走保守路径，让自校准去填真值。
    """
    assert per_token_bytes(MLA) is None


def test_head_dim_is_never_derived_from_hidden_size():
    """没有显式 head_dim 就是算不出，不许用除法凑一个。"""
    cfg = {"num_hidden_layers": 2, "num_key_value_heads": 2,
           "hidden_size": 512, "num_attention_heads": 8}
    assert per_token_bytes(cfg) is None


def test_mla_window_is_still_readable():
    """算不出开销不影响读窗口——两件事互相独立。"""
    assert declared_window(MLA) == 202752


def test_incomplete_config_reports_nothing():
    """字段不全时报读不到，绝不套一个默认值——那会让预算悄悄建立在假数上。"""
    assert per_token_bytes({"num_hidden_layers": 80}) is None


FIXTURES = json.loads(
    (Path(__file__).parent / "fixtures/budget/model_configs.json").read_text(encoding="utf-8")
)


@pytest.mark.parametrize("name,expected", [
    ("Llama-3.3-70B", (131072, 327_680)),
    ("glm-4.7-flash", (202752, None)),       # MLA：窗口读得到，开销算不出
    ("Qwen3.8-27B", (262144, 262_144)),
    ("Qwen3.6-35B-A3B", (262144, 81_920)),
    ("gemma-4-31B", (262144, 983_040)),
])
def test_every_installed_model_resolves(name, expected):
    cfg = FIXTURES[name]
    assert (declared_window(cfg), per_token_bytes(cfg)) == expected
