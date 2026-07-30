"""LatestSlot — a size-1, drop-oldest handoff between sampler and worker.

This is the concrete expression of the core design choice in docs/01 §3: when
the VLM is slower than the sampling interval, we must analyse the *freshest*
frame and drop stale ones, never build a backlog. "Argus is about now."

Thread-safe: one producer (sampler), one consumer (worker), but written to be
safe for many of each.
"""

from __future__ import annotations

import threading
from typing import Generic, TypeVar

T = TypeVar("T")


class LatestSlot(Generic[T]):
    def __init__(self) -> None:
        self._cond = threading.Condition()
        self._item: T | None = None
        self._has_item = False
        self._closed = False
        self._dropped = 0

    @property
    def dropped(self) -> int:
        """Count of items overwritten before being consumed."""
        with self._cond:
            return self._dropped

    def put(self, item: T) -> None:
        """Store ``item``, discarding any previous unconsumed item."""
        with self._cond:
            if self._closed:
                return
            if self._has_item:
                self._dropped += 1
            self._item = item
            self._has_item = True
            self._cond.notify()

    def get(self, timeout: float | None = None) -> T | None:
        """Return the latest item, or ``None`` if it times out or the slot is
        closed and empty."""
        with self._cond:
            if not self._has_item and not self._closed:
                self._cond.wait(timeout)
            if not self._has_item:
                return None
            item = self._item
            self._item = None
            self._has_item = False
            return item

    def close(self) -> None:
        """Wake any waiting consumer so it can exit."""
        with self._cond:
            self._closed = True
            self._cond.notify_all()
