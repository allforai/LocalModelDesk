"""A-57: uninstall-app.sh removes only our agent links, honours --dry-run."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _run(home, *args):
    env = {**os.environ, "HOME": str(home)}
    return subprocess.run([str(ROOT / "scripts" / "uninstall-app.sh"), "--app-path", str(home / "nope.app"),
                           "--data-root", str(home / "data"), "--launch-agents-dir", str(home / "LA"), *args],
                          capture_output=True, text=True, env=env, timeout=60)


def _setup(tmp_path):
    home = tmp_path / "home"
    ours = home / ".claude/skills/local-model-desk"
    ours.parent.mkdir(parents=True)
    ours.symlink_to("/x/LocalModelDesk.app/Contents/Resources/desk/agent_skill/bundled/local-model-desk")
    cli = home / ".local/bin/lmdesk"
    cli.parent.mkdir(parents=True)
    cli.symlink_to("/x/LocalModelDesk.app/Contents/Resources/bin/lmdesk")
    theirs = home / ".pi/agent/skills/local-model-desk"
    theirs.mkdir(parents=True)
    (theirs / "SKILL.md").write_text("someone else")
    other_link = home / ".dsh/skills/local-model-desk"
    other_link.parent.mkdir(parents=True)
    other_link.symlink_to(tmp_path)
    return home, ours, cli, theirs, other_link


def test_dry_run_reports_and_keeps(tmp_path):
    home, ours, cli, *_ = _setup(tmp_path)
    r = _run(home, "--dry-run")
    assert str(ours) in r.stdout and str(cli) in r.stdout
    assert ours.is_symlink() and cli.is_symlink()


def test_removes_only_our_links(tmp_path):
    home, ours, cli, theirs, other_link = _setup(tmp_path)
    _run(home)
    assert not ours.is_symlink() and not cli.is_symlink()
    assert (theirs / "SKILL.md").read_text() == "someone else"
    assert other_link.is_symlink()


def test_users_own_scripts_lmdesk_link_survives(tmp_path):
    home = tmp_path / "home"
    mine = tmp_path / "proj" / "scripts" / "lmdesk"
    mine.parent.mkdir(parents=True)
    mine.write_text("x")
    link = home / ".local/bin/lmdesk"
    link.parent.mkdir(parents=True)
    link.symlink_to(mine)
    _run(home)
    assert link.is_symlink()
