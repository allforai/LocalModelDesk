"""Typed exceptions for the foundation module (single error vocabulary, §2.5)."""


class FoundationError(Exception):
    """Base: machine-readable code, HTTP status, and structured payload."""

    code = "foundation_error"
    http_status = 500

    def __init__(self, message: str, **payload: object) -> None:
        super().__init__(message)
        self.message = message
        self.payload = payload


class ConfigCorruptError(FoundationError):
    code = "config_corrupt"
    http_status = 500


class ConfigInvalidError(FoundationError):
    code = "config_invalid"
    http_status = 400


class ConfigNotCorruptError(FoundationError):
    code = "config_not_corrupt"
    http_status = 409


class NotWritableError(FoundationError):
    code = "not_writable"
    http_status = 400


class LegacyRootError(FoundationError):
    code = "legacy_root_invalid"
    http_status = 400


class ModelsRootInvalidError(FoundationError):
    code = "models_root_invalid"
    http_status = 400


class ModelsRootUnrecognizedError(FoundationError):
    code = "models_root_unrecognized"
    http_status = 400


class AdoptConflictError(FoundationError):
    code = "adopt_conflict"
    http_status = 409


class InsufficientSpaceError(FoundationError):
    code = "insufficient_space"
    http_status = 409


class AdoptError(FoundationError):
    code = "adopt_failed"
    http_status = 500
