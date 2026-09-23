"""端到端：真的起一个 DeskApp，真的用 urllib 发 HTTP 请求，走跟生产一样的路由
适配层（runtime.py 里 `skills_adapter` 的接法），而不是像 test_skills_routes.py
那样直接调用路由表里的函数。

Finding 1（CRITICAL）就是因为路由这一层从来没被真的攻击过才漏过去的：
`{"staging_id": "../../llms"}` 打到 `/api/skills/discard`，删掉了整个模型库。
只在函数层面测 `discard(staging_id, staging_root)` 测不出这个洞——那样调用者
永远传的是一个干净的 Path，从来不是一段来自网络请求体、没被校验过的字符串。
这里要的是把请求体真的塞进 HTTP body，让它走一遍 JSON 解析、路由匹配、
adapter，再落到 service 手里。
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from desk.app import DeskApp, Response
from desk.skills.install import stage_from_url
from desk.skills.routes import build_routes
from desk.skills.service import SkillsService
from http_helpers import http_call


def fetch_ok(_url):
    return {"SKILL.md": "---\nname: fetched\ndescription: d\n---\n\n正文\n"}


def fetch_named(name: str):
    def _fetch(_url):
        return {"SKILL.md": f"---\nname: {name}\ndescription: d\n---\n\n正文\n"}
    return _fetch


@pytest.fixture()
def server(tmp_path):
    resources_root = tmp_path / "res"
    models_root = tmp_path / "models"
    (resources_root / "desk" / "skills" / "bundled").mkdir(parents=True)
    models_root.mkdir(parents=True)
    roots = SimpleNamespace(resources_root=resources_root, models_root=models_root)
    service = SkillsService(roots)
    # 同一份注入手法 test_skills_routes.py 已经在用：preview 不联网，测试自己给 fetch。
    # `_preview_fetch` 是个可变属性而不是闭包捕获的常量，好让单个测试中途换掉它
    # （比如换成一个声明危险 name 的 SKILL.md）。
    service._preview_fetch = fetch_ok
    service.preview_install = lambda url: stage_from_url(
        url, service._staging_root(), service._preview_fetch)

    app = DeskApp("127.0.0.1", 0)
    # 跟 runtime.py:_mount_routes 里一模一样的 adapter，路由层的行为不能因为测试
    # 换了一条更短的路径就测不到（2026-09-23 finding 1 的教训）。
    for method, pattern, handler in build_routes(service):
        def skills_adapter(req, handler=handler):
            status, payload = handler(req.body, req.query)
            return Response(status, payload)
        app.add_routes([(method, pattern, skills_adapter)])
    app.start_background()
    yield SimpleNamespace(app=app, service=service, models_root=models_root, roots=roots)
    app.shutdown()


def test_discard_with_a_path_traversal_staging_id_is_rejected_and_deletes_nothing(server):
    """CRITICAL 回归：{"staging_id": "../../llms"} 曾经把 `.staging/../../llms`
    解析成 `<models_root>/llms`——整个模型库——直接删掉。这里造一个同名的
    「模型库」哨兵文件，真的通过 HTTP 打这个请求，断言它还在。"""
    llms = server.models_root / "llms"
    llms.mkdir()
    sentinel = llms / "mlx-community" / "some-model" / "weights.safetensors"
    sentinel.parent.mkdir(parents=True)
    sentinel.write_bytes(b"not actually a model, but pretend it matters")

    status, body = http_call(
        server.app, "POST", "/api/skills/discard", {"staging_id": "../../llms"})

    assert status == 409, f"应该被拒绝，却是 {status}：{body}"
    assert body["error"]["code"] == "install_failed"
    assert sentinel.is_file(), "模型库被删了——finding 1 没修好"
    assert llms.is_dir()


def test_discard_with_a_traversal_staging_id_does_not_touch_the_staging_root_either(server):
    """确认拒绝发生在拼路径之前：staging 目录本身、和它里面正常的暂存都不受影响。"""
    status, staged = http_call(server.app, "POST", "/api/skills/preview", {"url": "u"})
    assert status == 200

    status, body = http_call(
        server.app, "POST", "/api/skills/discard", {"staging_id": "../etc"})
    assert status == 409

    # 正常暂存的那份还在，没被这次失败的请求波及。
    status, body = http_call(
        server.app, "POST", "/api/skills/install", {"staging_id": staged["staging_id"]})
    assert status == 200
    assert body == {"installed": "fetched", "enabled": False}


@pytest.mark.parametrize("bad_id", [
    "",
    "not-hex-at-all",
    "../../llms",
    "..",
    "a" * 31,                 # 差一位
    "a" * 33,                 # 多一位
    "A" * 32,                 # 大写不算——uuid4().hex 只产生小写
    "g" * 32,                 # 长度对了，但 g 不是十六进制字符
])
def test_install_with_a_malformed_staging_id_is_rejected_over_http(server, bad_id):
    status, body = http_call(
        server.app, "POST", "/api/skills/install", {"staging_id": bad_id})
    assert status == 409
    assert body["error"]["code"] == "install_failed"


def test_install_with_a_missing_staging_id_key_is_rejected_over_http(server):
    """请求体里根本没有 staging_id 这个键：`.get("staging_id")` 拿到 None。"""
    status, body = http_call(server.app, "POST", "/api/skills/install", {})
    assert status == 409
    assert body["error"]["code"] == "install_failed"


@pytest.mark.parametrize("bad_name,expected_snippet", [
    ("../../escaped", "点开头"),     # ".." 本身就是点开头，落在这条分支
    ("/abs/path/pwned", "目录名"),   # 不含前导点，落在「含 / 或 \」这条分支
    (".hidden", "点开头"),
])
def test_preview_rejects_a_skill_md_with_a_dangerous_name_over_http(server, bad_name, expected_snippet):
    """Finding 2：装之前（preview/staging 阶段）就该被拒绝，用户批准之前就该知道
    装不了——不是等到 install 才炸。三种危险 name 都要在这一步就被挡住。"""
    server.service._preview_fetch = fetch_named(bad_name)

    status, body = http_call(server.app, "POST", "/api/skills/preview", {"url": "u"})

    assert status == 409, f"{bad_name!r} 应该在预览阶段就被拒绝，却是 {status}：{body}"
    assert expected_snippet in body["error"]["message"], body["error"]["message"]
    # name 校验发生在 staged.mkdir() 之前（install.py），所以拒绝之后连暂存目录
    # 都不该被创建——不只是没跑到 skills/ 之外，是什么都没落盘。
    assert not (server.models_root / "skills").exists()
    assert not (server.models_root / "escaped").exists()
    assert not Path("/abs/path/pwned").exists()


def test_install_still_refuses_a_name_that_would_escape_even_if_staging_was_tampered_with(server):
    """带背带的证明：就算预览阶段的校验被绕过了（比如暂存文件在预览之后、确认之前
    被手改），land() 自己也要在真正写盘之前再校验一次、再做一次路径包含检查——
    这条测试直接绕过 preview 的校验，手改暂存文件，确认 install 这一层单独也能
    挡住（2026-09-23 finding 2，belt and braces）。"""
    status, staged = http_call(server.app, "POST", "/api/skills/preview", {"url": "u"})
    assert status == 200

    staging_dir = server.service._staging_root() / staged["staging_id"]
    (staging_dir / "SKILL.md").write_text(
        "---\nname: ../../escaped\ndescription: d\n---\n\n正文\n", encoding="utf-8")

    status, body = http_call(
        server.app, "POST", "/api/skills/install", {"staging_id": staged["staging_id"]})

    assert status == 409, f"应该被拒绝，却是 {status}：{body}"
    assert not (server.models_root / "escaped").exists(), "跑到 skills/ 之外去了"
