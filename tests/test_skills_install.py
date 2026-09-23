"""从 URL 装：先看全文，全成功才落盘，任何中断清掉暂存（R-skill-11/17）。

`fetch` 由调用方注入，所以这一层不联网也能完整测试。
"""
import shutil
from pathlib import Path

import pytest

from desk.skills.install import InstallError, discard, land, stage_from_url
from desk.skills.parse import split_skill

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


def test_the_previewed_body_matches_the_bytes_landed_on_disk(tmp_path):
    """预览看到的正文，和真正落盘之后能读到的正文，必须逐字节一致——这条防线一旦被
    大小写、规范化或顺序问题绕过，用户批准的文本和实际生效的文本就不是同一份了
    （2026-09-23 修复轮 1 finding 1：防的是这一类问题，不只是这一次攻击）。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged = stage_from_url("https://example.com/x", staging, fetch_ok)
    previewed_body = staged["body"]
    land(staged["staging_id"], staging, user)
    landed_text = (user / "fetched" / "SKILL.md").read_text(encoding="utf-8")
    _, landed_body, error = split_skill(landed_text)
    assert error is None
    assert landed_body == previewed_body


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


def test_landing_is_all_or_nothing(tmp_path, monkeypatch):
    """落盘中途失败不许留下半个目录——它会被扫描发现、列成坏 skill，而用户没同意装它。

    用 monkeypatch 让 `shutil.copytree` 本身失败：这是唯一能可靠触发「拷贝中途失败」
    的办法——旧版本靠「目标被一个普通文件占着」触发失败，但重装现在会先把占位的东西
    挪开再拷贝（finding 2），占位文件不再能拦住安装，所以不能再靠它来制造失败。
    """
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged = stage_from_url("https://example.com/x", staging, fetch_ok)

    def boom(*_a, **_kw):
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copytree", boom)
    with pytest.raises(InstallError):
        land(staged["staging_id"], staging, user)
    assert not (user / "fetched").exists(), "半个目录会被扫描器发现、列成用户没同意装的坏 skill"
    assert list(staging.glob("*")) == []


def test_land_re_validates_the_staged_skill_md(tmp_path):
    """暂存之后、确认落盘之前，暂存里的 SKILL.md 被改坏了——land 自己要再读一遍，
    不能假设预览之后暂存没被动过（2026-09-23 修复轮 1 finding 3）。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged = stage_from_url("https://example.com/x", staging, fetch_ok)
    (staging / staged["staging_id"] / "SKILL.md").write_text("没有 frontmatter 了", encoding="utf-8")
    with pytest.raises(InstallError):
        land(staged["staging_id"], staging, user)
    assert list(staging.glob("*")) == []


def test_reinstalling_replaces_rather_than_merges_the_old_files(tmp_path):
    """重装是整体替换，不是合并：新版本不再提供的旧附件必须消失，落的是刚看过的那份，
    不是新旧文件的并集（2026-09-23 修复轮 1 finding 2）。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    old_files = {"SKILL.md": "---\nname: fetched\ndescription: v1\n---\n\n第一版\n",
                 "OLD_ATTACHMENT.md": "旧附件"}
    new_files = {"SKILL.md": "---\nname: fetched\ndescription: v2\n---\n\n第二版\n",
                 "NEW_ATTACHMENT.md": "新附件"}

    staged1 = stage_from_url("https://example.com/x", staging, lambda _u: dict(old_files))
    land(staged1["staging_id"], staging, user)
    assert sorted(p.name for p in (user / "fetched").iterdir()) == ["OLD_ATTACHMENT.md", "SKILL.md"]

    staged2 = stage_from_url("https://example.com/x", staging, lambda _u: dict(new_files))
    land(staged2["staging_id"], staging, user)

    landed = sorted(p.name for p in (user / "fetched").iterdir())
    assert landed == ["NEW_ATTACHMENT.md", "SKILL.md"], "重装留下了旧版本已经不再提供的文件"
    assert "第二版" in (user / "fetched" / "SKILL.md").read_text(encoding="utf-8")
    # 挪开的旧版本不能留下痕迹——不只是不可见（点开头），是真的被清掉了。
    assert sorted(p.name for p in user.iterdir()) == ["fetched"]


def test_a_failed_reinstall_leaves_the_previous_version_intact(tmp_path, monkeypatch):
    """重装失败不能让用户连能用的旧版本都丢了——落盘中途失败，旧版本原样换回来
    （2026-09-23 修复轮 1 finding 2）。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged1 = stage_from_url("https://example.com/x", staging, fetch_ok)
    land(staged1["staging_id"], staging, user)
    original = (user / "fetched" / "SKILL.md").read_text(encoding="utf-8")

    staged2 = stage_from_url(
        "https://example.com/x", staging,
        lambda _u: {"SKILL.md": "---\nname: fetched\ndescription: v2\n---\n\n第二版\n"})

    def boom(*_a, **_kw):
        raise OSError("disk full")

    monkeypatch.setattr(shutil, "copytree", boom)
    with pytest.raises(InstallError):
        land(staged2["staging_id"], staging, user)

    assert (user / "fetched" / "SKILL.md").read_text(encoding="utf-8") == original, \
        "重装失败，用户丢了原本能用的旧版本"
    assert list(staging.glob("*")) == []
    assert sorted(p.name for p in user.iterdir()) == ["fetched"], "挪开的旧版本副本没清干净"
