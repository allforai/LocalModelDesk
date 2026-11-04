#!/usr/bin/env python3
"""Check exit_artifacts for workflow nodes.

Usage:
  python check_artifacts.py <workflow.json> [--node <node_id>] [--json]

Without --node: checks all nodes, prints summary.
With --node: checks one node's exit_artifacts.

The --json output additionally carries a read-only measurement surface an independent
gate can compare across an attempt: ``artifacts[].digest`` (sha256 of the file bytes,
null when the target is missing, unreadable or outside the project) and, on the node's
freshness object, ``binding_identity``/``binding_kind`` (the identity of the recorded
observation its ``readiness_status`` is judged against). Measuring never observes,
registers a read, or publishes anything.
"""

import argparse
import fnmatch
import hashlib
import json
import os
import stat
import subprocess
import sys
from pathlib import Path


BLOCKING_STATUS_VALUES = {
    "accepted_with_gaps",
    "accepted_with_warnings",
    "blocked",
    "conditional_pass",
    "degraded",
    "failed",
    "failed_validation",
    "failed_env",
    "incomplete",
    "not_generated",
    "not_ready",
    "partial",
    "partial_pass",
    "placeholder",
    "existence_only",
    "not_good_enough",
    "quality_failed",
    "needs_revision",
    "passed_with_warnings",
    "revision-requested",
    "spec_only",
    "spec_ready",
}

STATUS_FIELDS = (
    "status",
    "qa_status",
    "overall_status",
    "repair_status",
    "revalidation_status",
    "overall_launch_status",
    "validation_status",
    "acceptance_state",
    "quality_status",
    "effect_status",
    "experience_status",
    "visual_quality_status",
)

# The two critique stage gates. Reports write them at the top level or under
# `gates`, so `_production_gap_error` reads both places for these fields only.
MUST_FIX_GATE_FIELDS = ("must_fix_before_implementation", "must_fix_before_release")

PRODUCTION_GAP_FIELDS = (
    "asset_gaps",
    "audio_gaps",
    "code_gaps",
    "contract_gaps",
    "gaps",
    "warnings",
    "non_blocking_warnings",
    "known_gaps",
    "remaining_gaps",
    "test_gaps",
    "unresolved_findings",
    "degraded_contracts",
    "blockers",
    "major_findings",
    "quality_gaps",
    "effect_gaps",
    "experience_gaps",
    "visual_quality_gaps",
    "perceptual_gaps",
    # The concept-acceptance coverage gate: behaviour mappings with no evidence. A
    # non-empty list is that gate's QA verdict, never a score (ADR 0008).
    "missing_mappings",
    # Stage gates of the experience/creative critique: non-empty means not passed.
    *MUST_FIX_GATE_FIELDS,
)

FORBIDDEN_PRODUCTION_GAP_TERMS = (
    "absent",
    "borrowed",
    "conditional pass",
    "debug scene",
    "degraded",
    "fallback",
    "generic",
    "generic placeholder",
    "not good enough",
    "quality gap",
    "quality failed",
    "existence only",
    "function only",
    "structure only",
    "looks wrong",
    "does not match concept",
    "graphics",
    "missing",
    "not delivered",
    "not_generated",
    "placeholder",
    "prototype",
    "prototypeboard",
    "pure-color",
    "sample scene",
    "silent",
    "spec_ready",
    "stub",
    "tween fallback",
    "缺失",
    "未完成",
    "未生成",
    "未修复",
    "未处理",
    "待处理",
    "剩余",
    "降级",
    "占位",
    "警告",
)

ALLOWED_PRODUCTION_GAP_FLAGS = (
    "allowed_by_production_policy",
    "explicitly_approved_for_launch",
    "prototype_mode_allowed",
)

STALE_SENSITIVE_ARTIFACT_MARKERS = (
    ".allforai/game-2d/assembly/",
    ".allforai/game-2d/qa/",
    ".allforai/game-2d/repair/",
    ".allforai/game-frontend/assembly/",
    ".allforai/game-frontend/qa/",
    ".allforai/visual-qa/",
)

