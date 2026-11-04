#!/usr/bin/env python3
"""Append structured workflow run events to .allforai/bootstrap/run-log.jsonl."""

from __future__ import annotations

import argparse
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path


RUN_ID_PATH = Path(".allforai/bootstrap/run-id")
RUN_LOG_PATH = Path(".allforai/bootstrap/run-log.jsonl")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_run_id(project_root: Path) -> str:
    path = project_root / RUN_ID_PATH
    if path.exists():
        value = path.read_text(encoding="utf-8").strip()
        if value:
            return value
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(run_id + "\n", encoding="utf-8")
    return run_id


def _parse_json_value(value: str | None):
    if value is None or value == "":
        return None
    try:
        return json.loads(value)
    except Exception:
        return value


def _split_csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def record_event(project_root: Path, event: dict) -> dict:
    project_root = project_root.resolve()
    event = {key: value for key, value in event.items() if value not in (None, [], {})}
    payload = {
        "ts": _now(),
        "run_id": _read_run_id(project_root),
        **event,
    }
    log_path = project_root / RUN_LOG_PATH
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--event", required=True)
    parser.add_argument("--node-id")
    parser.add_argument("--capability")
    parser.add_argument("--status")
    parser.add_argument("--message")
    parser.add_argument("--command")
    parser.add_argument("--duration-ms", type=int)
    parser.add_argument("--expected-artifacts")
    parser.add_argument("--created-artifacts")
    parser.add_argument("--blocking-reason")
    parser.add_argument("--repair-route")
    parser.add_argument("--skill-refs")
    parser.add_argument("--metadata-json")
    args = parser.parse_args(argv)

    payload = record_event(
        Path(args.project_root),
        {
            "event": args.event,
            "node_id": args.node_id,
            "capability": args.capability,
            "status": args.status,
            "message": args.message,
            "command": args.command,
            "duration_ms": args.duration_ms,
            "expected_artifacts": _split_csv(args.expected_artifacts),
            "created_artifacts": _split_csv(args.created_artifacts),
            "blocking_reason": args.blocking_reason,
            "repair_route": args.repair_route,
            "skill_refs": _split_csv(args.skill_refs),
            "metadata": _parse_json_value(args.metadata_json),
        },
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
