"""A-50..A-55: link states and apply, all inside a temporary HOME."""
import os
from pathlib import Path

import pytest

from desk.agent_skill import installer
from desk.agent_skill.targets import TARGETS


@pytest.fixture
def env(tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    res = tmp_path / "A.app" / "Contents" / "Resources"
    skill = res / "desk" / "agent_skill" / "bundled" / "local-model-desk"
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text("---\nname: local-model-desk\n---\n")
    cli = res / "bin" / "lmdesk"
    cli.parent.mkdir(parents=True)
    cli.write_text("#!/bin/sh\n")
    other = tmp_path / "B.app" / "Contents" / "Resources" / "desk" / "agent_skill" / "bundled" / "local-model-desk"
    other.mkdir(parents=True)
    return home, skill, cli, other


def _row(result, key):
    return next(r for r in result["targets"] if r["key"] == key)


def test_fresh_home_everything_absent(env):
    home, skill, cli, _ = env
    s = installer.status(home, skill, cli, which=lambda _c: None)
    assert [r["key"] for r in s["targets"]] == ["claude", "codex", "pi", "dsh"]
    assert all(r["state"] == "absent" for r in s["targets"]) and s["cli"]["state"] == "absent"


def test_apply_installs_only_selected_and_cli_follows(env):
    home, skill, cli, _ = env
    r = installer.apply(home, skill, cli, {"claude", "pi"}, which=lambda _c: None)
    assert _row(r, "claude")["state"] == "installed" and _row(r, "pi")["state"] == "installed"
    assert _row(r, "codex")["state"] == "absent" and _row(r, "dsh")["state"] == "absent"
    assert os.readlink(home / ".claude/skills/local-model-desk") == str(skill)
    assert (home / ".pi/agent/skills/local-model-desk").is_symlink()
    assert r["cli"]["state"] == "installed" and os.readlink(home / ".local/bin/lmdesk") == str(cli)
    r2 = installer.apply(home, skill, cli, set(), which=lambda _c: None)
    assert all(row["state"] == "absent" for row in r2["targets"]) and r2["cli"]["state"] == "absent"


def test_stale_link_to_other_app_is_detected_and_replaced(env):
    home, skill, cli, other = env
    link = home / ".claude/skills/local-model-desk"
    link.parent.mkdir(parents=True)
    link.symlink_to(other)
    assert _row(installer.status(home, skill, cli), "claude")["state"] == "stale"
    assert installer.any_stale(home, skill, cli) is True
    installer.apply(home, skill, cli, {"claude"})
    assert os.readlink(link) == str(skill)


def test_dangling_link_with_our_suffix_is_stale(env):
    home, skill, cli, _ = env
    link = home / ".dsh/skills/local-model-desk"
    link.parent.mkdir(parents=True)
    link.symlink_to(Path("/nonexistent/x/desk/agent_skill/bundled/local-model-desk"))
    assert _row(installer.status(home, skill, cli), "dsh")["state"] == "stale"


def test_occupied_by_real_dir_is_untouched_and_others_proceed(env):
    home, skill, cli, _ = env
    real = home / ".claude/skills/local-model-desk"
    real.mkdir(parents=True)
    (real / "SKILL.md").write_text("mine")
    r = installer.apply(home, skill, cli, {"claude", "pi"})
    row = _row(r, "claude")
    assert row["state"] == "occupied" and row["result"] == "error"
    assert (real / "SKILL.md").read_text() == "mine"
    assert _row(r, "pi")["state"] == "installed"
    installer.apply(home, skill, cli, set())
    assert (real / "SKILL.md").read_text() == "mine"


def test_link_to_elsewhere_is_occupied_and_never_removed(env, tmp_path):
    home, skill, cli, _ = env
    elsewhere = tmp_path / "someone-else"
    elsewhere.mkdir()
    link = home / ".pi/agent/skills/local-model-desk"
    link.parent.mkdir(parents=True)
    link.symlink_to(elsewhere)
    assert _row(installer.status(home, skill, cli), "pi")["state"] == "occupied"
    installer.apply(home, skill, cli, set())
    assert link.is_symlink() and os.readlink(link) == str(elsewhere)


def test_cli_link_occupied_does_not_block_skill(env):
    home, skill, cli, _ = env
    (home / ".local/bin").mkdir(parents=True)
    (home / ".local/bin/lmdesk").write_text("other tool")
    r = installer.apply(home, skill, cli, {"claude"})
    assert _row(r, "claude")["state"] == "installed"
    assert r["cli"]["state"] == "occupied"
    assert (home / ".local/bin/lmdesk").read_text() == "other tool"


def test_skills_dir_that_is_itself_a_symlink_is_followed_not_replaced(env, tmp_path):
    home, skill, cli, _ = env
    synced = tmp_path / "synced-skills"
    synced.mkdir()
    (home / ".claude").mkdir()
    (home / ".claude/skills").symlink_to(synced)
    installer.apply(home, skill, cli, {"claude"})
    assert (home / ".claude/skills").is_symlink()
    assert (synced / "local-model-desk").is_symlink()


def test_unwritable_parent_is_error_row(env):
    home, skill, cli, _ = env
    (home / ".pi/agent").mkdir(parents=True)
    os.chmod(home / ".pi/agent", 0o500)
    try:
        r = installer.apply(home, skill, cli, {"pi"})
        row = _row(r, "pi")
        assert row["result"] == "error" and row["message"]
    finally:
        os.chmod(home / ".pi/agent", 0o700)


def test_detect_uses_commands_or_paths(env):
    home, skill, cli, _ = env
    (home / ".dsh").mkdir()
    s = installer.status(home, skill, cli, which=lambda c: "/x/codex" if c == "codex" else None)
    assert _row(s, "codex")["detected"] and _row(s, "dsh")["detected"]
    assert not _row(s, "pi")["detected"]


def test_targets_table_matches_spec():
    links = {t.key: str(t.link) for t in TARGETS}
    assert links["claude"] == ".claude/skills/local-model-desk"
    assert links["pi"] == ".pi/agent/skills/local-model-desk"
    assert links["dsh"] == ".dsh/skills/local-model-desk"
    assert links["codex"] in (".codex/skills/local-model-desk", ".agents/skills/local-model-desk")


def test_users_own_scripts_lmdesk_link_is_foreign(env, tmp_path):
    home, skill, cli, _ = env
    mine = tmp_path / "proj" / "scripts" / "lmdesk"
    mine.parent.mkdir(parents=True)
    mine.write_text("#!/bin/sh\n")
    link = home / ".local/bin/lmdesk"
    link.parent.mkdir(parents=True)
    link.symlink_to(mine)
    r = installer.apply(home, skill, cli, {"claude"})
    assert r["cli"]["state"] == "occupied" and os.readlink(link) == str(mine)
    installer.apply(home, skill, cli, set())
    assert link.is_symlink() and os.readlink(link) == str(mine)


def test_desk_repo_scripts_lmdesk_link_is_ours(env, tmp_path):
    home, skill, cli, _ = env
    repo = tmp_path / "repo"
    (repo / "desk" / "agent_cli").mkdir(parents=True)
    (repo / "scripts").mkdir()
    (repo / "scripts" / "lmdesk").write_text("#!/bin/sh\n")
    link = home / ".local/bin/lmdesk"
    link.parent.mkdir(parents=True)
    link.symlink_to(repo / "scripts" / "lmdesk")
    assert installer.status(home, skill, cli)["cli"]["state"] == "stale"


def test_dangling_stale_says_invalid_and_moved_says_old_location(env):
    home, skill, cli, other = env
    gone = home / ".dsh/skills/local-model-desk"
    gone.parent.mkdir(parents=True)
    gone.symlink_to("/nonexistent/x/desk/agent_skill/bundled/local-model-desk")
    moved = home / ".claude/skills/local-model-desk"
    moved.parent.mkdir(parents=True)
    moved.symlink_to(other)
    rows = {r["key"]: r for r in installer.status(home, skill, cli)["targets"]}
    assert rows["dsh"]["message"] == "已失效，点应用更新"
    assert rows["claude"]["message"] == "指向旧位置，点应用更新"
