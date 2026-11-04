#!/usr/bin/env python3
"""Build an auditable re-bootstrap workflow state index and reconciliation plan.

The script is intentionally generic. It does not decide product scope; it
summarizes current workflow facts so bootstrap can reorganize nodes without
blindly overwriting existing state.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from check_artifacts import freshness_admits, freshness_states


BOOTSTRAP_DIR = Path(".allforai/bootstrap")
WORKFLOW_PATH = BOOTSTRAP_DIR / "workflow.json"
NODE_SPECS_DIR = BOOTSTRAP_DIR / "node-specs"
RUN_LOG_PATH = BOOTSTRAP_DIR / "run-log.jsonl"
STATE_INDEX_PATH = BOOTSTRAP_DIR / "workflow-state-index.json"
RECONCILIATION_JSON_PATH = BOOTSTRAP_DIR / "workflow-reconciliation-plan.json"
RECONCILIATION_MD_PATH = BOOTSTRAP_DIR / "workflow-reconciliation-plan.md"


BLOCKING_STATUS_VALUES = {
    "blocked",
    "failed",
    "failed_validation",
    "not_generated",
    "missing",
    "stale",
    "invalid",
    "partial",
    "conditional_pass",
    "accepted_with_gaps",
    "accepted_with_warnings",
    "passed_with_warnings",
    "existence_only",
    "not_good_enough",
    "quality_failed",
}

GAP_FIELDS = {
    "gaps",
    "code_gaps",
    "test_gaps",
    "asset_gaps",
    "audio_gaps",
    "contract_gaps",
    "quality_gaps",
    "effect_gaps",
    "experience_gaps",
    "visual_quality_gaps",
    "perceptual_gaps",
    "remaining_gaps",
    "blockers",
    "major_findings",
    "unresolved_findings",
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _artifact_paths(items: Any) -> list[str]:
    paths: list[str] = []
    if not isinstance(items, list):
        return paths
    for item in items:
        if isinstance(item, dict):
            value = item.get("path")
        else:
            value = item
        if value:
            paths.append(str(value))
    return paths


def _frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    data: dict[str, Any] = {}
    lines = text[3:end].strip().splitlines()
    current_key: str | None = None
    for raw in lines:
        line = raw.rstrip()
        if not line:
            continue
        if line.startswith("  - ") and current_key:
            data.setdefault(current_key, []).append(line[4:].strip().strip('"').strip("'"))
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value == "":
            data[key] = []
            current_key = key
        elif value == "[]":
            data[key] = []
            current_key = None
        else:
            data[key] = value.strip('"').strip("'")
            current_key = None
    return data


def _scan_report_status(value: Any) -> tuple[str, list[str]]:
    blockers: list[str] = []
    status = "complete"
    if isinstance(value, dict):
        for key, item in value.items():
            key_l = str(key).lower()
            if key_l.endswith("status") or key_l in {"status", "qa_status", "verdict", "result"}:
                item_l = str(item).lower()
                if item_l in BLOCKING_STATUS_VALUES:
                    status = "blocked"
                    blockers.append(f"{key}={item}")
            if key in GAP_FIELDS and item:
                status = "blocked"
                blockers.append(f"{key} non-empty")
            child_status, child_blockers = _scan_report_status(item)
            if child_status == "blocked":
                status = "blocked"
                blockers.extend(child_blockers)
    elif isinstance(value, list):
        for item in value:
            child_status, child_blockers = _scan_report_status(item)
            if child_status == "blocked":
                status = "blocked"
                blockers.extend(child_blockers)
    return status, sorted(set(blockers))


def _artifact_state(project_root: Path, path_value: str) -> dict[str, Any]:
    path = project_root / path_value
    state: dict[str, Any] = {
        "path": path_value,
        "exists": path.exists(),
        "status": "missing",
        "blockers": [],
    }
    if not path.exists():
        return state
    stat = path.stat()
    state.update({
        "size": stat.st_size,
        "mtime": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
        "status": "exists",
    })
    if path.suffix.lower() == ".json":
        parsed = _load_json(path)
        if parsed is None:
            state["status"] = "invalid"
            state["blockers"] = ["json_parse_failed"]
        else:
            report_status, blockers = _scan_report_status(parsed)
            state["status"] = report_status
            state["blockers"] = blockers
    return state


def _load_run_log(project_root: Path) -> dict[str, dict[str, Any]]:
    path = project_root / RUN_LOG_PATH
    latest: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return latest
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except Exception:
            continue
        node_id = event.get("node_id") or event.get("node")
        if not node_id:
            continue
        latest[str(node_id)] = event
    return latest


def build_state_index(project_root: Path, workflow_path: Path | None = None) -> dict[str, Any]:
    workflow_path = workflow_path or project_root / WORKFLOW_PATH
    workflow = _load_json(workflow_path)
    if not isinstance(workflow, dict):
        workflow = {"nodes": []}
    raw_nodes = workflow.get("nodes")
    nodes = raw_nodes if isinstance(raw_nodes, list) else []
    run_latest = _load_run_log(project_root)
    specs_dir = project_root / NODE_SPECS_DIR
    freshness = freshness_states(project_root, workflow)

    indexed_nodes = []
    workflow_node_ids: set[str] = set()
    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("node_id") or "")
        if not node_id:
            continue
        workflow_node_ids.add(node_id)
        spec_path = specs_dir / f"{node_id}.md"
        spec_text = _read_text(spec_path)
        artifacts = [_artifact_state(project_root, path) for path in _artifact_paths(node.get("exit_artifacts"))]
        artifact_statuses = {item["status"] for item in artifacts}
        if "missing" in artifact_statuses:
            readiness = "missing"
        elif artifact_statuses & {"blocked", "invalid"}:
            readiness = "blocked"
        else:
            readiness = "complete"
        node_freshness = freshness.get(node_id)
        if not freshness_admits(node_freshness):
            readiness = 'blocked'
            for artifact in artifacts:
                artifact['status'] = 'stale'
                artifact['blockers'].append(_freshness_blocker(node_freshness))
        indexed_nodes.append({
            "node_id": node_id,
            "goal": node.get("goal"),
            "capability": node.get("capability"),
            "hard_blocked_by": node.get("hard_blocked_by") or [],
            "alignment_refs": node.get("alignment_refs") or [],
            "exit_artifacts": _artifact_paths(node.get("exit_artifacts")),
            "spec_exists": spec_path.exists(),
            "spec_hash": _sha256_text(spec_text) if spec_text else None,
            "spec_frontmatter": _frontmatter(spec_text),
            "artifact_readiness": readiness,
            "freshness": node_freshness,
            "artifacts": artifacts,
            "latest_run_event": run_latest.get(node_id),
        })

    orphan_specs = []
    if specs_dir.is_dir():
        for spec_path in sorted(specs_dir.glob("*.md")):
            if spec_path.stem not in workflow_node_ids:
                text = _read_text(spec_path)
                orphan_specs.append({
                    "node_id": spec_path.stem,
                    "spec_hash": _sha256_text(text),
                    "spec_frontmatter": _frontmatter(text),
                })

    return {
        "schema_version": 1,
        "generated_at": _now(),
        "workflow_path": str(workflow_path.relative_to(project_root)) if workflow_path.is_relative_to(project_root) else str(workflow_path),
        "goals": workflow.get("goals") or [],
        "node_count": len(indexed_nodes),
        "nodes": indexed_nodes,
        "orphan_specs": orphan_specs,
        "transition_log_count": len(workflow.get("transition_log") or []),
    }


def _freshness_blocker(freshness: dict | None) -> str:
    admission = (freshness or {}).get("admission")
    if admission == "invalid":
        return "invalid_source_inputs"
    if admission == "missing":
        return "missing_source_inputs"
    return "input_freshness"


def _repair_fields(freshness: dict | None) -> dict[str, Any]:
    """The explicit difference and repair owner of withheld completion, when known."""
    fields: dict[str, Any] = {}
    if isinstance(freshness, dict):
        if isinstance(freshness.get("diff"), dict):
            fields["diff"] = freshness["diff"]
        if isinstance(freshness.get("repair"), dict):
            fields["repair_owner"] = freshness["repair"].get("owner")
            fields["repair_responsibilities"] = freshness["repair"].get("responsibilities", [])
        # Source changed outside the flow is carried as its own state: an unverified
        # impact is not the ordinary repair its diff resembles.
        if freshness.get("external") in ("conflict", "unverified"):
            fields["external_change"] = freshness["external"]
    return fields


def _candidate_nodes(project_root: Path, candidate_workflow: Path | None) -> dict[str, dict[str, Any]]:
    if not candidate_workflow:
        return {}
    workflow = _load_json(candidate_workflow)
    if not isinstance(workflow, dict):
        return {}
    raw_nodes = workflow.get("nodes")
    nodes = raw_nodes if isinstance(raw_nodes, list) else []
    return {
        str(node.get("node_id")): node
        for node in nodes
        if isinstance(node, dict) and node.get("node_id")
    }


def build_reconciliation_plan(project_root: Path, state_index: dict[str, Any], candidate_workflow: Path | None = None) -> dict[str, Any]:
    current_by_id = {node["node_id"]: node for node in state_index.get("nodes", [])}
    candidate_by_id = _candidate_nodes(project_root, candidate_workflow)
    plan_items: list[dict[str, Any]] = []

    if candidate_by_id:
        all_ids = sorted(set(current_by_id) | set(candidate_by_id))
        for node_id in all_ids:
            current = current_by_id.get(node_id)
            candidate = candidate_by_id.get(node_id)
            if current and candidate:
                action = "keep"
                reasons = []
                if current.get("goal") != candidate.get("goal") or current.get("capability") != candidate.get("capability"):
                    action = "update"
                    reasons.append("goal_or_capability_changed")
                if current.get("exit_artifacts") != _artifact_paths(candidate.get("exit_artifacts")):
                    action = "update"
                    reasons.append("exit_artifacts_changed")
                if current.get("artifact_readiness") in {"blocked", "missing"}:
                    reasons.append(f"current_artifacts_{current.get('artifact_readiness')}")
                item = {"node_id": node_id, "action": action, "reasons": reasons}
                if not freshness_admits(current.get('freshness')):
                    item["action"] = 'invalidate'
                    reasons.append(_freshness_blocker(current['freshness']))
                    item.update(_repair_fields(current['freshness']))
                plan_items.append(item)
            elif candidate:
                plan_items.append({"node_id": node_id, "action": "add", "reasons": ["candidate_only"]})
            else:
                action = "remove"
                reasons = ["missing_from_candidate"]
                if current and current.get("artifact_readiness") == "complete":
                    action = "supersede"
                    reasons.append("completed_current_node_requires_audit")
                plan_items.append({"node_id": node_id, "action": action, "reasons": reasons})
    else:
        for node in state_index.get("nodes", []):
            readiness = node.get("artifact_readiness")
            action = "keep"
            reasons = ["no_candidate_workflow"]
            if readiness in {"blocked", "missing"}:
                action = "invalidate"
                reasons.append(f"artifact_readiness={readiness}")
            item = {"node_id": node["node_id"], "action": action, "reasons": reasons}
            if not freshness_admits(node.get("freshness")):
                item["action"] = "invalidate"
                reasons.append(_freshness_blocker(node.get("freshness")))
                item.update(_repair_fields(node.get("freshness")))
            plan_items.append(item)

    for orphan in state_index.get("orphan_specs", []):
        plan_items.append({
            "node_id": orphan["node_id"],
            "action": "remove",
            "reasons": ["orphan_node_spec"],
        })

    return {
        "schema_version": 1,
        "generated_at": _now(),
        "candidate_workflow": str(candidate_workflow) if candidate_workflow else None,
        "summary": {
            action: sum(1 for item in plan_items if item["action"] == action)
            for action in sorted({item["action"] for item in plan_items})
        },
        "items": plan_items,
        "write_policy": "audit-first; bootstrap must not silently overwrite existing workflow without this plan",
    }


def render_plan_md(plan: dict[str, Any]) -> str:
    lines = [
        "# Workflow Reconciliation Plan",
        "",
        f"- generated_at: `{plan.get('generated_at')}`",
        f"- candidate_workflow: `{plan.get('candidate_workflow') or 'none'}`",
        f"- write_policy: {plan.get('write_policy')}",
        "",
        "## Summary",
        "",
    ]
    for action, count in sorted((plan.get("summary") or {}).items()):
        lines.append(f"- {action}: {count}")
    lines.extend(["", "## Items", ""])
    for item in plan.get("items", []):
        reasons = ", ".join(item.get("reasons") or [])
        lines.append(f"- `{item.get('node_id')}`: **{item.get('action')}** — {reasons}")
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--candidate-workflow", default=None)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    project_root = Path(args.project_root).resolve()
    candidate = Path(args.candidate_workflow).resolve() if args.candidate_workflow else None
    state = build_state_index(project_root)
    plan = build_reconciliation_plan(project_root, state, candidate)

    if args.write:
        _write_json(project_root / STATE_INDEX_PATH, state)
        _write_json(project_root / RECONCILIATION_JSON_PATH, plan)
        (project_root / RECONCILIATION_MD_PATH).write_text(render_plan_md(plan), encoding="utf-8")

    print(json.dumps({"state_index": state, "reconciliation_plan": plan}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
