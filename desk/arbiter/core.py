"""Thread-safe facade for heavy-work ownership and LLM eviction.

R-arbiter-01 改写：能否并存由预算判定，预算不足时退化为互斥；持有者由单个变一组。
This facade now has two modes, selected once at construction by whether a
``budget`` (``desk.budget.budget.Budget``-shaped: a ``.cost(...)`` method) is
supplied:

* **legacy mode** (``budget=None``) — a fallback for call sites not wired up to
  a real ``Budget``. As of Task 7, ``desk/runtime.py`` *does* wire one
  (``arbiter = Arbiter(DEFAULT_LLM_PORT, budget=budget)``) — production runs in
  budget mode. What still runs legacy today is the browser-e2e test harness
  (``desk/testing/harness.py`` constructs its ``Arbiter`` with no ``budget=``),
  which is why ``tests/e2e/*`` exercises this branch, not the one below.
  Behaviour here is byte-for-byte the pre-Task-7 rule table: one heavy slot,
  media always evicts a resident LLM, a second LLM or a second media job is
  always refused. This is *not* an approximation of the old behaviour, it is
  the old behaviour, kept alive as a private fallback because
  ``desk/arbiter/state.py`` no longer contains it (R-arbiter-01 deleted the
  kind-hardcoded branches from the pure state machine on purpose).
* **budget mode** (``budget=<Budget>``) — coexistence is a real, multi-holder
  state: granting a request no longer evicts residents when the combined
  ``Workload`` set still fits (this is the law R-arbiter-01 overturns —
  "媒体在跑，预算够，聊天照样装得下"). A refusal is advisory-only here:
  ``acquire_heavy`` never auto-evicts in this mode, it just says no; the
  caller learns the minimal release set from ``can_start_heavy`` and releases
  those tokens itself before retrying (R-arbiter-05 "仅在预算不足时让出，且最小
  让出").
"""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import replace

from ..budget.budget import fits, plan
from .memory import MemoryReader
from .reaper import ReapResult, port_listeners, reap_port
from .state import (
    KINDS, MEDIA_KINDS, PHASE_ACQUIRING, PHASE_HELD, Decision, Holder, plan_acquire,
)


