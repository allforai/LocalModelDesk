"""R-budget-06：媒体按参数估算 + 本机标定（Task 7 Step 7）。

按参数估算的公式保留——不同分辨率/时长的作业不共用同一个估值；新增的是标定来源：
每次作业运行期采样 available_bytes（启动前基线、运行中最低点），差值即本机实测峰值，
写入实测档案，用来修正公式常数项。没量过之前，`Budget.cost()` 报 predicted；
量过一次之后变 measured——这就是「未经本机实测不放宽」。
"""
from pathlib import Path
from types import SimpleNamespace
import threading

import pytest

from desk.budget.budget import Budget, fits
from desk.budget.store import Measurements
from desk.media.memory_estimate import estimate_bytes
from desk.media.service import MediaService
from media_fakes import FIXED_TIME, FakeExecutor, FakeHistory

GIB = 1024 ** 3


class FakeArbiter:
    """跟 media_fakes.FakeArbiter 一样的最小假实现，独立一份避免耦合那个模块的形状。"""

    def __init__(self):
        self.acquired: list[tuple] = []
        self.released: list[str] = []

    def can_start_heavy(self, kind, params=None, key=None, estimated_bytes=None):
        return {"ok": True, "reason": None}

    def acquire_heavy(self, kind, label, display=None, *, params=None, key=None):
        token = f"permit-{len(self.acquired) + 1}"
        self.acquired.append((kind, label, token))
        return {"ok": True, "token": token}

    def release_heavy(self, token):
        self.released.append(token)
        return {"ok": True}


def make_calibrating_service(tmp_path: Path, *, memory_sequence, executor=None):
    executor = executor or FakeExecutor(script="success", lines=())
    arbiter, history = FakeArbiter(), FakeHistory()
    roots = SimpleNamespace(
        outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
        mlx_h3_cmd=("/fake/bin/mlx-h3",), mlx_h3_env={"PYTHONPATH": "/fake/pylibs/h3"},
    )
    caps = {"mlx_h3": SimpleNamespace(present=True, detail="")}
    measurements = Measurements()
    measurements_path = tmp_path / "measurements.json"
    reads = iter(memory_sequence)
    tail = memory_sequence[-1]

    def available_bytes():
        return next(reads, tail)

    service = MediaService(
        resolve_paths=lambda: roots, probe_capabilities=lambda: caps,
        arbiter=arbiter, list_catalog=lambda: [SimpleNamespace(key="h3", relpath="minimax-h3", gb=103.0)],
        append_history=history.append, executor=executor, clock=lambda: FIXED_TIME,
        measurements=measurements, measurements_path=measurements_path,
        available_bytes=available_bytes, mem_sample_interval_s=0.01,
    )
    return service, SimpleNamespace(
        executor=executor, arbiter=arbiter, history=history,
        measurements=measurements, measurements_path=measurements_path,
    )


def start_video(service, **overrides):
    params = dict(prompt="rain on a quiet street", width=512, height=288, frames=49, steps=16)
    params.update(overrides)
    return service.start_video_job(**params)


def test_job_run_records_measured_peak_from_baseline_minus_trough(tmp_path):
    """基线 116 GiB、运行中最低 89 GiB ⇒ 记录峰值 27 GiB（计划给定数字）。"""
    memory_sequence = [116 * GIB] + [89 * GIB] * 200
    service, deps = make_calibrating_service(tmp_path, memory_sequence=memory_sequence)

    done = threading.Event()
    service.on_job_finished(lambda _snap: done.set())
    start_video(service)
    assert done.wait(5.0), "job never finished"

    assert deps.measurements.media_peak("video") == 27 * GIB
    # 断言记录之后 Budget.cost("video", ...) 的 source 由 predicted 变为 measured。
    budget = Budget(
        measurements=deps.measurements,
        memory_reader=SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=200 * GIB)),
        media_estimate=estimate_bytes, now=lambda: FIXED_TIME,
    )
    workload = budget.cost("video", params={"width": 512, "height": 288, "frames": 49, "steps": 16})
    assert workload.source == "measured"
    assert workload.bytes_needed == 27 * GIB
    # 并且落了盘——档案是可重建的，但这次运行的标定不该随进程一起消失。
    saved = Measurements.load(deps.measurements_path)
    assert saved.media_peak("video") == 27 * GIB


