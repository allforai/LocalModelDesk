"""LLM data shapes, error codes, and chat event constructors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


DEFAULT_LLM_PORT = 8767

STATUS_IDLE = "idle"
STATUS_LOADING = "loading"
STATUS_LOADED = "loaded"
STATUS_ERROR = "error"

ERR_MODEL_NOT_FOUND = "model_not_found"
ERR_MODEL_DIR_MISSING = "model_dir_missing"
ERR_MEDIA_BUSY = "media_busy"
ERR_LOAD_IN_PROGRESS = "load_in_progress"
ERR_BACKEND_EXITED = "backend_exited"
ERR_LOAD_TIMEOUT = "load_timeout"
ERR_PORT_NOT_RELEASED = "port_not_released"
ERR_EVICTED = "evicted"
ERR_NO_MODEL_LOADED = "no_model_loaded"
ERR_MODEL_MISMATCH = "model_mismatch"
ERR_UPSTREAM_ERROR = "upstream_error"


class LlmRejected(Exception):
    """A request was rejected without changing the LLM state machine."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message}


class UpstreamError(Exception):
    """A chat upstream failure."""

    def __init__(self, message: str):
        super().__init__(message)
        self.code = ERR_UPSTREAM_ERROR
        self.message = message


@dataclass(frozen=True)
class LlmError:
    code: str
    message: str
    log_tail: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "message": self.message, "log_tail": self.log_tail}


@dataclass(frozen=True)
class LlmState:
    """The ``data:llmState`` contract."""

    status: str = STATUS_IDLE
    model_key: str | None = None
    error: LlmError | None = None
    loaded_at: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "model_key": self.model_key,
            "error": self.error.to_dict() if self.error else None,
            "loaded_at": self.loaded_at,
        }


@dataclass(frozen=True)
class LoadedModel:
    """The ``data:loadedModel`` contract."""

    key: str
    name: str
    hf_repo: str
    served_id: str
    vision: bool
    quant: str | None
    params: str | None
    gb: float

    @classmethod
    def from_entry(cls, entry: Any) -> LoadedModel:
        return cls(
            key=entry.key,
            name=entry.name,
            hf_repo=entry.hf_repo,
            served_id=entry.hf_repo,
            vision=bool(entry.vision),
            quant=entry.quant,
            params=entry.params,
            gb=float(entry.gb),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "hf_repo": self.hf_repo,
            "served_id": self.served_id,
            "vision": self.vision,
            "quant": self.quant,
            "params": self.params,
            "gb": self.gb,
        }


def delta_event(text: str | None, reasoning: str | None) -> dict[str, Any]:
    return {"type": "delta", "text": text, "reasoning": reasoning}


def done_event(usage: dict, finish_reason: str) -> dict[str, Any]:
    return {"type": "done", "usage": usage, "finish_reason": finish_reason}


def error_event(code: str, message: str) -> dict[str, Any]:
    return {"type": "error", "code": code, "message": message}
