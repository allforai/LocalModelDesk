"""扫描：两个根、用户覆盖自带、坏的照样列出并写明原因（R-skill-07/08/16）。"""
from pathlib import Path

from desk.skills.store import SkillStore

GOOD = """---
name: {name}
description: {desc}
---

{body}
"""


def write_skill(root: Path, dirname: str, *, name=None, desc="描述", body="正文", extra=None):
    d = root / dirname
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        GOOD.format(name=name or dirname, desc=desc, body=body), encoding="utf-8")
    for filename, text in (extra or {}).items():
        (d / filename).write_text(text, encoding="utf-8")
    return d


def store(tmp_path):
    return SkillStore(tmp_path / "bundled", tmp_path / "user")


def test_lists_both_roots_and_tags_the_source(tmp_path):
    write_skill(tmp_path / "bundled", "shipped")
    write_skill(tmp_path / "user", "mine")
    got = {s["name"]: s["source"] for s in store(tmp_path).scan()}
    assert got == {"shipped": "bundled", "mine": "user"}


def test_the_user_copy_wins_and_says_so(tmp_path):
    """同名覆盖必须看得见——静默覆盖会让人以为自带的那份还在生效。"""
    write_skill(tmp_path / "bundled", "review", body="自带正文")
    write_skill(tmp_path / "user", "review", body="我的正文")
    [entry] = store(tmp_path).scan()
    assert entry["source"] == "user"
    assert entry["overrides_bundled"] is True
    assert "我的正文" in entry["body"]


def test_a_skill_with_no_bundled_twin_is_not_marked_as_overriding(tmp_path):
    write_skill(tmp_path / "user", "mine")
    [entry] = store(tmp_path).scan()
    assert entry["overrides_bundled"] is False


def test_a_missing_description_is_listed_with_its_reason(tmp_path):
    """坏的不能消失：消失是最难查的故障。"""
    d = (tmp_path / "user" / "broken")
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: broken\n---\n正文\n", encoding="utf-8")
    [entry] = store(tmp_path).scan()
    assert entry["ok"] is False
    assert "description" in entry["error"]
    assert entry["name"] == "broken"


def test_a_directory_without_skill_md_is_listed_as_broken(tmp_path):
    (tmp_path / "user" / "empty").mkdir(parents=True)
    [entry] = store(tmp_path).scan()
    assert entry["ok"] is False
    assert "SKILL.md" in entry["error"]


def test_attachments_are_listed_with_their_sizes_but_not_inlined(tmp_path):
    """附件只登记不拼接——拼不拼由用户勾选决定（R-skill-10）。"""
    write_skill(tmp_path / "user", "deep",
                body="见 [深化](DEEPENING.md)。",
                extra={"DEEPENING.md": "附件正文"})
    [entry] = store(tmp_path).scan()
    assert entry["attachments"] == [
        {"file": "DEEPENING.md", "chars": len("附件正文"), "text": "附件正文"}]
    assert "附件正文" not in entry["body"], "附件被拼进正文了——拼不拼由用户勾选决定"


def test_a_referenced_file_that_does_not_exist_is_not_listed(tmp_path):
    """引用了但文件不在，就不该出现在可勾选清单里——勾了也拼不出东西。"""
    write_skill(tmp_path / "user", "dangling", body="见 [缺失](GONE.md)。")
    [entry] = store(tmp_path).scan()
    assert entry["attachments"] == []


def test_a_dot_directory_is_not_a_skill(tmp_path):
    """安装用的 .staging 就住在这个目录下（Task 9）。不跳过的话它会被列成一个坏 skill，
    而用户根本没在装任何东西。台面在会话存档上踩过同形的坑——glob("*.json") 当年
    把临时文件也扫了进去。"""
    (tmp_path / "user" / ".staging" / "abc").mkdir(parents=True)
    write_skill(tmp_path / "user", "real")
    assert [e["name"] for e in store(tmp_path).scan()] == ["real"]


def test_missing_roots_are_not_an_error(tmp_path):
    assert store(tmp_path).scan() == []


def test_chars_counts_the_body_only(tmp_path):
    write_skill(tmp_path / "user", "size", body="1234567890")
    [entry] = store(tmp_path).scan()
    assert entry["chars"] == len(entry["body"])
    assert entry["chars"] >= 10
