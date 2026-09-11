"""Gateway lifecycle, configuration application, and gateway status."""
from __future__ import annotations

import threading

from .http_server import GatewayHTTPServer
from .lan import lan_candidates, pick_lan_host, read_ifconfig

_DEFAULTS = {"enabled": True, "host": "0.0.0.0", "port": 8770}

_BIND_HINTS = {
    48: "该端口已被占用，换一个端口再试",
    49: "本机没有这个地址，请填 0.0.0.0、127.0.0.1 或本机网卡地址",
    13: "该端口需要更高权限，请改用 1024 以上的端口",
}


def _bind_message(host: str, port: int, exc: OSError) -> str:
    """OS 原文永远不是唯一解释（视觉基线 C3/F2）：附上人话提示与系统原文两份说明。"""
    hint = _BIND_HINTS.get(exc.errno, "请检查主机与端口")
    detail = exc.strerror or str(exc)
    return f"无法绑定 {host}:{port}——{hint}（系统报告：{detail}）"


def _lan_host(host: str) -> tuple[str, list[str]]:
    """Resolve a reachable LAN address for a wildcard bind, else echo the explicit host.

    The default-route probe used to return a VPN tunnel address (100.64.0.0/10) whenever
    a VPN was up — unreachable from anything else on the LAN (cross-exam 2026-09-08,
    J8/J19). `desk.gateway.lan` enumerates real interfaces instead.
    """
    if host != "0.0.0.0":
        return host, [host]
    output = read_ifconfig()
    candidates = lan_candidates(output)
    return (pick_lan_host(output) or "127.0.0.1"), candidates


class GatewayService:
    def __init__(self, backend, read_config, *, server_factory=GatewayHTTPServer):
        self._backend = backend
        self._read_config = read_config
        self._server_factory = server_factory
        self._server = None
        self._thread = None
        self._applied = None
        self._bound_port = None
        self._last_error = None
        self._last_good: tuple | None = None
        self.on_rollback = None

    def _gateway_config(self) -> dict:
        cfg = dict(_DEFAULTS)
        cfg.update((self._read_config() or {}).get("gateway") or {})
        return cfg

    def _start(self, cfg: dict) -> None:
        """Bind (or not) from an explicit config dict — never re-reads storage, so a
        rollback can retry the last-known-good config even if storage still holds the
        bad one (F12)."""
        self._applied = (bool(cfg["enabled"]), cfg["host"], cfg["port"])
        self._last_error = None
        if not cfg["enabled"]:
            return
        try:
            self._server = self._server_factory((cfg["host"], cfg["port"]), self._backend)
        except OSError as exc:
            self._server = None
            self._last_error = _bind_message(cfg["host"], cfg["port"], exc)
            return
        self._bound_port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="gateway-http", daemon=True
        )
        self._thread.start()
        self._last_good = self._applied

    def start_from_config(self) -> None:
        """Listen only when enabled; record bind errors without raising them."""
        self._start(self._gateway_config())

    def apply_config(self) -> dict:
        """Re-read configuration and replace the listener when it has changed.

        A bind failure never leaves the gateway parked on the bad config: it rolls back
        to the last address that actually bound and persists that rollback (F12), while
        keeping the plain-Chinese failure reason visible in `last_error`.
        """
        cfg = self._gateway_config()
        wanted = (bool(cfg["enabled"]), cfg["host"], cfg["port"])
        listening = self._server is not None
        if wanted == self._applied and listening == wanted[0]:
            return self.status()
        self.stop()
        self._start(cfg)
        if self._server is None and wanted[0] and self._last_good is not None and self._last_good != wanted:
            failure = self._last_error
            enabled, host, port = self._last_good
            restored = {"enabled": enabled, "host": host, "port": port}
            if self.on_rollback is not None:
                self.on_rollback(restored)
            self._start(restored)
            self._last_error = failure
        return self.status()

    def stop(self) -> None:
        """Close the listener and wait briefly for its serving thread to exit."""
        server, thread = self._server, self._thread
        self._server = None
        self._thread = None
        self._bound_port = None
        if server is not None:
            server.shutdown()
            server.server_close()
        if thread is not None:
            thread.join(timeout=10)

    def status(self) -> dict:
        """Return the current data:gatewayStatus projection."""
        if self._server is not None:
            enabled, host, _ = self._applied
            listening, port = True, self._bound_port
        else:
            cfg = self._gateway_config()
            enabled, host, port = bool(cfg["enabled"]), cfg["host"], cfg["port"]
            listening = False
        lan_host, lan_hosts = _lan_host(host)
        return {
            "enabled": enabled,
            "listening": listening,
            "host": host,
            "port": port,
            "lan_host": lan_host,
            "lan_candidates": lan_hosts,
            "openai_base_url": f"http://{lan_host}:{port}/v1",
            "anthropic_base_url": f"http://{lan_host}:{port}",
            "auth": "none",
            "last_error": self._last_error,
        }

    def handle_config_request(self, method: str, body=None):
        """Return the gateway configuration/status or apply persisted changes."""
        if method == "GET":
            return 200, {"config": self._gateway_config(), "status": self.status()}
        if method == "POST":
            return 200, {"config": self._gateway_config(), "status": self.apply_config()}
        return 405, {
            "error": {
                "message": "GET or POST only",
                "type": "invalid_request_error",
                "code": "method_not_allowed",
            }
        }
