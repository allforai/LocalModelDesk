# Source, baseline and evidence freshness

Bootstrap and resume use the copied `evidence_freshness.py` and
`reconcile_bootstrap_workflow.py` before reusing prior work. Both platforms use
these same helpers. This is a boundary check, not a background watcher.

For each workflow node, declare `source_inputs` as project-relative files,
directories or globs (explicit `[]` only when no product source is relevant),
`input_dependencies` for additional consumed files, and `required_documents`
for generated fact documents that must accompany delivery, each mapped in
`document_verification` to a project-specific argv that executes the document's
stated facts against the current source (documented examples, interfaces or
behaviors run against the code; existence, a hash or a status field is not a
check). A required document without that mapping is refused by every gate as
`missing_document_verification`. A node that writes product source declares
those paths in `parallel_write_scopes`: what a node delivers is part of its
contract, not something the gates infer from what it happens to read. Keep existing
`requirement_refs`, `decision_inputs` and `hard_blocked_by` contracts. Declare
other generated files in workflow `generated_outputs`; never classify product
source as generated merely to silence drift. Missing dependency knowledge is
uncertain impact and must be coordinated before affected work can proceed.
Every node that consumes `requirement_refs` must carry `source_inputs`; the
bootstrap, artifact, readiness and reconciliation gates report
`missing_source_inputs` or `invalid_source_inputs` for an omitted or malformed
declaration instead of skipping freshness or passing. Retained completed nodes
outside the current scope, without declarations or recorded observations, keep
their legacy gate behavior and are reported as `undeclared` with no provenance
claimed. A completion label cannot exempt current scoped work; removing a
previously recorded input declaration cannot downgrade verification to legacy.
Reopening historical work requires a declaration.

The source inventory excludes `.allforai`, generated host configuration, Git
metadata, dependency/cache directories, explicitly declared outputs, and whatever
the project's own ignore rules exclude: a build output or a prebuilt native tree
is the project stating that it generates those files, and fingerprinting them into
every record grows the recorded state — and the cost of every gate that reads it —
with the size of the build rather than the size of the product. A project outside
version control keeps the fixed exclusions. Inputs
inside those directories still participate when explicitly consumed. Selected
requirement content and baseline scope are fingerprinted independently of
unrelated decisions; the observed baseline version is retained as provenance.
The journal remains the sole product-decision authority. Freshness never accepts
changed implementation as a product decision and never edits that journal.

Use JSON on stdin to `python3 .allforai/bootstrap/scripts/evidence_freshness.py .`:

1. After declaring a node and its inputs, before generating its documents, send
   `{"operation":"observe","node_id":"NODE","kind":"contract"}`. Retain the
   returned content-addressed `observation` token. Generate/reconcile the Node-spec
   and required documents from those observed inputs.
2. If analysis discovers another input, send
   `{"operation":"read","observation":"TOKEN","path":"path/to/input"}`.
   Consume the returned content and replace TOKEN with the returned observation.
   This read is durably retained even when publication subsequently fails.
3. Publish with `{"operation":"publish","observation":"TOKEN",
   "verification_command":["python3","path/to/project-contract-validator.py"]}`.
   Supply a real project-specific validation argv that checks the relevant
   contract/documents; file existence or a no-op is not verification. The helper
   executes it and rejects nonzero exit, missing outputs, or inputs changed
   before/during verification. Contract publication permits execution but cannot
   prove completion; it binds the Node-spec, while required documents, exit
   artifacts and a verify gate's ledger-shaped entries
   (`<run>/evidence-entries/<node_id>.json` beside its exit artifacts, plus every
   evidence file those entries cite) are bound only when evidence is published.
4. After implementation has settled, observe again with `kind:"evidence"` before
   running acceptance and refreshing required documents. Publish that token with
   the real project-specific acceptance command. A newly observed snapshot alone
   cannot refresh old evidence: publication runs verification against that input.
   If the source changes, re-observe and actually reverify the new state. A
   missing required document or exit artifact returns `inconsistent` with the
   missing `diff.outputs` and its `repair` owner: passing tests do not complete
   a delivery whose facts are absent. The helper then executes every declared
   `document_verification` against the observed source; a document whose facts
   no longer hold returns `failed_verification` naming the `document` with the
   node as documentation owner, whatever the acceptance command reported. An
   evidence record whose documents were not verified under the currently
   declared check is `stale` with `diff.documents`. A check reads; after the last
   check the helper rechecks every current input and output, and a check that
   changed any source, upstream input or output is rejected as `stale` so proof
   observed for state A is never published for state B. A project checker script
   named in the argv must itself be a consumed input (`input_dependencies` or a
   registered `read`); otherwise publication returns `inconsistent` with
   `unobserved-check`, and a weakened checker later shows as a changed input.
   Correct the facts, re-observe and republish: only the affected node's record
   changes.
