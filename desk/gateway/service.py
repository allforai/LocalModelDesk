"""Gateway lifecycle, configuration application, and gateway status."""
from __future__ import annotations

import threading

from .http_server import GatewayHTTPServer
from .lan import lan_candidates, pick_lan_host, read_ifconfig

_DEFAULTS = {"enabled": True, "host": "0.0.0.0", "port": 8770}


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

    def _gateway_config(self) -> dict:
        cfg = dict(_DEFAULTS)
        cfg.update((self._read_config() or {}).get("gateway") or {})
        return cfg

    def start_from_config(self) -> None:
        """Listen only when enabled; record bind errors without raising them."""
        cfg = self._gateway_config()
        self._applied = (bool(cfg["enabled"]), cfg["host"], cfg["port"])
        self._last_error = None
        if not cfg["enabled"]:
            return
        try:
            self._server = self._server_factory((cfg["host"], cfg["port"]), self._backend)
        except OSError as exc:
            self._server = None
            detail = exc.strerror or str(exc)
            self._last_error = (
                f"bind {cfg['host']}:{cfg['port']} failed: [errno {exc.errno}] {detail}"
            )
            return
        self._bound_port = self._server.server_address[1]
        self._thread = threading.Thread(
            target=self._server.serve_forever, name="gateway-http", daemon=True
        )
        self._thread.start()

    def apply_config(self) -> dict:
        """Re-read configuration and replace the listener when it has changed."""
        cfg = self._gateway_config()
        wanted = (bool(cfg["enabled"]), cfg["host"], cfg["port"])
        listening = self._server is not None
        if wanted == self._applied and listening == wanted[0]:
            return self.status()
        self.stop()
        self.start_from_config()
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
