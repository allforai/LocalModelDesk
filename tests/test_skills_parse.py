"""frontmatter 与链接提取：只用标准库，且只认我们真的懂的那部分语法。

打包进 app 的 Python 没有 yaml（2026-09-23 实测），所以这里不能 import yaml——
那会在开发机上全绿、装进 app 就崩。
"""
from desk.skills.parse import parse_frontmatter, referenced_files, split_skill

CLAUDE_STYLE = """---
name: code-review
description: Review a diff for correctness.
---

# Code Review

正文第一段。
"""

PI_STYLE = """---
name: meta-skill
description: >
  第一行描述。
  第二行描述。
version: "0.20.1"
---

正文。
"""


def test_parses_a_single_line_description():
    fields, error = parse_frontmatter(CLAUDE_STYLE)
    assert error is None
    assert fields["name"] == "code-review"
    assert fields["description"] == "Review a diff for correctness."


def test_parses_a_folded_block_description():
    """Pi 的 skill 用 `description: >` 折叠多行——两个生态的写法都得认。"""
    fields, error = parse_frontmatter(PI_STYLE)
    assert error is None
    assert fields["description"] == "第一行描述。 第二行描述。"
    assert fields["version"] == "0.20.1"


def test_missing_frontmatter_is_an_error_not_an_empty_dict():
    """没有 frontmatter 不能悄悄当成「字段都空」——那会变成一个没有名字的 skill。"""
    fields, error = parse_frontmatter("# 只有正文\n")
    assert fields is None
    assert "frontmatter" in error


def test_unterminated_frontmatter_is_an_error():
    fields, error = parse_frontmatter("---\nname: x\n没有结束线\n")
    assert fields is None
    assert error


def test_a_line_we_do_not_understand_is_an_error_not_silently_dropped():
    """看不懂的语法要报错，不能跳过：跳过会让 skill 带着残缺的字段照常上场。"""
    fields, error = parse_frontmatter("---\nname: x\n- 列表项\n---\n")
    assert fields is None
    assert "- 列表项" in error


def test_split_returns_body_without_the_frontmatter():
    fields, body, error = split_skill(CLAUDE_STYLE)
    assert error is None
    assert body.startswith("# Code Review")
    assert "name: code-review" not in body


def test_referenced_files_takes_sibling_md_only():
    body = (
        "见 [深化](DEEPENING.md) 与 [两次](./DESIGN-IT-TWICE.md)。\n"
        "外链 [站](https://example.com/a.md) 不算。\n"
        "目录外 [上级](../other/x.md) 不算。\n"
        "非 md [脚本](run.sh) 不算。\n"
        "子目录 [深](refs/deep.md) 不算。\n"
    )
    assert referenced_files(body) == ["DEEPENING.md", "DESIGN-IT-TWICE.md"]


def test_referenced_files_dedupes_and_keeps_order():
    body = "[a](A.md) [b](B.md) [a again](A.md)"
    assert referenced_files(body) == ["A.md", "B.md"]


def test_no_links_is_an_empty_list():
    assert referenced_files("没有任何链接") == []


def test_referenced_files_rejects_colon_targets():
    """冒号目标如 `mailto:x.md` 被拒绝——防止协议处理器被当作同目录文件。"""
    body = "见 [邮件链接](mailto:x.md) 和 [正常](REAL.md)"
    assert referenced_files(body) == ["REAL.md"]


def test_referenced_files_rejects_backslash_targets():
    """反斜杠目标如 `sub\\deep.md` 被拒绝——防止 Windows 路径逃逸。"""
    body = "见 [windows路径](sub\\\\deep.md) 和 [正常](REAL.md)"
    assert referenced_files(body) == ["REAL.md"]


def test_parses_frontmatter_ending_with_folded_block():
    """frontmatter 以折叠块结尾（description 是最后一个字段，没有其他字段在后面）——
    现实中真实存在（.pi/agent/skills 里三个文件这样）。"""
    text = """---
name: orca-cli
description: >
  第一行。
  第二行。
---

正文"""
    fields, error = parse_frontmatter(text)
    assert error is None
    assert fields["name"] == "orca-cli"
    assert fields["description"] == "第一行。 第二行。"
