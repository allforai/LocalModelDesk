"""Where each agent reads user-level skills (A-50/A-51). Paths are relative to HOME unless they start with /."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

SKILL_NAME = "local-model-desk"
SKILL_SUFFIX = ("agent_skill", "bundled", SKILL_NAME)
CLI_LINK = Path(".local/bin/lmdesk")
CLI_SUFFIXES = (("Contents", "Resources", "bin", "lmdesk"), ("scripts", "lmdesk"))


@dataclass(frozen=True)
class Target:
    key: str
    name: str
    link: Path
    detect_cmds: tuple[str, ...]
    detect_paths: tuple[Path, ...]
    shared_note: str | None = None


TARGETS = (
    Target("claude", "Claude Code", Path(".claude/skills") / SKILL_NAME, ("claude",),
           (Path(".claude"), Path(".local/bin/claude"))),
    Target("codex", "Codex", Path(".agents/skills") / SKILL_NAME, ("codex",), (Path(".codex"),),
           "同时对 pi、DeepSeek Harness 生效"),
    Target("pi", "pi", Path(".pi/agent/skills") / SKILL_NAME, ("pi",), (Path(".pi"),)),
    Target("dsh", "DeepSeek Harness", Path(".dsh/skills") / SKILL_NAME, (),
           (Path("/Applications/DeepSeek Harness.app"), Path("Applications/DeepSeek Harness.app"), Path(".dsh"))),
)
