#!/usr/bin/env python3
"""Local model desk — launch and API tests.

Run: python3 /Users/aa/localModelDesk/media-gui/tests/test_desk.py
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

HOME = Path.home()
APP = HOME / "Applications" / "LocalModelDesk.app"
EXE = APP / "Contents" / "MacOS" / "LocalModelDesk"
DESK = "http://127.0.0.1:8766"
LLM_API = "http://127.0.0.1:8767/v1"
MODELS = Path(__file__).resolve().parents[2]


def get(url: str, timeout: float = 5):
    return urllib.request.urlopen(url, timeout=timeout)


def get_json(url: str, timeout: float = 5):
    with get(url, timeout=timeout) as r:
        return json.loads(r.read().decode())


class TestAppBundle(unittest.TestCase):
    def test_bundle_layout(self):
        self.assertTrue(APP.is_dir(), "App bundle missing")
        self.assertTrue((APP / "Contents" / "Info.plist").is_file())
        self.assertTrue(os.access(EXE, os.X_OK), "executable not +x")

    def test_executable_is_native_app(self):
        out = subprocess.check_output(["file", str(EXE)], text=True)
        self.assertIn("Mach-O", out)
        self.assertNotIn("shell script", out)

    def test_app_stays_alive_two_seconds(self):
        proc = subprocess.Popen(
            [str(EXE)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        try:
            time.sleep(2.0)
            self.assertIsNone(proc.poll(), "app process exited immediately (flash quit)")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                proc.kill()


class TestServerApi(unittest.TestCase):
    def test_home_200(self):
        with get(DESK + "/") as r:
            self.assertEqual(r.status, 200)
            body = r.read().decode()
        self.assertIn("本地模型台", body)
        self.assertIn("8767", body, "chat should hit mlx-lm not LM Studio 1234")
        self.assertNotIn("127.0.0.1:1234", body)

    def test_planner_idle_shape(self):
        data = get_json(DESK + "/api/planner")
        self.assertEqual(data.get("ram_gb"), 128)
        self.assertIn("loaded", data)
        self.assertIn("media", data)
        self.assertIn("advice", data)

    def test_six_llm_models_on_disk(self):
        models = get_json(DESK + "/api/llm/models")
        self.assertEqual(len(models), 6)
        for m in models:
            self.assertTrue(Path(m["path"]).exists(), m["path"])
            self.assertTrue(str(m["path"]).startswith(str(MODELS / "llms")))

    def test_history_endpoint(self):
        hist = get_json(DESK + "/api/history")
        self.assertIsInstance(hist, list)

    def test_video_range_seek(self):
        files = list((MODELS / "outputs").glob("h3-*.mp4"))
        if not files:
            self.skipTest("no h3 sample video")
        name = files[0].name
        req = urllib.request.Request(
            f"{DESK}/file/{name}",
            headers={"Range": "bytes=0-1023"},
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            self.assertEqual(r.status, 206)
            self.assertEqual(r.headers.get("Accept-Ranges"), "bytes")
            self.assertTrue((r.headers.get("Content-Range") or "").startswith("bytes 0-1023/"))
            self.assertEqual(len(r.read()), 1024)


class TestModelLayout(unittest.TestCase):
    def test_shared_models_folder(self):
        self.assertTrue((MODELS / "llms").is_dir())
        self.assertTrue((MODELS / "minimax-h3" / "mlx-8bit").is_dir())
        self.assertTrue((MODELS / "minimax-music3").is_dir())
        self.assertFalse((HOME / ".lmstudio" / "models").exists())

    def test_launchagent_installed(self):
        plist = HOME / "Library" / "LaunchAgents" / "com.aa.localmodeldesk.plist"
        self.assertTrue(plist.is_file())
        out = subprocess.check_output(
            ["launchctl", "print", f"gui/{os.getuid()}/com.aa.localmodeldesk"],
            text=True,
            stderr=subprocess.STDOUT,
        )
        self.assertIn("state = running", out)


class TestMutex(unittest.TestCase):
    def test_unload_endpoint(self):
        req = urllib.request.Request(DESK + "/api/llm/unload", method="POST", data=b"{}")
        with urllib.request.urlopen(req, timeout=10) as r:
            self.assertEqual(r.status, 200)
        time.sleep(0.4)
        plan = get_json(DESK + "/api/planner")
        self.assertEqual(plan.get("loaded"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
