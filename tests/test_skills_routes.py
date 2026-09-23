"""/api/skills：列表与重新扫描返回同一形状，重新扫描能看见新文件。"""
from pathlib import Path
from types import SimpleNamespace

from desk.skills.routes import build_routes
from desk.skills.service import SkillsService

SKILL = "---\nname: {n}\ndescription: d\n---\n\n正文\n"


def roots(tmp_path):
    (tmp_path / "res" / "desk" / "skills" / "bundled").mkdir(parents=True)
    (tmp_path / "models").mkdir(parents=True)
    return SimpleNamespace(resources_root=tmp_path / "res", models_root=tmp_path / "models")


def handler(service, method, path):
    return next(h for m, p, h in build_routes(service) if (m, p) == (method, path))


def write(root: Path, name: str):
    d = root / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(SKILL.format(n=name), encoding="utf-8")


def test_list_returns_skills_from_both_roots(tmp_path):
    r = roots(tmp_path)
    write(r.resources_root / "desk" / "skills" / "bundled", "shipped")
    write(r.models_root / "skills", "mine")
    status, body = handler(SkillsService(r), "GET", "/api/skills")(None, {})
    assert status == 200
    assert sorted(s["name"] for s in body["skills"]) == ["mine", "shipped"]


def test_rescan_sees_a_file_added_after_startup(tmp_path):
    """没有文件监听（R-skill-09），所以重新扫描必须真的重扫，不能返回缓存。"""
    r = roots(tmp_path)
    service = SkillsService(r)
    assert handler(service, "GET", "/api/skills")(None, {})[1]["skills"] == []
    write(r.models_root / "skills", "late")
    status, body = handler(service, "POST", "/api/skills/rescan")(None, {})
    assert status == 200
    assert [s["name"] for s in body["skills"]] == ["late"]


def test_both_routes_return_the_same_shape(tmp_path):
    r = roots(tmp_path)
    write(r.models_root / "skills", "one")
    service = SkillsService(r)
    listed = handler(service, "GET", "/api/skills")(None, {})[1]
    rescanned = handler(service, "POST", "/api/skills/rescan")(None, {})[1]
    assert listed == rescanned, "两个入口对同一个问题给了不同形状的答案"
