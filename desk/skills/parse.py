"""SKILL.md 的解析：frontmatter 与同目录 `.md` 链接。零 IO，可穷举测试。

**不许 import yaml。** 打包进 app 的 Python 没有它（2026-09-23 实测），照着开发机写
会在测试里全绿、装进 app 就崩。frontmatter 实际只用到 `key: value` 与 `key: >` 折叠块
这两种写法（核对过 ~/.claude/plugins/cache/ 与 ~/.pi/agent/skills/），解析这个子集即可。

看不懂的行报错而不是跳过：跳过会让 skill 带着残缺字段照常上场，而 R-skill-08 要求
坏掉的东西列出来并写明原因。
"""
from __future__ import annotations

import re

_FENCE = "---"
_KEY_VALUE = re.compile(r"^([A-Za-z_][A-Za-z0-9_-]*):\s*(.*)$")
_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def parse_frontmatter(text: str) -> tuple[dict | None, str | None]:
    lines = (text or "").splitlines()
    if not lines or lines[0].strip() != _FENCE:
        return None, "缺少 frontmatter：第一行必须是 ---"
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].strip() == _FENCE)
    except StopIteration:
        return None, "frontmatter 没有结束的 --- 行"

    fields: dict[str, str] = {}
    pending_key: str | None = None
    folded: list[str] = []
    for raw in lines[1:end]:
        if pending_key is not None and (raw.startswith((" ", "\t")) or not raw.strip()):
            if raw.strip():
                folded.append(raw.strip())
            continue
        if pending_key is not None:
            fields[pending_key] = " ".join(folded)
            pending_key, folded = None, []
        if not raw.strip():
            continue
        match = _KEY_VALUE.match(raw)
        if not match:
            return None, f"看不懂这一行：{raw.strip()}"
        key, value = match.group(1), match.group(2).strip()
        if value in (">", "|", ">-", "|-"):
            pending_key = key
            continue
        fields[key] = _unquote(value)
    if pending_key is not None:
        fields[pending_key] = " ".join(folded)
    return fields, None


def split_skill(text: str) -> tuple[dict | None, str, str | None]:
    """(字段, 去掉 frontmatter 的正文, 错误)。"""
    fields, error = parse_frontmatter(text)
    if error:
        return None, text or "", error
    lines = (text or "").splitlines()
    end = next(i for i in range(1, len(lines)) if lines[i].strip() == _FENCE)
    return fields, "\n".join(lines[end + 1:]).lstrip("\n"), None


def referenced_files(body: str) -> list[str]:
    """正文里指向**同目录下 `.md`** 的链接目标，去重且保持出现顺序。

    目录外的路径、URL、非 `.md` 一律不算——台面不跟出这个目录（R-skill-10）。
    """
    found: list[str] = []
    for target in _LINK.findall(body or ""):
        # 去掉开头的 ./ 才能用斜杠检查：./ 的目标是同目录文件（测试要求接受），
        # 但 ./../x.md 仍会被不变的斜杠检查拒绝
        if target.startswith("./"):
            target = target[2:]

        if "/" in target or "\\" in target or ":" in target:
            continue                      # 子目录、上级、URL 一律不算
        if not target.endswith(".md") or target in found:
            continue
        found.append(target)
    return found
