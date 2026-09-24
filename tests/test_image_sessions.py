"""Image sessions: the file store and its /api/image-sessions routes, on a real filesystem."""
import json
import re
import threading
from pathlib import Path

import pytest

from desk.library import LibraryService
from desk.library.errors import NotFoundError, ValidationError
from desk.library.http import LibRequest, routes
from desk.library.image_sessions import ImageSessionStore, auto_title


class FakeRoots:
    def __init__(self, base: Path):
        self.data_root = base
        self.history_path = base / "history.jsonl"
        self.sessions_dir = base / "sessions"
        self.image_sessions_dir = base / "image-sessions"
        self.outputs_root = base / "outputs"


def make_library(tmp_path):
    roots = FakeRoots(tmp_path)
    roots.outputs_root.mkdir(parents=True, exist_ok=True)
    return LibraryService(roots), roots


def store(tmp_path) -> ImageSessionStore:
    return ImageSessionStore(tmp_path / "image-sessions", tmp_path / "outputs")


def params(prompt="一只橘猫", seed=1, **extra):
    return {"prompt": prompt, "width": 1024, "height": 1024, "steps": 40, "seed": seed, **extra}


def begin(sessions, session_id, prompt="一只橘猫", seed=1, attempt_id=None, job_id=1):
    attempt_id = attempt_id or f"{job_id:032x}"
    assert sessions.begin_attempt(session_id, {"id": attempt_id, "job_id": job_id,
                                               "params": params(prompt, seed)})
    return attempt_id


def raw(sessions_dir: Path, session_id: str) -> dict:
    return json.loads((sessions_dir / f"{session_id}.json").read_text(encoding="utf-8"))


TS = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d$")


# ---- storage layout (D-01, D-02, D-04, D-10) ---------------------------------

def test_create_writes_one_json_file_per_session_in_its_own_directory(tmp_path):
    sessions = store(tmp_path)
    created = sessions.create()
    assert re.fullmatch(r"[0-9a-f]{32}", created["id"])
    assert created["title"] == "新会话" and created["title_auto"] is True
    assert created["attempts"] == []
    assert TS.match(created["created"]) and created["created"] == created["updated"]
    assert [p.name for p in (tmp_path / "image-sessions").iterdir()] == [f"{created['id']}.json"]
    assert raw(tmp_path / "image-sessions", created["id"]) == created


def test_image_and_chat_sessions_do_not_see_each_other(tmp_path):
    library, roots = make_library(tmp_path)
    image = library.create_image_session()
    chat = library.create_chat_session("chat")
    assert [s["id"] for s in library.list_chat_sessions()] == [chat["id"]]
    assert [s["id"] for s in library.list_image_sessions()] == [image["id"]]
    assert roots.image_sessions_dir != roots.sessions_dir


def test_list_is_summary_sorted_by_updated_with_corrupt_last(tmp_path):
    sessions = store(tmp_path)
    (tmp_path / "outputs").mkdir()
    older = sessions.create()
    newer = sessions.create()
    first = begin(sessions, older["id"], job_id=1)
    sessions.settle_attempt(older["id"], first, "done", "a.png")
    begin(sessions, older["id"], job_id=2)
    # make "newer" the most recently updated, deterministically
    data = raw(tmp_path / "image-sessions", newer["id"])
    data["updated"] = "2999-01-01T00:00:00"
    (tmp_path / "image-sessions" / f"{newer['id']}.json").write_text(json.dumps(data), "utf-8")
    (tmp_path / "image-sessions" / ("b" * 32 + ".json")).write_text("{not json", "utf-8")
    (tmp_path / "image-sessions" / ".tmp-abc.part").write_text("half", "utf-8")
    (tmp_path / "image-sessions" / ".tmp-old.json").write_text("half", "utf-8")

    listed = sessions.list()
    assert [item["id"] for item in listed] == [newer["id"], older["id"], "b" * 32]
    assert listed[1] == {
        "id": older["id"], "title": "一只橘猫", "created": older["created"],
        "updated": listed[1]["updated"], "attempt_count": 2, "running": True, "cover": "a.png",
    }
    assert listed[0]["attempt_count"] == 0 and listed[0]["running"] is False and listed[0]["cover"] is None
    assert listed[2] == {"id": "b" * 32, "corrupt": True}


