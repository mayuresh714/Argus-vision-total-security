"""Notifier implementations (Strategy pattern).

Each notifier delivers an Alert one way. They are intentionally dumb and
independent — the AlertManager owns fan-out and error isolation, so a single
broken channel never blocks the others or the pipeline (docs/01 §4.5).
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from abc import ABC, abstractmethod

from argus.domain import Alert

log = logging.getLogger("argus.alert")


class Notifier(ABC):
    """Delivers an alert through one channel."""

    @property
    @abstractmethod
    def channel(self) -> str:
        """Short channel name, recorded on the Alert (e.g. 'console')."""

    @abstractmethod
    def notify(self, alert: Alert) -> None:
        """Deliver ``alert``. May raise; the AlertManager isolates failures."""


class ConsoleNotifier(Notifier):
    """Logs the alert. The default, always-available channel."""

    @property
    def channel(self) -> str:
        return "console"

    def notify(self, alert: Alert) -> None:
        log.warning(
            "ALERT [%s] cam=%s score=%.2f :: %s",
            alert.severity.value.upper(),
            alert.camera_id,
            alert.score,
            alert.reason,
        )


class FileNotifier(Notifier):
    """Appends alerts as JSON lines to a file (a simple durable audit sink)."""

    def __init__(self, path: str) -> None:
        self._path = path

    @property
    def channel(self) -> str:
        return "file"

    def notify(self, alert: Alert) -> None:
        record = {
            "id": alert.id,
            "camera_id": alert.camera_id,
            "captured_at": alert.captured_at.isoformat(),
            "score": alert.score,
            "severity": alert.severity.value,
            "reason": alert.reason,
            "tags": list(alert.tags),
            "evidence_path": alert.evidence_path,
        }
        with open(self._path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(record) + "\n")


class WebhookNotifier(Notifier):
    """POSTs the alert as JSON to a URL (phone push / SOC / VMS bridge downstream).

    HTTP is done with the stdlib and an injectable poster so it's unit-testable
    without real networking.
    """

    def __init__(self, url: str, *, timeout: float = 5.0, poster=None) -> None:
        self._url = url
        self._timeout = timeout
        self._poster = poster or _urllib_post

    @property
    def channel(self) -> str:
        return "webhook"

    def notify(self, alert: Alert) -> None:
        payload = {
            "id": alert.id,
            "camera_id": alert.camera_id,
            "captured_at": alert.captured_at.isoformat(),
            "score": alert.score,
            "severity": alert.severity.value,
            "reason": alert.reason,
            "tags": list(alert.tags),
            "evidence_path": alert.evidence_path,
        }
        self._poster(self._url, payload, self._timeout)


def _urllib_post(url: str, payload: dict, timeout: float) -> None:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return
    except (urllib.error.URLError, TimeoutError) as exc:  # pragma: no cover - network
        raise RuntimeError(f"webhook POST failed: {exc}") from exc
