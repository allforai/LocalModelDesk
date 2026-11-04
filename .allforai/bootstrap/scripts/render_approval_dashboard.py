#!/usr/bin/env python3
"""Render the design and architecture approval dashboard.

Generates static HTML served by serve_approval.py. Approval buttons POST
directly to /api/action — no Playwright or localStorage required.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def combine_approvals(paths: list[Path]) -> dict:
    records = []
    sources = []
    for path in paths:
        payload = read_json(path)
        if not payload:
            continue
        source = path.as_posix()
        sources.append(source)
        for record in payload.get("records", []):
            if isinstance(record, dict):
                enriched = dict(record)
                enriched.setdefault("approval_record_path", source)
                records.append(enriched)
    return {"records": records, "sources": sources}


def read_gate_states() -> dict:
    gate_paths = {
        "art-concept": Path(".allforai/game-design/art/art-concept-validation.json"),
        "architecture-concept-validation": Path(
            ".allforai/architecture/architecture-concept-validation.json"
        ),
    }
    states = {}
    for node_id, path in gate_paths.items():
        payload = read_json(path)
        if payload:
            states[node_id] = payload
    return states


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--approval",
        action="append",
        required=True,
        help="Path to approval-records.json. May be passed more than once.",
    )
    parser.add_argument("--workflow", required=False)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    approval_paths = [Path(path) for path in args.approval]
    workflow_path = Path(args.workflow) if args.workflow else None
    output_path = Path(args.output)

    approval = combine_approvals(approval_paths)
    workflow = read_json(workflow_path) if workflow_path else {}
    gate_states = read_gate_states()
    embedded = json.dumps(
        {"approval": approval, "workflow": workflow, "gate_states": gate_states},
        ensure_ascii=False,
        separators=(",", ":"),
    ).replace("</", "<\\/")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>设计与架构审批看板</title>
<style>
*,*::before,*::after{{box-sizing:border-box}}
html,body{{margin:0;height:100%;font:14px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;color:#1a202c;background:#f0f2f5}}
a{{color:#2b6cb0;text-decoration:none}}
a:hover{{text-decoration:underline}}

/* ── Header ── */
.hd{{position:sticky;top:0;z-index:10;background:#1a365d;color:#fff;padding:0 20px;display:flex;align-items:center;gap:16px;height:52px;box-shadow:0 2px 8px rgba(0,0,0,.25)}}
.hd h1{{margin:0;font-size:16px;font-weight:700;letter-spacing:.3px;flex:1;white-space:nowrap}}
.hd-chips{{display:flex;gap:8px;flex-wrap:wrap}}
.stat-chip{{padding:3px 10px;border-radius:999px;font-size:12px;font-weight:600;cursor:pointer;border:none;color:#fff;transition:opacity .15s;white-space:nowrap}}
.stat-chip:hover{{opacity:.85}}
.chip-revision{{background:#c53030}}
.chip-review{{background:#2b6cb0}}
.chip-pending{{background:#718096}}
.chip-approved{{background:#276749}}
.hd-refresh{{padding:5px 12px;border-radius:6px;border:1px solid rgba(255,255,255,.3);background:rgba(255,255,255,.1);color:#fff;cursor:pointer;font-size:13px;white-space:nowrap;flex-shrink:0}}
.hd-refresh:hover{{background:rgba(255,255,255,.2)}}
.pulse{{display:inline-block;width:7px;height:7px;border-radius:50%;background:#68d391;margin-right:6px;animation:pulse 2s ease-in-out infinite}}
@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:.4}}}}

/* ── Layout ── */
.layout{{display:flex;height:calc(100vh - 52px)}}
.sidebar{{width:220px;min-width:0;flex-shrink:0;background:#fff;border-right:1px solid #e2e8f0;display:flex;flex-direction:column;transition:width .22s ease;overflow:hidden}}
.sidebar.collapsed{{width:28px}}
.sidebar-hd{{flex-shrink:0;display:flex;align-items:center;justify-content:space-between;padding:4px 8px 4px 12px;border-bottom:1px solid #e2e8f0;background:#fff;min-height:38px}}
.sidebar-hd-title{{font-size:12px;font-weight:700;color:#4a5568;letter-spacing:.3px;white-space:nowrap;transition:opacity .2s ease}}
.sidebar.collapsed .sidebar-hd-title{{opacity:0}}
.sidebar-body{{flex:1;overflow-y:auto;overflow-x:hidden;padding:12px 0}}
.sidebar.collapsed .sidebar-body{{overflow:hidden;pointer-events:none}}
.sidebar-toggle{{width:26px;height:26px;border-radius:7px;background:transparent;border:1.5px solid #e2e8f0;cursor:pointer;font-size:15px;color:#718096;display:flex;align-items:center;justify-content:center;flex-shrink:0;padding:0;line-height:1;transition:background .15s,color .15s,border-color .15s}}
.sidebar-toggle:hover{{background:#eff6ff;border-color:#bfdbfe;color:#3b82f6}}
.sidebar-section{{margin-bottom:4px}}
.sidebar-label{{padding:4px 16px;font-size:11px;font-weight:700;color:#a0aec0;text-transform:uppercase;letter-spacing:.6px;white-space:nowrap}}
.sidebar-item{{display:flex;align-items:center;gap:8px;padding:7px 16px;cursor:pointer;border-left:3px solid transparent;transition:background .1s;white-space:nowrap}}
.sidebar-item:hover{{background:#f7fafc}}
.sidebar-item.active{{background:#ebf8ff;border-left-color:#3182ce;color:#2b6cb0;font-weight:600}}
.sidebar-item.s-revision{{border-left-color:#fc8181}}
.sidebar-item.s-review{{border-left-color:#63b3ed}}
.sidebar-item.s-pending{{border-left-color:#cbd5e0}}
.sidebar-item.s-approved{{border-left-color:#68d391}}
.sidebar-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.dot-revision{{background:#e53e3e}}
.dot-review{{background:#3182ce}}
.dot-pending{{background:#a0aec0}}
.dot-approved{{background:#38a169}}
.sidebar-name{{font-size:13px;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}

/* ── Main panel ── */
.main{{display:none}}
@media(max-width:1100px){{.sidebar:not(.collapsed){{width:210px}}}}
@media(max-width:800px){{.layout{{flex-direction:column;height:auto}}.sidebar{{width:100%!important;max-height:220px;border-right:none;border-bottom:1px solid #e2e8f0}}.sidebar.collapsed{{max-height:34px}}.preview-panel,.preview-panel.open{{width:100%;height:72vh;border-left:none;border-top:1px solid #e2e8f0}}}}

/* ── Preview panel ── */
.preview-panel{{flex:1;background:#fff;border-left:1px solid #e2e8f0;overflow:hidden;display:flex;flex-direction:column;min-width:0}}
.preview-panel:not(.open) .preview-iframe,.preview-panel:not(.open) .preview-actions{{display:none}}
.preview-panel:not(.open) .tab-bar-empty{{display:flex}}
.preview-panel.open .tab-bar-empty{{display:none}}

/* Tab bar */
.tab-bar{{display:flex;align-items:flex-end;background:#eef0f3;border-bottom:1px solid #dde1e7;flex-shrink:0;overflow-x:auto;overflow-y:hidden;min-height:36px;scrollbar-width:none;-ms-overflow-style:none;padding:0 0 0 6px;gap:2px}}
.tab-bar::-webkit-scrollbar{{display:none}}
.tab-bar-empty{{align-items:center;justify-content:center;height:100%;color:#a0aec0;font-size:13px;display:none}}
.preview-tab{{display:flex;align-items:center;gap:5px;padding:0 8px 0 10px;height:28px;min-width:80px;max-width:180px;cursor:pointer;background:#dde1e9;border:1px solid #cdd2da;border-bottom:none;border-radius:5px 5px 0 0;font-size:12px;color:#5a6478;white-space:nowrap;flex-shrink:0;transition:background .12s;margin-top:8px;position:relative}}
.preview-tab:hover{{background:#e8eaee;color:#2d3748}}
.preview-tab.active{{background:#fff;color:#1a202c;font-weight:600;border-color:#dde1e7;height:32px;margin-top:4px;z-index:1;box-shadow:0 -1px 0 #fff}}
.preview-tab-name{{flex:1;overflow:hidden;text-overflow:ellipsis;min-width:40px}}
.preview-tab-x{{width:16px;height:16px;border-radius:3px;border:none;background:transparent;cursor:pointer;font-size:10px;color:#a0aec0;display:flex;align-items:center;justify-content:center;padding:0;flex-shrink:0;transition:background .1s,color .1s;margin-left:2px}}
.preview-tab-x:hover{{background:rgba(0,0,0,.1);color:#4a5568}}
.preview-iframe{{flex:1;border:none;width:100%;display:block}}
.preview-actions{{border-top:1px solid #e2e8f0;background:#fff;box-shadow:0 -4px 14px rgba(0,0,0,.06);flex-shrink:0}}
.pa-hd{{display:flex;align-items:center;gap:8px;height:40px;padding:0 14px;background:#f8fafc;border-bottom:1px solid #edf2f7}}
.pa-hd-info{{flex:1;min-width:0;display:flex;flex-direction:column;gap:1px}}
.preview-actions-title{{font-size:13px;font-weight:700;color:#1a202c;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.preview-actions-meta{{font-size:11px;color:#94a3b8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.pa-toggle{{width:26px;height:26px;border-radius:7px;border:1.5px solid #e2e8f0;background:transparent;cursor:pointer;font-size:15px;color:#718096;display:flex;align-items:center;justify-content:center;flex-shrink:0;padding:0;transition:background .15s,color .15s,border-color .15s}}
.pa-toggle:hover{{background:#f0f9ff;border-color:#bae6fd;color:#0284c7}}
.pa-body{{padding:6px 12px 10px;display:grid;grid-template-columns:1fr auto;gap:10px;align-items:start;overflow:hidden;transition:max-height .2s ease,padding .2s ease;max-height:300px}}
.pa-body.hidden{{max-height:0;padding-top:0;padding-bottom:0}}
.preview-actions textarea{{width:100%;min-height:54px;resize:vertical;padding:8px;border:1px solid #e2e8f0;border-radius:6px;font:inherit;font-size:13px;color:#2d3748;background:#f8fafc}}
.preview-actions textarea:focus{{outline:none;border-color:#90cdf4;background:#fff}}
.preview-actions-grid{{display:grid;grid-template-columns:1fr 1fr;gap:8px}}
.preview-actions-buttons{{display:flex;flex-direction:column;gap:6px;min-width:120px}}
.preview-actions-readonly{{font-size:13px;color:#4a5568;background:#f7fafc;border:1px solid #e2e8f0;border-radius:6px;padding:8px 10px}}
.section-head{{display:flex;align-items:center;gap:8px;margin:2px 0 8px;padding:0 2px 7px;border-bottom:1px solid #e2e8f0}}
.section-head h2{{margin:0;font-size:13px;font-weight:700;color:#2d3748}}
.section-badge{{padding:2px 9px;border-radius:999px;font-size:12px;font-weight:600}}
.badge-revision{{background:#fed7d7;color:#c53030}}
.badge-review{{background:#bee3f8;color:#2b6cb0}}
.badge-pending{{background:#e2e8f0;color:#4a5568}}
.badge-approved{{background:#c6f6d5;color:#276749}}
.cards{{display:flex;flex-direction:column;gap:8px;margin-bottom:18px}}

/* ── Card ── */
.card{{background:#fff;border-radius:8px;border:1px solid #e2e8f0;overflow:hidden;transition:box-shadow .15s,border-color .15s}}
.card:hover{{box-shadow:0 2px 8px rgba(0,0,0,.06);border-color:#cbd5e0}}
.card-bar{{height:4px}}
.bar-revision{{background:#e53e3e}}
.bar-review{{background:#3182ce}}
.bar-pending{{background:#a0aec0}}
.bar-approved{{background:#38a169}}
.card-body{{padding:10px 12px}}
.card-header{{display:flex;align-items:center;gap:8px;margin-bottom:6px}}
.card-title{{font-size:14px;font-weight:700;color:#1a202c;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.status-badge{{padding:2px 8px;border-radius:999px;font-size:11px;font-weight:600;white-space:nowrap}}
.badge-s-revision{{background:#fed7d7;color:#9b2c2c}}
.badge-s-review{{background:#bee3f8;color:#2c5282}}
.badge-s-pending{{background:#e2e8f0;color:#4a5568}}
.badge-s-approved{{background:#c6f6d5;color:#22543d}}
.card-meta{{font-size:12px;color:#718096;margin-bottom:6px;display:flex;flex-wrap:wrap;gap:6px 10px;align-items:center}}
.card-meta a{{font-size:12px}}

/* Checklist */
.checklist{{margin:6px 0 0;padding:8px 10px;list-style:none;background:#f7fafc;border-radius:6px}}
.checklist li{{display:flex;align-items:flex-start;gap:8px;font-size:13px;color:#4a5568;padding:3px 0}}
.checklist li::before{{content:"☐";color:#a0aec0;flex-shrink:0;margin-top:1px}}
.checklist li.done::before{{content:"☑";color:#38a169}}

/* Notes */
.review-details{{border-top:1px solid #edf2f7;margin-top:8px;padding-top:6px}}
.review-details summary{{cursor:pointer;color:#2b6cb0;font-size:12px;font-weight:700;list-style:none;display:flex;align-items:center;justify-content:space-between}}
.review-details summary::after{{content:"展开";font-weight:600;color:#718096}}
.review-details[open] summary::after{{content:"收起"}}
.notes-row{{display:grid;grid-template-columns:1fr;gap:8px;margin:8px 0}}
@media(max-width:600px){{.notes-row{{grid-template-columns:1fr}}}}
.note-block label{{display:block;font-size:12px;font-weight:600;color:#4a5568;margin-bottom:4px}}
.note-block textarea{{width:100%;min-height:58px;resize:vertical;padding:8px;border:1px solid #e2e8f0;border-radius:6px;font:inherit;font-size:13px;color:#2d3748;background:#f7fafc}}
.note-block textarea:focus{{outline:none;border-color:#90cdf4;background:#fff}}
.note-block.revision-notes textarea{{border-color:#fc8181;background:#fff5f5}}

/* Existing notes (read-only) */
.existing-notes{{margin:6px 0}}
.existing-notes .note-label{{font-size:12px;font-weight:600;color:#9b2c2c;margin-bottom:4px}}
.existing-notes .note-body{{background:#fff5f5;border:1px solid #fc8181;border-radius:6px;padding:8px 10px;font-size:13px;color:#c53030;white-space:pre-wrap}}

/* Actions */
.actions{{display:flex;flex-wrap:wrap;gap:6px}}
.btn{{padding:6px 10px;border-radius:6px;border:1px solid #e2e8f0;background:#fff;cursor:pointer;font-size:12px;font-weight:600;transition:all .15s}}
.btn-link{{border-color:#bee3f8;color:#2b6cb0;background:#ebf8ff}}
.btn-link:hover{{background:#bee3f8;text-decoration:none}}
.btn:hover{{background:#f7fafc}}
.btn:disabled{{opacity:.5;cursor:default}}
.btn-approve{{background:#276749;border-color:#276749;color:#fff}}
.btn-approve:hover:not(:disabled){{background:#22543d}}
.btn-revision{{background:#c53030;border-color:#c53030;color:#fff}}
.btn-revision:hover:not(:disabled){{background:#9b2c2c}}
.btn-save{{background:#2b6cb0;border-color:#2b6cb0;color:#fff}}
.btn-save:hover:not(:disabled){{background:#2c5282}}

/* Toast */
.toast{{position:fixed;bottom:24px;right:24px;padding:12px 20px;border-radius:8px;background:#276749;color:#fff;font-size:14px;font-weight:600;opacity:0;transform:translateY(8px);transition:all .25s;z-index:200;pointer-events:none;box-shadow:0 4px 12px rgba(0,0,0,.2)}}
.toast.show{{opacity:1;transform:translateY(0)}}
.toast.error{{background:#c53030}}
</style>
</head>
<body>
<header class="hd">
  <h1><span class="pulse"></span>设计与架构审批看板</h1>
  <div class="hd-chips" id="hd-stats"></div>
  <button class="hd-refresh" onclick="reloadRecords()">刷新</button>
</header>
<div class="layout">
  <nav class="sidebar" id="sidebar">
    <div class="sidebar-hd">
      <span class="sidebar-hd-title">节点列表</span>
      <button class="sidebar-toggle" id="sidebar-toggle" onclick="toggleSidebar()" title="折叠侧边栏">‹</button>
    </div>
    <div class="sidebar-body" id="sidebar-body"></div>
  </nav>
  <main class="main" id="main" hidden aria-hidden="true"></main>
  <div class="preview-panel" id="preview-panel">
    <div class="tab-bar" id="tab-bar">
      <span class="tab-bar-empty">选择一个节点的输出后在这里预览</span>
    </div>
    <iframe id="preview-iframe" class="preview-iframe" src="about:blank"></iframe>
    <div id="preview-actions" class="preview-actions"></div>
  </div>
</div>
<div class="toast" id="toast"></div>
<script>
const EMBEDDED = {embedded};
let state = EMBEDDED;
let activeFilter = null;
let currentRecords = [];
let activeNodeId = null;

const STATUS_ORDER = ["revision-requested","in-review","pending","approved"];
const STATUS_LABELS = {{"revision-requested":"要求修改","in-review":"审核中","pending":"待执行","approved":"已批准"}};
const STATUS_CHIP = {{"revision-requested":"chip-revision","in-review":"chip-review","pending":"chip-pending","approved":"chip-approved"}};
const STATUS_BADGE = {{"revision-requested":"badge-revision","in-review":"badge-review","pending":"badge-pending","approved":"badge-approved"}};
const STATUS_BADGE_S = {{"revision-requested":"badge-s-revision","in-review":"badge-s-review","pending":"badge-s-pending","approved":"badge-s-approved"}};
const STATUS_BAR = {{"revision-requested":"bar-revision","in-review":"bar-review","pending":"bar-pending","approved":"bar-approved"}};
const STATUS_DOT = {{"revision-requested":"dot-revision","in-review":"dot-review","pending":"dot-pending","approved":"dot-approved"}};
const STATUS_SIDEBAR = {{"revision-requested":"s-revision","in-review":"s-review","pending":"s-pending","approved":"s-approved"}};
const GATE_JSON_PATHS = {{
  "art-concept": ".allforai/game-design/art/art-concept-validation.json",
  "architecture-concept-validation": ".allforai/architecture/architecture-concept-validation.json"
}};

async function loadApproval() {{
  try {{
    const sources = (state.approval && state.approval.sources && state.approval.sources.length)
      ? state.approval.sources : ["approval-records.json"];
    const records = [];
    const loadedSources = [];
    for (const source of sources) {{
      const r = await fetch(normalizeOutputHref(source)+"?ts="+Date.now(),{{cache:"no-store"}});
      if (!r.ok) continue;
      const payload = await r.json();
      loadedSources.push(source);
      for (const record of (payload.records || [])) {{
        records.push({{...record, approval_record_path: source}});
      }}
    }}
    if (loadedSources.length) state.approval = {{records, sources: loadedSources}};
  }} catch(e) {{}}
}}

async function loadGateStates() {{
  state.gate_states = state.gate_states || {{}};
  for (const [nodeId, path] of Object.entries(GATE_JSON_PATHS)) {{
    if (!workflowHasNode(nodeId)) continue;
    try {{
      const r = await fetch(normalizeOutputHref(path)+"?ts="+Date.now(),{{cache:"no-store"}});
      if (r.ok) state.gate_states[nodeId] = await r.json();
    }} catch(e) {{}}
  }}
}}

function getNodeId(rec) {{ return rec.node_id || ""; }}

function normalizeOutputHref(path) {{
  if (!path) return null;
  let href = String(path);
  if (href.startsWith(".allforai/game-design/")) return href.slice(".allforai/game-design/".length);
  if (href.startsWith(".allforai/architecture/")) return "../architecture/" + href.slice(".allforai/architecture/".length);
  if (href.startsWith(".allforai/")) return "../" + href.slice(".allforai/".length);
  return href;
}}

function htmlOutputFor(rec) {{
  if (rec.html_output) return normalizeOutputHref(rec.html_output);
  const nid = getNodeId(rec);
  const map = {{
    "core-loop-design":"core-loop.html","character-arc-design":"character-arc.html",
    "ftue-design":"ftue.html","monetization-design":"monetization.html",
    "retention-hook-design":"retention-hook.html","meta-game-design":"meta-game.html",
    "level-design":"level-design.html","puzzle-design":"puzzle-design.html",
    "progression-curve-design":"progression-curve.html","audio-design":"audio-design.html",
    "worldbuilding":"worldbuilding.html","art-direction":"art-direction.html",
    "art-spec-design":"art-spec-design.html","tile-art-gen":"tile-art-review.html",
    "character-art-gen":"character-art-review.html","environment-art-gen":"environment-art-review.html",
    "ui-art-gen":"ui-art-review.html","vfx-art-gen":"vfx-art-review.html",
    "art-concept":"art/art-concept-validation.html",
    "art-qa":"art-qa-report.html","game-design-finalize":"game-design-dashboard.html",
    "architecture-concept-validation":"../architecture/architecture-concept-validation.html"
  }};
  return normalizeOutputHref(map[nid]) || null;
}}

function workflowNodes() {{
  return (state.workflow && Array.isArray(state.workflow.nodes)) ? state.workflow.nodes : [];
}}

function workflowHasNode(nodeId) {{
  return workflowNodes().some(n => n && n.node_id === nodeId);
}}

function gatePayload(nodeId) {{
  return (state.gate_states && state.gate_states[nodeId]) || null;
}}

function statusFromGateState(payload) {{
  const gateState = payload && payload.state ? String(payload.state) : "";
  if (!gateState) return "pending";
  if (gateState === "passed") return "approved";
  if (gateState === "passed_with_warnings") return "in-review";
  if (gateState === "needs_revision" || gateState.startsWith("blocked_") || gateState === "failed_validation") return "revision-requested";
  return "pending";
}}

function gateSummary(payload) {{
  if (!payload) return "等待 gate 产物生成。";
  const stateText = payload.state ? `状态：${{payload.state}}。` : "状态：未声明。";
  const summary = payload.approval_summary || payload.summary || "";
  const blockers = Array.isArray(payload.blocked_validation_items) && payload.blocked_validation_items.length
    ? `阻塞项：${{payload.blocked_validation_items.length}} 个。`
    : "";
  return [stateText, summary, blockers].filter(Boolean).join(" ");
}}

function virtualGateRecords(records) {{
  const existing = new Set(records.map(getNodeId));
  const gates = [];
  if (workflowHasNode("art-concept") && !existing.has("art-concept")) {{
    const payload = gatePayload("art-concept");
    gates.push({{
      node_id: "art-concept",
      gate_status: statusFromGateState(payload),
      discipline_owner: "art-director",
      html_output: ".allforai/game-design/art/art-concept-validation.html",
      gate_state: payload && payload.state,
      gate_summary: gateSummary(payload),
      read_only: true,
      virtual_gate: true,
      review_checklist: [
        "美术概念 HTML gate 已生成并可阅读",
        "美术方向与产品/游戏概念、目标受众和玩法可读性闭合",
        "未通过时必须阻断后续 art-gen 节点"
      ]
    }});
  }}
  if (workflowHasNode("architecture-concept-validation") && !existing.has("architecture-concept-validation")) {{
    const payload = gatePayload("architecture-concept-validation");
    gates.push({{
      node_id: "architecture-concept-validation",
      gate_status: statusFromGateState(payload),
      discipline_owner: "lead-engineer",
      html_output: ".allforai/architecture/architecture-concept-validation.html",
      gate_state: payload && payload.state,
      gate_summary: gateSummary(payload),
      read_only: true,
      virtual_gate: true,
      review_checklist: [
        "技术框架 / 技术架构决策 HTML gate 已生成并可阅读",
        "实现节点均映射到模块、输入契约、输出契约和验证路径",
        "无法运行或导入验证时必须暴露 blocked 状态，不允许替代验收"
      ]
    }});
  }}
  return gates;
}}

function getText(id) {{ const el=document.getElementById(id); return el?el.value:""; }}

function setButtons(nid, disabled) {{
  ["approve-"+nid,"revision-btn-"+nid,"save-"+nid].forEach(id => {{
    const el = document.getElementById(id);
    if (el) el.disabled = disabled;
  }});
}}

async function submitAction(action) {{
  action.created_at = new Date().toISOString();
  const nid = action.node_id;
  setButtons(nid, true);
  try {{
    const r = await fetch("/api/action", {{
      method: "POST",
      headers: {{"Content-Type": "application/json"}},
      body: JSON.stringify(action)
    }});
    if (!r.ok) {{
      const err = await r.json().catch(() => ({{}}));
      throw new Error(err.error || r.statusText);
    }}
    showToast("✓ 操作已保存");
    await reloadRecords();
  }} catch(e) {{
    showToast("✗ " + e.message, true);
    setButtons(nid, false);
  }}
}}

function approve(nodeId, approvalPath) {{
  submitAction({{action:"approve",node_id:nodeId,approval_record_path:approvalPath,approved_by:"discipline_owner",
    reviewer_notes:getText("reviewer-"+nodeId),revision_notes:""}});
}}

function requestRevision(nodeId, approvalPath) {{
  const notes = getText("revision-"+nodeId);
  if (!notes.trim()) {{ alert("请填写修改意见后再提交"); return; }}
  submitAction({{action:"request_revision",node_id:nodeId,approval_record_path:approvalPath,
    reviewer_notes:getText("reviewer-"+nodeId),revision_notes:notes}});
}}

function saveNotes(nodeId, approvalPath) {{
  submitAction({{action:"save_notes",node_id:nodeId,approval_record_path:approvalPath,
    reviewer_notes:getText("reviewer-"+nodeId),revision_notes:getText("revision-"+nodeId)}});
}}

function showToast(msg, isError) {{
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = "toast" + (isError ? " error" : "");
  requestAnimationFrame(() => {{ t.classList.add("show"); }});
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("show"), 2500);
}}

function filterBy(status) {{
  activeFilter = activeFilter === status ? null : status;
  render();
}}

function scrollTo(nodeId) {{
  const el = document.getElementById("card-"+nodeId);
  if (el) el.scrollIntoView({{behavior:"smooth",block:"start"}});
}}

function recordByNodeId(nodeId) {{
  return currentRecords.find(rec => getNodeId(rec) === nodeId) || null;
}}

function selectRecord(nodeId) {{
  const rec = recordByNodeId(nodeId);
  if (!rec) return;
  const href = htmlOutputFor(rec);
  if (href) openPreview(href, nodeId);
  else {{
    activeNodeId = nodeId;
    document.getElementById("preview-title").textContent = nodeId;
    document.getElementById("preview-iframe").src = "about:blank";
    document.getElementById("preview-panel").classList.add("open");
    renderPreviewActions(rec);
  }}
}}

function renderCard(rec) {{
  const nid = getNodeId(rec);
  const st = rec.gate_status || "pending";
  const isReadOnly = !!(rec.read_only || rec.virtual_gate);
  const outputHref = htmlOutputFor(rec);
  const outputLink = outputHref ? `<a href="javascript:void(0)" onclick="openPreview('${{escapeJs(outputHref)}}','${{escapeJs(nid)}}')">查看输出 ▶</a>` : "";
  const reviewers = (rec.discipline_reviewers||[]).join(", ");

  const checklist = (rec.review_checklist||[]).map(item => {{
    const text = typeof item==="string" ? item : (item.item||"");
    const checked = typeof item==="object" && item.checked;
    return `<li class="${{checked?"done":""}}">${{escapeHtml(text)}}</li>`;
  }}).join("");
  const checklistHtml = checklist ? `<ul class="checklist">${{checklist}}</ul>` : "";

  const existingRevision = rec.revision_notes ?
    `<div class="existing-notes"><div class="note-label">⚠ 待修改意见</div><div class="note-body">${{escapeHtml(rec.revision_notes)}}</div></div>` : "";

  const existingReviewer = rec.reviewer_notes ?
    `<div class="existing-notes" style="margin-bottom:8px"><div class="note-label" style="color:#2b6cb0">📝 评审备注</div><div class="note-body" style="border-color:#90cdf4;background:#ebf8ff;color:#2c5282">${{escapeHtml(rec.reviewer_notes)}}</div></div>` : "";

  const readonlyNotice = isReadOnly ?
    `<div class="existing-notes" style="margin-bottom:12px"><div class="note-label" style="color:#4a5568">只读验证 Gate${{rec.gate_state ? `：${{escapeHtml(rec.gate_state)}}` : ""}}</div><div class="note-body" style="border-color:#cbd5e0;background:#f7fafc;color:#4a5568">${{escapeHtml(rec.gate_summary || "此项来自 workflow 的自动化验证节点，不写入 approval-records.json。请打开 HTML gate 查看结论；若 gate 输出 blocked 或 failed，后续执行节点应被阻断。")}}</div></div>` : "";

  const isApproved = st === "approved";
  const approvalPath = rec.approval_record_path || "";
  return `<div class="card" id="card-${{escapeAttr(nid)}}">
  <div class="card-bar ${{STATUS_BAR[st]||"bar-pending"}}"></div>
  <div class="card-body">
    <div class="card-header">
      <div class="card-title">${{escapeHtml(nid)}}</div>
      <span class="status-badge ${{STATUS_BADGE_S[st]||"badge-s-pending"}}">${{STATUS_LABELS[st]||st}}</span>
    </div>
    <div class="card-meta">
      <span>负责人：<strong>${{escapeHtml(rec.discipline_owner||"")}}</strong></span>
      ${{reviewers ? `<span>评审员：${{escapeHtml(reviewers)}}</span>` : ""}}
      ${{isReadOnly ? `<span>类型：只读自动化 Gate</span>` : ""}}
      ${{rec.approved_by&&rec.approved_by.length ? `<span style="color:#276749">✓ 批准：${{escapeHtml((rec.approved_by||[]).join(", "))}}</span>` : ""}}
      ${{outputLink}}
    </div>
    ${{checklistHtml}}
    ${{readonlyNotice}}${{existingRevision}}${{existingReviewer}}
    ${{isApproved || isReadOnly ? "" : `
    <div class="notes-row">
      <div class="note-block">
        <label>评审备注</label>
        <textarea id="reviewer-${{escapeAttr(nid)}}" placeholder="评审员备注（不影响审批状态）">${{escapeHtml(rec.reviewer_notes||"")}}</textarea>
      </div>
      <div class="note-block revision-notes">
        <label>修改意见</label>
        <textarea id="revision-${{escapeAttr(nid)}}" placeholder="填写修改意见后点击&ldquo;要求修改&rdquo;">${{escapeHtml(rec.revision_notes||"")}}</textarea>
      </div>
    </div>
    <div class="actions">
      <button id="approve-${{escapeAttr(nid)}}" class="btn btn-approve" onclick="approve('${{escapeJs(nid)}}','${{escapeJs(approvalPath)}}')">✓ 批准</button>
      <button id="revision-btn-${{escapeAttr(nid)}}" class="btn btn-revision" onclick="requestRevision('${{escapeJs(nid)}}','${{escapeJs(approvalPath)}}')">↩ 要求修改</button>
      <button id="save-${{escapeAttr(nid)}}" class="btn btn-save" onclick="saveNotes('${{escapeJs(nid)}}','${{escapeJs(approvalPath)}}')">💾 保存备注</button>
    </div>`}}
  </div>
</div>`;
}}

let previewActionsCollapsed = false;

function togglePreviewActions() {{
  previewActionsCollapsed = !previewActionsCollapsed;
  const body = document.getElementById("pa-body");
  const btn = document.getElementById("pa-toggle-btn");
  if (body) body.classList.toggle("hidden", previewActionsCollapsed);
  if (btn) {{ btn.textContent = previewActionsCollapsed ? "▲" : "▼"; btn.title = previewActionsCollapsed ? "展开操作栏" : "折叠操作栏"; }}
  try {{ localStorage.setItem("paCollapsed", previewActionsCollapsed ? "1" : "0"); }} catch(e) {{}}
}}

function initPreviewActionsState() {{
  try {{ if (localStorage.getItem("paCollapsed") === "1") previewActionsCollapsed = true; }} catch(e) {{}}
}}

function renderPreviewActions(rec) {{
  const target = document.getElementById("preview-actions");
  if (!target) return;
  if (!rec) {{ target.innerHTML = ""; return; }}
  const nid = getNodeId(rec);
  const st = rec.gate_status || "pending";
  const isReadOnly = !!(rec.read_only || rec.virtual_gate);
  const reviewers = (rec.discipline_reviewers||[]).join(", ");
  const approvalPath = rec.approval_record_path || "";
  const hidden = previewActionsCollapsed ? " hidden" : "";
  const toggleIcon = previewActionsCollapsed ? "▲" : "▼";
  const toggleTitle = previewActionsCollapsed ? "展开操作栏" : "折叠操作栏";
  const metaParts = [STATUS_LABELS[st]||st, `负责人：${{escapeHtml(rec.discipline_owner||"")}}`, reviewers ? `评审员：${{escapeHtml(reviewers)}}` : "", rec.gate_state ? `Gate：${{escapeHtml(rec.gate_state)}}` : ""].filter(Boolean);
  const hd = `<div class="pa-hd">
    <div class="pa-hd-info">
      <span class="preview-actions-title">${{escapeHtml(nid)}}</span>
      <span class="preview-actions-meta">${{metaParts.join(" · ")}}</span>
    </div>
    <button class="pa-toggle" id="pa-toggle-btn" onclick="togglePreviewActions()" title="${{toggleTitle}}">${{toggleIcon}}</button>
  </div>`;
  if (isReadOnly) {{
    target.innerHTML = hd + `<div class="pa-body${{hidden}}" id="pa-body">
      <div class="preview-actions-readonly">${{escapeHtml(rec.gate_summary || "只读自动化 Gate，不写入审批记录。")}}</div>
      <div></div>
    </div>`;
    return;
  }}
  target.innerHTML = hd + `<div class="pa-body${{hidden}}" id="pa-body">
    <div class="preview-actions-grid">
      <textarea id="reviewer-${{escapeAttr(nid)}}" placeholder="评审备注（不影响审批状态）">${{escapeHtml(rec.reviewer_notes||"")}}</textarea>
      <textarea id="revision-${{escapeAttr(nid)}}" placeholder="修改意见：填写后点击要求修改">${{escapeHtml(rec.revision_notes||"")}}</textarea>
    </div>
    <div class="preview-actions-buttons">
      <button id="approve-${{escapeAttr(nid)}}" class="btn btn-approve" onclick="approve('${{escapeJs(nid)}}','${{escapeJs(approvalPath)}}')">批准</button>
      <button id="revision-btn-${{escapeAttr(nid)}}" class="btn btn-revision" onclick="requestRevision('${{escapeJs(nid)}}','${{escapeJs(approvalPath)}}')">要求修改</button>
      <button id="save-${{escapeAttr(nid)}}" class="btn btn-save" onclick="saveNotes('${{escapeJs(nid)}}','${{escapeJs(approvalPath)}}')">保存备注</button>
    </div>
  </div>`;
}}

function render() {{
  const approvalRecords = state.approval.records || [];
  const records = approvalRecords.concat(virtualGateRecords(approvalRecords));
  currentRecords = records;
  const grouped = {{}};
  for (const st of STATUS_ORDER) grouped[st] = [];
  for (const rec of records) {{
    const st = rec.gate_status || "pending";
    if (!grouped[st]) grouped[st] = [];
    grouped[st].push(rec);
  }}

  // Header chips
  const statsHtml = STATUS_ORDER
    .filter(st => grouped[st].length)
    .map(st => `<button class="stat-chip ${{STATUS_CHIP[st]}}" onclick="filterBy('${{st}}')">
      ${{STATUS_LABELS[st]}} ${{grouped[st].length}}
    </button>`).join("");
  document.getElementById("hd-stats").innerHTML = statsHtml;

  // Sidebar
  let sidebarHtml = "";
  for (const st of STATUS_ORDER) {{
    const items = grouped[st];
    if (!items.length) continue;
    sidebarHtml += `<div class="sidebar-section">
      <div class="sidebar-label">${{STATUS_LABELS[st]}}</div>`;
    for (const rec of items) {{
      const nid = getNodeId(rec);
      sidebarHtml += `<div class="sidebar-item ${{STATUS_SIDEBAR[st]||""}}" onclick="selectRecord('${{escapeJs(nid)}}')" title="${{escapeAttr(nid)}}">
        <span class="sidebar-dot ${{STATUS_DOT[st]||"dot-pending"}}"></span>
        <span class="sidebar-name">${{escapeHtml(nid)}}</span>
      </div>`;
    }}
    sidebarHtml += "</div>";
  }}
  document.getElementById("sidebar-body").innerHTML = sidebarHtml;

  // Main content
  const toShow = activeFilter
    ? STATUS_ORDER.filter(st => st === activeFilter)
    : STATUS_ORDER.filter(st => st !== "approved");

  let mainHtml = "";
  for (const st of toShow) {{
    const items = grouped[st];
    if (!items.length) continue;
    mainHtml += `<div class="section-head">
      <h2>${{{{"revision-requested":"⚠ 需要修改","in-review":"🔍 审核中","pending":"⏳ 待执行","approved":"✅ 已批准"}}[st]||st}}</h2>
      <span class="section-badge ${{STATUS_BADGE[st]||"badge-pending"}}">${{items.length}} 个节点</span>
    </div>
    <div class="cards">${{items.map(renderCard).join("")}}</div>`;
  }}

  if (!activeFilter && grouped["approved"].length) {{
    mainHtml += `<details style="margin-bottom:20px"><summary style="cursor:pointer;font-weight:600;color:#276749;padding:8px 0">✅ 已批准节点 (${{grouped["approved"].length}})</summary>
      <div class="cards" style="margin-top:10px">${{grouped["approved"].map(renderCard).join("")}}</div>
    </details>`;
  }}

  document.getElementById("main").innerHTML = "";
  if (activeNodeId) renderPreviewActions(recordByNodeId(activeNodeId));
}}

async function reloadRecords() {{
  await loadApproval();
  await loadGateStates();
  const focused = document.activeElement;
  if (focused && (focused.tagName === "TEXTAREA" || focused.tagName === "INPUT")) {{
    return;
  }}
  render();
}}

let openTabs = [];
let activeTabId = null;

function renderTabs() {{
  const bar = document.getElementById("tab-bar");
  if (!bar) return;
  const emptyEl = bar.querySelector(".tab-bar-empty");
  if (!openTabs.length) {{
    bar.innerHTML = "";
    if (emptyEl) bar.appendChild(emptyEl);
    return;
  }}
  const tabs = openTabs.map(tab => {{
    const active = tab.nodeId === activeTabId;
    return `<div class="preview-tab${{active?" active":""}}" onclick="switchTab('${{escapeJs(tab.nodeId)}}')" title="${{escapeAttr(tab.nodeId)}}">
      <span class="preview-tab-name">${{escapeHtml(tab.nodeId)}}</span>
      <button class="preview-tab-x" onclick="closeTab('${{escapeJs(tab.nodeId)}}',event)">✕</button>
    </div>`;
  }}).join("");
  bar.innerHTML = tabs;
}}

function switchTab(nodeId) {{
  if (activeTabId === nodeId) return;
  activeTabId = nodeId;
  activeNodeId = nodeId;
  const tab = openTabs.find(t => t.nodeId === nodeId);
  if (tab) {{
    const iframe = document.getElementById("preview-iframe");
    iframe.src = tab.href + "?ts=" + Date.now();
  }}
  renderPreviewActions(recordByNodeId(nodeId));
  renderTabs();
}}

function closeTab(nodeId, e) {{
  if (e) e.stopPropagation();
  openTabs = openTabs.filter(t => t.nodeId !== nodeId);
  if (activeTabId === nodeId) {{
    if (openTabs.length) {{
      const next = openTabs[openTabs.length - 1];
      activeTabId = next.nodeId;
      activeNodeId = next.nodeId;
      const iframe = document.getElementById("preview-iframe");
      iframe.src = next.href + "?ts=" + Date.now();
      renderPreviewActions(recordByNodeId(next.nodeId));
    }} else {{
      activeTabId = null;
      activeNodeId = null;
      document.getElementById("preview-panel").classList.remove("open");
      document.getElementById("preview-iframe").src = "about:blank";
      renderPreviewActions(null);
    }}
  }}
  renderTabs();
}}

function openPreview(href, nodeId) {{
  const existing = openTabs.find(t => t.nodeId === nodeId);
  if (!existing) {{
    openTabs.push({{nodeId, href}});
  }} else {{
    existing.href = href;
  }}
  activeTabId = nodeId;
  activeNodeId = nodeId;
  document.getElementById("preview-panel").classList.add("open");
  document.getElementById("preview-iframe").src = href + "?ts=" + Date.now();
  renderPreviewActions(recordByNodeId(nodeId));
  renderTabs();
}}

function closePreview() {{
  if (activeTabId) closeTab(activeTabId);
}}

function escapeHtml(v) {{ return String(v).replace(/[&<>"']/g,c=>({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c])); }}
function escapeAttr(v) {{ return escapeHtml(v); }}
function escapeJs(v) {{ return String(v).replace(/['\\\\]/g,"\\\\$&"); }}

function toggleSidebar() {{
  const sidebar = document.getElementById("sidebar");
  const btn = document.getElementById("sidebar-toggle");
  const collapsed = sidebar.classList.toggle("collapsed");
  btn.textContent = collapsed ? "›" : "‹";
  btn.title = collapsed ? "展开侧边栏" : "折叠侧边栏";
  try {{ localStorage.setItem("sidebarCollapsed", collapsed ? "1" : "0"); }} catch(e) {{}}
}}

function initSidebarState() {{
  try {{
    if (localStorage.getItem("sidebarCollapsed") === "1") {{
      const sidebar = document.getElementById("sidebar");
      const btn = document.getElementById("sidebar-toggle");
      sidebar.classList.add("collapsed");
      btn.textContent = "›";
      btn.title = "展开侧边栏";
    }}
  }} catch(e) {{}}
}}

render();
initSidebarState();
initPreviewActionsState();
loadGateStates().then(render);
setInterval(reloadRecords, 15000);
</script>
</body>
</html>
""",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
