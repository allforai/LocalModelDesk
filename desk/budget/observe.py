"""传感器：只产出观察，不做决策。

mlx-lm 每轮写一行 `Prompt Cache: N sequences, X GB`（server.py::_log_cache_stats，
用 n_bytes / 1e9 格式化，所以 GB 是十进制）。它下面还会跟若干以 "- " 开头的
分类型明细行，那些不是总数，混进来会让读数翻倍。

读不到一律返回 None：传感器坏了却沿用旧值，等于让预算建立在一个已经不成立的
观察上，而且没人看得出来。
"""
from __future__ import annotations

import re

_CACHE_LINE = re.compile(r"(?<!- )Prompt Cache:\s*\d+\s+sequences,\s*([\d.]+)\s*GB")
_GB = 1_000_000_000


def parse_cache_line(text: str) -> int | None:
    """日志里最后一条 Prompt Cache 行的字节数；读不到返回 None。"""
    matches = _CACHE_LINE.findall(text or "")
    if not matches:
        return None
    return int(float(matches[-1]) * _GB)


def measured_bytes_per_token(cache_bytes: int | None, prompt_tokens: int | None) -> int | None:
    """本机该模型每 token 的实测 KV 开销；任一读数缺失即返回 None。"""
    if not cache_bytes or not prompt_tokens:
        return None
    return int(cache_bytes / prompt_tokens)