def test_list_without_directory_is_empty(tmp_path):
    assert store(tmp_path).list() == []


# ---- titles (D-11, D-12, D-13) -------------------------------------------------

def test_auto_title_collapses_whitespace_and_truncates_at_24():
    assert auto_title("  一只\n橘猫\t 坐在窗边  ") == "一只 橘猫 坐在窗边"
    long = "一只橘猫坐在窗边，午后阳光，细腻的水彩插画，暖色调，柔和光影"
    assert auto_title(long) == long[:24] + "…"
    assert auto_title("x" * 24) == "x" * 24


def test_first_attempt_sets_title_and_later_attempts_do_not(tmp_path):
    sessions = store(tmp_path)
    session_id = sessions.create()["id"]
    first = begin(sessions, session_id, prompt="第一次的提示词", job_id=1)
    sessions.settle_attempt(session_id, first, "failed", error={"code": "exit_nonzero", "message": "exit 1"})
    begin(sessions, session_id, prompt="第二次完全不同", job_id=2)
    assert sessions.get(session_id)["title"] == "第一次的提示词"


def test_rename_stops_auto_titles(tmp_path):
    sessions = store(tmp_path)
    session_id = sessions.create()["id"]
    renamed = sessions.rename(session_id, "  我的猫  ")
    assert renamed["title"] == "我的猫" and renamed["title_auto"] is False
    begin(sessions, session_id, prompt="不会变成标题")
    assert sessions.get(session_id)["title"] == "我的猫"


@pytest.mark.parametrize("title", ["", "   ", "x" * 81, None, 5])
def test_rename_rejects_bad_titles_and_leaves_file_unchanged(tmp_path, title):
    sessions = store(tmp_path)
    session_id = sessions.create()["id"]
    before = (tmp_path / "image-sessions" / f"{session_id}.json").read_bytes()
    with pytest.raises(ValidationError, match="标题须为 1–80 个字"):
        sessions.rename(session_id, title)
    assert (tmp_path / "image-sessions" / f"{session_id}.json").read_bytes() == before


def test_rename_accepts_80_characters(tmp_path):
    sessions = store(tmp_path)
    session_id = sessions.create()["id"]
    assert sessions.rename(session_id, "字" * 80)["title"] == "字" * 80


# ---- attempts: append-only, settle rules (D-06..D-09, D-24) -------------------------

def test_attempts_append_in_order_with_complete_fields(tmp_path):
    sessions = store(tmp_path)
    (tmp_path / "outputs").mkdir()
    (tmp_path / "outputs" / "one.png").write_bytes(b"png")
    session_id = sessions.create()["id"]
    a1 = begin(sessions, session_id, seed=11, job_id=1)
    running = sessions.get(session_id)["attempts"][0]
    assert running == {"id": a1, "job_id": 1, "ts": running["ts"], "finished": None, "status": "running",
                       "params": params(seed=11), "output": None, "error": None, "base": None}
    assert sessions.settle_attempt(session_id, a1, "done", "one.png")
    a2 = begin(sessions, session_id, seed=11, job_id=2)
    assert sessions.settle_attempt(session_id, a2, "failed", error={"code": "exit_nonzero", "message": "exit 1",
                                                                    "log_tail": "boom"})
    a3 = begin(sessions, session_id, seed=12, job_id=3)
    assert sessions.settle_attempt(session_id, a3, "cancelled", error={"code": "cancelled", "message": "m"})

    got = sessions.get(session_id)["attempts"]
    assert [a["id"] for a in got] == [a1, a2, a3]
    assert [a["status"] for a in got] == ["done", "failed", "cancelled"]
    assert got[0]["output"] == "one.png" and got[0]["error"] is None and got[0]["output_missing"] is False
    assert got[1]["output"] is None and got[1]["error"]["log_tail"] == "boom"
    assert got[2]["output"] is None and got[2]["error"]["code"] == "cancelled"
    assert all(TS.match(a["finished"]) for a in got)
    assert [a["params"]["seed"] for a in got] == [11, 11, 12]
    assert "output_missing" not in json.dumps(raw(tmp_path / "image-sessions", session_id))


def test_output_missing_marks_done_attempts_whose_file_is_gone(tmp_path):
    sessions = store(tmp_path)
    session_id = sessions.create()["id"]
    attempt_id = begin(sessions, session_id)
    sessions.settle_attempt(session_id, attempt_id, "done", "gone.png")
    assert sessions.get(session_id)["attempts"][0]["output_missing"] is True


def test_settle_only_changes_running_attempts(tmp_path):
    sessions = store(tmp_path)
    session_id = sessions.create()["id"]
    attempt_id = begin(sessions, session_id)
    assert sessions.settle_attempt(session_id, attempt_id, "done", "x.png")
    assert not sessions.settle_attempt(session_id, attempt_id, "failed", error={"code": "c", "message": "m"})
    assert not sessions.settle_attempt(session_id, "f" * 32, "done", "y.png")
    assert not sessions.settle_attempt("0" * 32, attempt_id, "done", "y.png")
    assert sessions.get(session_id)["attempts"][0]["status"] == "done"
    with pytest.raises(ValueError):
        sessions.settle_attempt(session_id, attempt_id, "running")


def test_begin_on_missing_or_corrupt_session_returns_false_without_writing(tmp_path):
    sessions = store(tmp_path)
    assert sessions.begin_attempt("0" * 32, {"id": "a" * 32, "job_id": 1, "params": params()}) is False
    corrupt = tmp_path / "image-sessions" / ("c" * 32 + ".json")
    corrupt.parent.mkdir(parents=True, exist_ok=True)
    corrupt.write_text("[1, 2]", "utf-8")
    assert sessions.begin_attempt("c" * 32, {"id": "a" * 32, "job_id": 1, "params": params()}) is False
    assert corrupt.read_text("utf-8") == "[1, 2]"
    assert sorted(p.name for p in corrupt.parent.iterdir()) == [corrupt.name]


# ---- restart recovery (D-25) ------------------------------------------------------

def test_recover_running_settles_leftovers_as_interrupted(tmp_path):
    sessions = store(tmp_path)
    first, second = sessions.create()["id"], sessions.create()["id"]
    done = begin(sessions, first, job_id=1)
    sessions.settle_attempt(first, done, "done", "a.png")
    stale_1 = begin(sessions, first, job_id=2)
    stale_2 = begin(sessions, second, job_id=3)

    assert store(tmp_path).recover_running() == 2
    for session_id, attempt_id in ((first, stale_1), (second, stale_2)):
        attempt = next(a for a in sessions.get(session_id)["attempts"] if a["id"] == attempt_id)
        assert attempt["status"] == "failed" and TS.match(attempt["finished"]) and attempt["output"] is None
        assert attempt["error"] == {"code": "interrupted", "message": "应用在生成途中关闭，这次没有完成"}
    assert sessions.get(first)["attempts"][0]["status"] == "done"
    assert store(tmp_path).recover_running() == 0


def test_library_startup_recovers_running_attempts(tmp_path):
    library, _ = make_library(tmp_path)
    session_id = library.create_image_session()["id"]
    begin(library.image_sessions, session_id)
    restarted, _ = make_library(tmp_path)
    [attempt] = restarted.get_image_session(session_id)["attempts"]
    assert attempt["status"] == "failed" and attempt["error"]["code"] == "interrupted"
    assert not any(s["running"] for s in restarted.list_image_sessions())


# ---- delete semantics (D-30, D-31) -----------------------------------------------