STALE_SOURCE_DIRS = (
    "game-client/assets/scripts",
    "game-client/assets/scenes",
    "game-client/assets/resources",
    "assets/scripts",
    "assets/scenes",
    "assets/resources",
    "src",
)


def _resolve_path(path: str, project_root: Path | None = None) -> str:
    if os.path.isabs(path) or project_root is None:
        return path
    return str(project_root / path)


DIGEST_CHUNK = 1 << 20


def _contained(resolved, project_root: Path | None) -> bool:
    """True when the target stays inside the project, following symlinks.

    An artifact reached through a symlink that leaves the project is not this
    project's evidence, so it is refused rather than measured.
    """
    if project_root is None:
        return True
    try:
        return Path(resolved).resolve().is_relative_to(project_root.resolve())
    except OSError:
        return False


def artifact_digest(path: str, project_root: Path | None = None) -> tuple:
    """(sha256 of the file bytes, reason) for one artifact; never both set.

    Read-only and fail-closed: a missing, unreadable or escaped target measures as
    ``None`` with the reason why, never as an omitted field or a silent pass.

    The bytes are read from the descriptor the containment check accepted, and the
    resolved path is re-stat'ed against that descriptor's identity, so a target
    swapped between the check and the read is refused rather than measured. A swap
    inside a parent directory during the read window remains possible; a project
    that can rewrite its own tree mid-measurement is outside what this can prove.
    """
    try:
        resolved = Path(path).resolve()
    except OSError as exc:
        return None, "unreadable: " + str(exc)
    if not _contained(resolved, project_root):
        return None, "outside project root"
    handle = None
    try:
        # A FIFO must reach fstat without waiting for a writer. Nonblocking mode
        # has no effect on regular-file reads; non-regular descriptors are refused.
        handle = os.open(resolved, os.O_RDONLY | getattr(os, "O_NONBLOCK", 0))
        opened = os.fstat(handle)
        if not stat.S_ISREG(opened.st_mode):
            return None, "missing"
        named = os.stat(resolved)
        if (named.st_dev, named.st_ino) != (opened.st_dev, opened.st_ino):
            return None, "unreadable: target changed while it was being measured"
        digest = hashlib.sha256()
        while True:
            chunk = os.read(handle, DIGEST_CHUNK)
            if not chunk:
                break
            digest.update(chunk)
    except FileNotFoundError:
        return None, "missing"
    except IsADirectoryError:
        return None, "missing"
    except OSError as exc:
        return None, "unreadable: " + str(exc)
    finally:
        if handle is not None:
            os.close(handle)
    return digest.hexdigest(), None


# The recorded observation's shape, owned by evidence_freshness: ``snapshot`` builds
# exactly these keys, ``session`` refuses any kind outside this set, and ``evaluate``
# reads an absent kind as evidence. Measuring validates against that contract instead
# of asserting one of its own; a record that does not match it can never equal a
# current snapshot, so it is refused rather than digested into an identity.
SNAPSHOT_CONTAINERS = ("files", "requirements", "baseline_scope", "upstream")
OBSERVATION_KINDS = ("contract", "evidence")
DEFAULT_OBSERVATION_KIND = "evidence"


def _recorded_observation(record) -> tuple:
    """(inputs, kind) of a well-formed record, or (None, None)."""
    if not isinstance(record, dict) or not isinstance(record.get("inputs"), dict):
        return None, None
    inputs = record["inputs"]
    if any(not isinstance(inputs.get(key), dict) for key in SNAPSHOT_CONTAINERS):
        return None, None
    if not isinstance(inputs.get("contract"), str) or not inputs["contract"]:
        return None, None
    kind = record.get("kind", DEFAULT_OBSERVATION_KIND)
    if kind not in OBSERVATION_KINDS:
        return None, None
    return inputs, kind


