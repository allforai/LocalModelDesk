"""errors.py：拒绝异常、原因码、按路径选方言、两方言错误信封（R-gateway-09）。"""
from desk.gateway.errors import (
    ANTHROPIC,
    OPENAI,
    REASON_HEADER,
    REASON_INVALID_REQUEST,
    REASON_NO_MODEL_LOADED,
    RETRY_AFTER_SECONDS,
    GatewayReject,
    dialect_for_path,
    error_envelope,
)


def test_reject_carries_code_http_message():
    r = GatewayReject("no_model_loaded", 503, "no chat model is loaded")
    assert isinstance(r, Exception)
    assert (r.code, r.http, r.message) == ("no_model_loaded", 503, "no chat model is loaded")


def test_constants():
    assert RETRY_AFTER_SECONDS == 30
    assert REASON_HEADER == "X-LocalModelDesk-Reason"
    assert REASON_NO_MODEL_LOADED == "no_model_loaded"
    assert REASON_INVALID_REQUEST == "invalid_request"


def test_dialect_for_path():
    assert dialect_for_path("/v1/messages") == ANTHROPIC
    assert dialect_for_path("/v1/messages/count_tokens") == ANTHROPIC
    assert dialect_for_path("/v1/chat/completions") == OPENAI
    assert dialect_for_path("/v1/models") == OPENAI
    assert dialect_for_path("/no/such/path") == OPENAI


def test_openai_envelope_400():
    env = error_envelope(OPENAI, GatewayReject("invalid_request", 400, "bad body"))
    assert env == {"error": {"message": "bad body", "type": "invalid_request_error", "code": "invalid_request"}}


def test_openai_envelope_503_type():
    env = error_envelope(OPENAI, GatewayReject("no_model_loaded", 503, "nothing loaded"))
    assert env["error"]["type"] == "service_unavailable_error"
    assert env["error"]["code"] == "no_model_loaded"


def test_anthropic_envelope_503_is_overloaded():
    env = error_envelope(ANTHROPIC, GatewayReject("no_model_loaded", 503, "nothing loaded"))
    assert env == {"type": "error", "error": {"type": "overloaded_error", "message": "nothing loaded"}}


def test_anthropic_envelope_404_is_not_found():
    env = error_envelope(ANTHROPIC, GatewayReject("not_found", 404, "unknown path"))
    assert env["error"]["type"] == "not_found_error"


def test_anthropic_envelope_400():
    env = error_envelope(ANTHROPIC, GatewayReject("invalid_request", 400, "max_tokens is required"))
    assert env["error"]["type"] == "invalid_request_error"
