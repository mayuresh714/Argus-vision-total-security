"""In-memory Repository — dict-backed, thread-safe, for tests and demos."""

from __future__ import annotations

import threading

from argus.domain import Alert, Event
from argus.storage.base import Repository


class InMemoryRepository(Repository):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: dict[str, Event] = {}
        self._alerts: dict[str, Alert] = {}
        # Insertion order = chronological; we reverse for most-recent-first.
        self._event_order: list[str] = []
        self._alert_order: list[str] = []

    def save_event(self, event: Event) -> None:
        with self._lock:
            if event.id not in self._events:
                self._event_order.append(event.id)
            self._events[event.id] = event

    def save_alert(self, alert: Alert) -> None:
        with self._lock:
            if alert.id not in self._alerts:
                self._alert_order.append(alert.id)
            self._alerts[alert.id] = alert

    def list_events(self, *, limit: int = 100, camera_id: str | None = None) -> list[Event]:
        with self._lock:
            items = [self._events[i] for i in reversed(self._event_order)]
        if camera_id is not None:
            items = [e for e in items if e.camera_id == camera_id]
        return items[:limit]

    def list_alerts(self, *, limit: int = 100, camera_id: str | None = None) -> list[Alert]:
        with self._lock:
            items = [self._alerts[i] for i in reversed(self._alert_order)]
        if camera_id is not None:
            items = [a for a in items if a.camera_id == camera_id]
        return items[:limit]

    def get_event(self, event_id: str) -> Event | None:
        with self._lock:
            return self._events.get(event_id)

    def get_alert(self, alert_id: str) -> Alert | None:
        with self._lock:
            return self._alerts.get(alert_id)