class Arbiter:
    """Serialize heavy work, replacing an LLM holder before media work starts."""

    def __init__(
        self,
        llm_port: int,
        *,
        memory: MemoryReader | None = None,
        reaper: Callable[[int], ReapResult] = reap_port,
        clock: Callable[[], float] = time.time,
        logger: logging.Logger | None = None,
        budget=None,
    ):
        self.llm_port = llm_port
        self._memory = memory or MemoryReader()
        self._reaper = reaper
        self._owned_pid_provider: Callable[[], set[int]] | None = None
        self._clock = clock
        self._logger = logger or logging.getLogger(__name__)
        self._budget = budget
        self._transition_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._holders: dict[str, Holder] = {}     # token -> Holder
        self._workloads: dict[str, object] = {}    # token -> Workload (budget mode only)
        self._grant_baseline: dict[str, int] = {}  # token -> available_bytes at grant time
        self._subscribers: list[Callable[[dict], None]] = []

    @staticmethod
    def _reason(code: str, message: str) -> dict:
        return {"code": code, "message": message}

    @staticmethod
    def _public_holder(holder: Holder | None) -> dict | None:
        return None if holder is None else holder.public_view()

    @staticmethod
    def _workload_view(workload) -> dict:
        return {"kind": workload.kind, "key": workload.key,
                "bytes_needed": workload.bytes_needed, "source": workload.source}

    # ---- decision (pure given a snapshot; no locking) -----------------
    def _legacy_decision(self, holder: Holder | None, kind: str) -> Decision:
        """The pre-Task-7 transition table (see module docstring)."""
        if kind not in KINDS:
            return Decision("refuse", "unknown_kind", f"unknown heavy kind: {kind!r}")
        if holder is None:
            return Decision("grant")
        if holder.phase == PHASE_ACQUIRING:
            return Decision(
                "refuse", "transition_in_progress",
                "a heavy-work transition is in progress; retry shortly",
            )
        if holder.kind in MEDIA_KINDS:
            return Decision("refuse", "media_busy", f"{holder.kind} job {holder.label!r} is running")
        if kind == "llm":
            return Decision(
                "refuse", "llm_already_held",
                f"llm {holder.label!r} already holds memory; release it first",
            )
        return Decision("evict_then_grant")

    def _cost(self, kind: str, params: dict | None, key: str | None):
        """Budget-mode cost of a request. Never called in legacy mode."""
        params = params or {}
        if kind in ("video", "music"):
            return self._budget.cost(kind, key=key, params=params)
        return self._budget.cost(kind, key=key, config=params.get("config"),
                                  weights_gb=params.get("weights_gb"))

    def _decide_from(self, kind, params, key, holders, resident, available_bytes):
        """Decide given an already-known snapshot — no locking, safe to call
        while already holding ``_state_lock``."""
        if self._budget is None:
            holder = holders[-1] if holders else None
            return self._legacy_decision(holder, kind), None, holder
        workload = self._cost(kind, params, key)
        verdict = fits(list(resident) + [workload], available_bytes)
        holder = holders[-1] if holders else None
        return plan_acquire(holders, kind, verdict), workload, holder

    def _ownership_answer(self, kind: str, holders) -> dict:
        """无参查询的答案：只看谁占着，不看内存（R-budget-13）。

        六个调用点（下载闸、网关守卫、台面状态的两个按钮、两处测试台面）问的都是
        「现在谁占着、能不能开这一类」。无参进预算路径时 cost() 拿不到输入，产出
        bytes_needed=0 且 source=unavailable 的空壳，再撞上「一件 unavailable 整组
        保守」，会与机器多大无关地恒为 insufficient_budget。
        """
        if kind not in KINDS:
            return {"ok": False, "reason": self._reason("unknown_kind", f"unknown heavy kind: {kind!r}"),
                    "memory_warning": None, "release": []}
        if any(h.phase == PHASE_ACQUIRING for h in holders):
            return {"ok": False, "reason": self._reason(
                "transition_in_progress", "a heavy-work transition is in progress; retry shortly"),
                "memory_warning": None, "release": []}
        busy = next((h for h in holders if h.kind in MEDIA_KINDS), None)
        if kind in MEDIA_KINDS and busy is not None:
            return {"ok": False, "reason": self._reason("media_busy", f"{busy.kind} job {busy.label!r} is running"),
                    "memory_warning": None, "release": []}
        return {"ok": True, "reason": None, "memory_warning": None, "release": []}

    def _decide(self, kind, params, key):
        """Snapshot current holders (briefly under `_state_lock`) then decide."""
        available_bytes = self._memory.snapshot().available_bytes
        self._backfill_resident(available_bytes)
        with self._state_lock:
            holders = tuple(self._holders.values())
            resident = tuple(
                w for h in holders if (w := self._workloads.get(h.token)) is not None
            )
        decision, workload, holder = self._decide_from(
            kind, params, key, holders, resident, available_bytes)
        return decision, workload, resident, available_bytes, holder

    def _record_baseline(self, token: str, available_bytes: int) -> None:
        """授予时的可用内存。回填 bytes_resident 要用它作差。"""
        self._grant_baseline[token] = available_bytes

    def _backfill_resident(self, available_bytes: int) -> None:
        """用「授予时基线 − 当前可用」回填已分配字节，只填一次。

        采样点不在 acquire_heavy 里：那时模型还没开始加载，量到的是 0。改为每次读
        快照时顺带回填，不需要新线程也不需要改调用方。

        只填一次是有意的：KV 慢慢长起来时若跟着涨，未分配会越算越小，最终等于把
        这件重活当成不占内存。可用内存不降反升（别的进程释放了）时记 0，不记负数。
        """
        with self._state_lock:
            for token, workload in list(self._workloads.items()):
                if workload.bytes_resident:
                    continue
                baseline = self._grant_baseline.get(token)
                if baseline is None:
                    continue
                measured = max(baseline - available_bytes, 0)
                if measured:
                    self._workloads[token] = replace(workload, bytes_resident=measured)

    # ---- state mutation (holds _state_lock only) -----------------------
    def _grant(self, token: str, holder: Holder, workload, available_bytes: int) -> dict:
        with self._state_lock:
            self._holders[token] = holder
            if workload is not None:
                self._workloads[token] = workload
                self._record_baseline(token, available_bytes)
            holders = tuple(self._holders.values())
        return self._state_for(holders)

    def _replace_all(self, holder: Holder | None) -> dict:
        """Legacy single-slot replace: only the no-budget eviction path uses this."""
        with self._state_lock:
            self._holders = {} if holder is None else {holder.token: holder}
            self._workloads = {}
            self._grant_baseline = {}
            holders = tuple(self._holders.values())
        return self._state_for(holders)

    def _state_for(self, holders: tuple[Holder, ...]) -> dict:
        """Build the public state dict for `holders`.

        In budget mode, `can_start` answers ownership only (R-budget-13, via
        ``_ownership_answer``) — it takes no params/key, so it has no budget
        arithmetic to do. In legacy mode it still goes through
        ``_decide_from``/``_legacy_decision`` unchanged: the module docstring
        promises legacy is byte-for-byte the pre-Task-7 rule table (single
        heavy slot, any resident holder blocks any other kind), and
        ``_ownership_answer``'s narrower "only media blocks media" rule would
        silently widen that table — a real regression a Playwright e2e test
        caught (``tests/e2e/test_mutex_ui.py``, which runs the legacy-mode test
        harness): with a video holder resident, ``can_start_heavy("llm")``
        (still legacy) said refuse/media_busy while this method's `can_start`
        (switched unconditionally) said ok — two answers to the same
        parameterless ownership question from the same arbiter state. See
        ``test_can_start_heavy_and_desk_state_agree_on_ownership_in_legacy_mode``.

        The ``_backfill_resident`` call below stays regardless of branch: in
        budget mode it is not read by ``can_start`` any more, but this is
        still the 2-second desk_state poll that drives backfill for every
        other reader of ``bytes_resident`` (``can_start_heavy`` with params,
        ``release`` planning, ...). Dropping it here would silently stop
        backfill from ever running.
        """
        available_bytes = self._memory.snapshot().available_bytes
        self._backfill_resident(available_bytes)

        def can_start(kind: str) -> dict:
            if self._budget is not None:
                answer = self._ownership_answer(kind, holders)
                return {"ok": answer["ok"], "reason": answer["reason"]}
            decision, _workload, _holder = self._decide_from(
                kind, None, None, holders, (), available_bytes)
            if decision.action != "refuse":
                return {"ok": True, "reason": None}
            return {"ok": False, "reason": self._reason(decision.reason_code, decision.reason_message)}

        primary = holders[-1] if holders else None
        return {
            "holder": self._public_holder(primary),
            "media_busy": any(h.kind in MEDIA_KINDS for h in holders),
            "can_start": {"llm": can_start("llm"), "media": can_start("video")},
        }

    def _read_holder(self) -> Holder | None:
        with self._state_lock:
            holders = tuple(self._holders.values())
        return holders[-1] if holders else None

    def _dispatch(self, states: list[dict]) -> None:
        if not states:
            return
        with self._state_lock:
            subscribers = tuple(self._subscribers)
        for state in states:
            for callback in subscribers:
                try:
                    callback(state)
                except Exception:
                    self._logger.exception("heavy-state subscriber failed")

    def subscribe(self, callback: Callable[[dict], None]) -> Callable[[], None]:
        """Subscribe to state changes and return an idempotent unsubscribe callback."""
        with self._state_lock:
            self._subscribers.append(callback)

        def unsubscribe() -> None:
            with self._state_lock:
                try:
                    self._subscribers.remove(callback)
                except ValueError:
                    pass

        return unsubscribe

    def memory_snapshot(self) -> dict:
        """Return the current memory probe as a public dictionary."""
        return self._memory.snapshot().to_dict()

    def set_owned_pid_provider(self, provider: "Callable[[], set[int]] | None") -> None:
        """Register who reports the pids this desk actually spawned.

        Without it the reaper is asked to free the port blindly; with it a stranger
        listening on 8767 is left alone (P1: reaping must verify ownership).
        """
        self._owned_pid_provider = provider

    def _reap(self, port: int):
        if self._owned_pid_provider is None:
            return self._reaper(port)
        return self._reaper(port, owned_pids=self._owned_pid_provider())

    def reap_llm_port(self, port: int) -> dict:
        """Reap listeners on the supplied port, independent of eviction state."""
        return self._reap(port).to_dict()

    def llm_port_listeners(self, port: int) -> list[dict]:
        """Listeners still on the LLM port after reaping — strangers the arbiter will not kill."""
        return port_listeners(port)

    def desk_state(self) -> dict:
        with self._state_lock:
            holders = tuple(self._holders.values())
        return self._state_for(holders)

    def can_start_heavy(self, kind: str, params: dict | None = None, key: str | None = None,
                         estimated_bytes: int | None = None) -> dict:
        """Read-only acquisition pre-check.

        Legacy mode (no budget wired): unchanged from before Task 7 — an optional
        ``estimated_bytes`` produces a ``memory_warning`` without refusing, and
        never carries a ``release`` key.

        Budget mode: consults ``budget.cost``/``fits``; a refusal whose
        ``reason_code`` is ``insufficient_budget`` also carries ``release`` — the
        minimal set of resident workloads (``budget.plan``) that would need to be
        released for the request to fit (R-arbiter-05, R-budget-07).

        R-budget-13: a call with neither ``params`` nor ``key`` is asking who
        currently owns what, not whether a specific job fits — it never reaches
        the budget arithmetic below, because ``_cost`` would have nothing to
        cost and would fall back to an ``unavailable`` stub that always refuses
        (R-budget-10 treats one ``unavailable`` workload as grounds to refuse
        the whole group, regardless of machine size). This is the judgment call
        that matters, not whether a budget happens to be wired
        (``self._budget is None`` is the unrelated legacy fallback).
        """
        if self._budget is not None and params is None and key is None:
            with self._state_lock:
                holders = tuple(self._holders.values())
            return self._ownership_answer(kind, holders)

        decision, workload, resident, available_bytes, _holder = self._decide(kind, params, key)

        if self._budget is None:
            if decision.action == "refuse":
                return {"ok": False, "reason": self._reason(decision.reason_code, decision.reason_message),
                        "memory_warning": None}
            warning = None
            if estimated_bytes is not None and estimated_bytes > available_bytes:
                warning = {
                    "code": "insufficient_memory",
                    "required_bytes": estimated_bytes,
                    "available_bytes": available_bytes,
                    "message": (
                        f"model requires about {estimated_bytes / 1_000_000_000:.1f} GB; "
                        f"{available_bytes / 1_000_000_000:.1f} GB is currently available"
                    ),
                }
            return {"ok": True, "reason": None, "memory_warning": warning}

        if decision.action == "refuse":
            release: list[dict] = []
            if decision.reason_code == "insufficient_budget":
                outcome = plan([workload], list(resident), available_bytes)
                if outcome.ok:
                    release = [self._workload_view(w) for w in outcome.release]
            return {"ok": False, "reason": self._reason(decision.reason_code, decision.reason_message),
                    "memory_warning": None, "release": release}
        warning = None
        if workload.bytes_needed > available_bytes:
            warning = {
                "code": "insufficient_memory",
                "required_bytes": workload.bytes_needed,
                "available_bytes": available_bytes,
                "source": workload.source,
                "message": (
                    f"model requires about {workload.bytes_needed / 1_000_000_000:.1f} GB; "
                    f"{available_bytes / 1_000_000_000:.1f} GB is currently available"
                ),
            }
        return {"ok": True, "reason": None, "memory_warning": warning, "release": []}

    def _should_evict_llm(self, decision, workload, resident, available_bytes) -> bool:
        """最小让出方案是否「只需卸掉聊天模型」。

        只有这一种让出是自动的。方案若要求腾掉正在跑的媒体作业，一律拒绝——
        为了开另一件重活而静默杀掉用户正在跑的生成，不是台面该替他做的决定。
        """
        if self._budget is None or decision.reason_code != "insufficient_budget":
            return False
        outcome = plan([workload], list(resident), available_bytes)
        return outcome.ok and bool(outcome.release) and all(w.kind == "llm" for w in outcome.release)

    def acquire_heavy(self, kind: str, label: str, display: str | None = None,
                       *, params: dict | None = None, key: str | None = None) -> dict:
        """Acquire a token. In legacy mode, evicts the active LLM first for media
        requests (unchanged). In budget mode, grants alongside residents when the
        combined workload still fits and never auto-evicts otherwise — see the
        module docstring."""
        decision, _workload, _resident, _available, holder = self._decide(kind, params, key)
        if holder is not None and holder.phase == PHASE_ACQUIRING:
            return {"ok": False, "reason": self._reason(decision.reason_code, decision.reason_message)}

        states: list[dict] = []
        with self._transition_lock:
            decision, workload, resident, available_bytes, holder = self._decide(kind, params, key)
            if decision.action == "refuse":
                # 预算不足时不是直接拒绝：R-arbiter-05 要求「让出，且最小让出」。
                # plan() 早就算好了该腾谁，之前没有任何调用方消费它，于是
                # 「加载着聊天模型时开视频作业」会失败，而 legacy 模式下会先卸再跑。
                if self._should_evict_llm(decision, workload, resident, available_bytes):
                    decision = Decision("evict_then_grant")
                else:
                    return {"ok": False, "reason": self._reason(decision.reason_code, decision.reason_message)}

            token = uuid.uuid4().hex
            if decision.action == "grant":
                state = self._grant(token, Holder(kind, label, token, self._clock(), PHASE_HELD, display),
                                     workload, available_bytes)
                states.append(state)
                result = {"ok": True, "token": token, "state": state}
            else:
                # evict_then_grant — legacy mode only; budget mode's plan_acquire
                # never returns this action (see state.py).
                acquiring = Holder(kind, label, token, self._clock(), PHASE_ACQUIRING, display)
                states.append(self._replace_all(acquiring))
                reaped = self._reap(self.llm_port)
                if reaped.ok:
                    state = self._grant(token, Holder(kind, label, token, self._clock(), PHASE_HELD, display),
                                         workload, available_bytes)
                    states.append(state)
                    result = {"ok": True, "token": token, "state": state}
                else:
                    states.append(self._replace_all(holder))
                    result = {"ok": False, "reason": self._reason(
                        "evict_failed", reaped.error or "LLM eviction failed")}

        self._dispatch(states)
        return result

    def release_heavy(self, token: str) -> dict:
        """Release only the currently held matching token."""
        states: list[dict] = []
        with self._transition_lock:
            with self._state_lock:
                found = token in self._holders
                if found:
                    self._holders.pop(token, None)
                    self._workloads.pop(token, None)
                    self._grant_baseline.pop(token, None)
                holders = tuple(self._holders.values())
            if not found:
                return {"ok": False, "reason": self._reason(
                    "not_holder", "token does not hold the current heavy-work lease")}
            states.append(self._state_for(holders))
        self._dispatch(states)
        return {"ok": True}
