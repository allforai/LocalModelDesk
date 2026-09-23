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

    # 重装是整体替换，不是合并（R-skill-11/17）：旧版本先挪到一个点开头的名字——
    # 扫描器跳过点开头目录，换的中途不会被当成一个 skill 列出来——新版本落地成功之后
    # 才删掉旧的。落的必须是刚看过的那一份，不能是「新旧文件的并集」
    # （2026-09-23 修复轮 1 finding 2，替代原先 dirs_exist_ok=True 的合并写法）。
    moved_aside = None
    if target.exists():
        moved_aside = user_root / f".replacing-{uuid.uuid4().hex}"
        try:
            target.rename(moved_aside)
        except OSError as exc:
            # 挪都没挪成功：目标还是原来那份，什么都不用恢复，只清暂存。
            _clear(staged)
            raise InstallError(f"落盘失败：{exc}") from exc

    try:
        shutil.copytree(staged, target)
    except OSError as exc:
        _clear(target)                      # 不管是全新安装半途而废，还是替换阶段失败，
                                             # 目标都不许留半个（target 此刻要么本就不存在
                                             # 要么是这次失败的拷贝留下的残迹，清了安全）
        if moved_aside is not None:
            moved_aside.rename(target)      # 换回旧版本：重装失败不能让用户连能用的版本都丢了
        _clear(staged)
        raise InstallError(f"落盘失败：{exc}") from exc

    if moved_aside is not None:
        _clear(moved_aside)
    _clear(staged)
    return name


def discard(staging_id: str, staging_root: Path) -> None:
    _clear(Path(staging_root) / staging_id)
