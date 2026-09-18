#!/usr/bin/env python3
"""只读地打印本机的预算读数，供人工核对。不加载模型、不起作业、不写文件。"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desk.arbiter.memory import MemoryReader
from desk.budget.budget import Budget, Workload, fits
from desk.budget.store import Measurements
from desk.media.memory_estimate import estimate_bytes

GIB = 1024 ** 3


def main() -> int:
    snap = MemoryReader().snapshot()
    print(f"本机：总 {snap.total_bytes / GIB:.0f} GiB · 可用 {snap.available_bytes / GIB:.0f} GiB"
          f" · 压力 {snap.pressure}\n")
    budget = Budget(measurements=Measurements(), memory_reader=MemoryReader(),
                    media_estimate=estimate_bytes, now=lambda: 0.0)
    print(f"{'模型':34} {'权重GB':>6} {'窗口':>8} {'额度':>10} {'压缩点':>10}  来源")
    print("-" * 82)
    for directory in sorted((Path.home() / "LocalModelDesk/llms").glob("*/*/")):
        config_path = directory / "config.json"
        if not config_path.is_file():
            continue
        weights_gb = sum(f.stat().st_size for f in directory.glob("*.safetensors")) / 1e9
        chat = budget.for_chat(directory.name, json.loads(config_path.read_text()), weights_gb)
        print(f"{directory.name[:34]:34} {weights_gb:>6.0f} {str(chat.window or '—'):>8}"
              f" {chat.token_limit:>10,} {chat.compact_at:>10,}  {chat.source}")

    print("\n共存判定（驻留一个 30 GB 模型、其权重已分配时，还能不能开视频）：")
    resident = Workload("llm", "resident", int(60 * GIB), "measured", bytes_resident=int(30 * GIB))
    video = Workload("video", None, estimate_bytes("video", {}), "predicted")
    verdict = fits([resident, video], snap.available_bytes)
    print(f"  需要 {verdict.needed_bytes / GIB:.1f} GiB · 可用 {verdict.available_bytes / GIB:.1f} GiB"
          f" · 依据 {verdict.source} ⇒ {'装得下' if verdict.ok else '装不下'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