def recorded_binding(project_root: Path | None, node_id: str, state_text: str | None = None) -> tuple:
    """(identity, kind) of the observation this node's freshness is judged against.

    The identity is a stable digest over the recorded observation's inputs and its
    kind — the same record and the same precedence ``evidence_freshness.evaluate``
    uses for ``readiness_status``, so the two answer different questions about the
    same observation: what the node is bound to, and whether that binding still
    holds. A digest of the delivered bytes cannot answer either.

    Reading the state has no side effect. Pass ``state_text`` to measure the exact
    bytes a caller already read, so the identity and the readiness judged beside it
    describe one observation. An unreadable state, a record whose shape is not the
    recorded observation ``evidence_freshness`` writes, a kind outside its own set,
    or a node with no record all measure as ``(None, None)``.
    """
    if project_root is None or not node_id:
        return None, None
    try:
        from evidence_freshness import digest as canonical_digest
    except ImportError:
        return None, None
    if state_text is None:
        state_text = read_state_text(project_root)
    if state_text is None:
        return None, None
    try:
        state = json.loads(state_text)
    except ValueError:
        return None, None
    if not isinstance(state, dict):
        return None, None
    contracts = state.get("contracts") if isinstance(state.get("contracts"), dict) else {}
    nodes = state.get("nodes") if isinstance(state.get("nodes"), dict) else {}
    inputs, kind = _recorded_observation(contracts.get(node_id) or nodes.get(node_id))
    if inputs is None:
        return None, None
    try:
        return canonical_digest({"kind": kind, "inputs": inputs}), kind
    except (TypeError, ValueError):
        return None, None


def read_state_text(project_root: Path | None) -> str | None:
    """The freshness state exactly as it is on disk, or None when it cannot be read."""
    if project_root is None:
        return None
    try:
        return (project_root / FRESHNESS_STATE).read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None


def _artifact_status_error(path: str, project_root: Path | None = None) -> dict | None:
    if not path.endswith(".json") or not os.path.exists(path):
        return None
    stale_error = _stale_runtime_artifact_error(path, project_root)
    if stale_error:
        return stale_error
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as exc:
        return {"field": "$", "value": None, "reason": "invalid or unreadable JSON artifact: " + str(exc)}
    if not isinstance(data, dict):
        return None
    if not data:
        return {
            "field": "$",
            "value": {},
            "reason": "empty JSON artifact is not a valid completion report or contract",
        }
    for field in STATUS_FIELDS:
        value = data.get(field)
        if isinstance(value, str) and (
            value.lower() in BLOCKING_STATUS_VALUES or value.lower().startswith("blocked_by_")
        ):
            return {
                "field": field,
                "value": value,
                "reason": "artifact report status is blocking; file existence is not completion",
            }
    gap_error = _production_gap_error(data)
    if gap_error:
        return gap_error
    return None


def _stale_runtime_artifact_error(path: str, project_root: Path | None) -> dict | None:
    if project_root is None:
        return None
    try:
        rel_path = str(Path(path).resolve().relative_to(project_root.resolve()))
    except Exception:
        return None
    if not any(marker in rel_path for marker in STALE_SENSITIVE_ARTIFACT_MARKERS):
        return None
    artifact_mtime = os.path.getmtime(path)
    newest_source: tuple[str, float] | None = None
    for rel_dir in STALE_SOURCE_DIRS:
        source_dir = project_root / rel_dir
        if not source_dir.exists():
            continue
        for root, dirs, files in os.walk(source_dir):
            dirs[:] = [d for d in dirs if d not in {"node_modules", "library", "temp", "build"}]
            for name in files:
                if not name.endswith((".ts", ".js", ".json", ".scene", ".prefab", ".png", ".jpg", ".jpeg", ".webp", ".mp3", ".wav", ".ogg")):
                    continue
                full_path = os.path.join(root, name)
                mtime = os.path.getmtime(full_path)
                if mtime > artifact_mtime and (newest_source is None or mtime > newest_source[1]):
                    newest_source = (str(Path(full_path).relative_to(project_root)), mtime)
    if newest_source is None:
        return None
    return {
        "field": "$mtime",
        "value": rel_path,
        "newer_source": newest_source[0],
        "reason": "runtime/visual QA artifact is stale because source or asset files changed after it was written",
    }


