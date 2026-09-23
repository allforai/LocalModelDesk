"""skill 的门面：两个根在哪、扫出来是什么。

不缓存扫描结果：没有文件监听（R-skill-09），缓存会让「重新扫描」按钮变成假的。
"""
from __future__ import annotations

import io
import tarfile
import urllib.parse       # 必须显式导入：import urllib.request 不保证 urllib.parse 可用，
import urllib.request     # 而单测注入了 fetch、碰不到这一行——正是「单元绿、真机坏」的形状
from pathlib import Path

from .install import InstallError, discard as _discard, land, stage_from_url
from .store import SkillStore

_TARBALL = "https://codeload.github.com/{owner}/{repo}/tar/refs/heads/{branch}"


def _fetch_github(url: str) -> dict[str, str]:
    """把一个 GitHub 仓库 URL 取成 {文件名: 文本}，只收顶层的 `.md`。

    不执行、不解压到磁盘：直接在内存里读 tar 成员，只认顶层 `.md`，别的一概不看
    （R-skill-01/11）。成员名带路径分隔符的跳过——不跟进子目录，也就不可能被
    `../` 写出去。
    """
    parts = [p for p in urllib.parse.urlparse(url).path.split("/") if p]
    if len(parts) < 2:
        raise ValueError("不是一个仓库地址，形如 https://github.com/<owner>/<repo>")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    last = None
    for branch in ("main", "master"):
        try:
            with urllib.request.urlopen(
                    _TARBALL.format(owner=owner, repo=repo, branch=branch), timeout=30) as body:
                blob = body.read()
            break
        except Exception as exc:                  # 两个分支都试完才算失败
            last = exc
    else:
        raise ValueError(f"取不到仓库内容：{last}")

    files: dict[str, str] = {}
    with tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz") as tar:
        for member in tar.getmembers():
            # tarball 的成员都带一层 "<repo>-<branch>/" 前缀，剥掉之后只收顶层 .md
            name = member.name.split("/", 1)[-1] if "/" in member.name else ""
            if not member.isfile() or "/" in name or not name.endswith(".md"):
                continue
            handle = tar.extractfile(member)
            if handle is None:
                continue
            files[name] = handle.read().decode("utf-8", errors="replace")
    return files


class SkillsService:
    def __init__(self, roots):
        self._roots = roots

    def _store(self) -> SkillStore:
        # 自带的那批落在 resources_root/desk/skills/bundled：`build-app.sh:49` 已经把整个
        # `desk/` rsync 进 `Resources/desk/`，所以这条路径在开发模式（resources_root = 仓库根）
        # 与 bundle 模式下都成立，**不需要给构建脚本加一步**。少一步就少一类
        # 「开发机全绿、装进 app 没有」的故障。
        return SkillStore(Path(self._roots.resources_root) / "desk" / "skills" / "bundled",
                          Path(self._roots.models_root) / "skills")

    def list_skills(self) -> dict:
        return {"skills": self._store().scan()}

    def rescan(self) -> dict:
        return self.list_skills()

    def _staging_root(self) -> Path:
        return Path(self._roots.models_root) / "skills" / ".staging"

    def preview_install(self, url: str) -> dict:
        if not isinstance(url, str) or not url.strip():
            raise InstallError("请给一个仓库地址")
        return stage_from_url(url, self._staging_root(), _fetch_github)

    def confirm_install(self, staging_id: str) -> dict:
        # **只落盘，不启用**（R-skill-11）：装和用是两个动作。这里绝不碰任何会话的
        # skills 字段——用户得自己去芯片里点一下。
        name = land(staging_id, self._staging_root(), Path(self._roots.models_root) / "skills")
        return {"installed": name, "enabled": False}

    def discard_install(self, staging_id: str) -> dict:
        _discard(staging_id, self._staging_root())
        return {"discarded": staging_id}
