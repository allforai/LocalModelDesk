"""R-shell-02 的纯逻辑面：menuTitle 七行文案，表驱动（design §5 表）。"""
import json
import subprocess

import pytest

from shell_helpers import harness_path


HELD_LLM = {"holder": {"kind": "llm", "label": "qwen3-30b", "since": 1.0, "phase": "held"},
            "media_busy": False, "can_start": {}}
HELD_VIDEO = {"holder": {"kind": "video", "label": "h3", "since": 1.0, "phase": "held"},
              "media_busy": True, "can_start": {}}
HELD_MUSIC = {"holder": {"kind": "music", "label": "music3", "since": 1.0, "phase": "held"},
              "media_busy": True, "can_start": {}}
IDLE = {"holder": None, "media_busy": False, "can_start": {}}

CASES = [
    ({"server": "starting", "needs_setup": False, "desk_state": None}, "启动中…"),
    ({"server": "failed", "needs_setup": False, "desk_state": None}, "服务未运行"),
    ({"server": "stopped", "needs_setup": False, "desk_state": None}, "服务未运行"),
    ({"server": "owned", "needs_setup": True, "desk_state": IDLE}, "待设置"),
    ({"server": "owned", "needs_setup": False, "desk_state": IDLE}, "空闲"),
    ({"server": "attached", "needs_setup": False, "desk_state": IDLE}, "空闲"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_LLM}, "已加载 qwen3-30b"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_VIDEO}, "出片中"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_MUSIC}, "出歌中"),
    ({"server": "owned", "needs_setup": False, "desk_state": None}, "状态不可读"),
    ({"server": "owned", "needs_setup": False, "desk_state": {"unexpected": True}}, "状态不可读"),
]


@pytest.mark.parametrize("fixture,expected", CASES)
def test_menu_title(fixture, expected):
    proc = subprocess.run([harness_path(), "map-status"], input=json.dumps(fixture),
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected


@pytest.mark.parametrize("fixture,expected", [
    ({"server": "failed", "needs_setup": False, "desk_state": None}, "down"),
    ({"server": "owned", "needs_setup": False, "desk_state": IDLE}, "idle"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_LLM}, "loaded"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_VIDEO}, "busy"),
    ({"server": "owned", "needs_setup": False, "desk_state": None}, "down"),
])
def test_menu_glyph_state(fixture, expected):
    proc = subprocess.run([harness_path(), "glyph-state"], input=json.dumps(fixture),
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected


@pytest.mark.parametrize("failures,child,expected", [
    (1, "true", "keepWaiting"),
    (2, "false", "keepWaiting"),
    (3, "false", "serviceExited"),
    (3, "true", "serviceUnresponsive"),
    (7, "true", "serviceUnresponsive"),
])
def test_poll_failure_action(failures, child, expected):
    proc = subprocess.run([harness_path(), "poll-failure", str(failures), child],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected
