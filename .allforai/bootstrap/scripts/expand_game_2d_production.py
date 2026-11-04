#!/usr/bin/env python3
"""Expand game_2d_production handoff into workflow nodes and node-specs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from validate_bootstrap import (
    GAME_2D_PRODUCTION_REQUIRED_ARTIFACTS,
    GAME_2D_PRODUCTION_REQUIRED_NODES,
    _game_2d_handoff_required,
)


NODE_DEFS = [
    {
        "node_id": "game-2d-runtime-profile",
        "skill": "game-2d-production/00-env/runtime-profile",
        "goal": "检测 2D 游戏运行时、命令、视口和自动化能力",
        "exit_artifacts": [".allforai/game-2d/env/2d-runtime-profile.json"],
    },
    {
        "node_id": "game-2d-view-mode-runtime-contract",
        "skill": "game-2d-production/20-spec/view-mode-runtime-contract",
        "goal": "生成 2D 视角、坐标、相机、层级和缩放运行契约",
        "exit_artifacts": [".allforai/game-2d/spec/view-mode-runtime-contract.json"],
    },
    {
        "node_id": "game-2d-core-loop-playable-contract",
        "skill": "game-2d-production/20-spec/core-loop-playable-contract",
        "goal": "生成 2D 核心循环可玩性执行契约",
        "exit_artifacts": [".allforai/game-2d/spec/core-loop-playable-contract.json"],
    },
    {
        "node_id": "game-2d-asset-runtime-binding-contract",
        "skill": "game-2d-production/20-spec/asset-runtime-binding-contract",
        "goal": "生成 2D 美术、UI、动画、特效和音频运行时绑定契约",
        "exit_artifacts": [".allforai/game-2d/spec/asset-runtime-binding-contract.json"],
    },
    {
        "node_id": "game-2d-input-feedback-contract",
        "skill": "game-2d-production/20-spec/input-feedback-contract",
        "goal": "生成 2D 输入与反馈闭环契约",
        "exit_artifacts": [".allforai/game-2d/spec/input-feedback-contract.json"],
    },
    {
        "node_id": "game-2d-session-flow-contract",
        "skill": "game-2d-production/20-spec/session-flow-contract",
        "goal": "生成 2D 启动、游玩、胜负、重试和继续的 session flow 契约",
        "exit_artifacts": [".allforai/game-2d/spec/session-flow-contract.json"],
    },
    {
        "node_id": "game-2d-visual-acceptance-criteria",
        "skill": "visual-qa/20-spec/visual-acceptance-criteria",
        "goal": "生成 2D 运行时截图、资产绑定、原型占位拒绝和玩法不变量的视觉验收标准",
        "exit_artifacts": [
            ".allforai/visual-qa/visual-acceptance-criteria.json",
            ".allforai/visual-qa/visual-acceptance-criteria.md",
            ".allforai/visual-qa/visual-evidence-requirements.json",
        ],
    },
    {
        "node_id": "game-2d-playable-slice-assembly",
        "skill": "game-2d-production/30-generate/playable-slice-assembly",
        "goal": "把 2D 设计、美术、UI、音频和前端契约总装为可运行切片",
        "exit_artifacts": [
            ".allforai/game-2d/assembly/playable-slice-manifest.json",
            ".allforai/game-2d/assembly/playable-slice-assembly-report.json",
        ],
    },
    {
        "node_id": "game-2d-core-loop-playability-qa",
        "skill": "game-2d-production/40-qa/core-loop-playability-qa",
        "goal": "使用运行时输入、状态断言和截图验证 2D 核心循环可玩",
        "exit_artifacts": [".allforai/game-2d/qa/core-loop-playability-qa-report.json"],
    },
    {
        "node_id": "game-2d-asset-binding-visual-qa",
        "skill": "game-2d-production/40-qa/asset-binding-visual-qa",
        "goal": "使用运行时截图和两位独立审稿人（审稿人一为本会话 fresh-context 子 agent，审稿人二为跨平台 CLI 或第二个 fresh-context 子 agent）验证 2D 资产真实绑定且可读",
        "exit_artifacts": [".allforai/game-2d/qa/asset-binding-visual-qa-report.json"],
    },
    {
        "node_id": "game-2d-session-completion-qa",
        "skill": "game-2d-production/40-qa/session-completion-qa",
        "goal": "自动验证 2D 游戏 session 可以启动、进入玩法、完成、重试或继续",
        "exit_artifacts": [".allforai/game-2d/qa/session-completion-qa-report.json"],
    },
    {
        "node_id": "game-2d-code-repair-loop",
        "skill": "game-2d-production/40-qa/code-repair-loop",
        "goal": "修复 2D QA 发现的代码缺口并重跑受影响验收",
        "exit_artifacts": [
            ".allforai/game-2d/repair/code-repair-loop-report.json",
            ".allforai/game-2d/repair/code-repair-loop-report.md",
            ".allforai/game-2d/qa/revalidation-report.json",
        ],
    },
    {
        "node_id": "game-2d-production-closure-qa",
        "skill": "game-2d-production/40-qa/2d-production-closure-qa",
        "goal": "执行 2D 游戏最终出厂闭环验收",
        "exit_artifacts": sorted(GAME_2D_PRODUCTION_REQUIRED_ARTIFACTS),
    },
]


def _load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _artifact_paths(items) -> list[str]:
    paths = []
    for item in items or []:
        if isinstance(item, dict):
            paths.append(item.get("path", ""))
        else:
            paths.append(str(item))
    return paths


def _read_node_spec_frontmatter(path: Path) -> dict:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("---", 3)
    if end == -1:
        return {}
    data: dict[str, object] = {}
    for line in text[3:end].strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _cleanup_orphan_game_2d_specs(specs_dir: Path, workflow_node_ids: set[str], *, dry_run: bool) -> list[str]:
    if not specs_dir.is_dir():
        return []
    removed: list[str] = []
    for spec_path in specs_dir.glob("*.md"):
        spec_id = spec_path.stem
        if spec_id in workflow_node_ids:
            continue
        fm = _read_node_spec_frontmatter(spec_path)
        fm_node_id = str(fm.get("node_id") or "")
        capability = str(fm.get("capability") or "")
        text = ""
        try:
            text = spec_path.read_text(encoding="utf-8")
        except Exception:
            pass
        managed = (
            spec_id in GAME_2D_PRODUCTION_REQUIRED_NODES
            or fm_node_id in GAME_2D_PRODUCTION_REQUIRED_NODES
            or capability == "game-2d-production"
            or "game-2d-production/" in text
        )
        if not managed:
            continue
        removed.append(spec_id)
        if not dry_run:
            spec_path.unlink()
    return removed


def _find_frontend_assembly_node(nodes: list[dict]) -> str | None:
    for node in nodes:
        node_id = node.get("node_id")
        if not node_id:
            continue
        blob = " ".join(_artifact_paths(node.get("exit_artifacts"))).lower()
        if "playable-client-assembly-report.json" in blob:
            return node_id
        if "game-frontend" in node_id and "assembly" in node_id:
            return node_id
    return None


def _node_for(defn: dict, blockers: list[str]) -> dict:
    return {
        "node_id": defn["node_id"],
        "goal": defn["goal"],
        "capability": "game-2d-production",
        "human_gate": False,
        "discipline_owner": "gameplay-frontend-engineer",
        "hard_blocked_by": blockers,
        "alignment_refs": [],
        "exit_artifacts": defn["exit_artifacts"],
    }


def _upsert_game_2d_readiness_repair_loop(project_root: Path, *, dry_run: bool = False) -> bool:
    """Specialize the project readiness spec with the generated 2D repair loop."""
    spec_path = project_root / ".allforai/bootstrap/unattended-run-readiness-spec.json"
    if not spec_path.exists():
        return False
    try:
        spec = _load_json(spec_path)
    except Exception:
        return False
    if not isinstance(spec, dict):
        return False

    loops = spec.setdefault("required_repair_loops", [])
    if not isinstance(loops, list):
        return False

    desired = {
        "scope": "game-2d-production",
        "qa_node_ids": [
            "game-2d-core-loop-playability-qa",
            "game-2d-asset-binding-visual-qa",
            "game-2d-session-completion-qa",
        ],
        "repair_node_id": "game-2d-code-repair-loop",
        "closure_node_ids": ["game-2d-production-closure-qa"],
        "max_attempts": 3,
    }

    for index, loop in enumerate(loops):
        if isinstance(loop, dict) and loop.get("scope") == "game-2d-production":
            if loop == desired:
                return False
            loops[index] = desired
            if not dry_run:
                _write_json(spec_path, spec)
            return True

    loops.append(desired)
    if not dry_run:
        _write_json(spec_path, spec)
    return True


def _yaml_list(values: list[str]) -> str:
    if not values:
        return " []"
    return "\n" + "\n".join(f"  - {json.dumps(value, ensure_ascii=False)}" for value in values)


def _spec_for(defn: dict, node: dict) -> str:
    node_id = defn["node_id"]
    skill = defn["skill"]
    exit_artifacts = node["exit_artifacts"]
    blockers = node.get("hard_blocked_by") or []
    alignment_refs = node.get("alignment_refs") or []
    return f"""---