5. On bootstrap/resume send `{"operation":"check"}`, then run reconciliation
   with `--write`. `check_artifacts.py` consumes evidence freshness and
   `validate_unattended_readiness.py` consumes contract readiness. Do not bypass
   either gate, including when transition history says completed.

Changed source content, path/glob membership, relevant baseline scope, consumed
inputs or generated evidence invalidate direct and transitive consumers. An
unmapped source change is explicitly `uncertain`; coordinate the input mapping
and affected documents rather than claiming zero impact or rebuilding everything.
Revalidating a producer does not refresh its consumers. Reconcile only affected
work, preserve unrelated valid records, and reverify affected consumers in order.
Repeated checks are read-only and identical publication does not rewrite state.

Invalidation travels the way the flow does. A node's `source_inputs` bind what it
consumed in order to produce its work, so a path the flow itself delivers further
down the graph is an output of the plan, not an input to the work that planned it.
A design that names the implementation it governs inverts the graph: delivering
that implementation then stales the design it was built from, the design cannot be
refreshed without reopening frozen work, and the delivery can never publish. A path
covered by the declared `parallel_write_scopes` of a transitive consumer is
therefore excluded from an upstream node's binding instead of being fingerprinted
into it. The exclusion follows the dependency graph and never a node's claim about
itself: a node cannot exempt its own inputs, and an undeclared write scope excludes
nothing, so an implementation that never says what it writes keeps invalidating its
planners — that is the missing declaration reported, not freshness failing. Changes
inside a declared write scope still invalidate the node owning that scope and its
own consumers, and still surface as external change when no delivery accounts for
them. Planning refuses the inversion rather than tolerating it: `source_inputs`
that intersect the declared write scope of a node depending on that node are
reported as `inverted_source_inputs`.

## Source changed outside the delivery flow

At bootstrap/resume, after `check`, send `{"operation":"external-changes"}`. It
compares each published record with the current source, runs that delivery's own
recorded acceptance argv against the changed code, and records what it found in
`.allforai/bootstrap/external-changes.json`. This is the same boundary comparison,
not a background watcher, and it never writes the decision journal.

The freshness `check`, `check_artifacts.py`, reconciliation and readiness gates run
the detection themselves, so drift reaches them even when the explicit operation was
never sent, and none of them interviews or decides. What they do not do is execute
the project's acceptance: running project argv against live source is an act, not an
observation, and a gate that performs it can destroy the very out-of-flow edit it is
reporting on — a self-healing acceptance would regenerate the file and the drift
would disappear into a fact update nobody decided. A gate therefore reads the
recorded verdict and keeps it only while the basis it was established against — that
acceptance argv, that project source — still holds. Detected drift with no verdict
standing is `unverified_external_change`: unknown impact, affected work withheld, no
product decision demanded. Repeated boundary checks are read-only and leave the
store byte-identical.

The explicit operation is the verification, and it always executes afresh rather than
repeating what the store remembers. Whatever an acceptance depends on beyond the
project source — an installed dependency, a service, the environment — can move
without anything observable changing, so re-running `external-changes` is how a user
re-establishes a verdict they have reason to doubt. If the recorded acceptance moves
the source while it runs, no verdict is recorded: the run reports the move and leaves
the source in the state the command left it, since rolling it back would hide the move
and discard a change nobody decided.

- Recorded acceptance still passes: `fact-update`. The change is implementation
  only. Update the required fact documents and republish evidence; no product
  decision is asked for and none is required.
- Recorded acceptance fails: `product-conflict`. Changed code never becomes the
  desired behavior. The affected node's repair owner is `interactive-bootstrap`
  (`product-decision`) and readiness reports `unresolved_external_change`.
- Changed source that no node declares: `uncertain`, reported against every
  delivery whose provenance it touches. Coordinate the input mapping and the
  affected documents; zero impact is never assumed and nothing is rebuilt wholesale.
- No verification standing for the current source: readiness reports
  `unverified_external_change`, `check` and `check_artifacts.py` carry
  `external: unverified`, reconciliation carries `external_change: unverified`, and
  the affected work is withheld. This is unknown impact, not an implementation-only
  change and not yet a product question: verify the scoped drift and let the result
  decide whether a decision is needed. Repair routing stays with the owning node, so
  an implementation fact still recovers through documents and republication without
  anyone being interviewed.
