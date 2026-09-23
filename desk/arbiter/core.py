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
        if kind in MEDIA_KINDS:
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

    def _capacity_bytes(self) -> int:
        """判共存用的分母：这台机器能给重活多少（R-budget-16）。

        **整个系统只许有一个分母。** 预算给每件重活定额度时用的是机器自报的静态能力，
        这里判「装不装得下」必须用同一个数——否则模型会拿到一个按 107.5 GiB 尺寸算出的
        KV 额度，再被此刻只剩 61 GiB 的现实拒掉，结果是任何模型都加载不了。
        （真机上撞到过；当时单测全绿，因为夹具喂的两个数恰好一致。）

        问不出机器能力时退回可用内存：保守，且不会让台面整个不可用。
        """
        capacity = getattr(self._budget, "capacity_bytes", lambda: None)()
        if capacity:
            return int(capacity)
        return self._memory.snapshot().available_bytes

    def _decide(self, kind, params, key):
        """Snapshot current holders (briefly under `_state_lock`) then decide."""
        available_bytes = self._capacity_bytes()
        with self._state_lock:
            holders = tuple(self._holders.values())
            resident = tuple(
                w for h in holders if (w := self._workloads.get(h.token)) is not None
            )
        decision, workload, holder = self._decide_from(
            kind, params, key, holders, resident, available_bytes)
        return decision, workload, resident, available_bytes, holder

    # ---- state mutation (holds _state_lock only) -----------------------
    def _grant(self, token: str, holder: Holder, workload, available_bytes: int) -> dict:
        with self._state_lock:
            self._holders[token] = holder
            if workload is not None:
                self._workloads[token] = workload
            holders = tuple(self._holders.values())
        return self._state_for(holders)

    def _replace_all(self, holder: Holder | None) -> dict:
        """Legacy single-slot replace: only the no-budget eviction path uses this."""
        with self._state_lock:
            self._holders = {} if holder is None else {holder.token: holder}
            self._workloads = {}
            holders = tuple(self._holders.values())
        return self._state_for(holders)

    def _begin_eviction(self, acquiring: Holder) -> dict:
        """移除要被让出的那些持有者，把 `acquiring` 放上台；返回新状态与回滚材料。

        legacy 模式整张台子换人（单槽语义，原样保留）；budget 模式只移除聊天持有者，
        因为那里可能有别的重活正在共存，而它们的进程不归这次让出管。
        """
        with self._state_lock:
            if self._budget is None:
                undo = (dict(self._holders), dict(self._workloads))
                self._holders, self._workloads = {acquiring.token: acquiring}, {}
            else:
                undo = (dict(self._holders), dict(self._workloads))
                for token in [t for t, h in self._holders.items() if h.kind == "llm"]:
                    self._holders.pop(token, None)
                    self._workloads.pop(token, None)
                self._holders[acquiring.token] = acquiring
            holders = tuple(self._holders.values())
        return {"state": self._state_for(holders), "undo": undo}

    def _restore_eviction(self, undo) -> dict:
        """让出失败时把台账放回让出之前的样子。"""
        holders, workloads = undo
        with self._state_lock:
            self._holders, self._workloads = dict(holders), dict(workloads)
            current = tuple(self._holders.values())
        return self._state_for(current)

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

"""
        available_bytes = self._capacity_bytes()

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
            # `holder` 是"主"持有者（最后授予的那件），界面用它显示「当前在干什么」。
            # `holders` 是全部——预算模式下真的可能有两件共存，而消费者若只看
            # `holder` 就会把「别人也拿到了」误读成「我被驱逐了」：真机上聊天模型
            # 正是这样在视频作业授予的瞬间自己拆了自己（service.py::_on_desk_state）。
            "holder": self._public_holder(primary),
            "holders": [h.public_view() for h in holders],
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
                if self._should_evict_llm(decision, workload, resident, available_bytes):
                    # 查询与授予必须给同一个答案。`acquire_heavy` 在「最小让出只需卸
                    # 聊天模型」时会自动让出并授予；查询若还答「不行」，调用方看到
                    # 拒绝就当场退出，后面那半永远走不到——真机上「挂着聊天模型开
                    # 视频」正是这样被堵死的，而自动让出的单测一直绿着，因为它们
                    # 直接调授予，绕过了真实调用顺序里的这道问询。
                    # `release` 同时说明代价：界面据此讲「会先卸掉聊天模型」。
                    return {"ok": True, "reason": None, "memory_warning": None, "release": release}
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
        module docstring.

        R-budget-13 的判据是「这次调用有没有给出容量输入」，和 can_start_heavy 那边
        同一条，只是答案相反：查询没有容量输入时只回答归属，**授予**没有容量输入时
        必须拒绝。`_cost` 拿不到 params/key 只能产出 bytes_needed=0、
        source=unavailable 的空壳；空壳若恰好是当下唯一一件，`fits` 会判它装得下并
        授予，`_workloads` 里从此多出一个 0 字节的幽灵持有者，往后每一次 `fits`
        都把它整件漏算。两个生产调用点（desk/llm/service.py、desk/media/service.py）
        今天都传了参数，但防线要在 arbiter 里，不在调用点——本支刚修掉的正是这类
        「查询与授予各有一套判据」的不对称。"""
        if self._budget is not None and params is None and key is None:
            return {"ok": False, "reason": self._reason(
                "capacity_unknown",
                f"授予 {kind} 需要作业参数才算得出内存开销；这次调用没有给出，不予授予")}

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
                # evict_then_grant。两种模式都会走到这里：legacy 的转移表产生它，
                # budget 模式在「最小让出恰好只需卸聊天模型」时也产生它
                # （见 _should_evict_llm）。区别在于清掉谁——
                #   legacy 是单槽语义，整张台子换人；
                #   budget 下可能有两件重活共存，只该移除被让出的那一件。整个清空
                #   会把并发的媒体作业也从台账上抹掉，而它的进程还在跑：token 再也
                #   释放不掉、media_busy 变 false、它占的内存不再计入预算，
                #   后续判定于是放行过量的重活。
                acquiring = Holder(kind, label, token, self._clock(), PHASE_ACQUIRING, display)
                evicted = self._begin_eviction(acquiring)
                states.append(evicted["state"])
                reaped = self._reap(self.llm_port)
                if reaped.ok:
                    state = self._grant(token, Holder(kind, label, token, self._clock(), PHASE_HELD, display),
                                         workload, available_bytes)
                    states.append(state)
                    result = {"ok": True, "token": token, "state": state}
                else:
                    states.append(self._restore_eviction(evicted["undo"]))
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
                holders = tuple(self._holders.values())
            if not found:
                return {"ok": False, "reason": self._reason(
                    "not_holder", "token does not hold the current heavy-work lease")}
            states.append(self._state_for(holders))
        self._dispatch(states)
        return {"ok": True}
