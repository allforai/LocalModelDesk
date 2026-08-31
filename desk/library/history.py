"""Append-only JSONL job history with strict writes and tolerant reads."""
import json
import threading
import uuid
from datetime import datetime
from pathlib import Path

from .errors import ValidationError

_TS_FMT = "%Y-%m-%dT%H:%M:%S"


class HistoryStore:
    def __init__(self, history_file: Path):
        self._file = history_file
        self._lock = threading.Lock()

    def append(self, entry: dict) -> dict:
        if not isinstance(entry, dict):
            raise ValidationError("history entry must be a dict")
        for field in ("kind", "status"):
            if not entry.get(field):
                raise ValidationError(f"history entry missing required field: {field}")

        full = dict(entry)
        full.setdefault("id", uuid.uuid4().hex)
        full.setdefault("ts", datetime.now().strftime(_TS_FMT))
        line = json.dumps(full, ensure_ascii=False) + "\n"
        with self._lock:
            self._file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._file, "a", encoding="utf-8") as history_file:
                history_file.write(line)
        return full

    def list(self, limit: int | None = None) -> list[dict]:
        entries = self._read_all()
        entries.reverse()
        return entries if limit is None else entries[:limit]

    def by_output(self) -> dict[str, dict]:
        mapping: dict[str, dict] = {}
        for entry in self._read_all():
            output = entry.get("output")
            if output:
                mapping[output] = entry
        return mapping

    def _read_all(self) -> list[dict]:
        if not self._file.exists():
            return []

        entries = []
        with open(self._file, "r", encoding="utf-8") as history_file:
            for raw in history_file:
                raw = raw.strip()
                if not raw:
                    continue
                try:
                    entry = json.loads(raw)
                except ValueError:
                    continue
                if isinstance(entry, dict):
                    entries.append(entry)
        return entries
