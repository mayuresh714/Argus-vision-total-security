"""Prompt construction.

The prompt is the heart of v0 (docs/01 §6). It is kept here — separate from
transport and parsing — so it can be iterated and A/B tested independently.
It forces structured JSON output and steers the model toward *behaviour-based*
judgement with an explicit anti-bias instruction.
"""

from __future__ import annotations

import base64

from argus.domain import AnalysisUnit

SYSTEM_PROMPT = (
    "You are a security-monitoring assistant reviewing still frames from a fixed "
    "CCTV camera. Judge ONLY the behaviour visible in the frame(s). Do NOT identify "
    "or describe individuals' personal or demographic characteristics.\n\n"
    "Rate how suspicious the scene is from 0.0 (clearly normal) to 1.0 (clearly "
    "theft or a serious security concern). Suspicious cues include: concealing "
    "merchandise on the body or in a bag, tampering with tags or packaging, reaching "
    "into a till or restricted area, forcing a door, or leaving past the point of "
    "payment while concealing an item. Ordinary shopping, browsing, staff activity, "
    "and empty scenes are NOT suspicious.\n\n"
    "If the scene is ambiguous or visibility is poor, prefer a MODERATE score and say "
    "why — do not invent certainty.\n\n"
    'Respond with ONLY this JSON and nothing else:\n'
    '{"score": <float 0..1>, "tags": [<short strings>], "reason": "<one sentence>"}'
)

USER_INSTRUCTION_SINGLE = "Assess this single CCTV frame."
USER_INSTRUCTION_MULTI = (
    "Assess this short sequence of CCTV frames in time order; consider how the "
    "behaviour develops across them."
)


def build_prompt(unit: AnalysisUnit) -> str:
    """Return the plain-text user instruction appropriate for the unit size."""
    return USER_INSTRUCTION_SINGLE if len(unit.frames) == 1 else USER_INSTRUCTION_MULTI


def _data_url(image_bytes: bytes, media_type: str) -> str:
    b64 = base64.b64encode(image_bytes).decode("ascii")
    return f"data:{media_type};base64,{b64}"


def build_messages(unit: AnalysisUnit) -> list[dict]:
    """Build OpenAI-style chat messages (system + user-with-images).

    Works for one frame or many, so the exact same builder supports the
    image-vs-video progression from docs/02 B1.2.
    """
    content: list[dict] = [{"type": "text", "text": build_prompt(unit)}]
    for frame in unit.frames:
        content.append(
            {
                "type": "image_url",
                "image_url": {"url": _data_url(frame.image_bytes, frame.media_type)},
            }
        )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": content},
    ]
