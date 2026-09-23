"""Typed resources errors: machine-readable code plus HTTP status."""
from __future__ import annotations


class ResourceError(Exception):
    code = "resource_error"
    http_status = 500

    def __init__(self, message: str, detail: dict | None = None):
        super().__init__(message)
        self.message = message
        self.detail = detail

    def to_json(self) -> dict:
        error = {"code": self.code, "message": self.message}
        if self.detail:
            error["detail"] = self.detail
        return {"error": error}


class UnknownModelError(ResourceError):
    code = "unknown_model"
    http_status = 404


class ManifestUnavailableError(ResourceError):
    code = "manifest_unavailable"
    http_status = 503


class DownloadBusyError(ResourceError):
    code = "download_in_progress"
    http_status = 409


class MediaBusyError(ResourceError):
    code = "media_busy"
    http_status = 409


class NotDownloadingError(ResourceError):
    code = "not_downloading"
    http_status = 409


class HfCliMissingError(ResourceError):
    code = "hf_cli_missing"
    http_status = 503


class ConfirmRequiredError(ResourceError):
    code = "confirm_required"
    http_status = 400


class PathEscapeError(ResourceError):
    code = "path_escape"
    http_status = 400


class ConfigUnavailableError(ResourceError):
    """config.json 读不出来——不知道模型目录在哪，这类问题答不出来，不是"没有"。

    code 和 `desk.foundation.errors.ConfigCorruptError` 一样都是 "config_corrupt"：
    同一个原因（配置坏了）不管从哪个接口冒出来，前端只用认一种 code 去判断"该不该
    引导用户去修配置"，不必为 resources 这一片再单独学一套（R-config-corrupt-01）。
    """
    code = "config_corrupt"
    http_status = 500
