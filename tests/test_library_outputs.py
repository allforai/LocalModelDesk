"""Range planning follows RFC 7233's single-range rules."""

from types import SimpleNamespace

import pytest

from desk.library.history import HistoryStore
from desk.library.http import OutputsRootMissingError, RevealFailedError
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
                        ("a.webm", "video/webm"), ("a.png", "image/png")]:
        (root / name).write_bytes(b"x")
        assert outputs.serve(name, None).headers["Content-Type"] == ctype


def test_png_history_orphan_and_sidecar_delivery(tmp_path):
    outputs, root, history = make_stores(tmp_path)
    params = dict(prompt="cat", width=1024, height=768, steps=40, seed=0)
    history.append(dict(kind="image", status="done", output="cat.png", params=params))
    (root / "cat.png").write_bytes(b"png fixture")
    (root / "orphan.PNG").write_bytes(b"png fixture")
    (root / "cat.json").write_text("{}")
    items = {item["name"]: item for item in outputs.list()}
    assert set(items) == {"cat.png", "orphan.PNG"}
    assert all(item["kind"] == "image" for item in items.values())
    assert not items["cat.png"]["orphan"]
    assert items["orphan.PNG"]["orphan"]
    assert history.list()[0]["params"] == params
    assert outputs.serve("cat.json").status == 404


def test_reveal_folder_missing_root_raises_with_code(tmp_path):
    """issue #12: a fresh install has no outputs dir yet; reveal must not claim success."""
    history = HistoryStore(tmp_path / "history.jsonl")
    outputs = OutputsStore(tmp_path / "nonexistent-outputs", history)
    calls = []
    outputs.set_opener(lambda argv, **kw: calls.append(argv))

    with pytest.raises(OutputsRootMissingError) as caught:
        outputs.reveal(None)

    assert caught.value.code == "outputs_root_missing"
    assert not calls, "the opener must never run when the root does not exist"


def test_reveal_folder_opener_nonzero_raises_with_code(tmp_path):
    """issue #12: `open` failing silently (check=False, return value dropped) must not be a 200."""
    outputs, root, _ = make_stores(tmp_path)
    outputs.set_opener(lambda argv, **kw: SimpleNamespace(returncode=1))

    with pytest.raises(RevealFailedError) as caught:
        outputs.reveal(None)

    assert caught.value.code == "reveal_failed"


def test_reveal_file_opener_nonzero_raises_with_code(tmp_path):
    """The named-file reveal path (`open -R`) gets the same exit-code check as the folder path."""
    outputs, root, _ = make_stores(tmp_path)
    (root / "h3-a.mp4").write_bytes(b"x")
    outputs.set_opener(lambda argv, **kw: SimpleNamespace(returncode=1))

    with pytest.raises(RevealFailedError) as caught:
        outputs.reveal("h3-a.mp4")

    assert caught.value.code == "reveal_failed"


def test_reveal_succeeds_when_opener_reports_zero_or_nothing(tmp_path):
    """A real subprocess.run() result (returncode 0) and a bare test double (returns None) both pass."""
    outputs, root, _ = make_stores(tmp_path)

    outputs.set_opener(lambda argv, **kw: SimpleNamespace(returncode=0))
    assert outputs.reveal(None) == root

    calls = []
    outputs.set_opener(lambda argv, **kw: calls.append(argv))
    assert outputs.reveal(None) == root
    assert calls == [["open", str(root)]]


def test_serve_unsatisfiable_and_missing(tmp_path):
    outputs, root, _ = make_stores(tmp_path)
    (root / "h3-a.mp4").write_bytes(b"x" * 10)
    response = outputs.serve("h3-a.mp4", "bytes=10-")
    assert response.status == 416
    assert response.headers["Content-Range"] == "bytes */10"
    assert outputs.serve("../h3-a.mp4", None).status == 404
    assert outputs.serve("missing.mp4", None).status == 404
