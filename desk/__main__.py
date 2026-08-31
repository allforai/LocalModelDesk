"""Run the Desk HTTP service."""
from __future__ import annotations

from .app import DeskApp
from .foundation import capabilities, paths, routes


def build_app(host: str = "127.0.0.1", port: int = 8766) -> DeskApp:
    """Construct the HTTP app without requiring a valid persisted config."""
    roots = paths.resolve_paths(default_config_on_corrupt=True)
    paths.setup_logging(roots)
    app = DeskApp(host, port)
    app.add_routes(routes.build_routes())
    app.capabilities = capabilities.probe_capabilities(roots)
    return app


def main() -> None:
    app = build_app()
    try:
        app.serve_forever()
    finally:
        app.shutdown()


if __name__ == "__main__":
    main()
