"""Task 9：把 budget 接到真实运行路径上。

子系统建好、测过、却没通电，是这次工作流留下的缺口：`build_runtime` 里
`Arbiter(DEFAULT_LLM_PORT)` 不传 budget，于是生产走的是 legacy 兜底，
R-arbiter-01 的重写是死代码。

比"没接"更隐蔽的是"接了但传了空参数"：`acquire_heavy("llm", key, name)` 不带
config/weights 时，`budget.cost` 算出的聊天开销是 **0 字节**。零开销的重活当然
处处装得下；互斥只是被 R-budget-10（有一件 unavailable 就整组保守）碰巧保住的。
所以本文件既验"接上了"，也验"传了真数"。
"""
from pathlib import Path

import pytest

from desk.budget.budget import Budget
from desk.budget.store import Measurements

GIB = 1024 ** 3
LLAMA_CONFIG = {"max_position_embeddings": 131072, "num_hidden_layers": 80,
                "num_key_value_heads": 8, "head_dim": 128}


class FakeMemory:
    def snapshot(self):
        class S:
            available_bytes = 116 * GIB
            total_bytes = 186 * GIB
            pressure = "normal"
        return S()


def make_budget():
    """分母是机器自报的能力（R-budget-16），夹具里直接记一份，不去问真机。"""
    from desk.budget.device import GpuCapacity
    m = Measurements()
    m.record_gpu_capacity(GpuCapacity("测试设备", 128 * GIB, 107 * GIB, 80 * GIB), 0.0)
    return Budget(measurements=m, memory_reader=FakeMemory(),
                  media_estimate=lambda kind, params: 27 * GIB, now=lambda: 0.0)


def test_a_chat_workload_without_config_costs_nothing():
    """这条记录的是缺口本身：不传 config/weights，聊天开销算出来是 0 字节。

    它不是期望行为，是接线必须避开的陷阱——下一条才是要达成的。
    """
    assert make_budget().cost("llm", key="llama").bytes_needed == 0


def test_a_chat_workload_with_config_costs_real_bytes():
    workload = make_budget().cost("llm", key="llama", config=LLAMA_CONFIG, weights_gb=70.2)
    assert workload.bytes_needed > 70 * GIB      # 至少得包含权重
    assert workload.source == "predicted"


def _isolated_data_root(tmp_path, monkeypatch):
    """照 tests/test_production_runtime.py 的既有写法隔离数据根。

    不隔离时 build_runtime 会指向真实的 ~/Library/Application Support/LocalModelDesk
    并去探真机能力——既会把测试挂住，也会碰真实数据。
    """
    import json
    data_root = tmp_path / "data"
    data_root.mkdir()
    (data_root / "config.json").write_text(json.dumps({
        "config_version": 1,
        "first_run_done": False,
        "models_root": str(data_root / "models"),
        "outputs_root": str(data_root / "outputs"),
        "gateway": {"enabled": False, "host": "127.0.0.1", "port": 0},
    }), encoding="utf-8")
    monkeypatch.setenv("LOCALMODELDESK_DATA_ROOT", str(data_root))
    return data_root


def test_production_runtime_wires_budget_into_the_arbiter(tmp_path, monkeypatch):
    """没有这一条，整个 Task 7 在真实运行里都是死代码。"""
    _isolated_data_root(tmp_path, monkeypatch)
    from desk.runtime import build_runtime
    runtime = build_runtime(port=0)
    try:
        assert getattr(runtime.llm._arbiter, "_budget", None) is not None, \
            "build_runtime 没把 budget 传给 Arbiter，生产仍走 legacy 兜底"
    finally:
        # 没 start 过的 runtime 不能调 shutdown()（serve 循环没跑，标志位没人看），
        # 照 tests/test_production_runtime.py 的既有写法释放套接字。
        runtime.app._server.server_close()


def test_production_runtime_does_not_calibrate_media_from_the_memory_delta(tmp_path, monkeypatch):
    """媒体峰值按作业参数估算，不接运行时的整机差额（那个读数系统性偏低，方向朝 OOM）。

    这条原先断言的恰好相反——要求把 measurements / available_bytes 接进 MediaService。
    后来量到 available_bytes 对常驻内存只捕捉 51–73%，用它标定会让预算偏乐观，
    整套标定连同这条断言一起翻过来。
    """
    _isolated_data_root(tmp_path, monkeypatch)
    from desk.runtime import build_runtime
    runtime = build_runtime(port=0)
    try:
        media = runtime.media
        for gone in ("_measurements", "_available_bytes"):
            assert not hasattr(media, gone), f"MediaService 又接上了 {gone}"
    finally:
        runtime.app._server.server_close()


def test_llm_load_hands_the_arbiter_the_model_config_and_weights(tmp_path):
    """接线的实质：让预算拿到它判断所需的真数，而不是一个 0。

    用 tests/llm/llm_fakes.py 的既有夹具，不新造假后端。
    """
    import json
    from tests.llm.llm_fakes import make_service

    built = make_service(tmp_path)
    entry = built.entries[0]
    # 模型目录由夹具建好，补一份 config.json 供预算读取（只写 tmp_path）
    model_dir = built.paths.models_root / entry.relpath
    (model_dir / "config.json").write_text(json.dumps(LLAMA_CONFIG), encoding="utf-8")

    built.service.load(entry.key)

    call = getattr(built.arbiter, "last_acquire", None)
    assert call, "load 没有走 acquire_heavy"
    assert call["key"] == entry.key
    params = call["params"] or {}
    assert params.get("weights_gb"), "acquire_heavy 没收到 weights_gb，预算会把聊天算成 0 字节"
    assert params.get("config"), "acquire_heavy 没收到模型 config，预算算不出每 token 开销"


def test_production_runtime_can_probe_the_machine_capacity(tmp_path, monkeypatch):
    """R-budget-16：生产装配要把「装了 mlx 的解释器」交给预算，否则分母永远问不出来。"""
    _isolated_data_root(tmp_path, monkeypatch)
    from desk.runtime import build_runtime
    runtime = build_runtime(port=0)
    try:
        budget = runtime.llm._arbiter._budget
        assert getattr(budget, "_probe_python", None) is not None, \
            "build_runtime 没把 venv_python 传给 Budget，机器能力问不出来"
    finally:
        runtime.app._server.server_close()
