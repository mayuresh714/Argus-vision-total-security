"""Vision-Language Model layer: the reasoning engine.

    VlmBackend                 - the Strategy interface the worker depends on
    MockVlmBackend             - scripted/rule-based scoring (tests, demos, CI)
    OpenAiCompatibleVlmBackend - talks to any OpenAI-style vision endpoint
                                 (vLLM / Ollama / hosted Gemini|GPT|Claude proxy)

    build_prompt / parse_assessment - prompt construction and robust output
                                      parsing, kept separate from transport.
"""

from argus.vlm.base import VlmBackend, VlmError
from argus.vlm.mock_backend import MockVlmBackend
from argus.vlm.parser import ParsedAssessment, parse_assessment
from argus.vlm.prompt import build_messages, build_prompt

__all__ = [
    "VlmBackend",
    "VlmError",
    "MockVlmBackend",
    "ParsedAssessment",
    "parse_assessment",
    "build_prompt",
    "build_messages",
]