def test_delete_removes_only_the_session_file(tmp_path):
    library, roots = make_library(tmp_path)
    session_id = library.create_image_session()["id"]
    attempt_id = begin(library.image_sessions, session_id)
    (roots.outputs_root / "qwen-image-1.png").write_bytes(b"png")
    library.image_sessions.settle_attempt(session_id, attempt_id, "done", "qwen-image-1.png")
    library.append_history({"kind": "image", "status": "done", "output": "qwen-image-1.png",
                            "session_id": session_id, "attempt_id": attempt_id})
    handlers = {(m, p): h for m, p, h in routes(library)}
    outputs_before = handlers[("GET", "/api/outputs")](LibRequest()).body
    history_before = handlers[("GET", "/api/history")](LibRequest()).body
    files_before = sorted(p.name for p in roots.outputs_root.iterdir())
    history_bytes = roots.history_path.read_bytes()

    library.delete_image_session(session_id)

    assert not (roots.image_sessions_dir / f"{session_id}.json").exists()
    assert handlers[("GET", "/api/outputs")](LibRequest()).body == outputs_before
    assert handlers[("GET", "/api/history")](LibRequest()).body == history_before
    assert sorted(p.name for p in roots.outputs_root.iterdir()) == files_before
    assert roots.history_path.read_bytes() == history_bytes
    served = library.serve_output("qwen-image-1.png")
    assert served.status == 200
    with pytest.raises(NotFoundError):
        library.delete_image_session(session_id)


def test_running_attempt_session_can_be_deleted_and_late_settle_is_dropped(tmp_path):
    sessions = store(tmp_path)
    session_id = sessions.create()["id"]
    attempt_id = begin(sessions, session_id)
    sessions.delete(session_id)
    assert sessions.settle_attempt(session_id, attempt_id, "done", "x.png") is False
    assert not (tmp_path / "image-sessions" / f"{session_id}.json").exists()


def test_corrupt_session_can_still_be_deleted(tmp_path):
    sessions = store(tmp_path)
    path = tmp_path / "image-sessions" / ("d" * 32 + ".json")
    path.parent.mkdir(parents=True)
    path.write_text("nope", "utf-8")
    sessions.delete("d" * 32)
    assert not path.exists()


# ---- path traversal ----------------------------------------------------------------

@pytest.mark.parametrize("bad_id", ["../outside", "..%2Foutside", "/etc/passwd", "A" * 32,
                                    "a" * 31, "a" * 33, "", "../" + "a" * 29])
def test_ids_outside_the_hex_pattern_never_reach_the_filesystem(tmp_path, bad_id):
    sessions = store(tmp_path)
    outside = tmp_path / "outside.json"
    outside.write_text(json.dumps({"id": "x", "attempts": []}), "utf-8")
    sessions.create()
    assert sessions.exists(bad_id) is False
    with pytest.raises(NotFoundError):
        sessions.get(bad_id)
    with pytest.raises(NotFoundError):
        sessions.rename(bad_id, "t")
    with pytest.raises(NotFoundError):
        sessions.delete(bad_id)
    assert sessions.begin_attempt(bad_id, {"id": "a" * 32, "job_id": 1, "params": params()}) is False
    assert sessions.settle_attempt(bad_id, "a" * 32, "done", "x.png") is False
    assert outside.exists() and json.loads(outside.read_text("utf-8")) == {"id": "x", "attempts": []}


# ---- concurrency (D-15) --------------------------------------------------------------

