"""desk/resources/fit.py：把目录里的模型需求拼成 assess_fit() 的输入（R-budget-fit）。

拼装本身要 IO（capacity_bytes 探机器、config.json 探是否已下载），判定不要——
判定逻辑全部委托给 desk.budget.budget.assess_fit，这里只负责喂对的数字。
"""
import json

from desk.budget.budget import Budget
from desk.budget.device import GpuCapacity
from desk.budget.store import Measurements
from desk.media.memory_estimate import estimate_bytes
from desk.resources.catalog import entry
from desk.resources.fit import model_fit

GIB = 1024 ** 3
GLM = entry("glm")          # chat, 29.7 GB
H3 = entry("h3")             # video, 103.0 GB on disk but fit is about job peak, not weights


def make_budget(working_set_gib):
    m = Measurements()
    m.record_gpu_capacity(GpuCapacity("测试设备", 128 * GIB, working_set_gib * GIB, 80 * GIB), 0.0)
    return Budget(measurements=m, memory_reader=None, media_estimate=estimate_bytes, now=lambda: 0.0)


def test_chat_model_needs_its_catalog_weight_in_bytes():
    budget = make_budget(200)
    fit = model_fit(GLM, budget, models_root="/nope")
    assert fit["needed_bytes"] == int(GLM.gb * GIB)
    assert fit["level"] == "fits"


def test_media_model_needs_the_estimated_job_peak_not_the_weights():
    """h3 是 103 GB 的下载体积，但视频作业的峰值由 estimate_bytes 给——两者必须不同。"""
    budget = make_budget(200)
    fit = model_fit(H3, budget, models_root="/nope")
    assert fit["needed_bytes"] == estimate_bytes("video", {})
    assert fit["needed_bytes"] != int(H3.gb * GIB)


def test_unknown_capacity_yields_unknown_level_and_no_context(tmp_path):
    budget = Budget(measurements=Measurements(), memory_reader=None,
                     media_estimate=estimate_bytes, now=lambda: 0.0)   # 没记录过能力，探针也没给
    fit = model_fit(GLM, budget, models_root=str(tmp_path))
    assert fit["level"] == "unknown"
    assert fit["available_bytes"] is None
    assert fit["context"] is None


def test_no_budget_wired_is_also_unknown_not_a_guess():
    fit = model_fit(GLM, None, models_root="/nope")
    assert fit["level"] == "unknown"
    assert fit["context"] is None


def test_downloaded_chat_model_gets_the_sharper_context_limit(tmp_path):
    """config.json 落地之后才能算真实上下文额度——目录里没有就不许报这个数。"""
    budget = make_budget(200)
    model_dir = tmp_path / GLM.relpath
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text(json.dumps({
        "max_position_embeddings": 131072, "num_hidden_layers": 48,
        "num_key_value_heads": 8, "head_dim": 128,
    }), encoding="utf-8")

    fit = model_fit(GLM, budget, models_root=str(tmp_path))
    assert fit["context"] is not None
    assert fit["context"]["token_limit"] > 0
    assert fit["context"]["source"] == "predicted"


def test_not_downloaded_chat_model_reports_no_context_number():
    """没下载就没有 config.json——绝不能报一个不知道从哪来的上下文数字。"""
    budget = make_budget(200)
    fit = model_fit(GLM, budget, models_root="/does/not/exist")
    assert fit["context"] is None


def test_too_big_reports_the_shortfall():
    budget = make_budget(10)   # 只给 10 GiB，glm 需要 29.7 GB
    fit = model_fit(GLM, budget, models_root="/nope")
    assert fit["level"] == "too_big"
    assert fit["shortfall_bytes"] > 0


def test_config_error_yields_unknown_context_not_absent_context(tmp_path):
    """配置读不出来时 context 不能长得和"没下载"一样——两件事必须能分清（R-config-corrupt-01）。"""
    budget = make_budget(200)
    model_dir = tmp_path / GLM.relpath
    model_dir.mkdir(parents=True)
    (model_dir / "config.json").write_text(json.dumps({
        "max_position_embeddings": 131072, "num_hidden_layers": 48,
        "num_key_value_heads": 8, "head_dim": 128,
    }), encoding="utf-8")

    # 即便模型其实已经下载好了（config.json 就在磁盘上），调用方读不出 desk 自己
    # 的 config.json 就没法知道 models_root，只能传 None + 一个理由——这时 context
    # 必须是一个显式的"不知道"标记，和 test_not_downloaded_chat_model_reports_no_context_number
    # 里那个朴素的 None 不能是同一个值。
    fit = model_fit(GLM, budget, models_root=None, config_error="配置文件读不出来")
    assert fit["context"] is not None
    assert fit["context"] != model_fit(GLM, budget, models_root="/does/not/exist")["context"]
    assert fit["context"]["unknown"] is True
    assert fit["context"]["reason"] == "配置文件读不出来"
    # 设备能力判定和 models_root 无关，config 读不出来不该连这个也一起说不知道。
    assert fit["level"] == "fits"
