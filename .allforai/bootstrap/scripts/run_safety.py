#!/usr/bin/env python3
"""Persist a run-wide safety quarantine without accepting or deleting any output."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile


MARKER = ".allforai/bootstrap/safety-quarantine.json"


def quarantine(project_root: Path, node_ids: list[str], reason: str) -> dict:
    root = project_root.resolve()
    base = root / ".allforai/bootstrap"
    if not base.resolve().is_relative_to(root):
        return {"status": "blocked", "reason": "bootstrap state is outside project root"}
    if (not isinstance(node_ids, list) or not node_ids or
            any(not isinstance(n, str) or not n.strip() for n in node_ids) or
            not isinstance(reason, str) or not reason.strip()):
        return {"status": "blocked", "reason": "quarantine requires node identities and a reason"}
    lock = base / "safety-quarantine.lock"
    temporary = None
    locked = False
    persisted = False
    try:
        lock.mkdir()
        locked = True
        workflow = json.loads((base / "workflow.json").read_text(encoding="utf-8"))
        nodes = workflow.get("nodes")
        if not isinstance(nodes, list) or any(not isinstance(n, dict) for n in nodes):
            raise ValueError("invalid workflow nodes")
        declared = {n["node_id"]: n for n in nodes if isinstance(n.get("node_id"), str)}
        if not set(node_ids).issubset(declared):
            raise ValueError("quarantine names an unknown node")
        target = root / MARKER
        if target.is_symlink():
            raise ValueError("quarantine marker must not be a symlink")
        previous = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {
            "schema_version": 1, "status": "quarantined", "events": [], "node_ids": []}
        if (not isinstance(previous, dict) or previous.get("schema_version") != 1 or
                previous.get("status") != "quarantined" or
                not isinstance(previous.get("events"), list) or
                not isinstance(previous.get("node_ids"), list) or
                any(not isinstance(n, str) for n in previous["node_ids"])):
            raise ValueError("existing quarantine is unreadable")
        previous["node_ids"] = sorted(set(previous["node_ids"]) | set(node_ids))
        previous["events"].append({
            "recorded_at": datetime.now(timezone.utc).isoformat(), "reason": reason,
            "nodes": [{"node_id": n, "exit_artifacts": declared[n].get("exit_artifacts", [])}
                      for n in sorted(set(node_ids))]})
        previous["recovery"] = (
            "Keep this run blocked until listed outputs receive independent revalidation. "
            "Do not clear quarantine merely because Run Policy changed or a worker reported success.")
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=base, delete=False) as stream:
            temporary = Path(stream.name)
            json.dump(previous, stream, indent=2, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
        directory = os.open(base, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        persisted = True
        return {"status": "quarantined", "marker": MARKER, "node_ids": previous["node_ids"]}
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return {"status": "blocked", "reason": "cannot persist trustworthy safety quarantine; stop execution"}
    finally:
        if temporary is not None:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
        # An interrupted/failed publication leaves a persistent fence. Readiness
        # must refuse the lock as well as the marker; absence of the marker is not
        # proof that this attempt to quarantine never happened.
        if locked and persisted:
            try:
                lock.rmdir()
            except OSError:
                pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project_root", type=Path)
    parser.add_argument("--nodes-json", required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args()
    try:
        node_ids = json.loads(args.nodes_json)
    except ValueError:
        node_ids = None
    verdict = quarantine(args.project_root, node_ids, args.reason)
    print(json.dumps(verdict))
    return 0 if verdict["status"] == "quarantined" else 1


if __name__ == "__main__":
    raise SystemExit(main())
