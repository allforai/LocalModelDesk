"""从 URL 装一个 skill：先看全文，全成功才落盘，任何中断清掉暂存（R-skill-11/17）。

`fetch` 注入进来，所以这一层不联网也能完整测试；生产里由 service 传入真正的抓取实现。

只落 `SKILL.md` 与 `.md` 附件：台面不执行脚本与二进制（R-skill-01），把它们留在磁盘上
只会让人以为它会执行。

`<models_root>/skills/` 下不允许出现「装了一半」的目录：它会被扫描发现、被列成坏 skill，
而用户根本没同意装它。
"""
from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from .parse import split_skill


class InstallError(Exception):
    pass


def _clear(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def stage_from_url(url: str, staging_root: Path, fetch) -> dict:
    staging_root = Path(staging_root)
    staging_id = uuid.uuid4().hex
    staged = staging_root / staging_id
    # 下面四个早退都发生在 staged.mkdir() 之前：这个目录还没被创建，没有什么可清的——
    # 清一个不存在的路径是静默的空操作，写成看起来在清理只会让后来的人以为这里有清理
    # 逻辑（2026-09-23 修复轮 1 finding 4）。真正需要清理的是下面写暂存那段。
    try:
        files = fetch(url)
    except Exception as exc:                      # 网络、解析、任何失败都不留痕
        raise InstallError(f"取不下来：{exc}") from exc
    if not isinstance(files, dict) or "SKILL.md" not in files:
        raise InstallError("这个地址里没有 SKILL.md")
    fields, body, error = split_skill(files["SKILL.md"])
    if error:
        raise InstallError(f"SKILL.md 读不通：{error}")
    for required in ("name", "description"):
        if not (fields.get(required) or "").strip():
            raise InstallError(f"frontmatter 缺 {required}")

    try:
        staged.mkdir(parents=True, exist_ok=True)
        for filename, text in files.items():
            if not filename.endswith(".md") or "/" in filename or "\\" in filename:
                continue                          # 脚本、二进制、子目录一律不落
            (staged / filename).write_text(text, encoding="utf-8")
    except OSError as exc:
        _clear(staged)
        raise InstallError(f"写暂存失败：{exc}") from exc

    return {"staging_id": staging_id, "name": fields["name"].strip(),
            "description": fields["description"].strip(), "body": body,
            "attachments": sorted(p.name for p in staged.iterdir() if p.name != "SKILL.md")}


def _declared_name(skill_md: Path) -> str | None:
    """读一个已经落盘的 SKILL.md，返回它 frontmatter 里声明的 name；读不出、解析不出
    就返回 None——调用方把 None 当成「不能确认是同一个 skill」处理。"""
    if not skill_md.is_file():
        return None
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    fields, _body, error = split_skill(text)
    if error or not fields:
        return None
    return (fields.get("name") or "").strip()


def land(staging_id: str, staging_root: Path, user_root: Path) -> str:
    staged = Path(staging_root) / staging_id
    if not (staged / "SKILL.md").is_file():
        raise InstallError("暂存已经不在了，请重新预览")
    # 落盘前再读一遍暂存的 SKILL.md，不能假设预览之后它没被动过
    # （2026-09-23 修复轮 1 finding 3）。
    fields, _body, error = split_skill((staged / "SKILL.md").read_text(encoding="utf-8"))
    if error:
        _clear(staged)
        raise InstallError(error)
    name = fields["name"].strip()
    user_root = Path(user_root)
    target = user_root / name

    try:
        user_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        _clear(staged)
        raise InstallError(f"落盘失败：{exc}") from exc

    # 起步先清掉上一次崩溃（断电、被杀）留下的痕迹：崩溃窗口只可能落在下面两次改名
    # 之间，留下的只会是 .incoming-*/.replacing-* 这两类点开头的目录。只清这两类前缀，
    # 不做全局扫描式的 sweep——那会有清到正在进行中的操作的风险
    # （2026-09-23 修复轮 2 finding 3）。
    for stale in user_root.glob(".incoming-*"):
        _clear(stale)
    for stale in user_root.glob(".replacing-*"):
        _clear(stale)

    # 「路径撞了」不等于「是同一个 skill」：这台设备的文件系统既不区分大小写、也不做
    # Unicode 规范化，`Foo` 和 `foo`、NFC 的 `café` 和 NFD 的 `café` 都会落在同一个路径。
    # 只有已存在的目录声明的 name 和这次要装的 name 完全一样，才当成「重装同一个
    # skill」去替换；否则拒绝，绝不能把用户认识的另一个 skill 悄悄换掉——桌面猜不出
    # 用户想要哪个，猜错了不可挽回（2026-09-23 修复轮 2 finding 2，是修复轮 1
    # 引入的整体替换逻辑本身造出来的洞）。
    if target.exists():
        existing_name = _declared_name(target / "SKILL.md")
        if existing_name != name:
            _clear(staged)
            raise InstallError(
                f"{target.name!r} 已经是另一个 skill（叫 {existing_name!r}），这次装的是 "
                f"{name!r}：文件系统认为路径相同，但不是同一个 skill——先给其中一个改名再装")

    # 新版本先整个拷到一个点开头的临时目录——这一步最耗时，但 target 此刻完全没被动过，
    # 拷贝失败也好、进程被杀也好，target 都还是原样。真正有风险的窗口收窄成下面两次
    # 改名之间那一小段，而不是整个拷贝的时长（2026-09-23 修复轮 2 finding 3，
    # 取代修复轮 1「先挪旧的、再拷新的」的顺序）。
    incoming = user_root / f".incoming-{uuid.uuid4().hex}"
    try:
        shutil.copytree(staged, incoming)
    except OSError as exc:
        _clear(incoming)
        _clear(staged)
        raise InstallError(f"落盘失败：{exc}") from exc

    aside = None
    if target.exists():
        aside = user_root / f".replacing-{uuid.uuid4().hex}"
        try:
            target.rename(aside)
        except OSError as exc:
            # 挪都没挪成功：目标还是原来那份，新版本的临时拷贝清掉，只清暂存。
            _clear(incoming)
            _clear(staged)
            raise InstallError(f"落盘失败：{exc}") from exc

    try:
        incoming.rename(target)
    except OSError as exc:
        if aside is not None:
            aside.rename(target)        # 换回旧版本：重装失败不能让用户连能用的版本都丢了
        _clear(incoming)
        _clear(staged)
        raise InstallError(f"落盘失败：{exc}") from exc

    if aside is not None:
        _clear(aside)
    _clear(staged)
    return name


def discard(staging_id: str, staging_root: Path) -> None:
    _clear(Path(staging_root) / staging_id)
