#!/usr/bin/env python3
"""Validate bootstrap products: workflow.json + node-specs/*.md.

Checks:
  - workflow.json: schema valid, nodes non-empty, each node has node_id, goal/capability/exit_artifacts
  - workflow.json: consumers[]/hard_blocked_by[]/unlocks[]/alignment_refs[] references point to existing node IDs
  - workflow.json: exit_artifacts paths are not bare filenames
  - workflow.json nodes have matching node-specs, and node-specs are not orphaned
  - node-spec frontmatter matches workflow node_id, exit_artifacts, and graph fields
  - human_gate workflow nodes have matching approval records
  - app-design workflow closure emits handoff/QA artifacts and routes execution through concept-freeze
  - product routes with an end-user interface carry an experience design node, and the
    implementation of that interface is hard_blocked_by it
  - bootstrap-profile.json + workflow.json: mobile UI modules have platform UI automation
  - plan-confirmation.json: the delivered node set and hard_blocked_by edges match the plan
    the user actually confirmed, with user provenance and retained revision history
  - unattended-run-readiness-spec.json: each declared repair loop routes findings into the
    repair and holds closure for the QA rerun
  - workflow.json: a deferred effect proof names an existing downstream owner
  - node-specs/*.md: YAML frontmatter parseable, node_id field present
"""

import json
import os
from pathlib import Path
import re
import sys

from product_intent import JOURNAL as PRODUCT_JOURNAL, _journal_decision, validate_scope
from check_artifacts import DECLARE_HINT, freshness_admission, input_declaration_errors

try:
    import yaml
    _HAS_YAML = True
except ImportError:
    _HAS_YAML = False


def _node_id(node: dict, fallback: str = "") -> str:
    """Return the canonical workflow node identifier."""
    if not isinstance(node, dict):
        return fallback
    return node.get("node_id") or fallback


def _addressable_id(node_id) -> bool:
    """True when a value can actually name a node.

    An identifier keys a map, orders a report and anchors a blocker. Only a non-empty
    string does all three: a list or a dict raises when hashed, a number raises when
    ordered against a string, and neither names anything a user can act on.
    """
    return isinstance(node_id, str) and bool(node_id.strip())


def _addressable_nodes(raw_nodes) -> dict:
    """The subset of a node list every graph rule may read, keyed by identifier.

    Entries that cannot be addressed are dropped here rather than repaired: giving one
    a synthetic id would let a malformed record participate in routing decisions. They
    are reported by `workflow_shape_findings`, the one gate that owns node shape, so no
    rule below restates it and none of them can be reached by an identifier that raises.
    """
    nodes = {}
    for node in raw_nodes if isinstance(raw_nodes, list) else []:
        if isinstance(node, dict) and _addressable_id(node.get("node_id")):
            nodes[node["node_id"]] = node
    return nodes


def _lower_blob(value) -> str:
    """Serialize nested workflow/profile snippets for simple capability matching."""
    try:
        return json.dumps(value, ensure_ascii=False).lower()
    except TypeError:
        return str(value).lower()


def _load_json(path: str):
    with open(path) as f:
        return json.load(f)


def _artifact_path(item) -> str:
    if isinstance(item, dict):
        return item.get("path", "")
    return item


def _artifact_paths(items) -> list:
    if not isinstance(items, list):
        return []
    return [_artifact_path(item) for item in items]


def _read_node_spec(path: str) -> tuple:
    try:
        with open(path) as f:
            text = f.read()
    except Exception as e:
        return None, "", [f"cannot read: {e}"]

    if not text.startswith("---"):
        return None, text, ["no YAML frontmatter (missing opening ---)"]

    second = text.find("---", 3)
    if second == -1:
        return None, text, ["no closing --- for YAML frontmatter"]

    yaml_text = text[3:second].strip()
    if _HAS_YAML:
        try:
            data = yaml.safe_load(yaml_text)
        except Exception as e:
            return None, text, [f"YAML parse error: {e}"]
        if not isinstance(data, dict):
            return None, text, ["frontmatter is not a dict"]
        return data, text, []

    data = {}
    for line in yaml_text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data, text, []


REFERENCE_FIELDS = ("consumers", "hard_blocked_by", "unlocks", "alignment_refs")

# Capabilities that left /run. A workflow or node-spec generated before retirement is
# refused by name here rather than silently skipped or resolved against a missing file.
RETIRED_CAPABILITIES = {
    "hollowness-detector": (
        "the hollow verdict is cross-exam's, made after the pipeline by a party that did not "
        "write the code (ADR-0008); its machine-detectable patterns — a mock layer in served_by, "
        "a response identical to a canned fixture — are refusals in compute_completeness and "
        "the evidence-entry gate. Remove the node; run /cross-exam after /run instead"
    ),
}


def _retired_capability_error(node_id: str, capability) -> str:
    reason = RETIRED_CAPABILITIES.get(capability)
    if not reason:
        return ""
    return f"{node_id} names retired capability '{capability}': {reason}"


NODE_SPEC_REQUIRED_ATTENTION_TERMS = (
    "## Attention Contract",
    "Primary outcome",
    "Non-goals",
    "Must-read inputs",
    "Optional inputs",
    "Context budget",
    "Quality questions",
    "Stop conditions",
    "Repair targets",
)


APP_DESIGN_REQUIRED_NODES = {
    "ia-design",
    "user-flow-design",
    "interaction-design",
    "app-design-finalize",
}


APP_DESIGN_FINALIZE_REQUIRED_ARTIFACTS = {
    ".allforai/app-design/app-design-doc.json",
    ".allforai/app-design/app-design-doc.html",
    ".allforai/app-design/handoff/ui-design-input-handoff.json",
    ".allforai/app-design/handoff/program-development-node-handoff.json",
    ".allforai/app-design/qa/app-design-closure-qa-report.json",
}


# The experience-design contract, shared by the planning law and the gate below.
PRODUCT_ROUTES = ("new-product", "product-reconstruction")
EXPERIENCE_PRIORITY_MODES = ("consumer", "admin", "mixed", "none")
EXPERIENCE_DESIGN_MODES = ("consumer", "mixed")
APP_EXPERIENCE_DESIGN_ARTIFACTS = (
    ".allforai/app-design/concept/job-story-spec.json",
    ".allforai/app-design/spec/user-flow-spec.json",
    ".allforai/app-design/spec/screen-requirements-spec.json",
    ".allforai/app-design/spec/permissions-notifications-settings-spec.json",
)
# The structural floor: which journeys exist and what each screen owes them. The other two
# artifacts are planning law, judged by the node-spec audit, not by this gate.
APP_EXPERIENCE_DESIGN_REQUIRED = APP_EXPERIENCE_DESIGN_ARTIFACTS[1:3]
# Both paths are in live use in this repo; the design doc is the design wherever it sits.
GAME_EXPERIENCE_DESIGN_DOC_PATHS = (
    ".allforai/game-design/game-design-doc.json",
    ".allforai/game-design/design/game-design-doc.json",
)
UI_MODULE_ROLES = ("frontend", "mobile")
UI_IMPLEMENTATION_CAPABILITIES = ("implement", "translate", "ui-forge")
# Deliberately no bare "ui" or "expo": both hit build, require and export lines in any node.
UI_IMPLEMENTATION_TERMS = ("screen", "frontend", "front-end", "user interface", "界面", "页面",
                           "react native", "react-native", "flutter", "swiftui", "jetpack compose")
GAME_UI_IMPLEMENTATION_TERMS = ("scene", "hud", "gameplay", "canvas", "sprite")
# Where an identifier changes word: "SettingsScreen" names a screen, and lowercasing the
# text first would weld it into one word no boundary could find.
_CAMEL_CASE_SEAM = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


GAME_2D_PRODUCTION_REQUIRED_NODES = [
    "game-2d-runtime-profile",
    "game-2d-view-mode-runtime-contract",
    "game-2d-core-loop-playable-contract",
    "game-2d-asset-runtime-binding-contract",
    "game-2d-input-feedback-contract",
    "game-2d-session-flow-contract",
    "game-2d-visual-acceptance-criteria",
    "game-2d-playable-slice-assembly",
    "game-2d-core-loop-playability-qa",
    "game-2d-asset-binding-visual-qa",
    "game-2d-session-completion-qa",
    "game-2d-code-repair-loop",
    "game-2d-production-closure-qa",
]


GAME_2D_PRODUCTION_REQUIRED_ARTIFACTS = {
    ".allforai/game-2d/assembly/playable-slice-assembly-report.json",
    ".allforai/game-2d/qa/core-loop-playability-qa-report.json",
    ".allforai/game-2d/qa/asset-binding-visual-qa-report.json",
    ".allforai/game-2d/qa/session-completion-qa-report.json",
    ".allforai/game-2d/repair/code-repair-loop-report.json",
    ".allforai/game-2d/qa/revalidation-report.json",
    ".allforai/game-2d/qa/2d-production-closure-report.json",
    ".allforai/game-2d/qa/2d-production-closure.html",
}


CANVAS2D_GAME_CLIENT_MIN_NODE_COUNT = 12


CANVAS2D_RUNTIME_TERMS = (
    "canvas2d",
    "canvas 2d",
    "htmlcanvas",
    "htmlcanvaselement",
    "web canvas",
    "web-canvas",
    "webview canvas",
    "getcontext(\"2d\")",
    "getcontext('2d')",
)


CANVAS2D_MOBILE_TERMS = (
    "mobile",
    "ios",
    "android",
    "capacitor",
    "cordova",
    "webview",
    "app store",
    "google play",
)


CANVAS2D_AUDIO_TERMS = (
    "audio",
    "bgm",
    "sfx",
    "web audio",
    "audiocontext",
)


CANVAS2D_ART_TERMS = (
    "asset",
    "art",
    "sprite",
    "tileset",
    "texture",
    "icon",
)


CANVAS2D_REQUIRED_FAMILIES = {
    "runtime-core": (
        "runtime-core",
        "scene-manager",
        "renderer",
        "boot sequence",
        "progressmanager",
        "input manager",
    ),
    "interface-cards": (
        "interface-card",
        "interface cards",
        "interfaces/",
        "public module signatures",
        "preserved_exports",
    ),
    "asset-bundle": (
        "asset-bundle",
        "asset manifest",
        "preload",
        "resource manifest",
        "decoded resource",
    ),
    "scene-nodes": (
        "scene",
        "intro-scene",
        "gameplay-scene",
        "level-select",
        "map-scene",
        "dialog-scene",
        "shop-scene",
    ),
    "gameplay-system": (
        "gameplay-system",
        "matcher",
        "bfs",
        "core-loop",
        "obstacle",
        "special tile",
        "combo",
    ),
    "browser-qa": (
        "browser-qa",
        "playwright",
        "browser smoke",
        "runtime probe",
    ),
    "visual-qa": (
        "visual-qa",
        "visual acceptance",
        "screenshot",
        "codex visual",
    ),
    "gameplay-quality-qa": (
        "gameplay-quality",
        "playability",
        "solvability",
        "legal action",
        "rule invariant",
    ),
    "performance-qa": (
        "performance-qa",
        "performance budget",
        "fps",
        "memory",
        "render pressure",
    ),
    "qa-repair-loop": (
        "qa-repair-loop",
        "repair-loop",
        "repair and revalidation",
        "revalidation-report",
    ),
    "concept-acceptance": (
        "concept-acceptance",
        "concept acceptance",
        "acceptance-report",
        "missing_mappings",
        "missing behaviour mappings",
        "coverage gate",
    ),
}


CANVAS2D_REQUIRED_AUDIO_FAMILIES = {
    "audio-registry": (
        "audio-registry",
        "audio ids",
        "audio manifest",
        "sfx-manifest",
        "bgm-loop-manifest",
    ),
    "audio-style": (
        "audio-style",
        "sonic palette",
        "mix direction",
        "audio mood",
    ),
    "sfx-spec": (
        "sfx-spec",
        "event sfx",
        "sfx source strategy",
        "sfx-source-strategy",
    ),
    "audio-generation": (
        "sfx-procedural-generation",
        "sfx-source-adaptation",
        "bgm-loop-generation",
        "google lyria",
        "real audio files",
    ),
    "audio-system": (
        "audio-system",
        "audiomanager",
        "web audio",
        "loadbgm",
        "loadsfx",
    ),
    "audio-qa": (
        "audio-qa",
        "audio-loudness-qa",
        "audiobuffer",
        "audiocontext.state",
        "decoded buffer",
    ),
    "runtime-audio-import": (
        "runtime-audio-import",
        "engine-ready-audio-manifest",
        "runtime audio import",
        "actual playback",
        "playback validation",
    ),
}


