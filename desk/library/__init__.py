"""Local persistence for outputs, job history, chat sessions and media sessions."""
import os
import tempfile

from .errors import LibraryError, NotFoundError, ValidationError
from .history import HistoryStore
from .media_sessions import KINDS, MediaSessionStore
from .outputs import OutputsStore
from .sessions import SessionStore

__all__ = ["LibraryService", "LibraryError", "NotFoundError", "ValidationError"]


class LibraryService:
    """Facade that assembles the library stores from path roots."""

    def __init__(self, roots):
        _adopt_legacy_history(roots)
        self.history = HistoryStore(roots.history_path)
        self.outputs = OutputsStore(roots.outputs_root, self.history)
        self.sessions = SessionStore(roots.sessions_dir)
        self.media_sessions = {kind: MediaSessionStore(kind, roots.media_sessions_dirs[kind], roots.outputs_root)
                               for kind in KINDS}
        # 上次进程被杀时还在跑的尝试不会再有人落定；启动时一次性收尾（IS D-25、B-38a）。
        for store in self.media_sessions.values():
            store.recover_running()

    def append_history(self, entry: dict) -> dict:
        return self.history.append(entry)

    def list_history(self, limit: int | None = None) -> list[dict]:
        return self.history.list(limit)

    def list_outputs(self) -> list[dict]:
        return self.outputs.list()

    def serve_output(self, name: str, range_header: str | None = None):
        return self.outputs.serve(name, range_header)

    def list_chat_sessions(self) -> list[dict]:
        return self.sessions.list()

    def create_chat_session(
        self, title: str | None = None, model: str | None = None
    ) -> dict:
        return self.sessions.create(title, model)

    def update_chat_session(self, session_id: str, patch: dict) -> dict:
        return self.sessions.update(session_id, patch)

    def delete_chat_session(self, session_id: str) -> None:
        self.sessions.delete(session_id)

    def sessions_of(self, kind: str) -> MediaSessionStore:
        store = self.media_sessions.get(kind)
        if store is None:
            raise NotFoundError(f"不认识的媒体类型：{kind}")
        return store


def _adopt_legacy_history(roots) -> None:
    """Copy the old output history once, never overwriting or moving it."""
    target = roots.history_path
    legacy = roots.outputs_root / "history.jsonl"
    if target.exists() or not legacy.is_file():
        return

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(dir=target.parent, prefix=".tmp-history-")
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(legacy.read_bytes())
        os.replace(temporary_path, target)
    except BaseException:
        try:
            os.unlink(temporary_path)
        except OSError:
            pass
        raise
