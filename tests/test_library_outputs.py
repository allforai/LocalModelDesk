"""Range planning follows RFC 7233's single-range rules."""

import pytest

from desk.library.history import HistoryStore
from desk.library.outputs import OutputsStore
from desk.library.outputs import parse_range


@pytest.mark.parametrize(
    ("size", "header", "status", "start", "length"),
    [
        (10, None, 200, 0, 10),
        (10, "items=0-1", 200, 0, 10),
        (10, "bytes=wat", 200, 0, 10),
        (10, "bytes=0-1,4-5", 200, 0, 10),
        (10, "bytes=2-20", 206, 2, 8),
        (10, "bytes=3-", 206, 3, 7),
        (10, "bytes=-3", 206, 7, 3),
        (10, "bytes=-20", 206, 0, 10),
        (10, "bytes=10-", 416, None, 0),
        (10, "bytes=-0", 416, None, 0),
        (0, "bytes=0-0", 416, None, 0),
    ],
)
def test_parse_range_rfc7233_single_range(size, header, status, start, length):
    plan = parse_range(size, header)

    assert (plan.status, plan.start, plan.length) == (status, start, length)


@pytest.mark.parametrize("header", ["bytes=6-5", "bytes=-", "bytes=--1", "bytes=+1-2"])
def test_parse_range_invalid_syntax_falls_back_to_full_file(header):
    plan = parse_range(10, header)

    assert (plan.status, plan.start, plan.length) == (200, 0, 10)


def make_stores(tmp_path):
    history = HistoryStore(tmp_path / "history.jsonl")
    root = tmp_path / "outputs"
    root.mkdir()
    return OutputsStore(root, history), root, history


def test_resolve_returns_existing_regular_file(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    (root / "h3-a.mp4").write_bytes(b"x" * 8)

    assert outputs.resolve("h3-a.mp4") == (root / "h3-a.mp4").resolve()
    assert outputs.resolve("missing.mp4") is None


def test_resolve_rejects_escapes(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    secret = tmp_path / "secret.txt"
    secret.write_text("s")
    (root / "link.mp4").symlink_to(secret)

    for name in (
        "../secret.txt",
        "/etc/passwd",
        "..",
        "a/b.mp4",
        "a\\b.mp4",
        "%2e%2e%2fsecret.txt",
        "link.mp4",
        "",
    ):
        assert outputs.resolve(name) is None, name


def test_list_joins_history_and_marks_orphans(tmp_path):
    outputs, root, history = make_stores(tmp_path)
    entry = history.append(
        {"kind": "video", "status": "done", "output": "h3-known.mp4"}
    )
    (root / "h3-known.mp4").write_bytes(b"a" * 10)
    (root / "h3-orphan.mp4").write_bytes(b"b" * 20)
    (root / "music3-orphan.wav").write_bytes(b"c" * 30)
    (root / "mystery.webm").write_bytes(b"d" * 5)
    (root / "notes.txt").write_text("skip me")
    history.append(
        {"kind": "video", "status": "done", "output": "h3-gone.mp4"}
    )

    items = {item["name"]: item for item in outputs.list()}

    assert set(items) == {
        "h3-known.mp4", "h3-orphan.mp4", "music3-orphan.wav", "mystery.webm"
    }
    assert items["h3-known.mp4"] == {
        "name": "h3-known.mp4", "kind": "video", "bytes": 10,
        "ts": entry["ts"], "orphan": False, "history_id": entry["id"],
    }
    assert items["h3-orphan.mp4"]["orphan"] is True
    assert items["h3-orphan.mp4"]["kind"] == "video"
    assert items["h3-orphan.mp4"]["history_id"] is None
    assert items["music3-orphan.wav"]["kind"] == "music"
    assert items["mystery.webm"]["kind"] == "file"
    assert items["h3-orphan.mp4"]["ts"]


def test_list_missing_root_returns_empty(tmp_path):
    history = HistoryStore(tmp_path / "history.jsonl")

    assert OutputsStore(tmp_path / "nonexistent", history).list() == []


def test_serve_full_and_range_bytes(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    payload = bytes(range(256)) * 8
    (root / "h3-a.mp4").write_bytes(payload)

    full = outputs.serve("h3-a.mp4", None)
    assert full.status == 200
    assert full.headers["Accept-Ranges"] == "bytes"
    assert full.headers["Content-Type"] == "video/mp4"
    assert full.headers["Content-Length"] == "2048"
    assert full.body.read() == payload

    part = outputs.serve("h3-a.mp4", "bytes=0-1023")
    assert part.status == 206
    assert part.headers["Content-Range"] == "bytes 0-1023/2048"
    assert part.headers["Content-Length"] == "1024"
    got = part.body.read()
    assert len(got) == 1024 and got == payload[:1024]

    tail = outputs.serve("h3-a.mp4", "bytes=-100")
    assert tail.status == 206
    assert tail.headers["Content-Range"] == "bytes 1948-2047/2048"
    assert tail.body.read() == payload[-100:]


def test_serve_content_types(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    for name, ctype in [("a.wav", "audio/wav"), ("a.m4a", "audio/mp4"),
                        ("a.webm", "video/webm")]:
        (root / name).write_bytes(b"x")
        assert outputs.serve(name, None).headers["Content-Type"] == ctype


def test_serve_unsatisfiable_and_missing(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    (root / "h3-a.mp4").write_bytes(b"x" * 10)
    response = outputs.serve("h3-a.mp4", "bytes=10-")
    assert response.status == 416
    assert response.headers["Content-Range"] == "bytes */10"
    assert outputs.serve("../h3-a.mp4", None).status == 404
    assert outputs.serve("missing.mp4", None).status == 404
