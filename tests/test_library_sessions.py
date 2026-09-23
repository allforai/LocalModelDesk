"""library.sessions — multi-session chat persistence tests."""

import tempfile
from pathlib import Path

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


def test_list_ignores_the_half_written_temp_file(tmp_path):
    """写入窗口内 list() 不该返回幽灵损坏会话（keep-code-simple F5）。

    `_write` 的临时文件叫 `.tmp-XXXX.json`，而 `list()` 用 glob("*.json") ——
    实测 pathlib 的 glob **会**匹配点开头的 .tmp-XXXX.json。于是并发读时会读到
    空的或半写的文件，被记成 {"id": ".tmp-XXXX", "corrupt": True} 混进列表。
    """
    store = SessionStore(tmp_path / "sessions")
    real = store.create(title="真会话")
    # 模拟写入窗口：一个刚 mkstemp 出来、还没 os.replace 的空临时文件
    (tmp_path / "sessions" / ".tmp-abcd1234.json").write_text("", encoding="utf-8")

    listed = store.list()

    assert [s["id"] for s in listed] == [real["id"]], f"临时文件混进了会话列表：{listed}"
    assert not any(s.get("corrupt") for s in listed)


def test_a_genuinely_corrupt_session_is_still_reported(tmp_path):
    """反向：真正损坏的会话文件仍要报出来，不能被上面的修法一起滤掉。"""
    store = SessionStore(tmp_path / "sessions")
    (tmp_path / "sessions").mkdir(parents=True, exist_ok=True)
    (tmp_path / "sessions" / "broken.json").write_text("{not json", encoding="utf-8")

    listed = store.list()

    assert listed == [{"id": "broken", "corrupt": True}]


def test_the_write_temp_file_is_not_named_like_a_session(tmp_path):
    """两道防护各自要能独立咬住：这条盯的是临时文件名本身。

    list() 的「点开头跳过」能兜住残留，但它盖住了后缀这一半——撤掉 .part 改回
    .json 时上面那条测试并不会红。临时名不以 .json 结尾是独立的一道：任何别的
    读取方（备份、外部工具、未来某个不跳点文件的 glob）都不该把它当成会话。
    """
    store = SessionStore(tmp_path / "sessions")
    seen = []
    original = tempfile.mkstemp

    def spy(*args, **kwargs):
        fd, path = original(*args, **kwargs)
        seen.append(Path(path).name)
        return fd, path

    tempfile.mkstemp = spy
    try:
        store.create(title="写一条")
    finally:
        tempfile.mkstemp = original

    assert seen, "create 没有走 mkstemp"
    assert not any(name.endswith(".json") for name in seen), \
        f"临时文件名以 .json 结尾，会被任何 glob('*.json') 的读取方当成会话：{seen}"


def test_a_new_session_starts_with_no_skills_selected(tmp_path):
    from desk.library.sessions import SessionStore
    session = SessionStore(tmp_path).create()
    assert session["skills"] == []


def test_selection_survives_a_patch_and_a_reload(tmp_path):
    """选中状态是会话级的（R-skill-15）：附件勾选不写回 skill 目录——自带目录是只读的。"""
    from desk.library.sessions import SessionStore
    store = SessionStore(tmp_path)
    session = store.create()
    picked = [{"name": "code-review", "attachments": ["DEEPENING.md"]}]
    store.update(session["id"], {"skills": picked})
    reloaded = next(x for x in SessionStore(tmp_path).list() if x["id"] == session["id"])
    assert reloaded["skills"] == picked


def test_skills_must_be_a_list(tmp_path):
    import pytest
    from desk.library.errors import ValidationError
    from desk.library.sessions import SessionStore
    store = SessionStore(tmp_path)
    session = store.create()
    with pytest.raises(ValidationError):
        store.update(session["id"], {"skills": "code-review"})
