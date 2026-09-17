# desk/budget/store.py
"""本机实测档案：这台机器上量到过什么。

档案是可重建的——损坏就当空的，重新量一次即可，绝不能因此让台面起不来。

作废规则：条目记着写入时的权重大小。同名模型重新量化过之后每 token 开销完全
不同，沿用旧数会让预算错一倍以上，所以权重对不上就当没有这条。

收紧是永久且单调的：预算说装得下而实际爆了，这台机器上这个组合此后一直按更保守
的额度算。只从成功里学习的系统会反复犯同一个错误。
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

WEIGHTS_TOLERANCE = 0.01     # 1%，吸收浮点表示差异，挡得住 4bit/8bit 之别
OVERRUN_STEP = 0.8           # 每爆一次，该组合的额度乘 0.8


class Measurements:
    def __init__(self, data: dict | None = None) -> None:
        self._data = data or {}

    @classmethod
    def load(cls, path: Path) -> "Measurements":
        try:
            return cls(json.loads(Path(path).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            return cls()

    def save(self, path: Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=".tmp-measurements-")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(self._data, handle, ensure_ascii=False, indent=2)
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def model_bytes_per_token(self, key: str, weights_gb: float) -> int | None:
        entry = self._data.get("models", {}).get(key)
        if not entry:
            return None
        recorded = entry.get("weights_gb")
        if not recorded or abs(recorded - weights_gb) > recorded * WEIGHTS_TOLERANCE:
            return None
        return entry.get("bytes_per_token")

    def record_model(self, key: str, bytes_per_token: int, weights_gb: float, now: float) -> None:
        self._data.setdefault("models", {})[key] = {
            "bytes_per_token": int(bytes_per_token),
            "weights_gb": float(weights_gb),
            "measured_at": now,
        }

    def media_peak(self, kind: str) -> int | None:
        return (self._data.get("media", {}).get(kind) or {}).get("peak_bytes")

    def record_media(self, kind: str, peak_bytes: int, now: float) -> None:
        self._data.setdefault("media", {})[kind] = {
            "peak_bytes": int(peak_bytes), "measured_at": now,
        }

    def record_overrun(self, key: str, now: float) -> None:
        entry = self._data.setdefault("overruns", {}).setdefault(key, {"count": 0})
        entry["count"] += 1
        entry["last_at"] = now

    def overrun_factor(self, key: str) -> float:
        count = (self._data.get("overruns", {}).get(key) or {}).get("count", 0)
        return OVERRUN_STEP ** count

    def to_dict(self) -> dict:
        return dict(self._data)
