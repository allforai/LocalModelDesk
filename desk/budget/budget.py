"""合成额度与共存判定。

fits 与 plan 是纯函数：一组 Workload 加一个可用字节数进，结果出。所以组合可以在
单测里穷举，不必真装一个 70GB 的模型。不要往这两个函数里塞 IO。

共存是集合问题，不是两两判断：三件重活能否同时跑，不等于三个两两判断的合取；
「最小让出」也只有在集合上才算得出来——腾出谁取决于整组的组合。
"""
from __future__ import annotations

import itertools
import logging
from dataclasses import dataclass, field

from .estimate import declared_window, per_token_bytes
from .device import probe_gpu_capacity
from .observe import measured_bytes_per_token, parse_cache_line

GIB_F = float(1024 ** 3)

log = logging.getLogger(__name__)

SOURCES = ("measured", "predicted", "unavailable")   # 由强到弱


@dataclass(frozen=True)
class Workload:
    kind: str
    key: str | None
    bytes_needed: int
    source: str


@dataclass(frozen=True)
class Verdict:
    ok: bool
    needed_bytes: int
    available_bytes: int
    source: str
    shortfall_bytes: int


@dataclass(frozen=True)
class Plan:
    ok: bool
    release: tuple[Workload, ...]
    verdict: Verdict


def weakest_source(workloads) -> str:
    """一组的依据取最弱者：两件实测加一件没量过，整组仍是没量过（R-budget-10）。"""
    return max((w.source for w in workloads), key=SOURCES.index, default="measured")



def fits(workloads, available_bytes: int) -> Verdict:
    """这一组重活能否共存。"""
    workloads = list(workloads)
    needed = sum(w.bytes_needed for w in workloads)
    source = weakest_source(workloads)
    ok = needed <= available_bytes
    # 未经本机实测不放宽：来源不可用时，只允许单件——这正是今天的互斥行为。
    if source == "unavailable" and len(workloads) > 1:
        ok = False
    return Verdict(
        ok=ok, needed_bytes=needed, available_bytes=available_bytes,
        source=source, shortfall_bytes=max(needed - available_bytes, 0),
    )


def plan(wanted, resident, available_bytes: int) -> Plan:
    """想跑 wanted，当前驻留 resident ⇒ 该让出哪些（最小让出）。

    枚举 resident 的子集，取「能装下且让出总量最小」的那个。重活至多三件，
    子集至多 8 个，穷举比任何启发式都更容易证明是对的。

    接受一个候选组合要求严格富余（needed < available），不是「刚好塞满」
    （needed <= available）：塞满是 `fits()` 自己的公开语义（它的边界测试
    `test_empty_group_fits` 要求 0 <= 0 为真，所以那个 <= 不能动），但
    `plan()` 决定「要不要让出」时不能把「一点不剩地塞满」当成够用——
    `test_plan_releases_the_cheapest_set_that_makes_room` 与
    `test_plan_reports_failure_when_even_full_eviction_is_not_enough` 两条都
    把 needed 恰好等于 available 的临界情况判为「不够」，逼着（前者）多让出
    一件、（后者）判定失败。用 `fits()` 的非严格结果去接受组合会在这两条上
    判反，所以这里单独收紧。
    """
    resident = list(resident)
    wanted = list(wanted)
    best = None
    for size in range(len(resident) + 1):
        for combo in itertools.combinations(resident, size):
            # 让出一件重活，回收的就是它整件的额度——分母换成机器自报的静态
            # 能力之后（R-budget-16），"声明的占用"和"分母"是同一种东西，
            # 不再需要去问"你此刻实际占了多少"来对账。
            freed = sum(w.bytes_needed for w in combo)
            keep = [w for w in resident if w not in combo]
            verdict = fits(list(wanted) + keep, available_bytes + freed)
            accepted = verdict.ok and verdict.needed_bytes < verdict.available_bytes
            if accepted:
                # released 与 freed 现在同值（都是整件额度），但保留两个名字：
                # 它们问的不是同一件事——freed 是"让出后余量增加多少"，
                # released 是"用户放弃了多大一件东西"，即最小让出的排序量。
                released = sum(w.bytes_needed for w in combo)
                if best is None or released < best[0]:
                    best = (released, combo, verdict)
        if best is not None:
            break        # 子集按大小递增枚举，先找到的就是让出件数最少的
    if best is None:
        return Plan(ok=False, release=(), verdict=fits(wanted + resident, available_bytes))
    _, combo, verdict = best
    return Plan(ok=True, release=tuple(combo), verdict=verdict)


