"""Production composition root for the Desk HTTP and gateway services."""
from __future__ import annotations

from dataclasses import dataclass

from .app import DeskApp, Response
from .arbiter import Arbiter
from .foundation import capabilities, config, firstrun, paths, routes as foundation_routes
from .gateway.desk_backend import DeskGatewayBackend
from .gateway.service import GatewayService
from .library import LibraryService
from .library import http as library_http
from .llm.backend import MlxLmBackend
from .llm.routes import build_routes as build_llm_routes
from .llm.service import LlmService
from .llm.state import DEFAULT_LLM_PORT
from .media.executor import SubprocessExecutor
from .media.routes import build_routes as build_media_routes
from .media.service import MediaService
from .resources.http import build_routes as build_resource_routes
from .resources.service import ResourcesService
from .ui import StaticAssets


@dataclass
class ProductionRuntime:
    app: DeskApp
    gateway: GatewayService
    llm: LlmService
    _closed: bool = False

    @property
    def port(self) -> int:
        return self.app.port

    def start_background(self) -> None:
        self.gateway.start_from_config()
        self.app.start_background()

    def serve_forever(self) -> None:
        self.gateway.start_from_config()
        self.app.serve_forever()

    def shutdown(self) -> None:
        if self._closed:
            return
        self._closed = True
        self.gateway.stop()
        self.llm.close()
        self.app.shutdown()


def _mount_routes(app, roots, resources, llm, media, library, arbiter, gateway) -> None:
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
    firstrun.auto_configure_discovered(roots)
    roots = paths.resolve_paths(default_config_on_corrupt=True)
    paths.setup_logging(roots)
    resolve_paths = paths.resolve_paths
    arbiter = Arbiter(DEFAULT_LLM_PORT)
    resources = ResourcesService(
        resolve_paths=resolve_paths,
        can_start_heavy=lambda: arbiter.can_start_heavy("video"),
    )
    library = LibraryService(roots)
    llm = LlmService(
        MlxLmBackend(), arbiter, resources, paths, port=DEFAULT_LLM_PORT
    )
    media = MediaService(
        resolve_paths=resolve_paths,
        probe_capabilities=lambda: capabilities.probe_capabilities(resolve_paths()),
        arbiter=arbiter,
        list_catalog=resources.list_catalog,
        append_history=library.append_history,
        executor=SubprocessExecutor(),
    )
    gateway = GatewayService(
        DeskGatewayBackend(llm, arbiter),
        lambda: config.read_config(
            paths.resolve_paths(default_config_on_corrupt=True)
        ).to_json(),
    )
    app = DeskApp(host, port)
    _mount_routes(app, roots, resources, llm, media, library, arbiter, gateway)
    app.capabilities = capabilities.probe_capabilities(roots)
    return ProductionRuntime(app, gateway, llm)
