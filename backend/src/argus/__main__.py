"""CLI entrypoint: ``python -m argus [--config config.yaml]`` or ``argus``.

Builds the service from config, starts the pipeline threads, and serves the API
with uvicorn. Ctrl-C stops the service cleanly.
"""

from __future__ import annotations

import argparse
import sys

from argus.config import AppConfig
from argus.logging_config import configure_logging


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="argus", description="Argus v0 single-camera service")
    parser.add_argument("--config", "-c", help="Path to config.yaml", default=None)
    parser.add_argument("--no-serve", action="store_true", help="Run pipeline without the HTTP API")
    args = parser.parse_args(argv)

    config = AppConfig.from_yaml(args.config) if args.config else AppConfig()
    configure_logging(config.log_level)

    # Imported here so ``--help`` and config errors don't require the web stack.
    from argus.pipeline.service import build_service

    service = build_service(config)
    service.start()

    if args.no_serve:
        try:
            _block_forever()
        except KeyboardInterrupt:
            pass
        finally:
            service.stop()
        return 0

    import uvicorn

    from argus.api.app import create_app

    app = create_app(service)
    try:
        uvicorn.run(app, host=config.api.host, port=config.api.port, log_level=config.log_level.lower())
    finally:
        service.stop()
    return 0


def _block_forever() -> None:
    import threading

    threading.Event().wait()


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
