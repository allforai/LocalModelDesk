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
    try:
        files = fetch(url)
    except Exception as exc:                      # 网络、解析、任何失败都不留痕
        _clear(staged)
        raise InstallError(f"取不下来：{exc}") from exc
    if not isinstance(files, dict) or "SKILL.md" not in files:
        _clear(staged)
        raise InstallError("这个地址里没有 SKILL.md")
    fields, body, error = split_skill(files["SKILL.md"])
    if error:
        _clear(staged)
        raise InstallError(f"SKILL.md 读不通：{error}")
    for required in ("name", "description"):
        if not (fields.get(required) or "").strip():
            _clear(staged)
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
    fields, _body, error = split_skill((staged / "SKILL.md").read_text(encoding="utf-8"))
    if error:
        _clear(staged)
        raise InstallError(error)
    name = fields["name"].strip()
    target = Path(user_root) / name
    try:
        Path(user_root).mkdir(parents=True, exist_ok=True)
        if target.exists() and not target.is_dir():
            raise OSError(f"{target} 已经存在且不是目录")
        shutil.copytree(staged, target, dirs_exist_ok=True)
    except OSError as exc:
        _clear(staged)
        raise InstallError(f"落盘失败：{exc}") from exc
    _clear(staged)
    return name


def discard(staging_id: str, staging_root: Path) -> None:
    _clear(Path(staging_root) / staging_id)