VISIBLE_GAME_RUNTIME_TERMS = (
    "game-frontend",
    "game-ui",
    "gameplay",
    "runtime-gameplay-visual",
    "playable",
    "visual-qa",
    "screenshot",
    "scene",
    "hud",
)


VISUAL_QA_TERMS = (
    "runtime-gameplay-visual",
    "visual-qa",
    "visual acceptance",
    "ui-readability",
    "asset-binding-visual",
    "codex visual",
    "screenshot",
)


VISUAL_CRITERIA_TERMS = (
    "visual-acceptance-criteria",
    ".allforai/visual-qa/visual-acceptance-criteria.json",
    ".allforai/visual-qa/visual-acceptance-criteria.md",
)


PROGRESSION_MAP_TERMS = (
    "level-select",
    "level select",
    "world map",
    "mission map",
    "chapter map",
    "stage road",
    "progression route",
    "progression map",
    "选关",
    "关卡地图",
)


PROGRESSION_MAP_CRITERIA_TERMS = (
    "progression map acceptance",
    "progression_map_contract",
    "map metaphor",
    "node states",
    "label/icon",
    "prototype map geometry",
)


UI_TEST_PLATFORMS = {
    "android": {
        "display": "Android mobile UI",
        "runner_terms": (
            "connectedandroidtest",
            "espresso",
            "compose ui",
            "android-ui",
            "android ui",
            "maestro",
        ),
        "evidence_terms": (
            "android-ui-test-report",
            "android-logcat",
            "android-ui-screenshots",
            "connectedandroidtest",
        ),
    },
    "ios": {
        "display": "iOS mobile UI",
        "runner_terms": (
            "xcodebuild test",
            "xcuitest",
            "xctest",
            "ios-ui",
            "ios ui",
        ),
        "evidence_terms": (
            "ios-ui-test-report",
            "xcresult",
            "ios-ui-screenshots",
            "xcodebuild test",
        ),
    },
    "flutter": {
        "display": "Flutter mobile UI",
        "runner_terms": (
            "flutter test integration_test",
            "integration_test/",
            "patrol",
            "flutter-ui",
            "flutter ui",
        ),
        "evidence_terms": (
            "flutter-ui-test-report",
            "integration_test",
            "flutter-ui-screenshots",
            "patrol",
        ),
    },
    "react-native": {
        "display": "React Native mobile UI",
        "runner_terms": (
            "detox",
            "maestro",
            "react-native-ui",
            "react native ui",
        ),
        "evidence_terms": (
            "react-native-ui-test-report",
            "detox",
            "maestro",
            "rn-ui-screenshots",
        ),
    },
    "harmonyos": {
        "display": "HarmonyOS mobile UI",
        "runner_terms": (
            "hypium",
            "ohostest",
            "hdc",
            "harmony-ui",
            "harmonyos ui",
        ),
        "evidence_terms": (
            "harmony-ui-test-report",
            "hypium",
            "ohostest",
            "hdc",
        ),
    },
}


_GLOB_CHARS = re.compile(r"[*?\[]")


def _declaration_root(pattern: str) -> str:
    """The literal path a path declaration is rooted at, before any glob."""
    return _GLOB_CHARS.split(pattern, maxsplit=1)[0].rstrip("/")


def _covers(outer: str, outer_globbed: bool, inner: str) -> bool:
    if not outer:
        return True
    if inner == outer or inner.startswith(outer + "/"):
        return True
    # A glob root can stop mid-segment ('scripts/verify-*.ts'); a literal one cannot.
    return outer_globbed and inner.startswith(outer)


def _declarations_overlap(a: str, b: str) -> bool:
    root_a, root_b = _declaration_root(a), _declaration_root(b)
    return (_covers(root_b, bool(_GLOB_CHARS.search(b)), root_a)
            or _covers(root_a, bool(_GLOB_CHARS.search(a)), root_b))


def _string_list(value, *, allow_artifacts: bool = False) -> list:
    """The usable path/id strings in a declaration, ignoring malformed entries.

    Shape is reported by the checks that own it; a graph reading of a plan must not
    crash on the malformed value those checks are about to name.
    """
    if not isinstance(value, list):
        return []
    items = []
    for raw in value:
        if isinstance(raw, str) and raw:
            items.append(raw)
        elif allow_artifacts and isinstance(raw, dict) and isinstance(raw.get("path"), str) and raw["path"]:
            items.append(raw["path"])
    return items


def _dependency_edges(nodes: list) -> dict:
    """node_id -> the nodes it depends on: declared blockers plus the producers of
    the artifacts it consumes."""
    producers = {}
    for node in nodes:
        for field in ("exit_artifacts", "required_documents"):
            for raw in _string_list(node.get(field), allow_artifacts=True):
                producers[raw] = node["node_id"]
    edges = {}
    for node in nodes:
        deps = {d for d in _string_list(node.get("hard_blocked_by")) if _addressable_id(d)}
        for consumed in _string_list(node.get("input_dependencies")):
            producer = producers.get(consumed)
            if producer and producer != node["node_id"]:
                deps.add(producer)
        edges[node["node_id"]] = deps
    return edges


def _inverted_source_inputs(raw_nodes: list) -> list:
    """Refuse a plan whose freshness runs against the flow.

    A node's `source_inputs` are what it reads to produce its own work. When they
    reach into the write scope of a node that depends on it, delivering that work
    stales the node that planned it, and neither can publish again without
    reopening frozen work. See knowledge/input-freshness.md.
    """
    nodes = [n for n in raw_nodes if isinstance(n, dict) and _addressable_id(n.get("node_id"))]
    edges = _dependency_edges(nodes)
    by_id = {n["node_id"]: n for n in nodes}
    errors = []
    for node in nodes:
        nid = node["node_id"]
        sources = _string_list(node.get("source_inputs"))
        if not sources:
            continue
        reached, frontier = set(), {nid}
        while frontier:
            current = frontier.pop()
            for consumer, deps in edges.items():
                if current in deps and consumer not in reached:
                    reached.add(consumer)
                    frontier.add(consumer)
        for consumer in sorted(reached):
            scopes = _string_list(by_id[consumer].get("parallel_write_scopes"))
            overlap = next(((source, scope) for scope in scopes for source in sources
                            if _declarations_overlap(source, scope)), None)
            if overlap:
                source, scope = overlap
                errors.append(
                    f"inverted_source_inputs: workflow.json: {nid} source_input '{source}' lies in "
                    f"the write scope '{scope}' of '{consumer}', which depends on {nid}; delivering "
                    f"that work would stale the node that planned it. Declare what this node reads "
                    f"to produce its own work, not what the flow writes downstream"
                )
    return errors


def validate_workflow(wf_path: str) -> list:
    """Validate workflow.json schema."""
    errors = []
    try:
        wf = _load_json(wf_path)
    except Exception as e:
        return [f"workflow.json: cannot parse: {e}"]

    if "nodes" not in wf or not isinstance(wf["nodes"], list):
        errors.append("workflow.json: 'nodes' array missing or not a list")
        return errors

    if len(wf["nodes"]) == 0:
        errors.append("workflow.json: nodes array is empty")

    # Suspicious bare filenames that likely need a directory prefix
    SUSPICIOUS_BARE = {'.env', 'config.json', 'config.yaml', 'package.json',
                       'go.mod', 'Makefile', 'Dockerfile', 'README.md'}

    node_ids = set(_addressable_nodes(wf["nodes"]))

    for i, node in enumerate(wf["nodes"]):
        nid = _node_id(node, f"node[{i}]")
        if not isinstance(node, dict):
            errors.append(
                f"workflow.json: node[{i}] must be an object; a {type(node).__name__} carries "
                f"no node_id and no later check can read it"
            )
            continue
        if "id" in node:
            errors.append(f"workflow.json: {nid} uses forbidden legacy field 'id'; use 'node_id'")
        if "blocked_by" in node:
            errors.append(f"workflow.json: {nid} uses forbidden legacy field 'blocked_by'; use 'hard_blocked_by'")
        if not node.get("node_id"):
            errors.append(f"workflow.json: node[{i}] missing 'node_id'")
        elif not _addressable_id(node["node_id"]):
            errors.append(
                f"workflow.json: node[{i}] 'node_id' must be a non-empty string, got "
                f"{node['node_id']!r}; a node the graph cannot address can be neither "
                f"blocked, repaired nor reported"
            )
        if not _addressable_id(node.get("node_id")):
            # Shape precedes semantics. Every check below reports against this node's
            # identifier, and the freshness admission reader keys its record sets by it;
            # a node the graph cannot address has no field verdict worth reporting and
            # would raise on the first set membership test.
            continue
        if "goal" not in node:
            errors.append(f"workflow.json: {nid} missing 'goal'")
        if "capability" not in node:
            errors.append(f"workflow.json: {nid} missing 'capability'")
        elif not isinstance(node["capability"], str) or not node["capability"]:
            errors.append(f"workflow.json: {nid} 'capability' must be a non-empty string")
        elif _retired_capability_error(nid, node["capability"]):
            errors.append(f"workflow.json: {_retired_capability_error(nid, node['capability'])}")
        if "exit_artifacts" not in node:
            errors.append(f"workflow.json: {nid} missing 'exit_artifacts'")
        elif not isinstance(node["exit_artifacts"], list):
            errors.append(f"workflow.json: {nid} exit_artifacts must be a list")
        else:
            for raw in node["exit_artifacts"]:
                artifact_path = _artifact_path(raw)
                basename = os.path.basename(artifact_path)
                if artifact_path == basename and basename in SUSPICIOUS_BARE:
                    errors.append(
                        f"workflow.json: {nid} exit_artifact '{artifact_path}' "
                        f"looks like a bare filename — use full project-relative "
                        f"path (e.g., 'subdir/{artifact_path}' not '{artifact_path}')"
                    )

        for problem in input_declaration_errors(node):
            errors.append(f"workflow.json: {nid} {problem}")
        if freshness_admission(node, wf, Path(wf_path).resolve().parents[2]) == "missing":
            errors.append(
                f"workflow.json: {nid} missing 'source_inputs'; intent-aware work must {DECLARE_HINT} "
                f"so evidence freshness can trace it"
            )

        for field in REFERENCE_FIELDS:
            if field not in node:
                continue
            if not isinstance(node[field], list):
                errors.append(f"workflow.json: {nid} '{field}' must be a list")
                continue
            for cid in node[field]:
                if not _addressable_id(cid):
                    errors.append(
                        f"workflow.json: {nid} {field} entry must be a non-empty node id, "
                        f"got {cid!r}"
                    )
                elif cid not in node_ids:
                    errors.append(
                        f"workflow.json: {nid} {field} references "
                        f"non-existent node '{cid}'"
                    )

    errors.extend(_inverted_source_inputs(wf["nodes"]))

    return errors


def _profile_has_mobile_ui_module(profile: dict) -> bool:
    """Detect mobile app modules with user-facing screens."""
    for module in profile.get("modules", []):
        module_blob = _lower_blob(module)
        if module.get("role") == "mobile" and (
            "ui" in module_blob
            or "screen" in module_blob
            or "compose" in module_blob
            or "app/" in module_blob
            or "android" in module_blob
        ):
            return True

    return False


def _required_mobile_ui_platforms(profile: dict) -> list:
    """Infer platform-specific UI automation requirements from bootstrap profile."""
    if not _profile_has_mobile_ui_module(profile):
        return []

    blob = _lower_blob(profile)
    required = []

    if "flutter" in blob:
        required.append("flutter")
    if "react native" in blob or "react-native" in blob or "expo" in blob:
        required.append("react-native")
    if "harmonyos" in blob or "arkts" in blob or "deveco" in blob or "hypium" in blob:
        required.append("harmonyos")

    native_mobile_frameworks = {"flutter", "react-native", "harmonyos"}
    if not any(platform in required for platform in native_mobile_frameworks):
        if (
            "ios" in blob
            or "swiftui" in blob
            or "swift" in blob
            or "xcodebuild" in blob
            or "xcuitest" in blob
        ):
            required.append("ios")
        if (
            "android" in blob
            or "kotlin" in blob
            or "jetpack compose" in blob
            or "connectedandroidtest" in blob
        ):
            required.append("android")

    return required


def _node_blob(node: dict, specs_dir: str) -> str:
    nid = _node_id(node)
    blob = _lower_blob(node)
    spec_path = os.path.join(specs_dir, f"{nid}.md")
    if os.path.exists(spec_path):
        try:
            with open(spec_path) as f:
                blob += "\n" + f.read().lower()
        except Exception:
            pass
    return blob


def _read_text_if_exists(path: str) -> str:
    try:
        if os.path.exists(path):
            with open(path) as f:
                return f.read()
    except Exception:
        return ""
    return ""


