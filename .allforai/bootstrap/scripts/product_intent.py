"""Shared validation of explicit bootstrap scope; never infers user decisions."""
from pathlib import Path
import json
from typing import Any



def _is_local_session(root, profile):
    """True when this project's scope is a hand-projected local requirement set.

    `intent_session_path` is written only when THIS CLI creates the profile (see the local-change
    branch of the draft path). An actor that generates its own bootstrap-profile.json does not set it,
    and the content check below was gated on it alone — so on a generated profile the deeper
    requirement-drift check never ran and the gate degraded into an integer comparison: bumping a
    requirement revision from 2 to 3 in the profile and the workflow, changing nothing else, turned a
    blocked plan green while the node specs still contained nothing about the new requirement.

    The route is the reliable signal, so fall back to it when the key is absent, requiring the local
    requirement file to actually exist so a mislabelled profile cannot switch the check on by name.
    """
    declared = profile.get("intent_session_path")
    if declared:
        return declared == LOCAL
    # Fall back to the route, but only when the baseline this check reads is actually present.
    # Turning it on without `intent_scope` made a missing CLI-private key surface as invalid_scope,
    # i.e. it converted "the deeper check cannot run here" into "your scope is invalid" — a false
    # accusation dressed as a gate result, which is worse than the hole it was meant to close.
    return (profile.get("task_route") == "local-change"
            and "intent_scope" in profile
            and (Path(root) / LOCAL).exists())


# Limits of what a scope check could verify, for callers that want to say so. Never errors: a caller
# that ignores this list still behaves exactly as before.
SCOPE_ADVISORIES: list = []


def take_scope_advisories():
    """Drain and return advisories recorded by the most recent validate_scope call."""
    drained = list(SCOPE_ADVISORIES)
    SCOPE_ADVISORIES.clear()
    return drained


def validate_scope(project_root, workflow, *, consumed_sources=None):
    """Return typed blockers for the scope consumed by a generated workflow.

    Profiles without the scope contract remain legacy inputs. Their existence is
    not evidence of approval; bootstrap must capture scope before generating new work.
    If supplied, consumed_sources collects journal paths reached through scoped
    requirements; callers may use them only when the returned blockers are empty.
    """
    SCOPE_ADVISORIES.clear()
    root = Path(project_root)
    path = root / ".allforai/bootstrap/bootstrap-profile.json"
    try:
        if not isinstance(workflow, dict):
            raise ValueError("workflow.json must be an object")
        nodes = workflow.get("nodes", [])
        if not isinstance(nodes, list):
            raise ValueError("workflow.json nodes must be a list")
        if any(not isinstance(node, dict) for node in nodes):
            raise ValueError("workflow.json nodes must contain objects")
        for node in nodes:
            inputs = node.get("decision_inputs", [])
            if not isinstance(inputs, list) or any(
                    not isinstance(value, str) or not value.strip() for value in inputs):
                raise ValueError("decision_inputs must be an array of non-empty paths, including retained nodes")
        history = workflow.get("transition_log", [])
        if not isinstance(history, list):
            raise ValueError("workflow.json transition_log must be a list")
        for index, event in enumerate(history):
            if not isinstance(event, dict):
                raise ValueError(f"transition_log[{index}] must be an object")
            node_id = event.get("node_id", event.get("node"))
            if not isinstance(node_id, str) or not node_id.strip():
                raise ValueError(f"transition_log[{index}] needs a non-empty node_id or node")
            if "node_id" in event and "node" in event and event["node"] != node_id:
                raise ValueError(f"transition_log[{index}] has conflicting node_id and node")
            if not isinstance(event.get("status"), str) or not event["status"].strip():
                raise ValueError(f"transition_log[{index}] needs a non-empty status")
        scoped_nodes = any("requirement_refs" in node for node in nodes)
        # A wired but unmade product choice holds every route, including a project
        # that has no scope contract yet; it is never resolved by reaching a later gate.
        pending = _pending_decisions(root, workflow)
        if not path.exists():
            return pending + ([{"code": "invalid_scope", "message": "Scoped nodes require bootstrap-profile.json"}]
                              if scoped_nodes else [])
        profile = json.loads(path.read_text(encoding="utf-8"))
        scope = profile.get("task_scope")
        if "task_scope" not in profile and "task_route" not in profile:
            if scoped_nodes:
                raise ValueError("Scoped nodes require task_route and task_scope")
            return pending
        if profile.get("task_route") not in (
                "local-change", "product-reconstruction", "new-product"):
            return pending + [{"code": "pending_task_route", "message":
                               "Clarify the user's goal at interactive bootstrap; file presence cannot choose the route"}]
        if not isinstance(profile.get("task_goal"), str) or not profile["task_goal"].strip():
            raise ValueError("task_goal must be a non-empty user goal")
        if (not isinstance(scope, dict) or not isinstance(scope.get("areas"), list)
                or not scope["areas"] or any(not isinstance(area, str) or not area.strip()
                                             for area in scope["areas"])
                or not isinstance(scope.get("requirement_refs"), list)):
            raise ValueError("task_scope needs non-empty areas and a requirement_refs array")
        for ref in scope["requirement_refs"]:
            if (not isinstance(ref, dict)
                    or any(not isinstance(ref.get(key), str) or not ref[key].strip()
                           for key in ("path", "id"))
                    or type(ref.get("revision")) is not int or ref["revision"] < 1):
                raise ValueError("requirement_refs need path, id and a positive integer revision")
            requirement_path = Path(ref["path"])
            if (requirement_path.is_absolute()
                    or not (root / requirement_path).resolve().is_relative_to(root.resolve())):
                raise ValueError("requirement paths must stay inside the project")
        # A retained completed branch is historical work, not approval for this
        # request. Reconciliation still owns whether its evidence is reusable.
        # Claude records node_id; the native Codex producer records node.
        # Fold both histories together in log order so reopened work is not retained.
        retained = _retained_nodes(workflow, scope["requirement_refs"])
        blockers = list(pending)
        if _is_local_session(root, profile) and scope["requirement_refs"]:
            blockers.extend(_local_contract(root, workflow, profile, retained=retained))
        elif (profile.get("task_route") == "local-change" and scope["requirement_refs"]
              and "intent_scope" not in profile):
            # Declare the limit of what was checked, as a WARNING rather than a blocker.
            #
            # Blocking here was worse than the hole it closed. Without the baseline this check reads,
            # the gate silently degrades to verifying that the plan POINTS AT the current requirement
            # revision — which a bumped integer satisfies while the node specs still say nothing about
            # the new requirement. But making that a blocker also stopped a plan whose specs HAD
            # absorbed the requirement, giving correct work the same verdict as the bumped integer.
            # A false accusation dressed as a gate result is the more expensive error, so the gap is
            # reported and the caller decides.
            # Advisories must never enter `blockers`: five callers consume that list as errors, and
            # flagging entries in place meant filtering in each one — I filtered a single gate and
            # validate_bootstrap.py promptly reported passed:false on correct work. They go to a
            # separate sink instead, so a caller opts in to reading them rather than opting out.
            SCOPE_ADVISORIES.append({
                "code": "requirement_content_unchecked",
                "message": ("bootstrap-profile.json has no intent_scope baseline, so requirement "
                            "content drift was NOT checked: the plan's revision pointers were verified, "
                            "but not whether the node specs absorbed the requirement. Generate the "
                            "profile through product_intent.py so this gate can assure content")})
        if profile["task_route"] in ("product-reconstruction", "new-product") and scope["requirement_refs"]:
            blockers.extend(_product_contract(root, workflow, profile, retained=retained))
            blockers.extend(_experience_direction_blockers(root, profile, scope["requirement_refs"]))
        if profile["task_route"] != "product-reconstruction":
            for node in workflow.get("nodes", []):
                if node.get("capability") == "reverse-concept" and node.get("node_id") not in retained:
                    blockers.append({"code": "scope_route_conflict", "node_id": node.get("node_id"),
                                     "message": "reverse-concept requires a product-reconstruction goal"})
        if not scope.get("requirement_refs"):
            code = ("pending_requirement" if profile["task_route"] == "local-change"
                    else "pending_product_confirmation")
            blockers.append({"code": code, "message": "No confirmed requirements in the selected scope; return to bootstrap"})
        for ref in scope.get("requirement_refs", []):
            data = json.loads((root / ref["path"]).read_text(encoding="utf-8"))
            related = [item for item in data["requirements"] if item["id"] == ref["id"]]
            revisions = [item["revision"] for item in related]
            consumers = _consumers(workflow, ref)
            if any(type(revision) is not int or revision < 1 for revision in revisions):
                raise ValueError(f"{ref['id']}: invalid requirement revision")
            if not revisions or max(revisions) != ref["revision"]:
                _scoped(blockers, "stale_requirement",
                        f"{ref['id']}: reference does not select the current requirement revision", consumers)
                continue
            if len(revisions) != len(set(revisions)):
                _scoped(blockers, "invalid_requirement", f"{ref['id']}: duplicate requirement revisions", consumers)
                continue
            for item in related:
                if item["id"] == ref["id"] and item["revision"] == ref["revision"]:
                    if (not isinstance(item.get("goal"), str) or not item["goal"].strip()
                            or any(not isinstance(item.get(key), list) or not item[key]
                                   or any(not isinstance(value, str) or not value.strip()
                                          for value in item[key])
                                   for key in ("business_rules", "acceptance", "scope"))):
                        _scoped(blockers, "invalid_requirement",
                                f"{ref['id']}: goal, scope, business_rules and acceptance must be non-empty", consumers)
                    if not set(item.get("scope", [])).intersection(scope.get("areas", [])):
                        _scoped(blockers, "requirement_scope_conflict",
                                f"{ref['id']}: confirmed decision does not apply to this task scope", consumers)
                    confirmation = item.get("confirmation") or {}
                    if (item.get("status") != "confirmed"
                            or confirmation.get("source") != "user"
                            or any(not isinstance(confirmation.get(key), str)
                                   or not confirmation[key].strip()
                                   for key in ("reference", "decision_id", "reason"))):
                        _scoped(blockers, "pending_requirement",
                                f"{ref['id']}: return to interactive bootstrap for confirmation", consumers)
                    elif _journal_reference(confirmation["reference"]):
                        # A forged or malformed reference invalidates the whole scope; a
                        # verified decision that does not record this projection leaves
                        # only its consumers pending until the user confirms it.
                        source, decision = _journal_decision(root, confirmation["reference"])
                        try:
                            _journal_payload(item, decision)
                        except LegacyProjection as exc:
                            _scoped(blockers, "pending_requirement", f"{ref['id']}: {exc}", consumers)
                        except ValueError as exc:
                            _scoped(blockers, "pending_requirement",
                                    f"{ref['id']}: {exc}; return to interactive bootstrap", consumers)
                        if consumed_sources is not None:
                            consumed_sources.add(source)
        for node in workflow.get("nodes", []):
            if node.get("node_id") in retained:
                continue
            refs = node.get("requirement_refs")
            if not isinstance(refs, list) or not refs:
                blockers.append({"code": "scope_requirement_unwired", "node_id": node.get("node_id"),
                                 "message": f"{node.get('node_id')}: new scoped work needs non-empty requirement_refs"})
                continue
            for ref in refs:
                if ref not in scope["requirement_refs"] or ref["path"] not in node.get("decision_inputs", []):
                    blockers.append({"code": "scope_requirement_unwired", "node_id": node.get("node_id"),
                                     "message": "Node requirement must be in task_scope and consumed through decision_inputs"})
            # A node proves the inherited acceptance its own stage can reach; deferring the
            # full effect is allowed, losing it is not. The named owner must carry the same
            # confirmed requirements, so the user's acceptance keeps a final holder. Whether
            # that owner exists, runs later and proves an effect stays the bootstrap gate's
            # structural check on the same declaration.
            if "downstream_effect_owner" in node:
                owner_id = node["downstream_effect_owner"]
                owners = [n for n in workflow.get("nodes", []) if n.get("node_id") == owner_id]
                if len(owners) == 1 and any(ref not in owners[0].get("requirement_refs", []) for ref in refs):
                    blockers.append({"code": "unowned_effect_stage", "node_id": node.get("node_id"), "message":
                                     f"{node.get('node_id')}: deferred full effect names '{owner_id}', which does not "
                                     "consume this node's confirmed requirements; the owner must carry them"})
        if profile["task_route"] == "local-change":
            for ref in scope.get("requirement_refs", []):
                responsibilities = set()
                for node in workflow.get("nodes", []):
                    if ref in node.get("requirement_refs", []):
                        responsibilities.update(node.get("responsibilities", []))
                missing = {"implementation", "documentation", "verification"} - responsibilities
                if missing:
                    blockers.append({"code": "missing_scope_responsibility", "message":
                                     f"{ref['id']}: missing {', '.join(sorted(missing))} responsibility"})
        return blockers
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        return [{"code": "invalid_scope", "message": f"{path}: {exc}"}]


