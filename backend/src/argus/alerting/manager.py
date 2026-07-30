"""AlertManager — turns an alerting Event into a delivered, persisted Alert."""

from __future__ import annotations

import logging
from collections.abc import Sequence

from argus.alerting.notifiers import Notifier
from argus.domain import Alert, AnalysisUnit, Event
from argus.metrics import Metrics
from argus.storage.base import EvidenceWriter, Repository

log = logging.getLogger("argus.alert")


class AlertManager:
    """Owns the alert side effects: evidence, persistence, notifier fan-out.

    Depends only on abstractions (Repository, EvidenceWriter, Notifier), so it is
    fully testable with in-memory fakes and never knows how anything is stored or
    delivered.
    """

    def __init__(
        self,
        *,
        repository: Repository,
        notifiers: Sequence[Notifier],
        evidence_writer: EvidenceWriter,
        metrics: Metrics | None = None,
        max_notify_retries: int = 1,
    ) -> None:
        self._repo = repository
        self._notifiers = list(notifiers)
        self._evidence = evidence_writer
        self._metrics = metrics or Metrics()
        self._max_retries = max(0, max_notify_retries)

    def raise_alert(self, event: Event, unit: AnalysisUnit) -> Alert:
        """Persist evidence + alert and notify. Notifier failures are isolated
        (logged, retried a bounded number of times) and never propagate."""
        evidence_path = self._safe_write_evidence(unit, event)
        event.evidence_path = evidence_path

        alert = Alert(
            event_id=event.id,
            camera_id=event.camera_id,
            captured_at=event.captured_at,
            score=event.score,
            severity=event.severity,
            reason=event.reason,
            tags=event.tags,
            evidence_path=evidence_path,
        )

        delivered: list[str] = []
        for notifier in self._notifiers:
            if self._deliver(notifier, alert):
                delivered.append(notifier.channel)
        alert.notified_channels = tuple(delivered)

        self._repo.save_alert(alert)
        self._metrics.inc("alerts")
        return alert

    # ---- internals -----------------------------------------------------------

    def _safe_write_evidence(self, unit: AnalysisUnit, event: Event) -> str | None:
        try:
            return self._evidence.write(unit.primary, event_id=event.id)
        except OSError as exc:
            log.error("evidence write failed for event %s: %s", event.id, exc)
            self._metrics.inc("evidence_errors")
            return None

    def _deliver(self, notifier: Notifier, alert: Alert) -> bool:
        attempts = self._max_retries + 1
        for attempt in range(1, attempts + 1):
            try:
                notifier.notify(alert)
                return True
            except Exception as exc:  # notifier isolation: never break the pipeline
                self._metrics.inc("notify_failures")
                log.warning(
                    "notifier %s failed (attempt %d/%d): %s",
                    notifier.channel,
                    attempt,
                    attempts,
                    exc,
                )
        return False
