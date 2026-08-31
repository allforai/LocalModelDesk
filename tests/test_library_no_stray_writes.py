"""R-library-07: library writes only below injected roots."""
import os
from pathlib import Path

from desk.library import LibraryService
from desk.library.http import LibRequest, routes

MODULE_DIR = Path(__file__).resolve().parents[1] / "desk" / "library"


class FakeRoots:
    def __init__(self, base: Path):
        self.data_root = base
        self.history_path = base / "history.jsonl"
        self.sessions_dir = base / "sessions"
        self.outputs_root = base / "outputs"


def test_full_flow_writes_only_under_roots(tmp_path):
    jail = tmp_path / "jail"
    jail.mkdir()
    base = tmp_path / "data"
    base.mkdir()
    roots = FakeRoots(base)
    roots.outputs_root.mkdir()
    (roots.outputs_root / "h3-a.mp4").write_bytes(b"x" * 16)
    old_cwd = os.getcwd()
    os.chmod(jail, 0o500)
    os.chdir(jail)
    try:
        service = LibraryService(roots)
        service.append_history({"kind": "video", "status": "done", "output": "h3-a.mp4"})
        service.list_history()
        service.list_outputs()
        assert service.serve_output("h3-a.mp4", "bytes=0-3").body.read() == b"xxxx"
        session_id = service.create_chat_session(title="t")["id"]
        service.update_chat_session(
            session_id, {"messages": [{"role": "user", "content": "hi"}]}
        )
        service.delete_chat_session(session_id)
        for method, path, handler in routes(service):
            if method == "GET":
                handler(LibRequest(path_params={"name": "h3-a.mp4", "id": "0" * 32}))
    finally:
        os.chdir(old_cwd)
        os.chmod(jail, 0o700)

    assert list(jail.iterdir()) == []
    for path in tmp_path.rglob("*"):
        assert path == jail or path == base or base in path.parents, path


def test_module_source_has_no_hardcoded_user_paths():
    banned = ["Path.home(", "expanduser(", "/Users", "/Applications", '"~', "'~"]
    sources = list(MODULE_DIR.glob("*.py"))

    assert len(sources) >= 5
    for source in sources:
        text = source.read_text(encoding="utf-8")
        for token in banned:
            assert token not in text, f"{source.name} contains banned path token {token!r}"
