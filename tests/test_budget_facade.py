"""R-budget-01/03/05：门面把 IO 接到纯函数上，每个数带来源。"""
from desk.budget.budget import Budget, ChatBudget
from desk.budget.store import Measurements

GIB = 1024 ** 3
LLAMA = {"max_position_embeddings": 131072, "num_hidden_layers": 80,
         "num_key_value_heads": 8, "head_dim": 128}          # 327680 B/token
MYSTERY = {"max_position_embeddings": 4096}                   # 算不出每 token 字节


class FakeMemory:
    def __init__(self, available_gib): self.available = available_gib * GIB
    def snapshot(self):
        class S:
            available_bytes = self.available
            total_bytes = 186 * GIB
            pressure = "normal"
        return S()


def make(available_gib=116, measurements=None):
    return Budget(measurements=measurements or Measurements(),
                  memory_reader=FakeMemory(available_gib),
                  media_estimate=lambda kind, params: 27 * GIB,
                  now=lambda: 1_757_000_000.0)


def test_cold_start_budget_is_predicted():
    b = make().for_chat("llama", LLAMA, weights_gb=70.2)
    assert b.source == "predicted"
    assert b.window == 131072


def test_declared_window_caps_the_budget():
    """内存够 100 万 token，窗口只有 131072——窗口封顶。"""
    b = make(available_gib=100_000).for_chat("llama", LLAMA, weights_gb=70.2)
    assert b.token_limit == 131072


def test_memory_caps_the_budget_when_it_is_the_tighter_one():
    b = make(available_gib=8).for_chat("llama", LLAMA, weights_gb=0.1)
    assert b.token_limit < 131072


def test_compact_threshold_is_below_the_limit():
    b = make().for_chat("llama", LLAMA, weights_gb=70.2)
    assert 0 < b.compact_at < b.token_limit


def test_unknown_per_token_cost_falls_back_to_window_and_says_so():
    """算不出每 token 字节时只用声明窗口，并标 unavailable——不套默认值。"""
    b = make().for_chat("mystery", MYSTERY, weights_gb=1.0)
    assert b.token_limit == 4096
    assert b.source == "unavailable"


def test_recorded_turn_switches_the_source_to_measured():
    m = Measurements()
    b = make(measurements=m)
    b.record_turn("llama", "Prompt Cache: 1 sequences, 12.40 GB", 40_000, weights_gb=70.2)
    assert m.model_bytes_per_token("llama", 70.2) == 310_000
    assert make(measurements=m).for_chat("llama", LLAMA, weights_gb=70.2).source == "measured"


def test_unparsable_log_records_nothing_and_stays_predicted():
    """传感器坏了就保持 predicted，不许把上一次的数当成这一次的实测。"""
    m = Measurements()
    make(measurements=m).record_turn("llama", "格式变了", 40_000, weights_gb=70.2)
    assert m.model_bytes_per_token("llama", 70.2) is None


def test_launch_args_use_the_real_mlx_flag_names():
    args = make().launch_args("llama", LLAMA, weights_gb=70.2)
    assert "--prompt-cache-bytes" in args
    assert "--prompt-cache-size" in args
    assert args[args.index("--prompt-cache-size") + 1] == "1"   # 默认 10 份会让占用翻十倍


def test_launch_args_are_empty_when_the_cost_is_unknown():
    """算不出来就不传限额——传一个猜出来的上限比不传更危险。"""
    assert make().launch_args("mystery", MYSTERY, weights_gb=1.0) == []


def test_overrun_tightens_the_next_budget():
    m = Measurements()
    before = make(measurements=m).for_chat("llama", LLAMA, weights_gb=70.2).token_limit
    m.record_overrun("llama", 1_757_000_000.0)
    assert make(measurements=m).for_chat("llama", LLAMA, weights_gb=70.2).token_limit < before


def test_snapshot_labels_every_number_with_its_source():
    snap = make().snapshot()
    assert set(snap) >= {"available_bytes", "pressure", "media"}
    assert snap["media"]["video"]["source"] in ("predicted", "measured", "unavailable")


def test_recorded_turn_survives_a_restart(tmp_path):
    """R-budget-04 说「写入实测档案」——只记在内存里，重启就没了，自校准白做。

    这条盯的是持久化本身：新建一个只从磁盘加载的 Budget，必须还能读到上一轮量到的真值。
    """
    path = tmp_path / "measurements.json"
    first = Budget(measurements=Measurements.load(path), memory_reader=FakeMemory(116),
                   media_estimate=lambda kind, params: 27 * GIB,
                   now=lambda: 1_757_000_000.0, measurements_path=path)
    first.record_turn("llama", "Prompt Cache: 1 sequences, 12.40 GB", 40_000, weights_gb=70.2)

    reloaded = Budget(measurements=Measurements.load(path), memory_reader=FakeMemory(116),
                      media_estimate=lambda kind, params: 27 * GIB,
                      now=lambda: 1_757_000_000.0, measurements_path=path)
    assert reloaded.for_chat("llama", LLAMA, weights_gb=70.2).source == "measured", \
        "重启后丢了实测值：record_turn 没有落盘"


def test_weights_are_subtracted_before_the_kv_budget():
    """设计写的是 (可用 − 权重 − 安全余量) ÷ 每token字节，权重这一项不能漏。

    真机实测抓到的：可用 74 GiB、Llama-70B 权重 75 GB——模型根本装不进去，
    额度却报了满窗口 131072。漏减权重时，额度与「这个模型能不能装下」完全脱钩。
    """
    b = make(available_gib=74)
    assert b.for_chat("llama", LLAMA, weights_gb=75.0).token_limit == 0, \
        "权重比可用内存还大，却算出了正数额度"


def test_a_smaller_model_on_the_same_machine_still_gets_a_budget():
    """反向：权重减掉之后仍有余量的，额度要照常给出来，不能一刀切成 0。"""
    b = make(available_gib=74)
    assert b.for_chat("llama", LLAMA, weights_gb=10.0).token_limit > 0
