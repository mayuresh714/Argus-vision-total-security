"""Pydantic response models for the API — the public shape of Events/Alerts.

Kept separate from the domain dataclasses so the wire format can evolve
independently of internal models.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from argus.domain import Alert, Event


class EventOut(BaseModel):
    id: str
    camera_id: str
    captured_at: datetime
    score: float
    severity: str
    reason: str
    tags: list[str]
    model: str
    vlm_latency_ms: int
    became_alert: bool
    evidence_path: str | None = None

    @classmethod
    def of(cls, e: Event) -> "EventOut":
        return cls(
            id=e.id,
            camera_id=e.camera_id,
            captured_at=e.captured_at,
            score=e.score,
            severity=e.severity.value,
            reason=e.reason,
            tags=list(e.tags),
            model=e.model,
            vlm_latency_ms=e.vlm_latency_ms,
            became_alert=e.became_alert,
            evidence_path=e.evidence_path,
        )


class AlertOut(BaseModel):
    id: str
    event_id: str
    camera_id: str
    captured_at: datetime
    score: float
    severity: str
    reason: str
    tags: list[str]
    evidence_path: str | None = None
    notified_channels: list[str]

    @classmethod
    def of(cls, a: Alert) -> "AlertOut":
        return cls(
            id=a.id,
            event_id=a.event_id,
            camera_id=a.camera_id,
            captured_at=a.captured_at,
            score=a.score,
            severity=a.severity.value,
            reason=a.reason,
            tags=list(a.tags),
            evidence_path=a.evidence_path,
            notified_channels=list(a.notified_channels),
        )


class HealthOut(BaseModel):
    status: str
    running: bool
    camera_id: str
    sample_interval_seconds: float


class ControlOut(BaseModel):
    running: bool
