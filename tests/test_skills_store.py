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


def test_a_missing_name_is_listed_with_its_reason(tmp_path):
    """缺 name 字段（镜像测试缺 description）——没有 name UI 无法指向这个坏 skill。"""
    d = (tmp_path / "user" / "noname")
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\ndescription: 有描述\n---\n正文\n", encoding="utf-8")
    [entry] = store(tmp_path).scan()
    assert entry["ok"] is False
    assert "name" in entry["error"]
    assert entry["name"] == "noname"


def test_directory_without_skill_md_exact_error_message(tmp_path):
    """测试精确错误消息，区分「文件不存在」和「文件不可读」。"""
    (tmp_path / "user" / "empty").mkdir(parents=True)
    [entry] = store(tmp_path).scan()
    assert entry["ok"] is False
    assert entry["error"] == "目录里没有 SKILL.md"


def test_invalid_utf8_in_skill_md(tmp_path):
    """SKILL.md 包含无效 UTF-8 应被列为坏的。"""
    d = (tmp_path / "user" / "badutf8")
    d.mkdir(parents=True)
    (d / "SKILL.md").write_bytes(b"---\nname: x\n---\n\xff\xfe")
    [entry] = store(tmp_path).scan()
    assert entry["ok"] is False
    assert "读不出" in entry["error"]


def test_invalid_utf8_in_attachment_is_skipped(tmp_path):
    """附件包含无效 UTF-8 应被跳过，不会让扫描崩溃。"""
    write_skill(tmp_path / "user", "badattach",
                body="见 [坏的](BAD.md)。")
    # 写入无效 UTF-8 到附件
    (tmp_path / "user" / "badattach" / "BAD.md").write_bytes(b"\xff\xfe")
    [entry] = store(tmp_path).scan()
    assert entry["ok"] is True
    assert entry["attachments"] == []


def test_same_root_collision_marks_all_as_broken(tmp_path):
    """同一个根内，两个目录声明同一个 name 时，两个都标记为坏的并列出对方。"""
    write_skill(tmp_path / "user", "dir-a", name="dup")
    write_skill(tmp_path / "user", "dir-b", name="dup")
    entries = store(tmp_path).scan()
    assert len(entries) == 2
    assert all(e["ok"] is False for e in entries)
    assert all("重复" in e["error"] for e in entries)
    # 检查 dir-a 的错误提到了 dir-b
    dir_a = [e for e in entries if e["dir"].endswith("dir-a")][0]
    assert "dir-b" in dir_a["error"]
    # 检查 dir-b 的错误提到了 dir-a
    dir_b = [e for e in entries if e["dir"].endswith("dir-b")][0]
    assert "dir-a" in dir_b["error"]


def test_user_broken_entry_overrides_bundled(tmp_path):
    """用户的坏 skill 仍然覆盖自带版本（因为用户已经在编辑它）。"""
    write_skill(tmp_path / "bundled", "shared", body="自带正文")
    # 用户版本缺少 description
    d = (tmp_path / "user" / "shared")
    d.mkdir(parents=True)
    (d / "SKILL.md").write_text("---\nname: shared\n---\n用户正文\n", encoding="utf-8")
    [entry] = store(tmp_path).scan()
    assert entry["source"] == "user"
    assert entry["ok"] is False
    assert entry["overrides_bundled"] is True
    assert "description" in entry["error"]
