import pytest

from argus.domain import AnalysisUnit, Frame, utcnow
from argus.vlm.base import VlmError
from argus.vlm.mock_backend import MockVlmBackend
from argus.vlm.openai_compatible_backend import OpenAiCompatibleVlmBackend
from tests.fakes import FakeTransport, chat_response


def _unit(n=1) -> AnalysisUnit:
    frames = tuple(
        Frame(b"x", "image/jpeg", 10, 10, "cam-01", utcnow()) for _ in range(n)
    )
    return AnalysisUnit(frames=frames, camera_id="cam-01", captured_at=utcnow())


def test_mock_scripted_scores_in_order():
    vlm = MockVlmBackend(scores=[0.1, 0.9])
    assert vlm.assess(_unit()).score == 0.1
    assert vlm.assess(_unit()).score == 0.9
    # Past the end, defaults to 0.0 (quiet) when not looping.
    assert vlm.assess(_unit()).score == 0.0


def test_mock_scorer_callable():
    vlm = MockVlmBackend(scorer=lambda u: (0.7, "concealment", ["theft"]))
    r = vlm.assess(_unit())
    assert r.score == 0.7
    assert r.tags == ("theft",)


def test_mock_can_force_failure():
    vlm = MockVlmBackend(scores=[0.5], raise_on=0)
    with pytest.raises(VlmError):
        vlm.assess(_unit())


def test_mock_requires_exactly_one_mode():
    with pytest.raises(ValueError):
        MockVlmBackend()
    with pytest.raises(ValueError):
        MockVlmBackend(scores=[0.1], scorer=lambda u: (0.1, "", []))


def test_openai_backend_parses_response():
    transport = FakeTransport(
        response=chat_response('{"score": 0.82, "tags": ["concealment"], "reason": "hidden item"}')
    )
    vlm = OpenAiCompatibleVlmBackend(
        endpoint="http://x/v1/chat/completions", model="qwen-vl", transport=transport
    )
    r = vlm.assess(_unit())
    assert r.score == 0.82
    assert r.tags == ("concealment",)
    assert r.model == "qwen-vl"
    # One system + one user message, user carries the image.
    body = transport.requests[0][1]
    assert body["messages"][0]["role"] == "system"
    assert any(part["type"] == "image_url" for part in body["messages"][1]["content"])


def test_openai_backend_multi_frame_sends_all_images():
    transport = FakeTransport(response=chat_response('{"score": 0.3, "reason": "ok"}'))
    vlm = OpenAiCompatibleVlmBackend(
        endpoint="http://x", model="qwen-vl", transport=transport
    )
    vlm.assess(_unit(n=3))
    images = [p for p in transport.requests[0][1]["messages"][1]["content"] if p["type"] == "image_url"]
    assert len(images) == 3


def test_openai_backend_wraps_transport_error_as_vlmerror():
    transport = FakeTransport(error=RuntimeError("boom"))
    vlm = OpenAiCompatibleVlmBackend(endpoint="http://x", model="m", transport=transport)
    with pytest.raises(VlmError):
        vlm.assess(_unit())


def test_openai_backend_unparseable_output_raises_vlmerror():
    transport = FakeTransport(response=chat_response("I cannot help with that"))
    vlm = OpenAiCompatibleVlmBackend(endpoint="http://x", model="m", transport=transport)
    with pytest.raises(VlmError):
        vlm.assess(_unit())
