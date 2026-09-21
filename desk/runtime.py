"""Production composition root for the Desk HTTP and gateway services."""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging
from pathlib import Path
import time

from .app import DeskApp, Response
from .arbiter import Arbiter, MemoryReader
from .budget import Budget
from .budget.store import Measurements
from .foundation import capabilities, config, paths, routes as foundation_routes
from .foundation.errors import ConfigCorruptError
from .gateway.desk_backend import DeskGatewayBackend
from .gateway.service import GatewayService
from .library import LibraryService
from .library import http as library_http
from .llm.backend import MlxLmBackend
from .llm.routes import build_routes as build_llm_routes
from .llm.service import LlmService
from .llm.state import DEFAULT_LLM_PORT
from .media.executor import SubprocessExecutor
from .media.memory_estimate import estimate_bytes as media_estimate_bytes
from .media.routes import build_routes as build_media_routes
from .media.service import MediaService
from .resources.http import build_routes as build_resource_routes
from .resources.service import ResourcesService
from .ui import StaticAssets

log = logging.getLogger(__name__)


def _gateway_config_reader():
    """Read gateway config for the gateway service; corrupt config disables it
    instead of raising into startup (a corrupt config.json must not hang or
    crash the whole service — cross-exam G8)."""
    def read() -> dict:
        roots = paths.resolve_paths(default_config_on_corrupt=True)
        try:
            return config.read_config(roots).to_json()
        except ConfigCorruptError:
            log.error("config.json is corrupt; gateway falls back to defaults with listening disabled")
            defaults = config.default_config(roots.data_root).to_json()
            defaults["gateway"]["enabled"] = False
            return defaults
    return read


@dataclass
class ProductionRuntime:
    app: DeskApp
    gateway: GatewayService
    llm: LlmService
    media: MediaService
    resources: ResourcesService
    _closed: bool = False

    @property
    def port(self) -> int:
        return self.app.port

    def _start_gateway(self) -> None:
        try:
            self.gateway.start_from_config()
        except Exception:  # the gateway is optional; the desk must still serve
            log.exception("gateway failed to start; continuing without it")

    def start_background(self) -> None:
        self._start_gateway()
        self.app.start_background()

    def serve_forever(self) -> None:
        self._start_gateway()
        self.app.serve_forever()

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.gateway.stop()
        self.resources.close()
        self.media.close()
        self.llm.close()
        self.app.shutdown()


def _budget_payload(budget, llm, resources, roots) -> dict:
    """`/api/budget`：额度快照 + 当前驻留模型的对话额度，每个数字带来源（R-budget-01）。

    没有驻留模型时 Budget.snapshot_with_chat() 自己把 chat 记成「算不出」；
    只读 config.json 取声明窗口，绝不写模型目录。
    """
    loaded = (llm.status() or {}).get("loaded_model")
    if not loaded:
        return budget.snapshot_with_chat()
    entry = next((e for e in resources.list_catalog() if e.key == loaded["key"]), None)
    config: dict = {}
    if entry is not None:
        config_path = Path(roots.models_root) / entry.relpath / "config.json"
        try:
            data = json.loads(config_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if isinstance(data, dict):
            config = data
    return budget.snapshot_with_chat(loaded["key"], config, loaded["gb"])


def _mount_routes(app, roots, resources, llm, media, library, arbiter, gateway, budget) -> None:
    app.add_routes(foundation_routes.build_routes())

    for method, pattern, handler in build_resource_routes(resources):
        def resource_adapter(req, handler=handler):
            status, payload = handler(req.query, req.body, **req.path_params)
            # The shipped chat selector consumes the catalog as a bare array.
            if req.path == "/api/resources/catalog" and isinstance(payload, dict):
                payload = payload.get("models", payload)
            return Response(status, payload)
        app.add_routes([(method, pattern, resource_adapter)])

    for route in build_llm_routes(llm):
        def llm_adapter(req, handler=route.handler):
            result = handler(req.body)
            return Response(result.status, result.body, sse=result.sse)
        app.add_routes([(route.method, route.path, llm_adapter)])

    for method, pattern, handler in build_media_routes(media):
        def media_adapter(req, handler=handler):
            status, payload = handler(req.body, req.query)
            return Response(status, payload)
        app.add_routes([(method, pattern, media_adapter)])

    for method, pattern, handler in library_http.routes(library):
        def library_adapter(req, handler=handler):
            result = handler(library_http.LibRequest(
                path_params=req.path_params,
                query=req.query,
                headers=req.headers,
                body=req.raw_body,
            ))
            return Response(result.status, result.body, result.headers)
        app.add_routes([(method, pattern, library_adapter)])

    app.add_routes([
        ("GET", "/api/state", lambda _req: arbiter.desk_state()),
        ("GET", "/api/memory", lambda _req: arbiter.memory_snapshot()),
        ("GET", "/api/budget", lambda _req: Response(
            200, _budget_payload(budget, llm, resources, roots)
        )),
        ("GET", "/api/gateway/config", lambda _req: Response(
            *gateway.handle_config_request("GET")
        )),
        ("POST", "/api/gateway/config", lambda _req: Response(
            *gateway.handle_config_request("POST")
        )),
    ])
    app.static_assets = StaticAssets(roots.static_dir)


def build_runtime(host: str = "127.0.0.1", port: int = 8766) -> ProductionRuntime:
    """Assemble production services using only real leaf implementations."""
    roots = paths.resolve_paths(default_config_on_corrupt=True)
    paths.setup_logging(roots)
    resolve_paths = paths.resolve_paths
    measurements_path = roots.data_root / "measurements.json"
    measurements = Measurements.load(measurements_path)
    memory_reader = MemoryReader()
    budget = Budget(
        measurements=measurements,
        memory_reader=memory_reader,
        media_estimate=media_estimate_bytes,
        now=time.time,
        measurements_path=measurements_path,
        # 问机器能力要用装了 mlx 的那个解释器——台面自己的通常没有（R-budget-16）。
        probe_python=roots.venv_python,
    )
    arbiter = Arbiter(DEFAULT_LLM_PORT, budget=budget)
    resources = ResourcesService(
        resolve_paths=resolve_paths,
        can_start_heavy=lambda: arbiter.can_start_heavy("video"),
    )
    library = LibraryService(roots)
    llm = LlmService(
        MlxLmBackend(), arbiter, resources, paths, port=DEFAULT_LLM_PORT, budget=budget
    )
    arbiter.set_owned_pid_provider(llm.owned_pids)
    media = MediaService(
        resolve_paths=resolve_paths,
        probe_capabilities=lambda: capabilities.probe_capabilities(resolve_paths()),
        arbiter=arbiter,
        list_catalog=resources.list_catalog,
        append_history=library.append_history,
        executor=SubprocessExecutor(),
        measurements=measurements,
        measurements_path=measurements_path,
        available_bytes=lambda: memory_reader.snapshot().available_bytes,
    )
    gateway = GatewayService(DeskGatewayBackend(llm, arbiter), _gateway_config_reader())
    gateway.on_rollback = lambda cfg: config.update_config(roots, gateway=cfg)
    app = DeskApp(host, port)
    _mount_routes(app, roots, resources, llm, media, library, arbiter, gateway, budget)
    app.capabilities = capabilities.probe_capabilities(roots)
    return ProductionRuntime(app, gateway, llm, media, resources)
