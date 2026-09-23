"""/api/skills：列表与重新扫描返回同一形状，重新扫描能看见新文件。"""
from pathlib import Path
from types import SimpleNamespace

from desk.skills.install import stage_from_url
from desk.skills.routes import build_routes
from desk.skills.service import SkillsService

SKILL = "---\nname: {n}\ndescription: d\n---\n\n正文\n"


def fetch_ok(_url):
    return {"SKILL.md": "---\nname: fetched\ndescription: d\n---\n\n正文\n"}


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


def test_preview_install_returns_the_full_text_over_http(tmp_path):
    r = roots(tmp_path)
    service = SkillsService(r)
    service.preview_install = lambda url: stage_from_url(url, service._staging_root(), fetch_ok)
    status, body = handler(service, "POST", "/api/skills/preview")({"url": "u"}, {})
    assert status == 200
    assert body["name"] == "fetched"


def test_preview_install_error_maps_to_409(tmp_path):
    """`InstallError` 过 `_run` 必须变成 409，而不是让异常冒穿 HTTP 层。"""
    r = roots(tmp_path)
    service = SkillsService(r)
    status, body = handler(service, "POST", "/api/skills/preview")({"url": ""}, {})
    assert status == 409
    assert body["error"]["code"] == "install_failed"
    assert body["error"]["message"]


def test_preview_install_with_a_missing_url_gives_the_dedicated_message(tmp_path):
    """没给 url（body 里根本没有这个键）：`preview_install` 自己的守卫先接住，
    不能滑到 `_fetch_github` 里被那条更笼统的「取不下来」吞掉。"""
    r = roots(tmp_path)
    service = SkillsService(r)
    status, body = handler(service, "POST", "/api/skills/preview")({}, {})
    assert status == 409
    assert body["error"]["message"] == "请给一个仓库地址"


def test_install_route_lands_but_does_not_enable(tmp_path):
    r = roots(tmp_path)
    service = SkillsService(r)
    service.preview_install = lambda url: stage_from_url(url, service._staging_root(), fetch_ok)
    _, staged = handler(service, "POST", "/api/skills/preview")({"url": "u"}, {})
    status, body = handler(service, "POST", "/api/skills/install")({"staging_id": staged["staging_id"]}, {})
    assert status == 200
    assert body == {"installed": "fetched", "enabled": False}


def test_discard_route_then_install_fails_with_409(tmp_path):
    r = roots(tmp_path)
    service = SkillsService(r)
    service.preview_install = lambda url: stage_from_url(url, service._staging_root(), fetch_ok)
    _, staged = handler(service, "POST", "/api/skills/preview")({"url": "u"}, {})
    status, body = handler(service, "POST", "/api/skills/discard")({"staging_id": staged["staging_id"]}, {})
    assert status == 200
    assert body == {"discarded": staged["staging_id"]}
    status, body = handler(service, "POST", "/api/skills/install")({"staging_id": staged["staging_id"]}, {})
    assert status == 409
    assert body["error"]["code"] == "install_failed"
