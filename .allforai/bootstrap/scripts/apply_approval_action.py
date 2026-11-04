#!/usr/bin/env python3
"""Apply a queued approval-dashboard action to one approval-records.json file."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--approval", action="append", required=True)
    parser.add_argument("--action-json", required=True)
    args = parser.parse_args()

    approval_paths = [Path(path) for path in args.approval]
    action = json.loads(args.action_json)
    node_id = action.get("node_id")
    if not node_id:
        raise SystemExit("action_json missing node_id")

    requested_path = action.get("approval_record_path")
    candidates = approval_paths
    if requested_path:
        requested = Path(requested_path)
        candidates = [
            path
            for path in approval_paths
            if path == requested or path.as_posix().endswith(requested.as_posix())
        ] or approval_paths

    approval_path = None
    data = None
    record = None
    for path in candidates:
        if not path.exists():
            continue
        payload = json.loads(path.read_text(encoding="utf-8"))
        found = next(
            (item for item in payload.get("records", []) if item.get("node_id") == node_id),
            None,
        )
        if found is not None:
            approval_path = path
            data = payload
            record = found
            break

    if approval_path is None or data is None or record is None:
        raise SystemExit(f"approval record not found: {node_id}")

    now = datetime.now(timezone.utc).isoformat()
    reviewer_notes = action.get("reviewer_notes")
    revision_notes = action.get("revision_notes")
    if reviewer_notes is not None:
        record["reviewer_notes"] = reviewer_notes
    if revision_notes is not None:
        record["revision_notes"] = revision_notes

    kind = action.get("action")
    if kind == "approve":
        record["gate_status"] = "approved"
        record["approved_at"] = now
        approved_by = action.get("approved_by") or "discipline_owner"
        existing = record.get("approved_by") or []
        if approved_by not in existing:
            existing.append(approved_by)
        record["approved_by"] = existing
        record["revision_notes"] = ""
    elif kind == "request_revision":
        if not record.get("revision_notes"):
            raise SystemExit("request_revision requires revision_notes")
        record["gate_status"] = "revision-requested"
        record["approved_at"] = None
        record["approved_by"] = []
    elif kind == "save_notes":
        pass
    else:
        raise SystemExit(f"unknown action: {kind}")

    approval_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
