"""Core domain models.

These are deliberately immutable value objects (frozen dataclasses) where they
represent an observation at a point in time, and plain dataclasses for records
that accumulate a little state. Nothing here imports anything outside the stdlib
so the domain stays portable and trivially testable.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


def utcnow() -> datetime:
    """Timezone-aware current UTC time. Injected via clocks elsewhere for tests."""
    return datetime.now(timezone.utc)


def new_id() -> str:
    """Opaque unique identifier for events/alerts."""
    return uuid.uuid4().hex


@dataclass(frozen=True)
class Frame:
    """A single decoded-and-encoded image sampled from a source.

    The image is carried as already-encoded bytes (e.g. JPEG) so the core
    pipeline never needs numpy/OpenCV in memory — only the concrete sources that
    produce frames do.
    """

    image_bytes: bytes
    media_type: str  # e.g. "image/jpeg"
    width: int
    height: int
    camera_id: str
    captured_at: datetime


@dataclass(frozen=True)
class AnalysisUnit:
    """What a single VLM call sees.

    v0 = exactly one frame, but the type is a tuple of frames so the same
    interface supports an N-frame stack or a short clip later (see docs/01 and
    docs/02 on the image-vs-video decision) without changing the pipeline.
    """

    frames: tuple[Frame, ...]
    camera_id: str
    captured_at: datetime

    def __post_init__(self) -> None:
        if not self.frames:
            raise ValueError("AnalysisUnit requires at least one frame")

    @property
    def primary(self) -> Frame:
        """The representative frame (first). Used as the evidence image in v0."""
        return self.frames[0]

    @classmethod
    def from_frame(cls, frame: Frame) -> "AnalysisUnit":
        return cls(frames=(frame,), camera_id=frame.camera_id, captured_at=frame.captured_at)


@dataclass(frozen=True)
class SuspicionResult:
    """A VLM's structured judgement about one AnalysisUnit."""

    score: float  # in [0.0, 1.0]
    reason: str
    tags: tuple[str, ...]
    model: str
    latency_ms: int
    raw_output: str = ""

    def __post_init__(self) -> None:
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"score must be in [0,1], got {self.score}")


class Severity(str, Enum):
    """Confidence tier for an observation. See docs/02 B1.3 — Argus surfaces
    tiers, not a binary alarm, to protect operator trust."""

    INFO = "info"
    REVIEW = "review"
    NOTIFY = "notify"
    URGENT = "urgent"


@dataclass
class Event:
    """Every scored observation Argus records — alerting or not."""

    camera_id: str
    captured_at: datetime
    score: float
    severity: Severity
    reason: str
    tags: tuple[str, ...]
    model: str
    vlm_latency_ms: int
    became_alert: bool = False
    evidence_path: str | None = None
    raw_model_output: str = ""
    id: str = field(default_factory=new_id)
    created_at: datetime = field(default_factory=utcnow)


@dataclass
class Alert:
    """An Event that crossed threshold and passed the debounce policy."""

    event_id: str
    camera_id: str
    captured_at: datetime
    score: float
    severity: Severity
    reason: str
    tags: tuple[str, ...]
    evidence_path: str | None = None
    notified_channels: tuple[str, ...] = ()
    id: str = field(default_factory=new_id)
    created_at: datetime = field(default_factory=utcnow)
