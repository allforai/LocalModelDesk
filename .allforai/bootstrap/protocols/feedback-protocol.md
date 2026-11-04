# Meta-Skill Feedback Protocol

> After experience extraction, record universally useful findings for the
> myskills repository without leaking project-specific information.

## When to Trigger

After learning extraction (learning-protocol.md), if any extracted items
are classified as universally useful (not project-specific):

- Mapping gaps in preset mapping files → useful for all users of that stack pair
- Discovery blind spots → useful for all projects
- Convergence issues → useful for meta-skill improvement
- Safety gaps → critical for all users

Project-specific items (e.g., "this project's auth is unusual") stay local only.

## Privacy Rules (MANDATORY)

Before proposing any Issue, verify the content contains:
- Tech stack names (React, SwiftUI, Go, Gin)
- Abstract pattern descriptions ("CRUD completeness check", "handler directory coverage")
- Threshold/config suggestions ("coverage 50% → 80%")
- NO project names, company names, domain-specific terms
- NO file paths from the user's project
- NO code snippets from the user's project
- NO user identity (name, email, username)
- NO business logic descriptions

## Target Priority

Feedback uses this strict priority order:

1. **Local myskills repo first.** If a writable local `myskills` repository is
   available, record sanitized feedback there and notify the user. Do not
   create a GitHub Issue.
2. **Anonymous GitHub fallback.** If no local myskills repo is available, write
   sanitized GitHub issue content to project-local pending files. Only create an
   issue automatically when `META_SKILL_FEEDBACK_MODE=auto`, `gh` is
   authenticated, and the privacy scan passes.

Local repo candidates:

- `$META_SKILL_LOCAL_REPO`
- `../myskills` from the target project
- `../../myskills` from the target project
- `~/workspace/myskills`

The local repo must be a git repository whose remote contains
`allforai/myskills`, and it must be writable. If it is missing or unsafe, do not
write to it.

## Non-Interactive Flow

```
Orchestrator runs:

python3 .allforai/bootstrap/scripts/record_meta_skill_feedback.py . \
  --category "<mapping-gap|discovery-blind-spot|convergence|safety|workflow-gap>" \
  --message "<short deidentified failure pattern>"
```

- If local myskills exists → write `docs/feedback/inbox/<timestamp>-<category>.md`
  in that repo and report the path.
- If local myskills is unavailable → write:
  - `.allforai/bootstrap/pending-feedback.md`
  - `.allforai/bootstrap/pending-feedback.json`
- If `META_SKILL_FEEDBACK_MODE=auto` and GitHub is available → create an
  anonymous issue after privacy scan. Otherwise keep the pending draft.

## Issue Creation

For fallback issue creation:

```bash
# Ensure labels exist before creating issue (safe to run even if labels already exist)
gh label create "feedback/auto" --repo allforai/myskills --color "#0075ca" --description "Automatic feedback from meta-skill" 2>/dev/null || true
gh label create "{tech_stack_label}" --repo allforai/myskills --color "#e4e669" 2>/dev/null || true

gh issue create \
  --repo allforai/myskills \
  --title "[Auto Feedback] {tech_stack_pair} — {one_line_description}" \
  --body "$(cat <<'EOF'
## [Auto Feedback] {tech_stack_pair} — {description}

**Source**: meta-skill automatic feedback (anonymous)
**Tech Stack**: {source} → {target}
**Category**: {mapping-gap | discovery-blind-spot | convergence | safety}

### Description
{deidentified improvement suggestion}

### Suggested Change
{which knowledge file to modify and what to add/change}
EOF
)" \
  --label "feedback/auto,{tech_stack_label}" 2>/dev/null || \
gh issue create \
  --repo allforai/myskills \
  --title "[Auto Feedback] {tech_stack_pair} — {one_line_description}" \
  --body "$(cat <<'EOF'
## [Auto Feedback] {tech_stack_pair} — {description}
**Category**: {mapping-gap | discovery-blind-spot | convergence | safety}
{deidentified improvement suggestion}
Suggested: {which knowledge file to modify and what to add/change}
EOF
)"
```

## Fallback

If `gh` CLI is not available or not authenticated:
- Log the Issue content to `.allforai/bootstrap/pending-feedback.md`
- Inform user: "gh CLI 不可用，反馈已保存到 pending-feedback.md，您可以稍后手动提交"

If the privacy scan fails:
- Do not submit an issue.
- Write pending files with `privacy_findings[]`.
- Notify the user that manual review is required.
