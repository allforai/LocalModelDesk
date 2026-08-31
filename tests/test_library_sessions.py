"""library.sessions — multi-session chat persistence tests."""

import pytest

from desk.library.errors import NotFoundError, ValidationError
from desk.library.sessions import SessionStore


def test_create_list_roundtrip_and_restart(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    first = store.create()
    second = store.create(title="配色讨论", model="qwen3")

    assert first["title"] == "新会话"
    assert first["model"] is None
    assert first["messages"] == []
    assert len(first["id"]) == 32
    assert first["created"] == first["updated"]
    assert {session["id"] for session in store.list()} == {first["id"], second["id"]}

    restarted = SessionStore(tmp_path / "sessions")
    restored_second = next(session for session in restarted.list() if session["id"] == second["id"])
    assert restored_second["title"] == "配色讨论"
    assert restored_second["model"] == "qwen3"


def test_delete_removes_file(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    session = store.create()
    path = tmp_path / "sessions" / f"{session['id']}.json"

    assert path.is_file()
    store.delete(session["id"])
    assert not path.exists()
    assert store.list() == []
    with pytest.raises(NotFoundError):
        store.delete(session["id"])


def test_list_empty_when_dir_missing(tmp_path):
    assert SessionStore(tmp_path / "sessions").list() == []


def test_update_rename_model_messages_and_persists(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    session = store.create()
    messages = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "在", "reasoning": "…"},
    ]

    updated = store.update(
        session["id"], {"title": "新名字", "model": "qwen3", "messages": messages}
    )

    assert updated["title"] == "新名字"
    assert updated["model"] == "qwen3"
    assert updated["messages"] == messages
    assert updated["created"] == session["created"]
    restored = next(
        item for item in SessionStore(tmp_path / "sessions").list() if item["id"] == session["id"]
    )
    assert restored["messages"] == messages
    assert restored["title"] == "新名字"


def test_update_unknown_key_or_bad_messages_rejected(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    session = store.create()

    with pytest.raises(ValidationError):
        store.update(session["id"], {"nope": 1})
    with pytest.raises(ValidationError):
        store.update(session["id"], {"messages": "not-a-list"})


def test_unknown_or_malformed_id_is_not_found(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    store.create()

    for invalid_id in ("0" * 32, "../../x", "zz", ""):
        with pytest.raises(NotFoundError):
            store.update(invalid_id, {"title": "x"})
        with pytest.raises(NotFoundError):
            store.delete(invalid_id)
    assert len(store.list()) == 1


def test_write_failure_keeps_old_file_intact(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    session = store.create(title="保住我")
    path = tmp_path / "sessions" / f"{session['id']}.json"
    before = path.read_bytes()

    with pytest.raises(TypeError):
        store.update(session["id"], {"messages": [object()]})

    assert path.read_bytes() == before
    assert list((tmp_path / "sessions").glob(".tmp-*")) == []


def test_corrupt_file_yields_placeholder(tmp_path):
    store = SessionStore(tmp_path / "sessions")
    session = store.create()
    (tmp_path / "sessions" / ("f" * 32 + ".json")).write_text("{oops", encoding="utf-8")

    listed = store.list()

    assert session["id"] in {item["id"] for item in listed}
    assert {"id": "f" * 32, "corrupt": True} in listed
