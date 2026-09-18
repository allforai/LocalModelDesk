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
    # 这件重活已经占掉、因而已经从 available_bytes 里扣除的字节数。只有被授予并
    # 驻留之后才有值；未驻留的候选恒为 0。默认值不能去掉：既有几十处四参构造靠它。
    bytes_resident: int = 0


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


def _unallocated(workload) -> int:
    """这件重活还会再吃掉多少内存。

    available_bytes 的口径（free+inactive+purgeable+speculative）已经排除了已分配的
    部分，所以只有尚未分配的那半还需要从余量里扣。实测的 bytes_resident 可能因采样
    噪声略大于 bytes_needed，夹到 0：负数会让一件重活反过来「贡献」额度。
    """
    return max(workload.bytes_needed - workload.bytes_resident, 0)


def fits(workloads, available_bytes: int) -> Verdict:
    """这一组重活能否共存。"""
    workloads = list(workloads)
    needed = sum(_unallocated(w) for w in workloads)
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
            # 物理上只能回收已经分配的那部分：让出一件已驻留重活，未分配的那份
            # 从来没占过内存，回收不了。bytes_resident 恒为 0 时与 bytes_needed
            # 相等，今天看不出来——一旦接到真实驻留点（bytes_resident > 0），用
            # bytes_needed 算 freed 会让 plan() 把可用余量算得偏乐观。
            #
            # 夹在 bytes_needed 以内：一件重活占掉的不可能比它要的还多，而
            # bytes_resident 是实测量、且 Workload 可被外部直接构造
            # （scripts/budget-readback.py 就是手搓的），夹紧不能只靠回填那一处。
            # 不夹住，plan() 会以为让出它能回收超额的字节，据此自动卸掉聊天模型
            # 再授予一件其实装不下的作业——偏乐观的方向才是会 OOM 的那个方向。
            freed = sum(min(w.bytes_resident, w.bytes_needed) for w in combo)
            keep = [w for w in resident if w not in combo]
            verdict = fits(list(wanted) + keep, available_bytes + freed)
            accepted = verdict.ok and verdict.needed_bytes < verdict.available_bytes
            if accepted:
                # released 故意不跟着 freed 改用 bytes_resident：两者问的不是同一件事。
                # freed 是「让出之后物理上真能收回多少」，所以只能算已分配的部分；
                # released 是「让用户放弃了多大一件东西」，是「最小让出」的排序量——
                # 一件已授予 60 GiB 额度、当下才占 5 GiB 的聊天模型，被卸掉时用户
                # 失去的是那整件 60 GiB，不是 5 GiB。把两者「统一」成同一个字段，
                # 最小让出就会开始偏向卸掉大件（大件往往回填得慢、bytes_resident 小）。
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

    def __init__(self, measurements, memory_reader, media_estimate, now,
                 measurements_path=None) -> None:
        self._m = measurements
        self._memory = memory_reader
        self._media_estimate = media_estimate
        self._now = now
        # 没有路径就只记在内存里（单测用）；生产必须给路径，否则每次重启都从
        # predicted 重新开始，自校准等于白做。
        self._measurements_path = measurements_path

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
        # 权重先占掉，剩下的才轮到 KV。漏减这一项，额度就和「这个模型装不装得下」
        # 完全脱钩：真机上可用 74 GiB、权重 75 GB 的模型曾算出满窗口 131072。
        free_for_kv = available - int((weights_gb or 0.0) * GIB_F)
        usable = int(free_for_kv * SAFETY_FRACTION)
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
        if not measured:
            return
        self._m.record_model(key, measured, weights_gb, self._now())
        if self._measurements_path is None:
            return
        try:
            self._m.save(self._measurements_path)
        except OSError:
            # 档案是可重建的：写不进去就下一轮再量，不能让一次落盘失败打断回答。
            log.exception("measurements save failed")

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
