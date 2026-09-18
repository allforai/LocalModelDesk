"""Multi-session chat persistence: one JSON file per session."""

import json
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

from .errors import NotFoundError, ValidationError

_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_TS_FMT = "%Y-%m-%dT%H:%M:%S"
_PATCH_KEYS = frozenset({"title", "model", "messages"})


class SessionStore:
    def __init__(self, sessions_dir: Path):
        self._dir = sessions_dir
        self._lock = threading.Lock()

    def list(self) -> list[dict]:
        if not self._dir.is_dir():
            return []

        sessions = []
        for path in sorted(self._dir.glob("*.json")):
            # 跳过写入中的临时文件。新版本的临时名已不带 .json 后缀，但旧版本
            # 留下的 .tmp-XXXX.json 残留仍会被 glob 捞到——真会话的 id 不会以
            # 点开头，所以按点开头跳过既安全又能兜住残留。
            if path.name.startswith("."):
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("session file is not an object")
            except ValueError:
                sessions.append({"id": path.stem, "corrupt": True})
                continue
            sessions.append(data)
        sessions.sort(key=lambda session: session.get("updated", ""), reverse=True)
        return sessions

    def create(self, title: str | None = None, model: str | None = None) -> dict:
        now = datetime.now().strftime(_TS_FMT)
        session = {
            "id": uuid.uuid4().hex,
            "title": title or "新会话",
            "model": model,
            "created": now,
            "updated": now,
            "messages": [],
        }
        with self._lock:
            self._write(session)
        return session

    def delete(self, session_id: str) -> None:
        path = self._path(session_id)
        with self._lock:
            if path is None or not path.is_file():
                raise NotFoundError(f"session not found: {session_id}")
            path.unlink()

    def update(self, session_id: str, patch: dict) -> dict:
        if not isinstance(patch, dict):
            raise ValidationError("patch must be an object")
        unknown = set(patch) - _PATCH_KEYS
        if unknown:
            raise ValidationError(f"unknown patch keys: {sorted(unknown)}")
        if "messages" in patch and not isinstance(patch["messages"], list):
            raise ValidationError("messages must be a list")

        with self._lock:
            session = self._load(session_id)
            session.update(patch)
            session["updated"] = datetime.now().strftime(_TS_FMT)
            self._write(session)
        return session

    def _path(self, session_id: str) -> Path | None:
        if not isinstance(session_id, str) or not _ID_RE.fullmatch(session_id):
            return None
        return self._dir / f"{session_id}.json"

    def _load(self, session_id: str) -> dict:
        path = self._path(session_id)
        if path is None or not path.is_file():
            raise NotFoundError(f"session not found: {session_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def _write(self, session: dict) -> None:
        payload = json.dumps(session, ensure_ascii=False, indent=2)
        self._dir.mkdir(parents=True, exist_ok=True)
        # 临时文件不带 .json 后缀：list() 用 glob("*.json")，而 pathlib 的 glob
        # 会匹配点开头的 .tmp-XXXX.json，写入窗口内并发读会读到半写文件，
        # 被记成一条 corrupt 的幽灵会话（keep-code-simple F5）。
        fd, temporary_path = tempfile.mkstemp(dir=self._dir, prefix=".tmp-", suffix=".part")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
            os.replace(temporary_path, self._dir / f"{session['id']}.json")
        except BaseException:
            try:
                os.unlink(temporary_path)
            except OSError:
                pass
            raise
