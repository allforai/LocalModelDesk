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


@dataclass(frozen=True)
class Decision:
    action: Literal["grant", "evict_then_grant", "refuse"]
    reason_code: str | None = None
    reason_message: str | None = None


def plan_acquire(holder: Holder | None, kind: str) -> Decision:
    """Return the transition-table decision for a heavy-work request."""
    if kind not in KINDS:
        return Decision("refuse", "unknown_kind", f"unknown heavy kind: {kind!r}")
    if holder is None:
        return Decision("grant")
    if holder.phase == PHASE_ACQUIRING:
        return Decision(
            "refuse",
            "transition_in_progress",
            "a heavy-work transition is in progress; retry shortly",
        )
    if holder.kind in MEDIA_KINDS:
        return Decision(
            "refuse",
            "media_busy",
            f"{holder.kind} job {holder.label!r} is running",
        )
    if kind == "llm":
        return Decision(
            "refuse",
            "llm_already_held",
            f"llm {holder.label!r} already holds memory; release it first",
        )
    return Decision("evict_then_grant")
