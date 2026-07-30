"""HTTP surface (FastAPI). Thin read/control layer over the running service."""

from argus.api.app import create_app

__all__ = ["create_app"]
