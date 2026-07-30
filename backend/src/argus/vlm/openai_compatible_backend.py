"""A VLM backend that talks to any OpenAI-compatible vision chat endpoint.

This one interface reaches almost everything we care about (docs/02 B2):
  * local open models served by vLLM / Ollama / llama.cpp / TGI  (the workhorse)
  * hosted frontier models behind an OpenAI-style proxy          (escalation)

Uses only the stdlib (``urllib``) for HTTP so the core carries no ``requests``
dependency. The API key is read from an environment variable named in config —
never stored in the config file itself.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request

from argus.domain import AnalysisUnit, SuspicionResult
from argus.vlm.base import VlmBackend, VlmError
from argus.vlm.parser import ParseError, parse_assessment
from argus.vlm.prompt import build_messages


class OpenAiCompatibleVlmBackend(VlmBackend):
    def __init__(
        self,
        *,
        endpoint: str,
        model: str,
        api_key_env: str = "ARGUS_VLM_API_KEY",
        timeout_seconds: float = 20.0,
        max_tokens: int = 256,
        temperature: float = 0.0,
        transport: "Transport | None" = None,
    ) -> None:
        self._endpoint = endpoint
        self._model = model
        self._api_key = os.environ.get(api_key_env, "")
        self._timeout = timeout_seconds
        self._max_tokens = max_tokens
        self._temperature = temperature
        # Injected transport enables unit-testing without real HTTP (DIP).
        self._transport = transport or _UrllibTransport()

    @property
    def model_name(self) -> str:
        return self._model

    def assess(self, unit: AnalysisUnit) -> SuspicionResult:
        body = {
            "model": self._model,
            "messages": build_messages(unit),
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        started = time.monotonic()
        try:
            raw = self._transport.post_json(
                self._endpoint, body, headers, timeout=self._timeout
            )
        except Exception as exc:
            # I/O boundary: any transport failure becomes a VlmError so the
            # worker can skip the sample instead of crashing (docs/01 §8.2).
            raise VlmError(f"VLM transport error: {exc}") from exc
        latency_ms = int((time.monotonic() - started) * 1000)

        text = _extract_message_text(raw)
        try:
            parsed = parse_assessment(text)
        except ParseError as exc:
            raise VlmError(f"unparseable VLM output: {exc}") from exc

        return SuspicionResult(
            score=parsed.score,
            reason=parsed.reason,
            tags=parsed.tags,
            model=self._model,
            latency_ms=latency_ms,
            raw_output=text,
        )


def _extract_message_text(response: dict) -> str:
    try:
        return response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise VlmError(f"unexpected VLM response shape: {exc}") from exc


# --- transport seam ----------------------------------------------------------


class TransportError(RuntimeError):
    """HTTP/transport failure, decoupled from urllib specifics."""


class Transport:
    """Minimal transport protocol so backends can be tested without networking."""

    def post_json(
        self, url: str, body: dict, headers: dict, *, timeout: float
    ) -> dict:  # pragma: no cover - interface
        raise NotImplementedError


class _UrllibTransport(Transport):
    def post_json(self, url: str, body: dict, headers: dict, *, timeout: float) -> dict:
        data = json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise TransportError(f"HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise TransportError(str(exc)) from exc