def _allowed_gap(item) -> bool:
    if not isinstance(item, dict):
        return False
    return any(item.get(flag) is True for flag in ALLOWED_PRODUCTION_GAP_FLAGS)


def _gap_text(item) -> str:
    if isinstance(item, str):
        return item.lower()
    if isinstance(item, dict):
        parts = []
        for key, value in item.items():
            if key in ALLOWED_PRODUCTION_GAP_FLAGS:
                continue
            if isinstance(value, (str, int, float, bool)):
                parts.append(str(value))
            elif isinstance(value, list):
                parts.extend(str(v) for v in value if isinstance(v, (str, int, float, bool)))
        return " ".join(parts).lower()
    return ""


def _production_gap_error(data: dict) -> dict | None:
    policy = data.get("production_acceptance_policy")
    allow_gaps = isinstance(policy, dict) and policy.get("allow_placeholder_or_fallback_assets") is True

    for field in PRODUCTION_GAP_FIELDS:
        value = data.get(field)
        if field in MUST_FIX_GATE_FIELDS and value in (None, [], {}) and isinstance(data.get("gates"), dict):
            value = data["gates"].get(field)
        if value in (None, [], {}):
            continue
        if field in {
            "asset_gaps",
            "audio_gaps",
            "blockers",
            "code_gaps",
            "contract_gaps",
            "gaps",
            "major_findings",
            "missing_mappings",
            *MUST_FIX_GATE_FIELDS,
            "remaining_gaps",
            "test_gaps",
            "unresolved_findings",
        }:
            return {
                "field": field,
                "value": value,
                "reason": (
                    "artifact contains unresolved gaps/findings; continue repair and revalidation "
                    "instead of treating file existence as completion"
                ),
            }
        items = value if isinstance(value, list) else [value]
        for item in items:
            if allow_gaps or _allowed_gap(item):
                continue
            text = _gap_text(item)
            matched = [term for term in FORBIDDEN_PRODUCTION_GAP_TERMS if term in text]
            if matched:
                return {
                    "field": field,
                    "value": item,
                    "matched_terms": matched,
                    "reason": (
                        "production artifact contains placeholder/stub/fallback/missing asset gap; "
                        "route to producer skill or explicitly lower scope before completion"
                    ),
                }
    return None


FRESHNESS_FIELDS = ("source_inputs", "input_dependencies", "required_documents")
FRESHNESS_STATE = ".allforai/bootstrap/evidence-freshness.json"
BOOTSTRAP_PROFILE = ".allforai/bootstrap/bootstrap-profile.json"
DECLARE_HINT = "declare project-relative source paths or globs, or explicit [] when no product source is relevant"


def input_declaration_errors(node: dict) -> list:
    """Shape errors for a node's freshness declarations; empty when well-formed.

    A declaration is a list of non-empty project-relative paths or globs. An
    explicit empty list is a valid statement that no such input exists.
    """
    errors = []
    for field in FRESHNESS_FIELDS:
        if field not in node:
            continue
        value = node[field]
        if not isinstance(value, list) or any(not isinstance(p, str) or not p.strip() for p in value):
            errors.append(f"'{field}' must be a list of non-empty project-relative paths or globs; {DECLARE_HINT}")
            continue
        for path in value:
            if os.path.isabs(path) or ".." in path.replace(os.sep, "/").split("/"):
                errors.append(f"'{field}' entry {path!r} must be a relative project path without '..'")
    errors.extend(parallel_write_declaration_errors(node))
    errors.extend(document_verification_errors(node))
    return errors