DECISION_KEYS = ("id", "decision", "rationale")  # bootstrap-audits.md:287 Phase A decision artifact
PENDING_STATUSES = ("pending", "unresolved", "open", "deferred")


def _filled(value):
    return isinstance(value, str) and bool(value.strip())


def _claims_decision(payload):
    """Markers that make a record a product choice whatever else its keys look like.

    A queued status is one of them: an artifact that says the choice is still open is a
    choice, and no sibling family's keys may hide it.
    """
    return (any(key in payload for key in ("decision", "rationale"))
            or payload.get("status") in PENDING_STATUSES)


def _coverage_audit(payload):
    """The A0 output `bootstrap-audits.md:264` requires:
    {captured: [{id, node_id}], missing: [{id, rationale, consumer_node}]}."""
    return ("id" not in payload and isinstance(payload.get("captured"), list)
            and isinstance(payload.get("missing"), list)
            and all(isinstance(item, dict)
                    and all(_filled(item.get(key)) for key in ("id", "rationale", "consumer_node"))
                    for item in payload["missing"]))


def _cli_request(payload):
    """A recorded CLI request envelope: it names an operation and has no decision identity."""
    return "id" not in payload and _filled(payload.get("operation"))


def _requirement_source(payload):
    """A requirement file read as an input: {"requirements": [{id, ...}, ...]}."""
    items = payload.get("requirements")
    return ("id" not in payload and isinstance(items, list) and bool(items)
            and all(isinstance(item, dict) and _filled(item.get("id")) for item in items))


def _journal_record(payload):
    """The confirmation journal: a schema version and recorded decision batches."""
    batches = payload.get("batches")
    return (_filled(payload.get("schema_version")) and isinstance(batches, list) and bool(batches)
            and all(isinstance(batch, dict) and _filled(batch.get("batch_id"))
                    and isinstance(batch.get("decisions"), list) for batch in batches))


# Sibling families that share the `decision-*.json` name and record no single product
# choice. Each is recognised by its full contract shape, never by the presence of one
# key: a malformed or half-written sibling is not a licence to stop checking.
NON_DECISION_FAMILIES = (_coverage_audit, _cli_request, _requirement_source)


