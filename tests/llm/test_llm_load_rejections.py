"""Load-request rejections leave the current LLM state untouched."""
import pytest

from desk.llm.state import (
    ERR_KEY_REQUIRED,
    ERR_LOAD_IN_PROGRESS,
    ERR_MEDIA_BUSY,
    ERR_MODEL_DIR_MISSING,
    ERR_MODEL_NOT_FOUND,
    LlmRejected,
)
from tests.llm.llm_fakes import make_entry, make_service


def assert_rejected_without_state_change(service, key, code):
    before = service.status()

    with pytest.raises(LlmRejected) as raised:
        service.load(key)

    assert raised.value.code == code
    assert service.status() == before


def test_load_rejects_missing_catalog_model_without_state_change(tmp_path):
    testbed = make_service(tmp_path)

    assert_rejected_without_state_change(testbed.service, "missing", ERR_MODEL_NOT_FOUND)
    assert testbed.calls == []


@pytest.mark.parametrize("bad_key", [None, "", "   ", 123, {"key": "glm"}, ["glm"]])
def test_load_rejects_missing_or_non_string_key_before_any_lookup(tmp_path, bad_key):
    """issue #5: 缺 key/非字符串 key 必须先被参数校验拦下，不能落到「目录里查不到」的 404。"""
    testbed = make_service(tmp_path)

    assert_rejected_without_state_change(testbed.service, bad_key, ERR_KEY_REQUIRED)
    assert testbed.calls == []


def test_load_rejects_missing_model_directory_without_state_change(tmp_path):
    entry = make_entry(relpath="not-downloaded")
    testbed = make_service(tmp_path, entries=[entry])
    (testbed.paths.models_root / entry.relpath).rmdir()

    assert_rejected_without_state_change(testbed.service, entry.key, ERR_MODEL_DIR_MISSING)
    assert testbed.calls == []


def test_load_rejects_media_busy_without_state_change(tmp_path):
    testbed = make_service(
        tmp_path,
        arbiter_kw={"acquire_result": {"ok": False, "reason": {"code": ERR_MEDIA_BUSY}}},
    )

    assert_rejected_without_state_change(testbed.service, "glm", ERR_MEDIA_BUSY)
    assert [call[0] for call in testbed.calls] == ["acquire"]


def test_load_rejection_keeps_arbiter_reason_code(tmp_path):
    testbed = make_service(
        tmp_path,
        arbiter_kw={
            "acquire_result": {
                "ok": False,
                "reason": {"code": "evict_failed", "message": "LLM eviction failed"},
            }
        },
    )

    assert_rejected_without_state_change(testbed.service, "glm", "evict_failed")


def test_load_rejects_when_another_load_is_in_progress_without_state_change(tmp_path):
    testbed = make_service(tmp_path, backend_kw={"health_script": [False]})
    testbed.backend.hold_health = True
    testbed.service.load("glm")

    assert_rejected_without_state_change(testbed.service, "glm", ERR_LOAD_IN_PROGRESS)

    testbed.backend.health_release.set()
    assert testbed.service.wait_settled()["status"] == "loaded"
