"""Symlink states and apply for the agent skill and the lmdesk link (A-52..A-55). Never deletes real files."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

from .targets import CLI_LINK, CLI_SUFFIXES, SKILL_SUFFIX, TARGETS


def _ours(target: str, suffixes) -> bool:
    parts = Path(target).parts
    return any(tuple(parts[-len(s):]) == tuple(s) for s in suffixes)


def link_state(link: Path, current: Path, suffixes) -> dict:
    try:
        if link.is_symlink():
            target = os.readlink(link)
            if Path(target) == current:
                return {"state": "installed", "target": target, "message": None}
            if _ours(target, suffixes):
                return {"state": "stale", "target": target, "message": "指向旧位置，点应用更新"}
            return {"state": "occupied", "target": target, "message": f"这里已有指向 {target} 的链接，台面不会改动"}
        if link.exists():
            return {"state": "occupied", "target": None, "message": "这里已有同名文件或目录，台面不会改动"}
        return {"state": "absent", "target": None, "message": None}
    except OSError as exc:
        return {"state": "error", "target": None, "message": exc.strerror or str(exc)}


def _abs(home: Path, rel: Path) -> Path:
    return rel if rel.is_absolute() else home / rel


def detect(target, home: Path, which) -> bool:
    return any(which(cmd) for cmd in target.detect_cmds) or any(_abs(home, p).exists() for p in target.detect_paths)


def _install(link: Path, current: Path, state: dict) -> dict:
    if state["state"] == "installed":
        return {**state, "result": "ok"}
    if state["state"] in ("occupied", "error"):
        return {**state, "result": "error"}
    try:
        link.parent.mkdir(parents=True, exist_ok=True)
        if state["state"] == "stale":
            link.unlink()
        link.symlink_to(current)
    except OSError as exc:
        return {"state": "error", "target": None, "message": exc.strerror or str(exc), "result": "error"}
    return {"state": "installed", "target": str(current), "message": None, "result": "ok"}


def _uninstall(link: Path, state: dict) -> dict:
    if state["state"] not in ("installed", "stale"):
        return {**state, "result": "ok" if state["state"] in ("absent", "occupied") else "error"}
    try:
        if link.is_symlink():
            link.unlink()
    except OSError as exc:
        return {**state, "state": "error", "message": exc.strerror or str(exc), "result": "error"}
    return {"state": "absent", "target": None, "message": None, "result": "ok"}


def _row(target, home, which, state) -> dict:
    return {"key": target.key, "name": target.name, "path": str(_abs(home, target.link)),
            "detected": detect(target, home, which), "shared_note": target.shared_note, **state}


def status(home: Path, skill_dir: Path, cli_path: Path, which=shutil.which) -> dict:
    rows = [_row(t, home, which, link_state(_abs(home, t.link), skill_dir, (SKILL_SUFFIX,))) for t in TARGETS]
    cli = {"path": str(home / CLI_LINK), **link_state(home / CLI_LINK, cli_path, CLI_SUFFIXES)}
    return {"targets": rows, "cli": cli}


def apply(home: Path, skill_dir: Path, cli_path: Path, wanted: set[str], which=shutil.which) -> dict:
    rows = []
    for target in TARGETS:
        link = _abs(home, target.link)
        state = link_state(link, skill_dir, (SKILL_SUFFIX,))
        state = _install(link, skill_dir, state) if target.key in wanted else _uninstall(link, state)
        rows.append(_row(target, home, which, state))
    cli_link = home / CLI_LINK
    cli_state = link_state(cli_link, cli_path, CLI_SUFFIXES)
    any_installed = any(r["state"] == "installed" for r in rows)
    cli_state = _install(cli_link, cli_path, cli_state) if any_installed else _uninstall(cli_link, cli_state)
    return {"targets": rows, "cli": {"path": str(cli_link), **cli_state}}


def any_stale(home: Path, skill_dir: Path, cli_path: Path) -> bool:
    s = status(home, skill_dir, cli_path, which=lambda _c: None)
    return any(r["state"] == "stale" for r in s["targets"]) or s["cli"]["state"] == "stale"
