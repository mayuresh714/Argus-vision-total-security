"""DecisionEngine — the trust-preserving gate between scores and alerts.

Implements the debounce policy from docs/01 §4.4 and docs/02 B1.3, whose entire
purpose is to keep one real incident from becoming an alert storm (the #1 killer
of operator trust):

  * severity tiers      — every score maps to INFO/REVIEW/NOTIFY/URGENT.
  * alert threshold     — only NOTIFY+ scores are candidates to alert.
  * consecutive-N       — require N consecutive over-threshold samples first,
                          trading a little latency for far fewer one-off blips.
  * hysteresis          — the run of over-threshold samples only "clears" once a
                          score drops below ``clear_threshold``, so flicker
                          around the threshold doesn't re-trigger.
  * cooldown            — after firing, suppress further alerts for a window.

State is per-camera (v0 has one, but the structure is already multi-camera-safe).
The clock is injected, so cooldown behaviour is deterministic under test.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from argus.clock import Clock, SystemClock
from argus.config import DecisionConfig
from argus.domain import Severity, SuspicionResult


@dataclass(frozen=True)
class Decision:
    """Outcome of evaluating one SuspicionResult."""

    should_alert: bool
    severity: Severity
    # When ``should_alert`` is False, a short machine-readable reason why:
    # "below_threshold" | "awaiting_consecutive" | "cooldown".
    suppressed_by: str | None = None


@dataclass
class _CameraState:
    consecutive_over: int = 0
    hot: bool = False  # currently inside an un-cleared over-threshold run
    last_alert_at: datetime | None = None


class DecisionEngine:
    def __init__(self, config: DecisionConfig, *, clock: Clock | None = None) -> None:
        config.validate()
        self._cfg = config
        self._clock = clock or SystemClock()
        self._state: dict[str, _CameraState] = {}

    def severity_for(self, score: float) -> Severity:
        cfg = self._cfg
        if score >= cfg.urgent_threshold:
            return Severity.URGENT
        if score >= cfg.notify_threshold:
            return Severity.NOTIFY
        if score >= cfg.review_threshold:
            return Severity.REVIEW
        return Severity.INFO

    def evaluate(self, result: SuspicionResult, camera_id: str) -> Decision:
        cfg = self._cfg
        state = self._state.setdefault(camera_id, _CameraState())
        severity = self.severity_for(result.score)
        score = result.score

        # Below the alert threshold: never alerts. Update hysteresis/run state.
        if score < cfg.alert_threshold:
            state.consecutive_over = 0
            if score < cfg.clear_threshold:
                state.hot = False
            return Decision(False, severity, suppressed_by="below_threshold")

        # At/above the alert threshold.
        state.consecutive_over += 1

        if state.consecutive_over < cfg.consecutive_n:
            return Decision(False, severity, suppressed_by="awaiting_consecutive")

        now = self._clock.now()
        if (
            state.hot
            and state.last_alert_at is not None
            and (now - state.last_alert_at).total_seconds() < cfg.cooldown_seconds
        ):
            return Decision(False, severity, suppressed_by="cooldown")

        # Fire.
        state.hot = True
        state.last_alert_at = now
        return Decision(True, severity)

    def reset(self, camera_id: str | None = None) -> None:
        """Clear debounce state (all cameras, or one). Useful in tests."""
        if camera_id is None:
            self._state.clear()
        else:
            self._state.pop(camera_id, None)
