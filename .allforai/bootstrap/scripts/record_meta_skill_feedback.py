#!/usr/bin/env python3
"""Record deidentified meta-skill feedback locally, or fall back to GitHub issue drafts."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path


DEFAULT_REPO = "allforai/myskills"
GENERIC_PROJECT_NAMES = {"project", "repo", "app", "workspace", "client", "server"}
SENSITIVE_PATTERNS = [
    re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}"),
    re.compile(r"(?:token|api[_-]?key|secret|password)\s*[:=]\s*[^\s`]+", re.I),
    re.compile(r"https?://[^\s`]+"),
    re.compile(r"/Users/[^/\s`]+/[^\s`]*"),
    re.compile(r"/home/[^/\s`]+/[^\s`]*"),
]


def _run(args: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


def _load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _sanitize(text: str, *, project_root: Path) -> str:
    result = text
    project_name = project_root.name
    home = str(Path.home())
    result = result.replace(str(project_root), "<project-root>")
    result = result.replace(home, "<home>")
    if project_name:
        result = re.sub(re.escape(project_name), "<project>", result, flags=re.I)
    for pattern in SENSITIVE_PATTERNS:
        result = pattern.sub("<redacted>", result)
    return result


def _privacy_findings(text: str, *, project_root: Path) -> list[str]:
    findings = []
    if str(project_root) in text:
        findings.append("project_root_path")
    if (
        project_root.name
        and project_root.name.lower() not in GENERIC_PROJECT_NAMES
        and re.search(re.escape(project_root.name), text, re.I)
    ):
        findings.append("project_name")
    if re.search(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", text):
        findings.append("email")
    if re.search(r"(?:token|api[_-]?key|secret|password)\s*[:=]\s*[^\s`]+", text, re.I):
        findings.append("secret_like_value")
    if re.search(r"/Users/[^/\s`]+/|/home/[^/\s`]+/", text):
        findings.append("absolute_user_path")
    if re.search(r"https?://[^\s`]+", text):
        findings.append("url")
    return findings


def _candidate_repos(project_root: Path) -> list[Path]:
    values = []
    env_path = os.environ.get("META_SKILL_LOCAL_REPO")
    if env_path:
        values.append(Path(env_path).expanduser())
    values.extend([
        project_root.parent / "myskills",
        project_root.parent.parent / "myskills",
        Path.home() / "workspace/myskills",
    ])
    seen = set()
    result = []
    for value in values:
        resolved = value.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        result.append(resolved)
    return result


def _is_myskills_repo(path: Path) -> bool:
    if not (path / ".git").exists():
        return False
    proc = _run(["git", "remote", "-v"], cwd=path)
    if proc.returncode != 0:
        return False
    return "allforai/myskills" in proc.stdout or "allforai/myskills" in proc.stderr


def _writable_repo(path: Path) -> bool:
    if not os.access(path, os.W_OK):
        return False
    inbox = path / "docs/feedback/inbox"
    try:
        inbox.mkdir(parents=True, exist_ok=True)
        probe = inbox / ".write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink()
        return True
    except Exception:
        return False


def find_local_myskills(project_root: Path) -> Path | None:
    for candidate in _candidate_repos(project_root):
        if candidate.exists() and _is_myskills_repo(candidate) and _writable_repo(candidate):
            return candidate
    return None


def _collect_learned(project_root: Path) -> str:
    learned = project_root / ".allforai/bootstrap/learned"
    parts = []
    if learned.exists():
        for path in sorted(learned.glob("*.md")):
            text = path.read_text(encoding="utf-8", errors="replace").strip()
            if text:
                parts.append(f"## {path.name}\n\n{text}")
    return "\n\n".join(parts)


def _issue_body(category: str, message: str, version: str | None) -> str:
    return f"""## Anonymous Meta-Skill Feedback

Category: {category}
Meta-skill version: {version or "unknown"}

### Failure Pattern

{message}

### Expected Behavior

The meta-skill should record or repair this class of workflow issue without exposing project-specific information.

