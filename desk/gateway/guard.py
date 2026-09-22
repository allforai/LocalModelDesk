"""Admission checks for gateway chat requests; never auto-load or queue."""
from __future__ import annotations

from ..arbiter.state import still_holds
from .errors import (
    REASON_MEDIA_JOB_RUNNING,
    REASON_MODEL_NOT_LOADED,
    REASON_NO_MODEL_LOADED,
    GatewayReject,
)


def admit(backend, requested_model):
    """Return the resident model or reject with an HTTP 503.

    A model must already be loaded, the desk must still hold it, and a supplied
    model must name that resident model by key or ID.

    「台面还持有它吗」不是「有没有媒体作业在跑」：预算模式下两者可以共存，而共存
    的安全性在授予那一刻就算过了（聊天的满窗 KV 已经报进 `fits()`）。再拦一道是
    互斥时代的遗留，它让共存只剩「省一次加载」。
    """
    status = backend.llm_status()
    loaded = status.get("loaded")
    if status.get("state") != "loaded" or not loaded:
        raise GatewayReject(
            REASON_NO_MODEL_LOADED,
            503,
            "no chat model is loaded; the gateway never auto-loads",
        )

    if not still_holds(backend.desk_state(), "llm", loaded["key"]):
        code = REASON_MEDIA_JOB_RUNNING
        message = "the desk no longer holds this model; the gateway never queues or evicts"
        probe = backend.can_start_heavy("llm") or {}
        reason = probe.get("reason") or {}
        if reason.get("code"):
            code = reason["code"]
            message = reason.get("message") or message
        raise GatewayReject(code, 503, message)

    if requested_model and requested_model not in (loaded["key"], loaded["served_id"]):
        raise GatewayReject(
            REASON_MODEL_NOT_LOADED,
            503,
            f"requested model '{requested_model}' is not the resident model; "
            f"currently loaded: '{loaded['key']}' (served id '{loaded['served_id']}')",
        )
    return loaded
