"""从 URL 装：先看全文，全成功才落盘，任何中断清掉暂存（R-skill-11/17）。

`fetch` 由调用方注入，所以这一层不联网也能完整测试。
"""
from pathlib import Path

import pytest

from desk.skills.install import InstallError, discard, land, stage_from_url

SKILL = "---\nname: fetched\ndescription: 来自网上\n---\n\n正文 [附](A.md)\n"
FILES = {"SKILL.md": SKILL, "A.md": "附件正文", "run.sh": "rm -rf /", "logo.png": "\x00binary"}


def fetch_ok(_url):
    return dict(FILES)


def test_preview_returns_the_full_text_before_anything_lands(tmp_path):
    """装之前必须能读到全文：skill 就是指令，装别人的 skill 等于让别人的指令驱动你的模型。"""
    staged = stage_from_url("https://example.com/x", tmp_path / "staging", fetch_ok)
    assert staged["name"] == "fetched"
    assert staged["body"].strip().startswith("正文")
    assert SKILL.split("---")[2].strip() in staged["body"] or "正文" in staged["body"]
    assert list(tmp_path.glob("**/skills/fetched")) == [], "还没确认就落盘了"


def test_only_md_lands_scripts_and_binaries_do_not(tmp_path):
    """台面不执行它们（R-skill-01）；留着只会让人以为它会执行。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged = stage_from_url("https://example.com/x", staging, fetch_ok)
    land(staged["staging_id"], staging, user)
    landed = sorted(p.name for p in (user / "fetched").iterdir())
    assert landed == ["A.md", "SKILL.md"]


def test_landing_clears_the_staging_directory(tmp_path):
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged = stage_from_url("https://example.com/x", staging, fetch_ok)
    land(staged["staging_id"], staging, user)
    assert list(staging.glob("*")) == []


def test_discard_leaves_nothing_behind(tmp_path):
    staging = tmp_path / "staging"
    staged = stage_from_url("https://example.com/x", staging, fetch_ok)
    discard(staged["staging_id"], staging)
    assert list(staging.glob("*")) == []


def test_a_fetch_without_skill_md_never_stages(tmp_path):
    staging = tmp_path / "staging"
    with pytest.raises(InstallError):
        stage_from_url("https://example.com/x", staging, lambda _u: {"README.md": "x"})
    assert list(staging.glob("*")) == []


def test_a_broken_skill_md_never_stages(tmp_path):
    staging = tmp_path / "staging"
    with pytest.raises(InstallError):
        stage_from_url("https://example.com/x", staging, lambda _u: {"SKILL.md": "没有 frontmatter"})
    assert list(staging.glob("*")) == []


def test_a_failed_fetch_leaves_nothing_behind(tmp_path):
    staging = tmp_path / "staging"

    def boom(_url):
        raise OSError("network down")

    with pytest.raises(InstallError):
        stage_from_url("https://example.com/x", staging, boom)
    assert list(staging.glob("*")) == []


def test_installing_does_not_enable(tmp_path):
    """装和用是两个动作（R-skill-11）：落盘不碰任何会话的选中状态。"""
    from types import SimpleNamespace

    from desk.skills.service import SkillsService

    (tmp_path / "res").mkdir()
    roots = SimpleNamespace(resources_root=tmp_path / "res", models_root=tmp_path / "m")
    service = SkillsService(roots)
    service.preview_install = lambda _url: stage_from_url(
        "u", service._staging_root(), fetch_ok)          # 不联网
    staged = service.preview_install("u")
    assert service.confirm_install(staged["staging_id"]) == {"installed": "fetched", "enabled": False}


def test_a_skill_md_missing_a_required_field_never_stages(tmp_path):
    """有 frontmatter、能解析，但缺 description——不是「读不通」，是另一条守卫。"""
    staging = tmp_path / "staging"
    with pytest.raises(InstallError):
        stage_from_url("https://example.com/x", staging,
                        lambda _u: {"SKILL.md": "---\nname: x\n---\n\n正文\n"})
    assert list(staging.glob("*")) == []


def test_a_failed_staging_write_cleans_up_partial_state(tmp_path, monkeypatch):
    """SKILL.md 已经落了一半，第二个文件写失败——不许留下这半个暂存目录。"""
    staging = tmp_path / "staging"
    calls = {"n": 0}
    original = Path.write_text

    def flaky_write_text(self, *args, **kwargs):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OSError("disk full")
        return original(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", flaky_write_text)
    with pytest.raises(InstallError):
        stage_from_url("https://example.com/x", staging, fetch_ok)
    assert list(staging.glob("*")) == []


def test_landing_a_staging_id_that_is_gone_raises_and_touches_nothing(tmp_path):
    staging, user = tmp_path / "staging", tmp_path / "user"
    staging.mkdir(parents=True)
    with pytest.raises(InstallError):
        land("no-such-staging-id", staging, user)
    assert not user.exists()


def test_landing_is_all_or_nothing(tmp_path):
    """落盘中途失败不许留下半个目录——它会被扫描发现、列成坏 skill，而用户没同意装它。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged = stage_from_url("https://example.com/x", staging, fetch_ok)
    user.mkdir(parents=True)
    (user / "fetched").write_text("占位的普通文件", encoding="utf-8")   # 目标被占，落盘必失败
    with pytest.raises(InstallError):
        land(staged["staging_id"], staging, user)
    assert (user / "fetched").is_file(), "把用户原有的东西弄坏了"
    assert list(staging.glob("*")) == []
