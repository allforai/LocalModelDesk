"""skill 的门面：两个根在哪、扫出来是什么。

不缓存扫描结果：没有文件监听（R-skill-09），缓存会让「重新扫描」按钮变成假的。
"""
from __future__ import annotations

from pathlib import Path

from .store import SkillStore


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