def parallel_write_declaration_errors(node: dict) -> list:
    """Optional Codex draft write contract; shared reads do not grant write access."""
    if "parallel_write_scopes" not in node:
        return []
    scopes = node["parallel_write_scopes"]
    def control(p):
        return p.rstrip("/") in {".allforai", ".codex"} or (p.startswith(".allforai/") and not p.startswith(".allforai/bootstrap/artifacts/")) or p.startswith(".codex/")
    if not isinstance(scopes, list) or not scopes or any(
        not isinstance(p, str) or not p or p.strip() != p or os.path.isabs(p)
        or ".." in Path(p).parts or p.removeprefix("./").rstrip("/") in {"", "."}
        or control(p.removeprefix("./")) for p in scopes
    ):
        return ["'parallel_write_scopes' must be a non-empty list of safe project-relative write paths or globs, excluding driver control state"]
    scopes = [p.removeprefix("./").rstrip("/") for p in scopes]
    artifacts = node.get("exit_artifacts", [])
    outputs = [a.get("path", "") if isinstance(a, dict) else a for a in artifacts] if isinstance(artifacts, list) else []
    for field in ("required_documents", "required_docs"):
        values = node.get(field)
        if isinstance(values, list):
            outputs += [p.get("path", "") if isinstance(p, dict) else p for p in values]
    errors = []
    for path in outputs:
        if not isinstance(path, str) or not path:
            continue  # Existing artifact/document shape validators own this error.
        path = path.removeprefix("./").rstrip("/")
        if not control(path) and not any(path == p or path.startswith(p + "/") or fnmatch.fnmatchcase(path, p) for p in scopes):
            errors.append(f"'parallel_write_scopes' does not cover declared output {path!r}")
    return errors


def document_verification_errors(node: dict) -> list:
    """A required document must declare how it is checked against current source.

    ``document_verification`` maps each ``required_documents`` path to a non-empty
    argv that executes the document's stated facts against the code. Declaring
    the document alone is a responsibility, not proof of synchronization.
    """
    errors = []
    documents = node.get("required_documents")
    documents = [p for p in documents if isinstance(p, str) and p.strip()] if isinstance(documents, list) else []
    declared = node.get("document_verification")
    if "document_verification" in node and not isinstance(declared, dict):
        errors.append("'document_verification' must be an object mapping required documents to argv lists")
        declared = {}
    declared = declared if isinstance(declared, dict) else {}
    for path, argv in declared.items():
        if path not in documents:
            errors.append(f"'document_verification' entry {path!r} is not a declared required document")
        if not isinstance(argv, list) or not argv or any(not isinstance(s, str) or not s.strip() for s in argv):
            errors.append(f"'document_verification' for {path!r} must be a non-empty argv list that checks "
                          "the document against current source")
    for path in documents:
        if path not in declared:
            errors.append(f"'required_documents' entry {path!r} has no document_verification argv; declare a "
                          "project-specific check of that document against current source")
    return errors


def _completed_nodes(workflow: dict) -> set:
    """Nodes whose latest transition is completed, folding both native log formats.

    Malformed history never completes a node: scope validation rejects it
    separately, and an unreadable label cannot exempt work from declaring.
    """
    last_status: dict = {}
    log = workflow.get("transition_log")
    for event in log if isinstance(log, list) else []:
        if not isinstance(event, dict):
            continue
        node_id = event.get("node_id", event.get("node"))
        if isinstance(node_id, str):
            last_status[node_id] = event.get("status")
    return {node_id for node_id, status in last_status.items() if status == "completed"}


def _scope_refs(project_root: Path) -> list | None:
    """Current task_scope requirement refs from the bootstrap profile; None when unknown."""
    try:
        with open(project_root / BOOTSTRAP_PROFILE, encoding="utf-8") as handle:
            profile = json.load(handle)
    except (OSError, ValueError):
        return None
    scope = profile.get("task_scope") if isinstance(profile, dict) else None
    refs = scope.get("requirement_refs") if isinstance(scope, dict) else None
    return refs if isinstance(refs, list) else None


