"""从 URL 装：先看全文，全成功才落盘，任何中断清掉暂存（R-skill-11/17）。

`fetch` 由调用方注入，所以这一层不联网也能完整测试。
"""
import shutil
import threading
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


def test_every_previewed_file_matches_the_bytes_landed_on_disk(tmp_path):
    """预览看到的每一个文件——正文和每一份附件——落盘后都必须逐字节一致。防线原本
    只查了 SKILL.md 的正文（2026-09-23 修复轮 1 finding 1 的原始范围），但「用户批准
    的是什么，落地生效的就该是什么」这条不变量覆盖的是预览时给用户看过的一切，
    所以这里连附件都查，并且用一个非 ASCII 文件名的附件——Unicode 正是修复轮 2
    finding 1 发现的缺口所在（2026-09-23 修复轮 2：范围问法本身就问窄了，这里补全）。
    """
    staging, user = tmp_path / "staging", tmp_path / "user"
    files = {
        "SKILL.md": "---\nname: fetched\ndescription: 来自网上\n---\n\n正文 [附](café.md)\n",
        "café.md": "带重音符号文件名的附件正文",
    }
    staged = stage_from_url("https://example.com/x", staging, lambda _u: dict(files))
    previewed_body = staged["body"]
    previewed_attachments = list(staged["attachments"])
    assert previewed_attachments, "这个测试本身要求至少一个附件，不然没测到附件这一半"

    land(staged["staging_id"], staging, user)

    landed_text = (user / "fetched" / "SKILL.md").read_text(encoding="utf-8")
    _, landed_body, error = split_skill(landed_text)
    assert error is None
    assert landed_body == previewed_body

    for attachment_name in previewed_attachments:
        landed_path = user / "fetched" / attachment_name
        assert landed_path.is_file(), f"预览时列出的附件 {attachment_name} 落盘后找不到了"
        assert landed_path.read_text(encoding="utf-8") == files[attachment_name]


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


def test_a_name_collision_with_a_different_existing_skill_is_refused(tmp_path):
    """`Foo` 已经装了；现在装一个声明 name: foo 的不同仓库——文件系统认为路径相同
    （这台设备大小写不敏感），但两者不是同一个 skill。必须拒绝，不能因为路径撞了
    就把 Foo 悄悄换成 foo（2026-09-23 修复轮 2 finding 2：修复轮 1 的整体替换逻辑,
    靠 target.exists() 判断「是不是重装」，这个判断本身就是这个洞）。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged1 = stage_from_url(
        "https://example.com/x", staging,
        lambda _u: {"SKILL.md": "---\nname: Foo\ndescription: 第一个\n---\n\n第一个 skill 的正文\n"})
    land(staged1["staging_id"], staging, user)
    assert (user / "Foo" / "SKILL.md").is_file()

    staged2 = stage_from_url(
        "https://example.com/x", staging,
        lambda _u: {"SKILL.md": "---\nname: foo\ndescription: 第二个，不同的仓库\n---\n\n完全不同的正文\n"})
    with pytest.raises(InstallError):
        land(staged2["staging_id"], staging, user)

    # 原来的 Foo 必须原封不动：既没被删，也没被换成第二个仓库的内容。
    assert (user / "Foo" / "SKILL.md").is_file()
    assert "第一个" in (user / "Foo" / "SKILL.md").read_text(encoding="utf-8")
    assert list(staging.glob("*")) == []


def test_land_cleans_up_stale_incoming_and_replacing_directories_from_a_crash(tmp_path):
    """上一次崩溃（断电、被杀）留在两次改名之间，留下 .incoming-*/.replacing-*——
    下一次 land() 起步时 best-effort 清掉，不需要一个全局的扫描式 sweep
    （2026-09-23 修复轮 2 finding 3）。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    user.mkdir(parents=True)
    stale_incoming = user / ".incoming-deadbeef"
    stale_incoming.mkdir()
    (stale_incoming / "leftover.md").write_text("崩溃留下的半成品", encoding="utf-8")
    stale_replacing = user / ".replacing-deadbeef"
    stale_replacing.mkdir()
    (stale_replacing / "SKILL.md").write_text(
        "---\nname: fetched\ndescription: 崩溃前的旧版本\n---\n\n旧\n", encoding="utf-8")

    staged = stage_from_url("https://example.com/x", staging, fetch_ok)
    land(staged["staging_id"], staging, user)

    remaining = sorted(p.name for p in user.iterdir())
    assert remaining == ["fetched"], "崩溃留下的临时目录没被清掉"


def test_a_failed_final_swap_restores_the_previous_version(tmp_path, monkeypatch):
    """两次改名中的第二次（incoming → target）失败：必须把挪开的旧版本换回来，
    不能让用户丢了能用的版本——窗口收窄之后（finding 3）依然要保证 all-or-nothing。
    """
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged1 = stage_from_url("https://example.com/x", staging, fetch_ok)
    land(staged1["staging_id"], staging, user)
    original = (user / "fetched" / "SKILL.md").read_text(encoding="utf-8")

    staged2 = stage_from_url(
        "https://example.com/x", staging,
        lambda _u: {"SKILL.md": "---\nname: fetched\ndescription: v2\n---\n\n第二版\n"})

    original_rename = Path.rename

    def flaky_rename(self, target):
        if self.name.startswith(".incoming-"):
            raise OSError("disk full during final swap")
        return original_rename(self, target)

    monkeypatch.setattr(Path, "rename", flaky_rename)
    with pytest.raises(InstallError):
        land(staged2["staging_id"], staging, user)

    assert (user / "fetched" / "SKILL.md").read_text(encoding="utf-8") == original, \
        "第二次改名失败，用户丢了原本能用的旧版本"
    assert sorted(p.name for p in user.iterdir()) == ["fetched"], "残留的临时目录没清干净"
    assert list(staging.glob("*")) == []


