#!/usr/bin/env python3
"""Canonical repair-authorization accounting shared by both execution hosts.

A repair authorization is a uniquely identified grant to perform one repair attempt
against named QA obligations. It is charged when the grant is durably recorded, not
when the repair succeeds, and recording the same grant again is not another attempt
(CONTEXT.md, ADR 0006).

The ledger is its own file. Repair accounting is the only thing written here, so a
concurrent writer of `.allforai/bootstrap/workflow.json` cannot lose an authorization
and this module cannot lose an unrelated workflow field: the two never race for the
same document.

Scope: this module is the authorization API and its accounting. It decides nothing
about scheduling, dispatch, or acceptance, and its presence is not evidence that
either host consumes it.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from typing import Any
import uuid

LEDGER = '.allforai/bootstrap/repair-authorizations.json'
LOCK = '.allforai/bootstrap/repair-authorizations.lock'
LEDGER_VERSION = 1
# Where the plan declares which repair loops exist and how many attempts each QA
# obligation gets. This is the authority for a bound: a budget named by whoever is asking
# for the grant bounds nothing, because the asker can raise it (CONTEXT.md: the per-QA
# repair budget is the maximum available to an obligation *in its declared repair loop*).
READINESS_SPEC = '.allforai/bootstrap/unattended-run-readiness-spec.json'
# An omitted `max_attempts` is the one legitimate fallback, and both hosts and
# `validate_unattended_readiness.py` already read it as three. A declared-but-unusable
# bound is not a request for this default: it is a planning error.
DEFAULT_REPAIR_ATTEMPTS = 3

STATES = ('authorized', 'started', 'settled')
# authorized: charged, never launched. started: the one-time launch claim is durable, so
# execution may have occurred. settled: its outcome is recorded.
UNRESOLVED = ('authorized', 'started')
OUTCOMES = ('delivered', 'failed', 'aborted', 'unknown')
# What each state lets `settle` assert, because the ledger itself already proves it.
# A grant whose execution was never claimed can only have been abandoned; a claimed one
# can only report what its execution did. Everything else is a determination about an
# execution nobody watched, and that belongs to `reconcile` with evidence — otherwise
# `settle` is just `reconcile` with the evidence gate removed.
SETTLEABLE = {'authorized': ('aborted',), 'started': ('delivered', 'failed')}
DETERMINATIONS = ('executed', 'not_executed')
# A source record's status that ends an attempt, and the outcome it evidences.
TERMINAL_STATUS = {'completed': 'delivered', 'failed': 'failed'}
# Where a source record carries its own time, in the orders these documents use.
TIME_FIELDS = ('at', 'timestamp', 'recorded_at', 'dispatched_at', 'settled_at')
# The one log that records what this run executed. Absence is only evidence against it:
# any other list in the same document is a list of something else, and a record shape
# that cannot name a node is trivially "absent" of every attempt that ever ran.
EXECUTION_LOG = 'transition_log'
# Statuses that are not a refusal. `authorized` is a charge, not permission to run:
# only `start` with execution_allowed=true permits execution.
ACCEPTED = ('ok', 'authorized', 'replayed', 'started', 'settled')
# Statuses that are not success. Everything here exits non-zero from the CLI.
REFUSED = ('blocked', 'budget_exhausted', 'payload_conflict', 'invalid')


class Refusal(Exception):
    """A refusal carrying its own verdict status, so no caller reads a reason as success."""

    def __init__(self, status: str, reason: str, **detail: Any) -> None:
        super().__init__(reason)
        self.verdict = {'status': status, 'reason': reason, **detail}


def blocked(reason: str, **detail: Any) -> Refusal:
    return Refusal('blocked', reason, **detail)


def invalid(reason: str, **detail: Any) -> Refusal:
    return Refusal('invalid', reason, **detail)


def now_iso() -> str:
    return time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())


def new_authorization_id() -> str:
    """A durable unique dispatch id.

    The caller persists it and reuses it for every retry of the same dispatch: that is
    what makes a replay recognisable as the same attempt rather than a second one.
    """
    return uuid.uuid4().hex


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def write_json(target: Path, value: Any) -> None:
    """Write the document durably: no reader sees it half-written, no crash loses it.

    An atomic replace alone only orders the rename against other renames. The bytes and
    the directory entry both have to reach the disk, or a grant this module has already
    told a caller is durable can vanish in a power loss and be handed out again.
    """
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, sort_keys=True, indent=2) + '\n'
    with tempfile.NamedTemporaryFile(mode='w', dir=target.parent, delete=False) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
        temporary = Path(stream.name)
    try:
        temporary.replace(target)
        directory = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def file_digest(target: Path) -> str:
    return 'sha256:' + hashlib.sha256(target.read_bytes()).hexdigest()


@contextmanager
def ledger_lock(root: Path, attempts: int = 1000, interval: float = 0.01):
    """Serialize every read-modify-write of the ledger across processes and threads.

    Without it two dispatches can both read the same spend and both believe they are
    the last attempt within budget.
    """
    lock = root / LOCK
    lock.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(attempts):
        try:
            lock.mkdir()
            break
        except FileExistsError:
            time.sleep(interval)
    else:
        raise blocked('Repair-authorization ledger is locked; another writer holds it or '
                      'an abandoned writer must be reconciled',
                      untrusted='ledger_locked')
    try:
        yield
    finally:
        try:
            lock.rmdir()
        except OSError:
            pass


def text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ''


def positive_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def read_ledger(root: Path) -> dict:
    """The ledger, or a refusal.

    An absent ledger is not zero consumption. It is a run whose history is unknown,
    which stays untrusted until `initialize` records why zero is provable or
    `adopt_history` reconstructs the history from attributable evidence (ADR 0005,
    ADR 0007).
    """
    target = root / LEDGER
    if not target.exists():
        raise blocked('No repair-authorization ledger; absence of records is not proof of '
                      'unused budget. Record a provable new run with "initialize", or '
                      'reconstruct history with "adopt_history"',
                      untrusted='missing_ledger')
    try:
        ledger = json.loads(target.read_text())
    except (ValueError, OSError) as exc:
        raise blocked(f'Repair-authorization ledger is unreadable: {exc}',
                      untrusted='unreadable_ledger')
    if not isinstance(ledger, dict) or ledger.get('ledger_version') != LEDGER_VERSION:
        raise blocked('Repair-authorization ledger is not a version '
                      f'{LEDGER_VERSION} document', untrusted='unreadable_ledger')
    if not text(ledger.get('run_id')) or not isinstance(ledger.get('origin'), dict):
        raise blocked('Repair-authorization ledger has no run identity or origin; its '
                      'consumption cannot be attributed to a run',
                      untrusted='unreadable_ledger')
    entries = ledger.get('authorizations')
    if not isinstance(entries, list):
        raise blocked('Repair-authorization ledger has no readable authorization list',
                      untrusted='unreadable_ledger')
    seen: set[str] = set()
    for entry in entries:
        check_entry(entry, seen)
    return ledger


def check_entry(entry: Any, seen: set[str]) -> None:
    """Refuse any entry whose spend cannot be read exactly.

    A partially readable ledger is worse than none: it silently under-counts, and the
    under-count is spent budget handed out a second time.
    """
    if not isinstance(entry, dict):
        raise blocked(f'Unreadable authorization entry: {json.dumps(entry, sort_keys=True)}',
                      untrusted='unreadable_ledger')
    identifier = text(entry.get('authorization_id'))
    if not identifier or not text(entry.get('repair_node_id')):
        raise blocked('Authorization entry without a dispatch identity or repair node',
                      untrusted='unreadable_ledger')
    if identifier in seen:
        raise blocked(f'Duplicate authorization id {identifier}; the same dispatch is '
                      'recorded twice and its spend is ambiguous',
                      untrusted='unreadable_ledger')
    seen.add(identifier)
    obligations = entry.get('obligations')
    charged = entry.get('charged')
    if (not isinstance(obligations, list) or not obligations
            or not all(text(o) for o in obligations)
            or len(set(obligations)) != len(obligations)):
        raise blocked(f'Authorization {identifier} does not name its QA obligations',
                      untrusted='unreadable_ledger')
    if (not isinstance(charged, dict)
            or sorted(charged) != sorted(obligations)
            or not all(positive_int(charged[o]) for o in obligations)):
        raise blocked(f'Authorization {identifier} does not record what each obligation '
                      'was charged', untrusted='unreadable_ledger')
    budgets = entry.get('budgets')
    if (not isinstance(budgets, dict)
            or not all(positive_int(budgets.get(o)) for o in obligations)):
        # A spend recorded against no bound is a spend nothing can exhaust: `consumption`
        # reports it with an unknown budget, and an unknown budget reads as "not
        # exhausted". Every entry this module writes carries its bound, so an entry
        # without one is an edited ledger, not a state the accounting can reach.
        raise blocked(f'Authorization {identifier} does not record the budget each '
                      'obligation was charged against; a spend with no bound can never '
                      'be exhausted', untrusted='unreadable_ledger')
    if entry.get('state') not in STATES:
        raise blocked(f'Authorization {identifier} does not record which of '
                      f'{", ".join(STATES)} it is in; whether its execution began is '
                      'unknown', untrusted='unreadable_ledger')


def budget_of(entry: dict, obligation: str) -> int | None:
    budgets = entry.get('budgets')
    value = budgets.get(obligation) if isinstance(budgets, dict) else None
    return value if positive_int(value) else None


def spend(ledger: dict, repair_node_id: str, obligation: str) -> int:
    """Attempts already charged to this obligation through this repair node.

    Per obligation, not per repair task: one repair node serving several QA obligations
    spends one attempt of each, and an attempt answering a sibling is never charged
    here (CONTEXT.md, ADR 0005). Started and settled entries both count — the charge is
    the grant, and no settlement refunds it.
    """
    return sum(1 for entry in ledger['authorizations']
               if entry['repair_node_id'] == repair_node_id and obligation in entry['obligations'])


def unresolved(ledger: dict, repair_node_id: str, obligation: str) -> list[str]:
    """Grants for this obligation that have not reached an outcome.

    Both `authorized` and `started` count. A grant that was charged but never claimed may
    still be claimed; one that was claimed may already have run. Neither is a state a
    second grant for the same obligation can be issued over.
    """
    return [entry['authorization_id'] for entry in ledger['authorizations']
            if entry['state'] in UNRESOLVED and entry['repair_node_id'] == repair_node_id
            and obligation in entry['obligations']]


def find(ledger: dict, authorization_id: str) -> dict | None:
    return next((entry for entry in ledger['authorizations']
                 if entry['authorization_id'] == authorization_id), None)


def request_digest(run_id: str, repair_node_id: str, obligations: list[str],
                   budgets: dict) -> str:
    """The payload a replay must match.

    Provenance and timestamps are excluded on purpose: a retry of the same dispatch
    carries a new timestamp, and that is not a different authorization. What must not
    change is which obligations are charged, under which bounds, in which run.
    """
    return digest({'run_id': run_id, 'repair_node_id': repair_node_id,
                   'obligations': sorted(obligations), 'budgets': budgets})


def require_obligations(request: dict) -> tuple[str, list[str], dict]:
    repair_node_id = text(request.get('repair_node_id'))
    if not repair_node_id:
        raise invalid('repair_node_id is required')
    obligations = request.get('obligations')
    if (not isinstance(obligations, list) or not obligations
            or not all(text(o) for o in obligations)):
        raise invalid('obligations must be a non-empty list of QA node ids')
    obligations = [text(o) for o in obligations]
    if len(set(obligations)) != len(obligations):
        raise invalid('obligations names the same QA node twice; one dispatch charges '
                      'each obligation once')
    budgets = request.get('budgets')
    if not isinstance(budgets, dict) or any(not positive_int(budgets.get(o)) for o in obligations):
        raise invalid('budgets must give a positive attempt bound for every obligation')
    return repair_node_id, sorted(obligations), {o: budgets[o] for o in sorted(obligations)}


def require_run(ledger: dict, request: dict) -> str:
    run_id = text(request.get('run_id'))
    if not run_id:
        raise invalid('run_id is required')
    if run_id != ledger['run_id']:
        raise blocked(f'Ledger records run {ledger["run_id"]}, not {run_id}; one run\'s '
                      'accounting is not another\'s', untrusted='run_identity_mismatch')
    return run_id


WORKFLOW = '.allforai/bootstrap/workflow.json'


def read_workflow(root: Path) -> tuple[dict, str]:
    """The run's workflow document and its digest, or a refusal.

    This is the only record of whether the run has executed anything, so nothing about
    a run's history is taken on a caller's word: it is read here.
    """
    target = root / WORKFLOW
    if not target.exists():
        raise blocked(f'No {WORKFLOW}; there is no run whose history could be verified',
                      untrusted='missing_workflow')
    try:
        workflow = json.loads(target.read_text())
    except (ValueError, OSError) as exc:
        raise blocked(f'{WORKFLOW} is unreadable: {exc}; whether this run has executed '
                      'anything cannot be established', untrusted='unreadable_workflow')
    if not isinstance(workflow, dict):
        raise blocked(f'{WORKFLOW} is not a workflow document',
                      untrusted='unreadable_workflow')
    return workflow, file_digest(target)


def execution_traces(workflow: dict) -> dict:
    """How much execution the workflow document shows.

    Any non-zero count means this run has a history, and a history that the ledger does
    not contain is missing accounting — not unused budget.
    """
    transitions = workflow.get('transition_log')
    routes = workflow.get('repair_routes')
    completed = [n for n in workflow.get('nodes') or []
                 if isinstance(n, dict) and n.get('status') in ('completed', 'failed')]
    return {'transition_log': len(transitions) if isinstance(transitions, list) else 0,
            'repair_routes': len(routes) if isinstance(routes, list) else 0,
            'completed': len(completed)}


def loop_binding(workflow: dict) -> dict:
    """A digest over the declared repair loops only.

    Deliberately not over completion or transition state: those move every wave, and a
    binding that moved with them would either reject normal progress or invite a silent
    reset. Dynamic expansion may add loops later — that is supported, and it changes
    this digest without invalidating anything, because a newly declared obligation
    simply has no history to lose.
    """
    loops = []
    for loop in workflow.get('required_repair_loops') or workflow.get('repair_loops') or []:
        if not isinstance(loop, dict):
            continue
        loops.append({'repair_node_id': text(loop.get('repair_node_id')),
                      'qa_node_ids': sorted(text(q) for q in
                                            (loop.get('qa_node_ids') or loop.get('qa_nodes') or [])
                                            if text(q)),
                      'max_attempts': loop.get('max_attempts')})
    loops.sort(key=lambda entry: (entry['repair_node_id'], entry['qa_node_ids']))
    return {'repair_loops_digest': 'sha256:' + digest(loops), 'loops': len(loops)}


def declared_budget(loop: dict, index: int) -> int:
    """The attempts one declared loop authorizes per QA obligation.

    Mirrors what both hosts and the readiness validator already do, because a bound they
    disagree about is not a bound: an omitted `max_attempts` takes the documented default,
    and a declared one that is not a positive integer is a planning error rather than a
    request for that default. Defaulting there would grant attempts the plan never
    authorized — exactly the substitution this refuses to make silently.
    """
    if 'max_attempts' not in loop:
        return DEFAULT_REPAIR_ATTEMPTS
    bound = loop['max_attempts']
    if not positive_int(bound):
        raise blocked(f'required_repair_loops[{index}] declares max_attempts '
                      f'{json.dumps(bound)}, which is not a positive attempt bound. An '
                      'unusable bound routes nothing and is not read as the default; fix '
                      'the declaration rather than charging against a bound nobody set',
                      untrusted='invalid_repair_declaration', declared=bound)
    return bound


def declared_bounds(root: Path) -> dict[tuple[str, str], int]:
    """{(repair node, QA node): its declared attempt bound}, or a refusal.

    Read fresh on every grant, so dynamic expansion is supported by construction: a loop
    declared later simply appears here and becomes grantable, and one already charged
    keeps its spend because nothing about this reading touches the ledger. What it will
    not do is invent a bound. A plan that cannot be read, or that says two different
    things about the same obligation, leaves the run blocked with something to fix (ADR
    0005: untrusted state stops affected work).
    """
    target = root / READINESS_SPEC
    if not target.exists():
        raise blocked(f'No {READINESS_SPEC}; the repair loops and their per-QA attempt '
                      'bounds are undeclared, and a bound the caller supplies is not a '
                      'bound. Plan the run before charging repair budget against it',
                      untrusted='undeclared_repair_plan')
    try:
        spec = json.loads(target.read_text())
    except (ValueError, OSError) as exc:
        raise blocked(f'{READINESS_SPEC} is unreadable: {exc}; which repair loops the plan '
                      'declares, and what each obligation may spend, cannot be established',
                      untrusted='undeclared_repair_plan')
    loops = spec.get('required_repair_loops') if isinstance(spec, dict) else None
    if not isinstance(loops, list):
        raise blocked(f'{READINESS_SPEC} declares no readable required_repair_loops list; '
                      'there is no plan against which a repair budget could be bounded',
                      untrusted='undeclared_repair_plan')
    bounds: dict[tuple[str, str], int] = {}
    for index, loop in enumerate(loops):
        if not isinstance(loop, dict):
            raise blocked(f'required_repair_loops[{index}] is not a loop declaration',
                          untrusted='invalid_repair_declaration')
        repair_node_id = text(loop.get('repair_node_id'))
        if not repair_node_id:
            raise blocked(f'required_repair_loops[{index}] names no repair_node_id, so the '
                          'obligations it bounds cannot be identified',
                          untrusted='invalid_repair_declaration')
        qa_nodes = next((loop[key] for key in ('qa_node_ids', 'qa_nodes')
                         if isinstance(loop.get(key), list)), None)
        if qa_nodes is None or not all(text(q) for q in qa_nodes) or not qa_nodes:
            raise blocked(f'required_repair_loops[{index}] does not list the QA node ids '
                          f'repair node {repair_node_id} answers for',
                          untrusted='invalid_repair_declaration')
        bound = declared_budget(loop, index)
        for qa_node_id in (text(q) for q in qa_nodes):
            key = (repair_node_id, qa_node_id)
            if bounds.get(key, bound) != bound:
                # Two declarations of one obligation with different bounds: neither is
                # the plan's answer, and picking one would be this module choosing the
                # budget the plan failed to state.
                raise blocked(f'The plan declares {qa_node_id} through {repair_node_id} '
                              f'with both {bounds[key]} and {bound} attempts; which bound '
                              'this obligation has is ambiguous',
                              untrusted='ambiguous_repair_declaration',
                              declared=sorted({bounds[key], bound}))
            bounds[key] = bound
    return bounds


def require_declared(bounds: dict, repair_node_id: str, obligations: list[str],
                     budgets: dict, context: str) -> None:
    """Refuse a charge the plan does not authorize, at the bound the plan sets.

    Membership first: a pair the plan never declared has no budget at all, so charging it
    invents both the loop and its bound. Then the bound itself — refused on a mismatch
    rather than quietly corrected, because a caller asking to spend 99 against a declared
    3 is a defect in that caller, and answering it with a silent 3 hides the disagreement
    instead of surfacing it.
    """
    undeclared = [o for o in obligations if (repair_node_id, o) not in bounds]
    if undeclared:
        raise blocked(f'The plan declares no repair loop charging '
                      f'{", ".join(undeclared)} through {repair_node_id}; {context} an '
                      'obligation the plan never gave a budget invents the budget',
                      untrusted='undeclared_repair_pair', repair_node_id=repair_node_id,
                      undeclared=undeclared)
    conflicting = {o: {'declared': bounds[(repair_node_id, o)], 'stated': budgets[o]}
                   for o in obligations if budgets[o] != bounds[(repair_node_id, o)]}
    if conflicting:
        raise blocked(f'{context} a bound the plan did not declare: '
                      f'{json.dumps(conflicting, sort_keys=True)}. The declared repair '
                      'loop sets the per-QA budget; a bound named by whoever wants the '
                      'attempt bounds nothing',
                      untrusted='budget_not_declared', repair_node_id=repair_node_id,
                      budgets=conflicting)


def initialize(root: Path, run_id: str) -> dict:
    """Record that this run provably starts at zero, having checked that it does.

    Zero is a claim about history, and this module verifies it rather than accepting it.
    A workflow with any transition, repair route, or finished node has a history: its
    accounting must be recovered from that evidence, never assumed absent.
    """
    run_id = text(run_id)
    if not run_id:
        raise invalid('run_id is required')
    with ledger_lock(root):
        target = root / LEDGER
        if target.exists():
            existing = read_ledger(root)
            if existing['run_id'] == run_id:
                # Re-recording the same origin is the same statement, not a reset.
                return {'status': 'ok', 'reason': 'Run origin already recorded',
                        'run_id': run_id, 'replayed': True,
                        'origin': existing['origin']['kind'],
                        'authorizations': len(existing['authorizations'])}
            # Replacing a run's accounting is a decision only a user can take, and a
            # caller's own say-so is not that user's decision. There is no verified
            # record of such a confirmation to check here, so this refuses rather than
            # inventing a proof format nothing produces (ADR 0007).
            raise blocked(f'The ledger belongs to run {existing["run_id"]}, not {run_id}. '
                          'Replacing a run\'s accounting requires a user decision this '
                          'module cannot verify; move or archive the existing ledger '
                          'deliberately instead',
                          untrusted='existing_run', existing_run_id=existing['run_id'])
        workflow, source_digest = read_workflow(root)
        observed = execution_traces(workflow)
        if any(observed.values()):
            raise blocked(f'{WORKFLOW} already shows execution '
                          f'({json.dumps(observed, sort_keys=True)}); this run has a '
                          'history, and a missing ledger is not proof that it spent no '
                          'repair budget. Recover it with "adopt_history"',
                          untrusted='prior_execution', observed=observed)
        binding = loop_binding(workflow)
        proof = {'kind': 'verified_untouched_workflow', 'source_path': WORKFLOW,
                 'source_digest': source_digest, 'observed': observed,
                 'verified_at': now_iso()}
        write_json(target, {'ledger_version': LEDGER_VERSION, 'run_id': run_id,
                            'origin': {'kind': 'new_run', 'proof': proof,
                                       'binding': binding, 'recorded_at': now_iso()},
                            'authorizations': []})
        return {'status': 'ok',
                'reason': 'Workflow verified untouched; this run provably starts at zero',
                'run_id': run_id, 'origin': 'new_run', 'proof': proof, 'binding': binding}


def verify_source(root: Path, evidence: dict) -> tuple[Any, str]:
    """The document the evidence points at, proved to be the document it describes.

    Evidence that only asserts what a file said is not evidence: it cannot be checked,
    and a stale or edited source would reconstruct the wrong spend.
    """
    source_path = text(evidence.get('source_path'))
    source_digest = text(evidence.get('source_digest'))
    if not source_path or not source_digest:
        raise blocked('Evidence must name a source_path and its source_digest; an '
                      'unverifiable assertion is not attributable evidence',
                      untrusted='unverifiable_evidence')
    target = root / source_path
    if '..' in Path(source_path).parts or not target.is_file():
        raise blocked(f'Evidence source {source_path} is not a readable file in this '
                      'project', untrusted='unverifiable_evidence')
    actual = file_digest(target)
    if actual != source_digest:
        raise blocked(f'Evidence source {source_path} does not match its stated digest; '
                      'it changed, or the evidence describes another document',
                      untrusted='unverifiable_evidence',
                      stated=source_digest, actual=actual)
    return target, actual


def adopt_history(root: Path, run_id: str, evidence: Any) -> dict:
    """Reconstruct prior accounting from complete, verified, attributable evidence.

    Each record must resolve to a real entry of the real legacy ledger, and every entry
    of that ledger must be claimed exactly once. Anything less leaves the run blocked:
    a reconstruction that misses entries under-counts the spend, and an under-count is
    indistinguishable from unused budget (ADR 0007).
    """
    run_id = text(run_id)
    if not run_id:
        raise invalid('run_id is required')
    if not isinstance(evidence, dict):
        raise invalid('evidence must be an object')
    target, source_digest = verify_source(root, evidence)
    if text(evidence.get('source_path')) != WORKFLOW:
        # A digest proves a file is itself, which any caller can arrange for a file it
        # just wrote. What the history has to be reconstructed from is the run's own
        # record of what it did, exactly as `prove_absence` binds absence to it — without
        # this, a hand-written document reconstructs whatever spend its author preferred.
        raise blocked(f'Historical evidence must be the run\'s own {WORKFLOW}, not '
                      f'{evidence.get("source_path")}. Another document records this '
                      'run\'s repair history only by assertion, and an assertion a caller '
                      'authored is not attributable evidence',
                      untrusted='unverifiable_evidence', expected_source=WORKFLOW)
    if evidence.get('complete') is not True:
        raise blocked('Historical evidence is not asserted complete; absence of records '
                      'is not proof of unused budget',
                      untrusted='incomplete_history', source_path=str(target.name))
    records = evidence.get('authorizations')
    if not isinstance(records, list):
        raise invalid('evidence.authorizations must be a list')
    if (root / LEDGER).exists():
        # Checked before the records are validated so a live run is told the real reason
        # it cannot adopt history, not a complaint about evidence it will never use. The
        # authoritative check is still taken under the lock below.
        existing = read_ledger(root)
        raise blocked(f'Ledger already records run {existing["run_id"]}; adopting '
                      'history over live accounting would rewrite it',
                      untrusted='existing_run', existing_run_id=existing['run_id'])
    document = load_source(target)
    routes = legacy_routes(document)
    observed = execution_traces(document)
    # Historical charges are bounded by the plan that stands now. A pair the plan no
    # longer declares cannot be given a budget here, and saying so is more useful than
    # adopting a spend nothing bounds.
    bounds = declared_bounds(root)
    adopted: list[dict] = []
    seen: set[str] = set()
    claimed: dict[int, str] = {}
    cited: dict[str, str] = {}
    source = f'{evidence["source_path"]}@{source_digest}'
    for record in records:
        adopted.append(adopt_one(record, source, seen, routes, claimed, document, cited,
                                 bounds))
    unclaimed = sorted(set(range(len(routes))) - set(claimed))
    if unclaimed:
        raise blocked(f'Historical evidence leaves repair_routes entries {unclaimed} '
                      'unaccounted for; a partial reconstruction under-counts the spend',
                      untrusted='incomplete_history', unclaimed=unclaimed)
    if len(adopted) != observed['repair_routes']:
        # Belt to the `unclaimed` braces: the adopted count is the workflow's own charge
        # count, so the reconstruction is checked against what the run shows it did rather
        # than against the caller's list of what it says happened.
        raise blocked(f'Reconstruction adopts {len(adopted)} authorizations while '
                      f'{WORKFLOW} records {observed["repair_routes"]} charges '
                      f'({json.dumps(observed, sort_keys=True)}); the spend it accounts '
                      'for is not the spend the run shows',
                      untrusted='incomplete_history', observed=observed,
                      adopted=len(adopted))
    with ledger_lock(root):
        if (root / LEDGER).exists():
            existing = read_ledger(root)
            raise blocked(f'Ledger already records run {existing["run_id"]}; adopting '
                          'history over live accounting would rewrite it',
                          untrusted='existing_run', existing_run_id=existing['run_id'])
        workflow, _ = read_workflow(root)
        write_json(root / LEDGER, {
            'ledger_version': LEDGER_VERSION, 'run_id': run_id,
            'origin': {'kind': 'adopted_history',
                       'proof': {'kind': 'verified_attributable_evidence',
                                 'source_path': evidence['source_path'],
                                 'source_digest': source_digest,
                                 'records': len(adopted), 'routes': len(routes),
                                 'observed': observed, 'verified_at': now_iso()},
                       'binding': loop_binding(workflow), 'recorded_at': now_iso()},
            'authorizations': adopted})
        return {'status': 'ok',
                'reason': 'Historical authorizations adopted with their provenance',
                'run_id': run_id, 'origin': 'adopted_history', 'adopted': len(adopted),
                'unresolved': sorted(entry['authorization_id'] for entry in adopted
                                     if entry['state'] in UNRESOLVED)}


def load_source(target: Path) -> dict:
    """The verified evidence document, parsed once for every reference resolved in it."""
    try:
        document = json.loads(target.read_text())
    except (ValueError, OSError) as exc:
        raise blocked(f'Evidence source is unreadable: {exc}',
                      untrusted='unverifiable_evidence')
    if not isinstance(document, dict):
        raise blocked('Evidence source is not a document whose records can be resolved',
                      untrusted='unverifiable_evidence')
    return document


def legacy_routes(document: dict) -> list[dict]:
    """The legacy `repair_routes` ledger the evidence must reconstruct.

    This is the one historical format that actually exists, and it records exactly one
    thing: that an attempt was charged. It carries no record of whether that attempt ran
    or how it ended, so nothing about execution may be read out of it.
    """
    routes = document.get('repair_routes')
    if not isinstance(routes, list):
        raise blocked('Evidence source holds no readable repair_routes ledger; there is '
                      'no trustworthy record of what was already spent',
                      untrusted='unverifiable_evidence')
    if not routes:
        # An empty legacy ledger reconstructs nothing, so "adopting" it only stamps a
        # zero-spend origin with a provenance record. Absence of records is not proof of
        # unused budget (ADR 0007): a run that provably never executed is `initialize`'s
        # question, answered from the workflow, not a history to adopt.
        raise blocked('The legacy repair_routes ledger is empty, so there is no history '
                      'to reconstruct and no evidence that none was spent. A run that '
                      'provably never executed is recorded with "initialize", which '
                      'verifies that claim against the workflow',
                      untrusted='incomplete_history')
    for index, route in enumerate(routes):
        if (not isinstance(route, dict) or not text(route.get('repair_node_id'))
                or not text(route.get('qa_node_id'))):
            raise blocked(f'repair_routes[{index}] does not identify a repair and a QA '
                          'node; the historical spend cannot be attributed',
                          untrusted='ambiguous_history')
    return routes


ROUTE_REF = re.compile(r'^repair_routes\[(\d+)\]$')
RECORD_REF = re.compile(r'^([A-Za-z_][A-Za-z0-9_]*)\[(\d+)\]$')


def resolve_ref(document: dict, reference: str) -> dict | None:
    """The record a `field[index]` reference names, or None if it names nothing."""
    matched = RECORD_REF.match(text(reference))
    if not matched:
        return None
    values = document.get(matched.group(1))
    if not isinstance(values, list) or int(matched.group(2)) >= len(values):
        return None
    record = values[int(matched.group(2))]
    return record if isinstance(record, dict) else None


def names_authorization(record: dict) -> bool:
    """Whether this record identifies the attempt it is about, rather than only its node."""
    return bool(text(record.get('authorization_id')))


def attributes_to(record: dict, authorization_id: str, repair_node_id: str) -> bool:
    """Whether this source record is about that authorization, or about its repair node.

    Identity is what makes evidence evidence. A record that names some other node says
    nothing about this attempt, however truthfully it was digested.

    A record that names an authorization has already said which attempt it is about, so a
    mismatch there ends the question: falling back to the node would read a record that
    states it belongs to a different grant as evidence about this one. The node fallback
    exists for records that carry no identity of their own, and for those the caller must
    still show that no sibling attempt of the same node could equally claim them.
    """
    if names_authorization(record):
        return text(record['authorization_id']) == authorization_id
    return text(record.get('node') or record.get('node_id')) == repair_node_id


def record_time(record: dict) -> str:
    return next((text(record[field]) for field in TIME_FIELDS
                 if text(record.get(field))), '')


def predates(record: dict, moment: str) -> bool:
    """Whether this record is provably older than `moment`.

    Both are the same fixed-width UTC format, so ordering them as text is ordering them
    in time. A record with no time of its own is not provably older, and is treated as
    possibly relevant rather than dismissed.
    """
    stamp = record_time(record)
    return bool(stamp and moment and stamp < moment)


def adopted_execution(record: dict, identifier: str, repair_node_id: str, state: str,
                      document: dict, route: dict,
                      cited: dict[str, str]) -> tuple[str | None, dict | None, str]:
    """What the source actually evidences about this historical attempt's execution.

    Returns the outcome to record, the attribution behind it, and the time that
    attribution happened — the timestamp the adopted entry dates itself from, so the
    entry's own chronology comes from the source rather than from the caller.

    An `authorized` claim needs nothing: the route already proves the charge. A `started`
    or `settled` claim must resolve to a record of the same verified source that is about
    this attempt, and a settled one must resolve to a terminal record — whose status
    decides the outcome, so a caller cannot name one the evidence does not show.

    Legacy records rarely name an authorization, so most attributions here run through
    the node fallback, and one node may hold many historical attempts. Two conditions
    make such a record identify a single one: no other adopted authorization may cite the
    same record, and the record must be datable and no older than the charge it is
    claimed to evidence. Without both, one run of a node could be spread across every
    attempt that node ever had.
    """
    if state == 'authorized':
        return None, None, ''
    field = 'settlement_ref' if state == 'settled' else 'start_ref'
    reference = text(record.get(field))
    if not reference:
        raise blocked(f'Historical authorization {identifier} claims "{state}" but gives '
                      f'no {field}. A repair_routes entry proves only that an attempt was '
                      'charged, never that it ran or how it ended: name the record that '
                      'shows it, or adopt it as "authorized" and reconcile it',
                      untrusted='ambiguous_history')
    observed = resolve_ref(document, reference)
    if observed is None:
        raise blocked(f'{field} {reference} of historical authorization {identifier} does '
                      'not resolve to a record of the verified source',
                      untrusted='ambiguous_history')
    if not attributes_to(observed, identifier, repair_node_id):
        raise blocked(f'{field} {reference} is not about authorization {identifier} or '
                      f'its repair node {repair_node_id}; it evidences some other work',
                      untrusted='unattributable_evidence')
    if not names_authorization(observed):
        if reference in cited:
            raise blocked(f'{reference} is cited by both {cited[reference]} and '
                          f'{identifier}, and names only repair node {repair_node_id}; '
                          'one record of a node is one attempt of it, not evidence for '
                          'every attempt that node ever had',
                          untrusted='unattributable_evidence')
        cited[reference] = identifier
    moment = record_time(observed)
    if not moment:
        raise blocked(f'{field} {reference} carries no time, so it cannot be placed '
                      f'against the charge it evidences for {identifier}; an undated '
                      f'record of {repair_node_id} may be any of its runs',
                      untrusted='unattributable_evidence')
    charged_at = text(route.get('dispatched_at'))
    if charged_at and moment < charged_at:
        raise blocked(f'{field} {reference} is dated {moment}, before the charge it '
                      f'evidences was dispatched at {charged_at}; it records earlier '
                      f'work, not authorization {identifier}',
                      untrusted='unattributable_evidence')
    if state == 'started':
        return None, {'kind': 'start_record', 'start_ref': reference,
                      'record': observed}, moment
    status = text(observed.get('status'))
    if status not in TERMINAL_STATUS:
        raise blocked(f'settlement_ref {reference} has status {status or "none"}, which '
                      f'does not end an attempt. A settled claim needs a terminal record '
                      f'({", ".join(sorted(TERMINAL_STATUS))})',
                      untrusted='ambiguous_history')
    evidenced = TERMINAL_STATUS[status]
    declared = record.get('outcome')
    if declared is not None and declared != evidenced:
        raise blocked(f'Historical authorization {identifier} declares outcome '
                      f'"{declared}" but {reference} evidences "{evidenced}"; the record '
                      'does not get to overrule what the source shows',
                      untrusted='ambiguous_history')
    return evidenced, {'kind': 'settlement_record', 'settlement_ref': reference,
                       'status': status, 'record': observed}, moment


def adopt_one(record: Any, source: str, seen: set[str], routes: list[dict],
              claimed: dict[int, str], document: dict, cited: dict[str, str],
              bounds: dict) -> dict:
    """One historical authorization, resolved against the real ledger entry it claims."""
    if not isinstance(record, dict):
        raise blocked('Historical record is not an authorization object',
                      untrusted='ambiguous_history')
    identifier = text(record.get('authorization_id'))
    if not identifier:
        raise blocked('Historical record has no authorization id; it cannot be attributed '
                      'to a specific prior dispatch', untrusted='ambiguous_history')
    if identifier in seen:
        raise blocked(f'Historical evidence names authorization {identifier} twice; its '
                      'spend is ambiguous', untrusted='ambiguous_history')
    seen.add(identifier)
    reference = text(record.get('source_ref'))
    matched = ROUTE_REF.match(reference)
    if not matched or int(matched.group(1)) >= len(routes):
        raise blocked(f'Historical authorization {identifier} has no source_ref resolving '
                      'to a repair_routes entry of the verified source; its provenance '
                      'cannot be checked', untrusted='ambiguous_history')
    index = int(matched.group(1))
    if index in claimed:
        raise blocked(f'{reference} is claimed by both {claimed[index]} and {identifier}; '
                      'the same historical attempt cannot be two authorizations',
                      untrusted='ambiguous_history')
    claimed[index] = identifier
    route = routes[index]
    repair_node_id = text(record.get('repair_node_id'))
    obligations = sorted(text(o) for o in record.get('obligations') or [] if text(o))
    if repair_node_id != text(route['repair_node_id']) or obligations != [text(route['qa_node_id'])]:
        raise blocked(f'Historical authorization {identifier} does not match {reference}, '
                      f'which charges {route["qa_node_id"]} through '
                      f'{route["repair_node_id"]}', untrusted='ambiguous_history')
    state = record.get('state')
    if state not in STATES:
        raise blocked(f'Historical authorization {identifier} does not state which of '
                      f'{", ".join(STATES)} it reached; whether its execution began is '
                      'unknown', untrusted='ambiguous_history')
    # The route proves a charge and nothing else. Claiming the attempt ran, or ended,
    # asserts facts that are not in it, so those claims need their own record in the same
    # verified source. Without one the honest adoption is `authorized`: charged, with its
    # execution unresolved, which blocks until reconciled rather than resuming as though
    # the attempt were known to be finished.
    outcome, attribution, moment = adopted_execution(record, identifier, repair_node_id,
                                                     state, document, route, cited)
    # An adopted charge is bounded by the plan, exactly like a live one. A record that
    # states no bound takes the declared one — there is nothing to overrule, and a spend
    # with no bound could never be exhausted. A record that states a different one is
    # refused rather than corrected: history the caller re-prices is not history.
    stated = record.get('budgets') if isinstance(record.get('budgets'), dict) else {}
    budgets = {o: stated.get(o, bounds.get((repair_node_id, o))) for o in obligations}
    require_declared(bounds, repair_node_id, obligations,
                     {o: budgets[o] for o in obligations},
                     f'historical authorization {identifier} claims')
    # Dates come from the source wherever the record leaves them out: a `started` claim
    # is dated by the record that shows the start, so the chronology a later
    # reconciliation is checked against is the evidence's, never the caller's.
    granted_at = text(record.get('granted_at')) or text(route.get('dispatched_at'))
    started_at = text(record.get('started_at')) or (moment if state != 'authorized' else '')
    settled_at = text(record.get('settled_at')) or (moment if state == 'settled' else '')
    entry = {'authorization_id': identifier, 'repair_node_id': repair_node_id,
             'obligations': obligations, 'charged': record.get('charged'),
             'budgets': {o: budgets[o] for o in obligations},
             'state': state, 'outcome': outcome,
             'granted_at': granted_at or None,
             'started_at': started_at or None,
             'settled_at': settled_at or None,
             'request_digest': None,
             'provenance': {'adopted_from': reference, 'source': source,
                            'route': route, 'execution': attribution,
                            'adopted_at': now_iso()}}
    try:
        check_entry(entry, set())
    except Refusal as refusal:
        raise blocked(f'Historical authorization {identifier} is not attributable: '
                      f'{refusal.verdict["reason"]}', untrusted='ambiguous_history')
    return entry


def authorize(root: Path, request: dict) -> dict:
    """Grant one repair attempt against the named obligations, or refuse it.

    The whole grant is decided and written under one lock, so a multi-obligation
    dispatch is charged to every obligation or to none: a partial charge would leave a
    sibling silently paying for an attempt that was never authorized.
    """
    identifier = text(request.get('authorization_id'))
    if not identifier:
        raise invalid('authorization_id is required; a dispatch without a durable unique '
                      'identity cannot be replayed idempotently')
    repair_node_id, obligations, budgets = require_obligations(request)
    provenance = request.get('provenance') if isinstance(request.get('provenance'), dict) else {}
    with ledger_lock(root):
        ledger = read_ledger(root)
        run_id = require_run(ledger, request)
        wanted = request_digest(run_id, repair_node_id, obligations, budgets)
        existing = find(ledger, identifier)
        if existing is not None:
            # The same dispatch recorded again is not another attempt.
            if existing.get('request_digest') != wanted:
                raise Refusal('payload_conflict',
                              f'Authorization {identifier} already stands for a different '
                              'payload; a reused identity with changed obligations or '
                              'bounds is a defect, not a replay',
                              authorization_id=identifier,
                              recorded={'repair_node_id': existing['repair_node_id'],
                                        'obligations': existing['obligations'],
                                        'budgets': existing.get('budgets', {})})
            # A replay is bookkeeping, never a licence to run: only `start` permits
            # execution, and only the first time.
            return {'status': 'replayed', 'execution_allowed': False,
                    'reason': 'This dispatch is already authorized; nothing further '
                              'charged. Claim execution with "start"',
                    'authorization_id': identifier, 'run_id': run_id,
                    'repair_node_id': repair_node_id, 'charged': existing['charged'],
                    'state': existing['state']}
        # What the plan authorizes, read fresh so a loop declared by a later expansion is
        # grantable and one the plan never declared is not. This precedes every question
        # about ledger state: an undeclared charge has no budget to be within.
        require_declared(declared_bounds(root), repair_node_id, obligations, budgets,
                         'charging')
        # A prior grant that never reached an outcome leaves it unknown whether that
        # attempt ran. Handing out a new one would replay uncertain work; refunding it
        # would hand back budget that may already have been spent (ADR 0006). Only these
        # obligations are blocked — an independent repair elsewhere grants normally.
        stuck = {o: ids for o in obligations
                 for ids in [unresolved(ledger, repair_node_id, o)] if ids}
        if stuck:
            raise blocked('An earlier authorization for these obligations has no recorded '
                          'outcome; whether its execution occurred is unknown. Reconcile '
                          'it with evidence — this module neither replays nor refunds it',
                          untrusted='unresolved_authorization', unresolved=stuck)
        conflicting = {}
        for obligation in obligations:
            recorded = recorded_budget(ledger, repair_node_id, obligation)
            if recorded is not None and recorded != budgets[obligation]:
                conflicting[obligation] = {'recorded': recorded,
                                           'requested': budgets[obligation]}
        if conflicting:
            # The request already matches the current declaration, so reaching here means
            # the declaration itself moved under a history charged against the old bound.
            # Re-pointing that history at a new bound would silently re-price attempts
            # already spent, and resetting the ledger would lose them; both are worse than
            # stopping. The plan and the spend have to be reconciled by a person.
            raise blocked('The declared bound for these obligations differs from the one '
                          'their recorded attempts were charged against; a bound that '
                          'moves is not a bound. Reconcile the plan with the spend '
                          'already made — this module neither re-prices it nor resets it',
                          untrusted='budget_conflict', budgets=conflicting)
        charged = {o: spend(ledger, repair_node_id, o) + 1 for o in obligations}
        over = {o: {'spent': charged[o] - 1, 'budget': budgets[o]}
                for o in obligations if charged[o] > budgets[o]}
        if over:
            # All-or-none: an obligation with budget left is not charged on behalf of an
            # exhausted sibling, and the exhausted sibling is not charged again.
            raise Refusal('budget_exhausted',
                          'Repair budget is exhausted for at least one obligation; nothing '
                          'was charged. An exhausted obligation is not accepted — it still '
                          'has to be satisfied',
                          authorization_id=identifier, repair_node_id=repair_node_id,
                          exhausted=over,
                          remaining={o: budgets[o] - (charged[o] - 1) for o in obligations})
        entry = {'authorization_id': identifier, 'repair_node_id': repair_node_id,
                 'obligations': obligations, 'charged': charged, 'budgets': budgets,
                 'state': 'authorized', 'outcome': None, 'granted_at': now_iso(),
                 'started_at': None, 'settled_at': None, 'request_digest': wanted,
                 'provenance': provenance}
        ledger['authorizations'].append(entry)
        write_json(root / LEDGER, ledger)
        # Durable before the caller is told anything: the charge is on disk before any
        # work it could pay for. The grant alone still authorizes no execution.
        return {'status': 'authorized', 'execution_allowed': False,
                'reason': 'Repair attempt authorized and durably charged. It authorizes '
                          'no execution until "start" claims it',
                'authorization_id': identifier, 'run_id': run_id,
                'repair_node_id': repair_node_id, 'charged': charged,
                'remaining': {o: budgets[o] - charged[o] for o in obligations},
                'state': 'authorized'}


def recorded_budget(ledger: dict, repair_node_id: str, obligation: str) -> int | None:
    for entry in reversed(ledger['authorizations']):
        if entry['repair_node_id'] == repair_node_id and obligation in entry['obligations']:
            bound = budget_of(entry, obligation)
            if bound is not None:
                return bound
    return None


def start(root: Path, run_id: str, authorization_id: str) -> dict:
    """Claim the one execution this authorization pays for.

    Separated from `authorize` because a charge and a launch answer different questions.
    An authorize that is retried after a lost response must not re-run anything, so only
    the first successful claim returns `execution_allowed`. Every later call — a replay,
    a resumed driver, a second worker — is told no, whatever else it knows.
    """
    identifier = text(authorization_id)
    if not identifier:
        raise invalid('authorization_id is required')
    with ledger_lock(root):
        ledger = read_ledger(root)
        require_run(ledger, {'run_id': run_id})
        entry = find(ledger, identifier)
        if entry is None:
            raise blocked(f'No authorization {identifier} to start; execution without a '
                          'durable grant is exactly what the grant exists to prevent',
                          untrusted='unknown_authorization')
        if entry['state'] == 'settled':
            raise blocked(f'Authorization {identifier} is already settled; a spent '
                          'attempt is not restartable. Re-execution needs a new '
                          'authorization and a new charge',
                          untrusted='already_settled', outcome=entry.get('outcome'))
        if entry['state'] == 'started':
            return {'status': 'started', 'execution_allowed': False, 'replayed': True,
                    'reason': 'This attempt was already claimed; whether it ran is not '
                              'this call\'s to assume. Settle or reconcile it',
                    'authorization_id': identifier, 'state': 'started',
                    'charged': entry['charged'], 'claimed_at': entry.get('started_at')}
        entry['state'] = 'started'
        entry['started_at'] = now_iso()
        write_json(root / LEDGER, ledger)
        # Durable before the caller is told it may run: a claim that is not on disk
        # cannot stop a restart from running the same attempt twice.
        return {'status': 'started', 'execution_allowed': True,
                'reason': 'Execution claimed for this authorization, once',
                'authorization_id': identifier, 'state': 'started',
                'charged': entry['charged'], 'claimed_at': entry['started_at']}


def settle(root: Path, authorization_id: str, outcome: str, evidence: Any = None) -> dict:
    """Record how an attempt ended, when the ledger already proves what may be said.

    It never returns budget: delivery is not acceptance and failure is not a refund, so
    the attempt is spent either way.

    What it will not do is resolve an uncertainty. A grant whose execution was never
    claimed can only have been abandoned; a claimed one can only report what its
    execution did. `unknown` is not settleable at all — it is what `reconcile` records
    against evidence. Without this, `settle(id, "unknown")` would clear an
    unresolved-execution blocker with no evidence whatsoever and let the next
    authorization rerun work that may already have happened (ADR 0006).
    """
    identifier = text(authorization_id)
    if not identifier:
        raise invalid('authorization_id is required')
    if outcome not in OUTCOMES:
        raise invalid(f'outcome must be one of {", ".join(OUTCOMES)}')
    if outcome == 'unknown':
        raise invalid('"unknown" is not a settlement. An attempt whose execution is '
                      'uncertain is reconciled against attributable evidence, not '
                      'declared resolved')
    with ledger_lock(root):
        ledger = read_ledger(root)
        entry = find(ledger, identifier)
        if entry is None:
            raise blocked(f'No authorization {identifier} to settle; an unrecorded grant '
                          'cannot be reconciled', untrusted='unknown_authorization')
        if entry['state'] == 'settled':
            if entry.get('outcome') != outcome:
                raise Refusal('payload_conflict',
                              f'Authorization {identifier} is already settled as '
                              f'{entry.get("outcome")}; it cannot also be {outcome}',
                              authorization_id=identifier, recorded_outcome=entry.get('outcome'))
            return {'status': 'settled', 'reason': 'Already settled with this outcome',
                    'authorization_id': identifier, 'outcome': outcome, 'replayed': True,
                    'charged': entry['charged'], 'refunded': False}
        allowed = SETTLEABLE[entry['state']]
        if outcome not in allowed:
            if entry['state'] == 'authorized':
                raise blocked(f'Authorization {identifier} never claimed its execution, '
                              f'so "{outcome}" reports an execution that did not start. '
                              f'Settle it as {" or ".join(allowed)}, or start it first',
                              untrusted='unclaimed_execution', state=entry['state'],
                              settleable=list(allowed))
            raise blocked(f'Authorization {identifier} claimed its execution, so '
                          f'"{outcome}" is a determination about work that may already '
                          'have run. Reconcile it against attributable evidence instead',
                          untrusted='undetermined_execution', state=entry['state'],
                          settleable=list(allowed))
        entry['state'] = 'settled'
        entry['outcome'] = outcome
        entry['settled_at'] = now_iso()
        if evidence is not None:
            entry.setdefault('provenance', {})['settlement_evidence'] = evidence
        write_json(root / LEDGER, ledger)
        return {'status': 'settled', 'reason': 'Attempt settled; its charge stands',
                'authorization_id': identifier, 'outcome': outcome,
                'charged': entry['charged'], 'refunded': False}


def reconcile(root: Path, authorization_id: str, determination: str, evidence: Any) -> dict:
    """Resolve a grant that never reached an outcome, from evidence about THIS attempt.

    A matching digest proves only that a file is the file it claims to be. It does not
    say the file is about this authorization, and it does not say which determination it
    supports. So the evidence has to point at a record, that record has to be
    attributable to this attempt, and it has to actually show what is being claimed.

    The two determinations need opposite proofs. `executed` is shown by a record of the
    attempt running. `not_executed` is an absence, and an absence is only meaningful
    against a log asserted complete — so it is proved by a complete log in which nothing
    attributable to this attempt appears. Neither determination refunds (ADR 0006).
    """
    identifier = text(authorization_id)
    if not identifier:
        raise invalid('authorization_id is required')
    if determination not in DETERMINATIONS:
        raise invalid(f'determination must be one of {", ".join(DETERMINATIONS)}')
    if not isinstance(evidence, dict):
        raise blocked('Reconciliation requires evidence of whether the authorized '
                      'execution occurred; an uncertain crash stays blocked rather than '
                      'replaying or refunding it', untrusted='unverifiable_evidence',
                      authorization_id=identifier)
    target, source_digest = verify_source(root, evidence)
    basis = text(evidence.get('basis'))
    if not basis:
        raise blocked('Evidence must state the basis on which it determines whether the '
                      'execution occurred', untrusted='unverifiable_evidence',
                      authorization_id=identifier)
    document = load_source(target)
    with ledger_lock(root):
        ledger = read_ledger(root)
        entry = find(ledger, identifier)
        if entry is None:
            raise blocked(f'No authorization {identifier} to reconcile',
                          untrusted='unknown_authorization')
        if entry['state'] == 'settled':
            return {'status': 'ok', 'reason': 'Authorization was already settled',
                    'authorization_id': identifier, 'outcome': entry.get('outcome'),
                    'charged': entry['charged'], 'refunded': False, 'replayed': True}
        if determination == 'executed':
            # The other unresolved attempts of this same repair node. A record that names
            # no authorization cannot tell this attempt apart from any of them.
            rivals = [other['authorization_id'] for other in ledger['authorizations']
                      if other['state'] in UNRESOLVED
                      and other['repair_node_id'] == entry['repair_node_id']
                      and other['authorization_id'] != identifier]
            attribution = prove_execution(document, evidence, identifier, entry, rivals)
        else:
            attribution = prove_absence(document, evidence, identifier, entry,
                                        ledger['origin'].get('proof') or {})
        entry['state'] = 'settled'
        entry['outcome'] = 'unknown' if determination == 'executed' else 'aborted'
        entry['settled_at'] = now_iso()
        entry.setdefault('provenance', {})['reconciliation'] = {
            'determination': determination, 'basis': basis,
            'source_path': evidence['source_path'], 'source_digest': source_digest,
            'attribution': attribution, 'at': now_iso()}
        write_json(root / LEDGER, ledger)
        return {'status': 'ok',
                'reason': 'Authorization reconciled from evidence attributable to this '
                          'attempt; its charge stands either way — no attempt is refunded',
                'authorization_id': identifier, 'determination': determination,
                'outcome': entry['outcome'], 'charged': entry['charged'],
                'attribution': attribution, 'refunded': False}


def prove_execution(document: dict, evidence: dict, identifier: str, entry: dict,
                    rivals: list[str]) -> dict:
    """A record showing this attempt ran, or a refusal naming what is missing.

    A record that names no authorization is evidence about a *node*, and a node may hold
    several unresolved attempts at once — a shared repair serving two obligations is the
    ordinary case, not an abuse. So such a record is admitted only when this attempt is
    the node's sole unresolved one; otherwise it fits every rival equally and picks out
    none of them. It must also be datable and not older than the execution claim: an
    undated record is not evidence that this attempt ran, because it is not evidence that
    it happened after the attempt began.
    """
    reference = text(evidence.get('observation_ref'))
    if not reference:
        raise blocked('An "executed" determination must name an observation_ref: the '
                      'record of the verified source that shows this attempt running. A '
                      'file digest alone attributes nothing',
                      untrusted='unattributable_evidence', authorization_id=identifier)
    observed = resolve_ref(document, reference)
    if observed is None:
        raise blocked(f'observation_ref {reference} does not resolve to a record of the '
                      'verified source', untrusted='unattributable_evidence',
                      authorization_id=identifier)
    if not attributes_to(observed, identifier, entry['repair_node_id']):
        raise blocked(f'observation_ref {reference} is not about authorization '
                      f'{identifier} or its repair node {entry["repair_node_id"]}; it '
                      'evidences some other work',
                      untrusted='unattributable_evidence', authorization_id=identifier,
                      observed={'node': observed.get('node') or observed.get('node_id'),
                                'authorization_id': observed.get('authorization_id')})
    if not names_authorization(observed) and rivals:
        raise blocked(f'observation_ref {reference} names only repair node '
                      f'{entry["repair_node_id"]}, which also has the unresolved attempts '
                      f'{", ".join(sorted(rivals))}. A record that fits several attempts '
                      'identifies none of them: cite a record naming this authorization, '
                      'or reconcile the others first',
                      untrusted='unattributable_evidence', authorization_id=identifier,
                      rivals=sorted(rivals))
    if not record_time(observed):
        raise blocked(f'observation_ref {reference} carries no time, so it cannot be '
                      'placed after the execution claim; an undated record of this node '
                      'may be any of its runs', untrusted='unattributable_evidence',
                      authorization_id=identifier)
    if predates(observed, text(entry.get('started_at'))):
        raise blocked(f'observation_ref {reference} predates the execution claim at '
                      f'{entry.get("started_at")}; it records earlier work, not this '
                      'attempt', untrusted='unattributable_evidence',
                      authorization_id=identifier, observed_at=record_time(observed))
    return {'kind': 'execution_record', 'observation_ref': reference,
            'record': observed}


def prove_absence(document: dict, evidence: dict, identifier: str, entry: dict,
                  proof: dict) -> dict:
    """A complete log with nothing of this attempt in it, or a refusal.

    Absence is only evidence under two conditions, and both have to be checked because
    each alone is trivially satisfiable. The log must be one the caller vouches for as
    whole — otherwise it may simply be missing the record that proves the attempt ran.
    And it must be *this run's own* execution record: any unrelated document contains no
    trace of this attempt, so without this the emptiest irrelevant file would "prove"
    that nothing happened.
    """
    bound = text(proof.get('source_path'))
    if bound and text(evidence.get('source_path')) != bound:
        raise blocked(f'Absence must be proved against this run\'s own execution record '
                      f'({bound}), not {evidence.get("source_path")}. Another document '
                      'holds no trace of this attempt whether or not it ran',
                      untrusted='unattributable_evidence', authorization_id=identifier,
                      expected_source=bound)
    field = text(evidence.get('absence_of'))
    if not field or evidence.get('complete') is not True:
        raise blocked('A "not_executed" determination must name absence_of — the log '
                      'field it is absent from — and assert that log complete. An '
                      'absence from an incomplete record proves nothing',
                      untrusted='unverifiable_evidence', authorization_id=identifier)
    if field != EXECUTION_LOG:
        # Binding the document is not enough: the caller still chooses which list inside
        # it is read. Any other list is a list of something else, and one whose records
        # cannot name a node — `repair_routes` keys its entries by `repair_node_id` — is
        # "absent" of every attempt that ever ran. Absence is measured against the log
        # that records execution, or it is not measured at all.
        raise blocked(f'absence_of names {field}, not the run\'s execution log '
                      f'({EXECUTION_LOG}). Another list holds no record of this attempt '
                      'whether or not it ran, so its emptiness proves nothing',
                      untrusted='unverifiable_evidence', authorization_id=identifier,
                      expected_absence_of=EXECUTION_LOG)
    values = document.get(field)
    if not isinstance(values, list):
        raise blocked(f'absence_of names {field}, which is not a log in the verified '
                      'source', untrusted='unverifiable_evidence',
                      authorization_id=identifier)
    claimed_at = text(entry.get('started_at'))
    contradicting = [index for index, record in enumerate(values)
                     if isinstance(record, dict)
                     and attributes_to(record, identifier, entry['repair_node_id'])
                     and not predates(record, claimed_at)]
    if contradicting:
        raise blocked(f'{field} records work for this attempt at '
                      f'{contradicting}; the evidence contradicts a "not_executed" '
                      'determination rather than supporting it',
                      untrusted='unattributable_evidence', authorization_id=identifier,
                      contradicting=contradicting)
    return {'kind': 'complete_log_absence', 'absence_of': field,
            'records_examined': len(values), 'since': claimed_at or None}


def consumption(root: Path, repair_node_id: str | None = None) -> dict:
    """What each obligation has spent, and what is still unresolved.

    Reported per obligation because the budget is per obligation: a shared repair task
    tells you nothing about whether a particular QA obligation may be repaired again.
    An unresolved grant elsewhere is reported, not refused — reading the ledger while
    another independent repair is in flight is a normal thing to do.
    """
    ledger = read_ledger(root)
    wanted = text(repair_node_id) if repair_node_id else None
    obligations: dict[str, dict] = {}
    for entry in ledger['authorizations']:
        if wanted and entry['repair_node_id'] != wanted:
            continue
        for obligation in entry['obligations']:
            key = f'{entry["repair_node_id"]}::{obligation}'
            record = obligations.setdefault(key, {
                'repair_node_id': entry['repair_node_id'], 'qa_node_id': obligation,
                'spent': 0, 'budget': None, 'unresolved': []})
            record['spent'] += 1
            bound = budget_of(entry, obligation)
            if bound is not None:
                record['budget'] = bound
            if entry['state'] in UNRESOLVED:
                record['unresolved'].append(entry['authorization_id'])
    for record in obligations.values():
        record['remaining'] = (None if record['budget'] is None
                               else record['budget'] - record['spent'])
        record['exhausted'] = (record['remaining'] is not None and record['remaining'] <= 0)
    return {'status': 'ok', 'reason': 'Consumption read from the authoritative ledger',
            'run_id': ledger['run_id'], 'origin': ledger['origin']['kind'],
            'binding': ledger['origin'].get('binding'),
            'obligations': [obligations[key] for key in sorted(obligations)],
            'unresolved': [{'authorization_id': entry['authorization_id'],
                            'state': entry['state'],
                            'repair_node_id': entry['repair_node_id'],
                            'obligations': entry['obligations']}
                           for entry in ledger['authorizations']
                           if entry['state'] in UNRESOLVED
                           and not (wanted and entry['repair_node_id'] != wanted)]}


OPERATIONS = ('initialize', 'adopt_history', 'authorize', 'start', 'settle',
              'reconcile', 'consumption')


def session(root: Path, request: Any) -> dict:
    """One request, one verdict. The CLI and the Python API decide identically."""
    if not isinstance(request, dict):
        raise invalid('request must be an object')
    operation = text(request.get('operation'))
    if operation == 'initialize':
        return initialize(root, request.get('run_id'))
    if operation == 'adopt_history':
        return adopt_history(root, request.get('run_id'), request.get('evidence'))
    if operation == 'authorize':
        return authorize(root, request)
    if operation == 'start':
        return start(root, request.get('run_id'), request.get('authorization_id'))
    if operation == 'settle':
        return settle(root, request.get('authorization_id'), request.get('outcome'),
                      request.get('evidence'))
    if operation == 'reconcile':
        return reconcile(root, request.get('authorization_id'), request.get('determination'),
                         request.get('evidence'))
    if operation == 'consumption':
        return consumption(root, request.get('repair_node_id'))
    raise invalid(f'Unknown operation {operation!r}; expected one of {", ".join(OPERATIONS)}')


def main() -> int:
    try:
        # The project root defaults to the working directory: the engine's prompt ends the
        # command with a bare `.`, and an agent that reads it as punctuation must still
        # reach this project's ledger rather than fail before reading any accounting.
        root = Path(sys.argv[1] if len(sys.argv) > 1 else '.').resolve()
        result = session(root, json.load(sys.stdin))
    except Refusal as refusal:
        result = refusal.verdict
    except (ValueError, KeyError, TypeError, OSError, IndexError) as exc:
        result = {'status': 'invalid', 'reason': str(exc)}
    print(json.dumps(result, sort_keys=True))
    return 1 if result.get('status') in REFUSED else 0


if __name__ == '__main__':
    raise SystemExit(main())
