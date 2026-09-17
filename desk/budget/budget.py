"""合成额度与共存判定。

fits 与 plan 是纯函数：一组 Workload 加一个可用字节数进，结果出。所以组合可以在
单测里穷举，不必真装一个 70GB 的模型。不要往这两个函数里塞 IO。

共存是集合问题，不是两两判断：三件重活能否同时跑，不等于三个两两判断的合取；
「最小让出」也只有在集合上才算得出来——腾出谁取决于整组的组合。
"""
from __future__ import annotations

import itertools
from dataclasses import dataclass, field

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