def decision_record(project_root, path):
    """The object a `decision-*.json` path holds, or None when it is a sibling family
    that records no product choice.

    Identity is the artifact's own shape, not its filename, and a decision marker beats
    every sibling shape. Content that cannot be read comes back as an empty record
    rather than None: a malformed, partial or placeholder artifact must stay visible to
    the gates, never be dismissed as another family.
    """
    if not str(path).replace("\\", "/").rsplit("/", 1)[-1].startswith("decision-"):
        return None
    try:
        payload = json.loads((Path(project_root) / path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(payload, dict):
        return {}
    if _claims_decision(payload):
        return payload
    return None if any(family(payload) for family in NON_DECISION_FAMILIES) else payload


def _decision_artifact(project_root, path):
    """One Phase A decision whose resolution a gate can judge. A well-formed confirmation
    journal is a batch record of many choices, not one; a malformed one is not a journal."""
    record = decision_record(project_root, path)
    if record is None or (not _claims_decision(record) and _journal_record(record)):
        return None
    return record


def _unresolved(artifact):
    """Presence is not resolution. A queued status, a missing schema key and an empty
    choice all leave the product decision unmade."""
    if artifact.get("status") in PENDING_STATUSES:
        return True
    if any(key not in artifact for key in DECISION_KEYS):
        return True
    choice = artifact["decision"]
    if isinstance(choice, str):
        return not choice.strip()
    return choice is None or choice == [] or choice == {}


def _pending_decisions(project_root, workflow):
    """Blockers for wired decisions the user has not made.

    A decision artifact is the only place a product choice is recorded, and an
    unattended run never makes one. A requirement reference carries its own
    confirmation contract, so it is not read as a choice here.
    """
    blockers = []
    for node in workflow.get("nodes", []):
        refs = node.get("requirement_refs") or []
        paths = {ref["path"] for ref in refs
                 if isinstance(ref, dict) and isinstance(ref.get("path"), str)} if isinstance(refs, list) else set()
        for path in node.get("decision_inputs", []) or []:
            if path in paths:
                continue
            artifact = _decision_artifact(project_root, path)
            if artifact is None or not _unresolved(artifact):
                continue
            node_id = node.get("node_id")
            blockers.append({"code": "pending_decision", "node_id": node_id, "message":
                             f"{node_id}: {path}: the product choice is not made; return to "
                             "interactive bootstrap. An unattended run never chooses it."})
    return blockers


CONCEPT = ".allforai/product-concept/product-concept.json"
JOURNAL = ".allforai/product-concept/decision-journal.json"
BASELINE = ".allforai/product-concept/concept-baseline.json"
PROFILE = ".allforai/bootstrap/bootstrap-profile.json"
LOCAL = ".allforai/bootstrap/local-requirements.json"
TOPICS = ("target-users", "scenarios", "core-problem", "value-proposition", "business-loop",
          "experience-direction", "tradeoffs")
EXPERIENCE_TOPIC = "experience-direction"  # The experience the product gives people, decided before its tradeoffs.
PROPOSAL_ORIGIN = "model-proposal"  # Authored by the model for the user to choose from; never a decision.
_PROPOSAL_TEXT = ("id", "title", "who", "circumstance", "core_loop_feel", "first_minute", "return_reason", "goal")
_PROPOSAL_LISTS = ("anti_goals", "tradeoffs", "scope", "business_rules", "acceptance")
_PROPOSAL_KEYS = {*_PROPOSAL_TEXT, *_PROPOSAL_LISTS, "comparable"}
LOCAL_TOPIC = "local-requirements"  # Grouping label for hand-projected local requirements without a topic.
RUN_POLICY = ".allforai/bootstrap/run-policy.json"
RUN_POLICY_REPAIRS = ".allforai/bootstrap/run-policy-repairs.json"
EXTERNAL = ".allforai/bootstrap/external-changes.json"
POLICY_OPTIONS = {
    "on_repeated_failure": ["continue", "halt"],
    "on_needs_iteration": ["halt_with_report", "auto_fix_once", "accept"],
    "on_safety_warning": ["continue", "halt"],
}


def _policy_invalid(policy):
    return not isinstance(policy, dict) or any(policy.get(k) not in options for k, options in POLICY_OPTIONS.items())


def _recorded_policy(root):
    """Return (policy, previous content, problem); an unusable file is reported, never trusted."""
    target = root / RUN_POLICY
    if not target.exists():
        return None, None, None
    previous = target.read_text(encoding="utf-8")
    try:
        policy = json.loads(previous)
    except ValueError as exc:
        return None, previous, f"Recorded Run Policy is not JSON: {exc}"
    if _policy_invalid(policy):
        return None, policy, "Recorded Run Policy has missing or unknown choices"
    return policy, policy, None


def run_policy(root, request):
    """Run choices are separate from the product journal and never approve intent.

    Only the interactive run entry collects or repairs a policy, with explicit
    answers and an actual user reference. A repair records the invalid prior
    content in an audit file; unattended events never rewrite the policy.
    """
    policy, previous, problem = _recorded_policy(root)
    if policy is None:
        if request["operation"] != "run-policy":
            if problem:
                raise ValueError(f"Invalid Run Policy; repair it at the interactive entry without guessing answers ({problem})")
            if "answers" in request:
                raise ValueError("Run events consume a recorded Run Policy; they never collect or repair one")
        if "answers" not in request:
            result = {"status": "needs_run_policy", "questions": POLICY_OPTIONS,
                      "return_to": "interactive run entry before the first node"}
            if problem:
                result["invalid_policy"] = f"{problem}; repair it at the interactive entry without guessing answers"
            return result
        if not _text(request.get("user_reference")):
            raise ValueError("Run Policy requires an actual user response")
        policy = request["answers"]
        if _policy_invalid(policy):
            raise ValueError("Invalid Run Policy; repair it at the interactive entry without guessing answers")
        if problem:
            repairs = _read(root, RUN_POLICY_REPAIRS, [])
            if not isinstance(repairs, list):
                raise ValueError("Run Policy repair audit must stay a list")
            repairs.append({"previous": previous, "reason": problem, "answers": policy,
                            "user_reference": request["user_reference"]})
            _write(root, RUN_POLICY_REPAIRS, repairs)
        _write(root, RUN_POLICY, policy)
    if request["operation"] == "run-event":
        event = request["event"]
        if event not in POLICY_OPTIONS:
            raise ValueError("Unknown run event requires a report, never a new unattended interview")
        # A read, never a charge: the one repair `auto_fix_once` grants is an attempt the
        # repair-authorization ledger charges against the gate's declared loop, so a
        # second accounting here would either double-count it or hide it (ADR 0005).
        return {"status": "policy_action", "event": event, "action": policy[event], "questions": []}
    return {"status": "run_policy_ready", "policy": policy, "questions": []}


def _read(root, path, default=None):
    target = root / path
    return json.loads(target.read_text(encoding="utf-8")) if target.exists() else default


def _write(root, path, data):
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _text(value):
    return isinstance(value, str) and bool(value.strip())


def _item(item):
    if not isinstance(item, dict) or any(not _text(item.get(key)) for key in ("id", "goal", "topic")):
        raise ValueError("Intent needs id, topic and goal")
    for key in ("scope", "business_rules", "acceptance"):
        if not isinstance(item.get(key), list) or not item[key] or not all(_text(v) for v in item[key]):
            raise ValueError(f"Intent needs non-empty {key}")


def _proposal(value):
    """Validate one offered experience direction and return the script's own copy.

    The key set is exact on purpose: a proposal carries product meaning only, so a
    host cannot hand one `origin`, `status`, `round`, `recommended` or a
    `confirmation` and have the store treat it as something the user decided.
    """
    import copy
    if not isinstance(value, dict) or set(value) != _PROPOSAL_KEYS:
        raise ValueError("Experience proposal needs exactly its own fields")
    for key in _PROPOSAL_TEXT:
        if not _text(value[key]):
            raise ValueError(f"Experience proposal needs {key}")
    for key in _PROPOSAL_LISTS:
        if not isinstance(value[key], list) or not value[key] or not all(_text(v) for v in value[key]):
            raise ValueError(f"Experience proposal needs non-empty {key}")
    comparable = value["comparable"]
    if (not isinstance(comparable, dict) or set(comparable) != {"product", "approach"}
            or any(not _text(comparable[key]) for key in ("product", "approach"))):
        raise ValueError("Experience proposal needs comparable product and approach")
    return copy.deepcopy(value)


def _current_proposals(concept):
    """The offered directions of the newest round; earlier rounds stay as history."""
    proposals = concept.get("experience_proposals") or []
    rounds = [p["round"] for p in proposals]
    return [p for p in proposals if p["round"] == max(rounds)] if rounds else []


def _latest(concept):
    latest: dict[str, Any] = {}
    for item in concept.get("requirements", []):
        if item["id"] not in latest or latest[item["id"]]["revision"] < item["revision"]:
            latest[item["id"]] = item
    return latest


def _confirmed(root, item, *, statuses=("confirmed",)):
    """Product projections must equal the journal's explicit decision payload."""
    reference = item.get("confirmation", {}).get("reference", "")
    source, separator, fragment = reference.partition("#")
    if source != JOURNAL or not separator:
        raise ValueError("Product confirmation needs canonical journal provenance")
    batch_id, marker, index = fragment.split("/")
    journal = _read(root, JOURNAL, {})
    matches = [b for b in journal["batches"] if b["batch_id"] == batch_id]
    if journal["schema_version"] != "1.0" or len(matches) != 1 or marker != "decisions" or not index.isdecimal():
        raise ValueError("Invalid product journal reference")
    batch = matches[0]
    decision = batch["decisions"][int(index)]
    confirmation = item.get("confirmation", {})
    # Legacy schema-1.0 choices have no intent payload. The recorded choice and
    # rationale evidence the goal only; scope, business rules and acceptance are
    # still the model's projection until the user confirms them explicitly.
    matches_payload = (decision["intent"] == item if "intent" in decision else
                       decision.get("chosen") == item.get("goal")
                       and decision.get("rationale") == confirmation.get("reason")
                       and _text(decision.get("rationale")))
    if (batch.get("source") != "user_session" or batch.get("status", "confirmed") != "confirmed"
            or decision.get("status", "confirmed") != "confirmed" or not matches_payload
            or item.get("status") not in statuses or confirmation.get("source") != "user"
            or not _text(confirmation.get("decision_id")) or not _text(confirmation.get("reason"))):
        raise ValueError("Product projection differs from confirmed journal decision")
    if any(d.get("supersedes") in (fragment, reference) for b in journal["batches"] for d in b["decisions"]):
        raise ValueError("Product decision is superseded")
    if "intent" not in decision:
        raise LegacyProjection(reference)


class LegacyProjection(ValueError):
    """A journal choice evidences the goal only; the remaining projection needs the user."""

    EVIDENCED = ["goal"]
    UNCONFIRMED = ["scope", "business_rules", "acceptance"]

    def __init__(self, reference):
        self.reference = reference
        super().__init__("Legacy journal choice evidences the goal only; confirm scope, business_rules and "
                         "acceptance at interactive bootstrap")

    def expose(self, item):
        item["status"] = "pending"
        item["pending_reason"] = str(self)
        item["legacy_reuse"] = {"reference": self.reference, "evidenced": list(self.EVIDENCED),
                                "unconfirmed": list(self.UNCONFIRMED)}


def _journal_reference(reference):
    """True when a hand-projected confirmation cites a decision journal rather than a user turn."""
    return Path(reference.partition("#")[0]).name == "decision-journal.json"


def _journal_decision(root, reference):
    """Resolve a hand-projected journal reference to its confirmed user decision, else raise.

    Structural faults (missing file, wrong schema, non-user source, pending, removed,
    superseded, ambiguous or out-of-project references) are forged authority.
    """
    source, separator, fragment = reference.partition("#")
    if (Path(source).is_absolute() or not separator
            or not (root / source).resolve().is_relative_to(root.resolve())):
        raise ValueError("Journal reference needs a project-local path and decision fragment")
    journal = json.loads((root / source).read_text(encoding="utf-8"))
    if journal.get("schema_version") != "1.0" or not isinstance(journal.get("batches"), list):
        raise ValueError("Journal must use schema 1.0 batches")
    batch_id, marker, index = fragment.split("/")
    batches = [batch for batch in journal["batches"] if batch["batch_id"] == batch_id]
    if marker != "decisions" or len(batches) != 1:
        raise ValueError("Journal reference must select one decision")
    batch = batches[0]
    if (batch.get("source") != "user_session" or batch.get("status", "confirmed") != "confirmed"
            or not isinstance(batch.get("decisions"), list)):
        raise ValueError("Journal reference needs a confirmed user-session batch")
    if not index.isdecimal() or int(index) >= len(batch["decisions"]):
        raise ValueError("Journal decision index is invalid")
    decision = batch["decisions"][int(index)]
    if (decision.get("status", "confirmed") != "confirmed"
            or any(not _text(decision.get(key)) for key in ("question", "chosen"))):
        raise ValueError("Journal reference needs an explicit user choice")
    for recorded_batch in journal["batches"]:
        for recorded in recorded_batch["decisions"]:
            if recorded.get("supersedes") in (fragment, reference):
                raise ValueError("Journal decision was superseded; reconfirm the current requirement")
    return source, decision


def _journal_payload(item, decision):
    """Raise unless the resolved journal decision records this hand-projected requirement.

    A decision with the full `intent` payload must equal the projection. A goal-only
    choice must record the projection's goal and reason, and even then evidences the
    goal alone: scope, business rules and acceptance remain the model's projection.
    """
    confirmation = item.get("confirmation", {})
    if "intent" in decision:
        if decision["intent"] != item:
            raise ValueError("requirement differs from the confirmed journal payload")
        return
    if (decision.get("chosen") != item.get("goal") or not _text(decision.get("rationale"))
            or decision.get("rationale") != confirmation.get("reason")):
        raise ValueError("journal choice does not record this requirement's goal and reason")
    raise LegacyProjection(confirmation["reference"])


def _hand_projection(root, item, *, statuses=("confirmed",)):
    """Verify a legacy hand-projected local requirement exactly as the public gates do.

    A removed item verifies against the same provenance; an invalid tombstone gains
    no authority and is presented pending, never as approval or as new work.
    """
    confirmation = item.get("confirmation") or {}
    if (item.get("status") not in statuses or confirmation.get("source") != "user"
            or any(not _text(confirmation.get(key)) for key in ("reference", "decision_id", "reason"))):
        raise ValueError("Missing or invalid user confirmation provenance")
    if _journal_reference(confirmation["reference"]):
        _, decision = _journal_decision(root, confirmation["reference"])
        _journal_payload(item, decision)


def _session_path(root, profile):
    """The intent file an interactive session operates on.

    The session marker is authoritative. Without it, an existing hand-projected
    `local-requirements.json` on a non-product route is legacy local history that
    must be resumable in place; anything else is the product concept.
    """
    if profile.get("intent_session_path") == LOCAL:
        return LOCAL
    if (not profile.get("intent_session_path")
            and profile.get("task_route") not in ("product-reconstruction", "new-product")
            and _read(root, LOCAL, {}).get("requirements")):
        return LOCAL
    return CONCEPT


def _legacy_local(root, profile):
    """True when the session operates on a hand-projected local file without a session marker."""
    return _session_path(root, profile) == LOCAL and profile.get("intent_session_path") != LOCAL


def _verified(root, item, *, statuses=("confirmed",), legacy=False):
    """Verify an item's recorded provenance by route: gate rule for legacy files, journal payload otherwise."""
    if legacy:
        _hand_projection(root, item, statuses=statuses)
    else:
        _confirmed(root, item, statuses=statuses)


def _consumers(workflow, ref):
    """Current nodes that consume one scoped requirement reference."""
    return [node.get("node_id") for node in workflow.get("nodes", []) if ref in node.get("requirement_refs", [])]


def _scoped(blockers, code, message, node_ids):
    """Bind a requirement blocker to its consumers so unrelated work stays executable.

    A requirement nobody consumes still blocks globally; silence is not approval.
    """
    if not node_ids:
        blockers.append({"code": code, "message": message})
    for node_id in node_ids:
        blockers.append({"code": code, "node_id": node_id, "message": f"{node_id}: {message}"})


def _stage_obligation(node):
    """Separate the inherited product acceptance from this node's own evidence duty.

    The generated list is the user's complete confirmed acceptance and stays verbatim: it
    is the scope this node serves, not a claim that this stage proves all of it. What the
    node owes here is the evidence its declared responsibilities can actually produce at
    its own stage; a statement whose full product effect first exists later is deferred
    through the existing `downstream_effect_owner` declaration, never dropped or reworded.
    """
    duties = ", ".join(r for r in node.get("responsibilities", []) if _text(r)) or "declared on this node"
    return (
        "\nStage obligation:\n"
        "- The acceptance above is the complete user-confirmed acceptance of the requirements this "
        "node consumes. It is the scope this node serves, not a claim that this node proves all of "
        "it. Nothing in it may be dropped, reworded or narrowed here; acceptance that differs from "
        "the confirmed requirement is refused as stale_requirement.\n"
        f"- Prove what this node's declared responsibilities ({duties}) can actually produce at this "
        "stage, against those same statements, and record it under Quality Acceptance and Effect "
        "Verification. Documentation proves that the documents describe current behavior accurately "
        "and passes its declared document_verification; writing a guide is not proof that the "
        "behavior it describes was built.\n"
        "- Where a statement's full product effect first exists at a later stage, state the "
        "stage-local proof in Effect Verification and name the node that proves the full effect as "
        "downstream_effect_owner; a deferral with no owner, or one whose owner does not carry these "
        "requirements, is refused as unowned_effect_stage. A stage-local pass is not product "
        "completion: the nodes holding the implementation and verification responsibilities for "
        "these requirements still owe the full effect.\n")


def _reuse_legacy_choice(root, item):
    """Keep a confirmed legacy intent only when its journal choice verifies; else it is pending."""
    revision = item.setdefault("revision", 1)
    if type(revision) is not int or revision < 1:
        raise ValueError("Legacy intent revision must be a positive integer")
    try:
        _confirmed(root, item)
    except LegacyProjection as exc:
        exc.expose(item)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
        item["status"] = "pending"
        item["pending_reason"] = "Legacy intent needs user verification"


def _retained_nodes(workflow, refs):
    """Consume reconciled history, folding both native formats in log order."""
    last_status = {event.get("node_id", event.get("node")): event.get("status")
                   for event in workflow.get("transition_log", [])}
    return {node.get("node_id") for node in workflow.get("nodes", [])
            if last_status.get(node.get("node_id")) == "completed"
            and not any(ref in refs for ref in node.get("requirement_refs", []))}


def _product_contract(root, workflow, profile, *, retained=()):
    """Verify the frozen product scope; bind per-intent drift to the nodes that consume it.

    Freeze-level problems (provenance, scope, workflow baseline, plan shape) raise and
    block globally. One reopened, adjusted, removed or unverifiable intent, or an
    unresolved decision it depends on, returns blockers only for its consumers.
    """
    concept = _read(root, CONCEPT)
    _validate_question_ids(concept)
    baseline = _read(root, BASELINE, {}).get("intent_baseline")
    if not isinstance(baseline, dict):
        raise ValueError("Product work needs a frozen product baseline")
    source, fragment = baseline["confirmation"].split("#")
    batch_id, marker, index = fragment.split("/")
    journal = _read(root, JOURNAL)
    matches = [b for b in journal["batches"] if b["batch_id"] == batch_id]
    if (source != JOURNAL or marker != "decisions" or not index.isdecimal() or len(matches) != 1
            or journal.get("schema_version") != "1.0"):
        raise ValueError("Product scope has invalid journal provenance")
    batch = matches[0]
    decision = batch["decisions"][int(index)]
    if (batch.get("source") != "user_session" or not _text(batch.get("user_reference"))
            or batch.get("status", "confirmed") != "confirmed" or decision.get("status", "confirmed") != "confirmed"
            or decision.get("baseline") != baseline
            or any(d.get("supersedes") in (fragment, baseline["confirmation"])
                   for b in journal["batches"] for d in b["decisions"])):
        raise ValueError("Product baseline differs from confirmed scope")
    refs = baseline["requirement_refs"]
    if refs != profile["task_scope"]["requirement_refs"]:
        raise ValueError("Product task scope differs from frozen baseline")
    frozen = baseline.get("intents")
    if not isinstance(frozen, list) or len(frozen) != len(refs):
        raise ValueError("Product baseline intents must match its requirement refs")
    if workflow.get("product_baseline") != baseline:
        raise ValueError("Product workflow must consume current frozen baseline")
    stages = {"product", "experience", "technical", "implementation", "documentation", "verification"}
    omitted = workflow.get("not_applicable", {})
    if not isinstance(omitted, dict) or set(omitted) - {"experience", "technical"} or not all(_text(v) for v in omitted.values()):
        raise ValueError("Product stage applicability needs explicit planning reasons")
    for ref in refs:
        consumers = [n for n in workflow["nodes"] if ref in n.get("requirement_refs", [])]
        covered = {r for n in consumers for r in n.get("responsibilities", [])}
        if stages - covered - omitted.keys():
            raise ValueError("Product plan lacks applicable full-process responsibilities")
    return _intent_drift(root, workflow, concept, refs, frozen, label="Product", path=CONCEPT, retained=retained)


def _experience_direction_blockers(root, profile, refs):
    """A product people live with must carry the direction they chose for it.

    The classification is read, never re-derived: `admin`, `none` and a missing or
    illegal mode produce nothing here, the last because an unknown mode is the bootstrap
    gate's own `missing_experience_priority` and answering it twice sends the user to
    repair the wrong thing. The blocker is global like `pending_product_confirmation`:
    no single node is at fault when the whole scope never said what living with the
    product feels like.

    Provenance is not re-checked here. `_product_contract` already put every frozen
    intent through `_intent_drift` and `_confirmed`, so a confirmed direction of any
    origin — the model's proposal or the user's own words — satisfies this.
    """
    priority = profile.get("experience_priority")
    mode = priority.get("mode") if isinstance(priority, dict) else None
    if mode not in ("consumer", "mixed"):
        return []
    latest = _latest(_read(root, CONCEPT, {}))
    for ref in refs:
        item = latest.get(ref["id"])
        if (isinstance(item, dict) and item.get("topic") == EXPERIENCE_TOPIC
                and item.get("status") == "confirmed" and item.get("revision") == ref["revision"]):
            return []
    return [{"code": "ui_product_without_experience_direction",
             "message": f"experience_priority.mode is {mode} but the frozen scope holds no confirmed "
                        "experience-direction intent; return to interactive bootstrap, propose "
                        "directions and record the user's select or delegate, then refreeze and replan"}]


def _local_contract(root, workflow, profile, *, retained=()):
    """Verify the frozen local scope; bind per-intent drift to the nodes that consume it.

    The same two levels as the product route: unverifiable journal provenance of the
    frozen scope, a task scope differing from the frozen refs, or a malformed scope
    raise and block globally; one reopened, adjusted or unverifiable local intent, or
    an unresolved decision it depends on, returns blockers only for its consumers.
    """
    local = _read(root, LOCAL)
    _validate_question_ids(local)
    _discussion(root, local)  # Verify the journal-backed frozen local scope.
    baseline = profile["intent_scope"]
    refs = baseline["requirement_refs"]
    if refs != profile["task_scope"]["requirement_refs"]:
        raise ValueError("Local task scope differs from the frozen scope")
    frozen = baseline.get("intents")
    if not isinstance(frozen, list) or len(frozen) != len(refs):
        raise ValueError("Local scope intents must match its requirement refs")
    return _intent_drift(root, workflow, local, refs, frozen, label="Local", path=LOCAL, retained=retained)


def _intent_drift(root, workflow, concept, refs, frozen, *, label, path, retained=()):
    """Bind each frozen intent's drift to the current nodes that consume it.

    A reopened intent (latest revision pending) is pending work; an adjusted, removed,
    restored or silently changed one is stale; a journal choice that no longer verifies
    is pending with its reason; a pending question an intent depends on names the
    unresolved decision. Node projections are then checked against the confirmed
    intent so unrelated nodes keep their validity.
    """
    latest = _latest(concept)
    blockers: list[dict] = []
    drifted = set()
    for ref, intent in zip(refs, frozen):
        item = latest.get(ref["id"])
        consumers = _consumers(workflow, ref)
        if item is None or item != intent or ref["path"] != path or ref["revision"] != item["revision"]:
            drifted.add(ref["id"])
            if item is not None and item.get("status") == "pending":
                _scoped(blockers, "pending_requirement", f"{label} intent {ref['id']} was reopened after the freeze; "
                        "confirm it at interactive bootstrap, then refreeze and replan", consumers)
            else:
                _scoped(blockers, "stale_requirement", f"{label} intent {ref['id']} differs from the frozen "
                        "user-confirmed scope; refreeze and replan the affected work", consumers)
            continue
        try:
            _confirmed(root, item)
        except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
            drifted.add(ref["id"])
            _scoped(blockers, "pending_requirement",
                    f"{label} intent {ref['id']}: {exc}; return to interactive bootstrap", consumers)
    for question in concept.get("intent_questions", []):
        if not _question_pending(root, question):
            continue
        for ref in refs:
            if ref["id"] in set(question.get("depends_on", [])):
                _scoped(blockers, "pending_requirement", f"{label} intent {ref['id']} depends on unresolved decision "
                        f"{question['id']}; answer it at interactive bootstrap, then refreeze and replan",
                        _consumers(workflow, ref))
    for node in workflow["nodes"]:
        node_id = node.get("node_id")
        if node_id in retained:
            continue
        node_refs = node.get("requirement_refs", [])
        if not node_refs or any(ref not in refs for ref in node_refs):
            _scoped(blockers, "scope_requirement_unwired", f"{label} node consumes excluded or unconfirmed intent", [node_id])
            continue
        if any(ref["id"] in drifted for ref in node_refs):
            continue
        expected = [latest[r["id"]] for r in node_refs]
        if (node.get("product_goals") != [i["goal"] for i in expected]
                or node.get("acceptance") != [a for i in expected for a in i["acceptance"]]):
            _scoped(blockers, "stale_requirement", f"{label} goals and acceptance differ from confirmed intent", [node_id])
    return blockers


def _validate_question_ids(concept):
    intent_ids = set(_latest(concept))
    proposal_ids = set()
    proposals = concept.get("experience_proposals", [])
    separate = ("Proposal identities must be unique and separate from intent and question identities")
    if not isinstance(proposals, list):
        raise ValueError(separate)
    for proposal in proposals:
        identity = proposal.get("id") if isinstance(proposal, dict) else None
        if not _text(identity) or identity in intent_ids or identity in proposal_ids:
            raise ValueError(separate)
        # Every reader orders the store by `round`; a hand-edited proposal that lost it
        # is a malformed record to refuse in words, not a KeyError further down.
        opened = proposal.get("round")
        if not isinstance(opened, int) or isinstance(opened, bool) or opened < 1:
            raise ValueError(f"Stored experience proposal {identity} needs a positive whole round")
        proposal_ids.add(identity)
    question_ids = set()
    for question in concept.get("intent_questions", []):
        identity = question.get("id")
        if not _text(identity) or identity in intent_ids or identity in question_ids:
            raise ValueError("Question identities must be unique and separate from intent identities")
        if identity in proposal_ids:
            raise ValueError(separate)
        question_ids.add(identity)


def _question_pending(root, question):
    if question.get("status", "pending") != "resolved":
        return True
    try:
        reference = question["confirmation"]["reference"]
        source, fragment = reference.split("#")
        batch_id, marker, index = fragment.split("/")
        journal = _read(root, JOURNAL)
        batches = [b for b in journal["batches"] if b["batch_id"] == batch_id]
        return (source != JOURNAL or marker != "decisions" or not index.isdecimal()
                or journal.get("schema_version") != "1.0" or len(batches) != 1
                or batches[0].get("source") != "user_session"
                or batches[0].get("status", "confirmed") != "confirmed"
                or batches[0]["decisions"][int(index)].get("intent") != question
                or batches[0]["decisions"][int(index)].get("status", "confirmed") != "confirmed"
                or any(d.get("supersedes") in (reference, fragment)
                       for b in journal["batches"] for d in b["decisions"]))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
        return True


def _frozen_scope_batch(root, baseline):
    """Return the journal and batch identity that still confirm a frozen scope, else raise."""
    source, fragment = baseline["confirmation"].split("#")
    batch_id, marker, index = fragment.split("/")
    journal = _read(root, JOURNAL, {})
    batches = [b for b in journal.get("batches", []) if b["batch_id"] == batch_id]
    if (source != JOURNAL or marker != "decisions" or not index.isdecimal()
            or journal.get("schema_version") != "1.0"
            or len(batches) != 1 or batches[0].get("source") != "user_session"
            or batches[0].get("status", "confirmed") != "confirmed"
            or batches[0]["decisions"][int(index)].get("status", "confirmed") != "confirmed"
            or batches[0]["decisions"][int(index)].get("baseline") != baseline
            or any(d.get("supersedes") in (fragment, baseline["confirmation"])
                   for b in journal["batches"] for d in b["decisions"])):
        raise ValueError("Cannot resume unverified scope exclusions")
    return journal, batch_id


def _same_selection(previous, refs, exclude, intents):
    """True when a verified previous scope already binds exactly this confirmed selection."""
    by_id = lambda values: {v["id"]: v for v in values}  # noqa: E731
    return (isinstance(previous, dict)
            and by_id(previous.get("requirement_refs", [])) == by_id(refs)
            and previous.get("excluded") == exclude
            and by_id(previous.get("intents", [])) == by_id(intents))


def _discussion(root, concept):
    import copy
    concept = copy.deepcopy(concept)
    profile = _read(root, PROFILE, {})
    session_path = _session_path(root, profile)
    baseline = (profile.get("intent_scope", {}) if session_path == LOCAL
                else _read(root, BASELINE, {}).get("intent_baseline", {}))
    # A hand-projected legacy local file (no session marker) is verified exactly as
    # the public gates verify it, so resume exposes what they block and nothing more.
    legacy = _legacy_local(root, profile)
    excluded = {}
    if baseline:
        journal, batch_id = _frozen_scope_batch(root, baseline)
        excluded = dict(baseline["excluded"])
        # A later explicit reconsideration replaces only that exclusion. The
        # frozen baseline remains historical until the user freezes a new scope.
        after_scope = False
        reopened = set()
        for batch in journal["batches"]:
            if batch["batch_id"] == batch_id:
                after_scope = True
                continue
            if (not after_scope or batch.get("source") != "user_session"
                    or batch.get("status", "confirmed") != "confirmed"):
                continue
            for decision in batch["decisions"]:
                if decision.get("operation") == "reopen" and decision.get("status", "confirmed") == "confirmed":
                    identity = decision["intent"]["id"]
                    excluded.pop(identity, None)
                    reopened.add(identity)
        for question in concept.get("intent_questions", []):
            if set(question.get("depends_on", [])) & reopened:
                excluded.pop(question["id"], None)
    for item in _latest(concept).values():
        # A removal the user already excluded at freeze is journal-backed history; it
        # authorizes nothing and is not re-labelled pending, whatever its own provenance.
        if item.get("status") == "removed" and item["id"] in excluded:
            continue
        if item.get("status") in ("confirmed", "removed"):
            try:
                _verified(root, item, statuses=("confirmed", "removed"), legacy=legacy)
            except LegacyProjection as exc:
                exc.expose(item)
            except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
                item["status"] = "pending"
                item["pending_reason"] = str(exc) if legacy else "Missing or invalid user confirmation provenance"
    topics = []
    latest = {identity: dict(item, topic=item.get("topic", LOCAL_TOPIC)) for identity, item in _latest(concept).items()}
    # An offer still on the table is itself unfinished business: the experience topic
    # stays listed while the newest round waits for the user, even once every item and
    # question under it is settled. Once a direction is confirmed the offer is spent.
    current = _current_proposals(concept)
    direction_open = not any(i["topic"] == EXPERIENCE_TOPIC and i["status"] == "confirmed" for i in latest.values())
    for topic in dict.fromkeys([*TOPICS, *(i["topic"] for i in latest.values())]):
        items = [i for i in latest.values() if i["topic"] == topic and i["status"] == "pending" and i["id"] not in excluded]
        questions = [dict(q, status="pending") for q in concept.get("intent_questions", [])
                     if q["topic"] == topic and _question_pending(root, q) and q["id"] not in excluded]
        offered = topic == EXPERIENCE_TOPIC and current
        if not (items or questions or (offered and direction_open)):
            continue
        entry = {"topic": topic, "items": items, "questions": questions}
        if offered:
            recommended = next(p for p in current if p["recommended"])
            entry.update(proposals=current, recommended_id=recommended["id"],
                         rationale=recommended["rationale"])
        topics.append(entry)
    presented = {"status": "discussion", "topics": topics, "history": concept.get("requirements", []),
                 "excluded": excluded, "questions": concept.get("intent_questions", [])}
    # Absent proposals leave the resumed object byte-identical to what it has always been.
    if concept.get("experience_proposals"):
        presented["experience_proposals"] = concept["experience_proposals"]
    return presented



def _propose(root, profile, concept_path, concept, request):
    """Record one round of offered experience directions for the user to choose from.

    Nothing is decided here: the model authors the directions, the user picks one
    later through `select` or hands the pick back through `delegate`. So this writes
    no journal batch and asks for no user reference, and the round is appended —
    an earlier round stays readable as the history of what was already offered.
    """
    if concept_path != CONCEPT or profile.get("task_route") not in ("product-reconstruction", "new-product"):
        raise ValueError("Experience proposals belong to a product session; draft the product first")
    offered = request.get("proposals")
    if not isinstance(offered, list) or not 2 <= len(offered) <= 3:
        raise ValueError("Propose two or three experience directions")
    proposals = [_proposal(p) for p in offered]
    if len({p["id"] for p in proposals}) != len(proposals):
        raise ValueError("Proposal identities must be unique and separate from intent and question identities")
    if len([p for p in proposals if p["id"] == request.get("recommended_id")]) != 1:
        raise ValueError("Exactly one proposal must be recommended")
    if not _text(request.get("rationale")):
        raise ValueError("A recommendation needs its rationale")
    opened = max((p["round"] for p in concept.get("experience_proposals", [])), default=0) + 1
    for proposal in proposals:
        proposal.update(origin=PROPOSAL_ORIGIN, round=opened, recommended=proposal["id"] == request["recommended_id"])
        if proposal["recommended"]:
            proposal["rationale"] = request["rationale"]
    concept.setdefault("experience_proposals", []).extend(proposals)
    _validate_question_ids(concept)
    _write(root, CONCEPT, concept)
    return _discussion(root, concept)


def _direction_intent(concept, concept_path, action, op):
    """Turn one offered direction into the experience-direction intent, without its stamp.

    The user picks a direction; the product meaning that becomes intent is the
    proposal's own words, so nothing is reworded on the way in — a different wording
    is an explicit `adjust` on the new item, recorded as its own decision. Only the
    round on the table can be picked, and only one proposal-derived direction stands
    at a time: a change of mind removes the standing one first, so the concept never
    holds two confirmed directions and the reader never has to guess which one won.
    The caller attaches the batch confirmation, which is what makes it a decision.
    """
    import copy
    if concept_path != CONCEPT:
        raise ValueError("Experience directions belong to a product session")
    current = _current_proposals(concept)
    if not current:
        raise ValueError("No current experience proposals; propose before select or delegate")
    if op == "select":
        offered = [p for p in current if p["id"] == action.get("proposal_id")]
        if len(offered) != 1:
            raise ValueError("Select one proposal of the current round")
        proposal = offered[0]
    else:
        if "proposal_id" in action:
            raise ValueError("Delegate takes the recommended proposal; use select to name one")
        proposal = next(p for p in current if p.get("recommended") is True)
    latest = _latest(concept)
    if any(i.get("status") == "confirmed" and "proposal_id" in i for i in latest.values()):
        raise ValueError("An experience direction is already selected; remove it before choosing another")
    identity = EXPERIENCE_TOPIC + "-" + proposal["id"]
    if identity in latest:
        raise ValueError("Added intent needs an unused stable identity")
    item = {"id": identity, "topic": EXPERIENCE_TOPIC,
            **{key: copy.deepcopy(proposal[key])
               for key in ("goal", "scope", "business_rules", "acceptance")}}
    _item(item)
    # `who` and `circumstance` travel with the intent: later review reads the journey
    # from the confirmed direction itself, never from the proposals it came out of.
    item.update(revision=1, origin=PROPOSAL_ORIGIN, evidence=[], status="confirmed",
                proposal_id=proposal["id"], who=proposal["who"], circumstance=proposal["circumstance"])
    if op == "delegate":
        item.update(auto_decided=True)
    return item


def delegations(root):
    """Every standing direction the user handed back to the model, for disclosure.

    A delegated direction is the user's own confirmed intent like any other, so the
    only way a later reader can tell whose judgement chose it is that the record says
    so out loud and something reads that back. This reads and writes nothing, so it
    can be run at any point of a run, including after it stopped early.

    The turn and the reason come from the revision that carried the delegation, not
    from whatever revision stands now: rewording a delegated direction afterwards is
    the user's own turn, and reporting it as the delegation would move the handover
    to a turn that never happened.
    """
    concept = _read(Path(root), CONCEPT, {})
    titles = {p["id"]: p.get("title") for p in concept.get("experience_proposals", [])}
    disclosed = []
    for item in _latest(concept).values():
        if item.get("auto_decided") is not True or item.get("status") != "confirmed":
            continue
        handed = next((revision for revision in concept.get("requirements", [])
                       if revision["id"] == item["id"]
                       and revision.get("confirmation", {}).get("delegated") is True), item)
        confirmation = handed.get("confirmation", {})
        disclosed.append({"id": item["id"], "revision": item["revision"],
                          "proposal_id": item.get("proposal_id"),
                          "proposal_title": titles.get(item.get("proposal_id")),
                          "user_reference": confirmation.get("user_reference"),
                          "reason": confirmation.get("reason")})
    return {"status": "delegations", "delegations": disclosed}


def _external_change(root, request):
    """Record the user's decision about source changed outside the delivery flow.

    Only a detected, verified conflict reaches a decision: a verified
    implementation-only change is synchronized through its fact documents, and a
    change the source has already moved past is redetected rather than decided.
    Accepting one requires the explicit desired intent it establishes; the code
    change never supplies its own requirement, and no Run Policy answer stands in
    for this decision. The resolution is recorded beside the change; accepted
    intent changes go through the same journal, refreeze and replan loop as any
    other product decision.
    """
    # One canonical writer keeps the recorded store byte-identical across boundaries.
    from evidence_freshness import carried_resolution, detect_external_changes, write_json as write_external
    change_id, resolution = request.get("change_id"), request.get("resolution")
    if resolution not in ("accept", "reject", "defer"):
        raise ValueError("An external change is accepted, rejected or deferred by explicit user decision")
    if any(not _text(request.get(key)) for key in ("change_id", "reason", "user_reference")):
        raise ValueError("An external change decision needs its identity, actual user reference and reason")
    store = _read(root, EXTERNAL, {})
    changes = store.get("changes", {}) if isinstance(store.get("changes"), dict) else {}
    entry = changes.get(change_id)
    if not isinstance(entry, dict):
        raise ValueError("Unknown external change; detect it at the bootstrap or resume boundary first")
    detected = {c["change_id"]: c for c in detect_external_changes(root)}
    if change_id not in detected:
        raise ValueError("This external change is not present in the current source; redetect before deciding")
    if entry.get("classification") == "fact-update":
        raise ValueError("A verified implementation-only change is synchronized through its fact documents "
                         "and republished evidence, not through a product decision")
    # A decision the user's own later intent revision superseded is history, not consent.
    standing, superseded = carried_resolution(entry, detected[change_id]["requirement_binding"])
    settled = (standing or {}).get("resolution")
    if settled in ("accept", "reject"):
        raise ValueError(f"This external change is already {settled}ed; record a new product decision instead")
    record = {"resolution": resolution, "reason": request["reason"],
              "user_reference": request["user_reference"], "baseline_version": entry.get("baseline_version")}
    tag = {"change_id": change_id, "node_id": entry.get("node_id"),
           "resolution": resolution, "files": entry.get("files", {})}
    if resolution in ("accept", "reject"):
        if not _text(request.get("batch_id")):
            raise ValueError(f"A{'n accepted' if resolution == 'accept' else ' rejected'} external change "
                             "needs its decision batch identity")
        actions = request.get("actions", []) if resolution == "accept" else []
        if not isinstance(actions, list):
            raise ValueError("actions must be an explicit array")
        if resolution == "accept" and not actions and entry.get("impact", {}).get("product_decisions"):
            raise ValueError("Accepting this change needs the explicit desired product intent it establishes; "
                             "changed code is not a requirement")
        if actions:
            # Intent the change establishes is recorded through the ordinary decision
            # path, so identity, provenance and supersession rules apply unchanged.
            result = session(root, {"operation": "decide", "batch_id": request["batch_id"],
                                    "topic": "External source change",
                                    "user_reference": request["user_reference"], "actions": actions})
            journal = _read(root, JOURNAL)
            next(b for b in journal["batches"] if b["batch_id"] == request["batch_id"])["external_change"] = tag
        else:
            # No confirmed intent changes: the decision itself is still recorded.
            journal = _read(root, JOURNAL, {"schema_version": "1.0", "batches": []})
            if journal.get("schema_version") != "1.0" or not isinstance(journal.get("batches"), list):
                raise ValueError("Preserve canonical schema 1.0 journal batches")
            if any(b["batch_id"] == request["batch_id"] for b in journal["batches"]):
                raise ValueError("Batch identity already exists; resume before submitting new decisions")
            journal["batches"].append({
                "batch_id": request["batch_id"], "topic": "External source change", "source": "user_session",
                "user_reference": request["user_reference"], "external_change": tag,
                "decisions": [{"question": "Accept the changed source or restore the confirmed behavior?",
                               "chosen": ("Accept the changed source" if resolution == "accept"
                                          else "Restore the confirmed behavior"),
                               "rationale": request["reason"], "supersedes": None}]})
            result = {"status": "external_change_recorded"}
        _write(root, JOURNAL, journal)
        record.update(batch_id=request["batch_id"],
                      decision=JOURNAL + "#" + request["batch_id"] + "/decisions/0")
        if resolution == "reject":
            # The confirmed baseline stands; what remains is scoped implementation work,
            # not another product question. Its acceptance is the one already confirmed.
            record["repair_task"] = {"node_id": entry.get("node_id"), "responsibilities": ["implementation"],
                                     "files": sorted(entry.get("files", {})),
                                     "restore_acceptance": (entry.get("verification") or {}).get("command"),
                                     "product_decisions": entry.get("impact", {}).get("product_decisions", [])}
    else:
        result = {"status": "external_change_recorded"}
    # The decision binds the confirmed requirement content it was made against, so a
    # later baseline version carries it while a later intent revision retires it.
    record["requirement_binding"] = next((c["requirement_binding"] for c in detect_external_changes(root)
                                          if c["change_id"] == change_id),
                                         detected[change_id]["requirement_binding"])
    entry["resolution"] = record
    if superseded:
        entry["superseded_resolutions"] = superseded
    changes[change_id] = entry
    write_external(root, EXTERNAL, {"schema_version": "1.0", "changes": changes})
    return {**result, "external_change": {"change_id": change_id, "node_id": entry.get("node_id"),
                                          "classification": entry.get("classification"), "resolution": record}}


def session(root, request):
    """Apply explicit interactive bootstrap input; never called by unattended run."""
    if request.get("operation") in ("run-policy", "run-event"):
        return run_policy(root, request)
    if request.get("operation") == "delegations":
        return delegations(root)
    if request.get("operation") == "external-change":
        return _external_change(root, request)
    profile = _read(root, PROFILE, {})
    operation = request["operation"]
    # draft and admit name their own route; the other operations continue the
    # recorded session, or a legacy hand-projected local file awaiting recovery.
    concept_path = ((LOCAL if profile.get("intent_session_path") == LOCAL else CONCEPT)
                    if operation in ("draft", "admit") else _session_path(root, profile))
    concept = _read(root, concept_path, {})
    _validate_question_ids(concept)
    if operation == "admit":
        import copy
        if (request.get("route") != "local-change" or not _text(request.get("goal"))
                or not isinstance(request.get("areas"), list) or not request["areas"]
                or not all(_text(a) for a in request["areas"])):
            raise ValueError("Legacy admission needs the explicit local goal and areas")
        if _read(root, LOCAL, {}).get("requirements"):
            raise ValueError("Existing local history must be resumed, not overwritten; "
                             "use resume, then confirm its pending projections")
        items = copy.deepcopy(request["items"])
        if not isinstance(items, list) or not items:
            raise ValueError("Supply only relevant legacy projections and missing local requirements")
        for item in items:
            _item(item)
            if not set(item["scope"]) & set(request["areas"]):
                raise ValueError("Legacy projection is outside the requested local scope")
            _reuse_legacy_choice(root, item)
        if len({i["id"] for i in items}) != len(items):
            raise ValueError("Legacy projection identities must be unique")
        concept = {"requirements": items, "intent_questions": request.get("questions", [])}
        _validate_question_ids(concept)
        profile.update(task_route="local-change", task_goal=request["goal"], intent_session_path=LOCAL,
                       task_scope={"areas": request["areas"], "requirement_refs": []})
        profile.pop("intent_scope", None)
        _write(root, LOCAL, concept)
        _write(root, PROFILE, profile)
        return _discussion(root, concept)
    if operation == "resume":
        return _discussion(root, concept)
    if operation == "propose":
        return _propose(root, profile, concept_path, concept, request)
    if operation == "plan":
        import copy
        import re
        baseline = (profile["intent_scope"] if concept_path == LOCAL
                    else _read(root, BASELINE, {})["intent_baseline"])
        latest = _latest(concept)
        refs_by_id = {r["id"]: r for r in baseline["requirement_refs"]}
        workflow = copy.deepcopy(request)
        workflow.pop("operation")
        if concept_path == CONCEPT:
            workflow["product_baseline"] = baseline
        workflow.setdefault("transition_log", [])
        for node in workflow["nodes"]:
            if "intent_ids" in node:
                node["requirement_refs"] = [refs_by_id[i] for i in node.pop("intent_ids")]
        retained = _retained_nodes(workflow, baseline["requirement_refs"])
        bodies = {}
        for node in workflow["nodes"]:
            identity = node["node_id"]
            if not isinstance(identity, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", identity) or identity in bodies:
                raise ValueError("Node identity must be unique and filename-safe")
            bodies[identity] = node.pop("body", None)
            if identity in retained:
                if not (root / ".allforai/bootstrap/node-specs" / (identity + ".md")).is_file() and not _text(bodies[identity]):
                    raise ValueError("Retained node needs its historical Node-spec or task brief")
                continue
            if not _text(bodies[identity]):
                raise ValueError("Node needs a project-specific task brief")
            scope_inputs = [LOCAL] if concept_path == LOCAL else [CONCEPT, BASELINE]
            node["decision_inputs"] = list(dict.fromkeys([*node.get("decision_inputs", []), *scope_inputs]))
            selected = [latest[r["id"]] for r in node["requirement_refs"]]
            node["product_goals"] = [i["goal"] for i in selected]
            node["acceptance"] = [a for i in selected for a in i["acceptance"]]
        blockers = validate_scope(root, workflow)
        if blockers:
            raise ValueError(json.dumps(blockers))
        for node in workflow["nodes"]:
            path = root / ".allforai/bootstrap/node-specs" / (node["node_id"] + ".md")
            if node["node_id"] in retained:
                if not path.exists():
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("---\n" + json.dumps(node, ensure_ascii=False) + "\n---\n" + bodies[node["node_id"]], encoding="utf-8")
                continue
            body = bodies[node["node_id"]] + "\n\nConfirmed product goals:\n" + "\n".join("- " + v for v in node["product_goals"])
            body += ("\n\nConfirmed acceptance (inherited requirement scope, complete and unmodifiable):\n"
                     + "\n".join("- " + v for v in node["acceptance"]) + "\n" + _stage_obligation(node))
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("---\n" + json.dumps(node, ensure_ascii=False) + "\n---\n" + body, encoding="utf-8")
        for path in (root / ".allforai/bootstrap/node-specs").glob("*.md"):
            if path.stem not in bodies:
                path.unlink()
        _write(root, ".allforai/bootstrap/workflow.json", workflow)
        return {"status": "planned", "workflow": workflow}
    if operation == "freeze":
        include, exclude = request["include"], request["exclude"]
        if (not isinstance(include, list) or not include or not all(_text(i) for i in include)
                or len(include) != len(set(include)) or not isinstance(exclude, dict)
                or not all(_text(k) and _text(v) for k, v in exclude.items())):
            raise ValueError("Freeze needs explicit included identities and exclusion reasons")
        latest = _latest(concept)
        questions = concept.get("intent_questions", [])
        pending = {q["id"] for q in questions if _question_pending(root, q)}
        if (set(include) - latest.keys() or set(include) & exclude.keys()
                or (latest.keys() | pending) - (set(include) | exclude.keys())
                or exclude.keys() - (latest.keys() | pending)):
            raise ValueError("Freeze needs explicit scope for every intent and unresolved question")
        for q in questions:
            if q["id"] in pending and set(q.get("depends_on", [])) & set(include):
                raise ValueError("Included work depends on an unresolved decision")
        for identity in include:
            try:
                _confirmed(root, latest[identity])
            except LegacyProjection:
                raise
            except ValueError:
                # A frozen scope is journal-backed. A hand-projected user-turn item is
                # valid for its legacy gates but enters the session only once recorded.
                reference = latest[identity].get("confirmation", {}).get("reference", "")
                if (_legacy_local(root, profile) and _text(reference) and not _journal_reference(reference)):
                    raise ValueError(f"Legacy user-turn projection {identity} must be recorded with one confirm "
                                     "decision (same user reference, no new question) before a local freeze")
                raise
        if any(not _text(request.get(k)) for k in ("batch_id", "user_reference", "reason")):
            raise ValueError("Scope needs explicit user reference and reason")
        journal = _read(root, JOURNAL)
        baseline = _read(root, BASELINE, {})
        refs = [{"path": concept_path, "id": i, "revision": latest[i]["revision"]} for i in include]
        previous_scope = profile.get("intent_scope", {}) if concept_path == LOCAL else baseline.get("intent_baseline", {})
        # The same confirmed selection re-frozen converges: no new decision, version or
        # replan. A changed selection, a new revision, any user decision recorded after
        # the scope batch, or an unverifiable previous scope freezes a new version.
        if (_same_selection(previous_scope, refs, exclude, [latest[i] for i in include])
                and profile.get("task_scope", {}).get("requirement_refs") == previous_scope["requirement_refs"]):
            try:
                _, scope_batch = _frozen_scope_batch(root, previous_scope)
            except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
                pass
            else:
                if journal["batches"][-1]["batch_id"] == scope_batch:
                    return {"status": "frozen", "baseline": previous_scope, "unchanged": True}
        if any(b["batch_id"] == request["batch_id"] for b in journal["batches"]):
            raise ValueError("Scope batch identity already exists")
        contract = {"version": previous_scope.get("version", 0) + 1,
                    "requirement_refs": refs, "excluded": exclude,
                    "intents": [latest[i] for i in include],
                    "confirmation": JOURNAL + "#" + request["batch_id"] + "/decisions/0"}
        journal["batches"].append({"batch_id": request["batch_id"], "topic": "Product baseline scope",
                                   "source": "user_session", "user_reference": request["user_reference"],
                                   "decisions": [{"question": "Freeze this product scope?", "chosen": "Freeze explicit scope",
                                                  "rationale": request["reason"], "baseline": contract}]})
        baseline["intent_baseline"] = contract
        profile = _read(root, PROFILE, {})
        profile["task_scope"] = {"areas": sorted({a for i in include for a in latest[i]["scope"]}), "requirement_refs": refs}
        _write(root, JOURNAL, journal)
        if concept_path == LOCAL:
            # A frozen local scope is a session contract from here on, also for a
            # legacy hand-projected file that was resumed and confirmed in place.
            profile["intent_session_path"] = LOCAL
            profile["intent_scope"] = contract
        else:
            _write(root, BASELINE, baseline)
        _write(root, PROFILE, profile)
        return {"status": "frozen", "baseline": contract}
    if operation == "decide":
        import copy
        actions = request["actions"]
        if not isinstance(actions, list):
            raise ValueError("actions must be an explicit array")
        if not actions:
            return _discussion(root, concept)
        if any(not _text(request.get(k)) for k in ("batch_id", "topic", "user_reference")):
            raise ValueError("User decisions need batch identity, topic and actual user reference")
        journal = _read(root, JOURNAL, {"schema_version": "1.0", "batches": []})
        if journal.get("schema_version") != "1.0" or not isinstance(journal.get("batches"), list):
            raise ValueError("Preserve canonical schema 1.0 journal batches")
        if any(b["batch_id"] == request["batch_id"] for b in journal["batches"]):
            raise ValueError("Batch identity already exists; resume before submitting new decisions")
        batch = {"batch_id": request["batch_id"], "topic": request["topic"], "source": "user_session",
                 "user_reference": request["user_reference"], "decisions": []}
        for action in actions:
            op = action["operation"]
            if not _text(action.get("reason")):
                raise ValueError("Every explicit decision needs its reason")
            reference = JOURNAL + "#" + request["batch_id"] + "/decisions/" + str(len(batch["decisions"]))
            confirmation = {"source": "user", "reference": reference, "decision_id": reference.split("#")[1],
                            "reason": action["reason"], "user_reference": request["user_reference"]}
            previous = None
            if op == "add":
                item = copy.deepcopy(action["item"])
                _item(item)
                if item["id"] in _latest(concept):
                    raise ValueError("Added intent needs an unused stable identity")
                item.update(revision=1, origin="user-request", evidence=[], status="confirmed", confirmation=confirmation)
                concept.setdefault("requirements", []).append(item)
            elif op in ("select", "delegate"):
                item = _direction_intent(concept, concept_path, action, op)
                if op == "delegate":
                    confirmation["delegated"] = True
                item["confirmation"] = confirmation
                concept.setdefault("requirements", []).append(item)
            elif op in ("confirm", "adjust", "remove", "restore") or (op == "reopen" and action["id"] in _latest(concept)):
                item = _latest(concept)[action["id"]]
                previous = item.get("confirmation", {}).get("reference")
                if item["status"] == "removed" and op != "restore":
                    if item["id"] in _discussion(root, concept)["excluded"]:
                        raise ValueError("Removed intent excluded by the confirmed scope needs explicit restore")
                    try:
                        _verified(root, item, statuses=("removed",), legacy=_legacy_local(root, profile))
                    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
                        if op not in ("confirm", "remove"):
                            raise ValueError("Unverified legacy removal needs explicit confirmation")
                    else:
                        raise ValueError("Removed intent cannot be silently restored")
                if op == "restore" and item["status"] != "removed":
                    raise ValueError("Restore requires a removed intention")
                if op == "adjust":
                    replacement = copy.deepcopy(item)
                    changes = action["changes"]
                    if not changes or set(changes) - {"goal", "scope", "business_rules", "acceptance", "topic"}:
                        raise ValueError("Adjust only product meaning; identity and authority are immutable")
                    replacement.update(changes)
                    _item(replacement)
                    replacement.update(revision=item["revision"] + 1, supersedes={"id": item["id"], "revision": item["revision"]})
                    item["status"] = "superseded"
                    concept["requirements"].append(replacement)
                    item = replacement
                elif op in ("remove", "restore", "reopen") and item.get("confirmation"):
                    replacement = copy.deepcopy(item)
                    replacement.update(revision=item["revision"] + 1,
                                       supersedes={"id": item["id"], "revision": item["revision"]})
                    if item["status"] != "removed":
                        item["status"] = "superseded"
                    concept["requirements"].append(replacement)
                    item = replacement
                elif op == "confirm" and item["status"] != "pending":
                    if (_legacy_local(root, profile) and item["status"] == "confirmed"
                            and not _journal_reference(previous or "")):
                        try:
                            _hand_projection(root, item)
                        except (ValueError, TypeError, KeyError, AttributeError):
                            pass  # Unverified provenance still needs a fresh explicit decision.
                        else:
                            original = item["confirmation"]
                            if (request["user_reference"] != original["reference"]
                                    or action["reason"] != original["reason"]):
                                raise ValueError("Record the original user reference and reason unchanged; "
                                                 "legacy reuse is not new consent")
                    try:
                        _confirmed(root, item)
                    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError):
                        item["prior_confirmation"] = item.get("confirmation")
                    else:
                        raise ValueError("Reuse recorded confirmation; do not reconfirm it")
                elif op == "confirm" and item.get("confirmation"):
                    # Keep the historical goal-only or unverified provenance for context.
                    item["prior_confirmation"] = item["confirmation"]
                for stale in ("pending_reason", "legacy_reuse"):
                    item.pop(stale, None)
                item.update(status="removed" if op == "remove" else "pending" if op == "reopen" else "confirmed",
                            confirmation=confirmation)
            elif op in ("answer", "reopen"):
                item = next(q for q in concept["intent_questions"] if q["id"] == action["id"])
                previous = item.get("confirmation", {}).get("reference")
                if op == "answer" and not _text(action.get("answer")):
                    raise ValueError("Unanswered question remains pending")
                if op == "answer":
                    item.update(status="resolved", answer=action["answer"], confirmation=confirmation)
                else:
                    item.pop("answer", None)
                    item.update(status="pending", confirmation=confirmation)
            else:
                raise ValueError("Only explicit confirm/add/adjust/remove/answer/reopen/restore/select/delegate "
                                 "operations are supported")
            batch["decisions"].append({"question": action.get("id", item["id"]),
                                       "chosen": item.get("goal", item.get("answer", "Reopen decision")),
                                       "rationale": action["reason"], "operation": op,
                                       "supersedes": previous, "intent": copy.deepcopy(item)})
        _validate_question_ids(concept)
        journal["batches"].append(batch)
        _write(root, JOURNAL, journal)
        _write(root, concept_path, concept)
        return _discussion(root, concept)
    if operation == "draft":
        if request.get("route") not in ("product-reconstruction", "new-product") or not _text(request.get("goal")):
            raise ValueError("Product discussion needs an explicit product goal and route")
        if concept.get("requirements"):
            raise ValueError("Existing intent history must be resumed, not overwritten")
        items = request["items"]
        if not isinstance(items, list):
            raise ValueError("items must be an array")
        ids = set()
        for item in items:
            _item(item)
            if item["id"] in ids:
                raise ValueError("Duplicate intent identity")
            ids.add(item["id"])
            if item.get("origin") not in ("inference", "unknown", "user-request"):
                raise ValueError("Draft origin must distinguish inference, unknown or user-request")
            if item["origin"] == "inference" and (not item.get("evidence") or not _text(item.get("uncertainty"))):
                raise ValueError("Inference needs evidence and uncertainty")
            if request["route"] == "new-product" and item["origin"] == "inference":
                raise ValueError("New products start from user intent, not reverse inference")
            if item.get("status") == "confirmed" or "confirmation" in item:
                # A legacy confirmed projection is reused only with canonical journal
                # provenance; the draft never strips or invents confirmation.
                _reuse_legacy_choice(root, item)
            else:
                item.update(revision=1, status="pending")
        facts = request.get("facts", [])
        for evidence in [*facts, *(e for i in items for e in i.get("evidence", []))]:
            path = Path(evidence["path"])
            if path.is_absolute() or not (root / path).resolve().is_relative_to(root.resolve()):
                raise ValueError("Evidence must be project-local")
            if not _text(evidence.get("quote")) or evidence["quote"] not in (root / path).read_text(encoding="utf-8"):
                raise ValueError("Evidence quote is absent from source")
        questions = request.get("questions", [])
        for q in questions:
            if any(not _text(q.get(k)) for k in ("id", "topic", "question")):
                raise ValueError("Questions need identity, topic and question")
            q["status"] = "pending"
        for topic in TOPICS:
            if not any(i["topic"] == topic for i in items):
                questions.append({"id": "gap-" + topic, "topic": topic, "kind": "gap",
                                  "question": "What is the desired " + topic + "?", "status": "pending", "depends_on": []})
        concept.update(requirements=items, intent_facts=facts, intent_questions=questions)
        _validate_question_ids(concept)
        profile = _read(root, PROFILE, {})
        profile.update(task_goal=request["goal"], task_route=request["route"],
                       task_scope={"areas": sorted({a for i in items for a in i["scope"]}) or ["product"], "requirement_refs": []})
        _write(root, CONCEPT, concept)
        _write(root, PROFILE, profile)
        return _discussion(root, concept)
    raise ValueError("Unknown interactive operation")


if __name__ == "__main__":
    import sys
    try:
        request = ({"operation": "run-policy"} if sys.argv[2:] == ["--run-policy"] else
                   {"operation": "delegations"} if sys.argv[2:] == ["--delegations"] else
                   {"operation": "run-event", "event": sys.argv[3]} if len(sys.argv) == 4 and sys.argv[2] == "--policy-event"
                   else json.load(sys.stdin))
        result = session(Path(sys.argv[1]).resolve(), request)
        print(json.dumps(result, ensure_ascii=False))
        if result.get("status") == "needs_run_policy":
            sys.exit(1)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, StopIteration) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}))
        sys.exit(1)
