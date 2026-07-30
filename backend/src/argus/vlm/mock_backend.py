"""A deterministic VLM backend for tests, demos, and CI.

Two modes:
  * scripted  — return a predefined list of scores in order (great for pinning
                pipeline/debounce behaviour in tests).
  * scorer    — call a user-supplied function(unit) -> (score, reason, tags).

No network, no model weights, fully deterministic.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from argus.domain import AnalysisUnit, SuspicionResult
from argus.vlm.base import VlmBackend, VlmError

Scorer = Callable[[AnalysisUnit], "tuple[float, str, Sequence[str]]"]


class MockVlmBackend(VlmBackend):
    def __init__(
        self,
        *,
        scores: Sequence[float] | None = None,
        scorer: Scorer | None = None,
        model_name: str = "mock-vlm",
        latency_ms: int = 5,
        loop: bool = False,
        raise_on: int | None = None,
    ) -> None:
        if (scores is None) == (scorer is None):
            raise ValueError("provide exactly one of `scores` or `scorer`")
        self._scores = list(scores) if scores is not None else None
        self._scorer = scorer
        self._model_name = model_name
        self._latency_ms = latency_ms
        self._loop = loop
        self._raise_on = raise_on
        self._calls = 0

    @property
    def model_name(self) -> str:
        return self._model_name

    def assess(self, unit: AnalysisUnit) -> SuspicionResult:
        idx = self._calls
        self._calls += 1

        if self._raise_on is not None and idx == self._raise_on:
            raise VlmError(f"mock backend forced failure on call {idx}")

        if self._scorer is not None:
            score, reason, tags = self._scorer(unit)
        else:
            assert self._scores is not None
            if idx >= len(self._scores):
                if self._loop and self._scores:
                    score = self._scores[idx % len(self._scores)]
                else:
                    score = 0.0
            else:
                score = self._scores[idx]
            reason = f"mock score {score:.2f}"
            tags = ("mock",)

        return SuspicionResult(
            score=max(0.0, min(1.0, float(score))),
            reason=reason,
            tags=tuple(tags),
            model=self._model_name,
            latency_ms=self._latency_ms,
            raw_output="mock",
        )
