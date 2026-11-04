# Cross-Project Learning Protocol

> After /run completes, the orchestrator extracts reusable experience and
> writes it to `.allforai/bootstrap/learned/` in the target project.

## When to Trigger

After the orchestrator loop terminates (success or safety stop), if
workflow.json has any entries in:
- `corrections_applied` (node-spec modifications during execution)
- `diagnosis_history` (full-chain diagnoses performed)

## Extraction Process

1. Read `corrections_applied[]` and `diagnosis_history[]` from workflow.json
2. For each correction in corrections_applied:
   - Extract: which node, what was wrong, what was learned
   - Classify: mapping-gap / discovery-blind-spot / convergence / safety / other
3. For each diagnosis in diagnosis_history:
   - Extract: root_cause pattern, gaps_found domains
   - Classify same way
4. Group by tech stack pair (source → target) or by node type

## Output Format

Append to `.allforai/bootstrap/learned/<category>.md`:

```markdown
## [{date}] {project_name or "anonymous"}

### {Classification}
- {What was wrong} → {What was learned}
- {Pattern} → {Fix applied}

### Source
- Correction/Diagnosis from: {node_id}
- Severity: {high/medium/low}
```

## File Naming Convention

- Tech stack specific: `<source>-<target>.md` (e.g., `react-swiftui.md`)
- Node specific: `<node-type>-patterns.md` (e.g., `discovery-patterns.md`)
- General: `general-patterns.md`
- Blind spots (gaps not caught by expected capability node): `blind-spots.md` (append, do not overwrite)

## Privacy Rules

- Do NOT include project name, company name, file paths, code snippets
- Do NOT include user identity information
- Only include abstract, tech-stack-level descriptions
- Example: "styled-components → ViewModifier mapping missing" (OK)
- Counter-example: "In /Users/john/acme-shop/src/Button.tsx..." (NOT OK)

## Consumption

Next `/bootstrap` reads `.allforai/bootstrap/learned/` in Step 2.4 / Step 2.4.1 (Load Tech Stack Mappings + Load Blind-Spot Retrospectives).
Learned experience takes precedence over preset mappings when they conflict
(learned comes from actual execution, presets are theoretical).
