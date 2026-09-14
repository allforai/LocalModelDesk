"""Thread-safe facade for heavy-work ownership and LLM eviction."""
from __future__ import annotations

import logging
import threading
import time
import uuid
from collections.abc import Callable

from .memory import MemoryReader
from .reaper import ReapResult, port_listeners, reap_port
from .state import Holder, PHASE_ACQUIRING, PHASE_HELD, plan_acquire


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
    ):
        self.llm_port = llm_port
        self._memory = memory or MemoryReader()
        self._reaper = reaper
        self._owned_pid_provider: Callable[[], set[int]] | None = None
        self._clock = clock
        self._logger = logger or logging.getLogger(__name__)
        self._transition_lock = threading.Lock()
        self._state_lock = threading.Lock()
        self._holder: Holder | None = None
        self._subscribers: list[Callable[[dict], None]] = []

    @staticmethod
    def _reason(code: str, message: str) -> dict:
        return {"code": code, "message": message}

    @staticmethod
    def _public_holder(holder: Holder | None) -> dict | None:
        return None if holder is None else holder.public_view()

    def _state_for(self, holder: Holder | None) -> dict:
        def can_start(kind: str) -> dict:
            decision = plan_acquire(holder, kind)
            if decision.action != "refuse":
                return {"ok": True, "reason": None}
            return {
                "ok": False,
                "reason": self._reason(decision.reason_code, decision.reason_message),
            }

        return {
            "holder": self._public_holder(holder),
            "media_busy": holder is not None and holder.kind in {"video", "music"},
            "can_start": {"llm": can_start("llm"), "media": can_start("video")},
        }

    def _read_holder(self) -> Holder | None:
        with self._state_lock:
            return self._holder

    def _set_holder(self, holder: Holder | None) -> dict:
        with self._state_lock:
            self._holder = holder
            return self._state_for(holder)

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

    def current_holder(self) -> dict | None:
        return self._public_holder(self._read_holder())

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
        return self._state_for(self._read_holder())

    def can_start_heavy(self, kind: str, estimated_bytes: int | None = None) -> dict:
        """Read-only acquisition pre-check, with an optional memory warning."""
        decision = plan_acquire(self._read_holder(), kind)
        if decision.action == "refuse":
            return {
                "ok": False,
                "reason": self._reason(decision.reason_code, decision.reason_message),
                "memory_warning": None,
            }

        warning = None
        if estimated_bytes is not None:
            available_bytes = self._memory.snapshot().available_bytes
            if estimated_bytes > available_bytes:
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

    def acquire_heavy(self, kind: str, label: str, display: str | None = None) -> dict:
        """Acquire a token, evicting the active LLM first for media requests."""
        holder = self._read_holder()
        decision = plan_acquire(holder, kind)
        if holder is not None and holder.phase == PHASE_ACQUIRING:
            return {"ok": False, "reason": self._reason(
                decision.reason_code, decision.reason_message)}

        states: list[dict] = []
        with self._transition_lock:
            holder = self._read_holder()
            decision = plan_acquire(holder, kind)
            if decision.action == "refuse":
                return {"ok": False, "reason": self._reason(
                    decision.reason_code, decision.reason_message)}

            token = uuid.uuid4().hex
            if decision.action == "grant":
                state = self._set_holder(Holder(kind, label, token, self._clock(), PHASE_HELD, display))
                states.append(state)
                result = {"ok": True, "token": token, "state": state}
            else:
                acquiring = Holder(kind, label, token, self._clock(), PHASE_ACQUIRING, display)
                states.append(self._set_holder(acquiring))
                reaped = self._reap(self.llm_port)
                if reaped.ok:
                    state = self._set_holder(
                        Holder(kind, label, token, self._clock(), PHASE_HELD, display))
                    states.append(state)
                    result = {"ok": True, "token": token, "state": state}
                else:
                    states.append(self._set_holder(holder))
                    result = {"ok": False, "reason": self._reason(
                        "evict_failed", reaped.error or "LLM eviction failed")}

        self._dispatch(states)
        return result

    def release_heavy(self, token: str) -> dict:
        """Release only the currently held matching token."""
        states: list[dict] = []
        with self._transition_lock:
            holder = self._read_holder()
            if holder is None or holder.token != token:
                return {"ok": False, "reason": self._reason(
                    "not_holder", "token does not hold the current heavy-work lease")}
            states.append(self._set_holder(None))
        self._dispatch(states)
        return {"ok": True}