def _workflow_and_specs_blob(bdir: str, workflow: dict) -> str:
    specs_dir = os.path.join(bdir, "node-specs")
    parts = [_lower_blob(workflow)]
    for name in (
        "bootstrap-profile.json",
        "canvas2d-game-client-profile.json",
        "unattended-run-readiness-spec.json",
    ):
        parts.append(_read_text_if_exists(os.path.join(bdir, name)).lower())
    if os.path.isdir(specs_dir):
        for fname in sorted(os.listdir(specs_dir)):
            if fname.endswith(".md"):
                parts.append(_read_text_if_exists(os.path.join(specs_dir, fname)).lower())
    return "\n".join(parts)


def _contains_any(blob: str, terms: tuple[str, ...]) -> bool:
    return any(term in blob for term in terms)


def _scope_lock_excludes_audio(bdir: str) -> bool:
    """Return true only when a project-level scope lock explicitly cuts audio."""
    candidates = [
        os.path.join(bdir, "scope-lock.json"),
        os.path.join(os.path.dirname(bdir), "scope-lock.json"),
        os.path.join(os.path.dirname(os.path.dirname(bdir)), ".allforai", "scope-lock.json"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        try:
            data = _load_json(path)
        except Exception:
            continue
        blob = _lower_blob(data)
        if (
            ("audio" in blob or "sfx" in blob or "bgm" in blob or "音效" in blob or "音乐" in blob)
            and "approved_before_run" in blob
            and "true" in blob
        ):
            return True
    return False


def _canvas2d_game_client_detected(bdir: str, workflow: dict) -> bool:
    """Detect project-local Canvas2D/Web Canvas game clients."""
    blob = _workflow_and_specs_blob(bdir, workflow)
    has_canvas_runtime = _contains_any(blob, CANVAS2D_RUNTIME_TERMS)
    has_game_context = any(
        term in blob
        for term in (
            "game",
            "gameplay",
            "game-design",
            "level",
            "scene",
            "tile",
            "连连看",
            "onet",
        )
    )
    has_canvas_profile = os.path.exists(os.path.join(bdir, "canvas2d-game-client-profile.json"))
    return (has_canvas_runtime and has_game_context) or has_canvas_profile


def _matching_nodes(workflow: dict, specs_dir: str, terms: tuple[str, ...]) -> list[dict]:
    matched = []
    for node in workflow.get("nodes", []):
        if _contains_any(_node_blob(node, specs_dir), terms):
            matched.append(node)
    return matched


def _family_present(workflow: dict, specs_dir: str, terms: tuple[str, ...]) -> bool:
    return bool(_matching_nodes(workflow, specs_dir, terms))


def _node_own_blob(node: dict) -> str:
    """Serialize only workflow-owned node metadata, not the whole spec body."""
    return _lower_blob(node)


def _matching_nodes_by_contract(workflow: dict, terms: tuple[str, ...]) -> list[dict]:
    return [
        node
        for node in workflow.get("nodes", [])
        if _contains_any(_node_own_blob(node), terms)
    ]


def _ui_node_present(workflow: dict, specs_dir: str, platform: str) -> bool:
    """Return true when workflow contains a real platform UI automation node."""
    spec = UI_TEST_PLATFORMS[platform]
    runner_terms = spec["runner_terms"]
    evidence_terms = spec["evidence_terms"]

    for node in workflow.get("nodes", []):
        node_blob = _node_blob(node, specs_dir)

        if not any(term in node_blob for term in runner_terms):
            continue

        manual_only = (
            "manual — requires device" in node_blob
            or "manual - requires device" in node_blob
            or "document manual test scenarios" in node_blob
        )
        has_runner = any(term in node_blob for term in runner_terms)
        has_evidence = any(term in node_blob for term in evidence_terms)
        has_blocked_env = "blocked_env" in node_blob or "failed_env" in node_blob

        if has_runner and (has_evidence or has_blocked_env) and not manual_only:
            return True

    return False


def validate_mobile_ui_coverage(bdir: str) -> list:
    """Ensure mobile UI projects do not lose platform UI automation at bootstrap."""
    errors = []
    profile_path = os.path.join(bdir, "bootstrap-profile.json")
    workflow_path = os.path.join(bdir, "workflow.json")
    specs_dir = os.path.join(bdir, "node-specs")

    if not os.path.exists(profile_path) or not os.path.exists(workflow_path):
        return errors

    try:
        profile = _load_json(profile_path)
        workflow = _load_json(workflow_path)
    except Exception:
        return errors

    for platform in _required_mobile_ui_platforms(profile):
        if not _ui_node_present(workflow, specs_dir, platform):
            spec = UI_TEST_PLATFORMS[platform]
            errors.append(
                f"workflow.json: {spec['display']} module detected, but no platform UI "
                f"automation node with runner evidence was found. Generate a dedicated "
                f"UI automation/e2e-test node for {platform} and report BLOCKED_ENV if "
                f"the required device, simulator, emulator, or service is unavailable; "
                f"do not replace it with manual scenarios."
            )

    return errors


def validate_canvas2d_game_client_profile_flow(bdir: str) -> list:
    """Ensure Canvas2D game clients expand into production-grade nodes and QA."""
    errors = []
    workflow_path = os.path.join(bdir, "workflow.json")
    specs_dir = os.path.join(bdir, "node-specs")
    if not os.path.exists(workflow_path):
        return errors

    try:
        workflow = _load_json(workflow_path)
    except Exception:
        return errors

    if not _canvas2d_game_client_detected(bdir, workflow):
        return errors

    blob = _workflow_and_specs_blob(bdir, workflow)
    nodes = {
        node.get("node_id"): node
        for node in workflow.get("nodes", [])
        if node.get("node_id")
    }

    profile_path = os.path.join(bdir, "canvas2d-game-client-profile.json")
    if not os.path.exists(profile_path):
        errors.append(
            "workflow.json: Canvas2D game client detected, but "
            ".allforai/bootstrap/canvas2d-game-client-profile.json is missing"
        )

    canvas_nodes = _matching_nodes(workflow, specs_dir, CANVAS2D_RUNTIME_TERMS + ("gameplay", "scene"))
    if len(canvas_nodes) < CANVAS2D_GAME_CLIENT_MIN_NODE_COUNT:
        errors.append(
            "workflow.json: Canvas2D game client profile under-expanded; "
            f"found {len(canvas_nodes)} relevant nodes, expected at least "
            f"{CANVAS2D_GAME_CLIENT_MIN_NODE_COUNT}. Bootstrap must expand "
            "runtime core, scenes, gameplay systems, QA, repair loop, and "
            "concept acceptance instead of only scaffold/build/smoke nodes."
        )

    missing_families = []
    for family, terms in CANVAS2D_REQUIRED_FAMILIES.items():
        if not _family_present(workflow, specs_dir, terms):
            missing_families.append(family)

    audio_scope_locked = _scope_lock_excludes_audio(bdir)
    if not audio_scope_locked:
        for family, terms in CANVAS2D_REQUIRED_AUDIO_FAMILIES.items():
            if not _family_present(workflow, specs_dir, terms):
                missing_families.append(family)

    if _contains_any(blob, CANVAS2D_ART_TERMS):
        for family, terms in {
            "art-quality-qa": ("art-quality", "asset-binding-visual", "sprite readability", "runtime asset binding"),
        }.items():
            if not _family_present(workflow, specs_dir, terms):
                missing_families.append(family)

    if _contains_any(blob, CANVAS2D_MOBILE_TERMS):
        for family, terms in {
            "platform-build": ("ios-build", "android-sim", "capacitor", "xcodebuild", "gradle"),
            "dpr-screenshot-qa": ("devicescalefactor", "dpr", "central gameplay region"),
        }.items():
            if not _family_present(workflow, specs_dir, terms):
                missing_families.append(family)

    if missing_families:
        errors.append(
            "workflow.json: Canvas2D game client workflow missing required "
            f"profile families {sorted(set(missing_families))}"
        )
    if not audio_scope_locked and not _contains_any(blob, ("game-audio", "runtime-audio-import")):
        errors.append(
            "workflow.json: Canvas2D game production requires a full audio closure "
            "chain unless .allforai/scope-lock.json explicitly excludes audio before run"
        )

    qa_nodes = [
        node
        for node in workflow.get("nodes", [])
        if _contains_any(
            _node_blob(node, specs_dir),
            ("qa", "verify", "smoke", "visual", "test", "performance", "acceptance"),
        )
    ]
    if len(qa_nodes) < 5:
        errors.append(
            "workflow.json: Canvas2D game client needs a QA matrix, not a single smoke test; "
            f"found {len(qa_nodes)} QA/verify nodes, expected browser, visual, gameplay, "
            "performance/DPR, and final acceptance at minimum"
        )

    repair_nodes = _matching_nodes_by_contract(workflow, ("qa-repair-loop", "repair-loop", "revalidation-report"))
    acceptance_nodes = _matching_nodes_by_contract(workflow, ("concept-acceptance", "acceptance-report"))
    if qa_nodes and not repair_nodes:
        errors.append("workflow.json: Canvas2D QA nodes require a qa-repair-loop node")
    if repair_nodes and acceptance_nodes:
        repair_ids = {node["node_id"] for node in repair_nodes if node.get("node_id")}
        for acceptance in acceptance_nodes:
            blockers = set(acceptance.get("hard_blocked_by") or [])
            if not blockers.intersection(repair_ids):
                errors.append(
                    f"workflow.json: {acceptance.get('node_id')} must be hard_blocked_by "
                    "the Canvas2D qa-repair-loop"
                )
    elif not acceptance_nodes:
        errors.append("workflow.json: Canvas2D game client requires final concept-acceptance")

    effect_terms = (
        "effect verification",
        "runtime evidence",
        "runtime-effect",
        "screenshot",
        "decoded buffer",
        "production consumer",
        "module_wiring_proofs",
    )
    effect_node_id_terms = (
        "canvas2d",
        "gameplay-scene",
        "scene-manager",
        "audio-system",
        "vfx",
        "asset-bundle",
        "backend-client",
        "platform-plugins",
    )
    excluded_effect_node_terms = (
        "qa",
        "verify",
        "test",
        "repair",
        "acceptance",
        "compile",
        "build",
        "profile",
        "contract",
        "interface",
        "spec",
    )
    for node_id, node in sorted(nodes.items()):
        node_blob = _node_blob(node, specs_dir)
        node_id_blob = node_id.lower()
        is_visible_or_runtime = _contains_any(node_id_blob, effect_node_id_terms)
        is_excluded = _contains_any(node_id_blob, excluded_effect_node_terms)
        is_planning_only = _contains_any(node_blob, ("interface-card", "spec", "contract", "profile"))
        if is_visible_or_runtime and not is_excluded and not is_planning_only and not _contains_any(node_blob, effect_terms):
            errors.append(
                f"node-specs/{node_id}.md: Canvas2D runtime node completion must include "
                "effect verification, not only code creation"
            )

    return errors


def validate_game_visual_acceptance_standard_flow(bdir: str) -> list:
    """Ensure visible game workflows generate visual standards before screenshot QA."""
    errors = []
    workflow_path = os.path.join(bdir, "workflow.json")
    specs_dir = os.path.join(bdir, "node-specs")
    if not os.path.exists(workflow_path):
        return errors

    try:
        workflow = _load_json(workflow_path)
    except Exception:
        return errors

    blob = _workflow_and_specs_blob(bdir, workflow)
    has_visible_game = _contains_any(blob, VISIBLE_GAME_RUNTIME_TERMS) and (
        "game" in blob or "game-design" in blob
    )
    visual_qa_nodes = _matching_nodes(workflow, specs_dir, VISUAL_QA_TERMS)
    if not has_visible_game and not visual_qa_nodes:
        return errors

    criteria_nodes = _matching_nodes(workflow, specs_dir, VISUAL_CRITERIA_TERMS)
    if not criteria_nodes:
        errors.append(
            "workflow.json: visible game UI/runtime workflow requires a visual "
            "acceptance criteria producer before screenshot/visual QA nodes"
        )
        return errors

    required_artifacts = {
        ".allforai/visual-qa/visual-acceptance-criteria.json",
        ".allforai/visual-qa/visual-acceptance-criteria.md",
        ".allforai/visual-qa/visual-evidence-requirements.json",
    }
    criteria_ids = {node["node_id"] for node in criteria_nodes if node.get("node_id")}
    for node in criteria_nodes:
        artifacts = set(_artifact_paths(node.get("exit_artifacts")))
        missing = sorted(required_artifacts - artifacts)
        if missing:
            errors.append(
                f"workflow.json: {node.get('node_id')} visual criteria node missing "
                f"required exit_artifacts {missing}"
            )

    for node in visual_qa_nodes:
        node_id = node.get("node_id")
        if node_id in criteria_ids:
            continue
        blockers = set(node.get("hard_blocked_by") or [])
        if not blockers.intersection(criteria_ids):
            errors.append(
                f"workflow.json: visual QA node '{node_id}' must be hard_blocked_by "
                "the visual acceptance criteria producer"
            )

    if _contains_any(blob, PROGRESSION_MAP_TERMS):
        criteria_blob = "\n".join(_node_blob(node, specs_dir) for node in criteria_nodes)
        if not _contains_any(criteria_blob, PROGRESSION_MAP_CRITERIA_TERMS):
            errors.append(
                "workflow.json: level-select/world-map/progression route detected, "
                "but visual acceptance criteria node-spec does not define progression "
                "map acceptance standards"
            )

    return errors


def validate_node_spec_coverage(bdir: str) -> list:
    """Ensure workflow nodes and node-spec files stay in sync."""
    errors = []
    workflow_path = os.path.join(bdir, "workflow.json")
    specs_dir = os.path.join(bdir, "node-specs")
    if not os.path.exists(workflow_path) or not os.path.isdir(specs_dir):
        return errors

    try:
        workflow = _load_json(workflow_path)
    except Exception:
        return errors

    node_ids = {_node_id(node) for node in workflow.get("nodes", []) if _node_id(node)}
    spec_ids = {
        os.path.splitext(fname)[0]
        for fname in os.listdir(specs_dir)
        if fname.endswith(".md")
    }

    for node_id in sorted(node_ids - spec_ids):
        errors.append(f"node-specs: workflow node '{node_id}' has no matching node-spec file")
    for spec_id in sorted(spec_ids - node_ids):
        errors.append(f"node-specs/{spec_id}.md: no matching workflow node")

    return errors


def validate_node_spec_contracts(bdir: str) -> list:
    """Ensure node-spec frontmatter mirrors workflow node contracts."""
    errors = []
    workflow_path = os.path.join(bdir, "workflow.json")
    specs_dir = os.path.join(bdir, "node-specs")
    if not os.path.exists(workflow_path) or not os.path.isdir(specs_dir):
        return errors

    try:
        workflow = _load_json(workflow_path)
    except Exception:
        return errors

    nodes = {node.get("node_id"): node for node in workflow.get("nodes", []) if node.get("node_id")}
    for node_id, node in sorted(nodes.items()):
        spec_path = os.path.join(specs_dir, f"{node_id}.md")
        if not os.path.exists(spec_path):
            continue
        data, text, spec_errors = _read_node_spec(spec_path)
        if spec_errors:
            continue

        spec_node_id = data.get("node_id") or ""
        if spec_node_id != node_id:
            errors.append(
                f"node-specs/{node_id}.md: frontmatter node_id '{spec_node_id}' "
                f"does not match workflow node_id '{node_id}'"
            )

        if "exit_artifacts" in data:
            spec_paths = _artifact_paths(data.get("exit_artifacts"))
            workflow_paths = _artifact_paths(node.get("exit_artifacts"))
            if spec_paths != workflow_paths:
                errors.append(
                    f"node-specs/{node_id}.md: frontmatter exit_artifacts {spec_paths} "
                    f"do not match workflow exit_artifacts {workflow_paths}"
                )

        for field in ("hard_blocked_by", "alignment_refs", "unlocks"):
            if field in data:
                spec_value = data.get(field) or []
                workflow_value = node.get(field) or []
                if spec_value != workflow_value:
                    errors.append(
                        f"node-specs/{node_id}.md: frontmatter {field} {spec_value} "
                        f"does not match workflow {field} {workflow_value}"
                    )

        for field in ("requirement_refs", "responsibilities", "decision_inputs", "product_goals", "acceptance"):
            if node.get("requirement_refs") and data.get(field) != node.get(field):
                errors.append(f"node-specs/{node_id}.md: frontmatter {field} must match workflow {field}")

        # Both directions: a contract declared on one side only is invisible to the gates
        # that read the other. A document promised in the spec alone has no workflow
        # entry to verify, and a deferred effect owner named there alone routes nothing.
        for field in ('source_inputs', 'input_dependencies', 'parallel_write_scopes', 'required_documents',
                      'document_verification', 'downstream_effect_owner'):
            if field not in node and field not in data:
                continue
            if data.get(field) == node.get(field):
                continue
            if field not in node:
                code = ("missing_document_contract" if field.startswith(("required_doc", "document_"))
                        else "unowned_effect_stage" if field == "downstream_effect_owner" else "")
                errors.append(
                    f"{code + ': ' if code else ''}node-specs/{node_id}.md: frontmatter {field} "
                    f"is not declared on the workflow node; declare it in both or in neither"
                )
            else:
                errors.append(f"node-specs/{node_id}.md: frontmatter {field} must match workflow {field}")

        for term in NODE_SPEC_REQUIRED_ATTENTION_TERMS:
            if term not in text:
                errors.append(
                    f"node-specs/{node_id}.md: missing attention contract term {term!r}"
                )

    return errors


def validate_approval_records(bdir: str) -> list:
    """Ensure human_gate nodes and approval-records.json stay in sync."""
    errors = []
    workflow_path = os.path.join(bdir, "workflow.json")
    if not os.path.exists(workflow_path):
        return errors

    try:
        workflow = _load_json(workflow_path)
    except Exception:
        return errors

    nodes = [node for node in workflow.get("nodes", []) if node.get("human_gate") is True]
    if not nodes:
        return errors

    by_path = {}
    for node in nodes:
        node_id = node.get("node_id", "?")
        record_path = node.get("approval_record_path")
        if not record_path:
            errors.append(f"workflow.json: {node_id} human_gate missing approval_record_path")
            continue
        by_path.setdefault(record_path, []).append(node)

    for record_path, gated_nodes in sorted(by_path.items()):
        abs_path = os.path.join(os.path.dirname(bdir), "..", record_path)
        abs_path = os.path.normpath(abs_path)
        if not os.path.exists(abs_path):
            errors.append(f"{record_path}: approval records file missing")
            continue
        try:
            data = _load_json(abs_path)
        except Exception as e:
            errors.append(f"{record_path}: cannot parse: {e}")
            continue

        records = data.get("records")
        if not isinstance(records, list):
            errors.append(f"{record_path}: 'records' array missing or not a list")
            continue

        record_by_node = {}
        for index, record in enumerate(records):
            if "node" in record:
                errors.append(f"{record_path}: records[{index}] uses forbidden legacy field 'node'")
            record_node_id = record.get("node_id")
            if not record_node_id:
                errors.append(f"{record_path}: records[{index}] missing node_id")
                continue
            if record_node_id in record_by_node:
                errors.append(f"{record_path}: duplicate record for node_id '{record_node_id}'")
            record_by_node[record_node_id] = record

        expected_ids = {node["node_id"] for node in gated_nodes}
        actual_ids = set(record_by_node)
        for missing in sorted(expected_ids - actual_ids):
            errors.append(f"{record_path}: missing approval record for node_id '{missing}'")
        for extra in sorted(actual_ids - expected_ids):
            errors.append(f"{record_path}: approval record for non-human_gate node_id '{extra}'")

        for node in gated_nodes:
            node_id = node["node_id"]
            record = record_by_node.get(node_id)
            if not record:
                continue
            if (record.get("unlocks") or []) != (node.get("unlocks") or []):
                errors.append(
                    f"{record_path}: record '{node_id}' unlocks {record.get('unlocks') or []} "
                    f"do not match workflow unlocks {node.get('unlocks') or []}"
                )

            checklist = record.get("review_checklist")
            if checklist is not None and not isinstance(checklist, list):
                errors.append(f"{record_path}: record '{node_id}' review_checklist must be a list")

    return errors


def validate_app_design_flow(bdir: str) -> list:
    """Validate app-design planning closes into downstream implementation contracts."""
    errors = []
    workflow_path = os.path.join(bdir, "workflow.json")
    if not os.path.exists(workflow_path):
        return errors

    try:
        workflow = _load_json(workflow_path)
    except Exception:
        return errors

    nodes = {node.get("node_id"): node for node in workflow.get("nodes", []) if node.get("node_id")}
    app_nodes = {
        node_id: node
        for node_id, node in nodes.items()
        if node.get("capability") == "app-design" or node_id in APP_DESIGN_REQUIRED_NODES
    }
    if not app_nodes:
        return errors

    missing_required = sorted(APP_DESIGN_REQUIRED_NODES - set(nodes))
    for node_id in missing_required:
        errors.append(f"workflow.json: app-design workflow missing required node '{node_id}'")

    finalize = nodes.get("app-design-finalize")
    if not finalize:
        return errors

    expected_blockers = sorted(node_id for node_id in app_nodes if node_id != "app-design-finalize")
    actual_blockers = sorted(finalize.get("hard_blocked_by") or [])
    missing_blockers = sorted(set(expected_blockers) - set(actual_blockers))
    if missing_blockers:
        errors.append(
            "workflow.json: app-design-finalize hard_blocked_by missing "
            f"selected app-design nodes {missing_blockers}"
        )

    finalize_artifacts = set(_artifact_paths(finalize.get("exit_artifacts")))
    missing_artifacts = sorted(APP_DESIGN_FINALIZE_REQUIRED_ARTIFACTS - finalize_artifacts)
    if missing_artifacts:
        errors.append(
            "workflow.json: app-design-finalize missing required handoff/closure "
            f"exit_artifacts {missing_artifacts}"
        )

    concept_freeze = nodes.get("concept-freeze")
    if not concept_freeze:
        errors.append("workflow.json: app-design workflow missing concept-freeze node")
    elif "app-design-finalize" not in (concept_freeze.get("hard_blocked_by") or []):
        errors.append("workflow.json: concept-freeze must be hard_blocked_by app-design-finalize")

    for node_id, node in sorted(nodes.items()):
        if node_id == "concept-freeze":
            continue
        if node_id in app_nodes:
            continue
        if "app-design-finalize" in (node.get("hard_blocked_by") or []):
            errors.append(
                f"workflow.json: {node_id} depends directly on app-design-finalize; "
                "depend on concept-freeze instead"
            )

    return errors


def _project_root_from_bootstrap_dir(bdir: str) -> str:
    return os.path.abspath(os.path.join(bdir, "..", ".."))


def _game_2d_handoff_required(project_root: str) -> bool:
    handoff_path = os.path.join(
        project_root,
        ".allforai/game-design/design/program-development-node-handoff.json",
    )
    if not os.path.exists(handoff_path):
        return False

    try:
        handoff = _load_json(handoff_path)
    except Exception:
        return False

    blob = _lower_blob(handoff)
    if "game_2d_production" in blob:
        return True

    # Older handoff files may predate the explicit game_2d_production block.
    # Treat clear 2D client/runtime evidence as requiring the same expansion so
    # stale bootstraps are forced to regenerate instead of silently skipping
    # final 2D production closure.
    two_d_terms = (
        "2d",
        "web-canvas",
        "cocos",
        "phaser",
        "godot_2d",
        "unity_2d",
        "canvas",
    )
    implementation_nodes = handoff.get("implementation_nodes")
    has_program_nodes = isinstance(implementation_nodes, list) and bool(implementation_nodes)
    return has_program_nodes and any(term in blob for term in two_d_terms)


def validate_game_2d_production_flow(bdir: str) -> list:
    """Validate that 2D game handoff expands into concrete production nodes."""
    errors = []
    workflow_path = os.path.join(bdir, "workflow.json")
    specs_dir = os.path.join(bdir, "node-specs")
    if not os.path.exists(workflow_path):
        return errors

    project_root = _project_root_from_bootstrap_dir(bdir)
    if not _game_2d_handoff_required(project_root):
        return errors
    try:
        workflow = _load_json(workflow_path)
    except Exception:
        return errors

    nodes = {node.get("node_id"): node for node in workflow.get("nodes", []) if node.get("node_id")}
    missing_nodes = [node_id for node_id in GAME_2D_PRODUCTION_REQUIRED_NODES if node_id not in nodes]
    if missing_nodes:
        errors.append(
            "workflow.json: game 2D production handoff detected, but workflow is missing "
            f"required game-2d-production nodes {missing_nodes}"
        )
        return errors

    for previous, current in zip(
        GAME_2D_PRODUCTION_REQUIRED_NODES,
        GAME_2D_PRODUCTION_REQUIRED_NODES[1:],
    ):
        blockers = nodes[current].get("hard_blocked_by") or []
        if previous not in blockers:
            errors.append(
                f"workflow.json: {current} must be hard_blocked_by {previous} "
                "for ordered 2D production closure"
            )

    closure = nodes["game-2d-production-closure-qa"]
    closure_artifacts = set(_artifact_paths(closure.get("exit_artifacts")))
    missing_artifacts = sorted(GAME_2D_PRODUCTION_REQUIRED_ARTIFACTS - closure_artifacts)
    if missing_artifacts:
        errors.append(
            "workflow.json: game-2d-production-closure-qa missing required exit_artifacts "
            f"{missing_artifacts}"
        )

    for node_id in GAME_2D_PRODUCTION_REQUIRED_NODES:
        spec_path = os.path.join(specs_dir, f"{node_id}.md")
        if not os.path.exists(spec_path):
            continue
        try:
            with open(spec_path) as f:
                spec_text = f.read()
        except Exception:
            continue
        if "game-2d-production/" not in spec_text and "visual-qa/20-spec/visual-acceptance-criteria" not in spec_text:
            errors.append(
                f"node-specs/{node_id}.md: game 2D production node-spec must delegate "
                "to a game-2d-production child skill or the visual acceptance criteria skill"
            )

    return errors


PLAN_CONFIRMATION = "plan-confirmation.json"
PLAN_JOURNAL = ".allforai/bootstrap/plan-confirmation-journal.json"
CANONICAL_ROUTES = ("local-change", "product-reconstruction", "new-product")
RETURN_TO_BOOTSTRAP = "return to interactive /bootstrap Phase A"


def _text(value) -> bool:
    """True when a recorded field carries actual content rather than a placeholder."""
    return isinstance(value, str) and bool(value.strip())


def _completed_node_ids(workflow: dict) -> set:
    """Node ids whose latest recorded transition is completed, folding both log formats."""
    latest = {}
    history = workflow.get("transition_log")
    for event in history if isinstance(history, list) else []:
        if not isinstance(event, dict):
            continue
        node_id = event.get("node_id") or event.get("node")
        if _text(node_id):
            latest[node_id] = event.get("status")
    return {node_id for node_id, status in latest.items() if status == "completed"}


def _plan_shape(nodes) -> dict:
    """The plan a user can actually confirm: node ids plus their hard_blocked_by edges."""
    shape = {}
    for node in nodes if isinstance(nodes, list) else []:
        if not isinstance(node, dict):
            continue
        node_id = _node_id(node)
        if not _text(node_id):
            continue
        edges = node.get("hard_blocked_by") or []
        shape[node_id] = sorted(e for e in edges if _text(e)) if isinstance(edges, list) else []
    return shape


def _plan_shape_errors(plan, label: str) -> list:
    """Structural faults in a recorded graph. Malformed shapes are refused, never repaired:
    sanitizing a null, a string or a mixed edge list into `[]` would let a malformed record
    compare equal to a valid plan and become authority."""
    if not isinstance(plan, dict) or not plan:
        return [f"{label} must map each presented node id to its hard_blocked_by node ids"]
    errors = []
    for node_id, edges in plan.items():
        if not _text(node_id):
            errors.append(f"{label} has an empty node id")
        elif not isinstance(edges, list) or any(not _text(e) for e in edges):
            errors.append(f"{label}['{node_id}'] must be a list of non-empty hard_blocked_by node ids")
        elif len(set(edges)) != len(edges):
            errors.append(f"{label}['{node_id}'] repeats a hard_blocked_by node id")
        elif any(e not in plan for e in edges):
            errors.append(f"{label}['{node_id}'] depends on a node outside the recorded plan")
    return errors


def _normalized_plan(plan) -> dict:
    """Canonical edge order for a plan already proven well-formed by _plan_shape_errors."""
    return {node_id: sorted(edges) for node_id, edges in plan.items()}


def _plan_delta(before: dict, after: dict) -> dict:
    """The change one revision records against the previous confirmed plan."""
    return {
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
        "rewired": sorted(node_id for node_id in set(before) & set(after)
                          if before[node_id] != after[node_id]),
    }


def _declared_delta(delta) -> dict:
    """Read a recorded delta in either the id-list or the {node_id, ...} entry form."""
    if not isinstance(delta, dict):
        return {}
    read = {}
    for key in ("added", "removed", "rewired"):
        entries = delta.get(key) or []
        if not isinstance(entries, list):
            return {}
        ids = []
        for entry in entries:
            if _text(entry):
                ids.append(entry)
            elif isinstance(entry, dict) and _text(entry.get("node_id")):
                ids.append(entry["node_id"])
            else:
                return {}
        read[key] = sorted(ids)
    return read


PLAN_CONFIRMATION_CODES = ("unconfirmed_plan", "invalid_plan_confirmation", "unconfirmed_plan_delta")


def _finding(code: str, message: str, node_id: str = "") -> dict:
    finding = {"code": code, "message": message}
    if node_id:
        finding["node_id"] = node_id
        finding["message"] = f"{node_id}: {message}"
    return finding


def _plan_provenance_findings(root: Path, label: str, entry, plan) -> list:
    """The confirmation must resolve to a recorded user decision that carries this plan.

    Provenance is resolved by the contract the gates already enforce: the reference
    selects one decision in a schema-1.0 journal — `plan-confirmation-journal.json`,
    the planning journal bootstrap writes, or the product decision journal when the
    plan was genuinely confirmed there — and `product_intent._journal_decision` verifies
    it (user-session batch, explicit question and choice, not pending, removed or
    superseded). The decision's `intent` must record the exact graph presented,
    `{"plan": {node_id: [hard_blocked_by]}}`, so the reference binds the user's choice
    to this node set and, through the previous revision, to the delta they were shown.
    A `source: "user"` flag with free text is a self-asserted approval lane, not
    authority. Planning never writes the product journal for a local plan or run choice.
    """
    confirmation = entry.get("confirmation")
    confirmation = confirmation if isinstance(confirmation, dict) else {}
    reference = confirmation.get("reference")
    if (confirmation.get("source") != "user" or not _text(reference)
            or not _text(confirmation.get("reason"))):
        return [_finding("invalid_plan_confirmation",
                         f"{label} needs confirmation.source 'user' with the canonical "
                         f"decision-journal reference of the user's confirmation and the recorded "
                         f"reason; a boolean approval flag or an empty record is not user authority")]
    if not any(reference.startswith(journal + "#") for journal in (PLAN_JOURNAL, PRODUCT_JOURNAL)):
        return [_finding("invalid_plan_confirmation",
                         f"{label} confirmation.reference must select one decision in "
                         f"'{PLAN_JOURNAL}' (or in the product decision journal when the plan was "
                         f"genuinely confirmed there) as '<journal>#<batch_id>/decisions/<index>'; "
                         f"an arbitrary string is not a resolvable record of what the user "
                         f"confirmed — {RETURN_TO_BOOTSTRAP}")]
    try:
        _, decision = _journal_decision(root, reference)
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError) as exc:
        return [_finding("invalid_plan_confirmation",
                         f"{label} confirmation.reference does not resolve to a confirmed, "
                         f"current user decision: {exc}")]
    if plan is None:
        return []
    recorded = decision.get("intent")
    if not isinstance(recorded, dict) or set(recorded) != {"plan"}:
        return [_finding("invalid_plan_confirmation",
                         f"{label} references a decision that records no plan; the confirmed "
                         f'decision must carry intent {{"plan": {{node_id: hard_blocked_by}}}}')]
    shape_errors = _plan_shape_errors(recorded["plan"], f"{label} referenced decision intent.plan")
    if shape_errors:
        return [_finding("invalid_plan_confirmation", message) for message in shape_errors]
    if _normalized_plan(recorded["plan"]) != plan:
        return [_finding("invalid_plan_confirmation",
                         f"{label} plan differs from the graph recorded in the referenced "
                         f"decision; the user confirmed a different node set or dependency edges")]
    return []


def _plan_confirmation_entry_findings(root: Path, index: int, entry, previous) -> tuple:
    """Validate one recorded confirmation; return (findings, this revision's plan)."""
    label = f"{PLAN_CONFIRMATION} confirmations[{index}]"
    if not isinstance(entry, dict):
        return [_finding("invalid_plan_confirmation", f"{label} must be an object")], None

    findings = []
    revision = entry.get("revision")
    if isinstance(revision, bool) or not isinstance(revision, int) or revision != index + 1:
        findings.append(_finding(
            "invalid_plan_confirmation",
            f"{label} revision must be {index + 1}; earlier revisions are retained in order, "
            f"never renumbered or replaced"))
    if not _text(entry.get("stage")):
        findings.append(_finding("invalid_plan_confirmation",
                                 f"{label} needs the stage that presented this plan"))

    plan = entry.get("plan")
    shape_errors = _plan_shape_errors(plan, f"{label} plan")
    if shape_errors:
        findings.extend(_finding("invalid_plan_confirmation", f"{message}; an approval flag is not "
                                 f"a confirmed plan") for message in shape_errors[:1])
        findings.extend(_finding("invalid_plan_confirmation", message) for message in shape_errors[1:])
        plan = None
    else:
        plan = _normalized_plan(plan)

    findings.extend(_plan_provenance_findings(root, label, entry, plan))

    if plan is not None:
        if previous is None:
            if _declared_delta(entry.get("delta")) not in ({}, {"added": [], "removed": [], "rewired": []}):
                findings.append(_finding(
                    "invalid_plan_confirmation",
                    f"{label} is the first confirmation and has no earlier plan to record a "
                    f"delta against"))
        else:
            actual = _plan_delta(previous, plan)
            if not any(actual.values()):
                findings.append(_finding(
                    "invalid_plan_confirmation",
                    f"{label} records no change against revision {index}; a re-confirmation "
                    f"without a delta is not a revision"))
            elif "delta" not in entry:
                findings.append(_finding(
                    "invalid_plan_confirmation",
                    f"{label} must state the delta the user was shown against revision "
                    f"{index}: {actual}"))
            elif _declared_delta(entry.get("delta")) != actual:
                findings.append(_finding(
                    "invalid_plan_confirmation",
                    f"{label} delta does not match the change against revision {index}; the "
                    f"actual change is {actual}"))
    return findings, plan


def plan_confirmation_findings(bdir: str) -> list:
    """The plan the audits deliver must be the plan the user actually confirmed.

    Step 3.4 presents a node list; every later audit may change it. This gate reads
    the persisted record of what was presented and confirmed, recomputes the delta
    against the current graph, and refuses a node set or dependency edge the user
    never saw. Findings are typed and, for a delta, bound to the node that changed,
    so the confirmed part of a plan stays executable.

    Revisions are append-only history: each records the plan confirmed at that point, in
    order, and a normal later revision does not supersede the earlier one — it records the
    next graph, so earlier history stays valid and unchanged nodes are never re-confirmed.
    Supersession is reserved for retracting a recorded confirmation, and retracting one
    invalidates the chain from that point, which is why every revision must still resolve.
    A revision that changes nothing is not a revision. Work that is already finished is left alone — an unrecorded plan
    is demanded of the unfinished nodes, the ones that have yet to execute. Completion is
    never an exemption from a change, though: a node added or re-wired after the confirmed
    revision is reported even once it is marked complete, or mutating and then completing a
    record would license any graph change after the fact.

    Legacy inputs without the route contract are out of scope here: their scope
    provenance is already reported by validate_scope.
    """
    workflow_path = os.path.join(bdir, "workflow.json")
    profile_path = os.path.join(bdir, "bootstrap-profile.json")
    if not os.path.exists(workflow_path) or not os.path.exists(profile_path):
        return []
    try:
        workflow = _load_json(workflow_path)
        profile = _load_json(profile_path)
    except Exception:
        return []
    if not isinstance(workflow, dict) or not isinstance(profile, dict):
        return []  # A malformed workflow is reported by the scope gate, and never crashes this one.
    if profile.get("task_route") not in CANONICAL_ROUTES:
        return []

    root = Path(_project_root_from_bootstrap_dir(bdir))
    current = _plan_shape(workflow.get("nodes"))
    if not current:
        return []
    unfinished = sorted(set(current) - _completed_node_ids(workflow))

    record_path = os.path.join(bdir, PLAN_CONFIRMATION)
    if not os.path.exists(record_path):
        return [_finding(
            "unconfirmed_plan",
            f"{PLAN_CONFIRMATION} not found; Step 3.4 must persist the node ids and "
            f"hard_blocked_by edges presented to the user with their confirmation provenance, "
            f"so the audits' changes can be presented as a delta against it — "
            f"{RETURN_TO_BOOTSTRAP}", node_id)
            for node_id in unfinished]
    try:
        record = _load_json(record_path)
    except Exception as exc:
        return [_finding("invalid_plan_confirmation", f"{PLAN_CONFIRMATION} cannot be parsed: {exc}")]
    if not isinstance(record, dict) or record.get("schema_version") != "1.0":
        return [_finding("invalid_plan_confirmation", f"{PLAN_CONFIRMATION} needs schema_version '1.0'")]
    confirmations = record.get("confirmations")
    if not isinstance(confirmations, list) or not confirmations:
        return [_finding(
            "invalid_plan_confirmation",
            f"{PLAN_CONFIRMATION} confirmations must list every plan presented to the user, "
            f"oldest first; earlier revisions are kept, not overwritten")]

    findings = []
    previous = None
    for index, entry in enumerate(confirmations):
        entry_findings, plan = _plan_confirmation_entry_findings(root, index, entry, previous)
        findings.extend(entry_findings)
        if plan is None:
            return findings
        previous = plan

    delta = _plan_delta(previous, current)
    revision = len(confirmations)
    # A change made after the confirmation is reported whatever its status: completing a
    # node that was inserted without authority is the mutation, not an exemption from it.
    for node_id in delta["added"]:
        findings.append(_finding(
            "unconfirmed_plan_delta",
            f"added to the workflow after confirmed revision {revision}; present the delta and "
            f"record the user's confirmation before this node executes — {RETURN_TO_BOOTSTRAP}",
            node_id))
    for node_id in delta["rewired"]:
        findings.append(_finding(
            "unconfirmed_plan_delta",
            f"hard_blocked_by changed from {previous[node_id]} to {current[node_id]} after "
            f"confirmed revision {revision}; present the delta and record the user's confirmation "
            f"before this node executes — {RETURN_TO_BOOTSTRAP}", node_id))
    if delta["removed"]:
        findings.append(_finding(
            "unconfirmed_plan_delta",
            f"nodes {delta['removed']} were dropped from the workflow after confirmed revision "
            f"{revision}; a removal the user never saw is an unconfirmed plan change — "
            f"{RETURN_TO_BOOTSTRAP}"))
    return findings


def validate_plan_confirmation(bdir: str) -> list:
    """Rendered plan-confirmation errors for the bootstrap validator CLI."""
    return [f"{finding['code']}: {finding['message']}" for finding in plan_confirmation_findings(bdir)]


def plan_confirmation_blockers(project_root) -> list:
    """Typed plan-confirmation blockers for a run-time entry.

    The readiness gate and any other `/run` driver consume the same record through this
    call instead of assuming `/bootstrap` ran and passed: each blocker carries `code`,
    `message` and, for a delta, the `node_id` it holds, matching the blocker shape the
    readiness report already publishes.
    """
    return plan_confirmation_findings(os.path.join(str(project_root), ".allforai", "bootstrap"))


def _structural(findings: list, code: str, message: str, node_id: str = "") -> None:
    """Record one structural finding.

    Structural gates are decided once, here, and read by two consumers: this CLI renders
    them as `code: message` strings, and the run-time entry takes the same dicts as
    typed blockers. Neither consumer restates the rule.
    """
    finding = {"code": code, "message": message}
    if node_id:
        finding["node_id"] = node_id
    findings.append(finding)


def _rendered(findings: list) -> list:
    return [f"{finding['code']}: {finding['message']}" for finding in findings]


def _declared_node_ids(loop: dict, *keys: str) -> list:
    """The addressable node ids one repair-loop declaration names under `keys`.

    A declaration that is not a list names no nodes here; the readiness gate reports the
    container's own shape, so this rule reads the route and does not restate it.
    """
    for key in keys:
        declared = loop.get(key)
        if declared:
            return [n for n in declared if _text(n)] if isinstance(declared, list) else []
    return []


def repair_loop_declaration_findings(bdir: str) -> list:
    """A declared repair loop must describe a route the orchestrators can actually run.

    `validate_unattended_readiness.py` checks the declaration against the graph: a
    declared QA or closure node must carry its `hard_blocked_by` edge. This checks
    that the declaration itself routes something: a failed QA node never completes,
    so both engines dispatch the repair from this declaration and hold closure until
    the QA node reruns. A loop with no QA source, no closure holder, or a closure that
    never waits for the QA rerun wires an edge and routes nothing.
    """
    errors = []
    workflow_path = os.path.join(bdir, "workflow.json")
    spec_path = os.path.join(bdir, "unattended-run-readiness-spec.json")
    if not os.path.exists(workflow_path) or not os.path.exists(spec_path):
        return errors
    try:
        workflow = _load_json(workflow_path)
        spec = _load_json(spec_path)
    except Exception:
        return errors
    if (not isinstance(workflow, dict) or not isinstance(spec, dict)
            or not isinstance(spec.get("required_repair_loops"), list)):
        return errors

    nodes = _addressable_nodes(workflow.get("nodes"))
    for index, loop in enumerate(spec["required_repair_loops"]):
        if not isinstance(loop, dict):
            continue
        repair_node_id = loop.get("repair_node_id")
        if not _text(repair_node_id):
            continue
        label = f"required_repair_loops[{index}]"
        # The blocker is anchored to the repair node only when the graph actually holds it;
        # a loop naming an absent node is reported by the gate that owns that check.
        declared_node = repair_node_id if repair_node_id in nodes else ""
        # A declared node list is a collection of identifiers or it declares nothing:
        # a scalar is not one member, and iterating it is how a gate stops being a gate.
        qa_nodes = _declared_node_ids(loop, "qa_node_ids", "qa_nodes")
        closure_nodes = _declared_node_ids(loop, "closure_node_ids", "closure_nodes")
        if not qa_nodes:
            _structural(
                errors, "undeclared_repair_loop_routing",
                f"{label} names repair node "
                f"'{repair_node_id}' with no qa_node_ids; nothing routes findings into it",
                node_id=declared_node,
            )
        if not closure_nodes:
            _structural(
                errors, "undeclared_repair_loop_routing",
                f"{label} names repair node "
                f"'{repair_node_id}' with no closure_node_ids; nothing waits for the QA rerun",
                node_id=declared_node,
            )
        if repair_node_id in qa_nodes or repair_node_id in closure_nodes:
            _structural(
                errors, "undeclared_repair_loop_routing",
                f"{label} lists repair node "
                f"'{repair_node_id}' as its own QA or closure node",
                node_id=declared_node,
            )
        for closure_node_id in closure_nodes:
            node = nodes.get(closure_node_id)
            if node is None:
                continue
            edges = node.get("hard_blocked_by") or []
            edges = edges if isinstance(edges, list) else []
            missing = [qa for qa in qa_nodes if qa in nodes and qa not in edges]
            if missing:
                _structural(
                    errors, "undeclared_repair_loop_routing",
                    f"{label} closure node "
                    f"'{closure_node_id}' is not hard_blocked_by QA node(s) {missing}; it would "
                    f"close on the repair alone, without the QA rerun that proves it",
                    node_id=closure_node_id,
                )
    return errors


def validate_repair_loop_declaration(bdir: str) -> list:
    """Rendered repair-loop routing errors for the bootstrap validator CLI."""
    return _rendered(repair_loop_declaration_findings(bdir))


def coverage_gate_loop(nodes):
    """The repair loop auto_fix_once needs for the concept-acceptance coverage gate (ADR-0008, #65):
    one bounded repair hard_blocked_by the gate, then a rerun of the gate blocked by the repair.
    None when the workflow has no coverage gate."""
    gates = [n["node_id"] for n in nodes
             if isinstance(n, dict) and n.get("capability") == "concept-acceptance" and isinstance(n.get("node_id"), str)]
    if not gates:
        return None
    gate = gates[0]
    return {"scope": "concept-acceptance", "qa_node_ids": [gate], "repair_node_id": gate + "-repair",
            "closure_node_ids": [gate + "-rerun"], "max_attempts": 1}


def coverage_gate_loop_findings(bdir: str) -> list:
    """auto_fix_once repairs only through a declared loop (ADR-0006, #65).

    `validate_bootstrap.py` only validates `unattended-run-readiness-spec.json` — planning
    authors it, this CLI does not — so a plan that carries the coverage gate and that policy
    without a loop naming the gate is refused here, at bootstrap time, before
    `validate_unattended_readiness.py` catches the same fault again at run readiness. The
    message matches that readiness blocker (`missing_coverage_repair_loop`) so the user reads
    one explanation, not two.
    """
    findings: list = []
    workflow_path = os.path.join(bdir, "workflow.json")
    policy_path = os.path.join(bdir, "run-policy.json")
    spec_path = os.path.join(bdir, "unattended-run-readiness-spec.json")
    if not os.path.exists(workflow_path) or not os.path.exists(policy_path):
        return findings
    try:
        workflow = _load_json(workflow_path)
        policy = _load_json(policy_path)
    except Exception:
        return findings
    if not isinstance(policy, dict) or policy.get("on_needs_iteration") != "auto_fix_once":
        return findings
    if not isinstance(workflow, dict) or not isinstance(workflow.get("nodes"), list):
        return findings
    loop = coverage_gate_loop(workflow["nodes"])
    if loop is None:
        return findings
    gate = loop["qa_node_ids"][0]
    spec = {}
    if os.path.exists(spec_path):
        try:
            spec = _load_json(spec_path)
        except Exception:
            spec = {}
    declared = set()
    for existing in (spec.get("required_repair_loops") if isinstance(spec, dict) else None) or []:
        if isinstance(existing, dict):
            declared.update(str(q) for q in (existing.get("qa_node_ids") or existing.get("qa_nodes") or []))
            declared.update(str(q) for q in (existing.get("closure_node_ids") or existing.get("closure_nodes") or []))
    if gate not in declared:
        _structural(
            findings, "missing_coverage_repair_loop",
            f"run-policy.json on_needs_iteration is auto_fix_once and node {gate} is the "
            f"concept-acceptance coverage gate, but no unattended-run-readiness-spec.json "
            f"required_repair_loops entry names it in qa_node_ids. auto_fix_once repairs only "
            f"through a declared loop (ADR-0006): declare one with a repair node hard_blocked_by "
            f"{gate} and a rerun of the gate blocked by the repair, or choose halt_with_report.",
            node_id=gate,
        )
    return findings


def validate_coverage_gate_loop(bdir: str) -> list:
    """Rendered coverage-gate repair-loop errors for the bootstrap validator CLI."""
    return _rendered(coverage_gate_loop_findings(bdir))


def _downstream_of(nodes: dict, node_id: str, owner_id: str) -> bool:
    """True when owner_id transitively depends on node_id through hard_blocked_by."""
    seen = set()
    frontier = [owner_id]
    while frontier:
        current = frontier.pop()
        if current in seen:
            continue
        seen.add(current)
        edges = nodes.get(current, {}).get("hard_blocked_by") or []
        for edge in edges if isinstance(edges, list) else []:
            if edge == node_id:
                return True
            frontier.append(edge)
    return False


def effect_stage_ownership_findings(bdir: str) -> list:
    """A deferred effect proof must name a downstream node that actually proves it.

    A node whose full effect first exists after a later node declares
    `downstream_effect_owner`. The named node must exist, run after this one, and
    carry its own Effect Verification. Whether a node needed to defer at all stays
    a semantic judgment for the node-spec audit; an unowned deferral is structural.
    """
    errors = []
    workflow_path = os.path.join(bdir, "workflow.json")
    specs_dir = os.path.join(bdir, "node-specs")
    if not os.path.exists(workflow_path):
        return errors
    try:
        workflow = _load_json(workflow_path)
    except Exception:
        return errors

    if not isinstance(workflow, dict):
        return errors
    # A run-time entry reaches this on any file the user's graph currently holds, so a
    # malformed node list yields no structural finding here and is rejected by the shape
    # gate that owns it, rather than raising out of the caller. `_addressable_nodes` is
    # what makes that hold: an identifier that cannot key this map or order the report
    # below never reaches the rule.
    nodes = _addressable_nodes(workflow.get("nodes"))
    for node_id, node in sorted(nodes.items()):
        if "downstream_effect_owner" not in node:
            continue
        owner_id = node.get("downstream_effect_owner")
        if not _text(owner_id):
            _structural(
                errors, "unowned_effect_stage",
                f"workflow.json {node_id} downstream_effect_owner must "
                f"name the node that proves the full effect; omit the field when this node "
                f"proves it at its own stage",
                node_id=node_id,
            )
            continue
        if owner_id == node_id:
            _structural(
                errors, "unowned_effect_stage",
                f"workflow.json {node_id} defers its effect proof to itself",
                node_id=node_id,
            )
            continue
        if owner_id not in nodes:
            _structural(
                errors, "unowned_effect_stage",
                f"workflow.json {node_id} defers its effect proof to "
                f"non-existent node '{owner_id}'",
                node_id=node_id,
            )
            continue
        if not _downstream_of(nodes, node_id, owner_id):
            _structural(
                errors, "unowned_effect_stage",
                f"workflow.json {node_id} defers its effect proof to "
                f"'{owner_id}', which does not run after it; a deferred effect needs a "
                f"downstream owner, not a parallel one",
                node_id=node_id,
            )
            continue
        owner_spec = os.path.join(specs_dir, f"{owner_id}.md")
        if not os.path.exists(owner_spec):
            continue
        _, owner_text, spec_errors = _read_node_spec(owner_spec)
        if spec_errors:
            continue
        if "## Effect Verification" not in owner_text:
            _structural(
                errors, "unowned_effect_stage",
                f"node-specs/{owner_id}.md accepts the deferred effect of "
                f"'{node_id}' but carries no Effect Verification section to prove it",
                node_id=node_id,
            )
    return errors


def validate_effect_stage_ownership(bdir: str) -> list:
    """Rendered deferred-effect ownership errors for the bootstrap validator CLI."""
    return _rendered(effect_stage_ownership_findings(bdir))


def _produces(node: dict, required: str) -> bool:
    """True when this node itself ships `required`, monorepo prefixes included."""
    for path in _artifact_paths(node.get("exit_artifacts")):
        if isinstance(path, str) and (path == required or path.endswith("/" + required)):
            return True
    return False


def _ui_implementation_terms(profile: dict) -> tuple:
    """The vocabulary that names a user-facing surface in this particular project.

    The generic terms hold everywhere; a game adds its own words for a screen, and the
    profile's own frontend and mobile module paths name the directories this project
    puts one in — the same evidence `_profile_has_mobile_ui_module` reads.

    Returned as (words, fragments): a word has to stand as a word, a fragment counts
    wherever it appears. `_mentions_ui_surface` is the one reader of the distinction.
    """
    vocabulary = list(UI_IMPLEMENTATION_TERMS)
    if profile.get("is_game_project") is True:
        vocabulary.extend(GAME_UI_IMPLEMENTATION_TERMS)
    # Word boundaries are an ASCII idea: CJK text is not spaced, so "界面" inside a
    # sentence is the term itself and stays a fragment.
    words = tuple(term for term in vocabulary if term.isascii())
    fragments = [term for term in vocabulary if not term.isascii()]
    modules = profile.get("modules")
    for module in modules if isinstance(modules, list) else []:
        if isinstance(module, dict) and module.get("role") in UI_MODULE_ROLES:
            path = module.get("path")
            if _text(path):
                fragments.append(f"{path.strip().lower()}/")
    return words, tuple(fragments)


def _ui_word_pattern(words: tuple):
    """One pattern for the ASCII vocabulary, each term held to a word of its own.

    Only the END of the term is held to a boundary. "screenshot" carries the term on into
    a different word, and a headless node that attaches screenshots builds no interface.
    A compound that ENDS in the term still names a surface ("homescreen", "touchscreen",
    "lockscreen", "fullscreen"), so the start is left open: this recogniser may demand a
    design it did not strictly need, but it must never miss a node that builds a surface.
    The boundary is a letter rather than the regex word boundary: "home_screen" and
    "screen2" are still the word, and so are the plural ("screens", "canvases") and an
    identifier once `_CAMEL_CASE_SEAM` has split it. A space inside a term is any run of
    whitespace, because a spec body wraps its lines.
    """
    alternatives = "|".join(r"\s+".join(re.escape(part) for part in term.split())
                            for term in words)
    return re.compile(rf"(?:{alternatives})(?:e?s)?(?![a-z])")


def _mentions_ui_surface(node: dict, specs_dir: str, words: tuple, fragments: tuple) -> bool:
    """True when the node's own record or its spec body names a user-facing surface."""
    try:
        text = json.dumps(node, ensure_ascii=False)
    except TypeError:
        text = str(node)
    text += "\n" + _read_text_if_exists(os.path.join(specs_dir, f"{_node_id(node)}.md"))
    lowered = text.lower()
    if _contains_any(lowered, fragments):
        return True
    if not words:
        return False
    # Both readings, because either alone misses one: "SettingsScreen" is only a screen
    # once split, and "SwiftUI" is only the term while whole.
    pattern = _ui_word_pattern(words)
    return bool(pattern.search(lowered) or pattern.search(_CAMEL_CASE_SEAM.sub(" ", text).lower()))


def _is_implementation_node(node: dict) -> bool:
    """True when a node builds something, rather than deciding or reviewing it."""
    if node.get("capability") in UI_IMPLEMENTATION_CAPABILITIES:
        return True
    responsibilities = node.get("responsibilities")
    return isinstance(responsibilities, list) and "implementation" in responsibilities


def _ui_implementation_nodes(workflow: dict, specs_dir: str, profile: dict) -> list:
    """The one entry that recognises a node as building a user-facing surface.

    Every rule that has to reason about interface work — this gate and the run-time
    experience gate — asks here, so both refuse the same graphs and neither grows a
    second heuristic that can drift from this one.

    It reads the addressable subset rather than `workflow["nodes"]` raw, because this rule
    is called directly and not only behind the shape gate. It does not go through
    `_matching_nodes`: that helper matches substrings, which is right for its other
    callers and wrong here, where "screenshot" must not pass for "screen".
    """
    words, fragments = _ui_implementation_terms(profile)
    return [node for node in _addressable_nodes(workflow.get("nodes")).values()
            if _is_implementation_node(node)
            and _mentions_ui_surface(node, specs_dir, words, fragments)]


def experience_design_coverage_findings(bdir: str) -> list:
    """A product with end users must design for them before it builds for them.

    A product route that plans screens and designs none of them ships whatever the
    implementation node improvises. This gate reads the classification bootstrap
    recorded — `experience_priority.mode`, never re-derived here — and, when the
    product has an end-user interface, demands three things of the graph: the design
    exists as a node that produces the design artifacts, the implementation of the
    interface is held behind it, and no one has declared experience out of scope.

    The classification itself is demanded first and alone: on an unknown mode every
    later verdict would be guesswork, and reporting a guess beside a missing field
    invites repairing the wrong thing. All four codes name the interactive
    `/bootstrap` phase, because that is where a route, a mode and a plan are decided.

    Legacy and local-change inputs are out of scope, and a workflow or profile that
    cannot be read is left to the scope and shape gates that own those faults.
    """
    findings = []
    workflow_path = os.path.join(bdir, "workflow.json")
    profile_path = os.path.join(bdir, "bootstrap-profile.json")
    if not os.path.exists(workflow_path) or not os.path.exists(profile_path):
        return findings
    try:
        workflow = _load_json(workflow_path)
        profile = _load_json(profile_path)
    except Exception:
        return findings
    if not isinstance(workflow, dict) or not isinstance(profile, dict):
        return findings
    if profile.get("task_route") not in PRODUCT_ROUTES:
        return findings

    priority = profile.get("experience_priority")
    mode = priority.get("mode") if isinstance(priority, dict) else None
    reason = priority.get("reason") if isinstance(priority, dict) else None
    if mode not in EXPERIENCE_PRIORITY_MODES or not _text(reason):
        _structural(
            findings, "missing_experience_priority",
            f"bootstrap-profile.json must record experience_priority as "
            f'{{"mode": one of {list(EXPERIENCE_PRIORITY_MODES)}, "reason": "<one sentence>"}} '
            f"before a product route can be planned; until the product says who it serves, "
            f"no node can be held to an experience design contract — {RETURN_TO_BOOTSTRAP}")
        return findings
    if mode == "none":
        return findings

    not_applicable = workflow.get("not_applicable")
    if isinstance(not_applicable, dict) and "experience" in not_applicable:
        _structural(
            findings, "experience_not_applicable_on_ui_product",
            f"workflow.json declares not_applicable.experience while "
            f"bootstrap-profile.json classifies experience_priority.mode as '{mode}'; a "
            f"product that has end users cannot declare designing for them out of scope — "
            f"{RETURN_TO_BOOTSTRAP}")
    if mode not in EXPERIENCE_DESIGN_MODES:
        return findings

    specs_dir = os.path.join(bdir, "node-specs")
    nodes = _addressable_nodes(workflow.get("nodes"))
    ui_nodes = _ui_implementation_nodes(workflow, specs_dir, profile)
    if not ui_nodes:
        return findings

    if profile.get("is_game_project") is True:
        required_groups = [GAME_EXPERIENCE_DESIGN_DOC_PATHS]
    else:
        required_groups = [(path,) for path in APP_EXPERIENCE_DESIGN_REQUIRED]

    designed = []
    for group in required_groups:
        producers = sorted(
            node_id for node_id, node in nodes.items()
            if any(_produces(node, path) for path in group)
        )
        if not producers:
            _structural(
                findings, "missing_experience_design_node",
                f"workflow.json plans user-facing implementation but no node produces "
                f"{list(group)}; a product route with an end-user interface must carry an "
                f"experience design node that decides the journeys before they are built — "
                f"{RETURN_TO_BOOTSTRAP}")
            continue
        designed.append((group, producers))

    for ui_node in sorted(ui_nodes, key=_node_id):
        ui_id = _node_id(ui_node)
        for group, producers in designed:
            if ui_id in producers:
                continue
            if any(_downstream_of(nodes, producer, ui_id) for producer in producers):
                continue
            _structural(
                findings, "implementation_not_blocked_by_experience_design",
                f"workflow.json {ui_id} implements a user-facing surface but no "
                f"hard_blocked_by path reaches a producer of {list(group)} ({producers}); "
                f"an interface built before its design is the design — "
                f"{RETURN_TO_BOOTSTRAP}",
                node_id=ui_id)
    return findings


def validate_experience_design_coverage(bdir: str) -> list:
    """Rendered experience-design coverage errors for the bootstrap validator CLI."""
    return _rendered(experience_design_coverage_findings(bdir))


# The experience quality gate. Designing the interface (above) is not reviewing what was
# built from that design, so the two rules are separate: this one reads the review nodes.
EXPERIENCE_GATE_PRODUCT_ROUTES = ("new-product", "product-reconstruction")
EXPERIENCE_GATE_MODES = ("consumer", "mixed")
APP_EXPERIENCE_CRITIQUE = "experience-quality-critique"
GAME_CREATIVE_CRITIQUE = "creative-quality-critique"
# A game's creative critique writes one path whichever time it runs, so the stages below
# are the app's; a game's "after it was built" review is told apart by graph position.
APP_EXPERIENCE_CRITIQUE_STAGES = (
    ("design", f"{APP_EXPERIENCE_CRITIQUE}-design.json"),
    ("runtime", f"{APP_EXPERIENCE_CRITIQUE}-runtime.json"),
)
EXPERIENCE_GATE_CLOSURE_CAPABILITIES = ("concept-acceptance", "pipeline-closure-verify")


def _critique_nodes(nodes: dict, marker: str) -> dict:
    """Node ids that perform the review, mapped to the report paths they write.

    A node is the gate only when it ships the report. Repair nodes and closure nodes read
    the same report and name the same skill in their spec, so recognising a gate by what a
    node mentions would turn every reader of a review into a second copy of it.
    """
    matched = {}
    for node_id, node in sorted(nodes.items()):
        paths = [p for p in _artifact_paths(node.get("exit_artifacts"))
                 if isinstance(p, str) and marker in p]
        if paths:
            matched[node_id] = paths
    return matched


def experience_gate_flow_findings(bdir: str) -> list:
    """A product with an interface must review the experience it actually ships.

    The design gate above proves the journeys were decided before they were built. This
    one proves they were judged afterwards, by a graph a run can execute unattended: a
    review before the interface is implemented, a review of the running product, closure
    held behind the second one, and a declared repair loop behind each, so a refusal
    routes findings back into the build instead of stopping the run.

    Nodes are classified by the report they produce, never by their identifier or
    capability: a node named `experience-review` that writes nothing is not a review, and
    a node that reads the report is not a second one. An app's two stages are the two
    report file names; a game's creative critique writes one path both times, so the run
    after the build is the one that transitively depends on an implementation node.

    The trigger is narrow on purpose. A route that is not a product route, a mode without
    end users, and a profile written before `experience_priority` existed are all left
    alone — a missing classification is the design gate's blocker, and a project planned
    before this law is not retroactively refused at the `/run` boundary. Shape faults
    belong to the shape gate: an unreadable or mis-shaped input yields no verdict here.
    """
    findings = []
    workflow_path = os.path.join(bdir, "workflow.json")
    profile_path = os.path.join(bdir, "bootstrap-profile.json")
    if not os.path.exists(workflow_path) or not os.path.exists(profile_path):
        return findings
    try:
        workflow = _load_json(workflow_path)
        profile = _load_json(profile_path)
    except Exception:
        return findings
    if not isinstance(workflow, dict) or not isinstance(profile, dict):
        return findings
    if profile.get("task_route") not in EXPERIENCE_GATE_PRODUCT_ROUTES:
        return findings
    priority = profile.get("experience_priority")
    if not isinstance(priority, dict) or priority.get("mode") not in EXPERIENCE_GATE_MODES:
        return findings

    nodes = _addressable_nodes(workflow.get("nodes"))
    specs_dir = os.path.join(bdir, "node-specs")
    # The one heuristic for "this node builds a user-facing surface" lives with the design
    # gate; asking it here is what keeps the two gates refusing the same graphs.
    impl_ids = sorted(_node_id(node) for node in _ui_implementation_nodes(workflow, specs_dir, profile))
    if not impl_ids:
        return findings

    game = profile.get("is_game_project") is True
    critiques = _critique_nodes(nodes, GAME_CREATIVE_CRITIQUE if game else APP_EXPERIENCE_CRITIQUE)

    if game:
        if not critiques:
            _structural(
                findings, "missing_experience_gate",
                f"workflow.json plans user-facing implementation ({impl_ids}) but no node "
                f"produces a {GAME_CREATIVE_CRITIQUE} report; a game that is never reviewed "
                f"against its own creative intent ships whatever the build happened to "
                f"produce — {RETURN_TO_BOOTSTRAP}")
        # A game's review runs against one report path, so "the one after the build" is a
        # graph position: it waits on an implementation node instead of preceding it.
        closing = [node_id for node_id in critiques
                   if any(_downstream_of(nodes, impl_id, node_id) for impl_id in impl_ids)]
    else:
        staged = {stage: sorted(node_id for node_id, paths in critiques.items()
                                if any(path.endswith(suffix) for path in paths))
                  for stage, suffix in APP_EXPERIENCE_CRITIQUE_STAGES}
        for stage, suffix in APP_EXPERIENCE_CRITIQUE_STAGES:
            if staged[stage]:
                continue
            _structural(
                findings, "missing_experience_gate",
                f"workflow.json plans user-facing implementation ({impl_ids}) but no node "
                f"produces the {stage}-stage experience critique report (an exit artifact "
                f"ending '{suffix}'); an interface nobody reviews at this stage is released "
                f"on the author's own opinion of it — {RETURN_TO_BOOTSTRAP}")
        for impl_id in impl_ids:
            if staged["design"] and not any(_downstream_of(nodes, critique_id, impl_id)
                                            for critique_id in staged["design"]):
                _structural(
                    findings, "implementation_not_blocked_by_design_critique",
                    f"workflow.json {impl_id} builds a user-facing surface but no "
                    f"hard_blocked_by path reaches the design-stage experience critique "
                    f"{staged['design']}; a review the build did not wait for reviews a "
                    f"decision already made — {RETURN_TO_BOOTSTRAP}",
                    node_id=impl_id)
        closing = staged["runtime"]

    # A graph with no closure node passes this check with nothing to hold, and that is not a
    # way round the review: a non-empty must-fix list already fails the critique node's own
    # report in check_artifacts (`MUST_FIX_GATE_FIELDS`), so the run stops there either way.
    for node_id in sorted(nodes):
        if nodes[node_id].get("capability") not in EXPERIENCE_GATE_CLOSURE_CAPABILITIES:
            continue
        if any(_downstream_of(nodes, critique_id, node_id) for critique_id in closing):
            continue
        _structural(
            findings, "closure_not_blocked_by_experience_gate",
            f"workflow.json {node_id} closes the pipeline without a hard_blocked_by path "
            f"to the review of the running product ({closing or 'none planned'}); closure "
            f"that does not wait for that review accepts a product nobody looked at — "
            f"{RETURN_TO_BOOTSTRAP}",
            node_id=node_id)

    declared = set()
    spec = None
    spec_path = os.path.join(bdir, "unattended-run-readiness-spec.json")
    if os.path.exists(spec_path):
        try:
            spec = _load_json(spec_path)
        except Exception:
            spec = None
    if isinstance(spec, dict) and isinstance(spec.get("required_repair_loops"), list):
        for loop in spec["required_repair_loops"]:
            if isinstance(loop, dict):
                declared.update(_declared_node_ids(loop, "qa_node_ids", "qa_nodes"))
    for node_id in sorted(critiques):
        if node_id in declared:
            continue
        _structural(
            findings, "experience_gate_without_repair_loop",
            f"workflow.json {node_id} reviews the experience but no "
            f"unattended-run-readiness-spec.json required_repair_loops entry names it as a "
            f"qa node; a review with nowhere to send its findings halts the run instead of "
            f"repairing what it found — {RETURN_TO_BOOTSTRAP}",
            node_id=node_id)
    return findings


def validate_experience_gate_flow(bdir: str) -> list:
    """Rendered experience quality-gate errors for the bootstrap validator CLI."""
    return _rendered(experience_gate_flow_findings(bdir))


def workflow_shape_findings(bdir: str) -> list:
    """Node entries no graph rule can address, decided before any rule reads them.

    Every rule above keys a map by node identifier, orders a report by it and anchors a
    blocker to it. A value that is not a non-empty string does none of those: it raises
    when hashed or ordered against another identifier, and it names nothing a user can
    act on. Two nodes sharing one identifier are the same fault seen from the other side
    — one silently replaces the other in every map the rules build, so the graph that is
    validated is not the graph on disk.

    A run-time entry reaches these gates on whatever `workflow.json` currently holds, so
    the fault is returned as a typed finding rather than raised: a traceback is not a
    verdict, and a caller that cannot publish one leaves its last verdict standing.
    Faults in the file itself — unparseable bytes, a non-object root, a `nodes` value
    that is not a list — stay with the gates that own them and are not restated here.
    """
    findings = []
    workflow_path = os.path.join(bdir, "workflow.json")
    if not os.path.exists(workflow_path):
        return findings
    try:
        workflow = _load_json(workflow_path)
    except Exception:
        return findings
    if not isinstance(workflow, dict) or not isinstance(workflow.get("nodes"), list):
        return findings

    seen = set()
    for index, node in enumerate(workflow["nodes"]):
        if not isinstance(node, dict):
            _structural(
                findings, "malformed_workflow_node",
                f"workflow.json nodes[{index}] must be an object; a {type(node).__name__} "
                f"carries no node identifier, so no rule can plan, block or repair it",
            )
            continue
        node_id = node.get("node_id")
        if not _addressable_id(node_id):
            _structural(
                findings, "malformed_workflow_node",
                f"workflow.json nodes[{index}] node_id must be a non-empty string, got "
                f"{node_id!r}; an identifier that cannot key the graph names no node in "
                f"a plan, a dependency edge or a blocker",
            )
            continue
        if node_id in seen:
            _structural(
                findings, "malformed_workflow_node",
                f"workflow.json nodes[{index}] repeats node_id '{node_id}'; one entry "
                f"replaces the other wherever the graph is read by identifier, so the "
                f"validated graph is not the graph on disk",
                node_id=node_id,
            )
            continue
        seen.add(node_id)
    return findings


def workflow_shape_blockers(project_root) -> list:
    """Typed node-shape blockers for a run-time entry."""
    return workflow_shape_findings(os.path.join(str(project_root), ".allforai", "bootstrap"))


def structural_gate_blockers(project_root) -> list:
    """Typed structural-gate blockers for a run-time entry.

    `/run` must not assume `/bootstrap` ran and passed on the graph it is about to
    execute. Both engines re-decide the same repair-loop routing, deferred-effect
    ownership, experience-design coverage and experience quality-gate rules through this
    call, from the implementations above, so a workflow
    the bootstrap gate refuses cannot execute unattended on either host, and neither
    host restates the rule as a second copy that can drift.

    Shape is decided first and alone. The routing and ownership rules are safe on a
    malformed graph — they read the addressable subset — but a verdict computed from a
    subset describes a graph the user does not have, and reporting it beside the shape
    fault invites repairing the wrong thing. The bootstrap CLI reaches the same ordering
    through `validate_workflow`, which it runs before these gates.
    """
    bdir = os.path.join(str(project_root), ".allforai", "bootstrap")
    shape = workflow_shape_findings(bdir)
    if shape:
        return shape
    return (repair_loop_declaration_findings(bdir) + effect_stage_ownership_findings(bdir)
            + experience_design_coverage_findings(bdir) + experience_gate_flow_findings(bdir))


def validate_node_spec(path: str) -> list:
    """Validate a single node-spec markdown file."""
    data, text, errors = _read_node_spec(path)
    if errors:
        return errors
    if "node_id" not in data:
        errors.append("frontmatter missing 'node_id' field")
    if "node" in data:
        errors.append("frontmatter forbidden legacy 'node' field; use 'node_id'")
    retired = _retired_capability_error(str(data.get("node_id", "node-spec")), data.get("capability"))
    if retired:
        errors.append(f"frontmatter {retired}")
    for term in NODE_SPEC_REQUIRED_ATTENTION_TERMS:
        if term not in text:
            errors.append(f"missing attention contract term {term!r}")

    return errors


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_bootstrap.py <bootstrap-dir>")
        sys.exit(1)

    bdir = sys.argv[1]
    errors = []

    wf_path = os.path.join(bdir, "workflow.json")
    if os.path.exists(wf_path):
        try:
            errors.extend(f"{b['code']}: {b['message']}" for b in validate_scope(
                _project_root_from_bootstrap_dir(bdir), _load_json(wf_path)))
        except (OSError, ValueError) as exc:
            errors.append(f"workflow.json: cannot parse: {exc}")
        # Scope validation checks container shapes before any node traversal.
        if not errors:
            errors.extend(validate_workflow(wf_path))
        # Cross-node checks require a valid scope and workflow schema.
        if not errors:
            errors.extend(validate_node_spec_coverage(bdir))
            errors.extend(validate_node_spec_contracts(bdir))
            errors.extend(validate_approval_records(bdir))
            errors.extend(validate_app_design_flow(bdir))
            errors.extend(validate_experience_design_coverage(bdir))
            errors.extend(validate_experience_gate_flow(bdir))
            errors.extend(validate_game_2d_production_flow(bdir))
            errors.extend(validate_canvas2d_game_client_profile_flow(bdir))
            errors.extend(validate_game_visual_acceptance_standard_flow(bdir))
            errors.extend(validate_mobile_ui_coverage(bdir))
            errors.extend(validate_plan_confirmation(bdir))
            errors.extend(validate_repair_loop_declaration(bdir))
            errors.extend(validate_effect_stage_ownership(bdir))
            errors.extend(validate_coverage_gate_loop(bdir))
    else:
        if os.path.exists(os.path.join(bdir, "state-machine.json")):
            # The retired format used to skip validation and pass. Nothing generates or executes it
            # any more, and "could not check" is not "passed" (ADR-0010).
            errors.append("retired_bootstrap_format: state-machine.json is no longer supported; "
                          "rerun /bootstrap to generate workflow.json")
        else:
            errors.append("workflow.json not found")

    specs_dir = os.path.join(bdir, "node-specs")
    if os.path.isdir(specs_dir):
        for fname in sorted(os.listdir(specs_dir)):
            if fname.endswith(".md"):
                fpath = os.path.join(specs_dir, fname)
                spec_errors = validate_node_spec(fpath)
                errors.extend([f"node-specs/{fname}: {e}" for e in spec_errors])

    result = {"errors": errors, "passed": len(errors) == 0}
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["passed"] else 1)


# Also export for testing
__all__ = [
    "validate_workflow",
    "validate_node_spec",
    "validate_node_spec_coverage",
    "validate_node_spec_contracts",
    "validate_approval_records",
    "validate_app_design_flow",
    "validate_game_2d_production_flow",
    "validate_canvas2d_game_client_profile_flow",
    "validate_game_visual_acceptance_standard_flow",
    "validate_mobile_ui_coverage",
    "validate_plan_confirmation",
    "plan_confirmation_findings",
    "plan_confirmation_blockers",
    "validate_repair_loop_declaration",
    "repair_loop_declaration_findings",
    "coverage_gate_loop",
    "coverage_gate_loop_findings",
    "validate_coverage_gate_loop",
    "validate_effect_stage_ownership",
    "effect_stage_ownership_findings",
    "validate_experience_design_coverage",
    "experience_design_coverage_findings",
    "validate_experience_gate_flow",
    "experience_gate_flow_findings",
    "workflow_shape_findings",
    "workflow_shape_blockers",
    "structural_gate_blockers",
]


if __name__ == "__main__":
    main()
