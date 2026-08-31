"""Make the repo root importable and share the tiny HTTP test helper."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path


_ROOT = str(Path(__file__).resolve().parents[1])
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)


def http_call(app, method, path, body=None):
    """Fire one JSON request at a DeskApp bound to 127.0.0.1:<app.port>."""
    url = f"http://127.0.0.1:{app.port}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())
