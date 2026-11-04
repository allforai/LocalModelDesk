#!/usr/bin/env python3
"""Summarize .allforai/bootstrap/run-log.jsonl into JSON and Markdown reports."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

try:
    # Imported at module level on purpose: the generated project ships both scripts in
    # one directory, and the unit suite only has that directory on sys.path while the
    # module is being loaded, so a deferred import would find nothing to disclose.
    from product_intent import delegations as _delegations
    _delegations_unavailable = None
except ImportError as exc:  # a trace copied without the intent CLI still summarizes the run
    _delegations = None
    _delegations_unavailable = ("product_intent could not be imported, so delegated decisions "
                                f"were not looked up: {exc}")


RUN_LOG_PATH = Path(".allforai/bootstrap/run-log.jsonl")
SUMMARY_JSON = Path(".allforai/bootstrap/run-summary.json")
SUMMARY_MD = Path(".allforai/bootstrap/run-summary.md")


def _load_events(project_root: Path) -> list[dict]:
    path = project_root / RUN_LOG_PATH
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _node_id(event: dict) -> str | None:
    return event.get("node_id") or event.get("node")


def _delegated(project_root: Path) -> tuple[list, str | None]:
    """The directions the user handed to the model, and why they could not be read.

    Summarizing is the last thing a run does, on its way out of a success and out of
    an early stop alike, so an unreadable concept may not take the whole trace down
    with it. It costs the reading and says so instead: a disclosure that quietly
    reports nothing delegated would be worse than one that admits it cannot look.
    """
    if _delegations is None:
        return [], _delegations_unavailable
    try:
        return list(_delegations(project_root)["delegations"]), None
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        return [], str(exc)


def summarize(project_root: Path) -> dict:
    project_root = project_root.resolve()
    events = _load_events(project_root)
    by_event = Counter(event.get("event", "unknown") for event in events)
    by_status = Counter(event.get("status", "unknown") for event in events if event.get("status"))
    by_node = defaultdict(lambda: Counter())
    blockers = []
    failures = []
    completed_nodes = []
    for event in events:
        node_id = _node_id(event)
        if node_id:
            by_node[node_id][event.get("event", "unknown")] += 1
        if event.get("event") == "node_completed" and node_id:
            completed_nodes.append(node_id)
        if event.get("blocking_reason"):
            blockers.append(event)
        if event.get("event") in {"node_failed", "validation_failed", "preflight_blocked", "run_halted"}:
            failures.append(event)

    delegated, delegations_error = _delegated(project_root)
    summary = {
        "schema_version": "1.0",
        "event_count": len(events),
        "run_ids": sorted({event.get("run_id") for event in events if event.get("run_id")}),
        "first_ts": events[0].get("ts") if events else None,
        "last_ts": events[-1].get("ts") if events else None,
        "events_by_type": dict(sorted(by_event.items())),
        "events_by_status": dict(sorted(by_status.items())),
        "nodes": {
            node_id: dict(counter)
            for node_id, counter in sorted(by_node.items())
        },
        "completed_nodes": sorted(set(completed_nodes)),
        "blocker_count": len(blockers),
        "failure_count": len(failures),
        "blockers": blockers[-20:],
        "failures": failures[-20:],
        "delegations": delegated,
    }
    if delegations_error is not None:
        summary["delegations_error"] = delegations_error
    return summary


def write_reports(project_root: Path, summary: dict) -> tuple[Path, Path]:
    project_root = project_root.resolve()
    json_path = project_root / SUMMARY_JSON
    md_path = project_root / SUMMARY_MD
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Run Summary",
        "",
        f"- events: `{summary['event_count']}`",
        f"- run_ids: `{', '.join(summary['run_ids']) or 'none'}`",
        f"- first_ts: `{summary.get('first_ts')}`",
        f"- last_ts: `{summary.get('last_ts')}`",
        f"- blockers: `{summary['blocker_count']}`",
        f"- failures: `{summary['failure_count']}`",
        "",
        "## Events By Type",
    ]
    for key, value in summary["events_by_type"].items():
        lines.append(f"- `{key}`: {value}")
    if not summary["events_by_type"]:
        lines.append("- none")
    lines.extend(["", "## Completed Nodes"])
    for node_id in summary.get("completed_nodes", []):
        lines.append(f"- `{node_id}`")
    if not summary.get("completed_nodes"):
        lines.append("- none")
    lines.extend(["", "## Recent Failures"])
    for item in summary["failures"]:
        lines.append(
            f"- `{item.get('event')}` node=`{_node_id(item)}` "
            f"reason=`{item.get('blocking_reason') or item.get('message')}`"
        )
    if not summary["failures"]:
        lines.append("- none")
    lines.extend(["", "## Delegated Decisions"])
    for item in summary.get("delegations", []):
        lines.append(
            f"- `{item.get('id')}` proposal=`{item.get('proposal_title')}` "
            f"user_turn=`{item.get('user_reference')}` reason=`{item.get('reason')}`"
        )
    # `none` is a finding. A list that could not be read found nothing out, so it says
    # why instead and never words its own failure as "nothing was delegated".
    if not summary.get("delegations") and not summary.get("delegations_error"):
        lines.append("- none")
    if summary.get("delegations_error"):
        lines.append(f"- unreadable: {summary['delegations_error']}")
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    root = Path(args.project_root)
    summary = summarize(root)
    if args.write_report:
        write_reports(root, summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