COMPACT_FRACTION = 0.75    # 策略值，不是推导值：额度用到这个比例就压缩
CACHE_SLOTS = 1            # mlx-lm 默认保 10 份 KV 缓存；台面一次只服务一个会话


@dataclass(frozen=True)
class ChatBudget:
    token_limit: int
    compact_at: int
    source: str
    window: int | None


class Budget:
    """门面：把 IO（内存快照、日志文本、实测档案）接到纯函数上。

    依赖全部构造注入，所以测试不起服务、不装模型。
    """

    def __init__(self, measurements, memory_reader, media_estimate, now,
                 measurements_path=None, probe_python=None) -> None:
        self._m = measurements
        self._memory = memory_reader
        self._media_estimate = media_estimate
        self._now = now
        # 没有路径就只记在内存里（单测用）；生产必须给路径，否则每次重启都从
        # predicted 重新开始，自校准等于白做。
        self._measurements_path = measurements_path
        # 问机器能力用的解释器（要装了 mlx 的那个）。给 None 就只能靠档案里已有的读数。
        self._probe_python = probe_python
        # 上一轮的 (key, tokens, weights)——日志行落后一轮，见 record_turn。
        self._pending_turn = None

    # ---- 分母：机器自报的重活能力 ------------------------------------
    def capacity_bytes(self) -> int | None:
        """重活总共能用多少内存（R-budget-16）；问不出返回 None。

        这是**静态的机器属性**，不是此刻的可用内存——来自 mlx 的
        `max_recommended_working_set_size`，也就是它自己会 `set_wired_limit` 的那个值。
        wired 的内存不参与换页，所以它是硬上限；而 Apple 报这个数时已经替系统
        留好了量（本机 128 GiB 报 107.5 GiB，留 20.5 GiB ≈ 16%），不需要我们再拍留量。

        量一次记进实测档案，之后直接读——同一台机器同一个模型永远同一个答案，
        不随此刻在跑什么波动。
        """
        recorded = self._m.gpu_capacity()
        if recorded:
            return int(recorded["working_set_bytes"])
        if self._probe_python is None:
            return None
        capacity = probe_gpu_capacity(self._probe_python)
        if capacity is None:
            return None
        self._m.record_gpu_capacity(capacity, self._now())
        self._persist()
        return capacity.working_set_bytes

    # ---- 单件开销 ----------------------------------------------------
    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None) -> Workload:
        if kind in ("video", "music", "image"):
            measured = self._m.media_peak(kind)
            need = measured if measured else self._media_estimate(kind, params or {})
            return Workload(kind, key, int(need), "measured" if measured else "predicted")
        chat = self.for_chat(key, config or {}, weights_gb or 0.0)
        per_token = self._per_token(key, config or {}, weights_gb or 0.0)[0] or 0
        weights = int((weights_gb or 0.0) * GIB_F)
        return Workload(kind, key, weights + chat.token_limit * per_token, chat.source)

    # ---- 聊天额度 ----------------------------------------------------
    def _per_token(self, key, config, weights_gb):
        """(每 token 字节, 来源)。实测优先，否则预测，都没有就 unavailable。"""
        measured = self._m.model_bytes_per_token(key, weights_gb) if key else None
        if measured:
            return measured, "measured"
        predicted = per_token_bytes(config)
        return (predicted, "predicted") if predicted else (None, "unavailable")

    def for_chat(self, key, config, weights_gb) -> ChatBudget:
        window = declared_window(config)
        per_token, source = self._per_token(key, config, weights_gb)
        if per_token is None:
            limit = window or 0
            return ChatBudget(limit, int(limit * COMPACT_FRACTION), "unavailable", window)
        capacity = self.capacity_bytes()
        if capacity is None:
            # 分母问不出来（没装 mlx、非 Apple 芯片、字段改名）就只用声明窗口，
            # 并如实标「算不出」——不拿整机内存顶替（R-budget-16）。
            limit = window or 0
            return ChatBudget(limit, int(limit * COMPACT_FRACTION), "unavailable", window)
        # 权重先占掉，剩下的才轮到 KV。漏减这一项，额度就和「这个模型装不装得下」
        # 完全脱钩：曾经算出过一个根本装不进去的模型能带满窗口。
        free_for_kv = capacity - int((weights_gb or 0.0) * GIB_F)
        by_memory = max(free_for_kv // per_token, 0)
        limit = min(by_memory, window) if window else by_memory
        # 收紧作用于最终额度，而不只是内存推出的那一支：否则窗口比内存更紧时
        # （常见情况——声明窗口通常远小于内存能装下的量），爆过一次也不会让
        # 下一次的额度变小，收紧规则形同虚设。
        limit = int(limit * self._m.overrun_factor(key or ""))
        return ChatBudget(limit, int(limit * COMPACT_FRACTION), source, window)

    # ---- mlx-lm 限额参数 ---------------------------------------------
    def launch_args(self, key, config, weights_gb) -> list[str]:
        per_token, source = self._per_token(key, config, weights_gb)
        if per_token is None:
            return []       # 算不出来就不传：一个猜出来的上限比不传更危险
        chat = self.for_chat(key, config, weights_gb)
        return ["--prompt-cache-bytes", str(chat.token_limit * per_token),
                "--prompt-cache-size", str(CACHE_SLOTS)]

    # ---- 自校准 ------------------------------------------------------
    def record_turn(self, key, log_text, tokens, weights_gb) -> None:
        """一轮答完，把这台机器上的真值记下来（R-budget-04）。

        **日志行落后一轮，这一点是真机上量出来的。** mlx-lm 的 `_log_cache_stats()`
        在 `fetch_nearest_cache` **之前**调用（server.py:752 与 :964），所以一轮结束时
        读到的那行，描述的是**上一轮**结束后的缓存状态。拿它配本轮的 token 数会错位
        一轮；而第一轮时缓存还空（`0 sequences, 0.00 GB`），于是什么都记不上，
        预算永远停在 predicted——这正是真机上观察到的现象。

        所以配对是「第 N+1 轮开头记的那行」÷「第 N 轮的 token 数」：本轮先用日志
        结清上一轮，再把自己挂起等下一轮。
        """
        cache_bytes = parse_cache_line(log_text)
        pending = self._pending_turn
        self._pending_turn = (key, tokens, weights_gb)
        if pending is None or not cache_bytes:
            return
        prev_key, prev_tokens, prev_weights = pending
        if prev_key != key:
            return          # 中间换过模型，这份缓存不是它的
        measured = measured_bytes_per_token(cache_bytes, prev_tokens)
        if not measured:
            return
        self._m.record_model(prev_key, measured, prev_weights, self._now())
        self._persist()

    def _persist(self) -> None:
        """档案是可重建的：写不进去就下次再量，不能让一次落盘失败打断别的事。"""
        if self._measurements_path is None:
            return
        try:
            self._m.save(self._measurements_path)
        except OSError:
            log.exception("measurements save failed")

    def snapshot(self) -> dict:
        snap = self._memory.snapshot()
        media = {}
        for kind in ("video", "music", "image"):
            peak = self._m.media_peak(kind)
            media[kind] = {"peak_bytes": peak, "source": "measured" if peak else "predicted"}
        return {"available_bytes": snap.available_bytes,
                "total_bytes": snap.total_bytes,
                "pressure": snap.pressure,
                "media": media}

    def snapshot_with_chat(self, key=None, config=None, weights_gb=None) -> dict:
        """台面状态 + 诊断都要看得出每个数字的来源（R-budget-01）。

        没有驻留模型时 chat 就是「算不出」，不是猜一个：没有 key 就没有 for_chat
        可用的输入，装作能算反而会把「没有模型」和「模型没量过」混为一谈。
        """
        snap = self.snapshot()
        if key is None:
            chat = {"source": "unavailable"}
        else:
            cb = self.for_chat(key, config or {}, weights_gb or 0.0)
            chat = {"token_limit": cb.token_limit, "compact_at": cb.compact_at,
                    "source": cb.source, "window": cb.window}
        snap["chat"] = chat
        return snap