def test_calibration_is_skipped_when_no_measurements_seam_is_wired(tmp_path):
    """没接 measurements/available_bytes 时（今天的生产现实）行为不变：不记录、不崩。"""
    executor = FakeExecutor(script="success", lines=())
    arbiter, history = FakeArbiter(), FakeHistory()
    roots = SimpleNamespace(
        outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
        mlx_h3_cmd=("/fake/bin/mlx-h3",), mlx_h3_env={"PYTHONPATH": "/fake/pylibs/h3"},
    )
    caps = {"mlx_h3": SimpleNamespace(present=True, detail="")}
    service = MediaService(
        resolve_paths=lambda: roots, probe_capabilities=lambda: caps,
        arbiter=arbiter, list_catalog=lambda: [SimpleNamespace(key="h3", relpath="minimax-h3", gb=103.0)],
        append_history=history.append, executor=executor, clock=lambda: FIXED_TIME,
    )
    done = threading.Event()
    service.on_job_finished(lambda _snap: done.set())
    start_video(service)
    assert done.wait(5.0), "job never finished"
    # 没炸就是通过；没有 measurements 对象可查——这条路径本来就不存在标定状态。


def test_first_run_uses_predicted_cost_then_measured_after_calibration_changes_fits():
    """R-budget-06 的落点：没量过之前 predicted，量过之后 measured；
    按参数估算保守偏大时，未经本机实测不放宽（fits 判否），实测校正后才判是。"""
    measurements = Measurements()
    memory_reader = SimpleNamespace(snapshot=lambda: SimpleNamespace(available_bytes=30 * GIB))
    budget = Budget(measurements=measurements, memory_reader=memory_reader,
                     media_estimate=estimate_bytes, now=lambda: FIXED_TIME)
    params = {"width": 1024, "height": 576, "frames": 73, "steps": 16}

    before = budget.cost("video", params=params)
    assert before.source == "predicted"
    assert before.bytes_needed == estimate_bytes("video", params)
    verdict_before = fits([before], memory_reader.snapshot().available_bytes)
    assert verdict_before.ok is False   # 33.9 GiB 估算 > 30 GiB 可用：未经本机实测不放宽

    measurements.record_media("video", 27 * GIB, FIXED_TIME)

    after = budget.cost("video", params=params)
    assert after.source == "measured"
    assert after.bytes_needed == 27 * GIB
    verdict_after = fits([after], memory_reader.snapshot().available_bytes)
    assert verdict_after.ok is True   # 27 GiB 实测 < 30 GiB 可用


def test_insufficient_memory_warning_still_names_a_gib_number_and_now_the_source(tmp_path):
    """media/service.py 现有的 insufficient_memory 警告路径不能退化——数字来源要跟着标。"""
    from desk.media.service import MediaError

    class WarningArbiter(FakeArbiter):
        def can_start_heavy(self, kind, params=None, key=None, estimated_bytes=None):
            return {"ok": True, "reason": None, "memory_warning": {
                "code": "insufficient_memory", "required_bytes": estimated_bytes,
                "available_bytes": 1 * GIB,
                "message": "model requires more than is available",
            }}

    roots = SimpleNamespace(
        outputs_root=tmp_path / "outputs", models_root=tmp_path / "models",
        mlx_h3_cmd=("/fake/bin/mlx-h3",), mlx_h3_env={"PYTHONPATH": "/fake/pylibs/h3"},
    )
    caps = {"mlx_h3": SimpleNamespace(present=True, detail="")}
    measurements = Measurements()
    measurements.record_media("video", 27 * GIB, FIXED_TIME)
    service = MediaService(
        resolve_paths=lambda: roots, probe_capabilities=lambda: caps,
        arbiter=WarningArbiter(), list_catalog=lambda: [SimpleNamespace(key="h3", relpath="minimax-h3", gb=103.0)],
        append_history=FakeHistory().append, executor=FakeExecutor(), clock=lambda: FIXED_TIME,
        measurements=measurements,
    )
    with pytest.raises(MediaError) as exc:
        start_video(service)
    assert exc.value.code == "insufficient_memory"
    assert "27.0 GiB" in exc.value.message
    assert "已实测" in exc.value.message
    assert exc.value.detail["source"] == "measured"
