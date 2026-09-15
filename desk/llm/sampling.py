"""Default sampling for a resident model, taken from the model's own generation_config.json.

mlx_lm.server falls back to temperature 0 (greedy decoding) when a request omits it, and
reasoning models then tend to repeat one sentence until the token limit (real app,
2026-09-15: GLM 4.7 Flash repeated for 8192 tokens). Models ship their recommended values.
"""
from __future__ import annotations

import json
from pathlib import Path

SAMPLING_KEYS = ("temperature", "top_p", "top_k")
FALLBACK_SAMPLING = {"temperature": 0.7, "top_p": 0.95}


def model_sampling_defaults(model_dir: Path) -> dict[str, float | int]:
    """The model's recommended sampling keys, with the fallback filling any key it leaves out.

    A temperature alone was not enough for GLM 4.7 Flash (it rambled to the token limit in
    2 of 3 runs); with top_p 0.95 added it answered every time (real app, 2026-09-15).
    """
    try:
        config = json.loads((Path(model_dir) / "generation_config.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return dict(FALLBACK_SAMPLING)
    if not isinstance(config, dict):
        return dict(FALLBACK_SAMPLING)
    found = {
        key: config[key] for key in SAMPLING_KEYS
        if isinstance(config.get(key), (int, float)) and not isinstance(config.get(key), bool)
    }
    return {**FALLBACK_SAMPLING, **found}
