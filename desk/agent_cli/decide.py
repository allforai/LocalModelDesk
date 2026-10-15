"""What to do next, given the desk's state: wait, swap the chat model, submit, or fail (A-20/A-24/A-26)."""
from __future__ import annotations

from dataclasses import dataclass

from .errors import EXIT_MEMORY

RETRY_CODES = frozenset({"media_busy", "load_in_progress", "model_mismatch", "evicted",
                         "no_model_loaded", "job_not_running"})


@dataclass(frozen=True)
class Snapshot:
    llm_status: str
    llm_model: str | None
    active_chats: int
    ui_chat_recent: bool
    media_running: bool
    precheck: dict | None


@dataclass(frozen=True)
class Decision:
    action: str
    reason: str
    exit_code: int | None = None


def _wait(reason: str) -> Decision:
    return Decision("wait", reason)


def _releasable(precheck: dict | None) -> bool:
    return bool(precheck) and not precheck.get("ok") and bool(precheck.get("release"))


def _too_big(precheck: dict | None) -> bool:
    return bool(precheck) and not precheck.get("ok") and not precheck.get("release")


def _evicts_llm(precheck: dict | None) -> bool:
    return bool(precheck) and any(item.get("kind") == "llm" for item in precheck.get("release") or [])


def decide(op: str, want_model: str | None, snap: Snapshot) -> Decision:
    if op == "compose":
        # ffmpeg only, no arbiter (B-02): only a running media job makes it wait; no precheck is read.
        return _wait("媒体任务进行中") if snap.media_running else Decision("submit", "")
    if snap.llm_status == "loading":
        return _wait("正在加载模型")
    if op == "chat":
        if snap.llm_status == "loaded" and snap.llm_model == want_model:
            return Decision("submit", "")
        if snap.media_running:
            return _wait("媒体任务进行中")
        if snap.active_chats > 0:
            return _wait("有对话正在进行")
        if snap.ui_chat_recent and snap.llm_status == "loaded":
            return _wait("台面里最近在用当前模型对话")
        if _releasable(snap.precheck):
            return _wait("内存被占用，等待释放")
        if _too_big(snap.precheck):
            message = (snap.precheck.get("reason") or {}).get("message") or "内存不足"
            return Decision("fail", f"{message}。对话模型不能强制加载，请换一个更小的模型", EXIT_MEMORY)
        return Decision("swap", "")
    if snap.media_running:
        return _wait("媒体任务进行中")
    if snap.active_chats > 0:
        return _wait("有对话正在进行")
    if _evicts_llm(snap.precheck) and snap.ui_chat_recent:
        return _wait("生成需要卸掉对话模型，但台面里最近在用它")
    if _releasable(snap.precheck):
        return _wait("内存被占用，等待释放")
    return Decision("submit", "")