def test_concurrent_land_calls_are_serialized_and_neither_destroys_the_other(tmp_path):
    """land() 整个函数都在一把进程级的锁里（2026-09-23 修复轮 3 finding 1）：并发装
    两个不同的 skill，两边都必须完整落地，谁也不会踩谁。用真正的线程加
    threading.Event 控制先后顺序，不靠 mock 猜时序——先卡住第一个 land() 在拷贝阶段，
    确认第二个 land() 真的被锁挡住、还没完成，再放行，验证两边最终都成功。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    original_copytree = shutil.copytree
    first_call_started = threading.Event()
    first_call_may_finish = threading.Event()
    gate_state = {"used": False}

    def gated_copytree(src, dst, *args, **kwargs):
        if not gate_state["used"]:
            gate_state["used"] = True
            first_call_started.set()
            assert first_call_may_finish.wait(timeout=5), "测试本身卡住了，没人来放行"
        return original_copytree(src, dst, *args, **kwargs)

    staged_a = stage_from_url(
        "https://example.com/x", staging,
        lambda _u: {"SKILL.md": "---\nname: alpha\ndescription: A\n---\n\nA 的正文\n"})
    staged_b = stage_from_url(
        "https://example.com/x", staging,
        lambda _u: {"SKILL.md": "---\nname: beta\ndescription: B\n---\n\nB 的正文\n"})

    results: dict[str, object] = {}

    def run(label: str, staging_id: str) -> None:
        try:
            results[label] = land(staging_id, staging, user)
        except Exception as exc:                       # noqa: BLE001 —— 测试要能捕获任何异常类型
            results[label] = exc

    shutil.copytree = gated_copytree
    try:
        thread_a = threading.Thread(target=run, args=("a", staged_a["staging_id"]))
        thread_a.start()
        assert first_call_started.wait(timeout=5), "第一个 land() 没能进入拷贝阶段"

        thread_b = threading.Thread(target=run, args=("b", staged_b["staging_id"]))
        thread_b.start()

        # 给 B 一点时间：如果锁真的挡住了它，它这时候还不该完成。
        thread_b.join(timeout=0.3)
        assert thread_b.is_alive(), "第二个 land() 不该在第一个还没放锁之前就完成"

        first_call_may_finish.set()
        thread_a.join(timeout=5)
        thread_b.join(timeout=5)
    finally:
        shutil.copytree = original_copytree

    assert results.get("a") == "alpha", results.get("a")
    assert results.get("b") == "beta", results.get("b")
    assert (user / "alpha" / "SKILL.md").is_file()
    assert (user / "beta" / "SKILL.md").is_file()
    assert list(staging.glob("*")) == []


def test_a_double_fault_during_reinstall_degrades_to_a_clean_install_error(tmp_path, monkeypatch):
    """最终改名失败、换回旧版本也失败——双重故障必须还是一个干净的 InstallError，
    不能让原始的 OSError 冒穿出去变成一次没处理的崩溃；报错要点名旧版本被留在了
    哪个目录，用户才能手动救回来（2026-09-23 修复轮 3 finding 2）。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    staged1 = stage_from_url("https://example.com/x", staging, fetch_ok)
    land(staged1["staging_id"], staging, user)

    staged2 = stage_from_url(
        "https://example.com/x", staging,
        lambda _u: {"SKILL.md": "---\nname: fetched\ndescription: v2\n---\n\n第二版\n"})

    original_rename = Path.rename

    def flaky_rename(self, target):
        # 最终改名（incoming -> target）和恢复改名（aside -> target）都失败；
        # target -> aside 那一步（把旧版本挪开）必须成功，不然根本走不到双重故障。
        if self.name.startswith(".incoming-") or self.name.startswith(".replacing-"):
            raise OSError("disk full during swap")
        return original_rename(self, target)

    monkeypatch.setattr(Path, "rename", flaky_rename)
    with pytest.raises(InstallError) as excinfo:
        land(staged2["staging_id"], staging, user)

    message = str(excinfo.value)
    assert "没能换回来" in message, "必须明说旧版本也没能恢复"

    leftover = [p for p in user.iterdir() if p.name.startswith(".replacing-")]
    assert len(leftover) == 1, "旧版本应该原样留在 .replacing-* 里，不多不少"
    assert leftover[0].name in message, "报错要点名旧版本被留在了哪个目录"
    assert (leftover[0] / "SKILL.md").read_text(encoding="utf-8") == SKILL, "旧版本内容不能被弄坏"
    assert list(staging.glob("*")) == []


def test_reinstalling_over_a_corrupted_target_gives_a_clear_message(tmp_path):
    """target 存在，但读不出里面的 SKILL.md——不能说「已经是另一个 skill（叫
    None）」，那自相矛盾：同名却说不是同一个 skill。要说清楚问题在哪（读不出来），
    让用户自己删了或者修好（2026-09-23 修复轮 3 finding 3）。"""
    staging, user = tmp_path / "staging", tmp_path / "user"
    user.mkdir(parents=True)
    (user / "fetched").mkdir()          # 故意不放 SKILL.md：_declared_name 读不出，返回 None

    staged = stage_from_url("https://example.com/x", staging, fetch_ok)
    with pytest.raises(InstallError) as excinfo:
        land(staged["staging_id"], staging, user)

    message = str(excinfo.value)
    assert "None" not in message, "不能把读不出来的状态说成一个叫 None 的 skill"
    assert "fetched" in message
    assert list(staging.glob("*")) == []
    assert (user / "fetched").is_dir(), "没读懂的目录也不能被动"
