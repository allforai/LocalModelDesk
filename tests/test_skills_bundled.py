"""自带的 skill 必须自己扫得动，而且不能依赖台面做不到的事。

外部生态的 skill 大多写给会用工具的 agent（「跑这个脚本」「派一个子 agent」），
装进纯聊天模型里它会照着念一套自己做不到的流程。自带的这批是样板，必须是反例。
"""
from pathlib import Path

from desk.skills.store import SkillStore

BUNDLED = Path(__file__).resolve().parents[1] / "desk/skills/bundled"


def test_every_bundled_skill_parses(tmp_path):
    entries = SkillStore(BUNDLED, tmp_path / "none").scan()
    assert entries, "一个自带 skill 都没有"
    broken = [(e["name"], e["error"]) for e in entries if not e["ok"]]
    assert broken == [], f"自带的 skill 自己就是坏的：{broken}"


def test_no_bundled_skill_asks_for_a_capability_the_desk_does_not_have():
    forbidden = ("子 agent", "subagent", "运行脚本", "执行命令", "bash", "工具调用", "tool_call")
    offenders = []
    for path in BUNDLED.glob("*/SKILL.md"):
        text = path.read_text(encoding="utf-8")
        offenders += [(path.parent.name, word) for word in forbidden if word in text]
    assert offenders == [], f"自带 skill 要求了台面做不到的事：{offenders}"


def test_no_bundled_skill_links_to_files_that_are_not_there():
    from desk.skills.parse import referenced_files, split_skill
    missing = []
    for path in BUNDLED.glob("*/SKILL.md"):
        _fields, body, _error = split_skill(path.read_text(encoding="utf-8"))
        missing += [(path.parent.name, name) for name in referenced_files(body)
                    if not (path.parent / name).is_file()]
    assert missing == [], f"自带 skill 引了不存在的文件：{missing}"
