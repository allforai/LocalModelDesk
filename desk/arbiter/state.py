"""Pure state machine for heavy-work mutual exclusion (R-arbiter-01/04).

Zero I/O, zero locks: ``plan_acquire`` maps a current holder and requested
kind to a decision. Concurrency and side effects belong in ``core.py``.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


KINDS = ("llm", "video", "music")
MEDIA_KINDS = ("video", "music")

PHASE_HELD = "held"
PHASE_ACQUIRING = "acquiring"


@dataclass(frozen=True)
class Holder:
    kind: str
    label: str
    token: str
    since: float
    phase: str
    display: str | None = None

    def public_view(self) -> dict:
        """Human-readable holder view for `/api/state` and the menu bar (N2).

        `display` carries a full human-readable name (e.g. a model's catalog
        name, or a media job's window-matching status text); callers that
        have not been updated to pass one fall back to `label` so the field
        is never missing or null.
        """
        return {
            "kind": self.kind,
            "label": self.label,
            "display": self.display or self.label,
            "since": self.since,
            "phase": self.phase,
        }


@dataclass(frozen=True)
class Decision:
    action: Literal["grant", "evict_then_grant", "refuse"]
    reason_code: str | None = None
    reason_message: str | None = None


def plan_acquire(holders, kind: str, verdict) -> Decision:
    """能否再开一件重活：由预算判定，不由持有者种类硬编码（R-arbiter-01 改写）。

    互斥不再是公理，而是「预算不够时的结果」。种类相关的硬编码分支全部删除；
    留下的两条与容量无关：正在转换中、种类不认识。

    这里不再产生 `evict_then_grant`——让出哪些是 `budget.plan()` 在一组重活上算出来
    的集合结果，状态机看不到内存数字，也不替调用方决定让出谁。`core.py` 把
    `budget.plan()` 的建议通过 `can_start_heavy` 的 `release` 字段交给调用方，
    由调用方自己释放对应持有者后重试（R-arbiter-05）。
    """
    if kind not in KINDS:
        return Decision("refuse", "unknown_kind", f"unknown heavy kind: {kind!r}")
    if any(h.phase == PHASE_ACQUIRING for h in holders):
        return Decision(
            "refuse", "transition_in_progress",
            "a heavy-work transition is in progress; retry shortly",
        )
    if verdict.ok:
        return Decision("grant")
    return Decision(
        "refuse", "insufficient_budget",
        f"需要 {verdict.needed_bytes} 字节，可用 {verdict.available_bytes} 字节"
        f"（依据：{verdict.source}）",
    )


def still_holds(desk_state, kind: str, label: str | None) -> bool:
    """台面此刻是否还认这件重活由 `label` 持有。

    消费者问的从来是这个，而不是「有没有别的重活在跑」：预算模式下媒体作业可以与
    聊天共存，`holder` 只是最后授予的那一件，只看它就会把「别人也拿到了」误读成
    「我被驱逐了」。共存的安全性在授予那一刻已经算过了——`budget.cost("llm")` 报的
    `bytes_needed` 就是权重加满窗 KV，媒体能开正说明两者一起装得下。
    """
    if not isinstance(desk_state, dict):
        return False
    holders = desk_state.get("holders")
    if not isinstance(holders, list):
        holders = [desk_state.get("holder")]
    return any(
        isinstance(h, dict) and h.get("kind") == kind and h.get("label") == label
        for h in holders
    )
