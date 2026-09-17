"""Deterministic composition root used by browser end-to-end tests."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import json
from pathlib import Path
import socket
from types import SimpleNamespace

from desk.app import DeskApp, Response
from desk.arbiter.core import Arbiter
from desk.foundation import capabilities, config, firstrun, paths
from desk.foundation.paths import normalize_user_path
from desk.foundation.routes import config_payload
from desk.gateway.service import GatewayService
from desk.library import LibraryService
from desk.library import http as library_http
from desk.llm.routes import build_routes as build_llm_routes
from desk.llm.service import LlmService
from desk.media.service import MediaService
from desk.media.routes import build_routes as build_media_routes
from desk.resources.catalog import list_catalog
from desk.resources.http import build_routes as build_resource_routes
from desk.resources.manifest import ManifestFile
from desk.resources.service import ResourcesService
from desk.ui import StaticAssets

from .fakes import (
    DEFAULT_SNAPSHOT_A,
    FakeDownloadExecutor,
    FakeLlmBackend,
    FakeMediaExecutor,
    FakeMemoryReader,
    FixedClock,
    fake_reaper,
)
from .scripts import ChatScript, DownloadControl, MediaScript, MemoryScript
from .seed import MANIFEST_FILES, build_bundle_resources, seed_models


class _GatewayBackend:
    """Read-only gateway view over the real LLM and arbiter services."""

    def __init__(self, llm: LlmService, arbiter: Arbiter):
        self._llm, self._arbiter = llm, arbiter

    def llm_status(self) -> dict:
        status = self._llm.status()
        state = status["state"]
        loaded = status["loaded_model"]
        if loaded is not None:
            loaded = {**loaded, "loaded_at": state["loaded_at"]}
        return {"state": state["status"], "loaded": loaded}

    def desk_state(self) -> dict:
        return self._arbiter.desk_state()

    def can_start_heavy(self, kind: str) -> dict:
        return self._arbiter.can_start_heavy(kind)

    def chat_completion(self, request: dict) -> dict:
        return self._llm.chat_completion(request)

    def chat_stream(self, request: dict):
        for event in self._llm.chat_stream(request):
            if event["type"] == "delta":
                if event["reasoning"] is not None:
                    yield "reasoning", event["reasoning"]
                if event["text"] is not None:
                    yield "content", event["text"]
            elif event["type"] == "done":
                yield "finish", event
            else:
                raise RuntimeError(event["message"])


@dataclass
class TestHarness:
    """Running test server plus its real services and controllable fake leaves."""

    __test__ = False

    app: DeskApp
    gateway: GatewayService
    roots: paths.PathRoots
    arbiter: Arbiter
    resources: ResourcesService
    llm: LlmService
    media: MediaService
    library: LibraryService
    chat_script: ChatScript
    media_script: MediaScript
    download_control: DownloadControl
    clock: FixedClock
    base_url: str
    data_root: Path
    models_root: Path
    outputs_root: Path
    gateway_port: int
    seeded: dict[str, str]
    routes: list[tuple[str, str]]
    reveal_calls: list[list[str]]
    _closed: bool = False
    _unsubscribe: Callable[[], None] | None = None

    def close(self) -> None:
        if not self._closed:
            if self._unsubscribe is not None:
                self._unsubscribe()
                self._unsubscribe = None
            self.gateway.stop()
            self.app.shutdown()
            self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_exc) -> None:
        self.close()


def _manifest_fetcher(_repo: str) -> list[ManifestFile]:
    return [ManifestFile(path, size) for path, size in MANIFEST_FILES]


def _free_port() -> int:
    """Reserve a loopback port number for the gateway configuration."""
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


DEFAULT_BUDGET_PAYLOAD = {
    "available_bytes": 0, "total_bytes": 0, "pressure": "normal",
    "chat": {"source": "unavailable"}, "media": {},
}


def _mount_routes(app: DeskApp, roots, resources, llm, media, library, arbiter, gateway, budget_payload):
    """Mount the real service seams behind DeskApp's deliberately small codec.

    The production route modules use richer response carriers than ``DeskApp``.
    These adapters preserve the public paths while delegating every operation to
    the real services assembled by the harness.
    """
    def adopt(req):
        legacy_root, mode = req.body.get("legacy_root"), req.body.get("mode")
        if not legacy_root or mode not in ("point", "move"):
            from desk.foundation.errors import LegacyRootError
            raise LegacyRootError("body must include legacy_root and mode 'point'|'move'")
        raw_target = req.body.get("target_root")
        result = firstrun.adopt_legacy_models(
            roots, normalize_user_path(legacy_root), mode,
            target_root=normalize_user_path(raw_target) if raw_target else None,
        )
        return {
            "mode": result.mode, "models_root": str(result.models_root),
            "adopted": list(result.adopted), "moved_bytes": result.moved_bytes,
            "source_retained": result.source_retained,
        }

    def get_paths(_req):
        caps = capabilities.probe_capabilities(roots)
        return {
            "mode": roots.mode,
            "resources_root": str(roots.resources_root),
            "static_dir": str(roots.static_dir),
            "venv_python": str(roots.venv_python),
            "mlx_h3_cmd": list(roots.mlx_h3_cmd),
            "mlx_h3_env": dict(roots.mlx_h3_env),
            "music_python": str(roots.music_python),
            "music_env": dict(roots.music_env),
            "media_cli_dir": str(roots.media_cli_dir),
            "hf_cmd": list(roots.hf_cmd),
            "hf_env": dict(roots.hf_env),
            "data_root": str(roots.data_root),
            "config_path": str(roots.config_path),
            "logs_dir": str(roots.logs_dir),
            "sessions_dir": str(roots.sessions_dir),
            "history_path": str(roots.history_path),
            "models_root": str(roots.models_root),
            "outputs_root": str(roots.outputs_root),
            "capabilities": {
                name: {"present": cap.present, "path": cap.path, "detail": cap.detail}
                for name, cap in caps.items()
            },
        }

    def resource_adapter(req, handler):
        # Mirrors desk/runtime.py's unwrap: the shipped chat selector consumes
        # the catalog as a bare array, not the {"models": [...]} envelope.
        status, payload = handler(req.query, req.body, **req.path_params)
        if req.path == "/api/resources/catalog" and isinstance(payload, dict):
            payload = payload.get("models", payload)
        return status, payload

    def llm_adapter(req, handler):
        result = handler(req.body)
        return Response(result.status, result.body, sse=result.sse)

    def library_adapter(req, handler):
        result = handler(library_http.LibRequest(
            path_params=req.path_params, query=req.query,
            headers=req.headers, body=req.raw_body,
        ))
        return Response(result.status, result.body, result.headers)

    table = [
        ("GET", "/api/config", lambda _req: config_payload(roots)),
        ("PUT", "/api/config", lambda req: config.update_config(roots, **req.body).to_json()),
        ("POST", "/api/config/reset", lambda req: config.reset_config(roots, force=bool((req.body or {}).get("force")))),
        ("GET", "/api/paths", get_paths),
        ("POST", "/api/first-run", lambda req: firstrun.complete_first_run(
            roots, normalize_user_path(req.body["models_root"])
            if req.body.get("models_root") else None,
        ).to_json()),
        ("POST", "/api/adopt", adopt),
        ("POST", "/api/models/discover", lambda _req: {
            "models_root": str(firstrun.apply_discovered(roots)[0].models_root),
            "candidates": firstrun.discover_model_roots(roots),
            "found": bool(firstrun.discover_model_roots(roots)),
        }),
        *((method, path, lambda req, handler=handler: resource_adapter(req, handler))
          for method, path, handler in build_resource_routes(resources)),
        *((route.method, route.path, lambda req, handler=route.handler: llm_adapter(req, handler))
          for route in build_llm_routes(llm)),
        *((method, path, lambda req, handler=handler: handler(req.body, req.query))
          for method, path, handler in build_media_routes(media)),
        *((method, path, lambda req, handler=handler: library_adapter(req, handler))
          for method, path, handler in library_http.routes(library)),
        ("GET", "/api/state", lambda _req: arbiter.desk_state()),
        ("GET", "/api/memory", lambda _req: arbiter.memory_snapshot()),
        # 台面前端每个 tick 都会取它；测试台面不挂的话，e2e 里状态栏会一直报离线。
        # 缺省写死为「算不出」，与压缩测试前的既有行为一致；压缩 e2e 需要一个很小
        # 的 compact_at 才能触发，靠 launch_test_harness(budget=...) 覆盖。
        ("GET", "/api/budget", lambda _req: dict(budget_payload)),
        ("POST", "/api/gateway/config", lambda _req: gateway.handle_config_request("POST")[1]),
        ("GET", "/api/gateway/config", lambda _req: gateway.handle_config_request("GET")[1]),
    ]
    app.add_routes(table)
    return [(method, path) for method, path, _handler in table]


def launch_test_harness(
    tmp_path: Path,
    *,
    configured: bool = True,
    model_states: dict[str, str] | None = None,
    gateway_enabled: bool = True,
    chat_script: ChatScript | None = None,
    media_script: MediaScript | None = None,
    download_control: DownloadControl | None = None,
    memory_script: MemoryScript | None = None,
    budget: dict | None = None,
) -> TestHarness:
    """Launch real desk services against seeded files and deterministic fakes.

    Both HTTP listeners use port ``0`` so parallel test workers never contend
    for a fixed port.  Call :meth:`TestHarness.close` when the test is done.
    """
    tmp_path = Path(tmp_path)
    resources_root = build_bundle_resources(tmp_path)
    data_root = tmp_path / "data"
    initial_roots = paths.resolve_paths(data_root=data_root, resources_root=resources_root)
    seeded = seed_models(initial_roots.models_root, list_catalog(), model_states)
    gateway_port = _free_port()
    if configured:
        firstrun.complete_first_run(initial_roots, initial_roots.models_root)
        config.update_config(initial_roots, gateway={
            "enabled": gateway_enabled, "host": "127.0.0.1", "port": gateway_port,
        })
    roots = paths.resolve_paths(data_root=data_root, resources_root=resources_root)

    clock = FixedClock()
    chat_script = chat_script or ChatScript()
    media_script = media_script or MediaScript()
    download_control = download_control or DownloadControl()
    memory_script = memory_script or MemoryScript([DEFAULT_SNAPSHOT_A])
    arbiter = Arbiter(
        0, memory=FakeMemoryReader(memory_script), reaper=fake_reaper, clock=clock
    )
    resources = ResourcesService(
        resolve_paths=lambda: roots,
        # Downloader invokes this callback with no arguments.  Downloads use
        # the video reservation class; "download" is not an Arbiter kind.
        can_start_heavy=lambda: arbiter.can_start_heavy("video"),
        fetcher=_manifest_fetcher,
        executor=FakeDownloadExecutor(download_control),
        clock=clock,
        sleep=lambda _seconds: None,
    )
    library = LibraryService(roots)
    reveal_calls: list[list[str]] = []
    # Real "open -R" would launch Finder during test runs; record calls instead
    # (mirrors the seam tests/test_library_http.py already exercises).
    library.outputs.set_opener(lambda argv, **_kw: reveal_calls.append(list(argv)))
    llm = LlmService(
        FakeLlmBackend(chat_script), arbiter, resources,
        SimpleNamespace(resolve_paths=lambda: roots), port=0,
        poll_interval_s=0.001,
    )
    media = MediaService(
        resolve_paths=lambda: roots,
        probe_capabilities=lambda: capabilities.probe_capabilities(roots),
        arbiter=arbiter,
        list_catalog=resources.list_catalog,
        append_history=library.append_history,
        executor=FakeMediaExecutor(media_script),
        clock=clock,
    )
    app = DeskApp("127.0.0.1", 0)
    static_assets = StaticAssets(roots.static_dir)
    handler_type = app._server.RequestHandlerClass
    dispatch_json = handler_type._dispatch

    def dispatch_with_static(handler, method: str) -> None:
        resolved = static_assets.resolve(handler.path)
        if resolved is None:
            # Intentionally pre-empts the route table below: every POST here
            # streams SSE frames directly, before _find() ever sees the
            # request, regardless of what the /api/llm/chat/stream entry
            # built by build_llm_routes (kept in the table below) would do.
            if method == "POST" and handler.path.split("?", 1)[0] == "/api/llm/chat/stream":
                length = int(handler.headers.get("Content-Length") or 0)
                body = json.loads(handler.rfile.read(length).decode("utf-8")) if length else {}
                handler.send_response(200)
                handler.send_header("Content-Type", "text/event-stream; charset=utf-8")
                handler.send_header("Cache-Control", "no-cache")
                handler.end_headers()
                for event in llm.chat_stream(body):
                    handler.wfile.write(
                        b"data: " + json.dumps(event, ensure_ascii=False).encode("utf-8") + b"\n\n"
                    )
                    handler.wfile.flush()
                return
            dispatch_json(handler, method)
            return
        asset, content_type = resolved
        data = asset.read_bytes()
        handler.send_response(200)
        handler.send_header("Content-Type", content_type)
        handler.send_header("Content-Length", str(len(data)))
        handler.end_headers()
        handler.wfile.write(data)

    handler_type._dispatch = dispatch_with_static
    handler_type.do_PATCH = lambda handler: handler._dispatch("PATCH")
    gateway = GatewayService(
        _GatewayBackend(llm, arbiter),
        lambda: config.read_config(roots).to_json(),
    )
    budget_payload = budget if budget is not None else DEFAULT_BUDGET_PAYLOAD
    route_specs = _mount_routes(app, roots, resources, llm, media, library, arbiter, gateway, budget_payload)
    app.start_background()
    if configured and gateway_enabled:
        gateway.start_from_config()
    return TestHarness(
        app, gateway, roots, arbiter, resources, llm, media, library,
        chat_script, media_script, download_control, clock,
        f"http://127.0.0.1:{app.port}", roots.data_root, roots.models_root,
        roots.outputs_root, gateway_port, seeded, route_specs, reveal_calls,
        _unsubscribe=llm.close,
    )