node_id: {node_id}
goal: {json.dumps(node["goal"], ensure_ascii=False)}
capability: game-2d-production
human_gate: false
discipline_owner: gameplay-frontend-engineer
hard_blocked_by:{_yaml_list(blockers)}
alignment_refs:{_yaml_list(alignment_refs)}
exit_artifacts:{_yaml_list(exit_artifacts)}
---

# {node_id}

## Mission

执行 2D 游戏生产闭环节点。读取并严格遵循：

`${{CLAUDE_PLUGIN_ROOT}}/skills/{skill}/SKILL.md`

## Attention Contract

- Primary outcome: 完成 `{node_id}` 的真实 2D 生产效果，并产出可被下游验收和修复循环消费的证据。
- Non-goals / out-of-scope: 不重新定义游戏概念、不替换运行时、不用占位或 fallback 冒充完成、不扫描无关仓库文件。
- Must-read inputs: 读取本节点 skill、frontmatter 声明的 blockers 产物、2D 生产契约、程序 handoff、运行时 profile，以及与本节点输出直接相关的当前运行证据。
- Optional inputs: 读取项目概念、美术/音频/视觉验收标准、历史 QA 报告和运行日志；缺失时记录 warning，但不得隐式降低验收标准。
- Context budget: 优先读取声明的输入 artifact、接口卡片、当前运行证据和本节点相关源码；只有在定位 blocker 时才扩大到调用方/被调用方文件。
- Quality questions: 该节点是否让 2D 游戏更接近可交付产品；效果是否真实发生；截图、探针、音频、资产或玩法证据是否证明“好不好”；失败是否进入修复和重验。
- Stop conditions: 必需输入缺失、运行时不可启动、无法截图/探针/播放/交互、发现未修复质量缺口、或只能提供 mock/静态结构证据时，返回阻塞状态。
- Repair targets: 可输出 `code_gaps`、`asset_gaps`、`test_gaps`、`quality_gaps`、`effect_gaps`、`experience_gaps`、`environment_blockers`。