def _load_records(project_root: Path) -> tuple:
    """(recorded node ids, error). A missing state file records nothing; an
    unreadable or unknown-shaped one returns (None, reason) so gates fail closed."""
    path = project_root / FRESHNESS_STATE
    if not path.exists():
        return set(), None
    try:
        with open(path, encoding="utf-8") as handle:
            state = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, f"{FRESHNESS_STATE} is unreadable: {exc}"
    if not isinstance(state, dict):
        return None, f"{FRESHNESS_STATE} must be a JSON object"
    recorded: set = set()
    for bucket in ("nodes", "contracts"):
        records = state.get(bucket, {})
        if not isinstance(records, dict) or not all(
                isinstance(k, str) and isinstance(v, dict) for k, v in records.items()):
            return None, f"{FRESHNESS_STATE} '{bucket}' has an unknown record shape"
        recorded.update(records)
    return recorded, None


def _current_scope_work(node: dict, completed: set, scope_refs: list | None) -> bool:
    """Whether the node consumes requirements as current work: any consumer that
    is not completed, or a completed consumer of the current task scope. Unknown
    scope cannot prove a completed consumer historical, so it counts as current."""
    refs = node.get("requirement_refs")
    if not refs:
        return False
    if node.get("node_id") not in completed:
        return True
    return scope_refs is None or not isinstance(refs, list) or any(ref in scope_refs for ref in refs)


def _admission(node: dict, completed: set, scope_refs: list | None, recorded: set) -> str:
    if input_declaration_errors(node):
        return "invalid"
    if "source_inputs" in node:
        return "declared"
    partial = any(field in node for field in FRESHNESS_FIELDS)
    withdrawn = node.get("node_id") in recorded
    return "missing" if partial or withdrawn or _current_scope_work(node, completed, scope_refs) else "legacy"


def freshness_admission(node: dict, workflow: dict, project_root: Path | None = None) -> str:
    """How freshness admits a node: declared, missing, invalid, or legacy.

    Intent-aware work must declare source_inputs: any node consuming
    requirement_refs that is not completed, a completed consumer of the current
    task scope, and any node with a published freshness record. A completion
    label alone is not provenance. Only retained history outside the current
    scope with no record is legacy, and no provenance is claimed for it. Without
    ``project_root`` the scope and records are read from the working directory,
    where the generated runtime runs its gates.
    """
    root = Path(project_root) if project_root is not None else Path.cwd()
    recorded, _ = _load_records(root)
    return _admission(node, _completed_nodes(workflow), _scope_refs(root), recorded or set())


def freshness_states(project_root: Path, workflow: dict) -> dict:
    """Per-node freshness consumed by the artifact, readiness and reconciliation gates.

    Returns {} for a legacy workflow with no declarations and no freshness state.
    Otherwise every node gets a dict with status, readiness_status, admission and
    reason. Malformed declarations, an unreadable freshness state, or a failing
    evaluation fail closed as ``invalid`` for every admitted node instead of
    crashing or passing.
    """
    nodes = [n for n in (workflow.get("nodes") or []) if isinstance(n, dict) and n.get("node_id")]
    completed = _completed_nodes(workflow)
    scope_refs = _scope_refs(project_root)
    recorded, state_error = _load_records(project_root)
    admissions = {n["node_id"]: _admission(n, completed, scope_refs, recorded or set()) for n in nodes}
    if not (project_root / FRESHNESS_STATE).exists() and all(a == "legacy" for a in admissions.values()):
        # Legacy history keeps its pre-freshness gate only while the dynamic-read
        # register is readable: an unreadable register hides dependency impact.
        # Older projects may copy this gate alone. An absent register needs no
        # freshness helper; a present register still requires full validation.
        if not (project_root / ".allforai/bootstrap/observed-input-dependencies.json").exists():
            return {}
        from evidence_freshness import observed_reads
        try:
            observed_reads(project_root)
        except (ValueError, OSError):
            pass
        else:
            return {}
    states = {}
    invalid = {n["node_id"]: input_declaration_errors(n) for n in nodes if admissions[n["node_id"]] == "invalid"}
    evaluated: dict = {}
    failure = None
    if invalid:
        failure = "malformed declaration on " + ", ".join(f"{k}: {'; '.join(v)}" for k, v in sorted(invalid.items()))
    elif state_error:
        failure = "freshness state unreadable: " + state_error
    else:
        from evidence_freshness import evaluate
        try:
            evaluated = evaluate(project_root)["nodes"]
        except (ValueError, KeyError, TypeError, AttributeError, OSError, StopIteration) as exc:
            failure = f"freshness evaluation failed: {exc}"
    for node in nodes:
        node_id = node["node_id"]
        admission = admissions[node_id]
        if admission == "invalid":
            states[node_id] = {"status": "invalid", "readiness_status": "invalid", "admission": admission,
                               "reason": "Malformed input declaration: " + "; ".join(invalid[node_id])}
        elif admission == "missing":
            reason = ("Missing source_inputs: the node was published with a declaration that is now absent; "
                      if node_id in (recorded or set()) else "Missing source_inputs: impact is uncertain; ")
            states[node_id] = {"status": "undeclared", "readiness_status": "undeclared", "admission": admission,
                               "reason": reason + DECLARE_HINT}
        elif failure:
            states[node_id] = {"status": "invalid", "readiness_status": "invalid", "admission": admission,
                               "reason": "Freshness cannot be evaluated: " + failure}
        elif admission == "legacy":
            states[node_id] = {"status": "undeclared", "readiness_status": "undeclared", "admission": admission,
                               "reason": "Retained legacy node without source declarations; no provenance claimed"}
        else:
            states[node_id] = {**evaluated.get(node_id, {"status": "stale", "readiness_status": "stale"}),
                               "admission": admission}
    return states


