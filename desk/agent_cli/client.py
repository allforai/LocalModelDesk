"""JSON over HTTP to the desk, with connection failures sorted into refused / sandbox / other (A-33)."""
from __future__ import annotations

import errno
import json
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_SANDBOX_ERRNOS = {errno.EPERM, errno.EACCES}


class Unreachable(Exception):
    def __init__(self, kind: str, detail: str):
        super().__init__(detail)
        self.kind, self.detail = kind, detail


class HttpError(Exception):
    def __init__(self, status: int, code: str, message: str, detail: dict):
        super().__init__(message)
        self.status, self.code, self.message, self.detail = status, code, message, detail


def classify_os_error(exc: OSError) -> str:
    if exc.errno == errno.ECONNREFUSED:
        return "refused"
    if exc.errno in _SANDBOX_ERRNOS:
        return "sandbox"
    return "other"


def _http_error(exc: HTTPError) -> HttpError:
    code, message, detail = f"http_{exc.code}", f"HTTP {exc.code}", {}
    try:
        payload = json.loads(exc.read() or b"{}")
    except ValueError:
        payload = {}
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, str) and error:
        message = error
    elif isinstance(error, dict):
        code = error.get("code") or code
        message = error.get("message") or message
        detail = error.get("detail") if isinstance(error.get("detail"), dict) else {}
    return HttpError(exc.code, code, message, detail)


class DeskClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url, self.timeout = base_url.rstrip("/"), timeout

    def _send(self, method: str, path: str, body=None, query=None, timeout: float | None = None):
        url = self.base_url + path + (("?" + urlencode(query)) if query else "")
        data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
        req = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
        try:
            with urlopen(req, timeout=timeout or self.timeout) as response:
                raw = response.read()
        except HTTPError as exc:
            raise _http_error(exc) from None
        except URLError as exc:
            reason = exc.reason
            kind = classify_os_error(reason) if isinstance(reason, OSError) else "other"
            raise Unreachable(kind, str(reason)) from None
        except OSError as exc:
            raise Unreachable(classify_os_error(exc), str(exc)) from None
        return json.loads(raw) if raw else None

    def get(self, path, query=None):
        return self._send("GET", path, query=query)

    def post(self, path, body=None, timeout: float | None = None):
        return self._send("POST", path, body if body is not None else {}, timeout=timeout)

    def patch(self, path, body):
        return self._send("PATCH", path, body)
