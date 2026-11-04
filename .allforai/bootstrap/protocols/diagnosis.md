# Full-Chain Diagnosis Protocol

> Dispatched when any node returns status "failure". Performs root cause analysis,
> same-class gap expansion, and generates a repair plan.

## When to Trigger

A node subagent returns `{ "status": "failure", "errors": [...] }`.
Do NOT retry or backtrack. Diagnose first.

## Diagnosis Subagent Prompt Template

```
You are diagnosing a workflow failure.

## Failure Context
- Failed node: {node_id}
- Error: {errors from subagent response}
- Iteration: {iteration_count}

## System State
- All nodes: {nodes[] from workflow.json — id + goal + exit_artifacts per node}
- All node exit_artifacts: {extracted from workflow.json nodes[].exit_artifacts}
- Game-design gate state (if applicable): {records[] from .allforai/game-design/approval-records.json — check gate_status for any node with capability: game-design; revision-requested status not reset after re-execution is a common false-failure mode}
- Previous diagnoses: {diagnosis_history}

## Your Tasks

1. **Root Cause**: Trace from the failed node upstream. Which is the earliest
   node whose output is insufficient? Don't guess — read the actual artifact
   files via Read tool if needed.

2. **Impact Chain**: List all intermediate nodes between root cause and failure.

3. **Same-Class Expansion**: The specific gap you found — are there similar gaps
   elsewhere? If one API was missed, were other APIs in the same domain also missed?
   If one business flow is incomplete, are sibling flows also incomplete?

4. **Repair Plan**: Ordered list of nodes to re-run, from upstream to downstream.
   Each entry: node ID + specific action + what context to carry.
   Use `depends_on_previous: true` when a step needs the prior step's output.

5. **Prevention**: Should any node-spec's exit_artifacts or hints be tightened
   to prevent this class of failure in future iterations?

## Output Format

Return JSON:
```json
{
  "root_cause": {
    "node": "<node-id>",
    "description": "<what's wrong>"
  },
  "impact_chain": ["<node-id>", ...],
  "gaps_found": [
    { "domain": "<area>", "missing": ["<item>", ...], "severity": "high|medium|low" }
  ],
  "repair_plan": [
    { "node": "<node-id>", "action": "<what to do>", "depends_on_previous": true|false }
  ],
  "prevention": [
    { "node_spec": "<node-id>", "add_to_exit_artifacts": "<new file path to check>" },
    { "node_spec": "<node-id>", "add_to_hints": "<new hint>" }
  ]
}
```
```

## Repair Plan Execution

After diagnosis returns:

1. Orchestrator reads repair_plan
2. Executes each step in order:
   - Read the node-spec for that node
   - Dispatch subagent with the repair action as additional context
   - Carry gaps_found so the subagent knows the full scope
3. After each step, update workflow.json progress
4. Apply prevention rules: Edit the affected node-spec files
5. **After each successful repair step**, orchestrator appends to `workflow.json corrections_applied[]`:
   ```json
   { "node": "<node-id>", "what_was_wrong": "<root_cause.description>", "fix_applied": "<repair action taken>", "timestamp": "<ISO>" }
   ```

## Re-Verification

After repair_plan completes:
- Re-evaluate the originally failed node's exit_artifacts existence check
- If still failing → diagnose again (with updated context)
- diagnosis_history prevents re-diagnosing the same root cause

## Diagnosis History Recording

Each diagnosis result is appended to `workflow.json diagnosis_history[]` by the orchestrator:

```json
{
  "timestamp": "<ISO timestamp>",
  "failed_node": "<node-id>",
  "root_cause": { "node": "<node-id>", "description": "<what's wrong>" },
  "impact_chain": ["<node-id>", "..."],
  "gaps_found": [{ "domain": "<area>", "missing": ["<item>"], "severity": "high|medium|low" }],
  "repair_plan": [{ "node": "<node-id>", "action": "<what to do>", "depends_on_previous": true }],
  "out_of_scope": false
}
```

## Convergence Control

- Same root cause: max 2 diagnoses. 3rd → mark UNRESOLVED, output current best + TODO
- Repair plan length ≤ impact_chain length (can't be longer than the chain)
- Previously identified gaps must resolve (new gaps OK, old gaps can't recur)
- Repair step failure → new diagnosis, but nested depth max 1 level
- Each diagnosis record written to workflow.json diagnosis_history

## Out-of-Scope Repairs

If the diagnosis identifies a root cause in a node that **does not exist** in the current
state machine (e.g., demo-forge fails because API is missing, but there is no translate
node to fix the code), the orchestrator:

1. Marks the gap as UNRESOLVED
2. Records it in diagnosis_history with `"out_of_scope": true`
3. Outputs a clear TODO: "This issue requires [capability X] which is not in the current
   workflow. Re-run /bootstrap with goals including [X] to add the necessary nodes."
4. Does NOT attempt to create new nodes at runtime — node set is fixed at bootstrap time

This handles the scenario where a limited-scope workflow (e.g., goals: ["demo"]) encounters
issues that require capabilities from a broader scope (e.g., translate or tune).
