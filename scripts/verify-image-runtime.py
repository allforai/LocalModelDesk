"""Opt-in real HTTP generation/cancellation smoke; no mocks, isolated data only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--models-root", type=Path, required=True)
    parser.add_argument("--steps", type=int, default=4)
    args = parser.parse_args()
    evidence = args.evidence.resolve()
    evidence.mkdir(parents=True, exist_ok=True)
    data = evidence / "isolated-data"
    if data.exists():
        parser.error("Evidence data directory already exists; use a new attempt directory")
    os.environ["LOCALMODELDESK_DATA_ROOT"] = str(data)
    from desk.foundation.paths import resolve_paths
    from desk.foundation.config import update_config
    from desk.runtime import build_runtime
    from PIL import Image

    roots = resolve_paths()
    update_config(roots, models_root=str(args.models_root.resolve()), first_run_done=True,
                  gateway={"enabled": False}, outputs_root=str(data / "outputs"))
    runtime = build_runtime(port=0)
    runtime.start_background()
    base = f"http://127.0.0.1:{runtime.port}"
    report = {"served_by": {"host": base, "process": os.getpid(), "mock_layers": [], "fixtures": []},
              "requests": [], "status": "running"}

    def request(path, body=None):
        req = urllib.request.Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.load(response)
        return result

    def terminal():
        deadline = time.monotonic() + 600
        while time.monotonic() < deadline:
            state = request("/api/media/job")
            if state["status"] != "running":
                return state
            time.sleep(1)
        raise TimeoutError("Image job did not finish")

    try:
        report["capabilities"] = request("/api/capabilities")
        report["memory_before"] = request("/api/memory")
        report["model"] = runtime.resources.verify_model("qwen-image").to_json()
        report["download_start"] = request("/api/resources/download", {"key": "qwen-image"})
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            report["download_finished"] = request("/api/resources/download")
            if report["download_finished"]["state"] != "running":
                break
            time.sleep(0.2)
        assert report["download_finished"]["state"] == "finished", report["download_finished"]
        report["model_after_download"] = request("/api/resources/status/qwen-image")
        assert report["model_after_download"]["state"] == "present"
        payload = dict(prompt="A small orange cat beside a blue ceramic cup, warm afternoon light, watercolor illustration", width=512, height=512, steps=args.steps, seed=42)
        report["requests"].append({"path": "/api/media/image", "body": dict(payload), "response": request("/api/media/image", payload)})
        handle = runtime.media._handle
        report["generation_pid"] = handle.pid
        result = terminal()
        report["generation"] = result
        report["generation_returncode"] = handle.poll()
        assert result["status"] == "done", result
        output = data / "outputs" / result["output"]
        with Image.open(output) as img:
            img.load()
            report["png"] = {"path": str(output), "size": list(img.size), "format": img.format,
                             "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
        report["after_generation"] = request("/api/state")
        payload["steps"] = 40
        report["requests"].append({"path": "/api/media/image", "body": dict(payload), "response": request("/api/media/image", payload)})
        handle = runtime.media._handle
        report["cancel_pid"] = handle.pid
        time.sleep(3)
        report["cancel_response"] = request("/api/media/cancel", {})
        report["cancelled"] = terminal()
        report["cancel_returncode"] = handle.poll()
        report["after_cancel"] = request("/api/state")
        assert report["cancelled"]["status"] == "cancelled"
        assert handle.poll() is not None
        assert not report["after_cancel"]["media_busy"]
        report["status"] = "passed"
    except Exception as exc:
        report["status"] = "failed"
        report["error"] = repr(exc)
        raise
    finally:
        runtime.shutdown()
        report["server_stopped"] = True
        (evidence / "http-smoke.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
        print(json.dumps({"status": report["status"], "report": str(evidence / "http-smoke.json")}), flush=True)


if __name__ == "__main__":
    main()
