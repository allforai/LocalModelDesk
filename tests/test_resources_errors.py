import pytest

from desk.resources.errors import (
    ConfirmRequiredError,
    DownloadBusyError,
    HfCliMissingError,
    ManifestUnavailableError,
    MediaBusyError,
    NotDownloadingError,
    PathEscapeError,
    ResourceError,
    UnknownModelError,
)


def test_error_codes_and_http_status():
    cases = [
        (UnknownModelError, "unknown_model", 404),
        (ManifestUnavailableError, "manifest_unavailable", 503),
        (DownloadBusyError, "download_in_progress", 409),
        (MediaBusyError, "media_busy", 409),
        (NotDownloadingError, "not_downloading", 409),
        (HfCliMissingError, "hf_cli_missing", 503),
        (ConfirmRequiredError, "confirm_required", 400),
        (PathEscapeError, "path_escape", 400),
    ]
    for cls, code, status in cases:
        err = cls("boom")
        assert isinstance(err, ResourceError)
        assert err.code == code
        assert err.http_status == status


def test_to_json_envelope_with_detail():
    err = MediaBusyError(
        "busy", detail={"code": "media_busy", "message": "video running"}
    )
    assert err.to_json() == {
        "error": {
            "code": "media_busy",
            "message": "busy",
            "detail": {"code": "media_busy", "message": "video running"},
        }
    }


def test_to_json_without_detail_omits_key():
    assert UnknownModelError("nope").to_json() == {
        "error": {"code": "unknown_model", "message": "nope"}
    }


def test_errors_are_raisable():
    with pytest.raises(ResourceError):
        raise DownloadBusyError("x")
