"""Media generation sessions (image / video / music): one JSON file per session.

Layout and write discipline follow ``SessionStore``: ``<id>.json`` under the kind's
own directory, atomic temp-file + ``os.replace`` writes, dot-prefixed files skipped.
Every write method does read → modify → write back inside one lock and keeps no
in-memory copy, so a job settling an attempt and a request renaming or deleting
the same session never overwrite each other.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
import uuid
from datetime import datetime
from pathlib import Path

from .errors import NotFoundError, ValidationError

log = logging.getLogger(__name__)

_ID_RE = re.compile(r"^[0-9a-f]{32}$")
_TS_FMT = "%Y-%m-%dT%H:%M:%S"
DEFAULT_TITLE = "新会话"
TITLE_AUTO_CHARS = 24
TITLE_MAX_CHARS = 80
KINDS = ("image", "video", "music")
PARAM_KEYS = {
    "image": ("prompt", "width", "height", "steps", "seed"),
    "video": ("prompt", "width", "height", "frames", "steps", "seed",
              "mode", "use_audio", "first_frame", "last_frame", "ref_video"),
    "music": ("caption", "lyrics", "duration", "seed"),
}
COMPOSE_PARAM_KEYS = ("parts",)
TITLE_FIELD = {"image": "prompt", "video": "prompt", "music": "caption"}
SETTLED_STATUSES = frozenset({"done", "failed", "cancelled"})
INTERRUPTED_ERROR = {"code": "interrupted", "message": "应用在生成途中关闭，这次没有完成"}
INTERRUPTED_JOIN_ERROR = {"code": "interrupted", "message": "应用在拼接成片时关闭"}


class _Corrupt(Exception):
    """The session file exists but is not a readable session object."""


class SegmentMissing(Exception):
    """The attempt exists but is not done, or its file is gone."""


def auto_title(prompt: str) -> str:
    """Title taken from a prompt: whitespace collapsed, at most 24 characters plus an ellipsis."""
    text = " ".join(str(prompt).split())
    return f"{text[:TITLE_AUTO_CHARS]}…" if len(text) > TITLE_AUTO_CHARS else text


def _now() -> str:
    return datetime.now().strftime(_TS_FMT)


class MediaSessionStore:
    def __init__(self, kind: str, sessions_dir: Path, outputs_root: Path):
        if kind not in KINDS:
            raise ValueError(f"unknown media kind: {kind}")
        self.kind = kind
        self._dir = Path(sessions_dir)
        self._outputs_root = Path(outputs_root)
        self._lock = threading.Lock()

    # ---- reads -----------------------------------------------------------

    def list(self) -> list[dict]:
        if not self._dir.is_dir():
            return []
        summaries, corrupt = [], []
        for path in sorted(self._dir.glob("*.json")):
            if path.name.startswith("."):
                continue
            try:
                session = self._parse(path)
            except _Corrupt:
                corrupt.append({"id": path.stem, "corrupt": True})
                continue
            summaries.append(self._summary(session))
        summaries.sort(key=lambda item: str(item.get("updated", "")), reverse=True)
        return summaries + corrupt

    def get(self, session_id: str) -> dict:
        session = self._load(session_id)
        for attempt in session["attempts"]:
            if isinstance(attempt, dict) and attempt.get("status") == "done":
                attempt["output_missing"] = not self._is_output(attempt.get("output"))
                if attempt.get("joined_output"):
                    attempt["joined_missing"] = not self._is_output(attempt["joined_output"])
        return session

    def exists(self, session_id: str) -> bool:
        path = self._path(session_id)
        return path is not None and path.is_file()

    # ---- writes ----------------------------------------------------------

    def create(self) -> dict:
        now = _now()
        session = {"id": uuid.uuid4().hex, "kind": self.kind, "title": DEFAULT_TITLE, "title_auto": True,
                   "created": now, "updated": now, "attempts": []}
        with self._lock:
            self._write(session)
        return session

    def rename(self, session_id: str, title) -> dict:
        cleaned = title.strip() if isinstance(title, str) else ""
        if not 1 <= len(cleaned) <= TITLE_MAX_CHARS:
            raise ValidationError(f"标题须为 1–{TITLE_MAX_CHARS} 个字")
        with self._lock:
            session = self._load(session_id)
            session["title"] = cleaned
            session["title_auto"] = False
            session["updated"] = _now()
            self._write(session)
        return session

    def delete(self, session_id: str) -> None:
        """Remove only ``<id>.json``; outputs and history are never touched."""
        path = self._path(session_id)
        with self._lock:
            if path is None or not path.is_file():
                raise NotFoundError(f"会话不存在：{session_id}")
            path.unlink()

    def begin_attempt(self, session_id: str, attempt: dict) -> bool:
        """Append a running attempt; False (never an exception) when the session is gone or unreadable."""
        op = attempt.get("op") or "generate"
        params = attempt.get("params") or {}
        keys = COMPOSE_PARAM_KEYS if op == "compose" else PARAM_KEYS[self.kind]
        record = {
            "id": attempt["id"], "job_id": attempt.get("job_id"), "ts": _now(), "finished": None,
            "status": "running", "op": op,
            "params": {key: params[key] for key in keys if key in params},
            "continues": attempt.get("continues"), "refs": dict(attempt.get("refs") or {}),
            "output": None, "joined_output": None, "joined_error": None, "error": None,
            "base": attempt.get("base"),
        }
        with self._lock:
            session = self._load_quiet(session_id)
            if session is None:
                return False
            if op == "generate" and not session["attempts"] and session.get("title_auto", True):
                source = record["params"].get(TITLE_FIELD[self.kind]) or ""
                session["title"] = auto_title(source) or DEFAULT_TITLE
            session["attempts"].append(record)
            session["updated"] = record["ts"]
            self._write(session)
        return True

    def record_output(self, session_id: str, attempt_id: str, output: str) -> bool:
        """Write the finished segment's file name into a still-running attempt (B-38a)."""
        with self._lock:
            session = self._load_quiet(session_id)
            attempt = self._running(session, attempt_id)
            if attempt is None:
                return False
            attempt["output"] = output
            self._write(session)
        return True

    def settle_attempt(self, session_id: str, attempt_id: str, status: str, output: str | None = None,
                       error: dict | None = None, joined_output: str | None = None,
                       joined_error: dict | None = None) -> bool:
        """Settle a running attempt; False when the session or a running attempt with that id is gone."""
        if status not in SETTLED_STATUSES:
            raise ValueError(f"not a settled status: {status}")
        with self._lock:
            session = self._load_quiet(session_id)
            attempt = self._running(session, attempt_id)
            if attempt is None:
                return False
            now = _now()
            done = status == "done"
            attempt.update(
                status=status, finished=now,
                output=(output or attempt.get("output")) if done else None,
                error=None if done else dict(error or {}),
                joined_output=joined_output if done else None,
                joined_error=dict(joined_error) if done and joined_error else None,
            )
            session["updated"] = now
            self._write(session)
        return True

    def recover_running(self) -> int:
        """Settle attempts a previous process left running; a recorded segment survives as done (B-38a)."""
        if not self._dir.is_dir():
            return 0
        changed = 0
        with self._lock:
            for path in sorted(self._dir.glob("*.json")):
                if path.name.startswith("."):
                    continue
                try:
                    session = self._parse(path)
                except _Corrupt:
                    continue
                stale = [item for item in session["attempts"]
                         if isinstance(item, dict) and item.get("status") == "running"]
                if not stale:
                    continue
                now = _now()
                for attempt in stale:
                    if attempt.get("output"):
                        attempt.update(status="done", finished=now, error=None, joined_output=None,
                                       joined_error=dict(INTERRUPTED_JOIN_ERROR))
                    else:
                        attempt.update(status="failed", finished=now, output=None,
                                       error=dict(INTERRUPTED_ERROR))
                session["updated"] = now
                self._write(session)
                changed += len(stale)
        return changed

    def find_done(self, session_id: str, attempt_id: str) -> dict:
        """The done attempt whose file still exists; NotFoundError / SegmentMissing otherwise."""
        session = self.get(session_id)
        attempt = next((a for a in session["attempts"]
                        if isinstance(a, dict) and a.get("id") == attempt_id), None)
        if attempt is None:
            raise NotFoundError(f"找不到这一段：{attempt_id}")
        if attempt.get("status") != "done" or attempt.get("output_missing"):
            raise SegmentMissing(attempt_id)
        return attempt

    def chain(self, session_id: str, attempt_id: str) -> tuple[list[dict], bool]:
        """Attempts from the chain head to ``attempt_id`` (inclusive), following ``continues`` (B-22)."""
        session = self.get(session_id)
        by_id = {a.get("id"): a for a in session["attempts"] if isinstance(a, dict)}
        items, seen, cursor = [], set(), attempt_id
        while cursor is not None:
            if cursor in seen or cursor not in by_id:
                return list(reversed(items)), True
            seen.add(cursor)
            items.append(by_id[cursor])
            cursor = by_id[cursor].get("continues")
        return list(reversed(items)), False

    # ---- internals -------------------------------------------------------

    def _is_output(self, name) -> bool:
        return isinstance(name, str) and bool(name) and (self._outputs_root / name).is_file()

    @staticmethod
    def _running(session: dict | None, attempt_id: str) -> dict | None:
        if session is None:
            return None
        attempt = next((item for item in session["attempts"]
                        if isinstance(item, dict) and item.get("id") == attempt_id), None)
        return attempt if attempt is not None and attempt.get("status") == "running" else None

    @staticmethod
    def _summary(session: dict) -> dict:
        attempts = [item for item in session["attempts"] if isinstance(item, dict)]
        done = [item.get("joined_output") or item.get("output") for item in attempts
                if item.get("status") == "done" and (item.get("joined_output") or item.get("output"))]
        return {
            "id": session.get("id"), "title": session.get("title"),
            "created": session.get("created"), "updated": session.get("updated"),
            "attempt_count": len(session["attempts"]),
            "running": any(item.get("status") == "running" for item in attempts),
            "cover": done[-1] if done else None,
        }

    def _path(self, session_id) -> Path | None:
        if not isinstance(session_id, str) or not _ID_RE.fullmatch(session_id):
            return None
        return self._dir / f"{session_id}.json"

    def _parse(self, path: Path) -> dict:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise _Corrupt(str(exc)) from exc
        if not isinstance(data, dict) or not isinstance(data.get("attempts"), list):
            raise _Corrupt("session file is not a session object")
        if data.setdefault("kind", self.kind) != self.kind:
            raise _Corrupt(f"session kind {data['kind']!r} in the {self.kind} directory")
        data["id"] = path.stem  # the file name is the identity; a later write must land on the same file
        return data

    def _load(self, session_id: str) -> dict:
        path = self._path(session_id)
        if path is None or not path.is_file():
            raise NotFoundError(f"会话不存在：{session_id}")
        try:
            return self._parse(path)
        except _Corrupt as exc:
            raise ValidationError("会话文件已损坏，无法读取") from exc

    def _load_quiet(self, session_id: str) -> dict | None:
        try:
            return self._load(session_id)
        except NotFoundError:
            return None
        except ValidationError:
            log.warning("%s session %s is corrupt; attempt not recorded", self.kind, session_id)
            return None

    def _write(self, session: dict) -> None:
        payload = json.dumps(session, ensure_ascii=False, indent=2)
        self._dir.mkdir(parents=True, exist_ok=True)
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
