"""Time abstraction.

The pipeline never calls ``datetime.now``/``time.sleep`` directly — it depends on
these small protocols. Production wires the real clock; tests wire a controllable
one. This is the Dependency Inversion Principle applied to *time*, which is what
makes the debounce/cooldown logic deterministically testable.
"""

from __future__ import annotations

import time
from datetime import datetime
from typing import Protocol

from argus.domain import utcnow


class Clock(Protocol):
    def now(self) -> datetime:
        """Current timezone-aware time."""

    def monotonic(self) -> float:
        """Monotonic seconds, for measuring durations."""

    def sleep(self, seconds: float) -> None:
        """Block for ``seconds``."""


class SystemClock:
    """Real wall-clock + monotonic time backed by the stdlib."""

    def now(self) -> datetime:
        return utcnow()

    def monotonic(self) -> float:
        return time.monotonic()

    def sleep(self, seconds: float) -> None:
        if seconds > 0:
            time.sleep(seconds)
