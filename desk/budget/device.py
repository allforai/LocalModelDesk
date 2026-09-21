"""这台机器自报的重活能力——预算的分母（R-budget-16）。

`mlx_lm/server.py` 每次启动都做这件事：

    wired_limit = mx.device_info()["max_recommended_working_set_size"]
    mx.set_wired_limit(wired_limit)

**wired 的内存按定义不参与换页。** 所以这个值不是"建议"，是重活能用的硬上限：
超过去不是慢一点，是 mlx 分配失败，或者系统开始杀进程。虚拟内存在这里帮不上忙。

本机实测（M5 Max，2026-09-21）：

    memory_size                        128.0 GiB
    max_recommended_working_set_size   107.5 GiB   ← 预算的分母
    max_buffer_length                   80.6 GiB   ← 单个权重张量的上限

差额 20.5 GiB（16%）就是 Apple 替这台机器留给系统的量——**不需要我们再拍一个留量**。
本机另一组实测佐证这个留量是合理的：内核 wired 8.6 GiB + 系统守护进程 5.0 GiB ≈ 14 GiB。

这是**静态的机器属性**，和总内存一样：量一次记下来，不随此刻在跑什么变化。台面自己的
解释器通常没有 mlx（它只在跑模型的那个 venv 里），所以问一次子进程，把答案存进实测档案。
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

# 在目标解释器里执行：只读设备信息，不分配任何显存、不加载任何模型。
_PROBE = (
    "import json,mlx.core as mx;"
    "d=mx.device_info();"
    "print(json.dumps({k:d.get(k) for k in "
    "('device_name','memory_size','max_recommended_working_set_size','max_buffer_length')}))"
)


@dataclass(frozen=True)
class GpuCapacity:
    device_name: str
    memory_bytes: int
    working_set_bytes: int
    max_buffer_bytes: int


def parse_device_info(payload: str) -> GpuCapacity | None:
    """把探针的输出解析成能力；缺关键字段或值不合理就返回 None。

    没有 `max_recommended_working_set_size` 时**不拿 `memory_size` 顶替**——
    那会把 Apple 替系统留的那 16% 一起吃掉，方向朝危险那边。
    """
    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    working_set = data.get("max_recommended_working_set_size")
    if not isinstance(working_set, int) or working_set <= 0:
        return None
    return GpuCapacity(
        device_name=str(data.get("device_name") or "未知设备"),
        memory_bytes=int(data.get("memory_size") or 0),
        working_set_bytes=working_set,
        max_buffer_bytes=int(data.get("max_buffer_length") or 0),
    )


def probe_gpu_capacity(python: "str | Path") -> GpuCapacity | None:
    """问这个解释器所在的机器能给重活多少内存；问不出返回 None。

    问不出的情形都归到「算不出」而不是猜一个数：解释器不在、没装 mlx、非 Apple 芯片、
    mlx 换了字段名。上层据此退回保守路径（R-budget-02 同一条纪律）。
    """
    try:
        done = subprocess.run([str(python), "-c", _PROBE],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    if done.returncode != 0:
        return None
    return parse_device_info(done.stdout.strip())
