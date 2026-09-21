"""R-budget-16：预算的分母由机器自报，不由我们推算。

`mlx_lm/server.py` 每次启动都做这件事：

    wired_limit = mx.device_info()["max_recommended_working_set_size"]
    mx.set_wired_limit(wired_limit)

**wired 的内存按定义不参与换页**，所以这个值不是"建议"，是重活能用的硬上限——
超过去不是慢一点，是分配失败或者系统开始杀进程。本机（M5 Max，128 GiB）自报
107.5 GiB，也就是说 Apple 已经替这台机器算好了要给系统留 20.5 GiB（16%）。

于是预算不需要"整机可用内存减去一个拍出来的留量"，也不需要跟踪谁占了多少——
分母是个静态的机器属性，量一次记下来即可。
"""
import json

import pytest

from desk.budget.device import GpuCapacity, parse_device_info, probe_gpu_capacity

GIB = 1024 ** 3


def test_parses_what_mlx_reports():
    payload = json.dumps({
        "device_name": "Apple M5 Max",
        "memory_size": 137438953472,
        "max_recommended_working_set_size": 115418661683,
        "max_buffer_length": 86570401792,
    })
    cap = parse_device_info(payload)
    assert cap.working_set_bytes == 115418661683
    assert cap.max_buffer_bytes == 86570401792
    assert cap.memory_bytes == 137438953472
    assert cap.device_name == "Apple M5 Max"


def test_a_missing_working_set_is_not_a_capacity():
    """没有这个字段就不是能用的读数——返回 None 让上层退回保守，不拿 memory_size 顶替。

    拿总内存顶替会把 Apple 替系统留的那 16% 一起吃掉。
    """
    assert parse_device_info(json.dumps({"memory_size": 137438953472})) is None


def test_garbage_is_not_a_capacity():
    assert parse_device_info("not json") is None
    assert parse_device_info("") is None


def test_zero_or_negative_is_not_a_capacity():
    assert parse_device_info(json.dumps({"max_recommended_working_set_size": 0})) is None
    assert parse_device_info(json.dumps({"max_recommended_working_set_size": -1})) is None


def test_probe_returns_none_when_the_interpreter_cannot_import_mlx(tmp_path):
    """非 macOS、或那个 venv 里没装 mlx——报「算不出」，不猜。"""
    import sys
    assert probe_gpu_capacity(sys.executable) is None       # 本仓库的测试解释器没有 mlx


def test_probe_returns_none_for_a_missing_interpreter(tmp_path):
    assert probe_gpu_capacity(tmp_path / "no-such-python") is None


@pytest.mark.parametrize("venv", ["/Users/aa/LocalModelDesk/.venv-desk/bin/python3"])
def test_probe_reads_the_real_machine_when_mlx_is_available(venv):
    """真机探针：装了 mlx 的解释器要能问出这台机器的能力。

    只断言形状与量级关系，不断言具体数字——那随机器变。
    没装 mlx 的环境（CI、别人的机器）跳过。
    """
    from pathlib import Path
    if not Path(venv).exists():
        pytest.skip("这台机器上没有装了 mlx 的 venv")
    cap = probe_gpu_capacity(venv)
    if cap is None:
        pytest.skip("该解释器 import 不了 mlx")
    assert isinstance(cap, GpuCapacity)
    assert cap.working_set_bytes > 0
    # 机器自报的重活上限必须小于总内存——差额正是它替系统留的那部分。
    assert cap.working_set_bytes < cap.memory_bytes
    assert cap.max_buffer_bytes <= cap.working_set_bytes


def test_valid_json_from_a_failed_probe_is_not_trusted(tmp_path):
    """探针打印了像样的 JSON 却以非零码退出——不能信。

    这条是给 returncode 那道守卫准备的：import 失败时 stdout 本来就是空的，
    解析守卫已经挡住了，所以单靠那种场景测不出 returncode 检查有没有生效。
    真实情形是探针先打出东西、随后在别处崩掉。
    """
    import json as _json
    import stat

    fake = tmp_path / "fake-python"
    fake.write_text(
        "#!/bin/sh\n"
        f"echo '{_json.dumps({'max_recommended_working_set_size': 99, 'memory_size': 100})}'\n"
        "exit 3\n",
        encoding="utf-8")
    fake.chmod(fake.stat().st_mode | stat.S_IEXEC)

    assert probe_gpu_capacity(fake) is None
