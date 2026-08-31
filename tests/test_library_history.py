"""library.history — HistoryStore tests (R-library-03 / R-library-04)."""
import json
from pathlib import Path

import pytest

from desk.library.errors import ValidationError
from desk.library.history import HistoryStore


def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(tmp_path / "history.jsonl")


def test_append_fills_id_and_ts_and_roundtrips_params(tmp_path):
    history = store(tmp_path)
    params = {"prompt": "夕阳下的猫", "steps": 12, "nested": {"a": [1, 2]}}
    entry = history.append({"kind": "video", "status": "done",
                            "output": "h3-x.mp4", "params": params})
    assert len(entry["id"]) == 32
    int(entry["id"], 16)
    assert "T" in entry["ts"]
    listed = history.list()
    assert len(listed) == 1
    assert listed[0]["params"] == params
    assert listed[0]["id"] == entry["id"]


def test_append_missing_required_field_writes_nothing(tmp_path):
    history = store(tmp_path)
    with pytest.raises(ValidationError):
        history.append({"status": "done"})
    with pytest.raises(ValidationError):
        history.append({"kind": "video"})
    assert not (tmp_path / "history.jsonl").exists()


def test_list_newest_first_with_limit(tmp_path):
    history = store(tmp_path)
    for i in range(5):
        history.append({"kind": "video", "status": "done", "n": i})
    assert [entry["n"] for entry in history.list()] == [4, 3, 2, 1, 0]
    assert [entry["n"] for entry in history.list(limit=2)] == [4, 3]


def test_list_skips_bad_lines_and_never_rewrites_file(tmp_path):
    history = store(tmp_path)
    history.append({"kind": "music", "status": "done", "n": 0})
    history_file = tmp_path / "history.jsonl"
    with open(history_file, "a", encoding="utf-8") as handle:
        handle.write("not json at all\n")
        handle.write('{"kind": "video", "status": "done", "n": 1}\n')
        handle.write('{"trunca')
    before = history_file.read_bytes()
    assert [entry["n"] for entry in history.list()] == [1, 0]
    assert history_file.read_bytes() == before
