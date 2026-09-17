# tests/test_budget_store.py
"""R-budget-04 / R-budget-08：本机实测档案，含作废规则与失败记忆。"""
import json
import pytest
from desk.budget import store
from desk.budget.store import Measurements

T0 = 1_757_000_000.0


def test_missing_file_loads_empty(tmp_path):
    m = Measurements.load(tmp_path / "measurements.json")
    assert m.model_bytes_per_token("k", 70.2) is None
    assert m.media_peak("video") is None


def test_recorded_value_round_trips(tmp_path):
    path = tmp_path / "measurements.json"
    m = Measurements.load(path)
    m.record_model("llama-70b", 327_680, 70.2, T0)
    m.save(path)
    assert Measurements.load(path).model_bytes_per_token("llama-70b", 70.2) == 327_680


def test_weights_mismatch_invalidates_the_entry(tmp_path):
    """同名模型换了量化，每 token 开销完全不同；沿用旧数会错一倍以上。"""
    m = Measurements.load(tmp_path / "m.json")
    m.record_model("qwen-27b", 262_144, 28.0, T0)
    assert m.model_bytes_per_token("qwen-27b", 15.0) is None      # 8bit 换 4bit
    assert m.model_bytes_per_token("qwen-27b", 28.0) == 262_144   # 同一份仍可用


def test_weights_within_one_percent_still_match(tmp_path):
    m = Measurements.load(tmp_path / "m.json")
    m.record_model("k", 100, 70.20, T0)
    assert m.model_bytes_per_token("k", 70.25) == 100


def test_media_peak_round_trips(tmp_path):
    m = Measurements.load(tmp_path / "m.json")
    m.record_media("video", 29_000_000_000, T0)
    assert m.media_peak("video") == 29_000_000_000
    assert m.media_peak("music") is None


def test_overrun_tightens_permanently_and_monotonically(tmp_path):
    m = Measurements.load(tmp_path / "m.json")
    assert m.overrun_factor("k") == 1.0
    m.record_overrun("k", T0)
    once = m.overrun_factor("k")
    assert once < 1.0
    m.record_overrun("k", T0 + 60)
    assert m.overrun_factor("k") < once        # 单调收紧
    assert m.overrun_factor("other") == 1.0    # 只收紧撞过的那一个


def test_overrun_survives_a_reload(tmp_path):
    """收紧是永久的：重启之后还得记着这台机器上这个组合爆过。"""
    path = tmp_path / "m.json"
    m = Measurements.load(path)
    m.record_overrun("k", T0)
    m.save(path)
    assert Measurements.load(path).overrun_factor("k") < 1.0


def test_corrupt_file_loads_empty_instead_of_raising(tmp_path):
    """档案损坏不能让台面起不来——丢掉重测即可，它本来就是可重建的。"""
    path = tmp_path / "m.json"
    path.write_text("{not json", encoding="utf-8")
    assert Measurements.load(path).media_peak("video") is None


def test_save_is_atomic(tmp_path):
    """写档案不得留下半截文件：用临时文件加 os.replace。"""
    path = tmp_path / "m.json"
    m = Measurements.load(path)
    m.record_media("music", 28_000_000_000, T0)
    m.save(path)
    assert json.loads(path.read_text(encoding="utf-8"))["media"]["music"]["peak_bytes"] == 28_000_000_000
    assert list(tmp_path.glob(".tmp-*")) == []


def test_save_leaves_the_original_file_untouched_if_the_write_fails(tmp_path, monkeypatch):
    """真正验证原子性：dump 中途抛异常，旧文件必须原封不动，不留半截临时文件。"""
    path = tmp_path / "m.json"
    m = Measurements.load(path)
    m.record_media("video", 1, T0)
    m.save(path)
    original = path.read_text(encoding="utf-8")

    m.record_media("video", 999_999_999, T0 + 1)

    def boom(*args, **kwargs):
        raise RuntimeError("disk exploded mid-write")

    monkeypatch.setattr(store.json, "dump", boom)
    with pytest.raises(RuntimeError):
        m.save(path)

    assert path.read_text(encoding="utf-8") == original
    assert list(tmp_path.glob(".tmp-*")) == []
