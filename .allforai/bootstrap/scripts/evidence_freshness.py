#!/usr/bin/env python3
"""Content-bound observations and publication at bootstrap/resume boundaries."""
from __future__ import annotations

import hashlib
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
import json
import os
import subprocess
from pathlib import Path
import sys
import tempfile
import time
from typing import Any

WORKFLOW = '.allforai/bootstrap/workflow.json'
STATE = '.allforai/bootstrap/evidence-freshness.json'
OBSERVATIONS = '.allforai/bootstrap/input-observations'
READS = '.allforai/bootstrap/observed-input-dependencies.json'
EXTERNAL = '.allforai/bootstrap/external-changes.json'
# The run's own bookkeeping. It changes on every committed transition, so a node that
# registered it as a dependency would find its evidence stale after each commit the
# engine records — including its own — and every consumer would wait on it forever.
ORCHESTRATION_STATE = frozenset({
    WORKFLOW, STATE, READS, EXTERNAL,
    '.allforai/bootstrap/run-log.jsonl',
    '.allforai/bootstrap/repair-authorizations.json',
    '.allforai/bootstrap/run-policy.json',
    '.allforai/bootstrap/run-summary.json',
    '.allforai/bootstrap/unattended-run-readiness.json',
    '.allforai/bootstrap/workflow-state-index.json',
    '.allforai/bootstrap/workflow-reconciliation-plan.json',
})
ORCHESTRATION_STATE_DIRS = (OBSERVATIONS + '/',)


def orchestration_state(path):
    """True for the run's own bookkeeping, which is never a product input."""
    normalized = Path(path).as_posix()
    return normalized in ORCHESTRATION_STATE or normalized.startswith(ORCHESTRATION_STATE_DIRS)


# Caches exist only inside one read-only gate. Never reuse them across observe,
# publish, a verification subprocess, or a later gate in the same interpreter.
_READ_EVALUATION = ContextVar('freshness_read_evaluation', default=None)


