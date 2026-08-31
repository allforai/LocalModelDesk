"""Admission checks for gateway chat requests; never auto-load or queue."""
from __future__ import annotations

from .errors import (
    REASON_MEDIA_JOB_RUNNING,
    REASON_MODEL_NOT_LOADED,
    REASON_NO_MODEL_LOADED,
    GatewayReject,
)


def admit(backend, requested_model):
    """Return the resident model or reject with an HTTP 503.

    A media job has priority over model state, then a model must already be
    loaded, and a supplied model must name that resident model by key or ID.
    """
    desk = backend.desk_state()
    if desk.get("media_busy"):
        code = REASON_MEDIA_JOB_RUNNING
        message = "a media job is running; the gateway never queues or evicts"
        probe = backend.can_start_heavy("llm") or {}
        reason = probe.get("reason") or {}
        if reason.get("code"):
            code = reason["code"]
            message = reason.get("message") or message
        raise GatewayReject(code, 503, message)

    status = backend.llm_status()
    loaded = status.get("loaded")
    if status.get("state") != "loaded" or not loaded:
        raise GatewayReject(
            REASON_NO_MODEL_LOADED,
            503,
            "no chat model is loaded; the gateway never auto-loads",
        )

    if requested_model and requested_model not in (loaded["key"], loaded["served_id"]):
        raise GatewayReject(
            REASON_MODEL_NOT_LOADED,
            503,
            f"requested model '{requested_model}' is not the resident model; "
            f"currently loaded: '{loaded['key']}' (served id '{loaded['served_id']}')",
        )
    return loaded