def freshness_admits(freshness) -> bool:
    """True when freshness does not withhold completion.

    Absent freshness keeps the pre-freshness gate; a declared node admits only
    ``valid``; a legacy node admits only its own ``undeclared`` state, never an
    evaluated stale, invalid or unknown status. Anything else fails closed.
    """
    if freshness is None:
        return True
    if not isinstance(freshness, dict):
        return False
    admission = freshness.get("admission", "declared")
    status = freshness.get("status")
    if admission == "legacy":
        return status == "undeclared"
    return admission == "declared" and status == "valid"


def _load_workflow(project_root: Path):
    path = project_root / ".allforai/bootstrap/workflow.json"
    try:
        with open(path, encoding="utf-8") as handle:
            workflow = json.load(handle)
    except (OSError, ValueError):
        return None
    return workflow if isinstance(workflow, dict) else None


def check_node_artifacts(node: dict, project_root: Path | None = None) -> dict:
    """Check if a node's exit_artifacts all exist."""
    node_id = node.get("node_id")
    if not node_id:
        raise ValueError("workflow node missing required node_id")
    artifacts = node.get("exit_artifacts", [])
    results = []
    for item in artifacts:
        if isinstance(item, dict):
            path = item["path"]
            validation_commands = item.get("validation_commands", [])
        else:
            path = item
            validation_commands = []
        resolved_path = _resolve_path(path, project_root)
        entry = {"path": path, "exists": os.path.isfile(resolved_path)}
        # Additive measurement: existence cannot tell a fresh delivery from a
        # pre-existing or touched leftover, and mtime is not content.
        entry["digest"], digest_error = artifact_digest(resolved_path, project_root)
        if digest_error:
            entry["digest_error"] = digest_error
        if entry["exists"]:
            status_error = _artifact_status_error(resolved_path, project_root)
            if status_error:
                entry["status_error"] = status_error
            if isinstance(item, dict) and (item.get("required_fields") or item.get("accepted_statuses")):
                try:
                    with open(resolved_path, encoding="utf-8") as handle:
                        data = json.load(handle)
                    if not isinstance(data, dict):
                        raise ValueError("report must be a JSON object")
                    if any(key not in data for key in item.get("required_fields", [])):
                        raise ValueError("report missing required fields")
                    allowed = item.get("accepted_statuses")
                    if allowed and data.get("status") not in allowed:
                        raise ValueError("report status is not explicitly accepted")
                except (ValueError, TypeError, OSError) as exc:
                    entry["status_error"] = {"field": "$", "reason": str(exc)}
        if validation_commands and entry["exists"]:
            for cmd in validation_commands:
                try:
                    proc = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        cwd=str(project_root) if project_root else None,
                        timeout=300,
                    )
                except (subprocess.TimeoutExpired, OSError) as exc:
                    entry["validation_error"] = {"command": cmd, "stderr": str(exc)}
                    break
                if proc.returncode != 0:
                    entry["validation_error"] = {
                        "command": cmd,
                        "stderr": proc.stderr.decode(errors="replace"),
                    }
                    break
        results.append(entry)
    freshness = None
    if project_root:
        workflow = _load_workflow(project_root)
        if workflow is None:
            workflow = {"nodes": [node]}
        elif not any(isinstance(n, dict) and n.get("node_id") == node_id for n in workflow.get("nodes") or []):
            workflow = {**workflow, "nodes": [*(workflow.get("nodes") or []), node]}
        # The pair must describe one observation: readiness is evaluated between two
        # reads of the same state bytes, and a rebind landing in that window fails
        # closed to a null binding rather than reporting new identity beside old
        # readiness. freshness_states itself is untouched — the readiness and
        # reconciliation gates consume it unchanged.
        before = read_state_text(project_root)
        freshness = freshness_states(project_root, workflow).get(node_id)
        if isinstance(freshness, dict):
            identity, kind = (None, None)
            if before is not None and before == read_state_text(project_root):
                identity, kind = recorded_binding(project_root, node_id, before)
            freshness = {**freshness, "binding_identity": identity, "binding_kind": kind}
    return {
        "node_id": node_id,
        "goal": node.get("goal", ""),
        "freshness": freshness,
        "all_exist": freshness_admits(freshness) and bool(results) and all(
            r["exists"] and "validation_error" not in r and "status_error" not in r
            for r in results
        ),
        "artifacts": results,
    }


