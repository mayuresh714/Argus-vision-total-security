"""VlmBackend — the Strategy interface for suspicion assessment."""

from __future__ import annotations

from abc import ABC, abstractmethod

from argus.domain import AnalysisUnit, SuspicionResult


class VlmError(RuntimeError):
    """Raised when a backend cannot produce a usable assessment (timeout,
    transport error, or unparseable output). The worker catches this and skips
    the sample rather than crashing (docs/01 §8.2)."""


class VlmBackend(ABC):
    """Turns an AnalysisUnit into a SuspicionResult.

    Implementations are interchangeable (mock, local open model, hosted API) —
    the pipeline depends only on this interface, which is what lets us start on a
    frontier API and move to a self-hosted open model without touching the
    pipeline (docs/02 B2)."""

    @abstractmethod
    def assess(self, unit: AnalysisUnit) -> SuspicionResult:
        """Assess one unit. Must raise ``VlmError`` on any failure."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Identifier recorded on every Event for auditing/calibration."""
