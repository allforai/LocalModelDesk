"""library.history — HistoryStore tests (R-library-03 / R-library-04)."""
import json
import subprocess
import sys
import threading
from pathlib import Path

import pytest

from desk.library.errors import ValidationError
from desk.library.history import HistoryStore
from desk.library import LibraryService


def store(tmp_path: Path) -> HistoryStore:
    return HistoryStore(tmp_path / "history.jsonl")


def test_history_module_imports_under_the_active_python():
    """The class ``list`` method must not shadow the builtin in annotations."""
    result = subprocess.run(
        [sys.executable, "-c", "import desk.library.history"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, result.stderr


class FakeRoots:
    """Minimal data:pathRoots fake; library only accesses its attributes."""

    def __init__(self, base: Path):
        self.data_root = base
        self.history_path = base / "history.jsonl"
        self.sessions_dir = base / "sessions"
        self.outputs_root = base / "outputs"


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


def test_concurrent_append_is_line_atomic(tmp_path):
    history = store(tmp_path)

    def worker():
        for _ in range(50):
            history.append({"kind": "video", "status": "done"})

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    lines = (tmp_path / "history.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 400
    ids = {json.loads(line)["id"] for line in lines}
    assert len(ids) == 400


def test_by_output_maps_filename_to_entry_and_skips_null(tmp_path):
    history = store(tmp_path)
    entry = history.append(
        {"kind": "video", "status": "done", "output": "h3-a.mp4"}
    )
    history.append({"kind": "music", "status": "failed", "output": None})

    mapping = history.by_output()

    assert set(mapping) == {"h3-a.mp4"}
    assert mapping["h3-a.mp4"]["id"] == entry["id"]


def test_service_wires_stores_end_to_end(tmp_path):
    roots = FakeRoots(tmp_path)
    roots.outputs_root.mkdir()
    svc = LibraryService(roots)
    entry = svc.append_history({"kind": "video", "status": "done", "output": "h3-a.mp4"})
    (roots.outputs_root / "h3-a.mp4").write_bytes(b"x" * 4)
    assert svc.list_history()[0]["id"] == entry["id"]
    assert svc.list_outputs()[0]["history_id"] == entry["id"]
    assert svc.serve_output("h3-a.mp4", "bytes=0-1").status == 206
    session = svc.create_chat_session(title="t")
    svc.update_chat_session(session["id"], {"model": "m"})
    assert svc.list_chat_sessions()[0]["model"] == "m"
    svc.delete_chat_session(session["id"])
    assert svc.list_chat_sessions() == []


def test_legacy_history_adopted_by_copy(tmp_path):
    roots = FakeRoots(tmp_path)
    roots.outputs_root.mkdir()
    legacy = roots.outputs_root / "history.jsonl"
    legacy_bytes = b'{"kind": "video", "status": "done", "output": "h3-old.mp4"}\n'
    legacy.write_bytes(legacy_bytes)

    svc = LibraryService(roots)

    assert roots.history_path.read_bytes() == legacy_bytes
    assert legacy.read_bytes() == legacy_bytes
    assert svc.list_history()[0]["output"] == "h3-old.mp4"


def test_legacy_adoption_is_idempotent_and_never_overwrites(tmp_path):
    roots = FakeRoots(tmp_path)
    roots.outputs_root.mkdir()
    legacy_bytes = b'{"kind": "video", "status": "done"}\n'
    (roots.outputs_root / "history.jsonl").write_bytes(legacy_bytes)
    mine = b'{"kind": "music", "status": "done"}\n'
    roots.history_path.write_bytes(mine)

    LibraryService(roots)

    assert roots.history_path.read_bytes() == mine
    assert (roots.outputs_root / "history.jsonl").read_bytes() == legacy_bytes