def _project_root_for_workflow(workflow_path: str) -> Path:
    path = Path(workflow_path).resolve()
    if path.name == "workflow.json" and path.parent.name == "bootstrap" and path.parent.parent.name == ".allforai":
        return path.parent.parent.parent
    return Path.cwd()


def main():
    parser = argparse.ArgumentParser(description="Check workflow node exit artifacts")
    parser.add_argument("workflow_path", help="Path to workflow.json")
    parser.add_argument("--node", dest="node_id", help="Check specific node only")
    parser.add_argument("--json", dest="output_json", action="store_true")
    args = parser.parse_args()

    with open(args.workflow_path) as f:
        wf = json.load(f)

    nodes = wf.get("nodes", [])
    project_root = _project_root_for_workflow(args.workflow_path)

    if args.node_id:
        node = next((n for n in nodes if n.get("node_id") == args.node_id), None)
        if not node:
            print(f"Node '{args.node_id}' not found", file=sys.stderr)
            sys.exit(2)  # 2 = actual error (node not found), not "pending"
        result = check_node_artifacts(node, project_root)
        if args.output_json:
            print(json.dumps(result, indent=2))
            sys.exit(0)  # --json always exits 0; status is in the JSON
        else:
            status = "DONE" if result["all_exist"] else "PENDING"
            print(f"[{status}] {result['node_id']}: {result['goal']}")
            for a in result["artifacts"]:
                mark = "\u2713" if a["exists"] else "\u2717"
                print(f"  {mark} {a['path']}")
            sys.exit(0 if result["all_exist"] else 1)
    else:
        results = [check_node_artifacts(n, project_root) for n in nodes]
        done = sum(1 for r in results if r["all_exist"])
        total = len(results)
        if args.output_json:
            print(json.dumps({"done": done, "total": total, "nodes": results}, indent=2))
            sys.exit(0)  # --json always exits 0; status is in the JSON
        else:
            print(f"Progress: {done}/{total} nodes complete\n")
            for r in results:
                status = "DONE" if r["all_exist"] else "PENDING"
                print(f"  [{status}] {r['node_id']}: {r['goal']}")
            sys.exit(0 if done == total else 1)


if __name__ == "__main__":
    main()
