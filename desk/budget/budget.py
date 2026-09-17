"""合成额度与共存判定。

fits 与 plan 是纯函数：一组 Workload 加一个可用字节数进，结果出。所以组合可以在
单测里穷举，不必真装一个 70GB 的模型。不要往这两个函数里塞 IO。

共存是集合问题，不是两两判断：三件重活能否同时跑，不等于三个两两判断的合取；
「最小让出」也只有在集合上才算得出来——腾出谁取决于整组的组合。
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from .estimate import declared_window, per_token_bytes
from .observe import measured_bytes_per_token, parse_cache_line

GIB_F = float(1024 ** 3)

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
            freed = sum(w.bytes_needed for w in combo)
            keep = [w for w in resident if w not in combo]
            verdict = fits(list(wanted) + keep, available_bytes + freed)
            accepted = verdict.ok and verdict.needed_bytes < verdict.available_bytes
            if accepted:
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
SAFETY_FRACTION = 0.9      # 可用内存里留 10% 给系统与其它进程
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

    def __init__(self, measurements, memory_reader, media_estimate, now) -> None:
        self._m = measurements
        self._memory = memory_reader
        self._media_estimate = media_estimate
        self._now = now

    # ---- 单件开销 ----------------------------------------------------
    def cost(self, kind, *, key=None, params=None, config=None, weights_gb=None) -> Workload:
        if kind in ("video", "music"):
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
        available = self._memory.snapshot().available_bytes
        usable = int(available * SAFETY_FRACTION)
        by_memory = max(usable // per_token, 0)
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
    def record_turn(self, key, log_text, prompt_tokens, weights_gb) -> None:
        """一轮答完，把这台机器上的真值记下来（R-budget-04）。"""
        measured = measured_bytes_per_token(parse_cache_line(log_text), prompt_tokens)
        if measured:
            self._m.record_model(key, measured, weights_gb, self._now())

    def snapshot(self) -> dict:
        snap = self._memory.snapshot()
        media = {}
        for kind in ("video", "music"):
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