- The comparison itself cannot be completed — unreadable freshness state, an
  unparseable change store: readiness reports `undetermined_external_change`,
  project-wide rather than against one node, because no delivery can be shown to be
  free of a waiting product conflict. Repair the unreadable state at the interactive
  bootstrap entry. An undeterminable comparison is never read as a clear one.

A verdict is what a verification found, so it stands only while the source that
verification ran against still does. That source is what the flow consumes, not what
it produces: a `fact-update` prescribes resynchronizing the required documents, and
obeying a verdict cannot invalidate it. A change the user has already decided is
routed by the decision, not by the verdict's freshness — an accepted change stops
holding work, a rejected one keeps its scoped repair, a deferred one keeps its hold,
and each keeps the finding it was decided against. Only revised confirmed intent
retires a decision.

A conflict is settled only by the user, through `product_intent.py` with
`{"operation":"external-change","change_id":...,"resolution":"accept|reject|defer"}`
plus an actual `user_reference` and `reason`:

- `accept` carries the explicit intent `actions` that the change establishes and
  records them in one journal batch tagged with the change. Those intent changes
  then follow the ordinary refreeze, replan, resynchronize and reverify loop; the
  baseline version advances there, not in the acceptance itself. Accepting a change
  that touches confirmed decisions without stating the desired intent is refused.
- `reject` keeps the confirmed baseline, records the decision and its reason, and
  produces a scoped implementation repair task naming the node, the changed files
  and the confirmed acceptance to restore. Readiness reports
  `external_change_repair_pending` until that acceptance republishes.
- `defer`, and an interrupted interaction that records nothing at all, keep the
  conflict and its context. Work depending on the decision stays blocked; unrelated
  valid records keep their provenance and are not replanned or reset. The next
  boundary reports the same change identity with its resolution intact.

A change identity binds the node and the current content of the changed files, so
a later edit is a different change and an earlier decision cannot travel to it.
Advancing the confirmed baseline version for other work never changes that
identity: the decision was about this source, and an unrelated refreeze must not
orphan it or ask the user again. What a resolution does bind is the confirmed
requirement content it was decided against; when the user revises those very
requirements, the resolution is retained as `superseded_resolutions` history and
the change is presented for a fresh decision rather than carrying old consent to
a question the user has since changed. Detection never invents, reopens or
recomputes a recorded resolution, and a verified implementation-only change is
synchronized through its documents rather than through a product decision. Run Policy answers
are run choices: `accept` there is not acceptance of a changed product behavior.
Unattended execution reports unresolved conflicts and refuses the affected work; it
never interviews and never assumes acceptance. Resolution returns to the
interactive bootstrap entry and continues from the retained conflict.

Every withheld completion is an explicit difference with a repair owner, never a
bare warning. `check`, `check_artifacts.py`, the readiness `stale_evidence`
blocker and reconciliation `invalidate` items carry `diff` (changed `files`,
`requirements`, `baseline_scope`, `contract`, `outputs`, stale `upstream`, or an
`unpublished` contract/evidence) and `repair` (`owner` plus the drifted
`responsibilities`). A pending or not-yet-replanned product decision names
`interactive-bootstrap` (`product-decision` / `replan`); a stale producer names
that producer (`upstream`); everything else returns to the owning node
(`implementation`, `documentation`, `verification`, `contract`,
`requirement-sync`). Repair at the owner, re-observe, and republish against the
current inputs; the new evidence restores completion while unrelated valid
records keep their provenance. An approved product change is applied through
its recorded decision, refreeze and replan; it is never asked again and never
rewritten by implementation. `accepted_with_gaps` is a qualified Run Policy
outcome and a blocking artifact status: it cannot become verified or completed.
Unattended execution reports unresolved freshness prerequisites; product choices
return to interactive bootstrap. Existing Run Policy and visual-review rules apply.


### Read-only evaluation reuse

A single Python freshness gate may reuse parsed JSON, file fingerprints, inventory,
dependency edges and shared-ancestor snapshots. The reuse belongs only to that
read-only call (including nested external-change observation), and is discarded
before returning. Snapshot keys include the node contract and extra reads; cycle
checks and dynamically recorded dependencies still apply. Dependency propagation
uses the same graph and stops once verdicts converge.

Before returning a verdict, the gate checks the contents and metadata of observed
files, declared dependency-glob membership, and the product source tree again.
Changed inputs reject the evaluation rather than extending the cache's lifetime.
Product source glob checks preserve the existing generated-file and runtime-cache
exclusions. Missing inputs remain observed, so creating one invalidates the read.
No reuse crosses observation/publication, an actual verification command, or a
later gate. Publication inside the read-only context is rejected. This optimization
does not replace validation with file existence or raise execution timeouts.
