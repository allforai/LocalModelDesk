"""扫描两个根，产出**唯一一份**已解析列表（R-skill-16）。

注入、计数、界面显示都只读这份列表，不得再判定一次来源与覆盖。同一个问题有两个入口时
答案迟早分叉，而先被问到的那个说了算——这个代价台面已经付过（R-budget-18）。
"""
from __future__ import annotations

from pathlib import Path

from .parse import referenced_files, split_skill


def _broken(directory: Path, source: str, reason: str) -> dict:
    return {"name": directory.name, "description": "", "source": source,
            "overrides_bundled": False, "body": "", "chars": 0, "attachments": [],
            "ok": False, "error": reason, "dir": str(directory)}


def _read_one(directory: Path, source: str) -> dict:
    skill_md = directory / "SKILL.md"
    if not skill_md.is_file():
        return _broken(directory, source, "目录里没有 SKILL.md")
    try:
        text = skill_md.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return _broken(directory, source, f"读不出 SKILL.md：{exc}")
    fields, body, error = split_skill(text)
    if error:
        return _broken(directory, source, error)
    for required in ("name", "description"):
        if not (fields.get(required) or "").strip():
            return _broken(directory, source, f"frontmatter 缺 {required}")

    attachments = []
    for filename in referenced_files(body):
        path = directory / filename
        if not path.is_file():
            continue          # 引用了但文件不在：勾了也拼不出东西，不进可勾选清单
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        # 原文随列表一起给出：勾选时前端直接拼，不必再问一次。
        # 「同一个问题只许有一个入口」（R-skill-16）——再开一个取附件的接口，
        # 两边迟早对不上，而先被问到的那个说了算。
        attachments.append({"file": filename, "chars": len(text), "text": text})
    return {"name": fields["name"].strip(), "description": fields["description"].strip(),
            "source": source, "overrides_bundled": False, "body": body, "chars": len(body),
            "attachments": attachments, "ok": True, "error": None, "dir": str(directory)}


class SkillStore:
    def __init__(self, bundled_root: Path, user_root: Path):
        self._bundled = Path(bundled_root)
        self._user = Path(user_root)

    def _scan_root(self, root: Path, source: str) -> list[dict]:
        if not root.is_dir():
            return []
        # 跳过点开头的目录：安装用的 .staging 就住在用户根下（R-skill-17），
        # 不跳过它会被列成一个用户从没同意装的坏 skill。
        return [_read_one(d, source) for d in sorted(root.iterdir())
                if d.is_dir() and not d.name.startswith(".")]

    def scan(self) -> list[dict]:
        bundled = {e["name"]: e for e in self._scan_root(self._bundled, "bundled")}
        merged = dict(bundled)
        for entry in self._scan_root(self._user, "user"):
            entry["overrides_bundled"] = entry["name"] in bundled
            merged[entry["name"]] = entry
        return sorted(merged.values(), key=lambda e: e["name"])
