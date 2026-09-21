#!/usr/bin/env python3
"""只读地打印本机的预算读数，供人工核对。不加载模型、不起作业、不写文件。

预算的分母是**机器自报的重活能力**（R-budget-16）——mlx 的
`max_recommended_working_set_size`，也就是它自己会 `set_wired_limit` 的那个值。
wired 的内存不参与换页，所以它是硬上限；Apple 报这个数时已经替系统留好了量。

它是静态的机器属性：同一台机器同一个模型，这个脚本任何时候跑出来的额度都一样，
不随此刻开着几个浏览器标签变化。脚本也把「此刻可用内存」并排打出来作为对照——
那个数十分钟就能差十几个 GiB，正是换掉它的理由。
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from desk.arbiter.memory import MemoryReader
from desk.budget.budget import Budget
from desk.budget.store import Measurements
from desk.media.memory_estimate import estimate_bytes

GIB = 1024 ** 3
PROBE_PYTHON = Path(__file__).resolve().parents[1] / ".venv-desk/bin/python3"


def main() -> int:
    snap = MemoryReader().snapshot()
    budget = Budget(measurements=Measurements(), memory_reader=MemoryReader(),
                    media_estimate=estimate_bytes, now=lambda: 0.0,
                    probe_python=PROBE_PYTHON if PROBE_PYTHON.exists() else None)
    capacity = budget.capacity_bytes()
    if capacity is None:
        print("问不出这台机器的重活能力（没装 mlx 的解释器？）——额度只能退回声明窗口。")
    else:
        print(f"机器自报的重活上限   {capacity / GIB:6.1f} GiB   ← 预算的分母（静态）")
    print(f"此刻可用内存         {snap.available_bytes / GIB:6.1f} GiB   ← 仅作对照，不参与算额度")
    print(f"总内存               {snap.total_bytes / GIB:6.1f} GiB · 压力 {snap.pressure}\n")

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

    print("\n人工核对三件事：")
    print("  1. 权重接近或超过重活上限的模型，额度应该很小或为 0")
    print("  2. MLA 架构的模型（glm-4.7-flash）来源应为 unavailable，其余为 predicted")
    print("  3. 隔几分钟再跑一次，额度应当一个字节都不变——它是机器配置，不是当前状态")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
