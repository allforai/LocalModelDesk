"""library.sessions — multi-session chat persistence tests."""

import pytest

from desk.library.errors import NotFoundError
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
