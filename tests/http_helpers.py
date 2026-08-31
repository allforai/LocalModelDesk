"""HTTP helpers shared by independently collected test suites."""
import json
import urllib.error
import urllib.request


def http_call(app, method, path, body=None):
    """Fire one JSON request at a DeskApp bound to its loopback port."""
    url = f"http://127.0.0.1:{app.port}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=5) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())