def test_concurrent_settle_and_rename_lose_no_writes(tmp_path):
    sessions = store(tmp_path)
    session_id = sessions.create()["id"]
    ids = [begin(sessions, session_id, job_id=n) for n in range(1, 41)]
    barrier = threading.Barrier(2)

    def settle_all():
        barrier.wait()
        for n, attempt_id in enumerate(ids):
            assert sessions.settle_attempt(session_id, attempt_id, "done", f"{n}.png")

    def rename_many():
        barrier.wait()
        for n in range(40):
            sessions.rename(session_id, f"名字 {n}")

    threads = [threading.Thread(target=settle_all), threading.Thread(target=rename_many)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    final = sessions.get(session_id)
    assert final["title"] == "名字 39" and final["title_auto"] is False
    assert [a["status"] for a in final["attempts"]] == ["done"] * 40
    assert [a["output"] for a in final["attempts"]] == [f"{n}.png" for n in range(40)]


def test_concurrent_appends_from_two_writers_all_land(tmp_path):
    sessions = store(tmp_path)
    session_id = sessions.create()["id"]
    barrier = threading.Barrier(2)

    def writer(offset):
        barrier.wait()
        for n in range(25):
            begin(sessions, session_id, job_id=offset + n)

    threads = [threading.Thread(target=writer, args=(o,)) for o in (1, 101)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(30)
    assert len(sessions.get(session_id)["attempts"]) == 50


# ---- HTTP handlers (§3.1-§3.5) ---------------------------------------------------------

def call(library, method, path, *, session_id=None, body=None):
    handler = {(m, p): h for m, p, h in routes(library)}[(method, path)]
    raw_body = b"" if body is None else (body if isinstance(body, bytes) else json.dumps(body).encode())
    response = handler(LibRequest(path_params={"id": session_id} if session_id else {}, body=raw_body))
    return response.status, json.loads(response.body.decode("utf-8"))


def test_http_round_trip(tmp_path):
    library, _ = make_library(tmp_path)
    assert call(library, "GET", "/api/image-sessions") == (200, [])
    status, created = call(library, "POST", "/api/image-sessions")
    assert status == 200 and created["attempts"] == [] and created["title"] == "新会话"
    assert call(library, "POST", "/api/image-sessions", body={})[0] == 200
    status, listed = call(library, "GET", "/api/image-sessions")
    assert status == 200 and len(listed) == 2
    assert set(listed[0]) == {"id", "title", "created", "updated", "attempt_count", "running", "cover"}
    status, got = call(library, "GET", "/api/image-sessions/{id}", session_id=created["id"])
    assert status == 200 and got == created
    status, renamed = call(library, "PATCH", "/api/image-sessions/{id}", session_id=created["id"],
                           body={"title": "猫"})
    assert status == 200 and renamed["title"] == "猫" and renamed["title_auto"] is False
    assert call(library, "DELETE", "/api/image-sessions/{id}", session_id=created["id"]) == (
        200, {"deleted": created["id"]})
    assert len(call(library, "GET", "/api/image-sessions")[1]) == 1


def test_http_errors(tmp_path):
    library, roots = make_library(tmp_path)
    session_id = library.create_image_session()["id"]
    missing = "e" * 32
    assert call(library, "POST", "/api/image-sessions", body={"title": "x"}) == (
        400, {"error": "不认识的字段：['title']"})
    assert call(library, "POST", "/api/image-sessions", body=b"not json")[0] == 400
    assert call(library, "GET", "/api/image-sessions/{id}", session_id=missing) == (
        404, {"error": f"会话不存在：{missing}"})
    assert call(library, "GET", "/api/image-sessions/{id}", session_id="../x") == (
        404, {"error": "会话不存在：../x"})
    assert call(library, "PATCH", "/api/image-sessions/{id}", session_id=session_id,
                body={"title": "x", "attempts": []}) == (400, {"error": "不认识的字段：['attempts']"})
    assert call(library, "PATCH", "/api/image-sessions/{id}", session_id=session_id,
                body={"title": " "}) == (400, {"error": "标题须为 1–80 个字"})
    assert call(library, "PATCH", "/api/image-sessions/{id}", session_id=missing,
                body={"title": "ok"})[0] == 404
    assert call(library, "DELETE", "/api/image-sessions/{id}", session_id=missing)[0] == 404
    (roots.image_sessions_dir / ("c" * 32 + ".json")).write_text("{", "utf-8")
    assert call(library, "GET", "/api/image-sessions/{id}", session_id="c" * 32) == (
        400, {"error": "会话文件已损坏，无法读取"})
    assert call(library, "PATCH", "/api/image-sessions/{id}", session_id="c" * 32,
                body={"title": "ok"})[0] == 400
    assert call(library, "GET", "/api/image-sessions")[1][-1] == {"id": "c" * 32, "corrupt": True}
