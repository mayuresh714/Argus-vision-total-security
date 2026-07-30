"""A dependency-free source that replays scripted frames.

Used by tests, CI, and offline demos so the whole pipeline can run without a
camera or OpenCV. Also the simplest possible reference implementation of the
``FrameSource`` contract.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from argus.domain import Frame, utcnow
from argus.sources.base import FrameSource, SourceError


class FakeSource(FrameSource):
    """Yields a predefined list of frames, then reports exhaustion (``None``).

    If ``loop`` is True it repeats forever (handy for a live-ish demo).
    """

    def __init__(self, frames: Iterable[Frame], *, loop: bool = False) -> None:
        self._frames: list[Frame] = list(frames)
        self._loop = loop
        self._it: Iterator[Frame] | None = None
        self._opened = False

    def open(self) -> None:
        self._it = iter(self._frames)
        self._opened = True

    def read(self) -> Frame | None:
        if not self._opened or self._it is None:
            raise SourceError("FakeSource.read() before open()")
        try:
            return next(self._it)
        except StopIteration:
            if self._loop and self._frames:
                self._it = iter(self._frames)
                return next(self._it)
            return None

    def close(self) -> None:
        self._it = None
        self._opened = False

    @staticmethod
    def solid_frame(camera_id: str = "cam-01", *, width: int = 16, height: int = 16) -> Frame:
        """Build a tiny placeholder frame (opaque bytes) for tests/demos."""
        return Frame(
            image_bytes=b"\x00" * (width * height),
            media_type="image/raw",
            width=width,
            height=height,
            camera_id=camera_id,
            captured_at=utcnow(),
        )
