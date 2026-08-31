"""Gateway rejection vocabulary and dialect-native error envelopes."""
from __future__ import annotations

REASON_MEDIA_JOB_RUNNING = "media_job_running"
REASON_NO_MODEL_LOADED = "no_model_loaded"
REASON_MODEL_NOT_LOADED = "model_not_loaded"
REASON_INVALID_REQUEST = "invalid_request"
REASON_NOT_FOUND = "not_found"
REASON_METHOD_NOT_ALLOWED = "method_not_allowed"
REASON_UPSTREAM_ERROR = "upstream_error"

RETRY_AFTER_SECONDS = 30
REASON_HEADER = "X-LocalModelDesk-Reason"

OPENAI = "openai"
ANTHROPIC = "anthropic"

_OPENAI_TYPE_BY_HTTP = {
    400: "invalid_request_error",
    404: "invalid_request_error",
    405: "invalid_request_error",
    500: "api_error",
    503: "service_unavailable_error",
}
_ANTHROPIC_TYPE_BY_HTTP = {
    400: "invalid_request_error",
    404: "not_found_error",
    405: "invalid_request_error",
    500: "api_error",
    503: "overloaded_error",
}


class GatewayReject(Exception):
    """A rejected request with a machine-readable reason and HTTP status."""

    def __init__(self, code: str, http: int, message: str):
        super().__init__(message)
        self.code = code
        self.http = http
        self.message = message


def dialect_for_path(path: str) -> str:
    """Select Anthropic envelopes for /v1/messages routes, OpenAI otherwise."""
    if path == "/v1/messages" or path.startswith("/v1/messages/"):
        return ANTHROPIC
    return OPENAI


def error_envelope(dialect: str, reject: GatewayReject) -> dict:
    """Return a dialect-native error payload for a request rejection."""
    if dialect == ANTHROPIC:
        return {
            "type": "error",
            "error": {
                "type": _ANTHROPIC_TYPE_BY_HTTP.get(reject.http, "api_error"),
                "message": reject.message,
            },
        }
    return {
        "error": {
            "message": reject.message,
            "type": _OPENAI_TYPE_BY_HTTP.get(reject.http, "api_error"),
            "code": reject.code,
        }
    }
