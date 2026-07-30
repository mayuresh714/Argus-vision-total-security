"""Test doubles shared across the suite.

These make the pipeline deterministic without real time, networking, or a camera
— the payoff of injecting Clock/Transport/Notifier/FrameSource everywhere.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from argus.alerting.notifiers import Notifier
from argus.domain import Alert


class FakeClock:
    """Controllable clock. ``advance`` moves time without sleeping; ``sleep``
    records requested sleeps and also advances (so busy loops terminate)."""

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 1, 1, tzinfo=timezone.utc)
        self._mono = 0.0
        self.sleeps: list[float] = []

    def now(self) -> datetime:
        return self._now

    def monotonic(self) -> float:
        return self._mono

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.advance(seconds)

    def advance(self, seconds: float) -> None:
        self._mono += seconds
        self._now += timedelta(seconds=seconds)


class RecordingNotifier(Notifier):
    """Captures delivered alerts; can be told to fail to test isolation."""

    def __init__(self, channel: str = "recording", *, fail: bool = False) -> None:
        self._channel = channel
        self._fail = fail
        self.delivered: list[Alert] = []
        self.attempts = 0

    @property
    def channel(self) -> str:
        return self._channel

    def notify(self, alert: Alert) -> None:
        self.attempts += 1
        if self._fail:
            raise RuntimeError("recording notifier forced failure")
        self.delivered.append(alert)


class FakeTransport:
    """Stand-in for the OpenAI-compatible HTTP transport."""

    def __init__(self, response: dict | None = None, error: Exception | None = None) -> None:
        self._response = response
        self._error = error
        self.requests: list[tuple[str, dict, dict]] = []

    def post_json(self, url: str, body: dict, headers: dict, *, timeout: float) -> dict:
        self.requests.append((url, body, headers))
        if self._error is not None:
            raise self._error
        assert self._response is not None
        return self._response


def chat_response(text: str) -> dict:
    """Build a minimal OpenAI-style chat completion carrying ``text``."""
    return {"choices": [{"message": {"content": text}}]}
