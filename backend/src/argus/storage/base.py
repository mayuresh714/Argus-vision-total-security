"""Storage abstractions."""

from __future__ import annotations

from abc import ABC, abstractmethod

from argus.domain import Alert, Event, Frame


class Repository(ABC):
    """Persists and retrieves Events and Alerts.

    Kept as one interface (rather than split Event/Alert repos) because in v0
    they share a backend and transaction scope; splitting is a trivial later
    refactor if a store ever needs different backends.
    """

    @abstractmethod
    def save_event(self, event: Event) -> None: ...

    @abstractmethod
    def save_alert(self, alert: Alert) -> None: ...

    @abstractmethod
    def list_events(self, *, limit: int = 100, camera_id: str | None = None) -> list[Event]:
        """Most-recent-first."""

    @abstractmethod
    def list_alerts(self, *, limit: int = 100, camera_id: str | None = None) -> list[Alert]:
        """Most-recent-first."""

    @abstractmethod
    def get_event(self, event_id: str) -> Event | None: ...

    @abstractmethod
    def get_alert(self, alert_id: str) -> Alert | None: ...

    def close(self) -> None:  # optional override
        """Release any underlying resources."""


class EvidenceWriter(ABC):
    """Persists the evidence image for an alert and returns a locator (path)."""

    @abstractmethod
    def write(self, frame: Frame, *, event_id: str) -> str | None:
        """Persist ``frame`` and return a path/locator, or ``None`` if disabled."""
