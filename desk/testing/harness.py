"""Deterministic composition root used by browser end-to-end tests."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import socket
from types import SimpleNamespace

from desk.app import DeskApp
from desk.arbiter.core import Arbiter
from desk.foundation import capabilities, config, firstrun, paths
from desk.foundation.paths import normalize_user_path
from desk.gateway.service import GatewayService
from desk.library import LibraryService
from desk.llm.service import LlmService
from desk.media.service import MediaService
from desk.resources.catalog import list_catalog
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


def _mount_routes(app: DeskApp, roots, resources, llm, media, library, arbiter, gateway):
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

    table = [
        ("GET", "/api/config", lambda _req: {
            **config.read_config(roots).to_json(),
            "needs_setup": config.read_config(roots).needs_setup,
        }),
        ("PUT", "/api/config", lambda req: config.update_config(roots, **req.body).to_json()),
        ("GET", "/api/paths", lambda _req: {"data_root": str(roots.data_root),
                                                "models_root": str(roots.models_root),
                                                "outputs_root": str(roots.outputs_root)}),
        ("POST", "/api/first-run", lambda _req: firstrun.complete_first_run(roots).to_json()),
        ("POST", "/api/adopt", adopt),
        ("GET", "/api/resources/catalog", lambda _req: {
            "models": [entry.to_json() for entry in resources.list_catalog()]}),
        ("GET", "/api/resources/status", lambda _req: {
            "models": [status.to_json() for status in resources.verify_all_models()],
            "disk": resources.disk_usage().to_json()}),
        ("GET", "/api/resources/status/", lambda _req: {
            "models": [status.to_json() for status in resources.verify_all_models()]}),
        ("GET", "/api/resources/disk", lambda _req: resources.disk_usage().to_json()),
        ("GET", "/api/resources/download", lambda _req: resources.download_progress().__dict__),
        ("POST", "/api/resources/download", lambda req: resources.start_download(str(req.body.get("key", ""))).__dict__),
        ("POST", "/api/resources/download/cancel", lambda _req: resources.cancel_download().__dict__),
        ("POST", "/api/resources/delete", lambda req: resources.delete_model(
            str(req.body.get("key", "")), req.body.get("confirm"))),
        ("GET", "/api/llm/status", lambda _req: llm.status()),
        ("POST", "/api/llm/load", lambda req: {"state": llm.load(str(req.body.get("key", "")))}),
        ("POST", "/api/llm/unload", lambda _req: {"state": llm.unload()}),
        ("POST", "/api/llm/chat", lambda req: llm.chat_completion(req.body)),
        ("POST", "/api/llm/chat/stream", lambda req: {
            "events": list(llm.chat_stream(req.body))}),
        ("POST", "/api/media/video", lambda req: media.start_video_job(**req.body)),
        ("POST", "/api/media/music", lambda req: media.start_music_job(**req.body)),
        ("POST", "/api/media/cancel", lambda _req: media.cancel_job()),
        ("GET", "/api/media/job", lambda _req: media.job_status()),
        ("GET", "/api/state", lambda _req: arbiter.desk_state()),
        ("GET", "/api/memory", lambda _req: arbiter.memory_snapshot()),
        ("GET", "/api/outputs", lambda _req: library.list_outputs()),
        ("GET", "/api/history", lambda _req: library.list_history()),
        ("GET", "/api/sessions", lambda _req: library.list_chat_sessions()),
        ("POST", "/api/sessions", lambda req: library.create_chat_session(
            req.body.get("title"), req.body.get("model"))),
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
        can_start_heavy=arbiter.can_start_heavy,
        fetcher=_manifest_fetcher,
        executor=FakeDownloadExecutor(download_control),
        clock=clock,
        sleep=lambda _seconds: None,
    )
    library = LibraryService(roots)
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
    unsubscribe = arbiter.subscribe(llm.on_heavy_state_changed)
    app = DeskApp("127.0.0.1", 0)
    static_assets = StaticAssets(roots.static_dir)
    handler_type = app._server.RequestHandlerClass
    dispatch_json = handler_type._dispatch

    def dispatch_with_static(handler, method: str) -> None:
        resolved = static_assets.resolve(handler.path)
        if resolved is None:
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
    gateway = GatewayService(
        _GatewayBackend(llm, arbiter),
        lambda: config.read_config(roots).to_json(),
    )
    route_specs = _mount_routes(app, roots, resources, llm, media, library, arbiter, gateway)
    app.start_background()
    if configured and gateway_enabled:
        gateway.start_from_config()
    return TestHarness(
        app, gateway, roots, arbiter, resources, llm, media, library,
        chat_script, media_script, download_control, clock,
        f"http://127.0.0.1:{app.port}", roots.data_root, roots.models_root,
        roots.outputs_root, gateway_port, seeded, route_specs, _unsubscribe=unsubscribe,
    )