## Inputs

- `.allforai/game-design/game-design-doc.json`
- `.allforai/game-design/design/program-development-node-handoff.json`
- `.allforai/game-runtime/art/engine-ready-art-manifest.json`
- `.allforai/game-frontend/assembly/playable-client-assembly-report.json`
- `.allforai/game-frontend/qa/runtime-gameplay-visual-acceptance-report.json`
- 上游 `game-2d-production` 节点已经生成的 `.allforai/game-2d/` 契约和报告

## Required Behavior

- 使用目标项目真实运行时；如果无法运行，输出阻塞状态，不使用替代验收。
- 需要视觉判断时，使用运行时截图和两位独立审稿人的视觉验收文档（ADR-0003：缺跨平台 CLI 只是警告，审稿人二改由第二个 fresh-context 子 agent 承担）。
- 不允许只凭 JSON、日志、源码阅读或静态截图通过可玩性验收。
- 输出必须写到 frontmatter 中声明的 `exit_artifacts`。

## Outputs

{chr(10).join(f"- `{path}`" for path in exit_artifacts)}
"""


def expand_game_2d_production(project_root: Path, *, dry_run: bool = False) -> dict:
    project_root = project_root.resolve()
    bootstrap_dir = project_root / ".allforai/bootstrap"
    workflow_path = bootstrap_dir / "workflow.json"
    specs_dir = bootstrap_dir / "node-specs"

    if not workflow_path.exists():
        return {"status": "blocked", "reason": "missing_workflow", "changed": False}
    if not _game_2d_handoff_required(str(project_root)):
        workflow_node_ids: set[str] = set()
        if workflow_path.exists():
            try:
                workflow = _load_json(workflow_path)
                workflow_node_ids = {
                    node.get("node_id") for node in workflow.get("nodes", []) if node.get("node_id")
                }
            except Exception:
                workflow_node_ids = set()
        removed = _cleanup_orphan_game_2d_specs(specs_dir, workflow_node_ids, dry_run=dry_run)
        return {
            "status": "skipped",
            "reason": "game_2d_production_not_required",
            "changed": bool(removed),
            "removed_orphan_specs": removed,
        }
    workflow = _load_json(workflow_path)
    nodes = workflow.setdefault("nodes", [])
    if not isinstance(nodes, list):
        return {"status": "blocked", "reason": "workflow_nodes_not_list", "changed": False}

    by_node_id = {node.get("node_id"): node for node in nodes if node.get("node_id")}
    frontend_assembly = _find_frontend_assembly_node(nodes)
    changed = False
    previous: str | None = None
    generated: list[str] = []
    updated: list[str] = []

    for defn in NODE_DEFS:
        node_id = defn["node_id"]
        blockers = [previous] if previous else []
        if node_id == "game-2d-playable-slice-assembly" and frontend_assembly:
            blockers = sorted(set(blockers + [frontend_assembly]))
        if node_id == "game-2d-code-repair-loop":
            blockers = [
                "game-2d-core-loop-playability-qa",
                "game-2d-asset-binding-visual-qa",
                "game-2d-session-completion-qa",
            ]
        if node_id == "game-2d-production-closure-qa":
            blockers = ["game-2d-code-repair-loop"]
        blockers = [item for item in blockers if item]

        node = _node_for(defn, blockers)
        existing = by_node_id.get(node_id)
        if existing is None:
            nodes.append(node)
            by_node_id[node_id] = node
            generated.append(node_id)
            changed = True
        else:
            for key in (
                "goal",
                "capability",
                "human_gate",
                "discipline_owner",
                "hard_blocked_by",
                "alignment_refs",
                "exit_artifacts",
            ):
                if existing.get(key) != node[key]:
                    existing[key] = node[key]
                    changed = True
                    if node_id not in updated:
                        updated.append(node_id)

        spec_text = _spec_for(defn, by_node_id[node_id])
        spec_path = specs_dir / f"{node_id}.md"
        if not spec_path.exists() or spec_path.read_text(encoding="utf-8") != spec_text:
            if not dry_run:
                spec_path.parent.mkdir(parents=True, exist_ok=True)
                spec_path.write_text(spec_text, encoding="utf-8")
            changed = True
            if node_id not in generated and node_id not in updated:
                updated.append(node_id)
        previous = node_id

    if changed and not dry_run:
        _write_json(workflow_path, workflow)

    readiness_updated = _upsert_game_2d_readiness_repair_loop(project_root, dry_run=dry_run)
    removed_specs = _cleanup_orphan_game_2d_specs(
        specs_dir,
        {node.get("node_id") for node in nodes if node.get("node_id")},
        dry_run=dry_run,
    )

    return {
        "status": "expanded",
        "changed": changed or readiness_updated or bool(removed_specs),
        "generated_nodes": generated,
        "updated_nodes": updated,
        "removed_orphan_specs": removed_specs,
        "readiness_spec_updated": readiness_updated,
        "required_nodes": GAME_2D_PRODUCTION_REQUIRED_NODES,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", nargs="?", default=".")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = expand_game_2d_production(Path(args.project_root), dry_run=args.dry_run)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] in {"expanded", "skipped"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
