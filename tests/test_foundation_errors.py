import pytest

from desk.foundation import errors


CASES = [
    (errors.ConfigCorruptError, "config_corrupt", 500),
    (errors.NotWritableError, "not_writable", 400),
    (errors.LegacyRootError, "legacy_root_invalid", 400),
    (errors.AdoptConflictError, "adopt_conflict", 409),
    (errors.InsufficientSpaceError, "insufficient_space", 409),
    (errors.AdoptError, "adopt_failed", 500),
    (errors.ModelsRootInvalidError, "models_root_invalid", 400),
]


@pytest.mark.parametrize("cls,code,status", CASES)
def test_error_carries_code_status_payload(cls, code, status):
    err = cls("boom", extra=1)
    assert isinstance(err, errors.FoundationError)
    assert err.code == code
    assert err.http_status == status
    assert err.payload == {"extra": 1}
    assert err.message == "boom"
    assert str(err) == "boom"


def test_space_error_payload_names():
    err = errors.InsufficientSpaceError(
        "short", needed_bytes=10, free_bytes=4, shortfall_bytes=6)
    assert err.payload == {"needed_bytes": 10, "free_bytes": 4, "shortfall_bytes": 6}


def test_catchable_as_foundation_error():
    with pytest.raises(errors.FoundationError):
        raise errors.AdoptError("x", adopted=[], remaining=["llms"])
