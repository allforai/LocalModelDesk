"""A-80/A-82: SKILL.md shape and the sections agents rely on; scripts/lmdesk runs."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "desk" / "agent_skill" / "bundled" / "local-model-desk" / "SKILL.md"


def _frontmatter(text):
    assert text.startswith("---\n")
    head, _, body = text[4:].partition("\n---\n")
    fields = {}
    for line in head.splitlines():
        key, _, value = line.partition(":")
        fields[key.strip()] = value.strip()
    return fields, body


def test_frontmatter_rules():
    fields, _ = _frontmatter(SKILL.read_text(encoding="utf-8"))
    assert fields["name"] == "local-model-desk" == SKILL.parent.name
    assert 0 < len(fields["description"]) <= 1024
    for word in ("本地模型", "台面", "本地生图"):
        assert word in fields["description"]


def test_body_covers_every_exit_code_and_resume():
    _, body = _frontmatter(SKILL.read_text(encoding="utf-8"))
    for needle in ("~/.local/bin/lmdesk", "lmdesk image wait", "--no-wait", "--force", "--from", "--out",
                   "image sessions", "退出码 3", "退出码 4", "退出码 5", "退出码 6", "不要重新 gen"):
        assert needle in body, needle


def test_dev_entry_script_runs_help():
    script = ROOT / "scripts" / "lmdesk"
    assert os.access(script, os.X_OK)
    r = subprocess.run([str(script), "--help"], capture_output=True, text=True, timeout=30)
    assert r.returncode == 0 and "lmdesk" in r.stdout
