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
HELD_LLM_DISPLAY = {
    "holder": {"kind": "llm", "label": "glm", "display": "GLM 4.7 Flash 越狱 4bit",
               "since": 1.0, "phase": "held"},
    "media_busy": False, "can_start": {},
}
HELD_MUSIC_DISPLAY = {
    "holder": {"kind": "music", "label": "job-2", "display": "音乐生成中", "since": 1.0, "phase": "held"},
    "media_busy": True, "can_start": {},
}
IDLE = {"holder": None, "media_busy": False, "can_start": {}}

CASES = [
    ({"server": "starting", "needs_setup": False, "desk_state": None}, "启动中…"),
    ({"server": "failed", "needs_setup": False, "desk_state": None}, "服务未运行"),
    ({"server": "stopped", "needs_setup": False, "desk_state": None}, "服务未运行"),
    ({"server": "owned", "needs_setup": True, "desk_state": IDLE}, "待设置"),
    ({"server": "owned", "needs_setup": False, "desk_state": IDLE}, "空闲"),
    ({"server": "attached", "needs_setup": False, "desk_state": IDLE}, "空闲"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_LLM}, "已加载 qwen3-30b"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_VIDEO}, "视频生成中"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_MUSIC}, "音乐生成中"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_LLM_DISPLAY},
     "已加载 GLM 4.7 Flash 越狱 4bit"),
    ({"server": "owned", "needs_setup": False, "desk_state": HELD_MUSIC_DISPLAY}, "音乐生成中"),
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


@pytest.mark.parametrize("used,total,available,expected", [
    (62_461_775_872, 137_438_953_472, 74_977_177_600, "内存 已用 58 / 总 128 GiB（可用 70 GiB）"),
    (0, 137_438_953_472, 137_438_953_472, "内存 已用 0 / 总 128 GiB（可用 128 GiB）"),
    # N3：同屏三处内存读数因 0.4 GiB 抖动而不同（79.0/79.4/79.2）；取整后一致。
    (84_825_593_856, 137_438_953_472, 52_613_359_616,
     "内存 已用 79 / 总 128 GiB（可用 49 GiB）"),
])
def test_memory_menu_title_matches_web_wording(used, total, available, expected):
    proc = subprocess.run([harness_path(), "memory-line", str(used), str(total), str(available)],
                          capture_output=True, text=True, timeout=30)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected
