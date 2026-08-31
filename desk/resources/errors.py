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
