"""Evidence image writers."""

from __future__ import annotations

import os
from datetime import datetime

from argus.domain import Frame
from argus.storage.base import EvidenceWriter

_EXT_BY_MEDIA = {"image/jpeg": "jpg", "image/png": "png", "image/raw": "bin"}


class NullEvidenceWriter(EvidenceWriter):
    """Persists nothing (tests, or deployments that must not retain images)."""

    def write(self, frame: Frame, *, event_id: str) -> str | None:
        return None


class FileEvidenceWriter(EvidenceWriter):
    """Writes the evidence frame to ``<base_dir>/<camera_id>/<ts>_<event>.<ext>``."""

    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir

    def write(self, frame: Frame, *, event_id: str) -> str | None:
        ext = _EXT_BY_MEDIA.get(frame.media_type, "bin")
        cam_dir = os.path.join(self._base_dir, frame.camera_id)
        os.makedirs(cam_dir, exist_ok=True)
        stamp = _stamp(frame.captured_at)
        path = os.path.join(cam_dir, f"{stamp}_{event_id[:8]}.{ext}")
        with open(path, "wb") as fh:
            fh.write(frame.image_bytes)
        return path


def _stamp(ts: datetime) -> str:
    return ts.strftime("%Y%m%dT%H%M%S")
