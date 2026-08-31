"""gateway：OpenAI + Anthropic 兼容对外推理接口（纯翻译层，不加载、不排队）。"""

from .backend import GatewayBackend  # noqa: F401

from .errors import (  # noqa: F401
    REASON_HEADER,
    REASON_INVALID_REQUEST,
    REASON_MEDIA_JOB_RUNNING,
    REASON_METHOD_NOT_ALLOWED,
    REASON_MODEL_NOT_LOADED,
    REASON_NO_MODEL_LOADED,
    REASON_NOT_FOUND,
    REASON_UPSTREAM_ERROR,
    RETRY_AFTER_SECONDS,
    GatewayReject,
)
from .service import GatewayService  # noqa: F401