def _file_version(path):
    try:
        stat = path.stat()
        return (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
    except FileNotFoundError:
        return None


class _ReadEvaluation:
    def __init__(self, root):
        self.root = root.resolve()
        self.files = {}
        self.memo = {}
        self.expansions = {}
        self.tree = None
        # Resolved before the gate opens: asking Git what the project ignores is a
        # subprocess, and nothing may execute inside a read-only evaluation.
        self.paths = None

    def content(self, path):
        # Keep the unresolved path too: replacing a symlink must invalidate reads.
        key = str(path.absolute())
        if key not in self.files:
            before = _file_version(path)
            content = path.read_bytes() if path.is_file() else None
            after = _file_version(path)
            if before != after:
                raise ValueError('Inputs changed during freshness evaluation: ' + key)
            self.files[key] = (after, content)
        return self.files[key][1]

    def verify(self):
        # Recheck bytes as well as metadata, including previously missing files.
        # This is a boundary check, not a long-lived stat-only freshness cache.
        for key, (version, content) in self.files.items():
            path = Path(key)
            before = _file_version(path)
            current = path.read_bytes() if path.is_file() else None
            if before != version or _file_version(path) != before or current != content:
                raise ValueError('Inputs changed during freshness evaluation: ' + key)
        for paths, previous in self.expansions.items():
            if expand_paths(self.root, list(paths)) != previous:
                raise ValueError('Input membership changed during freshness evaluation')
        if self.tree is not None and source_tree(self.root) != self.tree:
            raise ValueError('Source tree changed during freshness evaluation')
        for key, (version, _) in self.files.items():
            if _file_version(Path(key)) != version:
                raise ValueError('Inputs changed during freshness evaluation: ' + key)


def _read_only_gate(function):
    @wraps(function)
    def wrapped(root, *args, **kwargs):
        active = _READ_EVALUATION.get()
        if active is not None:
            if active.root != root.resolve():
                raise ValueError('Freshness evaluation cannot cross project roots')
            return function(root, *args, **kwargs)
        context = _ReadEvaluation(root)
        context.paths = _ignore_aware_paths(root)
        token = _READ_EVALUATION.set(context)
        try:
            result = function(root, *args, **kwargs)
        finally:
            _READ_EVALUATION.reset(token)
        context.verify()  # No verdict escapes if inputs moved during the gate.
        return result
    return wrapped


def _memoized(key, compute):
    context = _READ_EVALUATION.get()
    if context is None:
        return compute()
    if key not in context.memo:
        context.memo[key] = compute()
    return context.memo[key]


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def read_json(root, path, default=None):
    target = root / path
    context = _READ_EVALUATION.get()
    if context is None:
        return json.loads(target.read_text()) if target.exists() else default
    if target.is_dir():
        raise IsADirectoryError(str(target))
    content = context.content(target)
    return (_memoized(('json', str(target.absolute())), lambda: json.loads(content))
            if content is not None else default)


def write_json(root, path, value):
    if _READ_EVALUATION.get() is not None:
        raise ValueError('Cannot publish inside a read-only freshness evaluation')
    target = root / path
    target.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(value, sort_keys=True, indent=2) + '\n'
    if not target.exists() or target.read_text() != content:
        with tempfile.NamedTemporaryFile(mode='w', dir=target.parent, delete=False) as stream:
            stream.write(content)
            temporary = Path(stream.name)
        try:
            temporary.replace(target)
        finally:
            temporary.unlink(missing_ok=True)


@contextmanager
def publication_lock(root):
    lock = root / '.allforai/bootstrap/freshness-publication.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    for _ in range(300):
        try:
            lock.mkdir()
            break
        except FileExistsError:
            time.sleep(.01)
    else:
        raise ValueError('Freshness publication is locked; retry or coordinate an abandoned writer')
    try:
        yield
    finally:
        lock.rmdir()


def fingerprint(root, path):
    target = (root / path).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError('Input must be inside project: ' + path)
    context = _READ_EVALUATION.get()
    if context is None:
        return hashlib.sha256(target.read_bytes()).hexdigest() if target.is_file() else None
    def calculate():
        content = context.content(root / path)
        return hashlib.sha256(content).hexdigest() if content is not None else None
    return _memoized(('fingerprint', str((root / path).absolute())), calculate)


def expand_paths(root, paths, *, track=True):
    if not isinstance(paths, list) or not all(isinstance(p, str) and p for p in paths):
        raise ValueError('Input dependencies must be a list of project paths or globs')
    expanded: set[str] = set()
    for path in paths:
        if Path(path).is_absolute() or '..' in Path(path).parts:
            raise ValueError('Input must be a relative project path: ' + path)
        if any(c in path for c in '*?['):
            matches = [p for p in root.glob(path) if p.is_file()]
            expanded.update(p.relative_to(root).as_posix() for p in matches)
        elif (root / path).is_dir():
            expanded.update(p.relative_to(root).as_posix() for p in (root / path).rglob('*') if p.is_file())
        else:
            expanded.add(path)
    context = _READ_EVALUATION.get()
    if context is not None and track:
        key = tuple(paths)
        previous = context.expansions.setdefault(key, expanded)
        if previous != expanded:
            raise ValueError('Input membership changed during freshness evaluation')
    return expanded


def observed_reads(root):
    """The dynamic-read register: {node_id: [project paths]} recorded by ``read``.

    A malformed register is refused, never treated as empty: dropping a recorded
    read would let evidence claim provenance it no longer tracks. The file is
    left in place for repair.
    """
    prefix = 'Malformed observed-input dependencies (' + READS + '): '
    try:
        reads = read_json(root, READS, {})
    except ValueError as exc:
        raise ValueError(prefix + 'not valid JSON; restore recorded dependencies before retrying: ' + str(exc)) from None
    if not isinstance(reads, dict):
        raise ValueError(prefix + 'top level must be an object keyed by node_id; restore recorded dependencies before retrying')
    for node_id, paths in reads.items():
        if not isinstance(node_id, str) or not node_id:
            raise ValueError(prefix + 'node ids must be non-empty strings; restore recorded dependencies before retrying')
        if not isinstance(paths, list) or not all(isinstance(p, str) and p for p in paths):
            raise ValueError(prefix + 'entry for ' + node_id + ' must be a list of project paths; '
                             'restore recorded dependencies before retrying')
        for path in paths:
            if Path(path).is_absolute() or '..' in Path(path).parts:
                raise ValueError(prefix + 'entry for ' + node_id + ' must use relative project paths, not ' + path
                                 + '; restore recorded dependencies before retrying')
    return reads


def intent_baseline(root):
    profile = read_json(root, '.allforai/bootstrap/bootstrap-profile.json', {})
    if profile.get('intent_session_path') == '.allforai/bootstrap/local-requirements.json':
        return profile.get('intent_scope', {})
    return read_json(root, '.allforai/product-concept/concept-baseline.json', {}).get('intent_baseline', {})


@_read_only_gate
def snapshot(root, node, extra=(), seen=()):
    if node['node_id'] in seen:
        raise ValueError('Cyclic input dependency; impact is uncertain')
    return _memoized(('snapshot', digest(node), tuple(sorted(set(extra)))),
                     lambda: _snapshot(root, node, extra, seen))


def _snapshot(root, node, extra=(), seen=()):
    if node['node_id'] in seen:
        raise ValueError('Cyclic input dependency; impact is uncertain')
    extra = set(extra) | set(observed_reads(root).get(node['node_id'], []))
    workflow = read_json(root, WORKFLOW, {})
    source_files = expand_paths(root, node.get('source_inputs', []), track=False)
    product_files = inventory(root, workflow)
    source_files = {p for p in source_files if p in product_files or not (root / p).exists()}
    # Invalidation follows the graph. What the flow delivers further down is an output
    # of the plan, not an input to the work that planned it: binding a design to the
    # implementation it governs would let that delivery stale the frozen design it was
    # built from, leaving neither able to publish.
    source_files -= downstream_write_scope(root, node['node_id'], workflow)
    paths = source_files | expand_paths(root, node.get('input_dependencies', [])) | extra
    refs = node.get('requirement_refs', [])
    ref_paths = {ref['path'] for ref in refs}
    # A shared concept document can carry unrelated decisions. Bind selected items.
    paths.update(p for p in node.get('decision_inputs', []) if isinstance(p, str) and p not in ref_paths
                 and p != '.allforai/product-concept/concept-baseline.json')
    inputs = {path: fingerprint(root, path) for path in sorted(paths)}
    requirements = {}
    for ref in refs:
        data = read_json(root, ref['path'], {})
        items = [item for item in data.get('requirements', []) if item.get('id') == ref['id']]
        requirements[ref['path'] + '#' + ref['id']] = digest(items)
    baseline = intent_baseline(root)
    selected = {ref['id'] for ref in refs}
    baseline_scope = {'requirement_refs': [ref for ref in baseline.get('requirement_refs', []) if ref['id'] in selected],
                      'intents': [item for item in baseline.get('intents', []) if item['id'] in selected],
                      'excluded': {k: v for k, v in baseline.get('excluded', {}).items() if k in selected}}
    by_id = {n['node_id']: n for n in workflow.get('nodes', [])}
    state = read_json(root, STATE, {'nodes': {}})
    upstream = {}
    for dep in dependencies(root, node, workflow):
        if dep not in by_id:
            raise ValueError('Missing dependency ' + dep + '; impact is uncertain')
        upstream[dep] = snapshot(root, by_id[dep], state['nodes'].get(dep, {}).get('extra', []),
                                 (*seen, node['node_id']))
    return {'files': inputs, 'requirements': requirements, 'contract': digest(node),
            'baseline_scope': baseline_scope, 'upstream': upstream}


def dependencies(root, node, workflow):
    return _memoized(('dependencies', digest(node)), lambda: _dependencies(root, node, workflow))


def _dependencies(root, node, workflow):
    producers = {item['path'] if isinstance(item, dict) else item: n['node_id']
                 for n in workflow.get('nodes', [])
                 for item in [*n.get('exit_artifacts', []), *n.get('required_documents', [])]}
    state = read_json(root, STATE, {'nodes': {}})
    # A copy: the expansion is memoized for the evaluation, and extending it in place
    # would make the next expansion of the same inputs look like changed membership.
    consumed = set(expand_paths(root, node.get('input_dependencies', [])))
    consumed.update(observed_reads(root).get(node['node_id'], []))
    for bucket in ('nodes', 'contracts'):
        consumed.update(state.get(bucket, {}).get(node['node_id'], {}).get('extra', []))
    return sorted(set(node.get('hard_blocked_by', [])) |
                  {producers[p] for p in consumed if p in producers and producers[p] != node['node_id']})


def evidence_entries(root, node):
    """Ledger-shaped entries a verify gate wrote beside its exit artifacts, and every file they cite.

    A gate's run directory is where its exit artifacts live; its entries file is
    ``<run>/evidence-entries/<node_id>.json`` and each entry's ``evidence.dir`` is a
    directory under that run. Both are the node's outputs: a swapped screenshot or a
    dropped entries file is drift in the delivery, not a still-valid verification.
    An entries file that cannot be parsed is still bound by its fingerprint.
    """
    paths: list[str] = []
    runs = sorted({Path(item['path'] if isinstance(item, dict) else item).parent.as_posix()
                   for item in node.get('exit_artifacts', [])})
    for run in runs:
        entries = run + '/evidence-entries/' + node['node_id'] + '.json'
        if not (root / entries).is_file():
            continue
        paths.append(entries)
        try:
            data = read_json(root, entries, {})
        except ValueError:
            continue
        for entry in data.get('entries', []) if isinstance(data, dict) and isinstance(data.get('entries'), list) else []:
            evidence = entry.get('evidence') if isinstance(entry, dict) else None
            directory = evidence.get('dir') if isinstance(evidence, dict) else None
            if not isinstance(directory, str) or not directory or Path(directory).is_absolute():
                continue
            target = (root / run / directory).resolve()
            if not target.is_relative_to(root.resolve()) or not target.is_dir():
                continue
            paths.extend(p.relative_to(root.resolve()).as_posix() for p in sorted(target.rglob('*')) if p.is_file())
    return paths


def outputs(root, node, kind='evidence'):
    """Outputs a publication binds: the Node-spec for a contract; the required
    fact documents, Node-spec, exit artifacts and ledger-shaped evidence entries
    for delivered evidence."""
    paths = []
    spec = '.allforai/bootstrap/node-specs/' + node['node_id'] + '.md'
    if kind == 'evidence':
        paths.extend(node.get('required_documents', []))
    if (root / spec).exists() or kind == 'contract':
        paths.append(spec)
    if kind == 'evidence':
        paths.extend(item['path'] if isinstance(item, dict) else item for item in node.get('exit_artifacts', []))
        paths.extend(p for p in evidence_entries(root, node) if p not in paths)
    return {p: fingerprint(root, p) for p in paths}


def input_diff(recorded, current):
    """Explicit differences between a recorded input snapshot and the current one."""
    diff: dict[str, Any] = {}
    files = {}
    for path in sorted(set(recorded.get('files', {})) | set(current.get('files', {}))):
        if recorded.get('files', {}).get(path) != current.get('files', {}).get(path):
            files[path] = ('added' if path not in recorded.get('files', {}) else
                           'removed' if path not in current.get('files', {}) else 'changed')
    if files:
        diff['files'] = files
    requirements = sorted(key for key in set(recorded.get('requirements', {})) | set(current.get('requirements', {}))
                          if recorded.get('requirements', {}).get(key) != current.get('requirements', {}).get(key))
    if requirements:
        diff['requirements'] = requirements
    if recorded.get('baseline_scope') != current.get('baseline_scope'):
        diff['baseline_scope'] = 'changed'
    if recorded.get('contract') != current.get('contract'):
        diff['contract'] = 'changed'
    upstream = sorted(dep for dep in set(recorded.get('upstream', {})) | set(current.get('upstream', {}))
                      if recorded.get('upstream', {}).get(dep) != current.get('upstream', {}).get(dep))
    if upstream:
        diff['upstream'] = upstream
    return diff


def output_diff(recorded, current):
    """Missing or changed published outputs, keyed by path."""
    diff = {}
    for path in sorted(set(recorded) | set(current)):
        if current.get(path) is None:
            diff[path] = 'missing'
        elif recorded.get(path) != current.get(path):
            diff[path] = 'changed' if path in recorded else 'added'
    return diff


def missing_outputs(current):
    return {path: 'missing' for path, value in current.items() if value is None}


def document_checks(node):
    """Declared project-specific verification argv per required document.

    A document is synchronized only when its stated facts are executed against
    the current source; a fingerprint, timestamp or report refresh proves nothing.
    """
    declared = node.get('document_verification')
    checks = {}
    for path in node.get('required_documents', []):
        argv = declared.get(path) if isinstance(declared, dict) else None
        if isinstance(argv, list) and argv and all(isinstance(s, str) and s for s in argv):
            checks[path] = argv
    return checks


def project_file_identity(root, token):
    """The project-relative identity of an argv token naming an existing project
    file (relative, ./relative or absolute inside the project), else None.
    Files outside the project are not read or resolved further."""
    if not isinstance(token, str) or not token:
        return None
    candidate = Path(token) if Path(token).is_absolute() else root / token
    try:
        if not candidate.is_file():
            return None
        resolved = candidate.resolve()
    except OSError:
        return None
    if not resolved.is_relative_to(root.resolve()):
        return None
    return resolved.relative_to(root.resolve()).as_posix()


def unverified_documents(node, record):
    """Required documents whose declared check did not verify this record."""
    checks = document_checks(node)
    verified = ((record or {}).get('verification') or {}).get('documents', {})
    return {path: 'unverified' for path in node.get('required_documents', [])
            if path not in checks or (record is not None and verified.get(path, {}).get('command') != checks[path])}


def scope_blockers(root, workflow):
    """The shared scope contract's blockers, keyed by consuming node (None = global)."""
    try:
        from product_intent import validate_scope
    except ImportError:
        return {}
    grouped: dict[str | None, set[str]] = {}
    for blocker in validate_scope(root, workflow):
        grouped.setdefault(blocker.get('node_id'), set()).add(blocker.get('code'))
    return grouped


@_read_only_gate
def routed_external_changes(root):
    """Detected external changes grouped by the delivery they reach.

    The boundary comparison belongs to the gates themselves, so drift reaches its
    repair owner without an earlier explicit ``external-changes`` invocation. The
    comparison is an observation: it reads the recorded verdicts and never executes
    the project's acceptance, because running project argv against live source is an
    act a gate has no mandate for. Two groups come back — changes a standing
    verification classified as needing a decision, and changes no current
    verification covers, which are unknown rather than harmless.

    A comparison that cannot be completed is not an absence of conflict. It raises,
    so every gate fails closed on the undeterminable state, rather than returning an
    empty result that silently hands affected work back to its node.
    """
    detected, _ = standing_changes(root)
    conflicts: dict[str, list[dict[str, Any]]] = {}
    unverified: dict[str, list[dict[str, Any]]] = {}
    for change in detected:
        # A change the user has already decided is routed by that decision, whatever a
        # verdict currently says: an accepted one stops holding work, a rejected one keeps
        # its scoped repair, a deferred one keeps its hold. Only a change nobody decided
        # and no verification covers is unknown.
        group = (conflicts if change['resolution'] or change['classification'] in ('product-conflict', 'uncertain')
                 else unverified if change['classification'] is None else None)
        if group is None:
            continue
        # An unmapped change belongs to every delivery whose provenance it touches.
        for target in ([change['node_id']] if change['node_id'] else change['impact']['tasks']):
            group.setdefault(target, []).append(change)
    return conflicts, unverified


def external_conflicts(root):
    """Currently detected external changes a standing verification says need a decision."""
    return routed_external_changes(root)[0]


def undecided_conflicts(external, node_id):
    """Conflicts on a node that no recorded user decision has settled yet."""
    return [c for c in external.get(node_id, [])
            if (c['resolution'] or {}).get('resolution') not in ('accept', 'reject')]


def rejected_conflicts(external, node_id):
    """Conflicts the user rejected, whose scoped implementation repair is outstanding."""
    return [c for c in external.get(node_id, []) if (c['resolution'] or {}).get('resolution') == 'reject']


def repair_responsibility(root, node, diff, blockers=None, external=None):
    """Who repairs an inconsistency and which responsibility drifted.

    An unresolved or unreplanned product decision belongs to interactive
    bootstrap; stale producers repair before their consumers; everything else
    returns to the node that owns the delivery. A diff never authorizes a
    product choice, and a Run Policy never resolves one.
    """
    if blockers is None:
        blockers = scope_blockers(root, read_json(root, WORKFLOW, {}))
    codes = blockers.get(None, set()) | blockers.get(node['node_id'], set())
    if codes & {'pending_requirement', 'pending_product_confirmation', 'pending_decision'}:
        return {'owner': 'interactive-bootstrap', 'responsibilities': ['product-decision']}
    if 'stale_requirement' in codes:
        return {'owner': 'interactive-bootstrap', 'responsibilities': ['replan']}
    if external is None:
        external = external_conflicts(root)
    if undecided_conflicts(external, node['node_id']):
        return {'owner': 'interactive-bootstrap', 'responsibilities': ['product-decision']}
    own = {k: v for k, v in diff.items() if k != 'upstream'}
    if not own and diff.get('upstream'):
        return {'owner': diff['upstream'][0], 'responsibilities': ['upstream']}
    responsibilities = []
    spec = '.allforai/bootstrap/node-specs/' + node['node_id'] + '.md'
    documents = set(node.get('required_documents', []))
    changed_outputs = diff.get('outputs', {})
    if 'requirements' in diff or 'baseline_scope' in diff:
        responsibilities.append('requirement-sync')
    if 'contract' in diff or spec in changed_outputs:
        responsibilities.append('contract')
    if 'files' in diff:
        responsibilities.append('implementation')
    if any(path in documents for path in changed_outputs) or diff.get('documents'):
        responsibilities.append('documentation')
    if (any(path not in documents and path != spec for path in changed_outputs) or diff.get('evidence') == 'unpublished'
            or diff.get('documents')):
        responsibilities.append('verification')
    return {'owner': node['node_id'], 'responsibilities': responsibilities}


def consumers(root, node_id, workflow):
    """Every node whose work transitively depends on ``node_id``."""
    edges = {n['node_id']: set(dependencies(root, n, workflow)) for n in workflow.get('nodes', [])}
    reached, frontier = set(), {node_id}
    while frontier:
        current = frontier.pop()
        for consumer, deps in edges.items():
            if current in deps and consumer not in reached:
                reached.add(consumer)
                frontier.add(consumer)
    return reached


def downstream_write_scope(root, node_id, workflow):
    """Paths a transitive consumer of ``node_id`` declares that it writes.

    Only a declared ``parallel_write_scopes`` exempts, and only on a node that
    depends on this one: a node cannot exempt its own inputs, and an implementation
    that never declares what it writes keeps invalidating its planners — that is the
    missing declaration surfacing, not freshness being bypassed. Changes inside the
    scope still invalidate the node owning it and that node's own consumers.
    """
    return _memoized(('downstream-write-scope', node_id),
                     lambda: _downstream_write_scope(root, node_id, workflow))


def _downstream_write_scope(root, node_id, workflow):
    by_id = {n['node_id']: n for n in workflow.get('nodes', [])}
    scoped: set[str] = set()
    for consumer in consumers(root, node_id, workflow):
        scopes = by_id.get(consumer, {}).get('parallel_write_scopes') or []
        scoped |= expand_paths(root, scopes)
    return scoped


def change_impact(root, node, workflow, files):
    """What a changed source file reaches: facts, product decisions, documents,
    dependent tasks and the acceptance artifacts bound to this delivery."""
    return {'facts': sorted(files),
            'documents': list(node.get('required_documents', [])),
            'product_decisions': [ref['path'] + '#' + ref['id'] for ref in node.get('requirement_refs', [])],
            'tasks': sorted({node['node_id']} | consumers(root, node['node_id'], workflow)),
            'acceptance': [item['path'] if isinstance(item, dict) else item
                           for item in node.get('exit_artifacts', [])]}


def owned_inputs(root, workflow, state):
    """Every path some node declares, observed or recorded as a consumed input."""
    owned = {p for n in workflow.get('nodes', [])
             for field in ('source_inputs', 'input_dependencies')
             for p in expand_paths(root, n.get(field, []), track=field != 'source_inputs')}
    owned.update(p for record in state['nodes'].values() for p in record.get('extra', []))
    owned.update(p for record in state['nodes'].values() for p in record.get('inputs', {}).get('files', {}))
    owned.update(p for paths in observed_reads(root).values() for p in paths)
    return owned


def reclassified(root, path, current):
    """A recorded path the inventory no longer carries although the file is still there.

    What counts as product source is the project's own statement, and that statement
    can change — an ignore rule added, or a build tree the inventory now recognises as
    generated. A file that left the inventory without leaving the disk was reclassified,
    not edited, so it is not a product change waiting for anyone's decision. A recorded
    path that is gone from disk as well is an ordinary removal and still reported.
    """
    return path not in current and (root / path).is_file()


def unmapped_changes(root, workflow, state):
    """Source that changed outside every declared input, and the nodes it reaches.

    Nothing maps this content to a delivery, so its impact is undetermined: it is
    reported as uncertain rather than assumed harmless or treated as a rebuild.
    """
    current = inventory(root, workflow)
    owned = owned_inputs(root, workflow, state)
    files: dict[str, str] = {}
    tasks = set()
    for node_id, record in state['nodes'].items():
        previous = record.get('source_snapshot', {})
        unknown = {p for p in set(previous) | set(current)
                   if source_path_included(p) and not reclassified(root, p, current)
                   and previous.get(p) != current.get(p)} - owned
        if not unknown:
            continue
        tasks.add(node_id)
        for path in unknown:
            files[path] = ('added' if path not in previous else
                           'removed' if path not in current else 'changed')
    return files, sorted(tasks)


def change_identity(node_id, fingerprints):
    """A change is the delivery plus the current content of the changed files.

    A later edit is different content and therefore a different change, so an
    earlier decision cannot travel to it. The identity deliberately excludes the
    confirmed baseline version: the decision was about this source, so advancing
    the version for unrelated work must not orphan it. Whether a recorded
    decision still applies to the current confirmed intent is
    ``carried_resolution``'s question, not an identity question.
    """
    return digest({'node_id': node_id, 'files': fingerprints})


def carried_resolution(entry, binding):
    """The recorded resolution that still applies to this change, and the history.

    A user decides an external change against the confirmed intent of that moment.
    Unchanged intent carries the decision forward across baseline versions and
    unrelated freezes. When the user revises the very requirements the decision was
    made against, the old resolution becomes history rather than standing consent
    for a semantically different question, and the change is presented again.
    """
    history = [item for item in entry.get('superseded_resolutions', []) if isinstance(item, dict)]
    resolution = entry.get('resolution') if isinstance(entry.get('resolution'), dict) else None
    if resolution is not None and resolution.get('requirement_binding') != binding:
        return None, [*history, resolution]
    return resolution, history


def detect_external_changes(root):
    """Source changed since a node published its evidence, keyed by content.

    This is a boundary comparison, not a watcher: it reads the recorded
    observation and the current source, and never runs or decides anything.
    Each change carries the confirmed baseline version and the node's selected
    requirement content as provenance for the decision recorded against it.
    """
    workflow = read_json(root, WORKFLOW, {})
    state = read_json(root, STATE, {'nodes': {}})
    # An unreadable record cannot establish what changed outside the flow; the
    # comparison fails closed instead of reporting an empty, reassuring result.
    if (not isinstance(state, dict) or not isinstance(state.get('nodes'), dict)
            or not all(isinstance(v, dict) for v in state['nodes'].values())):
        raise ValueError('Freshness state is unreadable; external source changes cannot be determined')
    baseline = intent_baseline(root).get('version')
    detected = []
    for node in workflow.get('nodes', []):
        record = state['nodes'].get(node['node_id'])
        if not record:
            continue
        current = snapshot(root, node, record.get('extra', []))
        files = input_diff(record['inputs'], current).get('files', {})
        if not files:
            continue
        detected.append({'change_id': change_identity(node['node_id'],
                                                      {p: fingerprint(root, p) for p in sorted(files)}),
                         'node_id': node['node_id'], 'files': files, 'baseline_version': baseline,
                         'requirement_binding': current['requirements'],
                         'impact': change_impact(root, node, workflow, files)})
    unmapped, tasks = unmapped_changes(root, workflow, state)
    if unmapped:
        # Source no node declares carries no confirmed requirement of its own.
        detected.append({'change_id': change_identity(None, {p: fingerprint(root, p) for p in sorted(unmapped)}),
                         'node_id': None, 'files': unmapped, 'baseline_version': baseline,
                         'requirement_binding': {},
                         'impact': {'facts': sorted(unmapped), 'documents': [], 'product_decisions': [],
                                    'tasks': tasks, 'acceptance': []}})
    return detected


def classify_external_change(root, record):
    """Verify a detected change against the baseline's own recorded acceptance.

    Passing acceptance establishes an implementation-only change whose facts are
    updated in place. A failing one, or a delivery with no rerunnable acceptance,
    is a product conflict: code behavior never becomes the desired behavior here.
    """
    if record is None:
        return 'uncertain', {'reason': 'Changed source is not covered by any declared input; coordinate the '
                                       'input mapping and the affected documents before claiming impact'}
    command = (record.get('verification') or {}).get('command')
    if not isinstance(command, list) or not command or not all(isinstance(s, str) and s for s in command):
        return 'uncertain', {'reason': 'No recorded acceptance command binds this delivery; '
                                       'the semantic impact of the change is undetermined'}
    try:
        verified = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 'uncertain', {'command': command, 'reason': 'Recorded acceptance could not be executed: ' + str(exc)}
    return ('fact-update' if verified.returncode == 0 else 'product-conflict',
            {'command': command, 'returncode': verified.returncode,
             'stdout': verified.stdout, 'stderr': verified.stderr})


def classification_basis(record, source):
    """What a verification was run against, so a stale verdict is not reused.

    A verdict is not a property of the changed file alone: it executes the
    delivery's recorded acceptance, which reads the rest of the source and can be
    republished with a different command. When either moves, the recorded verdict
    answers a question nobody is asking. It deliberately excludes the confirmed
    requirement content, which cannot change what the acceptance does — whether a
    recorded *decision* still applies to revised intent is ``carried_resolution``'s
    question. The basis also stays out of ``change_identity``: a decision is about
    this source, and unrelated source moving must not orphan it.

    The source here is what the flow consumes rather than what it produces. A
    verdict prescribes its own recovery — resynchronize the required documents and
    republish — so counting those documents would let the flow invalidate the verdict
    it is obeying and reopen a settled change as unknown drift.

    What the basis cannot observe — an installed dependency, a service, the
    environment — is why re-running the verification is always a fresh execution.
    """
    return digest({'command': ((record or {}).get('verification') or {}).get('command'), 'source': source})


def cache_classifications(root, changes):
    """Persist derived classifications; report whether the cache was written.

    This store holds two different kinds of content under one file. A
    classification is derived: it is recomputed from the current source whenever
    it is missing, so failing to write it costs a rerun and nothing else. A user's
    resolution is authoritative, and only the interactive decision path writes one
    — never this function, which merely carries forward what the store already
    holds. Persistence failure is therefore reported and not raised: a store the
    project cannot write must not delete a detected conflict from the gates.
    """
    try:
        write_json(root, EXTERNAL, {'schema_version': '1.0', 'changes': changes})
    except OSError:
        return False
    return True


def standing_changes(root):
    """Detected changes, each carrying the verdict that currently stands for it.

    This observes and never acts: it reads the recorded store, keeps an undecided
    verdict only while the basis it was established against still holds, and never
    executes the project's acceptance. A change with no standing verdict carries
    ``classification: None`` — unknown, which the gates route as unverified rather
    than repeating a verdict for a state nobody verified. Recorded user resolutions
    are carried forward regardless: a decision was made about this change identity
    and the intent of that moment, not about the freshness of a classification, and
    it keeps the finding it was made against so the report still says what was found.
    """
    workflow = read_json(root, WORKFLOW, {})
    state = read_json(root, STATE, {'nodes': {}})
    store = read_json(root, EXTERNAL, {}) or {}
    recorded = store.get('changes', {}) if isinstance(store.get('changes'), dict) else {}
    detected = detect_external_changes(root)
    source = digest(inventory(root, workflow))
    for change in detected:
        record = state['nodes'].get(change['node_id']) if change['node_id'] else None
        basis = classification_basis(record, source)
        previous = recorded.get(change['change_id']) or {}
        previous = previous if isinstance(previous, dict) else {}
        verdict = (previous['classification']
                   if previous.get('classification') in ('fact-update', 'product-conflict', 'uncertain') else None)
        resolution, history = carried_resolution(previous, change['requirement_binding'])
        # An undecided verdict stands only while the basis it was established against
        # does. A decided one is different in kind: the user answered this change against
        # that finding, so the finding stays as the decision's context and later movement
        # elsewhere is not new information about it. Reasking would demand a verification
        # nobody needs and put a settled product question back to the user.
        standing = verdict if resolution or previous.get('classification_basis') == basis else None
        change.update(classification=standing, classification_basis=basis, resolution=resolution,
                      verification=previous.get('verification') if standing else None)
        if history:
            change['superseded_resolutions'] = history
    return detected, recorded


def resolve_external_changes(root):
    """Verify detected external changes and record the result.

    This is the one path that executes the delivery's own recorded acceptance,
    because running project argv against live source is an act rather than an
    observation, and only an explicit request carries the mandate for it. It always
    establishes fresh evidence instead of repeating a memo, so re-running it is how
    a user re-verifies when something the comparison cannot observe — an installed
    dependency, a service, the environment — may have moved underneath a verdict.
    Detection never writes to the product journal, and a recorded user resolution is
    carried, never recomputed.
    """
    state = read_json(root, STATE, {'nodes': {}})
    before = digest(source_tree(root))
    detected, recorded = standing_changes(root)
    changes = dict(recorded)
    for change in detected:
        classification, verification = classify_external_change(
            root, state['nodes'].get(change['node_id']) if change['node_id'] else None)
        change.update(classification=classification, verification=verification)
        changes[change['change_id']] = change
    if detected and digest(source_tree(root)) != before:
        # Verification runs source that changed outside the flow, so the check can
        # move its own subject. A verdict for a snapshot that no longer exists is not
        # evidence: nothing is recorded and the comparison fails closed. The source is
        # left in the state the command left it: rolling it back would hide the move and
        # discard a change nobody decided.
        raise ValueError('Recorded acceptance modified the source it verifies; a check reads, it does not '
                         'modify. Reconcile the changed source before its impact can be classified')
    cache_classifications(root, changes)
    return detected, changes


def external_changes(root):
    """The boundary report of source changed outside the delivery flow."""
    detected, _ = resolve_external_changes(root)
    # A deferred conflict is still undecided: postponement is not acceptance.
    undecided = [c for c in detected if c['classification'] != 'fact-update'
                 and (c['resolution'] or {}).get('resolution') not in ('accept', 'reject')]
    status = ('conflict' if undecided else 'clear' if not detected else
              'fact_update' if all(c['classification'] == 'fact-update' for c in detected) else 'decided')
    return {'status': status, 'changes': detected}


def source_tree(root):
    context = _READ_EVALUATION.get()
    if context is None:
        return _source_tree(root)
    if context.tree is None:
        context.tree = _source_tree(root)
    return context.tree


def _ignore_aware_paths(root):
    """What the project itself carries: tracked files plus untracked ones it does not ignore.

    A project's ignore rules are its own statement about what it generates. A
    prebuilt native tree, a vendored dependency directory or a build output is not
    product source, and fingerprinting it into every record makes every gate slower
    the more the build produces — an Expo `ios/` tree alone reaches tens of
    thousands of files, which is a recorded snapshot per node of the same size.
    Returns None when Git cannot answer, so a project outside version control keeps
    the directory walk and its fixed exclusions.
    """
    # An ambient GIT_DIR/GIT_WORK_TREE/GIT_INDEX_FILE would point the question at
    # whatever repository the caller is standing in, so the listing is taken with the
    # project as the only repository in view.
    env = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
    try:
        listed = subprocess.run(['git', '-C', str(root), 'ls-files', '--cached', '--others',
                                 '--exclude-standard', '-z'],
                                capture_output=True, timeout=120, env=env)
    except (OSError, subprocess.SubprocessError):
        return None
    if listed.returncode != 0:
        return None
    return [p for p in listed.stdout.decode('utf-8', 'surrogateescape').split('\0') if p]


def _source_tree(root):
    """Every project file outside the flow's own working directories.

    Workflow-independent on purpose: a verification must not appear to move the
    source merely because the plan around it changed.
    """
    context = _READ_EVALUATION.get()
    paths = context.paths if context is not None else _ignore_aware_paths(root)
    if paths is None:
        paths = []
        for directory, dirs, files in os.walk(root):
            dirs[:] = sorted(d for d in dirs if d not in SOURCE_TREE_EXCLUDED_DIRS)
            paths.extend((Path(directory) / name).relative_to(root).as_posix() for name in sorted(files))
    result = {}
    for path in sorted(set(paths)):
        # `ls-files --cached` still names a tracked file that was deleted on disk.
        if Path(path).name == '.git' or not source_path_included(path) or not (root / path).is_file():
            continue
        result[path] = fingerprint(root, path)
    return result


SOURCE_TREE_EXCLUDED_DIRS = {'.git', '.allforai', '.claude', '.codex', '.local',
                             '__pycache__', '.pytest_cache', 'node_modules', '.venv', '.expo'}


def source_path_included(path):
    """Apply current source-tree exclusions to legacy recorded snapshots too."""
    return not any(part in SOURCE_TREE_EXCLUDED_DIRS for part in Path(path).parts)


def inventory(root, workflow):
    return _memoized(('inventory',), lambda: _inventory(root, workflow))


def _inventory(root, workflow):
    generated = {item['path'] if isinstance(item, dict) else item
                 for node in workflow.get('nodes', []) for item in node.get('exit_artifacts', [])}
    generated.update(workflow.get('generated_outputs', []))
    generated.update(p for node in workflow.get('nodes', []) for p in node.get('required_documents', []))
    return {path: value for path, value in source_tree(root).items() if path not in generated}


@_read_only_gate
def evaluate(root):
    workflow = read_json(root, WORKFLOW, {})
    state = read_json(root, STATE, {'nodes': {}})
    result: dict[str, dict[str, Any]] = {}
    current = inventory(root, workflow)
    owned = owned_inputs(root, workflow, state)
    uncertain_inputs = set()
    blockers = scope_blockers(root, workflow)
    external, unverified_external = routed_external_changes(root)
    for node in workflow.get('nodes', []):
        evidence = state['nodes'].get(node['node_id'])
        contract = state.get('contracts', {}).get(node['node_id'])
        record = contract or evidence
        if record is None and 'source_inputs' not in node:
            result[node['node_id']] = {'status': 'undeclared', 'readiness_status': 'undeclared',
                                      'reason': 'No source declaration or observation; no provenance claimed'}
            continue
        valid = record and record['inputs'] == snapshot(root, node, record.get('extra', []))
        valid = valid and record.get('outputs') == outputs(root, node, record.get('kind', 'evidence'))
        evidence_valid = (valid and evidence and evidence['inputs'] == snapshot(root, node, evidence.get('extra', []))
                          and evidence['outputs'] == outputs(root, node))
        diff: dict[str, Any]
        if record is None:
            diff = {'contract': 'unpublished'}
        else:
            bound = evidence or record
            diff = input_diff(bound['inputs'], snapshot(root, node, bound.get('extra', [])))
            changed = output_diff(bound.get('outputs', {}), outputs(root, node, bound.get('kind', 'evidence')))
            if evidence is None:
                diff['evidence'] = 'unpublished'
                changed.update(missing_outputs(outputs(root, node)))
            if changed:
                diff['outputs'] = changed
            unverified = unverified_documents(node, evidence)
            if unverified:
                diff['documents'] = unverified
                evidence_valid = False
        result[node['node_id']] = {'status': 'valid' if evidence_valid else 'stale',
                                  'readiness_status': 'valid' if valid else 'stale', 'diff': diff}
        if not evidence_valid:
            result[node['node_id']]['repair'] = repair_responsibility(root, node, diff, blockers, external)
        if record:
            previous = record.get('source_snapshot', {})
            unknown = {p for p in set(previous) | set(current)
                       if source_path_included(p) and not reclassified(root, p, current)
                       and previous.get(p) != current.get(p)} - owned
            uncertain_inputs.update(unknown)
            if unknown and valid:
                result[node['node_id']] = {'status': 'uncertain', 'readiness_status': 'uncertain',
                                          'reason': 'Unmapped product input changed'}
    graph = {n['node_id']: dependencies(root, n, workflow) for n in workflow.get('nodes', [])}
    for _ in workflow.get('nodes', []):
        previous = digest(result)
        for node in workflow['nodes']:
            stale_upstream = [dep for dep in graph[node['node_id']]
                              if result.get(dep, {}).get('status') != 'valid']
            if stale_upstream:
                entry = result[node['node_id']]
                entry['status'] = 'stale'
                entry['reason'] = 'Upstream evidence is stale or missing'
                if entry.get('status') != 'undeclared':
                    stale_diff = entry.setdefault('diff', {})
                    stale_diff['upstream'] = sorted(set(stale_diff.get('upstream', [])) | set(stale_upstream))
                    entry['repair'] = repair_responsibility(root, node, stale_diff, blockers, external)
            if any(result.get(dep, {}).get('readiness_status') != 'valid' for dep in graph[node['node_id']]):
                result[node['node_id']]['readiness_status'] = 'stale'
        if digest(result) == previous:
            break
    for node_id, entry in result.items():
        # Every gate reading this must be able to tell drift whose impact a verification
        # established from drift whose impact nothing has: the second is unknown, not
        # ordinary implementation repair, however similar the diff looks.
        if undecided_conflicts(external, node_id):
            entry['external'] = 'conflict'
        elif unverified_external.get(node_id):
            entry['external'] = 'unverified'
    return {'nodes': result, 'uncertain_inputs': sorted(uncertain_inputs)}


def session(root, request):
    operation = request['operation']
    if operation == 'check':
        return evaluate(root)
    if operation == 'external-changes':
        return external_changes(root)
    workflow = read_json(root, WORKFLOW, {})
    if operation == 'observe':
        node = next(n for n in workflow['nodes'] if n['node_id'] == request['node_id'])
        if 'source_inputs' not in node:
            raise ValueError('Missing source_inputs: impact is uncertain; declare relevant paths or explicit []')
        state = read_json(root, STATE, {'nodes': {}})
        extra = sorted(set(state['nodes'].get(node['node_id'], {}).get('extra', [])) |
                       set(state.get('contracts', {}).get(node['node_id'], {}).get('extra', [])) |
                       set(observed_reads(root).get(node['node_id'], [])))
        kind = request.get('kind', 'evidence')
        if kind not in {'contract', 'evidence'}:
            raise ValueError('Observation kind must be contract or evidence')
        observation = {'node_id': node['node_id'], 'inputs': snapshot(root, node, extra), 'extra': extra,
                       'source_snapshot': inventory(root, workflow), 'kind': kind,
                       'baseline_version': intent_baseline(root).get('version')}
        token = digest(observation)
        write_json(root, OBSERVATIONS + '/' + token + '.json', observation)
        return {'observation': token, **observation}
    if operation in {'read', 'publish'}:
        token = request['observation']
        if len(token) != 64 or any(c not in '0123456789abcdef' for c in token):
            raise ValueError('Invalid observation')
        observation = read_json(root, OBSERVATIONS + '/' + token + '.json')
        if digest(observation) != token:
            raise ValueError('Observation content does not match its identity')
        node = next(n for n in workflow['nodes'] if n['node_id'] == observation['node_id'])
        if (observation['inputs'] != snapshot(root, node, observation.get('extra', []))
                or observation['source_snapshot'] != inventory(root, workflow)):
            return {'status': 'stale', 'reason': 'Inputs changed after observation; reverify current inputs'}
        if operation == 'read':
            path = request['path']
            if orchestration_state(path):
                raise ValueError(f'{path} is orchestration state, not a product input: it changes on every '
                                 'committed transition, so registering it would make this evidence stale '
                                 'after each commit; read it without registering')
            fingerprint(root, path)  # Validate project containment before reading.
            content = (root / path).read_bytes()
            observation['extra'] = sorted(set(observation.get('extra', [])) | {path})
            observation['inputs']['files'][path] = hashlib.sha256(content).hexdigest()
            with publication_lock(root):
                reads = observed_reads(root)
                reads[node['node_id']] = sorted(set(reads.get(node['node_id'], [])) | {path})
                write_json(root, READS, reads)
            expanded = snapshot(root, node, observation['extra'])
            prior = observation['inputs']
            if (any(expanded[key] != prior[key] for key in ('files', 'requirements', 'contract', 'baseline_scope'))
                    or any(expanded['upstream'].get(dep) != value for dep, value in prior['upstream'].items())
                    or observation['source_snapshot'] != inventory(root, workflow)):
                return {'status': 'stale', 'reason': 'Inputs changed while registering dependency; reobserve current inputs'}
            observation['inputs']['upstream'] = expanded['upstream']
            token = digest(observation)
            write_json(root, OBSERVATIONS + '/' + token + '.json', observation)
            return {'observation': token, 'content': content.decode()}
        command = request.get('verification_command')
        if not isinstance(command, list) or not command or not all(isinstance(s, str) and s for s in command):
            raise ValueError('Publication requires an explicit verification_command argv')
        verified = subprocess.run(command, cwd=root, capture_output=True, text=True, timeout=300)
        if verified.returncode:
            return {'status': 'failed_verification', 'returncode': verified.returncode,
                    'stdout': verified.stdout, 'stderr': verified.stderr}
        with publication_lock(root):
            workflow = read_json(root, WORKFLOW, {})
            node = next(n for n in workflow['nodes'] if n['node_id'] == observation['node_id'])
            if (observation['inputs'] != snapshot(root, node, observation.get('extra', []))
                    or observation['source_snapshot'] != inventory(root, workflow)):
                return {'status': 'stale', 'reason': 'Inputs changed during verification; reverify current inputs'}
            upstream = evaluate(root)['nodes']
            required_status = 'readiness_status' if observation['kind'] == 'contract' else 'status'
            if any(upstream.get(dep, {}).get(required_status) != 'valid'
                   for dep in dependencies(root, node, workflow)):
                return {'status': 'stale', 'reason': 'Upstream verification is stale or missing; repair it before publishing consumer evidence'}
            observation['verification'] = {'command': command, 'returncode': 0,
                                           'stdout': verified.stdout, 'stderr': verified.stderr}
            observation['outputs'] = outputs(root, node, observation['kind'])
            if any(value is None for value in observation['outputs'].values()):
                diff = {'outputs': missing_outputs(observation['outputs'])}
                return {'status': 'inconsistent', 'diff': diff, 'repair': repair_responsibility(root, node, diff),
                        'reason': 'Required documents or evidence are missing; delivery is incomplete'}
            if observation['kind'] == 'evidence':
                checks = document_checks(node)
                undeclared = {p: 'unverified' for p in node.get('required_documents', []) if p not in checks}
                if undeclared:
                    diff = {'documents': undeclared}
                    return {'status': 'inconsistent', 'diff': diff, 'repair': repair_responsibility(root, node, diff),
                            'reason': 'Required documents need a declared project-specific verification against '
                                      'current source; declare document_verification at planning'}
                # A checker script is part of the delivery's inputs: an unobserved one
                # could change without invalidating the evidence it produced.
                unobserved: dict[str, str] = {}
                for path, argv in checks.items():
                    for token in argv:
                        identity = project_file_identity(root, token)
                        if (identity is not None and identity not in observation['outputs']
                                and identity not in observation['inputs']['files']):
                            unobserved.setdefault(path, 'unobserved-check:' + identity)
                if unobserved:
                    diff = {'documents': unobserved}
                    return {'status': 'inconsistent', 'diff': diff, 'repair': repair_responsibility(root, node, diff),
                            'reason': 'Document verification scripts must be consumed inputs; declare them in '
                                      'input_dependencies or register them with read, then reobserve'}
                documents = {}
                for path, argv in checks.items():
                    checked = subprocess.run(argv, cwd=root, capture_output=True, text=True, timeout=300)
                    if checked.returncode:
                        return {'status': 'failed_verification', 'document': path, 'command': argv,
                                'returncode': checked.returncode, 'stdout': checked.stdout, 'stderr': checked.stderr,
                                'repair': {'owner': node['node_id'], 'responsibilities': ['documentation']},
                                'reason': 'Required document does not verify against the current source; '
                                          'synchronize its facts, then reverify'}
                    documents[path] = {'command': argv, 'returncode': 0}
                # Recheck every current input after the last check ran: a checker that
                # rewrites source A into B must not publish A's evidence for B.
                if (observation['inputs'] != snapshot(root, node, observation.get('extra', []))
                        or observation['source_snapshot'] != inventory(root, workflow)
                        or outputs(root, node, observation['kind']) != observation['outputs']):
                    return {'status': 'stale', 'reason': 'Inputs or outputs changed during document verification; '
                                                         'a check reads, it does not modify; reobserve current inputs'}
                observation['verification']['documents'] = documents
            state = read_json(root, STATE, {'nodes': {}})
            bucket = 'contracts' if observation['kind'] == 'contract' else 'nodes'
            state.setdefault(bucket, {})[node['node_id']] = observation
            if bucket == 'nodes':
                state.get('contracts', {}).pop(node['node_id'], None)
            write_json(root, STATE, state)
        return {'status': 'valid', 'verified_documents': sorted(observation['verification'].get('documents', {}))}
    raise ValueError('Unknown operation')


def main():
    try:
        result = session(Path(sys.argv[1]).resolve(), json.load(sys.stdin))
    except (ValueError, KeyError, TypeError, OSError, StopIteration, subprocess.TimeoutExpired) as exc:
        result = {'status': 'invalid', 'reason': str(exc)}
    print(json.dumps(result, sort_keys=True))
    return 1 if result.get('status') in {'stale', 'invalid', 'inconsistent', 'failed_verification',
                                         'conflict'} else 0


if __name__ == '__main__':
    raise SystemExit(main())
