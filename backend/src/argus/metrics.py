"""Lightweight, thread-safe in-process metrics.

Deliberately tiny: counters + latency samples with a snapshot. Enough for the
observability requirements in docs/01 §9 without pulling a metrics framework into
an edge-deployable core. A Prometheus/OTel exporter can wrap ``snapshot()`` later.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field


@dataclass
class _Latency:
    count: int = 0
    total_ms: float = 0.0
    max_ms: float = 0.0

    def observe(self, ms: float) -> None:
        self.count += 1
        self.total_ms += ms
        self.max_ms = max(self.max_ms, ms)

    @property
    def avg_ms(self) -> float:
        return self.total_ms / self.count if self.count else 0.0


class Metrics:
    """Named counters and latency histograms guarded by a single lock."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: dict[str, int] = {}
        self._latencies: dict[str, _Latency] = {}

    def inc(self, name: str, by: int = 1) -> None:
        with self._lock:
            self._counters[name] = self._counters.get(name, 0) + by

    def observe(self, name: str, ms: float) -> None:
        with self._lock:
            self._latencies.setdefault(name, _Latency()).observe(ms)

    def snapshot(self) -> dict[str, object]:
        with self._lock:
            return {
                "counters": dict(self._counters),
                "latency_ms": {
                    name: {"count": lat.count, "avg": round(lat.avg_ms, 2), "max": round(lat.max_ms, 2)}
                    for name, lat in self._latencies.items()
                },
            }
