"""FrameSource abstraction."""

from __future__ import annotations

from abc import ABC, abstractmethod

from argus.domain import Frame


class SourceError(RuntimeError):
    """Raised when a source cannot be opened or read from."""


class FrameSource(ABC):
    """A pull-based source of encoded frames.

    Timing (the k-second cadence) is the Sampler's responsibility, not the
    source's — the source just answers "give me a current frame". This keeps the
    Single Responsibility split clean: sources decode, the sampler schedules.
    """

    @abstractmethod
    def open(self) -> None:
        """Acquire the underlying stream/file. Idempotent."""

    @abstractmethod
    def read(self) -> Frame | None:
        """Return the next frame to analyse, or ``None`` when exhausted
        (e.g. end of a finite file). Raise ``SourceError`` on failure."""

    @abstractmethod
    def close(self) -> None:
        """Release resources. Idempotent."""

    def __enter__(self) -> "FrameSource":
        self.open()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()
