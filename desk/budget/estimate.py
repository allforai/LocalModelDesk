"""冷启动初值：从模型 config.json 推算窗口与每 token 的 KV 开销。

纯函数，无 IO。窗口的查找顺序是写死的规则而不是「递归找第一个」：gemma-4 同时
有 text_config 和 vision_config 两个窗口，递归查找会撞上视觉塔的 131072，
把文本塔的 262144 砍掉一半。
"""
from __future__ import annotations

_WINDOW_KEY = "max_position_embeddings"
_KV_BYTES = 2      # fp16。若 mlx 量化了 KV，实际更小，我们偏早压缩——安全方向。
_K_AND_V = 2


def _text_scope(config: dict) -> dict:
    """文本塔的配置段。vision_config 永远不参与——它描述的是另一座塔。"""
    nested = config.get("text_config")
    return nested if isinstance(nested, dict) else config


def declared_window(config: dict) -> int | None:
    """模型声明的上下文窗口；读不到返回 None（R-budget-02）。"""
    nested = config.get("text_config")
    if isinstance(nested, dict) and isinstance(nested.get(_WINDOW_KEY), int):
        return nested[_WINDOW_KEY]
    value = config.get(_WINDOW_KEY)
    return value if isinstance(value, int) else None


# MLA（Multi-head Latent Attention）的标记。出现任一个，说明这个模型每层每 token
# 存的是一个压缩潜向量而不是 KV 头，下面的标准公式不适用。
_MLA_MARKERS = ("kv_lora_rank", "qk_nope_head_dim", "v_head_dim")


def per_token_bytes(config: dict) -> int | None:
    """每个 token 的 KV cache 字节数；算不出返回 None，绝不凑一个。

    只对标准 MHA/GQA 成立。head_dim 必须显式存在——用
    hidden_size // num_attention_heads 去补，在 glm-4.7-flash 这类 MLA 模型上
    会凑出 102（2048/20 = 102.4，连整数都不是），算出约 375 KB/token，
    而实际约 53 KB。高估 7 倍且看起来很合理的数，比没有数更危险。
    """
    scope = _text_scope(config)
    if any(marker in scope or marker in config for marker in _MLA_MARKERS):
        return None
    layers = scope.get("num_hidden_layers")
    kv_heads = scope.get("num_key_value_heads")
    head_dim = scope.get("head_dim")
    if not all(isinstance(v, int) for v in (layers, kv_heads, head_dim)):
        return None
    return layers * kv_heads * head_dim * _K_AND_V * _KV_BYTES
