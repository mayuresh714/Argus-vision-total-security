"""Robust parsing of model output into a structured assessment.

VLMs don't always return clean JSON — they wrap it in prose or code fences. This
parser extracts the first JSON object, coerces/validates the fields, and clamps
the score. On unrecoverable output it raises so the caller records a parse error
rather than emitting a bogus high-confidence result (docs/01 §8.2, docs/02 B1.7).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


class ParseError(ValueError):
    """Raised when model output contains no usable assessment JSON."""


@dataclass(frozen=True)
class ParsedAssessment:
    """Transport-agnostic result of parsing model text.

    The backend wraps this into a full ``SuspicionResult`` by adding model name
    and measured latency.
    """

    score: float
    reason: str
    tags: tuple[str, ...]


def parse_assessment(text: str) -> ParsedAssessment:
    payload = _extract_json(text)

    if "score" not in payload:
        raise ParseError("assessment JSON missing 'score'")

    score = _coerce_score(payload["score"])
    reason = str(payload.get("reason", "")).strip()
    tags = _coerce_tags(payload.get("tags"))
    return ParsedAssessment(score=score, reason=reason, tags=tags)


def _extract_json(text: str) -> dict:
    if not text or not text.strip():
        raise ParseError("empty model output")

    # Fast path: the whole string is JSON.
    stripped = text.strip()
    try:
        obj = json.loads(stripped)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass

    # Lenient path: find the first {...} block (handles code fences / prose).
    match = _JSON_OBJECT_RE.search(text)
    if match:
        try:
            obj = json.loads(match.group(0))
            if isinstance(obj, dict):
                return obj
        except json.JSONDecodeError as exc:
            raise ParseError(f"could not decode embedded JSON: {exc}") from exc

    raise ParseError("no JSON object found in model output")


def _coerce_score(value: object) -> float:
    try:
        score = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError) as exc:
        raise ParseError(f"score is not a number: {value!r}") from exc
    # Clamp rather than reject: a model saying 1.2 clearly means "very high".
    return max(0.0, min(1.0, score))


def _coerce_tags(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value.strip(),) if value.strip() else ()
    if isinstance(value, (list, tuple)):
        return tuple(str(t).strip() for t in value if str(t).strip())
    return ()
