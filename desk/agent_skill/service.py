"""AgentSkillService: status, apply, check and the cached stale flag (A-41/A-67/A-71)."""
from __future__ import annotations

import shutil
import subprocess
import threading
from pathlib import Path

from . import installer
from .targets import SKILL_NAME, TARGETS


class AgentSkillService:
    def __init__(self, resources_root: Path, mode: str, home: Path, which=shutil.which, run=subprocess.run):
        self._resources_root, self._mode, self._home = Path(resources_root), mode, Path(home)
        self._which, self._run = which, run
        self._lock = threading.Lock()
        self._stale = installer.any_stale(self._home, self.skill_dir, self.cli_path)

    @property
    def skill_dir(self) -> Path:
        return self._resources_root / "desk" / "agent_skill" / "bundled" / SKILL_NAME

    @property
    def cli_path(self) -> Path:
        return self._resources_root / ("bin" if self._mode == "bundle" else "scripts") / "lmdesk"

    def status(self) -> dict:
        return installer.status(self._home, self.skill_dir, self.cli_path, which=self._which)

    def apply(self, targets: list[str]) -> dict:
        known = {t.key for t in TARGETS}
        wanted = set(targets)
        if not wanted <= known:
            raise ValueError(f"未知的 agent：{', '.join(sorted(wanted - known))}")
        with self._lock:
            result = installer.apply(self._home, self.skill_dir, self.cli_path, wanted, which=self._which)
            self._stale = installer.any_stale(self._home, self.skill_dir, self.cli_path)
        return result

    def stale(self) -> bool:
        return self._stale

    def check(self) -> dict:
        try:
            done = self._run([str(self.cli_path), "status", "--json", "--timeout", "10"],
                             capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.TimeoutExpired) as exc:
            return {"ok": False, "message": f"lmdesk 无法运行：{exc}", "output": ""}
        if done.returncode == 0:
            return {"ok": True, "message": "lmdesk 能连上台面", "output": done.stdout}
        lines = (done.stderr or "").strip().splitlines()
        return {"ok": False, "message": lines[-1] if lines else f"lmdesk 退出码 {done.returncode}", "output": done.stderr}
