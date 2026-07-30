"""Sampler — grabs a frame every k seconds and puts it on the LatestSlot.

Decoupled from the worker (docs/01 §3): the clock keeps ticking even while a VLM
call is in flight, so a slow model degrades to "we skip some samples", not "the
pipeline stalls". On source failure it backs off and reconnects rather than
crashing (docs/01 §4.1).

The loop is split into ``sample_once`` (one iteration, easy to unit test) and
``run`` (the thread loop), following Single Responsibility.
"""

from __future__ import annotations

import logging

from argus.clock import Clock, SystemClock
from argus.domain import AnalysisUnit
from argus.metrics import Metrics
from argus.pipeline.latest_slot import LatestSlot
from argus.sources.base import FrameSource, SourceError

log = logging.getLogger("argus.sampler")

_BACKOFF_SCHEDULE = (2.0, 4.0, 8.0, 16.0)


class Sampler:
    def __init__(
        self,
        *,
        source: FrameSource,
        slot: LatestSlot[AnalysisUnit],
        interval_seconds: float,
        metrics: Metrics | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._source = source
        self._slot = slot
        self._interval = interval_seconds
        self._metrics = metrics or Metrics()
        self._clock = clock or SystemClock()
        self._stop = False
        self._reconnects = 0

    def sample_once(self) -> AnalysisUnit | None:
        """Grab one frame and enqueue it. Returns the unit, or ``None`` if the
        source yielded nothing (hiccup or EOF). Raises ``SourceError`` upward
        only for the caller/loop to handle reconnection."""
        frame = self._source.read()
        if frame is None:
            return None
        unit = AnalysisUnit.from_frame(frame)
        self._slot.put(unit)
        self._metrics.inc("frames_sampled")
        return unit

    def run(self) -> None:
        """Thread entrypoint: open the source, then sample on the k-second clock
        until stopped or the source is exhausted."""
        self._open_with_backoff()
        while not self._stop:
            start = self._clock.monotonic()
            try:
                unit = self.sample_once()
                if unit is None and self._is_finite_eof():
                    log.info("source exhausted; sampler stopping")
                    break
            except SourceError as exc:
                log.warning("source read failed: %s", exc)
                self._metrics.inc("source_errors")
                self._reconnect()
                continue
            self._sleep_remaining(start)

    def stop(self) -> None:
        self._stop = True

    # ---- internals -----------------------------------------------------------

    def _is_finite_eof(self) -> bool:
        # A finite source (a file) returning None means EOF; a live source
        # returning None is a hiccup we keep polling through. We treat only the
        # file source as finite here via duck-typing on the class name to avoid a
        # hard import of the optional OpenCV module.
        return type(self._source).__name__ in {"FileVideoSource", "FakeSource"}

    def _sleep_remaining(self, start: float) -> None:
        elapsed = self._clock.monotonic() - start
        self._clock.sleep(max(0.0, self._interval - elapsed))

    def _open_with_backoff(self) -> None:
        try:
            self._source.open()
        except SourceError as exc:
            log.warning("initial source open failed: %s", exc)
            self._reconnect()

    def _reconnect(self) -> None:
        if self._stop:
            return
        delay = _BACKOFF_SCHEDULE[min(self._reconnects, len(_BACKOFF_SCHEDULE) - 1)]
        self._reconnects += 1
        self._metrics.inc("reconnects")
        log.info("reconnecting to source in %.0fs (attempt %d)", delay, self._reconnects)
        self._clock.sleep(delay)
        try:
            self._source.close()
        except Exception:  # best-effort cleanup
            pass
        try:
            self._source.open()
            self._reconnects = 0
        except SourceError as exc:
            log.warning("reconnect failed: %s", exc)
