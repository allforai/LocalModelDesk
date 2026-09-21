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


def make(available_gib=116, measurements=None, capacity_gib=None):
    """`available_gib` 现在只影响压力那条路径；预算的分母是机器自报的能力。

    R-budget-16 之后分母不再是「此刻可用多少」而是「这台机器能给重活多少」——
    静态属性，从实测档案里读。夹具默认把它设成与旧参数同值，让既有断言的数值关系不变。
    """
    m = measurements or Measurements()
    if m.gpu_capacity() is None:
        from desk.budget.device import GpuCapacity
        gib = capacity_gib if capacity_gib is not None else available_gib
        m.record_gpu_capacity(
            GpuCapacity("测试设备", int(gib * GIB * 1.2), int(gib * GIB), int(gib * GIB * 0.75)),
            1_757_000_000.0)
    return Budget(measurements=m,
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
    # 日志行落后一轮（mlx-lm 在处理开始前打它），所以要两轮才结清第一轮。
    b.record_turn("llama", "Prompt Cache: 0 sequences, 0.00 GB", 40_000, weights_gb=70.2)
    b.record_turn("llama", "Prompt Cache: 1 sequences, 12.40 GB", 5_000, weights_gb=70.2)
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
    from desk.budget.device import GpuCapacity
    path = tmp_path / "measurements.json"
    m = Measurements.load(path)
    # 机器能力和每 token 开销存在同一份档案里，重启后都要还在。
    m.record_gpu_capacity(GpuCapacity("测试设备", 128 * GIB, 107 * GIB, 80 * GIB), 1_757_000_000.0)
    first = Budget(measurements=m, memory_reader=FakeMemory(116),
                   media_estimate=lambda kind, params: 27 * GIB,
                   now=lambda: 1_757_000_000.0, measurements_path=path)
    first.record_turn("llama", "Prompt Cache: 0 sequences, 0.00 GB", 40_000, weights_gb=70.2)
    first.record_turn("llama", "Prompt Cache: 1 sequences, 12.40 GB", 5_000, weights_gb=70.2)

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


def test_the_denominator_is_the_machines_capacity_not_what_is_free_right_now():
    """R-budget-16：同一台机器同一个模型，答案不随此刻在跑什么变化。

    分母换成机器自报的 wired limit 之后，可用内存只剩下「压力兜底」这一个用途。
    这条钉住的正是那个性质：把可用内存改小一个数量级，额度一个字节都不该变。
    """
    m = Measurements()
    from desk.budget.device import GpuCapacity
    m.record_gpu_capacity(GpuCapacity("测试设备", 128 * GIB, 107 * GIB, 80 * GIB), 0.0)
    roomy = Budget(measurements=m, memory_reader=FakeMemory(116),
                   media_estimate=lambda kind, params: 27 * GIB, now=lambda: 0.0)
    cramped = Budget(measurements=m, memory_reader=FakeMemory(3),
                     media_estimate=lambda kind, params: 27 * GIB, now=lambda: 0.0)
    assert (roomy.for_chat("llama", LLAMA, weights_gb=70.2).token_limit
            == cramped.for_chat("llama", LLAMA, weights_gb=70.2).token_limit)


def test_no_capacity_means_unavailable_not_a_guess_from_total_memory():
    """问不出分母时标「算不出」，不拿整机内存顶替——那会把系统留量一起吃掉。"""
    b = Budget(measurements=Measurements(), memory_reader=FakeMemory(116),
               media_estimate=lambda kind, params: 27 * GIB, now=lambda: 0.0)
    chat = b.for_chat("llama", LLAMA, weights_gb=70.2)
    assert chat.source == "unavailable"
    assert chat.token_limit == 131072          # 只剩声明窗口


def test_capacity_is_probed_once_and_remembered(tmp_path):
    """机器能力是静态属性：问一次记下来，之后不再问。"""
    from desk.budget.device import GpuCapacity
    calls = []

    def fake_probe(python):
        calls.append(python)
        return GpuCapacity("测试设备", 128 * GIB, 107 * GIB, 80 * GIB)

    import desk.budget.budget as mod
    original, mod.probe_gpu_capacity = mod.probe_gpu_capacity, fake_probe
    try:
        b = Budget(measurements=Measurements(), memory_reader=FakeMemory(116),
                   media_estimate=lambda kind, params: 27 * GIB, now=lambda: 0.0,
                   probe_python="/fake/python")
        assert b.capacity_bytes() == 107 * GIB
        assert b.capacity_bytes() == 107 * GIB
    finally:
        mod.probe_gpu_capacity = original
    assert len(calls) == 1, f"机器能力被问了 {len(calls)} 次，它是静态属性，应该只问一次"


def test_calibration_pairs_the_log_line_with_the_turn_it_actually_describes():
    """mlx-lm 在**处理开始前**打 Prompt Cache 行，它反映的是上一轮结束后的缓存。

    真机上抓到的：拿「本轮结束时读到的行」配「本轮的 token 数」，配错了一轮；
    第一轮时缓存还空（0.00 GB），于是什么都记不上，预算永远停在 predicted。
    正确的配对是「第 N+1 轮开头记的那行」÷「第 N 轮的 token 数」。
    """
    m = Measurements()
    from desk.budget.device import GpuCapacity
    m.record_gpu_capacity(GpuCapacity("测试设备", 128 * GIB, 107 * GIB, 80 * GIB), 0.0)
    b = Budget(measurements=m, memory_reader=FakeMemory(116),
               media_estimate=lambda kind, params: 27 * GIB, now=lambda: 0.0)

    # 第一轮：此时日志里的行是上一轮（不存在）留下的空缓存 —— 什么都不该记。
    b.record_turn("llama", "Prompt Cache: 0 sequences, 0.00 GB", 10_000, weights_gb=70.2)
    assert m.model_bytes_per_token("llama", 70.2) is None

    # 第二轮：现在日志里那行描述的是第一轮结束后的缓存，配第一轮的 10000 token。
    b.record_turn("llama", "Prompt Cache: 1 sequences, 1.00 GB", 20_000, weights_gb=70.2)
    assert m.model_bytes_per_token("llama", 70.2) == 1_000_000_000 // 10_000


def test_calibration_ignores_an_empty_cache_reading():
    """缓存被清过（换模型、trim）时那行是 0.00 GB——记 0 会把额度算成无穷大。"""
    m = Measurements()
    from desk.budget.device import GpuCapacity
    m.record_gpu_capacity(GpuCapacity("测试设备", 128 * GIB, 107 * GIB, 80 * GIB), 0.0)
    b = Budget(measurements=m, memory_reader=FakeMemory(116),
               media_estimate=lambda kind, params: 27 * GIB, now=lambda: 0.0)
    b.record_turn("llama", "Prompt Cache: 1 sequences, 1.00 GB", 10_000, weights_gb=70.2)
    b.record_turn("llama", "Prompt Cache: 0 sequences, 0.00 GB", 20_000, weights_gb=70.2)
    assert m.model_bytes_per_token("llama", 70.2) is None
