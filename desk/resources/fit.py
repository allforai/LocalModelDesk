"""这个模型这台机器装不装得下——resources 目录页与首运报告问的是同一件事。

判定逻辑（fits/tight/too_big/unknown）全在 `desk.budget.budget.assess_fit`，纯函数、
零 IO。本文件只做输入拼装：从目录条目和预算门面里凑出"需要多少字节"，唯一的 IO 是
读 config.json（判断模型是否已下载，下载完才有这份文件）。
"""
from __future__ import annotations

import json
from pathlib import Path

from ..budget.budget import Budget, assess_fit
from ..media.memory_estimate import estimate_bytes
from .catalog import GROUP_CHAT, ModelEntry

GIB = 1024 ** 3


def _read_config(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def model_fit(entry: ModelEntry, budget: Budget | None, models_root, *, config_error: str | None = None) -> dict:
    """单个目录条目的机型适配信息，JSON-ready。

    chat 模型的「需要多少」用权重（目录里的 gb），媒体模型用作业峰值估算
    （`estimate_bytes`，默认/草稿参数）——两者问的不是同一件事，media 的权重体积
    (比如 h3 的 103 GB 下载量) 从不决定它装不装得下，作业峰值才决定。

    ``config_error`` 只在调用方读不出 config.json（因而把 ``models_root`` 传成
    None）时给一个理由——这时 context 不能是普通的 None：那和"目录里没有
    config.json，模型确实没下载"是同一个 JSON 形状，两件事却完全不同（R-config-
    corrupt-01，呼应 `assess_fit` 的 unknown 语义：算不出就老实说算不出，不是
    悄悄报成"没有"）。
    """
    if entry.group == GROUP_CHAT:
        needed = int(entry.gb * GIB)
    else:
        needed = estimate_bytes(entry.group, {})
    capacity = budget.capacity_bytes() if budget is not None else None
    verdict = assess_fit(needed, capacity)

    context = None
    if config_error is not None:
        # 不知道模型目录在哪，所以也不知道这个模型是不是已经下载好了——和
        # "知道目录、看了一眼、confirmed 没有 config.json" 必须是两种形状。
        context = {"unknown": True, "reason": config_error}
    # 上下文额度只有「已下载 + 算得出机器能力 + 知道模型目录」时才报——三个条件
    # 缺一都不许猜：没下载就没有 config.json，没能力就没有 for_chat 能用的分母，
    # 不知道目录（比如 config.json 本身读不出来）就无从判断"已下载"。
    elif entry.group == GROUP_CHAT and budget is not None and capacity is not None and models_root is not None:
        config_path = Path(models_root) / entry.relpath / "config.json"
        config = _read_config(config_path)
        if config is not None:
            chat = budget.for_chat(entry.key, config, entry.gb)
            context = {
                "token_limit": chat.token_limit,
                "compact_at": chat.compact_at,
                "source": chat.source,
                "window": chat.window,
            }

    return {
        "level": verdict.level,
        "needed_bytes": verdict.needed_bytes,
        "available_bytes": verdict.available_bytes,
        "headroom_bytes": verdict.headroom_bytes,
        "shortfall_bytes": verdict.shortfall_bytes,
        "context": context,
    }
