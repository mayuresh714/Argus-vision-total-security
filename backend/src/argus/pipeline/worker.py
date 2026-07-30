"""InferenceWorker — consumes analysis units and produces events/alerts.

For each unit: call the VLM, score it, run the decision policy, record an Event,
and raise an Alert if warranted. Every failure mode (VLM error, etc.) is caught
so a bad sample is skipped, never fatal (docs/01 §8.2).

Split into ``process`` (one unit — pure, testable) and ``run`` (the thread loop).
"""

from __future__ import annotations

import logging

from argus.alerting.manager import AlertManager
from argus.decision.engine import DecisionEngine
from argus.domain import AnalysisUnit, Event
from argus.metrics import Metrics
from argus.pipeline.latest_slot import LatestSlot
from argus.vlm.base import VlmBackend, VlmError

log = logging.getLogger("argus.worker")


class InferenceWorker:
    def __init__(
        self,
        *,
        slot: LatestSlot[AnalysisUnit],
        vlm: VlmBackend,
        decision_engine: DecisionEngine,
        alert_manager: AlertManager,
        repository,
        metrics: Metrics | None = None,
        poll_timeout: float = 0.5,
    ) -> None:
        self._slot = slot
        self._vlm = vlm
        self._decision = decision_engine
        self._alerts = alert_manager
        self._repo = repository
        self._metrics = metrics or Metrics()
        self._poll_timeout = poll_timeout
        self._stop = False

    def process(self, unit: AnalysisUnit) -> Event | None:
        """Run the full per-unit pipeline. Returns the recorded Event, or
        ``None`` if the VLM failed and the sample was skipped."""
        self._metrics.inc("vlm_calls")
        try:
            result = self._vlm.assess(unit)
        except VlmError as exc:
            self._metrics.inc("vlm_errors")
            log.warning("VLM assessment failed; skipping sample: %s", exc)
            return None

        self._metrics.observe("vlm_latency_ms", result.latency_ms)

        decision = self._decision.evaluate(result, unit.camera_id)
        event = Event(
            camera_id=unit.camera_id,
            captured_at=unit.captured_at,
            score=result.score,
            severity=decision.severity,
            reason=result.reason,
            tags=result.tags,
            model=result.model,
            vlm_latency_ms=result.latency_ms,
            became_alert=decision.should_alert,
            raw_model_output=result.raw_output,
        )
        self._metrics.inc("events")

        if decision.should_alert:
            # AlertManager persists evidence + sets event.evidence_path, so save
            # the event after raising the alert to capture that path.
            self._alerts.raise_alert(event, unit)
            self._repo.save_event(event)
            log.info(
                "alert raised cam=%s score=%.2f severity=%s",
                event.camera_id,
                event.score,
                event.severity.value,
            )
        else:
            self._repo.save_event(event)

        return event

    def run(self) -> None:
        """Thread entrypoint: consume the slot until stopped."""
        while not self._stop:
            unit = self._slot.get(timeout=self._poll_timeout)
            if unit is None:
                continue
            try:
                self.process(unit)
            except Exception:  # last-resort guard: one bad unit never kills the loop
                self._metrics.inc("worker_errors")
                log.exception("unexpected error processing unit; continuing")

    def stop(self) -> None:
        self._stop = True
