"""Logging setup. Kept trivial for v0; swap for structured JSON logs when the
observability story (docs/01 §9) grows."""

from __future__ import annotations

import logging


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s :: %(message)s",
    )