### Suggested Fix

Update the relevant skill, bootstrap rule, validator, or orchestrator helper so future projects do not hit the same failure pattern.
"""


def _write_local(repo: Path, body: str, category: str) -> Path:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    slug = re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-") or "feedback"
    path = repo / "docs/feedback/inbox" / f"{timestamp}-{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body.rstrip() + "\n", encoding="utf-8")
    return path


def _write_pending(project_root: Path, body: str, category: str, mode: str, privacy_findings: list[str]) -> tuple[Path, Path]:
    root = project_root / ".allforai/bootstrap"
    root.mkdir(parents=True, exist_ok=True)
    md_path = root / "pending-feedback.md"
    json_path = root / "pending-feedback.json"
    payload = {
        "schema_version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "category": category,
        "repo": DEFAULT_REPO,
        "privacy_findings": privacy_findings,
        "body": body,
    }
    md_path.write_text(body.rstrip() + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return md_path, json_path


def _try_create_issue(body: str, category: str) -> dict:
    """Create an anonymous issue using the equivalent of `gh issue create`."""
    gh = shutil.which("gh")
    if not gh:
        return {"created": False, "reason": "missing_gh_cli"}
    auth = _run([gh, "auth", "status"])
    if auth.returncode != 0:
        return {"created": False, "reason": "gh_not_authenticated"}
    title = f"[Auto Feedback] {category}"
    label = "feedback/auto"
    _run([gh, "label", "create", label, "--repo", DEFAULT_REPO, "--color", "#0075ca", "--description", "Automatic feedback from meta-skill"])
    proc = _run([gh, "issue", "create", "--repo", DEFAULT_REPO, "--title", title, "--body", body, "--label", label])
    return {
        "created": proc.returncode == 0,
        "reason": "created" if proc.returncode == 0 else "gh_issue_create_failed",
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def record_feedback(project_root: Path, *, message: str | None, category: str, mode: str, version: str | None = None) -> dict:
    project_root = project_root.resolve()
    raw = message or _collect_learned(project_root)
    if not raw.strip():
        return {"status": "skipped", "reason": "no_feedback_content"}

    sanitized_message = _sanitize(raw, project_root=project_root)
    body = _issue_body(category, sanitized_message, version)
    privacy_findings = _privacy_findings(body, project_root=project_root)
    if privacy_findings:
        md_path, json_path = _write_pending(project_root, body, category, mode, privacy_findings)
        return {
            "status": "pending_privacy_review",
            "reason": "privacy_scan_failed",
            "privacy_findings": privacy_findings,
            "pending_markdown": str(md_path),
            "pending_json": str(json_path),
        }

    local_repo = find_local_myskills(project_root)
    if local_repo:
        path = _write_local(local_repo, body, category)
        return {
            "status": "recorded_local_myskills",
            "local_repo": str(local_repo),
            "record_path": str(path),
            "message": "Local myskills repo found; feedback recorded locally instead of creating an anonymous GitHub issue.",
        }

    if mode == "auto":
        issue = _try_create_issue(body, category)
        if issue.get("created"):
            return {"status": "created_github_issue", "issue": issue}
        md_path, json_path = _write_pending(project_root, body, category, mode, [])
        return {
            "status": "pending_github_issue",
            "reason": issue.get("reason"),
            "pending_markdown": str(md_path),
            "pending_json": str(json_path),
        }

    md_path, json_path = _write_pending(project_root, body, category, mode, [])
    return {
        "status": "pending_github_issue",
        "reason": "no_local_myskills_repo",
        "pending_markdown": str(md_path),
        "pending_json": str(json_path),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--message")
    parser.add_argument("--category", default="workflow-gap")
    parser.add_argument("--mode", choices=["draft", "auto"], default=os.environ.get("META_SKILL_FEEDBACK_MODE", "draft"))
    parser.add_argument("--version")
    args = parser.parse_args(argv)
    result = record_feedback(
        Path(args.project_root),
        message=args.message,
        category=args.category,
        mode=args.mode,
        version=args.version,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
